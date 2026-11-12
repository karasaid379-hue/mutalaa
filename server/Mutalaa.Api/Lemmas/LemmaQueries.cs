using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Endpoints;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Lemmas;

/// <summary>
/// Lemma karti okuma sorgulari (hepsi AsNoTracking, projeksiyonlu). Her liste sinirli ve belirlenimli siralidir:
/// tur dagilimi (sayi azalan, pos Ordinal), ayni kokun anlamlari (en cok 20; gecis azalan, kimlik), KWIC (en cok 8; okuma sirasi).
/// Capa uretimi ve ayristirma yalniz <c>Mutalaa.Domain.Anchors</c> ile yapilir.
/// </summary>
internal static class LemmaQueries
{
    public const int MaxSiblingGlosses = 20;

    /// <summary>KWIC baglami: kelimenin her iki yaninda en cok bu kadar kod noktasi.</summary>
    public const int ContextCodePoints = 40;

    /// <summary>Meal kimligi (meal:elmalili:{sure}:{ayet}); kartta yalniz bu meal gosterilir.</summary>
    public const string MealId = "elmalili";

    private sealed record WordKey(AnchorRef Anchor, int CharStart, int CharEnd);

    /// <summary>Lemma yoksa null.</summary>
    public static async Task<LemmaDetailResponse?> GetAsync(IcerikDbContext db, int id, CancellationToken cancellationToken)
    {
        Lemma? lemma = await db.Lemmas.AsNoTracking().SingleOrDefaultAsync(l => l.Id == id, cancellationToken);
        if (lemma is null)
        {
            return null;
        }

        LemmaRootInfo? root = null;
        if (lemma.RootId is { } rootId)
        {
            root = await db.Roots.AsNoTracking()
                .Where(r => r.Id == rootId)
                .Select(r => new LemmaRootInfo(r.Id, r.Letters, r.LettersBw, r.Occurrences, r.AyahCount, r.IdfQ, r.KokAnlami))
                .SingleOrDefaultAsync(cancellationToken);
        }

        List<LemmaPosCount> kinds = await PosDistributionAsync(db, id, cancellationToken);
        int ayahCount = await db.QuranWords.AsNoTracking()
            .Where(w => w.LemmaId == id)
            .Select(w => w.AyahIndex)
            .Distinct()
            .CountAsync(cancellationToken);

        LemmaWaveInfo? wave = await db.LemmaDalgas.AsNoTracking()
            .Where(d => d.LemmaId == id)
            .Select(d => new LemmaWaveInfo(d.Dalga, d.Sira))
            .SingleOrDefaultAsync(cancellationToken);

        List<LemmaSiblingGloss> siblings = lemma.RootId is { } siblingRoot
            ? await SiblingGlossesAsync(db, id, siblingRoot, cancellationToken)
            : [];

        int wordCount = kinds.Sum(k => k.Sayi);
        return new LemmaDetailResponse(
            new LemmaInfo(lemma.Id, lemma.Text, lemma.Lang, lemma.Status.ToLabel(), lemma.Origin, lemma.Occurrences, lemma.RootId, lemma.QacRef, lemma.EtymologicalOnly),
            root,
            kinds,
            new LemmaFrequency(wordCount, ayahCount),
            wave,
            siblings,
            await KwicAsync(db, id, wordCount, cancellationToken));
    }

    private static async Task<List<LemmaPosCount>> PosDistributionAsync(IcerikDbContext db, int id, CancellationToken cancellationToken)
    {
        var groups = await db.QuranWords.AsNoTracking()
            .Where(w => w.LemmaId == id)
            .GroupBy(w => w.Pos)
            .Select(g => new { Pos = g.Key, Sayi = g.Count() })
            .ToListAsync(cancellationToken);

        return [.. groups
            .OrderByDescending(g => g.Sayi)
            .ThenBy(g => g.Pos, StringComparer.Ordinal)
            .Select(g => new LemmaPosCount(g.Pos, g.Sayi))];
    }

    private static async Task<List<LemmaSiblingGloss>> SiblingGlossesAsync(IcerikDbContext db, int id, int rootId, CancellationToken cancellationToken)
    {
        var rows = await (
            from l in db.Lemmas.AsNoTracking()
            join g in db.LemmaGlosses.AsNoTracking() on l.Id equals g.LemmaId
            where l.RootId == rootId && l.Id != id && g.Status == XrefStatus.Onayli
            orderby l.Occurrences descending, l.Id
            select new { l.Id, l.Text, g.AnlamKisa, l.Occurrences })
            .Take(MaxSiblingGlosses)
            .ToListAsync(cancellationToken);

        return [.. rows.Select(r => new LemmaSiblingGloss(r.Id, r.Text, r.AnlamKisa, r.Occurrences))];
    }

    /// <summary>
    /// KWIC ornekleri: lemmanin gecisleri okuma sirasindadir (ayet sirasi, kelime); en cok <see cref="KwicSampling.MaxSamples"/> tanesi
    /// <see cref="KwicSampling.SampleIndices"/> ile secilir. Her ornegin ayet metni Tanzil birimidir (unit.kind = ayet);
    /// kelime, <c>[char_start, char_end)</c> kod noktasi araligiyla dilimlenir (UTF-16 degil).
    /// </summary>
    private static async Task<List<LemmaKwicItem>> KwicAsync(IcerikDbContext db, int id, int total, CancellationToken cancellationToken)
    {
        if (total == 0)
        {
            return [];
        }

        // Yalniz hafif sutunlar (capa ve iki ofset); en sik lemmada bile birkac bin satirdir.
        List<WordKey> ordered = await db.QuranWords.AsNoTracking()
            .Where(w => w.LemmaId == id)
            .OrderBy(w => w.AyahIndex)
            .ThenBy(w => w.Word)
            .Select(w => new WordKey(w.Anchor, w.CharStart, w.CharEnd))
            .ToListAsync(cancellationToken);

        List<WordKey> picked = [.. KwicSampling.SampleIndices(ordered.Count).Select(i => ordered[i])];
        List<AnchorRef> ayahAnchors = [.. picked.Select(p => p.Anchor.UnitOf()).Distinct()];
        List<AnchorRef> mealAnchors = [.. ayahAnchors.Select(MealAnchor)];

        var ayahRows = await db.Units.AsNoTracking()
            .Where(u => u.Kind == UnitKind.Ayet && ayahAnchors.Contains(u.Anchor))
            .Select(u => new { u.Anchor, u.Metin })
            .ToListAsync(cancellationToken);
        Dictionary<string, string> ayahText = ayahRows.ToDictionary(r => r.Anchor.ToString(), r => r.Metin, StringComparer.Ordinal);

        var mealRows = await db.Units.AsNoTracking()
            .Where(u => u.Kind == UnitKind.Meal && mealAnchors.Contains(u.Anchor))
            .Select(u => new { u.Anchor, u.Metin, u.MetinDurumu })
            .ToListAsync(cancellationToken);
        Dictionary<string, LemmaKwicMeal> meals = mealRows
            .Where(r => r.Metin.Length > 0)
            .ToDictionary(r => r.Anchor.ToString(), r => new LemmaKwicMeal(r.Anchor.ToString(), r.Metin, r.MetinDurumu.ToLabel()), StringComparer.Ordinal);

        List<LemmaKwicItem> items = new(picked.Count);
        foreach (WordKey word in picked)
        {
            AnchorRef ayah = word.Anchor.UnitOf();
            ayahText.TryGetValue(ayah.ToString(), out string? text);
            (string? left, string? hit, string? right) = text is null ? (null, null, null) : Split(text, word.CharStart, word.CharEnd);
            meals.TryGetValue(MealAnchor(ayah).ToString(), out LemmaKwicMeal? meal);
            items.Add(new LemmaKwicItem(word.Anchor.ToString(), ayah.ToString(), left, hit, right, meal));
        }

        return items;
    }

    /// <summary>Ayet capasindan meal:elmalili capasi; yalniz Domain ayristiricisiyla uretilir.</summary>
    private static AnchorRef MealAnchor(AnchorRef ayah) =>
        AnchorRef.Parse(string.Create(CultureInfo.InvariantCulture, $"meal:{MealId}:{ayah.Sure}:{ayah.Ayet}"));

    /// <summary>
    /// Metni kod noktasi ofsetleriyle (sol baglam, kelime, sag baglam) dilimler; ofset metne uymuyorsa ucu de null.
    /// Baglam sinirlari Mn isaretlerinin ortasina dusmez (<see cref="CodePointOffsets.SnapSpan"/>).
    /// </summary>
    internal static (string? Left, string? Word, string? Right) Split(string text, int start, int end)
    {
        int length = CodePointOffsets.CodePointCount(text);
        if (start < 0 || start >= end || end > length)
        {
            return (null, null, null);
        }

        AnchorSpan left = CodePointOffsets.SnapSpan(text, new AnchorSpan(Math.Max(0, start - ContextCodePoints), start));
        AnchorSpan right = CodePointOffsets.SnapSpan(text, new AnchorSpan(end, Math.Min(length, end + ContextCodePoints)));
        return (
            CodePointOffsets.Slice(text, left.Start, left.End),
            CodePointOffsets.Slice(text, start, end),
            CodePointOffsets.Slice(text, right.Start, right.End));
    }
}
