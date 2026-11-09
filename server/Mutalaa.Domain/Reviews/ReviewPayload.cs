using System.Text.Json;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// Metin incelemesinde onceki, onerilen ve duzenlenen jsonb degerleri: <c>{"metin": ..., "content_hash": ...}</c> (K-48).
/// Bos deger (null ya da JSON null) "deger yok" demektir; bozuk JSON ya da yanlis turde alan <c>dogrulama</c> hatasidir.
/// </summary>
internal static class ReviewPayload
{
    /// <summary>"metin" alani; deger yoksa null. Metin bos olamaz.</summary>
    public static string? ReadMetin(string? json, string name)
    {
        using JsonDocument? document = Parse(json, name);
        if (document is null)
        {
            return null;
        }

        string? metin = ReadString(document.RootElement, "metin", name);
        if (string.IsNullOrEmpty(metin))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.metin bos olamaz.");
        }

        return metin;
    }

    /// <summary>"content_hash" alani; deger (nesnenin kendisi) yoksa null. Nesne var ama alan yoksa hata.</summary>
    public static string? ReadContentHash(string? json, string name)
    {
        using JsonDocument? document = Parse(json, name);
        if (document is null)
        {
            return null;
        }

        string? hash = ReadString(document.RootElement, "content_hash", name);
        if (string.IsNullOrEmpty(hash))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.content_hash eksik.");
        }

        return hash;
    }

    private static JsonDocument? Parse(string? json, string name)
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

        if (document.RootElement.ValueKind == JsonValueKind.Null)
        {
            document.Dispose();
            return null;
        }

        if (document.RootElement.ValueKind != JsonValueKind.Object)
        {
            document.Dispose();
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir JSON nesnesi olmali.");
        }

        return document;
    }

    private static string? ReadString(JsonElement element, string property, string name)
    {
        if (!element.TryGetProperty(property, out JsonElement value))
        {
            return null;
        }

        if (value.ValueKind != JsonValueKind.String)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property} bir dizgi olmali.");
        }

        try
        {
            return value.GetString();
        }
        catch (InvalidOperationException e)
        {
            // Kacis dizisi gecerli UTF-16 vermiyor (tek basina vekil).
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property} gecerli Unicode degil.", e);
        }
    }
}
