using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Birlesik mealin izleyen birimi (attrs.birlesik_ile dolu; K-49 madde 8): metin degistiren karar 422 inceleme-desteklenmiyor;
/// durum onayi (onerilen yok), ret ve ozeti degismeyen metin serbest. Hat kokenli meal kaydi (onceki bos ya da dolu) iki onayla onayli olur.
/// Sentetik veri; tr-TR dahil.
/// </summary>
public class ReviewMergedFollowerTests
{
    private static ReviewTargetState Target(TextStatus durum = TextStatus.Taslak, bool follower = true, string metin = CurrentText) =>
        ReviewTargetState.ForUnit(Unit(UnitKind.Meal, durum, metin: metin, isMergedFollower: follower));

    // ---- IsMergedFollower ----

    [Theory]
    [InlineData(null, false)]
    [InlineData("", false)]
    [InlineData("{}", false)]
    [InlineData("{\"kapsam\":\"q:2:1-2\"}", false)]
    [InlineData("{\"birlesik_ile\":null}", false)]
    [InlineData("{\"birlesik_ile\":\"\"}", false)]
    [InlineData("{\"birlesik_ile\":\"meal:test:2:1\"}", true)]
    [InlineData("{\"kapsam\":\"q:2:1-2\",\"birlesik_ile\":\"meal:test:2:1\"}", true)]
    [InlineData("{\"birlesik_ile\":[\"meal:test:2:1\"]}", true)]
    [InlineData("[]", false)]
    [InlineData("{bozuk", false)]
    public void IsMergedFollower_is_true_only_for_a_filled_birlesik_ile_key(string? attrs, bool expected)
    {
        foreach (bool turkish in new[] { false, true })
        {
            CultureScope.For(turkish, () => Assert.Equal(expected, ReviewDecisions.IsMergedFollower(attrs)));
        }
    }

    // ---- ApplyUnitText ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ApplyUnitText_refuses_a_real_text_change_on_a_merged_follower(bool turkish) => CultureScope.For(turkish, () =>
    {
        UnitReviewState unit = Unit(UnitKind.Meal, isMergedFollower: true);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), null)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), Payload(EditedText))));
    });

    [Fact]
    public void ApplyUnitText_leaves_an_unchanged_text_or_no_value_alone_on_a_merged_follower()
    {
        UnitReviewState unit = Unit(UnitKind.Meal, isMergedFollower: true);

        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(CurrentText), null));
        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), "null", null));
        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), null, null));
    }

    // ---- Iki asamali onay ----

    [Fact]
    public void The_first_approval_that_would_change_a_merged_follower_is_refused_at_once()
    {
        Review review = UnitReview();

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(review, Request(), Target())));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Payload(EditedText)), Target())));
    }

    [Fact]
    public void The_second_approval_that_would_change_a_merged_follower_is_refused()
    {
        Review review = UnitReview(inceleyen: "test-editor-1");

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-2"), Target(TextStatus.Incelemede))));
    }

    [Fact]
    public void A_status_only_review_of_a_merged_follower_gets_two_approvals_and_becomes_approved_without_a_text_change()
    {
        Review review = UnitReview(onerilen: "null", onceki: "null");

        ReviewOutcome first = ReviewDecisions.Approve(review, Request(), Target());
        first.ApplyTo(review);
        ReviewOutcome second = ReviewDecisions.Approve(review, Request("test-editor-2"), Target(TextStatus.Incelemede));

        Assert.Equal(ReviewStatus.Acik, first.Durum);
        Assert.Equal(TextStatus.Incelemede, first.UnitMetinDurumu);
        Assert.Equal(ReviewStatus.Onaylandi, second.Durum);
        Assert.Equal(TextStatus.Onayli, second.UnitMetinDurumu);
        Assert.Null(second.UnitText);
    }

    [Fact]
    public void Rejecting_a_merged_follower_review_is_free_and_sends_the_unit_back_to_the_queue()
    {
        Review review = UnitReview();

        ReviewOutcome rejected = ReviewDecisions.Reject(review, Request(), Target(TextStatus.Incelemede));

        Assert.Equal(ReviewStatus.Reddedildi, rejected.Durum);
        Assert.Equal(TextStatus.Taslak, rejected.UnitMetinDurumu);
        Assert.Null(rejected.UnitText);
    }

    // ---- Ileti belirteci (editor OFFSET_MARKER = 'Ofsetli') ----

    [Fact]
    public void The_offset_messages_start_with_Ofsetli_and_the_merged_follower_message_does_not_contain_it()
    {
        UnitReviewState offsets = Unit(UnitKind.Risale, sourceKind: SourceKind.Risale, hasOffsetData: true);
        UnitReviewState follower = Unit(UnitKind.Meal, isMergedFollower: true);

        DomainException offsetError = Assert.Throws<DomainException>(
            () => ReviewDecisions.ApplyUnitText(offsets, Payload(CurrentText), Payload(ProposedText), null));
        DomainException followerError = Assert.Throws<DomainException>(
            () => ReviewDecisions.ApplyUnitText(follower, Payload(CurrentText), Payload(ProposedText), null));

        Assert.StartsWith("Ofsetli", offsetError.Message, StringComparison.Ordinal);
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, followerError.Code);
        Assert.DoesNotContain("Ofsetli", followerError.Message, StringComparison.Ordinal);
        Assert.Contains("birlesik_ile", followerError.Message, StringComparison.Ordinal);
    }

    // ---- Hat kokenli meal: onceki bos (ilk yukleme) ve onceki dolu (kaynak farki) ----

    [Fact]
    public void A_hat_meal_review_with_an_empty_onceki_is_approved_by_two_editors_and_applies_the_text_with_rev_plus_one()
    {
        Review review = UnitReview(onceki: "null");

        ReviewOutcome first = ReviewDecisions.Approve(review, Request(), Target(follower: false));
        first.ApplyTo(review);
        ReviewOutcome second = ReviewDecisions.Approve(review, Request("test-editor-2"), Target(TextStatus.Incelemede, follower: false));

        Assert.Equal(TextStatus.Incelemede, first.UnitMetinDurumu);
        Assert.Null(first.UnitText);
        Assert.Equal(ReviewStatus.Onaylandi, second.Durum);
        Assert.Equal(TextStatus.Onayli, second.UnitMetinDurumu);
        Assert.Equal(ProposedText, second.UnitText!.Value.Metin);
        Assert.Equal(2, second.UnitText.Value.Rev);
    }

    [Fact]
    public void A_source_difference_review_with_a_stale_onceki_is_refused_as_a_state_conflict()
    {
        Review review = UnitReview(onceki: Payload("Baska bir metin"));

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), Target(follower: false))));
    }
}
