using Microsoft.Extensions.Options;
using Mutalaa.Api.Settings;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Api.Releases;

/// <summary>
/// Onizleme (<c>POST /releases/preview</c>): paket uretmeden kalite kapisi raporu. <see cref="GatePlanner"/> Yayinlayicinin kullandigi koddur
/// (<c>SkipAssembly = true</c>, <c>PromoteFrom = null</c>: P-14 yalniz terfide). Ayni anda tek onizleme calisir (kuyruk yok): kilit doluysa
/// <see cref="TryPlanAsync"/> null doner. Dosya yazmaz; onceki yayinin paketleri gerekirse <see cref="IPreviousPackResolver"/> ile onbellege iner.
/// </summary>
public sealed class ReleasePreviewService(
    IConfiguration configuration,
    IOptions<ApiOptions> options,
    PackCatalog catalog,
    IPreviousPackResolver previousPacks) : IDisposable
{
    private readonly SemaphoreSlim _gate = new(1, 1);

    /// <returns>Plan; baska bir onizleme suruyorsa null.</returns>
    /// <exception cref="GatePlanException">Onceki yayin manifesti yok/okunamiyor ya da onceki paket yok/uyusmuyor.</exception>
    public async Task<GatePlan?> TryPlanAsync(BuildFlavor flavor, IReadOnlyList<string> packs, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(packs);

        string connectionString = configuration.GetConnectionString(DependencyInjection.ConnectionName)
            ?? throw new InvalidOperationException($"ConnectionStrings:{DependencyInjection.ConnectionName} ayari yok.");

        if (!await _gate.WaitAsync(TimeSpan.Zero, CancellationToken.None))
        {
            return null;
        }

        try
        {
            ApiOptions paths = options.Value;
            return await GatePlanner.PlanAsync(
                new GatePlanRequest(
                    connectionString,
                    flavor,
                    packs,
                    catalog,
                    Path.GetFullPath(paths.SourcesDir),
                    Path.GetFullPath(paths.RawDir),
                    PromoteFrom: null,
                    previousPacks,
                    SkipAssembly: true),
                cancellationToken);
        }
        finally
        {
            _gate.Release();
        }
    }

    public void Dispose() => _gate.Dispose();
}
