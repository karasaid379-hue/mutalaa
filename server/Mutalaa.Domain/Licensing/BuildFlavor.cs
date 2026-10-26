namespace Mutalaa.Domain.Licensing;

/// <summary>Derleme turu (JSON derleme_turu). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum BuildFlavor
{
    Dev = 0,
    Internal = 1,
    Public = 2,
}

/// <summary>BuildFlavor icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class BuildFlavorLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this BuildFlavor value) => value switch
    {
        BuildFlavor.Dev => "dev",
        BuildFlavor.Internal => "internal",
        BuildFlavor.Public => "public",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out BuildFlavor value)
    {
        switch (label)
        {
            case "dev":
                value = BuildFlavor.Dev;
                return true;
            case "internal":
                value = BuildFlavor.Internal;
                return true;
            case "public":
                value = BuildFlavor.Public;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
