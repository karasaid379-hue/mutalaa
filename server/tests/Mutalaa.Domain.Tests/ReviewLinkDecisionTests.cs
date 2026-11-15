using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Baglanti incelemesinde Duzelt ve onayla (A18.4), toplu onay uygunlugu, uzmanda durumunun karar akisi ve rol kurali.
/// Capalar biçim örnegidir; metin ve kanit sentetiktir.
/// </summary>
public class ReviewLinkDecisionTests
{
    private const string Hash16 = "0123456789abcdef";
    private const string OriginalEvidence = """{"matched_words": 9, "src_hash": "aaaaaaaaaaaaaaaa", "dst_hash": "bbbbbbbbbbbbbbbb", "run_id": "r1"}""";

    private static LinkRowState Row(XrefType type = XrefType.Iktibas, string dst = "q:2:255", AnchorSpan? dstSpan = null, string evidence = OriginalEvidence) =>
        new(type, AnchorRef.Parse("rn:sozler:soz-10:p4"), new AnchorSpan(5, 30), AnchorRef.Parse(dst), dstSpan, XrefOrigin.Hat, evidence);

    private static ReviewTargetState Target(LinkRowState? row = null, LinkDstFacts? dst = null, XrefStatus status = XrefStatus.Aday) =>
        ReviewTargetState.ForLink(status, row ?? Row(), dst ?? new LinkDstFacts(true, 120, 10, "fedcba9876543210ffff"));

    private static string Edit(string? dstAnchor = null, int[]? span = null, string? type = null)
    {
        Dictionary<string, object> map = [];
        if (dstAnchor is not null)
        {
            map["dst_anchor"] = dstAnchor;
        }

        if (span is not null)
        {
            map["dst_span"] = span;
        }

        if (type is not null)
        {
            map["type"] = type;
        }

        return JsonSerializer.Serialize(map);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_target_edit_changes_the_destination_marks_the_editor_origin_and_renews_the_dst_hash(bool turkish) => CultureScope.For(turkish, () =>
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(dstAnchor: "q:3:7")), Target());

        Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
        Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        LinkUpdate update = Assert.NotNull(outcome.Link);
        Assert.Equal(XrefType.Iktibas, update.Type);
        Assert.Equal(AnchorRef.Parse("q:3:7"), update.DstAnchor);
        Assert.Null(update.DstSpan);
        Assert.Equal(XrefOrigin.Editor, update.Origin);

        using JsonDocument evidence = JsonDocument.Parse(update.Evidence);
        Assert.True(evidence.RootElement.GetProperty("editor_duzeltmesi").GetBoolean());
        Assert.Equal("fedcba9876543210", evidence.RootElement.GetProperty("dst_hash").GetString());
        Assert.Equal("aaaaaaaaaaaaaaaa", evidence.RootElement.GetProperty("src_hash").GetString());
        Assert.Equal("r1", evidence.RootElement.GetProperty("run_id").GetString());

        using JsonDocument stored = JsonDocument.Parse(outcome.Duzenlenen!);
        Assert.Equal("q:3:7", stored.RootElement.GetProperty("dst_anchor").GetString());
    });

    [Fact]
    public void A_span_correction_keeps_the_dst_hash_because_the_unit_is_the_same()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(span: [3, 8])), Target());

        LinkUpdate update = Assert.NotNull(outcome.Link);
        Assert.Equal(new AnchorSpan(3, 8), update.DstSpan);
        Assert.Equal(AnchorRef.Parse("q:2:255"), update.DstAnchor);
        using JsonDocument evidence = JsonDocument.Parse(update.Evidence);
        Assert.Equal("bbbbbbbbbbbbbbbb", evidence.RootElement.GetProperty("dst_hash").GetString());
        Assert.True(evidence.RootElement.GetProperty("editor_duzeltmesi").GetBoolean());
        Assert.Equal(XrefOrigin.Editor, update.Origin);
    }

    [Fact]
    public void A_type_change_between_the_editable_types_is_applied()
    {
        LinkUpdate update = Assert.NotNull(ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(type: "ima")), Target()).Link);

        Assert.Equal(XrefType.Ima, update.Type);
        Assert.Equal(XrefOrigin.Editor, update.Origin);
    }

    [Fact]
    public void A_type_change_on_a_kok_row_is_refused_with_inceleme_desteklenmiyor()
    {
        ReviewTargetState target = Target(Row(type: XrefType.Kok));

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(type: "iktibas")), target)));
    }

    [Fact]
    public void An_edit_equal_to_the_row_is_a_plain_approval_and_keeps_the_origin_and_evidence()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(type: "iktibas")), Target());

        Assert.Equal(ReviewActions.Onayla, outcome.Eylem);
        Assert.Null(outcome.Link);
        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
    }

    [Theory]
    [InlineData(0, 3)]
    [InlineData(3, 12)]
    [InlineData(5, 5)]
    public void A_span_outside_the_ayah_word_count_is_a_validation_error_and_changes_nothing(int start, int end)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(span: [start, end])), Target())));
    }

    [Fact]
    public void A_new_destination_unit_that_does_not_exist_is_a_validation_error()
    {
        ReviewTargetState target = Target(dst: new LinkDstFacts(false, 0, 0, null));

        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(dstAnchor: "q:3:7")), target)));
    }

    [Fact]
    public void A_non_candidate_target_cannot_be_corrected()
    {
        ReviewTargetState target = Target(status: XrefStatus.Onayli);

        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: Edit(type: "ima")), target)));
    }

    [Fact]
    public void An_editor_cannot_approve_their_own_correction_proposal()
    {
        Review review = StatusReview(koken: XrefOrigin.Editor, oneren: "test-editor-1");

        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(review, Request(actor: "TEST-EDITOR-1", duzenlenen: Edit(type: "ima")), Target())));
    }

    [Theory]
    [InlineData("{bozuk")]
    [InlineData("{}")]
    [InlineData("""{"metin": "x"}""")]
    [InlineData("""{"type": "bilinmeyen"}""")]
    public void A_malformed_correction_is_a_validation_error(string payload)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(StatusReview(), Request(duzenlenen: payload), Target())));
    }

    [Fact]
    public void A_rejection_cannot_carry_a_correction()
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(StatusReview(), Request(duzenlenen: Edit(type: "ima")), Target())));
    }

    [Fact]
    public void A_plain_approval_without_a_value_still_works_without_the_link_row()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(StatusReview(), Request(), ReviewTargetState.ForStatus(XrefStatus.Aday));

        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        Assert.Null(outcome.Link);
    }

    // --- Toplu uygunluk ---

    [Fact]
    public void Bulk_approval_passes_only_for_the_toplu_class_without_an_edit()
    {
        string strong = """{"matched_words": 9, "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""";

        ReviewDecisions.RequireBulkEligible(XrefType.Iktibas, 0.5f, strong, hasEdit: false);

        Assert.Equal(DomainErrorCodes.TopluUygunDegil, CodeOf(() => { ReviewDecisions.RequireBulkEligible(XrefType.Iktibas, 0.5f, strong, hasEdit: true); return 0; }));
    }

    [Theory]
    [InlineData(XrefType.Atif, 0.2f, "{}")] // tutarsiz
    [InlineData(XrefType.Iktibas, 0.5f, "{}")] // gri
    [InlineData(XrefType.Iktibas, 0.9f, "{}")] // diger
    [InlineData(XrefType.Kok, 0.97f, """{"matched_words": 9, "coverage": 1, "phrase_freq": 1}""")]
    public void Bulk_approval_refuses_other_classes_with_toplu_uygun_degil(XrefType type, float confidence, string evidence)
    {
        Assert.Equal(
            DomainErrorCodes.TopluUygunDegil,
            CodeOf(() => { ReviewDecisions.RequireBulkEligible(type, confidence, evidence, hasEdit: false); return 0; }));
    }

    // --- uzmanda ve roller ---

    [Fact]
    public void An_expert_record_is_decided_like_an_open_one()
    {
        Review review = StatusReview(durum: ReviewStatus.Uzmanda);

        Assert.Equal(ReviewStatus.Onaylandi, ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)).Durum);
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)).Durum);
    }

    [Theory]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    [InlineData(ReviewStatus.GeriAlindi)]
    public void A_decided_record_still_gets_durum_gecisi_gecersiz(ReviewStatus durum)
    {
        Review review = StatusReview(durum: durum);

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday))));
    }

    [Theory]
    [InlineData(ReviewStatus.Uzmanda, true, false, false)]
    [InlineData(ReviewStatus.Uzmanda, false, true, true)]
    [InlineData(ReviewStatus.Uzmanda, true, true, true)]
    [InlineData(ReviewStatus.Uzmanda, false, false, false)]
    [InlineData(ReviewStatus.Acik, true, false, true)]
    [InlineData(ReviewStatus.Acik, false, true, false)]
    [InlineData(ReviewStatus.Acik, true, true, true)]
    [InlineData(ReviewStatus.Acik, false, false, false)]
    [InlineData(ReviewStatus.Onaylandi, false, true, true)]
    [InlineData(ReviewStatus.Reddedildi, true, false, true)]
    public void Only_the_expert_decides_an_expert_record_and_only_editor_or_admin_an_open_one(ReviewStatus durum, bool editorOrAdmin, bool uzman, bool expected)
    {
        Assert.Equal(expected, ReviewRoles.CanDecide(durum, editorOrAdmin, uzman));
    }
}
