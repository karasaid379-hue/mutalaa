using Microsoft.EntityFrameworkCore;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Lemmas;

/// <summary>
/// Turkce lemmanin tr_root_index uzerinden bir gecis ornegi (K-51 madde 9): <c>capa</c> meal birimi, <c>sol</c>, <c>kelime</c> ve <c>sag</c>
/// birim metninden kod noktasi ofsetiyle dilimlenir. Birimin ozeti satirin <c>unit_hash</c> degeriyle tutmuyorsa (metin degismis, satir
/// bayat) ya da ofset metne uymuyorsa uc alan da null'dir.
/// </summary>
public sealed record TrKwicItem(string Capa, string? Sol, string? Kelime, string? Sag);

/// <summary>Turkce lemma karti ekleri: kanit ozeti, koku harfleri, Arapca karsiligin metni ve ilk uc ornek.</summary>
public sealed record TrLemmaExtras(
    LemmaKanitSummary? KanitOzeti,
    string? RootLetters,
    string? ArLemmaText,
    IReadOnlyList<TrKwicItem> Kwic);

/// <summary>Turkce lemma (lang = 'tr') okuma sorgulari: hepsi AsNoTracking ve projeksiyonludur.</summary>
internal static class TrLemmaQueries
{
    /// <summary>Kartta ve inceleme anlik goruntusunde gosterilen ornek sayisi.</summary>
    public const int MaxKwic = 3;

    public static async Task<TrLemmaExtras> ExtrasAsync(
        IcerikDbContext db,
        int lemmaId,
        int? rootId,
        int? arLemmaId,
        string? kanit,
        CancellationToken cancellationToken)
    {
        string? letters = rootId is { } rid
            ? await db.Roots.AsNoTracking().Where(r => r.Id == rid).Select(r => r.Letters).SingleOrDefaultAsync(cancellationToken)
            : null;
        string? arText = arLemmaId is { } aid
            ? await db.Lemmas.AsNoTracking().Where(l => l.Id == aid).Select(l => l.Text).SingleOrDefaultAsync(cancellationToken)
            : null;
        return new TrLemmaExtras(LemmaKanitSummary.Summarize(kanit), letters, arText, await KwicAsync(db, lemmaId, cancellationToken));
    }

    /// <summary>
    /// tr_root_index satirlari okuma sirasindadir (capa sirasi, sonra baslangic); ilk <see cref="MaxKwic"/> tanesi alinir. Tablo bossa bos liste.
    /// Yalniz hafif sutunlar okunur (bir lemmanin satiri iki mealde birkac bindir); birim metni yalniz secilen uc satir icin okunur.
    /// </summary>
    private static async Task<List<TrKwicItem>> KwicAsync(IcerikDbContext db, int lemmaId, CancellationToken cancellationToken)
    {
        var rows = await db.TrRootIndexes.AsNoTracking()
            .Where(x => x.TrLemmaId == lemmaId)
            .Select(x => new { x.Anchor, x.SpanStart, x.SpanEnd, x.UnitHash })
            .ToListAsync(cancellationToken);
        if (rows.Count == 0)
        {
            return [];
        }

        var picked = rows.OrderBy(r => r.Anchor).ThenBy(r => r.SpanStart).Take(MaxKwic).ToList();
        List<AnchorRef> anchors = [.. picked.Select(p => p.Anchor).Distinct()];
        var units = await db.Units.AsNoTracking()
            .Where(u => anchors.Contains(u.Anchor))
            .Select(u => new { u.Anchor, u.Metin, u.ContentHash })
            .ToListAsync(cancellationToken);
        Dictionary<string, (string Metin, string Hash)> byAnchor = units.ToDictionary(u => u.Anchor.ToString(), u => (u.Metin, u.ContentHash), StringComparer.Ordinal);

        List<TrKwicItem> items = new(picked.Count);
        foreach (var row in picked)
        {
            string key = row.Anchor.ToString();
            (string? left, string? hit, string? right) = byAnchor.TryGetValue(key, out (string Metin, string Hash) unit)
                && unit.Hash.StartsWith(row.UnitHash, StringComparison.Ordinal)
                    ? LemmaQueries.Split(unit.Metin, row.SpanStart, row.SpanEnd)
                    : (null, null, null);
            items.Add(new TrKwicItem(key, left, hit, right));
        }

        return items;
    }
}
