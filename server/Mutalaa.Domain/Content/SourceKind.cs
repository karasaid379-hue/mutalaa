namespace Mutalaa.Domain.Content;

/// <summary>Kaynak turu (JSON source_kind). Bildirim sirasi packages/content-schema/enums.json sirasiyla aynidir; sayisal degerler bu siradir.</summary>
public enum SourceKind
{
    KuranMetni = 0,
    Meal = 1,
    Tefsir = 2,
    Hadis = 3,
    HadisCeviri = 4,
    Risale = 5,
    Kitap = 6,
    Morfoloji = 7,
    KelimeAnlami = 8,
    Sozluk = 9,
    MushafDuzeni = 10,
    MushafGorseli = 11,
    Font = 12,
    Baski = 13,
    Ses = 14,
    Zamanlama = 15,
    BaglantiVerisi = 16,
}

/// <summary>SourceKind icin ortak enum JSON etiketi eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class SourceKindLabels
{
    /// <summary>Degerin ortak etiketini (snake_case) dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToLabel(this SourceKind value) => value switch
    {
        SourceKind.KuranMetni => "kuran_metni",
        SourceKind.Meal => "meal",
        SourceKind.Tefsir => "tefsir",
        SourceKind.Hadis => "hadis",
        SourceKind.HadisCeviri => "hadis_ceviri",
        SourceKind.Risale => "risale",
        SourceKind.Kitap => "kitap",
        SourceKind.Morfoloji => "morfoloji",
        SourceKind.KelimeAnlami => "kelime_anlami",
        SourceKind.Sozluk => "sozluk",
        SourceKind.MushafDuzeni => "mushaf_duzeni",
        SourceKind.MushafGorseli => "mushaf_gorseli",
        SourceKind.Font => "font",
        SourceKind.Baski => "baski",
        SourceKind.Ses => "ses",
        SourceKind.Zamanlama => "zamanlama",
        SourceKind.BaglantiVerisi => "baglanti_verisi",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out SourceKind value)
    {
        switch (label)
        {
            case "kuran_metni":
                value = SourceKind.KuranMetni;
                return true;
            case "meal":
                value = SourceKind.Meal;
                return true;
            case "tefsir":
                value = SourceKind.Tefsir;
                return true;
            case "hadis":
                value = SourceKind.Hadis;
                return true;
            case "hadis_ceviri":
                value = SourceKind.HadisCeviri;
                return true;
            case "risale":
                value = SourceKind.Risale;
                return true;
            case "kitap":
                value = SourceKind.Kitap;
                return true;
            case "morfoloji":
                value = SourceKind.Morfoloji;
                return true;
            case "kelime_anlami":
                value = SourceKind.KelimeAnlami;
                return true;
            case "sozluk":
                value = SourceKind.Sozluk;
                return true;
            case "mushaf_duzeni":
                value = SourceKind.MushafDuzeni;
                return true;
            case "mushaf_gorseli":
                value = SourceKind.MushafGorseli;
                return true;
            case "font":
                value = SourceKind.Font;
                return true;
            case "baski":
                value = SourceKind.Baski;
                return true;
            case "ses":
                value = SourceKind.Ses;
                return true;
            case "zamanlama":
                value = SourceKind.Zamanlama;
                return true;
            case "baglanti_verisi":
                value = SourceKind.BaglantiVerisi;
                return true;
            default:
                value = default;
                return false;
        }
    }
}
