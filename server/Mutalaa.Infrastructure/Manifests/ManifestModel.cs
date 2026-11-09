namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Manifestteki tek paket satiri (Icerik paketleri 5). Url dolu gelir; ManifestBuilder uretir.
/// Title ve Bundled null ise JSON'a yazilmaz.
/// </summary>
public sealed record ManifestPack(
    string PackId,
    string Version,
    string Sha256,
    long SizeBytes,
    string MinAppVersion,
    IReadOnlyList<string> DependsOn,
    string Url,
    int SchemaVersion,
    string? Title = null,
    bool? Bundled = null);

/// <summary>
/// ManifestBuilder'a verilen paket girdisi (url henuz yok). Siralama ve url uretimi Builder'dadir.
/// </summary>
public sealed record ManifestPackInput(
    string PackId,
    string Version,
    string Sha256,
    long SizeBytes,
    string MinAppVersion,
    IReadOnlyList<string> DependsOn,
    int SchemaVersion,
    string? Title = null,
    bool? Bundled = null);

/// <summary>
/// Imzasiz manifest (signature alani ManifestSigner tarafindan eklenir). Flavor etikettir (dev, internal, public).
/// GeneratedAt UTC ve saniye duyarlilikli yazilir.
/// </summary>
public sealed record Manifest(
    string Flavor,
    string Release,
    DateTimeOffset GeneratedAt,
    IReadOnlyList<ManifestPack> Packs)
{
    /// <summary>Bu kod yalniz manifest_version 1'i yazar ve okur (manifest.schema.json).</summary>
    public const int CurrentVersion = 1;

    public int ManifestVersion { get; init; } = CurrentVersion;
}
