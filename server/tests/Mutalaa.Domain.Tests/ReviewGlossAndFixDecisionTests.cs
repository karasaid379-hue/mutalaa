using System.Text.Json;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Duzenle ve onayla (lemma_gloss, K-50 madde 6) ve quran_word_fix alan eslesmesi (A17.4). Sentetik anlam metinleri;
/// ortak yardimcilar Turk kulturunde de calisir.
/// </summary>
public class ReviewGlossAndFixDecisionTests
{
    private const string RowAnlam = "deneme anlami";
    private const string Hazir = "kaynak:quranwbw-tr";

    private static Review GlossReview(string? onerilen = null) =>
        new()
        {
            HedefTablo = ReviewTargets.LemmaGloss,
            HedefAnahtar = "7",
            Alan = ReviewFields.AnlamKisa,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Onerilen = onerilen ?? OnerilenJson(RowAnlam),
        };

    private static string OnerilenJson(string anlam) =>
        JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["anlam_kisa"] = anlam,
            ["dagilim"] = new[] { new Dictionary<string, object> { ["anlam"] = anlam, ["sayi"] = 5 } },
            ["baskin_pay"] = 0.9,
        });

    private static string Edit(string anlam) => JsonSerializer.Serialize(new Dictionary<string, string> { ["anlam_kisa"] = anlam });

    private static ReviewTargetState Gloss(string version = "1", string origin = Hazir, XrefStatus status = XrefStatus.Aday) =>
        ReviewTargetState.ForGloss(status, new GlossReviewState(RowAnlam, version, origin));

    [Fact]
    public void A_gloss_edit_updates_the_text_hash_version_and_origin_and_records_duzenle_onayla()
    {
        CultureScope.For(true, () =>
        {
            ReviewOutcome outcome = ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit("yeni anlam")), Gloss());

            Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
            Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
            Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
            LemmaGlossUpdate update = Assert.NotNull(outcome.Gloss);
            Assert.Equal("yeni anlam", update.AnlamKisa);
            Assert.Equal(ContentHash.Compute("yeni anlam"), update.ContentHash);
            Assert.Equal("2", update.Version);
            Assert.Equal("editor", update.Origin);
            using JsonDocument stored = JsonDocument.Parse(outcome.Duzenlenen!);
            Assert.Equal("yeni anlam", stored.RootElement.GetProperty("anlam_kisa").GetString());
        });
    }

    [Fact]
    public void An_approval_without_an_edit_is_a_status_approval_and_keeps_the_row_as_is()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(GlossReview(), Request(), Gloss());

        Assert.Equal(ReviewActions.Onayla, outcome.Eylem);
        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        Assert.Null(outcome.Gloss);
        Assert.Null(outcome.Duzenlenen);
    }

    [Fact]
    public void An_edit_equal_to_the_proposal_changes_the_version_when_the_row_differs_but_keeps_the_origin()
    {
        ReviewTargetState row = ReviewTargetState.ForGloss(XrefStatus.Aday, new GlossReviewState("baska", "3", Hazir));

        LemmaGlossUpdate update = Assert.NotNull(ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(RowAnlam)), row).Gloss);

        Assert.Equal(RowAnlam, update.AnlamKisa);
        Assert.Equal("4", update.Version);
        Assert.Equal(Hazir, update.Origin);
    }

    [Fact]
    public void An_edit_equal_to_the_current_row_does_not_bump_the_version()
    {
        LemmaGlossUpdate update = Assert.NotNull(ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(RowAnlam)), Gloss(version: "5")).Gloss);

        Assert.Equal("5", update.Version);
        Assert.Equal(Hazir, update.Origin);
        Assert.Equal(ContentHash.Compute(RowAnlam), update.ContentHash);
    }

    [Fact]
    public void Without_a_proposal_the_edited_value_makes_the_origin_editor()
    {
        Review review = GlossReview();
        review.Onerilen = null;

        LemmaGlossUpdate update = Assert.NotNull(ReviewDecisions.Approve(review, Request(duzenlenen: Edit("yeni anlam")), Gloss()).Gloss);

        Assert.Equal("editor", update.Origin);
    }

    [Fact]
    public void The_edited_value_is_canonicalised_to_NFC_and_trimmed()
    {
        // "e" + U+0301 (birlesik vurgu) NFC'de tek kod noktasi U+00E9 olur.
        string decomposed = "  café  ";

        LemmaGlossUpdate update = Assert.NotNull(ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(decomposed)), Gloss()).Gloss);

        Assert.Equal("café", update.AnlamKisa);
        Assert.Equal(ContentHash.Compute("café"), update.ContentHash);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\t \n")]
    public void An_empty_or_whitespace_only_value_is_a_validation_error(string value)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(value)), Gloss())));
    }

    [Fact]
    public void A_value_longer_than_200_code_points_is_a_validation_error_and_exactly_200_is_accepted()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(new string('a', 201))), Gloss())));

        // 200 kod noktasi: vekil ciftler (UTF-16'da 400) tek kod noktasi sayilir.
        string pairs = string.Concat(Enumerable.Repeat(char.ConvertFromUtf32(0x1F600), 200));
        LemmaGlossUpdate ok = Assert.NotNull(ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit(pairs)), Gloss()).Gloss);
        Assert.Equal(pairs, ok.AnlamKisa);
    }

    [Fact]
    public void A_non_candidate_gloss_conflicts_even_with_an_edit()
    {
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit("yeni")), Gloss(status: XrefStatus.Onayli))));
    }

    [Fact]
    public void A_gloss_rejection_cannot_carry_a_value()
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(GlossReview(), Request(duzenlenen: Edit("yeni")), Gloss())));
    }

    [Fact]
    public void An_edit_payload_without_anlam_kisa_is_a_validation_error()
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: "{}"), Gloss())));
    }

    [Theory]
    [InlineData("surah_alias")]
    [InlineData("lemma")]
    public void Other_status_targets_still_refuse_an_editor_value(string table)
    {
        Review review = StatusReview(table, ReviewFields.Status);

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Edit("yeni")), ReviewTargetState.ForStatus(XrefStatus.Aday))));
    }

    [Fact]
    public void A_non_numeric_stored_version_cannot_be_bumped()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(GlossReview(), Request(duzenlenen: Edit("yeni")), Gloss(version: "v1"))));
    }

    [Theory]
    [InlineData("root_id")]
    [InlineData("lemma_id")]
    [InlineData("pos")]
    [InlineData("features")]
    public void A_fix_decision_needs_the_review_field_to_match_the_fix_field(string alan)
    {
        Review review = StatusReview(ReviewTargets.QuranWordFix, alan);
        ReviewTargetState target = ReviewTargetState.ForFix(XrefStatus.Aday, alan);

        Assert.Equal(XrefStatus.Onayli, ReviewDecisions.Approve(review, Request(), target).TargetStatus);
        Assert.Equal(XrefStatus.Red, ReviewDecisions.Reject(review, Request(), target).TargetStatus);
    }

    [Theory]
    [InlineData("root_id", "lemma_id")]
    [InlineData("pos", "features")]
    [InlineData("features", "Features")]
    [InlineData("pos", "")]
    [InlineData("pos", "gecersiz_alan")]
    public void A_field_mismatch_is_refused_on_approve_and_reject(string alan, string fixField)
    {
        Review review = StatusReview(ReviewTargets.QuranWordFix, alan);
        ReviewTargetState target = ReviewTargetState.ForFix(XrefStatus.Aday, fixField);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(review, Request(), target)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Reject(review, Request(), target)));
    }

    [Fact]
    public void A_fix_without_its_field_is_a_programming_error_not_a_decision()
    {
        Review review = StatusReview(ReviewTargets.QuranWordFix, "pos");

        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)));
    }

    [Fact]
    public void An_unsupported_review_alan_is_refused_before_the_target_is_read()
    {
        Review review = StatusReview(ReviewTargets.QuranWordFix, "status");

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForFix(XrefStatus.Aday, "status"))));
    }
}
