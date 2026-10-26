namespace Mutalaa.Domain.Reviews;

/// <summary>Inceleme durumu (JSON inceleme_durumu). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum ReviewStatus
{
    Acik = 0,
    Onaylandi = 1,
    Reddedildi = 2,
    GeriAlindi = 3,
}

/// <summary>ReviewStatus icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class ReviewStatusLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this ReviewStatus value) => value switch
    {
        ReviewStatus.Acik => "acik",
        ReviewStatus.Onaylandi => "onaylandi",
        ReviewStatus.Reddedildi => "reddedildi",
        ReviewStatus.GeriAlindi => "geri_alindi",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out ReviewStatus value)
    {
        switch (label)
        {
            case "acik":
                value = ReviewStatus.Acik;
                return true;
            case "onaylandi":
                value = ReviewStatus.Onaylandi;
                return true;
            case "reddedildi":
                value = ReviewStatus.Reddedildi;
                return true;
            case "geri_alindi":
                value = ReviewStatus.GeriAlindi;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
