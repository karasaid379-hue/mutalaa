namespace Mutalaa.Domain;

/// <summary>Backend API hata kodlari (RFC 9457 ProblemDetails kodu). Beklenen HTTP durumu her kodun yanindadir; esleme Api'dedir.</summary>
public static class DomainErrorCodes
{
    /// <summary>400: girdi gecersiz (bos ya da cok uzun gerekce, bozuk anahtar, bozuk JSON).</summary>
    public const string Dogrulama = "dogrulama";

    /// <summary>409: kayit bu durumda bu gecisi kabul etmez.</summary>
    public const string DurumGecisiGecersiz = "durum-gecisi-gecersiz";

    /// <summary>422: ayet (Tanzil) metni degistirilemez.</summary>
    public const string DegistirilemezMetin = "degistirilemez-metin";

    /// <summary>422: hedef tablo ya da alan icin inceleme akisi desteklenmiyor.</summary>
    public const string IncelemeDesteklenmiyor = "inceleme-desteklenmiyor";

    /// <summary>412: iyimser eszamanlilik (xmin) uyusmazligi (If-Match tutmuyor; K-48).</summary>
    public const string SurumUyusmazligi = "surum-uyusmazligi";

    /// <summary>404: kayit yok.</summary>
    public const string Bulunamadi = "bulunamadi";

    /// <summary>422: baglanti adayi toplu onaya uygun degil (K-13 politika 1; yalniz "toplu" sinifi toplu onaylanir).</summary>
    public const string TopluUygunDegil = "toplu-uygun-degil";
}
