using System.Text.Json;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Lugat maddesi incelemesi (K-51 madde 9 ve 10; K-50 madde 6 deseni): hedef anahtari, Duzenle ve onayla, bos tanimla onay yok,
/// anlam basvurusunun hedefe uygulanmamasi. Sentetik basliksozler; Turk kulturunde de calisir.
/// </summary>
public class ReviewLugatDecisionTests
{
    private const string Word = "deneme-sozcuk";

    private static Review LugatReview(string? onerilen = null) =>
        new()
        {
            HedefTablo = ReviewTargets.LugatMadde,
            HedefAnahtar = "risale-kelime-frekans:" + Word,
            Alan = ReviewFields.TanimTr,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Onerilen = onerilen ?? OnerilenJson(),
        };

    private static string OnerilenJson() =>
        JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["anlam_basvuru"] = new[] { new Dictionary<string, object> { ["anlam"] = "deneme basvurusu", ["sayi"] = 4 } },
            ["siklik"] = 120,
            ["kitaplar"] = 3,
        });

    private static string Edit(string tanim) => JsonSerializer.Serialize(new Dictionary<string, string> { ["tanim_tr"] = tanim });

    private static ReviewTargetState Row(string version = "1", XrefStatus status = XrefStatus.Aday) =>
        ReviewTargetState.ForLugat(status, new LugatReviewState(Word, version));

    [Fact]
    public void Lugat_madde_is_a_known_supported_status_target_with_the_tanim_tr_field()
    {
        Assert.Contains(ReviewTargets.LugatMadde, ReviewTargets.All);
        Assert.True(ReviewTargets.IsKnown("lugat_madde"));
        Assert.True(ReviewTargets.IsSupported("lugat_madde"));
        Assert.True(ReviewTargets.HasStatusColumn("lugat_madde"));
        Assert.True(ReviewDecisions.IsSupported("lugat_madde", "tanim_tr"));
        Assert.False(ReviewDecisions.IsSupported("lugat_madde", "status"));
        Assert.False(ReviewDecisions.IsSupported("lugat_madde", "metin"));
    }

    [Theory]
    [InlineData("risale-kelime-frekans:deneme", "risale-kelime-frekans", "deneme")]
    [InlineData("risale-kelime-frekans:a:b:c", "risale-kelime-frekans", "a:b:c")]
    [InlineData("a:b", "a", "b")]
    public void Keys_split_at_the_first_colon_and_the_headword_may_hold_colons(string key, string sourceId, string word)
    {
        ReviewTarget target = ReviewTargets.Parse("lugat_madde", key);

        Assert.Equal("lugat_madde", target.Table);
        Assert.Equal(sourceId, target.SourceId);
        Assert.Equal(word, target.Basliksoz);
    }

    [Theory]
    [InlineData("")]
    [InlineData("deneme")]
    [InlineData(":deneme")]
    [InlineData("risale-kelime-frekans:")]
    [InlineData("risale-kelime-frekans:   ")]
    [InlineData("Risale:deneme")]
    [InlineData("risale kelime:deneme")]
    [InlineData("risale_kelime:deneme")]
    public void Bad_lugat_keys_are_a_validation_error(string key) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse("lugat_madde", key)));

    [Fact]
    public void Approval_with_a_tanim_writes_the_text_hash_version_and_editor_origin()
    {
        CultureScope.For(true, () =>
        {
            ReviewOutcome outcome = ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit("deneme tanimi")), Row());

            Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
            Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
            Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
            LugatMaddeUpdate update = Assert.NotNull(outcome.Lugat);
            Assert.Equal("deneme tanimi", update.TanimTr);
            Assert.Equal(ContentHash.Compute(Word + "\n" + "deneme tanimi"), update.ContentHash);
            Assert.Equal("2", update.Version);
            Assert.Equal("editor", update.Origin);
            using JsonDocument stored = JsonDocument.Parse(outcome.Duzenlenen!);
            Assert.Equal("deneme tanimi", stored.RootElement.GetProperty("tanim_tr").GetString());
            Assert.Null(outcome.Gloss);
        });
    }

    [Fact]
    public void Approval_without_a_tanim_is_unprocessable_even_when_a_reference_meaning_is_proposed()
    {
        // K-51 madde 10: onerilen.anlam_basvuru salt basvurudur; tanim olarak onaylanmaz.
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(), Row())));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void A_blank_edited_tanim_is_a_validation_error(string tanim) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit(tanim)), Row())));

    [Fact]
    public void The_edited_tanim_must_be_a_string_field_of_the_payload()
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: "{\"tanim_tr\": 5}"), Row())));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: "{\"anlam_kisa\": \"x\"}"), Row())));
    }

    [Fact]
    public void An_overlong_tanim_is_a_validation_error()
    {
        string tanim = new('a', LugatMaddeText.MaxLength + 1);

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit(tanim)), Row())));
        Assert.Equal(LugatMaddeText.MaxLength, LugatMaddeText.Normalize(new string('a', LugatMaddeText.MaxLength), "x").Length);
    }

    [Fact]
    public void The_tanim_is_canonicalised_to_NFC()
    {
        // "e" + U+0301 (birlesik vurgu) NFC'de tek kod noktasi U+00E9 olur.
        string decomposed = "café";

        LugatMaddeUpdate update = Assert.NotNull(ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit(decomposed)), Row()).Lugat);

        Assert.Equal("café", update.TanimTr);
        Assert.Equal(LugatMaddeText.ComputeHash(Word, "café"), update.ContentHash);
    }

    [Fact]
    public void Approval_bumps_the_version_from_the_current_row()
    {
        LugatMaddeUpdate update = Assert.NotNull(ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit("t")), Row(version: "6")).Lugat);

        Assert.Equal("7", update.Version);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit("t")), Row(version: "bozuk"))));
    }

    [Fact]
    public void The_reference_meaning_is_never_applied_to_the_target()
    {
        LugatMaddeUpdate update = Assert.NotNull(ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit("yazilan tanim")), Row()).Lugat);

        Assert.DoesNotContain("deneme basvurusu", update.TanimTr, StringComparison.Ordinal);
        Assert.Equal("yazilan tanim", update.TanimTr);
    }

    [Fact]
    public void Rejection_marks_the_madde_red_and_carries_no_edit()
    {
        ReviewOutcome outcome = ReviewDecisions.Reject(LugatReview(), Request(), Row());

        Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
        Assert.Equal(XrefStatus.Red, outcome.TargetStatus);
        Assert.Null(outcome.Lugat);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(LugatReview(), Request(duzenlenen: Edit("x")), Row())));
    }

    [Theory]
    [InlineData(XrefStatus.Onayli)]
    [InlineData(XrefStatus.Red)]
    public void A_madde_that_is_not_a_candidate_cannot_be_decided(XrefStatus status)
    {
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(LugatReview(), Request(duzenlenen: Edit("t")), Row(status: status))));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Reject(LugatReview(), Request(), Row(status: status))));
    }

    [Fact]
    public void Other_status_targets_still_refuse_an_edited_value()
    {
        Review review = StatusReview(ReviewTargets.Xref);

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => ReviewDecisions.Approve(review, Request(duzenlenen: Edit("t")), ReviewTargetState.ForStatus(XrefStatus.Aday))));
    }

    [Fact]
    public void The_content_hash_covers_the_headword_and_the_tanim_with_an_LF_separator()
    {
        Assert.Equal(ContentHash.Compute("ab\nc"), LugatMaddeText.ComputeHash("ab", "c"));
        Assert.Equal(ContentHash.Compute("ab\n"), LugatMaddeText.ComputeHash("ab", null));
        Assert.NotEqual(LugatMaddeText.ComputeHash("ab", "c"), LugatMaddeText.ComputeHash("a", "bc"));
        Assert.Equal("siklik", LugatMaddeText.SiklikKey);
    }

    [Fact]
    public void An_unverified_candidate_is_not_verified_until_approved()
    {
        Assert.False(ReviewVerification.IsVerified("lugat_madde", XrefStatus.Aday, null, ReviewStatus.Acik));
        Assert.True(ReviewVerification.IsVerified("lugat_madde", XrefStatus.Onayli, null, ReviewStatus.Onaylandi));
    }
}
