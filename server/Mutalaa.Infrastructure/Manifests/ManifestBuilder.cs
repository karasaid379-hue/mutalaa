namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Paket girdilerinden imzasiz Manifest kurar: paketler pack_id (Ordinal) sirasindadir, depends_on da Ordinal sirali,
/// url ManifestUrls.PackUrl ile uretilir, generated_at UTC ve saniyeye kesilir.
/// Siralama ayni girdiden ayni manifesti (ve imzayi) verir.
/// </summary>
public static class ManifestBuilder
{
    public static Manifest Build(
        string flavor,
        string release,
        DateTimeOffset generatedAt,
        string publicBaseUrl,
        IEnumerable<ManifestPackInput> packs)
    {
        ArgumentNullException.ThrowIfNull(flavor);
        ArgumentNullException.ThrowIfNull(release);
        ArgumentNullException.ThrowIfNull(publicBaseUrl);
        ArgumentNullException.ThrowIfNull(packs);

        ManifestPack[] rows =
        [
            .. packs
                .Select(p => new ManifestPack(
                    p.PackId,
                    p.Version,
                    p.Sha256,
                    p.SizeBytes,
                    p.MinAppVersion,
                    [.. p.DependsOn.Order(StringComparer.Ordinal)],
                    ManifestUrls.PackUrl(publicBaseUrl, flavor, p.PackId, p.Version),
                    p.SchemaVersion,
                    p.Title,
                    p.Bundled))
                .OrderBy(p => p.PackId, StringComparer.Ordinal),
        ];

        return new Manifest(flavor, release, TruncateToSecond(generatedAt), rows);
    }

    private static DateTimeOffset TruncateToSecond(DateTimeOffset value)
    {
        DateTime utc = value.UtcDateTime;
        return new DateTimeOffset(utc.AddTicks(-(utc.Ticks % TimeSpan.TicksPerSecond)), TimeSpan.Zero);
    }
}
