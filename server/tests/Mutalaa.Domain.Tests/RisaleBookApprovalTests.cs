using Mutalaa.Domain.Content;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Kitap bazinda toplu onay kurali (K-51 madde 11): kitap ozeti, onkosul degerlendirmesi, karar sirasi, ETag bicimi. Girdiler sentetiktir
/// (capalar <c>rn:test-deneme:...</c>, ozetler sabit onaltilik dizgiler). Her sinama tr-TR kulturunde de calisir.
/// </summary>
public class RisaleBookApprovalTests
{
    private const string Slug = "deneme-kitap";

    private static string Hash(char c) => new(c, 64);

    private static RisaleBookUnit Unit(string anchor, char hash = 'a', TextStatus durum = TextStatus.Taslak, bool evidence = true) =>
        new(anchor, Hash(hash), durum, evidence);

    private static List<RisaleBookUnit> Book() =>
    [
        Unit("rn:deneme-kitap:bolum-1:p1", 'a'),
        Unit("rn:deneme-kitap:bolum-1:p2", 'b'),
        Unit("rn:deneme-kitap:bolum-2:p1", 'c', TextStatus.Onayli),
    ];

    [Fact]
    public void Digest_is_the_content_digest_of_anchor_and_content_hash_pairs_and_ignores_status_and_order()
    {
        List<RisaleBookUnit> units = Book();
        string expected = ContentDigest.Compute(units.Select(u => new ContentDigestEntry(u.Anchor, u.ContentHash)));

        Assert.Equal(expected, RisaleBookApproval.ComputeDigest(units));

        units.Reverse();
        Assert.Equal(expected, RisaleBookApproval.ComputeDigest(units));

        // Metin durumu ve kanit ozete girmez: onay ozeti degistirmez.
        List<RisaleBookUnit> approved = [.. units.Select(u => u with { MetinDurumu = TextStatus.Onayli, HasGbutEvidence = false })];
        Assert.Equal(expected, RisaleBookApproval.ComputeDigest(approved));
    }

    [Fact]
    public void Digest_changes_when_a_content_hash_or_an_anchor_changes_and_an_empty_book_has_the_empty_sha256()
    {
        string baseline = RisaleBookApproval.ComputeDigest(Book());

        List<RisaleBookUnit> changedHash = Book();
        changedHash[0] = changedHash[0] with { ContentHash = Hash('d') };
        Assert.NotEqual(baseline, RisaleBookApproval.ComputeDigest(changedHash));

        List<RisaleBookUnit> extra = Book();
        extra.Add(Unit("rn:deneme-kitap:bolum-2:p2", 'e'));
        Assert.NotEqual(baseline, RisaleBookApproval.ComputeDigest(extra));

        Assert.Equal("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", RisaleBookApproval.ComputeDigest([]));
    }

    [Fact]
    public void Assess_counts_statuses_and_units_without_evidence()
    {
        List<RisaleBookUnit> units = Book();
        units.Add(Unit("rn:deneme-kitap:bolum-3:p1", 'f', TextStatus.Incelemede, evidence: false));

        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, units);

        Assert.Equal(4, assessment.Total);
        Assert.Equal(2, assessment.Draft);
        Assert.Equal(1, assessment.Approved);
        Assert.Equal(1, assessment.WithoutEvidence);
        Assert.False(assessment.GbutEvidence);
        Assert.True(assessment.SlugVerified);
        Assert.Equal(RisaleBookApproval.ComputeDigest(units), assessment.Digest);
    }

    [Fact]
    public void An_empty_book_has_no_gbut_evidence_and_nothing_to_approve()
    {
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, []);

        Assert.False(assessment.GbutEvidence);
        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, assessment.Digest, sampleReadingDone: true);
        Assert.Equal(RisaleApprovalOutcome.NothingToApprove, verdict.Outcome);
    }

    [Fact]
    public void Decide_approves_when_digest_matches_and_every_prerequisite_holds()
    {
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, Book());

        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, assessment.Digest, sampleReadingDone: true);

        Assert.Equal(RisaleApprovalOutcome.Approve, verdict.Outcome);
        Assert.Empty(verdict.Missing);
    }

    [Fact]
    public void Decide_reports_a_stale_digest_before_any_prerequisite()
    {
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: false, [Unit("rn:deneme-kitap:p1", evidence: false)]);

        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, Hash('0'), sampleReadingDone: false);

        Assert.Equal(RisaleApprovalOutcome.Stale, verdict.Outcome);
        Assert.Empty(verdict.Missing);
    }

    [Fact]
    public void Decide_lists_every_missing_prerequisite_in_the_fixed_order()
    {
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: false, [Unit("rn:deneme-kitap:p1", evidence: false)]);

        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, assessment.Digest, sampleReadingDone: false);

        Assert.Equal(RisaleApprovalOutcome.PrerequisitesMissing, verdict.Outcome);
        Assert.Equal(
            [RisaleApprovalPrerequisites.GbutKanitiYok, RisaleApprovalPrerequisites.SlugDogrulanmadi, RisaleApprovalPrerequisites.OrnekOkumaYok],
            verdict.Missing);
    }

    [Theory]
    [InlineData(false, true, true, "gbut-kaniti-yok")]
    [InlineData(true, false, true, "slug-dogrulanmadi")]
    [InlineData(true, true, false, "ornek-okuma-yok")]
    public void Each_prerequisite_alone_blocks_the_approval(bool evidence, bool slugVerified, bool sample, string expected)
    {
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified, [Unit("rn:deneme-kitap:p1", evidence: evidence)]);

        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, assessment.Digest, sample);

        Assert.Equal(RisaleApprovalOutcome.PrerequisitesMissing, verdict.Outcome);
        Assert.Equal([expected], verdict.Missing);
    }

    [Fact]
    public void One_unit_without_evidence_is_enough_to_miss_the_gbut_prerequisite()
    {
        List<RisaleBookUnit> units = Book();
        units[1] = units[1] with { HasGbutEvidence = false };

        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, units);

        Assert.Equal([RisaleApprovalPrerequisites.GbutKanitiYok], RisaleBookApproval.Missing(assessment, sampleReadingDone: true));
    }

    [Fact]
    public void Decide_finds_nothing_to_approve_when_no_draft_unit_remains()
    {
        List<RisaleBookUnit> units = [.. Book().Select(u => u with { MetinDurumu = TextStatus.Onayli })];
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, units);

        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, assessment.Digest, sampleReadingDone: true);

        Assert.Equal(RisaleApprovalOutcome.NothingToApprove, verdict.Outcome);
    }

    [Fact]
    public void Etag_is_the_quoted_lowercase_hex_digest_and_only_that_shape_parses()
    {
        string digest = RisaleBookApproval.ComputeDigest(Book());
        string etag = RisaleBookApproval.FormatEtag(digest);

        Assert.Equal("\"" + digest + "\"", etag);
        Assert.True(RisaleBookApproval.TryParseEtag(etag, out string parsed));
        Assert.Equal(digest, parsed);

        Assert.False(RisaleBookApproval.TryParseEtag(null, out _));
        Assert.False(RisaleBookApproval.TryParseEtag(digest, out _)); // tirnaksiz
        Assert.False(RisaleBookApproval.TryParseEtag("*", out _));
        Assert.False(RisaleBookApproval.TryParseEtag("W/" + etag, out _));
        Assert.False(RisaleBookApproval.TryParseEtag(etag + ", " + etag, out _));
        Assert.False(RisaleBookApproval.TryParseEtag("\"" + digest.ToUpperInvariant() + "\"", out _)); // buyuk harf
        Assert.False(RisaleBookApproval.TryParseEtag("\"" + digest[..63] + "\"", out _)); // kisa
        Assert.False(RisaleBookApproval.TryParseEtag("\"" + digest[..63] + "g\"", out _)); // onaltilik degil
    }

    [Fact]
    public void Anchor_prefix_includes_the_trailing_colon_so_related_slugs_do_not_collide_and_target_key_is_risale_slug()
    {
        Assert.Equal("rn:sozler:", RisaleBookApproval.AnchorPrefix("sozler"));
        Assert.False("rn:sozler-osmanlica:p1".StartsWith(RisaleBookApproval.AnchorPrefix("sozler"), StringComparison.Ordinal));
        Assert.Equal("risale:sozler", RisaleBookApproval.TargetKey("sozler"));
    }

    [Theory]
    [InlineData(null, false)]
    [InlineData("", false)]
    [InlineData("   ", false)]
    [InlineData("Deneme gerekcesi", true)]
    public void Gerekce_is_required_and_not_blank(string? gerekce, bool valid) =>
        Assert.Equal(valid, RisaleBookApproval.CheckGerekce(gerekce) is null);

    [Fact]
    public void Gerekce_is_capped_at_2000_code_points()
    {
        Assert.Null(RisaleBookApproval.CheckGerekce(new string('a', 2000)));
        Assert.NotNull(RisaleBookApproval.CheckGerekce(new string('a', 2001)));

        // Vekil cift tek kod noktasidir: 2000 cift gecerli, 2001 gecersiz.
        Assert.Null(RisaleBookApproval.CheckGerekce(string.Concat(Enumerable.Repeat("\U0001D11E", 2000))));
        Assert.NotNull(RisaleBookApproval.CheckGerekce(string.Concat(Enumerable.Repeat("\U0001D11E", 2001))));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_decision_is_culture_independent(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Ozet ve ETag kulturden bagimsiz kucuk harf onaltiliktir (tr-TR'de buyuk-kucuk harf donusumune bagli kod yok).
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(slugVerified: true, Book());
        Assert.Matches("^[0-9a-f]{64}$", assessment.Digest);
        Assert.True(RisaleBookApproval.TryParseEtag(RisaleBookApproval.FormatEtag(assessment.Digest), out _));
        Assert.Equal(RisaleApprovalOutcome.Approve, RisaleBookApproval.Decide(assessment, assessment.Digest, sampleReadingDone: true).Outcome);
        Assert.Equal("rn:" + Slug + ":", RisaleBookApproval.AnchorPrefix(Slug));
    });
}
