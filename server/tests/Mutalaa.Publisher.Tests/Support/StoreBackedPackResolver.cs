using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>Test cozucusu: onceki yayinin paketini depodan indirir, manifestteki sha256 ile dogrular ve gecici klasore yazar (API cozucusunun iskeleti).</summary>
internal sealed class StoreBackedPackResolver(IPackStore store, string directory) : IPreviousPackResolver
{
    public async Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken)
    {
        string key = StorageKeys.Pack(flavorLabel, pack.PackId, pack.Version);
        byte[] bytes = await store.GetAsync(key, cancellationToken)
            ?? throw new GatePlanException(GatePlanFailure.PreviousPackMissing, $"Onceki yayinin paketi depoda yok: {key}");
        if (!string.Equals(PackFiles.Sha256(bytes), pack.Sha256, StringComparison.Ordinal))
        {
            throw new GatePlanException(GatePlanFailure.PreviousPackMismatch, $"Onceki yayinin paketi manifestteki sha256 ile uyusmuyor: {key}");
        }

        string path = Path.Combine(directory, $"{pack.PackId}-{pack.Version}.db");
        await PackFiles.WriteBytesAsync(path, bytes, cancellationToken);
        return path;
    }
}
