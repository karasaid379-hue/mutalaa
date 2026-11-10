using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>Oturum: giris, kilit, cerez ozellikleri, 401/403 govdeleri (Docker'li; gercek Program, gercek veritabani).</summary>
public class AuthTests(EditorialDatabase<AuthTests> fixture) : ApiTestBase<AuthTests>(fixture), IClassFixture<EditorialDatabase<AuthTests>>
{
    // Sentetik degerler: gercek hesap degildir.
    private const string EditorEmail = "editor@example.test";
    private const string EditorPassword = "deneme-parolasi-123";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static string SetCookie(HttpResponseMessage response) =>
        string.Join("; ", response.Headers.TryGetValues("Set-Cookie", out IEnumerable<string>? values) ? values : []);

    [Fact]
    public async Task A_correct_login_returns_the_session_and_the_cookie_opens_me()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(login, Ct);
        Assert.Equal(EditorEmail, body.GetProperty("kullanici").GetProperty("email").GetString());
        Assert.Equal(["editor"], body.GetProperty("roller").EnumerateArray().Select(e => e.GetString()));

        using HttpResponseMessage me = await client.GetAsync("/api/v1/auth/me", Ct);
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);
        JsonElement meBody = await ApiFactory.ReadJsonAsync(me, Ct);
        Assert.Equal(EditorEmail, meBody.GetProperty("kullanici").GetProperty("email").GetString());
    }

    [Fact]
    public async Task The_session_cookie_is_secure_httponly_and_samesite_strict_and_carries_no_password()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        string cookie = SetCookie(login);
        Assert.StartsWith("mutalaa.editor=", cookie, StringComparison.Ordinal);
        Assert.Contains("secure", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("httponly", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=strict", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(EditorPassword, cookie, StringComparison.Ordinal);
    }

    [Fact]
    public async Task In_the_Testing_environment_the_cookie_is_secure_even_over_plain_http()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateClient();

        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        Assert.Contains("secure", SetCookie(login), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task In_the_Development_environment_the_cookie_follows_the_request_scheme()
    {
        ApiFactory development = CreateFactory("Development");
        await development.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = development.CreateClient();

        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        string cookie = SetCookie(login);
        Assert.StartsWith("mutalaa.editor=", cookie, StringComparison.Ordinal);
        Assert.DoesNotContain("secure", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("httponly", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=strict", cookie, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task A_wrong_password_and_an_unknown_user_get_the_same_401_problem()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage wrongPassword = await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct);
        using HttpResponseMessage unknownUser = await ApiFactory.LoginAsync(client, "yok@example.test", EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, wrongPassword.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, unknownUser.StatusCode);
        Assert.Equal("application/problem+json", wrongPassword.Content.Headers.ContentType?.MediaType);
        JsonElement a = await ApiFactory.ReadJsonAsync(wrongPassword, Ct);
        JsonElement b = await ApiFactory.ReadJsonAsync(unknownUser, Ct);
        Assert.Equal("urn:mutalaa:problem:oturum-acilamadi", a.GetProperty("type").GetString());
        Assert.Equal(a.GetProperty("type").GetString(), b.GetProperty("type").GetString());
        Assert.Equal(a.GetProperty("title").GetString(), b.GetProperty("title").GetString());
        Assert.Equal(a.GetProperty("detail").GetString(), b.GetProperty("detail").GetString());
        Assert.Empty(SetCookie(wrongPassword));
        Assert.Empty(SetCookie(unknownUser));
    }

    [Fact]
    public async Task After_five_wrong_attempts_even_the_correct_password_is_refused_with_401()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        for (int attempt = 1; attempt <= 5; attempt++)
        {
            using HttpResponseMessage wrong = await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct);
            Assert.Equal(HttpStatusCode.Unauthorized, wrong.StatusCode);
        }

        using HttpResponseMessage correct = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, correct.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(correct, Ct);
        Assert.Equal("urn:mutalaa:problem:oturum-acilamadi", body.GetProperty("type").GetString());
        Assert.Empty(SetCookie(correct));
        Assert.NotNull(await Db.ScalarAsync<DateTime?>("SELECT lockout_end::timestamp FROM kimlik.users", Ct));
    }

    [Fact]
    public async Task Four_wrong_attempts_do_not_lock_the_account()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        for (int attempt = 1; attempt <= 4; attempt++)
        {
            using HttpResponseMessage wrong = await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct);
            Assert.Equal(HttpStatusCode.Unauthorized, wrong.StatusCode);
        }

        using HttpResponseMessage correct = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.OK, correct.StatusCode);
    }

    [Fact]
    public async Task Me_without_a_session_is_a_401_problem_without_a_Location_header()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/auth/me", Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Null(response.Headers.Location);
        Assert.False(response.Headers.Contains("Location"));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:oturum-acilamadi", body.GetProperty("type").GetString());
        Assert.False(string.IsNullOrEmpty(body.GetProperty("traceId").GetString()));
    }

    [Fact]
    public async Task An_editor_calling_an_admin_endpoint_gets_a_403_problem_without_a_Location_header()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();
        (await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct)).Dispose();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/users", Ct);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.False(response.Headers.Contains("Location"));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:yetki-yok", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task A_user_without_any_role_cannot_use_the_editor_endpoints()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword);
        using HttpClient client = Factory.CreateApiClient();
        (await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct)).Dispose();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/auth/me", Ct);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task Logout_ends_the_session()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();
        (await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct)).Dispose();

        using HttpResponseMessage logout = await client.PostAsync("/api/v1/auth/logout", content: null, Ct);
        using HttpResponseMessage me = await client.GetAsync("/api/v1/auth/me", Ct);

        Assert.Equal(HttpStatusCode.NoContent, logout.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, me.StatusCode);
    }

    [Fact]
    public async Task A_login_body_without_a_password_is_a_400_validation_problem_naming_the_field_in_snake_case()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.PostAsJsonAsync("/api/v1/auth/login", new { email = EditorEmail }, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
        Assert.True(body.GetProperty("errors").TryGetProperty("parola", out JsonElement messages));
        Assert.NotEmpty(messages.EnumerateArray());
    }

    [Fact]
    public async Task An_unknown_json_field_is_a_400()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/auth/login",
            new { email = EditorEmail, parola = EditorPassword, ekstra = 1 },
            Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task Login_works_under_tr_TR_with_a_dotted_and_dotless_I_email_in_another_case()
    {
        await Factory.AddUserAsync("ISIK.Ilhan@example.test", EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        HttpStatusCode status = default;
        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage response = await ApiFactory.LoginAsync(client, "isik.ilhan@example.test", EditorPassword, Ct);
            status = response.StatusCode;
        });

        Assert.Equal(HttpStatusCode.OK, status);
    }

    [Fact]
    public async Task The_log_never_contains_the_email_or_the_password()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();

        (await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct)).Dispose();
        (await ApiFactory.LoginAsync(client, "yok@example.test", "baska-yanlis-parola-1", Ct)).Dispose();
        (await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct)).Dispose();
        (await client.GetAsync("/api/v1/auth/me", Ct)).Dispose();
        for (int attempt = 0; attempt < 5; attempt++)
        {
            (await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct)).Dispose();
        }

        Assert.NotEmpty(Factory.Logs.Messages);
        string log = Factory.Logs.Text;
        Assert.DoesNotContain(EditorEmail, log, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("yok@example.test", log, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(EditorPassword, log, StringComparison.Ordinal);
        Assert.DoesNotContain("yanlis-parola", log, StringComparison.Ordinal);
        Assert.DoesNotContain("mutalaa.editor=", log, StringComparison.Ordinal);
    }
}
