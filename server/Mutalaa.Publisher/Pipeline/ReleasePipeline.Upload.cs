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
    /// Ayni sha256 atlanir; farkli sha256 satiri basarisiz yapar (4). Gecici depo hatasinda satir dogrulandi kalir (4). Tasinan (yerelde olmayan)
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

                    PutResult put = await store.PutPackAsync(key, local, pack.Sha256, cancellationToken);
                    Say(Inv($"yukleme {pack.PackId} {pack.Version}: {(put == PutResult.Uploaded ? "yuklendi" : "ayni, atlandi")}"));
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

            return ReleaseResult.Fail(ExitCodes.Storage, StorageMessage(ex), row.Surum, ReleaseStatus.Basarisiz);
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
