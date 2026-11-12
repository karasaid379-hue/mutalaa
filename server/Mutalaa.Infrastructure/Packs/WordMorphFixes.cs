using System.Globalization;
using System.Text;
using System.Text.Json;
using MackySoft.Json.Canonicalization;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>Bir quran_word_fix satirinin alan turune cevrilmis degeri: root_id ve lemma_id icin Id, pos ve features icin Text (features kanonik JSON).</summary>
public readonly record struct WordFixValue(string Field, int? Id, string? Text);

/// <summary>
/// quran_word_fix uygulama kurali (K-50 madde 4, 6 ve 9; Icerik paketleri 3.3). new_value metindir; alan turune gore cevrilir: root_id ve lemma_id
/// yalniz ondalik rakamlardan olusan pozitif int, pos bos olmayan metin, features gecerli JSON (null degil; RFC 8785 kanonik biciminde yazilir).
/// Duzeltmenin gosterdigi root_id ya da lemma_id pakette (onayli Arapca lemma ya da sozluk kokunde) yoksa, ya da kelimenin QAC satiri yoksa
/// duzeltme uygulanamaz: kapi bunu yayin reddi sayar (<c>duzeltme-uygulanamaz:{neden}</c>), birlestirici ise o duzeltmeyi atlar (yayin zaten durur).
/// Kapi ve birlestirici ayni denetimi kullanir.
/// </summary>
public static class WordMorphFixes
{
    public const string RootId = "root_id";
    public const string LemmaId = "lemma_id";
    public const string Pos = "pos";
    public const string Features = "features";

    public const string DefectUnknownField = "alan-bilinmiyor";
    public const string DefectBadValue = "deger-gecersiz";
    public const string DefectNoWord = "kelime-yok";
    public const string DefectNoTarget = "hedef-kimlik-yok";

    /// <summary>Duzeltmeyi denetler. Uygulanabilirse null doner ve <paramref name="value"/> dolar; aksi halde kisa ASCII neden.</summary>
    /// <param name="wordHasMorphology">Duzeltilen kelimenin QAC satiri (word_morph) var.</param>
    /// <param name="rootExists">Verilen root_id pakette var.</param>
    /// <param name="lemmaExists">Verilen lemma_id pakette (onayli Arapca lemma) var.</param>
    public static string? Check(
        string field,
        string newValue,
        bool wordHasMorphology,
        Func<int, bool> rootExists,
        Func<int, bool> lemmaExists,
        out WordFixValue value)
    {
        ArgumentNullException.ThrowIfNull(field);
        ArgumentNullException.ThrowIfNull(newValue);
        ArgumentNullException.ThrowIfNull(rootExists);
        ArgumentNullException.ThrowIfNull(lemmaExists);

        value = default;
        switch (field)
        {
            case RootId:
            case LemmaId:
                if (!TryParseId(newValue, out int id))
                {
                    return DefectBadValue;
                }

                value = new WordFixValue(field, id, null);
                break;
            case Pos:
                if (string.IsNullOrWhiteSpace(newValue))
                {
                    return DefectBadValue;
                }

                value = new WordFixValue(field, null, newValue);
                break;
            case Features:
                string? canonical = CanonicalJson(newValue);
                if (canonical is null)
                {
                    return DefectBadValue;
                }

                value = new WordFixValue(field, null, canonical);
                break;
            default:
                return DefectUnknownField;
        }

        if (!wordHasMorphology)
        {
            return DefectNoWord;
        }

        if (value.Id is { } target)
        {
            bool exists = string.Equals(field, RootId, StringComparison.Ordinal) ? rootExists(target) : lemmaExists(target);
            if (!exists)
            {
                return DefectNoTarget;
            }
        }

        return null;
    }

    /// <summary>
    /// JSON metnini RFC 8785 kanonik bicimine cevirir (features sutunu hem tabanda hem duzeltmede ayni biciminde yazilir). Gecersiz JSON ve JSON null icin null.
    /// </summary>
    public static string? CanonicalJson(string json)
    {
        ArgumentNullException.ThrowIfNull(json);

        try
        {
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            using JsonDocument document = JsonDocument.Parse(bytes);
            if (document.RootElement.ValueKind == JsonValueKind.Null)
            {
                return null;
            }

            return Encoding.UTF8.GetString(Rfc8785JsonCanonicalizer.Canonicalize(bytes));
        }
        catch (Exception ex) when (ex is JsonException or JsonCanonicalizationException)
        {
            // RFC 8785 kanonikleme yinelenen anahtar, -0 ve temsil edilemeyen buyuk/sonsuz sayi icin JsonCanonicalizationException atar.
            return null;
        }
    }

    /// <summary>
    /// <see cref="CanonicalJson"/> sonucu; kanonikleme basarisizsa (jsonb'de bile gorulebilen temsil edilemeyen sayi) ham metin. Belirlenimcidir: paket satiri ve kaynak
    /// ozeti ayni islevi kullanir, bu yuzden ayni jsonb degeri her gosterimde (<c>["a", "b"]</c> ya da <c>["a","b"]</c>) ayni baytlari verir.
    /// </summary>
    public static string CanonicalJsonOrRaw(string json) => CanonicalJson(json) ?? json;

    private static bool TryParseId(string text, out int id) =>
        int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out id) && id > 0;
}
