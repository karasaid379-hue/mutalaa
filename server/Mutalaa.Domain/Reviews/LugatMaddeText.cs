using System.Globalization;
using System.Text.Json;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// <c>lugat_madde.tanim_tr</c> editor degeri (K-52 madde 10, K-50 madde 6 deseni): editorun yazdigi ya da degistirdigi tanim kendi
/// urettigimiz metindir, ilk kayitta kanonikilestirilir (NFC). Lugat kaynagindan gelen tanim (<c>origin = 'kaynak'</c>) bayt bayt
/// saklanir ve burada islenmez. Saf islevler; hata <see cref="DomainException"/> (<c>dogrulama</c>).
/// </summary>
public static class LugatMaddeText
{
    /// <summary>En cok kod noktasi (kanonik metin uzerinden).</summary>
    public const int MaxLength = 2000;

    /// <summary><c>lugat_madde.origin</c>: hattin actigi aday.</summary>
    public const string HatOrigin = "hat";

    /// <summary><c>lugat_madde.origin</c>: lugat kaynagindan gelen tanim (bayt bayt; K-52 madde 10 ve 14).</summary>
    public const string KaynakOrigin = "kaynak";

    /// <summary><c>lugat_madde.origin</c>: editorun yazdigi ya da degistirdigi tanim.</summary>
    public const string EditorOrigin = "editor";

    /// <summary><c>kaynaklar</c> jsonb'sinde toplam siklik anahtari (int). Kuyruk siralamasi bunu okur; tek yerde tanimlidir.</summary>
    public const string SiklikKey = "siklik";

    /// <summary>Kanonik tanim: bos, yalniz bosluk, gecersiz Unicode ya da 2000 kod noktasindan uzun deger 400.</summary>
    public static string Normalize(string? value, string name)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bos olamaz.");
        }

        string canonical;
        try
        {
            canonical = TextCanonicalizer.Canonicalize(value);
        }
        catch (ArgumentException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli Unicode degil.", e);
        }

        if (string.IsNullOrWhiteSpace(canonical))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bos olamaz.");
        }

        if (CodePointOffsets.CodePointCount(canonical) > MaxLength)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} en cok {MaxLength.ToString(CultureInfo.InvariantCulture)} karakter olabilir.");
        }

        return canonical;
    }

    /// <summary>Review.duzenlenen jsonb'si: <c>{"tanim_tr": ...}</c> (kanonik deger).</summary>
    public static string ToPayload(string canonical) =>
        JsonSerializer.Serialize(new Dictionary<string, string> { ["tanim_tr"] = canonical });

    /// <summary>
    /// <c>content_hash</c> = <c>sha256(basliksoz + "\n" + (tanim_tr ?? ""))</c>: basliksoz satir sonu tasimaz, bu yuzden ayrim belirsiz degildir.
    /// Hat adayi (tanim bos) ve onayli madde ayni islevi kullanir; tanim eklenince ozet degisir.
    /// </summary>
    public static string ComputeHash(string basliksoz, string? tanimTr)
    {
        ArgumentNullException.ThrowIfNull(basliksoz);
        return ContentHash.Compute(basliksoz + "\n" + (tanimTr ?? string.Empty));
    }

    /// <summary>Surum ('1', '2' ...) bir artar; ASCII rakamli, isaretsiz tamsayi olmayan surum 400.</summary>
    public static string NextVersion(string version) => LemmaGlossText.NextVersion(version);
}
