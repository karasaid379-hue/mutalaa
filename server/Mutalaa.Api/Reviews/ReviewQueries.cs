using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Domain;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Reviews;

/// <summary>Liste, ayrinti ve istatistik okuma sorgulari: hepsi AsNoTracking ve projeksiyonludur.</summary>
internal static class ReviewQueries
{
    public const int DefaultLimit = 50;
    public const int MaxLimit = 200;

    /// <summary>Listede gereken alanlar; buyuk jsonb sutunlari (onceki, onerilen, duzenlenen) listede okunmaz.</summary>
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
        (DateTime CreatedAt, long Id)? after,
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

        if (after is { } cursor)
        {
            DateTime at = cursor.CreatedAt;
            long id = cursor.Id;
            query = query.Where(r => r.CreatedAt > at || (r.CreatedAt == at && r.Id > id));
        }

        List<Row> rows = await query
            .OrderBy(r => r.CreatedAt)
            .ThenBy(r => r.Id)
            .Take(limit + 1)
            .Select(r => new Row(
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
                r.Guven,
                r.Oneren,
                r.Inceleyen,
                r.IkinciInceleyen,
                r.IkinciIncelendiAt,
                r.CreatedAt,
                r.IncelendiAt,
                EF.Property<uint>(r, RowVersion.Name)))
            .ToListAsync(cancellationToken);

        string? next = null;
        if (rows.Count > limit)
        {
            rows.RemoveAt(rows.Count - 1);
            Row last = rows[^1];
            next = ReviewCursor.Encode(last.CreatedAt, last.Id);
        }

        Dictionary<string, UnitKind> kinds = await UnitKindsForPendingAsync(db, rows, cancellationToken);
        HashSet<long> verifiedTargets = await VerifiedTargetsOfApprovedAiRowsAsync(db, rows, cancellationToken);
        List<ReviewItemDto> items = [.. rows.Select(r => ToItem(r, kinds, verifiedTargets.Contains(r.Id)))];
        return new ReviewListResponse(items, next);
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
        return new ReviewStatsResponse(queues, queues.Sum(q => q.Acik));
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
        };
        return (detail, row.Xmin);
    }

    private static ReviewItemDto ToItem(Row r, Dictionary<string, UnitKind> kinds, bool targetVerified)
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
                        .Select(x => new { x.Id, x.SrcAnchor, x.DstAnchor, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                Id = row.Id,
                                SrcAnchor = row.SrcAnchor.ToString(),
                                DstAnchor = row.DstAnchor.ToString(),
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
                        .Select(x => new { x.Id, x.Anchor, x.Field, x.QacValue, x.NewValue, x.Status })
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
                        .Select(x => new { x.Id, x.Lang, x.Text, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                LemmaId = row.Id,
                                Lang = row.Lang,
                                Text = row.Text,
                                Status = row.Status.ToLabel(),
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
                        .Select(x => new { x.LemmaId, x.AnlamKisa, x.Status })
                        .SingleOrDefaultAsync(cancellationToken);
                    return row is null
                        ? TargetView.Empty
                        : new TargetView(
                            new ReviewTargetSnapshot
                            {
                                Tablo = target.Table,
                                LemmaId = row.LemmaId,
                                AnlamKisa = row.AnlamKisa,
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
