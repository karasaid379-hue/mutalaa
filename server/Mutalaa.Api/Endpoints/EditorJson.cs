using System.Text.Encodings.Web;
using System.Text.Json;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Editor uclarinin JSON yazimi: alan adlari snake_case (veritabani sutunlariyla ayni) ve ASCII disi karakterler
/// kacislanmaz (Arapca ve Turkce metin okunur kalir; bayt bayt metin butunlugu). jsonb alanlari dizgi degil ham JSON olarak gider.
/// </summary>
internal static class EditorJson
{
    /// <summary>
    /// Tek kodlayici: hem bu sinifin secenekleri hem HTTP JSON secenekleri (Program.cs, ConfigureHttpJsonOptions) bunu kullanir;
    /// boylece her uc ASCII disi metni ayni bicimde (kacissiz UTF-8) yazar.
    /// </summary>
    public static readonly JavaScriptEncoder Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping;

    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Encoder = Encoder,
    };

    /// <summary>jsonb sutun degerini JSON ogesi yapar; deger yoksa null. Veritabani zaten gecerli JSON tutar.</summary>
    public static JsonElement? Raw(string? json)
    {
        if (json is null)
        {
            return null;
        }

        using JsonDocument document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    public static IResult Ok<T>(T value) => TypedResults.Json(value, Options);
}
