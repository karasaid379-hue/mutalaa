using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// P-01 ve P-07...P-14: her kural icin en az bir olumlu ve bir olumsuz test. Her test Invariant ve tr-TR kulturunde kosar
/// (InlineData(false), InlineData(true)). Test adi kurali belli eder.
/// </summary>
public class GateRuleTests
{
    // ---- Kural kodlari ----

    [Fact]
    public void Rule_codes_round_trip_and_skip_P02_to_P06()
    {
        GateRule[] all = Enum.GetValues<GateRule>();
        Assert.Equal(9, all.Length);

        foreach (GateRule rule in all)
        {
            string code = rule.ToCode();
            Assert.True(GateRuleCodes.TryParse(code, out GateRule parsed));
            Assert.Equal(rule, parsed);
        }

        foreach (string missing in new[] { "P-02", "P-03", "P-04", "P-05", "P-06", "P-15", "P-00", "p-01", "P-1", "P01", " P-01", "P-01 ", string.Empty })
        {
            Assert.False(GateRuleCodes.TryParse(missing, out _), missing);
        }

        Assert.False(GateRuleCodes.TryParse(null, out _));
        Assert.Equal("P-01", GateRule.P01.ToCode());
        Assert.Equal("P-14", GateRule.P14.ToCode());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((GateRule)2).ToCode());
    }

    // ---- P-01 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P01_unregistered_source_rejects_release(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new() { Sources = [Src("kaynaksiz", registered: false)], Units = [Unit("k:kaynaksiz:bolum-1:p1", source: "kaynaksiz")] };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.True(result.Rejected);
        GateViolation violation = Assert.Single(result.Report.Violations);
        Assert.Equal(GateRule.P01, violation.Rule);
        Assert.Equal("kaynaksiz", violation.Subject);
        Assert.Empty(result.IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P01_registered_source_with_attribution_passes(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(units: [Unit("q:1:1")]));

        Assert.False(result.Rejected);
        Assert.Contains("q:1:1", result.IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P01_empty_attribution_text_rejects_release(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new() { Sources = [Src("atifsiz", attribution: " \t")], Units = [Unit("k:atifsiz:bolum-1:p1", source: "atifsiz")] };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Internal, input);

        Assert.True(result.Rejected);
        Assert.Equal(GateReasons.AtifMetniBos, Assert.Single(result.Report.Violations).Reason);
        Assert.Empty(result.IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P01_unit_with_source_missing_from_input_rejects_release(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new() { Sources = [Src(Regular)], Units = [Unit("k:yok:bolum-1:p1", source: "yok")] };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.True(result.Rejected);
        Assert.Equal("yok", Assert.Single(result.Report.Violations).Subject);
        Assert.DoesNotContain("k:yok:bolum-1:p1", result.IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P01_pack_content_without_any_source_rejects_release(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new() { Sources = [Src(Regular)], Packs = [Pack("core", [])] };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.True(result.Rejected);
        GateViolation violation = Assert.Single(result.Report.Violations);
        Assert.Equal(GateRule.P01, violation.Rule);
        Assert.Equal("core", violation.Subject);
        Assert.Empty(result.IncludedPacks);
    });

    // ---- P-07 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_approved_human_xref_enters_public(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = Xref(XrefType.Atif, XrefStatus.Onayli);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [xref]));

        Assert.True(result.IsXrefIncluded(xref.Id));
        Assert.True(result.XrefVerdicts[xref.Id].Approved);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_candidate_human_xref_blocked_in_public_but_enters_internal(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = Xref(XrefType.Iktibas, XrefStatus.Aday);

        XrefVerdict publicVerdict = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [xref])).XrefVerdicts[xref.Id];
        XrefVerdict internalVerdict = GateEvaluator.Evaluate(BuildFlavor.Internal, WithRegularSource(xrefs: [xref])).XrefVerdicts[xref.Id];

        Assert.False(publicVerdict.Included);
        Assert.Equal(GateRule.P07, publicVerdict.Rule);
        Assert.Equal(GateReasons.AdayPublic, publicVerdict.Reason);
        Assert.True(internalVerdict.Included);
        Assert.False(internalVerdict.Approved);
    });

    [Theory]
    [InlineData(false, BuildFlavor.Dev)]
    [InlineData(false, BuildFlavor.Internal)]
    [InlineData(false, BuildFlavor.Public)]
    [InlineData(true, BuildFlavor.Dev)]
    [InlineData(true, BuildFlavor.Internal)]
    [InlineData(true, BuildFlavor.Public)]
    public void P07_red_xref_never_enters_any_flavor(bool turkish, BuildFlavor flavor) => CultureScope.For(turkish, () =>
    {
        foreach (XrefType type in Enum.GetValues<XrefType>())
        {
            GateXref xref = Xref(type, XrefStatus.Red, 0.99);
            XrefVerdict verdict = GateEvaluator.Evaluate(flavor, WithRegularSource(xrefs: [xref])).XrefVerdicts[xref.Id];

            Assert.False(verdict.Included);
            Assert.Equal(GateReasons.Red, verdict.Reason);
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_automatic_xref_at_threshold_enters_and_below_is_blocked(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref atThreshold = Xref(XrefType.Kok, XrefStatus.Aday, XrefTypeClass.ConfidenceMin, id: 1);
        GateXref below = Xref(XrefType.Kok, XrefStatus.Aday, 0.4999, id: 2);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [atThreshold, below]));

        Assert.True(result.IsXrefIncluded(atThreshold.Id));
        Assert.False(result.IsXrefIncluded(below.Id));
        Assert.Equal(GateReasons.DusukGuven, result.XrefVerdicts[below.Id].Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_xref_with_source_work_not_visible_is_blocked(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Kaynak eser test-kucuk: public'te gorunmez.
        GateXref xref = Xref(XrefType.Atif, XrefStatus.Onayli, src: "test-kucuk");
        GateInput input = new() { Sources = [Src(Regular), Src("test-kucuk")], Xrefs = [xref] };

        XrefVerdict publicVerdict = GateEvaluator.Evaluate(BuildFlavor.Public, input).XrefVerdicts[xref.Id];
        XrefVerdict internalVerdict = GateEvaluator.Evaluate(BuildFlavor.Internal, input).XrefVerdicts[xref.Id];

        Assert.False(publicVerdict.Included);
        Assert.Equal(GateReasons.KaynakEserGorunmez, publicVerdict.Reason);
        Assert.True(internalVerdict.Included);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_xref_with_destination_work_not_visible_is_blocked_unless_separate_index(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref blocked = Xref(XrefType.Atif, XrefStatus.Onayli, dst: "test-tefsir-ornek", id: 1);
        GateXref separate = Xref(XrefType.Atif, XrefStatus.Onayli, dst: "risale-atif-dizini", separateIndex: true, id: 2);
        GateInput input = new() { Sources = [Src(Regular), Src("test-tefsir-ornek")], Xrefs = [blocked, separate] };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.False(result.IsXrefIncluded(blocked.Id));
        Assert.Equal(GateReasons.HedefEserGorunmez, result.XrefVerdicts[blocked.Id].Reason);
        Assert.True(result.IsXrefIncluded(separate.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_public_open_review_blocks_but_internal_ignores_it(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref xref = Xref(XrefType.Atif, XrefStatus.Onayli, openReview: true);

        XrefVerdict publicVerdict = GateEvaluator.Evaluate(BuildFlavor.Public, WithRegularSource(xrefs: [xref])).XrefVerdicts[xref.Id];
        XrefVerdict devVerdict = GateEvaluator.Evaluate(BuildFlavor.Dev, WithRegularSource(xrefs: [xref])).XrefVerdicts[xref.Id];

        Assert.False(publicVerdict.Included);
        Assert.Equal(GateReasons.AcikInceleme, publicVerdict.Reason);
        Assert.True(devVerdict.Included);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_public_kok_and_lemma_need_approved_lexicon_entry(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref kokNo = Xref(XrefType.Kok, XrefStatus.Aday, 0.9, lexiconApproved: false, id: 1);
        GateXref lemmaNo = Xref(XrefType.Lemma, XrefStatus.Onayli, 0.9, lexiconApproved: false, id: 2);
        GateXref kokYes = Xref(XrefType.Kok, XrefStatus.Aday, 0.9, lexiconApproved: true, id: 3);
        GateXref similarNo = Xref(XrefType.BenzerAyet, XrefStatus.Aday, 0.9, lexiconApproved: false, id: 4);

        GateInput input = WithRegularSource(xrefs: [kokNo, lemmaNo, kokYes, similarNo]);
        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        GateResult internalResult = GateEvaluator.Evaluate(BuildFlavor.Internal, input);

        Assert.False(publicResult.IsXrefIncluded(kokNo.Id));
        Assert.False(publicResult.IsXrefIncluded(lemmaNo.Id));
        Assert.Equal(GateReasons.SozlukOnaysiz, publicResult.XrefVerdicts[kokNo.Id].Reason);
        Assert.True(publicResult.IsXrefIncluded(kokYes.Id));
        Assert.True(publicResult.IsXrefIncluded(similarNo.Id));
        Assert.True(internalResult.IsXrefIncluded(kokNo.Id));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P07_unknown_status_or_type_and_missing_confidence_fail_closed(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateXref unknownStatus = Xref(XrefType.Atif, (XrefStatus)9, id: 1);
        GateXref unknownType = Xref((XrefType)99, XrefStatus.Onayli, id: 2);
        GateXref nan = Xref(XrefType.Kok, XrefStatus.Aday, double.NaN, id: 3);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, WithRegularSource(xrefs: [unknownStatus, unknownType, nan]));

        Assert.False(result.IsXrefIncluded(unknownStatus.Id));
        Assert.False(result.IsXrefIncluded(unknownType.Id));
        Assert.False(result.IsXrefIncluded(nan.Id));
        Assert.Equal(GateReasons.TurBilinmiyor, result.XrefVerdicts[unknownType.Id].Reason);
        Assert.True(result.XrefVerdicts[nan.Id].Folded);
    });

    [Fact]
    public void P07_type_classes_partition_all_xref_types()
    {
        foreach (XrefType type in Enum.GetValues<XrefType>())
        {
            Assert.True(XrefTypeClass.RequiresHumanApproval(type) ^ XrefTypeClass.IsAutomatic(type), type.ToLabel());
        }

        Assert.Equal(Enum.GetValues<XrefType>().Length, XrefTypeClass.HumanApprovalTypes.Length + XrefTypeClass.AutomaticTypes.Length);
        Assert.Equal(0.50, XrefTypeClass.ConfidenceMin);
        Assert.Equal(0.70, XrefTypeClass.FoldBelow);
    }

    // ---- P-08 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P08_unapproved_ai_draft_blocked_in_public_and_marked_in_internal(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units: [Unit("q:1:1", status: TextStatus.Incelemede, aiDraft: true)]);

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        GateResult internalResult = GateEvaluator.Evaluate(BuildFlavor.Internal, input);

        Assert.Empty(publicResult.IncludedUnits);
        Assert.Equal(GateRule.P08, Single(publicResult, GateSubjectKind.Birim).Rule);
        Assert.Contains("q:1:1", internalResult.IncludedUnits);
        Assert.Equal(GateReasons.Dogrulanmamis, Single(internalResult, GateSubjectKind.Birim).Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P08_approved_ai_draft_is_a_normal_approved_unit(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units: [Unit("q:1:1", status: TextStatus.Onayli, aiDraft: true)]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Contains("q:1:1", result.IncludedUnits);
        Assert.Equal(GateReasons.Uygun, Single(result, GateSubjectKind.Birim).Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P08_takes_precedence_over_P10_for_ai_drafts(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units:
        [
            Unit("q:1:1", status: TextStatus.Taslak, aiDraft: true),
            Unit("q:1:2", status: TextStatus.Taslak, aiDraft: false),
        ]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Rule == GateRule.P08 && r.Count == 1);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Rule == GateRule.P10 && r.Count == 1);
    });

    // ---- P-09 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_only_approved_word_fixes_and_glosses_apply(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Lexicals =
            [
                new GateLexical(LexicalKind.QuranWordFix, "fix-ok", XrefStatus.Onayli, false),
                new GateLexical(LexicalKind.QuranWordFix, "fix-aday", XrefStatus.Aday, false),
                new GateLexical(LexicalKind.QuranWordFix, "fix-red", XrefStatus.Red, false),
                new GateLexical(LexicalKind.LemmaGloss, "gloss-ok", XrefStatus.Onayli, false),
                new GateLexical(LexicalKind.LemmaGloss, "gloss-aday", XrefStatus.Aday, false),
                new GateLexical(LexicalKind.LemmaGloss, "gloss-yok", null, false),
            ],
        };

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);

            Assert.Equal(["lemma_gloss:gloss-ok", "quran_word_fix:fix-ok"], result.IncludedLexicals.Order(StringComparer.Ordinal));
            Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Rule == GateRule.P09 && r.Id == "quran_word_fix" && r.Count == 2);
            Assert.False(result.Rejected);
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P09_root_index_and_form_apply_only_with_approved_lemma(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Lexicals =
            [
                new GateLexical(LexicalKind.TrRootIndex, "ri-ok", null, true),
                new GateLexical(LexicalKind.TrRootIndex, "ri-no", null, false),
                new GateLexical(LexicalKind.TrForm, "f-ok", null, true),
                new GateLexical(LexicalKind.TrForm, "f-no", null, false),
            ],
        };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.Equal(["tr_form:f-ok", "tr_root_index:ri-ok"], result.IncludedLexicals.Order(StringComparer.Ordinal));
        Assert.Contains(result.Report.Rows, r => r.Id == "tr_form" && r.Rule == GateRule.P09 && r.Reason == GateReasons.LemmaOnaysiz);
    });

    // ---- P-10 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P10_only_approved_units_enter_public(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units:
        [
            Unit("q:1:1", status: TextStatus.Onayli),
            Unit("q:1:2", status: TextStatus.Incelemede),
            Unit("q:1:3", status: TextStatus.Taslak),
        ]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Equal(["q:1:1"], result.IncludedUnits);
        GateReportRow blocked = Assert.Single(result.Report.Rows, r => r.Rule == GateRule.P10);
        Assert.Equal(2, blocked.Count);
        Assert.Equal(GateDecision.Girmedi, blocked.Decision);
        Assert.False(result.Rejected);
    });

    [Theory]
    [InlineData(false, BuildFlavor.Dev)]
    [InlineData(false, BuildFlavor.Internal)]
    [InlineData(true, BuildFlavor.Dev)]
    [InlineData(true, BuildFlavor.Internal)]
    public void P10_internal_flavors_admit_unapproved_units(bool turkish, BuildFlavor flavor) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units: [Unit("q:1:1", status: TextStatus.Taslak)]);

        GateResult result = GateEvaluator.Evaluate(flavor, input);

        Assert.Contains("q:1:1", result.IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Deprecated_unit_never_enters_any_flavor(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(units: [Unit("q:1:1", unitStatus: UnitStatus.KullanimDisi, hasSuccessors: true)]);

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);
            Assert.Empty(result.IncludedUnits);
            Assert.Null(Single(result, GateSubjectKind.Birim).Rule);
            Assert.Equal(GateReasons.KullanimDisi, Single(result, GateSubjectKind.Birim).Reason);
        }
    });

    // ---- P-11 (saf kisim) ----

    private const string HashA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private const string HashB = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P11_matching_content_hashes_pass(bool turkish) => CultureScope.For(turkish, () =>
    {
        Dictionary<string, string> raw = new(StringComparer.Ordinal) { ["q:1:1"] = HashA, ["q:1:2"] = HashB };
        Dictionary<string, string> units = new(StringComparer.Ordinal) { ["q:1:2"] = HashB, ["q:1:1"] = HashA };

        Assert.Empty(GateEvaluator.VerifyP11ContentHashes(raw, units));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P11_hash_mismatch_missing_unit_and_extra_unit_are_violations(bool turkish) => CultureScope.For(turkish, () =>
    {
        Dictionary<string, string> raw = new(StringComparer.Ordinal) { ["q:1:1"] = HashA, ["q:1:2"] = HashB, ["q:1:3"] = HashA };
        Dictionary<string, string> units = new(StringComparer.Ordinal) { ["q:1:1"] = HashB, ["q:1:2"] = HashB, ["q:1:9"] = HashA };

        IReadOnlyList<GateViolation> violations = GateEvaluator.VerifyP11ContentHashes(raw, units);

        Assert.Equal(
            [
                new GateViolation(GateRule.P11, "q:1:1", "hash-uyusmuyor"),
                new GateViolation(GateRule.P11, "q:1:3", "birim-yok"),
                new GateViolation(GateRule.P11, "q:1:9", "ham-dosyada-yok"),
            ],
            violations);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P11_attribution_must_match_source_row_exactly(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Empty(GateEvaluator.VerifyP11Attribution("s", "Atif", "https://example.invalid/a", "Atif", "https://example.invalid/a"));
        Assert.Empty(GateEvaluator.VerifyP11Attribution("s", "Atif", null, "Atif", null));

        IReadOnlyList<GateViolation> text = GateEvaluator.VerifyP11Attribution("s", "Atif", null, "atif", null);
        IReadOnlyList<GateViolation> url = GateEvaluator.VerifyP11Attribution("s", "Atif", "https://example.invalid/a", "Atif", null);
        IReadOnlyList<GateViolation> trailing = GateEvaluator.VerifyP11Attribution("s", "Atif", null, "Atif ", null);

        Assert.Equal("atif-metni-uyusmuyor", Assert.Single(text).Reason);
        Assert.Equal("atif-url-uyusmuyor", Assert.Single(url).Reason);
        Assert.Single(trailing);
        Assert.All(text.Concat(url), v => Assert.Equal(GateRule.P11, v.Rule));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P11_notice_must_match_raw_block_byte_for_byte(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Empty(GateEvaluator.VerifyP11Notice("s", "Bildirim\n", "Bildirim\n"));
        Assert.Single(GateEvaluator.VerifyP11Notice("s", "Bildirim\n", "Bildirim"));
        Assert.Single(GateEvaluator.VerifyP11Notice("s", "Bildirim", "bildirim"));
        Assert.Single(GateEvaluator.VerifyP11Notice("s", null, "Bildirim"));
    });

    // ---- P-12 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P12_test_prefix_blocked_in_public(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (string slug in new[] { "test-kucuk", "test-ses", "test-tefsir-ornek", "test-baska" })
        {
            Assert.False(FlavorPolicy.AllowsSource(BuildFlavor.Public, slug), slug);
        }

        GateInput input = new() { Sources = [Src("test-kucuk")], Units = [Unit("k:test-kucuk:bolum-1:p1", source: "test-kucuk")] };
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Empty(result.IncludedSources);
        Assert.Empty(result.IncludedUnits);
        Assert.Equal(GateRule.P12, Row(result, GateSubjectKind.Kaynak, "test-kucuk").Rule);
        Assert.Equal(GateRule.P12, Single(result, GateSubjectKind.Birim).Rule);
        Assert.False(result.Rejected);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P12_internal_admits_only_end_to_end_fixtures(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.True(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "test-kucuk"));
        Assert.True(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "test-ses"));
        Assert.False(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "test-tefsir-ornek"));
        Assert.False(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "test-baska"));
        Assert.False(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "TEST-KUCUK"));
        Assert.False(FlavorPolicy.AllowsSource(BuildFlavor.Internal, "test-kucuk-2"));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P12_dev_admits_all_test_sources_and_non_test_sources_are_unaffected(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (string slug in new[] { "test-kucuk", "test-ses", "test-tefsir-ornek", "test-baska" })
        {
            Assert.True(FlavorPolicy.AllowsSource(BuildFlavor.Dev, slug), slug);
        }

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            Assert.True(FlavorPolicy.AllowsSource(flavor, "tanzil-uthmani"));
            Assert.True(FlavorPolicy.AllowsSource(flavor, "testament"));
            Assert.True(FlavorPolicy.AllowsSource(flavor, "tefsir-elmalili"));
        }
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P12_prefix_check_is_culture_independent(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Turkce kulturde "TEST-" kucuk harfe cevrilirken I/i sorunu cikmasin: onek denetimi OrdinalIgnoreCase'dir.
        Assert.True(FlavorPolicy.IsTestSource("TEST-KUCUK"));
        Assert.True(FlavorPolicy.IsTestSource("Test-kucuk"));
        Assert.False(FlavorPolicy.IsTestSource("tes-kucuk"));
        Assert.False(FlavorPolicy.IsTestSource("atest-kucuk"));
    });

    // ---- P-13 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P13_acyclic_dependencies_within_manifest_pass(bool turkish) => CultureScope.For(turkish, () =>
    {
        GatePack[] packs =
        [
            Pack("core", [Regular]),
            Pack("kelime-kok", [Regular], ["core"]),
            Pack("tefsir-a", [Regular], ["core", "kelime-kok"]),
        ];

        Assert.Empty(GateEvaluator.EvaluateP13(packs, ["core", "kelime-kok", "tefsir-a"]));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P13_self_dependency_is_a_violation(bool turkish) => CultureScope.For(turkish, () =>
    {
        IReadOnlyList<GateViolation> violations = GateEvaluator.EvaluateP13([Pack("core", [Regular], ["core"])], ["core"]);

        Assert.Equal([new GateViolation(GateRule.P13, "core", "kendine-bagimlilik")], violations);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P13_cycle_is_a_violation(bool turkish) => CultureScope.For(turkish, () =>
    {
        GatePack[] packs = [Pack("a", [Regular], ["b"]), Pack("b", [Regular], ["c"]), Pack("c", [Regular], ["a"])];

        IReadOnlyList<GateViolation> violations = GateEvaluator.EvaluateP13(packs, ["a", "b", "c"]);

        GateViolation violation = Assert.Single(violations);
        Assert.Equal(GateRule.P13, violation.Rule);
        Assert.Equal("dongu:a>b>c>a", violation.Reason);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P13_dependency_missing_from_manifest_is_a_violation_but_carried_pack_satisfies_it(bool turkish) => CultureScope.For(turkish, () =>
    {
        GatePack[] packs = [Pack("tefsir-a", [Regular], ["core"])];

        Assert.Equal(
            [new GateViolation(GateRule.P13, "tefsir-a", "bagimlilik-manifestte-yok:core")],
            GateEvaluator.EvaluateP13(packs, ["tefsir-a"]));
        Assert.Empty(GateEvaluator.EvaluateP13(packs, ["tefsir-a", "core"]));

        // Evaluate: core onceki surumden tasindi (CarriedPackIds) -> sorun yok.
        GateInput carried = new() { Sources = [Src(Regular)], Packs = packs, CarriedPackIds = ["core"] };
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Dev, carried).Rejected);

        GateInput missing = new() { Sources = [Src(Regular)], Packs = packs };
        Assert.True(GateEvaluator.Evaluate(BuildFlavor.Dev, missing).Rejected);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P13_dependency_excluded_by_P12_leaves_dependent_without_manifest_entry(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Sources = [Src(Regular), Src("test-kucuk")],
            Packs = [Pack("test-kucuk", ["test-kucuk"]), Pack("tefsir-a", [Regular], ["test-kucuk"])],
        };

        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Internal, input).Rejected);

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        Assert.True(publicResult.Rejected);
        Assert.Equal(GateRule.P13, Assert.Single(publicResult.Report.Violations).Rule);
    });

    // ---- P-14 ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P14_equal_source_digests_pass(bool turkish) => CultureScope.For(turkish, () =>
    {
        Dictionary<string, string> internalDigests = new(StringComparer.Ordinal) { ["a"] = HashA, ["b"] = HashB, ["test-kucuk"] = HashA };
        Dictionary<string, string> publicDigests = new(StringComparer.Ordinal) { ["a"] = HashA, ["b"] = HashB };

        Assert.Empty(GateEvaluator.EvaluateP14(internalDigests, publicDigests));
        Assert.Empty(GateEvaluator.EvaluateP14(internalDigests, new Dictionary<string, string>()));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void P14_changed_or_missing_internal_digest_is_a_violation(bool turkish) => CultureScope.For(turkish, () =>
    {
        Dictionary<string, string> internalDigests = new(StringComparer.Ordinal) { ["a"] = HashA, ["b"] = HashB };
        Dictionary<string, string> publicDigests = new(StringComparer.Ordinal) { ["a"] = HashB, ["b"] = HashB, ["c"] = HashA };

        IReadOnlyList<GateViolation> violations = GateEvaluator.EvaluateP14(internalDigests, publicDigests);

        Assert.Equal(
            [
                new GateViolation(GateRule.P14, "a", "ozet-uyusmuyor"),
                new GateViolation(GateRule.P14, "c", "ic-kanalda-yok"),
            ],
            violations);
    });

    // ---- Capa sureklilik (kural kodu yok) ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Anchor_continuity_requires_previous_anchors_active_or_redirected(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Sources = [Src(Regular)],
            Units =
            [
                Unit("q:1:1"),
                Unit("q:1:2", unitStatus: UnitStatus.KullanimDisi, hasSuccessors: true),
                Unit("q:1:3", unitStatus: UnitStatus.KullanimDisi, hasSuccessors: false),
            ],
            PreviousAnchors = ["q:1:1", "q:1:2", "q:1:3", "q:1:4"],
        };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.True(result.Rejected);
        Assert.Equal(
            [
                new GateViolation(null, "q:1:3", GateReasons.CapaKayboldu + ":" + GateReasons.CapaYonlendirmesiz),
                new GateViolation(null, "q:1:4", GateReasons.CapaKayboldu + ":" + GateReasons.CapaSatirYok),
            ],
            result.Report.Violations);
    });

    // ---- Girdi hatalari ve derleme turu ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Duplicate_source_pack_or_xref_identifiers_are_input_errors(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Throws<ArgumentException>(() => GateEvaluator.Evaluate(BuildFlavor.Dev, new GateInput { Sources = [Src("a"), Src("a")] }));
        Assert.Throws<ArgumentException>(() => GateEvaluator.Evaluate(BuildFlavor.Dev, new GateInput { Packs = [Pack("p", ["a"]), Pack("p", ["a"])] }));
        Assert.Throws<ArgumentException>(() => GateEvaluator.Evaluate(BuildFlavor.Dev, WithRegularSource(xrefs: [Xref(XrefType.Atif, XrefStatus.Onayli), Xref(XrefType.Atif, XrefStatus.Onayli)])));
        Assert.Throws<ArgumentNullException>(() => GateEvaluator.Evaluate(BuildFlavor.Dev, null!));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Undefined_numeric_flavor_behaves_as_public(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Sources = [Src(Regular), Src("test-kucuk")],
            Units = [Unit("q:1:1", status: TextStatus.Taslak), Unit("k:test-kucuk:bolum-1:p1", source: "test-kucuk")],
        };

        GateResult undefined = GateEvaluator.Evaluate((BuildFlavor)42, input);
        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Empty(undefined.IncludedUnits);
        Assert.Equal(publicResult.Report.ToJson(), undefined.Report.ToJson());
    });
    // ---- Paket icerigi: birim suzmesinden sonra ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_pack_whose_units_are_all_filtered_in_public_does_not_enter_with_icerik_yok_and_no_rule_code(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("k:" + Regular + ":bolum-1:p1", status: TextStatus.Taslak), Unit("k:" + Regular + ":bolum-1:p2", status: TextStatus.Incelemede)],
            Packs = [Pack("hadis-sentetik", [Regular])],
        };

        GateResult publicResult = GateEvaluator.Evaluate(BuildFlavor.Public, input);
        GateResult devResult = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        GateReportRow row = Row(publicResult, GateSubjectKind.Paket, "hadis-sentetik");
        Assert.Equal((GateDecision.Girmedi, (GateRule?)null, GateReasons.IcerikYok), (row.Decision, row.Rule, row.Reason));
        Assert.DoesNotContain("hadis-sentetik", publicResult.IncludedPacks);
        Assert.False(publicResult.Report.Rejected);
        Assert.Empty(publicResult.Report.Violations);
        // Kaynak girdi (suzme birim duzeyinde); paket yalniz icerigi kalmadigi icin girmedi. Iç derlemede taslak birimler girer, paket de girer.
        Assert.Equal(GateDecision.Girdi, Row(publicResult, GateSubjectKind.Kaynak, Regular).Decision);
        Assert.Contains("hadis-sentetik", devResult.IncludedPacks);
        Assert.Equal(GateDecision.Girdi, Row(devResult, GateSubjectKind.Paket, "hadis-sentetik").Decision);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_pack_with_at_least_one_included_unit_enters_and_a_deprecated_only_source_does_not(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput mixed = new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("k:" + Regular + ":bolum-1:p1", status: TextStatus.Taslak), Unit("k:" + Regular + ":bolum-1:p2")],
            Packs = [Pack("hadis-sentetik", [Regular])],
        };
        GateInput deprecated = new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("k:" + Regular + ":bolum-1:p1", unitStatus: UnitStatus.KullanimDisi, hasSuccessors: true)],
            Packs = [Pack("hadis-sentetik", [Regular])],
        };

        Assert.Contains("hadis-sentetik", GateEvaluator.Evaluate(BuildFlavor.Public, mixed).IncludedPacks);
        Assert.DoesNotContain("hadis-sentetik", GateEvaluator.Evaluate(BuildFlavor.Dev, deprecated).IncludedPacks);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_pack_that_carries_structure_rows_enters_every_flavor_even_when_all_its_units_are_filtered(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new()
        {
            Sources = [Src(Regular)],
            Units = [Unit("q:1:1", status: TextStatus.Taslak), Unit("q:1:2", status: TextStatus.Taslak)],
            Packs = [Pack("core", [Regular], hasStructure: true), Pack("hadis-sentetik", [Regular])],
        };

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            GateResult result = GateEvaluator.Evaluate(flavor, input);

            Assert.Equal(GateDecision.Girdi, Row(result, GateSubjectKind.Paket, "core").Decision);
            Assert.Equal(
                flavor == BuildFlavor.Public ? GateDecision.Girmedi : GateDecision.Girdi,
                Row(result, GateSubjectKind.Paket, "hadis-sentetik").Decision);
        }
    });

    [Fact]
    public void Without_any_unit_evidence_in_the_input_the_pack_content_flag_stays_authoritative()
    {
        GateInput input = new() { Sources = [Src(Regular)], Packs = [Pack("hadis-sentetik", [Regular])] };

        Assert.Contains("hadis-sentetik", GateEvaluator.Evaluate(BuildFlavor.Public, input).IncludedPacks);
    }


    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Unparseable_flavor_label_makes_the_gate_behave_as_public(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = new() { Sources = [Src("test-kucuk")], Units = [Unit("k:test-kucuk:bolum-1:p1", source: "test-kucuk", status: TextStatus.Taslak)] };

        // TryParseLabel basarisizken out degeri Dev'dir (en gevsek); kapi bunu kullanmaz.
        Assert.False(BuildFlavorLabels.TryParseLabel("Internal", out BuildFlavor naive));
        Assert.Equal(BuildFlavor.Dev, naive);
        Assert.NotEmpty(GateEvaluator.Evaluate(naive, input).IncludedUnits);

        BuildFlavor safe = FlavorPolicy.ParseOrMostRestrictive("Internal");

        Assert.Equal(BuildFlavor.Public, safe);
        Assert.Empty(GateEvaluator.Evaluate(safe, input).IncludedUnits);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Report_counts_included_and_excluded_items_per_group(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput input = WithRegularSource(
            units: [Unit("q:1:1"), Unit("q:1:2"), Unit("q:1:3", status: TextStatus.Taslak)],
            xrefs:
            [
                Xref(XrefType.Atif, XrefStatus.Onayli, id: 1),
                Xref(XrefType.Atif, XrefStatus.Aday, id: 2),
                Xref(XrefType.Atif, XrefStatus.Aday, id: 3),
            ]);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Id == Regular && r.Decision == GateDecision.Girdi && r.Count == 2);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Birim && r.Rule == GateRule.P10 && r.Count == 1);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Id == "atif" && r.Decision == GateDecision.Girdi && r.Count == 1);
        Assert.Contains(result.Report.Rows, r => r.Kind == GateSubjectKind.Baglanti && r.Id == "atif" && r.Rule == GateRule.P07 && r.Count == 2);
    });
}
