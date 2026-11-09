using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>dogrulanmis ve ikinci_onay_bekliyor turetimleri, TextMutability ve hata kodlari (K-48).</summary>
public class ReviewVerificationTests
{
    [Theory]
    [InlineData("lemma")]
    [InlineData("lemma_gloss")]
    [InlineData("quran_word_fix")]
    [InlineData("surah_alias")]
    [InlineData("xref")]
    public void Status_tables_are_verified_when_the_target_status_is_onayli(string table)
    {
        Assert.True(ReviewVerification.IsVerified(table, XrefStatus.Onayli, null, ReviewStatus.Acik));
        Assert.False(ReviewVerification.IsVerified(table, XrefStatus.Aday, null, ReviewStatus.Onaylandi));
        Assert.False(ReviewVerification.IsVerified(table, XrefStatus.Red, null, ReviewStatus.Onaylandi));
        Assert.False(ReviewVerification.IsVerified(table, null, TextStatus.Onayli, ReviewStatus.Onaylandi));
    }

    [Fact]
    public void A_unit_is_verified_when_its_text_status_is_onayli()
    {
        Assert.True(ReviewVerification.IsVerified("unit", null, TextStatus.Onayli, ReviewStatus.Acik));
        Assert.False(ReviewVerification.IsVerified("unit", null, TextStatus.Incelemede, ReviewStatus.Onaylandi));
        Assert.False(ReviewVerification.IsVerified("unit", null, TextStatus.Taslak, ReviewStatus.Onaylandi));
        Assert.False(ReviewVerification.IsVerified("unit", XrefStatus.Onayli, null, ReviewStatus.Onaylandi));
    }

    [Theory]
    [InlineData("source")]
    [InlineData("root")]
    [InlineData("tr_root_index")]
    [InlineData("tr_form")]
    [InlineData("page_map")]
    [InlineData("ayah_box")]
    [InlineData("audio_timing")]
    public void Tables_without_a_status_column_are_verified_by_an_approved_review(string table)
    {
        Assert.True(ReviewVerification.IsVerified(table, null, null, ReviewStatus.Onaylandi));
        Assert.False(ReviewVerification.IsVerified(table, null, null, ReviewStatus.Acik));
        Assert.False(ReviewVerification.IsVerified(table, null, null, ReviewStatus.Reddedildi));
        Assert.False(ReviewVerification.IsVerified(table, null, null, ReviewStatus.GeriAlindi));
    }

    [Fact]
    public void An_unknown_target_table_is_a_validation_error()
    {
        DomainException e = Assert.Throws<DomainException>(() => ReviewVerification.IsVerified("bilinmeyen", null, null, ReviewStatus.Onaylandi));

        Assert.Equal(DomainErrorCodes.Dogrulama, e.Code);
    }

    [Theory]
    [InlineData(UnitKind.Meal, "test-editor-1", null, ReviewStatus.Acik, true)]
    [InlineData(UnitKind.Tefsir, "test-editor-1", null, ReviewStatus.Acik, true)]
    [InlineData(UnitKind.Meal, null, null, ReviewStatus.Acik, false)]
    [InlineData(UnitKind.Meal, "", null, ReviewStatus.Acik, false)]
    [InlineData(UnitKind.Meal, "test-editor-1", "test-editor-2", ReviewStatus.Acik, false)]
    [InlineData(UnitKind.Meal, "test-editor-1", null, ReviewStatus.Onaylandi, false)]
    [InlineData(UnitKind.Meal, "test-editor-1", null, ReviewStatus.Reddedildi, false)]
    [InlineData(UnitKind.Risale, "test-editor-1", null, ReviewStatus.Acik, false)]
    [InlineData(UnitKind.Ayet, "test-editor-1", null, ReviewStatus.Acik, false)]
    public void The_second_approval_is_pending_only_for_an_open_meal_or_tefsir_review_with_a_first_approver(
        UnitKind kind, string? inceleyen, string? ikinci, ReviewStatus durum, bool expected)
    {
        Review review = UnitReview(durum: durum, inceleyen: inceleyen);
        review.IkinciInceleyen = ikinci;

        Assert.Equal(expected, ReviewVerification.IsSecondApprovalPending(review, kind));
    }

    [Fact]
    public void The_second_approval_is_never_pending_for_non_text_reviews()
    {
        Review review = StatusReview();
        review.Inceleyen = "test-editor-1";

        Assert.False(ReviewVerification.IsSecondApprovalPending(review, UnitKind.Meal));
    }

    [Fact]
    public void Pending_follows_the_decision_flow()
    {
        Review review = UnitReview();
        Assert.False(ReviewVerification.IsSecondApprovalPending(review, UnitKind.Meal));

        ReviewDecisions.Approve(review, Request("test-editor-1"), ReviewTargetState.ForUnit(Unit())).ApplyTo(review);
        Assert.True(ReviewVerification.IsSecondApprovalPending(review, UnitKind.Meal));

        ReviewDecisions.Approve(review, Request("test-editor-2"), ReviewTargetState.ForUnit(Unit(durum: TextStatus.Incelemede))).ApplyTo(review);
        Assert.False(ReviewVerification.IsSecondApprovalPending(review, UnitKind.Meal));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Only_ayet_units_and_kuran_metni_sources_have_immutable_text(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (UnitKind kind in Enum.GetValues<UnitKind>())
        {
            foreach (SourceKind source in Enum.GetValues<SourceKind>())
            {
                bool expected = kind == UnitKind.Ayet || source == SourceKind.KuranMetni;
                Assert.Equal(expected, TextMutability.IsImmutable(kind, source));
            }
        }
    });

    [Fact]
    public void Error_codes_are_the_documented_kebab_case_strings()
    {
        Assert.Equal(
            ["dogrulama", "durum-gecisi-gecersiz", "degistirilemez-metin", "inceleme-desteklenmiyor", "surum-uyusmazligi", "bulunamadi"],
            new[]
            {
                DomainErrorCodes.Dogrulama,
                DomainErrorCodes.DurumGecisiGecersiz,
                DomainErrorCodes.DegistirilemezMetin,
                DomainErrorCodes.IncelemeDesteklenmiyor,
                DomainErrorCodes.SurumUyusmazligi,
                DomainErrorCodes.Bulunamadi,
            });
    }

    [Fact]
    public void DomainException_carries_the_code_and_the_message()
    {
        DomainException plain = new(DomainErrorCodes.Bulunamadi, "Kayit yok.");
        DomainException wrapped = new(DomainErrorCodes.Dogrulama, "Bozuk.", new InvalidOperationException("ic"));

        Assert.Equal("bulunamadi", plain.Code);
        Assert.Equal("Kayit yok.", plain.Message);
        Assert.Equal("dogrulama", wrapped.Code);
        Assert.IsType<InvalidOperationException>(wrapped.InnerException);
        Assert.Throws<ArgumentException>(() => new DomainException(string.Empty, "x"));
    }
}
