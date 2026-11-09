using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>Mutalaa:Auth:DevAutoLogin: yalniz Development ve yalniz loopback; baska ortamda acilis durur (Docker'li).</summary>
public class DevAutoLoginTests(EditorialDatabase<DevAutoLoginTests> fixture)
    : ApiTestBase<DevAutoLoginTests>(fixture), IClassFixture<EditorialDatabase<DevAutoLoginTests>>
{
    // Sentetik degerler: gercek hesap degildir.
    private const string AdminEmail = "yonetici@example.test";
    private const string AdminPassword = "yonetici-parolasi-123";
    private const string EnabledKey = "Mutalaa:Auth:DevAutoLogin";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private ApiFactory DevFactory(bool autoLogin = true) => CreateFactory(
        "Development",
        new Dictionary<string, string?>
        {
            [EnabledKey] = autoLogin ? "true" : "false",
            [ApiFactory.AdminEmailKey] = AdminEmail,
        });

    /// <summary>TestServer varsayilan olarak RemoteIpAddress vermez (null); burada istenen adres verilir.</summary>
    private static async Task<(HttpStatusCode Status, string Body, string SetCookie)> MeFromAsync(ApiFactory factory, IPAddress? remote)
    {
        HttpContext context = await factory.Server.SendAsync(c =>
        {
            c.Request.Method = HttpMethods.Get;
            c.Request.Scheme = "https";
            c.Request.Host = new HostString("localhost");
            c.Request.Path = "/api/v1/auth/me";
            c.Connection.RemoteIpAddress = remote;
        });

        using StreamReader reader = new(context.Response.Body, Encoding.UTF8);
        string body = await reader.ReadToEndAsync(Ct);
        return ((HttpStatusCode)context.Response.StatusCode, body, context.Response.Headers.SetCookie.ToString());
    }

    [Fact]
    public void An_enabled_flag_outside_Development_stops_the_host_at_startup()
    {
        foreach (string environment in new[] { "Testing", "Production", "Staging" })
        {
            ApiFactory factory = CreateFactory(environment, new Dictionary<string, string?> { [EnabledKey] = "true" });

            Exception exception = Assert.ThrowsAny<Exception>(() => factory.CreateClient());

            Assert.Contains(EnabledKey, Flatten(exception), StringComparison.Ordinal);
        }
    }

    private static string Flatten(Exception exception)
    {
        StringBuilder text = new();
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            text.AppendLine(current.GetType().Name).AppendLine(current.Message);
        }

        return text.ToString();
    }

    [Fact]
    public async Task In_Development_a_loopback_request_without_a_session_signs_in_as_the_seed_admin()
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode status, string body, string setCookie) = await MeFromAsync(factory, IPAddress.Loopback);

        Assert.Equal(HttpStatusCode.OK, status);
        using JsonDocument document = JsonDocument.Parse(body);
        Assert.Equal(AdminEmail, document.RootElement.GetProperty("kullanici").GetProperty("email").GetString());
        Assert.Equal(["admin"], document.RootElement.GetProperty("roller").EnumerateArray().Select(e => e.GetString()));
        Assert.StartsWith("mutalaa.editor=", setCookie, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_IPv6_loopback_and_an_IPv4_mapped_loopback_also_count_as_loopback()
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode v6, _, _) = await MeFromAsync(factory, IPAddress.IPv6Loopback);
        (HttpStatusCode mapped, _, _) = await MeFromAsync(factory, IPAddress.Parse("::ffff:127.0.0.1"));

        Assert.Equal(HttpStatusCode.OK, v6);
        Assert.Equal(HttpStatusCode.OK, mapped);
    }

    [Fact]
    public async Task A_null_or_remote_address_does_not_sign_in()
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode unknown, _, string unknownCookie) = await MeFromAsync(factory, remote: null);
        (HttpStatusCode remote, _, string remoteCookie) = await MeFromAsync(factory, IPAddress.Parse("203.0.113.5"));

        Assert.Equal(HttpStatusCode.Unauthorized, unknown);
        Assert.Equal(HttpStatusCode.Unauthorized, remote);
        Assert.Empty(unknownCookie);
        Assert.Empty(remoteCookie);
    }

    [Fact]
    public async Task With_the_flag_off_even_a_loopback_request_does_not_sign_in()
    {
        ApiFactory factory = DevFactory(autoLogin: false);
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode status, _, string setCookie) = await MeFromAsync(factory, IPAddress.Loopback);

        Assert.Equal(HttpStatusCode.Unauthorized, status);
        Assert.Empty(setCookie);
    }

    [Fact]
    public async Task When_the_seed_admin_does_not_exist_the_request_stays_anonymous()
    {
        ApiFactory factory = DevFactory();

        (HttpStatusCode status, _, _) = await MeFromAsync(factory, IPAddress.Loopback);

        Assert.Equal(HttpStatusCode.Unauthorized, status);
    }

    [Fact]
    public async Task An_existing_session_is_left_alone_even_on_loopback()
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);
        await factory.AddUserAsync("editor@example.test", "editor-parolasi-1234", Roles.Editor);
        using HttpClient client = factory.CreateApiClient();
        (await ApiFactory.LoginAsync(client, "editor@example.test", "editor-parolasi-1234", Ct)).Dispose();

        using HttpResponseMessage me = await client.GetAsync("/api/v1/auth/me", Ct);

        // TestServer istemcisi RemoteIpAddress vermez; oturum zaten cerezden gelir.
        JsonElement body = await ApiFactory.ReadJsonAsync(me, Ct);
        Assert.Equal("editor@example.test", body.GetProperty("kullanici").GetProperty("email").GetString());
    }
}
