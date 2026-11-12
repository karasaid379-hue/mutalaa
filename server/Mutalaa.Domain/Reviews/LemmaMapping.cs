using System.Globalization;
using System.Text.Json;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Reviews;

/// <summary>lemma.lang degerleri.</summary>
public static class LemmaLangs
{
    public const string Arabic = "ar";
    public const string Turkish = "tr";
}

/// <summary>lemma.onay_yolu degerleri (K-51 madde 9): yalniz lang = 'tr' ve status = 'onayli' iken dolu.</summary>
public static class LemmaApprovalPaths
{
    public const string Editor = "editor";
    public const string Otomatik = "otomatik";
}

/// <summary>lemma.origin degeri: editor kararinin degistirdigi eslemenin kokeni (hat degerleri 'kaikki' vb. hattindir).</summary>
public static class LemmaOrigins
{
    public const string Editor = "editor";
}

/// <summary>Turkce lemma kok eslemesinin degeri: <c>{root_id, ar_lemma_id, etymological_only}</c> (review.onerilen ve review.duzenlenen).</summary>
public readonly record struct RootMappingValue(int RootId, int? ArLemmaId, bool EtymologicalOnly);

/// <summary>
/// Kok eslemesi degerinin dogrulanmasi icin veritabani olgulari (Domain veritabanina bakmaz; Api yukler): kok var mi, Arapca karsilik var mi,
/// dili ve koku.
/// </summary>
public readonly record struct RootMappingFacts(bool RootExists, bool ArLemmaExists, string? ArLemmaLang, int? ArLemmaRootId);

/// <summary>
/// lemma hedefinin karar anindaki satiri. <see cref="Facts"/> yalniz (lemma, kok_eslemesi) onayinda gerekir: degeri Api yukleyip verir.
/// </summary>
public readonly record struct LemmaReviewState(string Lang, int? RootId, int? ArLemmaId, bool EtymologicalOnly, string? Origin, string? OnayYolu)
{
    public RootMappingFacts? Facts { get; init; }

    public bool IsTurkish => string.Equals(Lang, LemmaLangs.Turkish, StringComparison.Ordinal);

    /// <summary>Satirin degerleri ayni kalir; yalniz onay yolu (ve istenirse koken) degisir.</summary>
    internal LemmaMappingUpdate ToUpdate(string? onayYolu, string? origin = null, RootMappingValue? value = null) =>
        new(
            value?.RootId ?? RootId,
            value is { } v ? v.ArLemmaId : ArLemmaId,
            value?.EtymologicalOnly ?? EtymologicalOnly,
            origin ?? Origin,
            onayYolu);
}

/// <summary>lemma satirinin kok eslemesi alanlarinin onaydan sonraki degerleri (hepsi yazilir).</summary>
public readonly record struct LemmaMappingUpdate(int? RootId, int? ArLemmaId, bool EtymologicalOnly, string? Origin, string? OnayYolu);

/// <summary>
/// Kok eslemesi jsonb degerleri ve itiraz isareti. Bos deger (null, JSON null) "deger yok" demektir; bozuk JSON, nesne olmayan deger,
/// eksik ya da yanlis turde alan <c>dogrulama</c> hatasidir.
/// </summary>
public static class LemmaMappingPayload
{
    public const string RootIdKey = "root_id";
    public const string ArLemmaIdKey = "ar_lemma_id";
    public const string EtymologicalOnlyKey = "etymological_only";
    public const string ObjectionKey = "itiraz";
    public const string ReasonKey = "gerekce";

    /// <summary>Degeri okur; deger yoksa null. <c>root_id</c> ve <c>etymological_only</c> zorunludur, <c>ar_lemma_id</c> yoksa ya da null ise Arapca karsilik yoktur.</summary>
    public static RootMappingValue? Read(string? json, string name)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        using JsonDocument document = Parse(json, name);
        JsonElement root = document.RootElement;
        if (root.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir JSON nesnesi olmali.");
        }

        int rootId = ReadId(root, RootIdKey, name, required: true) ?? throw new InvalidOperationException("required");
        int? arLemmaId = ReadId(root, ArLemmaIdKey, name, required: false);
        if (!root.TryGetProperty(EtymologicalOnlyKey, out JsonElement etymological)
            || etymological.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{EtymologicalOnlyKey} true ya da false olmali.");
        }

        return new RootMappingValue(rootId, arLemmaId, etymological.GetBoolean());
    }

    /// <summary>Hata vermeden okur: Api, degeri dogrulamadan once hangi kimliklerin yuklenecegini bilmek icin kullanir.</summary>
    public static bool TryRead(string? json, out RootMappingValue value)
    {
        try
        {
            RootMappingValue? read = Read(json, "deger");
            value = read.GetValueOrDefault();
            return read.HasValue;
        }
        catch (DomainException)
        {
            value = default;
            return false;
        }
    }

    /// <summary>review.duzenlenen jsonb degeri: <c>{"root_id", "ar_lemma_id", "etymological_only"}</c>.</summary>
    public static string ToPayload(RootMappingValue value) =>
        JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            [RootIdKey] = value.RootId,
            [ArLemmaIdKey] = value.ArLemmaId,
            [EtymologicalOnlyKey] = value.EtymologicalOnly,
        });

    /// <summary>Kayit otomatik onaya itiraz mi: <c>onerilen.itiraz = true</c>. Okunamayan ya da itiraz olmayan deger false.</summary>
    public static bool IsObjection(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return false;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(json);
            return document.RootElement.ValueKind == JsonValueKind.Object
                && document.RootElement.TryGetProperty(ObjectionKey, out JsonElement flag)
                && flag.ValueKind == JsonValueKind.True;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    /// <summary>Itiraz kaydinin onerilen degeri: <c>{"itiraz": true, "gerekce": ...}</c>.</summary>
    public static string ToObjectionPayload(string gerekce) =>
        JsonSerializer.Serialize(new Dictionary<string, object> { [ObjectionKey] = true, [ReasonKey] = gerekce });

    /// <summary>
    /// Degeri alanda dogrular (K-51 madde 2 ve 9): kok var olmali; Arapca karsilik varsa var olmali, <c>lang = 'ar'</c> olmali ve koku
    /// <c>root_id</c> ile ayni olmali. Hata <c>dogrulama</c> (400).
    /// </summary>
    public static void Validate(RootMappingValue value, RootMappingFacts? facts)
    {
        RootMappingFacts f = facts ?? throw new InvalidOperationException("Kok eslemesi hedefi icin dogrulama olgulari verilmeli.");
        if (!f.RootExists)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"root_id {value.RootId.ToString(CultureInfo.InvariantCulture)} diye bir kok yok.");
        }

        if (value.ArLemmaId is null)
        {
            return;
        }

        if (!f.ArLemmaExists)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "ar_lemma_id diye bir lemma yok.");
        }

        if (!string.Equals(f.ArLemmaLang, LemmaLangs.Arabic, StringComparison.Ordinal))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "ar_lemma_id Arapca (lang = 'ar') bir lemma olmali.");
        }

        if (f.ArLemmaRootId != value.RootId)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "ar_lemma_id lemmasinin koku root_id ile ayni olmali.");
        }
    }

    private static JsonDocument Parse(string json, string name)
    {
        try
        {
            return JsonDocument.Parse(json);
        }
        catch (JsonException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli bir JSON degil.", e);
        }
    }

    private static int? ReadId(JsonElement root, string property, string name, bool required)
    {
        if (!root.TryGetProperty(property, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
        {
            return required
                ? throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property} zorunludur.")
                : null;
        }

        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out int id) || id < 1)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property} 1 ya da daha buyuk bir tamsayi olmali.");
        }

        return id;
    }
}

/// <summary>Otomatik onay kanitinin ozeti (<c>lemma.kanit</c>): kaynak sayisi, QAC eslesme turu, karar ve neden. Alan yoksa ya da turu uymuyorsa null.</summary>
public readonly record struct LemmaKanitSummary(int? KaynakSayisi, string? QacEslesme, string? Karar, string? Neden, string? PolitikaSurumu)
{
    /// <summary>Kanit yoksa, bozuksa ya da nesne degilse null (ozet cikarilamaz); aksi halde bulunabilen alanlarla ozet.</summary>
    public static LemmaKanitSummary? Summarize(string? kanitJson)
    {
        if (string.IsNullOrWhiteSpace(kanitJson))
        {
            return null;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(kanitJson);
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            int? sources = root.TryGetProperty("kaynaklar", out JsonElement list) && list.ValueKind == JsonValueKind.Array
                ? list.GetArrayLength()
                : null;
            string? match = root.TryGetProperty("qac", out JsonElement qac) && qac.ValueKind == JsonValueKind.Object
                ? Text(qac, "eslesme")
                : null;
            return new LemmaKanitSummary(sources, match, Text(root, "karar"), Text(root, "neden"), Text(root, "politika_surumu"));
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string? Text(JsonElement element, string property)
    {
        if (!element.TryGetProperty(property, out JsonElement value))
        {
            return null;
        }

        return value.ValueKind switch
        {
            JsonValueKind.String => value.GetString(),
            JsonValueKind.Number => value.GetRawText(),
            _ => null,
        };
    }
}

/// <summary>
/// Otomatik onaya itiraz (K-51 madde 9): editor <c>review</c> acar (koken editor, <c>onerilen = {itiraz: true, gerekce}</c>); BASKA bir editor
/// onaylarsa lemma <c>aday</c> olur (onay yolu bosalir), reddederse degismez. Karar kurali <see cref="ReviewDecisions"/> icindedir.
/// </summary>
public static class LemmaObjections
{
    /// <summary>
    /// Itiraz kaydini kurar. Turkce olmayan lemma 422 <c>inceleme-desteklenmiyor</c>; durumu <c>onayli</c> ve onay yolu <c>otomatik</c> olmayan lemma
    /// ya da zaten acik itiraz 409 <c>durum-gecisi-gecersiz</c>; gerekce zorunlu (400). Veritabani yazimi cagiranindir.
    /// </summary>
    public static Review Open(int lemmaId, XrefStatus status, LemmaReviewState lemma, string? actor, string? gerekce, bool hasOpenObjection)
    {
        string who = ReviewDecisions.RequireActor(actor);
        string reason = ReviewDecisions.RequireGerekce(gerekce);
        ReviewDecisions.RequireTurkish(lemma);
        ReviewDecisions.RequireAutoApproved(status, lemma);
        if (hasOpenObjection)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Bu lemma icin acik bir itiraz zaten var.");
        }

        return new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemmaId.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.KokEslemesi,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Editor,
            Oneren = who,
            Onceki = Snapshot(lemma),
            Onerilen = LemmaMappingPayload.ToObjectionPayload(reason),
            Gerekce = reason,
        };
    }

    /// <summary>Itiraz anindaki eslemenin kaydi (denetim izi): kok, Arapca karsilik, etimolojik isaret ve onay yolu.</summary>
    private static string Snapshot(LemmaReviewState lemma) =>
        JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            [LemmaMappingPayload.RootIdKey] = lemma.RootId,
            [LemmaMappingPayload.ArLemmaIdKey] = lemma.ArLemmaId,
            [LemmaMappingPayload.EtymologicalOnlyKey] = lemma.EtymologicalOnly,
            ["onay_yolu"] = lemma.OnayYolu,
        });
}

/// <summary>Etimolojik isaret karari: denetim izi olarak kapanmis review satiri ve lemma'ya yazilacak degerler.</summary>
public readonly record struct EtymologyMark(Review Review, LemmaMappingUpdate Update);

/// <summary>
/// <c>etimolojik_isaretle</c> eylemi (K-51 madde 9): editor, onayli bir Turkce lemmanin <c>etymological_only</c> degerini kendi karariyla
/// degistirir; otomatik onayli satirda da calisir ve onay yolunu <c>editor</c> yapar (kanit korunur).
/// </summary>
public static class LemmaEtymology
{
    /// <summary>
    /// Turkce olmayan lemma 422 <c>inceleme-desteklenmiyor</c>; durumu <c>onayli</c> olmayan ya da koku olmayan lemma 409
    /// <c>durum-gecisi-gecersiz</c>; deger degismiyorsa 400 <c>dogrulama</c>; gerekce zorunlu (400).
    /// </summary>
    public static EtymologyMark Apply(
        int lemmaId,
        XrefStatus status,
        LemmaReviewState lemma,
        bool etymologicalOnly,
        string? actor,
        string? gerekce,
        DateTime now)
    {
        string who = ReviewDecisions.RequireActor(actor);
        string reason = ReviewDecisions.RequireGerekce(gerekce);
        ReviewDecisions.RequireTurkish(lemma);
        if (status != XrefStatus.Onayli)
        {
            throw new DomainException(
                DomainErrorCodes.DurumGecisiGecersiz,
                $"Etimolojik isaret yalniz onayli lemmada degistirilir (durum: {status.ToLabel()}); aday icin Duzenle ve onayla kullanilir.");
        }

        if (lemma.RootId is null)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Kokusuz lemmada etimolojik isaret degistirilemez.");
        }

        if (lemma.EtymologicalOnly == etymologicalOnly)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Degisiklik yok: etymological_only zaten bu deger.");
        }

        string previous = JsonSerializer.Serialize(new Dictionary<string, object> { [LemmaMappingPayload.EtymologicalOnlyKey] = lemma.EtymologicalOnly });
        string proposed = JsonSerializer.Serialize(new Dictionary<string, object> { [LemmaMappingPayload.EtymologicalOnlyKey] = etymologicalOnly });
        Review review = new()
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemmaId.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.KokEslemesi,
            Eylem = ReviewActions.EtimolojikIsaretle,
            Durum = ReviewStatus.Onaylandi,
            Koken = XrefOrigin.Editor,
            Oneren = who,
            Inceleyen = who,
            IncelendiAt = now,
            Gerekce = reason,
            Onceki = previous,
            Onerilen = proposed,
        };

        // Deger editor karariyla degisti: koken editor, onay yolu editor; kanit (otomatik onayin denetim izi) oldugu gibi kalir.
        LemmaMappingUpdate update = new(lemma.RootId, lemma.ArLemmaId, etymologicalOnly, LemmaOrigins.Editor, LemmaApprovalPaths.Editor);
        return new EtymologyMark(review, update);
    }
}
