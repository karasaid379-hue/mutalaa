using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>release.ozetler bicimi, kaynak ozeti (K-46 madde 1) ve PackInspector (Docker'siz).</summary>
public class ReleaseDigestsTests
{
    private static readonly string EmptyDigest = ContentDigest.Compute([]);

    [Fact]
    public void Round_trips_in_ordinal_key_order()
    {
        ReleaseDigests digests = new(
            new Dictionary<string, string>(StringComparer.Ordinal) { ["b"] = "2", ["a"] = "1" },
            new Dictionary<string, string>(StringComparer.Ordinal) { ["z"] = "9", ["core"] = "8" });

        string json = digests.ToJson();

        Assert.Equal("""{"kaynaklar":{"a":"1","b":"2"},"paketler":{"core":"8","z":"9"}}""", json);
        ReleaseDigests parsed = ReleaseDigests.Parse(json);
        Assert.Equal(digests.Sources, parsed.Sources);
        Assert.Equal(digests.Packs, parsed.Packs);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("{}")]
    [InlineData("[]")]
    [InlineData("bozuk")]
    [InlineData("""{"kaynaklar":[1],"paketler":"x"}""")]
    public void Empty_or_malformed_values_parse_as_empty(string? json)
    {
        ReleaseDigests parsed = ReleaseDigests.Parse(json);

        Assert.Empty(parsed.Sources);
        Assert.Empty(parsed.Packs);
    }

    [Fact]
    public void Source_digest_follows_the_content_digest_rule_over_active_units_only()
    {
        UnitRow a = PackTestData.Unit("k:x:p1", "x", metin: "Deneme paragrafi 1");
        UnitRow b = PackTestData.Unit("k:x:p2", "x", metin: "Deneme paragrafi 2");
        UnitRow retired = PackTestData.Unit("k:x:p3", "x", metin: "Deneme paragrafi 3", status: "kullanim_disi", successors: "k:x:p2");
        EditorialSnapshot snapshot = new() { Units = [b, retired, a] };

        IReadOnlyDictionary<string, string> digests = SourceDigests.Compute(snapshot, ["x"]);

        Assert.Equal(ContentDigest.Compute([new ContentDigestEntry(a.Anchor, a.ContentHash), new ContentDigestEntry(b.Anchor, b.ContentHash)]), digests["x"]);
    }

    [Fact]
    public void Source_digest_changes_when_one_content_hash_changes_and_ignores_other_sources()
    {
        UnitRow a = PackTestData.Unit("k:x:p1", "x", metin: "Deneme paragrafi 1");
        UnitRow other = PackTestData.Unit("k:y:p1", "y", metin: "Deneme paragrafi 9");
        UnitRow changed = PackTestData.Unit("k:x:p1", "x", metin: "Deneme paragrafi 1 duzeltildi");

        string before = SourceDigests.Compute(new EditorialSnapshot { Units = [a, other] }, ["x"])["x"];
        string same = SourceDigests.Compute(new EditorialSnapshot { Units = [a] }, ["x"])["x"];
        string after = SourceDigests.Compute(new EditorialSnapshot { Units = [changed, other] }, ["x"])["x"];

        Assert.Equal(before, same);
        Assert.NotEqual(before, after);
    }

    [Fact]
    public void A_source_without_units_or_structure_rows_gets_the_empty_digest()
    {
        IReadOnlyDictionary<string, string> digests = SourceDigests.Compute(new EditorialSnapshot(), ["bos"]);

        Assert.Equal(EmptyDigest, digests["bos"]);
    }

    [Fact]
    public void A_structure_only_source_hashes_its_page_and_marker_rows_independent_of_input_order()
    {
        PageMapRow page1 = new("ust-veri", null, 1, null, "q:1:1", null, "q:1:3", null);
        PageMapRow page2 = new("ust-veri", null, 2, null, "q:1:4", null, "q:1:7", null);
        QuranMarkerRow marker = new("cuz", 1, "q:1:1", null, "ust-veri");

        string one = SourceDigests.Compute(new EditorialSnapshot { PageMaps = [page1, page2], QuranMarkers = [marker] }, ["ust-veri"])["ust-veri"];
        string reordered = SourceDigests.Compute(new EditorialSnapshot { PageMaps = [page2, page1], QuranMarkers = [marker] }, ["ust-veri"])["ust-veri"];
        string fewer = SourceDigests.Compute(new EditorialSnapshot { PageMaps = [page1], QuranMarkers = [marker] }, ["ust-veri"])["ust-veri"];
        string otherSource = SourceDigests.Compute(new EditorialSnapshot { PageMaps = [page1, page2], QuranMarkers = [marker] }, ["baska"])["baska"];

        Assert.Equal(one, reordered);
        Assert.NotEqual(one, fewer);
        Assert.NotEqual(EmptyDigest, one);
        Assert.Equal(EmptyDigest, otherSource);
    }

    [Fact]
    public void The_turkish_lemma_source_digest_follows_status_approval_path_evidence_presence_and_the_offset_rows()
    {
        const string slug = "kaikki-tr";
        TrLemmaRow Lemma(string status, string? path, bool kanit) => new(1, "deneme", "deneme-1", 1, 0, null, false, 3, status, path, kanit, "kaikki", slug, "dv-1");
        TrRootIndexRow Index(string hash) => new("meal:elmalili:1:1", 0, 4, 1, 1, false, hash, "dv-1");
        string Digest(TrLemmaRow lemma, params TrRootIndexRow[] index) =>
            SourceDigests.Compute(new EditorialSnapshot { TrLemmas = [lemma], TrRootIndex = index, TrForms = [new TrFormRow("deneme", "deneme", 1, 2, "dv-1")] }, [slug])[slug];

        string auto = Digest(Lemma("onayli", "otomatik", true), Index("0123456789abcdef"));

        Assert.NotEqual(EmptyDigest, auto);
        Assert.Equal(auto, Digest(Lemma("onayli", "otomatik", true), Index("0123456789abcdef")));
        Assert.NotEqual(auto, Digest(Lemma("aday", "otomatik", true), Index("0123456789abcdef")));
        Assert.NotEqual(auto, Digest(Lemma("onayli", "editor", true), Index("0123456789abcdef")));
        Assert.NotEqual(auto, Digest(Lemma("onayli", "otomatik", false), Index("0123456789abcdef")));
        Assert.NotEqual(auto, Digest(Lemma("onayli", "otomatik", true), Index("fedcba9876543210")));
        Assert.NotEqual(auto, Digest(Lemma("onayli", "otomatik", true)));
        Assert.Equal(EmptyDigest, SourceDigests.Compute(new EditorialSnapshot { TrLemmas = [Lemma("onayli", "editor", true)] }, ["baska"])["baska"]);
    }

    [Fact]
    public async Task PackInspector_reads_meta_sources_attributions_and_anchors_from_a_written_pack()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        SqlitePackWriter writer = new(PackTestData.Definitions());
        PackContent content = PackTestData.SmallContent(BuildFlavor.Internal);
        PackFile file = await writer.WriteAsync(content, PackTestData.Request(dir.Path), ct);

        PackFileMeta meta = PackInspector.ReadMeta(file.Path);
        Assert.Equal(("test-kucuk", "2026.11.0", "internal", "1", file.ContentDigest), (meta.PackId, meta.Version, meta.Flavor, meta.SchemaVersion, meta.ContentDigest));
        Assert.Equal(["test-kucuk"], PackInspector.ReadPackSources(file.Path));
        Assert.Equal(
            ["k:test-kucuk:bolum-1:p1", "k:test-kucuk:bolum-1:p2", "k:test-kucuk:bolum-1:p3"],
            PackInspector.ReadUnitAnchors(file.Path));
        PackAttributionInfo attribution = Assert.Single(PackInspector.ReadAttributions(file.Path));
        Assert.Equal(("test-kucuk", "Deneme kaynagi", "Sentetik test verisi (Mutalaa)."), (attribution.SourceId, attribution.Title, attribution.RequiredCredit));

        // Okuma sonrasi dosya kilitli kalmaz (Pooling=False): silinebilir.
        File.Delete(file.Path);
        Assert.False(File.Exists(file.Path));
    }
}
