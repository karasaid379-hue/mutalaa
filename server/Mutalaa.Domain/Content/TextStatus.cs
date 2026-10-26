namespace Mutalaa.Domain.Content;

/// <summary>Metin durumu (JSON metin_durumu). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum TextStatus
{
    Taslak = 0,
    Incelemede = 1,
    Onayli = 2,
}

/// <summary>TextStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class TextStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this TextStatus value) => value switch
    {
        TextStatus.Taslak => "taslak",
        TextStatus.Incelemede => "incelemede",
        TextStatus.Onayli => "onayli",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out TextStatus value)
    {
        switch (label)
        {
            case "taslak":
                value = TextStatus.Taslak;
                return true;
            case "incelemede":
                value = TextStatus.Incelemede;
                return true;
            case "onayli":
                value = TextStatus.Onayli;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
