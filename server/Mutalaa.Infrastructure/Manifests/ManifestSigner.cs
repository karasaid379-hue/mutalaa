using System.Text.Json;
using NSec.Cryptography;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Manifesti Ed25519 ile imzalar (K-45). Girdi, signature alani olmayan manifest JSON'udur (ManifestJson.Write ciktisi);
/// imza kanonik (RFC 8785) baytlar uzerindendir. Cikti ayni ozellik sirasini korur ve signature {alg, kid, value}
/// alanini sona ekler. Ed25519 belirlenimcidir: ayni girdi ve anahtar her seferinde ayni baytlari verir.
/// </summary>
public static class ManifestSigner
{
    public const string Algorithm = "ed25519";
    public const int SignatureLength = 64;

    public static byte[] Sign(ReadOnlySpan<byte> manifestJsonWithoutSignature, SigningKey key)
    {
        ArgumentNullException.ThrowIfNull(key);

        using JsonDocument document = JsonDocument.Parse(manifestJsonWithoutSignature.ToArray());
        JsonElement root = document.RootElement;
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new ArgumentException("Manifest kok degeri nesne degil.", nameof(manifestJsonWithoutSignature));
        }

        if (root.TryGetProperty(ManifestCanonicalizer.SignatureProperty, out _))
        {
            throw new ArgumentException("Manifest zaten signature alani tasiyor.", nameof(manifestJsonWithoutSignature));
        }

        byte[] canonical = ManifestCanonicalizer.Canonicalize(root);
        byte[] signature;
        using (Key nsecKey = key.ToNSecKey())
        {
            signature = SignatureAlgorithm.Ed25519.Sign(nsecKey, canonical);
        }

        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream, ManifestJson.IndentedOptions))
        {
            writer.WriteStartObject();
            foreach (JsonProperty property in root.EnumerateObject())
            {
                property.WriteTo(writer);
            }

            writer.WriteStartObject(ManifestCanonicalizer.SignatureProperty);
            writer.WriteString("alg", Algorithm);
            writer.WriteString("kid", key.Kid);
            writer.WriteString("value", Base64Strict.Encode(signature));
            writer.WriteEndObject();
            writer.WriteEndObject();
        }

        stream.WriteByte((byte)'\n');
        return stream.ToArray();
    }
}
