using Microsoft.Extensions.DependencyInjection;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Api testleri icin ortak taban: sinif veritabani (EditorialDatabase fiksturu) her testten once kimlik tablolarindan temizlenir,
/// her test kendi fabrikasini kurar (fabrika goctan SONRA kurulur). Fabrikalar test sonunda yok edilir.
/// </summary>
public abstract class ApiTestBase<TTests>(EditorialDatabase<TTests> fixture) : IAsyncLifetime
{
    private readonly List<ApiFactory> _factories = [];

    internal TestDatabase Db => fixture.Database;

    /// <summary>Varsayilan fabrika: Testing ortami, ek ayar yok.</summary>
    internal ApiFactory Factory { get; private set; } = null!;

    public async ValueTask InitializeAsync()
    {
        await Db.ExecuteAsync(
            "TRUNCATE kimlik.user_roles, kimlik.user_claims, kimlik.user_logins, kimlik.user_tokens, kimlik.role_claims, kimlik.users, kimlik.roles",
            TestContext.Current.CancellationToken);
        Factory = CreateFactory();
    }

    public async ValueTask DisposeAsync()
    {
        foreach (ApiFactory factory in _factories)
        {
            await factory.DisposeAsync();
        }
    }

    internal ApiFactory CreateFactory(
        string environment = "Testing",
        IReadOnlyDictionary<string, string?>? settings = null,
        Action<IServiceCollection>? configureServices = null,
        string? connectionString = null)
    {
        ApiFactory factory = new(connectionString ?? Db.ConnectionString, environment, settings, configureServices);
        _factories.Add(factory);
        return factory;
    }
}
