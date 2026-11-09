using System.Text;
using System.Text.Json;
using Json.Schema;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>Sema denetimi sonucu. IsValid ise Errors bostur.</summary>
public sealed record ManifestValidation(bool IsValid, IReadOnlyList<ManifestError> Errors);

/// <summary>
/// Manifesti packages/content-schema/manifest.schema.json'a karsi denetler (JsonSchema.Net, RequireFormatValidation = true)
/// ve semada ifade edilemeyenleri ekler: pack_id tekrari ve (publicBaseUrl verilmisse) url'nin
/// {PublicBaseUrl}/packs/{flavor}/{pack_id}/{version}/{pack_id}-{version}.db ile uyumu.
/// Sema metni cagirana aittir (dosya yolu Publisher yapilandirmasinda: SchemaDir); bu sinif dosya sistemine bakmaz.
/// </summary>
public sealed class ManifestSchemaValidator
{
    private static readonly EvaluationOptions Options = new()
    {
        RequireFormatValidation = true,
        OutputFormat = OutputFormat.List,
    };

    private readonly JsonSchema _schema;

    public ManifestSchemaValidator(string schemaJson)
    {
        ArgumentNullException.ThrowIfNull(schemaJson);
        _schema = JsonSchema.FromText(schemaJson);
    }

    /// <summary>Sema dosyasini kati UTF-8 (BOM'suz) okuyup dogrulayici kurar.</summary>
    public static ManifestSchemaValidator FromFile(string path)
    {
        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));
        return new ManifestSchemaValidator(text);
    }

    /// <param name="manifestJson">Manifest baytlari (imzali ya da imzasiz; signature alani da semaya girer).</param>
    /// <param name="publicBaseUrl">Verilirse url deseni de denetlenir; sonundaki '/' kirpilir.</param>
    public ManifestValidation Validate(ReadOnlySpan<byte> manifestJson, string? publicBaseUrl = null)
    {
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(manifestJson.ToArray());
        }
        catch (JsonException ex)
        {
            return Fail(new ManifestError(ManifestErrorCodes.InvalidJson, "Manifest JSON degil: " + ex.Message));
        }

        using (document)
        {
            JsonElement root = document.RootElement;
            List<ManifestError> errors = [];

            EvaluationResults results = _schema.Evaluate(root, Options);
            if (!results.IsValid)
            {
                CollectSchemaErrors(results, errors);
            }

            if (root.ValueKind == JsonValueKind.Object)
            {
                CheckPacks(root, publicBaseUrl, errors);
            }

            return new ManifestValidation(errors.Count == 0, errors);
        }
    }

    private static void CollectSchemaErrors(EvaluationResults results, List<ManifestError> errors)
    {
        bool any = false;
        foreach (EvaluationResults detail in results.Details ?? [])
        {
            if (detail.IsValid || detail.Errors is null)
            {
                continue;
            }

            foreach (KeyValuePair<string, string> error in detail.Errors)
            {
                errors.Add(new ManifestError(
                    ManifestErrorCodes.SchemaMismatch,
                    $"{detail.InstanceLocation}: {error.Key}: {error.Value}"));
                any = true;
            }
        }

        if (!any)
        {
            errors.Add(new ManifestError(ManifestErrorCodes.SchemaMismatch, "Manifest sema ile uyusmuyor."));
        }
    }

    private static void CheckPacks(JsonElement root, string? publicBaseUrl, List<ManifestError> errors)
    {
        if (!root.TryGetProperty("packs", out JsonElement packs) || packs.ValueKind != JsonValueKind.Array)
        {
            return;
        }

        string? flavor = StringOf(root, "flavor");
        HashSet<string> seen = new(StringComparer.Ordinal);
        foreach (JsonElement pack in packs.EnumerateArray())
        {
            if (pack.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            string? packId = StringOf(pack, "pack_id");
            if (packId is not null && !seen.Add(packId))
            {
                errors.Add(new ManifestError(ManifestErrorCodes.PackIdDuplicate, $"pack_id birden fazla kez geciyor: {packId}"));
            }

            string? version = StringOf(pack, "version");
            string? url = StringOf(pack, "url");
            if (publicBaseUrl is null || flavor is null || packId is null || version is null || url is null)
            {
                continue;
            }

            string expected = ManifestUrls.PackUrl(publicBaseUrl, flavor, packId, version);
            if (!string.Equals(url, expected, StringComparison.Ordinal))
            {
                errors.Add(new ManifestError(
                    ManifestErrorCodes.UrlMismatch,
                    $"{packId}: url beklenenle uyusmuyor (beklenen: {expected}, gelen: {url})."));
            }
        }
    }

    private static string? StringOf(JsonElement element, string name) =>
        element.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static ManifestValidation Fail(ManifestError error) => new(false, [error]);
}
