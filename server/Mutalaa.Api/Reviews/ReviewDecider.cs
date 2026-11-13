using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Validation;
using Mutalaa.Domain;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Reviews;

/// <summary>Karar girdisi (tekil ve toplu ortak): karar etiketi cozulmus, duzenlenen deger henuz jsonb'ye cevrilmemis.</summary>
/// <param name="Bulk">Toplu karar ucundan mi (baglanti adayinda toplu onay yalniz "toplu" sinifinda gecer, K-13 politika 1).</param>
internal sealed record DecisionInput(bool Approve, DecisionEdit? Edit, string? Gerekce, bool Bulk = false);

/// <summary>Uygulanmis ama henuz kaydedilmemis karar: izlenen review ve izlenen hedef satiri.</summary>
internal sealed record PreparedDecision(Review Review, object Target);

/// <summary>
/// Karari Domain kuraliyla hesaplar ve izlenen review ile hedef satirina yazar; <c>SaveChanges</c> cagiranindir
/// (tekil karar tek, toplu karar tum kararlar icin tek kayit yapar). Kural Domain'dedir; burada yalniz yukleme ve yazma vardir.
/// </summary>
internal static class ReviewDecider
{
    public const string ApproveLabel = "onaylandi";
    public const string RejectLabel = "reddedildi";

    public static bool TryParseKarar(string? karar, out bool approve)
    {
        approve = false;
        switch (karar)
        {
            case ApproveLabel:
                approve = true;
                return true;
            case RejectLabel:
                return true;
            default:
                return false;
        }
    }

    /// <summary>
    /// Karar metinleri (<c>gerekce</c> ve <c>duzenlenen.metin</c>) PostgreSQL'e yazilabilir mi (NUL ve eslesmemis vekil yok).
    /// Hata alan adi <paramref name="prefix"/> + alan (ornegin <c>kararlar[0].gerekce</c>).
    /// </summary>
    public static void CheckText(IDictionary<string, string[]> errors, string prefix, string? gerekce, DecisionEdit? edit)
    {
        WritableText.Check(errors, prefix + "gerekce", gerekce);
        if (edit is not null)
        {
            WritableText.Check(errors, prefix + "duzenlenen.metin", edit.Metin);
            WritableText.Check(errors, prefix + "duzenlenen.anlam_kisa", edit.AnlamKisa);
            WritableText.Check(errors, prefix + "duzenlenen.dst_anchor", edit.DstAnchor);
            WritableText.Check(errors, prefix + "duzenlenen.type", edit.Type);
            WritableText.Check(errors, prefix + "duzenlenen.new_value", edit.NewValue);
        }
    }

    /// <summary>Zorunlu <c>gerekce</c> (karar disi uclar: itiraz, etimolojik isaret): bos olamaz, en cok 2000 kod noktasi, NUL ve eslesmemis vekil yok.</summary>
    public static void CheckRequiredGerekce(IDictionary<string, string[]> errors, string? gerekce)
    {
        if (string.IsNullOrWhiteSpace(gerekce))
        {
            errors["gerekce"] = ["gerekce boş olamaz."];
        }
        else if (!WritableText.TryCountCodePoints(gerekce, out int length))
        {
            errors["gerekce"] = [WritableText.Message("gerekce")];
        }
        else if (length > ReviewDecisions.MaxGerekceLength)
        {
            errors["gerekce"] = ["gerekce en çok 2000 karakter olabilir."];
        }
    }

    public static async Task<PreparedDecision> ApplyAsync(
        IcerikDbContext db,
        Review review,
        DecisionInput input,
        string actor,
        DateTime now,
        CancellationToken cancellationToken)
    {
        if (!ReviewDecisions.IsSupported(review.HedefTablo, review.Alan))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{review.HedefTablo}' hedefinde '{review.Alan}' alani icin inceleme desteklenmiyor.");
        }

        ReviewTarget target = ReviewTargets.Parse(review.HedefTablo, review.HedefAnahtar);
        string? edited = BuildEdited(input.Edit, review);
        (object entity, ReviewTargetState state) = await LoadTargetAsync(db, target, review, edited, cancellationToken);

        if (input.Bulk && input.Approve && entity is Xref candidate)
        {
            ReviewDecisions.RequireBulkEligible(candidate.Type, candidate.Confidence, candidate.Evidence, input.Edit is not null);
        }

        ReviewDecisionRequest request = new()
        {
            Actor = actor,
            Gerekce = input.Gerekce,
            Duzenlenen = edited,
            Now = now,
        };

        ReviewOutcome outcome = input.Approve
            ? ReviewDecisions.Approve(review, request, state)
            : ReviewDecisions.Reject(review, request, state);

        outcome.ApplyTo(review);
        ApplyToTarget(entity, outcome);
        return new PreparedDecision(review, entity);
    }

    /// <summary>Kararin ardindan hedefin durum etiketi (durum sutunlu hedefte status, birimde metin_durumu).</summary>
    public static string? TargetStateLabel(object target) => target switch
    {
        Unit unit => unit.MetinDurumu.ToLabel(),
        SurahAlias alias => alias.Status.ToLabel(),
        Xref xref => xref.Status.ToLabel(),
        QuranWordFix fix => fix.Status.ToLabel(),
        Lemma lemma => lemma.Status.ToLabel(),
        LemmaGloss gloss => gloss.Status.ToLabel(),
        _ => null,
    };

    /// <summary>Ikinci onay bekliyor mu: yalniz birim hedefinde (tur meal ya da tefsir) anlamlidir.</summary>
    public static bool IsSecondApprovalPending(PreparedDecision prepared) =>
        prepared.Target is Unit unit && ReviewVerification.IsSecondApprovalPending(prepared.Review, unit.Kind);

    /// <summary>
    /// Duzenlenen deger jsonb olur: birim metninde <c>{"metin", "content_hash"}</c> (ozet kanonik metinden hesaplanir),
    /// lemma_gloss'ta <c>{"anlam_kisa"}</c> (kanonik deger; bos, yalniz bosluk ya da 200 karakterden uzun 400).
    /// </summary>
    private static string? BuildEdited(DecisionEdit? edit, Review review)
    {
        if (edit is null)
        {
            return null;
        }

        string hedefTablo = review.HedefTablo;
        bool hasRootFields = edit.RootId is not null || edit.ArLemmaId is not null || edit.EtymologicalOnly is not null;
        bool hasLinkFields = edit.DstAnchor is not null || edit.DstSpan is not null || edit.Type is not null;
        if (ReviewDecisions.IsRootMappingTarget(review.HedefTablo, review.Alan))
        {
            // Kok eslemesi (K-51 madde 9): yalniz root_id, ar_lemma_id (yoksa Arapca karsilik yok) ve etymological_only.
            if (edit.Metin is not null || edit.AnlamKisa is not null)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "Kok eslemesi icin duzenlenen.root_id, ar_lemma_id ve etymological_only verilmeli; metin ve anlam_kisa kabul edilmez.");
            }

            if (edit.RootId is not { } rootId || edit.EtymologicalOnly is not { } etymological)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.root_id ve duzenlenen.etymological_only zorunludur.");
            }

            return LemmaMappingPayload.ToPayload(new RootMappingValue(rootId, edit.ArLemmaId, etymological));
        }

        if (hasRootFields)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.root_id, ar_lemma_id ve etymological_only yalniz lemma + kok_eslemesi incelemesinde verilir.");
        }

        if (ReviewDecisions.IsLinkTarget(review.HedefTablo, review.Alan))
        {
            // Baglanti (A18.4): yalniz dst_anchor, dst_span ve type; en az biri.
            if (edit.Metin is not null || edit.AnlamKisa is not null || edit.NewValue is not null)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "Baglanti icin duzenlenen.dst_anchor, dst_span ve type verilmeli; baska alan kabul edilmez.");
            }

            if (!hasLinkFields)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen en az bir alan icermeli (dst_anchor, dst_span ya da type).");
            }

            XrefType? type = null;
            if (edit.Type is not null)
            {
                if (!XrefTypeLabels.TryParseLabel(edit.Type, out XrefType parsed))
                {
                    throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.type gecerli bir baglanti turu olmali.");
                }

                type = parsed;
            }

            AnchorSpan? span = null;
            if (edit.DstSpan is not null)
            {
                if (edit.DstSpan.Length != 2)
                {
                    throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.dst_span iki tamsayidan olusan [bas, son) dizisi olmali.");
                }

                span = new AnchorSpan(edit.DstSpan[0], edit.DstSpan[1]);
            }

            return LinkEditPayload.ToPayload(new LinkEditValue(edit.DstAnchor, span, type));
        }

        if (hasLinkFields)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.dst_anchor, dst_span ve type yalniz baglanti (xref) incelemesinde verilir.");
        }

        if (string.Equals(hedefTablo, ReviewTargets.QuranWordFix, StringComparison.Ordinal))
        {
            if (edit.Metin is not null || edit.AnlamKisa is not null)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "quran_word_fix icin duzenlenen.new_value verilmeli; metin ve anlam_kisa kabul edilmez.");
            }

            return WordFixPayload.ToPayload(edit.NewValue
                ?? throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.new_value zorunludur."));
        }

        if (edit.NewValue is not null)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.new_value yalniz quran_word_fix incelemesinde verilir.");
        }

        if (string.Equals(hedefTablo, ReviewTargets.LemmaGloss, StringComparison.Ordinal))
        {
            if (edit.Metin is not null)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "lemma_gloss icin duzenlenen.anlam_kisa verilmeli; duzenlenen.metin kabul edilmez.");
            }

            return LemmaGlossText.ToPayload(LemmaGlossText.Normalize(edit.AnlamKisa, "duzenlenen.anlam_kisa"));
        }

        if (string.IsNullOrEmpty(edit.Metin))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.metin bos olamaz.");
        }

        string canonical;
        try
        {
            canonical = TextCanonicalizer.Canonicalize(edit.Metin);
        }
        catch (ArgumentException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.metin gecerli Unicode degil.", e);
        }

        return JsonSerializer.Serialize(new Dictionary<string, string>
        {
            ["metin"] = canonical,
            ["content_hash"] = ContentHash.Compute(canonical),
        });
    }

    /// <summary>
    /// Hedefi yukler. Kok eslemesi (lemma + kok_eslemesi) icin uygulanacak degerin (duzenlenen, yoksa onerilen) dogrulama olgulari da yuklenir:
    /// kok var mi, Arapca karsilik var mi, dili ve koku. Deger okunamiyorsa olgu verilmez ve Domain bozuk degeri 400 ile reddeder.
    /// </summary>
    private static async Task<(object Entity, ReviewTargetState State)> LoadTargetAsync(
        IcerikDbContext db,
        ReviewTarget target,
        Review review,
        string? edited,
        CancellationToken cancellationToken)
    {
        switch (target.Table)
        {
            case ReviewTargets.Unit:
                {
                    Unit unit = await db.Units.SingleOrDefaultAsync(u => u.Anchor == target.Anchor, cancellationToken)
                        ?? throw Missing();
                    SourceKind kind = await db.Sources.AsNoTracking()
                        .Where(s => s.Slug == unit.SourceId)
                        .Select(s => s.Tur)
                        .SingleAsync(cancellationToken);
                    return (unit, ReviewTargetState.ForUnit(new UnitReviewState(
                        unit.Kind,
                        kind,
                        unit.MetinDurumu,
                        unit.Metin,
                        unit.ContentHash,
                        unit.Rev,
                        ReviewDecisions.HasOffsetData(unit.Marks, unit.Sentences?.Length ?? 0),
                        ReviewDecisions.IsMergedFollower(unit.Attrs))));
                }

            case ReviewTargets.SurahAlias:
                {
                    short surahNo = (short)target.SurahNo!.Value;
                    string alias = target.Alias!;
                    SurahAlias row = await db.SurahAliases.SingleOrDefaultAsync(s => s.SurahNo == surahNo && s.Alias == alias, cancellationToken)
                        ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            case ReviewTargets.Xref:
                {
                    Guid id = target.Id!.Value;
                    Xref row = await db.Xrefs.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    LinkRowState link = new(row.Type, row.SrcAnchor, row.SrcSpan, row.DstAnchor, row.DstSpan, row.Origin, row.Evidence);
                    return (row, ReviewTargetState.ForLink(row.Status, link, await LoadLinkFactsAsync(db, link, edited, cancellationToken)));
                }

            case ReviewTargets.QuranWordFix:
                {
                    Guid id = target.Id!.Value;
                    QuranWordFix row = await db.QuranWordFixes.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForFix(row.Status, row.Field, await LoadWordFixFactsAsync(db, row.Field, edited, cancellationToken)));
                }

            case ReviewTargets.Lemma:
                {
                    int id = target.LemmaId!.Value;
                    Lemma row = await db.Lemmas.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    LemmaReviewState lemma = new(row.Lang, row.RootId, row.ArLemmaId, row.EtymologicalOnly, row.Origin, row.OnayYolu);
                    if (ReviewDecisions.IsRootMappingTarget(review.HedefTablo, review.Alan)
                        && LemmaMappingPayload.TryRead(edited ?? review.Onerilen, out RootMappingValue value))
                    {
                        lemma = lemma with { Facts = await LoadFactsAsync(db, value, cancellationToken) };
                    }

                    return (row, ReviewTargetState.ForLemma(row.Status, lemma));
                }

            case ReviewTargets.LemmaGloss:
                {
                    int id = target.LemmaId!.Value;
                    LemmaGloss row = await db.LemmaGlosses.SingleOrDefaultAsync(x => x.LemmaId == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForGloss(row.Status, new GlossReviewState(row.AnlamKisa, row.Version, row.Origin)));
                }

            default:
                throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, $"'{target.Table}' icin inceleme desteklenmiyor.");
        }
    }

    /// <summary>
    /// Duzeltmenin cozdugu hedef ucun olgulari (birim var mi, metin uzunlugu, ayetin kelime sayisi, ozet). Duzenleme yoksa ya da
    /// cozulemiyorsa (Domain ayni hatayi kendi koduyla verir) null.
    /// </summary>
    private static async Task<LinkDstFacts?> LoadLinkFactsAsync(IcerikDbContext db, LinkRowState row, string? edited, CancellationToken cancellationToken)
    {
        if (!LinkEditPayload.TryRead(edited, out LinkEditValue value))
        {
            return null;
        }

        ResolvedLinkEdit resolved;
        try
        {
            resolved = LinkEdits.Resolve(row.Type, row.DstAnchor, row.DstSpan, value);
        }
        catch (DomainException)
        {
            return null;
        }

        return await LoadDstFactsAsync(db, resolved.DstAnchor, cancellationToken);
    }

    /// <summary>Birim capasi icin hedef olgulari: birim satiri, metin uzunlugu, ozet; Kur'an ayetinde quran_word sayisi.</summary>
    internal static async Task<LinkDstFacts> LoadDstFactsAsync(IcerikDbContext db, AnchorRef unit, CancellationToken cancellationToken)
    {
        var row = await db.Units.AsNoTracking()
            .Where(u => u.Anchor == unit)
            .Select(u => new { u.Metin, u.ContentHash })
            .SingleOrDefaultAsync(cancellationToken);
        int words = 0;
        if (unit.Kind == AnchorKind.Q)
        {
            short sure = (short)unit.Sure;
            short ayet = (short)unit.Ayet;
            words = await db.QuranWords.AsNoTracking().CountAsync(w => w.Surah == sure && w.Ayah == ayet, cancellationToken);
        }

        return row is null
            ? new LinkDstFacts(false, 0, words, null)
            : new LinkDstFacts(true, CodePointOffsets.CodePointCount(row.Metin), words, row.ContentHash);
    }

    /// <summary>Kelime duzeltmesi yeni degerinin olgulari: kok ya da lemma var mi (yalniz root_id ve lemma_id alaninda); deger okunamiyorsa null.</summary>
    internal static async Task<WordFixFacts?> LoadWordFixFactsAsync(IcerikDbContext db, string field, string? edited, CancellationToken cancellationToken)
    {
        string? raw;
        try
        {
            raw = WordFixPayload.ReadNewValue(edited, "duzenlenen");
        }
        catch (DomainException)
        {
            return null;
        }

        return await LoadWordFixFactsForValueAsync(db, field, raw, cancellationToken);
    }

    internal static async Task<WordFixFacts?> LoadWordFixFactsForValueAsync(IcerikDbContext db, string field, string? raw, CancellationToken cancellationToken)
    {
        if (!WordFixValues.TryParseId(raw, out int id))
        {
            return null;
        }

        if (string.Equals(field, ReviewFields.RootId, StringComparison.Ordinal))
        {
            return new WordFixFacts(await db.Roots.AsNoTracking().AnyAsync(r => r.Id == id, cancellationToken), false, null);
        }

        if (string.Equals(field, ReviewFields.LemmaId, StringComparison.Ordinal))
        {
            string? lang = await db.Lemmas.AsNoTracking().Where(l => l.Id == id).Select(l => l.Lang).SingleOrDefaultAsync(cancellationToken);
            return new WordFixFacts(false, lang is not null, lang);
        }

        return null;
    }

    /// <summary>Kok eslemesi degerinin alan dogrulamasi icin olgular: kok var mi; Arapca karsilik varsa dili ve koku.</summary>
    internal static async Task<RootMappingFacts> LoadFactsAsync(IcerikDbContext db, RootMappingValue value, CancellationToken cancellationToken)
    {
        int rootId = value.RootId;
        bool rootExists = await db.Roots.AsNoTracking().AnyAsync(r => r.Id == rootId, cancellationToken);
        if (value.ArLemmaId is not { } arId)
        {
            return new RootMappingFacts(rootExists, false, null, null);
        }

        var ar = await db.Lemmas.AsNoTracking()
            .Where(l => l.Id == arId)
            .Select(l => new { l.Lang, l.RootId })
            .SingleOrDefaultAsync(cancellationToken);
        return ar is null
            ? new RootMappingFacts(rootExists, false, null, null)
            : new RootMappingFacts(rootExists, true, ar.Lang, ar.RootId);
    }

    private static DomainException Missing() =>
        new(DomainErrorCodes.Bulunamadi, "Incelemenin hedef kaydi bulunamadi.");

    /// <summary>Kok eslemesi alanlarini lemma satirina yazar (kanit dokunulmaz: otomatik onayin denetim izi).</summary>
    internal static void ApplyMapping(Lemma lemma, LemmaMappingUpdate mapping)
    {
        lemma.RootId = mapping.RootId;
        lemma.ArLemmaId = mapping.ArLemmaId;
        lemma.EtymologicalOnly = mapping.EtymologicalOnly;
        lemma.Origin = mapping.Origin;
        lemma.OnayYolu = mapping.OnayYolu;
    }

    private static void ApplyToTarget(object entity, ReviewOutcome outcome)
    {
        switch (entity)
        {
            case Unit unit:
                if (outcome.UnitText is { } text)
                {
                    unit.Metin = text.Metin;
                    unit.ContentHash = text.ContentHash;
                    unit.Rev = text.Rev;
                    unit.TrNarrow = text.TrNarrow;
                    unit.TrWide = text.TrWide;
                    unit.ArNorm = text.ArNorm;
                    unit.TrStem = text.TrStem;
                }

                if (outcome.UnitMetinDurumu is { } durum)
                {
                    unit.MetinDurumu = durum;
                }

                break;
            case SurahAlias alias when outcome.TargetStatus is { } status:
                alias.Status = status;
                break;
            case Xref xref when outcome.TargetStatus is { } status:
                xref.Status = status;
                if (outcome.Link is { } link)
                {
                    xref.Type = link.Type;
                    xref.DstAnchor = link.DstAnchor;
                    xref.DstSpan = link.DstSpan;
                    xref.Origin = link.Origin;
                    xref.Evidence = link.Evidence;
                }

                break;
            case QuranWordFix fix when outcome.TargetStatus is { } status:
                fix.Status = status;
                if (outcome.WordFixNewValue is { } newValue)
                {
                    fix.NewValue = newValue;
                }

                break;
            case Lemma lemma when outcome.TargetStatus is { } status:
                lemma.Status = status;
                if (outcome.LemmaMapping is { } mapping)
                {
                    ApplyMapping(lemma, mapping);
                }

                break;
            case LemmaGloss gloss when outcome.TargetStatus is { } status:
                gloss.Status = status;
                if (outcome.Gloss is { } edited)
                {
                    gloss.AnlamKisa = edited.AnlamKisa;
                    gloss.ContentHash = edited.ContentHash;
                    gloss.Version = edited.Version;
                    gloss.Origin = edited.Origin;
                }

                break;
            default:
                break;
        }
    }
}
