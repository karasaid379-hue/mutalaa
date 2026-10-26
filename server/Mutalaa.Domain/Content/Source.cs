using Mutalaa.Domain.Licensing;

namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.source satiri (Editoryal veritabani 3). Baslangic degerleri veritabani varsayilaniyla aynidir;
/// jsonb sutunlari ham JSON dizgisidir, zaman damgalari UTC'dir.
/// </summary>
public sealed class Source
{
    /// <summary>Lisans defterindeki kimlik (birincil anahtar).</summary>
    public required string Slug { get; set; }

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required SourceKind Tur { get; set; }

    public required string Baslik { get; set; }

    public string? Yazar { get; set; }

    public short? YazarVefatYili { get; set; }

    public required string Surum { get; set; }

    public string? Provider { get; set; }

    public string? KaynakUrl { get; set; }

    public DateOnly? AlinmaTarihi { get; set; }

    public string? DosyaSha256 { get; set; }

    /// <summary>jsonb.</summary>
    public string? BaskiBilgisi { get; set; }

    public required string LicenseName { get; set; }

    public string? LicenseUrl { get; set; }

    public LicenseStatus LicenseStatus { get; set; } = LicenseStatus.Bekliyor;

    public string? LisansKopyasi { get; set; }

    public string? LisansSha256 { get; set; }

    public DateOnly? KamuMaliTarihi { get; set; }

    /// <summary>jsonb.</summary>
    public string Kisitlar { get; set; } = "{}";

    public bool EmbedOk { get; set; }

    public bool KurulGerekli { get; set; }

    /// <summary>jsonb: {"onay_no","onayli_surum"}.</summary>
    public string? KurulOnay { get; set; }

    public DateOnly? KurulOnayTarihi { get; set; }

    public string? KurulOnayOzeti { get; set; }

    public required string AtifMetni { get; set; }

    public string? AtifUrl { get; set; }

    public string? NoticeText { get; set; }

    public DateOnly? YenidenKontrol { get; set; }

    public string? Notlar { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime UpdatedAt { get; set; }
}
