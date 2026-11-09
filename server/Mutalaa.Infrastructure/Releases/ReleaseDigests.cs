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
/// (tanzil-ust-veri) page_map ve quran_marker satirlari kanonik JSON satirlari (UTF-8 bayt sirasinda, LF'li) olarak ozetlenir; ikisi de yoksa
/// girdisiz SHA-256. Derleme turunden bagimsizdir: butun anlik goruntuden hesaplanir.
/// </summary>
public static class SourceDigests
{
    private const string ActiveStatus = "etkin";

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

        lines.Sort(Utf8Order.Instance);
        using IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        foreach (string line in lines)
        {
            hash.AppendData(Encoding.UTF8.GetBytes(line));
            hash.AppendData("\n"u8);
        }

        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private static long? Wide(int? value) => value;

    private static string Line(string table, params object?[] values) =>
        Encoding.UTF8.GetString(PackRows.Canonical(new PackRow(table, values)));
}
