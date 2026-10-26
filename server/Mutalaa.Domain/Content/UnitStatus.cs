namespace Mutalaa.Domain.Content;

/// <summary>Birim (capa) durumu (JSON unit_status). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum UnitStatus
{
    Etkin = 0,
    KullanimDisi = 1,
}

/// <summary>UnitStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class UnitStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this UnitStatus value) => value switch
    {
        UnitStatus.Etkin => "etkin",
        UnitStatus.KullanimDisi => "kullanim_disi",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out UnitStatus value)
    {
        switch (label)
        {
            case "etkin":
                value = UnitStatus.Etkin;
                return true;
            case "kullanim_disi":
                value = UnitStatus.KullanimDisi;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
