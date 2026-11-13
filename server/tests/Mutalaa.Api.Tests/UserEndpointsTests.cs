using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>/api/v1/users: yalniz admin; olusturma, listeleme, rol degisimi (Docker'li).</summary>
public class UserEndpointsTests(EditorialDatabase<UserEndpointsTests> fixture)
    : ApiTestBase<UserEndpointsTests>(fixture), IClassFixture<EditorialDatabase<UserEndpointsTests>>
{
    // Sentetik degerler: gercek hesap degildir.
    private const string AdminEmail = "yonetici@example.test";
    private const string AdminPassword = "yonetici-parolasi-123";
    private const string EditorEmail = "editor@example.test";
    private const string EditorPassword = "editor-parolasi-1234";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private async Task<HttpClient> AdminClientAsync(ApiFactory? factory = null)
    {
        factory ??= Factory;
        EditorUser? existing = await FindAsync(factory, AdminEmail);
        if (existing is null)
        {
            await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);
        }

        HttpClient client = factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, AdminEmail, AdminPassword, Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    private static async Task<EditorUser?> FindAsync(ApiFactory factory, string email)
    {
        await using AsyncServiceScope scope = factory.Services.CreateAsyncScope();
        return await scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>().FindByEmailAsync(email);
    }

    private static Task<HttpResponseMessage> CreateUserAsync(HttpClient client, string email, string password, params string[] roles) =>
        client.PostAsJsonAsync("/api/v1/users", new { email, parola = password, roller = roles }, Ct);

    [Fact]
    public async Task An_admin_creates_a_user_who_can_then_log_in_with_the_given_roles()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage created = await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor");

        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(created, Ct);
        Assert.Equal(EditorEmail, body.GetProperty("email").GetString());
        Assert.Equal(["editor"], body.GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
        Assert.False(body.GetProperty("kilitli").GetBoolean());
        Assert.False(string.IsNullOrEmpty(body.GetProperty("id").GetString()));

        using HttpClient editor = Factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(editor, EditorEmail, EditorPassword, Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
    }

    [Fact]
    public async Task The_list_returns_the_users_with_roles_and_never_a_password_or_hash()
    {
        using HttpClient admin = await AdminClientAsync();
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor", "admin")).Dispose();

        using HttpResponseMessage response = await admin.GetAsync("/api/v1/users", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        string text = await response.Content.ReadAsStringAsync(Ct);
        Assert.DoesNotContain("hash", text, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("parola", text, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("stamp", text, StringComparison.OrdinalIgnoreCase);
        using JsonDocument document = JsonDocument.Parse(text);
        JsonElement[] users = [.. document.RootElement.EnumerateArray()];
        Assert.Equal([EditorEmail, AdminEmail], users.Select(u => u.GetProperty("email").GetString()));
        Assert.Equal(["admin", "editor"], users[0].GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
        Assert.Equal(["admin"], users[1].GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
    }

    [Fact]
    public async Task A_second_user_with_the_same_email_in_any_case_is_a_409_conflict()
    {
        using HttpClient admin = await AdminClientAsync();
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor")).Dispose();

        using HttpResponseMessage duplicate = await CreateUserAsync(admin, "EDITOR@Example.Test", EditorPassword, "editor");

        Assert.Equal(HttpStatusCode.Conflict, duplicate.StatusCode);
        Assert.Equal("application/problem+json", duplicate.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ApiFactory.ReadJsonAsync(duplicate, Ct);
        Assert.Equal("urn:mutalaa:problem:cakisma", body.GetProperty("type").GetString());
        Assert.Equal(2L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
    }

    [Fact]
    public async Task An_admin_can_create_an_expert_user_and_change_a_role_to_uzman()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage created = await CreateUserAsync(admin, "uzman-yeni@example.test", EditorPassword, "uzman");
        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(created, Ct);
        Assert.Equal(["uzman"], body.GetProperty("roller").EnumerateArray().Select(e => e.GetString()));

        using HttpResponseMessage editor = await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor");
        string id = (await ApiFactory.ReadJsonAsync(editor, Ct)).GetProperty("id").GetString()!;
        using HttpResponseMessage changed = await admin.PutAsJsonAsync($"/api/v1/users/{id}/roles", new { roller = new[] { "editor", "uzman" } }, Ct);

        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);
        Assert.Equal(["editor", "uzman"], (await ApiFactory.ReadJsonAsync(changed, Ct)).GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
    }

    [Fact]
    public async Task A_short_password_is_a_400_with_the_identity_errors_and_creates_nothing()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage response = await CreateUserAsync(admin, EditorEmail, "kisa-parola", "editor");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
        JsonElement[] errors = [.. body.GetProperty("hatalar").EnumerateArray()];
        Assert.Contains(errors, e => e.GetProperty("kod").GetString() == "PasswordTooShort");
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
        Assert.DoesNotContain("kisa-parola", await response.Content.ReadAsStringAsync(Ct), StringComparison.Ordinal);
    }

    [Fact]
    public async Task An_unknown_role_is_a_400_and_creates_nothing()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage response = await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor", "superuser");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.True(body.GetProperty("errors").TryGetProperty("roller", out _));
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
    }

    [Fact]
    public async Task A_create_body_without_roles_is_a_400_validation_problem()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage response = await admin.PostAsJsonAsync(
            "/api/v1/users",
            new { email = EditorEmail, parola = EditorPassword },
            Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.True(body.GetProperty("errors").TryGetProperty("roller", out _));
    }

    [Fact]
    public async Task Changing_roles_renews_the_security_stamp_and_ends_the_old_session_of_the_user()
    {
        // Dogrulama araligi sifir: cerezdeki damga her istekte denetlenir (uretimde 1 dakika).
        ApiFactory factory = CreateFactory(configureServices: services =>
            services.Configure<SecurityStampValidatorOptions>(o => o.ValidationInterval = TimeSpan.Zero));
        using HttpClient admin = await AdminClientAsync(factory);
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor")).Dispose();
        using HttpClient editor = factory.CreateApiClient();
        (await ApiFactory.LoginAsync(editor, EditorEmail, EditorPassword, Ct)).Dispose();
        using (HttpResponseMessage before = await editor.GetAsync("/api/v1/auth/me", Ct))
        {
            Assert.Equal(HttpStatusCode.OK, before.StatusCode);
        }

        string stampBefore = await Db.ScalarAsync<string>("SELECT security_stamp FROM kimlik.users WHERE email = @e", Ct, ("e", EditorEmail));
        string id = await Db.ScalarAsync<string>("SELECT id FROM kimlik.users WHERE email = @e", Ct, ("e", EditorEmail));

        // Cerezin IssuedUtc degeri saniye duyarlidir; damga denetimi ancak gecen sure sifirdan buyukse isler.
        await Task.Delay(TimeSpan.FromMilliseconds(1100), Ct);
        using HttpResponseMessage changed = await admin.PutAsJsonAsync($"/api/v1/users/{id}/roles", new { roller = new[] { "admin" } }, Ct);

        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(changed, Ct);
        Assert.Equal(["admin"], body.GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
        string stampAfter = await Db.ScalarAsync<string>("SELECT security_stamp FROM kimlik.users WHERE email = @e", Ct, ("e", EditorEmail));
        Assert.NotEqual(stampBefore, stampAfter);
        Assert.Equal(["admin"], await Db.ColumnAsync("SELECT r.name FROM kimlik.user_roles ur JOIN kimlik.roles r ON r.id = ur.role_id WHERE ur.user_id = @id", Ct, ("id", id)));

        // Eski oturum artik gecersiz: kullanici yeniden giris yapmali.
        using HttpResponseMessage stale = await editor.GetAsync("/api/v1/auth/me", Ct);
        Assert.Equal(HttpStatusCode.Unauthorized, stale.StatusCode);
        using HttpResponseMessage relogin = await ApiFactory.LoginAsync(editor, EditorEmail, EditorPassword, Ct);
        Assert.Equal(HttpStatusCode.OK, relogin.StatusCode);
        using HttpResponseMessage fresh = await editor.GetAsync("/api/v1/users", Ct);
        Assert.Equal(HttpStatusCode.OK, fresh.StatusCode);
    }

    [Fact]
    public async Task Putting_the_same_roles_again_changes_nothing_and_keeps_the_security_stamp()
    {
        using HttpClient admin = await AdminClientAsync();
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor")).Dispose();
        string id = await Db.ScalarAsync<string>("SELECT id FROM kimlik.users WHERE email = @e", Ct, ("e", EditorEmail));
        string stampBefore = await Db.ScalarAsync<string>("SELECT security_stamp FROM kimlik.users WHERE id = @id", Ct, ("id", id));

        using HttpResponseMessage response = await admin.PutAsJsonAsync($"/api/v1/users/{id}/roles", new { roller = new[] { "editor", "editor" } }, Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(stampBefore, await Db.ScalarAsync<string>("SELECT security_stamp FROM kimlik.users WHERE id = @id", Ct, ("id", id)));
    }

    [Fact]
    public async Task The_last_admin_cannot_lose_the_admin_role_but_can_once_another_admin_exists()
    {
        using HttpClient admin = await AdminClientAsync();
        string adminId = await Db.ScalarAsync<string>("SELECT id FROM kimlik.users WHERE email = @e", Ct, ("e", AdminEmail));

        using HttpResponseMessage refused = await admin.PutAsJsonAsync($"/api/v1/users/{adminId}/roles", new { roller = new[] { "editor" } }, Ct);

        Assert.Equal(HttpStatusCode.Conflict, refused.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(refused, Ct);
        Assert.Equal("urn:mutalaa:problem:durum-gecisi-gecersiz", body.GetProperty("type").GetString());
        Assert.Equal(["admin"], await Db.ColumnAsync("SELECT r.name FROM kimlik.user_roles ur JOIN kimlik.roles r ON r.id = ur.role_id WHERE ur.user_id = @id", Ct, ("id", adminId)));

        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "admin")).Dispose();
        using HttpResponseMessage allowed = await admin.PutAsJsonAsync($"/api/v1/users/{adminId}/roles", new { roller = new[] { "editor" } }, Ct);

        Assert.Equal(HttpStatusCode.OK, allowed.StatusCode);
    }

    [Fact]
    public async Task Roles_of_an_unknown_user_is_a_404()
    {
        using HttpClient admin = await AdminClientAsync();

        using HttpResponseMessage response = await admin.PutAsJsonAsync("/api/v1/users/yok/roles", new { roller = new[] { "editor" } }, Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:bulunamadi", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task Every_users_endpoint_is_forbidden_to_an_editor_and_unauthorized_without_a_session()
    {
        await Factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        using HttpClient anonymous = Factory.CreateApiClient();
        using HttpClient editor = Factory.CreateApiClient();
        (await ApiFactory.LoginAsync(editor, EditorEmail, EditorPassword, Ct)).Dispose();

        foreach (HttpClient client in new[] { anonymous, editor })
        {
            HttpStatusCode expected = ReferenceEquals(client, anonymous) ? HttpStatusCode.Unauthorized : HttpStatusCode.Forbidden;
            using HttpResponseMessage list = await client.GetAsync("/api/v1/users", Ct);
            using HttpResponseMessage create = await CreateUserAsync(client, "yeni@example.test", EditorPassword, "editor");
            using HttpResponseMessage roles = await client.PutAsJsonAsync("/api/v1/users/x/roles", new { roller = new[] { "admin" } }, Ct);

            Assert.Equal(expected, list.StatusCode);
            Assert.Equal(expected, create.StatusCode);
            Assert.Equal(expected, roles.StatusCode);
        }

        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", Ct));
    }

    [Fact]
    public async Task The_log_of_user_management_never_contains_emails_or_passwords()
    {
        using HttpClient admin = await AdminClientAsync();
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor")).Dispose();
        (await CreateUserAsync(admin, EditorEmail, EditorPassword, "editor")).Dispose();
        (await CreateUserAsync(admin, "kisa@example.test", "kisa", "editor")).Dispose();

        string log = Factory.Logs.Text;
        Assert.DoesNotContain(EditorEmail, log, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(AdminEmail, log, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(EditorPassword, log, StringComparison.Ordinal);
        Assert.DoesNotContain(AdminPassword, log, StringComparison.Ordinal);
    }
}
