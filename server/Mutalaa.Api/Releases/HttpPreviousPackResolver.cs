using System.Globalization;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Settings;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Api.Releases;

/// <summary>
/// Onizlemede onceki yayinin paket dosyasini yerel bir yola cozer (<see cref="IPreviousPackResolver"/>). Sira: yerel paket klasoru
/// (<c>ApiOptions.PacksDir/{derleme}/{surum}/{pack}-{surum}.db</c>, Yayinlayicinin yerlesimi) -> gecici onbellek (<c>TempDir/previous/...</c>) ->
/// manifestteki herkese acik <c>url</c>. Her aday sha256 ile manifeste baglidir. Indirme yalniz http/https, en cok <see cref="DownloadTimeout"/>,
/// en cok manifestteki <c>size_bytes</c> kadar bayt, akisla diske ve sha256 ile birlikte; uyusmazlik <see cref="GatePlanFailure.PreviousPackMismatch"/>,
/// ulasilamazlik <see cref="GatePlanFailure.PreviousPackMissing"/> olur. Iletilerde adres (url) yer almaz.
/// </summary>
public sealed partial class HttpPreviousPackResolver(
    IOptions<ApiOptions> options,
    IHttpClientFactory clients,
    ILogger<HttpPreviousPackResolver> logger) : IPreviousPackResolver
{
    /// <summary>Adli <see cref="HttpClient"/> (ReleaseServices kaydeder).</summary>
    public const string ClientName = "previous-packs";

    /// <summary>Bir paketin indirilmesi icin toplam sure.</summary>
    public static readonly TimeSpan DownloadTimeout = TimeSpan.FromSeconds(60);

    private const int BufferSize = 81920;

    /// <summary>Bir paketin indirilmesi icin toplam sure (varsayilan <see cref="DownloadTimeout"/>; testler kisaltir).</summary>
    public TimeSpan Timeout { get; init; } = DownloadTimeout;

    [GeneratedRegex("^[0-9a-f]{64}$", RegexOptions.CultureInvariant)]
    private static partial Regex Sha256Pattern();

    public async Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(pack);
        if (!BuildFlavorLabels.TryParseLabel(flavorLabel, out _))
        {
            throw new ArgumentException("Gecersiz derleme turu etiketi.", nameof(flavorLabel));
        }

        if (!Sha256Pattern().IsMatch(pack.Sha256))
        {
            throw new GatePlanException(GatePlanFailure.ManifestUnreadable, $"Onceki yayinin manifestinde gecersiz sha256 ({pack.PackId}).");
        }

        ApiOptions paths = options.Value;
        string local;
        try
        {
            local = PackFiles.LocalPackPath(paths.PacksDir, flavorLabel, pack.PackId, pack.Version);
        }
        catch (ArgumentException ex)
        {
            throw new GatePlanException(GatePlanFailure.ManifestUnreadable, "Onceki yayinin manifestinde gecersiz paket kimligi ya da surum.", ex);
        }

        if (await HasValidFileAsync(local, pack, cancellationToken))
        {
            return local;
        }

        string cache = Path.Combine(paths.TempDir, "previous", flavorLabel, $"{pack.PackId}-{pack.Version}-{pack.Sha256[..12]}.db");
        if (await HasValidFileAsync(cache, pack, cancellationToken))
        {
            return cache;
        }

        await DownloadAsync(pack, cache, cancellationToken);
        return cache;
    }

    private static async Task<bool> HasValidFileAsync(string path, ManifestPack pack, CancellationToken cancellationToken) =>
        File.Exists(path) && string.Equals(await PackFiles.Sha256Async(path, cancellationToken), pack.Sha256, StringComparison.Ordinal);

    private async Task DownloadAsync(ManifestPack pack, string target, CancellationToken cancellationToken)
    {
        string name = $"{pack.PackId} {pack.Version}";
        if (!Uri.TryCreate(pack.Url, UriKind.Absolute, out Uri? uri) || uri.Scheme is not ("http" or "https"))
        {
            throw new GatePlanException(
                GatePlanFailure.PreviousPackMissing,
                $"Onceki yayinin paketi yerelde yok ve manifestteki adresi indirilebilir degil (yalniz http/https): {name}.");
        }

        if (pack.SizeBytes <= 0)
        {
            throw new GatePlanException(GatePlanFailure.PreviousPackMismatch, $"Onceki yayinin paketinin manifestteki boyutu gecersiz: {name}.");
        }

        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
        string temp = target + "." + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture) + ".part";
        try
        {
            await DownloadToFileAsync(uri, pack, name, temp, cancellationToken);
            try
            {
                File.Move(temp, target, overwrite: true);
            }
            catch (IOException)
            {
                // Baska bir islem ayni dosyayi onbellege koymus olabilir; o gecerliyse sorun yok, degilse hata yayilir.
                if (!await HasValidFileAsync(target, pack, cancellationToken))
                {
                    throw;
                }
            }
        }
        finally
        {
            TryDelete(temp);
        }

        logger.LogInformation("Onceki yayin paketi indirildi: {Pack} {Version}.", pack.PackId, pack.Version);
    }

    private async Task DownloadToFileAsync(Uri uri, ManifestPack pack, string name, string temp, CancellationToken cancellationToken)
    {
        using CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(Timeout);

        string sha256;
        long total = 0;
        try
        {
            using HttpClient client = clients.CreateClient(ClientName);
            using HttpRequestMessage request = new(HttpMethod.Get, uri);
            using HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token);
            if (!response.IsSuccessStatusCode)
            {
                throw new GatePlanException(
                    GatePlanFailure.PreviousPackMissing,
                    string.Create(CultureInfo.InvariantCulture, $"Onceki yayinin paketi indirilemedi (HTTP {(int)response.StatusCode}): {name}."));
            }

            if (response.Content.Headers.ContentLength is long declared && declared > pack.SizeBytes)
            {
                throw SizeExceeded(name);
            }

            using IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            await using Stream body = await response.Content.ReadAsStreamAsync(timeout.Token);
            await using FileStream file = new(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None, BufferSize, useAsync: true);
            byte[] buffer = new byte[BufferSize];
            int read;
            while ((read = await body.ReadAsync(buffer, timeout.Token)) > 0)
            {
                total += read;
                if (total > pack.SizeBytes)
                {
                    throw SizeExceeded(name);
                }

                hash.AppendData(buffer, 0, read);
                await file.WriteAsync(buffer.AsMemory(0, read), timeout.Token);
            }

            sha256 = Convert.ToHexStringLower(hash.GetHashAndReset());
        }
        catch (HttpRequestException ex)
        {
            logger.LogWarning("Onceki yayin paketi indirilemedi ({ExceptionType}): {Pack} {Version}.", ex.GetType().Name, pack.PackId, pack.Version);
            throw new GatePlanException(GatePlanFailure.PreviousPackMissing, $"Onceki yayinin paketine ulasilamadi: {name}.", ex);
        }
        catch (OperationCanceledException ex) when (!cancellationToken.IsCancellationRequested)
        {
            throw new GatePlanException(GatePlanFailure.PreviousPackMissing, $"Onceki yayinin paketi zamaninda indirilemedi: {name}.", ex);
        }

        if (total != pack.SizeBytes || !string.Equals(sha256, pack.Sha256, StringComparison.Ordinal))
        {
            throw new GatePlanException(GatePlanFailure.PreviousPackMismatch, $"Onceki yayinin paketi manifestteki sha256 ve boyutla uyusmuyor: {name}.");
        }
    }

    private static GatePlanException SizeExceeded(string name) =>
        new(GatePlanFailure.PreviousPackMismatch, $"Onceki yayinin paketi manifestteki boyutu asiyor: {name}.");

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (IOException)
        {
            // Gecici dosya; bir sonraki calistirmada benzersiz adla yeniden denenir.
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
