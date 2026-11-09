using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>PackAssembler: kapi sonucuna gore paket satirlari (xref yerlesimi, etiket, bos sure, atif, onay). Docker gerektirmez.</summary>
public class PackAssemblerTests
{
    private static PackContent Assemble(string packId, BuildFlavor flavor, EditorialSnapshot? snapshot = null)
    {
        EditorialSnapshot data = snapshot ?? PackTestData.Snapshot();
        GateResult gate = PackTestData.Evaluate(flavor, data);
        return PackAssembler.Assemble(PackCatalog.Default.Get(packId), flavor, data, gate, PackCatalog.Default);
    }

    [Fact]
    public void Core_in_dev_takes_every_included_unit_with_labels_ranges_and_approval()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);

        Assert.Equal("core", core.PackId);
        Assert.Equal(BuildFlavor.Dev, core.Flavor);
        Assert.Equal(["q:1:1", "q:1:2", "q:1:3"], core.Units.Select(u => u.Anchor).Order(StringComparer.Ordinal));
        PackUnitRow first = core.Units.Single(u => u.Anchor == "q:1:1");
        Assert.Equal("1:1", first.Label);
        Assert.Equal("ayet", first.Kind);
        Assert.Equal("Deneme paragrafi 1", first.Text);
        // Editoryal int4range [1,2) -> pakette kapali aralik [1,1].
        Assert.Equal((1L, 1L), (first.AyahFirst, first.AyahLast));
        Assert.Equal(1, first.Approved);
        Assert.Equal(0, core.Units.Single(u => u.Anchor == "q:1:3").Approved);
        Assert.Equal("[]", first.Marks);
        Assert.Equal("{}", first.Attrs);
        Assert.Equal("etkin", first.Status);
    }

    [Fact]
    public void A_wider_editorial_range_becomes_a_closed_range_with_hi_minus_one()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        UnitRow wide = PackTestData.Unit("q:1:1", "tanzil-uthmani", "ayet", ayahLo: 7, ayahHi: 10);
        EditorialSnapshot changed = Replace(snapshot, units: [wide, .. snapshot.Units.Skip(1)]);

        PackContent core = Assemble("core", BuildFlavor.Dev, changed);

        PackUnitRow row = core.Units.Single(u => u.Anchor == "q:1:1");
        Assert.Equal((7L, 9L), (row.AyahFirst, row.AyahLast));
    }

    [Fact]
    public void A_unit_without_an_ayah_range_has_null_bounds()
    {
        PackContent kucuk = Assemble("test-kucuk", BuildFlavor.Dev);

        PackUnitRow row = Assert.Single(kucuk.Units);
        Assert.Null(row.AyahFirst);
        Assert.Null(row.AyahLast);
        // Ayet olmayan birimin etiketi capa metnidir (sure adlari onaylanana kadar).
        Assert.Equal("k:test-kucuk:bolum-1:p1", row.Label);
    }

    [Fact]
    public void Core_in_public_drops_the_unapproved_unit_and_its_words()
    {
        PackContent core = Assemble("core", BuildFlavor.Public);

        Assert.Equal(["q:1:1", "q:1:2"], core.Units.Select(u => u.Anchor).Order(StringComparer.Ordinal));
        Assert.All(core.Units, u => Assert.Equal(1, u.Approved));
        Assert.Equal(["q:1:1:1", "q:1:2:1"], core.QuranWords.Select(w => w.Anchor).Order(StringComparer.Ordinal));
        Assert.Equal(core.Units.Count, core.UnitSearch.Count);
    }

    [Fact]
    public void Unit_search_rows_carry_the_editorial_keys_by_anchor()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);

        PackUnitSearchRow row = core.UnitSearch.Single(r => r.Anchor == "q:1:1");
        Assert.Equal("deneme paragrafi 1", row.TrWide);
        Assert.Null(row.TrStem);
        Assert.Equal(PackTestData.SyntheticArabic, row.ArNorm);
    }

    [Fact]
    public void Core_carries_words_markers_and_the_medine_604_page_map_but_an_empty_sure_table()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);

        Assert.Equal(3, core.QuranWords.Count);
        Assert.Equal(2, core.QuranMarkers.Count);
        PackPageMapRow page = Assert.Single(core.PageMaps);
        Assert.Equal("medine-604", page.Layout);
        Assert.Equal(("q:1:1", "q:1:3"), (page.StartAnchor, page.EndAnchor));
        Assert.Empty(core.Sures);
        Assert.Empty(core.TrRootIndex);
        Assert.Equal(("cuz", 1L, "q:1:1", (string?)null), (core.QuranMarkers[0].Kind, core.QuranMarkers[0].No, core.QuranMarkers[0].Anchor, core.QuranMarkers[0].SecdeTuru));
    }

    [Fact]
    public void Core_lists_the_simple_clean_source_for_pack_source_and_attribution_only()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);

        Assert.Equal(
            ["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"],
            core.PackSources.Select(s => s.SourceId).Order(StringComparer.Ordinal));
        Assert.Equal(
            ["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"],
            core.Attributions.Select(s => s.SourceId).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(core.Units, u => u.Anchor.Contains("simple", StringComparison.Ordinal));
    }

    [Fact]
    public void Attribution_maps_source_fields_and_keeps_the_notice_verbatim()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);

        PackAttributionRow uthmani = core.Attributions.Single(a => a.SourceId == "tanzil-uthmani");
        Assert.Equal("Uthmani deneme", uthmani.Title);
        Assert.Equal("1", uthmani.Version);
        Assert.Equal("Atif 1", uthmani.RequiredCredit);
        Assert.Null(uthmani.SourceUrl);
        Assert.Equal(PackTestData.TanzilNotice, uthmani.NoticeText);

        // atif_url ?? kaynak_url
        Assert.Equal("https://example.invalid/atif", core.Attributions.Single(a => a.SourceId == "tanzil-simple-clean").SourceUrl);
        Assert.Equal("https://example.invalid/ust-veri", core.Attributions.Single(a => a.SourceId == "tanzil-ust-veri").SourceUrl);
    }

    [Fact]
    public void Xrefs_are_placed_by_the_packaging_rules_with_verdict_flags()
    {
        PackContent core = Assemble("core", BuildFlavor.Dev);
        PackContent tefsir = Assemble("tefsir-test-ornek", BuildFlavor.Dev);
        PackContent kucuk = Assemble("test-kucuk", BuildFlavor.Dev);

        // iki uc core -> core
        PackXrefRow inCore = Assert.Single(core.Xrefs);
        Assert.Equal(PackTestData.XrefCore.ToString("D"), inCore.Id);
        Assert.Equal((1L, 0L), (inCore.Approved, inCore.Folded));
        Assert.Equal("benzer_ayet", inCore.Type);
        // real degerler kisa onlu gosterimle (0,7f -> 0,7)
        Assert.Equal(0.7, inCore.Score);
        Assert.Equal(0.9, inCore.Confidence);
        // bir uc core, digeri P -> P
        PackXrefRow toTefsir = Assert.Single(tefsir.Xrefs);
        Assert.Equal(PackTestData.XrefToTefsir.ToString("D"), toTefsir.Id);
        Assert.Equal(0, toTefsir.Approved);
        Assert.Equal("{}", toTefsir.Evidence);
        Assert.Equal("test", toTefsir.DataVersion);
        PackXrefRow fromKucuk = Assert.Single(kucuk.Xrefs);
        Assert.Equal(PackTestData.XrefFromKucuk.ToString("D"), fromKucuk.Id);
        // red hicbir pakete girmez
        Assert.DoesNotContain(core.Xrefs.Concat(tefsir.Xrefs).Concat(kucuk.Xrefs), x => x.Id == PackTestData.XrefRed.ToString("D"));
    }

    [Fact]
    public void Xref_spans_are_written_as_the_editorial_half_open_bounds()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        XrefRow spanned = snapshot.Xrefs[0] with { SrcLo = 3, SrcHi = 8, DstLo = 0, DstHi = 5 };
        EditorialSnapshot changed = Replace(snapshot, xrefs: [spanned, .. snapshot.Xrefs.Skip(1)]);

        PackXrefRow row = Assert.Single(Assemble("core", BuildFlavor.Dev, changed).Xrefs);

        Assert.Equal((3L, 8L, 0L, 5L), (row.SrcStart, row.SrcEnd, row.DstStart, row.DstEnd));
    }

    [Fact]
    public void A_low_confidence_unapproved_automatic_xref_is_folded()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        XrefRow low = PackTestData.Xref("q:1:1", "q:1:2", "benzer_ayet", "aday", confidence: 0.6f, id: PackTestData.XrefCore);
        EditorialSnapshot changed = Replace(snapshot, xrefs: [low]);

        PackXrefRow row = Assert.Single(Assemble("core", BuildFlavor.Dev, changed).Xrefs);

        Assert.Equal((0L, 1L), (row.Approved, row.Folded));
        Assert.Equal(0.6, row.Confidence);
    }

    [Fact]
    public void Candidate_links_of_human_approval_types_do_not_enter_public()
    {
        // test-kucuk ve test-tefsir-ornek public'e girmez (P-12); core'daki iki uclu onayli baglanti girer.
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot);

        PackContent core = PackAssembler.Assemble(PackCatalog.Default.Get("core"), BuildFlavor.Public, snapshot, gate, PackCatalog.Default);

        Assert.Equal([PackTestData.XrefCore.ToString("D")], core.Xrefs.Select(x => x.Id));
    }

    [Fact]
    public void A_pack_that_did_not_pass_the_gate_cannot_be_assembled()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot);

        PackAssemblyException ex = Assert.Throws<PackAssemblyException>(() =>
            PackAssembler.Assemble(PackCatalog.Default.Get("test-kucuk"), BuildFlavor.Public, snapshot, gate, PackCatalog.Default));

        Assert.Contains("test-kucuk", ex.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Assembly_is_culture_independent(bool turkish)
    {
        string baseline = PackDigest.Compute(Assemble("core", BuildFlavor.Dev));
        string measured = string.Empty;

        CultureScope.For(turkish, () => measured = PackDigest.Compute(Assemble("core", BuildFlavor.Dev)));

        Assert.Equal(baseline, measured);
    }

    [Fact]
    public void Assembled_content_digest_is_stable_for_a_reordered_snapshot()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot reordered = Replace(
            snapshot,
            units: [.. snapshot.Units.Reverse()],
            words: [.. snapshot.QuranWords.Reverse()],
            xrefs: [.. snapshot.Xrefs.Reverse()]);

        Assert.Equal(
            PackDigest.Compute(Assemble("core", BuildFlavor.Dev, snapshot)),
            PackDigest.Compute(Assemble("core", BuildFlavor.Dev, reordered)));
    }

    [Fact]
    public void LabelOf_uses_sure_ayet_only_for_ayah_units()
    {
        Assert.Equal("2:255", PackAssembler.LabelOf("ayet", "q:2:255"));
        Assert.Equal("meal:elmalili:2:255", PackAssembler.LabelOf("meal", "meal:elmalili:2:255"));
        Assert.Equal("q:2:255:3", PackAssembler.LabelOf("ayet", "q:2:255:3"));
        Assert.Equal("gecersiz", PackAssembler.LabelOf("ayet", "gecersiz"));
    }

    private static EditorialSnapshot Replace(
        EditorialSnapshot source,
        IReadOnlyList<UnitRow>? units = null,
        IReadOnlyList<QuranWordRow>? words = null,
        IReadOnlyList<XrefRow>? xrefs = null) => new()
        {
            Sources = source.Sources,
            Units = units ?? source.Units,
            QuranWords = words ?? source.QuranWords,
            QuranMarkers = source.QuranMarkers,
            PageMaps = source.PageMaps,
            Xrefs = xrefs ?? source.Xrefs,
            OpenReviewXrefIds = source.OpenReviewXrefIds,
            Lexicals = source.Lexicals,
            PreviousRelease = source.PreviousRelease,
        };
}
