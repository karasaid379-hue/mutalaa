using System.Globalization;
using System.Net;
using System.Text.Json;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// RFC 9457 hata govdesi denetimi: sapmalari liste olarak dondurur (bos liste = uygun). Matris gibi cok yanitli testlerde
/// tum sapmalar tek iletide toplanir.
/// </summary>
internal static class ProblemChecks
{
    public const string TypePrefix = "urn:mutalaa:problem:";

    /// <summary>
    /// Yanit beklenen durumda, <c>application/problem+json</c>, <c>Location</c> basligi yok, <c>type = urn:mutalaa:problem:{code}</c>,
    /// <c>kod = code</c>, <c>status</c> HTTP durumuyla ayni, <c>title</c> bos degil ve <c>traceId</c> var.
    /// </summary>
    public static async Task<List<string>> DeviationsAsync(
        HttpResponseMessage response,
        HttpStatusCode status,
        string code,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(response);

        List<string> deviations = [];
        if (response.StatusCode != status)
        {
            deviations.Add($"durum {(int)response.StatusCode}, beklenen {(int)status}");
        }

        string? mediaType = response.Content.Headers.ContentType?.MediaType;
        if (!string.Equals(mediaType, "application/problem+json", StringComparison.Ordinal))
        {
            deviations.Add($"icerik turu '{mediaType}', beklenen application/problem+json");
        }

        if (response.Headers.Contains("Location") || response.Headers.Location is not null)
        {
            deviations.Add("Location basligi var");
        }

        string text = await response.Content.ReadAsStringAsync(cancellationToken);
        try
        {
            using JsonDocument document = JsonDocument.Parse(text);
            JsonElement body = document.RootElement;
            string? type = Text(body, "type");
            if (!string.Equals(type, TypePrefix + code, StringComparison.Ordinal))
            {
                deviations.Add($"type '{type}', beklenen '{TypePrefix}{code}'");
            }

            if (!string.Equals(Text(body, "kod"), code, StringComparison.Ordinal))
            {
                deviations.Add($"kod '{Text(body, "kod")}', beklenen '{code}'");
            }

            if (string.IsNullOrEmpty(Text(body, "traceId")))
            {
                deviations.Add("traceId yok ya da bos");
            }

            if (string.IsNullOrEmpty(Text(body, "title")))
            {
                deviations.Add("title yok ya da bos");
            }

            if (!body.TryGetProperty("status", out JsonElement bodyStatus)
                || bodyStatus.ValueKind != JsonValueKind.Number
                || bodyStatus.GetInt32() != (int)response.StatusCode)
            {
                deviations.Add("govdedeki status HTTP durumuyla ayni degil");
            }
        }
        catch (JsonException)
        {
            deviations.Add("govde JSON degil: " + text[..Math.Min(text.Length, 80)]);
        }

        return deviations;
    }

    private static string? Text(JsonElement body, string name) =>
        body.ValueKind == JsonValueKind.Object && body.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    /// <summary>Sapmalar varsa hepsini listeleyen iletiyle basarisiz olur.</summary>
    public static void AssertNone(IReadOnlyCollection<string> deviations, string title)
    {
        ArgumentNullException.ThrowIfNull(deviations);
        Assert.True(
            deviations.Count == 0,
            string.Create(CultureInfo.InvariantCulture, $"{title}: {deviations.Count} sapma{Environment.NewLine}") + string.Join(Environment.NewLine, deviations));
    }
}
