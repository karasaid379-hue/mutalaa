using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>Oturum ve kullanici uclari: kilitli hesap yaniti, bos rol listesi, NUL girdisi (Docker'li).</summary>
public class AuthUsersFixTests(EditorialDatabase<AuthUsersFixTests> fixture)
    : ApiTestBase<AuthUsersFixTests>(fixture), IClassFixture<EditorialDatabase<AuthUsersFixTests>>
{
    // Sentetik degerler: gercek hesap degildir.
    private const string AdminEmail = "yonetici@example.test";
    private const string AdminPassword = "yonetici-parolasi-123";
    private const string EditorEmail = "editor@example.test";
    private const string EditorPassword = "editor-parolasi-1234";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private async Task<HttpClient> AdminClientAsync()
    {
        await Factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);
        HttpClient client = Factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, AdminEmail, AdminPassword, Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    private static async Task AssertValidationAsync(HttpResponseMessage response, string field)
    {
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
        Assert.True(body.GetProperty("errors").TryGetProperty(field, out JsonElement messages), $"errors.{field} yok.");
        Assert.NotEmpty(messages.EnumerateArray());
    }

    [Fact]
    public async Task A_locked_account_gets_the_same_401_body_as_an_unknown_user()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient client = Factory.CreateApiClient();
        for (int attempt = 1; attempt <= 5; attempt++)
        {
            (await ApiFactory.LoginAsync(client, EditorEmail, "yanlis-parola-123456", Ct)).Dispose();
        }

        using HttpResponseMessage locked = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);
        using HttpResponseMessage unknown = await ApiFactory.LoginAsync(client, "yok@example.test", EditorPassword, Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, unknown.StatusCode);
        JsonElement a = await ApiFactory.ReadJsonAsync(locked, Ct);
        JsonElement b = await ApiFactory.ReadJsonAsync(unknown, Ct);
        Assert.Equal("urn:mutalaa:problem:oturum-acilamadi", a.GetProperty("type").GetString());
        Assert.Equal(b.GetProperty("type").GetString(), a.GetProperty("type").GetString());
        Assert.Equal(b.GetProperty("title").GetString(), a.GetProperty("title").GetString());
        Assert.Equal(b.GetProperty("detail").GetString(), a.GetProperty("detail").GetString());
        Assert.Equal(b.GetProperty("status").GetInt32(), a.GetProperty("status").GetInt32());
        Assert.False(locked.Headers.Contains("Set-Cookie"));
    }

    [Fact]
    public async Task Creating_a_user_without_roles_is_a_400_validation_problem_and_creates_nobody()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage response = await admin.PostAsJsonAsync(
            "/api/v1/users",
            new { email = EditorEmail, parola = EditorPassword, roller = Array.Empty<string>() },
            Ct);

        await AssertValidationAsync(response, "roller");
        Assert.Equal(1, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
    }

    [Fact]
    public async Task Setting_an_empty_role_list_is_a_400_validation_problem_and_changes_nothing()
    {
        using HttpClient admin = await AdminClientAsync();
        EditorUser editor = await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);

        using HttpResponseMessage response = await admin.PutAsJsonAsync($"/api/v1/users/{editor.Id}/roles", new { roller = Array.Empty<string>() }, Ct);

        await AssertValidationAsync(response, "roller");
        Assert.Equal(1, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.user_roles WHERE user_id = @id", Ct, ("id", editor.Id)));
    }

    [Fact]
    public async Task An_empty_role_list_for_the_last_admin_is_still_a_400_validation_problem()
    {
        using HttpClient admin = await AdminClientAsync();
        string adminId = await Db.ScalarAsync<string>("SELECT id FROM kimlik.users WHERE email = @e", Ct, ("e", AdminEmail));

        using HttpResponseMessage response = await admin.PutAsJsonAsync($"/api/v1/users/{adminId}/roles", new { roller = Array.Empty<string>() }, Ct);

        await AssertValidationAsync(response, "roller");
    }

    [Fact]
    public async Task A_NUL_in_the_login_email_is_a_400_validation_problem()
    {
        using HttpClient client = Factory.CreateApiClient();
        using StringContent body = new("{\"email\":\"a\\u0000@example.test\",\"parola\":\"x\"}", Encoding.UTF8, "application/json");

        using HttpResponseMessage response = await client.PostAsync("/api/v1/auth/login", body, Ct);

        await AssertValidationAsync(response, "email");
    }

    [Fact]
    public async Task A_NUL_in_the_new_user_email_is_a_400_validation_problem()
    {
        using HttpClient admin = await AdminClientAsync();
        using StringContent body = new(
            "{\"email\":\"a\\u0000@example.test\",\"parola\":\"editor-parolasi-1234\",\"roller\":[\"editor\"]}",
            Encoding.UTF8,
            "application/json");

        using HttpResponseMessage response = await admin.PostAsync("/api/v1/users", body, Ct);

        await AssertValidationAsync(response, "email");
        Assert.Equal(1, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
    }
}
