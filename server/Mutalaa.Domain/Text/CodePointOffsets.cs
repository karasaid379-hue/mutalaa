using System.Globalization;
using System.Text;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Text;

/// <summary>
/// Kod noktasi ve UTF-16 ofsetleri arasinda donusum, Mn hizalamasi (Capa semasi 8, K-35 madde 8).
/// Kod noktasi sayimi <see cref="Rune"/> ile yapilir; tek basina vekil bir kod noktasi sayilir.
/// </summary>
public static class CodePointOffsets
{
    /// <summary>Metindeki kod noktasi sayisi.</summary>
    public static int CodePointCount(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        int count = 0;
        foreach (Rune unused in text.EnumerateRunes())
        {
            count++;
        }

        return count;
    }

    /// <summary>Kod noktasi ofsetini UTF-16 ofsetine cevirir.</summary>
    /// <exception cref="ArgumentOutOfRangeException"><paramref name="cp"/> [0, kod noktasi sayisi] disindaysa.</exception>
    public static int CpToUtf16(string text, int cp)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (cp < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(cp));
        }

        int seen = 0;
        int utf16 = 0;
        foreach (Rune rune in text.EnumerateRunes())
        {
            if (seen == cp)
            {
                return utf16;
            }

            seen++;
            utf16 += rune.Utf16SequenceLength;
        }

        if (seen == cp)
        {
            return utf16;
        }

        throw new ArgumentOutOfRangeException(nameof(cp));
    }

    /// <summary>UTF-16 ofsetini kod noktasi ofsetine cevirir.</summary>
    /// <exception cref="ArgumentOutOfRangeException">
    /// <paramref name="index"/> [0, UTF-16 uzunlugu] disindaysa ya da bir vekil ciftin ortasina dusuyorsa.
    /// </exception>
    public static int Utf16ToCp(string text, int index)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (index < 0 || index > text.Length)
        {
            throw new ArgumentOutOfRangeException(nameof(index));
        }

        if (index > 0 && index < text.Length && char.IsHighSurrogate(text[index - 1]) && char.IsLowSurrogate(text[index]))
        {
            throw new ArgumentOutOfRangeException(nameof(index), "Vekil ciftin ortasi.");
        }

        int count = 0;
        int utf16 = 0;
        foreach (Rune rune in text.EnumerateRunes())
        {
            if (utf16 >= index)
            {
                break;
            }

            utf16 += rune.Utf16SequenceLength;
            count++;
        }

        return count;
    }

    /// <summary>
    /// Sinir hizalama: baslangic bir Mn uzerine duserse Mn olmayana (ya da 0'a) dek geriye, bitis bir Mn onune
    /// duserse Mn olmayana (ya da sona) dek ileriye kayar. Araliklar kod noktasidir.
    /// </summary>
    /// <exception cref="ArgumentOutOfRangeException">0 &lt;= baslangic &lt;= bitis &lt;= kod noktasi sayisi degilse.</exception>
    public static AnchorSpan SnapSpan(string text, AnchorSpan span)
    {
        ArgumentNullException.ThrowIfNull(text);
        List<Rune> runes = [.. text.EnumerateRunes()];
        if (span.Start < 0 || span.Start > span.End || span.End > runes.Count)
        {
            throw new ArgumentOutOfRangeException(nameof(span));
        }

        int start = span.Start;
        int end = span.End;
        while (start > 0 && start < runes.Count && IsMn(runes[start]))
        {
            start--;
        }

        while (end < runes.Count && IsMn(runes[end]))
        {
            end++;
        }

        return new AnchorSpan(start, end);
    }

    private static bool IsMn(Rune rune) => Rune.GetUnicodeCategory(rune) == UnicodeCategory.NonSpacingMark;
}
