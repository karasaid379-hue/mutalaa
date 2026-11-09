using Microsoft.Extensions.DependencyInjection.Extensions;
using Mutalaa.Api.Releases;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Api.Hosting;

public static class ReleaseServices
{
    /// <summary>
    /// Yayin uclarinin servisleri: <see cref="ReleaseRepository"/> (Api DI'inda kayitli degildir), paket katalogu, onceki paket cozucusu
    /// (<see cref="HttpPreviousPackResolver"/>), onizleme ve sir temizleyici. Testler katalogu ve cozucuyu sonradan degistirebilir (son kayit gecerli).
    /// </summary>
    public static IServiceCollection AddReleaseServices(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.TryAddSingleton(TimeProvider.System);
        services.TryAddSingleton(PackCatalog.Default);
        services.AddHttpClient(HttpPreviousPackResolver.ClientName, client => client.Timeout = HttpPreviousPackResolver.DownloadTimeout);
        services.TryAddSingleton<IPreviousPackResolver, HttpPreviousPackResolver>();
        services.TryAddSingleton<ReleaseRepository>();
        services.TryAddSingleton<ReleasePreviewService>();
        services.TryAddSingleton<SecretRedactor>();
        return services;
    }
}
