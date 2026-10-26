using Mutalaa.Domain.Licensing;

namespace Mutalaa.Domain.Releases;

/// <summary>icerik.release satiri (Editoryal veritabani 10). Yayimlanmis surum degismez.</summary>
public sealed class Release
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public int Id { get; set; }

    public required string Surum { get; set; }

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required BuildFlavor Derleme { get; set; }

    public ReleaseStatus Durum { get; set; } = ReleaseStatus.Hazirlaniyor;

    /// <summary>jsonb: imzali manifest.json.</summary>
    public string? Manifest { get; set; }

    /// <summary>jsonb.</summary>
    public string KapiRaporu { get; set; } = "{}";

    /// <summary>jsonb.</summary>
    public string KaynakDurumu { get; set; } = "{}";

    /// <summary>jsonb.</summary>
    public string Ozetler { get; set; } = "{}";

    public required string DataVersion { get; set; }

    public required string Olusturan { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC.</summary>
    public DateTime? YayinlandiAt { get; set; }
}
