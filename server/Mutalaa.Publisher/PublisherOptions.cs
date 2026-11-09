using Microsoft.Extensions.Configuration;

namespace Mutalaa.Publisher;

/// <summary>
/// Publisher: bolumu (gizli olmayan ayarlar). Yollar goreli verilebilir ve calisma dizinine gore cozulur (proje koku); bu sinif
/// yolu cozmez, cagiran Path.GetFullPath uygular. Varsayilanlar appsettings.json ile ayni degerlerdir.
/// </summary>
public sealed class PublisherOptions
{
    public const string SectionName = "Publisher";

    public string SchemaDir { get; init; } = "packages/content-schema/sql";

    public string RawDir { get; init; } = "data/raw";

    public string OutDir { get; init; } = "data/packs";

    public string SourcesDir { get; init; } = "pipeline/sources";

    /// <summary>Kuru calistirma raporlari: {ReportsDir}/{flavor}-{tarih}/.</summary>
    public string ReportsDir { get; init; } = "data/reports/publisher";

    /// <summary>Onceki yayinin paketleri depodan buraya inip acilir (git disi gecici klasor).</summary>
    public string TempDir { get; init; } = ".tmp/publisher";

    public string MinAppVersion { get; init; } = "1.0.0";

    /// <summary>manifest.schema.json yolu; bos ise {SchemaDir}/../manifest.schema.json.</summary>
    public string? ManifestSchemaPath { get; init; }

    public static PublisherOptions FromConfiguration(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        IConfigurationSection section = configuration.GetSection(SectionName);
        PublisherOptions defaults = new();
        return new PublisherOptions
        {
            SchemaDir = Value(section, "SchemaDir", defaults.SchemaDir),
            RawDir = Value(section, "RawDir", defaults.RawDir),
            OutDir = Value(section, "OutDir", defaults.OutDir),
            SourcesDir = Value(section, "SourcesDir", defaults.SourcesDir),
            ReportsDir = Value(section, "ReportsDir", defaults.ReportsDir),
            TempDir = Value(section, "TempDir", defaults.TempDir),
            MinAppVersion = Value(section, "MinAppVersion", defaults.MinAppVersion),
            ManifestSchemaPath = string.IsNullOrWhiteSpace(section["ManifestSchemaPath"]) ? null : section["ManifestSchemaPath"],
        };
    }

    public string ResolveManifestSchemaPath() =>
        Path.GetFullPath(ManifestSchemaPath ?? Path.Combine(SchemaDir, "..", "manifest.schema.json"));

    private static string Value(IConfigurationSection section, string key, string fallback) =>
        string.IsNullOrWhiteSpace(section[key]) ? fallback : section[key]!;
}
