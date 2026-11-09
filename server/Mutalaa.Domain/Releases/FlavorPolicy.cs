namespace Mutalaa.Domain.Releases;

/// <summary>
/// Derleme turune bagli saf kurallar. Tanimsiz ya da ayristirilamayan derleme turu en kisitlayici tur (public) sayilir
/// (Backend API 7 A13 notu: TryParseLabel basarisizken out degeri Dev'dir; kapi yalniz bool'a guvenir).
/// </summary>
public static class FlavorPolicy
{
    /// <summary>P-12: bu onekle baslayan kaynak public'e hic girmez.</summary>
    public const string TestPrefix = "test-";

    /// <summary>Etiketi ayristirir; bool basarisizsa Public doner. out degerine bakilmaz.</summary>
    public static BuildFlavor ParseOrMostRestrictive(string? label)
    {
        bool parsed = BuildFlavorLabels.TryParseLabel(label, out BuildFlavor value);
        return parsed ? Normalize(value) : BuildFlavor.Public;
    }

    /// <summary>Tanimsiz sayisal degeri Public yapar.</summary>
    public static BuildFlavor Normalize(BuildFlavor flavor) => flavor switch
    {
        BuildFlavor.Dev => BuildFlavor.Dev,
        BuildFlavor.Internal => BuildFlavor.Internal,
        _ => BuildFlavor.Public,
    };

    /// <summary>Slug "test-" ile baslar (buyuk-kucuk harf gozetilmez: slug gramerinde buyuk harf yoktur, kacak olmasin).</summary>
    public static bool IsTestSource(string slug)
    {
        ArgumentNullException.ThrowIfNull(slug);
        return slug.StartsWith(TestPrefix, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>Uctan uca fikstur kaynaklari (internal'a girebilen tek test- kaynaklari). Buyuk-kucuk harf duyarli.</summary>
    public static bool IsEndToEndFixture(string slug) =>
        string.Equals(slug, "test-kucuk", StringComparison.Ordinal) ||
        string.Equals(slug, "test-ses", StringComparison.Ordinal);

    /// <summary>P-12: kaynagin bu derlemeye girip giremeyecegi (kaynak kaydi denetimi ayridir: P-01).</summary>
    public static bool AllowsSource(BuildFlavor flavor, string slug)
    {
        if (!IsTestSource(slug))
        {
            return true;
        }

        return Normalize(flavor) switch
        {
            BuildFlavor.Dev => true,
            BuildFlavor.Internal => IsEndToEndFixture(slug),
            _ => false,
        };
    }

    /// <summary>P-08 ve P-10: onaysiz birimler yalniz dev ve internal'a girer ("dogrulanmamis" isaretiyle).</summary>
    public static bool AllowsUnapprovedUnits(BuildFlavor flavor) => Normalize(flavor) != BuildFlavor.Public;
}
