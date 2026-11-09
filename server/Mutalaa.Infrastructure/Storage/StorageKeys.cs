namespace Mutalaa.Infrastructure.Storage;

/// <summary>
/// Depo anahtar duzeni, icerik turleri ve Cache-Control degerleri (Backend API 10.5). Anahtarlar kova icindeki yoldur
/// (kova adi icermez); manifestteki mutlak adres {PublicBaseUrl}/{Pack(...)} olur.
/// </summary>
public static class StorageKeys
{
    /// <summary>Paket nesnesi: surumlu adres degismez, istemci sonsuza dek onbellekleyebilir.</summary>
    public const string PackCacheControl = "public, max-age=31536000, immutable";

    /// <summary>Manifest ve manifest gecmisi: her okumada yeniden dogrulanir.</summary>
    public const string ManifestCacheControl = "no-cache";

    public const string PackContentType = "application/vnd.sqlite3";

    public const string ManifestContentType = "application/json";

    /// <summary>Yuklenen paketin sha256 degerini tasiyan kullanici ust verisinin adi (x-amz-meta-sha256).</summary>
    public const string Sha256MetadataName = "sha256";

    /// <summary>packs/{flavor}/{pack_id}/{version}/{pack_id}-{version}.db</summary>
    public static string Pack(string flavor, string packId, string version)
    {
        RequireSegment(flavor);
        RequireSegment(packId);
        RequireSegment(version);
        return $"packs/{flavor}/{packId}/{version}/{packId}-{version}.db";
    }

    /// <summary>{flavor}/manifest.json</summary>
    public static string Manifest(string flavor)
    {
        RequireSegment(flavor);
        return $"{flavor}/manifest.json";
    }

    /// <summary>{flavor}/manifests/{surum}.json</summary>
    public static string ManifestHistory(string flavor, string surum)
    {
        RequireSegment(flavor);
        RequireSegment(surum);
        return $"{flavor}/manifests/{surum}.json";
    }

    // Anahtar parcasi tek bir yol bolumudur: bos, egik cizgi ya da nokta-nokta icermez.
    private static void RequireSegment(string value)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(value);
        if (value.Contains('/', StringComparison.Ordinal)
            || value.Contains('\\', StringComparison.Ordinal)
            || value.Contains("..", StringComparison.Ordinal))
        {
            throw new ArgumentException($"Gecersiz anahtar parcasi: {value}", nameof(value));
        }
    }
}
