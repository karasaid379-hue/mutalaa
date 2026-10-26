namespace Mutalaa.Domain.Links;

/// <summary>Baglanti durumu. Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum XrefStatus
{
    Aday = 0,
    Onayli = 1,
    Red = 2,
}

/// <summary>XrefStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class XrefStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this XrefStatus value) => value switch
    {
        XrefStatus.Aday => "aday",
        XrefStatus.Onayli => "onayli",
        XrefStatus.Red => "red",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out XrefStatus value)
    {
        switch (label)
        {
            case "aday":
                value = XrefStatus.Aday;
                return true;
            case "onayli":
                value = XrefStatus.Onayli;
                return true;
            case "red":
                value = XrefStatus.Red;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
