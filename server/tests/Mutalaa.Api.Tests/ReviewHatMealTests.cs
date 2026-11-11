using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Hat kokenli meal incelemeleri (K-49 madde 9 ve 10), liste suzgecleri (kaynak, asama) ve birlesik mealin izleyen birimi (madde 8).
/// Veri sentetiktir ("Deneme paragrafi N"); gercek meal metni yoktur (Docker'li).
/// </summary>
public class ReviewHatMealTests(EditorialDatabase<ReviewHatMealTests> fixture)
    : ReviewTestBase<ReviewHatMealTests>(fixture), IClassFixture<EditorialDatabase<ReviewHatMealTests>>
{
    private static JsonElement[] Items(JsonElement body) => [.. body.GetProperty("items").EnumerateArray()];

    private static async Task<long[]> ListIdsAsync(HttpClient client, string query)
    {
        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return [.. Items(await ApiFactory.ReadJsonAsync(response, Ct)).Select(i => i.GetProperty("id").GetInt64())];
    }

    /// <summary>Hat kaydi: koken = hat, oneren = hat; onceki ve onerilen jsonb (null olabilir).</summary>
    private async Task<Review> SeedHatReviewAsync(Unit unit, string? onceki, string? onerilen) =>
        await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = unit.Anchor.ToString(),
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Onceki = onceki,
            Onerilen = onerilen,
        });

    /// <summary>Hat yukleme yuku: {metin, content_hash, uyari, tanik} (K-49 madde 9).</summary>
    private static string HatPayload(string metin) =>
        JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["metin"] = metin,
            ["content_hash"] = ContentHash.Compute(metin),
            ["uyari"] = "Deneme uyarisi",
            ["tanik"] = new Dictionary<string, object> { ["skor"] = 97.5, ["yontem"] = "deneme-1" },
        });

    private async Task<Unit> SeedFollowerAsync(string source, string anchor)
    {
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor, metin: string.Empty);
        await Db.ExecuteAsync(
            "UPDATE icerik.unit SET attrs = @a::jsonb WHERE anchor = @n",
            Ct,
            ("a", "{\"birlesik_ile\":\"meal:test:2:1\"}"),
            ("n", anchor));
        return unit;
    }

    private async Task<HttpResponseMessage> ApproveAsync(HttpClient client, long reviewId, object? body = null) =>
        await DecideAsync(client, reviewId, Etag(await XminAsync(reviewId)), body ?? Approve());

    // ---- Hat kokenli meal: iki onay ----

    [Fact]
    public async Task A_first_load_hat_meal_with_an_empty_onceki_becomes_approved_after_two_approvals_and_keeps_its_text()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Current));
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await ApproveAsync(a, review.Id);
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal("incelemede", (await UnitRowAsync(anchor)).Durum);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);

        using HttpResponseMessage second = await ApproveAsync(b, review.Id);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);

        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(ContentHash.Compute(Current), hash);
        Assert.Equal(1, rev);
        Assert.Equal("onayli", durum);
        (string reviewDurum, _, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("onaylandi", reviewDurum);
        Assert.False(string.IsNullOrEmpty(inceleyen));
        Assert.False(string.IsNullOrEmpty(ikinci));
        Assert.NotEqual(inceleyen, ikinci);
    }

    [Fact]
    public async Task A_hat_meal_with_an_empty_onceki_and_a_different_text_applies_the_text_at_the_second_approval()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Proposed));
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await ApproveAsync(a, review.Id);
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal(Current, (await UnitRowAsync(anchor)).Metin);

        using HttpResponseMessage second = await ApproveAsync(b, review.Id);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);

        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Proposed, metin);
        Assert.Equal(ContentHash.Compute(Proposed), hash);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
    }

    [Fact]
    public async Task A_hat_meal_with_a_null_onerilen_gets_a_status_only_approval_and_the_text_stays()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: null);
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await ApproveAsync(a, review.Id);
        using HttpResponseMessage second = await ApproveAsync(b, review.Id);

        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);
        (string metin, _, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("onayli", durum);
        Assert.Equal("onaylandi", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_source_difference_record_with_a_filled_onceki_is_approved_with_two_editors_and_the_new_text_is_applied()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor, durum: TextStatus.Onayli);
        Review review = await SeedHatReviewAsync(unit, onceki: Payload(Current), onerilen: HatPayload(Proposed));
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await ApproveAsync(a, review.Id);
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        // Onayli birim ilk onayda eski metnini ve durumunu korur.
        (string firstText, _, int firstRev, string firstState) = await UnitRowAsync(anchor);
        Assert.Equal(Current, firstText);
        Assert.Equal(1, firstRev);
        Assert.Equal("onayli", firstState);

        using HttpResponseMessage second = await ApproveAsync(b, review.Id);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Proposed, metin);
        Assert.Equal(ContentHash.Compute(Proposed), hash);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
    }

    [Fact]
    public async Task A_source_difference_record_with_a_stale_onceki_is_a_409_and_changes_nothing()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor, durum: TextStatus.Onayli);
        Review review = await SeedHatReviewAsync(unit, onceki: Payload(Current), onerilen: HatPayload(Proposed));

        // Birim, kayit acildiktan sonra baska yolla (editor duzeltmesi) degisti: onceki.content_hash bayat.
        await Db.ExecuteAsync(
            "UPDATE icerik.unit SET metin = @m, content_hash = @h, rev = 2 WHERE anchor = @a",
            Ct,
            ("m", Edited),
            ("h", ContentHash.Compute(Edited)),
            ("a", anchor));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ApproveAsync(client, review.Id);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        (string metin, _, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Edited, metin);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_correction_proposal_for_a_unit_with_an_open_hat_review_is_a_409_conflict()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Current));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = Proposed, gerekce = "Deneme gerekcesi" },
            Ct);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("cakisma", await ProblemCodeAsync(response));
        Assert.Equal(1, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    // ---- Suzgecler: kaynak ve asama ----

    [Fact]
    public async Task The_kaynak_filter_lists_only_unit_reviews_of_that_source()
    {
        await ResetReviewsAsync();
        string sourceA = await SeedSourceAsync();
        string sourceB = await SeedSourceAsync();
        Unit unitA1 = await SeedUnitAsync(sourceA, UnitKind.Meal, MealAnchor());
        Unit unitA2 = await SeedUnitAsync(sourceA, UnitKind.Meal, MealAnchor());
        Unit unitB = await SeedUnitAsync(sourceB, UnitKind.Meal, MealAnchor());
        Review a1 = await SeedHatReviewAsync(unitA1, onceki: null, onerilen: HatPayload(Current));
        Review a2 = await SeedHatReviewAsync(unitA2, onceki: null, onerilen: HatPayload(Current));
        Review b = await SeedHatReviewAsync(unitB, onceki: null, onerilen: HatPayload(Current));
        _ = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        long[] onlyA = await ListIdsAsync(client, "kaynak=" + Uri.EscapeDataString(sourceA));
        long[] onlyB = await ListIdsAsync(client, "kaynak=" + Uri.EscapeDataString(sourceB) + "&hedef_tablo=unit&alan=metin");
        long[] none = await ListIdsAsync(client, "kaynak=" + Uri.EscapeDataString("yok-" + sourceA));
        long[] all = await ListIdsAsync(client, string.Empty);

        Assert.Equal([a1.Id, a2.Id], onlyA);
        Assert.Equal([b.Id], onlyB);
        Assert.Empty(none);
        Assert.Equal(4, all.Length);
    }

    [Fact]
    public async Task The_kaynak_filter_pages_with_the_cursor()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string other = await SeedSourceAsync();
        List<long> expected = [];
        for (int i = 0; i < 3; i++)
        {
            Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
            expected.Add((await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Current))).Id);
        }

        _ = await SeedHatReviewAsync(await SeedUnitAsync(other, UnitKind.Meal, MealAnchor()), onceki: null, onerilen: HatPayload(Current));
        using HttpClient client = await ClientAsync();

        List<long> seen = [];
        string? cursor = null;
        int pages = 0;
        do
        {
            string query = "limit=2&kaynak=" + Uri.EscapeDataString(source) + (cursor is null ? string.Empty : "&cursor=" + Uri.EscapeDataString(cursor));
            using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);
            JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
            seen.AddRange(Items(body).Select(i => i.GetProperty("id").GetInt64()));
            cursor = body.GetProperty("next_cursor").ValueKind == JsonValueKind.Null ? null : body.GetProperty("next_cursor").GetString();
            pages++;
        }
        while (cursor is not null && pages < 10);

        Assert.Equal(2, pages);
        Assert.Equal(expected, seen);
    }

    [Fact]
    public async Task The_asama_filter_separates_first_and_second_approval_waiting_reviews()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit waitingFirst = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Unit waitingSecond = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Unit finished = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Review first = await SeedHatReviewAsync(waitingFirst, onceki: null, onerilen: HatPayload(Current));
        Review second = await SeedHatReviewAsync(waitingSecond, onceki: null, onerilen: HatPayload(Current));
        Review done = await SeedHatReviewAsync(finished, onceki: null, onerilen: HatPayload(Current));
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        Assert.Equal(HttpStatusCode.OK, (await ApproveAsync(a, second.Id)).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await ApproveAsync(a, done.Id)).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await ApproveAsync(b, done.Id)).StatusCode);

        long[] ilk = await ListIdsAsync(a, "asama=ilk");
        long[] ikinci = await ListIdsAsync(a, "asama=ikinci");
        long[] ikinciOfSource = await ListIdsAsync(a, "asama=ikinci&kaynak=" + Uri.EscapeDataString(source));
        long[] closedWithStage = await ListIdsAsync(a, "asama=ilk&durum=onaylandi");

        Assert.Equal([first.Id], ilk);
        Assert.Equal([second.Id], ikinci);
        Assert.Equal([second.Id], ikinciOfSource);
        Assert.Empty(closedWithStage);
    }

    // ---- Birlesik meal: izleyen birim ----

    [Fact]
    public async Task A_text_changing_decision_on_a_merged_follower_is_a_422_that_does_not_use_the_offset_wording()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedFollowerAsync(source, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Proposed));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ApproveAsync(client, review.Id);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:inceleme-desteklenmiyor", body.GetProperty("type").GetString());
        string detail = body.GetProperty("detail").GetString()!;
        Assert.DoesNotContain("Ofsetli", detail, StringComparison.Ordinal);
        Assert.Contains("birlesik_ile", detail, StringComparison.Ordinal);
        (string metin, _, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(string.Empty, metin);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", durum);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task An_edited_approval_on_a_merged_follower_is_a_422()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedFollowerAsync(source, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: null);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ApproveAsync(client, review.Id, Approve(duzenlenen: new { metin = Edited }));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal(string.Empty, (await UnitRowAsync(anchor)).Metin);
    }

    [Fact]
    public async Task A_merged_follower_with_a_null_onerilen_gets_a_status_only_approval_with_two_editors_and_stays_empty()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedFollowerAsync(source, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: null);
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await ApproveAsync(a, review.Id);
        using HttpResponseMessage second = await ApproveAsync(b, review.Id);

        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(string.Empty, metin);
        Assert.Equal(ContentHash.Compute(string.Empty), hash);
        Assert.Equal(1, rev);
        Assert.Equal("onayli", durum);
    }

    [Fact]
    public async Task Rejecting_a_merged_follower_review_is_free()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedFollowerAsync(source, anchor);
        Review review = await SeedHatReviewAsync(unit, onceki: null, onerilen: HatPayload(Proposed));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("reddedildi", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal(string.Empty, (await UnitRowAsync(anchor)).Metin);
    }

    [Fact]
    public async Task A_correction_proposal_on_a_merged_follower_is_a_422_without_the_offset_wording_and_opens_no_review()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        await SeedFollowerAsync(source, anchor);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = Proposed, gerekce = "Deneme gerekcesi" },
            Ct);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:inceleme-desteklenmiyor", body.GetProperty("type").GetString());
        string detail = body.GetProperty("detail").GetString()!;
        Assert.DoesNotContain("Ofsetli", detail, StringComparison.Ordinal);
        Assert.DoesNotContain("ofsetli", detail, StringComparison.Ordinal);
        Assert.Contains("birlesik_ile", detail, StringComparison.Ordinal);
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }
}
