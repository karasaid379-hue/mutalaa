using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Commands;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>promote (P-14), rollback ve watch (Docker: gercek PostgreSQL + bellek ici sahte depo).</summary>
public class PromoteRollbackWatchTests(PostgresFixture postgres)
{
    private const string KucukPack = "test-kucuk";
    private const string SyntheticPack = "hadis-sentetik";

    private static Task<ReleaseResult> PublishAsync(PublisherHarness harness, BuildFlavor flavor = BuildFlavor.Dev, string[]? packs = null) =>
        harness.Pipeline.PublishAsync(new PublishRequest(flavor, packs ?? []), TestContext.Current.CancellationToken);

    // ---------------------------------------------------------------- promote

    [Fact]
    public async Task Promote_builds_public_with_the_same_version_and_filters_test_sources()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult internalRelease = await PublishAsync(harness, BuildFlavor.Internal);
        Assert.Equal(["hadis-sentetik", "test-kucuk"], harness.ReadStoredManifest("internal").Packs.Select(p => p.PackId).ToArray());
        Release source = (await harness.Releases.FindAsync(BuildFlavor.Internal, internalRelease.Surum!, ct))!;

        ReleaseResult promoted = await harness.Pipeline.PromoteAsync(new PromoteRequest(), ct);

        Assert.Equal((ExitCodes.Success, internalRelease.Surum, ReleaseStatus.Yayinlandi), (promoted.ExitCode, promoted.Surum, promoted.Status));
        Release row = (await harness.Releases.FindAsync(BuildFlavor.Public, internalRelease.Surum!, ct))!;
        Assert.Equal((ReleaseRequests.Terfi, source.Id, ReleaseStatus.Yayinlandi), (row.Talep, row.KaynakReleaseId, row.Durum));

        // P-12: public'te test- kaynagi yok; manifest imzali ve yalniz hadis-sentetik.
        Manifest manifest = harness.ReadStoredManifest("public");
        Assert.Equal([SyntheticPack], manifest.Packs.Select(p => p.PackId).ToArray());
        Assert.Equal(internalRelease.Surum, manifest.Release);
        Assert.True(ManifestVerifier.Verify(harness.Store.Peek(PublisherHarness.ManifestKey("public"))!, harness.Keys[BuildFlavor.Public].GetPublicKey()).IsValid);
        using JsonDocument report = JsonDocument.Parse(row.KapiRaporu);
        JsonElement kucuk = report.RootElement.GetProperty("rows").EnumerateArray()
            .Single(r => r.GetProperty("kind").GetString() == "kaynak" && r.GetProperty("id").GetString() == "test-kucuk");
        Assert.Equal("P-12", kucuk.GetProperty("rule").GetString());
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Public), ct));
    }

    [Fact]
    public async Task Promote_is_rejected_with_exit_2_when_the_source_digests_differ_from_the_internal_release()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult internalRelease = await PublishAsync(harness, BuildFlavor.Internal);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 sonradan degisti", ct);

        ReleaseResult promoted = await harness.Pipeline.PromoteAsync(new PromoteRequest(), ct);

        Assert.Equal(ExitCodes.GateRejected, promoted.ExitCode);
        Release row = (await harness.Releases.GetAsync(2, ct))!;
        Assert.Equal((BuildFlavor.Public, ReleaseStatus.Basarisiz, internalRelease.Surum), (row.Derleme, row.Durum, row.Surum));
        using JsonDocument report = JsonDocument.Parse(row.KapiRaporu);
        JsonElement violation = Assert.Single(report.RootElement.GetProperty("violations").EnumerateArray());
        Assert.Equal(("P-14", "sentetik-kaynak", "ozet-uyusmuyor"), (violation.GetProperty("rule").GetString(), violation.GetProperty("subject").GetString(), violation.GetProperty("reason").GetString()));
        Assert.False(harness.Store.Contains(PublisherHarness.ManifestKey("public")));
    }

    [Fact]
    public async Task Promote_without_a_published_internal_release_exits_with_1_and_does_nothing()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness, BuildFlavor.Dev);

        int code = await new PromoteCommand(harness.Context).RunAsync(new PromoteRequest(), ct);

        Assert.Equal(1, code);
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task Promote_dry_run_reports_without_writing_and_promote_twice_exits_with_1()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness, BuildFlavor.Internal);

        ReleaseResult dry = await harness.Pipeline.PromoteAsync(new PromoteRequest(DryRun: true), ct);
        Assert.Equal(ExitCodes.Success, dry.ExitCode);
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
        Assert.False(harness.Store.Contains(PublisherHarness.ManifestKey("public")));

        Assert.Equal(ExitCodes.Success, (await harness.Pipeline.PromoteAsync(new PromoteRequest(), ct)).ExitCode);
        ReleaseResult twice = await harness.Pipeline.PromoteAsync(new PromoteRequest(), ct);
        Assert.Equal(ExitCodes.Other, twice.ExitCode);
    }

    [Fact]
    public async Task Promote_dry_run_reports_the_p14_mismatch_with_exit_2()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness, BuildFlavor.Internal);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 sonradan degisti", ct);

        ReleaseResult dry = await harness.Pipeline.PromoteAsync(new PromoteRequest(DryRun: true), ct);

        Assert.Equal(ExitCodes.GateRejected, dry.ExitCode);
        Assert.Contains("P-14", harness.Out.ToString(), StringComparison.Ordinal);
    }

    // ---------------------------------------------------------------- rollback

    [Fact]
    public async Task Rollback_opens_a_new_release_that_re_signs_the_target_packs_and_withdraws_the_current_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        await PublishAsync(harness);
        Release first = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.0", ct))!;
        Release second = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.1", ct))!;

        ReleaseResult rolled = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, "2026.11.0"), ct);

        Assert.Equal((ExitCodes.Success, "2026.11.2", ReleaseStatus.Yayinlandi), (rolled.ExitCode, rolled.Surum, rolled.Status));
        Release row = (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.2", ct))!;
        Assert.Equal((ReleaseRequests.GeriAlma, first.Id), (row.Talep, row.KaynakReleaseId));
        Assert.Equal(ReleaseStatus.GeriCekildi, (await harness.Releases.GetAsync(second.Id, ct))!.Durum);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(first.Id, ct))!.Durum);

        byte[] bytes = harness.Store.Peek(PublisherHarness.ManifestKey("dev"))!;
        Manifest manifest = ManifestJson.Read(bytes);
        Assert.Equal("2026.11.2", manifest.Release);
        Assert.All(manifest.Packs, p => Assert.Equal("2026.11.0", p.Version));
        Assert.True(ManifestVerifier.Verify(bytes, harness.Keys[BuildFlavor.Dev].GetPublicKey()).IsValid);
        Assert.Equal(bytes, harness.Store.Peek(PublisherHarness.HistoryKey("dev", "2026.11.2")));
        Assert.Empty(await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), ct));

        // Sonraki yayin geri alinan yayini "onceki" sayar: DB hala 2026.11.1 icerigindedir, bu yuzden hadis-sentetik yeniden derlenir.
        await PublishAsync(harness);
        Manifest next = harness.ReadStoredManifest("dev");
        Assert.Equal("2026.11.3", next.Release);
        Assert.Equal("2026.11.3", next.Packs.Single(p => p.PackId == SyntheticPack).Version);
        Assert.Equal("2026.11.0", next.Packs.Single(p => p.PackId == KucukPack).Version);
    }

    [Fact]
    public async Task Rollback_exits_with_4_when_the_target_manifest_or_a_target_pack_is_missing_from_the_store()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        await PublishAsync(harness);
        int rows = await harness.CountReleasesAsync(ct);

        ReleaseResult noManifest = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, "2026.11.9"), ct);
        harness.Store.Remove(PublisherHarness.PackKey("dev", SyntheticPack, "2026.11.0"));
        ReleaseResult noPack = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, "2026.11.0"), ct);

        Assert.Equal((ExitCodes.Storage, ExitCodes.Storage), (noManifest.ExitCode, noPack.ExitCode));
        Assert.Equal(rows, await harness.CountReleasesAsync(ct));
        Assert.Equal("2026.11.1", harness.ReadStoredManifest("dev").Release);
    }

    [Fact]
    public async Task Rollback_to_the_current_release_or_with_an_invalid_version_exits_with_1()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);

        ReleaseResult current = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, "2026.11.0"), ct);
        ReleaseResult invalid = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, "bir-surum"), ct);

        Assert.Equal((ExitCodes.Other, ExitCodes.Other), (current.ExitCode, invalid.ExitCode));
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task Rollback_store_unavailable_exits_with_4()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        harness.Store.Fault = (_, _) => new StorageException(StorageFailure.Unavailable, "baglanti reddedildi");

        int code = await new RollbackCommand(harness.Context).RunAsync(new RollbackRequest(BuildFlavor.Dev, "2026.11.0"), ct);

        Assert.Equal(4, code);
    }

    // ---------------------------------------------------------------- watch

    [Fact]
    public async Task Watch_once_with_nothing_pending_exits_with_0()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, TestContext.Current.CancellationToken);

        Assert.Equal(0, code);
        Assert.Contains("Bekleyen talep yok", harness.Out.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Watch_once_runs_a_publish_request_with_its_pack_list()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release request = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor", Paketler: [KucukPack], Notlar: "api talebi"),
            ct);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(0, code);
        Release row = (await harness.Releases.GetAsync(request.Id, ct))!;
        Assert.Equal(ReleaseStatus.Yayinlandi, row.Durum);
        Assert.Equal([KucukPack], harness.ReadStoredManifest("dev").Packs.Select(p => p.PackId).ToArray());
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
    }

    [Fact]
    public async Task Watch_once_dispatches_promotion_and_rollback_requests_by_their_request_type()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult internalRelease = await PublishAsync(harness, BuildFlavor.Internal);
        Release source = (await harness.Releases.FindAsync(BuildFlavor.Internal, internalRelease.Surum!, ct))!;
        Release promotion = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Public, source.Surum, ReleaseRequests.Terfi, "2026.11.09-api", "editor", source.Id),
            ct);

        Assert.Equal(0, await new WatchCommand(harness.Context).RunAsync(1, once: true, ct));
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(promotion.Id, ct))!.Durum);
        Assert.Equal(internalRelease.Surum, harness.ReadStoredManifest("public").Release);

        ReleaseResult devFirst = await PublishAsync(harness, BuildFlavor.Dev);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        await PublishAsync(harness, BuildFlavor.Dev);
        Release target = (await harness.Releases.FindAsync(BuildFlavor.Dev, devFirst.Surum!, ct))!;
        Release rollback = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.GeriAlma, "2026.11.09-api", "editor", target.Id),
            ct);

        Assert.Equal(0, await new WatchCommand(harness.Context).RunAsync(1, once: true, ct));
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(rollback.Id, ct))!.Durum);
        Assert.Equal(rollback.Surum, harness.ReadStoredManifest("dev").Release);
        Assert.All(harness.ReadStoredManifest("dev").Packs, p => Assert.Equal(target.Surum, p.Version));
    }

    [Fact]
    public async Task Watch_once_fails_an_unsatisfiable_request_instead_of_looping_and_returns_a_non_zero_code()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release bad = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Public, null, ReleaseRequests.Terfi, "2026.11.09-api", "editor"), ct);
        Release good = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(bad.Id, ct))!.Durum);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(good.Id, ct))!.Durum);
    }

    [Fact]
    public async Task Watch_once_fails_a_row_with_an_unknown_pack_id_and_still_processes_the_valid_request_behind_it()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release bad = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor", Paketler: ["yok-boyle-paket"]),
            ct);
        Release good = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Release failed = (await harness.Releases.GetAsync(bad.Id, ct))!;
        Assert.Equal(ReleaseStatus.Basarisiz, failed.Durum);
        Assert.Contains("yok-boyle-paket", failed.KapiRaporu, StringComparison.Ordinal);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(good.Id, ct))!.Durum);
    }

    [Fact]
    public async Task Watch_once_fails_a_request_whose_previous_release_has_no_manifest_or_that_selects_no_pack_that_can_enter()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await PublishAsync(harness);
        await harness.Database.ExecuteAsync("UPDATE icerik.release SET manifest = NULL", ct);
        Release noManifest = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        Release noPack = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Public, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor", Paketler: [KucukPack]),
            ct);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Release first = (await harness.Releases.GetAsync(noManifest.Id, ct))!;
        Assert.Equal(ReleaseStatus.Basarisiz, first.Durum);
        Assert.Contains("Onceki yayinin manifesti yok", first.KapiRaporu, StringComparison.Ordinal);
        Release second = (await harness.Releases.GetAsync(noPack.Id, ct))!;
        Assert.Equal(ReleaseStatus.Basarisiz, second.Durum);
        Assert.Contains("Manifestte hic paket yok", second.KapiRaporu, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Watch_once_leaves_a_request_preparing_when_the_failure_is_a_configuration_error()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release request = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        Dictionary<string, string?> values = new(StringComparer.Ordinal)
        {
            ["ConnectionStrings:Editorial"] = harness.Database.ConnectionString,
            ["Storage:PublicBaseUrl"] = PublisherHarness.PublicBaseUrl,
        };
        IConfiguration configuration =
            new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        await using PublisherContext context = new(configuration, harness.Releases, harness.Host);

        int code = await new WatchCommand(context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Assert.Equal(ReleaseStatus.Hazirlaniyor, (await harness.Releases.GetAsync(request.Id, ct))!.Durum);
        Assert.Contains("Signing:dev:PrivateKey", harness.Error.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Watch_once_survives_an_unexpected_exception_from_one_row_and_keeps_that_row_open()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release broken = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        Release good = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Internal, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        harness.Store.Fault = (operation, key) =>
            operation == "put-pack" && key.StartsWith("packs/dev/", StringComparison.Ordinal) ? new IOException("disk hatasi (sentetik)") : null;

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        // Gecici hata satiri basarisiz yapmaz: dogrulandi kalir (upload ile surer).
        Assert.Equal(ReleaseStatus.Dogrulandi, (await harness.Releases.GetAsync(broken.Id, ct))!.Durum);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(good.Id, ct))!.Durum);
        Assert.Contains("IOException", harness.Error.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Watch_once_fails_a_promotion_row_whose_version_differs_from_its_internal_source()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult internalRelease = await PublishAsync(harness, BuildFlavor.Internal);
        Release source = (await harness.Releases.FindAsync(BuildFlavor.Internal, internalRelease.Surum!, ct))!;
        Release promotion = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Public, "2026.11.5", ReleaseRequests.Terfi, "2026.11.09-api", "editor", source.Id),
            ct);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Release row = (await harness.Releases.GetAsync(promotion.Id, ct))!;
        Assert.Equal(ReleaseStatus.Basarisiz, row.Durum);
        Assert.Contains("terfi-surumu-uyumsuz", row.KapiRaporu, StringComparison.Ordinal);
        Assert.False(harness.Store.Contains(PublisherHarness.ManifestKey("public")));
    }

    [Fact]
    public async Task Watch_once_rejects_a_release_version_that_is_not_calver_before_any_file_path_is_built()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        // surum sutununda CalVer kisiti yok (yalniz CreateAsync denetler); bozuk satir dosya yoluna girmeden once reddedilir.
        Release request = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        await harness.Database.ExecuteAsync("UPDATE icerik.release SET surum = '../kacis' WHERE id = @id", ct, ("id", request.Id));

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(request.Id, ct))!.Durum);
        Assert.False(Directory.Exists(Path.Combine(harness.Directory.Path, "kacis")));
        Assert.False(Directory.Exists(harness.OutDir));
    }

    // ---------------------------------------------------------------- rollback: acik satir

    [Fact]
    public async Task Cli_rollback_resumes_an_open_rollback_row_for_the_same_target_instead_of_opening_a_second_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult first = await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        await PublishAsync(harness);
        Release target = (await harness.Releases.FindAsync(BuildFlavor.Dev, first.Surum!, ct))!;
        Release open = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.GeriAlma, "2026.11.09-api", "editor", target.Id),
            ct);
        int rows = await harness.CountReleasesAsync(ct);

        ReleaseResult rolled = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, first.Surum!), ct);

        Assert.Equal((ExitCodes.Success, open.Surum), (rolled.ExitCode, rolled.Surum));
        Assert.Equal(rows, await harness.CountReleasesAsync(ct));
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(open.Id, ct))!.Durum);
        Assert.Equal(open.Surum, harness.ReadStoredManifest("dev").Release);

        // Sonra watch calissa acik satir kalmadigindan hicbir sey yurutulmez.
        Assert.Equal(0, await new WatchCommand(harness.Context).RunAsync(1, once: true, ct));
        Assert.Equal(open.Surum, harness.ReadStoredManifest("dev").Release);
    }

    [Fact]
    public async Task Cli_rollback_fails_a_stale_open_rollback_row_for_another_target_so_watch_cannot_run_it_later()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        ReleaseResult first = await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        ReleaseResult second = await PublishAsync(harness);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 yine duzeltildi", ct);
        await PublishAsync(harness);
        Release firstRow = (await harness.Releases.FindAsync(BuildFlavor.Dev, first.Surum!, ct))!;
        Release stale = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.GeriAlma, "2026.11.09-api", "editor", firstRow.Id),
            ct);

        ReleaseResult rolled = await harness.Pipeline.RollbackAsync(new RollbackRequest(BuildFlavor.Dev, second.Surum!), ct);

        Assert.Equal(ExitCodes.Success, rolled.ExitCode);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(stale.Id, ct))!.Durum);
        string manifestRelease = harness.ReadStoredManifest("dev").Release;
        Assert.Equal(rolled.Surum, manifestRelease);

        Assert.Equal(0, await new WatchCommand(harness.Context).RunAsync(1, once: true, ct));
        Assert.Equal(manifestRelease, harness.ReadStoredManifest("dev").Release);
    }

    [Fact]
    public async Task Watch_once_exits_with_1_when_another_publisher_holds_the_lock()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        Release request = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);
        await using PublisherLock? held = await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct);
        Assert.NotNull(held);

        int code = await new WatchCommand(harness.Context).RunAsync(1, once: true, ct);

        Assert.Equal(1, code);
        Assert.Equal(ReleaseStatus.Hazirlaniyor, (await harness.Releases.GetAsync(request.Id, ct))!.Durum);
    }
}
