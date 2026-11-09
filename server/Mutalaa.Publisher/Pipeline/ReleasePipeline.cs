using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using static Mutalaa.Publisher.Pipeline.Files;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>
/// Ortak yayin duzenleyicisi (Backend API 10.2, 10.6): publish, build, upload, promote, rollback ve watch bunu kullanir. Danisma kilidi
/// KOMUT katmanindadir (<see cref="PublisherLock"/>); burada alinmaz. Durum gecisleri: hazirlaniyor -> dogrulandi -> yayinlandi; kapi
/// reddi, oz denetim hatasi ve depoda cakisma satiri basarisiz yapar; gecici depo hatasinda satir dogrulandi kalir (upload ile surer).
/// Beklenmeyen istisnalarda (ornegin veritabani kopmasi) satir oldugu gibi kalir ve sonraki calistirmada surdurulur.
/// </summary>
public sealed partial class ReleasePipeline(PublisherContext context)
{
    /// <summary>Komut satiri dogrulamasi ve boru hatti ayni iletiyi kullanir.</summary>
    public const string RestartWithDryRunMessage = "--restart ile --dry-run birlikte kullanilamaz (kuru calistirma satir ve depo yazmaz).";

    private PublisherContext Context { get; } = context;

    /// <summary>publish ve build: kapi, paketler, imzali manifest; build dogrulandi'da durur, publish yukler.</summary>
    public async Task<ReleaseResult> PublishAsync(PublishRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.Restart && request.DryRun)
        {
            throw new PublisherException(ExitCodes.Other, RestartWithDryRunMessage, isPermanent: true);
        }

        ValidatePackIds(request.Packs);
        string outRoot = Path.GetFullPath(request.OutDir ?? Context.Options.OutDir);

        if (request.DryRun)
        {
            return await DryRunAsync(request.Flavor, request.Packs, outRoot, promoteFrom: null, cancellationToken);
        }

        _ = Context.GetSigningKey(request.Flavor);
        _ = Context.PublicBaseUrl;
        _ = Context.ConnectionString;
        if (!request.StopAtVerified)
        {
            _ = Context.GetStore();
        }

        Release row = await ResolvePublishRowAsync(request, cancellationToken);
        IReadOnlyList<string> packs = request.Packs.Count > 0 ? request.Packs : row.Paketler ?? [];
        return await RunRowAsync(row, packs, outRoot, promoteFrom: null, request.StopAtVerified, cancellationToken);
    }

    /// <summary>upload: dogrulandi satiri yukler (yayinlandi satir yeniden calistirilabilir: ayni sha256 atlanir, manifest yeniden yazilir).</summary>
    public async Task<ReleaseResult> UploadAsync(UploadRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        string outRoot = Path.GetFullPath(request.OutDir ?? Context.Options.OutDir);
        _ = Context.ConnectionString;
        _ = Context.GetStore();

        Release? row = request.Surum is null
            ? await Context.Releases.FindOpenAsync(request.Flavor, null, cancellationToken)
            : await Context.Releases.FindAsync(request.Flavor, request.Surum, cancellationToken);
        if (row is null)
        {
            return ReleaseResult.Fail(ExitCodes.Other, request.Surum is null
                ? $"Yuklenecek acik yayin yok ({request.Flavor.ToLabel()}); once 'build' ya da 'publish' calistirin."
                : $"Yayin yok: {request.Flavor.ToLabel()} {request.Surum}.");
        }

        if (row.Durum is not (ReleaseStatus.Dogrulandi or ReleaseStatus.Yayinlandi))
        {
            return ReleaseResult.Fail(ExitCodes.Other, $"Yayin yuklenemez, durum: {row.Durum.ToLabel()} ({row.Surum}).", row.Surum, row.Durum);
        }

        // Yayinlanmis satir yalniz derleme turunun en son yayinlanan satiriysa yeniden yuklenebilir; eski bir yayini yuklemek manifest.json'u
        // geriye alirdi (sessiz geri alma). Geri alma yalniz 'rollback' ile yapilir.
        if (row.Durum == ReleaseStatus.Yayinlandi)
        {
            Release? latest = await Context.Releases.LatestPublishedAsync(row.Derleme, cancellationToken);
            if (latest is null || latest.Id != row.Id)
            {
                return ReleaseResult.Fail(
                    ExitCodes.Other,
                    $"Eski yayin yeniden yuklenemez ({row.Derleme.ToLabel()} {row.Surum}); geri donmek icin 'rollback' kullanin.",
                    row.Surum,
                    row.Durum);
            }
        }

        return await UploadRowAsync(row, outRoot, cancellationToken);
    }

    /// <summary>promote: yayinlandi internal yayini ayni surumle public icin uretir; P-14 kaynak ozetlerini karsilastirir.</summary>
    public async Task<ReleaseResult> PromoteAsync(PromoteRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        IReadOnlyList<string> requestedPacks = request.Packs ?? [];
        ValidatePackIds(requestedPacks);
        string outRoot = Path.GetFullPath(request.OutDir ?? Context.Options.OutDir);

        Release? existing = request.ReleaseId is int id ? await Context.Releases.GetAsync(id, cancellationToken) : null;
        if (request.ReleaseId is not null && existing is null)
        {
            return ReleaseResult.Fail(ExitCodes.Other, "Terfi satiri yok.");
        }

        Release? source;
        if (existing is not null)
        {
            source = existing.KaynakReleaseId is int sourceId ? await Context.Releases.GetAsync(sourceId, cancellationToken) : null;
        }
        else
        {
            source = request.Surum is null
                ? await Context.Releases.LatestPublishedAsync(BuildFlavor.Internal, cancellationToken)
                : await Context.Releases.FindAsync(BuildFlavor.Internal, request.Surum, cancellationToken);
        }

        if (source is null || source.Derleme != BuildFlavor.Internal || source.Durum != ReleaseStatus.Yayinlandi)
        {
            return await PreconditionFailedAsync(
                existing,
                ExitCodes.Other,
                "terfi-kaynagi-yok",
                "Terfi edilecek 'yayinlandi' durumunda bir internal yayin yok.",
                cancellationToken);
        }

        // Terfi ayni surumle yapilir (K-46 madde 8, P-14): watch satirinin surumu kaynak internal yayinin surumuyle ayni olmali; yoksa public
        // manifest, test edilen internal yayindan farkli bir surum numarasi tasirdi.
        if (existing is not null && !string.Equals(existing.Surum, source.Surum, StringComparison.Ordinal))
        {
            return await PreconditionFailedAsync(
                existing,
                ExitCodes.Other,
                "terfi-surumu-uyumsuz",
                $"Terfi satirinin surumu ({existing.Surum}) kaynak internal yayinin surumuyle ({source.Surum}) ayni olmali.",
                cancellationToken);
        }

        ReleaseDigests internalDigests = ReleaseDigests.Parse(source.Ozetler);
        if (request.DryRun)
        {
            return await DryRunAsync(BuildFlavor.Public, requestedPacks, outRoot, internalDigests, cancellationToken);
        }

        _ = Context.GetSigningKey(BuildFlavor.Public);
        _ = Context.PublicBaseUrl;
        _ = Context.ConnectionString;
        _ = Context.GetStore();

        Release row;
        if (existing is not null)
        {
            row = existing;
        }
        else
        {
            Release? target = await Context.Releases.FindAsync(BuildFlavor.Public, source.Surum, cancellationToken);
            if (target is not null && target.Durum == ReleaseStatus.Yayinlandi)
            {
                return ReleaseResult.Fail(ExitCodes.Other, $"Bu surum zaten terfi edilmis: public {source.Surum}.", source.Surum, target.Durum);
            }

            row = target ?? await Context.Releases.CreateAsync(
                new NewRelease(
                    BuildFlavor.Public,
                    source.Surum,
                    ReleaseRequests.Terfi,
                    await Context.DataVersionAsync(cancellationToken),
                    "publisher",
                    source.Id,
                    requestedPacks.Count > 0 ? [.. requestedPacks] : null,
                    request.Notes),
                cancellationToken);
        }

        IReadOnlyList<string> packs = requestedPacks.Count > 0 ? requestedPacks : row.Paketler ?? [];
        return await RunRowAsync(row, packs, outRoot, internalDigests, stopAtVerified: false, cancellationToken);
    }

    /// <summary>
    /// rollback: hedefin manifesti ve butun paket anahtarlari depoda olmali (yoksa 4). Yeni satir (talep = geri_alma, yeni surum) acilir,
    /// hedefin paketleri yeni manifestle yeniden imzalanir, onceki guncel yayin geri_cekildi olur.
    /// </summary>
    public async Task<ReleaseResult> RollbackAsync(RollbackRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (!ReleaseVersion.TryParse(request.To, out _))
        {
            return ReleaseResult.Fail(ExitCodes.Other, $"Gecersiz surum: {request.To}");
        }

        string label = request.Flavor.ToLabel();
        string outRoot = Path.GetFullPath(request.OutDir ?? Context.Options.OutDir);
        SigningKey key = Context.GetSigningKey(request.Flavor);
        string baseUrl = Context.PublicBaseUrl;
        _ = Context.ConnectionString;
        IPackStore store = Context.GetStore();

        Release? existing = request.ReleaseId is int id ? await Context.Releases.GetAsync(id, cancellationToken) : null;
        if (request.ReleaseId is not null && existing is null)
        {
            return ReleaseResult.Fail(ExitCodes.Other, "Geri alma satiri yok.");
        }

        Manifest target;
        try
        {
            byte[]? targetBytes = await store.GetAsync(StorageKeys.ManifestHistory(label, request.To), cancellationToken);
            if (targetBytes is null)
            {
                return await PreconditionFailedAsync(existing, ExitCodes.Storage, "hedef-manifest-yok", $"Hedef manifest depoda yok: {StorageKeys.ManifestHistory(label, request.To)}", cancellationToken);
            }

            target = ParseManifest(targetBytes, $"hedef manifest ({request.To})");

            if (!string.Equals(target.Flavor, label, StringComparison.Ordinal) || !string.Equals(target.Release, request.To, StringComparison.Ordinal))
            {
                return await PreconditionFailedAsync(existing, ExitCodes.Verification, "hedef-manifest-uyumsuz", "Hedef manifestin flavor/release alani istenenle uyusmuyor.", cancellationToken);
            }

            byte[]? currentBytes = await store.GetAsync(StorageKeys.Manifest(label), cancellationToken);
            if (currentBytes is not null && string.Equals(ParseManifest(currentBytes, "guncel manifest").Release, request.To, StringComparison.Ordinal))
            {
                return await PreconditionFailedAsync(existing, ExitCodes.Other, "hedef-zaten-guncel", $"Hedef yayin zaten guncel: {request.To}", cancellationToken);
            }

            foreach (ManifestPack pack in target.Packs)
            {
                string packKey = StorageKeys.Pack(label, pack.PackId, pack.Version);
                StoredObject? head = await store.HeadAsync(packKey, cancellationToken);
                if (head is null || !string.Equals(head.Sha256, pack.Sha256, StringComparison.Ordinal) || head.Size != pack.SizeBytes)
                {
                    return await PreconditionFailedAsync(existing, ExitCodes.Storage, "hedef-paket-yok", $"Hedef yayinin paketi depoda yok ya da farkli: {packKey}", cancellationToken);
                }
            }
        }
        catch (StorageException ex)
        {
            return ReleaseResult.Fail(ExitCodes.Storage, StorageMessage(ex));
        }

        Release? targetRow = await Context.Releases.FindAsync(request.Flavor, request.To, cancellationToken);

        // CLI geri alma acik (hazirlaniyor ya da dogrulandi) bir geri alma satirini gormezden gelmez: ayni hedefse onu surdurur; baska hedefse
        // o talep yeni komutla gecersiz kalmistir, basarisiz yapilir (yoksa sonraki watch turu manifest.json'u beklenmedik bicimde geri alirdi).
        while (existing is null && await Context.Releases.FindOpenAsync(request.Flavor, ReleaseRequests.GeriAlma, cancellationToken) is { } open)
        {
            if (targetRow is not null && open.KaynakReleaseId == targetRow.Id)
            {
                existing = open;
            }
            else
            {
                await FailRowAsync(open.Id, null, "yeni-geri-alma-talebi", $"Acik geri alma talebi yeni bir 'rollback --to {request.To}' komutuyla gecersiz kaldi.", cancellationToken);
            }
        }

        Release row = existing ?? await Context.Releases.CreateAsync(
            new NewRelease(
                request.Flavor,
                null,
                ReleaseRequests.GeriAlma,
                await Context.DataVersionAsync(cancellationToken),
                "publisher",
                targetRow?.Id,
                null,
                request.Notes),
            cancellationToken);

        if (row.Durum == ReleaseStatus.Dogrulandi)
        {
            return await UploadRowAsync(row, outRoot, cancellationToken);
        }

        if (row.Durum != ReleaseStatus.Hazirlaniyor)
        {
            return ReleaseResult.Fail(ExitCodes.Other, $"Geri alma satiri islenemez, durum: {row.Durum.ToLabel()}.", row.Surum, row.Durum);
        }

        IEnumerable<ManifestPackInput> inputs = target.Packs.Select(ToInput);
        Manifest manifest = ManifestBuilder.Build(label, row.Surum, Context.Clock.GetUtcNow(), baseUrl, inputs);
        byte[] signed = ManifestSigner.Sign(ManifestJson.Write(manifest), key);

        string gateJson = GateReport.Create(request.Flavor, [], []).ToJson();
        await WriteTextAsync(Path.Combine(ReleaseDir(outRoot, label, row.Surum), "gate-report.json"), gateJson + "\n", cancellationToken);
        await WriteBytesAsync(Path.Combine(ReleaseDir(outRoot, label, row.Surum), "manifest.json"), signed, cancellationToken);

        string digests = targetRow is null ? ReleaseDigests.Empty.ToJson() : ReleaseDigests.Parse(targetRow.Ozetler).ToJson();
        await Context.Releases.MarkVerifiedAsync(row.Id, Encoding.UTF8.GetString(signed), gateJson, digests, null, cancellationToken);
        Say(Inv($"geri alma: {label} {request.To} -> yeni surum {row.Surum} (dogrulandi)"));
        return await UploadRowAsync(row, outRoot, cancellationToken);
    }

    /// <summary>watch: bekleyen satiri talebine gore yurutur (yayin -> publish, terfi -> promote, geri_alma -> rollback).</summary>
    public async Task<ReleaseResult> ProcessRequestAsync(Release row, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(row);

        try
        {
            return await DispatchRequestAsync(row, cancellationToken);
        }
        catch (PublisherException ex) when (ex.IsPermanent)
        {
            // Kalici girdi hatasi (bilinmeyen paket, onceki manifest yok, bozuk surum...): yeniden denemek sonucu degistirmez, satir basarisiz olur.
            // Yapilandirma hatalari (sir, anahtar, baglanti dizesi yok) kalici degildir; bunlar yayilir ve satir hazirlaniyor kalir.
            Release current = await Context.Releases.GetAsync(row.Id, cancellationToken) ?? row;
            return await PreconditionFailedAsync(current, ex.ExitCode, "girdi-hatasi", ex.Message, cancellationToken);
        }
    }

    private async Task<ReleaseResult> DispatchRequestAsync(Release row, CancellationToken cancellationToken)
    {
        switch (row.Talep)
        {
            case ReleaseRequests.Yayin:
                return await PublishAsync(
                    new PublishRequest(row.Derleme, row.Paketler ?? [], DryRun: false, Version: row.Surum, ReleaseId: row.Id, Notes: row.Notlar),
                    cancellationToken);
            case ReleaseRequests.Terfi:
                return await PromoteAsync(new PromoteRequest(Packs: row.Paketler, ReleaseId: row.Id, Notes: row.Notlar), cancellationToken);
            case ReleaseRequests.GeriAlma:
                Release? source = row.KaynakReleaseId is int sourceId ? await Context.Releases.GetAsync(sourceId, cancellationToken) : null;
                if (source is null)
                {
                    return await PreconditionFailedAsync(row, ExitCodes.Other, "geri-alma-hedefi-yok", "Geri alma satirinin kaynak_release_id degeri yok ya da satir bulunamadi.", cancellationToken);
                }

                return await RollbackAsync(new RollbackRequest(row.Derleme, source.Surum, ReleaseId: row.Id, Notes: row.Notlar), cancellationToken);
            default:
                return ReleaseResult.Fail(ExitCodes.Other, $"Bilinmeyen talep: {row.Talep}", row.Surum, row.Durum);
        }
    }

    private async Task<Release> ResolvePublishRowAsync(PublishRequest request, CancellationToken cancellationToken)
    {
        if (request.ReleaseId is int id)
        {
            Release row = await Context.Releases.GetAsync(id, cancellationToken)
                ?? throw new PublisherException(ExitCodes.Other, "Yayin satiri yok.");
            if (row.Derleme != request.Flavor)
            {
                throw new PublisherException(ExitCodes.Other, "Yayin satirinin derleme turu istenenle uyusmuyor.");
            }

            return row;
        }

        Release? existing = request.Version is not null
            ? await Context.Releases.FindAsync(request.Flavor, request.Version, cancellationToken)
            : await Context.Releases.FindOpenAsync(request.Flavor, ReleaseRequests.Yayin, cancellationToken);
        if (existing is not null)
        {
            if (!request.Restart)
            {
                return existing;
            }

            // --restart yalniz acik 'dogrulandi' yayin satirini yeniden baslatir ('hazirlaniyor' satir zaten yeniden derlenir); 'yayinlandi' satira
            // ve baska bir talep turunun (terfi, geri alma) satirina dokunulmaz. Etkisiz kalacaksa sessiz kalinmaz: acik hata (1), satir degismez.
            if (existing.Talep == ReleaseRequests.Yayin && existing.Durum == ReleaseStatus.Dogrulandi)
            {
                return await RestartRowAsync(existing, request, cancellationToken);
            }

            if (existing.Talep == ReleaseRequests.Yayin && existing.Durum == ReleaseStatus.Hazirlaniyor)
            {
                return existing;
            }

            throw new PublisherException(
                ExitCodes.Other,
                $"--restart uygulanamadi: {existing.Derleme.ToLabel()} {existing.Surum} satiri 'dogrulandi' durumunda bir yayin talebi degil (talep: {existing.Talep}, durum: {existing.Durum.ToLabel()}); satira dokunulmadi.");
        }

        if (request.Restart && request.Version is not null
            && await Context.Releases.FindOpenAsync(request.Flavor, ReleaseRequests.Yayin, cancellationToken) is { } open)
        {
            throw new PublisherException(
                ExitCodes.Other,
                $"--restart uygulanamadi: istenen surumde ({request.Version}) satir yok; acik yayin satiri baska surumde ({open.Surum}, durum: {open.Durum.ToLabel()}); satira dokunulmadi.");
        }

        return await CreateRowAsync(request, cancellationToken);
    }

    /// <summary>
    /// Yerel ciktisi kaybolmus ya da depoyla tutarsiz kalmis 'dogrulandi' satiri basarisiz yapar (hata kodu yeniden-baslatildi) ve ayni surumle
    /// yeni bir satir acar; sonraki adim derleme ve yuklemedir. Onceki denemeden depoda kalan paket nesneleri yayimlanmamis surumun nesnesi
    /// oldugu icin yuklemede degistirilir.
    /// </summary>
    private async Task<Release> RestartRowAsync(Release stale, PublishRequest request, CancellationToken cancellationToken)
    {
        // Surum depoda yayin asamasina gelmisse (canli manifest.json bu surumu gosteriyor ya da manifests/{surum}.json var) satir basarisiz YAPILMAZ:
        // ayni surum yeni baytlarla yeniden derlenirse depodaki degismez nesnelerle cakisirdi; dogru yol ayni baytlarla 'upload'. Depo erisimi
        // (ayar ya da ag) yoksa kontrol yapilamaz ve mevcut davranis surer.
        if (await TryIsVersionShownAsync(stale, cancellationToken))
        {
            throw new PublisherException(
                ExitCodes.Other,
                $"--restart uygulanamadi: yayin canli manifestte ({stale.Derleme.ToLabel()} {stale.Surum}); upload ile tamamlayin (satir 'dogrulandi' kaldi).");
        }

        Say(Inv($"yeniden baslatma: {stale.Derleme.ToLabel()} {stale.Surum} (dogrulandi satir basarisiz yapildi, ayni surumle yeniden derlenecek)"));
        await FailRowAsync(
            stale.Id,
            null,
            "yeniden-baslatildi",
            "Dogrulandi satir 'publish --restart' ile basarisiz yapildi; ayni surumle yeniden derleniyor.",
            cancellationToken);
        return await CreateRowAsync(
            request with
            {
                Version = stale.Surum,
                Packs = request.Packs.Count > 0 ? request.Packs : stale.Paketler ?? [],
                Notes = request.Notes ?? stale.Notlar,
            },
            cancellationToken);
    }

    private async Task<bool> TryIsVersionShownAsync(Release row, CancellationToken cancellationToken)
    {
        IPackStore store;
        try
        {
            store = Context.GetStore();
        }
        catch (PublisherException)
        {
            return false;
        }

        try
        {
            return await IsVersionShownAsync(store, row.Derleme.ToLabel(), row.Surum, cancellationToken);
        }
        catch (StorageException ex)
        {
            // Depo ayarliyken kontrol yapilamadiysa surumun canli olmadigi kanitlanamaz: satira dokunulmaz, hata verilir.
            throw new PublisherException(
                ExitCodes.Storage,
                StorageMessage(ex) + " --restart depo denetimi yapilamadi; satira dokunulmadi, depo donunce yeniden deneyin.");
        }
    }

    private async Task<Release> CreateRowAsync(PublishRequest request, CancellationToken cancellationToken)
    {
        try
        {
            return await Context.Releases.CreateAsync(
                new NewRelease(
                    request.Flavor,
                    request.Version,
                    ReleaseRequests.Yayin,
                    await Context.DataVersionAsync(cancellationToken),
                    "publisher",
                    null,
                    request.Packs.Count > 0 ? [.. request.Packs] : null,
                    request.Notes),
                cancellationToken);
        }
        catch (ReleaseConflictException ex)
        {
            throw new PublisherException(ExitCodes.Other, ex.Message, ex);
        }
    }

    private void ValidatePackIds(IReadOnlyList<string> packs)
    {
        foreach (string id in packs)
        {
            if (!Context.Catalog.TryGet(id, out _))
            {
                throw new PublisherException(ExitCodes.Other, $"Bilinmeyen paket kimligi: {id}", isPermanent: true);
            }
        }
    }

    private async Task<ReleaseResult> PreconditionFailedAsync(Release? row, int exitCode, string code, string message, CancellationToken cancellationToken)
    {
        // watch tarafindan acilan satirda kosul kalici olarak saglanamiyorsa satir basarisiz olur (sonsuz yeniden deneme olmasin).
        if (row is not null && row.Durum == ReleaseStatus.Hazirlaniyor)
        {
            await FailRowAsync(row.Id, null, code, message, cancellationToken);
        }

        return ReleaseResult.Fail(exitCode, message, row?.Surum, row is null ? null : ReleaseStatus.Basarisiz);
    }

    private async Task FailRowAsync(int id, string? gateJson, string code, string message, CancellationToken cancellationToken)
    {
        string json = gateJson ?? await ExistingGateJsonAsync(id, cancellationToken);
        await Context.Releases.MarkFailedAsync(id, WithError(json, code, Context.Redact(message)), cancellationToken);
    }

    private async Task<string> ExistingGateJsonAsync(int id, CancellationToken cancellationToken) =>
        (await Context.Releases.GetAsync(id, cancellationToken))?.KapiRaporu ?? "{}";

    private static string WithError(string? existing, string code, string message)
    {
        JsonObject node;
        try
        {
            node = JsonNode.Parse(string.IsNullOrWhiteSpace(existing) ? "{}" : existing) as JsonObject ?? new JsonObject();
        }
        catch (JsonException)
        {
            node = new JsonObject();
        }

        node["hata"] = new JsonObject { ["kod"] = code, ["mesaj"] = message };
        return node.ToJsonString();
    }

    private string StorageMessage(StorageException ex) =>
        Context.Redact(Inv($"Depo hatasi ({ex.Failure}): {ex.Message}"));

    private static Manifest ParseManifest(ReadOnlySpan<byte> bytes, string what)
    {
        try
        {
            return ManifestJson.Read(bytes);
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or FormatException or KeyNotFoundException)
        {
            throw new PublisherException(ExitCodes.Verification, $"Manifest okunamadi ({what}): {ex.Message}", ex);
        }
    }

    private static ManifestPackInput ToInput(ManifestPack pack) => new(
        pack.PackId,
        pack.Version,
        pack.Sha256,
        pack.SizeBytes,
        pack.MinAppVersion,
        pack.DependsOn,
        pack.SchemaVersion,
        pack.Title,
        pack.Bundled);

    private void Say(string line) => Context.Out.WriteLine(Context.Redact(line));
}
