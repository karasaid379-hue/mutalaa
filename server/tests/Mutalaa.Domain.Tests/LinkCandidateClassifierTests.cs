using Mutalaa.Domain.Links;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Baglanti adayi sinifi (A18.4, K-51 madde 2): her dal ve sinirlar. Kanit sentetiktir; her test Invariant ve tr-TR kulturunde calisir.
/// </summary>
public class LinkCandidateClassifierTests
{
    private const string Strong = """{"matched_words": 9, "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""";

    private static LinkCandidateClass Classify(XrefType type, float confidence, string? evidence) =>
        LinkCandidateClassifier.Classify(type, confidence, evidence);

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void An_inconsistent_quote_is_tutarsiz_whatever_the_type_or_confidence(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Equal(LinkCandidateClass.Tutarsiz, Classify(XrefType.Iktibas, 0.99f, """{"consistent_quote": false, "matched_words": 9, "coverage": 1, "phrase_freq": 1}"""));
        Assert.Equal(LinkCandidateClass.Tutarsiz, Classify(XrefType.Kok, 0.5f, """{"consistent_quote": false}"""));
    });

    [Theory]
    [InlineData(0.30f, LinkCandidateClass.Tutarsiz)]
    [InlineData(0.10f, LinkCandidateClass.Tutarsiz)]
    [InlineData(0.0f, LinkCandidateClass.Tutarsiz)]
    [InlineData(0.31f, LinkCandidateClass.Diger)]
    public void A_low_confidence_atif_is_tutarsiz_up_to_030_inclusive(float confidence, LinkCandidateClass expected) =>
        Assert.Equal(expected, Classify(XrefType.Atif, confidence, null));

    [Fact]
    public void A_low_confidence_iktibas_is_not_tutarsiz_because_the_rule_is_about_atif()
    {
        Assert.Equal(LinkCandidateClass.Diger, Classify(XrefType.Iktibas, 0.2f, "{}"));
    }

    [Theory]
    [InlineData(XrefType.Iktibas)]
    [InlineData(XrefType.Atif)]
    public void A_strong_exact_unique_quote_is_toplu(XrefType type)
    {
        Assert.Equal(LinkCandidateClass.Toplu, Classify(type, 0.5f, Strong));
    }

    [Fact]
    public void Toplu_accepts_a_high_confidence_without_the_consistent_quote_flag()
    {
        string evidence = """{"matched_words": 7, "coverage": 1, "phrase_freq": 1}""";

        Assert.Equal(LinkCandidateClass.Toplu, Classify(XrefType.Iktibas, 0.95f, evidence));
        Assert.Equal(LinkCandidateClass.Diger, Classify(XrefType.Iktibas, 0.94f, evidence));
    }

    [Theory]
    [InlineData("""{"matched_words": 6, "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""")]
    [InlineData("""{"matched_words": 9, "coverage": 0.9, "phrase_freq": 1, "consistent_quote": true}""")]
    [InlineData("""{"matched_words": 9, "coverage": 1, "phrase_freq": 2, "consistent_quote": true}""")]
    [InlineData("""{"matched_words": 9, "coverage": 1, "consistent_quote": true}""")]
    [InlineData("""{"coverage": 1, "phrase_freq": 1, "consistent_quote": true}""")]
    [InlineData("""{"matched_words": 9, "phrase_freq": 1, "consistent_quote": true}""")]
    [InlineData("""{"matched_words": "9", "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""")]
    public void A_missing_or_weak_field_keeps_the_candidate_out_of_toplu(string evidence)
    {
        Assert.NotEqual(LinkCandidateClass.Toplu, Classify(XrefType.Iktibas, 0.97f, evidence));
    }

    [Theory]
    [InlineData(XrefType.Ima)]
    [InlineData(XrefType.Kok)]
    [InlineData(XrefType.Lemma)]
    [InlineData(XrefType.BenzerAyet)]
    public void Only_iktibas_and_atif_can_be_toplu(XrefType type)
    {
        Assert.NotEqual(LinkCandidateClass.Toplu, Classify(type, 0.97f, Strong));
    }

    [Theory]
    [InlineData(0.40f, LinkCandidateClass.Gri)]
    [InlineData(0.55f, LinkCandidateClass.Gri)]
    [InlineData(0.79f, LinkCandidateClass.Gri)]
    [InlineData(0.80f, LinkCandidateClass.Diger)]
    [InlineData(0.39f, LinkCandidateClass.Diger)]
    [InlineData(1.0f, LinkCandidateClass.Diger)]
    public void Gri_is_the_band_040_inclusive_to_080_exclusive(float confidence, LinkCandidateClass expected)
    {
        Assert.Equal(expected, Classify(XrefType.Iktibas, confidence, "{}"));
    }

    [Fact]
    public void The_order_is_tutarsiz_then_toplu_then_gri()
    {
        // Gri bandindaki guven ama tutarsiz alinti: tutarsiz kazanir. Toplu'ya uyan guven 0.5 ise (alinti tutarli) toplu gri'den once gelir.
        Assert.Equal(LinkCandidateClass.Tutarsiz, Classify(XrefType.Atif, 0.5f, """{"consistent_quote": false}"""));
        Assert.Equal(LinkCandidateClass.Toplu, Classify(XrefType.Iktibas, 0.5f, Strong));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("{bozuk")]
    [InlineData("[1, 2]")]
    [InlineData("\"metin\"")]
    [InlineData("null")]
    public void Unreadable_evidence_counts_as_no_field(string? evidence)
    {
        Assert.Equal(LinkCandidateClass.Gri, Classify(XrefType.Iktibas, 0.5f, evidence));
        Assert.Equal(default, LinkEvidenceReader.ReadFacts(evidence));
    }

    [Fact]
    public void Evidence_numbers_and_booleans_must_have_the_right_json_type()
    {
        LinkEvidenceFacts facts = LinkEvidenceReader.ReadFacts("""{"matched_words": "9", "coverage": 1.0, "phrase_freq": null, "consistent_quote": "false"}""");

        Assert.Null(facts.MatchedWords);
        Assert.Equal(1.0, facts.Coverage);
        Assert.Null(facts.PhraseFreq);
        Assert.Null(facts.ConsistentQuote);
    }

    [Theory]
    [InlineData(LinkCandidateClass.Tutarsiz, "tutarsiz")]
    [InlineData(LinkCandidateClass.Toplu, "toplu")]
    [InlineData(LinkCandidateClass.Gri, "gri")]
    [InlineData(LinkCandidateClass.Diger, "diger")]
    public void Class_labels_round_trip_with_ordinal_matching(LinkCandidateClass value, string label)
    {
        Assert.Equal(label, value.ToLabel());
        Assert.True(LinkCandidateClassLabels.TryParseLabel(label, out LinkCandidateClass parsed));
        Assert.Equal(value, parsed);
        Assert.False(LinkCandidateClassLabels.TryParseLabel(label.ToUpperInvariant(), out _));
        Assert.False(LinkCandidateClassLabels.TryParseLabel(null, out _));
    }

    [Fact]
    public void The_queue_order_is_the_numeric_order_of_the_enum()
    {
        Assert.Equal(
            [LinkCandidateClass.Tutarsiz, LinkCandidateClass.Toplu, LinkCandidateClass.Gri, LinkCandidateClass.Diger],
            Enum.GetValues<LinkCandidateClass>().Order());
    }

    [Fact]
    public void ReadString_reads_only_string_fields()
    {
        Assert.Equal("abc", LinkEvidenceReader.ReadString("""{"src_hash": "abc"}""", "src_hash"));
        Assert.Null(LinkEvidenceReader.ReadString("""{"src_hash": 5}""", "src_hash"));
        Assert.Null(LinkEvidenceReader.ReadString("""{"src_hash": "abc"}""", "dst_hash"));
        Assert.Null(LinkEvidenceReader.ReadString("{bozuk", "src_hash"));
        Assert.Null(LinkEvidenceReader.ReadString(null, "src_hash"));
    }
}
