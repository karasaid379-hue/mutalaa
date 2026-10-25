using System.Text;

namespace Mutalaa.Domain.Text;

/// <summary>
/// Kendi urettigimiz metnin ilk kayit kanonikilestirmesi (Capa semasi 7, K-35 madde 7).
/// Tanzil gibi kaynaktan alinan metne UYGULANMAZ.
/// </summary>
public static class TextCanonicalizer
{
    /// <summary>
    /// Sira: (1) silinecek karakterler, (2) NFC, (3) CRLF ve CR -> LF, U+0020/U+0009 dizileri -> tek U+0020,
    /// bastan ve sondan yalniz U+0020, U+0009, U+000A kirpilir. U+00A0, U+200C, U+200D, U+2028, U+2029 ve U+0085 korunur.
    /// </summary>
    /// <exception cref="ArgumentException">Metin gecerli Unicode degilse (NFC icin).</exception>
    public static string Canonicalize(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        // 1. Silme (hepsi BMP).
        StringBuilder removed = new(text.Length);
        foreach (char c in text)
        {
            if (!IsRemoved(c))
            {
                removed.Append(c);
            }
        }

        // 2. NFC.
        string nfc = removed.ToString().Normalize(NormalizationForm.FormC);

        // 3. Satir sonu ve bosluk.
        StringBuilder sb = new(nfc.Length);
        int i = 0;
        while (i < nfc.Length)
        {
            char c = nfc[i];
            if (c == '\r')
            {
                sb.Append('\n');
                i += i + 1 < nfc.Length && nfc[i + 1] == '\n' ? 2 : 1;
            }
            else if (c == ' ' || c == '\t')
            {
                while (i < nfc.Length && (nfc[i] == ' ' || nfc[i] == '\t'))
                {
                    i++;
                }

                sb.Append(' ');
            }
            else
            {
                sb.Append(c);
                i++;
            }
        }

        // Dilin Trim() islevi U+00A0'i da keser; yalniz U+0020, U+0009, U+000A kirpilir.
        int start = 0;
        int end = sb.Length;
        while (start < end && IsTrimmed(sb[start]))
        {
            start++;
        }

        while (end > start && IsTrimmed(sb[end - 1]))
        {
            end--;
        }

        return sb.ToString(start, end - start);
    }

    private static bool IsTrimmed(char c) => c == ' ' || c == '\t' || c == '\n';

    private static bool IsRemoved(char c)
    {
        return c == (char)0xFEFF
            || c == (char)0x00AD
            || c == (char)0x200E
            || c == (char)0x200F
            || (c >= (char)0x202A && c <= (char)0x202E)
            || (c >= (char)0x2066 && c <= (char)0x2069)
            || c == (char)0x061C;
    }
}
