using System.Text;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using static Mutalaa.Publisher.Pipeline.Files;

namespace Mutalaa.Publisher.Pipeline;

public sealed partial class ReleasePipeline
{
    /// <summary>Derleme asamasinin girdisi. Surum kuru calistirmada null olabilir. PromoteFrom yalniz terfide dolu (P-14).</summary>
    private sealed record BuildSpec(
        BuildFlavor Flavor,
        string? Surum,
        string DataVersion,
        IReadOnlyList<string> Packs,
        bool DryRun,
        string OutRoot,
        ReleaseDigests? PromoteFrom);

    private sealed class BuildOutcome
    {
        public required GateReport Report { get; init; }

        public required ReleaseDigests Digests { get; init; }

        public byte[]? ManifestBytes { get; init; }

        public IReadOnlyList<PackBuild> Packs { get; init; } = [];

        public IReadOnlyList<PackSelfCheckReport> SelfChecks { get; init; } = [];
    }

    private async Task<ReleaseResult> DryRunAsync(
        BuildFlavor flavor,
        IReadOnlyList<string> packs,
        string outRoot,
        ReleaseDigests? promoteFrom,
        CancellationToken cancellationToken)
    {
        _ = Context.ConnectionString;
        string label = flavor.ToLabel();
        BuildSpec spec = new(flavor, null, await Context.DataVersionAsync(cancellationToken), packs, DryRun: true, outRoot, promoteFrom);
        BuildOutcome outcome = await BuildAsync(spec, cancellationToken);

        string directory = Path.Combine(
            Path.GetFullPath(Context.Options.ReportsDir),
            Inv($"{label}-{Context.Clock.GetUtcNow().UtcDateTime:yyyy-MM-dd}"));
        string gateJson = outcome.Report.ToJson();
        await WriteTextAsync(Path.Combine(directory, "gate-report.json"), gateJson + "\n", cancellationToken);

        Say(Inv($"kuru calistirma: {label} (release satiri ve depo yazilmadi)"));
        PrintReport(outcome.Report);
        foreach (PackBuild pack in outcome.Packs.Where(p => !p.Carried && p.ContentDigest.Length >= 12))
        {
            Say(Inv($"paket {pack.PackId}: yeni derlenir ozet={pack.ContentDigest[..12]}"));
        }

        Say(Inv($"rapor: {directory}"));
        return outcome.Report.Rejected
            ? ReleaseResult.Fail(ExitCodes.GateRejected, "Kapi yayini reddetti (ihlal var).")
            : ReleaseResult.Ok(null, null, "Kapi gecti (kuru calistirma).", outcome.Packs);
    }

    private async Task<ReleaseResult> RunRowAsync(
        Release row,
        IReadOnlyList<string> packs,
        string outRoot,
        ReleaseDigests? promoteFrom,
        bool stopAtVerified,
        CancellationToken cancellationToken)
    {
        string label = row.Derleme.ToLabel();
        RequireVersion(row.Surum);
        switch (row.Durum)
        {
            case ReleaseStatus.Yayinlandi:
                return ReleaseResult.Fail(ExitCodes.Other, $"Yayin zaten yayinlandi: {label} {row.Surum}.", row.Surum, row.Durum);
            case ReleaseStatus.Dogrulandi:
                return stopAtVerified
                    ? ReleaseResult.Ok(row.Surum, row.Durum, $"Yayin zaten dogrulandi: {label} {row.Surum}.")
                    : await UploadRowAsync(row, outRoot, cancellationToken);
            case ReleaseStatus.Hazirlaniyor:
                break;
            default:
                return ReleaseResult.Fail(ExitCodes.Other, $"Yayin islenemez, durum: {row.Durum.ToLabel()} ({row.Surum}).", row.Surum, row.Durum);
        }

        Say(Inv($"yayin: {label} {row.Surum} ({row.Talep})"));
        BuildSpec spec = new(row.Derleme, row.Surum, row.DataVersion, packs, DryRun: false, outRoot, promoteFrom);
        BuildOutcome outcome;
        try
        {
            outcome = await BuildAsync(spec, cancellationToken);
        }
        catch (PackWriteException ex) when (ex.Report is not null)
        {
            await FailRowAsync(row.Id, null, "oz-denetim", ex.Message, cancellationToken);
            return ReleaseResult.Fail(ExitCodes.Verification, Context.Redact(ex.Message), row.Surum, ReleaseStatus.Basarisiz);
        }

        string directory = ReleaseDir(outRoot, label, row.Surum);
        string gateJson = outcome.Report.ToJson();
        await WriteTextAsync(Path.Combine(directory, "gate-report.json"), gateJson + "\n", cancellationToken);
        PrintReport(outcome.Report);

        if (outcome.Report.Rejected)
        {
            await Context.Releases.MarkFailedAsync(row.Id, gateJson, cancellationToken);
            return ReleaseResult.Fail(ExitCodes.GateRejected, "Kapi yayini reddetti; satir basarisiz, manifest yayimlanmadi.", row.Surum, ReleaseStatus.Basarisiz);
        }

        byte[] manifestBytes = outcome.ManifestBytes
            ?? throw new InvalidOperationException("Manifest uretilmedi.");
        await WriteBytesAsync(Path.Combine(directory, "manifest.json"), manifestBytes, cancellationToken);
        await WriteTextAsync(Path.Combine(directory, "self-check.json"), SelfCheckJson(row.Surum, outcome.SelfChecks), cancellationToken);

        await Context.Releases.MarkVerifiedAsync(
            row.Id,
            Encoding.UTF8.GetString(manifestBytes),
            gateJson,
            outcome.Digests.ToJson(),
            packs.Count > 0 ? [.. packs] : null,
            cancellationToken);
        Say(Inv($"dogrulandi: {label} {row.Surum} ({outcome.Packs.Count} paket)"));

        if (stopAtVerified)
        {
            return ReleaseResult.Ok(row.Surum, ReleaseStatus.Dogrulandi, $"Yayin dogrulandi, yukleme yapilmadi: {label} {row.Surum}.", outcome.Packs);
        }

        ReleaseResult uploaded = await UploadRowAsync(row, outRoot, cancellationToken);
        return uploaded.Success ? uploaded with { Packs = outcome.Packs } : uploaded;
    }

    private async Task<BuildOutcome> BuildAsync(BuildSpec spec, CancellationToken cancellationToken)
    {
        BuildFlavor flavor = spec.Flavor;
        string label = flavor.ToLabel();

        // Asama A (kapi plani) Infrastructure'dadir: GatePlanner dosya yazmaz; Yayinlayici yalniz onceki paket dosyalarini cozer.
        GatePlan plan;
        try
        {
            plan = await GatePlanner.PlanAsync(
                new GatePlanRequest(
                    Context.ConnectionString,
                    flavor,
                    spec.Packs,
                    Context.Catalog,
                    Path.GetFullPath(Context.Options.SourcesDir),
                    Path.GetFullPath(Context.Options.RawDir),
                    spec.PromoteFrom,
                    new PublisherPackResolver(Context, spec.OutRoot)),
                cancellationToken);
        }
        catch (GatePlanException ex)
        {
            throw ToPublisherException(ex);
        }

        foreach (string warning in plan.Warnings)
        {
            Say(warning);
        }

        EditorialSnapshot snapshot = plan.Snapshot;
        Manifest? previousManifest = plan.PreviousManifest;
        ReleaseDigests previousDigests = plan.PreviousDigests;
        IReadOnlyList<ManifestPack> carriedVerbatim = plan.CarriedVerbatim;
        IReadOnlyDictionary<string, string> sourceDigests = plan.SourceDigests;
        GateReport report = plan.Report;
        if (report.Rejected)
        {
            return new BuildOutcome { Report = report, Digests = new ReleaseDigests(sourceDigests, new Dictionary<string, string>(StringComparer.Ordinal)) };
        }

        // Asama B: onceki yayinla ayni ozet tasinir; degilse yazilir.
        SqlitePackWriter? writer = spec.DryRun ? null : new SqlitePackWriter(PackDefinitions.Load(Context.Options.SchemaDir), Context.Clock);
        List<ManifestPackInput> inputs = [];
        List<PackBuild> builds = [];
        List<PackSelfCheckReport> selfChecks = [];
        Dictionary<string, string> packDigests = new(StringComparer.Ordinal);

        foreach (PlannedPack item in plan.Planned)
        {
            cancellationToken.ThrowIfCancellationRequested();
            PackDefinition definition = item.Definition;
            PackContent content = item.Content ?? throw new InvalidOperationException("Paket icerigi planlanmadi.");
            string digest = item.Digest ?? throw new InvalidOperationException("Paket ozeti planlanmadi.");
            ManifestPack? prev = previousManifest?.Packs.FirstOrDefault(p => string.Equals(p.PackId, definition.PackId, StringComparison.Ordinal));
            bool same = prev is not null
                && previousDigests.Packs.TryGetValue(definition.PackId, out string? previousDigest)
                && string.Equals(previousDigest, digest, StringComparison.Ordinal);

            packDigests[definition.PackId] = digest;
            if (same && prev is not null)
            {
                inputs.Add(new ManifestPackInput(
                    prev.PackId, prev.Version, prev.Sha256, prev.SizeBytes, Context.Options.MinAppVersion, definition.DependsOn, prev.SchemaVersion, definition.Title, definition.Bundled));
                builds.Add(new PackBuild(prev.PackId, prev.Version, prev.Sha256, prev.SizeBytes, Carried: true, digest));
                Say(Inv($"paket {definition.PackId}: ozet ayni, onceki surum {prev.Version} tasindi"));
                continue;
            }

            if (writer is null)
            {
                builds.Add(new PackBuild(definition.PackId, string.Empty, string.Empty, 0, Carried: false, digest));
                continue;
            }

            PackFile file = await writer.WriteAsync(
                content,
                new PackWriteRequest(spec.OutRoot, spec.Surum!, spec.DataVersion, snapshot.Sources, digest),
                cancellationToken);
            inputs.Add(new ManifestPackInput(
                definition.PackId, spec.Surum!, file.Sha256, file.SizeBytes, Context.Options.MinAppVersion, definition.DependsOn, definition.SchemaVersion, definition.Title, definition.Bundled));
            builds.Add(new PackBuild(definition.PackId, spec.Surum!, file.Sha256, file.SizeBytes, Carried: false, digest));
            selfChecks.Add(file.SelfCheck);
            Say(Inv($"paket {definition.PackId}: yazildi {file.SizeBytes} bayt sha256={file.Sha256[..12]}"));
        }

        foreach (ManifestPack pack in carriedVerbatim)
        {
            inputs.Add(ToInput(pack));
            builds.Add(new PackBuild(pack.PackId, pack.Version, pack.Sha256, pack.SizeBytes, Carried: true, previousDigests.Packs.GetValueOrDefault(pack.PackId) ?? string.Empty));
            if (previousDigests.Packs.TryGetValue(pack.PackId, out string? carriedDigest))
            {
                packDigests[pack.PackId] = carriedDigest;
            }
        }

        ReleaseDigests digests = new(sourceDigests, packDigests);
        if (spec.DryRun)
        {
            return new BuildOutcome { Report = report, Digests = digests, Packs = builds };
        }

        if (inputs.Count == 0)
        {
            throw new PublisherException(ExitCodes.Other, "Manifestte hic paket yok (kapidan giren paket bulunamadi).", isPermanent: true);
        }

        Manifest manifest = ManifestBuilder.Build(label, spec.Surum!, Context.Clock.GetUtcNow(), Context.PublicBaseUrl, inputs);
        byte[] signed = ManifestSigner.Sign(ManifestJson.Write(manifest), Context.GetSigningKey(flavor));
        return new BuildOutcome { Report = report, Digests = digests, ManifestBytes = signed, Packs = builds, SelfChecks = selfChecks };
    }

    private static PublisherException ToPublisherException(GatePlanException ex) => new(
        ex.Failure switch
        {
            GatePlanFailure.PreviousPackMissing => ExitCodes.Storage,
            GatePlanFailure.ManifestUnreadable or GatePlanFailure.PreviousPackMismatch => ExitCodes.Verification,
            _ => ExitCodes.Other,
        },
        ex.Message,
        ex,
        ex.IsPermanent);

    private void PrintReport(GateReport report)
    {
        int entered = report.Rows.Count(r => r.Decision == GateDecision.Girdi);
        int skipped = report.Rows.Count(r => r.Decision == GateDecision.Girmedi);
        Say(Inv($"kapi {report.Flavor.ToLabel()}: girdi={entered} girmedi={skipped} ihlal={report.Violations.Count}"));
        foreach (GateReportRow row in report.Rows)
        {
            string rule = row.Rule is null ? "-" : row.Rule.Value.ToCode();
            Say(Inv($"  {row.Kind.ToLabel()} {row.Id}: {row.Decision.ToLabel()} [{rule}] {row.Reason} x{row.Count}"));
        }

        // Her (kural, gerekce) grubunda ilk GateReport.MaxViolationsShown ihlal yazilir; ihlal= toplam sayiyi korur.
        foreach (string line in report.ViolationLines())
        {
            Say(line);
        }
    }

    private static string SelfCheckJson(string surum, IReadOnlyList<PackSelfCheckReport> reports)
    {
        StringBuilder builder = new();
        builder.Append("{\n  \"release\": ").Append(JsonStringLiteral(surum)).Append(",\n  \"packs\": [");
        for (int i = 0; i < reports.Count; i++)
        {
            builder.Append(i == 0 ? "\n" : ",\n").Append(reports[i].ToJson().TrimEnd('\n'));
        }

        builder.Append(reports.Count == 0 ? "]\n}\n" : "\n  ]\n}\n");
        return builder.ToString();
    }

    private static string JsonStringLiteral(string value) => System.Text.Json.JsonSerializer.Serialize(value);
}
