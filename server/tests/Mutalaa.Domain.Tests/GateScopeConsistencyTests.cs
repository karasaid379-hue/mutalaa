using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// K-47 (BC-50 a): sarkan baglanti ("uc-birim-girmedi", P-07) ve (BC-50 b): capa sureklilik ("capa-kayboldu", kural kodu yok).
/// Her test Invariant ve tr-TR kulturunde kosar. Capalar yalniz kimliktir; metin yoktur.
/// </summary>
public class GateScopeConsistencyTests
{
    private const string Src1 = "q:1:1";
    private const string Dst1 = "q:1:2";

    private static GateXref LinkBetween(string src, string dst, XrefStatus status = XrefStatus.Onayli, int id = 1) =>
        Xref(XrefType.Atif, status, id: id) with { SrcAnchor = src, DstAnchor = dst };

    private static GateReportRow XrefRow(GateResult result) => Single(result, GateSubjectKind.Baglanti);

    // ---- Sarkan baglanti (K-47 madde 1) ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Xref_with_a_draft_end_unit_is_dropped_in_public_and_kept_in_dev_and_internal(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = LinkBetween(Src1, Dst1);
        GateInput input = WithRegularSource(
            units: [Unit(Src1), Unit(Dst1, status: TextStatus.Taslak)],
            xrefs: [xref]);

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        XrefVerdict verdict = publicResult.XrefVerdicts[xref.Id];

        Assert.False(publicResult.IsXrefIncluded(xref.Id));
        Assert.Equal(GateRule.P07, verdict.Rule);
        Assert.Equal(GateReasons.UcBirimGirmedi, verdict.Reason);
        Assert.Equal("hedef=P-10:onaysiz-birim", verdict.Detail);
        Assert.False(publicResult.Rejected);

        GateReportRow row = XrefRow(publicResult);
        Assert.Equal(GateDecision.Girmedi, row.Decision);
        Assert.Equal(GateRule.P07, row.Rule);
        Assert.Equal("uc-birim-girmedi:hedef=P-10:onaysiz-birim", row.Reason);

        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal })
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);
            Assert.True(result.IsXrefIncluded(xref.Id), flavor.ToLabel());
            Assert.Equal(GateDecision.Girdi, XrefRow(result).Decision);
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Xref_with_an_ai_draft_source_end_names_P08_and_the_source_end(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = LinkBetween(Src1, Dst1);
        GateInput input = WithRegularSource(
            units: [Unit(Src1, status: TextStatus.Taslak, aiDraft: true), Unit(Dst1)],
            xrefs: [xref]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.False(result.IsXrefIncluded(xref.Id));
        Assert.Equal("kaynak=P-08:yapay-zeka-taslagi-onaysiz", result.XrefVerdicts[xref.Id].Detail);
        Assert.Equal("uc-birim-girmedi:kaynak=P-08:yapay-zeka-taslagi-onaysiz", XrefRow(result).Reason);
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Dev, input).IsXrefIncluded(xref.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Xref_with_both_ends_out_of_scope_lists_both_ends_and_a_deprecated_end_is_out_in_every_flavor(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = LinkBetween(Src1, Dst1);
        GateInput input = WithRegularSource(
            units: [Unit(Src1, status: TextStatus.Incelemede), Unit(Dst1, unitStatus: UnitStatus.KullanimDisi, hasSuccessors: true)],
            xrefs: [xref]);

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        Assert.Equal("kaynak=P-10:onaysiz-birim,hedef=kullanim-disi", publicResult.XrefVerdicts[xref.Id].Detail);

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);
            Assert.False(result.IsXrefIncluded(xref.Id), flavor.ToLabel());
        }

        GateResult dev = GateEvaluator.Evaluate(BuildFlavor.Dev, input);
        Assert.Equal("hedef=kullanim-disi", dev.XrefVerdicts[xref.Id].Detail);
    });

    [Theory]
    [InlineData(false, "q:1:2:3-7")]
    [InlineData(true, "q:1:2:3-7")]
    [InlineData(false, "q:1:2:3")]
    [InlineData(true, "q:1:2:3")]
    public void Xref_end_with_a_word_range_resolves_to_its_unit(bool turkish, string wordEnd) => CultureScope.For(turkish, () =>
    {
        GateXref xref = LinkBetween(Src1, wordEnd);
        GateInput input = WithRegularSource(units: [Unit(Src1), Unit(Dst1, status: TextStatus.Taslak)], xrefs: [xref]);

        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Public, input).IsXrefIncluded(xref.Id));
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Dev, input).IsXrefIncluded(xref.Id));

        GateInput approved = WithRegularSource(units: [Unit(Src1), Unit(Dst1)], xrefs: [xref]);
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, approved).IsXrefIncluded(xref.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Xref_end_with_an_exact_offset_range_resolves_to_its_unit(bool turkish) => CultureScope.For(turkish, () =>
    {
        const string paragraph = "rn:sozler:soz-1:p1";
        GateXref xref = LinkBetween(Src1, paragraph + "@0-5");
        GateInput input = WithRegularSource(units: [Unit(Src1), Unit(paragraph, status: TextStatus.Taslak)], xrefs: [xref]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.False(result.IsXrefIncluded(xref.Id));
        Assert.Equal("hedef=P-10:onaysiz-birim", result.XrefVerdicts[xref.Id].Detail);
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Internal, input).IsXrefIncluded(xref.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_end_unit_filter_only_looks_at_ends_that_have_a_unit_row_in_the_input(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Yalniz CheckXrefEndUnits'in kendi davranisi (Domain duzeyi): girdide birim satiri olmayan uc, kaynak slug'i gorunur verilmisse suzmede adlanmaz.
        // Gercek akista GateInputBuilder birim satiri olmayan ucun slug'ini bos yapar ve baglanti bu filtreye gelmeden "hedef-eser-gorunmez" ile
        // elenir; o yol GateInputBuilderTests.K47_a_link_to_an_end_without_a_unit_row_... testinde Build uzerinden kilitlidir.
        GateXref topic = LinkBetween(Src1, "konu:tevhid", id: 1);
        GateXref noUnits = LinkBetween("q:9:9", "q:9:10", id: 2);
        GateInput input = WithRegularSource(units: [Unit(Src1)], xrefs: [topic, noUnits]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.True(result.IsXrefIncluded(topic.Id));
        Assert.True(result.IsXrefIncluded(noUnits.Id));

        // Satirsiz ucun oteki ucu taslaga donunce suzmede adlanan yalniz o oteki uctur.
        GateInput draft = WithRegularSource(units: [Unit(Src1, status: TextStatus.Taslak)], xrefs: [topic]);
        GateResult dropped = GateEvaluator.Evaluate(BuildFlavor.Public, draft);
        Assert.False(dropped.IsXrefIncluded(topic.Id));
        Assert.Equal("kaynak=P-10:onaysiz-birim", dropped.XrefVerdicts[topic.Id].Detail);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Xref_into_a_separate_index_is_not_checked_against_the_destination_unit(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Domain duzeyi; Build'in DstIsSeparateIndex'i kurmasi GateInputBuilderTests.K47_a_link_into_a_separate_index_... testindedir.
        GateXref xref = Xref(XrefType.Atif, XrefStatus.Onayli, dst: "risale-atif-dizini", separateIndex: true) with { DstAnchor = "rn:sozler:soz-1:p1" };
        GateInput input = new()
        {
            Sources = [Src(Regular), Src("risale-atif-dizini")],
            Units = [Unit(Src1), Unit("rn:sozler:soz-1:p1", source: "risale-atif-dizini", status: TextStatus.Taslak)],
            Xrefs = [xref],
        };

        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, input).IsXrefIncluded(xref.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void An_xref_already_excluded_for_another_reason_keeps_that_reason(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref red = LinkBetween(Src1, Dst1, XrefStatus.Red);
        GateInput input = WithRegularSource(units: [Unit(Src1), Unit(Dst1, status: TextStatus.Taslak)], xrefs: [red]);

        XrefVerdict verdict = GateEvaluator.Evaluate(BuildFlavor.Public, input).XrefVerdicts[red.Id];

        Assert.Equal(GateReasons.Red, verdict.Reason);
        Assert.Equal(string.Empty, verdict.Detail);
    });

    [Theory]
    [InlineData(false, BuildFlavor.Dev, TextStatus.Taslak, true)]
    [InlineData(false, BuildFlavor.Internal, TextStatus.Incelemede, true)]
    [InlineData(false, BuildFlavor.Public, TextStatus.Taslak, false)]
    [InlineData(false, BuildFlavor.Public, TextStatus.Incelemede, false)]
    [InlineData(false, BuildFlavor.Public, TextStatus.Onayli, true)]
    [InlineData(true, BuildFlavor.Dev, TextStatus.Taslak, true)]
    [InlineData(true, BuildFlavor.Internal, TextStatus.Incelemede, true)]
    [InlineData(true, BuildFlavor.Public, TextStatus.Taslak, false)]
    [InlineData(true, BuildFlavor.Public, TextStatus.Incelemede, false)]
    [InlineData(true, BuildFlavor.Public, TextStatus.Onayli, true)]
    public void End_unit_matrix_flavor_by_text_status(bool turkish, BuildFlavor flavor, TextStatus endStatus, bool expectedIncluded) => CultureScope.For(turkish, () =>
    {
        GateXref xref = LinkBetween(Src1, Dst1);
        GateInput input = WithRegularSource(units: [Unit(Src1), Unit(Dst1, status: endStatus)], xrefs: [xref]);

        GateResult result = GateEvaluator.Evaluate(flavor, input);

        Assert.Equal(expectedIncluded, result.IsXrefIncluded(xref.Id));
        Assert.Equal(expectedIncluded ? null : GateRule.P07, result.XrefVerdicts[xref.Id].Rule);
        Assert.False(result.Rejected);
    });

    // ---- Capa sureklilik (K-47 madde 2) ----

    private static GateInput Previous(string[] previous, params GateUnit[] units) =>
        new() { Sources = [Src(Regular)], Units = units, PreviousAnchors = previous };

    private static string[] Reasons(GateResult result) => [.. result.Report.Violations.Select(v => v.Subject + "=" + v.Reason)];

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Active_unit_back_to_draft_rejects_public_but_passes_dev_and_internal(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = Previous([Src1], Unit(Src1, status: TextStatus.Taslak));

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.True(publicResult.Rejected);
        GateViolation violation = Assert.Single(publicResult.Report.Violations);
        Assert.Null(violation.Rule);
        Assert.Equal(Src1, violation.Subject);
        Assert.Equal("capa-kayboldu:onaysiz-birim", violation.Reason);

        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Dev, input).Rejected);
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Internal, input).Rejected);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Ai_draft_unit_is_named_in_the_continuity_reason(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = Previous([Src1], Unit(Src1, status: TextStatus.Taslak, aiDraft: true));

        Assert.Equal(["q:1:1=capa-kayboldu:yapay-zeka-taslagi-onaysiz"], Reasons(GateEvaluator.Evaluate(BuildFlavor.Public, input)));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Deprecated_unit_with_successors_keeps_continuity_in_every_flavor(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = Previous([Src1], Unit(Src1, unitStatus: UnitStatus.KullanimDisi, hasSuccessors: true));

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            Assert.False(GateEvaluator.Evaluate(flavor, input).Rejected, flavor.ToLabel());
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Deprecated_unit_without_successors_and_anchor_without_a_row_are_rejected(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = Previous(
            [Src1, Dst1, "q:1:3"],
            Unit(Src1, unitStatus: UnitStatus.KullanimDisi, hasSuccessors: false),
            Unit(Dst1));

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);
            Assert.Equal(["q:1:1=capa-kayboldu:yonlendirmesiz", "q:1:3=capa-kayboldu:satir-yok"], Reasons(result));
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Active_unit_filtered_out_by_its_source_rule_is_lost_with_that_reason(bool turkish) => CultureScope.For(turkish, () =>
    {
        const string anchor = "k:test-kucuk:bolum-1:p1";
        GateInput input = new()
        {
            Sources = [Src(Regular), Src("test-kucuk")],
            Units = [Unit(anchor, source: "test-kucuk")],
            PreviousAnchors = [anchor],
        };

        Assert.Equal(["k:test-kucuk:bolum-1:p1=capa-kayboldu:test-oneki"], Reasons(GateEvaluator.Evaluate(BuildFlavor.Public, input)));
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Internal, input).Rejected);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Previous_anchors_in_scope_pass_and_no_previous_anchors_means_no_check(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput inScope = Previous([Src1, Dst1], Unit(Src1), Unit(Dst1));
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Public, inScope).Rejected);

        GateInput none = Previous([], Unit(Src1, status: TextStatus.Taslak));
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Public, none).Rejected);
    });
}
