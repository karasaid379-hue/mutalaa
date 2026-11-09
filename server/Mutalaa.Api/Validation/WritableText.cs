using System.Buffers;
using System.Globalization;
using System.Text;

namespace Mutalaa.Api.Validation;

/// <summary>
/// Kullanici girdisi olan metnin PostgreSQL'e yazilabilir ya da sorguya girebilir olmasi: NUL (U+0000) ve eslesmemis vekil karakter
/// (UTF-16 gecersiz) text sutunlarina ve parametrelerine gidince veritabani hatasi (500) verir; girdi sinirinda 400 <c>dogrulama</c>
/// ile reddedilir. Saf islevlerdir; kulturden bagimsizdir.
/// </summary>
public static class WritableText
{
    /// <summary>
    /// Metin yazilabilirse (null ya da bos dahil) true ve Unicode kod noktasi sayisi; NUL ya da eslesmemis vekil varsa false.
    /// </summary>
    public static bool TryCountCodePoints(string? text, out int codePoints)
    {
        codePoints = 0;
        if (string.IsNullOrEmpty(text))
        {
            return true;
        }

        int count = 0;
        ReadOnlySpan<char> rest = text;
        while (!rest.IsEmpty)
        {
            OperationStatus status = Rune.DecodeFromUtf16(rest, out Rune rune, out int consumed);
            if (status != OperationStatus.Done || rune.Value == 0)
            {
                codePoints = 0;
                return false;
            }

            count++;
            rest = rest[consumed..];
        }

        codePoints = count;
        return true;
    }

    public static bool IsWritable(string? text) => TryCountCodePoints(text, out _);

    /// <summary>Alan yazilabilir degilse hatalara <paramref name="field"/> altinda ileti ekler; yazilabilirse hicbir sey yapmaz.</summary>
    /// <returns>Alan yazilabilir mi.</returns>
    public static bool Check(IDictionary<string, string[]> errors, string field, string? value)
    {
        ArgumentNullException.ThrowIfNull(errors);
        if (IsWritable(value))
        {
            return true;
        }

        errors[field] = [Message(field)];
        return false;
    }

    public static string Message(string field) =>
        string.Create(CultureInfo.InvariantCulture, $"{field} alanı geçersiz karakter içeriyor (NUL ya da eşleşmemiş vekil karakter).");
}
