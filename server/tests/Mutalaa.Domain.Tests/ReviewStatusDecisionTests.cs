using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>Inceleme karari kurallari: ortak denetimler ve durum hedefleri (K-48). Her sinama tr-TR kulturunde de calisir.</summary>
public class ReviewStatusDecisionTests
{
    public static TheoryData<string, string> StatusPairs => new()
    {
        { "surah_alias", "status" },
        { "xref", "status" },
        { "lemma", "status" },
        { "lemma_gloss", "anlam_kisa" },
        { "quran_word_fix", "root_id" },
        { "quran_word_fix", "lemma_id" },
        { "quran_word_fix", "pos" },
        { "quran_word_fix", "features" },
    };

    public static TheoryData<string, string> UnsupportedPairs => new()
    {
        { "source", "metin" },
        { "root", "status" },
        { "tr_root_index", "status" },
        { "tr_form", "status" },
        { "page_map", "status" },
        { "ayah_box", "status" },
        { "audio_timing", "status" },
        { "unit", "status" },
        { "unit", "anlam_kisa" },
        { "xref", "metin" },
        { "xref", "alan" },
        { "lemma", "anlam_kisa" },
        { "lemma_gloss", "status" },
        { "surah_alias", "alias" },
        { "quran_word_fix", "status" },
        { "bilinmeyen", "status" },
    };

    private static ReviewTargetState Candidate => ReviewTargetState.ForStatus(XrefStatus.Aday);

    /// <summary>Hedef tablosuna uygun aday durumu: quran_word_fix alani review.alan ile ayni, lemma_gloss satiri dolu.</summary>
    private static ReviewTargetState CandidateFor(string table, string alan) => table switch
    {
        "quran_word_fix" => ReviewTargetState.ForFix(XrefStatus.Aday, alan),
        "lemma_gloss" => ReviewTargetState.ForGloss(XrefStatus.Aday, new GlossReviewState("deneme anlami", "1", "kaynak:quranwbw-tr")),
        _ => Candidate,
    };

    [Fact]
    public void IsSupported_lists_exactly_the_documented_pairs()
    {
        Assert.True(ReviewDecisions.IsSupported("unit", "metin"));
        foreach (string[] pair in new[] { new[] { "surah_alias", "status" }, ["xref", "status"], ["lemma", "status"], ["lemma_gloss", "anlam_kisa"] })
        {
            Assert.True(ReviewDecisions.IsSupported(pair[0], pair[1]), string.Join('/', pair));
        }

        Assert.False(ReviewDecisions.IsSupported(null, "status"));
        Assert.False(ReviewDecisions.IsSupported("xref", null));
        Assert.False(ReviewDecisions.IsSupported("XREF", "status"));
    }

    [Theory]
    [MemberData(nameof(StatusPairs))]
    public void Approve_marks_the_candidate_target_onayli(string table, string alan)
    {
        CultureScope.For(true, () =>
        {
            Review review = StatusReview(table, alan);

            ReviewOutcome outcome = ReviewDecisions.Approve(review, Request("test-editor-1", "Deneme gerekcesi"), CandidateFor(table, alan));

            Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
            Assert.Equal("onayla", outcome.Eylem);
            Assert.Equal("test-editor-1", outcome.Inceleyen);
            Assert.Equal(Now, outcome.IncelendiAt);
            Assert.Equal("Deneme gerekcesi", outcome.Gerekce);
            Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
            Assert.Null(outcome.IkinciInceleyen);
            Assert.Null(outcome.UnitText);
            Assert.Null(outcome.UnitMetinDurumu);
        });
    }

    [Theory]
    [MemberData(nameof(StatusPairs))]
    public void Reject_marks_the_candidate_target_red(string table, string alan)
    {
        CultureScope.For(true, () =>
        {
            Review review = StatusReview(table, alan);

            ReviewOutcome outcome = ReviewDecisions.Reject(review, Request(), CandidateFor(table, alan));

            Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
            Assert.Equal("reddet", outcome.Eylem);
            Assert.Equal("test-editor-1", outcome.Inceleyen);
            Assert.Equal(XrefStatus.Red, outcome.TargetStatus);
        });
    }

    [Theory]
    [InlineData(XrefStatus.Onayli)]
    [InlineData(XrefStatus.Red)]
    public void A_target_that_is_not_a_candidate_conflicts_on_approve_and_reject(XrefStatus status)
    {
        Review review = StatusReview();
        ReviewTargetState target = ReviewTargetState.ForStatus(status);

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), target)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Reject(review, Request(), target)));
    }

    [Fact]
    public void An_editor_value_is_not_supported_on_status_targets()
    {
        // xref (baglanti duzeltmesi) ve quran_word_fix (new_value) artik deger kabul eder (A18.4); sure adi hedefi kabul etmez.
        Review review = StatusReview(ReviewTargets.SurahAlias);

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Payload("Deneme paragrafi 9")), Candidate)));
    }

    [Fact]
    public void A_reject_request_cannot_carry_an_edited_value()
    {
        Review review = StatusReview();

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(review, Request(duzenlenen: "{}"), Candidate)));
    }

    [Theory]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    [InlineData(ReviewStatus.GeriAlindi)]
    public void Only_an_open_review_can_be_decided(ReviewStatus status)
    {
        Review review = StatusReview(durum: status);

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), Candidate)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Reject(review, Request(), Candidate)));
    }

    [Theory]
    [MemberData(nameof(UnsupportedPairs))]
    public void Unsupported_target_and_field_pairs_are_422_before_any_other_check(string table, string alan)
    {
        // Durum da gecersiz, gerekce de bos: desteklenmeyen hedef yine de ilk hatadir.
        Review review = StatusReview(table, alan, durum: ReviewStatus.Onaylandi);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(review, Request(gerekce: null), Candidate)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Reject(review, Request(gerekce: null), Candidate)));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\t\n")]
    public void The_reason_is_required(string? gerekce)
    {
        Review review = StatusReview();

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(gerekce: gerekce), Candidate)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(review, Request(gerekce: gerekce), Candidate)));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_reason_is_limited_to_2000_code_points(bool turkish) => CultureScope.For(turkish, () =>
    {
        Review review = StatusReview();
        string atLimit = new('a', 2000);
        string tooLong = new('a', 2001);
        // 2000 kod noktasi ama 4000 UTF-16 birimi: sinir kod noktasiyla olculur.
        string astral = string.Concat(Enumerable.Repeat("\U00010000", 2000));
        string astralTooLong = astral + "\U00010000";

        Assert.Equal(atLimit, ReviewDecisions.Approve(review, Request(gerekce: atLimit), Candidate).Gerekce);
        Assert.Equal(astral, ReviewDecisions.Approve(review, Request(gerekce: astral), Candidate).Gerekce);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(gerekce: tooLong), Candidate)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(gerekce: astralTooLong), Candidate)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(review, Request(gerekce: tooLong), Candidate)));
    });

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData(" ")]
    public void The_acting_user_is_required(string? actor)
    {
        Review review = StatusReview();
        ReviewDecisionRequest request = new() { Actor = actor!, Gerekce = "Deneme gerekcesi", Now = Now };

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, request, Candidate)));
    }

    [Fact]
    public void Validation_comes_before_the_state_conflict()
    {
        Review review = StatusReview(durum: ReviewStatus.Onaylandi);

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(gerekce: null), Candidate)));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void An_editor_cannot_approve_their_own_proposal(bool turkish) => CultureScope.For(turkish, () =>
    {
        Review review = StatusReview(koken: XrefOrigin.Editor, oneren: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-1"), Candidate)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("TEST-EDITOR-1"), Candidate)));
        Assert.Equal(XrefStatus.Onayli, ReviewDecisions.Approve(review, Request("test-editor-2"), Candidate).TargetStatus);
    });

    [Fact]
    public void The_proposer_may_reject_their_own_proposal()
    {
        Review review = StatusReview(koken: XrefOrigin.Editor, oneren: "test-editor-1");

        Assert.Equal(XrefStatus.Red, ReviewDecisions.Reject(review, Request("test-editor-1"), Candidate).TargetStatus);
    }

    [Fact]
    public void The_four_eyes_rule_applies_only_to_editor_origin_proposals()
    {
        Review pipeline = StatusReview(koken: XrefOrigin.Hat, oneren: "hat");
        Review vote = StatusReview(koken: XrefOrigin.KullaniciOyu, oneren: "test-editor-1");

        Assert.Equal(XrefStatus.Onayli, ReviewDecisions.Approve(pipeline, Request("hat"), Candidate).TargetStatus);
        Assert.Equal(XrefStatus.Onayli, ReviewDecisions.Approve(vote, Request("test-editor-1"), Candidate).TargetStatus);
    }

    [Fact]
    public void ApplyTo_writes_the_decision_fields_and_leaves_the_proposal_untouched()
    {
        Review review = StatusReview(koken: XrefOrigin.Hat, oneren: "hat");
        review.Onerilen = "{\"kind\": \"deneme\"}";
        review.Onceki = null;

        ReviewDecisions.Approve(review, Request("test-editor-1", "Deneme gerekcesi"), Candidate).ApplyTo(review);

        Assert.Equal(ReviewStatus.Onaylandi, review.Durum);
        Assert.Equal("onayla", review.Eylem);
        Assert.Equal("test-editor-1", review.Inceleyen);
        Assert.Equal(Now, review.IncelendiAt);
        Assert.Equal("Deneme gerekcesi", review.Gerekce);
        Assert.Null(review.IkinciInceleyen);
        Assert.Equal("{\"kind\": \"deneme\"}", review.Onerilen);
        Assert.Equal("hat", review.Oneren);
        Assert.Equal(XrefOrigin.Hat, review.Koken);
    }

    [Fact]
    public void ApplyTo_rejects_a_null_review()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(StatusReview(), Request(), Candidate);

        Assert.Throws<ArgumentNullException>(() => outcome.ApplyTo(null!));
    }

    [Fact]
    public void A_missing_target_state_is_a_programming_error_not_a_domain_error()
    {
        Review review = StatusReview();

        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Approve(review, Request(), default));
        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Reject(review, Request(), default));
    }
}
