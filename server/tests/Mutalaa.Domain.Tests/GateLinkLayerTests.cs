using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// K-51 (A18.6): tur bazinda yayin kapisi (xref_gate), uc ozeti (uc-ozeti-tutmadi), Turkce lemma / tr_root_index / tr_form kurallari (P-09:
/// kanitsiz-otomatik-onay, ozet-tutmadi, kapi-olculmedi, kapi-gecmedi) ve rapordaki kapi satirlari. Sentetik veri; hicbir dini metin yoktur.
/// Her test Invariant ve tr-TR kulturunde kosar.
/// </summary>
public class GateLinkLayerTests
{
    private static readonly XrefType[] AutoGateTypes = [XrefType.Kok, XrefType.Lemma, XrefType.BenzerAyet];

    private const string HashA = "aaaaaaaaaaaaaaaa";
    private const string HashB = "bbbbbbbbbbbbbbbb";

    // ---- XrefGateRules.Resolve ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Resolve_picks_gold_over_silver_and_ignores_synthetic_unknown_and_other_types(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve([], XrefType.Kok).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve([Gate(XrefType.Kok, "sentetik", "gecti")], XrefType.Kok).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve([Gate(XrefType.Kok, "silver", "belki")], XrefType.Kok).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve([Gate(XrefType.Lemma, "silver", "gecti")], XrefType.Kok).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve([Gate(XrefType.Kok, "Silver", "gecti")], XrefType.Kok).Status);

        XrefTypeGate silver = XrefGateRules.Resolve([Gate(XrefType.Kok, "silver", "gecti")], XrefType.Kok);
        Assert.True(silver.Opens);
        Assert.Equal("silver", silver.SetClass);

        XrefTypeGate goldFailed = XrefGateRules.Resolve([Gate(XrefType.Kok, "silver", "gecti"), Gate(XrefType.Kok, "altin", "kaldi")], XrefType.Kok);
        Assert.Equal(XrefGateStatus.Failed, goldFailed.Status);
        Assert.Equal("altin", goldFailed.SetClass);

        XrefTypeGate synthPlusFailed = XrefGateRules.Resolve([Gate(XrefType.Kok, "sentetik", "gecti"), Gate(XrefType.Kok, "silver", "kaldi")], XrefType.Kok);
        Assert.Equal(XrefGateStatus.Failed, synthPlusFailed.Status);

        Assert.Equal(GateReasons.KapiOlculmedi, XrefGateRules.ReasonWhenClosed(XrefTypeGate.NotMeasured));
        Assert.Equal(GateReasons.KapiGecmedi, XrefGateRules.ReasonWhenClosed(synthPlusFailed));
        Assert.Null(XrefGateRules.ReasonWhenClosed(silver));
        Assert.True(XrefGateRules.HasGate(XrefType.BenzerAyet));
        Assert.False(XrefGateRules.HasGate(XrefType.Anlamsal));
        Assert.False(XrefGateRules.HasGate(XrefType.Atif));
    });

    // ---- P-07: tur kapisi, derleme turu x tur x kapi durumu ----

    // gates (set sinifi ve sonuc, null = satir yok), publicIn, kapali kapinin gerekcesi
    public static TheoryData<string?, string?, bool, string?> GateStates() => new()
    {
        { null, null, false, GateReasons.KapiOlculmedi },
        { "sentetik", "gecti", false, GateReasons.KapiOlculmedi },
        { "sentetik", "kaldi", false, GateReasons.KapiOlculmedi },
        { "silver", "kaldi", false, GateReasons.KapiGecmedi },
        { "altin", "kaldi", false, GateReasons.KapiGecmedi },
        { "silver", "gecti", true, null },
        { "altin", "gecti", true, null },
    };

    [Theory]
    [MemberData(nameof(GateStates))]
    public void P07_automatic_candidate_by_gate_state_under_invariant_culture(string? setClass, string? result, bool publicIn, string? reason) =>
        CultureScope.Invariant(() => AssertGateState(setClass, result, publicIn, reason));

    [Theory]
    [MemberData(nameof(GateStates))]
    public void P07_automatic_candidate_by_gate_state_under_turkish_culture(string? setClass, string? result, bool publicIn, string? reason) =>
        CultureScope.Turkish(() => AssertGateState(setClass, result, publicIn, reason));

    private static void AssertGateState(string? setClass, string? result, bool publicIn, string? reason)
    {
        foreach (XrefType type in AutoGateTypes)
        {
            GateMeasurement[] gates = setClass is null ? [] : [Gate(type, setClass, result!)];
            GateXref candidate = Xref(type, XrefStatus.Aday, 0.80, id: 1);
            GateXref approved = Xref(type, XrefStatus.Onayli, 0.80, id: 2);

            // dev ve internal: kapi satirindan bagimsiz, aday girer.
            foreach (BuildFlavor inner in new[] { BuildFlavor.Dev, BuildFlavor.Internal })
            {
                GateResult innerResult = GateEvaluator.Evaluate(inner, WithRegularSource(xrefs: [candidate, approved], gates: gates));
                Assert.True(innerResult.IsXrefIncluded(candidate.Id), $"{inner} {type.ToLabel()}");
                Assert.True(innerResult.IsXrefIncluded(approved.Id));
            }

            GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [candidate, approved], gates: gates));
            Assert.Equal(publicIn, publicResult.IsXrefIncluded(candidate.Id));
            Assert.True(publicResult.IsXrefIncluded(approved.Id), "onayli satir her derlemeye girer");
            if (!publicIn)
            {
                XrefVerdict verdict = publicResult.XrefVerdicts[candidate.Id];
                Assert.Equal(GateRule.P07, verdict.Rule);
                Assert.Equal(reason, verdict.Reason);
                Assert.Contains(
                    publicResult.Report.Rows,
                    r => r.Kind == GateSubjectKind.Baglanti && r.Id == type.ToLabel() && r.Decision == GateDecision.Girmedi && r.Rule == GateRule.P07 && r.Reason == reason);
            }
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_gate_is_per_type_and_does_not_touch_human_or_semantic_types(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Yalniz kok kapisi acik: lemma ve benzer_ayet kapali kalir.
        GateXref kok = Xref(XrefType.Kok, XrefStatus.Aday, 0.80, id: 1);
        GateXref lemma = Xref(XrefType.Lemma, XrefStatus.Aday, 0.80, id: 2);
        GateXref similar = Xref(XrefType.BenzerAyet, XrefStatus.Aday, 0.80, id: 3);
        GateResult result = GateEvaluator.Evaluate(
            BuildFlavor.Public,
            WithRegularSource(xrefs: [kok, lemma, similar], gates: [Gate(XrefType.Kok, "silver", "gecti")]));

        Assert.True(result.IsXrefIncluded(kok.Id));
        Assert.False(result.IsXrefIncluded(lemma.Id));
        Assert.False(result.IsXrefIncluded(similar.Id));

        // Acik kapi insan onayi isteyen turun adayini ve anlamsali public'e sokmaz.
        GateXref atif = Xref(XrefType.Atif, XrefStatus.Aday, 0.99, id: 4);
        GateXref anlamsal = Xref(XrefType.Anlamsal, XrefStatus.Onayli, 0.99, id: 5);
        GateMeasurement[] open = [.. OpenGates(), Gate(XrefType.Atif, "silver", "gecti"), Gate(XrefType.Anlamsal, "silver", "gecti")];
        GateResult human = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [atif, anlamsal], gates: open));
        Assert.Equal(GateReasons.AdayPublic, human.XrefVerdicts[atif.Id].Reason);
        Assert.Equal(GateReasons.AnlamsalPublic, human.XrefVerdicts[anlamsal.Id].Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_open_gate_keeps_confidence_open_review_and_lexicon_rules(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref low = Xref(XrefType.Kok, XrefStatus.Aday, 0.40, id: 1);
        GateXref review = Xref(XrefType.Kok, XrefStatus.Aday, 0.90, openReview: true, id: 2);
        GateXref lexicon = Xref(XrefType.Lemma, XrefStatus.Aday, 0.90, lexiconApproved: false, id: 3);
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [low, review, lexicon], gates: OpenGates()));

        Assert.Equal(GateReasons.DusukGuven, result.XrefVerdicts[low.Id].Reason);
        Assert.Equal(GateReasons.AcikInceleme, result.XrefVerdicts[review.Id].Reason);
        Assert.Equal(GateReasons.SozlukOnaysiz, result.XrefVerdicts[lexicon.Id].Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Report_writes_a_gate_row_per_automatic_type_with_class_and_result(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(
            xrefs: [Xref(XrefType.Kok, XrefStatus.Aday, id: 1), Xref(XrefType.Lemma, XrefStatus.Aday, id: 2), Xref(XrefType.BenzerAyet, XrefStatus.Aday, id: 3)],
            gates: [Gate(XrefType.Kok, "silver", "gecti"), Gate(XrefType.Lemma, "altin", "kaldi")]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        GateReportRow kok = Row(result, GateSubjectKind.Kapi, "kok");
        Assert.Equal(GateDecision.Girdi, kok.Decision);
        Assert.Equal("silver-ile-olculdu", kok.Reason);
        Assert.Null(kok.Rule);
        GateReportRow lemma = Row(result, GateSubjectKind.Kapi, "lemma");
        Assert.Equal(GateDecision.Girmedi, lemma.Decision);
        Assert.Equal(GateRule.P07, lemma.Rule);
        Assert.Equal("kapi-gecmedi:altin", lemma.Reason);
        GateReportRow similar = Row(result, GateSubjectKind.Kapi, "benzer_ayet");
        Assert.Equal(GateDecision.Girmedi, similar.Decision);
        Assert.Equal(GateReasons.KapiOlculmedi, similar.Reason);

        // Kapi satiri olmayan girdide (kapi turunde baglanti ve olcum yok) kapi satiri yazilmaz.
        GateResult none = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [Xref(XrefType.Atif, XrefStatus.Onayli)]));
        Assert.DoesNotContain(none.Report.Rows, r => r.Kind == GateSubjectKind.Kapi);
        Assert.Equal("kapi", GateSubjectKind.Kapi.ToLabel());
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Report_counts_candidate_rows_left_out_by_the_gate_and_by_human_approval_requirement(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(xrefs:
        [
            Xref(XrefType.Kok, XrefStatus.Aday, id: 1),
            Xref(XrefType.Kok, XrefStatus.Aday, id: 2),
            Xref(XrefType.Kok, XrefStatus.Onayli, id: 3),
            Xref(XrefType.Atif, XrefStatus.Aday, id: 4),
        ]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Id == "kok" && r.Decision == GateDecision.Girmedi && r.Reason == GateReasons.KapiOlculmedi && r.Count == 2);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Id == "kok" && r.Decision == GateDecision.Girdi && r.Reason == GateReasons.Uygun && r.Count == 1);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Id == "atif" && r.Decision == GateDecision.Girmedi && r.Reason == GateReasons.AdayPublic && r.Count == 1);
    });

    // ---- P-07: uc ozeti ----

    private static GateInput WithHashedUnits(GateXref xref, string? srcUnitHash, string? dstUnitHash, params GateUnit[] more) =>
        new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("q:1:1", hash: srcUnitHash), Unit("q:1:2", hash: dstUnitHash), .. more],
            Xrefs = [xref],
            Gates = OpenGates(),
        };

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_end_hash_mismatch_keeps_the_row_out_in_every_flavor_and_status(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            foreach (XrefStatus status in new[] { XrefStatus.Onayli, XrefStatus.Aday })
            {
                GateXref srcBad = Xref(XrefType.BenzerAyet, status, 0.9) with { SrcHash = HashA, DstHash = HashB };
                GateResult src = GateEvaluator.Evaluate(flavor, WithHashedUnits(srcBad, HashB, HashB));
                AssertHashRejected(src, srcBad.Id);

                GateXref dstBad = Xref(XrefType.BenzerAyet, status, 0.9) with { SrcHash = HashA, DstHash = HashA };
                GateResult dst = GateEvaluator.Evaluate(flavor, WithHashedUnits(dstBad, HashA, HashB));
                AssertHashRejected(dst, dstBad.Id);
            }
        }
    });

    private static void AssertHashRejected(GateResult result, Guid id)
    {
        XrefVerdict verdict = result.XrefVerdicts[id];
        Assert.False(verdict.Included);
        Assert.Equal(GateRule.P07, verdict.Rule);
        Assert.Equal(GateReasons.UcOzetiTutmadi, verdict.Reason);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Rule == GateRule.P07 && r.Reason == GateReasons.UcOzetiTutmadi);
        Assert.False(result.Rejected);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_matching_hashes_missing_fields_and_ends_without_a_unit_row_are_not_affected(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Ozetler tutuyor (xref ozeti 40 hane olsa da ilk 16 hane karsilastirilir; buyuk-kucuk harf gozetilmez).
        GateXref match = Xref(XrefType.BenzerAyet, XrefStatus.Onayli, 0.9, id: 1) with { SrcHash = HashA + "ffff", DstHash = HashB.ToUpperInvariant() };
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, WithHashedUnits(match, HashA, HashB)).IsXrefIncluded(match.Id));

        // Xref'te ozet alani yok (editor satiri): denetlenmez.
        GateXref noFields = Xref(XrefType.BenzerAyet, XrefStatus.Onayli, 0.9, id: 2);
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, WithHashedUnits(noFields, HashA, HashB)).IsXrefIncluded(noFields.Id));

        // Birimin ozeti yok (girdide HashPrefix null): denetlenmez.
        GateXref unitNoHash = Xref(XrefType.BenzerAyet, XrefStatus.Onayli, 0.9, id: 3) with { SrcHash = HashA, DstHash = HashB };
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, WithHashedUnits(unitNoHash, null, null)).IsXrefIncluded(unitNoHash.Id));

        // Ucun birim satiri yok (konu:): denetlenmez; baska uc tutuyorsa girer.
        GateXref topic = Xref(XrefType.Atif, XrefStatus.Onayli, 0.9, id: 4) with { DstAnchor = "konu:tevhid", SrcHash = HashA, DstHash = HashB };
        GateInput topicInput = new() { Sources = [Src(Regular)], Units = [Unit("q:1:1", hash: HashA)], Xrefs = [topic] };
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, topicInput).IsXrefIncluded(topic.Id));

        // Kelime ucu birim duzeyine inilerek denetlenir.
        GateXref word = Xref(XrefType.Kok, XrefStatus.Onayli, 0.9, id: 5) with { SrcAnchor = "q:1:1:2", SrcHash = HashB, DstHash = HashB };
        AssertHashRejected(GateEvaluator.Evaluate(BuildFlavor.Dev, WithHashedUnits(word, HashA, HashB)), word.Id);
    });

    // ---- P-09: Turkce lemma ----

    private static GateLexical Lemma(int id, XrefStatus status, string? onayYolu, bool kanit = true) =>
        new(LexicalKind.TrLemma, id.ToString(System.Globalization.CultureInfo.InvariantCulture), status, false, LemmaId: id, OnayYolu: onayYolu, HasKanit: kanit);

    private static GateLexical RootIndex(int lemmaId, string unit = "meal:test:1:1", string? unitHash = HashA, int start = 0) =>
        new(LexicalKind.TrRootIndex, unit + "|" + start.ToString(System.Globalization.CultureInfo.InvariantCulture), null, true, LemmaId: lemmaId, UnitAnchor: unit, UnitHash: unitHash);

    private static GateLexical Form(int lemmaId, string key = "forma") =>
        new(LexicalKind.TrForm, key + "|" + lemmaId.ToString(System.Globalization.CultureInfo.InvariantCulture), null, true, LemmaId: lemmaId);

    private static GateInput LexicalInput(GateLexical[] lexicals, GateMeasurement[]? gates = null, TextStatus unitStatus = TextStatus.Onayli, string? unitHash = HashA) =>
        new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("meal:test:1:1", status: unitStatus, hash: unitHash)],
            Lexicals = lexicals,
            Gates = gates ?? [],
        };

    // onay yolu, kanit var mi, kapi satiri (sinif, sonuc), publicIn, devIn, girmeyen public hucrenin gerekcesi
    public static TheoryData<string, bool, string?, string?, bool, bool, string?> LemmaCells() => new()
    {
        { "editor", true, null, null, true, true, null },
        { "editor", false, null, null, true, true, null },
        { "otomatik", true, null, null, false, true, GateReasons.KapiOlculmedi },
        { "otomatik", true, "sentetik", "gecti", false, true, GateReasons.KapiOlculmedi },
        { "otomatik", true, "silver", "kaldi", false, true, GateReasons.KapiGecmedi },
        { "otomatik", true, "altin", "kaldi", false, true, GateReasons.KapiGecmedi },
        { "otomatik", true, "silver", "gecti", true, true, null },
        { "otomatik", true, "altin", "gecti", true, true, null },
        { "otomatik", false, "silver", "gecti", false, false, GateReasons.KanitsizOtomatikOnay },
        { "otomatik", false, null, null, false, false, GateReasons.KanitsizOtomatikOnay },
    };

    [Theory]
    [MemberData(nameof(LemmaCells))]
    public void P09_turkish_lemma_matrix_under_invariant_culture(string path, bool kanit, string? setClass, string? result, bool publicIn, bool devIn, string? reason) =>
        CultureScope.Invariant(() => AssertLemmaCell(path, kanit, setClass, result, publicIn, devIn, reason));

    [Theory]
    [MemberData(nameof(LemmaCells))]
    public void P09_turkish_lemma_matrix_under_turkish_culture(string path, bool kanit, string? setClass, string? result, bool publicIn, bool devIn, string? reason) =>
        CultureScope.Turkish(() => AssertLemmaCell(path, kanit, setClass, result, publicIn, devIn, reason));

    private static void AssertLemmaCell(string path, bool kanit, string? setClass, string? result, bool publicIn, bool devIn, string? reason)
    {
        GateMeasurement[] gates = setClass is null ? [] : [Gate(XrefType.Kok, setClass, result!)];
        // Bagli tr_root_index ve tr_form lemmanin kararini izler (kapi ve kanit gerekceleri satira tasinir).
        GateLexical[] lexicals = [Lemma(1, XrefStatus.Onayli, path, kanit), RootIndex(1), Form(1)];

        foreach ((BuildFlavor flavor, bool expected) in new[] { (BuildFlavor.Dev, devIn), (BuildFlavor.Internal, devIn), (BuildFlavor.Public, publicIn) })
        {
            GateResult r = GateEvaluator.Evaluate(flavor, LexicalInput(lexicals, gates));

            Assert.Equal(expected, r.IncludedLexicals.Contains("lemma_tr:1"));
            Assert.Equal(expected, r.IncludedLexicals.Contains("tr_root_index:meal:test:1:1|0"));
            Assert.Equal(expected, r.IncludedLexicals.Contains("tr_form:forma|1"));
            Assert.False(r.Rejected);
            if (!expected)
            {
                foreach (string label in new[] { "lemma_tr", "tr_root_index", "tr_form" })
                {
                    Assert.Contains(r.Report.Rows, row => row.Kind == GateSubjectKind.Sozluk && row.Id == label && row.Decision == GateDecision.Girmedi && row.Rule == GateRule.P09 && row.Reason == reason);
                }
            }
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_turkish_lemma_uses_the_kok_gate_not_the_lemma_gate_and_reports_the_approval_path(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateLexical[] lexicals = [Lemma(1, XrefStatus.Onayli, "otomatik"), Lemma(2, XrefStatus.Onayli, "editor")];

        GateResult lemmaGateOnly = GateEvaluator.Evaluate(BuildFlavor.Public, LexicalInput(lexicals, [Gate(XrefType.Lemma, "silver", "gecti")]));
        Assert.DoesNotContain("lemma_tr:1", lemmaGateOnly.IncludedLexicals);
        Assert.Contains("lemma_tr:2", lemmaGateOnly.IncludedLexicals);

        GateResult kokGate = GateEvaluator.Evaluate(BuildFlavor.Public, LexicalInput(lexicals, [Gate(XrefType.Kok, "silver", "gecti")]));
        Assert.Contains("lemma_tr:1", kokGate.IncludedLexicals);
        Assert.Contains(kokGate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lemma_tr" && r.Reason == GateReasons.OtomatikOnay && r.Count == 1);
        Assert.Contains(kokGate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lemma_tr" && r.Reason == GateReasons.Uygun && r.Count == 1);
        Assert.Equal("silver-ile-olculdu", Row(kokGate, GateSubjectKind.Kapi, "kok").Reason);

        // Otomatik lemma kapi satirini xref olmasa da gerektirir: public'te kok kapi satiri "olculmedi" yazilir.
        GateResult none = GateEvaluator.Evaluate(BuildFlavor.Public, LexicalInput(lexicals));
        Assert.Equal(GateReasons.KapiOlculmedi, Row(none, GateSubjectKind.Kapi, "kok").Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_turkish_lemma_that_is_not_approved_never_enters_and_blocks_its_rows(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateLexical[] lexicals =
        [
            Lemma(1, XrefStatus.Aday, null), Lemma(2, XrefStatus.Red, "editor"), Lemma(3, XrefStatus.Onayli, "bilinmeyen"),
            RootIndex(1, start: 0), RootIndex(2, start: 1), Form(1, "a"), Form(2, "b"),
        ];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, LexicalInput(lexicals));

            Assert.Empty(result.IncludedLexicals);
            Assert.Contains(result.Report.Rows, r => r.Id == "lemma_tr" && r.Reason == GateReasons.OnaysizSatir && r.Count == 2);
            Assert.Contains(result.Report.Rows, r => r.Id == "lemma_tr" && r.Reason == GateReasons.Red && r.Count == 1);
            Assert.Contains(result.Report.Rows, r => r.Id == "tr_root_index" && r.Reason == GateReasons.LemmaOnaysiz && r.Count == 2);
            Assert.Contains(result.Report.Rows, r => r.Id == "tr_form" && r.Reason == GateReasons.LemmaOnaysiz && r.Count == 2);
        }
    });

    // ---- P-09: tr_root_index ozeti ve birim kapsami ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_root_index_unit_hash_mismatch_is_blocked_with_ozet_tutmadi_in_every_flavor(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateLexical[] lexicals = [Lemma(1, XrefStatus.Onayli, "editor"), RootIndex(1, unitHash: HashA), RootIndex(1, unitHash: HashB, start: 5)];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, LexicalInput(lexicals, unitHash: HashA + "0000"));

            Assert.Contains("tr_root_index:meal:test:1:1|0", result.IncludedLexicals);
            Assert.DoesNotContain("tr_root_index:meal:test:1:1|5", result.IncludedLexicals);
            Assert.Contains(result.Report.Rows, r => r.Id == "tr_root_index" && r.Decision == GateDecision.Girmedi && r.Rule == GateRule.P09 && r.Reason == GateReasons.OzetTutmadi && r.Count == 1);
            Assert.False(result.Rejected);
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_root_index_unit_must_be_in_scope(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateLexical[] inScope = [Lemma(1, XrefStatus.Onayli, "editor"), RootIndex(1)];

        // Taslak meal birimi public kapsaminda degil (P-10): satir birim-girmedi ile disarida; dev'de girer.
        GateResult draftPublic = GateEvaluator.Evaluate(BuildFlavor.Public, LexicalInput(inScope, unitStatus: TextStatus.Taslak));
        Assert.DoesNotContain("tr_root_index:meal:test:1:1|0", draftPublic.IncludedLexicals);
        Assert.Contains(draftPublic.Report.Rows, r => r.Id == "tr_root_index" && r.Reason == GateReasons.BirimGirmedi && r.Rule == GateRule.P09);
        GateResult draftDev = GateEvaluator.Evaluate(BuildFlavor.Dev, LexicalInput(inScope, unitStatus: TextStatus.Taslak));
        Assert.Contains("tr_root_index:meal:test:1:1|0", draftDev.IncludedLexicals);

        // Birim satiri hic yok: kapsamda sayilmaz.
        GateLexical[] orphan = [Lemma(1, XrefStatus.Onayli, "editor"), RootIndex(1, unit: "meal:test:9:9")];
        GateResult missing = GateEvaluator.Evaluate(BuildFlavor.Dev, LexicalInput(orphan));
        Assert.DoesNotContain("tr_root_index:meal:test:9:9|0", missing.IncludedLexicals);
        Assert.Contains(missing.Report.Rows, r => r.Id == "tr_root_index" && r.Reason == GateReasons.BirimGirmedi);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_legacy_rows_without_lemma_id_keep_the_linked_approval_rule(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Lexicals =
            [
                new GateLexical(LexicalKind.TrRootIndex, "a|0", null, true),
                new GateLexical(LexicalKind.TrRootIndex, "b|0", null, false),
            ],
        };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Equal(["tr_root_index:a|0"], result.IncludedLexicals);
    });

    [Fact]
    public void Gate_report_json_is_deterministic_with_gate_rows()
    {
        GateInput input = WithRegularSource(
            xrefs: [Xref(XrefType.Kok, XrefStatus.Aday, id: 1), Xref(XrefType.BenzerAyet, XrefStatus.Aday, id: 2)],
            lexicals: [Lemma(1, XrefStatus.Onayli, "otomatik")],
            gates: [Gate(XrefType.Kok, "silver", "gecti")]);

        string a = GateEvaluator.Evaluate(BuildFlavor.Public, input).Report.ToJson();
        string b = GateEvaluator.Evaluate(BuildFlavor.Public, input).Report.ToJson();

        Assert.Equal(a, b);
        Assert.Contains("\"kind\":\"kapi\"", a, StringComparison.Ordinal);
    }
}
