using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>Birim metni incelemesi: tek onay, iki asamali onay (meal, tefsir), ApplyUnitText ve degistirilemez metin (K-48).</summary>
public class ReviewUnitTextDecisionTests
{
    private static ReviewTargetState Target(UnitKind kind = UnitKind.Meal, TextStatus durum = TextStatus.Taslak, SourceKind sourceKind = SourceKind.Meal) =>
        ReviewTargetState.ForUnit(Unit(kind, durum, sourceKind: sourceKind));

    // ---- ApplyUnitText ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ApplyUnitText_applies_the_proposal_with_hash_rev_and_search_keys(bool turkish) => CultureScope.For(turkish, () =>
    {
        UnitReviewState unit = Unit(rev: 3);

        UnitTextUpdate update = ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), null)!.Value;

        SearchKeys keys = SearchNormalizer.Keys(ProposedText);
        Assert.Equal(ProposedText, update.Metin);
        Assert.Equal(ContentHash.Compute(ProposedText), update.ContentHash);
        Assert.Equal(4, update.Rev);
        Assert.Equal(keys.TrNarrow, update.TrNarrow);
        Assert.Equal(keys.TrWide, update.TrWide);
        Assert.Equal(keys.ArNorm, update.ArNorm);
        Assert.Null(update.TrStem);
    });

    [Fact]
    public void ApplyUnitText_prefers_the_edited_value_over_the_proposal()
    {
        UnitTextUpdate update = ReviewDecisions.ApplyUnitText(Unit(), Payload(CurrentText), Payload(ProposedText), Payload(EditedText))!.Value;

        Assert.Equal(EditedText, update.Metin);
    }

    [Fact]
    public void ApplyUnitText_canonicalizes_the_applied_text()
    {
        UnitTextUpdate update = ReviewDecisions.ApplyUnitText(
            Unit(),
            Payload(CurrentText),
            Payload("  Deneme\t paragrafi   2 \r\n"),
            null)!.Value;

        Assert.Equal("Deneme paragrafi 2", update.Metin);
        Assert.Equal(ContentHash.Compute("Deneme paragrafi 2"), update.ContentHash);
    }

    [Fact]
    public void ApplyUnitText_applies_nfc_to_our_own_text()
    {
        UnitTextUpdate update = ReviewDecisions.ApplyUnitText(Unit(), null, Payload("Deneme é"), null)!.Value;

        Assert.Equal("Deneme é", update.Metin);
    }

    [Fact]
    public void ApplyUnitText_ignores_the_content_hash_inside_the_applied_payload()
    {
        UnitTextUpdate update = ReviewDecisions.ApplyUnitText(Unit(), null, Payload(ProposedText, new string('0', 64)), null)!.Value;

        Assert.Equal(ContentHash.Compute(ProposedText), update.ContentHash);
    }

    [Theory]
    [InlineData(null, null)]
    [InlineData("null", null)]
    [InlineData("", " ")]
    public void ApplyUnitText_changes_nothing_when_there_is_no_value(string? onerilen, string? duzenlenen)
    {
        Assert.Null(ReviewDecisions.ApplyUnitText(Unit(), Payload(CurrentText), onerilen, duzenlenen));
    }

    [Fact]
    public void ApplyUnitText_changes_nothing_when_the_text_is_already_the_stored_text()
    {
        Assert.Null(ReviewDecisions.ApplyUnitText(Unit(), Payload(CurrentText), Payload(CurrentText), null));
        Assert.Null(ReviewDecisions.ApplyUnitText(Unit(), Payload(CurrentText), Payload(CurrentText + "  "), null));
    }

    [Fact]
    public void ApplyUnitText_rejects_a_stale_target()
    {
        string stale = Payload("Deneme paragrafi 0");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), stale, Payload(ProposedText), null)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), stale, null, null)));
    }

    [Fact]
    public void ApplyUnitText_skips_the_stale_check_when_there_is_no_baseline()
    {
        Assert.NotNull(ReviewDecisions.ApplyUnitText(Unit(), null, Payload(ProposedText), null));
        Assert.NotNull(ReviewDecisions.ApplyUnitText(Unit(), "null", Payload(ProposedText), null));
    }

    [Theory]
    [InlineData("{bozuk")]
    [InlineData("[]")]
    [InlineData("\"metin\"")]
    [InlineData("{\"metin\": \"Deneme paragrafi 1\"}")]
    [InlineData("{\"metin\": \"Deneme paragrafi 1\", \"content_hash\": 5}")]
    public void ApplyUnitText_rejects_a_malformed_baseline(string onceki) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), onceki, Payload(ProposedText), null)));

    [Theory]
    [InlineData("{bozuk")]
    [InlineData("[]")]
    [InlineData("{\"content_hash\": \"abc\"}")]
    [InlineData("{\"metin\": \"\"}")]
    [InlineData("{\"metin\": 5}")]
    [InlineData("{\"metin\": \"  \\t\\n \"}")]
    public void ApplyUnitText_rejects_a_malformed_applied_value(string value)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), null, value, null)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), null, null, value)));
    }

    [Fact]
    public void ApplyUnitText_rejects_text_that_is_not_valid_unicode()
    {
        // JsonSerializer tek basina vekili U+FFFD'ye cevirir; bozuk metin ham JSON kacisiyla verilir.
        string lone = "{\"metin\": \"Deneme \\ud800 paragrafi\"}";

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.ApplyUnitText(Unit(), null, lone, null)));
    }

    [Theory]
    [InlineData(UnitKind.Ayet, SourceKind.Meal)]
    [InlineData(UnitKind.Ayet, SourceKind.KuranMetni)]
    [InlineData(UnitKind.Meal, SourceKind.KuranMetni)]
    [InlineData(UnitKind.Risale, SourceKind.KuranMetni)]
    public void ApplyUnitText_never_changes_immutable_text(UnitKind kind, SourceKind sourceKind)
    {
        UnitReviewState unit = Unit(kind, sourceKind: sourceKind);

        Assert.Equal(DomainErrorCodes.DegistirilemezMetin, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, null, Payload(ProposedText), null)));
        Assert.Equal(DomainErrorCodes.DegistirilemezMetin, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, null, null, null)));
    }

    // ---- Tek onayli birim (meal ve tefsir disi) ----

    [Theory]
    [InlineData(UnitKind.Risale)]
    [InlineData(UnitKind.Hadis)]
    [InlineData(UnitKind.HadisCeviri)]
    [InlineData(UnitKind.Kitap)]
    public void A_single_approval_applies_the_text_and_approves_the_unit(UnitKind kind)
    {
        CultureScope.For(true, () =>
        {
            Review review = UnitReview();

            ReviewOutcome outcome = ReviewDecisions.Approve(review, Request("test-editor-1"), Target(kind));

            Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
            Assert.Equal("onayla", outcome.Eylem);
            Assert.Equal("test-editor-1", outcome.Inceleyen);
            Assert.Equal(Now, outcome.IncelendiAt);
            Assert.Null(outcome.IkinciInceleyen);
            Assert.Null(outcome.IkinciIncelendiAt);
            Assert.Null(outcome.IkinciGerekce);
            Assert.Null(outcome.Duzenlenen);
            Assert.Equal(TextStatus.Onayli, outcome.UnitMetinDurumu);
            Assert.Equal(ProposedText, outcome.UnitText!.Value.Metin);
            Assert.Equal(2, outcome.UnitText.Value.Rev);
            Assert.Null(outcome.TargetStatus);
        });
    }

    [Fact]
    public void A_single_approval_with_an_edited_value_applies_it_and_keeps_the_proposal()
    {
        Review review = UnitReview();

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(duzenlenen: Payload(EditedText)), Target(UnitKind.Risale));
        outcome.ApplyTo(review);

        Assert.Equal("duzenle_onayla", outcome.Eylem);
        Assert.Equal(EditedText, outcome.UnitText!.Value.Metin);
        Assert.Equal(Payload(EditedText), review.Duzenlenen);
        Assert.Equal(Payload(ProposedText), review.Onerilen);
        Assert.Equal(Payload(CurrentText), review.Onceki);
    }

    [Fact]
    public void A_status_only_approval_keeps_the_text_and_approves_the_unit()
    {
        Review review = UnitReview(onerilen: "null");

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(), Target(UnitKind.Risale));

        Assert.Equal(TextStatus.Onayli, outcome.UnitMetinDurumu);
        Assert.Null(outcome.UnitText);
        Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
    }

    [Fact]
    public void A_stale_target_blocks_the_approval()
    {
        Review review = UnitReview(onceki: Payload("Deneme paragrafi 0"));

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), Target(UnitKind.Risale))));
    }

    [Fact]
    public void A_malformed_edited_value_is_a_validation_error()
    {
        Review review = UnitReview();

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: "{bozuk"), Target(UnitKind.Risale))));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: " "), Target(UnitKind.Risale))));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: "{\"metin\": \"\"}"), Target(UnitKind.Risale))));
    }

    [Theory]
    [InlineData(UnitKind.Ayet, SourceKind.Meal)]
    [InlineData(UnitKind.Meal, SourceKind.KuranMetni)]
    [InlineData(UnitKind.Ayet, SourceKind.KuranMetni)]
    public void Immutable_text_cannot_be_approved_but_can_be_rejected(UnitKind kind, SourceKind sourceKind)
    {
        Review review = UnitReview();
        ReviewTargetState target = Target(kind, TextStatus.Onayli, sourceKind);

        Assert.Equal(DomainErrorCodes.DegistirilemezMetin, CodeOf(() => ReviewDecisions.Approve(review, Request(), target)));
        Assert.Equal(DomainErrorCodes.DegistirilemezMetin, CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Payload(EditedText)), target)));
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(review, Request(), target).Durum);
    }

    // ---- Iki asamali onay (meal, tefsir) ----

    [Theory]
    [InlineData(UnitKind.Meal)]
    [InlineData(UnitKind.Tefsir)]
    public void The_first_approval_records_the_reviewer_and_leaves_the_review_open(UnitKind kind)
    {
        CultureScope.For(true, () =>
        {
            Review review = UnitReview();

            ReviewOutcome outcome = ReviewDecisions.Approve(review, Request("test-editor-1", "Birinci gerekce"), Target(kind));

            Assert.Equal(ReviewStatus.Acik, outcome.Durum);
            Assert.Equal("onayla", outcome.Eylem);
            Assert.Equal("test-editor-1", outcome.Inceleyen);
            Assert.Equal(Now, outcome.IncelendiAt);
            Assert.Equal("Birinci gerekce", outcome.Gerekce);
            Assert.Null(outcome.IkinciInceleyen);
            Assert.Null(outcome.UnitText);
            Assert.Equal(TextStatus.Incelemede, outcome.UnitMetinDurumu);
        });
    }

    [Theory]
    [InlineData(TextStatus.Taslak, TextStatus.Incelemede)]
    [InlineData(TextStatus.Incelemede, null)]
    [InlineData(TextStatus.Onayli, null)]
    public void The_first_approval_moves_only_a_draft_unit_to_incelemede(TextStatus current, TextStatus? expected)
    {
        Review review = UnitReview();

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(), Target(UnitKind.Meal, current));

        Assert.Equal(expected, outcome.UnitMetinDurumu);
        Assert.Null(outcome.UnitText);
    }

    [Fact]
    public void The_first_approval_may_carry_an_edited_value_that_is_stored_not_applied()
    {
        Review review = UnitReview();

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(duzenlenen: Payload(EditedText)), Target());
        outcome.ApplyTo(review);

        Assert.Equal("duzenle_onayla", outcome.Eylem);
        Assert.Equal(Payload(EditedText), outcome.Duzenlenen);
        Assert.Equal(Payload(EditedText), review.Duzenlenen);
        Assert.Equal(Payload(ProposedText), review.Onerilen);
        Assert.Null(outcome.UnitText);
        Assert.Equal(ReviewStatus.Acik, review.Durum);
    }

    [Fact]
    public void The_first_approval_of_a_stale_review_conflicts()
    {
        Review review = UnitReview(onceki: Payload("Deneme paragrafi 0"));

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), Target())));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_second_approval_by_another_editor_applies_the_value_and_approves(bool turkish) => CultureScope.For(turkish, () =>
    {
        Review review = UnitReview();
        ReviewDecisions.Approve(review, Request("test-editor-1", "Birinci gerekce"), Target()).ApplyTo(review);

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request("test-editor-2", "Ikinci gerekce"), Target(durum: TextStatus.Incelemede));
        outcome.ApplyTo(review);

        Assert.Equal(ReviewStatus.Onaylandi, review.Durum);
        Assert.Equal("onayla", review.Eylem);
        Assert.Equal("test-editor-1", review.Inceleyen);
        Assert.Equal("Birinci gerekce", review.Gerekce);
        Assert.Equal("test-editor-2", review.IkinciInceleyen);
        Assert.Equal(Now, review.IkinciIncelendiAt);
        Assert.Equal("Ikinci gerekce", review.IkinciGerekce);
        Assert.Equal(TextStatus.Onayli, outcome.UnitMetinDurumu);
        Assert.Equal(ProposedText, outcome.UnitText!.Value.Metin);
        Assert.Equal(2, outcome.UnitText.Value.Rev);
    });

    [Fact]
    public void The_second_approval_applies_the_value_edited_by_the_first_approver()
    {
        Review review = UnitReview();
        ReviewDecisions.Approve(review, Request("test-editor-1", duzenlenen: Payload(EditedText)), Target()).ApplyTo(review);

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request("test-editor-2"), Target(durum: TextStatus.Incelemede));
        outcome.ApplyTo(review);

        Assert.Equal("duzenle_onayla", review.Eylem);
        Assert.Equal(EditedText, outcome.UnitText!.Value.Metin);
        Assert.Equal(Payload(EditedText), review.Duzenlenen);
        Assert.Equal(Payload(ProposedText), review.Onerilen);
    }

    [Fact]
    public void The_second_approval_cannot_come_from_the_first_approver()
    {
        Review review = UnitReview(inceleyen: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-1"), Target(durum: TextStatus.Incelemede))));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("Test-Editor-1"), Target(durum: TextStatus.Incelemede))));
    }

    [Fact]
    public void The_second_approval_cannot_change_the_value()
    {
        Review review = UnitReview(inceleyen: "test-editor-1");

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-2", duzenlenen: Payload(EditedText)), Target(durum: TextStatus.Incelemede))));
    }

    [Fact]
    public void The_second_approval_of_a_stale_review_conflicts()
    {
        Review review = UnitReview(onceki: Payload("Deneme paragrafi 0"), inceleyen: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-2"), Target(durum: TextStatus.Incelemede))));
    }

    [Fact]
    public void The_four_eyes_rule_holds_at_every_stage_of_a_meal_review()
    {
        Review first = UnitReview(koken: XrefOrigin.Editor, oneren: "test-editor-1");
        Review second = UnitReview(koken: XrefOrigin.Editor, oneren: "test-editor-2", inceleyen: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(first, Request("test-editor-1"), Target())));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(second, Request("test-editor-2"), Target(durum: TextStatus.Incelemede))));
        Assert.Equal(TextStatus.Incelemede, ReviewDecisions.Approve(first, Request("test-editor-2"), Target()).UnitMetinDurumu);
    }

    [Fact]
    public void An_approved_unit_keeps_its_old_text_and_status_until_the_second_approval()
    {
        Review review = UnitReview();

        ReviewOutcome first = ReviewDecisions.Approve(review, Request("test-editor-1"), Target(UnitKind.Tefsir, TextStatus.Onayli));

        Assert.Null(first.UnitMetinDurumu);
        Assert.Null(first.UnitText);
    }

    // ---- Ret ----

    [Theory]
    [InlineData(TextStatus.Taslak, null)]
    [InlineData(TextStatus.Incelemede, TextStatus.Taslak)]
    [InlineData(TextStatus.Onayli, null)]
    public void A_rejection_returns_an_incelemede_unit_to_taslak_and_never_changes_the_text(TextStatus current, TextStatus? expected)
    {
        Review review = UnitReview();

        ReviewOutcome outcome = ReviewDecisions.Reject(review, Request("test-editor-1", "Ret gerekcesi"), Target(UnitKind.Meal, current));

        Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
        Assert.Equal("reddet", outcome.Eylem);
        Assert.Equal("test-editor-1", outcome.Inceleyen);
        Assert.Equal("Ret gerekcesi", outcome.Gerekce);
        Assert.Null(outcome.IkinciInceleyen);
        Assert.Equal(expected, outcome.UnitMetinDurumu);
        Assert.Null(outcome.UnitText);
    }

    [Fact]
    public void A_rejection_after_the_first_approval_is_recorded_as_the_second_stage_decision()
    {
        Review review = UnitReview();
        ReviewDecisions.Approve(review, Request("test-editor-1", "Birinci gerekce"), Target()).ApplyTo(review);

        ReviewOutcome outcome = ReviewDecisions.Reject(review, Request("test-editor-2", "Ret gerekcesi"), Target(durum: TextStatus.Incelemede));
        outcome.ApplyTo(review);

        Assert.Equal(ReviewStatus.Reddedildi, review.Durum);
        Assert.Equal("test-editor-1", review.Inceleyen);
        Assert.Equal("Birinci gerekce", review.Gerekce);
        Assert.Equal("test-editor-2", review.IkinciInceleyen);
        Assert.Equal(Now, review.IkinciIncelendiAt);
        Assert.Equal("Ret gerekcesi", review.IkinciGerekce);
        Assert.Equal(TextStatus.Taslak, outcome.UnitMetinDurumu);
    }

    [Fact]
    public void A_first_approver_may_change_their_mind_and_reject()
    {
        Review review = UnitReview(inceleyen: "test-editor-1");

        ReviewOutcome outcome = ReviewDecisions.Reject(review, Request("test-editor-1"), Target(durum: TextStatus.Incelemede));

        Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
    }

    [Fact]
    public void A_rejection_keeps_the_edited_value_for_the_audit_trail()
    {
        Review review = UnitReview(duzenlenen: Payload(EditedText), inceleyen: "test-editor-1");

        ReviewOutcome outcome = ReviewDecisions.Reject(review, Request("test-editor-2"), Target(durum: TextStatus.Incelemede));

        Assert.Equal(Payload(EditedText), outcome.Duzenlenen);
    }

    [Fact]
    public void Non_two_stage_units_reject_into_the_first_stage_fields()
    {
        Review review = UnitReview();

        ReviewOutcome outcome = ReviewDecisions.Reject(review, Request("test-editor-1"), Target(UnitKind.Risale));

        Assert.Equal("test-editor-1", outcome.Inceleyen);
        Assert.Null(outcome.IkinciInceleyen);
    }

    // ---- Yardimcilar ----

    [Theory]
    [InlineData("unit", "metin", UnitKind.Meal, true)]
    [InlineData("unit", "metin", UnitKind.Tefsir, true)]
    [InlineData("unit", "metin", UnitKind.Risale, false)]
    [InlineData("unit", "metin", UnitKind.Ayet, false)]
    [InlineData("unit", "metin", UnitKind.Hadis, false)]
    [InlineData("unit", "status", UnitKind.Meal, false)]
    [InlineData("xref", "status", UnitKind.Meal, false)]
    [InlineData("lemma_gloss", "anlam_kisa", UnitKind.Tefsir, false)]
    public void RequiresSecondApproval_is_only_for_meal_and_tefsir_text(string table, string alan, UnitKind kind, bool expected) =>
        Assert.Equal(expected, ReviewDecisions.RequiresSecondApproval(table, alan, kind));

    [Fact]
    public void A_unit_target_state_is_required_for_unit_reviews()
    {
        Review review = UnitReview();

        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)));
        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Reject(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)));
    }
}
