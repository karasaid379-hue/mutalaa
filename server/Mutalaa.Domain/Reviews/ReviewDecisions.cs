using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>review.eylem degerleri (Editoryal veritabani 8).</summary>
public static class ReviewActions
{
    public const string Oner = "oner";
    public const string Onayla = "onayla";
    public const string DuzenleOnayla = "duzenle_onayla";
    public const string Reddet = "reddet";
    public const string UzmanaGonder = "uzmana_gonder";
    public const string EtimolojikIsaretle = "etimolojik_isaretle";
}

/// <summary>review.alan degerleri (Backend API 4.1 kuyruk tablosu).</summary>
public static class ReviewFields
{
    public const string Status = "status";
    public const string Metin = "metin";
    public const string AnlamKisa = "anlam_kisa";
    public const string RootId = "root_id";
    public const string LemmaId = "lemma_id";
    public const string Pos = "pos";
    public const string Features = "features";
}

/// <summary>Onay ya da ret istegi. Now UTC olmali; saf islevler saati kendileri okumaz.</summary>
public readonly record struct ReviewDecisionRequest
{
    /// <summary>Karari veren editorun kullanici adi.</summary>
    public required string Actor { get; init; }

    /// <summary>Zorunlu, bos olmayan, en cok 2000 karakter (kod noktasi).</summary>
    public string? Gerekce { get; init; }

    /// <summary>Editorun duzenledigi deger (jsonb); yalniz birim metni onayinda ve yalniz ilk onayda kabul edilir. Retle verilemez.</summary>
    public string? Duzenlenen { get; init; }

    public required DateTime Now { get; init; }
}

/// <summary>Birim hedefinin karar anindaki durumu (unit satirindan okunur).</summary>
public readonly record struct UnitReviewState(
    UnitKind Kind,
    SourceKind SourceKind,
    TextStatus MetinDurumu,
    string Metin,
    string ContentHash,
    int Rev);

/// <summary>Hedefin karar anindaki durumu: durum sutunlu hedeflerde Status, birimde Unit.</summary>
public readonly record struct ReviewTargetState
{
    public XrefStatus? Status { get; init; }

    public UnitReviewState? Unit { get; init; }

    public static ReviewTargetState ForStatus(XrefStatus status) => new() { Status = status };

    public static ReviewTargetState ForUnit(UnitReviewState unit) => new() { Unit = unit };
}

/// <summary>Birim metni degisikligi: yeni kanonik metin, ozet, rev ve arama anahtarlari. tr_stem hep NULL yazilir.</summary>
public readonly record struct UnitTextUpdate(string Metin, string ContentHash, int Rev, string TrNarrow, string TrWide, string ArNorm)
{
    /// <summary>Her zaman null: tr_stem hatta yeniden hesaplanir.</summary>
    public string? TrStem => null;
}

/// <summary>
/// Kararin sonucu: review satirinin yeni alanlari ve hedefe yazilacak degisiklikler. Hedef degisikligi olmayan alan null'dir
/// (TargetStatus, UnitMetinDurumu, UnitText). Veritabani yazimi Api katmaninda tek islemde yapilir.
/// </summary>
public readonly record struct ReviewOutcome
{
    public required ReviewStatus Durum { get; init; }

    public required string Eylem { get; init; }

    public string? Inceleyen { get; init; }

    public DateTime? IncelendiAt { get; init; }

    public string? Gerekce { get; init; }

    public string? Duzenlenen { get; init; }

    public string? IkinciInceleyen { get; init; }

    public DateTime? IkinciIncelendiAt { get; init; }

    public string? IkinciGerekce { get; init; }

    /// <summary>Durum sutunlu hedefin yeni durumu (Onayli ya da Red).</summary>
    public XrefStatus? TargetStatus { get; init; }

    /// <summary>Birimin yeni metin_durumu; null ise degismez.</summary>
    public TextStatus? UnitMetinDurumu { get; init; }

    /// <summary>Birimin yeni metni ve turevleri; null ise metin degismez.</summary>
    public UnitTextUpdate? UnitText { get; init; }

    /// <summary>Review satirinin karar alanlarini yazar (hedef degisiklikleri yazilmaz).</summary>
    public void ApplyTo(Review review)
    {
        ArgumentNullException.ThrowIfNull(review);
        review.Durum = Durum;
        review.Eylem = Eylem;
        review.Inceleyen = Inceleyen;
        review.IncelendiAt = IncelendiAt;
        review.Gerekce = Gerekce;
        review.Duzenlenen = Duzenlenen;
        review.IkinciInceleyen = IkinciInceleyen;
        review.IkinciIncelendiAt = IkinciIncelendiAt;
        review.IkinciGerekce = IkinciGerekce;
    }
}

/// <summary>
/// Inceleme karari kurallari (K-48), saf islevler: veritabani, saat ve HTTP yok. Hata <see cref="DomainException"/>'dir.
/// Kontrol sirasi: desteklenmeyen hedef (422), girdi (400), kayit durumu (409), dort goz (409), hedef durumu (409), degistirilemez metin (422), deger.
/// </summary>
public static class ReviewDecisions
{
    /// <summary>Gerekce uzunluk ust siniri (kod noktasi).</summary>
    public const int MaxGerekceLength = 2000;

    /// <summary>Durum hedefleri: (surah_alias|xref|lemma, status), (lemma_gloss, anlam_kisa), (quran_word_fix, root_id|lemma_id|pos|features); birim metni: (unit, metin).</summary>
    public static bool IsSupported(string? hedefTablo, string? alan) => hedefTablo switch
    {
        ReviewTargets.SurahAlias or ReviewTargets.Xref or ReviewTargets.Lemma => alan is ReviewFields.Status,
        ReviewTargets.LemmaGloss => alan is ReviewFields.AnlamKisa,
        ReviewTargets.QuranWordFix => alan is ReviewFields.RootId or ReviewFields.LemmaId or ReviewFields.Pos or ReviewFields.Features,
        ReviewTargets.Unit => alan is ReviewFields.Metin,
        _ => false,
    };

    /// <summary>Ikinci onay yalniz (unit, metin) ve birim turu meal ya da tefsir ise gerekir.</summary>
    public static bool RequiresSecondApproval(string? hedefTablo, string? alan, UnitKind kind) =>
        hedefTablo is ReviewTargets.Unit && alan is ReviewFields.Metin && kind is UnitKind.Meal or UnitKind.Tefsir;

    /// <summary>Acik kaydi onaylar (ilk ya da ikinci onay) ve sonucu hesaplar.</summary>
    public static ReviewOutcome Approve(Review review, ReviewDecisionRequest request, ReviewTargetState target)
    {
        ArgumentNullException.ThrowIfNull(review);
        RequireSupported(review);
        string actor = RequireActor(request.Actor);
        string gerekce = RequireGerekce(request.Gerekce);
        RequireOpen(review);
        RequireNotOwnProposal(review, actor);

        return string.Equals(review.HedefTablo, ReviewTargets.Unit, StringComparison.Ordinal)
            ? ApproveUnitText(review, request, target, actor, gerekce)
            : ApproveStatus(review, request, target, actor, gerekce);
    }

    /// <summary>Acik kaydi reddeder. Ret her asamada verilebilir; hedefi degistirmez (durum sutunlu hedef Red olur, incelemede birim taslaga doner).</summary>
    public static ReviewOutcome Reject(Review review, ReviewDecisionRequest request, ReviewTargetState target)
    {
        ArgumentNullException.ThrowIfNull(review);
        RequireSupported(review);
        string actor = RequireActor(request.Actor);
        string gerekce = RequireGerekce(request.Gerekce);
        if (request.Duzenlenen is not null)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Ret duzenlenen deger tasimaz.");
        }

        RequireOpen(review);

        if (string.Equals(review.HedefTablo, ReviewTargets.Unit, StringComparison.Ordinal))
        {
            UnitReviewState unit = RequireUnit(target);
            bool secondStage = RequiresSecondApproval(review.HedefTablo, review.Alan, unit.Kind) && !string.IsNullOrEmpty(review.Inceleyen);
            return Rejected(review, request, actor, gerekce, secondStage) with
            {
                UnitMetinDurumu = unit.MetinDurumu == TextStatus.Incelemede ? TextStatus.Taslak : null,
            };
        }

        RequireCandidate(target);
        return Rejected(review, request, actor, gerekce, secondStage: false) with { TargetStatus = XrefStatus.Red };
    }

    /// <summary>
    /// Birim metni onayinin uygulama adimi (saf hesap). (1) guncel content_hash onceki.content_hash ile ayni olmali
    /// (yoksa 409 <c>durum-gecisi-gecersiz</c>, hedef bayatlamis; onceki bossa taban cizgisi yok, kontrol atlanir);
    /// (2) uygulanacak metin duzenlenen, yoksa onerilen; ikisi de bossa (yalniz durum onayi) metin degismez, null doner;
    /// (3) metin degisiyorsa Canonicalize, ContentHash, rev + 1 ve arama anahtarlari (tr_stem NULL). Ozet degismiyorsa null doner.
    /// Degistirilemez metin (ayet, kuran_metni) 422 <c>degistirilemez-metin</c>.
    /// </summary>
    public static UnitTextUpdate? ApplyUnitText(UnitReviewState unit, string? onceki, string? onerilen, string? duzenlenen)
    {
        RequireMutable(unit);
        RequireFresh(unit, onceki);

        string? text = ReviewPayload.ReadMetin(duzenlenen, "duzenlenen") ?? ReviewPayload.ReadMetin(onerilen, "onerilen");
        if (text is null)
        {
            return null;
        }

        string canonical;
        string hash;
        try
        {
            canonical = TextCanonicalizer.Canonicalize(text);
            hash = ContentHash.Compute(canonical);
        }
        catch (ArgumentException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Metin gecerli Unicode degil.", e);
        }

        if (canonical.Length == 0)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Metin bos olamaz.");
        }

        if (string.Equals(hash, unit.ContentHash, StringComparison.Ordinal))
        {
            return null;
        }

        SearchKeys keys = SearchNormalizer.Keys(canonical);
        return new UnitTextUpdate(canonical, hash, unit.Rev + 1, keys.TrNarrow, keys.TrWide, keys.ArNorm);
    }

    private static ReviewOutcome ApproveStatus(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        if (request.Duzenlenen is not null)
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, "Bu hedefte editor degeri duzenlenemez; onayla ya da reddet.");
        }

        RequireCandidate(target);
        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = ReviewActions.Onayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = review.Duzenlenen,
            TargetStatus = XrefStatus.Onayli,
        };
    }

    private static ReviewOutcome ApproveUnitText(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        UnitReviewState unit = RequireUnit(target);
        RequireMutable(unit);

        bool twoStage = RequiresSecondApproval(review.HedefTablo, review.Alan, unit.Kind);
        bool second = twoStage && !string.IsNullOrEmpty(review.Inceleyen);

        if (second)
        {
            if (request.Duzenlenen is not null)
            {
                throw new DomainException(
                    DomainErrorCodes.IncelemeDesteklenmiyor,
                    "Ikinci onay degeri degistiremez; degistirmek isteyen reddeder.");
            }

            if (string.Equals(review.Inceleyen, actor, StringComparison.OrdinalIgnoreCase))
            {
                throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Ikinci onay ilk onaydan farkli bir editorden gelmeli.");
            }
        }

        // Girilen deger bozuksa hemen 400; kayitli duzenlenen ilk onayda zaten dogrulanmistir.
        if (request.Duzenlenen is not null && ReviewPayload.ReadMetin(request.Duzenlenen, "duzenlenen") is null)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen bos olamaz.");
        }

        string? stored = request.Duzenlenen ?? review.Duzenlenen;
        string eylem = stored is null ? ReviewActions.Onayla : ReviewActions.DuzenleOnayla;

        if (twoStage && !second)
        {
            // Ilk onay: metin uygulanmaz, kayit acik kalir. Taslak birim incelemede olur; onayli birim eski metnini ve durumunu korur.
            RequireFresh(unit, review.Onceki);
            return new ReviewOutcome
            {
                Durum = ReviewStatus.Acik,
                Eylem = eylem,
                Inceleyen = actor,
                IncelendiAt = request.Now,
                Gerekce = gerekce,
                Duzenlenen = stored,
                UnitMetinDurumu = unit.MetinDurumu == TextStatus.Taslak ? TextStatus.Incelemede : null,
            };
        }

        UnitTextUpdate? text = ApplyUnitText(unit, review.Onceki, review.Onerilen, stored);
        if (second)
        {
            return new ReviewOutcome
            {
                Durum = ReviewStatus.Onaylandi,
                Eylem = eylem,
                Inceleyen = review.Inceleyen,
                IncelendiAt = review.IncelendiAt,
                Gerekce = review.Gerekce,
                Duzenlenen = stored,
                IkinciInceleyen = actor,
                IkinciIncelendiAt = request.Now,
                IkinciGerekce = gerekce,
                UnitMetinDurumu = TextStatus.Onayli,
                UnitText = text,
            };
        }

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = eylem,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = stored,
            UnitMetinDurumu = TextStatus.Onayli,
            UnitText = text,
        };
    }

    private static ReviewOutcome Rejected(Review review, ReviewDecisionRequest request, string actor, string gerekce, bool secondStage) =>
        secondStage
            ? new ReviewOutcome
            {
                Durum = ReviewStatus.Reddedildi,
                Eylem = ReviewActions.Reddet,
                Inceleyen = review.Inceleyen,
                IncelendiAt = review.IncelendiAt,
                Gerekce = review.Gerekce,
                Duzenlenen = review.Duzenlenen,
                IkinciInceleyen = actor,
                IkinciIncelendiAt = request.Now,
                IkinciGerekce = gerekce,
            }
            : new ReviewOutcome
            {
                Durum = ReviewStatus.Reddedildi,
                Eylem = ReviewActions.Reddet,
                Inceleyen = actor,
                IncelendiAt = request.Now,
                Gerekce = gerekce,
                Duzenlenen = review.Duzenlenen,
            };

    private static void RequireSupported(Review review)
    {
        if (!IsSupported(review.HedefTablo, review.Alan))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{review.HedefTablo}' hedefinde '{review.Alan}' alani icin inceleme desteklenmiyor.");
        }
    }

    private static string RequireActor(string? actor)
    {
        if (string.IsNullOrWhiteSpace(actor))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Karari veren kullanici belli degil.");
        }

        return actor;
    }

    private static string RequireGerekce(string? gerekce)
    {
        if (string.IsNullOrWhiteSpace(gerekce))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "gerekce zorunludur.");
        }

        if (CodePointOffsets.CodePointCount(gerekce) > MaxGerekceLength)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "gerekce en cok 2000 karakter olabilir.");
        }

        return gerekce;
    }

    private static void RequireOpen(Review review)
    {
        if (review.Durum != ReviewStatus.Acik)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, $"Yalniz acik kayda karar verilebilir (durum: {review.Durum.ToLabel()}).");
        }
    }

    /// <summary>Dort goz: editor kokenli kayitta oneren kendi onerisini onaylayamaz (kullanici adi buyuk-kucuk harfe duyarsiz, Ordinal).</summary>
    private static void RequireNotOwnProposal(Review review, string actor)
    {
        if (review.Koken == XrefOrigin.Editor && string.Equals(review.Oneren, actor, StringComparison.OrdinalIgnoreCase))
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Editor kendi onerisini onaylayamaz.");
        }
    }

    private static void RequireCandidate(ReviewTargetState target)
    {
        XrefStatus status = target.Status
            ?? throw new InvalidOperationException("Durum sutunlu hedef icin hedef durumu verilmeli.");
        if (status != XrefStatus.Aday)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, $"Hedef aday degil (durum: {status.ToLabel()}).");
        }
    }

    private static UnitReviewState RequireUnit(ReviewTargetState target) =>
        target.Unit ?? throw new InvalidOperationException("Birim hedefi icin birim durumu verilmeli.");

    private static void RequireMutable(UnitReviewState unit)
    {
        if (TextMutability.IsImmutable(unit.Kind, unit.SourceKind))
        {
            throw new DomainException(DomainErrorCodes.DegistirilemezMetin, "Ayet (Tanzil) metni degistirilemez.");
        }
    }

    private static void RequireFresh(UnitReviewState unit, string? onceki)
    {
        string? expected = ReviewPayload.ReadContentHash(onceki, "onceki");
        if (expected is not null && !string.Equals(expected, unit.ContentHash, StringComparison.Ordinal))
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Hedef bayatlamis: birimin metni inceleme acildiktan sonra degismis.");
        }
    }
}
