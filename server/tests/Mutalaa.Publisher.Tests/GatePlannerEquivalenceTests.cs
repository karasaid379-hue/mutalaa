using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// A14.6a: GatePlanner (Infrastructure) ile Yayinlayicinin kuru calistirma kapi raporu AYNI olmali. Karsilastirma fikstur veritabaninda
/// (gercek PostgreSQL + gercek SeaweedFS) uc derleme turu icin, onceki yayin yokken ve varken (capa surekliligi dahil), paket birlestirme
/// atlanarak (SkipAssembly) ve atlanmayarak yapilir.
/// </summary>
public class GatePlannerEquivalenceTests(PostgresFixture postgres, SeaweedFixture seaweed)
{
    public static TheoryData<BuildFlavor> Flavors => new() { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public };

    private static async Task<string> DryRunReportAsync(EndToEndHarness harness, BuildFlavor flavor, string[]? packs)
    {
        await harness.PublishAsync(flavor, packs, dryRun: true);
        return await File.ReadAllTextAsync(
            Path.Combine(harness.ReportsDir, $"{flavor.ToLabel()}-2026-11-09", "gate-report.json"),
            TestContext.Current.CancellationToken);
    }

    private static Task<GatePlan> PlanAsync(EndToEndHarness harness, BuildFlavor flavor, string[]? packs, bool skipAssembly) =>
        GatePlanner.PlanAsync(
            new GatePlanRequest(
                harness.Database.ConnectionString,
                flavor,
                packs ?? [],
                harness.Catalog,
                Path.GetFullPath(harness.SourcesDir),
                Path.GetFullPath(harness.RawDir),
                PromoteFrom: null,
                new StoreBackedPackResolver(harness.Reader, Path.Combine(harness.Directory.Path, "onceki")),
                skipAssembly),
            TestContext.Current.CancellationToken);

    private static async Task AssertEquivalentAsync(EndToEndHarness harness, BuildFlavor flavor, string[]? packs = null)
    {
        string dryRun = await DryRunReportAsync(harness, flavor, packs);
        GatePlan skipped = await PlanAsync(harness, flavor, packs, skipAssembly: true);
        GatePlan assembled = await PlanAsync(harness, flavor, packs, skipAssembly: false);

        Assert.Equal(dryRun, skipped.Report.ToJson() + "\n");
        Assert.Equal(dryRun, assembled.Report.ToJson() + "\n");

        // SkipAssembly yalniz paket icerigini ve ozetini atlar; kapiya giren paket kumesi ayni kalir.
        Assert.Equal(assembled.Planned.Select(p => p.Definition.PackId), skipped.Planned.Select(p => p.Definition.PackId));
        Assert.All(skipped.Planned, p => Assert.Equal((null, null), (p.Content, p.Digest)));
        Assert.All(assembled.Planned, p => Assert.False(string.IsNullOrEmpty(p.Digest)));
        Assert.Equal(assembled.SourceDigests, skipped.SourceDigests);
        Assert.Equal(assembled.Warnings, skipped.Warnings);
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task Without_a_previous_release_the_plan_report_equals_the_dry_run_report(BuildFlavor flavor)
    {
        await using EndToEndHarness harness = await EndToEndHarness.CreateAsync(postgres, seaweed);

        await AssertEquivalentAsync(harness, flavor);
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task With_a_previous_release_the_plan_report_equals_the_dry_run_report_including_anchor_continuity(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await EndToEndHarness.CreateAsync(postgres, seaweed);
        foreach (BuildFlavor each in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            Assert.Equal(ExitCodes.Success, (await harness.PublishAsync(each)).ExitCode);
        }

        // Degisiklik yok: onceki yayinin butun capalari kapsamda.
        await AssertEquivalentAsync(harness, flavor);

        // Onayli birim taslaga doner: public'te onceki capa kapsam disi kalir (capa-kayboldu), dev ve internal'da kalir.
        await harness.Database.ExecuteAsync(
            "UPDATE icerik.unit SET metin_durumu = 'taslak'::icerik.metin_durumu WHERE anchor = @a",
            ct,
            ("a", EndToEndData.SentetikApproved));
        await AssertEquivalentAsync(harness, flavor);

        GatePlan plan = await PlanAsync(harness, flavor, null, skipAssembly: true);
        Assert.Equal(flavor == BuildFlavor.Public, plan.Report.Rejected);
        if (flavor == BuildFlavor.Public)
        {
            Assert.Contains(plan.Report.Violations, v => v.Reason.StartsWith("capa-kayboldu", StringComparison.Ordinal));
        }
    }

    [Fact]
    public async Task A_selection_of_packs_carries_the_rest_from_the_previous_manifest_and_stays_equivalent()
    {
        await using EndToEndHarness harness = await EndToEndHarness.CreateAsync(postgres, seaweed);
        Assert.Equal(ExitCodes.Success, (await harness.PublishAsync(BuildFlavor.Dev)).ExitCode);

        string[] selection = ["hadis-sentetik"];
        await AssertEquivalentAsync(harness, BuildFlavor.Dev, selection);

        GatePlan plan = await PlanAsync(harness, BuildFlavor.Dev, selection, skipAssembly: false);
        Assert.Equal(["hadis-sentetik"], plan.Planned.Select(p => p.Definition.PackId).ToArray());
        Assert.NotEmpty(plan.CarriedVerbatim);
        Assert.DoesNotContain(plan.CarriedVerbatim, p => p.PackId == "hadis-sentetik");
    }
}
