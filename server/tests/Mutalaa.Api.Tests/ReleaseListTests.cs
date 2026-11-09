using System.Net;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using static Mutalaa.Api.Tests.Support.ReleaseTestKit;

namespace Mutalaa.Api.Tests;

/// <summary>
/// GET /releases (anahtar kumesi imleci, derleme suzgeci) ve GET /releases/{id:int} (Docker'li): editor okur; ayrintida ham JSON nesneler,
/// xmin ve ETag. Route kisiti <c>{id:int}</c> /releases/preview ile cakismaz.
/// </summary>
public class ReleaseListTests(EditorialDatabase<ReleaseListTests> fixture)
    : ApiTestBase<ReleaseListTests>(fixture), IClassFixture<EditorialDatabase<ReleaseListTests>>
{
    private const string KapiRaporu = """{"flavor":"dev","rejected":false,"rows":[{"kind":"kaynak","id":"test-kucuk","decision":"girdi","rule":null,"reason":"uygun","count":1}],"violations":[]}""";
    private const string Ozetler = """{"kaynaklar":{"test-kucuk":"0123456789abcdef"},"paketler":{"test-kucuk":"fedcba9876543210"}}""";
    private const string Manifest = """{"manifest_version":1,"flavor":"dev","release":"2026.11.0","generated_at":"2026-11-10T08:00:00Z","packs":[]}""";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private async Task<HttpClient> EditorClientAsync()
    {
        await ResetAsync(Db, Ct);
        return await EditorAsync(Factory, Ct);
    }

    private static async Task<JsonElement> BodyAsync(HttpResponseMessage response) => await ApiFactory.ReadJsonAsync(response, Ct);

    private static string[] Surums(JsonElement list) => [.. list.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("surum").GetString()!)];

    // --- Liste ---

    [Fact]
    public async Task The_list_is_newest_first_with_the_documented_summary_fields()
    {
        using HttpClient editor = await EditorClientAsync();
        DateTime published = new(2026, 11, 9, 10, 0, 0, DateTimeKind.Utc);
        int first = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0", "internal", "yayinlandi", Paketler: ["core", "test-kucuk"], Olusturan: "yazar-1", YayinlandiAt: published), Ct);
        int second = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0", "public", "hazirlaniyor", "terfi", first, Olusturan: "yazar-2"), Ct);

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/releases", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement list = await BodyAsync(response);
        Assert.Equal(JsonValueKind.Null, list.GetProperty("next_cursor").ValueKind);
        JsonElement[] items = [.. list.GetProperty("items").EnumerateArray()];
        Assert.Equal([second, first], items.Select(i => i.GetProperty("id").GetInt32()));

        JsonElement promoted = items[0];
        Assert.Equal(
            ["created_at", "derleme", "durum", "id", "kaynak_release_id", "olusturan", "paketler", "surum", "talep", "xmin", "yayinlandi_at"],
            promoted.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal(("public", "hazirlaniyor", "terfi", first, "yazar-2"), (
            promoted.GetProperty("derleme").GetString(),
            promoted.GetProperty("durum").GetString(),
            promoted.GetProperty("talep").GetString(),
            promoted.GetProperty("kaynak_release_id").GetInt32(),
            promoted.GetProperty("olusturan").GetString()));
        Assert.Equal(JsonValueKind.Null, promoted.GetProperty("paketler").ValueKind);
        Assert.Equal(JsonValueKind.Null, promoted.GetProperty("yayinlandi_at").ValueKind);
        Assert.True(DateTimeOffset.TryParse(promoted.GetProperty("created_at").GetString(), out DateTimeOffset created));
        Assert.True(created > DateTimeOffset.UtcNow.AddMinutes(-10));

        JsonElement published0 = items[1];
        Assert.Equal(["core", "test-kucuk"], published0.GetProperty("paketler").EnumerateArray().Select(e => e.GetString()));
        Assert.Equal(JsonValueKind.Null, published0.GetProperty("kaynak_release_id").ValueKind);
        Assert.Equal(new DateTimeOffset(published), DateTimeOffset.Parse(published0.GetProperty("yayinlandi_at").GetString()!, System.Globalization.CultureInfo.InvariantCulture));
        Assert.True(published0.GetProperty("xmin").GetUInt32() > 0);
    }

    [Fact]
    public async Task The_list_never_carries_the_heavy_json_columns()
    {
        using HttpClient editor = await EditorClientAsync();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0", Manifest: Manifest, KapiRaporu: KapiRaporu, Ozetler: Ozetler, Notlar: "Not."), Ct);

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/releases", Ct);

        string text = await response.Content.ReadAsStringAsync(Ct);
        Assert.DoesNotContain("manifest", text, StringComparison.Ordinal);
        Assert.DoesNotContain("kapi_raporu", text, StringComparison.Ordinal);
        Assert.DoesNotContain("ozetler", text, StringComparison.Ordinal);
        Assert.DoesNotContain("notlar", text, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_flavor_filter_returns_only_that_flavor()
    {
        using HttpClient editor = await EditorClientAsync();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0", "dev"), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.1", "internal"), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.2", "dev", "basarisiz"), Ct);

        using HttpResponseMessage dev = await editor.GetAsync("/api/v1/releases?derleme=dev", Ct);
        using HttpResponseMessage internalOnly = await editor.GetAsync("/api/v1/releases?derleme=internal", Ct);
        using HttpResponseMessage publicOnly = await editor.GetAsync("/api/v1/releases?derleme=public", Ct);

        Assert.Equal(["2026.11.2", "2026.11.0"], Surums(await BodyAsync(dev)));
        Assert.Equal(["2026.11.1"], Surums(await BodyAsync(internalOnly)));
        Assert.Empty(Surums(await BodyAsync(publicOnly)));
    }

    [Theory]
    [InlineData("DEV")]
    [InlineData("Internal")]
    [InlineData("")]
    [InlineData("production")]
    public async Task An_invalid_flavor_filter_is_a_400(string flavor)
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/releases?derleme={flavor}", Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("dogrulama", Code(body));
        Assert.True(body.GetProperty("errors").TryGetProperty("derleme", out _));
    }

    [Fact]
    public async Task Paging_follows_the_cursor_without_gaps_or_duplicates_and_ends_with_a_null_cursor()
    {
        using HttpClient editor = await EditorClientAsync();
        for (int i = 0; i < 5; i++)
        {
            _ = await InsertReleaseAsync(Db, new ReleaseSeed($"2026.11.{i}"), Ct);
        }

        using HttpResponseMessage page1Response = await editor.GetAsync("/api/v1/releases?limit=2", Ct);
        JsonElement page1 = await BodyAsync(page1Response);
        string cursor1 = page1.GetProperty("next_cursor").GetString()!;
        using HttpResponseMessage page2Response = await editor.GetAsync($"/api/v1/releases?limit=2&cursor={cursor1}", Ct);
        JsonElement page2 = await BodyAsync(page2Response);
        string cursor2 = page2.GetProperty("next_cursor").GetString()!;
        using HttpResponseMessage page3Response = await editor.GetAsync($"/api/v1/releases?limit=2&cursor={cursor2}", Ct);
        JsonElement page3 = await BodyAsync(page3Response);

        Assert.Equal(["2026.11.4", "2026.11.3"], Surums(page1));
        Assert.Equal(["2026.11.2", "2026.11.1"], Surums(page2));
        Assert.Equal(["2026.11.0"], Surums(page3));
        Assert.Equal(JsonValueKind.Null, page3.GetProperty("next_cursor").ValueKind);
        Assert.NotEqual(cursor1, cursor2);
    }

    [Fact]
    public async Task A_page_that_exactly_fills_the_limit_with_nothing_after_it_has_no_cursor()
    {
        using HttpClient editor = await EditorClientAsync();
        for (int i = 0; i < 2; i++)
        {
            _ = await InsertReleaseAsync(Db, new ReleaseSeed($"2026.11.{i}"), Ct);
        }

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/releases?limit=2", Ct);

        JsonElement list = await BodyAsync(response);
        Assert.Equal(2, list.GetProperty("items").GetArrayLength());
        Assert.Equal(JsonValueKind.Null, list.GetProperty("next_cursor").ValueKind);
    }

    [Fact]
    public async Task The_cursor_combines_with_the_flavor_filter()
    {
        using HttpClient editor = await EditorClientAsync();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0", "dev"), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.1", "internal"), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.2", "dev"), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.3", "dev"), Ct);

        using HttpResponseMessage first = await editor.GetAsync("/api/v1/releases?derleme=dev&limit=1", Ct);
        string cursor = (await BodyAsync(first)).GetProperty("next_cursor").GetString()!;
        using HttpResponseMessage second = await editor.GetAsync($"/api/v1/releases?derleme=dev&limit=5&cursor={cursor}", Ct);

        Assert.Equal(["2026.11.2", "2026.11.0"], Surums(await BodyAsync(second)));
    }

    [Fact]
    public async Task The_default_limit_is_50_and_200_is_the_largest_accepted()
    {
        using HttpClient editor = await EditorClientAsync();
        await Db.ExecuteAsync("INSERT INTO icerik.release (surum, derleme, data_version, olusturan) SELECT '2026.10.' || g, 'dev', 'x', 'y' FROM generate_series(1, 52) g", Ct);

        using HttpResponseMessage defaults = await editor.GetAsync("/api/v1/releases", Ct);
        using HttpResponseMessage largest = await editor.GetAsync("/api/v1/releases?limit=200", Ct);

        JsonElement byDefault = await BodyAsync(defaults);
        Assert.Equal(50, byDefault.GetProperty("items").GetArrayLength());
        Assert.NotEqual(JsonValueKind.Null, byDefault.GetProperty("next_cursor").ValueKind);
        JsonElement all = await BodyAsync(largest);
        Assert.Equal(52, all.GetProperty("items").GetArrayLength());
        Assert.Equal(JsonValueKind.Null, all.GetProperty("next_cursor").ValueKind);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("201")]
    [InlineData("abc")]
    [InlineData("1.5")]
    public async Task A_limit_outside_1_to_200_or_not_a_number_is_a_400(string limit)
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/releases?limit={limit}", Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal("dogrulama", Code(await BodyAsync(response)));
    }

    [Theory]
    [InlineData("42")]
    [InlineData("!!!")]
    [InlineData("cjo0Mg==")]
    [InlineData("a")]
    public async Task A_cursor_that_this_API_did_not_issue_is_a_400(string cursor)
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/releases?cursor={Uri.EscapeDataString(cursor)}", Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.True((await BodyAsync(response)).GetProperty("errors").TryGetProperty("cursor", out _));
    }

    [Fact]
    public async Task Errors_in_several_query_values_are_reported_together()
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/releases?derleme=x&limit=0&cursor=!", Ct);

        JsonElement errors = (await BodyAsync(response)).GetProperty("errors");
        Assert.Equal(["cursor", "derleme", "limit"], errors.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task An_admin_can_read_too_and_an_anonymous_caller_gets_401()
    {
        await ResetAsync(Db, Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0"), Ct);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);
        using HttpClient anonymous = Factory.CreateApiClient();

        using HttpResponseMessage adminList = await admin.GetAsync("/api/v1/releases", Ct);
        using HttpResponseMessage anonymousList = await anonymous.GetAsync("/api/v1/releases", Ct);
        using HttpResponseMessage anonymousDetail = await anonymous.GetAsync("/api/v1/releases/1", Ct);

        Assert.Equal(HttpStatusCode.OK, adminList.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, anonymousList.StatusCode);
        Assert.Equal("application/problem+json", anonymousList.Content.Headers.ContentType?.MediaType);
        Assert.Null(anonymousList.Headers.Location);
        Assert.Equal(HttpStatusCode.Unauthorized, anonymousDetail.StatusCode);
    }

    // --- Ayrinti ---

    [Fact]
    public async Task The_detail_carries_the_summary_notes_data_version_raw_json_objects_and_xmin_with_an_ETag()
    {
        using HttpClient editor = await EditorClientAsync();
        int id = await InsertReleaseAsync(
            Db,
            new ReleaseSeed("2026.11.0", "dev", "yayinlandi", Paketler: ["core"], Notlar: "Ayrinti notu.", Manifest: Manifest, KapiRaporu: KapiRaporu, Ozetler: Ozetler, DataVersion: "2026.11.09-abc1234", Olusturan: "yazar-1", YayinlandiAt: DateTime.UtcNow),
            Ct);

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/releases/{id}", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await BodyAsync(response);
        Assert.Equal(
            ["created_at", "data_version", "derleme", "durum", "id", "kapi_raporu", "kaynak_release_id", "manifest", "notlar", "olusturan", "ozetler", "paketler", "surum", "talep", "xmin", "yayinlandi_at"],
            body.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal(("Ayrinti notu.", "2026.11.09-abc1234", "yazar-1", "dev", "yayinlandi", "yayin"), (
            body.GetProperty("notlar").GetString(),
            body.GetProperty("data_version").GetString(),
            body.GetProperty("olusturan").GetString(),
            body.GetProperty("derleme").GetString(),
            body.GetProperty("durum").GetString(),
            body.GetProperty("talep").GetString()));

        // Ham JSON nesneler dizge degil, nesnedir.
        JsonElement report = body.GetProperty("kapi_raporu");
        Assert.Equal(JsonValueKind.Object, report.ValueKind);
        Assert.False(report.GetProperty("rejected").GetBoolean());
        Assert.Equal("test-kucuk", report.GetProperty("rows")[0].GetProperty("id").GetString());
        Assert.Equal("0123456789abcdef", body.GetProperty("ozetler").GetProperty("kaynaklar").GetProperty("test-kucuk").GetString());
        Assert.Equal(JsonValueKind.Object, body.GetProperty("manifest").ValueKind);
        Assert.Equal("2026.11.0", body.GetProperty("manifest").GetProperty("release").GetString());

        uint xmin = body.GetProperty("xmin").GetUInt32();
        Assert.Equal($"\"{xmin}\"", response.Headers.ETag?.Tag);
        Assert.False(response.Headers.ETag?.IsWeak);
    }

    [Fact]
    public async Task A_release_without_a_manifest_shows_null_and_empty_json_defaults()
    {
        using HttpClient editor = await EditorClientAsync();
        int id = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0"), Ct);

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/releases/{id}", Ct);

        JsonElement body = await BodyAsync(response);
        Assert.Equal(JsonValueKind.Null, body.GetProperty("manifest").ValueKind);
        Assert.Equal(JsonValueKind.Object, body.GetProperty("kapi_raporu").ValueKind);
        Assert.Equal(JsonValueKind.Object, body.GetProperty("ozetler").ValueKind);
        Assert.Equal(JsonValueKind.Null, body.GetProperty("notlar").ValueKind);
        Assert.Equal(JsonValueKind.Null, body.GetProperty("yayinlandi_at").ValueKind);
    }

    [Fact]
    public async Task The_xmin_and_ETag_change_when_the_row_changes()
    {
        using HttpClient editor = await EditorClientAsync();
        int id = await InsertReleaseAsync(Db, new ReleaseSeed("2026.11.0"), Ct);
        using HttpResponseMessage before = await editor.GetAsync($"/api/v1/releases/{id}", Ct);

        await Db.ExecuteAsync("UPDATE icerik.release SET notlar = 'degisti' WHERE id = @id", Ct, ("id", id));
        using HttpResponseMessage after = await editor.GetAsync($"/api/v1/releases/{id}", Ct);

        Assert.NotEqual(before.Headers.ETag?.Tag, after.Headers.ETag?.Tag);
        Assert.NotEqual((await BodyAsync(before)).GetProperty("xmin").GetUInt32(), (await BodyAsync(after)).GetProperty("xmin").GetUInt32());
    }

    [Fact]
    public async Task An_unknown_release_is_a_404_problem()
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/releases/99999", Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal("bulunamadi", Code(await BodyAsync(response)));
    }

    [Theory]
    [InlineData("/api/v1/releases/abc")]
    [InlineData("/api/v1/releases/1.5")]
    [InlineData("/api/v1/releases/99999999999")]
    public async Task A_non_integer_id_does_not_match_the_route_and_is_a_404(string url)
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage response = await editor.GetAsync(url, Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Preview_is_a_POST_only_route_and_the_integer_constraint_keeps_it_apart_from_the_detail_route()
    {
        using HttpClient editor = await EditorClientAsync();

        using HttpResponseMessage getPreview = await editor.GetAsync("/api/v1/releases/preview", Ct);
        using HttpResponseMessage getPromote = await editor.GetAsync("/api/v1/releases/1/promote", Ct);

        Assert.Equal(HttpStatusCode.MethodNotAllowed, getPreview.StatusCode);
        Assert.Contains("POST", getPreview.Content.Headers.Allow);
        Assert.Equal("yontem-desteklenmiyor", Code(await BodyAsync(getPreview)));
        Assert.Equal(HttpStatusCode.MethodNotAllowed, getPromote.StatusCode);
    }
}
