namespace Mutalaa.Infrastructure.Manifests;

/// <summary>Paket adresi: {PublicBaseUrl}/packs/{flavor}/{pack_id}/{version}/{pack_id}-{version}.db (Backend API 10.5).</summary>
public static class ManifestUrls
{
    /// <summary>PublicBaseUrl sonundaki '/' isaretleri kirpilir.</summary>
    public static string PackUrl(string publicBaseUrl, string flavor, string packId, string version)
    {
        ArgumentNullException.ThrowIfNull(publicBaseUrl);
        ArgumentNullException.ThrowIfNull(flavor);
        ArgumentNullException.ThrowIfNull(packId);
        ArgumentNullException.ThrowIfNull(version);

        string baseUrl = publicBaseUrl.TrimEnd('/');
        return $"{baseUrl}/packs/{flavor}/{packId}/{version}/{packId}-{version}.db";
    }
}
