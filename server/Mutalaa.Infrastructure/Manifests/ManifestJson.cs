using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Manifest JSON yazici ve okuyucusu. Ozellik sirasi sabittir:
/// manifest_version, flavor, release, generated_at, packs[pack_id, version, sha256, size_bytes, min_app_version,
/// depends_on, url, schema_version, title, bundled], signature (signature'i ManifestSigner ekler).
/// Cikti UTF-8 (BOM'suz), 2 bosluk girintili, LF satir sonlu ve sonda tek LF ile biter.
/// Imza girdisi bu bicime degil, RFC 8785 kanonik bicime (ManifestCanonicalizer) baglidir.
/// </summary>
public static class ManifestJson
{
    /// <summary>generated_at bicimi: UTC, saniye duyarlilikli, Z sonekli.</summary>
    public const string GeneratedAtFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'";

    /// <summary>Girintili cikti secenekleri; ManifestSigner da imzali manifesti ayni seceneklerle yazar.</summary>
    internal static readonly JsonWriterOptions IndentedOptions = new()
    {
        Indented = true,
        IndentSize = 2,
        NewLine = "\n",
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    /// <summary>Imzasiz manifestin JSON baytlari.</summary>
    public static byte[] Write(Manifest manifest)
    {
        ArgumentNullException.ThrowIfNull(manifest);

        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream, IndentedOptions))
        {
            writer.WriteStartObject();
            writer.WriteNumber("manifest_version", manifest.ManifestVersion);
            writer.WriteString("flavor", manifest.Flavor);
            writer.WriteString("release", manifest.Release);
            writer.WriteString("generated_at", FormatGeneratedAt(manifest.GeneratedAt));
            writer.WriteStartArray("packs");
            foreach (ManifestPack pack in manifest.Packs.OrderBy(p => p.PackId, StringComparer.Ordinal))
            {
                WritePack(writer, pack);
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        stream.WriteByte((byte)'\n');
        return stream.ToArray();
    }

    /// <summary>UTC yyyy-MM-ddTHH:mm:ssZ; kultur gozetmez.</summary>
    public static string FormatGeneratedAt(DateTimeOffset value) =>
        value.UtcDateTime.ToString(GeneratedAtFormat, CultureInfo.InvariantCulture);

    /// <summary>
    /// Manifesti okur (signature yok sayilir; bilinmeyen alanlar atlanir). Zorunlu alan eksik ya da tur yanlissa
    /// JsonException atar. Sema denetimi ManifestSchemaValidator'indir.
    /// </summary>
    public static Manifest Read(ReadOnlySpan<byte> json)
    {
        using JsonDocument document = JsonDocument.Parse(json.ToArray());
        JsonElement root = document.RootElement;
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException("Manifest kok degeri nesne degil.");
        }

        int version = RequireInt32(root, "manifest_version");
        string flavor = RequireString(root, "flavor");
        string release = RequireString(root, "release");
        string generatedAt = RequireString(root, "generated_at");
        if (!root.TryGetProperty("packs", out JsonElement packsElement) || packsElement.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException("packs dizisi yok.");
        }

        List<ManifestPack> packs = [];
        foreach (JsonElement item in packsElement.EnumerateArray())
        {
            packs.Add(ReadPack(item));
        }

        DateTimeOffset parsed = DateTimeOffset.Parse(
            generatedAt,
            CultureInfo.InvariantCulture,
            DateTimeStyles.AdjustToUniversal | DateTimeStyles.AssumeUniversal);

        return new Manifest(flavor, release, parsed, packs) { ManifestVersion = version };
    }

    private static void WritePack(Utf8JsonWriter writer, ManifestPack pack)
    {
        writer.WriteStartObject();
        writer.WriteString("pack_id", pack.PackId);
        writer.WriteString("version", pack.Version);
        writer.WriteString("sha256", pack.Sha256);
        writer.WriteNumber("size_bytes", pack.SizeBytes);
        writer.WriteString("min_app_version", pack.MinAppVersion);
        writer.WriteStartArray("depends_on");
        foreach (string dependency in pack.DependsOn)
        {
            writer.WriteStringValue(dependency);
        }

        writer.WriteEndArray();
        writer.WriteString("url", pack.Url);
        writer.WriteNumber("schema_version", pack.SchemaVersion);
        if (pack.Title is not null)
        {
            writer.WriteString("title", pack.Title);
        }

        if (pack.Bundled is bool bundled)
        {
            writer.WriteBoolean("bundled", bundled);
        }

        writer.WriteEndObject();
    }

    private static ManifestPack ReadPack(JsonElement item)
    {
        if (item.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException("packs ogesi nesne degil.");
        }

        List<string> dependsOn = [];
        if (!item.TryGetProperty("depends_on", out JsonElement depends) || depends.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException("depends_on dizisi yok.");
        }

        foreach (JsonElement dependency in depends.EnumerateArray())
        {
            dependsOn.Add(dependency.ValueKind == JsonValueKind.String
                ? dependency.GetString()!
                : throw new JsonException("depends_on ogesi metin degil."));
        }

        string? title = item.TryGetProperty("title", out JsonElement titleElement) && titleElement.ValueKind == JsonValueKind.String
            ? titleElement.GetString()
            : null;
        bool? bundled = item.TryGetProperty("bundled", out JsonElement bundledElement)
            && bundledElement.ValueKind is JsonValueKind.True or JsonValueKind.False
                ? bundledElement.GetBoolean()
                : null;

        return new ManifestPack(
            RequireString(item, "pack_id"),
            RequireString(item, "version"),
            RequireString(item, "sha256"),
            RequireInt64(item, "size_bytes"),
            RequireString(item, "min_app_version"),
            dependsOn,
            RequireString(item, "url"),
            item.TryGetProperty("schema_version", out JsonElement schemaVersion) && schemaVersion.ValueKind == JsonValueKind.Number
                ? schemaVersion.GetInt32()
                : 1,
            title,
            bundled);
    }

    private static string RequireString(JsonElement element, string name) =>
        element.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()!
            : throw new JsonException($"{name} alani yok ya da metin degil.");

    private static int RequireInt32(JsonElement element, string name) =>
        element.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.Number && value.TryGetInt32(out int number)
            ? number
            : throw new JsonException($"{name} alani yok ya da tamsayi degil.");

    private static long RequireInt64(JsonElement element, string name) =>
        element.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.Number && value.TryGetInt64(out long number)
            ? number
            : throw new JsonException($"{name} alani yok ya da tamsayi degil.");
}
