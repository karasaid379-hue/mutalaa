using System.Diagnostics.CodeAnalysis;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// Kelime duzeltmesi degerinin dogrulanmasi icin veritabani olgulari (Domain veritabanina bakmaz; Api yukler): kok var mi, lemma var mi ve dili.
/// </summary>
public readonly record struct WordFixFacts(bool RootExists, bool LemmaExists, string? LemmaLang);

/// <summary><c>quran_word_fix.new_value</c> degerinin alana gore kurali (K-51 madde 2).</summary>
public static class WordFixValues
{
    /// <summary><c>pos</c> en cok bu kadar kod noktasi olabilir.</summary>
    public const int MaxPosLength = 20;

    /// <summary><c>features</c> metni en cok bu kadar kod noktasi olabilir.</summary>
    public const int MaxFeaturesLength = 2000;

    /// <summary>Alan dort degerden biri mi (Ordinal).</summary>
    public static bool IsField([NotNullWhen(true)] string? field) =>
        field is ReviewFields.RootId or ReviewFields.LemmaId or ReviewFields.Pos or ReviewFields.Features;

    /// <summary>
    /// Degeri alana gore dogrular ve kanonik biciminii dondurur. <c>root_id</c>: var olan <c>root.id</c> (kanonik tamsayi);
    /// <c>lemma_id</c>: var olan Arapca (<c>lang = 'ar'</c>) lemma kimligi; <c>pos</c>: bos olmayan, en cok 20 kod noktasi (uc bosluklar kirpilir);
    /// <c>features</c>: JSON nesnesi metni (en cok 2000 kod noktasi). Hata 400 <c>dogrulama</c>.
    /// </summary>
    public static string Normalize(string field, string? value, WordFixFacts? facts, string name)
    {
        if (!IsField(field))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "field root_id, lemma_id, pos ya da features olmali.");
        }

        if (string.IsNullOrWhiteSpace(value))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bos olamaz.");
        }

        switch (field)
        {
            case ReviewFields.RootId:
                {
                    int id = ParseId(value, name);
                    if (facts is not { RootExists: true })
                    {
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}: {id.ToString(CultureInfo.InvariantCulture)} kimlikli kok yok.");
                    }

                    return id.ToString(CultureInfo.InvariantCulture);
                }

            case ReviewFields.LemmaId:
                {
                    int id = ParseId(value, name);
                    if (facts is not { LemmaExists: true })
                    {
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}: {id.ToString(CultureInfo.InvariantCulture)} kimlikli lemma yok.");
                    }

                    if (!string.Equals(facts.Value.LemmaLang, LemmaLangs.Arabic, StringComparison.Ordinal))
                    {
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}: lemma Arapca (lang = 'ar') olmali.");
                    }

                    return id.ToString(CultureInfo.InvariantCulture);
                }

            case ReviewFields.Pos:
                {
                    string pos = value.Trim();
                    if (CodePointOffsets.CodePointCount(pos) > MaxPosLength)
                    {
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} en cok {MaxPosLength.ToString(CultureInfo.InvariantCulture)} karakter olabilir.");
                    }

                    return pos;
                }

            default:
                {
                    string features = value.Trim();
                    if (CodePointOffsets.CodePointCount(features) > MaxFeaturesLength)
                    {
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} en cok {MaxFeaturesLength.ToString(CultureInfo.InvariantCulture)} karakter olabilir.");
                    }

                    RequireJsonObject(features, name);
                    return features;
                }
        }
    }

    /// <summary><c>root_id</c> ve <c>lemma_id</c> degerinin sayisal kismi (Api olgulari yuklemek icin kullanir); kanonik tamsayi degilse false.</summary>
    public static bool TryParseId(string? value, out int id)
    {
        id = 0;
        return value is not null
            && int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out id)
            && id >= 1
            && string.Equals(id.ToString(CultureInfo.InvariantCulture), value, StringComparison.Ordinal);
    }

    private static int ParseId(string value, string name)
    {
        if (!TryParseId(value, out int id))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} kanonik bir pozitif tamsayi olmali (ASCII rakam, baska karakter ve bastaki sifir yok).");
        }

        return id;
    }

    private static void RequireJsonObject(string text, string name)
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(text);
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir JSON nesnesi metni olmali.");
            }
        }
        catch (JsonException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli bir JSON nesnesi metni degil.", e);
        }
    }
}

/// <summary>Kelime duzeltmesinin <c>review.duzenlenen</c> jsonb'si: <c>{"new_value": ...}</c>; baska alan ve yanlis tur 400.</summary>
public static class WordFixPayload
{
    /// <summary><c>new_value</c> degeri; deger yoksa (null, JSON null) null.</summary>
    public static string? ReadNewValue(string? json, string name)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(json);
        }
        catch (JsonException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli bir JSON degil.", e);
        }

        using (document)
        {
            JsonElement root = document.RootElement;
            if (root.ValueKind == JsonValueKind.Null)
            {
                return null;
            }

            if (root.ValueKind != JsonValueKind.Object)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir JSON nesnesi olmali.");
            }

            string? value = null;
            foreach (JsonProperty property in root.EnumerateObject())
            {
                if (!string.Equals(property.Name, "new_value", StringComparison.Ordinal))
                {
                    throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property.Name} bilinmeyen alan; yalniz new_value verilir.");
                }

                if (property.Value.ValueKind != JsonValueKind.String)
                {
                    throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.new_value bir dizgi olmali.");
                }

                try
                {
                    value = property.Value.GetString();
                }
                catch (InvalidOperationException e)
                {
                    throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.new_value gecerli Unicode degil.", e);
                }
            }

            return value ?? throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.new_value eksik.");
        }
    }

    public static string ToPayload(string newValue) =>
        JsonSerializer.Serialize(new Dictionary<string, string> { ["new_value"] = newValue });
}

/// <summary>Editorun kelime duzeltmesi adayi acmasi (saf islev): duzeltme satiri ve onu izleyen <c>review</c> kaydi.</summary>
public static class WordFixProposals
{
    /// <summary>
    /// Adayi kurar. <paramref name="anchor"/> kelime capasi olmali (<c>q:s:a:k</c>; aralik, ayet ve kelimesiz capa degil) ve <c>quran_word</c>'de var olmasi
    /// cagiranin gorevidir. <paramref name="qacValue"/> kelimenin bugunku QAC degeridir. Hata 400 <c>dogrulama</c>.
    /// </summary>
    public static (QuranWordFix Fix, Review Review) Open(
        Guid id,
        AnchorRef anchor,
        string? field,
        string? newValue,
        string? reason,
        string? qacValue,
        WordFixFacts? facts,
        string? actor)
    {
        ArgumentNullException.ThrowIfNull(anchor);

        string who = ReviewDecisions.RequireActor(actor);
        if (anchor.Kind != AnchorKind.Q || anchor.Ilk <= 0 || anchor.Son > 0)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "anchor tek bir kelime capasi olmali (q:{sure}:{ayet}:{kelime}).");
        }

        if (!WordFixValues.IsField(field))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "field root_id, lemma_id, pos ya da features olmali.");
        }

        if (string.IsNullOrWhiteSpace(reason))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "reason zorunludur.");
        }

        if (CodePointOffsets.CodePointCount(reason) > ReviewDecisions.MaxGerekceLength)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "reason en cok 2000 karakter olabilir.");
        }

        string value = WordFixValues.Normalize(field, newValue, facts, "new_value");

        QuranWordFix fix = new()
        {
            Id = id,
            Anchor = anchor,
            Field = field,
            QacValue = qacValue,
            NewValue = value,
            Reason = reason,
            Status = XrefStatus.Aday,
            Editor = who,
        };

        Review review = new()
        {
            HedefTablo = ReviewTargets.QuranWordFix,
            HedefAnahtar = id.ToString("D", CultureInfo.InvariantCulture),
            Alan = field,
            Eylem = ReviewActions.Oner,
            Onerilen = ToProposal(value, qacValue, reason),
            Koken = XrefOrigin.Editor,
            Oneren = who,
        };
        return (fix, review);
    }

    private static string ToProposal(string newValue, string? qacValue, string reason)
    {
        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("new_value", newValue);
            if (qacValue is null)
            {
                writer.WriteNull("qac_value");
            }
            else
            {
                writer.WriteString("qac_value", qacValue);
            }

            writer.WriteString("reason", reason);
            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }
}
