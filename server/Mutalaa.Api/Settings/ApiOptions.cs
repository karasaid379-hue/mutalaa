namespace Mutalaa.Api.Settings;

/// <summary>
/// Dosya yollari (Mutalaa:Paths). Goreli degerler calisma dizinine gore tam yola cevrilir
/// (dotnet run icin calisma dizini depo kokudur; csproj RunWorkingDirectory).
/// </summary>
public sealed class ApiOptions
{
    public const string SectionName = "Mutalaa:Paths";

    /// <summary>Degismez ham veri (OCR sayfa gorselleri vb.).</summary>
    public string RawDir { get; set; } = "data/raw";

    /// <summary>Kaynak kayitlari (pipeline/sources/*.toml).</summary>
    public string SourcesDir { get; set; } = "pipeline/sources";

    /// <summary>Uretilen icerik paketleri.</summary>
    public string PacksDir { get; set; } = "data/packs";

    /// <summary>Api'nin gecici dosyalari.</summary>
    public string TempDir { get; set; } = ".tmp/api";

    internal void Normalize()
    {
        RawDir = Path.GetFullPath(RawDir);
        SourcesDir = Path.GetFullPath(SourcesDir);
        PacksDir = Path.GetFullPath(PacksDir);
        TempDir = Path.GetFullPath(TempDir);
    }
}
