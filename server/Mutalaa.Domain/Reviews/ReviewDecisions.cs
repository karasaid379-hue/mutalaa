using System.Text.Json;
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

    /// <summary>Kapali denetim kaydi: eslesen dizi kalip listesine eklendi (A18.4); onerilen <c>{anahtar, gerekce}</c>.</summary>
    public const string KalipEkle = "kalip_ekle";

    /// <summary>Kapali denetim kaydi: baglanti ima olarak da isaretlendi (A18.4); yeni <c>ima</c> satiri acildi.</summary>
    public const string ImaIsaretle = "ima_isaretle";
}

/// <summary>Inceleme kararinda yetkili rol adlari (K-51 madde 2); Identity rol adlariyla ayni dizgilerdir. Karar akisi bu sabitleri sonraki adimda kullanir.</summary>
public static class ReviewRoles
{
    public const string Editor = "editor";
    public const string Admin = "admin";

    /// <summary>Yalniz <c>uzmanda</c> durumundaki incelemenin kararini verir.</summary>
    public const string Uzman = "uzman";

    /// <summary>
    /// Karar yetkisi (K-51 madde 2): <c>uzmanda</c> kaydin kararini yalniz <c>uzman</c>, <c>acik</c> kaydin kararini yalniz editor ya da admin verir.
    /// Karar verilmis kayitta rol sorulmaz (karar zaten 409 <c>durum-gecisi-gecersiz</c> alir).
    /// </summary>
    public static bool CanDecide(ReviewStatus durum, bool isEditorOrAdmin, bool isUzman) => durum switch
    {
        ReviewStatus.Uzmanda => isUzman,
        ReviewStatus.Acik => isEditorOrAdmin,
        _ => true,
    };
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

    /// <summary>Turkce lemma kok eslemesi (K-51 madde 9): (lemma, kok_eslemesi); onerilen ve duzenlenen <c>{root_id, ar_lemma_id, etymological_only}</c>.</summary>
    public const string KokEslemesi = "kok_eslemesi";
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

/// <summary>
/// Birim hedefinin karar anindaki durumu (unit satirindan okunur). <paramref name="HasOffsetData"/>: birimin metne bagli ofsetli
/// turev alani var (bos olmayan <c>marks</c> ya da en az bir <c>sentences</c> araligi; <see cref="ReviewDecisions.HasOffsetData"/>).
/// <paramref name="IsMergedFollower"/>: birlesik mealin izleyen birimi (<c>attrs.birlesik_ile</c> dolu; K-49 madde 8,
/// <see cref="ReviewDecisions.IsMergedFollower"/>): metni bas birimdedir, kendi metni degistirilemez.
/// </summary>
public readonly record struct UnitReviewState(
    UnitKind Kind,
    SourceKind SourceKind,
    TextStatus MetinDurumu,
    string Metin,
    string ContentHash,
    int Rev,
    bool HasOffsetData = false,
    bool IsMergedFollower = false);

/// <summary>
/// <c>lemma_gloss</c> hedefinin karar anindaki satiri: guncel anlam, surum ve kokeni (Duzenle ve onayla, K-50 madde 6).
/// </summary>
public readonly record struct GlossReviewState(string AnlamKisa, string Version, string Origin);

/// <summary>
/// Hedefin karar anindaki durumu: durum sutunlu hedeflerde Status, birimde Unit. <c>quran_word_fix</c> icin <see cref="Field"/>
/// (duzeltmenin alani; review.alan ile eslesmeli), <c>lemma_gloss</c> icin <see cref="Gloss"/> dolu olmalidir.
/// </summary>
public readonly record struct ReviewTargetState
{
    public XrefStatus? Status { get; init; }

    public UnitReviewState? Unit { get; init; }

    /// <summary>quran_word_fix.field.</summary>
    public string? Field { get; init; }

    public GlossReviewState? Gloss { get; init; }

    /// <summary>lemma hedefinin satiri (dil, kok eslemesi, onay yolu); verilmezse lemma yalniz durum hedefi olarak islenir (onay yolu yazilmaz).</summary>
    public LemmaReviewState? LemmaRow { get; init; }

    /// <summary>xref hedefinin satiri (yalniz duzeltmeli onayda gerekir).</summary>
    public LinkRowState? LinkRow { get; init; }

    /// <summary>Duzeltmenin cozdugu hedef ucun olgulari (birim var mi, metin uzunlugu, kelime sayisi, ozet).</summary>
    public LinkDstFacts? LinkDst { get; init; }

    /// <summary>quran_word_fix new_value dogrulamasi icin olgular (kok var mi, lemma var mi ve dili).</summary>
    public WordFixFacts? FixFacts { get; init; }

    public static ReviewTargetState ForStatus(XrefStatus status) => new() { Status = status };

    public static ReviewTargetState ForFix(XrefStatus status, string field, WordFixFacts? facts = null) => new() { Status = status, Field = field, FixFacts = facts };

    /// <summary>Baglanti hedefi: satirin degerleri ve (duzeltme varsa) yeni hedef ucun olgulari.</summary>
    public static ReviewTargetState ForLink(XrefStatus status, LinkRowState link, LinkDstFacts? dst = null) => new() { Status = status, LinkRow = link, LinkDst = dst };

    public static ReviewTargetState ForGloss(XrefStatus status, GlossReviewState gloss) => new() { Status = status, Gloss = gloss };

    public static ReviewTargetState ForLemma(XrefStatus status, LemmaReviewState lemma) => new() { Status = status, LemmaRow = lemma };

    public static ReviewTargetState ForUnit(UnitReviewState unit) => new() { Unit = unit };
}

/// <summary>Birim metni degisikligi: yeni kanonik metin, ozet, rev ve arama anahtarlari. tr_stem hep NULL yazilir.</summary>
public readonly record struct UnitTextUpdate(string Metin, string ContentHash, int Rev, string TrNarrow, string TrWide, string ArNorm)
{
    /// <summary>Her zaman null: tr_stem hatta yeniden hesaplanir.</summary>
    public string? TrStem => null;
}

/// <summary>
/// lemma_gloss satirinin onaydan sonraki degerleri (Duzenle ve onayla): kanonik anlam, <c>sha256(anlam_kisa)</c>, surum ve koken.
/// Metin degismediyse surum ayni kalir.
/// </summary>
public readonly record struct LemmaGlossUpdate(string AnlamKisa, string ContentHash, string Version, string Origin);

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

    /// <summary>lemma_gloss'un duzenlenmis degerleri; null ise anlam degismez (durum onayi ya da ret).</summary>
    public LemmaGlossUpdate? Gloss { get; init; }

    /// <summary>
    /// lemma satirinin kok eslemesi alanlari (tam degistirme: kok, Arapca karsilik, etimolojik isaret, koken, onay yolu);
    /// null ise lemma'da yalniz <see cref="TargetStatus"/> yazilir.
    /// </summary>
    public LemmaMappingUpdate? LemmaMapping { get; init; }

    /// <summary>xref satirinin duzeltilmis alanlari (tur, hedef, aralik, koken, kanit); null ise baglanti degismez.</summary>
    public LinkUpdate? Link { get; init; }

    /// <summary>quran_word_fix.new_value yeni degeri; null ise degismez.</summary>
    public string? WordFixNewValue { get; init; }

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
public static partial class ReviewDecisions
{
    /// <summary>Gerekce uzunluk ust siniri (kod noktasi).</summary>
    public const int MaxGerekceLength = 2000;

    /// <summary>
    /// Durum hedefleri: (surah_alias|xref|lemma, status), (lemma, kok_eslemesi; yalniz Turkce lemma, K-51 madde 9), (lemma_gloss, anlam_kisa),
    /// (quran_word_fix, root_id|lemma_id|pos|features); birim metni: (unit, metin).
    /// </summary>
    public static bool IsSupported(string? hedefTablo, string? alan) => hedefTablo switch
    {
        ReviewTargets.SurahAlias or ReviewTargets.Xref => alan is ReviewFields.Status,
        ReviewTargets.Lemma => alan is ReviewFields.Status or ReviewFields.KokEslemesi,
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

        if (string.Equals(review.HedefTablo, ReviewTargets.Unit, StringComparison.Ordinal))
        {
            return ApproveUnitText(review, request, target, actor, gerekce);
        }

        if (IsRootMapping(review))
        {
            return ApproveRootMapping(review, request, target, actor, gerekce);
        }

        if (request.Duzenlenen is not null && IsLinkTarget(review))
        {
            return ApproveLink(review, request, target, actor, gerekce);
        }

        if (request.Duzenlenen is not null && string.Equals(review.HedefTablo, ReviewTargets.QuranWordFix, StringComparison.Ordinal))
        {
            return ApproveWordFix(review, request, target, actor, gerekce);
        }

        return ApproveStatus(review, request, target, actor, gerekce);
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

        if (IsRootMapping(review))
        {
            return RejectRootMapping(review, request, target, actor, gerekce);
        }

        RequireFieldMatch(review, target);
        RequireCandidate(target);
        return Rejected(review, request, actor, gerekce, secondStage: false) with { TargetStatus = XrefStatus.Red };
    }

    /// <summary>
    /// Birim metni onayinin uygulama adimi (saf hesap). (1) guncel content_hash onceki.content_hash ile ayni olmali
    /// (yoksa 409 <c>durum-gecisi-gecersiz</c>, hedef bayatlamis; onceki bossa taban cizgisi yok, kontrol atlanir);
    /// (2) uygulanacak metin duzenlenen, yoksa onerilen; ikisi de bossa (yalniz durum onayi) metin degismez, null doner;
    /// (3) metin degisiyorsa Canonicalize, ContentHash, rev + 1 ve arama anahtarlari (tr_stem NULL). Ozet degismiyorsa null doner.
    /// Degistirilemez metin (ayet, kuran_metni) 422 <c>degistirilemez-metin</c>.
    /// Ofsetli turev alanlar (marks, sentences) metin degisimiyle kayar; yeniden hesaplari BC-59'dadir (A20):
    /// metin GERCEKTEN degisiyorsa ve birimde ofsetli alan varsa 422 <c>inceleme-desteklenmiyor</c> (K-48 degismez; kisitlama BC-59'da kalkar).
    /// Birlesik mealin izleyen biriminde (<c>attrs.birlesik_ile</c> dolu; K-49 madde 8) metin degistiren her karar da ayni kodla 422 verir.
    /// Durum onayi (metin degismez) ve ret serbesttir.
    /// </summary>
    public static UnitTextUpdate? ApplyUnitText(UnitReviewState unit, string? onceki, string? onerilen, string? duzenlenen)
    {
        RequireMutable(unit);
        RequireFresh(unit, onceki);
        return ResolveTextChange(unit, onerilen, duzenlenen);
    }

    /// <summary>Uygulanacak degerden yeni metni hesaplar (ApplyUnitText 2 ve 3); metin degismiyorsa null. Ofsetli alan denetimi burada.</summary>
    private static UnitTextUpdate? ResolveTextChange(UnitReviewState unit, string? onerilen, string? duzenlenen)
    {
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

        RequireNotMergedFollower(unit);
        RequireNoOffsetData(unit);

        SearchKeys keys = SearchNormalizer.Keys(canonical);
        return new UnitTextUpdate(canonical, hash, unit.Rev + 1, keys.TrNarrow, keys.TrWide, keys.ArNorm);
    }

    /// <summary>
    /// Birimde metne bagli ofsetli turev alan var mi: <c>marks</c> bos dizi (ya da bos/null) degilse ya da <c>sentences</c> araligi varsa.
    /// Anlasilamayan <c>marks</c> degeri (bozuk JSON, dizi olmayan) ihtiyatla "var" sayilir.
    /// </summary>
    public static bool HasOffsetData(string? marksJson, int sentenceCount)
    {
        if (sentenceCount > 0)
        {
            return true;
        }

        if (string.IsNullOrWhiteSpace(marksJson))
        {
            return false;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(marksJson);
            return document.RootElement.ValueKind switch
            {
                JsonValueKind.Null or JsonValueKind.Undefined => false,
                JsonValueKind.Array => document.RootElement.GetArrayLength() > 0,
                _ => true,
            };
        }
        catch (JsonException)
        {
            return true;
        }
    }

    /// <summary>
    /// Birim birlesik mealin izleyen birimi mi: <c>attrs</c> jsonb'sinde <c>birlesik_ile</c> anahtari dolu (bos olmayan metin ya da
    /// null olmayan baska deger). Degismez iki yonludur (<c>birlesik_ile</c> varsa metin bos); metin bas birimdedir (K-49 madde 8).
    /// </summary>
    public static bool IsMergedFollower(string? attrsJson)
    {
        if (string.IsNullOrWhiteSpace(attrsJson))
        {
            return false;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(attrsJson);
            if (document.RootElement.ValueKind != JsonValueKind.Object
                || !document.RootElement.TryGetProperty("birlesik_ile", out JsonElement value))
            {
                return false;
            }

            return value.ValueKind switch
            {
                JsonValueKind.Null or JsonValueKind.Undefined => false,
                JsonValueKind.String => !string.IsNullOrEmpty(value.GetString()),
                _ => true,
            };
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static void RequireNoOffsetData(UnitReviewState unit)
    {
        if (unit.HasOffsetData)
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                "Ofsetli alanlarin (marks, sentences) yeniden hesabi BC-59'da (A20) yapilana kadar bu birimde metin degisimi desteklenmiyor; metni degistiren onay yapilamaz.");
        }
    }

    /// <summary>Izleyen birimin metni bos kalir; metin degistiren karar 422. Ileti "Ofsetli" ile baslamaz (editor OFFSET_MARKER eslesmesi).</summary>
    private static void RequireNotMergedFollower(UnitReviewState unit)
    {
        if (unit.IsMergedFollower)
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                "Birlesik meal izleyen birimi (attrs.birlesik_ile) kendi metnini tasimaz; metin degistiren karar verilemez, metin bas birimde duzeltilir.");
        }
    }

    private static ReviewOutcome ApproveStatus(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        bool isGloss = string.Equals(review.HedefTablo, ReviewTargets.LemmaGloss, StringComparison.Ordinal);
        if (request.Duzenlenen is not null && !isGloss)
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, "Bu hedefte editor degeri duzenlenemez; onayla ya da reddet.");
        }

        RequireFieldMatch(review, target);
        RequireCandidate(target);

        LemmaGlossUpdate? gloss = null;
        string? stored = review.Duzenlenen;
        if (request.Duzenlenen is not null)
        {
            (gloss, stored) = ResolveGlossEdit(review, request.Duzenlenen, target);
        }

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = gloss is null ? ReviewActions.Onayla : ReviewActions.DuzenleOnayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = stored,
            TargetStatus = XrefStatus.Onayli,
            Gloss = gloss,

            // Turkce lemma durum onayi da editor onayidir: lemma_tr_onayli_onay_yolu_check onayli tr satirda onay yolunu zorunlu kilar.
            LemmaMapping = target.LemmaRow is { IsTurkish: true } row ? row.ToUpdate(onayYolu: LemmaApprovalPaths.Editor) : null,
        };
    }

    /// <summary>
    /// Duzenle ve onayla (lemma_gloss, K-50 madde 6): editor degeri kanonikilestirilir (NFC), ozet <c>sha256(kanonik anlam_kisa)</c> olur,
    /// metin satirdakinden farkliysa surum bir artar; deger onerilen.anlam_kisa'dan farkliysa koken <c>editor</c> olur, ayniysa degismez.
    /// <c>onerilen.dagilim</c> ve <c>baskin_pay</c> hedefe uygulanmaz. Donen ikinci deger review.duzenlenen jsonb'sidir.
    /// </summary>
    private static (LemmaGlossUpdate Update, string Stored) ResolveGlossEdit(Review review, string duzenlenen, ReviewTargetState target)
    {
        GlossReviewState row = target.Gloss
            ?? throw new InvalidOperationException("lemma_gloss hedefi icin satir durumu verilmeli.");

        string canonical = LemmaGlossText.Normalize(ReviewPayload.ReadAnlamKisa(duzenlenen, "duzenlenen"), "duzenlenen.anlam_kisa");
        string? proposed = ReviewPayload.ReadAnlamKisa(review.Onerilen, "onerilen");

        bool textChanged = !string.Equals(canonical, row.AnlamKisa, StringComparison.Ordinal);
        string version = textChanged ? LemmaGlossText.NextVersion(row.Version) : row.Version;
        string origin = string.Equals(canonical, proposed, StringComparison.Ordinal) ? row.Origin : LemmaGlossText.EditorOrigin;

        return (new LemmaGlossUpdate(canonical, ContentHash.Compute(canonical), version, origin), LemmaGlossText.ToPayload(canonical));
    }

    /// <summary>
    /// <c>quran_word_fix</c> incelemesinde review.alan duzeltmenin <c>field</c> degeriyle eslesmeli (root_id, lemma_id, pos, features);
    /// eslesmeyen karar 422 <c>inceleme-desteklenmiyor</c>. Alan degeri desteklenen dort alandan degilse zaten eslesemez.
    /// </summary>
    private static void RequireFieldMatch(Review review, ReviewTargetState target)
    {
        if (!string.Equals(review.HedefTablo, ReviewTargets.QuranWordFix, StringComparison.Ordinal))
        {
            return;
        }

        string field = target.Field
            ?? throw new InvalidOperationException("quran_word_fix hedefi icin duzeltmenin alani verilmeli.");
        if (!string.Equals(field, review.Alan, StringComparison.Ordinal))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"Inceleme alani '{review.Alan}' duzeltmenin alaniyla ('{field}') eslesmiyor.");
        }
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
            if (unit.HasOffsetData || unit.IsMergedFollower)
            {
                // Metin ikinci onayda uygulanir; uygulanamayacak degisikligi kullanici ilk onayda ogrensin.
                _ = ResolveTextChange(unit, review.Onerilen, stored);
            }

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

    internal static ReviewOutcome Rejected(Review review, ReviewDecisionRequest request, string actor, string gerekce, bool secondStage) =>
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

    internal static string RequireActor(string? actor)
    {
        if (string.IsNullOrWhiteSpace(actor))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Karari veren kullanici belli degil.");
        }

        return actor;
    }

    internal static string RequireGerekce(string? gerekce)
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

    internal static void RequireOpen(Review review)
    {
        // uzmanda kayit karar icin acik gibi kabul edilir; kimin karar verecegi ReviewRoles.CanDecide ile (Api) sorulur.
        if (review.Durum is not (ReviewStatus.Acik or ReviewStatus.Uzmanda))
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

    internal static void RequireCandidate(ReviewTargetState target)
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
