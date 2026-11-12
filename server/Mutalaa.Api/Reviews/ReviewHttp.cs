using System.Buffers.Text;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Primitives;
using Mutalaa.Api.Problems;

namespace Mutalaa.Api.Reviews;

/// <summary>ETag (<c>"{xmin}"</c>) bicimi ve If-Match ayristirma (K-48 madde 6).</summary>
internal static class ReviewEtag
{
    public static string Format(uint xmin) => "\"" + xmin.ToString(CultureInfo.InvariantCulture) + "\"";

    /// <summary>
    /// Baslik yoksa 428 <c>surum-gerekli</c>; <c>*</c>, zayif (<c>W/</c>) etiket, virgullu liste ya da bozuk bicim 400 <c>dogrulama</c>.
    /// Gecerli bicim yalniz <c>"rakamlar"</c>.
    /// </summary>
    public static IResult? TryParseIfMatch(HttpRequest request, out uint xmin)
    {
        ArgumentNullException.ThrowIfNull(request);
        xmin = 0;

        StringValues values = request.Headers.IfMatch;
        if (values.Count == 0 || (values.Count == 1 && string.IsNullOrWhiteSpace(values[0])))
        {
            return ApiProblem.Create(
                StatusCodes.Status428PreconditionRequired,
                ProblemCodes.SurumGerekli,
                "If-Match başlığı zorunludur; kaydın ETag değerini gönderin.");
        }

        string? value = values.Count == 1 ? values[0] : null;
        if (value is not null && TryParseTag(value, out xmin))
        {
            return null;
        }

        return ApiProblem.Create(
            StatusCodes.Status400BadRequest,
            ProblemCodes.Dogrulama,
            "If-Match yalnız tek ve güçlü bir ETag kabul eder: \"123\" biçimi (\"*\", W/ ve liste yok).");
    }

    private static bool TryParseTag(string value, out uint xmin)
    {
        xmin = 0;
        if (value.Length < 3 || value[0] != '"' || value[^1] != '"')
        {
            return false;
        }

        ReadOnlySpan<char> digits = value.AsSpan(1, value.Length - 2);
        foreach (char c in digits)
        {
            if (c is < '0' or > '9')
            {
                return false;
            }
        }

        return uint.TryParse(digits, NumberStyles.None, CultureInfo.InvariantCulture, out xmin);
    }
}

/// <summary>Opak imlec: (created_at, id) anahtar kumesi, base64url. Bozuk imlec 400.</summary>
internal static class ReviewCursor
{
    public static string Encode(DateTime createdAt, long id) =>
        Base64Url.EncodeToString(Encoding.ASCII.GetBytes(
            createdAt.Ticks.ToString(CultureInfo.InvariantCulture) + ":" + id.ToString(CultureInfo.InvariantCulture)));

    private const string WavePrefix = "dalga:";

    /// <summary>Dalga imleci (turu etiketli): <c>dalga:{dalga}:{sira}:{lemma_id}:{id}</c>, base64url. Olusturma imleci bununla cozulmez.</summary>
    public static string EncodeWave(WaveCursor cursor) =>
        Base64Url.EncodeToString(Encoding.ASCII.GetBytes(string.Create(
            CultureInfo.InvariantCulture,
            $"{WavePrefix}{cursor.Dalga}:{cursor.Sira}:{cursor.LemmaId}:{cursor.Id}")));

    public static bool TryDecodeWave(string? text, out WaveCursor cursor)
    {
        cursor = default;
        if (string.IsNullOrEmpty(text) || text.Length > 128)
        {
            return false;
        }

        string decoded;
        try
        {
            decoded = Encoding.ASCII.GetString(Base64Url.DecodeFromChars(text));
        }
        catch (FormatException)
        {
            return false;
        }

        if (!decoded.StartsWith(WavePrefix, StringComparison.Ordinal))
        {
            return false;
        }

        string[] parts = decoded[WavePrefix.Length..].Split(':');
        if (parts.Length != 4
            || !int.TryParse(parts[0], NumberStyles.None, CultureInfo.InvariantCulture, out int dalga)
            || !int.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out int sira)
            || !int.TryParse(parts[2], NumberStyles.None, CultureInfo.InvariantCulture, out int lemma)
            || !long.TryParse(parts[3], NumberStyles.None, CultureInfo.InvariantCulture, out long id)
            || dalga > ReviewQueries.NoWave)
        {
            return false;
        }

        cursor = new WaveCursor(dalga, sira, lemma, id);
        return true;
    }

    public static bool TryDecode(string? text, out DateTime createdAt, out long id)
    {
        createdAt = default;
        id = 0;
        if (string.IsNullOrEmpty(text) || text.Length > 128)
        {
            return false;
        }

        string decoded;
        try
        {
            decoded = Encoding.ASCII.GetString(Base64Url.DecodeFromChars(text));
        }
        catch (FormatException)
        {
            return false;
        }

        int colon = decoded.IndexOf(':', StringComparison.Ordinal);
        if (colon <= 0
            || !long.TryParse(decoded.AsSpan(0, colon), NumberStyles.None, CultureInfo.InvariantCulture, out long ticks)
            || !long.TryParse(decoded.AsSpan(colon + 1), NumberStyles.None, CultureInfo.InvariantCulture, out id)
            || ticks > DateTime.MaxValue.Ticks)
        {
            return false;
        }

        createdAt = new DateTime(ticks, DateTimeKind.Utc);
        return true;
    }
}

/// <summary>Dalga sirasinin anahtar kumesi: (dalga, sira, lemma_id, review.id); dalgasiz kayitta dalga 5, sira en buyuk, lemma 0.</summary>
internal readonly record struct WaveCursor(int Dalga, int Sira, int LemmaId, long Id);

internal static class ReviewJson
{
    /// <summary>jsonb metnini JSON nesnesine cevirir; bos ya da JSON null ise null.</summary>
    public static JsonElement? Parse(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        using JsonDocument document = JsonDocument.Parse(json);
        return document.RootElement.ValueKind == JsonValueKind.Null ? null : document.RootElement.Clone();
    }
}
