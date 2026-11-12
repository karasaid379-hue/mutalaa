using System.Globalization;
using System.Text.Json;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// <c>lemma_gloss.anlam_kisa</c> editor degeri (K-50 madde 6): kendi urettigimiz metindir, ilk kayitta kanonikilestirilir (NFC).
/// Saf islevler; hata <see cref="DomainException"/> (<c>dogrulama</c>).
/// </summary>
public static class LemmaGlossText
{
    /// <summary>En cok kod noktasi (kanonik metin uzerinden).</summary>
    public const int MaxLength = 200;

    /// <summary><c>lemma_gloss.origin</c>: editorun yazdigi ya da degistirdigi anlam.</summary>
    public const string EditorOrigin = "editor";

    /// <summary>Kanonik anlam: bos, yalniz bosluk, gecersiz Unicode ya da 200 kod noktasindan uzun deger 400.</summary>
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
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} en cok {MaxLength} karakter olabilir.");
        }

        return canonical;
    }

    /// <summary>Review.duzenlenen jsonb'si: <c>{"anlam_kisa": ...}</c> (kanonik deger).</summary>
    public static string ToPayload(string canonical) =>
        JsonSerializer.Serialize(new Dictionary<string, string> { ["anlam_kisa"] = canonical });

    /// <summary>Surum (<c>"1"</c>, <c>"2"</c> ...) bir artar; ASCII rakamli, isaretsiz tamsayi olmayan surum 400.</summary>
    public static string NextVersion(string version)
    {
        if (!int.TryParse(version, NumberStyles.None, CultureInfo.InvariantCulture, out int current)
            || current == int.MaxValue)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "lemma_gloss.version tamsayi degil; artirilamaz.");
        }

        return (current + 1).ToString(CultureInfo.InvariantCulture);
    }
}
