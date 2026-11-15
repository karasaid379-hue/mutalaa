using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Gercek Program'i (Testing ortami: kullanici sirlari yuklenmez) sinif veritabanina baglayarak calistirir.
/// Baglanti dizesi, ozellik bayraklari ve yollar <c>UseSetting</c> ile verilir (Build oncesi okunan ayarlar icin).
/// Development ortaminda kullanici sirlari yuklenir ve UseSetting'i ezebilir; bu yuzden yalniz orada baglanti ve seed anahtarlari
/// ayrica bellek icindeki ayar kaynagiyla (en yuksek oncelik) verilir.
/// </summary>
internal sealed class ApiFactory : WebApplicationFactory<Program>
{
    public const string AdminEmailKey = "Mutalaa:Seed:AdminEmail";

    private readonly string _environment;
    private readonly IReadOnlyDictionary<string, string?> _settings;
    private readonly Action<IServiceCollection>? _configureServices;

    public ApiFactory(
        string connectionString,
        string environment = "Testing",
        IReadOnlyDictionary<string, string?>? settings = null,
        Action<IServiceCollection>? configureServices = null)
    {
        _environment = environment;
        _settings = new Dictionary<string, string?>(settings ?? new Dictionary<string, string?>(), StringComparer.Ordinal)
        {
            ["ConnectionStrings:Editorial"] = connectionString,
        };
        _configureServices = configureServices;
    }

    public CapturingLoggerProvider Logs { get; } = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment(_environment);
        foreach ((string key, string? value) in _settings)
        {
            builder.UseSetting(key, value);
        }

        if (string.Equals(_environment, "Development", StringComparison.Ordinal))
        {
            string[] secretKeys = ["ConnectionStrings:Editorial", AdminEmailKey, "Mutalaa:Seed:AdminPassword"];
            Dictionary<string, string?> overrides = _settings
                .Where(p => secretKeys.Contains(p.Key, StringComparer.Ordinal))
                .ToDictionary(p => p.Key, p => p.Value, StringComparer.Ordinal);
            builder.ConfigureAppConfiguration((_, configuration) => configuration.AddInMemoryCollection(overrides));
        }

        builder.ConfigureTestServices(services =>
        {
            // Serilog writeToProviders: kayitli saglayicilar (bu dahil) her iletiyi alir.
            services.AddSingleton<ILoggerProvider>(Logs);
            _configureServices?.Invoke(services);
        });
    }

    /// <summary>https tabani (Secure cerez saklanir), yonlendirme izlenmez.</summary>
    public HttpClient CreateApiClient() => CreateClient(new WebApplicationFactoryClientOptions
    {
        BaseAddress = new Uri("https://localhost"),
        AllowAutoRedirect = false,
    });

    /// <summary>Kullanici ve rolleri dogrudan UserManager ile olusturur (seed gerekmez; roller yoksa olusturulur).</summary>
    public async Task<EditorUser> AddUserAsync(string email, string password, params string[] roles)
    {
        await using AsyncServiceScope scope = Services.CreateAsyncScope();
        RoleManager<IdentityRole> roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
        foreach (string role in new[] { Roles.Editor, Roles.Admin, Roles.Uzman })
        {
            if (!await roleManager.RoleExistsAsync(role))
            {
                Assert.True((await roleManager.CreateAsync(new IdentityRole(role))).Succeeded);
            }
        }

        UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
        EditorUser user = new() { UserName = email, Email = email, EmailConfirmed = true };
        IdentityResult created = await users.CreateAsync(user, password);
        Assert.True(created.Succeeded, string.Join(", ", created.Errors.Select(e => e.Code)));
        if (roles.Length > 0)
        {
            Assert.True((await users.AddToRolesAsync(user, roles)).Succeeded);
        }

        return user;
    }

    /// <summary>Giris yapar (cerez istemcide kalir) ve yaniti dondurur.</summary>
    public static Task<HttpResponseMessage> LoginAsync(HttpClient client, string email, string password, CancellationToken cancellationToken) =>
        client.PostAsJsonAsync("/api/v1/auth/login", new { email, parola = password }, cancellationToken);

    public static async Task<JsonElement> ReadJsonAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        string text = await response.Content.ReadAsStringAsync(cancellationToken);
        using JsonDocument document = JsonDocument.Parse(text);
        return document.RootElement.Clone();
    }
}
