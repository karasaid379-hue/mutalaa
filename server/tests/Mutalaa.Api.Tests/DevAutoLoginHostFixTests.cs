using System.Net;
using System.Text;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>DevAutoLogin DNS rebinding korumasi: loopback uzak adres yetmez, Host basligi da loopback olmalidir (Docker'li).</summary>
public class DevAutoLoginHostFixTests(EditorialDatabase<DevAutoLoginHostFixTests> fixture)
    : ApiTestBase<DevAutoLoginHostFixTests>(fixture), IClassFixture<EditorialDatabase<DevAutoLoginHostFixTests>>
{
    // Sentetik degerler: gercek hesap degildir.
    private const string AdminEmail = "yonetici@example.test";
    private const string AdminPassword = "yonetici-parolasi-123";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private ApiFactory DevFactory() => CreateFactory(
        "Development",
        new Dictionary<string, string?>
        {
            ["Mutalaa:Auth:DevAutoLogin"] = "true",
            [ApiFactory.AdminEmailKey] = AdminEmail,
        });

    private static async Task<(HttpStatusCode Status, string SetCookie)> MeAsync(ApiFactory factory, HostString host)
    {
        HttpContext context = await factory.Server.SendAsync(c =>
        {
            c.Request.Method = HttpMethods.Get;
            c.Request.Scheme = "https";
            c.Request.Host = host;
            c.Request.Path = "/api/v1/auth/me";
            c.Connection.RemoteIpAddress = IPAddress.Loopback;
        });

        using StreamReader reader = new(context.Response.Body, Encoding.UTF8);
        _ = await reader.ReadToEndAsync(Ct);
        return ((HttpStatusCode)context.Response.StatusCode, context.Response.Headers.SetCookie.ToString());
    }

    [Theory]
    [InlineData("evil.example")]
    [InlineData("evil.example:5080")]
    [InlineData("localhost.evil.example")]
    [InlineData("127.0.0.1.evil.example")]
    [InlineData("192.0.2.10")]
    public async Task A_loopback_remote_address_with_a_foreign_Host_does_not_sign_in(string host)
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode status, string setCookie) = await MeAsync(factory, new HostString(host));

        Assert.Equal(HttpStatusCode.Unauthorized, status);
        Assert.Empty(setCookie);
    }

    [Theory]
    [InlineData("localhost")]
    [InlineData("localhost:5080")]
    [InlineData("LocalHost:5080")]
    [InlineData("127.0.0.1")]
    [InlineData("127.0.0.1:5080")]
    [InlineData("[::1]")]
    [InlineData("[::1]:5080")]
    public async Task A_loopback_Host_with_a_loopback_remote_address_signs_in(string host)
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode status, string setCookie) = await MeAsync(factory, new HostString(host));

        Assert.Equal(HttpStatusCode.OK, status);
        Assert.StartsWith("mutalaa.editor=", setCookie, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_missing_Host_does_not_sign_in()
    {
        ApiFactory factory = DevFactory();
        await factory.AddUserAsync(AdminEmail, AdminPassword, Roles.Admin);

        (HttpStatusCode status, string setCookie) = await MeAsync(factory, default);

        Assert.Equal(HttpStatusCode.Unauthorized, status);
        Assert.Empty(setCookie);
    }

    [Theory]
    [InlineData("localhost", true)]
    [InlineData("LOCALHOST", true)]
    [InlineData("127.0.0.1", true)]
    [InlineData("[::1]", true)]
    [InlineData("::1", true)]
    [InlineData("localhost.", false)]
    [InlineData("evil.example", false)]
    [InlineData("", false)]
    public void IsLoopbackHost_matches_only_the_three_loopback_names(string host, bool expected)
    {
        Assert.Equal(expected, DevAutoLogin.IsLoopbackHost(host));
    }
}
