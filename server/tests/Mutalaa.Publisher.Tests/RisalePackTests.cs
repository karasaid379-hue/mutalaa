using System.Globalization;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// Risale paketleri (A20.4, K-51): katalogun shared/data/risale-kitaplar.json ile senkronu, risale-{kitap} (yalniz unit), risale-dizin (unit_ref, icerigi olmayan
/// unit_fts ve unit_tri, xref_idx, page_map), etiket, gorunurluk ve kapi kurallari. Girdi tamamen sentetiktir: "Deneme paragrafi N", uydurma Arapca harf dizisi;
/// gercek Risale metni yoktur (kitap basliklari katalogdan okunur). Docker gerektirmez.
/// </summary>
public partial class RisalePackTests
{
    private const string BookSozler = "sozler";
    private const string BookOsmanlica = "sozler-osmanlica";
    private const string FixtureBook = PackCatalog.RisaleFixtureBookSlug;

    private const string S1 = "rn:sozler:soz-1:p1";
    private const string S2 = "rn:sozler:soz-1:p2";
    private const string O1 = "rn:sozler-osmanlica:soz-1:p1";
    private const string T1 = "rn:test-ornek:bolum-1:p1";

    private static readonly Guid XrefToApproved = new("0190c000-0000-7000-8000-000000000001");
    private static readonly Guid XrefToDraft = new("0190c000-0000-7000-8000-000000000002");

    private static PackCatalog Catalog => PackCatalog.Default;

    private static RisaleBook Book(string slug) => RisaleBookTable.Default.Single(b => string.Equals(b.Slug, slug, StringComparison.Ordinal));

    // ---------------------------------------------------------------- katalog <-> shared/data/risale-kitaplar.json

    [Fact]
    public void Embedded_book_table_is_byte_identical_to_the_shared_json_file()
    {
        byte[] file = File.ReadAllBytes(RepoFiles.PathOf("shared/data/risale-kitaplar.json"));

        Assert.Equal(file, RisaleBookTable.ReadEmbeddedBytes());
    }

    [Fact]
    public void Catalog_is_generated_from_the_json_file_one_pack_per_book_plus_index_and_fixture()
    {
        using JsonDocument document = JsonDocument.Parse(File.ReadAllBytes(RepoFiles.PathOf("shared/data/risale-kitaplar.json")));
        JsonElement[] rows = [.. document.RootElement.GetProperty("kitaplar").EnumerateArray()];

        Assert.Equal(87, rows.Length);
        Assert.Equal(87, RisaleBookTable.Default.Count);
        Assert.Equal(rows.Select(r => r.GetProperty("slug").GetString()!), RisaleBookTable.Default.Select(b => b.Slug));

        foreach (JsonElement row in rows)
        {
            string slug = row.GetProperty("slug").GetString()!;
            PackDefinition pack = Catalog.Get("risale-" + slug);

            Assert.Equal(row.GetProperty("baslik").GetString(), pack.Title);
            Assert.Equal(row.GetProperty("dil").GetString(), pack.Book!.Language);
            Assert.Equal(row.GetProperty("yon").GetString(), pack.Book.Direction);
            Assert.Equal(row.GetProperty("rnk").GetProperty("cilt").GetInt32(), pack.Book.Volume);
            Assert.Equal("rn:" + slug, pack.AnchorPrefix);
            Assert.Equal([(PackCatalog.RisaleTextSlug, PackSourceRole.Content, true)], pack.Sources.Select(s => (s.Slug, s.Role, s.Required)));
            Assert.Empty(pack.DependsOn);
            Assert.False(pack.Bundled);
            Assert.False(pack.IndexesBooks);
        }

        // 87 kitap + risale-dizin + risale-test-ornek.
        Assert.Equal(89, Catalog.All.Count(p => p.PackId.StartsWith("risale-", StringComparison.Ordinal)));
        Assert.Equal(87, Catalog.All.Count(p => p.Book is not null && p.Book.Volume is not null));
    }

    [Fact]
    public void Book_languages_and_directions_follow_k_51_osmanlica_and_arabic_are_rtl()
    {
        Assert.Equal(61, RisaleBookTable.Default.Count(b => b.Language == "tr"));
        Assert.Equal(12, RisaleBookTable.Default.Count(b => b.Language == "ota"));
        Assert.Equal(14, RisaleBookTable.Default.Count(b => b.Language == "ar"));
        Assert.All(RisaleBookTable.Default, b => Assert.Equal(b.Language == "tr" ? "ltr" : "rtl", b.Direction));
        Assert.Equal(("tr", "ltr"), (Book(BookSozler).Language, Book(BookSozler).Direction));
        Assert.Equal(("ota", "rtl"), (Book(BookOsmanlica).Language, Book(BookOsmanlica).Direction));
    }

    [Fact]
    public void Pack_ids_are_unique_within_the_length_rule_and_each_resolves_to_exactly_one_pack_type()
    {
        PackDefinitions definitions = PackTestData.Definitions();
        string[] ids = [.. Catalog.All.Select(p => p.PackId)];

        Assert.Equal(ids.Length, ids.Distinct(StringComparer.Ordinal).Count());
        foreach (PackDefinition pack in Catalog.All.Where(p => p.PackId.StartsWith("risale-", StringComparison.Ordinal)))
        {
            // Capa semasi 5: slug en cok 64 karakter; paket kimligi "risale-" ekiyle 71.
            Assert.True(pack.PackId.Length <= 64 + "risale-".Length, pack.PackId);
            string expectedType = pack.IndexesBooks ? "risale-dizin" : "risale-kitap";
            Assert.Equal(expectedType, definitions.Resolve(pack.PackId).Name);
        }

        Assert.Equal("risale-kitap", definitions.Resolve("risale-test-ornek").Name);
        Assert.Single(Catalog.All, p => p.IndexesBooks);
        Assert.Equal(PackCatalog.RisaleIndexPackId, Catalog.All.Single(p => p.IndexesBooks).PackId);
    }

    [Fact]
    public void Fixture_book_is_a_test_source_pack_that_cannot_be_a_real_book_slug()
    {
        PackDefinition fixture = Catalog.Get("risale-test-ornek");

        Assert.Equal("rn:test-ornek", fixture.AnchorPrefix);
        Assert.Equal([(PackCatalog.RisaleFixtureSourceSlug, PackSourceRole.Content, true)], fixture.Sources.Select(s => (s.Slug, s.Role, s.Required)));
        Assert.True(FlavorPolicy.IsTestSource(PackCatalog.RisaleFixtureSourceSlug));
        Assert.False(FlavorPolicy.IsEndToEndFixture(PackCatalog.RisaleFixtureSourceSlug));
        Assert.Null(fixture.Book!.Volume);
        Assert.DoesNotContain(RisaleBookTable.Default, b => b.Slug.StartsWith("test-", StringComparison.Ordinal));
    }

    [Fact]
    public void Index_pack_binds_text_fixture_link_and_page_sources_and_depends_on_nothing()
    {
        PackDefinition index = Catalog.Get("risale-dizin");

        Assert.Empty(index.DependsOn);
        Assert.Equal(
            [
                (PackCatalog.RisaleTextSlug, PackSourceRole.Content, true),
                (PackCatalog.RisaleFixtureSourceSlug, PackSourceRole.Content, false),
                (PackCatalog.RisaleLinkSlug, PackSourceRole.Attribution, false),
                (PackCatalog.RisaleLugatSlug, PackSourceRole.Glossary, false),
                (PackCatalog.RisalePageSlug, PackSourceRole.Structure, false),
            ],
            index.Sources.Select(s => (s.Slug, s.Role, s.Required)));
        Assert.Equal("rnk-baski", index.Sources.Single(s => s.Role == PackSourceRole.Structure).PageMapLayout);
        Assert.Equal("rnk-baski-test", index.Sources.Single(s => s.Slug == PackCatalog.RisaleFixtureSourceSlug).PageMapLayout);
        Assert.Null(index.AnchorPrefix);
    }

    [Fact]
    public void Book_table_rejects_reserved_duplicate_overlong_and_malformed_rows()
    {
        static byte[] Json(string slug, string dil = "tr", string yon = "ltr", int cilt = 1) =>
            System.Text.Encoding.UTF8.GetBytes(
                $"{{\"surum\":1,\"kitaplar\":[{{\"slug\":\"{slug}\",\"baslik\":\"Deneme\",\"dil\":\"{dil}\",\"yon\":\"{yon}\",\"rnk\":{{\"cilt\":{cilt.ToString(CultureInfo.InvariantCulture)}}}}}]}}");

        Assert.Single(RisaleBookTable.Parse(Json("deneme-kitap")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("dizin")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("test-ornek")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json(new string('a', 65))));
        Assert.Single(RisaleBookTable.Parse(Json(new string('a', 64))));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("Deneme")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("deneme_kitap")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("deneme", dil: "fr")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("deneme", yon: "ttb")));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("deneme", cilt: 0)));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(Json("deneme", cilt: 40000)));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse("{}"u8));
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse("["u8));

        byte[] twice = System.Text.Encoding.UTF8.GetBytes(
            "{\"kitaplar\":[{\"slug\":\"a\",\"baslik\":\"A\",\"dil\":\"tr\",\"yon\":\"ltr\",\"rnk\":{\"cilt\":1}},{\"slug\":\"a\",\"baslik\":\"B\",\"dil\":\"tr\",\"yon\":\"ltr\",\"rnk\":{\"cilt\":2}}]}");
        Assert.Throws<InvalidDataException>(() => RisaleBookTable.Parse(twice));
    }

    // ---------------------------------------------------------------- capa -> paket, dizin korkulugu

    [Theory]
    [InlineData("rn:sozler:soz-10:hakikat-3:p4", "risale-sozler")]
    [InlineData("rn:sozler-osmanlica:soz-1:p1", "risale-sozler-osmanlica")]
    [InlineData("rn:sozler:soz-1:p1:s2", "risale-sozler")]
    [InlineData("rn:sozler:soz-1:p1@3-9", "risale-sozler")]
    [InlineData("rn:test-ornek:bolum-1:p1", "risale-test-ornek")]
    public void Risale_anchors_map_to_their_book_pack_and_the_prefix_finds_the_definition(string anchor, string packId)
    {
        Assert.Equal(packId, PackCatalog.PackIdForAnchor(anchor));
        Assert.True(Catalog.TryGetByAnchorPrefix(GatePack.PrefixOf(anchor), out PackDefinition? pack));
        Assert.Equal(packId, pack.PackId);
    }

    [Fact]
    public void The_reserved_dizin_slug_never_maps_to_a_pack_and_is_never_a_book_prefix()
    {
        // rn:dizin:... risale-dizin paketiyle cakisirdi: capa kabul edilse bile paketlenemez.
        Assert.Null(PackCatalog.PackIdForAnchor("rn:dizin:soz-1:p1"));
        Assert.Null(PackCatalog.PackIdForAnchor(AnchorRef.Parse("rn:dizin:p1")));
        Assert.Null(Catalog.PackIdForXref("q:2:255", "rn:dizin:p1"));
        Assert.False(Catalog.TryGetByAnchorPrefix("rn:dizin", out _));
        Assert.False(Catalog.TryGetByAnchorPrefix("rn:yok", out _));
        Assert.Equal("risale-dizin", Catalog.PackIdForXref("q:2:255", "rn:sozler:soz-1:p1"));
    }

    [Fact]
    public void Prefix_of_cuts_the_first_two_segments_without_parsing()
    {
        Assert.Equal("rn:sozler", GatePack.PrefixOf("rn:sozler:soz-1:p1:s2"));
        Assert.Equal("rn:sozler", GatePack.PrefixOf("rn:sozler"));
        Assert.Equal("konu", GatePack.PrefixOf("konu"));
        Assert.Equal("q:2", GatePack.PrefixOf("q:2:255"));
    }

    // ---------------------------------------------------------------- etiket

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Label_is_built_from_title_header_path_and_paragraph_number_in_any_culture(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            RisaleBook book = Book(BookSozler);
            UnitRow unit = PackTestData.Unit(S1, PackCatalog.RisaleTextSlug, "risale") with
            {
                Attrs = "{\"baslik_yolu\":[\"Deneme bölümü 1\",\"Deneme alt bölüm 2\"],\"p\":4}",
            };

            Assert.Equal($"{book.Title} › Deneme bölümü 1 › Deneme alt bölüm 2 ¶4", RisaleLabels.Build(book, unit));

            // Paragraf numarasi attrs'ta yoksa capanin p{n} parcasindan, binlik ayraci olmadan.
            UnitRow big = PackTestData.Unit("rn:sozler:soz-1:p1234", PackCatalog.RisaleTextSlug, "risale") with { Attrs = "{\"baslik_yolu\":[]}" };
            Assert.Equal($"{book.Title} ¶1234", RisaleLabels.Build(book, big));
        });
    }

    [Fact]
    public void Label_handles_headings_footnotes_and_unreadable_attrs_without_using_the_slug()
    {
        RisaleBook book = Book(BookSozler);

        UnitRow heading = PackTestData.Unit(S1, PackCatalog.RisaleTextSlug, "risale") with
        {
            Role = "baslik",
            Attrs = "{\"baslik_yolu\":[\"Deneme bölümü 1\"],\"p\":1}",
        };
        Assert.Equal($"{book.Title} › Deneme bölümü 1", RisaleLabels.Build(book, heading));

        UnitRow footnote = PackTestData.Unit("rn:sozler:soz-1:hasiye-2:p1", PackCatalog.RisaleTextSlug, "risale") with
        {
            Role = "dipnot",
            Attrs = "{\"baslik_yolu\":[\"Deneme bölümü 1\"],\"p\":1,\"hasiye_no\":2}",
        };
        Assert.Equal($"{book.Title} › Deneme bölümü 1 › Haşiye 2 ¶1", RisaleLabels.Build(book, footnote));

        UnitRow broken = PackTestData.Unit(S2, PackCatalog.RisaleTextSlug, "risale") with { Attrs = "{bozuk" };
        Assert.Equal($"{book.Title} ¶2", RisaleLabels.Build(book, broken));

        UnitRow notObject = PackTestData.Unit(S2, PackCatalog.RisaleTextSlug, "risale") with { Attrs = "[1]" };
        Assert.Equal($"{book.Title} ¶2", RisaleLabels.Build(book, notObject));

        // Etiket capa metni ya da slug degildir.
        Assert.DoesNotContain("soz-1", RisaleLabels.Build(book, broken), StringComparison.Ordinal);
    }

    // ---------------------------------------------------------------- sentetik anlik goruntu

    private static SourceRow Src(string slug, string tur) => PackTestData.Source(slug, tur, atifMetni: "Sentetik atif (" + slug + ")", baslik: "Deneme " + slug);

    private static UnitRow RisaleUnit(
        string anchor,
        string source,
        long ord,
        string durum = "onayli",
        string? trWide = "deneme paragrafi",
        string? trStem = "deneme paragraf",
        string? arNorm = null,
        string role = "govde",
        string path = "Deneme bölümü 1") =>
        PackTestData.Unit(anchor, source, "risale", $"Deneme paragrafı {ord.ToString(CultureInfo.InvariantCulture)}", durum, ord, arNorm: arNorm, trWide: trWide, trStem: trStem) with
        {
            Role = role,
            Attrs = $"{{\"baslik_yolu\":[\"{path}\"],\"p\":{ord.ToString(CultureInfo.InvariantCulture)}}}",
        };

    /// <summary>
    /// PackTestData.Snapshot + Risale: sozler p1 (onayli) ve p2 (taslak), sozler-osmanlica p1 (onayli; kaynakta tr_wide dolu olsa da dizinde yalniz ar_norm),
    /// fikstur kitabi p1 (test-risale-ornek kaynagi), kaynaklar risale-rnk-metin, risale-baski-rnk, risale-atif-dizini, test-risale-ornek. Sayfalar: 5 (p1 - p1),
    /// 6 (p1 - p2 taslak), osmanlica 1 (p1 - p1), fikstur 1 (kendi kaynagi ve "rnk-baski-test" duzeni; cilt 1 Sozler cildiyle cakisir). Baglantilar: q:1:1 -> p1 (onayli atif), q:1:1 -> p2 (onayli atif; ucu taslak: K-47 sarkan uc).
    /// </summary>
    private static EditorialSnapshot Snapshot(int? sozlerVolume = null, bool draftOnly = false)
    {
        EditorialSnapshot basis = PackTestData.Snapshot();
        int sozler = sozlerVolume ?? Book(BookSozler).Volume!.Value;
        int osmanlica = Book(BookOsmanlica).Volume!.Value;
        string firstState = draftOnly ? "taslak" : "onayli";

        return new EditorialSnapshot
        {
            Sources =
            [
                .. basis.Sources,
                Src(PackCatalog.RisaleTextSlug, "risale"),
                Src(PackCatalog.RisalePageSlug, "baski"),
                Src(PackCatalog.RisaleLinkSlug, "baglanti_verisi"),
                Src(PackCatalog.RisaleFixtureSourceSlug, "kitap"),
            ],
            Units =
            [
                .. basis.Units,
                RisaleUnit(S1, PackCatalog.RisaleTextSlug, 1, firstState, arNorm: PackTestData.SyntheticArabic),
                RisaleUnit(S2, PackCatalog.RisaleTextSlug, 2, "taslak"),
                RisaleUnit(O1, PackCatalog.RisaleTextSlug, 1, firstState, trWide: "deneme", trStem: "deneme", arNorm: PackTestData.SyntheticArabic),
                RisaleUnit(T1, PackCatalog.RisaleFixtureSourceSlug, 1, "onayli", arNorm: PackTestData.SyntheticArabic),
            ],
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps =
            [
                .. basis.PageMaps,
                new PageMapRow(PackCatalog.RisalePageSlug, sozler, 5, null, S1, 0, S1, null),
                new PageMapRow(PackCatalog.RisalePageSlug, sozler, 6, null, S1, 3, S2, null),
                new PageMapRow(PackCatalog.RisalePageSlug, osmanlica, 1, null, O1, 0, O1, null),
                new PageMapRow(PackCatalog.RisaleFixtureSourceSlug, 1, 1, null, T1, 0, T1, null),
            ],
            Xrefs =
            [
                .. basis.Xrefs,
                PackTestData.Xref("q:1:1", S1, "atif", "onayli", id: XrefToApproved),
                PackTestData.Xref("q:1:1", S2, "atif", "onayli", id: XrefToDraft),
            ],
        };
    }

    private static PackContent Assemble(BuildFlavor flavor, EditorialSnapshot snapshot, string packId, out GateResult gate)
    {
        gate = PackTestData.Evaluate(flavor, snapshot, Catalog);
        return PackAssembler.Assemble(Catalog.Get(packId), flavor, snapshot, gate, Catalog);
    }

    private static PackContent Assemble(BuildFlavor flavor, EditorialSnapshot snapshot, string packId) => Assemble(flavor, snapshot, packId, out _);

    // ---------------------------------------------------------------- risale-{kitap}: yalniz unit

    [Fact]
    public void Book_pack_takes_only_its_own_prefixed_units_with_no_search_links_or_pages()
    {
        PackContent sozler = Assemble(BuildFlavor.Dev, Snapshot(), "risale-sozler");

        // Ayni kaynaktan (risale-rnk-metin) gelen sozler-osmanlica birimi sozler paketine girmez.
        Assert.Equal([S1, S2], sozler.Units.Select(u => u.Anchor).Order(StringComparer.Ordinal));
        Assert.Empty(sozler.UnitSearch);
        Assert.Empty(sozler.UnitRefs);
        Assert.Empty(sozler.Xrefs);
        Assert.Empty(sozler.PageMaps);
        Assert.Empty(sozler.TrRootIndex);
        Assert.Equal([PackCatalog.RisaleTextSlug], sozler.PackSources.Select(s => s.SourceId));
        Assert.Equal(("tr", "ltr"), (sozler.Language, sozler.Direction));

        PackContent osmanlica = Assemble(BuildFlavor.Dev, Snapshot(), "risale-sozler-osmanlica");
        Assert.Equal([O1], osmanlica.Units.Select(u => u.Anchor));
        Assert.Equal(("ota", "rtl"), (osmanlica.Language, osmanlica.Direction));
    }

    [Fact]
    public void Book_pack_units_carry_the_approval_flag_and_the_label_from_attrs()
    {
        PackContent sozler = Assemble(BuildFlavor.Dev, Snapshot(), "risale-sozler");
        string title = Book(BookSozler).Title;

        PackUnitRow first = sozler.Units.Single(u => u.Anchor == S1);
        PackUnitRow second = sozler.Units.Single(u => u.Anchor == S2);
        Assert.Equal((1L, $"{title} › Deneme bölümü 1 ¶1"), (first.Approved, first.Label));
        Assert.Equal((0L, $"{title} › Deneme bölümü 1 ¶2"), (second.Approved, second.Label));
        Assert.Equal("risale", first.Kind);
        Assert.Equal("govde", first.Role);
    }

    [Fact]
    public void A_book_without_units_is_not_a_candidate_in_any_flavor_icerik_yok()
    {
        EditorialSnapshot snapshot = Snapshot();

        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            GateResult gate = PackTestData.Evaluate(flavor, snapshot, Catalog);

            Assert.DoesNotContain("risale-mektubat", gate.IncludedPacks);
            Assert.Contains(
                gate.Report.Rows,
                r => r.Kind == GateSubjectKind.Paket && r.Id == "risale-mektubat" && r.Decision == GateDecision.Girmedi && r.Rule is null && r.Reason == GateReasons.IcerikYok);
            Assert.DoesNotContain(gate.Report.Violations, v => v.Subject == "risale-mektubat");
        }
    }

    // ---------------------------------------------------------------- gorunurluk (dev / internal / public)

    [Fact]
    public void Dev_takes_unapproved_units_with_the_flag_and_the_test_fixture_book()
    {
        EditorialSnapshot snapshot = Snapshot();
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Dev, snapshot, Catalog);

        Assert.Contains("risale-sozler", gate.IncludedPacks);
        Assert.Contains("risale-sozler-osmanlica", gate.IncludedPacks);
        Assert.Contains("risale-test-ornek", gate.IncludedPacks);
        Assert.Contains("risale-dizin", gate.IncludedPacks);

        PackContent sozler = PackAssembler.Assemble(Catalog.Get("risale-sozler"), BuildFlavor.Dev, snapshot, gate, Catalog);
        Assert.Equal([1L, 0L], sozler.Units.OrderBy(u => u.Ord).Select(u => u.Approved));

        PackContent fixture = PackAssembler.Assemble(Catalog.Get("risale-test-ornek"), BuildFlavor.Dev, snapshot, gate, Catalog);
        Assert.Equal([T1], fixture.Units.Select(u => u.Anchor));
        Assert.Equal([PackCatalog.RisaleFixtureSourceSlug], fixture.PackSources.Select(s => s.SourceId));
    }

    [Fact]
    public void Internal_takes_unapproved_units_but_not_the_test_risale_fixture()
    {
        EditorialSnapshot snapshot = Snapshot();
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Internal, snapshot, Catalog);

        // P-12: internal'a yalniz test-kucuk ve test-ses girer; test-risale-ornek girmez.
        Assert.DoesNotContain("risale-test-ornek", gate.IncludedPacks);
        Assert.DoesNotContain(PackCatalog.RisaleFixtureSourceSlug, gate.IncludedSources);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Paket && r.Id == "risale-test-ornek" && r.Rule == GateRule.P12);

        Assert.Contains("risale-sozler", gate.IncludedPacks);
        PackContent sozler = PackAssembler.Assemble(Catalog.Get("risale-sozler"), BuildFlavor.Internal, snapshot, gate, Catalog);
        Assert.Equal([1L, 0L], sozler.Units.OrderBy(u => u.Ord).Select(u => u.Approved));

        PackContent index = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Internal, snapshot, gate, Catalog);
        Assert.DoesNotContain(index.UnitRefs, r => r.PackId == "risale-test-ornek");
        Assert.DoesNotContain(index.PackSources, s => s.SourceId == PackCatalog.RisaleFixtureSourceSlug);
    }

    [Fact]
    public void Public_takes_only_approved_units_and_never_the_test_fixture()
    {
        EditorialSnapshot snapshot = Snapshot();
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot, Catalog);

        Assert.DoesNotContain("risale-test-ornek", gate.IncludedPacks);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Kaynak && r.Id == PackCatalog.RisaleFixtureSourceSlug && r.Rule == GateRule.P12);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Id == PackCatalog.RisaleTextSlug && r.Rule == GateRule.P10 && r.Reason == GateReasons.OnaysizBirim);

        PackContent sozler = PackAssembler.Assemble(Catalog.Get("risale-sozler"), BuildFlavor.Public, snapshot, gate, Catalog);
        Assert.Equal([S1], sozler.Units.Select(u => u.Anchor));
        Assert.All(sozler.Units, u => Assert.Equal(1L, u.Approved));

        PackContent index = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Public, snapshot, gate, Catalog);
        Assert.DoesNotContain(index.UnitRefs, r => r.Anchor == S2);
        Assert.DoesNotContain(index.UnitSearch, r => r.Anchor == S2);
    }

    [Fact]
    public void Public_with_only_unapproved_risale_units_leaves_every_risale_pack_icerik_yok_and_does_not_reject()
    {
        EditorialSnapshot snapshot = Snapshot(draftOnly: true);
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot, Catalog);

        foreach (string packId in new[] { "risale-sozler", "risale-sozler-osmanlica", "risale-dizin", "risale-test-ornek" })
        {
            Assert.DoesNotContain(packId, gate.IncludedPacks);
        }

        Assert.Contains(
            gate.Report.Rows,
            r => r.Kind == GateSubjectKind.Paket && r.Id == "risale-sozler" && r.Decision == GateDecision.Girmedi && r.Rule is null && r.Reason == GateReasons.IcerikYok);
        Assert.Contains(
            gate.Report.Rows,
            r => r.Kind == GateSubjectKind.Paket && r.Id == "risale-dizin" && r.Decision == GateDecision.Girmedi && r.Rule is null && r.Reason == GateReasons.IcerikYok);
        Assert.DoesNotContain(gate.Report.Violations, v => v.Subject.StartsWith("risale-", StringComparison.Ordinal));
    }

    [Fact]
    public void Book_approval_is_scoped_per_book_one_approved_book_does_not_pull_in_the_others()
    {
        // sozler-osmanlica onayli, sozler yalniz taslak: public'te yalniz osmanlica paketi (ve dizin) girer; ayni kaynaktan beslenen sozler girmez.
        EditorialSnapshot basis = Snapshot();
        EditorialSnapshot snapshot = new()
        {
            Sources = basis.Sources,
            Units = [.. basis.Units.Select(u => u.Anchor == S1 ? u with { MetinDurumu = "taslak" } : u)],
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = basis.Xrefs,
        };

        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot, Catalog);

        Assert.DoesNotContain("risale-sozler", gate.IncludedPacks);
        Assert.Contains("risale-sozler-osmanlica", gate.IncludedPacks);
        Assert.Contains("risale-dizin", gate.IncludedPacks);

        PackContent index = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Public, snapshot, gate, Catalog);
        Assert.Equal([O1], index.UnitRefs.Select(r => r.Anchor));
    }

    // ---------------------------------------------------------------- P-07: sarkan baglanti, page_map suzmesi

    [Fact]
    public void Links_to_a_filtered_risale_unit_do_not_enter_public_and_the_index_carries_only_the_included_ones()
    {
        EditorialSnapshot snapshot = Snapshot();

        GateResult dev = PackTestData.Evaluate(BuildFlavor.Dev, snapshot, Catalog);
        Assert.True(dev.XrefVerdicts[XrefToApproved].Included);
        Assert.True(dev.XrefVerdicts[XrefToDraft].Included);

        GateResult publicGate = PackTestData.Evaluate(BuildFlavor.Public, snapshot, Catalog);
        Assert.True(publicGate.XrefVerdicts[XrefToApproved].Included);
        XrefVerdict dangling = publicGate.XrefVerdicts[XrefToDraft];
        Assert.False(dangling.Included);
        Assert.Equal(GateRule.P07, dangling.Rule);
        Assert.Equal(GateReasons.UcBirimGirmedi, dangling.Reason);
        Assert.Contains(GateRule.P10.ToCode(), dangling.Detail, StringComparison.Ordinal);

        PackContent publicIndex = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Public, snapshot, publicGate, Catalog);
        Assert.Contains(publicIndex.Xrefs, x => x.DstAnchor == S1);
        Assert.DoesNotContain(publicIndex.Xrefs, x => x.DstAnchor == S2);

        PackContent devIndex = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Dev, snapshot, dev, Catalog);
        Assert.Contains(devIndex.Xrefs, x => x.DstAnchor == S2);
        Assert.Contains(PackCatalog.RisaleLinkSlug, devIndex.PackSources.Select(s => s.SourceId));
    }

    [Fact]
    public void Index_page_map_has_volume_equal_to_the_book_volume_and_only_pages_with_both_ends_in_scope()
    {
        EditorialSnapshot snapshot = Snapshot();

        PackContent dev = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");
        Assert.Equal(
            [("rnk-baski", 5L), ("rnk-baski", 6L), ("rnk-baski", 1L), ("rnk-baski-test", 1L)],
            dev.PageMaps.Select(p => (p.Layout, p.Page)));
        Assert.Equal(Book(BookSozler).Volume, dev.PageMaps.Single(p => p.Page == 5).Volume);
        Assert.Equal(Book(BookOsmanlica).Volume, dev.PageMaps.Single(p => p.StartAnchor == O1).Volume);
        Assert.Contains(PackCatalog.RisalePageSlug, dev.PackSources.Select(s => s.SourceId));

        // public: sayfa 6 taslak bir paragrafa uzandigi icin sarkan olurdu; yazilmaz. Fikstur sayfasi test- kaynagidir: public ve internal'a girmez.
        PackContent publicIndex = Assemble(BuildFlavor.Public, snapshot, "risale-dizin");
        Assert.Equal([5L, 1L], publicIndex.PageMaps.Select(p => p.Page));
        Assert.DoesNotContain(publicIndex.PageMaps, p => p.Layout == "rnk-baski-test");
        Assert.DoesNotContain(Assemble(BuildFlavor.Internal, snapshot, "risale-dizin").PageMaps, p => p.Layout == "rnk-baski-test");

        // Core'un Medine sayfa satiri risale-dizin'e sizmaz.
        Assert.DoesNotContain(dev.PageMaps, p => p.Layout == "medine-604");
    }

    [Fact]
    public void A_page_map_volume_that_differs_from_the_book_volume_is_an_assembly_error()
    {
        EditorialSnapshot snapshot = Snapshot(sozlerVolume: 999);

        Assert.Throws<PackAssemblyException>(() => Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"));
    }

    // ---------------------------------------------------------------- risale-dizin: unit_ref ve arama satirlari

    [Fact]
    public void Index_pack_carries_unit_refs_with_book_pack_ids_and_search_rows_by_language()
    {
        PackContent index = Assemble(BuildFlavor.Dev, Snapshot(), "risale-dizin");

        Assert.Empty(index.Units);
        Assert.Equal(new[] { S1, S2, O1, T1 }.Order(StringComparer.Ordinal), index.UnitRefs.Select(r => r.Anchor).Order(StringComparer.Ordinal));
        Assert.Equal("risale-sozler", index.UnitRefs.Single(r => r.Anchor == S1).PackId);
        Assert.Equal("risale-sozler-osmanlica", index.UnitRefs.Single(r => r.Anchor == O1).PackId);
        Assert.Equal("risale-test-ornek", index.UnitRefs.Single(r => r.Anchor == T1).PackId);
        Assert.Equal(2L, index.UnitRefs.Single(r => r.Anchor == S2).Ord);
        Assert.Equal(Book(BookSozler).Title + " › Deneme bölümü 1 ¶2", index.UnitRefs.Single(r => r.Anchor == S2).Label);

        // Turkce kitap: tr_wide, tr_stem ve ar_norm; Osmanlica kitap: yalniz ar_norm (kaynakta tr_wide dolu olsa da).
        PackUnitSearchRow turkish = index.UnitSearch.Single(r => r.Anchor == S1);
        Assert.Equal(("deneme paragrafi", "deneme paragraf", PackTestData.SyntheticArabic), (turkish.TrWide, turkish.TrStem, turkish.ArNorm));
        PackUnitSearchRow ottoman = index.UnitSearch.Single(r => r.Anchor == O1);
        Assert.Equal(((string?)null, (string?)null, PackTestData.SyntheticArabic), (ottoman.TrWide, ottoman.TrStem, ottoman.ArNorm));

        // Dizin metin tasimaz.
        Assert.Empty(index.TrRootIndex);
        Assert.Null(index.Language);
        Assert.Null(index.Direction);
    }

    [Fact]
    public void Row_stream_puts_unit_ref_between_unit_and_unit_search_and_the_digest_follows_labels()
    {
        EditorialSnapshot snapshot = Snapshot();
        PackContent index = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        string[] tables = [.. PackRows.Enumerate(index).Select(r => r.Table).Distinct(StringComparer.Ordinal)];
        Assert.Equal(["pack_source", "attribution", "unit_ref", "unit_search", "xref_idx", "page_map"], tables);
        Assert.Equal(4, PackRows.Count(index)[PackTables.UnitRef]);

        PackContent relabeled = new()
        {
            PackId = index.PackId,
            Flavor = index.Flavor,
            PackSources = index.PackSources,
            Attributions = index.Attributions,
            UnitRefs = [.. index.UnitRefs.Select(r => r with { Label = r.Label + "!" })],
            UnitSearch = index.UnitSearch,
            Xrefs = index.Xrefs,
            PageMaps = index.PageMaps,
        };
        Assert.NotEqual(PackDigest.Compute(index), PackDigest.Compute(relabeled));
    }

    // ---------------------------------------------------------------- yazici: SQLite dosyalari

    private static SqlitePackWriter Writer() => new(PackTestData.Definitions());

    private static async Task<PackFile> Write(PackContent content, EditorialSnapshot snapshot, string dir, CancellationToken ct) =>
        await Writer().WriteAsync(content, new PackWriteRequest(dir, "2026.11.0", "2026.11.13-abcdef0", snapshot.Sources), ct);

    private static SqliteConnection Open(string path, bool readOnly = true)
    {
        SqliteConnectionStringBuilder builder = new() { DataSource = path, Pooling = false, Mode = readOnly ? SqliteOpenMode.ReadOnly : SqliteOpenMode.ReadWrite };
        SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        return connection;
    }

    private static List<string> Strings(SqliteConnection connection, string sql, params (string Name, object Value)[] parameters)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        foreach ((string name, object value) in parameters)
        {
            command.Parameters.AddWithValue(name, value);
        }

        using SqliteDataReader reader = command.ExecuteReader();
        List<string> values = [];
        while (reader.Read())
        {
            values.Add(Convert.ToString(reader.GetValue(0), CultureInfo.InvariantCulture)!);
        }

        return values;
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Book_pack_file_has_only_unit_meta_with_language_and_direction_and_no_search_tables(bool turkish)
    {
        async Task Body()
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            using PackTestData.TempDir temp = new();
            EditorialSnapshot snapshot = Snapshot();

            PackFile file = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-sozler-osmanlica"), snapshot, temp.Path, ct);

            Assert.True(file.SelfCheck.Passed, file.SelfCheck.ToJson());
            using SqliteConnection connection = Open(file.Path);
            Assert.Equal(["attribution", "pack_meta", "pack_source", "unit"], Strings(connection, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"));
            Assert.Equal(["ota"], Strings(connection, "SELECT value FROM pack_meta WHERE key = 'dil'"));
            Assert.Equal(["rtl"], Strings(connection, "SELECT value FROM pack_meta WHERE key = 'yon'"));
            Assert.Equal(["1"], Strings(connection, "SELECT value FROM pack_meta WHERE key = 'unit_count'"));
            Assert.Equal([O1], Strings(connection, "SELECT anchor FROM unit"));
            Assert.Empty(Strings(connection, "SELECT name FROM sqlite_master WHERE name LIKE 'unit_search%' OR name LIKE 'unit_fts%' OR name LIKE 'unit_tri%' OR name IN ('xref_idx', 'tr_root_index', 'page_map')"));
        }

        if (turkish)
        {
            await AsyncCultureScope.TurkishAsync(Body);
        }
        else
        {
            await Body();
        }
    }

    [Fact]
    public async Task Other_packs_have_no_language_or_direction_meta()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();

        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);

        using SqliteConnection connection = Open(file.Path);
        Assert.Empty(Strings(connection, "SELECT key FROM pack_meta WHERE key IN ('dil', 'yon')"));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Index_file_chain_fts_match_to_unit_ref_to_the_book_unit_through_attach_within_the_attach_budget(bool turkish)
    {
        async Task Body()
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            using PackTestData.TempDir temp = new();
            EditorialSnapshot snapshot = Snapshot();

            PackFile index = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"), snapshot, temp.Path, ct);
            PackFile sozler = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-sozler"), snapshot, temp.Path, ct);
            PackFile osmanlica = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-sozler-osmanlica"), snapshot, temp.Path, ct);
            PackFile fixture = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-test-ornek"), snapshot, temp.Path, ct);
            Assert.True(index.SelfCheck.Passed, index.SelfCheck.ToJson());
            Assert.Equal(10, index.SelfCheck.Items.Count);
            Assert.Contains(index.SelfCheck.Items, i => i.Name == "lugat" && i.Passed);
            Assert.Contains(index.SelfCheck.Items, i => i.Name == "fts_query" && i.Passed && !i.Detail.StartsWith("atlandi", StringComparison.Ordinal));

            // Dizin dosyasi: tablo kumesi ve icerigi olmayan FTS tablolari.
            using (SqliteConnection inspect = Open(index.Path))
            {
                Assert.Equal(
                    ["attribution", "lugat", "pack_meta", "pack_source", "page_map", "tr_root_index", "unit_fts", "unit_ref", "unit_tri", "xref_idx"],
                    PackDefinitions.UserTables(inspect));
                Assert.Equal(["4"], Strings(inspect, "SELECT value FROM pack_meta WHERE key = 'unit_count'"));
                Assert.Empty(Strings(inspect, "SELECT key FROM pack_meta WHERE key IN ('dil', 'yon')"));
            }

            // Ana veritabani unit_fts de tasir (core gibi); dizin ve kitaplar ATTACH edilir: en kotu durum 8 bagli sema (Icerik paketleri 2).
            string main = Path.Combine(temp.Path, "main.db");
            PackFile small = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);
            File.Copy(small.Path, main);
            string[] standIns = ["p_kelime_kok", "p_tefsir_elmalili", "p_hadis_tecrid", "p_hadis_kutub_i_sitte"];
            Dictionary<string, string> attach = new(StringComparer.Ordinal)
            {
                ["p_risale_dizin"] = index.Path,
                ["p_risale_sozler"] = sozler.Path,
                ["p_risale_sozler_osmanlica"] = osmanlica.Path,
                ["p_risale_test_ornek"] = fixture.Path,
            };
            foreach (string name in standIns)
            {
                string copy = Path.Combine(temp.Path, name + ".db");
                File.Copy(small.Path, copy);
                attach[name] = copy;
            }

            using SqliteConnection connection = Open(main, readOnly: false);
            foreach ((string schema, string path) in attach)
            {
                using SqliteCommand command = connection.CreateCommand();
                command.CommandText = "ATTACH DATABASE $path AS " + schema;
                command.Parameters.AddWithValue("$path", path);
                command.ExecuteNonQuery();
            }

            List<string> schemas = Strings(connection, "SELECT name FROM pragma_database_list WHERE name <> 'main'");
            Assert.Equal(8, schemas.Count);
            Assert.True(schemas.Count <= 8, "ATTACH butcesi (MAX_ATTACHED = 8) asildi.");

            // Turkce kitap: tr_wide sutununda arama -> unit_ref -> kitap paketindeki birim.
            const string chain = "SELECT r.anchor || '|' || r.pack_id FROM p_risale_dizin.unit_ref r WHERE r.rowid IN (SELECT rowid FROM p_risale_dizin.unit_fts WHERE unit_fts MATCH $q) ORDER BY r.rowid";
            Assert.Equal(
                new[] { $"{S1}|risale-sozler", $"{S2}|risale-sozler", $"{T1}|risale-test-ornek" }.Order(StringComparer.Ordinal),
                Strings(connection, chain, ("$q", "tr_wide : \"deneme\"")).Order(StringComparer.Ordinal));

            // Osmanlica kitapta tr_wide NULL: kaynakta "deneme" olsa da dizinde bulunmaz; ar_norm ile bulunur.
            Assert.DoesNotContain(O1 + "|risale-sozler-osmanlica", Strings(connection, chain, ("$q", "tr_wide : \"deneme\"")));
            Assert.Contains(O1 + "|risale-sozler-osmanlica", Strings(connection, chain, ("$q", "ar_norm : \"" + PackTestData.SyntheticArabic + "\"")));

            // Trigram (ar_norm alt dizesi) de ayni rowid'e gider.
            Assert.Contains(O1 + "|risale-sozler-osmanlica", Strings(connection, "SELECT r.anchor || '|' || r.pack_id FROM p_risale_dizin.unit_ref r WHERE r.rowid IN (SELECT rowid FROM p_risale_dizin.unit_tri WHERE unit_tri MATCH $q)", ("$q", "\"ثجح\"")));

            // Zincirin sonu: unit_ref.pack_id kitap paketini, anchor o paketteki birimi gosterir; rowid'ler iki paketin arasinda esit varsayilmaz.
            string bookSchema = "p_" + Strings(connection, "SELECT pack_id FROM p_risale_dizin.unit_ref WHERE anchor = $a", ("$a", S1)).Single().Replace('-', '_');
            Assert.Equal("p_risale_sozler", bookSchema);
            Assert.Equal(["Deneme paragrafı 1"], Strings(connection, "SELECT text FROM p_risale_sozler.unit WHERE anchor = $a", ("$a", S1)));
            Assert.Equal(["Deneme paragrafı 1"], Strings(connection, "SELECT text FROM p_risale_sozler_osmanlica.unit WHERE anchor = $a", ("$a", O1)));

            // Kalici basvuru capadir: dizinin rowid'i (capa bayt sirasinda 1..4: O1, S1, S2, T1) kitap paketindeki rowid ile ayni olmak zorunda degildir (S2: dizinde 3, kitapta 2).
            Assert.Equal(["3"], Strings(connection, "SELECT rowid FROM p_risale_dizin.unit_ref WHERE anchor = $a", ("$a", S2)));
            Assert.Equal(["2"], Strings(connection, "SELECT rowid FROM p_risale_sozler.unit WHERE anchor = $a", ("$a", S2)));
        }

        if (turkish)
        {
            await AsyncCultureScope.TurkishAsync(Body);
        }
        else
        {
            await Body();
        }
    }

    [Fact]
    public async Task Index_xref_and_page_rows_are_written_and_attribution_lists_the_registered_sources()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = Snapshot();

        PackFile index = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"), snapshot, temp.Path, ct);

        Assert.True(index.SelfCheck.Passed, index.SelfCheck.ToJson());
        using SqliteConnection connection = Open(index.Path);
        Assert.Equal(["2"], Strings(connection, "SELECT count(*) FROM xref_idx WHERE dst_anchor IN ('" + S1 + "', '" + S2 + "')"));
        Assert.Equal(["3"], Strings(connection, "SELECT count(*) FROM page_map WHERE layout = 'rnk-baski'"));
        Assert.Equal(["1"], Strings(connection, "SELECT count(*) FROM page_map WHERE layout = 'rnk-baski-test'"));
        Assert.Equal(
            [PackCatalog.RisaleLinkSlug, PackCatalog.RisalePageSlug, PackCatalog.RisaleTextSlug, PackCatalog.RisaleFixtureSourceSlug],
            Strings(connection, "SELECT source_id FROM pack_source ORDER BY source_id"));
        Assert.Equal(Strings(connection, "SELECT source_id FROM pack_source ORDER BY source_id"), Strings(connection, "SELECT source_id FROM attribution ORDER BY source_id"));
    }

    [Fact]
    public async Task Self_check_fails_when_unit_ref_and_the_contentless_fts_rows_disagree()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = Snapshot();
        PackFile index = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"), snapshot, temp.Path, ct);

        using (SqliteConnection connection = Open(index.Path, readOnly: false))
        {
            using SqliteCommand delete = connection.CreateCommand();
            delete.CommandText = "DELETE FROM unit_ref WHERE anchor = $a";
            delete.Parameters.AddWithValue("$a", S2);
            Assert.Equal(1, delete.ExecuteNonQuery());
        }

        PackType type = PackTestData.Definitions().Resolve("risale-dizin");
        PackSelfCheckReport report = PackSelfCheck.RunOnFile(
            index.Path,
            new PackSelfCheckExpectations("risale-dizin", "2026.11.0", PackTestData.Definitions().ExpectedTables(type), new Dictionary<string, string>(), []));

        Assert.False(report.Items.Single(i => i.Name == "fts_query").Passed);
        Assert.False(report.Items.Single(i => i.Name == "unit_count").Passed);
    }

    [Fact]
    public async Task Empty_index_pack_passes_the_self_check_with_skipped_fts_item()
    {
        // Public'te hicbir birim yoksa dizin kapidan girmez; yine de bos dizin icerigi yazilabilir ve oz denetim kirmizi olmaz (satirsiz FTS atlanir).
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = Snapshot();
        PackContent empty = new() { PackId = "risale-dizin", Flavor = BuildFlavor.Dev };

        PackFile file = await Write(empty, snapshot, temp.Path, ct);

        Assert.True(file.SelfCheck.Passed, file.SelfCheck.ToJson());
        Assert.Contains(file.SelfCheck.Items, i => i.Name == "fts_query" && i.Detail.StartsWith("atlandi", StringComparison.Ordinal));
    }

    // ---------------------------------------------------------------- yeni tablo adlari ve DDL

    [Fact]
    public void Risale_pack_types_in_paketler_json_match_the_written_table_sets()
    {
        PackDefinitions definitions = PackTestData.Definitions();

        Assert.Equal(["attribution", "pack_meta", "pack_source", "unit"], definitions.ExpectedTables(definitions.Resolve("risale-sozler")));
        Assert.Equal(
            ["attribution", "lugat", "pack_meta", "pack_source", "page_map", "tr_root_index", "unit_fts", "unit_ref", "unit_tri", "xref_idx"],
            definitions.ExpectedTables(definitions.Resolve("risale-dizin")));
        Assert.Equal(["anchor", "pack_id", "ord", "label"], PackTables.Columns("unit_ref"));
    }
}
