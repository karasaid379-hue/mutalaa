using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>GateInputBuilder: anlik goruntuden Domain kapi girdisine esleme (kurallar Domain'de; burada yalniz girdi). Docker gerektirmez.</summary>
public class GateInputBuilderTests
{
    private static GateInput Build(EditorialSnapshot? snapshot = null, Func<string, bool>? fileExists = null, IReadOnlyCollection<string>? carried = null, IReadOnlyCollection<string>? previous = null) =>
        GateInputBuilder.Build(snapshot ?? PackTestData.Snapshot(), PackCatalog.Default, "pipeline/sources", carried, previous, fileExists ?? PackTestData.AllRegistered());

    private static EditorialSnapshot With(
        EditorialSnapshot source,
        IReadOnlyList<SourceRow>? sources = null,
        IReadOnlyList<UnitRow>? units = null,
        IReadOnlyList<XrefRow>? xrefs = null,
        IReadOnlySet<Guid>? reviews = null,
        IReadOnlyList<LexicalRow>? lexicals = null) => new()
        {
            Sources = sources ?? source.Sources,
            Units = units ?? source.Units,
            QuranWords = source.QuranWords,
            QuranMarkers = source.QuranMarkers,
            PageMaps = source.PageMaps,
            Xrefs = xrefs ?? source.Xrefs,
            OpenReviewXrefIds = reviews ?? source.OpenReviewXrefIds,
            Lexicals = lexicals ?? source.Lexicals,
            PreviousRelease = source.PreviousRelease,
        };

    [Fact]
    public void Every_catalog_pack_is_a_gate_pack_and_only_packs_with_data_have_content()
    {
        GateInput input = Build();

        Assert.Equal(PackCatalog.Default.All.Select(p => p.PackId), input.Packs.Select(p => p.PackId));
        Assert.Equal(
            ["core", "tefsir-test-ornek", "test-kucuk"],
            input.Packs.Where(p => p.HasContent).Select(p => p.PackId).Order(StringComparer.Ordinal));
        GatePack core = input.Packs.Single(p => p.PackId == "core");
        Assert.Equal(["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"], core.SourceSlugs.Order(StringComparer.Ordinal));
        Assert.Empty(core.DependsOn);
        Assert.Equal(["core"], input.Packs.Single(p => p.PackId == "tefsir-test-ornek").DependsOn);
        GatePack empty = input.Packs.Single(p => p.PackId == "hadis-tecrid");
        Assert.False(empty.HasContent);
        Assert.Empty(empty.SourceSlugs);
    }

    [Fact]
    public void A_pack_without_data_is_reported_as_icerik_yok_without_a_rule_code_and_does_not_reject()
    {
        GateResult result = PackTestData.Evaluate(BuildFlavor.Dev, PackTestData.Snapshot());

        Assert.False(result.Rejected);
        GateReportRow row = result.Report.Rows.Single(r => r.Kind == GateSubjectKind.Paket && r.Id == "hadis-tecrid");
        Assert.Equal(GateDecision.Girmedi, row.Decision);
        Assert.Null(row.Rule);
        Assert.Equal(GateReasons.IcerikYok, row.Reason);
        Assert.DoesNotContain(result.IncludedPacks, p => p.StartsWith("hadis-", StringComparison.Ordinal));
    }

    [Fact]
    public void Only_a_pack_that_carries_the_quran_structure_and_has_structure_rows_is_marked_as_structure()
    {
        GateInput input = Build();
        EditorialSnapshot noStructure = new() { Sources = PackTestData.Snapshot().Sources, Units = PackTestData.Snapshot().Units };

        Assert.Equal(["core"], input.Packs.Where(p => p.HasStructure).Select(p => p.PackId));
        Assert.DoesNotContain(Build(noStructure).Packs, p => p.HasStructure);
    }

    [Fact]
    public void Core_stays_in_public_through_its_structure_rows_while_a_text_pack_with_only_draft_units_does_not_enter()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot allDrafts = With(snapshot, units: [.. snapshot.Units.Select(u => u with { MetinDurumu = "taslak" })]);

        GateResult result = PackTestData.Evaluate(BuildFlavor.Public, allDrafts);

        Assert.False(result.Rejected, result.Report.ToJson());
        Assert.Contains("core", result.IncludedPacks);
        Assert.Empty(result.IncludedUnits);
        // test- onekli kaynaklar public'e girmez (P-12); tefsir-test-ornek paketi bu yuzden kapida kalir, icerik-yok degil kaynak nedeniyle.
        Assert.DoesNotContain("test-kucuk", result.IncludedPacks);
    }

    [Fact]
    public void Core_with_data_enters_the_gate_with_its_fixtures_in_dev()
    {
        GateResult result = PackTestData.Evaluate(BuildFlavor.Dev, PackTestData.Snapshot());

        Assert.False(result.Rejected, result.Report.ToJson());
        Assert.Equal(["core", "tefsir-test-ornek", "test-kucuk"], result.IncludedPacks.Order(StringComparer.Ordinal));
        Assert.Contains("q:1:3", result.IncludedUnits);
    }

    [Fact]
    public void A_source_without_its_toml_file_is_unregistered_and_the_gate_rejects_its_pack_with_p01()
    {
        GateResult result = PackTestData.Evaluate(BuildFlavor.Dev, PackTestData.Snapshot(), fileExists: path => !path.EndsWith("tanzil-ust-veri.toml", StringComparison.Ordinal));

        Assert.True(result.Rejected);
        GateViolation violation = Assert.Single(result.Report.Violations, v => v.Rule == GateRule.P01 && v.Subject == "tanzil-ust-veri");
        Assert.Equal(GateReasons.KaynakKaydiYok, violation.Reason);
    }

    [Fact]
    public void A_blank_atif_text_is_reported_as_atif_metni_bos()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        SourceRow blank = snapshot.Sources.Single(s => s.Slug == "test-kucuk") with { AtifMetni = "  " };
        EditorialSnapshot changed = With(snapshot, sources: [.. snapshot.Sources.Where(s => s.Slug != "test-kucuk"), blank]);

        GateResult result = PackTestData.Evaluate(BuildFlavor.Dev, changed);

        Assert.True(result.Rejected);
        Assert.Contains(result.Report.Violations, v => v.Rule == GateRule.P01 && v.Subject == "test-kucuk" && v.Reason == GateReasons.AtifMetniBos);
    }

    [Fact]
    public void A_required_core_source_without_a_source_row_is_unregistered()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot changed = With(snapshot, sources: [.. snapshot.Sources.Where(s => s.Slug != "tanzil-simple-clean")]);

        GateResult result = PackTestData.Evaluate(BuildFlavor.Dev, changed);

        Assert.True(result.Rejected);
        Assert.Contains(result.Report.Violations, v => v.Rule == GateRule.P01 && v.Subject == "tanzil-simple-clean" && v.Reason == GateReasons.KaynakKaydiYok);
    }

    [Fact]
    public void A_missing_optional_source_does_not_block_a_pack()
    {
        // hadis-tecrid: tecrid-ar zorunlu, tecrid-naim istege bagli. Yalniz tecrid-ar var: pakete bagli kaynak yalniz o.
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot changed = With(
            snapshot,
            sources: [.. snapshot.Sources, PackTestData.Source("tecrid-ar", "hadis")],
            units: [.. snapshot.Units, PackTestData.Unit("h:tecrid:1", "tecrid-ar", "hadis")]);

        GateInput input = Build(changed);
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        GatePack pack = input.Packs.Single(p => p.PackId == "hadis-tecrid");
        Assert.True(pack.HasContent);
        Assert.Equal(["tecrid-ar"], pack.SourceSlugs);
        Assert.False(result.Rejected, result.Report.ToJson());
        Assert.Contains("hadis-tecrid", result.IncludedPacks);
    }

    [Fact]
    public void Unit_flags_map_status_ai_draft_and_successors()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        UnitRow draft = PackTestData.Unit("k:test-kucuk:bolum-1:p2", "test-kucuk", durum: "taslak", aiDraft: true);
        UnitRow retired = PackTestData.Unit("k:test-kucuk:bolum-1:p3", "test-kucuk", status: "kullanim_disi", successors: "[{\"anchor\":\"k:test-kucuk:bolum-1:p1\"}]");
        EditorialSnapshot changed = With(snapshot, units: [.. snapshot.Units, draft, retired]);

        GateInput input = Build(changed);

        GateUnit mappedDraft = input.Units.Single(u => u.Anchor == "k:test-kucuk:bolum-1:p2");
        Assert.True(mappedDraft.IsAiDraft);
        Assert.Equal(TextStatus.Taslak, mappedDraft.TextStatus);
        Assert.Equal(UnitStatus.Etkin, mappedDraft.Status);
        Assert.False(mappedDraft.HasSuccessors);
        GateUnit mappedRetired = input.Units.Single(u => u.Anchor == "k:test-kucuk:bolum-1:p3");
        Assert.Equal(UnitStatus.KullanimDisi, mappedRetired.Status);
        Assert.True(mappedRetired.HasSuccessors);
        Assert.Equal("test-kucuk", mappedRetired.SourceSlug);
    }

    [Fact]
    public void An_ai_draft_is_reported_as_p08_and_a_plain_draft_as_p10_in_public()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        UnitRow ai = PackTestData.Unit("q:1:4", "tanzil-uthmani", "ayet", durum: "taslak", aiDraft: true);
        EditorialSnapshot changed = With(snapshot, units: [.. snapshot.Units, ai]);

        GateResult result = PackTestData.Evaluate(BuildFlavor.Public, changed);

        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Rule == GateRule.P08 && r.Id == "tanzil-uthmani");
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Rule == GateRule.P10 && r.Id == "tanzil-uthmani");
        Assert.DoesNotContain("q:1:3", result.IncludedUnits);
        Assert.DoesNotContain("q:1:4", result.IncludedUnits);
    }

    [Fact]
    public void Xref_flags_map_confidence_review_lexicon_and_source_slugs()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        Guid first = Guid.NewGuid();
        Guid second = Guid.NewGuid();
        Guid third = Guid.NewGuid();
        XrefRow reviewed = PackTestData.Xref("q:1:1", "q:1:2", "kok", "aday", confidence: 0.7f, id: first) with { LexiconStatus = "aday" };
        XrefRow approvedLexicon = PackTestData.Xref("q:1:1", "q:1:2", "lemma", "onayli", id: second) with { LexiconStatus = "onayli" };
        XrefRow unknownEnd = PackTestData.Xref("q:1:1", "rn:yok:p1", "atif", "aday", id: third);
        EditorialSnapshot changed = With(snapshot, xrefs: [reviewed, approvedLexicon, unknownEnd], reviews: new HashSet<Guid> { first });

        GateInput input = Build(changed);

        GateXref a = input.Xrefs.Single(x => x.Id == first);
        Assert.Equal((XrefType.Kok, XrefStatus.Aday), (a.Type, a.Status));
        Assert.Equal(0.7, a.Confidence);
        Assert.True(a.HasOpenReview);
        Assert.False(a.LexiconApproved);
        Assert.Equal(("tanzil-uthmani", "tanzil-uthmani", false), (a.SrcSourceSlug, a.DstSourceSlug, a.DstIsSeparateIndex));
        GateXref b = input.Xrefs.Single(x => x.Id == second);
        Assert.True(b.LexiconApproved);
        Assert.False(b.HasOpenReview);
        GateXref c = input.Xrefs.Single(x => x.Id == third);
        Assert.Equal(string.Empty, c.DstSourceSlug);
        Assert.True(c.LexiconApproved);
    }

    [Fact]
    public void A_xref_without_lexicon_status_counts_as_approved_and_a_link_to_a_separate_index_is_marked()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot changed = With(
            snapshot,
            sources: [.. snapshot.Sources, PackTestData.Source("risale-atif-dizini", "baglanti_verisi")],
            units: [.. snapshot.Units, PackTestData.Unit("rn:atif:p1", "risale-atif-dizini", "risale")],
            xrefs: [PackTestData.Xref("q:1:1", "rn:atif:p1", "atif", "onayli")]);

        GateXref xref = Assert.Single(Build(changed).Xrefs);

        Assert.True(xref.DstIsSeparateIndex);
        Assert.Equal("risale-atif-dizini", xref.DstSourceSlug);
        Assert.True(xref.LexiconApproved);
    }

    [Fact]
    public void Lexical_rows_map_kind_status_and_linked_lemma()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        EditorialSnapshot changed = With(
            snapshot,
            lexicals:
            [
                new LexicalRow(LexicalKind.QuranWordFix, "id-1", "onayli", false),
                new LexicalRow(LexicalKind.LemmaGloss, "7", "aday", false),
                new LexicalRow(LexicalKind.TrRootIndex, "q:1:1|0", null, true),
            ]);

        GateInput input = Build(changed);

        Assert.Equal(
            [(LexicalKind.QuranWordFix, XrefStatus.Onayli, false), (LexicalKind.LemmaGloss, XrefStatus.Aday, false), (LexicalKind.TrRootIndex, (XrefStatus?)null, true)],
            input.Lexicals.Select(l => (l.Kind, l.Status, l.LinkedLemmaApproved)));
    }

    [Fact]
    public void Carried_packs_and_previous_anchors_pass_through()
    {
        GateInput input = Build(carried: ["kelime-kok"], previous: ["q:1:1", "q:9:9"]);

        Assert.Equal(["kelime-kok"], input.CarriedPackIds);
        Assert.Equal(["q:1:1", "q:9:9"], input.PreviousAnchors);
        Assert.Empty(Build().CarriedPackIds);
        Assert.Empty(Build().PreviousAnchors);
    }

    [Fact]
    public void A_previous_anchor_missing_from_the_snapshot_rejects_the_release_with_continuity()
    {
        GateInput input = Build(previous: ["q:1:1", "q:9:9"]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.True(result.Rejected);
        GateViolation violation = Assert.Single(result.Report.Violations);
        Assert.Equal(("q:9:9", GateReasons.CapaKayip), (violation.Subject, violation.Reason));
        Assert.Null(violation.Rule);
    }

    [Fact]
    public void An_unknown_enum_label_is_a_data_error()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        UnitRow bad = PackTestData.Unit("k:test-kucuk:bolum-1:p9", "test-kucuk", durum: "bilinmiyor");
        EditorialSnapshot changed = With(snapshot, units: [.. snapshot.Units, bad]);

        Assert.Throws<InvalidDataException>(() => Build(changed));
    }

    [Fact]
    public void IsRegistered_checks_the_toml_file_and_never_leaves_the_directory()
    {
        string sources = RepoFiles.PathOf("pipeline/sources");

        Assert.True(GateInputBuilder.IsRegistered(sources, "tanzil-uthmani", File.Exists));
        Assert.True(GateInputBuilder.IsRegistered(sources, "test-kucuk", File.Exists));
        Assert.False(GateInputBuilder.IsRegistered(sources, "yok-kaynak", File.Exists));
        Assert.False(GateInputBuilder.IsRegistered(sources, "../packages/x", _ => true));
        Assert.False(GateInputBuilder.IsRegistered(sources, string.Empty, _ => true));
    }

    [Fact]
    public void The_default_file_check_uses_the_sources_directory()
    {
        // fileExists verilmezse File.Exists kullanilir: depodaki gercek kayit dosyalari bulunur.
        GateInput input = GateInputBuilder.Build(PackTestData.Snapshot(), PackCatalog.Default, RepoFiles.PathOf("pipeline/sources"));

        Assert.All(input.Sources, s => Assert.True(s.Registered, s.Slug));
    }
}
