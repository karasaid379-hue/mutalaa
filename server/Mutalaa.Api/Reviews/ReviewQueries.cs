using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Lemmas;
using Mutalaa.Domain;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Reviews;

/// <summary>
/// Kuyruk asamasi suzgeci (<c>asama</c>): <see cref="Ilk"/> ilk onay bekleyen (acik, inceleyen yok), <see cref="Ikinci"/> ikinci onay
/// bekleyen (acik, inceleyen dolu, ikinci_inceleyen yok). Etiketler: <c>ilk</c>, <c>ikinci</c>.
/// </summary>
internal enum ReviewStage
{
    Ilk,
    Ikinci,
}

/// <summary>
/// Kuyruk siralamasi (<c>sira</c>): olusturma (varsayilan, created_at ve id), kelime anlami dalgasi (K-50 madde 7) ya da baglanti adayi sinifi
/// (A18.4: tutarsiz, toplu, gri, diger; sinif icinde confidence azalan).
/// </summary>
internal enum ReviewSort
{
    Olusturma,
    Dalga,
    Sinif,
}

/// <summary>Turkce lemma onay yolu suzgeci (<c>onay_yolu</c>): otomatik, editor ya da aday (onay yolu yok).</summary>
internal enum ApprovalFilter
{
    Otomatik,
    Editor,
    Aday,
}

/// <summary>Liste, ayrinti ve istatistik okuma sorgulari: hepsi AsNoTracking ve projeksiyonludur.</summary>
internal static class ReviewQueries
{
    public const int DefaultLimit = 50;
    public const int MaxLimit = 200;

    /// <summary>lemma_dalga satiri olmayan kayitlarin dalga anahtari: gercek dalgalarin (0..4) hepsinden sonra gelir.</summary>
    public const int NoWave = 5;

    /// <summary>Baglanti satiri okunamayan ya da olmayan kayitlarin sinif sirasi: dort sinifin da (0..3) sonrasi.</summary>
    public const int NoClass = 4;

    /// <summary>
    /// Aday sinifinin SQL karsiligi (<see cref="LinkCandidateClassifier"/> ile ayni kural; uyum <c>ReviewLinkClassSqlParityTests</c> ile denetlenir).
    /// jsonb alanlari tur denetiminden sonra sayiya cevrilir (yanlis turde alan "alan yok" sayilir); sinif sirasi <see cref="LinkCandidateClass"/> degeridir.
    /// </summary>
    internal const string ClassSql = """
        SELECT x.id::text AS xref_key,
               CASE
                 WHEN (x.evidence -> 'consistent_quote') = 'false'::jsonb OR (x.type = 'atif' AND x.confidence <= 0.30::real) THEN 0
                 WHEN x.type IN ('iktibas', 'atif')
                      AND CASE WHEN jsonb_typeof(x.evidence -> 'matched_words') = 'number' THEN (x.evidence ->> 'matched_words')::numeric END >= 7
                      AND CASE WHEN jsonb_typeof(x.evidence -> 'coverage') = 'number' THEN (x.evidence ->> 'coverage')::numeric END >= 0.999999
                      AND CASE WHEN jsonb_typeof(x.evidence -> 'phrase_freq') = 'number' THEN (x.evidence ->> 'phrase_freq')::numeric END = 1
                      AND ((x.evidence -> 'consistent_quote') = 'true'::jsonb OR x.confidence >= 0.95::real) THEN 1
                 WHEN x.confidence >= 0.40::real AND x.confidence < 0.80::real THEN 2
                 ELSE 3
               END AS sinif_sira,
               x.confidence AS confidence
        FROM icerik.xref x
        """;

    /// <summary>Baglanti satirinin sinif sirasi ve guveni (ham SQL projeksiyonu).</summary>
    private sealed class ClassRow
    {
        public required string XrefKey { get; init; }

        public int SinifSira { get; init; }

        public float Confidence { get; init; }
    }

    /// <summary>Turkce lemma onay yolu (ham SQL projeksiyonu; yalniz lang = 'tr').</summary>
    private sealed class PathRow
    {
        public required string LemmaKey { get; init; }

        public string? OnayYolu { get; init; }
    }

    private static IQueryable<ClassRow> ClassRows(IcerikDbContext db) => db.Database.SqlQueryRaw<ClassRow>(ClassSql);

    private static IQueryable<PathRow> PathRows(IcerikDbContext db) =>
        db.Database.SqlQueryRaw<PathRow>("SELECT id::text AS lemma_key, onay_yolu FROM icerik.lemma WHERE lang = 'tr'");

    /// <summary>Liste ve ayrintiya eklenen turetilmis alanlar (hedefe gore: sinif, dalga, onay yolu).</summary>
    private sealed record Enrichment(string? Sinif, int? Dalga, string? OnayYolu);

    /// <summary>Listede gereken alanlar; jsonb degerler (onceki, onerilen, duzenlenen) listede de doner (Backend API §4, BÇ-55).</summary>
    private sealed record Row(
        long Id,
        string HedefTablo,
        string HedefAnahtar,
        Guid? XrefId,
        string Alan,
        string Eylem,
        ReviewStatus Durum,
        XrefOrigin Koken,
        string? YzModeli,
        string? YzKaydi,
        string? Onceki,
        string? Onerilen,
        string? Duzenlenen,
        float? Guven,
        string Oneren,
        string? Inceleyen,
        string? IkinciInceleyen,
        DateTime? IkinciIncelendiAt,
        DateTime CreatedAt,
        DateTime? IncelendiAt,
        uint Xmin);

    public static async Task<ReviewListResponse> ListAsync(
        IcerikDbContext db,
        string? hedefTablo,
        string? alan,
        ReviewStatus durum,
        string? kaynak,
        ReviewStage? asama,
        ReviewSort sira,
        LinkCandidateClass? sinif,
        ApprovalFilter? onayYolu,
        (DateTime CreatedAt, long Id)? after,
        WaveCursor? waveAfter,
        ClassCursor? classAfter,
        int limit,
        CancellationToken cancellationToken)
    {
        IQueryable<Review> query = db.Reviews.AsNoTracking().Where(r => r.Durum == durum);
        if (hedefTablo is not null)
        {
            query = query.Where(r => r.HedefTablo == hedefTablo);
        }

        if (alan is not null)
        {
            query = query.Where(r => r.Alan == alan);
        }

        if (kaynak is not null)
        {
            // Kaynak sutunu yalniz birim hedeflerinde anlamlidir: hedef_anahtar birimin capasidir (unit.source_id uzerinden).
            // Capa sutunu AnchorRef donusturuculu oldugu icin esleme ham SQL alt sorgusuyla (yalniz sutun, tek parametre) yapilir.
            IQueryable<string> sourceAnchors = db.Database.SqlQuery<string>(
                $"SELECT anchor AS \"Value\" FROM icerik.unit WHERE source_id = {kaynak}");
            query = query.Where(r => r.HedefTablo == ReviewTargets.Unit && sourceAnchors.Contains(r.HedefAnahtar));
        }

        if (asama is ReviewStage.Ilk)
        {
            query = query.Where(r => r.Durum == ReviewStatus.Acik && (r.Inceleyen == null || r.Inceleyen == string.Empty));
        }
        else if (asama is ReviewStage.Ikinci)
        {
            query = query.Where(r => r.Durum == ReviewStatus.Acik
                && r.Inceleyen != null && r.Inceleyen != string.Empty
                && (r.IkinciInceleyen == null || r.IkinciInceleyen == string.Empty));
        }

        if (sinif is { } wantedClass)
        {
            // Sinif yalniz baglanti satirlarinda vardir; baglantisi okunamayan kayit hicbir sinifa girmez.
            int wantedRank = (int)wantedClass;
            IQueryable<ClassRow> classes = ClassRows(db);
            query = query.Where(r => r.HedefTablo == ReviewTargets.Xref && classes.Any(c => c.XrefKey == r.HedefAnahtar && c.SinifSira == wantedRank));
        }

        if (onayYolu is { } wantedPath)
        {
            IQueryable<PathRow> paths = PathRows(db);
            query = wantedPath switch
            {
                ApprovalFilter.Otomatik => query.Where(r => r.HedefTablo == ReviewTargets.Lemma
                    && paths.Any(p => p.LemmaKey == r.HedefAnahtar && p.OnayYolu == LemmaApprovalPaths.Otomatik)),
                ApprovalFilter.Editor => query.Where(r => r.HedefTablo == ReviewTargets.Lemma
                    && paths.Any(p => p.LemmaKey == r.HedefAnahtar && p.OnayYolu == LemmaApprovalPaths.Editor)),
                _ => query.Where(r => r.HedefTablo == ReviewTargets.Lemma
                    && paths.Any(p => p.LemmaKey == r.HedefAnahtar && p.OnayYolu == null)),
            };
        }

        List<Row> rows;
        string? next = null;
        if (sira == ReviewSort.Dalga)
        {
            (rows, next) = await ListByWaveAsync(db, query, waveAfter, limit, cancellationToken);
        }
        else if (sira == ReviewSort.Sinif)
        {
            (rows, next) = await ListByClassAsync(db, query, classAfter, limit, cancellationToken);
        }
        else
        {
            if (after is { } cursor)
            {
                DateTime at = cursor.CreatedAt;
                long id = cursor.Id;
                query = query.Where(r => r.CreatedAt > at || (r.CreatedAt == at && r.Id > id));
            }

            rows = await ProjectRows(query
                .OrderBy(r => r.CreatedAt)
                .ThenBy(r => r.Id)
                .Take(limit + 1))
                .ToListAsync(cancellationToken);

            if (rows.Count > limit)
            {
                rows.RemoveAt(rows.Count - 1);
                Row last = rows[^1];
                next = ReviewCursor.Encode(last.CreatedAt, last.Id);
            }
        }

        Dictionary<string, UnitKind> kinds = await UnitKindsForPendingAsync(db, rows, cancellationToken);
        HashSet<long> verifiedTargets = await VerifiedTargetsOfApprovedAiRowsAsync(db, rows, cancellationToken);
        Dictionary<long, Enrichment> enrichment = await EnrichAsync(db, [.. rows.Select(r => (r.Id, r.HedefTablo, r.HedefAnahtar))], cancellationToken);
        List<ReviewItemDto> items = [.. rows.Select(r => ToItem(r, kinds, verifiedTargets.Contains(r.Id), enrichment.GetValueOrDefault(r.Id)))];
        return new ReviewListResponse(items, next);
    }

    /// <summary>
    /// Sinif sirasi (A18.4): (sinif sirasi, confidence azalan, review.id) artan; baglantisi okunamayan kayitlar en sonda
    /// (sinif <see cref="NoClass"/>, guven -1). Anahtarlar once sayfalanir, sonra satirlar tek sorguyla okunup bu sirada dizilir.
    /// </summary>
    private static async Task<(List<Row> Rows, string? Next)> ListByClassAsync(
        IcerikDbContext db,
        IQueryable<Review> query,
        ClassCursor? after,
        int limit,
        CancellationToken cancellationToken)
    {
        IQueryable<ClassRow> classes = ClassRows(db);
        var keyed =
            from r in query
            join c in classes on r.HedefAnahtar equals c.XrefKey into joined
            from c in joined.DefaultIfEmpty()
            select new
            {
                r.Id,
                Rank = (int?)c.SinifSira ?? NoClass,
                Conf = (float?)c.Confidence ?? -1f,
            };

        if (after is { } cursor)
        {
            int cr = cursor.Sinif;
            float cc = cursor.Confidence;
            long ci = cursor.Id;
            keyed = keyed.Where(k => k.Rank > cr
                || (k.Rank == cr && (k.Conf < cc || (k.Conf == cc && k.Id > ci))));
        }

        var page = await keyed
            .OrderBy(k => k.Rank)
            .ThenByDescending(k => k.Conf)
            .ThenBy(k => k.Id)
            .Take(limit + 1)
            .ToListAsync(cancellationToken);

        string? next = null;
        if (page.Count > limit)
        {
            page.RemoveAt(page.Count - 1);
            var last = page[^1];
            next = ReviewCursor.EncodeClass(new ClassCursor(last.Rank, last.Conf, last.Id));
        }

        long[] ids = [.. page.Select(p => p.Id)];
        Dictionary<long, Row> byId = (await ProjectRows(db.Reviews.AsNoTracking().Where(r => ids.Contains(r.Id)))
            .ToListAsync(cancellationToken))
            .ToDictionary(r => r.Id);
        return ([.. ids.Where(byId.ContainsKey).Select(i => byId[i])], next);
    }

    /// <summary>
    /// Satirlara hedefe gore turetilmis alanlar: baglantida sinif (kanittan, <see cref="LinkCandidateClassifier"/>), lemma ve lemma_gloss'ta dalga,
    /// lemmada Turkce onay yolu. Her tablo icin tek sorgu (N+1 yok); bozuk anahtar ya da bulunamayan satir alan yazmaz.
    /// </summary>
    private static async Task<Dictionary<long, Enrichment>> EnrichAsync(
        IcerikDbContext db,
        IReadOnlyCollection<(long Id, string Tablo, string Anahtar)> rows,
        CancellationToken cancellationToken)
    {
        Dictionary<long, Enrichment> result = [];

        Dictionary<long, Guid> xrefKeys = [];
        Dictionary<long, int> lemmaKeys = [];
        Dictionary<long, int> glossKeys = [];
        foreach ((long id, string tablo, string anahtar) in rows)
        {
            if (string.Equals(tablo, ReviewTargets.Xref, StringComparison.Ordinal) && Guid.TryParseExact(anahtar, "D", out Guid guid))
            {
                xrefKeys[id] = guid;
            }
            else if (string.Equals(tablo, ReviewTargets.Lemma, StringComparison.Ordinal) && TryLemmaId(anahtar, out int lemmaId))
            {
                lemmaKeys[id] = lemmaId;
            }
            else if (string.Equals(tablo, ReviewTargets.LemmaGloss, StringComparison.Ordinal) && TryLemmaId(anahtar, out int glossId))
            {
                glossKeys[id] = glossId;
            }
        }

        if (xrefKeys.Count > 0)
        {
            Guid[] ids = [.. xrefKeys.Values.Distinct()];
            var found = await db.Xrefs.AsNoTracking()
                .Where(x => ids.Contains(x.Id))
                .Select(x => new { x.Id, x.Type, x.Confidence, x.Evidence })
                .ToListAsync(cancellationToken);
            Dictionary<Guid, string> classes = found.ToDictionary(
                f => f.Id,
                f => LinkCandidateClassifier.Classify(f.Type, f.Confidence, f.Evidence).ToLabel());
            foreach ((long reviewId, Guid xrefId) in xrefKeys)
            {
                if (classes.TryGetValue(xrefId, out string? label))
                {
                    result[reviewId] = new Enrichment(label, null, null);
                }
            }
        }

        if (lemmaKeys.Count > 0 || glossKeys.Count > 0)
        {
            int[] lemmaIds = [.. lemmaKeys.Values.Concat(glossKeys.Values).Distinct()];
            Dictionary<int, int> waves = (await db.LemmaDalgas.AsNoTracking()
                .Where(d => lemmaIds.Contains(d.LemmaId))
                .Select(d => new { d.LemmaId, d.Dalga })
                .ToListAsync(cancellationToken))
                .ToDictionary(d => d.LemmaId, d => (int)d.Dalga);

            int[] pathIds = [.. lemmaKeys.Values.Distinct()];
            Dictionary<int, string?> paths = (await db.Lemmas.AsNoTracking()
                .Where(l => pathIds.Contains(l.Id) && l.Lang == LemmaLangs.Turkish)
                .Select(l => new { l.Id, l.OnayYolu })
                .ToListAsync(cancellationToken))
                .ToDictionary(l => l.Id, l => l.OnayYolu);

            foreach ((long reviewId, int lemmaId) in lemmaKeys)
            {
                result[reviewId] = new Enrichment(
                    null,
                    waves.TryGetValue(lemmaId, out int wave) ? wave : null,
                    paths.GetValueOrDefault(lemmaId));
            }

            foreach ((long reviewId, int lemmaId) in glossKeys)
            {
                result[reviewId] = new Enrichment(null, waves.TryGetValue(lemmaId, out int wave) ? wave : null, null);
            }
        }

        return result;
    }

    private static bool TryLemmaId(string key, out int id) =>
        int.TryParse(key, NumberStyles.None, CultureInfo.InvariantCulture, out id)
        && id >= 1
        && string.Equals(id.ToString(CultureInfo.InvariantCulture), key, StringComparison.Ordinal);

    /// <summary>lemma_dalga satiri ve metin birlesim anahtari (ham SQL projeksiyonu).</summary>
    private sealed class WaveRow
    {
        public required string LemmaKey { get; init; }

        public int LemmaId { get; init; }

        public int Dalga { get; init; }

        public int Sira { get; init; }
    }

    private static IQueryable<Row> ProjectRows(IQueryable<Review> query) =>
        query.Select(r => new Row(
            r.Id,
            r.HedefTablo,
            r.HedefAnahtar,
            r.XrefId,
            r.Alan,
            r.Eylem,
            r.Durum,
            r.Koken,
            r.YzModeli,
            r.YzKaydi,
            r.Onceki,
            r.Onerilen,
            r.Duzenlenen,
            r.Guven,
            r.Oneren,
            r.Inceleyen,
            r.IkinciInceleyen,
            r.IkinciIncelendiAt,
            r.CreatedAt,
            r.IncelendiAt,
            EF.Property<uint>(r, RowVersion.Name)));

    /// <summary>
    /// Dalga sirasi (K-50 madde 7): (dalga, lemma_dalga.sira, lemma_id, review.id) artan; lemma_dalga satiri olmayanlar en sonda
    /// (dalga <see cref="NoWave"/>, sira en buyuk, lemma 0, kendi aralarinda review.id). Birlesim metin karsilastirmasidir
    /// (<c>lemma_dalga.lemma_id::text = review.hedef_anahtar</c>): hedef_anahtar'i tamsayiya cevirmek bozuk anahtarda listeyi 500 yapardi.
    /// Anahtarlar once (kimlik, sira anahtari) ile sayfalanir, sonra satirlar tek sorguyla okunup bu sirada dizilir.
    /// </summary>
    private static async Task<(List<Row> Rows, string? Next)> ListByWaveAsync(
        IcerikDbContext db,
        IQueryable<Review> query,
        WaveCursor? after,
        int limit,
        CancellationToken cancellationToken)
    {
        // Birlesim anahtari metin olarak SQL'de uretilir (lemma_id::text); LINQ'te int.ToString() kultur uyarisi (CA1305) verir.
        IQueryable<WaveRow> waves = db.Database.SqlQuery<WaveRow>(
            $"SELECT lemma_id::text AS lemma_key, lemma_id, dalga::integer AS dalga, sira FROM icerik.lemma_dalga");
        var keyed =
            from r in query
            join d in waves on r.HedefAnahtar equals d.LemmaKey into joined
            from d in joined.DefaultIfEmpty()
            select new
            {
                r.Id,
                Dalga = (int?)d.Dalga ?? NoWave,
                Sira = (int?)d.Sira ?? int.MaxValue,
                Lemma = (int?)d.LemmaId ?? 0,
            };

        if (after is { } cursor)
        {
            int cd = cursor.Dalga;
            int cs = cursor.Sira;
            int cl = cursor.LemmaId;
            long ci = cursor.Id;
            keyed = keyed.Where(k => k.Dalga > cd
                || (k.Dalga == cd && (k.Sira > cs
                    || (k.Sira == cs && (k.Lemma > cl
                        || (k.Lemma == cl && k.Id > ci))))));
        }

        var page = await keyed
            .OrderBy(k => k.Dalga)
            .ThenBy(k => k.Sira)
            .ThenBy(k => k.Lemma)
            .ThenBy(k => k.Id)
            .Take(limit + 1)
            .ToListAsync(cancellationToken);

        string? next = null;
        if (page.Count > limit)
        {
            page.RemoveAt(page.Count - 1);
            var last = page[^1];
            next = ReviewCursor.EncodeWave(new WaveCursor(last.Dalga, last.Sira, last.Lemma, last.Id));
        }

        long[] ids = [.. page.Select(p => p.Id)];
        Dictionary<long, Row> byId = (await ProjectRows(db.Reviews.AsNoTracking().Where(r => ids.Contains(r.Id)))
            .ToListAsync(cancellationToken))
            .ToDictionary(r => r.Id);
        return ([.. ids.Where(byId.ContainsKey).Select(i => byId[i])], next);
    }

    public static async Task<ReviewStatsResponse> StatsAsync(IcerikDbContext db, CancellationToken cancellationToken)
    {
        var groups = await db.Reviews.AsNoTracking()
            .Where(r => r.Durum == ReviewStatus.Acik)
            .GroupBy(r => new { r.HedefTablo, r.Alan })
            .Select(g => new { g.Key.HedefTablo, g.Key.Alan, Acik = g.Count() })
            .ToListAsync(cancellationToken);

        List<ReviewQueueCount> queues = [.. groups
            .OrderBy(g => g.HedefTablo, StringComparer.Ordinal)
            .ThenBy(g => g.Alan, StringComparer.Ordinal)
            .Select(g => new ReviewQueueCount(g.HedefTablo, g.Alan, g.Acik))];

        // Acik baglanti adaylarinin sinif sayilari (sabit sira, sifirlar dahil); baglantisi okunamayan kayit hicbir sinifa girmez.
        IQueryable<ClassRow> classRows = ClassRows(db);
        var classGroups = await (
            from r in db.Reviews.AsNoTracking()
            where r.Durum == ReviewStatus.Acik && r.HedefTablo == ReviewTargets.Xref
            join c in classRows on r.HedefAnahtar equals c.XrefKey
            group c by c.SinifSira into g
            select new { Rank = g.Key, N = g.Count() })
            .ToListAsync(cancellationToken);
        List<ReviewClassCount> classes =
        [
            .. new[] { LinkCandidateClass.Tutarsiz, LinkCandidateClass.Toplu, LinkCandidateClass.Gri, LinkCandidateClass.Diger }
                .Select(c => new ReviewClassCount(c.ToLabel(), classGroups.FirstOrDefault(g => g.Rank == (int)c)?.N ?? 0)),
        ];

        int expert = await db.Reviews.AsNoTracking().CountAsync(r => r.Durum == ReviewStatus.Uzmanda, cancellationToken);
        return new ReviewStatsResponse(queues, queues.Sum(q => q.Acik), classes, expert);
    }

    /// <summary>Kayit yoksa null. Ayrinti: liste alanlari, jsonb degerler, hedef anlik gorunumu ve turetilmis dogrulanmis.</summary>
    public static async Task<(ReviewDetailDto? Detail, uint Xmin)> GetAsync(IcerikDbContext db, long id, CancellationToken cancellationToken)
    {
        var row = await db.Reviews.AsNoTracking()
            .Where(r => r.Id == id)
            .Select(r => new { Review = r, Xmin = EF.Property<uint>(r, RowVersion.Name) })
            .SingleOrDefaultAsync(cancellationToken);
        if (row is null)
        {
            return (null, 0);
        }

        Review r = row.Review;
        TargetView view = await LoadTargetViewAsync(db, r, cancellationToken);
        bool verified = ReviewVerification.IsVerified(r.HedefTablo, view.Status, view.MetinDurumu, r.Durum);
        bool pending = view.Kind is { } kind && ReviewVerification.IsSecondApprovalPending(r, kind);
        Enrichment? extra = (await EnrichAsync(db, [(r.Id, r.HedefTablo, r.HedefAnahtar)], cancellationToken)).GetValueOrDefault(r.Id);

        ReviewDetailDto detail = new()
        {
            Id = r.Id,
            HedefTablo = r.HedefTablo,
            HedefAnahtar = r.HedefAnahtar,
            XrefId = r.XrefId,
            Alan = r.Alan,
            Eylem = r.Eylem,
            Durum = r.Durum.ToLabel(),
            Koken = r.Koken.ToLabel(),
            YzModeli = r.YzModeli,
            YzKaydi = ReviewJson.Parse(r.YzKaydi),
            Guven = r.Guven,
            Oneren = r.Oneren,
            Inceleyen = r.Inceleyen,
            IkinciInceleyen = r.IkinciInceleyen,
            IkinciIncelendiAt = r.IkinciIncelendiAt,
            CreatedAt = r.CreatedAt,
            IncelendiAt = r.IncelendiAt,
            Xmin = row.Xmin,
            Dogrulanmamis = ReviewVerification.IsUnverified(r.YzModeli, r.Durum, verified),
            IkinciOnayBekliyor = pending,
            Onceki = ReviewJson.Parse(r.Onceki),
            Onerilen = ReviewJson.Parse(r.Onerilen),
            Duzenlenen = ReviewJson.Parse(r.Duzenlenen),
            Gerekce = r.Gerekce,
            IkinciGerekce = r.IkinciGerekce,
            SureMs = r.SureMs,
            Hedef = view.Snapshot,
            Dogrulanmis = verified,
            Sinif = extra?.Sinif,
            Dalga = extra?.Dalga,
            OnayYolu = extra?.OnayYolu,
        };
        return (detail, row.Xmin);
    }

    private static ReviewItemDto ToItem(Row r, Dictionary<string, UnitKind> kinds, bool targetVerified, Enrichment? extra)
    {
        bool pending = false;
        if (kinds.TryGetValue(r.HedefAnahtar, out UnitKind kind))
        {
            Review shell = new()
            {
                HedefTablo = r.HedefTablo,
                HedefAnahtar = r.HedefAnahtar,
                Alan = r.Alan,
                Eylem = r.Eylem,
                Koken = r.Koken,
                Oneren = r.Oneren,
                Durum = r.Durum,
                Inceleyen = r.Inceleyen,
                IkinciInceleyen = r.IkinciInceleyen,
            };
            pending = ReviewVerification.IsSecondApprovalPending(shell, kind);
        }

        return new ReviewItemDto
        {
            Id = r.Id,
            HedefTablo = r.HedefTablo,
            HedefAnahtar = r.HedefAnahtar,
            XrefId = r.XrefId,
            Alan = r.Alan,
            Eylem = r.Eylem,
            Durum = r.Durum.ToLabel(),
            Koken = r.Koken.ToLabel(),
            YzModeli = r.YzModeli,
            YzKaydi = ReviewJson.Parse(r.YzKaydi),
            Onceki = ReviewJson.Parse(r.Onceki),
            Onerilen = ReviewJson.Parse(r.Onerilen),
            Duzenlenen = ReviewJson.Parse(r.Duzenlenen),
            Guven = r.Guven,
            Oneren = r.Oneren,
            Inceleyen = r.Inceleyen,
            IkinciInceleyen = r.IkinciInceleyen,
            IkinciIncelendiAt = r.IkinciIncelendiAt,
            CreatedAt = r.CreatedAt,
            IncelendiAt = r.IncelendiAt,
            Xmin = r.Xmin,

            // Ayrintiyla ayni tek kural (ReviewVerification.IsUnverified); hedef onayi yalniz onayli yapay zeka satirlari icin okunur.
            Dogrulanmamis = ReviewVerification.IsUnverified(r.YzModeli, r.Durum, targetVerified),
            IkinciOnayBekliyor = pending,
            Sinif = extra?.Sinif,
            Dalga = extra?.Dalga,
            OnayYolu = extra?.OnayYolu,
        };
    }

    /// <summary>
    /// Ikinci onay bekleme adayi satirlar (unit + metin, ilk onay var, ikinci yok, acik) icin birim turlerini tek sorguyla okur.
    /// Anahtar hedef_anahtar dizgisidir.
    /// </summary>
    private static async Task<Dictionary<string, UnitKind>> UnitKindsForPendingAsync(IcerikDbContext db, List<Row> rows, CancellationToken cancellationToken)
    {
        Dictionary<string, AnchorRef> anchors = new(StringComparer.Ordinal);
        foreach (Row r in rows)
        {
            if (string.Equals(r.HedefTablo, ReviewTargets.Unit, StringComparison.Ordinal)
                && string.Equals(r.Alan, ReviewFields.Metin, StringComparison.Ordinal)
                && r.Durum == ReviewStatus.Acik
                && !string.IsNullOrEmpty(r.Inceleyen)
                && string.IsNullOrEmpty(r.IkinciInceleyen)
                && AnchorRef.TryParse(r.HedefAnahtar, out AnchorRef? anchor))
            {
                anchors[r.HedefAnahtar] = anchor;
            }
        }

        Dictionary<string, UnitKind> result = new(StringComparer.Ordinal);
        if (anchors.Count == 0)
        {
            return result;
        }

        List<AnchorRef> wanted = [.. anchors.Values];
        var found = await db.Units.AsNoTracking()
            .Where(u => wanted.Contains(u.Anchor))
            .Select(u => new { u.Anchor, u.Kind })
            .ToListAsync(cancellationToken);

        Dictionary<string, UnitKind> byAnchor = found.ToDictionary(f => f.Anchor.ToString(), f => f.Kind, StringComparer.Ordinal);
        foreach ((string key, AnchorRef anchor) in anchors)
        {
            if (byAnchor.TryGetValue(anchor.ToString(), out UnitKind kind))
            {
                result[key] = kind;
            }
        }

        return result;
    }

    /// <summary>
    /// <c>dogrulanmamis</c> kurali hedef onayina yalniz <c>yz_modeli</c> dolu ve review'u <c>onaylandi</c> olan satirlarda bakar
    /// (aksi hâlde sonuc hedefe bagli degildir). Bu satirlarin hedef durumlari hedef tablosu basina tek sorguyla okunur (N+1 yok).
    /// Donen kume, hedefi <see cref="ReviewVerification.IsVerified"/> ile onayli olan review kimliklerini icerir.
    /// </summary>
    private static async Task<HashSet<long>> VerifiedTargetsOfApprovedAiRowsAsync(IcerikDbContext db, List<Row> rows, CancellationToken cancellationToken)
    {
        HashSet<long> verified = [];
        List<(Row Row, ReviewTarget Target)> targets = [];
        foreach (Row r in rows)
        {
            if (r.YzModeli is null || r.Durum != ReviewStatus.Onaylandi || !ReviewTargets.IsKnown(r.HedefTablo))
            {
                continue;
            }

            if (!ReviewTargets.HasStatusColumn(r.HedefTablo))
            {
                if (ReviewVerification.IsVerified(r.HedefTablo, null, null, r.Durum))
                {
                    verified.Add(r.Id);
                }

                continue;
            }

            try
            {
                targets.Add((r, ReviewTargets.Parse(r.HedefTablo, r.HedefAnahtar)));
            }
            catch (DomainException)
            {
                // Bozuk anahtar: hedef okunamaz, onayli sayilmaz (ayrintida da anlik gorunum yoktur).
            }
        }

        foreach (IGrouping<string, (Row Row, ReviewTarget Target)> group in targets.GroupBy(t => t.Target.Table, StringComparer.Ordinal))
        {
            switch (group.Key)
            {
                case ReviewTargets.Unit:
                    {
                        List<AnchorRef> wanted = [.. group.Select(t => t.Target.Anchor!)];
                        var found = await db.Units.AsNoTracking()
                            .Where(u => wanted.Contains(u.Anchor))
                            .Select(u => new { u.Anchor, u.MetinDurumu })
                            .ToListAsync(cancellationToken);
                        Dictionary<string, TextStatus> byAnchor = found.ToDictionary(f => f.Anchor.ToString(), f => f.MetinDurumu, StringComparer.Ordinal);
                        foreach ((Row row, ReviewTarget target) in group)
                        {
                            if (byAnchor.TryGetValue(target.Anchor!.ToString(), out TextStatus status)
                                && ReviewVerification.IsVerified(group.Key, null, status, row.Durum))
                            {
                                verified.Add(row.Id);
                            }
                        }

                        break;
                    }

                case ReviewTargets.SurahAlias:
                    {
                        List<short> numbers = [.. group.Select(t => (short)t.Target.SurahNo!.Value)];
                        var found = await db.SurahAliases.AsNoTracking()
                            .Where(s => numbers.Contains(s.SurahNo))
                            .Select(s => new { s.SurahNo, s.Alias, s.Status })
                            .ToListAsync(cancellationToken);
                        MarkVerified(
                            verified,
                            group,
                            found.ToDictionary(f => Key(f.SurahNo) + ":" + f.Alias, f => f.Status, StringComparer.Ordinal),
                            t => Key(t.Target.SurahNo!.Value) + ":" + t.Target.Alias);
                        break;
                    }

                case ReviewTargets.Xref:
                    {
                        List<Guid> ids = [.. group.Select(t => t.Target.Id!.Value)];
                        var found = await db.Xrefs.AsNoTracking()
                            .Where(x => ids.Contains(x.Id))
                            .Select(x => new { x.Id, x.Status })
                            .ToListAsync(cancellationToken);
                        MarkVerified(verified, group, found.ToDictionary(f => Key(f.Id), f => f.Status, StringComparer.Ordinal), t => Key(t.Target.Id!.Value));
                        break;
                    }

                case ReviewTargets.QuranWordFix:
                    {
                        List<Guid> ids = [.. group.Select(t => t.Target.Id!.Value)];
                        var found = await db.QuranWordFixes.AsNoTracking()
                            .Where(x => ids.Contains(x.Id))
                            .Select(x => new { x.Id, x.Status })
                            .ToListAsync(cancellationToken);
                        MarkVerified(verified, group, found.ToDictionary(f => Key(f.Id), f => f.Status, StringComparer.Ordinal), t => Key(t.Target.Id!.Value));
                        break;
                    }

                case ReviewTargets.Lemma:
                    {
                        List<int> ids = [.. group.Select(t => t.Target.LemmaId!.Value)];
                        var found = await db.Lemmas.AsNoTracking()
                            .Where(x => ids.Contains(x.Id))
                            .Select(x => new { x.Id, x.Status })
                            .ToListAsync(cancellationToken);
                        MarkVerified(verified, group, found.ToDictionary(f => Key(f.Id), f => f.Status, StringComparer.Ordinal), t => Key(t.Target.LemmaId!.Value));
                        break;
                    }

                case ReviewTargets.LemmaGloss:
                    {
                        List<int> ids = [.. group.Select(t => t.Target.LemmaId!.Value)];
                        var found = await db.LemmaGlosses.AsNoTracking()
                            .Where(x => ids.Contains(x.LemmaId))
                            .Select(x => new { x.LemmaId, x.Status })
                            .ToListAsync(cancellationToken);
                        MarkVerified(verified, group, found.ToDictionary(f => Key(f.LemmaId), f => f.Status, StringComparer.Ordinal), t => Key(t.Target.LemmaId!.Value));
                        break;
                    }
            }
        }

        return verified;
    }

    private static string Key(int value) => value.ToString(CultureInfo.InvariantCulture);

    private static string Key(short value) => value.ToString(CultureInfo.InvariantCulture);

    private static string Key(Guid value) => value.ToString("D", CultureInfo.InvariantCulture);

    private static void MarkVerified(
        HashSet<long> verified,
        IGrouping<string, (Row Row, ReviewTarget Target)> group,
        Dictionary<string, XrefStatus> statuses,
        Func<(Row Row, ReviewTarget Target), string> keyOf)
    {
        foreach ((Row Row, ReviewTarget Target) item in group)
        {
            if (statuses.TryGetValue(keyOf(item), out XrefStatus status)
                && ReviewVerification.IsVerified(group.Key, status, null, item.Row.Durum))
            {
                verified.Add(item.Row.Id);
            }
        }
    }

    /// <summary>Yari acik aralik <c>[bas, son]</c> iki sayi; aralik yoksa (birimin tamami) null.</summary>
    private static int[]? ToPair(AnchorSpan? span) => span is { } s ? [s.Start, s.End] : null;

    private sealed record TargetView(ReviewTargetSnapshot? Snapshot, XrefStatus? Status, TextStatus? MetinDurumu, UnitKind? Kind)
    {
        public static readonly TargetView Empty = new(null, null, null, null);
    }

    private static async Task<TargetView> LoadTargetViewAsync(IcerikDbContext db, Review review, CancellationToken cancellationToken)
    {
        ReviewTarget target;
        try
        {
            target = ReviewTargets.Parse(review.HedefTablo, review.HedefAnahtar);
        }
        catch (DomainException)
        {
            // Desteklenmeyen hedef ya da bozuk anahtar: anlik gorunum yok.
            return TargetView.Empty;
        }

        switch (target.Table)
        {
            case ReviewTargets.Unit:
                {
                    var unit = await db.Units.AsNoTracking()
                        .Where(u => u.Anchor == target.Anchor)
                        .Select(u => new { u.Anchor, u.Kind, u.SourceId, u.Metin, u.ContentHash, u.MetinDurumu, u.Status, u.Rev })
                        .SingleOrDefaultAsync(cancellationToken);
                    return unit is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                Anchor = unit.Anchor.ToString(),
                                Kind = unit.Kind.ToLabel(),
                                Source = unit.SourceId,
                                Metin = unit.Metin,
                                ContentHash = unit.ContentHash,
                                MetinDurumu = unit.MetinDurumu.ToLabel(),
                                Status = unit.Status.ToLabel(),
                                Rev = unit.Rev,
                            },
                            null,
                            unit.MetinDurumu,
                            unit.Kind);
                }

            case ReviewTargets.SurahAlias:
                {
                    short surahNo = (short)target.SurahNo!.Value;
                    string alias = target.Alias!;
                    SurahAlias? row = await db.SurahAliases.AsNoTracking()
                        .SingleOrDefaultAsync(s => s.SurahNo == surahNo && s.Alias == alias, cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                SurahNo = row.SurahNo,
                                Alias = row.Alias,
                                Kind = row.Kind,
                                Risky = row.Risky,
                                Status = row.Status.ToLabel(),
                            },
                            row.Status,
                            null,
                            null);
                }

            case ReviewTargets.Xref:
                {
                    Guid id = target.Id!.Value;
                    var row = await db.Xrefs.AsNoTracking()
                        .Where(x => x.Id == id)
                        .Select(x => new { x.Id, x.SrcAnchor, x.SrcSpan, x.DstAnchor, x.DstSpan, x.Type, x.Score, x.Confidence, x.Origin, x.Evidence, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    if (row is null)
                    {
                        return TargetView.Empty;
                    }

                    // Vurgulu dizi: kaynak birimin metni ve ozeti ayri okunur. Kur'an kaynakta aralik kelime konumudur (kod noktasi degil):
                    // dilimlenmez. Metin yoksa, aralik metin disindaysa ya da kanittaki src_hash birimin ozetiyle uyusmuyorsa uc alan null.
                    HighlightedSequence highlight = HighlightedSequence.None;
                    if (row.SrcAnchor.Kind != AnchorKind.Q)
                    {
                        AnchorRef srcAnchor = row.SrcAnchor;
                        var src = await db.Units.AsNoTracking()
                            .Where(u => u.Anchor == srcAnchor)
                            .Select(u => new { u.Metin, u.ContentHash })
                            .SingleOrDefaultAsync(cancellationToken);
                        if (src is not null)
                        {
                            highlight = LinkHighlight.Compute(src.Metin, src.ContentHash, LinkEvidenceReader.ReadString(row.Evidence, "src_hash"), row.SrcSpan);
                        }
                    }

                    return new TargetView(
                        new ReviewTargetSnapshot
                        {
                            Tablo = target.Table,
                            Id = row.Id,
                            SrcAnchor = row.SrcAnchor.ToString(),
                            DstAnchor = row.DstAnchor.ToString(),
                            Type = row.Type.ToLabel(),
                            SrcSpan = ToPair(row.SrcSpan),
                            DstSpan = ToPair(row.DstSpan),
                            Score = row.Score,
                            Confidence = row.Confidence,
                            Origin = row.Origin.ToLabel(),
                            EvidenceOzeti = ReviewJson.Parse(LinkEvidenceSummary.Build(row.Evidence)),
                            VurguluDizi = new VurguluDizi(highlight.Sol, highlight.Dizi, highlight.Sag),
                            Sinif = LinkCandidateClassifier.Classify(row.Type, row.Confidence, row.Evidence).ToLabel(),
                            Status = row.Status.ToLabel(),
                        },
                        row.Status,
                        null,
                        null);
                }

            case ReviewTargets.QuranWordFix:
                {
                    Guid id = target.Id!.Value;
                    var row = await db.QuranWordFixes.AsNoTracking()
                        .Where(x => x.Id == id)
                        .Select(x => new { x.Id, x.Anchor, x.Field, x.QacValue, x.NewValue, x.Reason, x.Editor, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                Id = row.Id,
                                Anchor = row.Anchor.ToString(),
                                Field = row.Field,
                                QacValue = row.QacValue,
                                NewValue = row.NewValue,
                                Reason = row.Reason,
                                Editor = row.Editor,
                                Status = row.Status.ToLabel(),
                            },
                            row.Status,
                            null,
                            null);
                }

            case ReviewTargets.Lemma:
                {
                    int id = target.LemmaId!.Value;
                    var row = await db.Lemmas.AsNoTracking()
                        .Where(x => x.Id == id)
                        .Select(x => new { x.Id, x.Lang, x.Text, x.RootId, x.Occurrences, x.EtymologicalOnly, x.Origin, x.Status, x.OnayYolu, x.ArLemmaId, x.Freq, x.Kanit })
                        .SingleOrDefaultAsync(cancellationToken);
                    if (row is null)
                    {
                        return TargetView.Empty;
                    }

                    // Turkce lemma (K-51 madde 9): onay yolu, kanit ozeti, kok harfleri, Arapca karsilik, siklik ve ilk uc ornek.
                    TrLemmaExtras? tr = string.Equals(row.Lang, LemmaLangs.Turkish, StringComparison.Ordinal)
                        ? await TrLemmaQueries.ExtrasAsync(db, row.Id, row.RootId, row.ArLemmaId, row.Kanit, cancellationToken)
                        : null;
                    return new TargetView(
                        new ReviewTargetSnapshot
                        {
                            Tablo = target.Table,
                            LemmaId = row.Id,
                            Lang = row.Lang,
                            Text = row.Text,
                            RootId = row.RootId,
                            Occurrences = row.Occurrences,
                            EtymologicalOnly = row.EtymologicalOnly,
                            Origin = row.Origin,
                            Status = row.Status.ToLabel(),
                            OnayYolu = row.OnayYolu,
                            ArLemmaId = row.ArLemmaId,
                            Freq = row.Freq,
                            KanitOzeti = tr?.KanitOzeti,
                            RootLetters = tr?.RootLetters,
                            ArLemmaText = tr?.ArLemmaText,
                            Kwic = tr?.Kwic,
                        },
                        row.Status,
                        null,
                        null);
                }

            case ReviewTargets.LemmaGloss:
                {
                    int id = target.LemmaId!.Value;
                    var row = await db.LemmaGlosses.AsNoTracking()
                        .Where(x => x.LemmaId == id)
                        .Select(x => new { x.LemmaId, x.AnlamKisa, x.Origin, x.KuranAnlamlari, x.TurkceEsKelime, x.YalnizcaEtimolojik, x.Version, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                LemmaId = row.LemmaId,
                                AnlamKisa = row.AnlamKisa,
                                Origin = row.Origin,
                                KuranAnlamlari = ReviewJson.Parse(row.KuranAnlamlari),
                                TurkceEsKelime = row.TurkceEsKelime,
                                YalnizcaEtimolojik = row.YalnizcaEtimolojik,
                                Version = row.Version,
                                Status = row.Status.ToLabel(),
                            },
                            row.Status,
                            null,
                            null);
                }

            default:
                return TargetView.Empty;
        }
    }
}
