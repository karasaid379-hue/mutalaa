using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// release.ozetler jsonb degeri (K-46 madde 1): <c>{"kaynaklar": {slug: kaynak_ozeti}, "paketler": {pack_id: paket_ozeti}}</c>.
/// Kaynak ozeti derleme turunden bagimsizdir ve P-14 onu karsilastirir; paket ozeti (pack_meta.content_digest) bir sonraki yayinda
/// degismeyen paketin tasinmasini saglar. Anahtarlar Ordinal sirali yazilir.
/// </summary>
public sealed class ReleaseDigests
{
    public static ReleaseDigests Empty { get; } = new(new Dictionary<string, string>(StringComparer.Ordinal), new Dictionary<string, string>(StringComparer.Ordinal));

    public ReleaseDigests(IReadOnlyDictionary<string, string> sources, IReadOnlyDictionary<string, string> packs)
    {
        Sources = sources;
        Packs = packs;
    }

    /// <summary>Kaynak slug'i -> kaynak ozeti.</summary>
    public IReadOnlyDictionary<string, string> Sources { get; }

    /// <summary>Paket kimligi -> paket ozeti.</summary>
    public IReadOnlyDictionary<string, string> Packs { get; }

    /// <summary>Bos ya da bicimi bozuk girdi <see cref="Empty"/> doner (varsayilan sutun degeri <c>{}</c>).</summary>
    public static ReleaseDigests Parse(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return Empty;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(json);
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                return Empty;
            }

            return new ReleaseDigests(ReadMap(document.RootElement, "kaynaklar"), ReadMap(document.RootElement, "paketler"));
        }
        catch (JsonException)
        {
            return Empty;
        }
    }

    public string ToJson()
    {
        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream, new JsonWriterOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }))
        {
            writer.WriteStartObject();
            WriteMap(writer, "kaynaklar", Sources);
            WriteMap(writer, "paketler", Packs);
            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static Dictionary<string, string> ReadMap(JsonElement root, string name)
    {
        Dictionary<string, string> map = new(StringComparer.Ordinal);
        if (root.TryGetProperty(name, out JsonElement element) && element.ValueKind == JsonValueKind.Object)
        {
            foreach (JsonProperty property in element.EnumerateObject())
            {
                if (property.Value.ValueKind == JsonValueKind.String && property.Value.GetString() is { } value)
                {
                    map[property.Name] = value;
                }
            }
        }

        return map;
    }

    private static void WriteMap(Utf8JsonWriter writer, string name, IReadOnlyDictionary<string, string> map)
    {
        writer.WriteStartObject(name);
        foreach (string key in map.Keys.Order(Utf8Order.Instance))
        {
            writer.WriteString(key, map[key]);
        }

        writer.WriteEndObject();
    }
}

/// <summary>
/// Kaynak ozeti hesabi (K-46 madde 1, Yayin sureci 2.2): kaynagin etkin birimleri <see cref="ContentDigest"/> kuraliyla; birimi olmayan kaynakta
/// (tanzil-ust-veri) page_map ve quran_marker satirlari kanonik JSON satirlari (UTF-8 bayt sirasinda, LF'li) olarak ozetlenir; sozluk kaynaklarinda
/// (K-46 madde 1) qac-morfoloji icin root, lemma, quran_word'un QAC sutunlari ve quran_word_fix satirlari (butun durumlar), kaikki-tr icin Turkce lemma, tr_root_index ve tr_form satirlari (onay yolu, kanit varligi ve unit_hash dahil), quranwbw-tr icin lemma_gloss
/// satirlari (butun durumlar, status ve origin dahil; kuran_anlamlari RFC 8785 kanonik bicimiyle) ayni bicimde ozetlenir; hicbiri yoksa girdisiz SHA-256. Derleme turunden bagimsizdir: butun anlik goruntuden hesaplanir.
/// </summary>
public static class SourceDigests
{
    private const string ActiveStatus = "etkin";
    private const string QuranWordFixTable = "quran_word_fix";
    private const string TrLemmaTable = "lemma_tr";

    public static IReadOnlyDictionary<string, string> Compute(EditorialSnapshot snapshot, IEnumerable<string> slugs)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        ArgumentNullException.ThrowIfNull(slugs);

        HashSet<string> wanted = new(slugs, StringComparer.Ordinal);
        Dictionary<string, List<ContentDigestEntry>> entries = new(StringComparer.Ordinal);
        foreach (UnitRow unit in snapshot.Units)
        {
            if (wanted.Contains(unit.SourceId) && string.Equals(unit.Status, ActiveStatus, StringComparison.Ordinal))
            {
                if (!entries.TryGetValue(unit.SourceId, out List<ContentDigestEntry>? list))
                {
                    list = [];
                    entries[unit.SourceId] = list;
                }

                list.Add(new ContentDigestEntry(unit.Anchor, unit.ContentHash));
            }
        }

        SortedDictionary<string, string> result = new(StringComparer.Ordinal);
        foreach (string slug in wanted)
        {
            result[slug] = entries.TryGetValue(slug, out List<ContentDigestEntry>? list)
                ? ContentDigest.Compute(list)
                : StructureDigest(snapshot, slug);
        }

        return result;
    }

    private static string StructureDigest(EditorialSnapshot snapshot, string slug)
    {
        List<string> lines = [];
        foreach (PageMapRow page in snapshot.PageMaps)
        {
            if (string.Equals(page.SourceId, slug, StringComparison.Ordinal))
            {
                lines.Add(Line(PackTables.PageMap, slug, Wide(page.Volume), page.Page, Wide(page.Line), page.StartAnchor, Wide(page.StartOffset), page.EndAnchor, Wide(page.EndOffset)));
            }
        }

        foreach (QuranMarkerRow marker in snapshot.QuranMarkers)
        {
            if (string.Equals(marker.SourceId, slug, StringComparison.Ordinal))
            {
                lines.Add(Line(PackTables.QuranMarker, slug, marker.Kind, marker.No, marker.Anchor, marker.SecdeTuru));
            }
        }

        AddLexiconLines(snapshot, slug, lines);

        lines.Sort(Utf8Order.Instance);
        using IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        foreach (string line in lines)
        {
            hash.AppendData(Encoding.UTF8.GetBytes(line));
            hash.AppendData("\n"u8);
        }

        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private static void AddLexiconLines(EditorialSnapshot snapshot, string slug, List<string> lines)
    {
        if (string.Equals(slug, PackCatalog.QacMorphologySlug, StringComparison.Ordinal))
        {
            foreach (RootRow root in snapshot.Roots)
            {
                if (string.Equals(root.SourceId, slug, StringComparison.Ordinal))
                {
                    lines.Add(Line(PackTables.Root, slug, root.Id, root.Letters, root.Occurrences, root.AyahCount, root.IdfQ is { } idf ? PackRows.FromSingle(idf) : null, root.KokAnlami));
                }
            }

            foreach (LemmaRow lemma in snapshot.Lemmas)
            {
                if (string.Equals(lemma.SourceId, slug, StringComparison.Ordinal))
                {
                    lines.Add(Line(
                        PackTables.Lemma,
                        slug,
                        lemma.Id,
                        lemma.Text,
                        lemma.TextClean,
                        lemma.RootId,
                        lemma.Occurrences,
                        lemma.ArLemmaId,
                        lemma.EtymologicalOnly ? 1L : 0L,
                        lemma.Status));
                }
            }

            foreach (QuranWordRow word in snapshot.QuranWords)
            {
                if (string.Equals(word.MorphSource, slug, StringComparison.Ordinal))
                {
                    string? features = word.Features is null ? null : WordMorphFixes.CanonicalJson(word.Features) ?? word.Features;
                    lines.Add(Line(PackTables.QuranWord, slug, word.Anchor, word.RootId, word.LemmaId, word.Pos, features, word.MorphSource));
                }
            }

            // quran_word_fix satirlari (butun durumlar; K-46 madde 1): aday -> onayli gecisi ve onayli duzeltmenin degeri ozeti degistirir; P-14 terfide yakalar.
            foreach (QuranWordFixRow fix in snapshot.WordFixes)
            {
                lines.Add(Line(QuranWordFixTable, slug, fix.Id.ToString("D", CultureInfo.InvariantCulture), fix.Anchor, fix.Field, fix.NewValue, fix.Status));
            }
        }
        else if (string.Equals(slug, PackCatalog.TrLemmaSourceSlug, StringComparison.Ordinal))
        {
            // Turkce lemma (butun durumlar; onay yolu ve kanit varligi dahil), tr_root_index (unit_hash dahil) ve tr_form: onay durumu, onay yolu ya da
            // eslemeler degisirse kaynak ozeti degisir ve terfide P-14 yakalar (K-51 madde 1 ve 9).
            HashSet<int> own = [];
            foreach (TrLemmaRow lemma in snapshot.TrLemmas)
            {
                if (string.Equals(lemma.SourceId, slug, StringComparison.Ordinal))
                {
                    own.Add(lemma.Id);
                    lines.Add(Line(
                        TrLemmaTable,
                        slug,
                        lemma.Id,
                        lemma.Text,
                        lemma.TextClean,
                        lemma.RootId,
                        lemma.ArLemmaId,
                        lemma.EtymologicalOnly ? 1L : 0L,
                        lemma.Freq,
                        lemma.Status,
                        lemma.OnayYolu,
                        lemma.HasKanit ? 1L : 0L));
                }
            }

            foreach (TrRootIndexRow row in snapshot.TrRootIndex)
            {
                if (own.Contains(row.TrLemmaId))
                {
                    lines.Add(Line(PackTables.TrRootIndex, slug, row.Anchor, row.SpanStart, row.SpanEnd, row.RootId, row.TrLemmaId, row.EtymologicalOnly ? 1L : 0L, row.UnitHash));
                }
            }

            foreach (TrFormRow row in snapshot.TrForms)
            {
                if (own.Contains(row.TrLemmaId))
                {
                    lines.Add(Line(PackTables.TrForm, slug, row.KeyWide, row.KeyNarrow, row.TrLemmaId, row.Freq));
                }
            }
        }
        else if (string.Equals(slug, PackCatalog.GlossSourceSlug, StringComparison.Ordinal))
        {
            foreach (LemmaGlossRow gloss in snapshot.LemmaGlosses)
            {
                lines.Add(Line(
                    PackTables.LemmaGloss,
                    slug,
                    gloss.LemmaId,
                    gloss.AnlamKisa,
                    WordMorphFixes.CanonicalJsonOrRaw(gloss.KuranAnlamlari),
                    gloss.TurkceEsKelime,
                    gloss.YalnizcaEtimolojik ? 1L : 0L,
                    gloss.Status,
                    gloss.Origin,
                    gloss.Version));
            }
        }
    }

    private static long? Wide(int? value) => value;

    private static string Line(string table, params object?[] values) =>
        Encoding.UTF8.GetString(PackRows.Canonical(new PackRow(table, values)));
}
