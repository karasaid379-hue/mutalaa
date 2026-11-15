using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// K-51 madde 5 (kapi alt turu): benzer_ayet/sozluksel, benzer_ayet/alim (QurSim), kok/xref (P-07) ve kok/tr_lemma (P-09) ile lemma kapilari
/// birbirinden bagimsizdir. Sentetik veri; hicbir dini metin yoktur. Her test Invariant ve tr-TR kulturunde kosar.
/// </summary>
public class GateSubtypeTests
{
    private const string Qursim = "qursim";

    private static GateInput Input(GateXref[]? xrefs = null, GateLexical[]? lexicals = null, GateMeasurement[]? gates = null) =>
        new()
        {
            Sources = [Src(Regular), Src(Qursim)],
            Units = [Unit("meal:test:1:1", hash: "aaaaaaaaaaaaaaaa")],
            Xrefs = xrefs ?? [],
            Lexicals = lexicals ?? [],
            Gates = gates ?? [],
        };

    private static GateXref Similar(int id, string? sourceId = null, bool qursimEvidence = false, XrefStatus status = XrefStatus.Aday) =>
        Xref(XrefType.BenzerAyet, status, 0.80, id: id) with { EvidenceSourceId = sourceId, HasQursimEvidence = qursimEvidence };

    private static GateLexical AutoLemma(int id) =>
        new(LexicalKind.TrLemma, id.ToString(System.Globalization.CultureInfo.InvariantCulture), XrefStatus.Onayli, false, LemmaId: id, OnayYolu: GateReasons.OnayYoluOtomatik, HasKanit: true);

    // ---- kapi kimligi ve alt tur sozlesmesi ----

    [Fact]
    public void GateKeyOf_maps_each_link_type_and_evidence_to_its_subtype()
    {
        Assert.Equal(new GateKey(XrefType.Kok, "xref"), XrefGateRules.GateKeyOf(XrefType.Kok, null, false));
        Assert.Equal(new GateKey(XrefType.Lemma, string.Empty), XrefGateRules.GateKeyOf(XrefType.Lemma, null, false));
        Assert.Equal(new GateKey(XrefType.BenzerAyet, "sozluksel"), XrefGateRules.GateKeyOf(XrefType.BenzerAyet, null, false));
        Assert.Equal(new GateKey(XrefType.BenzerAyet, "sozluksel"), XrefGateRules.GateKeyOf(XrefType.BenzerAyet, "baska-kaynak", false));
        Assert.Equal(new GateKey(XrefType.BenzerAyet, "alim"), XrefGateRules.GateKeyOf(XrefType.BenzerAyet, "qursim", false));
        Assert.Equal(new GateKey(XrefType.BenzerAyet, "alim"), XrefGateRules.GateKeyOf(XrefType.BenzerAyet, null, true));
        Assert.Equal(new GateKey(XrefType.BenzerAyet, "sozluksel"), XrefGateRules.GateKeyOf(XrefType.BenzerAyet, "QURSIM", false));
        Assert.Equal(new GateKey(XrefType.Atif, string.Empty), XrefGateRules.GateKeyOf(XrefType.Atif, "qursim", true));

        Assert.Equal(["kok/xref", "kok/tr_lemma", "lemma", "benzer_ayet/sozluksel", "benzer_ayet/alim"], XrefGateRules.AllKeys.Select(k => k.Label));
    }

    [Theory]
    [InlineData(XrefType.BenzerAyet, "sozluksel", true)]
    [InlineData(XrefType.BenzerAyet, "alim", true)]
    [InlineData(XrefType.BenzerAyet, "", false)]
    [InlineData(XrefType.BenzerAyet, "xref", false)]
    [InlineData(XrefType.Kok, "tr_lemma", true)]
    [InlineData(XrefType.Kok, "xref", true)]
    [InlineData(XrefType.Kok, "", false)]
    [InlineData(XrefType.Kok, "alim", false)]
    [InlineData(XrefType.Lemma, "", true)]
    [InlineData(XrefType.Lemma, "tr_lemma", false)]
    [InlineData(XrefType.Atif, "", true)]
    [InlineData(XrefType.Iktibas, "alim", false)]
    public void IsValid_matches_the_database_check(XrefType type, string subtype, bool valid) =>
        Assert.Equal(valid, XrefGateSubtypes.IsValid(type, subtype));

    // ---- her alt tur icin acik / kapali / olculmedi ----

    // set sinifi, sonuc (null = satir yok), public'te girer mi, kapali kapinin gerekcesi
    public static TheoryData<string?, string?, bool, string?> States() => new()
    {
        { null, null, false, GateReasons.KapiOlculmedi },
        { "sentetik", "gecti", false, GateReasons.KapiOlculmedi },
        { "silver", "kaldi", false, GateReasons.KapiGecmedi },
        { "altin", "kaldi", false, GateReasons.KapiGecmedi },
        { "silver", "gecti", true, null },
        { "altin", "gecti", true, null },
    };

    [Theory]
    [MemberData(nameof(States))]
    public void Every_xref_subtype_gate_opens_closes_and_reports_by_its_own_measurement_in_invariant_culture(string? setClass, string? result, bool publicIn, string? reason) =>
        CultureScope.Invariant(() => AssertXrefSubtypes(setClass, result, publicIn, reason));

    [Theory]
    [MemberData(nameof(States))]
    public void Every_xref_subtype_gate_opens_closes_and_reports_by_its_own_measurement_in_turkish_culture(string? setClass, string? result, bool publicIn, string? reason) =>
        CultureScope.Turkish(() => AssertXrefSubtypes(setClass, result, publicIn, reason));

    private static void AssertXrefSubtypes(string? setClass, string? result, bool publicIn, string? reason)
    {
        // (kapi, bu kapiya bagli aday satir, kapinin olcum satiri)
        (GateKey Key, GateXref Candidate, GateMeasurement? Gate)[] cases =
        [
            (new GateKey(XrefType.Kok, "xref"), Xref(XrefType.Kok, XrefStatus.Aday, 0.80, id: 1), setClass is null ? null : Gate(XrefType.Kok, setClass, result!)),
            (new GateKey(XrefType.Lemma, string.Empty), Xref(XrefType.Lemma, XrefStatus.Aday, 0.80, id: 2), setClass is null ? null : Gate(XrefType.Lemma, setClass, result!)),
            (new GateKey(XrefType.BenzerAyet, "sozluksel"), Similar(3), setClass is null ? null : Gate(XrefType.BenzerAyet, setClass, result!)),
            (new GateKey(XrefType.BenzerAyet, "alim"), Similar(4, sourceId: Qursim), setClass is null ? null : AlimGate(setClass, result!)),
            (new GateKey(XrefType.BenzerAyet, "alim"), Similar(5, qursimEvidence: true), setClass is null ? null : AlimGate(setClass, result!)),
        ];

        foreach ((GateKey key, GateXref candidate, GateMeasurement? gate) in cases)
        {
            GateMeasurement[] gates = gate is null ? [] : [gate];

            foreach (BuildFlavor inner in new[] { BuildFlavor.Dev, BuildFlavor.Internal })
            {
                Assert.True(GateEvaluator.Evaluate(inner, Input([candidate], gates: gates)).IsXrefIncluded(candidate.Id), $"{inner} {key.Label}");
            }

            GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, Input([candidate], gates: gates));
            Assert.Equal(publicIn, publicResult.IsXrefIncluded(candidate.Id));
            if (!publicIn)
            {
                Assert.Equal(GateRule.P07, publicResult.XrefVerdicts[candidate.Id].Rule);
                Assert.Equal(reason, publicResult.XrefVerdicts[candidate.Id].Reason);
            }

            // Kapi satiri tur/alt_tur kimligiyle yazilir.
            GateReportRow row = Row(publicResult, GateSubjectKind.Kapi, key.Label);
            if (publicIn)
            {
                Assert.Equal(GateDecision.Girdi, row.Decision);
                Assert.Equal(setClass + "-ile-olculdu", row.Reason);
            }
            else
            {
                Assert.Equal(GateDecision.Girmedi, row.Decision);
                Assert.Equal(GateRule.P07, row.Rule);
                Assert.Equal(setClass is "silver" or "altin" ? reason + ":" + setClass : reason, row.Reason);
            }
        }
    }

    [Theory]
    [MemberData(nameof(States))]
    public void The_tr_lemma_gate_opens_automatic_turkish_lemma_rows_by_its_own_measurement(string? setClass, string? result, bool publicIn, string? reason) =>
        CultureScope.For(false, () =>
        {
            GateMeasurement[] gates = setClass is null ? [] : [TrLemmaGate(setClass, result!)];
            GateResult r = GateEvaluator.Evaluate(BuildFlavor.Public, Input(lexicals: [AutoLemma(1)], gates: gates));

            Assert.Equal(publicIn, r.IncludedLexicals.Contains("lemma_tr:1"));
            GateReportRow row = Row(r, GateSubjectKind.Kapi, "kok/tr_lemma");
            Assert.Equal(publicIn ? GateDecision.Girdi : GateDecision.Girmedi, row.Decision);
            if (!publicIn)
            {
                Assert.Contains(r.Report.Rows, x => x.Kind == GateSubjectKind.Sozluk && x.Id == "lemma_tr" && x.Rule == GateRule.P09 && x.Reason == reason);
            }

            // dev ve internal kapidan bagimsiz.
            foreach (BuildFlavor inner in new[] { BuildFlavor.Dev, BuildFlavor.Internal })
            {
                Assert.Contains("lemma_tr:1", GateEvaluator.Evaluate(inner, Input(lexicals: [AutoLemma(1)], gates: gates)).IncludedLexicals);
            }
        });

    // ---- kapilar birbirini etkilemez ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_kok_xref_gate_and_the_turkish_lemma_gate_do_not_affect_each_other(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref kok = Xref(XrefType.Kok, XrefStatus.Aday, 0.80, id: 1);
        GateLexical[] lemmas = [AutoLemma(1)];

        // Yalniz kok/xref acik: kok baglantisi girer, Turkce lemma girmez.
        GateResult xrefOnly = GateEvaluator.Evaluate(BuildFlavor.Public, Input([kok], lemmas, [Gate(XrefType.Kok, "silver", "gecti")]));
        Assert.True(xrefOnly.IsXrefIncluded(kok.Id));
        Assert.DoesNotContain("lemma_tr:1", xrefOnly.IncludedLexicals);
        Assert.Equal(GateReasons.KapiOlculmedi, Row(xrefOnly, GateSubjectKind.Kapi, "kok/tr_lemma").Reason);

        // Yalniz kok/tr_lemma acik: Turkce lemma girer, kok baglantisi girmez.
        GateResult lemmaOnly = GateEvaluator.Evaluate(BuildFlavor.Public, Input([kok], lemmas, [TrLemmaGate("silver", "gecti")]));
        Assert.False(lemmaOnly.IsXrefIncluded(kok.Id));
        Assert.Equal(GateReasons.KapiOlculmedi, lemmaOnly.XrefVerdicts[kok.Id].Reason);
        Assert.Contains("lemma_tr:1", lemmaOnly.IncludedLexicals);

        // kok/xref kaldi, kok/tr_lemma gecti: ikisi ayri yonde karar verir.
        GateResult split = GateEvaluator.Evaluate(BuildFlavor.Public, Input([kok], lemmas, [Gate(XrefType.Kok, "silver", "kaldi"), TrLemmaGate("silver", "gecti")]));
        Assert.Equal(GateReasons.KapiGecmedi, split.XrefVerdicts[kok.Id].Reason);
        Assert.Contains("lemma_tr:1", split.IncludedLexicals);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_alim_and_sozluksel_gates_do_not_affect_each_other_and_a_qursim_evidenced_row_always_takes_the_alim_gate(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref lexical = Similar(1);
        GateXref byEvidenceSource = Similar(2, sourceId: Qursim);
        GateXref byQursimObject = Similar(3, qursimEvidence: true);
        GateXref both = Similar(4, sourceId: Qursim, qursimEvidence: true);
        GateXref[] all = [lexical, byEvidenceSource, byQursimObject, both];

        // Yalniz alim acik: QurSim kanitli satirlar girer, sozluksel girmez (sozluksel olcum kaldi olsa bile alim satiri etkilenmez).
        GateResult alimOnly = GateEvaluator.Evaluate(BuildFlavor.Public, Input(all, gates: [AlimGate("silver", "gecti"), Gate(XrefType.BenzerAyet, "silver", "kaldi")]));
        Assert.False(alimOnly.IsXrefIncluded(lexical.Id));
        Assert.Equal(GateReasons.KapiGecmedi, alimOnly.XrefVerdicts[lexical.Id].Reason);
        Assert.True(alimOnly.IsXrefIncluded(byEvidenceSource.Id));
        Assert.True(alimOnly.IsXrefIncluded(byQursimObject.Id));
        Assert.True(alimOnly.IsXrefIncluded(both.Id));

        // Yalniz sozluksel acik: yalniz sozluksel satir girer; QurSim kanitli satir da alim kapisini bekler.
        GateResult lexicalOnly = GateEvaluator.Evaluate(BuildFlavor.Public, Input(all, gates: [Gate(XrefType.BenzerAyet, "silver", "gecti")]));
        Assert.True(lexicalOnly.IsXrefIncluded(lexical.Id));
        Assert.False(lexicalOnly.IsXrefIncluded(byEvidenceSource.Id));
        Assert.False(lexicalOnly.IsXrefIncluded(byQursimObject.Id));
        Assert.Equal(GateReasons.KapiOlculmedi, lexicalOnly.XrefVerdicts[byQursimObject.Id].Reason);

        // Onayli satir her derlemeye girer, kapidan bagimsiz.
        GateXref approvedAlim = Similar(5, sourceId: Qursim, status: XrefStatus.Onayli);
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Public, Input([approvedAlim])).IsXrefIncluded(approvedAlim.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_legacy_row_with_an_empty_subtype_no_longer_opens_kok_or_benzer_ayet_but_still_resolves_lemma(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref kok = Xref(XrefType.Kok, XrefStatus.Aday, 0.80, id: 1);
        GateXref similar = Similar(2);
        GateXref alim = Similar(3, sourceId: Qursim);
        GateXref lemma = Xref(XrefType.Lemma, XrefStatus.Aday, 0.80, id: 4);
        GateMeasurement[] legacy =
        [
            Gate(XrefType.Kok, "silver", "gecti", string.Empty),
            Gate(XrefType.BenzerAyet, "altin", "gecti", string.Empty),
            Gate(XrefType.Lemma, "altin", "gecti"),
        ];

        GateResult r = GateEvaluator.Evaluate(BuildFlavor.Public, Input([kok, similar, alim, lemma], [AutoLemma(1)], legacy));

        Assert.False(r.IsXrefIncluded(kok.Id));
        Assert.False(r.IsXrefIncluded(similar.Id));
        Assert.False(r.IsXrefIncluded(alim.Id));
        Assert.Equal(GateReasons.KapiOlculmedi, r.XrefVerdicts[kok.Id].Reason);
        Assert.Equal(GateReasons.KapiOlculmedi, r.XrefVerdicts[similar.Id].Reason);
        Assert.DoesNotContain("lemma_tr:1", r.IncludedLexicals);
        Assert.True(r.IsXrefIncluded(lemma.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Resolve_is_per_key_gold_wins_over_silver_and_synthetic_never_opens(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateMeasurement[] all =
        [
            Gate(XrefType.BenzerAyet, "silver", "gecti"),
            AlimGate("altin", "kaldi"),
            AlimGate("sentetik", "gecti"),
            TrLemmaGate("sentetik", "gecti"),
            TrLemmaGate("silver", "kaldi"),
        ];

        Assert.True(XrefGateRules.Resolve(all, new GateKey(XrefType.BenzerAyet, "sozluksel")).Opens);
        XrefTypeGate alim = XrefGateRules.Resolve(all, new GateKey(XrefType.BenzerAyet, "alim"));
        Assert.Equal(XrefGateStatus.Failed, alim.Status);
        Assert.Equal("altin", alim.SetClass);
        Assert.Equal(XrefGateStatus.Failed, XrefGateRules.Resolve(all, XrefGateRules.TrLemmaKey).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve(all, new GateKey(XrefType.Kok, "xref")).Status);
        Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve(all, new GateKey(XrefType.Lemma, string.Empty)).Status);

        // Yalniz sentetik: hicbir kapiyi acmaz.
        GateMeasurement[] synthetic = [.. XrefGateRules.AllKeys.Select(k => new GateMeasurement(k.Type, "sentetik", "gecti", k.SubType))];
        foreach (GateKey key in XrefGateRules.AllKeys)
        {
            Assert.Equal(XrefGateStatus.NotMeasured, XrefGateRules.Resolve(synthetic, key).Status);
        }
    });

    [Fact]
    public void The_gate_report_with_subtypes_is_deterministic_and_names_the_subtype_in_each_gate_row()
    {
        GateInput input = Input(
            [Xref(XrefType.Kok, XrefStatus.Aday, id: 1), Similar(2), Similar(3, sourceId: Qursim)],
            [AutoLemma(1)],
            [Gate(XrefType.Kok, "silver", "gecti"), AlimGate("altin", "gecti")]);

        GateResult a = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        GateResult b = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Equal(a.Report.ToJson(), b.Report.ToJson());
        Assert.Equal(
            ["benzer_ayet/alim", "benzer_ayet/sozluksel", "kok/tr_lemma", "kok/xref"],
            a.Report.Rows.Where(r => r.Kind == GateSubjectKind.Kapi).Select(r => r.Id).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(a.Report.Rows, r => r.Kind == GateSubjectKind.Kapi && (r.Id is "kok" or "benzer_ayet"));
    }
}
