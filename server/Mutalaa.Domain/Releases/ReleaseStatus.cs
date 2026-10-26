namespace Mutalaa.Domain.Releases;

/// <summary>Yayin (surum) durumu (JSON surum_durumu). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum ReleaseStatus
{
    Hazirlaniyor = 0,
    Dogrulandi = 1,
    Yayinlandi = 2,
    Basarisiz = 3,
    GeriCekildi = 4,
}

/// <summary>ReleaseStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class ReleaseStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this ReleaseStatus value) => value switch
    {
        ReleaseStatus.Hazirlaniyor => "hazirlaniyor",
        ReleaseStatus.Dogrulandi => "dogrulandi",
        ReleaseStatus.Yayinlandi => "yayinlandi",
        ReleaseStatus.Basarisiz => "basarisiz",
        ReleaseStatus.GeriCekildi => "geri_cekildi",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out ReleaseStatus value)
    {
        switch (label)
        {
            case "hazirlaniyor":
                value = ReleaseStatus.Hazirlaniyor;
                return true;
            case "dogrulandi":
                value = ReleaseStatus.Dogrulandi;
                return true;
            case "yayinlandi":
                value = ReleaseStatus.Yayinlandi;
                return true;
            case "basarisiz":
                value = ReleaseStatus.Basarisiz;
                return true;
            case "geri_cekildi":
                value = ReleaseStatus.GeriCekildi;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
