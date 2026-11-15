using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>Yeniden dogrulama kaydinin karari (K-51 madde 8): onay "hala gecerli", ret "gecersiz". Veri sentetiktir.</summary>
public class ReviewRevalidationDecisionTests
{
    private const string Flag = """{"yeniden_dogrula": true, "neden": "uretilmedi"}""";

    private static Review Revalidation(string? onerilen = Flag, XrefOrigin koken = XrefOrigin.Hat, string oneren = "hat", ReviewStatus durum = ReviewStatus.Acik)
    {
        Review review = StatusReview(koken: koken, oneren: oneren, durum: durum);
        review.Onerilen = onerilen;
        return review;
    }

    private static ReviewTargetState Target(XrefStatus status = XrefStatus.Onayli) =>
        ReviewTargetState.ForLink(
            status,
            new LinkRowState(XrefType.Iktibas, AnchorRef.Parse("rn:sozler:soz-10:p4"), new AnchorSpan(5, 30), AnchorRef.Parse("q:2:255"), null, XrefOrigin.Hat, "{}"));

    [Theory]
    [InlineData("""{"yeniden_dogrula": true}""", true)]
    [InlineData("""{"yeniden_dogrula": true, "neden": "uc_metni_degisti"}""", true)]
    [InlineData("""{"yeniden_dogrula": false}""", false)]
    [InlineData("""{"yeniden_dogrula": "true"}""", false)]
    [InlineData("""{"neden": "uretilmedi"}""", false)]
    [InlineData("[]", false)]
    [InlineData("bozuk", false)]
    [InlineData("", false)]
    [InlineData(null, false)]
    public void The_flag_is_recognised_only_as_a_json_true_on_a_link_status_record(string? onerilen, bool expected)
    {
        Assert.Equal(expected, ReviewDecisions.IsRevalidation(ReviewTargets.Xref, ReviewFields.Status, onerilen));
    }

    [Fact]
    public void The_flag_does_not_make_other_targets_revalidation_records()
    {
        Assert.False(ReviewDecisions.IsRevalidation(ReviewTargets.Lemma, ReviewFields.KokEslemesi, Flag));
        Assert.False(ReviewDecisions.IsRevalidation(ReviewTargets.Xref, "baska", Flag));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Approval_keeps_the_approved_link_untouched(bool turkish) => CultureScope.For(turkish, () =>
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(Revalidation(), Request(), Target());

        Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
        Assert.Equal(ReviewActions.Onayla, outcome.Eylem);
        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        Assert.Null(outcome.Link);
        Assert.Null(outcome.Duzenlenen);
        Assert.Equal("test-editor-1", outcome.Inceleyen);
    });

    [Fact]
    public void Rejection_turns_the_approved_link_red()
    {
        ReviewOutcome outcome = ReviewDecisions.Reject(Revalidation(), Request(), Target());

        Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
        Assert.Equal(XrefStatus.Red, outcome.TargetStatus);
        Assert.Null(outcome.Link);
    }

    [Fact]
    public void An_edited_value_is_422_even_when_it_is_empty_or_unchanged()
    {
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(Revalidation(), Request(duzenlenen: """{"type": "atif"}"""), Target())));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(Revalidation(), Request(duzenlenen: "{}"), Target())));
    }

    [Theory]
    [InlineData(XrefStatus.Aday)]
    [InlineData(XrefStatus.Red)]
    public void The_link_must_be_approved_for_both_decisions(XrefStatus status)
    {
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(Revalidation(), Request(), Target(status))));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Reject(Revalidation(), Request(), Target(status))));
    }

    [Fact]
    public void The_four_eyes_rule_and_the_input_checks_are_the_same_as_for_other_records()
    {
        Review own = Revalidation(koken: XrefOrigin.Editor, oneren: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(own, Request(), Target())));
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(own, Request(), Target()).Durum);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(Revalidation(), Request(gerekce: " "), Target())));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(Revalidation(durum: ReviewStatus.Onaylandi), Request(), Target())));
    }

    [Fact]
    public void A_record_with_the_expert_status_is_decidable()
    {
        Assert.Equal(ReviewStatus.Onaylandi, ReviewDecisions.Approve(Revalidation(durum: ReviewStatus.Uzmanda), Request(), Target()).Durum);
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(Revalidation(durum: ReviewStatus.Uzmanda), Request(), Target()).Durum);
    }

    [Fact]
    public void A_revalidation_record_is_never_bulk_eligible()
    {
        DomainException e = Assert.Throws<DomainException>(
            () => ReviewDecisions.RequireBulkEligible(XrefType.Iktibas, 0.97f, """{"matched_words": 9}""", hasEdit: false, revalidation: true));

        Assert.Equal(DomainErrorCodes.TopluUygunDegil, e.Code);
    }
}
