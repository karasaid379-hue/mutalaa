namespace Mutalaa.Api.Problems;

/// <summary>
/// Hata kodu tablosu (Backend API 6): tek yerde. ProblemDetails <c>type</c> alani <c>urn:mutalaa:problem:{kod}</c> olur,
/// kod ayrica <c>kod</c> uzantisi olarak govdede de gider.
/// </summary>
public static class ProblemCodes
{
    public const string TypePrefix = "urn:mutalaa:problem:";

    /// <summary>Uc kendi kodunu ProblemDetails.Extensions icinde bu anahtarla verir.</summary>
    public const string ExtensionKey = "kod";

    public const string Dogrulama = "dogrulama";
    public const string OturumAcilamadi = "oturum-acilamadi";
    public const string YetkiYok = "yetki-yok";
    public const string Bulunamadi = "bulunamadi";
    public const string YontemDesteklenmiyor = "yontem-desteklenmiyor";
    public const string DurumGecisiGecersiz = "durum-gecisi-gecersiz";
    public const string Cakisma = "cakisma";
    public const string SurumUyusmazligi = "surum-uyusmazligi";
    public const string SurumGerekli = "surum-gerekli";
    public const string Hata = "hata";
    public const string SunucuHatasi = "sunucu-hatasi";

    // Yayin uclari (K-48 madde 7 ve 9).
    public const string YayinSuruyor = "yayin-suruyor";
    public const string KaliteKapisi = "kalite-kapisi";
    public const string OncekiYayinBozuk = "onceki-yayin-bozuk";
    public const string DepoErisilemiyor = "depo-erisilemiyor";

    /// <summary>HTTP durumundan varsayilan kod; tabloda olmayan 4xx "dogrulama", 5xx "sunucu-hatasi" olur.</summary>
    public static string ForStatus(int status) => status switch
    {
        StatusCodes.Status400BadRequest => Dogrulama,
        StatusCodes.Status401Unauthorized => OturumAcilamadi,
        StatusCodes.Status403Forbidden => YetkiYok,
        StatusCodes.Status404NotFound => Bulunamadi,
        StatusCodes.Status405MethodNotAllowed => YontemDesteklenmiyor,
        StatusCodes.Status409Conflict => DurumGecisiGecersiz,
        StatusCodes.Status412PreconditionFailed => SurumUyusmazligi,
        StatusCodes.Status422UnprocessableEntity => Hata,
        StatusCodes.Status428PreconditionRequired => SurumGerekli,
        >= 500 => SunucuHatasi,
        _ => Dogrulama,
    };

    /// <summary>Durumun Turkce basligi (uc <c>detail</c> ile ayrintilar); tabloda olmayan durumda null.</summary>
    public static string? TitleForStatus(int status) => status switch
    {
        StatusCodes.Status400BadRequest => "Geçersiz istek",
        StatusCodes.Status401Unauthorized => "Oturum açılamadı",
        StatusCodes.Status403Forbidden => "Yetki yok",
        StatusCodes.Status404NotFound => "Bulunamadı",
        StatusCodes.Status405MethodNotAllowed => "Yöntem desteklenmiyor",
        StatusCodes.Status409Conflict => "Çakışma",
        StatusCodes.Status412PreconditionFailed => "Sürüm uyuşmazlığı",
        StatusCodes.Status422UnprocessableEntity => "İşlenemeyen içerik",
        StatusCodes.Status428PreconditionRequired => "Sürüm gerekli",
        StatusCodes.Status500InternalServerError => "Sunucu hatası",
        StatusCodes.Status503ServiceUnavailable => "Hizmet kullanılamıyor",
        _ => null,
    };

    public static string TypeUri(string code) => TypePrefix + code;
}
