using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>GET /api/v1/reviews, /reviews/{id} ve /reviews/stats: sentetik veri (Docker'li).</summary>
public class ReviewListTests(EditorialDatabase<ReviewListTests> fixture)
    : ReviewTestBase<ReviewListTests>(fixture), IClassFixture<EditorialDatabase<ReviewListTests>>
{
    private static JsonElement[] Items(JsonElement body) => [.. body.GetProperty("items").EnumerateArray()];

    [Fact]
    public async Task The_list_defaults_to_open_reviews_and_carries_xmin_and_the_derived_flags()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Review open = await SeedUnitReviewAsync(unit);
        Review decided = await SeedUnitReviewAsync(unit, durum: ReviewStatus.Onaylandi);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        JsonElement[] items = Items(body);
        JsonElement item = Assert.Single(items);
        Assert.Equal(open.Id, item.GetProperty("id").GetInt64());
        Assert.NotEqual(decided.Id, item.GetProperty("id").GetInt64());
        Assert.Equal("acik", item.GetProperty("durum").GetString());
        Assert.Equal("unit", item.GetProperty("hedef_tablo").GetString());
        Assert.Equal("metin", item.GetProperty("alan").GetString());
        Assert.Equal("hat", item.GetProperty("koken").GetString());
        Assert.Equal(await XminAsync(open.Id), item.GetProperty("xmin").GetUInt32());
        Assert.False(item.GetProperty("dogrulanmamis").GetBoolean());
        Assert.False(item.GetProperty("ikinci_onay_bekliyor").GetBoolean());
        Assert.Equal(JsonValueKind.Null, body.GetProperty("next_cursor").ValueKind);
    }

    [Fact]
    public async Task The_durum_filter_accepts_the_four_labels()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        await SeedUnitReviewAsync(unit);
        Review rejected = await SeedUnitReviewAsync(unit, durum: ReviewStatus.Reddedildi);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?durum=reddedildi", Ct);

        JsonElement item = Assert.Single(Items(await ApiFactory.ReadJsonAsync(response, Ct)));
        Assert.Equal(rejected.Id, item.GetProperty("id").GetInt64());
        foreach (string label in new[] { "acik", "onaylandi", "reddedildi", "geri_alindi" })
        {
            using HttpResponseMessage each = await client.GetAsync("/api/v1/reviews?durum=" + label, Ct);
            Assert.Equal(HttpStatusCode.OK, each.StatusCode);
        }
    }

    [Fact]
    public async Task The_hedef_tablo_and_alan_filters_narrow_the_queue()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        await SeedUnitReviewAsync(unit);
        (_, Review alias) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        JsonElement byTable = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?hedef_tablo=surah_alias", Ct), Ct);
        JsonElement byField = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?alan=metin", Ct), Ct);
        JsonElement none = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?hedef_tablo=unit&alan=status", Ct), Ct);

        Assert.Equal(alias.Id, Assert.Single(Items(byTable)).GetProperty("id").GetInt64());
        Assert.Equal("unit", Assert.Single(Items(byField)).GetProperty("hedef_tablo").GetString());
        Assert.Empty(Items(none));
    }

    [Fact]
    public async Task Keyset_paging_walks_every_row_once_in_creation_order_across_pages()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        long[] ids = new long[5];
        for (int i = 0; i < ids.Length; i++)
        {
            ids[i] = (await SeedUnitReviewAsync(unit)).Id;
        }

        using HttpClient client = await ClientAsync();
        List<long> seen = [];
        string? cursor = null;
        int pages = 0;
        do
        {
            string url = "/api/v1/reviews?limit=2" + (cursor is null ? string.Empty : "&cursor=" + cursor);
            JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync(url, Ct), Ct);
            seen.AddRange(Items(body).Select(i => i.GetProperty("id").GetInt64()));
            JsonElement next = body.GetProperty("next_cursor");
            cursor = next.ValueKind == JsonValueKind.Null ? null : next.GetString();
            pages++;
        }
        while (cursor is not null && pages < 10);

        Assert.Equal(3, pages);
        Assert.Equal(ids, seen);
    }

    [Theory]
    [InlineData("hedef_tablo=yok")]
    [InlineData("durum=bilinmiyor")]
    [InlineData("durum=ACIK")]
    [InlineData("limit=0")]
    [InlineData("limit=201")]
    [InlineData("limit=-1")]
    [InlineData("limit=abc")]
    [InlineData("cursor=%25%25%25")]
    [InlineData("cursor=bozuk-imlec")]
    public async Task Invalid_filters_limits_and_cursors_are_400_problems(string query)
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task A_cursor_with_a_wrong_payload_shape_is_a_400()
    {
        using HttpClient client = await ClientAsync();
        string wrongShape = Convert.ToBase64String(Encoding.ASCII.GetBytes("hello")).TrimEnd('=');

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?cursor=" + wrongShape, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task The_limit_boundaries_1_and_200_are_accepted()
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage one = await client.GetAsync("/api/v1/reviews?limit=1", Ct);
        using HttpResponseMessage max = await client.GetAsync("/api/v1/reviews?limit=200", Ct);

        Assert.Equal(HttpStatusCode.OK, one.StatusCode);
        Assert.Equal(HttpStatusCode.OK, max.StatusCode);
    }

    [Fact]
    public async Task yz_kaydi_is_a_json_object_and_an_ai_review_is_marked_unverified()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Review ai = await SeedUnitReviewAsync(unit, yzModeli: "deneme-model-1");
        using HttpClient client = await ClientAsync();

        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews", Ct), Ct);

        JsonElement item = Assert.Single(Items(body));
        Assert.Equal(ai.Id, item.GetProperty("id").GetInt64());
        Assert.Equal("deneme-model-1", item.GetProperty("yz_modeli").GetString());
        JsonElement record = item.GetProperty("yz_kaydi");
        Assert.Equal(JsonValueKind.Object, record.ValueKind);
        Assert.Equal("deneme-1", record.GetProperty("prompt_id").GetString());
        Assert.True(item.GetProperty("dogrulanmamis").GetBoolean());
    }

    [Fact]
    public async Task A_review_with_a_first_approval_on_a_meal_unit_is_listed_as_waiting_for_the_second_approval()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit meal = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Unit risale = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor());
        Review waiting = await SeedUnitReviewAsync(meal, inceleyen: EditorAEmail);
        Review single = await SeedUnitReviewAsync(risale, inceleyen: EditorAEmail);
        using HttpClient client = await ClientAsync();

        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews", Ct), Ct);

        Dictionary<long, bool> pending = Items(body).ToDictionary(i => i.GetProperty("id").GetInt64(), i => i.GetProperty("ikinci_onay_bekliyor").GetBoolean());
        Assert.True(pending[waiting.Id]);
        Assert.False(pending[single.Id]);
    }

    [Fact]
    public async Task Stats_counts_only_open_reviews_per_queue()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        await SeedUnitReviewAsync(unit);
        await SeedUnitReviewAsync(unit);
        await SeedUnitReviewAsync(unit, durum: ReviewStatus.Onaylandi);
        await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews/stats", Ct), Ct);

        Assert.Equal(3, body.GetProperty("toplam_acik").GetInt32());
        JsonElement[] queues = [.. body.GetProperty("kuyruklar").EnumerateArray()];
        Assert.Equal(2, queues.Length);
        JsonElement aliasQueue = queues.Single(q => q.GetProperty("hedef_tablo").GetString() == "surah_alias");
        Assert.Equal("status", aliasQueue.GetProperty("alan").GetString());
        Assert.Equal(1, aliasQueue.GetProperty("acik").GetInt32());
        JsonElement unitQueue = queues.Single(q => q.GetProperty("hedef_tablo").GetString() == "unit");
        Assert.Equal("metin", unitQueue.GetProperty("alan").GetString());
        Assert.Equal(2, unitQueue.GetProperty("acik").GetInt32());
    }

    [Fact]
    public async Task The_detail_returns_values_the_target_snapshot_and_an_etag_equal_to_xmin()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        uint xmin = await XminAsync(review.Id);
        Assert.Equal(Etag(xmin), response.Headers.ETag?.Tag);
        Assert.False(response.Headers.ETag?.IsWeak);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal(xmin, body.GetProperty("xmin").GetUInt32());
        Assert.Equal(Current, body.GetProperty("onceki").GetProperty("metin").GetString());
        Assert.Equal(Proposed, body.GetProperty("onerilen").GetProperty("metin").GetString());
        Assert.Equal(JsonValueKind.Null, body.GetProperty("duzenlenen").ValueKind);
        JsonElement hedef = body.GetProperty("hedef");
        Assert.Equal("unit", hedef.GetProperty("tablo").GetString());
        Assert.Equal(unit.Anchor.ToString(), hedef.GetProperty("anchor").GetString());
        Assert.Equal("meal", hedef.GetProperty("kind").GetString());
        Assert.Equal(source, hedef.GetProperty("source").GetString());
        Assert.Equal(Current, hedef.GetProperty("metin").GetString());
        Assert.Equal(unit.ContentHash, hedef.GetProperty("content_hash").GetString());
        Assert.Equal("taslak", hedef.GetProperty("metin_durumu").GetString());
        Assert.Equal("etkin", hedef.GetProperty("status").GetString());
        Assert.Equal(1, hedef.GetProperty("rev").GetInt32());
        Assert.False(body.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task The_detail_of_an_approved_unit_is_verified_and_an_approved_ai_review_on_it_is_no_longer_unverified()
    {
        // Tek kural (liste ve ayrinti): yz_modeli dolu ve not (review onaylandi ve hedef onayli); acik review rozetli kalir.
        string source = await SeedSourceAsync();
        Unit approved = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), durum: TextStatus.Onayli);
        Review ai = await SeedUnitReviewAsync(approved, durum: ReviewStatus.Onaylandi, yzModeli: "deneme-model-1");
        using HttpClient client = await ClientAsync();

        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{ai.Id}", Ct), Ct);

        Assert.True(body.GetProperty("dogrulanmis").GetBoolean());
        Assert.False(body.GetProperty("dogrulanmamis").GetBoolean());
        Assert.Equal(JsonValueKind.Object, body.GetProperty("yz_kaydi").ValueKind);
    }

    [Fact]
    public async Task The_detail_snapshot_of_a_surah_alias_and_of_an_unsupported_target()
    {
        (SurahAlias alias, Review aliasReview) = await SeedAliasReviewAsync();
        Review other = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Root,
            HedefAnahtar = "1",
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = ReviewStatus.Onaylandi,
        });
        using HttpClient client = await ClientAsync();

        JsonElement aliasBody = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{aliasReview.Id}", Ct), Ct);
        JsonElement otherBody = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{other.Id}", Ct), Ct);

        JsonElement hedef = aliasBody.GetProperty("hedef");
        Assert.Equal("surah_alias", hedef.GetProperty("tablo").GetString());
        Assert.Equal(1, hedef.GetProperty("surah_no").GetInt32());
        Assert.Equal(alias.Alias, hedef.GetProperty("alias").GetString());
        Assert.Equal("yazim", hedef.GetProperty("kind").GetString());
        Assert.False(hedef.GetProperty("risky").GetBoolean());
        Assert.Equal("aday", hedef.GetProperty("status").GetString());
        Assert.False(aliasBody.GetProperty("dogrulanmis").GetBoolean());

        // Durum sutunu olmayan hedefte hedef anlik gorunumu yoktur; dogrulanmis review durumundan turetilir.
        Assert.Equal(JsonValueKind.Null, otherBody.GetProperty("hedef").ValueKind);
        Assert.True(otherBody.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task A_missing_review_is_a_404_problem()
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews/987654321", Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
    }

    [Theory]
    [InlineData("GET", "/api/v1/reviews")]
    [InlineData("GET", "/api/v1/reviews/1")]
    [InlineData("GET", "/api/v1/reviews/stats")]
    [InlineData("POST", "/api/v1/reviews/1/decision")]
    [InlineData("POST", "/api/v1/reviews/decisions")]
    public async Task Without_a_session_every_review_endpoint_is_a_401_problem_without_a_Location_header(string method, string path)
    {
        using HttpClient client = Factory.CreateApiClient();
        using HttpRequestMessage request = new(new HttpMethod(method), path);
        if (method == "POST")
        {
            request.Content = JsonContent.Create(new { karar = "onaylandi", gerekce = "x" });
        }

        using HttpResponseMessage response = await client.SendAsync(request, Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.False(response.Headers.Contains("Location"));
    }
}
