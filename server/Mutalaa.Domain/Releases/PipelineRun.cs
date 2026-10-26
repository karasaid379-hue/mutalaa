namespace Mutalaa.Domain.Releases;

/// <summary>icerik.pipeline_run satiri (Editoryal veritabani 10). Kimligi hat uretir (UUIDv7).</summary>
public sealed class PipelineRun
{
    public Guid RunId { get; set; }

    public required string Komut { get; set; }

    public required string GitCommit { get; set; }

    /// <summary>Girdi, yapilandirma ve arac surumlerinin ozeti.</summary>
    public required string ParmakIzi { get; set; }

    /// <summary>UTC.</summary>
    public DateTime Baslangic { get; set; }

    /// <summary>UTC.</summary>
    public DateTime? Bitis { get; set; }

    /// <summary>calisiyor, basarili, basarisiz.</summary>
    public required string Durum { get; set; }

    /// <summary>jsonb.</summary>
    public string Manifest { get; set; } = "{}";
}
