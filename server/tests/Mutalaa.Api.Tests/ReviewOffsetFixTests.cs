using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Ofsetli turev alanlari (marks, sentences) olan birimde metin degistiren onay 422 inceleme-desteklenmiyor; durum onayi ve ret serbest;
/// duzeltme onerisi ucu da ayni kosulda 422 verir (yeniden hesap BC-59'da, A20). Sentetik veri (Docker'li).
/// </summary>
public class ReviewOffsetFixTests(EditorialDatabase<ReviewOffsetFixTests> fixture)
    : ReviewTestBase<ReviewOffsetFixTests>(fixture), IClassFixture<EditorialDatabase<ReviewOffsetFixTests>>
{
    private const string Marks = "[{\"tur\":\"vurgu\",\"baslangic\":0,\"bitis\":4}]";

    private async Task<Unit> SeedOffsetUnitAsync(string source, UnitKind kind, string anchor, bool withMarks = true)
    {
        Unit unit = await SeedUnitAsync(source, kind, anchor);
        if (withMarks)
        {
            await Db.ExecuteAsync("UPDATE icerik.unit SET marks = @m::jsonb WHERE anchor = @a", Ct, ("m", Marks), ("a", anchor));
        }
        else
        {
            await Db.ExecuteAsync("UPDATE icerik.unit SET sentences = ARRAY['[0,5)'::int4range] WHERE anchor = @a", Ct, ("a", anchor));
        }

        return unit;
    }

    private async Task AssertUnitUntouchedAsync(string anchor)
    {
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(Mutalaa.Domain.Text.ContentHash.Compute(Current), hash);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", durum);
    }

    private static async Task AssertProblemAsync(HttpResponseMessage response, HttpStatusCode status, string code)
    {
        Assert.Equal(status, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:" + code, body.GetProperty("type").GetString());
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task Approving_a_text_change_on_a_unit_with_offset_data_is_a_422_and_changes_nothing(bool withMarks)
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor, withMarks);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "inceleme-desteklenmiyor");
        await AssertUnitUntouchedAsync(anchor);
        (string durum, _, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Null(inceleyen);
    }

    [Fact]
    public async Task Approving_an_edited_text_on_a_unit_with_offset_data_is_a_422()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = Edited }));

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "inceleme-desteklenmiyor");
        await AssertUnitUntouchedAsync(anchor);
    }

    [Fact]
    public async Task A_status_only_approval_on_a_unit_with_offset_data_is_free_and_keeps_the_text()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = unit.Anchor.ToString(),
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Onceki = Payload(Current),
            Onerilen = null,
            Koken = Mutalaa.Domain.Links.XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string metin, _, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("onayli", durum);
        Assert.Contains("vurgu", await Db.ScalarAsync<string>("SELECT marks::text FROM icerik.unit WHERE anchor = @a", Ct, ("a", anchor)), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Rejecting_a_text_change_on_a_unit_with_offset_data_is_free()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string durum, _, _, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("reddedildi", durum);
        await AssertUnitUntouchedAsync(anchor);
    }

    [Fact]
    public async Task The_first_approval_of_a_two_stage_meal_review_is_refused_at_once_when_the_text_would_change()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "inceleme-desteklenmiyor");
        await AssertUnitUntouchedAsync(anchor);
        (string durum, _, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Null(inceleyen);
    }

    [Fact]
    public async Task A_bulk_decision_with_an_unsupported_text_change_is_a_422_naming_the_review_and_applies_nothing()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string offsetAnchor = TestData.UnitAnchor();
        string plainAnchor = TestData.UnitAnchor();
        Unit offsetUnit = await SeedOffsetUnitAsync(source, UnitKind.Risale, offsetAnchor);
        Unit plainUnit = await SeedUnitAsync(source, UnitKind.Risale, plainAnchor);
        Review plain = await SeedUnitReviewAsync(plainUnit);
        Review offset = await SeedUnitReviewAsync(offsetUnit);
        using HttpClient client = await ClientAsync();
        object[] items =
        [
            new { id = plain.Id, xmin = await XminAsync(plain.Id), karar = "onaylandi", gerekce = "Toplu gerekce" },
            new { id = offset.Id, xmin = await XminAsync(offset.Id), karar = "onaylandi", gerekce = "Toplu gerekce" },
        ];

        using HttpResponseMessage response = await client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = items }, Ct);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:inceleme-desteklenmiyor", body.GetProperty("type").GetString());
        Assert.Equal(offset.Id, body.GetProperty("kimlik").GetInt64());
        Assert.Equal("acik", (await ReviewRowAsync(plain.Id)).Durum);
        Assert.Equal("taslak", (await UnitRowAsync(plainAnchor)).Durum);
    }

    [Fact]
    public async Task A_correction_proposal_on_a_unit_with_offset_data_is_a_422_and_opens_no_review()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = Proposed, gerekce = "Deneme gerekcesi" },
            Ct);

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "inceleme-desteklenmiyor");
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Fact]
    public async Task The_offset_422_messages_of_the_decision_and_the_correction_both_start_with_Ofsetli()
    {
        // Editor (apps/editor problem-text.ts OFFSET_MARKER = 'Ofsetli') bu iki iletiyi ayni belirtecle taniyip ozel metin gosterir.
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage decision = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());
        using HttpResponseMessage correction = await client.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = Proposed, gerekce = "Deneme gerekcesi" },
            Ct);

        foreach (HttpResponseMessage response in new[] { decision, correction })
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
            JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
            Assert.StartsWith("Ofsetli", body.GetProperty("detail").GetString(), StringComparison.Ordinal);
        }
    }

    [Fact]
    public async Task A_correction_proposal_with_no_change_on_a_unit_with_offset_data_stays_a_400_no_change()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        await SeedOffsetUnitAsync(source, UnitKind.Risale, anchor);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = Current, gerekce = "Deneme gerekcesi" },
            Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
    }
}
