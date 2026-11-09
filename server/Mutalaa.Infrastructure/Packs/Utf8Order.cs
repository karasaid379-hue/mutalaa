namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// UTF-8 bayt sirasi (PostgreSQL COLLATE "C" ve ContentDigest ile ayni). UTF-8 bayt sirasi Unicode kod noktasi sirasidir;
/// StringComparer.Ordinal UTF-16 birim sirasidir ve vekil ciftlerde (U+10000 ustu) ayrilir. Burada vekil cifti
/// BMP ust araligindan (U+E000...U+FFFF) sonraya alinir; bellek ayirmaz. Gecerli (eslesmis vekilli) dizgiler icindir.
/// </summary>
public sealed class Utf8Order : IComparer<string?>
{
    public static Utf8Order Instance { get; } = new();

    public static int Compare(ReadOnlySpan<char> x, ReadOnlySpan<char> y)
    {
        int n = Math.Min(x.Length, y.Length);
        for (int i = 0; i < n; i++)
        {
            char a = x[i];
            char b = y[i];
            if (a != b)
            {
                return Fix(a).CompareTo(Fix(b));
            }
        }

        return x.Length.CompareTo(y.Length);
    }

    /// <summary>Null en kucuktur (bos dizgiden once).</summary>
    public int Compare(string? x, string? y)
    {
        if (ReferenceEquals(x, y))
        {
            return 0;
        }

        if (x is null)
        {
            return -1;
        }

        if (y is null)
        {
            return 1;
        }

        return Compare(x.AsSpan(), y.AsSpan());
    }

    // Vekil birimleri (D800-DFFF) kod noktasi sirasinda E000-FFFF'ten sonra gelir.
    private static int Fix(char c) => c >= '' ? c - 0x800 : c >= '\uD800' ? c + 0x2000 : c;
}
