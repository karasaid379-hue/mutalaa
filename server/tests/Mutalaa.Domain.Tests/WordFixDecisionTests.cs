using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// quran_word_fix adayi (K-51 madde 2, A18.4): alana gore deger kurali, aday acma ve Duzenle ve onayla. Degerler sentetiktir;
/// kimlikler ve "deneme" metinleri Kur'an ya da QAC verisi degildir.
/// </summary>
public class WordFixDecisionTests
{
    private static readonly AnchorRef Word = AnchorRef.Parse("q:2:255:3");

    private static WordFixFacts RootOk => new(true, false, null);

    private static WordFixFacts LemmaOk(string lang = "ar") => new(false, true, lang);

    private static string CodeOf(Action action) => Assert.Throws<DomainException>(action).Code;

    // --- Deger kurali ---

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_root_id_must_be_a_canonical_id_of_an_existing_root(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Equal("17", WordFixValues.Normalize("root_id", "17", RootOk, "new_value"));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("root_id", "17", new WordFixFacts(false, false, null), "new_value")));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("root_id", "17", null, "new_value")));
    });

    [Theory]
    [InlineData("017")]
    [InlineData("0")]
    [InlineData("-3")]
    [InlineData("+3")]
    [InlineData("1.5")]
    [InlineData("abc")]
    [InlineData("١٢")] // Arapca-Hindi rakamlar
    [InlineData(" 7")]
    [InlineData("99999999999")]
    public void A_non_canonical_id_is_a_validation_error(string value)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("lemma_id", value, LemmaOk(), "new_value")));
        Assert.False(WordFixValues.TryParseId(value, out _));
    }

    [Fact]
    public void A_lemma_id_must_exist_and_be_arabic()
    {
        Assert.Equal("42", WordFixValues.Normalize("lemma_id", "42", LemmaOk(), "new_value"));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("lemma_id", "42", LemmaOk("tr"), "new_value")));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("lemma_id", "42", new WordFixFacts(false, false, null), "new_value")));
    }

    [Theory]
    [InlineData("N", "N")]
    [InlineData("  PRON ", "PRON")]
    [InlineData("12345678901234567890", "12345678901234567890")]
    public void A_pos_is_non_blank_and_at_most_twenty_code_points(string value, string expected)
    {
        Assert.Equal(expected, WordFixValues.Normalize("pos", value, null, "new_value"));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(null)]
    [InlineData("123456789012345678901")]
    public void A_blank_or_too_long_pos_is_a_validation_error(string? value)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("pos", value, null, "new_value")));
    }

    [Fact]
    public void Twenty_supplementary_code_points_are_still_twenty()
    {
        string twenty = string.Concat(Enumerable.Repeat("\U0001F600", 20));

        Assert.Equal(twenty, WordFixValues.Normalize("pos", twenty, null, "new_value"));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("pos", twenty + "\U0001F600", null, "new_value")));
    }

    [Theory]
    [InlineData("""{"zaman": "gecmis"}""")]
    [InlineData("{}")]
    [InlineData("""  {"a": 1}  """)]
    public void Features_must_be_a_json_object_text(string value)
    {
        Assert.Equal(value.Trim(), WordFixValues.Normalize("features", value, null, "new_value"));
    }

    [Theory]
    [InlineData("[1]")]
    [InlineData("\"metin\"")]
    [InlineData("5")]
    [InlineData("{bozuk")]
    [InlineData("null")]
    public void A_features_value_that_is_not_a_json_object_is_a_validation_error(string value)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize("features", value, null, "new_value")));
    }

    [Theory]
    [InlineData("Pos")]
    [InlineData("")]
    [InlineData("text")]
    public void An_unknown_field_is_a_validation_error(string field)
    {
        Assert.False(WordFixValues.IsField(field));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => WordFixValues.Normalize(field, "N", null, "new_value")));
    }

    // --- Aday acma ---

    [Fact]
    public void A_proposal_builds_an_aday_fix_and_an_editor_review()
    {
        Guid id = Guid.CreateVersion7();

        (QuranWordFix fix, Review review) = WordFixProposals.Open(id, Word, "root_id", "17", "Deneme gerekcesi", "9", RootOk, "editor-a");

        Assert.Equal(id, fix.Id);
        Assert.Equal(Word, fix.Anchor);
        Assert.Equal("root_id", fix.Field);
        Assert.Equal("9", fix.QacValue);
        Assert.Equal("17", fix.NewValue);
        Assert.Equal("Deneme gerekcesi", fix.Reason);
        Assert.Equal(XrefStatus.Aday, fix.Status);
        Assert.Equal("editor-a", fix.Editor);

        Assert.Equal(ReviewTargets.QuranWordFix, review.HedefTablo);
        Assert.Equal(id.ToString("D"), review.HedefAnahtar);
        Assert.Equal("root_id", review.Alan);
        Assert.Equal(ReviewActions.Oner, review.Eylem);
        Assert.Equal(XrefOrigin.Editor, review.Koken);
        Assert.Equal("editor-a", review.Oneren);
        using JsonDocument proposal = JsonDocument.Parse(review.Onerilen!);
        Assert.Equal("17", proposal.RootElement.GetProperty("new_value").GetString());
        Assert.Equal("9", proposal.RootElement.GetProperty("qac_value").GetString());
        Assert.Equal("Deneme gerekcesi", proposal.RootElement.GetProperty("reason").GetString());
    }

    [Fact]
    public void A_proposal_without_a_current_qac_value_writes_null()
    {
        (_, Review review) = WordFixProposals.Open(Guid.CreateVersion7(), Word, "pos", "N", "Deneme", null, null, "editor-a");

        using JsonDocument proposal = JsonDocument.Parse(review.Onerilen!);
        Assert.Equal(JsonValueKind.Null, proposal.RootElement.GetProperty("qac_value").ValueKind);
    }

    [Theory]
    [InlineData("q:2:255")] // ayet
    [InlineData("q:2:255:3-7")] // aralik
    [InlineData("q:2:255-257")]
    [InlineData("konu:tevhid")]
    [InlineData("meal:elmalili:2:255")]
    public void Only_a_single_word_anchor_can_carry_a_proposal(string anchor)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => WordFixProposals.Open(Guid.CreateVersion7(), AnchorRef.Parse(anchor), "pos", "N", "Deneme", null, null, "editor-a")));
    }

    [Theory]
    [InlineData(null, "pos", "N", "Deneme")]
    [InlineData("  ", "pos", "N", "Deneme")]
    [InlineData("editor-a", "kind", "N", "Deneme")]
    [InlineData("editor-a", null, "N", "Deneme")]
    [InlineData("editor-a", "pos", "N", "")]
    [InlineData("editor-a", "pos", "N", null)]
    [InlineData("editor-a", "pos", "", "Deneme")]
    public void A_proposal_needs_an_actor_a_known_field_a_reason_and_a_value(string? actor, string? field, string? value, string? reason)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => WordFixProposals.Open(Guid.CreateVersion7(), Word, field, value, reason, null, null, actor)));
    }

    [Fact]
    public void A_reason_over_two_thousand_code_points_is_refused()
    {
        string reason = new('a', ReviewDecisions.MaxGerekceLength + 1);

        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => WordFixProposals.Open(Guid.CreateVersion7(), Word, "pos", "N", reason, null, null, "editor-a")));
    }

    // --- Duzenle ve onayla ---

    private static Review FixReview(string alan = "root_id", XrefOrigin koken = XrefOrigin.Editor, string oneren = "editor-a") =>
        new()
        {
            HedefTablo = ReviewTargets.QuranWordFix,
            HedefAnahtar = Guid.Empty.ToString("D"),
            Alan = alan,
            Eylem = ReviewActions.Oner,
            Koken = koken,
            Oneren = oneren,
        };

    private static string NewValueJson(string value) => JsonSerializer.Serialize(new Dictionary<string, string> { ["new_value"] = value });

    [Fact]
    public void An_edited_new_value_is_validated_applied_and_recorded()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(
            FixReview(),
            Request(actor: "editor-b", duzenlenen: NewValueJson("21")),
            ReviewTargetState.ForFix(XrefStatus.Aday, "root_id", RootOk));

        Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
        Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        Assert.Equal("21", outcome.WordFixNewValue);
        using JsonDocument stored = JsonDocument.Parse(outcome.Duzenlenen!);
        Assert.Equal("21", stored.RootElement.GetProperty("new_value").GetString());
    }

    [Fact]
    public void An_edited_value_of_a_missing_root_is_a_validation_error()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(
                FixReview(),
                Request(actor: "editor-b", duzenlenen: NewValueJson("21")),
                ReviewTargetState.ForFix(XrefStatus.Aday, "root_id", new WordFixFacts(false, false, null)))));
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("""{"anlam_kisa": "x"}""")]
    [InlineData("""{"new_value": 5}""")]
    [InlineData("""{"new_value": "N", "ek": 1}""")]
    [InlineData("{bozuk")]
    [InlineData("[1]")]
    public void A_malformed_new_value_payload_is_a_validation_error(string payload)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(FixReview("pos"), Request(actor: "editor-b", duzenlenen: payload), ReviewTargetState.ForFix(XrefStatus.Aday, "pos"))));
    }

    [Fact]
    public void The_proposer_cannot_approve_their_own_fix_but_a_plain_approval_by_another_editor_works()
    {
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(FixReview("pos"), Request(actor: "EDITOR-A", duzenlenen: NewValueJson("N")), ReviewTargetState.ForFix(XrefStatus.Aday, "pos"))));

        ReviewOutcome plain = ReviewDecisions.Approve(FixReview("pos"), Request(actor: "editor-b"), ReviewTargetState.ForFix(XrefStatus.Aday, "pos"));
        Assert.Equal(ReviewActions.Onayla, plain.Eylem);
        Assert.Null(plain.WordFixNewValue);
    }

    [Fact]
    public void An_edit_on_a_mismatching_field_or_a_non_candidate_fix_is_refused()
    {
        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(FixReview("pos"), Request(actor: "editor-b", duzenlenen: NewValueJson("N")), ReviewTargetState.ForFix(XrefStatus.Aday, "features"))));
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(FixReview("pos"), Request(actor: "editor-b", duzenlenen: NewValueJson("N")), ReviewTargetState.ForFix(XrefStatus.Onayli, "pos"))));
    }

    [Fact]
    public void A_rejection_cannot_carry_a_new_value()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Reject(FixReview("pos"), Request(actor: "editor-b", duzenlenen: NewValueJson("N")), ReviewTargetState.ForFix(XrefStatus.Aday, "pos"))));
    }

    [Fact]
    public void The_payload_reader_returns_null_for_an_absent_value()
    {
        Assert.Null(WordFixPayload.ReadNewValue(null, "duzenlenen"));
        Assert.Null(WordFixPayload.ReadNewValue("null", "duzenlenen"));
        Assert.Equal("N", WordFixPayload.ReadNewValue(WordFixPayload.ToPayload("N"), "duzenlenen"));
    }
}
