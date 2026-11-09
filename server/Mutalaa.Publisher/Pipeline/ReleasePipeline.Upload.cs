using System.Text;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Storage;
using static Mutalaa.Publisher.Pipeline.Files;

namespace Mutalaa.Publisher.Pipeline;

public sealed partial class ReleasePipeline
{
    /// <summary>
    /// Yukleme sirasi (Backend API 10.5): paketler (HEAD ile dogrulanir) -> manifests/{surum}.json -> manifest.json -> yayinlandi.
    /// Ayni sha256 atlanir; farkli sha256 satiri basarisiz yapar (4); tek istisna yayimlanmamis surumun nesnesidir (paket surumu = satir surumu,
    /// satir yayinlanmamis ve depoda surumun manifesti yok): o degistirilir. Gecici depo hatasinda satir dogrulandi kalir (4). Tasinan (yerelde olmayan)
    /// paketin surumu depoda yoksa 4. Geri alma satirinda onceki guncel yayin geri_cekildi olur.
    /// </summary>
    private async Task<ReleaseResult> UploadRowAsync(Release stale, string outRoot, CancellationToken cancellationToken)
    {
        Release row = await Context.Releases.GetAsync(stale.Id, cancellationToken)
            ?? throw new PublisherException(ExitCodes.Other, "Yayin satiri yok.");
        string label = row.Derleme.ToLabel();

        byte[] manifestBytes = await ReadManifestBytesAsync(row, outRoot, label, cancellationToken);
        Manifest manifest = ParseManifest(manifestBytes, $"{label} {row.Surum}");
        if (!string.Equals(manifest.Flavor, label, StringComparison.Ordinal) || !string.Equals(manifest.Release, row.Surum, StringComparison.Ordinal))
        {
            throw new PublisherException(ExitCodes.Other, "Manifestin flavor/release alani yayin satiriyla uyusmuyor.");
        }

        IPackStore store = Context.GetStore();
        bool? versionShown = null;
        HashSet<string> shownKeys = new(StringComparer.Ordinal);
        try
        {
            foreach (ManifestPack pack in manifest.Packs)
            {
                cancellationToken.ThrowIfCancellationRequested();
                string key = StorageKeys.Pack(label, pack.PackId, pack.Version);
                string local = LocalPackPath(outRoot, label, pack.PackId, pack.Version);
                if (File.Exists(local))
                {
                    string actual = await Sha256Async(local, cancellationToken);
                    if (!string.Equals(actual, pack.Sha256, StringComparison.Ordinal))
                    {
                        throw new PublisherException(ExitCodes.Other, $"Yerel paket dosyasinin ozeti manifestle uyusmuyor: {Path.GetFileName(local)}");
                    }

                    // Yayimlanmamis surumun nesnesi (paket surumu = satirin surumu; satir yayinlanmamis; surum depoda yayin asamasina gelmemis: ne
                    // manifests/{surum}.json var ne canli manifest.json bu surumu gosteriyor) onceki denemeden kalmis olabilir: yeniden derlenen paket
                    // degistirir (K-46 madde 3). Veritabani satiri tek basina yetmez (yedekten geri yukleme): depo surumu yayimlanmis gosteriyorsa nesne
                    // degismezdir. Yayinlanmis satir ve daha eski surumlu (tasinan) paketler de degismezdir: farkli sha256 cakismadir (4).
                    bool replace = row.Durum != ReleaseStatus.Yayinlandi && string.Equals(pack.Version, row.Surum, StringComparison.Ordinal);
                    if (replace)
                    {
                        versionShown ??= await IsVersionShownAsync(store, label, row.Surum, cancellationToken);
                        if (versionShown.Value)
                        {
                            replace = false;
                            shownKeys.Add(key);
                        }
                    }

                    PutResult put = await store.PutPackAsync(key, local, pack.Sha256, replace, cancellationToken);
                    Say(Inv($"yukleme {pack.PackId} {pack.Version}: {PutLabel(put)}"));
                    continue;
                }

                StoredObject? head = await store.HeadAsync(key, cancellationToken);
                if (head is null)
                {
                    throw new PublisherException(ExitCodes.Storage, $"Tasinan paket depoda yok: {key}");
                }

                if (!string.Equals(head.Sha256, pack.Sha256, StringComparison.Ordinal) || head.Size != pack.SizeBytes)
                {
                    throw new ObjectConflictException(key, head.Sha256, pack.Sha256);
                }

                Say(Inv($"yukleme {pack.PackId} {pack.Version}: depoda var (tasinan)"));
            }

            await store.PutManifestAsync(StorageKeys.ManifestHistory(label, row.Surum), manifestBytes, cancellationToken);
            await store.PutManifestAsync(StorageKeys.Manifest(label), manifestBytes, cancellationToken);
        }
        catch (ObjectConflictException ex)
        {
            if (row.Durum == ReleaseStatus.Dogrulandi)
            {
                await FailRowAsync(row.Id, null, "depo-cakismasi", ex.Message, cancellationToken);
            }

            string message = shownKeys.Contains(ex.Key) ? StorageMessage(ex) + " " + VersionShownHint : StorageMessage(ex);
            return ReleaseResult.Fail(ExitCodes.Storage, message, row.Surum, ReleaseStatus.Basarisiz);
        }
        catch (PublisherException ex) when (ex.ExitCode == ExitCodes.Storage)
        {
            // Tasinan paket depoda yok: yayin dogrulandi kalir (paket geri yuklenince upload surer).
            return ReleaseResult.Fail(ExitCodes.Storage, Context.Redact(ex.Message), row.Surum, row.Durum);
        }
        catch (StorageException ex)
        {
            return ReleaseResult.Fail(
                ExitCodes.Storage,
                StorageMessage(ex) + " Yayin 'dogrulandi' kaldi; 'upload' ile surer.",
                row.Surum,
                row.Durum);
        }

        if (row.Durum == ReleaseStatus.Dogrulandi)
        {
            await Context.Releases.MarkPublishedAsync(row.Id, cancellationToken);
            if (row.Talep == ReleaseRequests.GeriAlma)
            {
                Release? previous = await Context.Releases.LatestPublishedAsync(row.Derleme, row.Id, cancellationToken);
                if (previous is not null)
                {
                    await Context.Releases.MarkWithdrawnAsync(previous.Id, cancellationToken);
                    Say(Inv($"geri cekildi: {label} {previous.Surum}"));
                }
            }
        }

        Say(Inv($"yayinlandi: {label} {row.Surum}"));
        return ReleaseResult.Ok(row.Surum, ReleaseStatus.Yayinlandi, $"Yayinlandi: {label} {row.Surum}.");
    }

    private const string VersionShownHint =
        "Surum depoda yayimlanmis gorunuyor; yeni --version kullanin.";

    /// <summary>
    /// Surum depoda yayin asamasina gelmis mi: manifests/{surum}.json var ya da canli manifest.json bu surumu gosteriyor (K-46 madde 3). Canli manifest
    /// okunamiyorsa surumun canli olmadigi kanitlanamaz; temkinli olarak gorunur sayilir. Depo hatasi cagirana yayilir.
    /// </summary>
    private static async Task<bool> IsVersionShownAsync(IPackStore store, string label, string surum, CancellationToken cancellationToken)
    {
        if (await store.HeadAsync(StorageKeys.ManifestHistory(label, surum), cancellationToken) is not null)
        {
            return true;
        }

        byte[]? live = await store.GetAsync(StorageKeys.Manifest(label), cancellationToken);
        if (live is null)
        {
            return false;
        }

        try
        {
            return string.Equals(ManifestJson.Read(live).Release, surum, StringComparison.Ordinal);
        }
        catch (Exception ex) when (ex is System.Text.Json.JsonException or InvalidOperationException or FormatException or KeyNotFoundException)
        {
            return true;
        }
    }

    private static string PutLabel(PutResult put) => put switch
    {
        PutResult.Uploaded => "yuklendi",
        PutResult.Replaced => "degistirildi (yayimlanmamis surumun onceki denemeden kalan nesnesi)",
        _ => "ayni, atlandi",
    };

    // Cikti klasorundeki manifest.json tam imzali baytlardir; yoksa veritabanindaki jsonb metni kullanilir (anahtar sirasi/bosluk degisir, imza
    // kanonik JSON uzerinden oldugu icin gecerli kalir).
    private async Task<byte[]> ReadManifestBytesAsync(Release row, string outRoot, string label, CancellationToken cancellationToken)
    {
        string path = Path.Combine(ReleaseDir(outRoot, label, row.Surum), "manifest.json");
        if (File.Exists(path))
        {
            return await File.ReadAllBytesAsync(path, cancellationToken);
        }

        if (string.IsNullOrWhiteSpace(row.Manifest))
        {
            throw new PublisherException(ExitCodes.Other, $"Yayinin manifesti yok (dosya ve veritabani): {label} {row.Surum}.");
        }

        return new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetBytes(row.Manifest + "\n");
    }
}
