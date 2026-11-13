using System.Globalization;
using System.Text.Json;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// Risale birim etiketi (<c>unit.label</c> ve <c>unit_ref.label</c>): "Sözler › 10. Söz › 3. Hakikat ¶4". Parcalar kitabin basligi (kitap tablosundan, slug'dan
/// turetilmez) ve birimin <c>attrs.baslik_yolu</c> dizisidir (bolumun gorunen baslik zinciri); paragraf numarasi <c>attrs.p</c> (yoksa capanin son <c>p{n}</c>
/// parcasi), haşiye biriminde onune "Haşiye {n}" (<c>attrs.hasiye_no</c>) eklenir. Baslik birimi paragraf isareti almaz. Sayilar InvariantCulture ile yazilir;
/// sonuc cihazin yerel ayarina bagli degildir (tr-TR testi). attrs okunamazsa etiket kitap basligi ve paragraf numarasina iner; capa metni etiket olmaz.
/// </summary>
public static class RisaleLabels
{
    /// <summary>U+203A tek acili tirnak: baslik zinciri ayraci.</summary>
    public const string Separator = " › ";

    /// <summary>U+00B6 paragraf isareti.</summary>
    public const string ParagraphMark = "¶";

    private const string HeadingRole = "baslik";
    private const string FootnoteRole = "dipnot";

    public static string Build(RisaleBook book, UnitRow unit)
    {
        ArgumentNullException.ThrowIfNull(book);
        ArgumentNullException.ThrowIfNull(unit);

        List<string> parts = [book.Title];
        long? paragraph = null;
        long? footnote = null;
        ReadAttrs(unit.Attrs, parts, ref paragraph, ref footnote);

        if (footnote is { } n && string.Equals(unit.Role, FootnoteRole, StringComparison.Ordinal))
        {
            parts.Add(string.Create(CultureInfo.InvariantCulture, $"Haşiye {n}"));
        }

        string label = string.Join(Separator, parts);
        if (string.Equals(unit.Role, HeadingRole, StringComparison.Ordinal))
        {
            return label;
        }

        paragraph ??= ParagraphOfAnchor(unit.Anchor);
        return paragraph is { } p ? string.Create(CultureInfo.InvariantCulture, $"{label} {ParagraphMark}{p}") : label;
    }

    private static void ReadAttrs(string? attrs, List<string> parts, ref long? paragraph, ref long? footnote)
    {
        if (string.IsNullOrWhiteSpace(attrs))
        {
            return;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(attrs);
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return;
            }

            if (root.TryGetProperty("baslik_yolu", out JsonElement path) && path.ValueKind == JsonValueKind.Array)
            {
                foreach (JsonElement item in path.EnumerateArray())
                {
                    if (item.ValueKind == JsonValueKind.String && item.GetString() is { Length: > 0 } title)
                    {
                        parts.Add(title);
                    }
                }
            }

            paragraph = ReadNumber(root, "p");
            footnote = ReadNumber(root, "hasiye_no");
        }
        catch (JsonException)
        {
            // Okunamayan attrs etiketi bozmaz: kitap basligi ve capadan paragraf numarasi yeter.
        }
    }

    private static long? ReadNumber(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.Number && value.TryGetInt64(out long number) && number > 0
            ? number
            : null;

    // Birim capasi "...:p{n}" ile biter (hasiye ve baslik birimleri de paragraf capasidir).
    private static long? ParagraphOfAnchor(string anchor)
    {
        int cut = anchor.LastIndexOf(':');
        string last = cut < 0 ? anchor : anchor[(cut + 1)..];
        return last.Length > 1
            && last[0] == 'p'
            && long.TryParse(last.AsSpan(1), NumberStyles.None, CultureInfo.InvariantCulture, out long number)
            && number > 0
                ? number
                : null;
    }
}
