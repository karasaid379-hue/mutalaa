namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.source satiri (Editoryal veritabani 3): betimleyici kaynak kaydi ve atif (K-42 madde 4).
/// jsonb sutunlari ham JSON dizgisidir, zaman damgalari UTC'dir.
/// </summary>
public sealed class Source
{
    /// <summary>Kaynak kaydindaki kimlik (pipeline/sources/{slug}.toml; birincil anahtar).</summary>
    public required string Slug { get; set; }

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required SourceKind Tur { get; set; }

    public required string Baslik { get; set; }

    public string? Yazar { get; set; }

    public required string Surum { get; set; }

    public string? Provider { get; set; }

    public string? KaynakUrl { get; set; }

    public DateOnly? AlinmaTarihi { get; set; }

    public string? DosyaSha256 { get; set; }

    /// <summary>jsonb.</summary>
    public string? BaskiBilgisi { get; set; }

    public required string AtifMetni { get; set; }

    public string? AtifUrl { get; set; }

    public string? NoticeText { get; set; }

    public string? Notlar { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime UpdatedAt { get; set; }
}
