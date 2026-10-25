namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Capa ayristirma hata kodlari (Capa semasi 2, hata onceligi K-35 madde 1).
/// </summary>
public enum AnchorErrorCode
{
    /// <summary>BICIM: karakter kumesi ya da desen uymuyor.</summary>
    Bicim,

    /// <summary>SURE_ARALIGI: sure 1-114 disinda.</summary>
    SureAraligi,

    /// <summary>AYET_ARALIGI: ayet surenin ayet sayisini asiyor.</summary>
    AyetAraligi,

    /// <summary>TERS_ARALIK: baslangic bitisten buyuk (ya da yari acik aralikta bosluk).</summary>
    TersAralik,

    /// <summary>KANONIK_DEGIL: tek kelime ya da tek ayet aralik olarak yazilmis.</summary>
    KanonikDegil,

    /// <summary>UZUNLUK: toplam, slug, derinlik ya da sayi siniri asildi.</summary>
    Uzunluk,
}
