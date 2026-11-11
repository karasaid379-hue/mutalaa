using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Ofsetli turev alanlar (marks, sentences): ofsetli alanlarin yeniden hesabi BC-59'da (A20) yapilana kadar metin degisimi desteklenmez (422 inceleme-desteklenmiyor);
/// durum onayi (metin degismez) ve ret serbesttir. Yardimci ve karar kurali, tr-TR dahil.
/// </summary>
public class ReviewOffsetDataTests
{
    private static ReviewTargetState Target(UnitKind kind = UnitKind.Risale, TextStatus durum = TextStatus.Taslak, bool offsets = true) =>
        ReviewTargetState.ForUnit(Unit(kind, durum, sourceKind: kind == UnitKind.Risale ? SourceKind.Risale : SourceKind.Meal, hasOffsetData: offsets));

    // ---- HasOffsetData ----

    [Theory]
    [InlineData(null, 0, false)]
    [InlineData("", 0, false)]
    [InlineData("[]", 0, false)]
    [InlineData("  [ ]  ", 0, false)]
    [InlineData("null", 0, false)]
    [InlineData("[]", 1, true)]
    [InlineData(null, 3, true)]
    [InlineData("[{\"tur\":\"vurgu\",\"baslangic\":0,\"bitis\":4}]", 0, true)]
    [InlineData("{}", 0, true)]
    [InlineData("{bozuk", 0, true)]
    public void HasOffsetData_is_true_for_a_non_empty_marks_array_or_any_sentence(string? marks, int sentences, bool expected)
    {
        foreach (bool turkish in new[] { false, true })
        {
            CultureScope.For(turkish, () => Assert.Equal(expected, ReviewDecisions.HasOffsetData(marks, sentences)));
        }
    }

    // ---- ApplyUnitText ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ApplyUnitText_refuses_a_real_text_change_when_the_unit_has_offset_data(bool turkish) => CultureScope.For(turkish, () =>
    {
        UnitReviewState unit = Unit(UnitKind.Risale, sourceKind: SourceKind.Risale, hasOffsetData: true);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), null)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), Payload(EditedText))));
    });

    [Fact]
    public void ApplyUnitText_leaves_an_unchanged_text_or_no_value_alone_even_with_offset_data()
    {
        UnitReviewState unit = Unit(UnitKind.Risale, sourceKind: SourceKind.Risale, hasOffsetData: true);

        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(CurrentText), null));
        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(CurrentText + "  "), null));
        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), "null", null));
        Assert.Null(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), null, null));
    }

    [Fact]
    public void ApplyUnitText_still_applies_the_text_when_the_unit_has_no_offset_data()
    {
        UnitReviewState unit = Unit(UnitKind.Risale, sourceKind: SourceKind.Risale);

        Assert.NotNull(ReviewDecisions.ApplyUnitText(unit, Payload(CurrentText), Payload(ProposedText), null));
    }

    // ---- Tek onayli birim ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_single_approval_that_changes_the_text_is_refused_and_a_status_only_approval_or_rejection_is_free(bool turkish) => CultureScope.For(turkish, () =>
    {
        Review changing = UnitReview();
        Review statusOnly = UnitReview(onerilen: "null");

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(changing, Request(), Target())));
        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(changing, Request(duzenlenen: Payload(EditedText)), Target())));

        ReviewOutcome status = ReviewDecisions.Approve(statusOnly, Request(), Target());
        Assert.Equal(TextStatus.Onayli, status.UnitMetinDurumu);
        Assert.Null(status.UnitText);

        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(changing, Request(), Target()).Durum);
    });

    // ---- Iki asamali onay (meal, tefsir) ----

    [Fact]
    public void The_first_approval_of_a_two_stage_review_is_refused_early_when_the_text_would_change()
    {
        Review review = UnitReview();

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(review, Request(), Target(UnitKind.Meal))));
        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Payload(EditedText)), Target(UnitKind.Meal))));
    }

    [Fact]
    public void A_two_stage_status_only_approval_and_rejection_are_free_with_offset_data()
    {
        Review statusOnly = UnitReview(onerilen: "null");
        Review changing = UnitReview();

        ReviewOutcome first = ReviewDecisions.Approve(statusOnly, Request(), Target(UnitKind.Meal));
        first.ApplyTo(statusOnly);
        ReviewOutcome second = ReviewDecisions.Approve(statusOnly, Request("test-editor-2"), Target(UnitKind.Meal, TextStatus.Incelemede));

        Assert.Equal(ReviewStatus.Acik, first.Durum);
        Assert.Equal(ReviewStatus.Onaylandi, second.Durum);
        Assert.Null(second.UnitText);
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(changing, Request(), Target(UnitKind.Meal)).Durum);
    }

    [Fact]
    public void The_second_approval_is_also_refused_when_the_text_would_change()
    {
        // Ilk onay offset bilgisi yokken (ornegin sonradan eklenmis turev alan) verilmis olabilir; ikinci onay yine korur.
        Review review = UnitReview(inceleyen: "test-editor-1");

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-2"), Target(UnitKind.Meal, TextStatus.Incelemede))));
    }
}
