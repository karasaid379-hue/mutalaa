namespace Mutalaa.Domain.Releases;

/// <summary>
/// release.durum gecis kurali (Backend API 10.6), saf: hazirlaniyor -> dogrulandi | basarisiz; dogrulandi -> yayinlandi | basarisiz;
/// yayinlandi -> geri_cekildi. basarisiz ve geri_cekildi sondur. Ayni duruma gecis (idempotent yeniden calistirma) gecis sayilmaz.
/// </summary>
public static class ReleaseTransitions
{
    public static bool CanTransition(ReleaseStatus from, ReleaseStatus to) => (from, to) switch
    {
        (ReleaseStatus.Hazirlaniyor, ReleaseStatus.Dogrulandi) => true,
        (ReleaseStatus.Hazirlaniyor, ReleaseStatus.Basarisiz) => true,
        (ReleaseStatus.Dogrulandi, ReleaseStatus.Yayinlandi) => true,
        (ReleaseStatus.Dogrulandi, ReleaseStatus.Basarisiz) => true,
        (ReleaseStatus.Yayinlandi, ReleaseStatus.GeriCekildi) => true,
        _ => false,
    };

    /// <summary>Gecis gecersizse InvalidOperationException atar.</summary>
    public static void Require(ReleaseStatus from, ReleaseStatus to)
    {
        if (!CanTransition(from, to))
        {
            throw new InvalidOperationException($"Gecersiz yayin durumu gecisi: {from.ToLabel()} -> {to.ToLabel()}.");
        }
    }

    /// <summary>Acik (henuz yayinlanmamis ve basarisiz olmamis) durum: hazirlaniyor ya da dogrulandi.</summary>
    public static bool IsOpen(ReleaseStatus status) => status is ReleaseStatus.Hazirlaniyor or ReleaseStatus.Dogrulandi;
}
