namespace Mutalaa.Domain.Content;

/// <summary>Birim turu (JSON unit_kind). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum UnitKind
{
    Ayet = 0,
    Meal = 1,
    Tefsir = 2,
    Risale = 3,
    Hadis = 4,
    HadisCeviri = 5,
    Kitap = 6,
}

/// <summary>UnitKind icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class UnitKindLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this UnitKind value) => value switch
    {
        UnitKind.Ayet => "ayet",
        UnitKind.Meal => "meal",
        UnitKind.Tefsir => "tefsir",
        UnitKind.Risale => "risale",
        UnitKind.Hadis => "hadis",
        UnitKind.HadisCeviri => "hadis_ceviri",
        UnitKind.Kitap => "kitap",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out UnitKind value)
    {
        switch (label)
        {
            case "ayet":
                value = UnitKind.Ayet;
                return true;
            case "meal":
                value = UnitKind.Meal;
                return true;
            case "tefsir":
                value = UnitKind.Tefsir;
                return true;
            case "risale":
                value = UnitKind.Risale;
                return true;
            case "hadis":
                value = UnitKind.Hadis;
                return true;
            case "hadis_ceviri":
                value = UnitKind.HadisCeviri;
                return true;
            case "kitap":
                value = UnitKind.Kitap;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
