using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// Onceki yayinin paket dosyasini yerel bir yola cozer (kapi, onceki yayinin butun capalarini bu dosyalardan okur). Yayinlayici once cikti
/// klasorune, sonra gecici onbellege, sonra depoya (sha256 denetimiyle) bakar; API kendi cozucusunu verir. Dosya yoksa ya da sha256 manifestle
/// uyusmuyorsa <see cref="GatePlanException"/> atar.
/// </summary>
public interface IPreviousPackResolver
{
    Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken);
}

/// <summary>Kapi planinin girdisi. Yollar tam yoldur (cagiran <see cref="Path.GetFullPath(string)"/> uygular).</summary>
/// <param name="SelectedPackIds">Bos ise katalogdaki butun paketler; dolu ise yalniz bunlar yeniden uretilir, ote kalanlar onceki manifestten tasinir.</param>
/// <param name="PromoteFrom">Terfide kaynak (internal) yayinin ozetleri; dolu ise P-14 denetlenir.</param>
/// <param name="SkipAssembly">
/// Onizleme: paket birlestirme ve paket ozeti atlanir (<see cref="PlannedPack.Content"/> ve <see cref="PlannedPack.Digest"/> null). Kapi raporu
/// gercek derlemeyle aynidir: P-13 yalniz paket tanimlarina bakar.
/// </param>
public sealed record GatePlanRequest(
    string ConnectionString,
    BuildFlavor Flavor,
    IReadOnlyList<string> SelectedPackIds,
    PackCatalog Catalog,
    string SourcesDir,
    string RawDir,
    ReleaseDigests? PromoteFrom,
    IPreviousPackResolver PreviousPacks,
    bool SkipAssembly = false);

/// <summary>Kapiya giren ve bu derlemede uretilecek bir paket. Content ve Digest yalniz <see cref="GatePlanRequest.SkipAssembly"/> false iken dolu.</summary>
public sealed record PlannedPack(PackDefinition Definition, PackContent? Content, string? Digest);

/// <summary>
/// Kapi planinin sonucu: B asamasinin (paket yazimi, manifest, imza) ihtiyaci olan her sey. <see cref="Report"/> reddedildiyse
/// (<see cref="GateReport.Rejected"/>) B asamasina gecilmez.
/// </summary>
public sealed record GatePlan(
    EditorialSnapshot Snapshot,
    Manifest? PreviousManifest,
    ReleaseDigests PreviousDigests,
    IReadOnlyList<ManifestPack> CarriedVerbatim,
    GateResult Gate,
    IReadOnlyList<PlannedPack> Planned,
    IReadOnlyDictionary<string, string> SourceDigests,
    GateReport Report,
    IReadOnlyList<string> Warnings);

/// <summary>Kapi planinin hata turu (cagiranin cikis kodu eslemesi icin).</summary>
public enum GatePlanFailure
{
    /// <summary>Onceki yayinin satirinda manifest yok (kalici).</summary>
    PreviousManifestMissing,

    /// <summary>Onceki (ya da hedef) manifest okunamadi.</summary>
    ManifestUnreadable,

    /// <summary>Onceki yayinin paketi depoda ya da yerelde yok.</summary>
    PreviousPackMissing,

    /// <summary>Onceki yayinin paketinin sha256 degeri manifestle uyusmuyor.</summary>
    PreviousPackMismatch,
}

/// <summary>Beklenen, anlatilabilir kapi plani hatasi: iletide gizli deger bulunmaz. IsPermanent: yeniden denemek sonucu degistirmez.</summary>
public sealed class GatePlanException : Exception
{
    public GatePlanException(GatePlanFailure failure, string message, bool isPermanent = false)
        : base(message)
    {
        Failure = failure;
        IsPermanent = isPermanent;
    }

    public GatePlanException(GatePlanFailure failure, string message, Exception innerException, bool isPermanent = false)
        : base(message, innerException)
    {
        Failure = failure;
        IsPermanent = isPermanent;
    }

    public GatePlanFailure Failure { get; }

    public bool IsPermanent { get; }
}

/// <summary>
/// Yayin kapisinin planlama asamasi (A asamasi; Backend API 10.2): anlik goruntu, onceki yayin, kapi degerlendirmesi, ham dosya denetimi, kaynak
/// ozetleri, P-14 ve P-13, paket birlestirme ve ozetleme. Dosya yazmaz, depo ve imza anahtarina dokunmaz. Yayinlayici ve API ayni kodu kullanir.
/// </summary>
public static class GatePlanner
{
    public static async Task<GatePlan> PlanAsync(GatePlanRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Catalog);
        ArgumentNullException.ThrowIfNull(request.PreviousPacks);

        BuildFlavor flavor = request.Flavor;
        string label = flavor.ToLabel();
        List<string> warnings = [];

        EditorialSnapshot snapshot;
        await using (EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(request.ConnectionString, cancellationToken))
        {
            snapshot = await reader.LoadAsync(flavor, cancellationToken);
        }

        Manifest? previousManifest = null;
        ReleaseDigests previousDigests = ReleaseDigests.Empty;
        if (snapshot.PreviousRelease is { } previous)
        {
            previousManifest = previous.Manifest is null
                ? throw new GatePlanException(GatePlanFailure.PreviousManifestMissing, $"Onceki yayinin manifesti yok: {label} {previous.Surum}.", isPermanent: true)
                : ParseManifest(Encoding.UTF8.GetBytes(previous.Manifest), $"onceki yayin {previous.Surum}");
            previousDigests = ReleaseDigests.Parse(previous.Ozetler);
        }

        HashSet<string> selected = new(request.SelectedPackIds, StringComparer.Ordinal);
        List<ManifestPack> carriedVerbatim = previousManifest is null || selected.Count == 0
            ? []
            : [.. previousManifest.Packs.Where(p => !selected.Contains(p.PackId))];

        HashSet<string> previousAnchors = previousManifest is null
            ? []
            : await LoadPreviousAnchorsAsync(label, previousManifest, request.PreviousPacks, cancellationToken);

        GateInput input = GateInputBuilder.Build(
            snapshot,
            request.Catalog,
            request.SourcesDir,
            [.. carriedVerbatim.Select(p => p.PackId)],
            previousAnchors);
        GateResult gate = GateEvaluator.Evaluate(flavor, input);

        List<GateViolation> extra = [.. new TanzilRawVerifier(request.RawDir).VerifyAll(snapshot, gate.IncludedSources)];
        IReadOnlyDictionary<string, string> sourceDigests = SourceDigests.Compute(snapshot, gate.IncludedSources);
        if (request.PromoteFrom is not null)
        {
            extra.AddRange(GateEvaluator.EvaluateP14(request.PromoteFrom.Sources, sourceDigests));
        }

        // Paketleri topla ve ozetle (dosya yazilmaz); manifest kumesi icin P-13 gercek kumeyle yeniden denetlenir.
        List<PlannedPack> planned = [];
        foreach (PackDefinition definition in request.Catalog.All)
        {
            if (!gate.IncludedPacks.Contains(definition.PackId) || (selected.Count > 0 && !selected.Contains(definition.PackId)))
            {
                continue;
            }

            if (request.SkipAssembly)
            {
                planned.Add(new PlannedPack(definition, null, null));
                continue;
            }

            PackContent content = PackAssembler.Assemble(definition, flavor, snapshot, gate, request.Catalog);
            planned.Add(new PlannedPack(definition, content, PackDigest.Compute(content)));
        }

        foreach (string id in selected.Order(StringComparer.Ordinal))
        {
            if (!gate.IncludedPacks.Contains(id))
            {
                warnings.Add($"uyari: istenen paket kapidan girmedi: {id}");
            }
        }

        List<GatePack> finalPacks =
        [
            .. planned.Select(p => new GatePack(p.Definition.PackId, p.Definition.DependsOn, [], true)),
            .. carriedVerbatim.Select(p => new GatePack(p.PackId, p.DependsOn, [], true)),
        ];
        extra.AddRange(GateEvaluator.EvaluateP13(finalPacks, [.. finalPacks.Select(p => p.PackId)]));

        return new GatePlan(
            snapshot,
            previousManifest,
            previousDigests,
            carriedVerbatim,
            gate,
            planned,
            sourceDigests,
            gate.Report.WithViolations(extra),
            warnings);
    }

    private static async Task<HashSet<string>> LoadPreviousAnchorsAsync(
        string label,
        Manifest previous,
        IPreviousPackResolver resolver,
        CancellationToken cancellationToken)
    {
        HashSet<string> anchors = new(StringComparer.Ordinal);
        foreach (ManifestPack pack in previous.Packs)
        {
            string path = await resolver.ResolveAsync(label, pack, cancellationToken);
            foreach (string anchor in PackInspector.ReadUnitAnchors(path))
            {
                anchors.Add(anchor);
            }
        }

        return anchors;
    }

    private static Manifest ParseManifest(ReadOnlySpan<byte> bytes, string what)
    {
        try
        {
            return ManifestJson.Read(bytes);
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or FormatException or KeyNotFoundException)
        {
            throw new GatePlanException(GatePlanFailure.ManifestUnreadable, $"Manifest okunamadi ({what}): {ex.Message}", ex);
        }
    }
}
