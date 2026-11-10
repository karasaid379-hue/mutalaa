using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using static Mutalaa.Publisher.Pipeline.Files;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>
/// Onceki yayinin paket dosyasini cozer: once cikti klasoru, sonra gecici onbellek; ikisi de yoksa depodan indirilir ve manifestteki sha256 ile
/// dogrulanir (yoksa <see cref="GatePlanFailure.PreviousPackMissing"/>, uyusmazsa <see cref="GatePlanFailure.PreviousPackMismatch"/>).
/// </summary>
internal sealed class PublisherPackResolver(PublisherContext context, string outRoot) : IPreviousPackResolver
{
    public async Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(pack);

        string local = LocalPackPath(outRoot, flavorLabel, pack.PackId, pack.Version);
        if (File.Exists(local) && string.Equals(await Sha256Async(local, cancellationToken), pack.Sha256, StringComparison.Ordinal))
        {
            return local;
        }

        string cache = Path.Combine(Path.GetFullPath(context.Options.TempDir), "previous", flavorLabel, $"{pack.PackId}-{pack.Version}-{pack.Sha256[..12]}.db");
        if (File.Exists(cache) && string.Equals(await Sha256Async(cache, cancellationToken), pack.Sha256, StringComparison.Ordinal))
        {
            return cache;
        }

        string key = StorageKeys.Pack(flavorLabel, pack.PackId, pack.Version);
        byte[]? bytes = await context.GetStore().GetAsync(key, cancellationToken)
            ?? throw new GatePlanException(GatePlanFailure.PreviousPackMissing, $"Onceki yayinin paketi depoda yok: {key}");
        if (!string.Equals(Sha256(bytes), pack.Sha256, StringComparison.Ordinal))
        {
            throw new GatePlanException(GatePlanFailure.PreviousPackMismatch, $"Onceki yayinin paketi manifestteki sha256 ile uyusmuyor: {key}");
        }

        await WriteBytesAsync(cache, bytes, cancellationToken);
        return cache;
    }
}
