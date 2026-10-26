namespace Mutalaa.Domain.Links;

/// <summary>Baglanti turu. Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum XrefType
{
    Atif = 0,
    Iktibas = 1,
    Ima = 2,
    Kok = 3,
    Lemma = 4,
    Konu = 5,
    BenzerAyet = 6,
    Anlamsal = 7,
}

/// <summary>XrefType icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class XrefTypeLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this XrefType value) => value switch
    {
        XrefType.Atif => "atif",
        XrefType.Iktibas => "iktibas",
        XrefType.Ima => "ima",
        XrefType.Kok => "kok",
        XrefType.Lemma => "lemma",
        XrefType.Konu => "konu",
        XrefType.BenzerAyet => "benzer_ayet",
        XrefType.Anlamsal => "anlamsal",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out XrefType value)
    {
        switch (label)
        {
            case "atif":
                value = XrefType.Atif;
                return true;
            case "iktibas":
                value = XrefType.Iktibas;
                return true;
            case "ima":
                value = XrefType.Ima;
                return true;
            case "kok":
                value = XrefType.Kok;
                return true;
            case "lemma":
                value = XrefType.Lemma;
                return true;
            case "konu":
                value = XrefType.Konu;
                return true;
            case "benzer_ayet":
                value = XrefType.BenzerAyet;
                return true;
            case "anlamsal":
                value = XrefType.Anlamsal;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
