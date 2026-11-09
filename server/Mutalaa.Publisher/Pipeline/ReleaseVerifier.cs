using System.Globalization;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using static Mutalaa.Publisher.Pipeline.Files;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>verify istegi. ManifestPath verilirse manifest yerel dosyadan, verilmezse depodan okunur; PublicKey base64 (32 bayt).</summary>
public sealed record VerifyRequest(BuildFlavor Flavor, string? ManifestPath = null, string? EmbeddedCorePath = null, string? PublicKey = null);

/// <summary>Dogrulama bulgusu: kararli kod ve ileti.</summary>
public sealed record VerifyFinding(string Code, string Message);

/// <summary>
/// verify (Yayin sureci 5; Backend API 10.1): imza, sema, adres, boyut, sha256, paket dosyasi (pack_meta, P-12, oz denetim), P-13,
/// depodaki her nesnenin manifestte ya da manifest gecmisinde bulunmasi ve gomulu core. Veritabani gerekmez (CI yapit taramasi).
/// Bulgu varsa 3; depoya ulasilamazsa 4.
/// </summary>
public sealed class ReleaseVerifier(PublisherContext context)
{
    public async Task<ReleaseResult> VerifyAsync(VerifyRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        IReadOnlyList<VerifyFinding> findings;
        try
        {
            findings = await RunAsync(request, cancellationToken);
        }
        catch (StorageException ex)
        {
            return ReleaseResult.Fail(ExitCodes.Storage, context.Redact(Inv($"Depo hatasi ({ex.Failure}): {ex.Message}")));
        }

        foreach (VerifyFinding finding in findings)
        {
            context.Out.WriteLine(context.Redact(Inv($"BULGU [{finding.Code}] {finding.Message}")));
        }

        return findings.Count == 0
            ? ReleaseResult.Ok(null, null, $"Dogrulama tamam: {request.Flavor.ToLabel()}.")
            : ReleaseResult.Fail(ExitCodes.Verification, Inv($"Dogrulama basarisiz: {findings.Count} bulgu."));
    }

    /// <summary>Bulgu listesini dondurur (bos = gecti). StorageException yayilir.</summary>
    public async Task<IReadOnlyList<VerifyFinding>> RunAsync(VerifyRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        BuildFlavor flavor = request.Flavor;
        string label = flavor.ToLabel();
        List<VerifyFinding> findings = [];
        IPackStore store = context.GetStore();

        byte[]? manifestBytes;
        if (request.ManifestPath is not null)
        {
            manifestBytes = File.Exists(request.ManifestPath) ? await File.ReadAllBytesAsync(request.ManifestPath, cancellationToken) : null;
        }
        else
        {
            manifestBytes = await store.GetAsync(StorageKeys.Manifest(label), cancellationToken);
        }

        if (manifestBytes is null)
        {
            findings.Add(new VerifyFinding("manifest-yok", "Manifest bulunamadi."));
            return findings;
        }

        // Imza: acik anahtar --public-key, Signing:{f}:PublicKey ya da ozel anahtardan turetilir.
        byte[] publicKey = context.GetPublicKey(flavor, request.PublicKey);
        string? expectedKid = request.PublicKey is null ? context.Configuration[$"Signing:{label}:Kid"] : null;
        ManifestVerification signature = ManifestVerifier.Verify(manifestBytes, publicKey, string.IsNullOrWhiteSpace(expectedKid) ? null : expectedKid);
        foreach (ManifestError error in signature.Errors)
        {
            findings.Add(new VerifyFinding(error.Code, error.Message));
        }

        // Sema ve adres deseni.
        string schemaPath = context.Options.ResolveManifestSchemaPath();
        if (!File.Exists(schemaPath))
        {
            throw new PublisherException(ExitCodes.Other, $"Manifest semasi bulunamadi: {schemaPath}");
        }

        ManifestValidation validation = ManifestSchemaValidator.FromFile(schemaPath)
            .Validate(manifestBytes, string.IsNullOrWhiteSpace(context.Storage.PublicBaseUrl) ? null : context.Storage.PublicBaseUrl);
        foreach (ManifestError error in validation.Errors)
        {
            findings.Add(new VerifyFinding(error.Code, error.Message));
        }

        Manifest manifest;
        try
        {
            manifest = ManifestJson.Read(manifestBytes);
        }
        catch (Exception ex) when (ex is System.Text.Json.JsonException or InvalidOperationException or FormatException or KeyNotFoundException)
        {
            findings.Add(new VerifyFinding("manifest-okunamadi", ex.Message));
            return findings;
        }

        if (!string.Equals(manifest.Flavor, label, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("flavor-uyumsuz", $"Manifest flavor degeri '{manifest.Flavor}', beklenen '{label}'."));
        }

        // Anahtar parcalari (release, pack_id, version) depo anahtarina girmeden once desenle denetlenir: egik cizgi ya da '..' iceren deger
        // ArgumentException yerine bulgu uretir ve depoya hic gidilmez.
        bool keyPartsValid = true;
        if (!IsValidVersion(manifest.Release))
        {
            findings.Add(new VerifyFinding("manifest-anahtar-gecersiz", "Manifest release degeri gecerli bir CalVer (YYYY.M.N) degil."));
            keyPartsValid = false;
        }

        foreach (ManifestPack pack in manifest.Packs)
        {
            if (!IsValidPackId(pack.PackId))
            {
                findings.Add(new VerifyFinding("manifest-anahtar-gecersiz", "Manifestte gecersiz bir pack_id var (kucuk harfle baslayan kucuk harf, rakam ve tire bekleniyor)."));
                keyPartsValid = false;
            }

            if (!IsValidVersion(pack.Version))
            {
                findings.Add(new VerifyFinding("manifest-anahtar-gecersiz", "Manifestte gecersiz bir paket surumu var (CalVer YYYY.M.N bekleniyor)."));
                keyPartsValid = false;
            }
        }

        if (!keyPartsValid)
        {
            return findings;
        }

        if (await store.HeadAsync(StorageKeys.ManifestHistory(label, manifest.Release), cancellationToken) is null)
        {
            findings.Add(new VerifyFinding("manifest-gecmisi-yok", $"Manifest gecmisi nesnesi yok: {StorageKeys.ManifestHistory(label, manifest.Release)}"));
        }

        PackDefinitions definitions = PackDefinitions.Load(context.Options.SchemaDir);
        foreach (ManifestPack pack in manifest.Packs)
        {
            await VerifyPackAsync(label, flavor, pack, definitions, store, findings, cancellationToken);
        }

        // P-13: depends_on dongusuz ve her bagimlilik ayni manifestte.
        List<GatePack> gatePacks = [.. manifest.Packs.Select(p => new GatePack(p.PackId, p.DependsOn, [], true))];
        foreach (GateViolation violation in GateEvaluator.EvaluateP13(gatePacks, [.. gatePacks.Select(p => p.PackId)]))
        {
            findings.Add(new VerifyFinding("P-13", $"{violation.Subject}: {violation.Reason}"));
        }

        // packs/{f}/ altindaki her nesne gecerli manifestte ya da manifest gecmisinde olmali.
        HashSet<string> known = new(StringComparer.Ordinal);
        foreach (ManifestPack pack in manifest.Packs)
        {
            known.Add(StorageKeys.Pack(label, pack.PackId, pack.Version));
        }

        Dictionary<string, HashSet<string>> corePackHashes = new(StringComparer.Ordinal);
        AddCoreHash(corePackHashes, manifest);
        await foreach (string historyKey in store.ListKeysAsync($"{label}/manifests/", cancellationToken))
        {
            byte[]? historyBytes = await store.GetAsync(historyKey, cancellationToken);
            if (historyBytes is null)
            {
                continue;
            }

            try
            {
                Manifest history = ManifestJson.Read(historyBytes);
                foreach (ManifestPack pack in history.Packs)
                {
                    known.Add(StorageKeys.Pack(label, pack.PackId, pack.Version));
                }

                AddCoreHash(corePackHashes, history);
            }
            catch (Exception ex) when (ex is System.Text.Json.JsonException or InvalidOperationException or FormatException or KeyNotFoundException or ArgumentException)
            {
                findings.Add(new VerifyFinding("gecmis-manifest-bozuk", $"{historyKey}: {ex.Message}"));
            }
        }

        await foreach (string key in store.ListKeysAsync($"packs/{label}/", cancellationToken))
        {
            if (!known.Contains(key))
            {
                findings.Add(new VerifyFinding("nesne-manifestte-yok", $"Depodaki nesne ne gecerli manifestte ne gecmiste var: {key}"));
            }
        }

        if (request.EmbeddedCorePath is not null)
        {
            await VerifyEmbeddedCoreAsync(request.EmbeddedCorePath, corePackHashes, findings, cancellationToken);
        }

        return findings;
    }

    private static void AddCoreHash(Dictionary<string, HashSet<string>> hashes, Manifest manifest)
    {
        foreach (ManifestPack pack in manifest.Packs)
        {
            if (string.Equals(pack.PackId, PackCatalog.CorePackId, StringComparison.Ordinal))
            {
                if (!hashes.TryGetValue("core", out HashSet<string>? set))
                {
                    set = new HashSet<string>(StringComparer.Ordinal);
                    hashes["core"] = set;
                }

                set.Add(pack.Sha256);
            }
        }
    }

    private static async Task VerifyEmbeddedCoreAsync(string path, Dictionary<string, HashSet<string>> corePackHashes, List<VerifyFinding> findings, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            findings.Add(new VerifyFinding("gomulu-core-yok", "Gomulu core dosyasi bulunamadi."));
            return;
        }

        if (!corePackHashes.TryGetValue("core", out HashSet<string>? allowed))
        {
            findings.Add(new VerifyFinding("gomulu-core-uyusmuyor", "Manifestte ve gecmiste core paketi yok."));
            return;
        }

        string actual = await Sha256Async(path, cancellationToken);
        if (!allowed.Contains(actual))
        {
            findings.Add(new VerifyFinding("gomulu-core-uyusmuyor", "Gomulu core dosyasinin sha256 degeri manifestteki ya da gecmisteki core ile uyusmuyor."));
        }
    }

    private async Task VerifyPackAsync(
        string label,
        BuildFlavor flavor,
        ManifestPack pack,
        PackDefinitions definitions,
        IPackStore store,
        List<VerifyFinding> findings,
        CancellationToken cancellationToken)
    {
        string key = StorageKeys.Pack(label, pack.PackId, pack.Version);
        StoredObject? head = await store.HeadAsync(key, cancellationToken);
        if (head is null)
        {
            findings.Add(new VerifyFinding("paket-yok", $"Paket depoda yok: {key}"));
            return;
        }

        if (head.Size != pack.SizeBytes)
        {
            findings.Add(new VerifyFinding("paket-boyut", $"{key}: depodaki boyut manifestle uyusmuyor."));
        }

        if (head.Sha256 is not null && !string.Equals(head.Sha256, pack.Sha256, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("paket-sha256-meta", $"{key}: x-amz-meta-sha256 manifestle uyusmuyor."));
        }

        byte[]? bytes = await store.GetAsync(key, cancellationToken);
        if (bytes is null)
        {
            findings.Add(new VerifyFinding("paket-yok", $"Paket okunamadi: {key}"));
            return;
        }

        if (bytes.LongLength != pack.SizeBytes)
        {
            findings.Add(new VerifyFinding("paket-boyut", $"{key}: indirilen boyut manifestle uyusmuyor."));
        }

        if (!string.Equals(Sha256(bytes), pack.Sha256, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("paket-sha256", $"{key}: indirilen dosyanin sha256 degeri manifestle uyusmuyor."));
            return;
        }

        string temp = Path.Combine(Path.GetFullPath(context.Options.TempDir), "verify", Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture) + ".db");
        await WriteBytesAsync(temp, bytes, cancellationToken);
        try
        {
            InspectPackFile(temp, label, flavor, pack, definitions, findings);
        }
        finally
        {
            TryDelete(temp);
        }
    }

    private static void InspectPackFile(string path, string label, BuildFlavor flavor, ManifestPack pack, PackDefinitions definitions, List<VerifyFinding> findings)
    {
        PackFileMeta meta;
        IReadOnlyList<string> sources;
        IReadOnlyList<PackAttributionInfo> attributions;
        PackSelfCheckReport? report = null;
        try
        {
            meta = PackInspector.ReadMeta(path);
            sources = PackInspector.ReadPackSources(path);
            attributions = PackInspector.ReadAttributions(path);

            if (definitions.TryResolve(pack.PackId, out PackType? type))
            {
                Dictionary<string, string> expectedMeta = new(StringComparer.Ordinal)
                {
                    ["pack_id"] = pack.PackId,
                    ["version"] = pack.Version,
                    ["flavor"] = label,
                    ["schema_version"] = pack.SchemaVersion.ToString(CultureInfo.InvariantCulture),
                };
                List<SourceRow> sourceRows =
                [
                    .. attributions.Select(a => new SourceRow(
                        a.SourceId, "kitap", a.Title, null, a.Version ?? string.Empty, null, a.SourceUrl, null, null, null, a.RequiredCredit, null, a.NoticeText, null)),
                ];
                report = PackSelfCheck.RunOnFile(path, new PackSelfCheckExpectations(pack.PackId, pack.Version, definitions.ExpectedTables(type), expectedMeta, sourceRows));
            }
            else
            {
                findings.Add(new VerifyFinding("paket-turu", $"Paket kimligi hicbir ture eslesmiyor: {pack.PackId}"));
            }
        }
        catch (Microsoft.Data.Sqlite.SqliteException ex)
        {
            findings.Add(new VerifyFinding("paket-acilamadi", $"{pack.PackId}: {ex.Message}"));
            return;
        }

        if (!string.Equals(meta.PackId, pack.PackId, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("pack-meta", $"{pack.PackId}: pack_meta.pack_id manifestle uyusmuyor."));
        }

        if (!string.Equals(meta.Version, pack.Version, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("pack-meta", $"{pack.PackId}: pack_meta.version manifestle uyusmuyor."));
        }

        if (!string.Equals(meta.Flavor, label, StringComparison.Ordinal))
        {
            findings.Add(new VerifyFinding("pack-meta", $"{pack.PackId}: pack_meta.flavor '{meta.Flavor}', beklenen '{label}'."));
        }

        foreach (string source in sources)
        {
            if (!FlavorPolicy.AllowsSource(flavor, source))
            {
                findings.Add(new VerifyFinding("P-12", $"{pack.PackId}: '{label}' derlemesinde bulunmamasi gereken kaynak: {source}"));
            }
        }

        if (report is not null)
        {
            foreach (SelfCheckItem item in report.Items.Where(i => !i.Passed))
            {
                findings.Add(new VerifyFinding("oz-denetim", $"{pack.PackId}: {item.Name} ({item.Detail})"));
            }
        }
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (IOException)
        {
            // Windows/OneDrive kilidi: gecici dosya .tmp altindadir; temizlik en iyi cabadir.
        }
    }
}
