using System.Text.Json;

namespace Mutalaa.Domain.Links;

/// <summary>
/// Baglanti adayinin editor kuyrugu sinifi (Iktibas tespiti 12, K-51 madde 2, A18.4): kuyruk sirasi tutarsiz, toplu, gri, diger.
/// Sayisal deger kuyruk sirasidir (kucuk once).
/// </summary>
public enum LinkCandidateClass
{
    Tutarsiz = 0,
    Toplu = 1,
    Gri = 2,
    Diger = 3,
}

/// <summary>LinkCandidateClass etiketleri (API <c>sinif</c> alani ve suzgeci). Acik switch; yansima ve kulturlu donusum yok.</summary>
public static class LinkCandidateClassLabels
{
    public static string ToLabel(this LinkCandidateClass value) => value switch
    {
        LinkCandidateClass.Tutarsiz => "tutarsiz",
        LinkCandidateClass.Toplu => "toplu",
        LinkCandidateClass.Gri => "gri",
        LinkCandidateClass.Diger => "diger",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    /// <summary>Etiketi tam (Ordinal, buyuk-kucuk harf duyarli) eslestirir; eslesmezse false.</summary>
    public static bool TryParseLabel(string? label, out LinkCandidateClass value)
    {
        switch (label)
        {
            case "tutarsiz":
                value = LinkCandidateClass.Tutarsiz;
                return true;
            case "toplu":
                value = LinkCandidateClass.Toplu;
                return true;
            case "gri":
                value = LinkCandidateClass.Gri;
                return true;
            case "diger":
                value = LinkCandidateClass.Diger;
                return true;
            default:
                value = default;
                return false;
        }
    }
}

/// <summary>
/// Siniflandirmanin okudugu kanit alanlari (<c>xref.evidence</c> jsonb). Alan yoksa ya da turu yanlissa null'dir.
/// Sayilar JSON sayisidir (<c>matched_words</c> n, <c>coverage</c>, <c>phrase_freq</c> f); <c>consistent_quote</c> JSON bool.
/// </summary>
public readonly record struct LinkEvidenceFacts(double? MatchedWords, double? Coverage, double? PhraseFreq, bool? ConsistentQuote);

/// <summary>
/// Aday sinifi kurali (saf islev). Sira onemlidir: once tutarsiz, sonra toplu, sonra gri, kalani diger.
/// <list type="bullet">
/// <item><description><b>tutarsiz</b>: <c>evidence.consistent_quote = false</c> ya da (<c>confidence &lt;= 0,30</c> ve tur <c>atif</c>).</description></item>
/// <item><description><b>toplu</b>: tur <c>iktibas</c> ya da <c>atif</c>, n (<c>matched_words</c>) &gt;= 7, kapsama = 1, f (<c>phrase_freq</c>) = 1
/// (alan yoksa toplu degil) ve (<c>consistent_quote = true</c> ya da <c>confidence &gt;= 0,95</c>).</description></item>
/// <item><description><b>gri</b>: <c>0,40 &lt;= confidence &lt; 0,80</c>.</description></item>
/// </list>
/// Ayni kural kuyruk sirasi ve suzgeci icin SQL'de de yazilidir (<c>ReviewQueries</c>); ikisinin uyumu bir testle denetlenir.
/// </summary>
public static class LinkCandidateClassifier
{
    public const float InconsistentAtifMaxConfidence = 0.30f;
    public const double BulkMinMatchedWords = 7;
    public const double BulkMinCoverage = 0.999999;
    public const float BulkMinConfidence = 0.95f;
    public const float GreyMinConfidence = 0.40f;
    public const float GreyMaxConfidenceExclusive = 0.80f;

    public static LinkCandidateClass Classify(XrefType type, float confidence, LinkEvidenceFacts facts)
    {
        if (facts.ConsistentQuote == false || (type == XrefType.Atif && confidence <= InconsistentAtifMaxConfidence))
        {
            return LinkCandidateClass.Tutarsiz;
        }

        if (type is XrefType.Iktibas or XrefType.Atif
            && facts.MatchedWords >= BulkMinMatchedWords
            && facts.Coverage >= BulkMinCoverage
            && facts.PhraseFreq == 1
            && (facts.ConsistentQuote == true || confidence >= BulkMinConfidence))
        {
            return LinkCandidateClass.Toplu;
        }

        return confidence >= GreyMinConfidence && confidence < GreyMaxConfidenceExclusive
            ? LinkCandidateClass.Gri
            : LinkCandidateClass.Diger;
    }

    /// <summary>Kaniti jsonb metninden okuyarak siniflandirir; bos, bozuk ya da nesne olmayan kanit "alan yok" demektir.</summary>
    public static LinkCandidateClass Classify(XrefType type, float confidence, string? evidenceJson) =>
        Classify(type, confidence, LinkEvidenceReader.ReadFacts(evidenceJson));
}

/// <summary>Kanit jsonb'sinden sinif alanlarini tolerans ile okur (bozuk JSON, nesne olmayan kok ya da yanlis turde alan: alan yok).</summary>
public static class LinkEvidenceReader
{
    public static LinkEvidenceFacts ReadFacts(string? evidenceJson)
    {
        if (string.IsNullOrWhiteSpace(evidenceJson))
        {
            return default;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(evidenceJson);
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return default;
            }

            return new LinkEvidenceFacts(
                Number(root, "matched_words"),
                Number(root, "coverage"),
                Number(root, "phrase_freq"),
                Bool(root, "consistent_quote"));
        }
        catch (JsonException)
        {
            return default;
        }
    }

    /// <summary>Metin alani (dizgi degilse ya da yoksa null).</summary>
    public static string? ReadString(string? evidenceJson, string property)
    {
        if (string.IsNullOrWhiteSpace(evidenceJson))
        {
            return null;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(evidenceJson);
            if (document.RootElement.ValueKind == JsonValueKind.Object
                && document.RootElement.TryGetProperty(property, out JsonElement value)
                && value.ValueKind == JsonValueKind.String)
            {
                return value.GetString();
            }
        }
        catch (JsonException)
        {
            // Bozuk kanit: alan yok.
        }
        catch (InvalidOperationException)
        {
            // Kacis dizisi gecerli UTF-16 vermiyor.
        }

        return null;
    }

    private static double? Number(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out double d) ? d : null;

    private static bool? Bool(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False ? value.GetBoolean() : null;
}
