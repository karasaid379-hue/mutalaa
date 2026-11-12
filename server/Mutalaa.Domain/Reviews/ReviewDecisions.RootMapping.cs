using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// Turkce lemma kok eslemesi incelemesi (K-51 madde 9): onay, ret, Duzenle ve onayla ve otomatik onaya itirazin karari.
/// Kontrol sirasi ortak siradir (desteklenmeyen hedef 422, girdi 400, kayit durumu 409, dort goz 409, hedef durumu 409, deger 400).
/// </summary>
public static partial class ReviewDecisions
{
    /// <summary>Hedef (lemma, kok_eslemesi) mi (Ordinal).</summary>
    public static bool IsRootMappingTarget(string? hedefTablo, string? alan) =>
        string.Equals(hedefTablo, ReviewTargets.Lemma, StringComparison.Ordinal)
        && string.Equals(alan, ReviewFields.KokEslemesi, StringComparison.Ordinal);

    internal static bool IsRootMapping(Review review) => IsRootMappingTarget(review.HedefTablo, review.Alan);

    /// <summary>kok_eslemesi yalniz Turkce lemmada islenir; Arapca (QAC) lemmanin esleme incelemesi yoktur: 422.</summary>
    internal static void RequireTurkish(LemmaReviewState lemma)
    {
        if (!lemma.IsTurkish)
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                "Kok eslemesi incelemesi yalniz Turkce (lang = 'tr') lemmada desteklenir.");
        }
    }

    /// <summary>Itiraz yalniz otomatik onayli lemmaya (status onayli ve onay yolu otomatik) yapilir ve onaylanir: aksi 409.</summary>
    internal static void RequireAutoApproved(XrefStatus status, LemmaReviewState lemma)
    {
        if (status != XrefStatus.Onayli || !string.Equals(lemma.OnayYolu, LemmaApprovalPaths.Otomatik, StringComparison.Ordinal))
        {
            throw new DomainException(
                DomainErrorCodes.DurumGecisiGecersiz,
                $"Itiraz yalniz otomatik onayli lemmaya yapilir (durum: {status.ToLabel()}, onay yolu: {lemma.OnayYolu ?? "yok"}).");
        }
    }

    private static LemmaReviewState RequireLemmaRow(ReviewTargetState target) =>
        target.LemmaRow ?? throw new InvalidOperationException("lemma hedefi icin lemma satiri verilmeli.");

    private static XrefStatus RequireStatus(ReviewTargetState target) =>
        target.Status ?? throw new InvalidOperationException("Durum sutunlu hedef icin hedef durumu verilmeli.");

    private static ReviewOutcome ApproveRootMapping(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        LemmaReviewState lemma = RequireLemmaRow(target);
        RequireTurkish(lemma);

        if (LemmaMappingPayload.IsObjection(review.Onerilen))
        {
            return ApproveObjection(request, target, lemma, actor, gerekce);
        }

        RequireCandidate(target);

        RootMappingValue? edited = LemmaMappingPayload.Read(request.Duzenlenen, "duzenlenen");
        if (request.Duzenlenen is not null && edited is null)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen bos olamaz.");
        }

        // Editor degeri verdiyse bozuk bir hat onerisi onu engellemez (editor onu duzeltmek icin duzenler); yoksa oneri okunur ve bozuksa 400.
        RootMappingValue? proposed = edited is null
            ? LemmaMappingPayload.Read(review.Onerilen, "onerilen")
            : (LemmaMappingPayload.TryRead(review.Onerilen, out RootMappingValue readable) ? readable : null);

        RootMappingValue value = edited ?? proposed
            ?? throw new DomainException(DomainErrorCodes.Dogrulama, "Onerilen kok eslemesi yok; duzenlenen deger verilmeli.");
        LemmaMappingPayload.Validate(value, lemma.Facts);

        // Koken: deger hattin onerisinden farkliysa (oneri yoksa da) editor; ayniysa hattin kokeni korunur (lemma_gloss ile ayni kural).
        string? origin = proposed is { } p && p == value ? lemma.Origin : LemmaOrigins.Editor;

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = edited is null ? ReviewActions.Onayla : ReviewActions.DuzenleOnayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = edited is { } e ? LemmaMappingPayload.ToPayload(e) : review.Duzenlenen,
            TargetStatus = XrefStatus.Onayli,
            LemmaMapping = lemma.ToUpdate(LemmaApprovalPaths.Editor, origin, value),
        };
    }

    /// <summary>Itirazin onayi: lemma aday olur, onay yolu bosalir (kanit ve esleme degerleri kalir); hat tr_root_index ve tr_form'u bir sonraki kosuda kaldirir.</summary>
    private static ReviewOutcome ApproveObjection(ReviewDecisionRequest request, ReviewTargetState target, LemmaReviewState lemma, string actor, string gerekce)
    {
        if (request.Duzenlenen is not null)
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, "Itiraz onayi deger tasimaz; onayla ya da reddet.");
        }

        RequireAutoApproved(RequireStatus(target), lemma);
        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = ReviewActions.Onayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            TargetStatus = XrefStatus.Aday,
            LemmaMapping = lemma.ToUpdate(onayYolu: null),
        };
    }

    private static ReviewOutcome RejectRootMapping(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        LemmaReviewState lemma = RequireLemmaRow(target);
        RequireTurkish(lemma);

        ReviewOutcome rejected = Rejected(review, request, actor, gerekce, secondStage: false);
        if (LemmaMappingPayload.IsObjection(review.Onerilen))
        {
            // Itirazin reddi lemmayi degistirmez.
            return rejected;
        }

        RequireCandidate(target);
        return rejected with { TargetStatus = XrefStatus.Red };
    }
}
