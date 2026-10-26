using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Veritabani gerektirmeyen model erisimi. Baglam, Api'nin ve dotnet ef'in kullandigi DI yolundan (AddIcerikDb + AddEditorIdentity)
/// baglanti dizesiz kurulur: Identity modeli Stores seceneklerini DI'dan okudugu icin DI'siz kurulan model farkli cikar.
/// </summary>
internal static class ModelFactory
{
    /// <summary>Model onbellegini atlar: her baglam modeli yeniden kurar (yerel ayar testleri icin).</summary>
    private sealed class UncachedModelCacheKeyFactory : IModelCacheKeyFactory
    {
        public object Create(DbContext context, bool designTime) => new object();
    }

    public static ServiceProvider BuildServices(bool uncachedModel = false, IConfiguration? configuration = null)
    {
        IConfiguration config = configuration ?? new ConfigurationBuilder().Build();
        ServiceCollection services = new();
        services.AddLogging();
        services.AddSingleton(config);
        services.AddIcerikDb(config);
        services.AddEditorIdentity();
        if (uncachedModel)
        {
            services.AddDbContext<IcerikDbContext>(o => o.ReplaceService<IModelCacheKeyFactory, UncachedModelCacheKeyFactory>());
        }

        return services.BuildServiceProvider();
    }

    /// <summary>Model uzerinde eylemi calistirir; varsayilan (onbellekli) ve yeni kurulmus model icin.</summary>
    public static void ForEachModel(Action<IModel> action)
    {
        action(CreateModel(uncachedModel: false));
        action(CreateModel(uncachedModel: true));
    }

    public static IModel CreateModel(bool uncachedModel)
    {
        using ServiceProvider provider = BuildServices(uncachedModel);
        using IServiceScope scope = provider.CreateScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return context.GetService<IDesignTimeModel>().Model;
    }
}
