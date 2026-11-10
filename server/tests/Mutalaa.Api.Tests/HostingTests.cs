using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Configuration.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Settings;
using Mutalaa.Api.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>Acilis: saglik uclari, ProblemDetails, ayarlar, ortam ve gunluk (Docker'li).</summary>
public class HostingTests(EditorialDatabase<HostingTests> fixture)
    : ApiTestBase<HostingTests>(fixture), IClassFixture<EditorialDatabase<HostingTests>>
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static bool HasUserSecrets(IConfiguration configuration) =>
        ((IConfigurationRoot)configuration).Providers
            .OfType<JsonConfigurationProvider>()
            .Any(p => p.Source.Path?.EndsWith("secrets.json", StringComparison.OrdinalIgnoreCase) == true);

    [Fact]
    public async Task Live_is_200_for_anonymous_get_and_head()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage get = await client.GetAsync("/health/live", Ct);
        using HttpResponseMessage head = await client.SendAsync(new HttpRequestMessage(HttpMethod.Head, "/health/live"), Ct);

        Assert.Equal(HttpStatusCode.OK, get.StatusCode);
        Assert.Equal(HttpStatusCode.OK, head.StatusCode);
    }

    [Fact]
    public async Task Ready_is_200_with_a_reachable_database()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync("/health/ready", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Ready_is_503_when_the_database_cannot_be_reached_but_live_stays_200()
    {
        ApiFactory unreachable = CreateFactory(connectionString: "Host=127.0.0.1;Port=1;Username=x;Password=y;Database=z;Timeout=2;Pooling=false");
        using HttpClient client = unreachable.CreateApiClient();

        using HttpResponseMessage ready = await client.GetAsync("/health/ready", Ct);
        using HttpResponseMessage live = await client.GetAsync("/health/live", Ct);

        Assert.Equal(HttpStatusCode.ServiceUnavailable, ready.StatusCode);
        Assert.Equal(HttpStatusCode.OK, live.StatusCode);
    }

    [Fact]
    public async Task A_post_to_a_health_endpoint_is_a_405_problem_with_an_Allow_header()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.PostAsync("/health/live", content: null, Ct);

        Assert.Equal(HttpStatusCode.MethodNotAllowed, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Contains("GET", response.Content.Headers.Allow);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:yontem-desteklenmiyor", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task An_unknown_path_is_a_404_problem()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/yok", Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:bulunamadi", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task Every_problem_has_a_urn_type_and_a_single_trace_id()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/auth/me", Ct);

        string text = await response.Content.ReadAsStringAsync(Ct);
        using JsonDocument document = JsonDocument.Parse(text);
        JsonElement body = document.RootElement;
        Assert.StartsWith("urn:mutalaa:problem:", body.GetProperty("type").GetString(), StringComparison.Ordinal);
        Assert.False(string.IsNullOrEmpty(body.GetProperty("traceId").GetString()));
        Assert.Equal(body.GetProperty("type").GetString()!["urn:mutalaa:problem:".Length..], body.GetProperty("kod").GetString());
        Assert.False(body.TryGetProperty("trace_id", out _));
    }

    [Fact]
    public async Task A_malformed_json_body_is_a_400_problem()
    {
        using HttpClient client = Factory.CreateApiClient();
        using StringContent content = new("{bozuk", System.Text.Encoding.UTF8, "application/json");

        using HttpResponseMessage response = await client.PostAsync("/api/v1/auth/login", content, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
    }

    [Fact]
    public async Task With_the_editor_feature_off_the_editor_endpoints_are_404_but_health_stays()
    {
        ApiFactory off = CreateFactory(settings: new Dictionary<string, string?> { ["Mutalaa:Features:Editor"] = "false" });
        using HttpClient client = off.CreateApiClient();

        using HttpResponseMessage me = await client.GetAsync("/api/v1/auth/me", Ct);
        using HttpResponseMessage login = await client.PostAsJsonAsync("/api/v1/auth/login", new { email = "a@example.test", parola = "x" }, Ct);
        using HttpResponseMessage live = await client.GetAsync("/health/live", Ct);

        Assert.Equal(HttpStatusCode.NotFound, me.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, login.StatusCode);
        Assert.Equal(HttpStatusCode.OK, live.StatusCode);
    }

    [Fact]
    public async Task The_editor_feature_is_on_by_default()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage me = await client.GetAsync("/api/v1/auth/me", Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, me.StatusCode);
    }

    [Fact]
    public void User_secrets_are_not_loaded_in_the_Testing_environment_but_are_in_Development()
    {
        IConfiguration testing = Factory.Services.GetRequiredService<IConfiguration>();
        ApiFactory development = CreateFactory("Development");
        IConfiguration dev = development.Services.GetRequiredService<IConfiguration>();

        Assert.False(HasUserSecrets(testing));
        Assert.True(HasUserSecrets(dev));
    }

    [Fact]
    public void Even_in_Development_the_test_connection_string_wins_over_user_secrets()
    {
        ApiFactory development = CreateFactory("Development");

        IConfiguration dev = development.Services.GetRequiredService<IConfiguration>();

        Assert.Equal(Db.ConnectionString, dev.GetConnectionString("Editorial"));
    }

    [Fact]
    public void Paths_default_to_the_repository_folders_as_full_paths()
    {
        ApiOptions options = Factory.Services.GetRequiredService<IOptions<ApiOptions>>().Value;

        Assert.Equal(Path.GetFullPath("data/raw"), options.RawDir);
        Assert.Equal(Path.GetFullPath("pipeline/sources"), options.SourcesDir);
        Assert.Equal(Path.GetFullPath("data/packs"), options.PacksDir);
        Assert.Equal(Path.GetFullPath(".tmp/api"), options.TempDir);
        Assert.All([options.RawDir, options.SourcesDir, options.PacksDir, options.TempDir], p => Assert.True(Path.IsPathRooted(p)));
    }

    [Fact]
    public void Configured_relative_paths_become_full_paths()
    {
        ApiFactory custom = CreateFactory(settings: new Dictionary<string, string?>
        {
            ["Mutalaa:Paths:RawDir"] = "ozel/ham",
            ["Mutalaa:Paths:TempDir"] = "ozel/gecici",
        });

        ApiOptions options = custom.Services.GetRequiredService<IOptions<ApiOptions>>().Value;

        Assert.Equal(Path.GetFullPath("ozel/ham"), options.RawDir);
        Assert.Equal(Path.GetFullPath("ozel/gecici"), options.TempDir);
        Assert.Equal(Path.GetFullPath("data/packs"), options.PacksDir);
    }

    [Fact]
    public async Task The_json_console_format_option_starts_the_host_and_serves_requests()
    {
        ApiFactory json = CreateFactory(settings: new Dictionary<string, string?> { ["Serilog:Format"] = "Json" });
        using HttpClient client = json.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync("/health/live", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Request_logging_writes_the_path_and_status_but_not_query_strings_or_cookies()
    {
        using HttpClient client = Factory.CreateApiClient();
        using HttpRequestMessage request = new(HttpMethod.Get, "/api/v1/auth/me?gizli=sorgu-degeri");
        request.Headers.Add("Cookie", "mutalaa.editor=cerez-degeri");

        (await client.SendAsync(request, Ct)).Dispose();

        string log = Factory.Logs.Text;
        Assert.Contains("/api/v1/auth/me", log, StringComparison.Ordinal);
        Assert.Contains("401", log, StringComparison.Ordinal);
        Assert.DoesNotContain("sorgu-degeri", log, StringComparison.Ordinal);
        Assert.DoesNotContain("cerez-degeri", log, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_default_culture_is_invariant_and_the_Turkish_I_does_not_change_routing()
    {
        using HttpClient client = Factory.CreateApiClient();
        HttpStatusCode status = default;

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage response = await client.GetAsync("/HEALTH/LIVE", Ct);
            status = response.StatusCode;
        });

        Assert.Equal("", System.Globalization.CultureInfo.DefaultThreadCurrentCulture?.Name);
        Assert.Equal(HttpStatusCode.OK, status);
    }
}
