using Microsoft.Extensions.Configuration;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// ReleasePipeline publish/build/upload (Docker: gercek PostgreSQL + bellek ici sahte depo). Durum gecisleri, yukleme sirasi, tasima,
/// kuru calistirma, kapi reddi, gecici depo hatasi, depoda cakisma ve gizli degerin ciktida bulunmamasi.
/// </summary>
public class ReleasePipelineTests(PostgresFixture postgres)
{
    private const string KucukPack = "test-kucuk";
    private const string SyntheticPack = "hadis-sentetik";

    private static Task<ReleaseResult> PublishAsync(
        PublisherHarness harness,
        BuildFlavor flavor = BuildFlavor.Dev,
        string[]? packs = null,
        string? version = null,
        bool stop = false,
        bool dryRun = false) =>
        harness.Pipeline.PublishAsync(new PublishRequest(flavor, packs ?? [], dryRun, version, StopAtVerified: stop), TestContext.Current.CancellationToken);

    [Fact]
    public async Task Publish_builds_signs_uploads_in_order_and_marks_the_release_published()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult result = await PublishAsync(harness);

        Assert.Equal(ExitCodes.Success, result.ExitCode);
        Assert.Equal("2026.11.0", result.Surum);
        Release row = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!;
        Assert.Equal(ReleaseStatus.Yayinlandi, row.Durum);
        Assert.Equal((ReleaseRequests.Yayin, "2026.11.09-abc1234", (DateTime?)harness.Clock.GetUtcNow().UtcDateTime), (row.Talep, row.DataVersion, row.YayinlandiAt));
        Assert.False(JsonDocument.Parse(row.KapiRaporu).RootElement.GetProperty("rejected").GetBoolean());

        // Yukleme sirasi: paketler -> manifest gecmisi -> manifest.json (en son).
        Assert.Equal(
            [
                PublisherHarness.PackKey("dev", SyntheticPack, "2026.11.0"),
                PublisherHarness.PackKey("dev", KucukPack, "2026.11.0"),
                PublisherHarness.HistoryKey("dev", "2026.11.0"),
                PublisherHarness.ManifestKey("dev"),
            ],
            harness.Store.Writes);

        // Imzali manifest: depo, gecmis ve cikti klasoru ayni baytlar; imza gecerli; sha256/boyut paket nesneleriyle ayni.
        byte[] manifestBytes = harness.Store.Peek(PublisherHarness.ManifestKey("dev"))!;
        Assert.Equal(manifestBytes, harness.Store.Peek(PublisherHarness.HistoryKey("dev", "2026.11.0")));
        Assert.Equal(manifestBytes, await File.ReadAllBytesAsync(Path.Combine(harness.OutDir, "dev", "2026.11.0", "manifest.json"), ct));
        Assert.True(ManifestVerifier.Verify(manifestBytes, harness.Keys[BuildFlavor.Dev].GetPublicKey()).IsValid);
        Manifest manifest = ManifestJson.Read(manifestBytes);
        Assert.Equal(["hadis-sentetik", "test-kucuk"], manifest.Packs.Select(p => p.PackId).ToArray());
        foreach (ManifestPack pack in manifest.Packs)
        {
            byte[] packBytes = harness.Store.Peek(PublisherHarness.PackKey("dev", pack.PackId, pack.Version))!;
            Assert.Equal((pack.SizeBytes, pack.Sha256), (packBytes.LongLength, Files256(packBytes)));
            Assert.Equal($"{PublisherHarness.PublicBaseUrl}/packs/dev/{pack.PackId}/{pack.Version}/{pack.PackId}-{pack.Version}.db", pack.Url);
        }

        // Cikti klasoru: .db, manifest.json, gate-report.json, self-check.json.
        string directory = Path.Combine(harness.OutDir, "dev", "2026.11.0");
        Assert.True(File.Exists(Path.Combine(directory, "test-kucuk-2026.11.0.db")));
        Assert.True(File.Exists(Path.Combine(directory, "hadis-sentetik-2026.11.0.db")));
        Assert.True(File.Exists(Path.Combine(directory, "gate-report.json")));
        using JsonDocument selfCheck = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(directory, "self-check.json"), ct));
        Assert.Equal(2, selfCheck.RootElement.GetProperty("packs").GetArrayLength());
        Assert.All(selfCheck.RootElement.GetProperty("packs").EnumerateArray(), p => Assert.True(p.GetProperty("passed").GetBoolean()));

        // Ozetler: kaynak ve paket ozetleri satira yazilir.
        ReleaseDigests digests = ReleaseDigests.Parse(row.Ozetler);
        Assert.Equal(["sentetik-kaynak", "test-kucuk"], digests.Sources.Keys.Order(StringComparer.Ordinal).ToArray());
        Assert.Equal(["hadis-sentetik", "test-kucuk"], digests.Packs.Keys.Order(StringComparer.Ordinal).ToArray());

        // Yayindan sonra verify temiz.
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));
    }

    private static string Files256(byte[] bytes) => Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(bytes));

    [Fact]
    public async Task An_unchanged_pack_is_carried_from_the_previous_release_and_not_written()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        harness.Store.Writes.Clear();

        ReleaseResult second = await PublishAsync(harness);

        Assert.Equal("2026.11.1", second.Surum);
        Manifest manifest = harness.ReadStoredManifest("dev");
        Assert.Equal("2026.11.1", manifest.Release);
        Assert.All(manifest.Packs, p => Assert.Equal("2026.11.0", p.Version));
        // Yalniz manifest gecmisi ve manifest.json yazildi; pakete dokunulmadi, yeni .db dosyasi uretilmedi.
        Assert.Equal([PublisherHarness.HistoryKey("dev", "2026.11.1"), PublisherHarness.ManifestKey("dev")], harness.Store.Writes);
        Assert.Empty(Directory.GetFiles(Path.Combine(harness.OutDir, "dev", "2026.11.1"), "*.db"));
        Assert.True(second.Packs!.All(p => p.Carried));
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));
    }

    [Fact]
    public async Task Only_the_changed_pack_gets_a_new_version()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);

        await PublishAsync(harness);

        Manifest manifest = harness.ReadStoredManifest("dev");
        Assert.Equal("2026.11.1", manifest.Packs.Single(p => p.PackId == SyntheticPack).Version);
        Assert.Equal("2026.11.0", manifest.Packs.Single(p => p.PackId == KucukPack).Version);
        Assert.True(harness.Store.Contains(PublisherHarness.PackKey("dev", SyntheticPack, "2026.11.1")));
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));
    }

    [Fact]
    public async Task Dry_run_writes_no_release_row_no_store_object_and_no_pack_but_writes_the_reports()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult result = await PublishAsync(harness, BuildFlavor.Internal, dryRun: true);

        Assert.Equal(ExitCodes.Success, result.ExitCode);
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
        Assert.Empty(harness.Store.Keys);
        Assert.False(Directory.Exists(harness.OutDir));
        string report = Path.Combine(harness.ReportsDir, "internal-2026-11-09", "gate-report.json");
        Assert.True(File.Exists(report));
        Assert.Contains("\"rejected\":false", await File.ReadAllTextAsync(report, ct), StringComparison.Ordinal);
        Assert.Contains("kuru calistirma", harness.Out.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Dry_run_for_public_excludes_test_sources_and_still_exits_zero()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult result = await PublishAsync(harness, BuildFlavor.Public, dryRun: true);

        Assert.Equal(0, result.ExitCode);
        string report = await File.ReadAllTextAsync(Path.Combine(harness.ReportsDir, "public-2026-11-09", "gate-report.json"), ct);
        using JsonDocument document = JsonDocument.Parse(report);
        JsonElement kucuk = document.RootElement.GetProperty("rows").EnumerateArray()
            .Single(r => r.GetProperty("kind").GetString() == "kaynak" && r.GetProperty("id").GetString() == "test-kucuk");
        Assert.Equal(("girmedi", "P-12"), (kucuk.GetProperty("decision").GetString(), kucuk.GetProperty("rule").GetString()));
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task A_gate_violation_fails_the_row_writes_the_report_and_exits_with_2_then_the_version_can_be_retried()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        harness.UnregisterSource(PublisherHarness.SyntheticSlug);

        ReleaseResult rejected = await PublishAsync(harness);

        Assert.Equal(ExitCodes.GateRejected, rejected.ExitCode);
        Release failed = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Equal((ReleaseStatus.Basarisiz, "2026.11.0"), (failed.Durum, failed.Surum));
        using JsonDocument report = JsonDocument.Parse(failed.KapiRaporu);
        Assert.True(report.RootElement.GetProperty("rejected").GetBoolean());
        Assert.Contains(report.RootElement.GetProperty("violations").EnumerateArray(), v => v.GetProperty("rule").GetString() == "P-01");
        Assert.True(File.Exists(Path.Combine(harness.OutDir, "dev", "2026.11.0", "gate-report.json")));
        Assert.Empty(harness.Store.Keys);
        Assert.Empty(Directory.GetFiles(Path.Combine(harness.OutDir, "dev", "2026.11.0"), "*.db"));

        // Basarisiz satir surum numarasini yakmaz: duzeltilince ayni surumle yeniden denenir.
        harness.RegisterSource(PublisherHarness.SyntheticSlug);
        ReleaseResult retry = await PublishAsync(harness);

        Assert.Equal((ExitCodes.Success, "2026.11.0"), (retry.ExitCode, retry.Surum));
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!.Durum);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(1, ct))!.Durum);
    }

    [Fact]
    public async Task A_missing_signing_key_exits_with_1_before_creating_a_row_and_never_prints_a_seed()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        harness.Keys.Remove(BuildFlavor.Dev);
        Dictionary<string, string?> values = new(StringComparer.Ordinal)
        {
            ["ConnectionStrings:Editorial"] = harness.Database.ConnectionString,
            ["Storage:PublicBaseUrl"] = PublisherHarness.PublicBaseUrl,
        };
        IConfiguration configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        await using PublisherContext context = new(configuration, harness.Releases, harness.Host);

        PublisherException exception = await Assert.ThrowsAsync<PublisherException>(() =>
            new ReleasePipeline(context).PublishAsync(new PublishRequest(BuildFlavor.Dev, []), ct));

        Assert.Equal(ExitCodes.Other, exception.ExitCode);
        Assert.Contains("Signing:dev:PrivateKey", exception.Message, StringComparison.Ordinal);
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task A_transient_store_error_leaves_the_row_verified_and_upload_resumes_without_rewriting_packs()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        harness.Store.Fault = (operation, key) =>
            operation == "put-manifest" && key == PublisherHarness.ManifestKey("dev")
                ? new StorageException(StorageFailure.Unavailable, "baglanti reddedildi")
                : null;

        ReleaseResult failed = await PublishAsync(harness);

        Assert.Equal(ExitCodes.Storage, failed.ExitCode);
        Release row = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!;
        Assert.Equal(ReleaseStatus.Dogrulandi, row.Durum);
        Assert.False(harness.Store.Contains(PublisherHarness.ManifestKey("dev")));
        int packWrites = harness.Store.Writes.Count(k => k.StartsWith("packs/", StringComparison.Ordinal));
        Assert.Equal(2, packWrites);

        harness.Store.Fault = null;
        ReleaseResult resumed = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev), ct);

        Assert.Equal(ExitCodes.Success, resumed.ExitCode);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(row.Id, ct))!.Durum);
        Assert.Equal(packWrites, harness.Store.Writes.Count(k => k.StartsWith("packs/", StringComparison.Ordinal)));
        Assert.Equal("2026.11.0", harness.ReadStoredManifest("dev").Release);
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));
    }

    [Fact]
    public async Task A_different_sha256_at_an_existing_key_fails_the_release_and_exits_with_4()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        string key = PublisherHarness.PackKey("dev", KucukPack, "2026.11.0");
        harness.Store.Seed(key, [1, 2, 3], new string('a', 64));

        ReleaseResult result = await PublishAsync(harness);

        Assert.Equal(ExitCodes.Storage, result.ExitCode);
        Release row = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Equal(ReleaseStatus.Basarisiz, row.Durum);
        Assert.Contains("depo-cakismasi", row.KapiRaporu, StringComparison.Ordinal);
        Assert.False(harness.Store.Contains(PublisherHarness.ManifestKey("dev")));
        Assert.Equal([1, 2, 3], harness.Store.Peek(key));
    }

    [Fact]
    public async Task Store_error_messages_never_contain_configured_secrets()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        string secret = harness.Configuration["Storage:SecretKey"]!;
        string seed = harness.Keys[BuildFlavor.Dev].SeedBase64();
        harness.Store.Fault = (operation, _) =>
            operation == "put-pack" ? new StorageException(StorageFailure.Other, $"imza {secret} ve {seed} hatasi") : null;

        ReleaseResult result = await PublishAsync(harness);
        int code = await new Commands.UploadCommand(harness.Context).RunAsync(new UploadRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Equal(ExitCodes.Storage, result.ExitCode);
        Assert.Equal(ExitCodes.Storage, code);
        string everything = result.Message + harness.Out + harness.Error;
        Assert.DoesNotContain(secret, everything, StringComparison.Ordinal);
        Assert.DoesNotContain(seed, everything, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Build_stops_at_verified_without_touching_the_store_and_upload_then_publishes()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult built = await PublishAsync(harness, stop: true);

        Assert.Equal((ExitCodes.Success, ReleaseStatus.Dogrulandi), (built.ExitCode, built.Status));
        Assert.Empty(harness.Store.Keys);
        Assert.True(File.Exists(Path.Combine(harness.OutDir, "dev", "2026.11.0", "manifest.json")));
        Release row = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Equal(ReleaseStatus.Dogrulandi, row.Durum);
        Assert.NotNull(row.Manifest);

        ReleaseResult uploaded = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev, "2026.11.0"), ct);

        Assert.Equal((ExitCodes.Success, ReleaseStatus.Yayinlandi), (uploaded.ExitCode, uploaded.Status));
        Assert.Equal("2026.11.0", harness.ReadStoredManifest("dev").Release);

        // Yayinlanmis yayinin upload'u tekrar calistirilabilir (ayni sha256 atlanir).
        int before = harness.Store.Writes.Count(k => k.StartsWith("packs/", StringComparison.Ordinal));
        ReleaseResult again = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev, "2026.11.0"), ct);
        Assert.Equal(ExitCodes.Success, again.ExitCode);
        Assert.Equal(before, harness.Store.Writes.Count(k => k.StartsWith("packs/", StringComparison.Ordinal)));
    }

    [Fact]
    public async Task Publish_resumes_a_verified_row_by_uploading_instead_of_rebuilding()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness, stop: true);
        byte[] manifestBefore = await File.ReadAllBytesAsync(Path.Combine(harness.OutDir, "dev", "2026.11.0", "manifest.json"), ct);

        ReleaseResult result = await PublishAsync(harness);

        Assert.Equal((ExitCodes.Success, "2026.11.0"), (result.ExitCode, result.Surum));
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
        Assert.Equal(manifestBefore, harness.Store.Peek(PublisherHarness.ManifestKey("dev")));
    }

    [Fact]
    public async Task Publish_resumes_a_preparing_row_instead_of_opening_a_new_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release pending = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-eski", "test"), ct);

        ReleaseResult result = await PublishAsync(harness);

        Assert.Equal((ExitCodes.Success, pending.Surum), (result.ExitCode, result.Surum));
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(pending.Id, ct))!.Durum);
    }

    [Fact]
    public async Task Upload_exits_with_4_when_a_carried_pack_version_is_missing_from_both_the_store_and_the_local_output()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await PublishAsync(harness, stop: true);
        harness.Store.Remove(PublisherHarness.PackKey("dev", KucukPack, "2026.11.0"));
        Directory.Delete(Path.Combine(harness.OutDir, "dev", "2026.11.0"), recursive: true);

        ReleaseResult result = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev, "2026.11.1"), ct);

        Assert.Equal(ExitCodes.Storage, result.ExitCode);
        Assert.Equal(ReleaseStatus.Dogrulandi, (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.1", ct))!.Durum);
        Assert.Equal("2026.11.0", harness.ReadStoredManifest("dev").Release);
    }

    [Fact]
    public async Task Upload_restores_a_carried_pack_from_the_local_output_when_the_store_lacks_it()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await PublishAsync(harness, stop: true);
        harness.Store.Remove(PublisherHarness.PackKey("dev", KucukPack, "2026.11.0"));

        ReleaseResult result = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev, "2026.11.1"), ct);

        Assert.Equal(ExitCodes.Success, result.ExitCode);
        Assert.True(harness.Store.Contains(PublisherHarness.PackKey("dev", KucukPack, "2026.11.0")));
        Assert.Equal("2026.11.1", harness.ReadStoredManifest("dev").Release);
    }

    [Fact]
    public async Task Upload_with_nothing_open_exits_with_1()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult result = await harness.Pipeline.UploadAsync(new UploadRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Equal(ExitCodes.Other, result.ExitCode);
    }

    [Fact]
    public async Task The_pack_option_builds_only_the_named_packs_and_carries_the_rest()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult only = await PublishAsync(harness, packs: [KucukPack]);

        Assert.Equal(ExitCodes.Success, only.ExitCode);
        Assert.Equal([KucukPack], harness.ReadStoredManifest("dev").Packs.Select(p => p.PackId).ToArray());
        Assert.Equal([KucukPack], (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!.Paketler!);

        await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.KucukAnchor, "Deneme paragrafi 1 duzeltildi", ct);
        await PublishAsync(harness, packs: [SyntheticPack]);

        // test-kucuk degisti ama --pack yalniz hadis-sentetik dedi: test-kucuk onceki yayindan aynen tasinir (eski icerik, eski surum).
        // hadis-sentetik degismedi: ozeti onceki yayinla ayni oldugundan o da tasinir (surumu 2026.11.1 kalir).
        Manifest manifest = harness.ReadStoredManifest("dev");
        Assert.Equal("2026.11.2", manifest.Release);
        Assert.Equal("2026.11.0", manifest.Packs.Single(p => p.PackId == KucukPack).Version);
        Assert.Equal("2026.11.1", manifest.Packs.Single(p => p.PackId == SyntheticPack).Version);
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));
    }

    [Fact]
    public async Task An_unknown_pack_id_is_an_input_error()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        int code = await new Commands.PublishCommand(harness.Context).RunAsync(new PublishRequest(BuildFlavor.Dev, ["yok-boyle-paket"]), ct);

        Assert.Equal(1, code);
        Assert.Contains("yok-boyle-paket", harness.Error.ToString(), StringComparison.Ordinal);
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task An_explicit_version_is_used_and_a_published_version_cannot_be_republished()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        ReleaseResult first = await PublishAsync(harness, version: "2026.11.7");
        ReleaseResult second = await PublishAsync(harness, version: "2026.11.7");

        Assert.Equal((ExitCodes.Success, "2026.11.7"), (first.ExitCode, first.Surum));
        Assert.Equal(ExitCodes.Other, second.ExitCode);
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
    }
}
