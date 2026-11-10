using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;
using static Mutalaa.Api.Tests.Support.ReleaseTestKit;

namespace Mutalaa.Api.Tests;

/// <summary>
/// POST /releases, /releases/{id}/promote ve /rollback (K-48 madde 7; Docker'li): satir alanlari, yetki, dogrulama, acik satir engeli
/// (409 yayin-suruyor) ve durum kurallari. Veriler sentetiktir; talepler yalniz release satiri acar (isi Yayinlayici watch yapar).
/// </summary>
public partial class ReleaseEndpointsTests(EditorialDatabase<ReleaseEndpointsTests> fixture)
    : ApiTestBase<ReleaseEndpointsTests>(fixture), IClassFixture<EditorialDatabase<ReleaseEndpointsTests>>
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    [GeneratedRegex(@"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}-([0-9a-f]{4,40}|nogit)$", RegexOptions.CultureInvariant)]
    private static partial Regex DataVersionPattern();

    [GeneratedRegex(@"^[0-9]{4}\.([1-9]|1[0-2])\.(0|[1-9][0-9]*)$", RegexOptions.CultureInvariant)]
    private static partial Regex CalVerPattern();

    private async Task<HttpClient> AdminAsync()
    {
        await ResetAsync(Db, Ct);
        return await ReleaseTestKit.AdminAsync(Factory, Ct);
    }

    private static async Task<JsonElement> ReadBodyAsync(HttpResponseMessage response) => await ApiFactory.ReadJsonAsync(response, Ct);

    private static async Task AssertProblemAsync(HttpResponseMessage response, HttpStatusCode status, string code)
    {
        Assert.Equal(status, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Null(response.Headers.Location);
        JsonElement body = await ReadBodyAsync(response);
        Assert.Equal(code, Code(body));
        Assert.Equal("urn:mutalaa:problem:" + code, body.GetProperty("type").GetString());
    }

    // --- POST /releases ---

    [Fact]
    public async Task Creating_a_release_answers_202_with_Location_and_opens_a_hazirlaniyor_yayin_row()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", notlar = "Deneme notu." }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        JsonElement body = await ReadBodyAsync(response);
        int id = body.GetProperty("id").GetInt32();
        Assert.Equal($"/api/v1/releases/{id}", response.Headers.Location?.OriginalString);
        Assert.Equal("dev", body.GetProperty("derleme").GetString());
        Assert.Equal("hazirlaniyor", body.GetProperty("durum").GetString());
        Assert.Equal("yayin", body.GetProperty("talep").GetString());
        Assert.Matches(CalVerPattern(), body.GetProperty("surum").GetString()!);

        ReleaseRow row = await ReadAsync(Db, id, Ct);
        Assert.Equal(("dev", "hazirlaniyor", "yayin"), (row.Derleme, row.Durum, row.Talep));
        Assert.Equal(body.GetProperty("surum").GetString(), row.Surum);
        Assert.Null(row.Paketler);
        Assert.Null(row.KaynakReleaseId);
        Assert.Equal("Deneme notu.", row.Notlar);
        Assert.Equal(AdminEmail, row.Olusturan);
        Assert.Matches(DataVersionPattern(), row.DataVersion);
    }

    [Fact]
    public async Task The_response_body_has_exactly_the_documented_fields()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "internal" }, Ct);

        JsonElement body = await ReadBodyAsync(response);
        Assert.Equal(["derleme", "durum", "id", "surum", "talep"], body.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task A_pack_selection_is_stored_and_an_empty_one_means_all_packs_stored_as_null()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage selected = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", paketler = new[] { "core", "test-kucuk" } }, Ct);
        int selectedId = (await ReadBodyAsync(selected)).GetProperty("id").GetInt32();
        await Db.ExecuteAsync("UPDATE icerik.release SET durum = 'basarisiz'::icerik.surum_durumu WHERE id = @id", Ct, ("id", selectedId));
        using HttpResponseMessage all = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", paketler = Array.Empty<string>() }, Ct);
        int allId = (await ReadBodyAsync(all)).GetProperty("id").GetInt32();

        string[]? stored = (await ReadAsync(Db, selectedId, Ct)).Paketler;
        Assert.NotNull(stored);
        Assert.Equal(["core", "test-kucuk"], stored);
        Assert.Null((await ReadAsync(Db, allId, Ct)).Paketler);
    }

    [Fact]
    public async Task A_notes_value_of_2000_code_points_is_accepted()
    {
        using HttpClient admin = await AdminAsync();
        string emoji = char.ConvertFromUtf32(0x1F600);
        string notes = string.Concat(Enumerable.Repeat(emoji, 2000));

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", notlar = notes }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        int id = (await ReadBodyAsync(response)).GetProperty("id").GetInt32();
        Assert.Equal(notes, (await ReadAsync(Db, id, Ct)).Notlar);
    }

    [Fact]
    public async Task Version_numbers_follow_the_month_counter_across_flavors()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage first = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev" }, Ct);
        using HttpResponseMessage second = await PostAsync(admin, "/api/v1/releases", new { derleme = "internal" }, Ct);

        Assert.Equal(MonthVersion(0), (await ReadBodyAsync(first)).GetProperty("surum").GetString());
        Assert.Equal(MonthVersion(1), (await ReadBodyAsync(second)).GetProperty("surum").GetString());
    }

    // --- Yetki ---

    private static object? AdminRouteBody(string url) =>
        url.EndsWith("/promote", StringComparison.Ordinal) || url.EndsWith("/rollback", StringComparison.Ordinal) ? null : new { derleme = "dev" };

    [Theory]
    [InlineData("/api/v1/releases")]
    [InlineData("/api/v1/releases/preview")]
    [InlineData("/api/v1/releases/1/promote")]
    [InlineData("/api/v1/releases/1/rollback")]
    public async Task An_editor_is_forbidden_from_every_release_request_endpoint(string url)
    {
        await ResetAsync(Db, Ct);
        using HttpClient editor = await EditorAsync(Factory, Ct);

        using HttpResponseMessage response = await PostAsync(editor, url, AdminRouteBody(url), Ct);

        await AssertProblemAsync(response, HttpStatusCode.Forbidden, "yetki-yok");
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    [Theory]
    [InlineData("/api/v1/releases")]
    [InlineData("/api/v1/releases/preview")]
    [InlineData("/api/v1/releases/1/promote")]
    [InlineData("/api/v1/releases/1/rollback")]
    public async Task An_anonymous_caller_gets_401_from_every_release_request_endpoint(string url)
    {
        await ResetAsync(Db, Ct);
        using HttpClient anonymous = Factory.CreateApiClient();

        using HttpResponseMessage response = await PostAsync(anonymous, url, AdminRouteBody(url), Ct);

        await AssertProblemAsync(response, HttpStatusCode.Unauthorized, "oturum-acilamadi");
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    // --- Dogrulama ---

    [Fact]
    public async Task An_unknown_pack_is_a_400_validation_error_and_opens_no_row()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", paketler = new[] { "core", "yok-boyle-paket" } }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        JsonElement body = await ReadBodyAsync(response);
        Assert.Contains("yok-boyle-paket", body.GetProperty("errors").GetProperty("paketler")[0].GetString(), StringComparison.Ordinal);
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task A_duplicate_pack_is_a_400_validation_error()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", paketler = new[] { "core", "core" } }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.True((await ReadBodyAsync(response)).GetProperty("errors").TryGetProperty("paketler", out _));
    }

    [Theory]
    [InlineData("""{"derleme":"production"}""", "derleme")]
    [InlineData("""{"derleme":"DEV"}""", "derleme")]
    [InlineData("""{"derleme":""}""", "derleme")]
    [InlineData("""{"paketler":["core"]}""", "derleme")]
    [InlineData("""{"derleme":"dev","notlar":"a\u0000b"}""", "notlar")]
    public async Task A_bad_body_is_a_400_validation_error_naming_the_field(string json, string field)
    {
        using HttpClient admin = await AdminAsync();
        using StringContent content = new(json, new MediaTypeHeaderValue("application/json"));

        using HttpResponseMessage response = await admin.PostAsync("/api/v1/releases", content, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.True((await ReadBodyAsync(response)).GetProperty("errors").TryGetProperty(field, out _));
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task Notes_over_2000_code_points_are_a_400_validation_error()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev", notlar = new string('a', 2001) }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.True((await ReadBodyAsync(response)).GetProperty("errors").TryGetProperty("notlar", out _));
    }

    [Theory]
    [InlineData("""{"derleme":"dev","bilinmeyen":1}""")]
    [InlineData("""{"derleme":"dev",""")]
    [InlineData("""[]""")]
    public async Task An_unknown_field_or_broken_JSON_is_a_400(string json)
    {
        using HttpClient admin = await AdminAsync();
        using StringContent content = new(json, new MediaTypeHeaderValue("application/json"));

        using HttpResponseMessage response = await admin.PostAsync("/api/v1/releases", content, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task A_missing_or_empty_body_is_a_400()
    {
        using HttpClient admin = await AdminAsync();
        using StringContent empty = new(string.Empty, new MediaTypeHeaderValue("application/json"));

        using HttpResponseMessage emptyJson = await admin.PostAsync("/api/v1/releases", empty, Ct);
        using HttpResponseMessage noContentType = await admin.PostAsync("/api/v1/releases", content: null, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, emptyJson.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, noContentType.StatusCode);
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    // --- Acik satir engeli (409 yayin-suruyor) ---

    [Fact]
    public async Task A_second_request_while_a_row_is_open_is_a_409_yayin_suruyor_pointing_at_the_open_row()
    {
        using HttpClient admin = await AdminAsync();
        using HttpResponseMessage first = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev" }, Ct);
        JsonElement opened = await ReadBodyAsync(first);

        using HttpResponseMessage second = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev" }, Ct);

        await AssertProblemAsync(second, HttpStatusCode.Conflict, "yayin-suruyor");
        JsonElement running = (await ReadBodyAsync(second)).GetProperty("yayin");
        Assert.Equal(opened.GetProperty("id").GetInt32(), running.GetProperty("id").GetInt32());
        Assert.Equal(opened.GetProperty("surum").GetString(), running.GetProperty("surum").GetString());
        Assert.Equal(["derleme", "durum", "id", "surum", "talep"], running.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal(("dev", "hazirlaniyor", "yayin"), (running.GetProperty("derleme").GetString(), running.GetProperty("durum").GetString(), running.GetProperty("talep").GetString()));
        Assert.Equal(1, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task A_verified_row_blocks_new_requests_too_and_the_yayin_extension_shows_its_state()
    {
        using HttpClient admin = await AdminAsync();
        int open = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "public", "dogrulandi", "terfi"), Ct);

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "public" }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "yayin-suruyor");
        JsonElement running = (await ReadBodyAsync(response)).GetProperty("yayin");
        Assert.Equal(open, running.GetProperty("id").GetInt32());
        Assert.Equal(("dogrulandi", "terfi"), (running.GetProperty("durum").GetString(), running.GetProperty("talep").GetString()));
    }

    [Fact]
    public async Task An_open_row_of_another_flavor_does_not_block()
    {
        using HttpClient admin = await AdminAsync();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal"), Ct);

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev" }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
    }

    [Theory]
    [InlineData("basarisiz")]
    [InlineData("yayinlandi")]
    [InlineData("geri_cekildi")]
    public async Task A_finished_row_does_not_block(string status)
    {
        using HttpClient admin = await AdminAsync();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", status, YayinlandiAt: status == "basarisiz" ? null : DateTime.UtcNow), Ct);

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = "dev" }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
    }

    [Fact]
    public async Task Two_simultaneous_requests_open_exactly_one_row()
    {
        using HttpClient admin = await AdminAsync();

        Task<HttpResponseMessage> a = PostAsync(admin, "/api/v1/releases", new { derleme = "internal" }, Ct);
        Task<HttpResponseMessage> b = PostAsync(admin, "/api/v1/releases", new { derleme = "internal" }, Ct);
        HttpResponseMessage[] responses = await Task.WhenAll(a, b);
        try
        {
            Assert.Equal([HttpStatusCode.Accepted, HttpStatusCode.Conflict], responses.Select(r => r.StatusCode).Order());
            HttpResponseMessage conflict = responses.Single(r => r.StatusCode == HttpStatusCode.Conflict);
            Assert.Equal("yayin-suruyor", Code(await ReadBodyAsync(conflict)));
            Assert.Equal(1, await CountAsync(Db, Ct));
        }
        finally
        {
            foreach (HttpResponseMessage response in responses)
            {
                response.Dispose();
            }
        }
    }

    // --- tr-TR ---

    [Theory]
    [InlineData("dev")]
    [InlineData("internal")]
    [InlineData("public")]
    public async Task Flavor_labels_are_culture_independent_under_tr_TR(string flavor)
    {
        using HttpClient admin = await AdminAsync();

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases", new { derleme = flavor }, Ct);

            Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
            JsonElement body = await ReadBodyAsync(response);
            Assert.Equal(flavor, body.GetProperty("derleme").GetString());
            Assert.Equal(flavor, (await ReadAsync(Db, body.GetProperty("id").GetInt32(), Ct)).Derleme);
        });
    }

    // --- Terfi ---

    [Fact]
    public async Task Promoting_a_published_internal_release_opens_a_terfi_row_with_the_same_version_and_the_source_id()
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(3), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{source}/promote", new { notlar = "Terfi notu." }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        JsonElement body = await ReadBodyAsync(response);
        int id = body.GetProperty("id").GetInt32();
        Assert.Equal($"/api/v1/releases/{id}", response.Headers.Location?.OriginalString);
        Assert.Equal(("public", "hazirlaniyor", "terfi", MonthVersion(3)), (body.GetProperty("derleme").GetString(), body.GetProperty("durum").GetString(), body.GetProperty("talep").GetString(), body.GetProperty("surum").GetString()));

        ReleaseRow row = await ReadAsync(Db, id, Ct);
        Assert.Equal(("public", "terfi", MonthVersion(3), source), (row.Derleme, row.Talep, row.Surum, row.KaynakReleaseId));
        Assert.Null(row.Paketler);
        Assert.Equal("Terfi notu.", row.Notlar);
        Assert.Equal(AdminEmail, row.Olusturan);
        Assert.Matches(DataVersionPattern(), row.DataVersion);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("{}")]
    public async Task Promote_and_rollback_accept_an_empty_or_missing_body(string? json)
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);
        using StringContent? content = json is null ? null : new StringContent(json, new MediaTypeHeaderValue("application/json"));

        using HttpResponseMessage response = await admin.PostAsync($"/api/v1/releases/{source}/promote", content, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        Assert.Null((await ReadAsync(Db, (await ReadBodyAsync(response)).GetProperty("id").GetInt32(), Ct)).Notlar);
    }

    [Theory]
    [InlineData("internal", "hazirlaniyor")]
    [InlineData("internal", "dogrulandi")]
    [InlineData("internal", "basarisiz")]
    [InlineData("internal", "geri_cekildi")]
    [InlineData("dev", "yayinlandi")]
    [InlineData("public", "yayinlandi")]
    public async Task Only_a_published_internal_release_can_be_promoted(string flavor, string status)
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), flavor, status, YayinlandiAt: status == "yayinlandi" ? DateTime.UtcNow : null), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{source}/promote", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "durum-gecisi-gecersiz");
        Assert.Equal(1, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task Promoting_an_unknown_release_is_a_404()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases/99999/promote", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.NotFound, "bulunamadi");
    }

    [Theory]
    [InlineData("yayinlandi")]
    [InlineData("geri_cekildi")]
    public async Task Promoting_a_version_that_already_has_a_public_row_is_a_409_cakisma(string publicStatus)
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "public", publicStatus, "terfi", source, YayinlandiAt: DateTime.UtcNow), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{source}/promote", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "cakisma");
        Assert.Equal(2, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task A_failed_public_row_with_the_same_version_does_not_prevent_a_new_promotion()
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "public", "basarisiz", "terfi", source), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{source}/promote", null, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
    }

    [Fact]
    public async Task An_open_public_row_blocks_a_promotion_with_409_yayin_suruyor_but_open_rows_of_other_flavors_do_not()
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "dev"), Ct);
        int openPublic = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(2), "public", "hazirlaniyor", "yayin"), Ct);

        using HttpResponseMessage blocked = await PostAsync(admin, $"/api/v1/releases/{source}/promote", null, Ct);

        await AssertProblemAsync(blocked, HttpStatusCode.Conflict, "yayin-suruyor");
        Assert.Equal(openPublic, (await ReadBodyAsync(blocked)).GetProperty("yayin").GetProperty("id").GetInt32());

        await Db.ExecuteAsync("UPDATE icerik.release SET durum = 'basarisiz'::icerik.surum_durumu WHERE id = @id", Ct, ("id", openPublic));
        using HttpResponseMessage allowed = await PostAsync(admin, $"/api/v1/releases/{source}/promote", null, Ct);
        Assert.Equal(HttpStatusCode.Accepted, allowed.StatusCode);
    }

    [Fact]
    public async Task Promote_notes_over_2000_code_points_are_a_400()
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{source}/promote", new { notlar = new string('a', 2001) }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.True((await ReadBodyAsync(response)).GetProperty("errors").TryGetProperty("notlar", out _));
    }

    [Fact]
    public async Task A_non_numeric_release_id_does_not_match_the_route()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage promote = await PostAsync(admin, "/api/v1/releases/abc/promote", null, Ct);
        using HttpResponseMessage rollback = await PostAsync(admin, "/api/v1/releases/abc/rollback", null, Ct);

        Assert.Equal(HttpStatusCode.NotFound, promote.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, rollback.StatusCode);
    }

    // --- Geri alma ---

    [Fact]
    public async Task Rolling_back_to_an_older_published_release_opens_a_geri_alma_row_with_a_new_version_and_the_target_id()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        int target = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-2)), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-1)), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{target}/rollback", new { notlar = "Geri alma notu." }, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        JsonElement body = await ReadBodyAsync(response);
        int id = body.GetProperty("id").GetInt32();
        Assert.Equal($"/api/v1/releases/{id}", response.Headers.Location?.OriginalString);
        Assert.Equal(("dev", "hazirlaniyor", "geri_alma", MonthVersion(2)), (body.GetProperty("derleme").GetString(), body.GetProperty("durum").GetString(), body.GetProperty("talep").GetString(), body.GetProperty("surum").GetString()));

        ReleaseRow row = await ReadAsync(Db, id, Ct);
        Assert.Equal(("dev", "geri_alma", MonthVersion(2), target), (row.Derleme, row.Talep, row.Surum, row.KaynakReleaseId));
        Assert.Equal("Geri alma notu.", row.Notlar);
        Assert.Equal(AdminEmail, row.Olusturan);
        Assert.Matches(DataVersionPattern(), row.DataVersion);
    }

    [Fact]
    public async Task A_withdrawn_release_can_be_the_rollback_target_and_the_new_row_keeps_the_target_flavor()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        int target = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "public", "geri_cekildi", "terfi", YayinlandiAt: now.AddHours(-2)), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "public", "yayinlandi", "terfi", YayinlandiAt: now.AddHours(-1)), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{target}/rollback", null, Ct);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        ReleaseRow row = await ReadAsync(Db, (await ReadBodyAsync(response)).GetProperty("id").GetInt32(), Ct);
        Assert.Equal(("public", "geri_alma", target), (row.Derleme, row.Talep, row.KaynakReleaseId));
    }

    [Fact]
    public async Task Rolling_back_to_the_release_that_is_already_live_is_a_409()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-2)), Ct);
        int live = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-1)), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{live}/rollback", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "durum-gecisi-gecersiz");
        Assert.Equal(2, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task The_live_release_is_decided_per_flavor()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        int devRelease = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-3)), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "internal", "yayinlandi", YayinlandiAt: now.AddHours(-1)), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{devRelease}/rollback", null, Ct);

        // dev'in tek yayini zaten guncel: baska derleme turundeki daha yeni yayin onu "eski" yapmaz.
        await AssertProblemAsync(response, HttpStatusCode.Conflict, "durum-gecisi-gecersiz");
    }

    [Theory]
    [InlineData("hazirlaniyor")]
    [InlineData("dogrulandi")]
    [InlineData("basarisiz")]
    public async Task A_release_that_was_never_published_is_not_a_rollback_target(string status)
    {
        using HttpClient admin = await AdminAsync();
        int target = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", status), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{target}/rollback", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "durum-gecisi-gecersiz");
    }

    [Fact]
    public async Task Rolling_back_to_an_unknown_release_is_a_404()
    {
        using HttpClient admin = await AdminAsync();

        using HttpResponseMessage response = await PostAsync(admin, "/api/v1/releases/99999/rollback", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.NotFound, "bulunamadi");
    }

    [Fact]
    public async Task An_open_row_of_the_target_flavor_blocks_a_rollback_with_409_yayin_suruyor()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        int target = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-3)), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-2)), Ct);
        int open = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(2), "dev", "dogrulandi", "geri_alma", target), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{target}/rollback", null, Ct);

        await AssertProblemAsync(response, HttpStatusCode.Conflict, "yayin-suruyor");
        JsonElement running = (await ReadBodyAsync(response)).GetProperty("yayin");
        Assert.Equal((open, "geri_alma"), (running.GetProperty("id").GetInt32(), running.GetProperty("talep").GetString()));
    }

    [Fact]
    public async Task Rollback_notes_over_2000_code_points_are_a_400()
    {
        using HttpClient admin = await AdminAsync();
        DateTime now = DateTime.UtcNow;
        int target = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-2)), Ct);
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(1), "dev", "yayinlandi", YayinlandiAt: now.AddHours(-1)), Ct);

        using HttpResponseMessage response = await PostAsync(admin, $"/api/v1/releases/{target}/rollback", new { notlar = new string('a', 2001) }, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
    }

    [Fact]
    public async Task A_post_with_a_json_body_to_a_route_that_takes_none_is_still_handled()
    {
        using HttpClient admin = await AdminAsync();
        int source = await InsertReleaseAsync(Db, new ReleaseSeed(MonthVersion(0), "internal", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);

        using HttpResponseMessage unknownField = await admin.PostAsJsonAsync($"/api/v1/releases/{source}/promote", new { baska = "x" }, Ct);

        await AssertProblemAsync(unknownField, HttpStatusCode.BadRequest, "dogrulama");
    }
}
