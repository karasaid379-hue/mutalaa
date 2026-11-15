using Microsoft.EntityFrameworkCore;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Infrastructure.Reviews;

/// <summary>Kitap basina birim sayilari (etkin <c>risale</c> birimleri).</summary>
public sealed record RisaleBookCounts(string Slug, long Total, long Draft, long Approved);

/// <summary>
/// Kitap onayi sorgulari ve toplu yazma (K-52 madde 11). Birim capasi <c>AnchorRef</c> donusturuculu oldugu icin esleme ham SQL ile yapilir
/// (yalniz sutunlar; kullanici girdisi parametredir). Kitap = <c>kind = 'risale'</c>, <c>status = 'etkin'</c> ve capa oneki <c>rn:{slug}:</c>
/// olan birimler; oneke slug'i izleyen <c>:</c> dahildir, boylece <c>sozler</c> ile <c>sozler-osmanlica</c> karismaz.
/// </summary>
public static class RisaleBookStore
{
    /// <summary>Katalogdaki kitaplarin sayilari; birimi olmayan kitap sozlukte yoktur. Fikstur kitabi (<c>test-...</c>) dahildir, cagiran suzer.</summary>
    public static async Task<IReadOnlyDictionary<string, RisaleBookCounts>> CountsAsync(IcerikDbContext db, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(db);

        List<CountRow> rows = await db.Database.SqlQuery<CountRow>(
            $"""
            SELECT split_part(anchor, ':', 2) AS slug,
                   count(*) AS total,
                   count(*) FILTER (WHERE metin_durumu = 'taslak') AS draft,
                   count(*) FILTER (WHERE metin_durumu = 'onayli') AS approved
            FROM icerik.unit
            WHERE kind = 'risale' AND status = 'etkin' AND starts_with(anchor, 'rn:')
            GROUP BY 1
            """).ToListAsync(cancellationToken);
        return rows.ToDictionary(r => r.Slug, r => new RisaleBookCounts(r.Slug, r.Total, r.Draft, r.Approved), StringComparer.Ordinal);
    }

    /// <summary>
    /// Kitabin etkin birimleri (capa bayt sirasiyla) ve G-BUT kaniti: birimin <c>run_id</c> degeri, <c>durum = basarili</c> ve
    /// <c>manifest.qa_rapor</c> dolu bir <c>pipeline_run</c> satirina baglidir (hat yuklemesi dort kapi gecmeden yazilmaz).
    /// </summary>
    public static async Task<List<RisaleBookUnit>> LoadUnitsAsync(IcerikDbContext db, string slug, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(db);
        string prefix = RisaleBookApproval.AnchorPrefix(slug);

        List<UnitRow> rows = await db.Database.SqlQuery<UnitRow>(
            $"""
            SELECT u.anchor AS anchor,
                   u.content_hash AS content_hash,
                   u.metin_durumu::text AS durum,
                   (r.run_id IS NOT NULL) AS has_evidence
            FROM icerik.unit u
            LEFT JOIN icerik.pipeline_run r
              ON r.run_id = u.run_id AND r.durum = 'basarili' AND coalesce(r.manifest ->> 'qa_rapor', '') <> ''
            WHERE u.kind = 'risale' AND u.status = 'etkin' AND starts_with(u.anchor, {prefix})
            ORDER BY u.anchor COLLATE "C"
            """).ToListAsync(cancellationToken);

        return [.. rows.Select(r => new RisaleBookUnit(
            r.Anchor,
            r.ContentHash,
            TextStatusLabels.TryParseLabel(r.Durum, out TextStatus status) ? status : throw new InvalidOperationException($"Bilinmeyen metin_durumu: {r.Durum}"),
            r.HasEvidence))];
    }

    /// <summary>
    /// Kitabi kilitler (acik islem icinde cagrilir): ayni kitabi onaylayan iki istek siralanir (danisma kilidi) ve kitabin satirlari
    /// islem bitene kadar baska yazici tarafindan degistirilemez (<c>FOR UPDATE</c>; hat yuklemesi ve duzeltme onayi bekler).
    /// </summary>
    public static async Task LockAsync(IcerikDbContext db, string slug, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(db);
        string prefix = RisaleBookApproval.AnchorPrefix(slug);
        string lockKey = "risale-book-approval:" + slug;
        await db.Database.ExecuteSqlAsync($"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))", cancellationToken);
        await db.Database.ExecuteSqlAsync(
            $"SELECT 1 FROM icerik.unit WHERE kind = 'risale' AND status = 'etkin' AND starts_with(anchor, {prefix}) FOR UPDATE",
            cancellationToken);
    }

    /// <summary>
    /// Verilen capalardaki <c>taslak</c> birimleri <c>onayli</c> yapar (tek ifade); metin, ozet ve surum sutunlarina dokunulmaz.
    /// Onayli ya da reddedilmis (<c>incelemede</c>) birim zaten <c>taslak</c> degildir, dokunulmaz. Etkilenen satir sayisi doner.
    /// </summary>
    public static async Task<int> ApproveDraftsAsync(IcerikDbContext db, IReadOnlyList<string> anchors, DateTime nowUtc, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(db);
        ArgumentNullException.ThrowIfNull(anchors);
        string[] list = [.. anchors];
        return await db.Database.ExecuteSqlAsync(
            $"""
            UPDATE icerik.unit
            SET metin_durumu = 'onayli', updated_at = {nowUtc}
            WHERE kind = 'risale' AND status = 'etkin' AND metin_durumu = 'taslak' AND anchor = ANY({list})
            """,
            cancellationToken);
    }

    private sealed class CountRow
    {
        public required string Slug { get; init; }

        public long Total { get; init; }

        public long Draft { get; init; }

        public long Approved { get; init; }
    }

    private sealed class UnitRow
    {
        public required string Anchor { get; init; }

        public required string ContentHash { get; init; }

        public required string Durum { get; init; }

        public bool HasEvidence { get; init; }
    }
}
