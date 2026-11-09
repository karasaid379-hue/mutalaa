using System.Text;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// A13.5 butunlesik test, yayini DEGISTIREN senaryolar (Docker: gercek postgres:18 + gercek SeaweedFS). Her test kendi veritabanini ve kendi
/// kovasini acar; komutlar komut satirindan (PublisherApp.RunAsync) calistirilir: cikis kodlari 0, 2 (kapi), 3 (dogrulama), 4 (depo), 1 (diger).
/// </summary>
public class ReleaseEndToEndFlowTests(PostgresFixture postgres, SeaweedFixture seaweed)
{
    private const string ApprovedText = "Deneme paragrafi 1 (onayli).";

    private Task<EndToEndHarness> NewHarnessAsync() => EndToEndHarness.CreateAsync(postgres, seaweed);

    private static string[] PackIds(Manifest manifest) => [.. manifest.Packs.Select(p => p.PackId).Order(StringComparer.Ordinal)];

    // ---------------------------------------------------------------- publish, verify, tasima

    [Fact]
    public async Task Publish_then_verify_exits_0_and_a_second_publish_carries_the_packs_from_the_previous_release()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        CliResult first = await harness.RunCliAsync("publish", "--flavor", "dev");
        CliResult verified = await harness.RunCliAsync("verify", "--flavor", "dev");

        Assert.Equal((0, 0), (first.Code, verified.Code));
        Manifest manifest = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.Equal("2026.11.0", manifest.Release);
        Assert.All(manifest.Packs, p => Assert.Equal("2026.11.0", p.Version));
        Assert.Contains("Dogrulama tamam", verified.Out, StringComparison.Ordinal);

        // Ikinci yayin: icerik ayni, ozetler ayni -> butun paketler onceki surumden tasinir, depoya yalniz manifest gecmisi eklenir.
        List<string> before = await harness.AllKeysAsync(ct);
        CliResult second = await harness.RunCliAsync("publish", "--flavor", "dev");

        Assert.Equal(0, second.Code);
        Manifest next = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.Equal("2026.11.1", next.Release);
        Assert.Equal(PackIds(manifest), PackIds(next));
        Assert.All(next.Packs, p => Assert.Equal("2026.11.0", p.Version));
        Assert.Equal(manifest.Packs.Select(p => p.Sha256).Order(StringComparer.Ordinal), next.Packs.Select(p => p.Sha256).Order(StringComparer.Ordinal));
        List<string> after = await harness.AllKeysAsync(ct);
        Assert.Equal([StorageKeys.ManifestHistory("dev", "2026.11.1")], after.Except(before, StringComparer.Ordinal).ToArray());
        Assert.Equal(
            ReleaseDigests.Parse((await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.0", ct)).Ozetler).Packs,
            ReleaseDigests.Parse((await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.1", ct)).Ozetler).Packs);

        // Yalniz degisen paket yeni surum alir.
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, "Deneme paragrafi 1 (duzeltildi).", ct);
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        Manifest third = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.Equal("2026.11.2", third.Packs.Single(p => p.PackId == "hadis-sentetik").Version);
        Assert.All(third.Packs.Where(p => p.PackId != "hadis-sentetik"), p => Assert.Equal("2026.11.0", p.Version));
        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev")).Code);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Two_builds_of_the_same_data_have_the_same_content_digest_while_the_files_differ(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        ReleaseResult first = await harness.PublishAsync(BuildFlavor.Dev, version: "2026.11.0", stop: true);
        harness.Clock.Advance(TimeSpan.FromHours(3));
        ReleaseResult second = default!;
        await StorageTestKit.RunAsync(turkish, async () => second = await harness.PublishAsync(BuildFlavor.Dev, version: "2026.11.1", stop: true));

        Assert.Equal((ExitCodes.Success, ExitCodes.Success), (first.ExitCode, second.ExitCode));
        Assert.Empty(await harness.AllKeysAsync(ct));
        foreach (string packId in new[] { "core", "hadis-sentetik", "test-kucuk", "tefsir-test-ornek" })
        {
            string one = Path.Combine(harness.OutDir, "dev", "2026.11.0", $"{packId}-2026.11.0.db");
            string two = Path.Combine(harness.OutDir, "dev", "2026.11.1", $"{packId}-2026.11.1.db");
            PackFileMeta a = PackInspector.ReadMeta(one);
            PackFileMeta b = PackInspector.ReadMeta(two);

            Assert.NotNull(a.ContentDigest);
            Assert.Equal(a.ContentDigest, b.ContentDigest);
            Assert.NotEqual(a.Version, b.Version);
            Assert.NotEqual(await File.ReadAllBytesAsync(one, ct), await File.ReadAllBytesAsync(two, ct));
        }

        // Ikisinin de release.ozetler paket ozetleri ayni; kaynak ozetleri derleme turunden bagimsizdir ve ayni.
        ReleaseDigests d1 = ReleaseDigests.Parse((await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.0", ct)).Ozetler);
        ReleaseDigests d2 = ReleaseDigests.Parse((await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.1", ct)).Ozetler);
        Assert.Equal(d1.Packs, d2.Packs);
        Assert.Equal(d1.Sources, d2.Sources);
    }

    // ---------------------------------------------------------------- kuru calistirma

    [Fact]
    public async Task Dry_run_writes_no_release_row_no_pack_and_no_store_object_for_every_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        CliResult dev = await harness.RunCliAsync("publish", "--flavor", "dev", "--dry-run");
        CliResult internalRun = await harness.RunCliAsync("publish", "--flavor", "internal", "--dry-run");
        CliResult publicRun = await harness.RunCliAsync("publish", "--flavor", "public", "--dry-run");

        Assert.Equal((0, 0, 0), (dev.Code, internalRun.Code, publicRun.Code));
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
        Assert.Empty(await harness.AllKeysAsync(ct));
        Assert.False(Directory.Exists(harness.OutDir));
        foreach (string flavor in new[] { "dev", "internal", "public" })
        {
            string report = await File.ReadAllTextAsync(Path.Combine(harness.ReportsDir, $"{flavor}-2026-11-09", "gate-report.json"), ct);
            Assert.Contains("\"rejected\":false", report, StringComparison.Ordinal);
        }

        // Kuru calistirma raporu P-12 kararlarini yazar.
        Assert.Contains("kaynak test-tefsir-ornek: girmedi [P-12]", internalRun.Out, StringComparison.Ordinal);
        Assert.Contains("kaynak test-kucuk: girmedi [P-12]", publicRun.Out, StringComparison.Ordinal);
        Assert.DoesNotContain("girmedi [P-12]", dev.Out, StringComparison.Ordinal);
    }

    // ---------------------------------------------------------------- kapi reddi ve yeniden deneme

    [Fact]
    public async Task P01_a_pack_whose_source_has_no_registry_file_is_rejected_with_exit_2_and_the_version_is_retried()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        harness.UnregisterSource(EndToEndData.Sentetik);

        CliResult rejected = await harness.RunCliAsync("publish", "--flavor", "dev");

        Assert.Equal(2, rejected.Code);
        Release failed = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Equal((ReleaseStatus.Basarisiz, "2026.11.0"), (failed.Durum, failed.Surum));
        Assert.Contains(EndToEndHarness.Violations(failed), v => v.Rule == "P-01" && v.Subject == EndToEndData.Sentetik && v.Reason == "kaynak-kaydi-yok");
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(failed);
        Assert.Contains(rows, r => r.Kind == "kaynak" && r.Id == EndToEndData.Sentetik && r.Decision == "girmedi" && r.Rule == "P-01");
        Assert.Contains(rows, r => r.Kind == "paket" && r.Id == EndToEndData.SentetikPack && r.Decision == "girmedi" && r.Rule == "P-01");
        Assert.Empty(await harness.AllKeysAsync(ct));
        Assert.Empty(Directory.GetFiles(Path.Combine(harness.OutDir, "dev", "2026.11.0"), "*.db"));
        Assert.True(File.Exists(Path.Combine(harness.OutDir, "dev", "2026.11.0", "gate-report.json")));

        // Basarisiz deneme surum numarasini yakmaz: kayit duzeltilince ayni surumle yeniden denenir (kismi tekil dizin).
        harness.RegisterSource(EndToEndData.Sentetik);
        CliResult retry = await harness.RunCliAsync("publish", "--flavor", "dev");

        Assert.Equal(0, retry.Code);
        Assert.Equal(2, await harness.CountReleasesAsync(ct));
        Assert.Equal(
            [("basarisiz", "2026.11.0"), ("yayinlandi", "2026.11.0")],
            await ReleaseStatusesAsync(harness, ct));
        Assert.Equal("2026.11.0", (await harness.ReadManifestAsync(BuildFlavor.Dev, ct)).Release);

        // Yayinlanmis surumle ikinci bir acik satir acilamaz (release_surum_derleme_key kismi tekil dizini).
        await Assert.ThrowsAsync<ReleaseConflictException>(() => harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, "2026.11.0", ReleaseRequests.Yayin, "2026.11.09-abc1234", "test"), ct));
    }

    private static async Task<(string Durum, string Surum)[]> ReleaseStatusesAsync(EndToEndHarness harness, CancellationToken ct)
    {
        List<(string, string)> rows = [];
        foreach (int id in new[] { 1, 2 })
        {
            Release row = (await harness.Releases.GetAsync(id, ct))!;
            rows.Add((row.Durum.ToLabel(), row.Surum));
        }

        return [.. rows];
    }

    [Fact]
    public async Task Verify_embedded_core_accepts_the_published_core_and_its_history_and_rejects_changed_bytes_or_a_missing_file()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);

        async Task<string> WriteCoreAsync(string name, Func<byte[], byte[]>? change = null)
        {
            Manifest manifest = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
            ManifestPack core = manifest.Packs.Single(p => p.PackId == "core");
            byte[] bytes = await harness.Reader.GetAsync(StorageKeys.Pack("dev", core.PackId, core.Version), ct) ?? throw new InvalidOperationException("core yok");
            string path = Path.Combine(harness.Directory.Path, name);
            await File.WriteAllBytesAsync(path, change is null ? bytes : change(bytes), ct);
            return path;
        }

        // Olumlu yol: yayinlanan core.db ile bulgu yok, cikis 0.
        string embedded = await WriteCoreAsync("core-ilk.db");
        CliResult ok = await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", embedded);
        Assert.Equal(0, ok.Code);
        Assert.DoesNotContain("BULGU", ok.Out, StringComparison.Ordinal);

        // Baytlari degisik dosya reddedilir.
        string tampered = await WriteCoreAsync("core-bozuk.db", bytes => [.. bytes[..^1], (byte)(bytes[^1] ^ 0xFF)]);
        CliResult bad = await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", tampered);
        Assert.Equal(3, bad.Code);
        Assert.Contains("BULGU [gomulu-core-uyusmuyor]", bad.Out, StringComparison.Ordinal);
        CliResult missing = await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", Path.Combine(harness.Directory.Path, "yok.db"));
        Assert.Equal(3, missing.Code);
        Assert.Contains("BULGU [gomulu-core-yok]", missing.Out, StringComparison.Ordinal);

        // core degisip yeniden yayinlaninca: yeni surumun baytlari kabul, eski surumun baytlari (manifest gecmisi) de kabul, bozuk hala red.
        await harness.Database.ExecuteAsync("UPDATE icerik.page_map SET page = 2", ct);
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        Manifest next = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.Equal("2026.11.1", next.Packs.Single(p => p.PackId == "core").Version);
        string current = await WriteCoreAsync("core-yeni.db");

        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", current)).Code);
        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", embedded)).Code);
        Assert.Equal(3, (await harness.RunCliAsync("verify", "--flavor", "dev", "--embedded-core", tampered)).Code);
        Assert.NotEqual(await File.ReadAllBytesAsync(embedded, ct), await File.ReadAllBytesAsync(current, ct));
    }

    [Fact]
    public async Task P11_a_changed_unit_text_with_the_hash_left_alone_or_a_changed_word_text_rejects_the_release_with_exit_2()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        string original = harness.Content.Uthmani.Verses[1].Text;

        // 1) Metin degisti, content_hash ayni kaldi: yalniz hash'i denetlemek bunu kacirirdi; pakete degisen metin yazilacakti.
        await harness.Database.ExecuteAsync("UPDATE icerik.unit SET metin = metin || 'x' WHERE anchor = 'q:1:2'", ct);
        CliResult textRun = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(2, textRun.Code);
        IReadOnlyList<(string? Rule, string Subject, string Reason)> textViolations = EndToEndHarness.Violations((await harness.Releases.GetAsync(1, ct))!);
        Assert.Contains(textViolations, v => v is { Rule: "P-11", Subject: "q:1:2", Reason: "metin-uyusmuyor" });
        Assert.Contains(textViolations, v => v is { Rule: "P-11", Subject: "q:1:2", Reason: "hash-metinle-uyusmuyor" });
        await harness.Database.ExecuteAsync("UPDATE icerik.unit SET metin = @m WHERE anchor = 'q:1:2'", ct, ("m", original));

        // 2) quran_word.text_uthmani ayet metninin diliminden farkli.
        await harness.Database.ExecuteAsync("UPDATE icerik.quran_word SET text_uthmani = text_uthmani || 'x' WHERE anchor = 'q:1:2:1'", ct);
        CliResult wordRun = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(2, wordRun.Code);
        Assert.Contains(EndToEndHarness.Violations((await harness.Releases.GetAsync(2, ct))!), v => v is { Rule: "P-11", Subject: "q:1:2:1", Reason: "kelime-metni-uyusmuyor" });
        Assert.Empty(await harness.AllKeysAsync(ct));
    }

    [Fact]
    public async Task P11_a_changed_unit_hash_or_notice_rejects_the_release_with_exit_2_and_a_corrected_retry_succeeds()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        // 1) Birimin content_hash degeri ham dosyadan yeniden hesaplananla ayni degil.
        await harness.Database.ExecuteAsync("UPDATE icerik.unit SET content_hash = repeat('0', 64) WHERE anchor = 'q:1:2'", ct);
        CliResult hashRun = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(2, hashRun.Code);
        Release hashFailed = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Contains(EndToEndHarness.Violations(hashFailed), v => v is { Rule: "P-11", Subject: "q:1:2", Reason: "hash-uyusmuyor" });
        await harness.Database.ExecuteAsync("UPDATE icerik.unit SET content_hash = @h WHERE anchor = 'q:1:2'", ct, ("h", Mutalaa.Domain.Text.ContentHash.Compute(harness.Content.Uthmani.Verses[1].Text)));

        // 2) Bildirim blogu ham dosyadaki ile bayt bayt ayni degil.
        await harness.Database.ExecuteAsync("UPDATE icerik.source SET notice_text = notice_text || 'x' WHERE slug = 'tanzil-uthmani'", ct);
        CliResult noticeRun = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(2, noticeRun.Code);
        Release noticeFailed = (await harness.Releases.GetAsync(2, ct))!;
        Assert.Contains(EndToEndHarness.Violations(noticeFailed), v => v is { Rule: "P-11", Subject: "tanzil-uthmani", Reason: "bildirim-uyusmuyor" });
        await harness.Database.ExecuteAsync("UPDATE icerik.source SET notice_text = @n WHERE slug = 'tanzil-uthmani'", ct, ("n", harness.Content.UthmaniNotice));

        // 3) Ham dosya degistirilmis (SHA-256 kayittakiyle ayni degil).
        string raw = Path.Combine(harness.RawDir, "tanzil-uthmani", EndToEndData.TanzilDate, "quran-uthmani.txt");
        byte[] original = await File.ReadAllBytesAsync(raw, ct);
        byte[] flipped = [.. original];
        flipped[0] ^= 0x01;
        await File.WriteAllBytesAsync(raw, flipped, ct);
        CliResult rawRun = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(2, rawRun.Code);
        Assert.Contains(EndToEndHarness.Violations((await harness.Releases.GetAsync(3, ct))!), v => v is { Rule: "P-11", Subject: "tanzil-uthmani", Reason: "ham-dosya-sha256-uyusmuyor" });
        Assert.Empty(await harness.AllKeysAsync(ct));

        // Hepsi duzeltilince ayni surumle yayinlanir.
        await File.WriteAllBytesAsync(raw, original, ct);
        CliResult retry = await harness.RunCliAsync("publish", "--flavor", "dev");
        Assert.Equal(0, retry.Code);
        Assert.Equal("2026.11.0", (await harness.ReadManifestAsync(BuildFlavor.Dev, ct)).Release);
    }

    [Fact]
    public async Task P13_a_pack_selected_without_its_dependency_is_rejected_and_the_complete_set_publishes()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        CliResult rejected = await harness.RunCliAsync("publish", "--flavor", "dev", "--pack", "tefsir-test-ornek");

        Assert.Equal(2, rejected.Code);
        Release failed = (await harness.Releases.GetAsync(1, ct))!;
        Assert.Contains(EndToEndHarness.Violations(failed), v => v.Rule == "P-13" && v.Subject == "tefsir-test-ornek");
        Assert.Empty(await harness.AllKeysAsync(ct));

        CliResult ok = await harness.RunCliAsync("publish", "--flavor", "dev", "--pack", "core", "--pack", "tefsir-test-ornek");

        Assert.Equal(0, ok.Code);
        Assert.Equal(["core", "tefsir-test-ornek"], PackIds(await harness.ReadManifestAsync(BuildFlavor.Dev, ct)));
        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev")).Code);
    }

    // ---------------------------------------------------------------- verify: kurcalanmis ve imzasiz manifest

    [Fact]
    public async Task A_tampered_manifest_and_an_unsigned_manifest_exit_3_in_verify()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        string original = Encoding.UTF8.GetString(await harness.ManifestBytesAsync(BuildFlavor.Dev, ct));

        // Kurcalanmis: boyut alani degistirildi, imza ayni kaldi.
        string tampered = original.Replace("\"size_bytes\":", "\"size_bytes\":9", StringComparison.Ordinal);
        Assert.NotEqual(original, tampered);
        await harness.Reader.PutManifestAsync(StorageKeys.Manifest("dev"), Encoding.UTF8.GetBytes(tampered), ct);
        CliResult tamperedRun = await harness.RunCliAsync("verify", "--flavor", "dev");

        // Imzasiz: signature nesnesi kaldirildi.
        System.Text.Json.Nodes.JsonObject node = System.Text.Json.Nodes.JsonNode.Parse(original)!.AsObject();
        Assert.True(node.Remove("signature"));
        await harness.Reader.PutManifestAsync(StorageKeys.Manifest("dev"), Encoding.UTF8.GetBytes(node.ToJsonString()), ct);
        CliResult unsignedRun = await harness.RunCliAsync("verify", "--flavor", "dev");

        Assert.Equal((3, 3), (tamperedRun.Code, unsignedRun.Code));
        Assert.Contains("BULGU", tamperedRun.Out, StringComparison.Ordinal);
        Assert.Contains("BULGU", unsignedRun.Out, StringComparison.Ordinal);

        // Asil manifest geri yazilinca temiz.
        await harness.Reader.PutManifestAsync(StorageKeys.Manifest("dev"), Encoding.UTF8.GetBytes(original), ct);
        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev")).Code);
    }

    // ---------------------------------------------------------------- terfi ve P-14

    [Fact]
    public async Task P14_promotion_is_rejected_with_exit_2_when_the_source_digests_differ_and_succeeds_when_they_match()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "internal")).Code);
        Release internalRow = await harness.GetReleaseAsync(BuildFlavor.Internal, "2026.11.0", ct);
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, "Deneme paragrafi 1 (sonradan degisti).", ct);

        CliResult dry = await harness.RunCliAsync("promote", "--from", "internal", "--to", "public", "--dry-run");
        CliResult rejected = await harness.RunCliAsync("promote", "--from", "internal", "--to", "public");

        Assert.Equal((2, 2), (dry.Code, rejected.Code));
        Assert.Contains("P-14", dry.Out, StringComparison.Ordinal);
        Release failed = (await harness.Releases.GetAsync(2, ct))!;
        Assert.Equal((BuildFlavor.Public, ReleaseStatus.Basarisiz, ReleaseRequests.Terfi, internalRow.Id), (failed.Derleme, failed.Durum, failed.Talep, failed.KaynakReleaseId));
        Assert.Contains(EndToEndHarness.Violations(failed), v => v is { Rule: "P-14", Subject: EndToEndData.Sentetik, Reason: "ozet-uyusmuyor" });
        Assert.DoesNotContain(await harness.AllKeysAsync(ct), k => k.StartsWith("public/", StringComparison.Ordinal) || k.StartsWith("packs/public/", StringComparison.Ordinal));

        // Icerik internal'da test edilenle ayni olunca terfi basarir: ayni surum, test kaynaklari public'e girmez.
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, ApprovedText, ct);
        CliResult promoted = await harness.RunCliAsync("promote", "--from", "internal", "--to", "public");

        Assert.Equal(0, promoted.Code);
        Manifest publicManifest = await harness.ReadManifestAsync(BuildFlavor.Public, ct);
        Assert.Equal("2026.11.0", publicManifest.Release);
        Assert.Equal(["core", "hadis-sentetik"], PackIds(publicManifest));
        Release row = await harness.GetReleaseAsync(BuildFlavor.Public, "2026.11.0", ct);
        Assert.Equal((ReleaseStatus.Yayinlandi, ReleaseRequests.Terfi, internalRow.Id), (row.Durum, row.Talep, row.KaynakReleaseId));
        ReleaseDigests internalDigests = ReleaseDigests.Parse(internalRow.Ozetler);
        ReleaseDigests publicDigests = ReleaseDigests.Parse(row.Ozetler);
        foreach ((string slug, string digest) in publicDigests.Sources)
        {
            Assert.Equal(internalDigests.Sources[slug], digest);
        }

        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "public")).Code);
    }

    // ---------------------------------------------------------------- rollback

    [Fact]
    public async Task Rollback_opens_a_new_release_row_and_points_the_manifest_back_at_the_old_packs()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        Manifest first = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, "Deneme paragrafi 1 (duzeltildi).", ct);
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        Manifest second = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.NotEqual(first.Packs.Single(p => p.PackId == "hadis-sentetik").Sha256, second.Packs.Single(p => p.PackId == "hadis-sentetik").Sha256);
        Release firstRow = await harness.GetReleaseAsync(BuildFlavor.Dev, first.Release, ct);
        Release secondRow = await harness.GetReleaseAsync(BuildFlavor.Dev, second.Release, ct);
        int rowsBefore = await harness.CountReleasesAsync(ct);
        List<string> keysBefore = await harness.AllKeysAsync(ct);

        CliResult rolled = await harness.RunCliAsync("rollback", "--flavor", "dev", "--to", first.Release);

        Assert.Equal(0, rolled.Code);
        Assert.Equal(rowsBefore + 1, await harness.CountReleasesAsync(ct));
        Manifest current = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Assert.Equal("2026.11.2", current.Release);
        Assert.Equal(PackIds(first), PackIds(current));
        foreach (ManifestPack pack in current.Packs)
        {
            ManifestPack old = first.Packs.Single(p => p.PackId == pack.PackId);
            Assert.Equal((old.Version, old.Sha256, old.SizeBytes, old.Url), (pack.Version, pack.Sha256, pack.SizeBytes, pack.Url));
        }

        Release row = await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.2", ct);
        Assert.Equal((ReleaseRequests.GeriAlma, firstRow.Id, ReleaseStatus.Yayinlandi), (row.Talep, row.KaynakReleaseId, row.Durum));
        Assert.Equal(ReleaseStatus.GeriCekildi, (await harness.Releases.GetAsync(secondRow.Id, ct))!.Durum);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(firstRow.Id, ct))!.Durum);

        // Yeni manifest yeniden imzalanir; paket nesneleri silinmez, yalniz manifest gecmisi eklenir.
        Assert.True(ManifestVerifier.Verify(await harness.ManifestBytesAsync(BuildFlavor.Dev, ct), harness.Keys[BuildFlavor.Dev].GetPublicKey()).IsValid);
        Assert.Equal([StorageKeys.ManifestHistory("dev", "2026.11.2")], (await harness.AllKeysAsync(ct)).Except(keysBefore, StringComparer.Ordinal).ToArray());
        Assert.Equal(0, (await harness.RunCliAsync("verify", "--flavor", "dev")).Code);

        // Depoda olmayan surume geri alinamaz (4); depo ve satir sayisi degismez.
        int rows = await harness.CountReleasesAsync(ct);
        Assert.Equal(4, (await harness.RunCliAsync("rollback", "--flavor", "dev", "--to", "2026.11.9")).Code);
        Assert.Equal(rows, await harness.CountReleasesAsync(ct));
    }

    // ---------------------------------------------------------------- watch ve kilit

    [Fact]
    public async Task Watch_once_dispatches_each_request_by_its_request_type()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();

        // yayin: paket listesiyle.
        Release publish = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor", Paketler: ["core", "hadis-sentetik"], Notlar: "api talebi"),
            ct);
        Assert.Equal(0, (await harness.RunCliAsync("watch", "--once")).Code);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(publish.Id, ct))!.Durum);
        Assert.Equal(["core", "hadis-sentetik"], PackIds(await harness.ReadManifestAsync(BuildFlavor.Dev, ct)));

        // terfi: internal yayini public'e.
        ReleaseResult internalRelease = await harness.PublishAsync(BuildFlavor.Internal);
        Release source = await harness.GetReleaseAsync(BuildFlavor.Internal, internalRelease.Surum!, ct);
        Release promotion = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Public, source.Surum, ReleaseRequests.Terfi, "2026.11.09-api", "editor", source.Id),
            ct);
        Assert.Equal(0, (await harness.RunCliAsync("watch", "--once")).Code);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(promotion.Id, ct))!.Durum);
        Manifest promoted = await harness.ReadManifestAsync(BuildFlavor.Public, ct);
        Assert.Equal(source.Surum, promoted.Release);
        Assert.Equal(["core", "hadis-sentetik"], PackIds(promoted));

        // geri alma: dev'in ilk yayinina.
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, "Deneme paragrafi 1 (duzeltildi).", ct);
        ReleaseResult devSecond = await harness.PublishAsync(BuildFlavor.Dev);
        Assert.Equal(0, devSecond.ExitCode);
        Release rollback = await harness.Releases.CreateAsync(
            new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.GeriAlma, "2026.11.09-api", "editor", publish.Id),
            ct);
        Assert.Equal(0, (await harness.RunCliAsync("watch", "--once")).Code);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(rollback.Id, ct))!.Durum);
        Manifest rolledBack = await harness.ReadManifestAsync(BuildFlavor.Dev, ct);
        Manifest target = ManifestJson.Read((await harness.Reader.GetAsync(StorageKeys.ManifestHistory("dev", publish.Surum), ct))!);
        Assert.Equal(rollback.Surum, rolledBack.Release);
        Assert.Equal(target.Packs.Select(p => (p.PackId, p.Version, p.Sha256)).Order().ToArray(), rolledBack.Packs.Select(p => (p.PackId, p.Version, p.Sha256)).Order().ToArray());

        // Bekleyen talep yokken tek tur 0 ile biter.
        CliResult idle = await harness.RunCliAsync("watch", "--once");
        Assert.Equal(0, idle.Code);
        Assert.Contains("Bekleyen talep yok", idle.Out, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_second_publisher_exits_with_1_while_the_advisory_lock_is_held_and_works_after_it_is_released()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Release request = await harness.Releases.CreateAsync(new NewRelease(BuildFlavor.Dev, null, ReleaseRequests.Yayin, "2026.11.09-api", "editor"), ct);

        CliResult publishRun;
        CliResult watchRun;
        await using (PublisherLock? held = await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct))
        {
            Assert.NotNull(held);
            publishRun = await harness.RunCliAsync("publish", "--flavor", "dev");
            watchRun = await harness.RunCliAsync("watch", "--once");
        }

        Assert.Equal((1, 1), (publishRun.Code, watchRun.Code));
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
        Assert.Equal(ReleaseStatus.Hazirlaniyor, (await harness.Releases.GetAsync(request.Id, ct))!.Durum);
        Assert.Empty(await harness.AllKeysAsync(ct));

        // Kilit birakilinca ayni satir surdurulur ve yayinlanir.
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        Assert.Equal(ReleaseStatus.Yayinlandi, (await harness.Releases.GetAsync(request.Id, ct))!.Durum);
        Assert.Equal(1, await harness.CountReleasesAsync(ct));
    }

    // ---------------------------------------------------------------- upload

    [Fact]
    public async Task Upload_can_run_again_with_the_same_sha256_and_a_different_sha256_at_an_existing_key_exits_with_4()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        Assert.Equal(0, (await harness.RunCliAsync("publish", "--flavor", "dev")).Code);
        List<string> keys = await harness.AllKeysAsync(ct);
        Dictionary<string, StoredObject> heads = [];
        foreach (string key in keys.Where(k => k.StartsWith("packs/", StringComparison.Ordinal)))
        {
            heads[key] = (await harness.Reader.HeadAsync(key, ct))!;
        }

        // Ayni sha256: butun paketler atlanir, hicbir nesne degismez.
        CliResult again = await harness.RunCliAsync("upload", "--flavor", "dev", "--surum", "2026.11.0");

        Assert.Equal(0, again.Code);
        Assert.Equal(heads.Count, again.Out.Split('\n').Count(l => l.Contains("ayni, atlandi", StringComparison.Ordinal)));
        Assert.DoesNotContain("yuklendi", again.Out.Replace("ayni, atlandi", string.Empty, StringComparison.Ordinal), StringComparison.Ordinal);
        Assert.Equal(keys, await harness.AllKeysAsync(ct));
        foreach ((string key, StoredObject head) in heads)
        {
            Assert.Equal(head, await harness.Reader.HeadAsync(key, ct));
        }

        // build yuklemez: dogrulandi'da durur, cikti klasoru dolar.
        await harness.ChangeUnitAsync(EndToEndData.SentetikApproved, "Deneme paragrafi 1 (duzeltildi).", ct);
        CliResult built = await harness.RunCliAsync("build", "--flavor", "dev");
        Assert.Equal(0, built.Code);
        Assert.Equal(keys, await harness.AllKeysAsync(ct));
        Release pending = await harness.GetReleaseAsync(BuildFlavor.Dev, "2026.11.1", ct);
        Assert.Equal(ReleaseStatus.Dogrulandi, pending.Durum);
        string outDirectory = Path.Combine(harness.OutDir, "dev", "2026.11.1");
        Assert.True(File.Exists(Path.Combine(outDirectory, "manifest.json")));
        Assert.True(File.Exists(Path.Combine(outDirectory, "gate-report.json")));
        Assert.True(File.Exists(Path.Combine(outDirectory, "self-check.json")));
        Assert.True(File.Exists(Path.Combine(outDirectory, "hadis-sentetik-2026.11.1.db")));

        // Ayni anahtara FARKLI sha256: yukleme reddedilir (4), satir basarisiz olur, manifest.json eski yayinda kalir, mevcut nesneye dokunulmaz.
        string conflictKey = StorageKeys.Pack("dev", "hadis-sentetik", "2026.11.1");
        byte[] planted = Encoding.UTF8.GetBytes("baska icerik");
        string plantedFile = Path.Combine(harness.Directory.Path, "planted.db");
        await File.WriteAllBytesAsync(plantedFile, planted, ct);
        Assert.Equal(PutResult.Uploaded, await harness.Reader.PutPackAsync(conflictKey, plantedFile, new string('c', 64), ct));

        CliResult conflict = await harness.RunCliAsync("upload", "--flavor", "dev");

        Assert.Equal(4, conflict.Code);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(pending.Id, ct))!.Durum);
        Assert.Equal("2026.11.0", (await harness.ReadManifestAsync(BuildFlavor.Dev, ct)).Release);
        Assert.Equal(planted, await harness.Reader.GetAsync(conflictKey, ct));
        // Depodaki yetim nesne dogrulamada yakalanir (3).
        Assert.Equal(3, (await harness.RunCliAsync("verify", "--flavor", "dev")).Code);
    }

    // ---------------------------------------------------------------- gizli degerler

    [Fact]
    public async Task No_command_output_contains_a_configured_secret()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EndToEndHarness harness = await NewHarnessAsync();
        string[] secrets =
        [
            harness.Storage.SecretKey,
            harness.Storage.AccessKey,
            harness.Keys[BuildFlavor.Dev].SeedBase64(),
            new Npgsql.NpgsqlConnectionStringBuilder(harness.Database.ConnectionString).Password!,
        ];

        CliResult publish = await harness.RunCliAsync("publish", "--flavor", "dev");
        CliResult verify = await harness.RunCliAsync("verify", "--flavor", "dev");
        CliResult bad = await harness.RunCliAsync("rollback", "--flavor", "dev", "--to", "2026.11.9");
        string everything = publish.Out + publish.Error + verify.Out + verify.Error + bad.Out + bad.Error + harness.Out + harness.Error;
        string stored = Encoding.UTF8.GetString(await harness.ManifestBytesAsync(BuildFlavor.Dev, ct));

        Assert.All(secrets, s => Assert.False(string.IsNullOrEmpty(s)));
        foreach (string secret in secrets)
        {
            Assert.DoesNotContain(secret, everything, StringComparison.Ordinal);
            Assert.DoesNotContain(secret, stored, StringComparison.Ordinal);
        }
    }
}
