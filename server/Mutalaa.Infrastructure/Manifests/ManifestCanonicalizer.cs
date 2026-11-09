using System.Text.Json;
using MackySoft.Json.Canonicalization;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Imza girdisi (K-45 madde 2): signature alani cikarilmis manifestin RFC 8785 (JCS) baytlari.
/// Kok nesnenin yalniz ust duzey "signature" ozelligi cikarilir; baska hicbir sey degistirilmez.
/// Gecersiz JSON, kok nesne olmayan deger, yinelenen ozellik adi ve JCS'in reddettigi degerler
/// (-0, sonsuz sayi) icin JsonException ya da JsonCanonicalizationException atar.
/// </summary>
public static class ManifestCanonicalizer
{
    public const string SignatureProperty = "signature";

    public static byte[] Canonicalize(ReadOnlySpan<byte> manifestJson)
    {
        using JsonDocument document = JsonDocument.Parse(manifestJson.ToArray());
        return Canonicalize(document.RootElement);
    }

    /// <summary>Kok nesnesi verilmis belge elemani icin kanonik bayt; ManifestVerifier ayni belgeyi yeniden ayristirmasin diye acik.</summary>
    public static byte[] Canonicalize(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException("Manifest kok degeri nesne degil.");
        }

        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            foreach (JsonProperty property in root.EnumerateObject())
            {
                if (property.NameEquals(SignatureProperty))
                {
                    continue;
                }

                property.WriteTo(writer);
            }

            writer.WriteEndObject();
        }

        return Rfc8785JsonCanonicalizer.Canonicalize(stream.ToArray());
    }
}
