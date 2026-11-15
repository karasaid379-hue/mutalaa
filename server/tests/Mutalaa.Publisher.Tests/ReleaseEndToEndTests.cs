using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// A13.5 butunlesik test (Docker: gercek postgres:18 + gercek SeaweedFS kabi). Fikstur veritabani her icerik durumundan ornek tasir
/// (<see cref="EndToEndData"/>); uc derleme bir kez yayimlanir (<see cref="PublishedWorld"/>) ve bu siniftaki testler yayini YALNIZ OKUR.
/// Yayini degistiren senaryolar <see cref="ReleaseEndToEndFlowTests"/> icindedir.
/// </summary>
public class ReleaseEndToEndTests(PublishedWorld world, PostgresFixture postgres, SeaweedFixture seaweed) : IClassFixture<PublishedWorld>
{
    private EndToEndHarness Harness => world.Harness;

    public static TheoryData<BuildFlavor> Flavors => new() { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public };

    public static TheoryData<BuildFlavor, bool> FlavorsByCulture => new()
    {
        { BuildFlavor.Dev, false },
        { BuildFlavor.Dev, true },
        { BuildFlavor.Internal, false },
        { BuildFlavor.Internal, true },
        { BuildFlavor.Public, false },
        { BuildFlavor.Public, true },
    };

    private static string[] ExpectedPacks(BuildFlavor flavor) => flavor switch
    {
        BuildFlavor.Dev => ["core", "hadis-sentetik", "kelime-kok", "tefsir-test-ornek", "test-kucuk"],
        BuildFlavor.Internal => ["core", "hadis-sentetik", "kelime-kok", "test-kucuk"],
        _ => ["core", "hadis-sentetik", "kelime-kok"],
    };

    private async Task<Release> ReleaseOfAsync(BuildFlavor flavor, CancellationToken ct) =>
        await Harness.GetReleaseAsync(flavor, world.Results[flavor].Surum!, ct);

    private static IReadOnlyList<GateRow> RowsOf(IReadOnlyList<GateRow> rows, string kind, string id) =>
        [.. rows.Where(r => string.Equals(r.Kind, kind, StringComparison.Ordinal) && string.Equals(r.Id, id, StringComparison.Ordinal))];

    private static string AnyId(SeededContent content, string name) => content.Xrefs[name].Id.ToString("D", System.Globalization.CultureInfo.InvariantCulture);

    // ---------------------------------------------------------------- uc derleme uretimi

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task Each_flavor_is_published_with_its_pack_set_and_a_valid_signed_manifest(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string label = flavor.ToLabel();

        Manifest manifest = await Harness.ReadManifestAsync(flavor, ct);
        byte[] bytes = await Harness.ManifestBytesAsync(flavor, ct);
        Release row = await ReleaseOfAsync(flavor, ct);

        Assert.Equal(ExpectedPacks(flavor), manifest.Packs.Select(p => p.PackId).Order(StringComparer.Ordinal).ToArray());
        Assert.Equal((label, world.Results[flavor].Surum), (manifest.Flavor, manifest.Release));
        Assert.Equal((ReleaseStatus.Yayinlandi, ReleaseRequests.Yayin), (row.Durum, row.Talep));
        ManifestVerification verification = ManifestVerifier.Verify(bytes, Harness.Keys[flavor].GetPublicKey(), Harness.Keys[flavor].Kid);
        Assert.True(verification.IsValid, string.Join(";", verification.Errors.Select(e => e.Code)));
        Assert.StartsWith(label + "-", Harness.Keys[flavor].Kid, StringComparison.Ordinal);
        Assert.Equal(bytes, await Harness.Reader.GetAsync(StorageKeys.ManifestHistory(label, manifest.Release), ct));
        Assert.All(manifest.Packs, p => Assert.Equal($"{Harness.Storage.PublicBaseUrl}/packs/{label}/{p.PackId}/{p.Version}/{p.PackId}-{p.Version}.db", p.Url));
    }

    [Fact]
    public async Task The_three_flavors_get_distinct_versions_from_one_monthly_counter()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        string[] versions = [.. new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public }.Select(f => world.Results[f].Surum!)];

        Assert.Equal(["2026.11.0", "2026.11.1", "2026.11.2"], versions);
        Assert.Equal(3, await Harness.CountReleasesAsync(ct));
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task A_manifest_and_its_packs_are_publicly_readable_and_match_their_declared_sha256_and_size(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using HttpClient http = new();

        byte[] anonymousManifest = await http.GetByteArrayAsync(new Uri($"{Harness.Storage.PublicBaseUrl}/{flavor.ToLabel()}/manifest.json"), ct);
        Manifest manifest = ManifestJson.Read(anonymousManifest);

        Assert.Equal(await Harness.ManifestBytesAsync(flavor, ct), anonymousManifest);
        foreach (ManifestPack pack in manifest.Packs)
        {
            byte[] anonymousPack = await http.GetByteArrayAsync(new Uri(pack.Url), ct);
            Assert.Equal((pack.SizeBytes, pack.Sha256), (anonymousPack.LongLength, Convert.ToHexStringLower(SHA256.HashData(anonymousPack))));
        }
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task Pack_meta_matches_the_manifest_the_release_digests_and_the_self_check_passes(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Manifest manifest = await Harness.ReadManifestAsync(flavor, ct);
        Release row = await ReleaseOfAsync(flavor, ct);
        ReleaseDigests digests = ReleaseDigests.Parse(row.Ozetler);

        foreach (ManifestPack pack in manifest.Packs)
        {
            using PackDb db = await Harness.OpenPackAsync(flavor, pack.PackId, ct);
            Dictionary<string, string> meta = db.Meta();
            Assert.Equal((pack.PackId, pack.Version, flavor.ToLabel()), (meta["pack_id"], meta["version"], meta["flavor"]));
            Assert.Equal(digests.Packs[pack.PackId], meta["content_digest"]);
        }

        string selfCheck = await File.ReadAllTextAsync(Path.Combine(Harness.OutDir, flavor.ToLabel(), manifest.Release, "self-check.json"), ct);
        using JsonDocument document = JsonDocument.Parse(selfCheck);
        JsonElement[] packs = [.. document.RootElement.GetProperty("packs").EnumerateArray()];
        Assert.Equal(manifest.Packs.Count, packs.Length);
        Assert.All(packs, p => Assert.True(p.GetProperty("passed").GetBoolean(), p.GetProperty("pack_id").GetString()));
    }

    [Fact]
    public async Task The_core_self_check_probes_the_first_anchor_because_the_fixture_ends_at_2_33()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Manifest manifest = await Harness.ReadManifestAsync(BuildFlavor.Dev, ct);

        string selfCheck = await File.ReadAllTextAsync(Path.Combine(Harness.OutDir, "dev", manifest.Release, "self-check.json"), ct);
        using JsonDocument document = JsonDocument.Parse(selfCheck);
        JsonElement core = document.RootElement.GetProperty("packs").EnumerateArray().Single(p => p.GetProperty("pack_id").GetString() == "core");
        JsonElement probe = core.GetProperty("checks").EnumerateArray().Single(c => c.GetProperty("name").GetString() == "probe_anchor");

        Assert.StartsWith("q:1:1 satir=1", probe.GetProperty("detail").GetString(), StringComparison.Ordinal);
        using PackDb db = await Harness.OpenPackAsync(BuildFlavor.Dev, "core", ct);
        Assert.Equal(40, db.Scalar<int>("SELECT count(*) FROM unit"));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM unit WHERE anchor = 'q:2:255'"));
        Assert.Equal((1, 0), (db.Scalar<int>("SELECT count(*) FROM unit WHERE anchor = 'q:2:33'"), db.Scalar<int>("SELECT count(*) FROM unit WHERE anchor = 'q:2:34'")));
    }

    // ---------------------------------------------------------------- kapi kurallari

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P01_every_published_source_has_a_registry_file_and_an_attribution_text(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Release row = await ReleaseOfAsync(flavor, ct);
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(row);

        Assert.Empty(EndToEndHarness.Violations(row));
        Assert.DoesNotContain(rows, r => r.Rule == "P-01");
        foreach (string slug in new[] { EndToEndData.Uthmani, EndToEndData.SimpleClean, EndToEndData.UstVeri, EndToEndData.Sentetik })
        {
            GateRow source = Assert.Single(RowsOf(rows, "kaynak", slug));
            Assert.Equal("girdi", source.Decision);
        }

        // Pakete yazilan atif satirlari kaynak kaydindan (source) aynen gelir.
        using PackDb db = await Harness.OpenPackAsync(flavor, "hadis-sentetik", ct);
        Assert.Equal("Sentetik test verisi (Mutalaa).", db.Column("SELECT required_credit FROM attribution WHERE source_id = 'hadis-sentetik'").Single());
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P07_links_enter_by_status_type_and_confidence_per_flavor(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeededContent content = Harness.Content;
        Manifest manifest = await Harness.ReadManifestAsync(flavor, ct);

        Dictionary<string, string[]> expectedNames = new(StringComparer.Ordinal)
        {
            // K-51: benzer_ayet core'da, kok ve lemma kelime-kok'te; xref_gate fiksturde bos oldugundan public'te otomatik aday satirlar girmez (kapi-olculmedi), onayli girer.
            ["core"] = flavor == BuildFlavor.Public ? ["benzer-onayli"] : ["benzer-onayli", "benzer-yuksek"],
            [EndToEndData.KelimeKokPack] = flavor == BuildFlavor.Public ? ["kok-onayli"] : ["kok-onayli", "kok-orta", "kok-yuksek"],
            ["hadis-sentetik"] = flavor == BuildFlavor.Public ? ["atif-onayli"] : ["atif-aday", "atif-onayli"],
            ["test-kucuk"] = ["iktibas-kucuk"],
            ["tefsir-test-ornek"] = ["ima-tefsir"],
        };

        List<string> everywhere = [];
        foreach (ManifestPack pack in manifest.Packs)
        {
            using PackDb db = await Harness.OpenPackAsync(flavor, pack.PackId, ct);
            string[] actual = [.. db.Column("SELECT id FROM xref_idx").Order(StringComparer.Ordinal)];
            string[] expected = [.. expectedNames[pack.PackId].Select(n => AnyId(content, n)).Order(StringComparer.Ordinal)];
            Assert.Equal(expected, actual);
            everywhere.AddRange(actual);

            if (pack.PackId == EndToEndData.KelimeKokPack && flavor != BuildFlavor.Public)
            {
                // approved/folded onceden hesaplanir: 0,6 guvenli aday katlanir (< 0,70), 0,9 guvenli aday katlanmaz.
                Assert.Equal((0, 1), (db.Scalar<int>("SELECT approved FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "kok-orta"))), db.Scalar<int>("SELECT folded FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "kok-orta")))));
                Assert.Equal((0, 0), (db.Scalar<int>("SELECT approved FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "kok-yuksek"))), db.Scalar<int>("SELECT folded FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "kok-yuksek")))));
            }

            if (pack.PackId == "core")
            {
                Assert.Equal(1, db.Scalar<int>("SELECT approved FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "benzer-onayli"))));
                Assert.Equal("{}", db.Scalar<string>("SELECT value FROM pack_meta WHERE key = 'gate_summary'"));
            }

            if (pack.PackId == "hadis-sentetik")
            {
                Assert.Equal(1, db.Scalar<int>("SELECT approved FROM xref_idx WHERE id = $id", ("$id", AnyId(content, "atif-onayli"))));
            }
        }

        // red hicbir derlemeye, esigin altindaki otomatik aday hicbir derlemeye girmez.
        Assert.DoesNotContain(AnyId(content, "atif-red"), everywhere);
        Assert.DoesNotContain(AnyId(content, "kok-dusuk"), everywhere);

        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(await ReleaseOfAsync(flavor, ct));
        Assert.Equal(("girmedi", "P-07", "red", 1), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "atif" && r.Reason == "red")));
        Assert.Equal(("girmedi", "P-07", "dusuk-guven", 1), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "kok" && r.Reason == "dusuk-guven")));
        if (flavor == BuildFlavor.Public)
        {
            // K-51 madde 5: olculmemis turun aday satirlari public'e girmez; rapor "girmedi - P-07" yazar ve onayli satir girer.
            Assert.Equal(("girmedi", "P-07", "kapi-olculmedi", 2), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "kok" && r.Reason == "kapi-olculmedi")));
            Assert.Equal(("girmedi", "P-07", "kapi-olculmedi", 1), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "benzer_ayet" && r.Reason == "kapi-olculmedi")));
            GateRow gateRow = Assert.Single(rows, r => r.Kind == "kapi" && r.Id == "kok");
            Assert.Equal(("girmedi", "P-07", "kapi-olculmedi"), (gateRow.Decision, gateRow.Rule, gateRow.Reason));
        }
        else
        {
            Assert.Equal(("girdi", (string?)null, "aday", 2), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "kok" && r.Reason == "aday")));
        }

        if (flavor == BuildFlavor.Public)
        {
            Assert.Equal(("girmedi", "P-07", "aday-public", 1), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "atif" && r.Reason == "aday-public")));
            Assert.DoesNotContain(rows, r => r.Kind == "baglanti" && r.Id == "atif" && r.Reason == "aday");
        }
        else
        {
            Assert.Equal(("girdi", (string?)null, "aday", 1), Reduce(Assert.Single(rows, r => r.Kind == "baglanti" && r.Id == "atif" && r.Reason == "aday")));
        }
    }

    private static (string Decision, string? Rule, string Reason, int Count) Reduce(GateRow row) => (row.Decision, row.Rule, row.Reason, row.Count);

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P08_and_P10_unapproved_text_and_ai_drafts_enter_only_the_internal_flavors_with_the_unverified_flag(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackDb db = await Harness.OpenPackAsync(flavor, "hadis-sentetik", ct);
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(await ReleaseOfAsync(flavor, ct));
        IReadOnlyList<GateRow> unitRows = RowsOf(rows, "birim", EndToEndData.Sentetik);

        if (flavor == BuildFlavor.Public)
        {
            Assert.Equal([EndToEndData.SentetikApproved], db.Anchors());
            Assert.Equal(1, db.Scalar<int>("SELECT min(approved) FROM unit"));
            Assert.Contains(unitRows, r => r.Decision == "girmedi" && r.Rule == "P-10" && r.Reason == GateReasons.OnaysizBirim && r.Count == 1);
            Assert.Contains(unitRows, r => r.Decision == "girmedi" && r.Rule == "P-08" && r.Reason == GateReasons.YapayZekaTaslagi && r.Count == 1);
        }
        else
        {
            Assert.Equal([EndToEndData.SentetikApproved, EndToEndData.SentetikDraft, EndToEndData.SentetikAi], db.Anchors());
            Assert.Equal(
                [(EndToEndData.SentetikApproved, 1), (EndToEndData.SentetikDraft, 0), (EndToEndData.SentetikAi, 0)],
                db.Column("SELECT anchor || '|' || approved FROM unit ORDER BY rowid").Select(s => (s.Split('|')[0], int.Parse(s.Split('|')[1], System.Globalization.CultureInfo.InvariantCulture))));
            Assert.Contains(unitRows, r => r.Decision == "girdi" && r.Reason == GateReasons.Dogrulanmamis && r.Count == 2);
            Assert.DoesNotContain(unitRows, r => r.Decision == "girmedi");
        }
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P09_only_approved_word_fixes_are_applied_and_the_candidate_is_reported_as_left_out(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(await ReleaseOfAsync(flavor, ct));

        GateRow[] fixes = [.. RowsOf(rows, "sozluk", "quran_word_fix")];

        // Her derlemede yalniz onayli duzeltme uygulanir (iki onayli, bir aday, bir red).
        Assert.Equal(2, fixes.Length);
        Assert.Single(fixes, r => r.Decision == "girdi" && r.Reason == GateReasons.Uygun && r.Count == 2);
        Assert.Single(fixes, r => r.Decision == "girmedi" && r.Rule == "P-09" && r.Reason == GateReasons.OnaysizSatir && r.Count == 2);

        using PackDb db = await Harness.OpenPackAsync(flavor, EndToEndData.KelimeKokPack, ct);
        Assert.Equal("2", db.Meta()[PackMetaKeys.WordFixCount]);
        Assert.Equal("N", db.Scalar<string>("SELECT pos FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixApprovedPos)));
        Assert.Equal(2, db.Scalar<int>("SELECT root_id FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixApprovedRoot)));
        Assert.Equal(1, db.Scalar<int>("SELECT root_id FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixCandidate)));
        Assert.Equal("V", db.Scalar<string>("SELECT pos FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixCandidate)));
        Assert.Equal("V", db.Scalar<string>("SELECT pos FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixRejected)));
        Assert.Equal("{\"deneme\":\"1\"}", db.Scalar<string>("SELECT features FROM word_morph WHERE anchor = $a", ("$a", EndToEndData.FixApprovedPos)));
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P09_candidate_glosses_enter_only_dev_and_internal_with_status_aday_and_the_public_pack_has_none(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        bool inner = flavor != BuildFlavor.Public;
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(await ReleaseOfAsync(flavor, ct));

        GateRow[] glosses = [.. RowsOf(rows, "sozluk", "lemma_gloss")];

        // red hicbir derlemeye girmez; aday yalniz dev ve internal'a girer (public'te dista kalan anlam sayisi = aday sayisi).
        Assert.Single(glosses, r => r.Decision == "girdi" && r.Reason == GateReasons.Uygun && r.Count == 1);
        Assert.Single(glosses, r => r.Decision == "girmedi" && r.Rule == "P-09" && r.Reason == GateReasons.Red && r.Count == 1);
        if (inner)
        {
            Assert.Equal(3, glosses.Length);
            Assert.Single(glosses, r => r.Decision == "girdi" && r.Reason == GateReasons.Aday && r.Count == 2);
        }
        else
        {
            Assert.Equal(3, glosses.Length);
            Assert.Single(glosses, r => r.Decision == "girmedi" && r.Rule == "P-09" && r.Reason == GateReasons.AdayPublic && r.Count == 2);
        }

        using PackDb db = await Harness.OpenPackAsync(flavor, EndToEndData.KelimeKokPack, ct);
        Assert.Equal(inner ? 2 : 0, db.Scalar<int>("SELECT count(*) FROM lemma_gloss WHERE status = 'aday'"));
        Assert.Equal(1, db.Scalar<int>("SELECT count(*) FROM lemma_gloss WHERE status = 'onayli'"));
        Assert.Equal(inner ? 3 : 1, db.Scalar<int>("SELECT count(*) FROM lemma_gloss"));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM lemma_gloss WHERE lemma_id = $id", ("$id", EndToEndData.LemmaRejected)));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM lemma_gloss WHERE origin = ''"));
        Assert.Equal("editor", db.Scalar<string>("SELECT origin FROM lemma_gloss WHERE lemma_id = $id", ("$id", EndToEndData.LemmaApproved)));
        Assert.Empty(EndToEndHarness.Violations(await ReleaseOfAsync(flavor, ct)));
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task The_kelime_kok_pack_carries_the_qac_dictionary_with_its_sources_and_an_untouched_attribution(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(await ReleaseOfAsync(flavor, ct));
        using PackDb db = await Harness.OpenPackAsync(flavor, EndToEndData.KelimeKokPack, ct);

        GateRow pack = Assert.Single(RowsOf(rows, "paket", EndToEndData.KelimeKokPack));
        Assert.Equal("girdi", pack.Decision);
        Assert.Equal(2, db.Scalar<int>("SELECT count(*) FROM root"));
        Assert.Equal(5, db.Scalar<int>("SELECT count(*) FROM lemma WHERE lang = 'ar'"));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM lemma WHERE lang <> 'ar'"));
        int morphWords = Harness.Content.Uthmani.Verses.Take(2).Sum(v => v.Text.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length);
        Assert.Equal(morphWords, db.Scalar<int>("SELECT count(*) FROM word_morph"));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM tr_form"));
        Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM tr_root_index"));
        Assert.Equal([EndToEndData.Qac, EndToEndData.Wbw], db.Column("SELECT source_id FROM pack_source ORDER BY source_id"));
        Assert.Equal([EndToEndData.Qac, EndToEndData.Wbw], db.Column("SELECT source_id FROM attribution ORDER BY source_id"));
        Assert.Equal("Sentetik test verisi (Mutalaa).", db.Scalar<string>("SELECT required_credit FROM attribution WHERE source_id = $s", ("$s", EndToEndData.Qac)));
        Assert.Equal("0", db.Meta()["unit_count"]);
    }

    [Theory]
    [MemberData(nameof(FlavorsByCulture))]
    public async Task P11_the_tanzil_units_and_the_notice_are_byte_identical_to_the_raw_files(BuildFlavor flavor, bool turkish)
    {
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            SeededContent content = Harness.Content;
            using PackDb db = await Harness.OpenPackAsync(flavor, "core", ct);

            // Bildirim: pakete yazilan attribution.notice_text, ham dosyanin bildirim blogu ile bayt bayt ayni.
            string notice = db.Column("SELECT notice_text FROM attribution WHERE source_id = 'tanzil-uthmani'").Single();
            Assert.Equal(Encoding.UTF8.GetBytes(content.UthmaniNotice), Encoding.UTF8.GetBytes(notice));
            Assert.Equal(
                Encoding.UTF8.GetBytes(content.SimpleCleanNotice),
                Encoding.UTF8.GetBytes(db.Column("SELECT notice_text FROM attribution WHERE source_id = 'tanzil-simple-clean'").Single()));
            Assert.StartsWith("\n\n#", notice, StringComparison.Ordinal);

            // Ayet metni: 40 satir, bayt bayt ham dosyadaki gibi ve content_hash ham metinden yeniden hesaplanan ile ayni.
            Assert.Equal(40, content.Uthmani.Verses.Count);
            foreach (TanzilVerse verse in content.Uthmani.Verses)
            {
                string anchor = string.Create(System.Globalization.CultureInfo.InvariantCulture, $"q:{verse.Sure}:{verse.Ayet}");
                string text = db.Column("SELECT text FROM unit WHERE anchor = $a", ("$a", anchor)).Single();
                string hash = db.Column("SELECT content_hash FROM unit WHERE anchor = $a", ("$a", anchor)).Single();
                Assert.Equal(Encoding.UTF8.GetBytes(verse.Text), Encoding.UTF8.GetBytes(text));
                Assert.Equal(ContentHash.Compute(verse.Text), hash);
            }

            // Ayet etiketi "{s}:{a}" (sure adlari onaylanana kadar), sure tablosu bos.
            Assert.Equal("1:1", db.Column("SELECT label FROM unit WHERE anchor = 'q:1:1'").Single());
            Assert.Equal(0, db.Scalar<int>("SELECT count(*) FROM sure"));
            Assert.Equal(["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"], db.Column("SELECT source_id FROM pack_source ORDER BY source_id"));
        });
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task P12_test_sources_follow_the_flavor_policy(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Release row = await ReleaseOfAsync(flavor, ct);
        IReadOnlyList<GateRow> rows = EndToEndHarness.GateRows(row);
        Manifest manifest = await Harness.ReadManifestAsync(flavor, ct);
        string[] packIds = [.. manifest.Packs.Select(p => p.PackId)];

        // internal: yalniz uctan uca fikstur kaynaklari (test-kucuk, test-ses); tefsir ornegi P-12 ile girmez. public: ikisi de girmez.
        (string Slug, bool Enters)[] expected = flavor switch
        {
            BuildFlavor.Dev => [(EndToEndData.Kucuk, true), (EndToEndData.Tefsir, true), (EndToEndData.Ses, true)],
            BuildFlavor.Internal => [(EndToEndData.Kucuk, true), (EndToEndData.Tefsir, false), (EndToEndData.Ses, true)],
            _ => [(EndToEndData.Kucuk, false), (EndToEndData.Tefsir, false), (EndToEndData.Ses, false)],
        };
        foreach ((string slug, bool enters) in expected)
        {
            GateRow source = Assert.Single(RowsOf(rows, "kaynak", slug));
            Assert.Equal(enters ? ("girdi", (string?)null) : ("girmedi", "P-12"), (source.Decision, source.Rule));
        }

        Assert.Equal(expected[0].Enters, packIds.Contains("test-kucuk", StringComparer.Ordinal));
        Assert.Equal(expected[1].Enters, packIds.Contains("tefsir-test-ornek", StringComparer.Ordinal));
        Assert.Empty(EndToEndHarness.Violations(row));
        if (!expected[1].Enters)
        {
            GateRow pack = Assert.Single(RowsOf(rows, "paket", "tefsir-test-ornek"));
            Assert.Equal(("girmedi", "P-12"), (pack.Decision, pack.Rule));
        }
    }

    [Fact]
    public async Task P12_internal_admits_test_kucuk_but_not_the_tefsir_example_and_public_admits_neither()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Manifest internalManifest = await Harness.ReadManifestAsync(BuildFlavor.Internal, ct);
        Manifest publicManifest = await Harness.ReadManifestAsync(BuildFlavor.Public, ct);

        Assert.Contains(internalManifest.Packs, p => p.PackId == "test-kucuk");
        Assert.DoesNotContain(internalManifest.Packs, p => p.PackId == "tefsir-test-ornek");
        Assert.DoesNotContain(publicManifest.Packs, p => p.PackId is "test-kucuk" or "tefsir-test-ornek");

        // Her derlemede paket imzali manifestin yaninda depoda yalniz kendi derlemesinin nesneleri vardir.
        List<string> keys = await Harness.AllKeysAsync(ct);
        Assert.DoesNotContain(keys, k => k.StartsWith("packs/public/test-", StringComparison.Ordinal) || k.StartsWith("packs/public/tefsir-test-", StringComparison.Ordinal));
        Assert.DoesNotContain(keys, k => k.StartsWith("packs/internal/tefsir-test-", StringComparison.Ordinal));
        Assert.Contains(keys, k => k.StartsWith("packs/dev/tefsir-test-ornek/", StringComparison.Ordinal));
    }

    // ---------------------------------------------------------------- FTS sorgusu ve imza

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task The_core_pack_answers_an_fts_query_built_from_its_own_data(bool turkish)
    {
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            using PackDb db = await Harness.OpenPackAsync(BuildFlavor.Dev, "core", ct);
            string token = Harness.Content.ProbeArabicToken;
            Assert.NotEmpty(token);

            // Belirtec ilk ayetin ar_norm alanindan turetildi (metin elle yazilmaz); sorgu o ayeti bulur.
            List<string> hits = db.Column("SELECT u.anchor FROM unit_fts f JOIN unit u ON u.rowid = f.rowid WHERE unit_fts MATCH $q ORDER BY u.rowid", ("$q", "ar_norm : \"" + token + "\""));
            Assert.Contains("q:1:1", hits);
            Assert.Equal(1, db.Scalar<int>("SELECT count(*) FROM unit WHERE anchor = 'q:1:1'"));
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task The_test_kucuk_pack_finds_the_dotless_i_word_under_either_culture(bool turkish)
    {
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            using PackDb db = await Harness.OpenPackAsync(BuildFlavor.Internal, "test-kucuk", ct);
            string key = SearchNormalizer.TurkishWide(EndToEndData.Light);

            List<string> hits = db.Column("SELECT u.anchor FROM unit_fts f JOIN unit u ON u.rowid = f.rowid WHERE unit_fts MATCH $q ORDER BY u.rowid", ("$q", "tr_wide : \"" + key + "\""));

            Assert.Equal("isik", key);
            Assert.Equal([EndToEndData.KucukFirst], hits);
        });
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task Each_manifest_verifies_only_with_its_own_flavor_key_and_a_tampered_copy_does_not(BuildFlavor flavor)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        byte[] bytes = await Harness.ManifestBytesAsync(flavor, ct);
        BuildFlavor other = flavor == BuildFlavor.Dev ? BuildFlavor.Internal : BuildFlavor.Dev;

        Assert.True(ManifestVerifier.Verify(bytes, Harness.Keys[flavor].GetPublicKey()).IsValid);
        Assert.False(ManifestVerifier.Verify(bytes, Harness.Keys[other].GetPublicKey()).IsValid);

        string tampered = Encoding.UTF8.GetString(bytes).Replace("\"size_bytes\":", "\"size_bytes\":1", StringComparison.Ordinal);
        Assert.NotEqual(Encoding.UTF8.GetString(bytes), tampered);
        Assert.False(ManifestVerifier.Verify(Encoding.UTF8.GetBytes(tampered), Harness.Keys[flavor].GetPublicKey()).IsValid);
    }

    [Theory]
    [MemberData(nameof(Flavors))]
    public async Task Verify_command_passes_on_every_published_flavor(BuildFlavor flavor)
    {
        CliResult result = await Harness.RunCliAsync("verify", "--flavor", flavor.ToLabel());

        Assert.Equal((0, string.Empty), (result.Code, result.Error));
        Assert.Contains("Dogrulama tamam", result.Out, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_core_pack_is_bundled_and_depends_on_nothing_in_every_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            Manifest manifest = await Harness.ReadManifestAsync(flavor, ct);
            ManifestPack core = manifest.Packs.Single(p => p.PackId == "core");
            Assert.Empty(core.DependsOn);
            Assert.True(core.Bundled == true);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_fresh_database_built_under_either_culture_yields_the_same_source_and_pack_digests_as_the_published_release(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        ReleaseDigests expected = ReleaseDigests.Parse((await ReleaseOfAsync(BuildFlavor.Dev, ct)).Ozetler);
        ReleaseDigests actual = ReleaseDigests.Empty;

        // Tohumlama, kapi, paket yazimi ve ozetleme ayni kulturde calisir: tr-TR (I/i tuzagi) ozetleri degistirmemeli.
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            await using EndToEndHarness fresh = await EndToEndHarness.CreateAsync(postgres, seaweed);
            ReleaseResult result = await fresh.PublishAsync(BuildFlavor.Dev);
            Assert.Equal(ExitCodes.Success, result.ExitCode);
            actual = ReleaseDigests.Parse((await fresh.GetReleaseAsync(BuildFlavor.Dev, result.Surum!, ct)).Ozetler);
        });

        Assert.Equal(expected.Sources, actual.Sources);
        Assert.Equal(expected.Packs, actual.Packs);
        Assert.NotEmpty(actual.Packs);
    }
}
