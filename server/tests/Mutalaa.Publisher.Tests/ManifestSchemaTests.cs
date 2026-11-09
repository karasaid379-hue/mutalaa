using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Json.Schema;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// packages/content-schema/manifest.schema.json (Icerik paketleri 5, 6; K-21, K-42, K-44 madde 5) sema testleri.
/// A12.3 kabul olcutleri (a)-(e) adlandirilmis testlerdir. Docker gerektirmez.
/// Sema, ornek manifest ve enums.json cikti klasorunun data\ altina kopyalanir.
/// </summary>
public class ManifestSchemaTests
{
    private static readonly JsonSchema Schema = JsonSchema.FromText(ReadData("manifest.schema.json"));

    private static readonly EvaluationOptions Options = new() { RequireFormatValidation = true };

    private static string ReadData(string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", name);
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("Dosya cikti klasorune kopyalanmamis: " + path);
        }

        return new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));
    }

    private static JsonObject Example() => JsonNode.Parse(ReadData("manifest-ornek.json"))!.AsObject();

    private static bool IsValid(JsonNode manifest) =>
        Schema.Evaluate(JsonSerializer.SerializeToElement(manifest), Options).IsValid;

    private static JsonObject FirstPack(JsonObject manifest) => manifest["packs"]!.AsArray()[0]!.AsObject();

    // ---- A12.3 kabul olcutleri (a)-(e) ----

    [Fact]
    public void A12_3_a_section_5_example_is_valid()
    {
        Assert.True(IsValid(Example()));
    }

    [Fact]
    public void A12_3_b_manifest_without_signature_is_rejected()
    {
        JsonObject manifest = Example();
        Assert.True(manifest.Remove("signature"));

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void A12_3_c_unknown_flavor_is_rejected()
    {
        JsonObject manifest = Example();
        manifest["flavor"] = "beta";

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void A12_3_d_uppercase_sha256_is_rejected()
    {
        JsonObject manifest = Example();
        JsonObject pack = FirstPack(manifest);
        pack["sha256"] = pack["sha256"]!.GetValue<string>().ToUpperInvariant();

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("1.2.3")]
    [InlineData("2026.13.0")]
    public void A12_3_e_non_calver_version_is_rejected(string version)
    {
        JsonObject manifest = Example();
        FirstPack(manifest)["version"] = version;

        Assert.False(IsValid(manifest));
    }

    // ---- Sondaki satir sonu: "$" .NET'te son LF'den once de eslesir; desenler "(?![\s\S])" ile biter ----

    [Theory]
    [InlineData("sha256")]
    [InlineData("version")]
    [InlineData("min_app_version")]
    [InlineData("pack_id")]
    [InlineData("url")]
    public void A_trailing_line_feed_is_rejected_in_every_pack_pattern_field(string field)
    {
        JsonObject manifest = Example();
        JsonObject pack = FirstPack(manifest);
        pack[field] = pack[field]!.GetValue<string>() + "\n";

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void A_trailing_line_feed_is_rejected_in_release()
    {
        JsonObject manifest = Example();
        manifest["release"] = manifest["release"]!.GetValue<string>() + "\n";

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void Whitespace_inside_the_url_is_rejected()
    {
        JsonObject manifest = Example();
        FirstPack(manifest)["url"] = "http://192.168.1.50:8333/mutalaa/ packs/core.db";

        Assert.False(IsValid(manifest));
    }

    // ---- Ek denetimler ----

    [Fact]
    public void Schema_flavor_enum_matches_enums_json_derleme_turu_in_order()
    {
        JsonObject schema = JsonNode.Parse(ReadData("manifest.schema.json"))!.AsObject();
        string[] fromSchema = [.. schema["properties"]!["flavor"]!["enum"]!.AsArray().Select(n => n!.GetValue<string>())];
        string[] fromEnums = [.. JsonNode.Parse(ReadData("enums.json"))!["enums"]!["derleme_turu"]!.AsArray().Select(n => n!.GetValue<string>())];

        Assert.Equal(fromEnums, fromSchema);
    }

    [Fact]
    public void Unknown_field_inside_signature_is_rejected()
    {
        JsonObject manifest = Example();
        manifest["signature"]!["extra"] = "x";

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("alg")]
    [InlineData("kid")]
    [InlineData("value")]
    public void Signature_requires_alg_kid_and_value(string field)
    {
        JsonObject manifest = Example();
        Assert.True(manifest["signature"]!.AsObject().Remove(field));

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("alg")]
    [InlineData("kid")]
    [InlineData("value")]
    public void Signature_fields_must_not_be_empty(string field)
    {
        JsonObject manifest = Example();
        manifest["signature"]![field] = string.Empty;

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void Pack_without_url_is_rejected()
    {
        JsonObject manifest = Example();
        Assert.True(FirstPack(manifest).Remove("url"));

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("pack_id")]
    [InlineData("version")]
    [InlineData("sha256")]
    [InlineData("size_bytes")]
    [InlineData("min_app_version")]
    [InlineData("depends_on")]
    public void Pack_without_required_field_is_rejected(string field)
    {
        JsonObject manifest = Example();
        Assert.True(FirstPack(manifest).Remove(field));

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("manifest_version")]
    [InlineData("flavor")]
    [InlineData("release")]
    [InlineData("generated_at")]
    [InlineData("packs")]
    public void Manifest_without_required_top_level_field_is_rejected(string field)
    {
        JsonObject manifest = Example();
        Assert.True(manifest.Remove(field));

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void Unknown_top_level_and_pack_fields_are_accepted_for_forward_compatibility()
    {
        JsonObject manifest = Example();
        manifest["yeni_alan"] = "gelecek";
        FirstPack(manifest)["yeni_pack_alani"] = 42;

        Assert.True(IsValid(manifest));
    }

    [Fact]
    public void Optional_pack_fields_may_be_absent()
    {
        JsonObject manifest = Example();
        JsonObject pack = FirstPack(manifest);
        pack.Remove("schema_version");
        pack.Remove("title");
        pack.Remove("bundled");

        Assert.True(IsValid(manifest));
    }

    [Fact]
    public void Empty_packs_array_is_rejected()
    {
        JsonObject manifest = Example();
        manifest["packs"] = new JsonArray();

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(2)]
    public void Manifest_version_other_than_one_is_rejected(int version)
    {
        JsonObject manifest = Example();
        manifest["manifest_version"] = version;

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("2026.0.0")]
    [InlineData("2026.1.01")]
    [InlineData("26.11.0")]
    [InlineData("2026.11")]
    public void Release_that_is_not_calver_is_rejected(string release)
    {
        JsonObject manifest = Example();
        manifest["release"] = release;

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("2026.1.0")]
    [InlineData("2026.12.7")]
    [InlineData("2026.11.120")]
    public void Release_calver_boundaries_are_accepted(string release)
    {
        JsonObject manifest = Example();
        manifest["release"] = release;

        Assert.True(IsValid(manifest));
    }

    [Theory]
    [InlineData("2026-11-20T09:00:00+03:00")]
    [InlineData("2026-11-20 09:00:00Z")]
    [InlineData("20.11.2026")]
    [InlineData("2026-13-40T09:00:00Z")]
    public void Generated_at_must_be_a_utc_date_time(string value)
    {
        JsonObject manifest = Example();
        manifest["generated_at"] = value;

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("Core")]
    [InlineData("1core")]
    [InlineData("kelime_kok")]
    [InlineData("")]
    public void Pack_id_must_be_lowercase_letters_digits_and_hyphens(string packId)
    {
        JsonObject manifest = Example();
        FirstPack(manifest)["pack_id"] = packId;

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void Depends_on_entries_must_be_pack_ids_and_unique()
    {
        JsonObject manifest = Example();
        JsonObject second = manifest["packs"]!.AsArray()[1]!.AsObject();
        second["depends_on"] = new JsonArray("core", "core");
        Assert.False(IsValid(manifest));

        second["depends_on"] = new JsonArray("Core");
        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("")]
    [InlineData("mutalaa/packs/core.db")]
    [InlineData("ftp://host/core.db")]
    public void Pack_url_must_be_absolute_http_or_https(string url)
    {
        JsonObject manifest = Example();
        FirstPack(manifest)["url"] = url;

        Assert.False(IsValid(manifest));
    }

    [Theory]
    [InlineData("sha256", "abc")]
    [InlineData("min_app_version", "1.0")]
    [InlineData("min_app_version", "v1.0.0")]
    public void Pack_string_fields_with_wrong_shape_are_rejected(string field, string value)
    {
        JsonObject manifest = Example();
        FirstPack(manifest)[field] = value;

        Assert.False(IsValid(manifest));
    }

    [Fact]
    public void Pack_size_bytes_must_be_a_non_negative_integer()
    {
        JsonObject manifest = Example();
        JsonObject pack = FirstPack(manifest);

        pack["size_bytes"] = -1;
        Assert.False(IsValid(manifest));

        pack["size_bytes"] = 1.5;
        Assert.False(IsValid(manifest));

        pack["size_bytes"] = 0;
        Assert.True(IsValid(manifest));
    }

    [Fact]
    public void Pack_schema_version_must_be_at_least_one()
    {
        JsonObject manifest = Example();
        FirstPack(manifest)["schema_version"] = 0;

        Assert.False(IsValid(manifest));
    }
}
