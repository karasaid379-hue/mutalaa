using System.Text.Json.Nodes;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// GatePlanner hata turleri (onceki yayinin manifesti yok / okunamadi, paketi yok, sha256 uyusmuyor) ve Yayinlayicinin bunlari ayni ileti ve
/// cikis koduyla (1 kalici, 3, 4, 3) PublisherException'a cevirmesi. Docker: gercek PostgreSQL + bellek ici sahte depo.
/// </summary>
public class GatePlannerFailureTests(PostgresFixture postgres)
{
    private static Task<ReleaseResult> PublishAsync(PublisherHarness harness) =>
        harness.Pipeline.PublishAsync(new PublishRequest(BuildFlavor.Dev, []), TestContext.Current.CancellationToken);

    private static Task<GatePlan> PlanAsync(PublisherHarness harness) =>
        GatePlanner.PlanAsync(
            new GatePlanRequest(
                harness.Database.ConnectionString,
                BuildFlavor.Dev,
                [],
                PublisherHarness.SyntheticCatalog(),
                Path.GetFullPath(harness.SourcesDir),
                Path.GetFullPath(Path.Combine(harness.Directory.Path, "raw")),
                PromoteFrom: null,
                new StoreBackedPackResolver(harness.Store, Path.Combine(harness.Directory.Path, "onceki"))),
            TestContext.Current.CancellationToken);

    private static async Task RewriteManifestAsync(PublisherHarness harness, Action<JsonObject> edit)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Release row = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!;
        JsonObject manifest = JsonNode.Parse(row.Manifest!)!.AsObject();
        edit(manifest);
        await harness.Database.ExecuteAsync(
            "UPDATE icerik.release SET manifest = @m::jsonb WHERE id = @id",
            ct,
            ("m", manifest.ToJsonString()),
            ("id", row.Id));
    }

    [Fact]
    public async Task Fails_permanently_when_the_previous_release_has_no_manifest()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Assert.Equal(ExitCodes.Success, (await PublishAsync(harness)).ExitCode);
        await harness.Database.ExecuteAsync("UPDATE icerik.release SET manifest = NULL", ct);

        GatePlanException planned = await Assert.ThrowsAsync<GatePlanException>(() => PlanAsync(harness));
        PublisherException published = await Assert.ThrowsAsync<PublisherException>(() => PublishAsync(harness));

        Assert.Equal((GatePlanFailure.PreviousManifestMissing, true), (planned.Failure, planned.IsPermanent));
        Assert.Equal("Onceki yayinin manifesti yok: dev 2026.11.0.", planned.Message);
        Assert.Equal((ExitCodes.Other, true, planned.Message), (published.ExitCode, published.IsPermanent, published.Message));
    }

    [Fact]
    public async Task Fails_with_a_verification_error_when_the_previous_manifest_cannot_be_read()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Assert.Equal(ExitCodes.Success, (await PublishAsync(harness)).ExitCode);
        await RewriteManifestAsync(harness, m => m.Remove("packs"));

        GatePlanException planned = await Assert.ThrowsAsync<GatePlanException>(() => PlanAsync(harness));
        PublisherException published = await Assert.ThrowsAsync<PublisherException>(() => PublishAsync(harness));

        Assert.Equal((GatePlanFailure.ManifestUnreadable, false), (planned.Failure, planned.IsPermanent));
        Assert.StartsWith("Manifest okunamadi (onceki yayin 2026.11.0): ", planned.Message, StringComparison.Ordinal);
        Assert.Equal((ExitCodes.Verification, false, planned.Message), (published.ExitCode, published.IsPermanent, published.Message));
    }

    [Fact]
    public async Task Fails_with_a_storage_error_when_a_previous_pack_is_missing_everywhere()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Assert.Equal(ExitCodes.Success, (await PublishAsync(harness)).ExitCode);
        await RewriteManifestAsync(harness, m => m["packs"]!.AsArray()[0]!["version"] = "2026.11.9");
        Directory.Delete(harness.OutDir, recursive: true);

        GatePlanException planned = await Assert.ThrowsAsync<GatePlanException>(() => PlanAsync(harness));
        PublisherException published = await Assert.ThrowsAsync<PublisherException>(() => PublishAsync(harness));

        Assert.Equal((GatePlanFailure.PreviousPackMissing, false), (planned.Failure, planned.IsPermanent));
        Assert.StartsWith("Onceki yayinin paketi depoda yok: ", planned.Message, StringComparison.Ordinal);
        Assert.Equal((ExitCodes.Storage, false, planned.Message), (published.ExitCode, published.IsPermanent, published.Message));
    }

    [Fact]
    public async Task Fails_with_a_verification_error_when_a_previous_pack_sha256_does_not_match_the_manifest()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Assert.Equal(ExitCodes.Success, (await PublishAsync(harness)).ExitCode);
        await RewriteManifestAsync(harness, m => m["packs"]!.AsArray()[0]!["sha256"] = new string('0', 64));
        Directory.Delete(harness.OutDir, recursive: true);

        GatePlanException planned = await Assert.ThrowsAsync<GatePlanException>(() => PlanAsync(harness));
        PublisherException published = await Assert.ThrowsAsync<PublisherException>(() => PublishAsync(harness));

        Assert.Equal((GatePlanFailure.PreviousPackMismatch, false), (planned.Failure, planned.IsPermanent));
        Assert.StartsWith("Onceki yayinin paketi manifestteki sha256 ile uyusmuyor: ", planned.Message, StringComparison.Ordinal);
        Assert.Equal((ExitCodes.Verification, false, planned.Message), (published.ExitCode, published.IsPermanent, published.Message));
    }
}
