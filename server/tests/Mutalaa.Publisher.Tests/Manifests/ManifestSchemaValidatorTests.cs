using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Json.Schema;
using Mutalaa.Infrastructure.Manifests;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>
/// ManifestSchemaValidator: uretilen manifest semaya uyar; semada ifade edilemeyenler (pack_id tekrari, url deseni)
/// ek kontrollerle yakalanir; sema sonucu mevcut ManifestSchemaTests'in kullandigi dogrudan JsonSchema sonucuyla celismez.
/// </summary>
public class ManifestSchemaValidatorTests
{
    private static readonly string SchemaText = ReadData("manifest.schema.json");

    private static readonly ManifestSchemaValidator Validator = new(SchemaText);

    private static readonly JsonSchema RawSchema = JsonSchema.FromText(SchemaText);

    private static readonly EvaluationOptions RawOptions = new() { RequireFormatValidation = true };

    private static string ReadData(string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", name);
        return new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true).GetString(File.ReadAllBytes(path));
    }

    private static JsonObject Signed() => JsonNode.Parse(ImzaFixture.SignedManifest())!.AsObject();

    private static byte[] Bytes(JsonNode node) => Encoding.UTF8.GetBytes(node.ToJsonString());

    private static string[] Codes(ManifestValidation result) => [.. result.Errors.Select(e => e.Code)];

    private static bool RawIsValid(JsonNode node) =>
        RawSchema.Evaluate(JsonSerializer.SerializeToElement(node), RawOptions).IsValid;

    [Fact]
    public void A_built_and_signed_manifest_conforms_to_the_schema_and_the_url_pattern()
    {
        ManifestValidation result = Validator.Validate(ImzaFixture.SignedManifest(), ImzaFixture.PublicBaseUrl);

        Assert.True(result.IsValid, string.Join("; ", result.Errors.Select(e => e.Message)));
    }

    [Fact]
    public void An_unsigned_manifest_does_not_conform_because_signature_is_required()
    {
        ManifestValidation result = Validator.Validate(ImzaFixture.UnsignedManifest(), ImzaFixture.PublicBaseUrl);

        Assert.False(result.IsValid);
        Assert.Contains(ManifestErrorCodes.SchemaMismatch, Codes(result));
    }

    [Fact]
    public void A_repeated_pack_id_is_rejected()
    {
        JsonObject node = Signed();
        JsonArray packs = node["packs"]!.AsArray();
        packs.Add(JsonNode.Parse(packs[0]!.ToJsonString()));

        ManifestValidation result = Validator.Validate(Bytes(node), ImzaFixture.PublicBaseUrl);

        Assert.False(result.IsValid);
        Assert.Contains(ManifestErrorCodes.PackIdDuplicate, Codes(result));
        Assert.DoesNotContain(ManifestErrorCodes.SchemaMismatch, Codes(result));
    }

    [Fact]
    public void A_url_that_does_not_follow_the_layout_is_rejected()
    {
        JsonObject node = Signed();
        node["packs"]![0]!["url"] = "http://192.168.1.50:8333/mutalaa/packs/dev/core/2026.11.0/baska-ad.db";

        ManifestValidation result = Validator.Validate(Bytes(node), ImzaFixture.PublicBaseUrl);

        Assert.Equal([ManifestErrorCodes.UrlMismatch], Codes(result));
    }

    [Fact]
    public void A_url_with_another_flavor_segment_is_rejected()
    {
        JsonObject node = Signed();
        node["packs"]![1]!["url"] = node["packs"]![1]!["url"]!.GetValue<string>().Replace("/dev/", "/public/", StringComparison.Ordinal);

        Assert.Equal([ManifestErrorCodes.UrlMismatch], Codes(Validator.Validate(Bytes(node), ImzaFixture.PublicBaseUrl)));
    }

    [Fact]
    public void A_trailing_slash_on_the_public_base_url_is_trimmed()
    {
        ManifestValidation result = Validator.Validate(ImzaFixture.SignedManifest(), ImzaFixture.PublicBaseUrl + "/");

        Assert.True(result.IsValid);
    }

    [Fact]
    public void Without_a_public_base_url_the_url_pattern_is_not_checked()
    {
        JsonObject node = Signed();
        node["packs"]![0]!["url"] = "https://baska.example/core.db";

        Assert.True(Validator.Validate(Bytes(node)).IsValid);
        Assert.Equal([ManifestErrorCodes.UrlMismatch], Codes(Validator.Validate(Bytes(node), ImzaFixture.PublicBaseUrl)));
    }

    [Fact]
    public void Invalid_json_is_reported_not_thrown()
    {
        ManifestValidation result = Validator.Validate("{"u8);

        Assert.Equal([ManifestErrorCodes.InvalidJson], Codes(result));
    }

    [Fact]
    public void The_section_5_example_is_valid_with_its_own_base_url()
    {
        byte[] example = Encoding.UTF8.GetBytes(ReadData("manifest-ornek.json"));

        Assert.True(Validator.Validate(example, ImzaFixture.PublicBaseUrl).IsValid);
    }

    [Theory]
    [InlineData("no-change")]
    [InlineData("remove-signature")]
    [InlineData("flavor-beta")]
    [InlineData("uppercase-sha256")]
    [InlineData("version-not-calver")]
    [InlineData("empty-packs")]
    [InlineData("extra-signature-field")]
    [InlineData("relative-url")]
    public void The_schema_verdict_agrees_with_the_raw_schema_used_by_ManifestSchemaTests(string mutation)
    {
        JsonObject node = Signed();
        switch (mutation)
        {
            case "remove-signature":
                node.Remove("signature");
                break;
            case "flavor-beta":
                node["flavor"] = "beta";
                break;
            case "uppercase-sha256":
                node["packs"]![0]!["sha256"] = node["packs"]![0]!["sha256"]!.GetValue<string>().ToUpperInvariant();
                break;
            case "version-not-calver":
                node["packs"]![0]!["version"] = "1.2.3";
                break;
            case "empty-packs":
                node["packs"] = new JsonArray();
                break;
            case "extra-signature-field":
                node["signature"]!["extra"] = "x";
                break;
            case "relative-url":
                node["packs"]![0]!["url"] = "mutalaa/packs/core.db";
                break;
        }

        ManifestValidation result = Validator.Validate(Bytes(node));

        Assert.Equal(RawIsValid(node), !Codes(result).Contains(ManifestErrorCodes.SchemaMismatch, StringComparer.Ordinal));
        Assert.Equal(mutation == "no-change", result.IsValid);
    }
}
