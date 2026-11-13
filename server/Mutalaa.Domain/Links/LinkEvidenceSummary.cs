using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Links;

/// <summary>
/// Baglanti kanitinin editor kartina giden ozeti (A18.4): <c>xref.evidence</c> jsonb'sinden yalniz beyaz listedeki anahtarlar gecer.
/// Bilinmeyen anahtar, beklenen turde olmayan deger ve cok uzun metin atilir; hattin ic ayrintilari (run_id, llm vb.) dis dunyaya cikmaz.
/// </summary>
public static class LinkEvidenceSummary
{
    /// <summary>Metin degerleri icin ust sinir (kod birimi); asani atilir.</summary>
    public const int MaxStringLength = 256;

    /// <summary><c>alternatives</c> dizisinde en cok bu kadar oge gecer.</summary>
    public const int MaxAlternatives = 10;

    private const int MaxAlternativeProperties = 8;

    private static readonly string[] Numbers = ["matched_words", "ayah_words", "coverage", "identity", "phrase_freq"];
    private static readonly string[] Bools = ["consistent_quote", "editor_duzeltmesi"];
    private static readonly string[] Strings = ["position", "subtype", "src_hash", "dst_hash", "source_id"];

    /// <summary>
    /// Ozeti JSON nesnesi olarak dondurur (anahtar sirasi sabit: sayilar, mantiksallar, metinler, <c>group</c>, <c>alternatives</c>).
    /// Kanit bos, bozuk ya da nesne degilse null doner; hicbir anahtar gecmezse <c>{}</c>.
    /// </summary>
    public static string? Build(string? evidenceJson)
    {
        if (string.IsNullOrWhiteSpace(evidenceJson))
        {
            return null;
        }

        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(evidenceJson);
        }
        catch (JsonException)
        {
            return null;
        }

        using (document)
        {
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            using MemoryStream stream = new();
            using (Utf8JsonWriter writer = new(stream))
            {
                writer.WriteStartObject();
                foreach (string name in Numbers)
                {
                    if (root.TryGetProperty(name, out JsonElement v) && v.ValueKind == JsonValueKind.Number)
                    {
                        writer.WritePropertyName(name);
                        v.WriteTo(writer);
                    }
                }

                foreach (string name in Bools)
                {
                    if (root.TryGetProperty(name, out JsonElement v) && v.ValueKind is JsonValueKind.True or JsonValueKind.False)
                    {
                        writer.WriteBoolean(name, v.GetBoolean());
                    }
                }

                foreach (string name in Strings)
                {
                    if (root.TryGetProperty(name, out JsonElement v) && TryShortString(v, out string text))
                    {
                        writer.WriteString(name, text);
                    }
                }

                if (root.TryGetProperty("group", out JsonElement group) && TryScalar(group, out _))
                {
                    writer.WritePropertyName("group");
                    group.WriteTo(writer);
                }

                if (root.TryGetProperty("alternatives", out JsonElement alternatives) && alternatives.ValueKind == JsonValueKind.Array)
                {
                    writer.WritePropertyName("alternatives");
                    WriteAlternatives(writer, alternatives);
                }

                writer.WriteEndObject();
            }

            return Encoding.UTF8.GetString(stream.ToArray());
        }
    }

    private static void WriteAlternatives(Utf8JsonWriter writer, JsonElement alternatives)
    {
        writer.WriteStartArray();
        int count = 0;
        foreach (JsonElement item in alternatives.EnumerateArray())
        {
            if (count >= MaxAlternatives)
            {
                break;
            }

            if (item.ValueKind == JsonValueKind.Object)
            {
                writer.WriteStartObject();
                int written = 0;
                foreach (JsonProperty property in item.EnumerateObject())
                {
                    if (written >= MaxAlternativeProperties)
                    {
                        break;
                    }

                    if (TryScalar(property.Value, out _))
                    {
                        writer.WritePropertyName(property.Name);
                        property.Value.WriteTo(writer);
                        written++;
                    }
                }

                writer.WriteEndObject();
                count++;
            }
            else if (TryScalar(item, out _))
            {
                item.WriteTo(writer);
                count++;
            }
        }

        writer.WriteEndArray();
    }

    /// <summary>Kisa dizgi, sayi ya da mantiksal (nesne, dizi ve null degil).</summary>
    private static bool TryScalar(JsonElement value, out JsonElement scalar)
    {
        scalar = value;
        return value.ValueKind switch
        {
            JsonValueKind.String => TryShortString(value, out _),
            JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False => true,
            _ => false,
        };
    }

    private static bool TryShortString(JsonElement value, out string text)
    {
        text = string.Empty;
        if (value.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        try
        {
            string? s = value.GetString();
            if (s is null || s.Length > MaxStringLength)
            {
                return false;
            }

            text = s;
            return true;
        }
        catch (InvalidOperationException)
        {
            return false;
        }
    }

    /// <summary>
    /// Duzeltmeyi kanita isler (Duzeltme yapilmis onay): <c>editor_duzeltmesi = true</c> yazilir; hedef birim degistiyse <c>dst_hash</c>
    /// yeni birimin <c>content_hash</c> degerinin ilk 16 hanesi olur (K-51 madde 1; aksi halde Yayinlayici satiri <c>uc-ozeti-tutmadi</c> diye atar).
    /// Kalan anahtarlar oldugu gibi korunur. Bozuk ya da nesne olmayan kanit bos nesneden baslar.
    /// </summary>
    public static string WithEditorCorrection(string? evidenceJson, string? newDstHash16)
    {
        Dictionary<string, JsonElement> map = new(StringComparer.Ordinal);
        if (!string.IsNullOrWhiteSpace(evidenceJson))
        {
            try
            {
                using JsonDocument document = JsonDocument.Parse(evidenceJson);
                if (document.RootElement.ValueKind == JsonValueKind.Object)
                {
                    foreach (JsonProperty property in document.RootElement.EnumerateObject())
                    {
                        map[property.Name] = property.Value.Clone();
                    }
                }
            }
            catch (JsonException)
            {
                // Bozuk kanit: bos nesneden baslanir.
            }
        }

        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            foreach ((string name, JsonElement value) in map)
            {
                if (string.Equals(name, "editor_duzeltmesi", StringComparison.Ordinal)
                    || (newDstHash16 is not null && string.Equals(name, "dst_hash", StringComparison.Ordinal)))
                {
                    continue;
                }

                writer.WritePropertyName(name);
                value.WriteTo(writer);
            }

            if (newDstHash16 is not null)
            {
                writer.WriteString("dst_hash", newDstHash16);
            }

            writer.WriteBoolean("editor_duzeltmesi", true);
            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    /// <summary>Birimin <c>content_hash</c> degerinin ilk 16 hanesi (kanit <c>src_hash</c>/<c>dst_hash</c> bicimi).</summary>
    public static string? Hash16(string? contentHash) =>
        contentHash is { Length: >= 16 } ? contentHash[..16] : null;
}

/// <summary>Vurgulu dizi: kaynak birim metninden kaynak araligina denk gelen dilim ve iki yanindaki baglam (kod noktasi pencereleri).</summary>
public readonly record struct HighlightedSequence(string? Sol, string? Dizi, string? Sag)
{
    /// <summary>Metin yok, aralik gecersiz ya da ozet uyusmuyor: uc alan da null.</summary>
    public static HighlightedSequence None => default;
}

/// <summary>Vurgulu dizi hesabi (saf islev).</summary>
public static class LinkHighlight
{
    /// <summary>Vurgunun solunda ve saginda gosterilen baglam penceresi (kod noktasi).</summary>
    public const int Window = 40;

    /// <summary>
    /// <paramref name="text"/> kaynak birimin metni, <paramref name="contentHash"/> birimin guncel ozeti, <paramref name="evidenceSrcHash"/>
    /// kanitin <c>src_hash</c> degeri (16 hane), <paramref name="span"/> kaynak araligi ([bas, son) kod noktasi; null birimin tamami).
    /// Ozet yoksa ya da birimin ozetinin onekiyle uyusmuyorsa (metin degismis, ofset guvenilmez) hicbir sey gosterilmez.
    /// </summary>
    public static HighlightedSequence Compute(string? text, string? contentHash, string? evidenceSrcHash, AnchorSpan? span)
    {
        if (text is null
            || contentHash is null
            || evidenceSrcHash is not { Length: >= 16 and <= 64 }
            || !contentHash.StartsWith(evidenceSrcHash, StringComparison.Ordinal))
        {
            return HighlightedSequence.None;
        }

        if (span is not { } range)
        {
            return new HighlightedSequence(string.Empty, text, string.Empty);
        }

        int length = CodePointOffsets.CodePointCount(text);
        if (range.Start < 0 || range.Start >= range.End || range.End > length)
        {
            return HighlightedSequence.None;
        }

        int from = Math.Max(0, range.Start - Window);
        int to = Math.Min(length, range.End + Window);
        return new HighlightedSequence(
            CodePointOffsets.Slice(text, from, range.Start),
            CodePointOffsets.Slice(text, range.Start, range.End),
            CodePointOffsets.Slice(text, range.End, to));
    }
}
