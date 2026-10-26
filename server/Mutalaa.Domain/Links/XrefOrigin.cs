namespace Mutalaa.Domain.Links;

/// <summary>Baglanti kaynagi. Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum XrefOrigin
{
    Hat = 0,
    Editor = 1,
    KullaniciOyu = 2,
}

/// <summary>XrefOrigin icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class XrefOriginLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this XrefOrigin value) => value switch
    {
        XrefOrigin.Hat => "hat",
        XrefOrigin.Editor => "editor",
        XrefOrigin.KullaniciOyu => "kullanici_oyu",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out XrefOrigin value)
    {
        switch (label)
        {
            case "hat":
                value = XrefOrigin.Hat;
                return true;
            case "editor":
                value = XrefOrigin.Editor;
                return true;
            case "kullanici_oyu":
                value = XrefOrigin.KullaniciOyu;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
