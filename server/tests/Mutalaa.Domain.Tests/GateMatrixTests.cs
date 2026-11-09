using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Derleme turu x icerik matrisinin her hucresi (Yayin sureci 5 madde 1). Her Theory hem Invariant hem tr-TR kulturunde kosar.
/// Beklenen degerler tabloda acik yazilidir; kapi mantigindan turetilmez.
/// </summary>
public class GateMatrixTests
{
    // ---- Birim: derleme turu x metin durumu x yapay zeka taslagi ----

    public static TheoryData<BuildFlavor, TextStatus, bool, bool, GateRule?> UnitCells()
    {
        TheoryData<BuildFlavor, TextStatus, bool, bool, GateRule?> data = [];

        foreach (BuildFlavor inner in new[] { BuildFlavor.Dev, BuildFlavor.Internal })
        {
            foreach (TextStatus status in new[] { TextStatus.Taslak, TextStatus.Incelemede, TextStatus.Onayli })
            {
                data.Add(inner, status, false, true, null);
                data.Add(inner, status, true, true, null);
            }
        }

        data.Add(BuildFlavor.Public, TextStatus.Onayli, false, true, null);
        data.Add(BuildFlavor.Public, TextStatus.Onayli, true, true, null);
        data.Add(BuildFlavor.Public, TextStatus.Taslak, false, false, GateRule.P10);
        data.Add(BuildFlavor.Public, TextStatus.Taslak, true, false, GateRule.P08);
        data.Add(BuildFlavor.Public, TextStatus.Incelemede, false, false, GateRule.P10);
        data.Add(BuildFlavor.Public, TextStatus.Incelemede, true, false, GateRule.P08);
        return data;
    }

    [Theory]
    [MemberData(nameof(UnitCells))]
    public void Unit_matrix_under_invariant_culture(BuildFlavor flavor, TextStatus status, bool aiDraft, bool included, GateRule? rule) =>
        CultureScope.Invariant(() => AssertUnitCell(flavor, status, aiDraft, included, rule));

    [Theory]
    [MemberData(nameof(UnitCells))]
    public void Unit_matrix_under_turkish_culture(BuildFlavor flavor, TextStatus status, bool aiDraft, bool included, GateRule? rule) =>
        CultureScope.Turkish(() => AssertUnitCell(flavor, status, aiDraft, included, rule));

    private static void AssertUnitCell(BuildFlavor flavor, TextStatus status, bool aiDraft, bool included, GateRule? rule)
    {
        GateInput input = WithRegularSource(units: [Unit("q:1:1", status: status, aiDraft: aiDraft)]);

        GateResult result = GateEvaluator.Evaluate(flavor, input);

        Assert.Equal(included, result.IncludedUnits.Contains("q:1:1"));
        GateReportRow row = Single(result, GateSubjectKind.Birim);
        Assert.Equal(included ? GateDecision.Girdi : GateDecision.Girmedi, row.Decision);
        Assert.Equal(rule, row.Rule);
        Assert.False(result.Rejected);
        if (included && status != TextStatus.Onayli)
        {
            Assert.Equal(GateReasons.Dogrulanmamis, row.Reason);
        }
    }

    // ---- Baglanti: derleme turu x tur x durum x confidence ----

    // devIn, internalIn, publicIn: beklenen giris; girmeyen hucrede kural P-07'dir.
    public static TheoryData<XrefType, XrefStatus, double, bool, bool, bool, bool, bool> XrefCells()
    {
        TheoryData<XrefType, XrefStatus, double, bool, bool, bool, bool, bool> data = [];

        // type, status, confidence, devIn, internalIn, publicIn, approved, folded
        // Insan onayi isteyen tur (atif): confidence karari etkilemez.
        data.Add(XrefType.Atif, XrefStatus.Onayli, 0.90, true, true, true, true, false);
        data.Add(XrefType.Atif, XrefStatus.Onayli, 0.00, true, true, true, true, false);
        data.Add(XrefType.Atif, XrefStatus.Aday, 0.90, true, true, false, false, false);
        data.Add(XrefType.Atif, XrefStatus.Aday, 0.20, true, true, false, false, false);
        data.Add(XrefType.Atif, XrefStatus.Red, 0.90, false, false, false, false, false);

        // Otomatik tur (benzer_ayet): esikler 0,50 (giris) ve 0,70 (katlama).
        data.Add(XrefType.BenzerAyet, XrefStatus.Onayli, 0.49, true, true, true, true, false);
        data.Add(XrefType.BenzerAyet, XrefStatus.Onayli, 0.90, true, true, true, true, false);
        data.Add(XrefType.BenzerAyet, XrefStatus.Aday, 0.49, false, false, false, false, true);
        data.Add(XrefType.BenzerAyet, XrefStatus.Aday, 0.50, true, true, true, false, true);
        data.Add(XrefType.BenzerAyet, XrefStatus.Aday, 0.69, true, true, true, false, true);
        data.Add(XrefType.BenzerAyet, XrefStatus.Aday, 0.70, true, true, true, false, false);
        data.Add(XrefType.BenzerAyet, XrefStatus.Aday, 0.95, true, true, true, false, false);
        data.Add(XrefType.BenzerAyet, XrefStatus.Red, 0.90, false, false, false, false, false);

        // anlamsal: her zaman katli; v1 public'te yok (onayli olsa bile).
        data.Add(XrefType.Anlamsal, XrefStatus.Onayli, 0.90, true, true, false, true, true);
        data.Add(XrefType.Anlamsal, XrefStatus.Aday, 0.80, true, true, false, false, true);
        data.Add(XrefType.Anlamsal, XrefStatus.Aday, 0.49, false, false, false, false, true);
        data.Add(XrefType.Anlamsal, XrefStatus.Red, 0.90, false, false, false, false, true);
        return data;
    }

    [Theory]
    [MemberData(nameof(XrefCells))]
    public void Xref_matrix_under_invariant_culture(XrefType type, XrefStatus status, double confidence, bool dev, bool internalIn, bool publicIn, bool approved, bool folded) =>
        CultureScope.Invariant(() => AssertXrefCell(type, status, confidence, dev, internalIn, publicIn, approved, folded));

    [Theory]
    [MemberData(nameof(XrefCells))]
    public void Xref_matrix_under_turkish_culture(XrefType type, XrefStatus status, double confidence, bool dev, bool internalIn, bool publicIn, bool approved, bool folded) =>
        CultureScope.Turkish(() => AssertXrefCell(type, status, confidence, dev, internalIn, publicIn, approved, folded));

    private static void AssertXrefCell(XrefType type, XrefStatus status, double confidence, bool dev, bool internalIn, bool publicIn, bool approved, bool folded)
    {
        (BuildFlavor Flavor, bool Expected)[] cells =
        [
            (BuildFlavor.Dev, dev),
            (BuildFlavor.Internal, internalIn),
            (BuildFlavor.Public, publicIn),
        ];

        foreach ((BuildFlavor flavor, bool expected) in cells)
        {
            GateXref xref = Xref(type, status, confidence);
            GateResult result = GateEvaluator.Evaluate(flavor, WithRegularSource(xrefs: [xref]));

            XrefVerdict verdict = result.XrefVerdicts[xref.Id];
            Assert.True(expected == verdict.Included, $"{flavor} {type.ToLabel()} {status.ToLabel()} {confidence}: beklenen giris={expected}");
            Assert.Equal(expected, result.IsXrefIncluded(xref.Id));
            Assert.Equal(expected ? null : GateRule.P07, verdict.Rule);
            Assert.Equal(approved, verdict.Approved);
            Assert.Equal(folded, verdict.Folded);
            Assert.False(result.Rejected);
        }
    }

    // Aday satirin tur taramasi: insan onayi isteyen turler public'te yok; otomatik turler 0,50 ile her derlemede.
    public static TheoryData<XrefType, bool> CandidateTypes() => new()
    {
        { XrefType.Atif, true },
        { XrefType.Iktibas, true },
        { XrefType.Ima, true },
        { XrefType.Konu, true },
        { XrefType.Kok, false },
        { XrefType.Lemma, false },
        { XrefType.BenzerAyet, false },
    };

    [Theory]
    [MemberData(nameof(CandidateTypes))]
    public void Candidate_xref_by_type_under_invariant_culture(XrefType type, bool humanApproval) =>
        CultureScope.Invariant(() => AssertCandidateType(type, humanApproval));

    [Theory]
    [MemberData(nameof(CandidateTypes))]
    public void Candidate_xref_by_type_under_turkish_culture(XrefType type, bool humanApproval) =>
        CultureScope.Turkish(() => AssertCandidateType(type, humanApproval));

    private static void AssertCandidateType(XrefType type, bool humanApproval)
    {
        GateXref xref = Xref(type, XrefStatus.Aday, 0.50);

        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Dev, WithRegularSource(xrefs: [xref])).IsXrefIncluded(xref.Id));
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Internal, WithRegularSource(xrefs: [xref])).IsXrefIncluded(xref.Id));
        Assert.Equal(!humanApproval, GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [xref])).IsXrefIncluded(xref.Id));
        Assert.Equal(humanApproval, XrefTypeClass.RequiresHumanApproval(type));
        Assert.Equal(!humanApproval, XrefTypeClass.IsAutomatic(type));
    }

    // ---- Kaynak: derleme turu x slug x kayit durumu ----

    // flavor, slug, registered, attribution, expectedIncluded, expectedRule, expectedViolation
    public static TheoryData<BuildFlavor, string, bool, string?, bool, GateRule?, bool> SourceCells()
    {
        TheoryData<BuildFlavor, string, bool, string?, bool, GateRule?, bool> data = [];

        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            data.Add(flavor, Regular, true, Attribution, true, null, false);
            data.Add(flavor, "kaynaksiz", false, null, false, GateRule.P01, true);
            data.Add(flavor, "bos-atif", true, "", false, GateRule.P01, true);
            data.Add(flavor, "bosluk-atif", true, "   ", false, GateRule.P01, true);
            data.Add(flavor, "atifsiz", true, null, false, GateRule.P01, true);
        }

        data.Add(BuildFlavor.Dev, "test-kucuk", true, Attribution, true, null, false);
        data.Add(BuildFlavor.Internal, "test-kucuk", true, Attribution, true, null, false);
        data.Add(BuildFlavor.Public, "test-kucuk", true, Attribution, false, GateRule.P12, false);

        data.Add(BuildFlavor.Dev, "test-ses", true, Attribution, true, null, false);
        data.Add(BuildFlavor.Internal, "test-ses", true, Attribution, true, null, false);
        data.Add(BuildFlavor.Public, "test-ses", true, Attribution, false, GateRule.P12, false);

        data.Add(BuildFlavor.Dev, "test-tefsir-ornek", true, Attribution, true, null, false);
        data.Add(BuildFlavor.Internal, "test-tefsir-ornek", true, Attribution, false, GateRule.P12, false);
        data.Add(BuildFlavor.Public, "test-tefsir-ornek", true, Attribution, false, GateRule.P12, false);

        // Kaydi olmayan test- kaynagi: dev ve internal'da (girebilecegi yerde) P-01 ihlali; public'te P-12 ile zaten girmez.
        data.Add(BuildFlavor.Dev, "test-kucuk", false, null, false, GateRule.P01, true);
        data.Add(BuildFlavor.Internal, "test-ses", false, null, false, GateRule.P01, true);
        data.Add(BuildFlavor.Public, "test-kucuk", false, null, false, GateRule.P12, false);

        // Buyuk harfli ad: onek buyuk-kucuk gozetmeden test- sayilir, fikstur adi ise tam eslesmelidir.
        data.Add(BuildFlavor.Internal, "TEST-KUCUK", true, Attribution, false, GateRule.P12, false);
        data.Add(BuildFlavor.Public, "TEST-KUCUK", true, Attribution, false, GateRule.P12, false);
        return data;
    }

    [Theory]
    [MemberData(nameof(SourceCells))]
    public void Source_matrix_under_invariant_culture(BuildFlavor flavor, string slug, bool registered, string? attribution, bool included, GateRule? rule, bool violation) =>
        CultureScope.Invariant(() => AssertSourceCell(flavor, slug, registered, attribution, included, rule, violation));

    [Theory]
    [MemberData(nameof(SourceCells))]
    public void Source_matrix_under_turkish_culture(BuildFlavor flavor, string slug, bool registered, string? attribution, bool included, GateRule? rule, bool violation) =>
        CultureScope.Turkish(() => AssertSourceCell(flavor, slug, registered, attribution, included, rule, violation));

    private static void AssertSourceCell(BuildFlavor flavor, string slug, bool registered, string? attribution, bool included, GateRule? rule, bool violation)
    {
        GateInput input = new()
        {
            Sources = [Src(slug, registered, attribution)],
            Units = [Unit("k:" + slug + ":bolum-1:p1", source: slug)],
        };

        GateResult result = GateEvaluator.Evaluate(flavor, input);

        Assert.Equal(included, result.IncludedSources.Contains(slug));
        GateReportRow row = Row(result, GateSubjectKind.Kaynak, slug);
        Assert.Equal(included ? GateDecision.Girdi : GateDecision.Girmedi, row.Decision);
        Assert.Equal(rule, row.Rule);
        Assert.Equal(violation, result.Rejected);

        // Kaynagin birimi kaynakla ayni kararı alir.
        Assert.Equal(included, result.IncludedUnits.Count == 1);
        GateReportRow unitRow = Single(result, GateSubjectKind.Birim);
        Assert.Equal(rule, unitRow.Rule);
    }

    // ---- Paket: derleme turu x paket ----

    // flavor, packId, sources, hasContent, expectedIncluded, expectedRule, expectedViolation
    public static TheoryData<BuildFlavor, string, string[], bool, bool, GateRule?, bool> PackCells()
    {
        TheoryData<BuildFlavor, string, string[], bool, bool, GateRule?, bool> data = [];

        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            data.Add(flavor, "core", [Regular], true, true, null, false);
            data.Add(flavor, "kaynaksiz-paket", ["kaydi-yok"], true, false, GateRule.P01, true);
            data.Add(flavor, "kaynak-listesiz", [], true, false, GateRule.P01, true);
            data.Add(flavor, "kelime-kok", [Regular], false, false, null, false);
        }

        data.Add(BuildFlavor.Dev, "test-kucuk", ["test-kucuk"], true, true, null, false);
        data.Add(BuildFlavor.Internal, "test-kucuk", ["test-kucuk"], true, true, null, false);
        data.Add(BuildFlavor.Public, "test-kucuk", ["test-kucuk"], true, false, GateRule.P12, false);

        data.Add(BuildFlavor.Dev, "tefsir-test-ornek", ["test-tefsir-ornek"], true, true, null, false);
        data.Add(BuildFlavor.Internal, "tefsir-test-ornek", ["test-tefsir-ornek"], true, false, GateRule.P12, false);
        data.Add(BuildFlavor.Public, "tefsir-test-ornek", ["test-tefsir-ornek"], true, false, GateRule.P12, false);

        // Birden cok kaynakli paket: suzme kaynak duzeyindedir, paket girebilen kaynakla girer.
        data.Add(BuildFlavor.Public, "karma", [Regular, "test-kucuk"], true, true, null, false);
        data.Add(BuildFlavor.Internal, "karma", [Regular, "test-tefsir-ornek"], true, true, null, false);
        return data;
    }

    [Theory]
    [MemberData(nameof(PackCells))]
    public void Pack_matrix_under_invariant_culture(BuildFlavor flavor, string packId, string[] sources, bool hasContent, bool included, GateRule? rule, bool violation) =>
        CultureScope.Invariant(() => AssertPackCell(flavor, packId, sources, hasContent, included, rule, violation));

    [Theory]
    [MemberData(nameof(PackCells))]
    public void Pack_matrix_under_turkish_culture(BuildFlavor flavor, string packId, string[] sources, bool hasContent, bool included, GateRule? rule, bool violation) =>
        CultureScope.Turkish(() => AssertPackCell(flavor, packId, sources, hasContent, included, rule, violation));

    private static void AssertPackCell(BuildFlavor flavor, string packId, string[] sources, bool hasContent, bool included, GateRule? rule, bool violation)
    {
        // Kaynak kaydi: "kaydi-yok" disindakiler kayitli; "kaydi-yok" girdide hic yok.
        GateInput input = new()
        {
            Sources = [.. new[] { Regular, "test-kucuk", "test-tefsir-ornek" }.Select(s => Src(s))],
            Packs = [Pack(packId, sources, hasContent: hasContent)],
        };

        GateResult result = GateEvaluator.Evaluate(flavor, input);

        Assert.Equal(included, result.IncludedPacks.Contains(packId));
        GateReportRow row = Row(result, GateSubjectKind.Paket, packId);
        Assert.Equal(included ? GateDecision.Girdi : GateDecision.Girmedi, row.Decision);
        Assert.Equal(rule, row.Rule);
        Assert.Equal(violation, result.Rejected);
        if (!hasContent)
        {
            Assert.Equal(GateReasons.IcerikYok, row.Reason);
        }
    }
}
