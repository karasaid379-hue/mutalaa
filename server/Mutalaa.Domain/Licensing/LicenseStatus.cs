namespace Mutalaa.Domain.Licensing;

/// <summary>Lisans durumu (K-06); en kisitlayici sagdadir. Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum LicenseStatus
{
    Serbest = 0,
    Bekliyor = 1,
    IcKullanim = 2,
    Kapali = 3,
}

/// <summary>LicenseStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class LicenseStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this LicenseStatus value) => value switch
    {
        LicenseStatus.Serbest => "serbest",
        LicenseStatus.Bekliyor => "bekliyor",
        LicenseStatus.IcKullanim => "ic_kullanim",
        LicenseStatus.Kapali => "kapali",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out LicenseStatus value)
    {
        switch (label)
        {
            case "serbest":
                value = LicenseStatus.Serbest;
                return true;
            case "bekliyor":
                value = LicenseStatus.Bekliyor;
                return true;
            case "ic_kullanim":
                value = LicenseStatus.IcKullanim;
                return true;
            case "kapali":
                value = LicenseStatus.Kapali;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
