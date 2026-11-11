using System.Text.Json;
using Mutalaa.Api.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Depodaki OpenAPI belgesi (server/Mutalaa.Api/openapi/v1.json) gercek yanit govdesini anlatir: ProblemDetails uzantilari,
/// 400 dogrulama yanitinin errors alani, limit parametresinin tam sayi araligi, sayi dugumlerinin dizgi kabul etmemesi
/// (NumberHandling.Strict) ve inceleme ogelerinin jsonb alanlari. Docker gerekmez.
/// </summary>
public sealed class OpenApiDocumentFixTests : IDisposable
{
    private readonly JsonDocument _document =
        JsonDocument.Parse(RepoFiles.ReadUtf8(RepoFiles.PathOf("server/Mutalaa.Api/openapi/v1.json")));

    private JsonElement Schemas => _document.RootElement.GetProperty("components").GetProperty("schemas");

    public void Dispose() => _document.Dispose();

    private static bool AllowsString(JsonElement schema)
    {
        JsonElement type = schema.GetProperty("type");
        return type.ValueKind == JsonValueKind.String
            ? type.GetString() == "string"
            : type.EnumerateArray().Any(t => t.GetString() == "string");
    }

    [Fact]
    public void ProblemDetails_describes_the_real_body_kod_traceId_and_open_extensions()
    {
        JsonElement problem = Schemas.GetProperty("ProblemDetails");
        JsonElement properties = problem.GetProperty("properties");

        Assert.True(AllowsString(properties.GetProperty("kod")));
        Assert.True(AllowsString(properties.GetProperty("traceId")));
        foreach (string extension in new[] { "kapi_raporu", "yayin", "kimlikler", "kimlik", "hatalar" })
        {
            Assert.True(properties.TryGetProperty(extension, out _), $"ProblemDetails.{extension} yok.");
        }

        // additionalProperties acikca yazilidir ve false degildir (ucun tipli uzantilari ve ek alanlar serbest).
        Assert.True(problem.TryGetProperty("additionalProperties", out JsonElement additional), "ProblemDetails.additionalProperties yok.");
        Assert.NotEqual(JsonValueKind.False, additional.ValueKind);
    }

    [Fact]
    public void ProblemDetails_status_is_a_plain_int32()
    {
        JsonElement status = Schemas.GetProperty("ProblemDetails").GetProperty("properties").GetProperty("status");

        JsonElement type = status.GetProperty("type");
        string[] kinds = type.ValueKind == JsonValueKind.String ? [type.GetString()!] : [.. type.EnumerateArray().Select(t => t.GetString()!)];
        Assert.Contains("integer", kinds);
        Assert.DoesNotContain("string", kinds);
        Assert.Equal("int32", status.GetProperty("format").GetString());
    }

    [Fact]
    public void ValidationProblemDetails_adds_errors_as_a_field_to_messages_map()
    {
        JsonElement validation = Schemas.GetProperty("ValidationProblemDetails");
        string text = validation.GetRawText();

        Assert.Contains("#/components/schemas/ProblemDetails", text, StringComparison.Ordinal);
        JsonElement errors = FindErrors(validation);
        Assert.Equal("object", errors.GetProperty("type").GetString());
        JsonElement values = errors.GetProperty("additionalProperties");
        Assert.Equal("array", values.GetProperty("type").GetString());
        Assert.Equal("string", values.GetProperty("items").GetProperty("type").GetString());
    }

    private static JsonElement FindErrors(JsonElement validation)
    {
        if (validation.TryGetProperty("properties", out JsonElement direct) && direct.TryGetProperty("errors", out JsonElement found))
        {
            return found;
        }

        foreach (JsonElement part in validation.GetProperty("allOf").EnumerateArray())
        {
            if (part.TryGetProperty("properties", out JsonElement properties) && properties.TryGetProperty("errors", out JsonElement nested))
            {
                return nested;
            }
        }

        throw new Xunit.Sdk.XunitException("ValidationProblemDetails.errors yok.");
    }

    [Fact]
    public void Every_400_problem_response_points_at_ValidationProblemDetails()
    {
        int checkedCount = 0;
        foreach (JsonProperty path in _document.RootElement.GetProperty("paths").EnumerateObject())
        {
            foreach (JsonProperty operation in path.Value.EnumerateObject())
            {
                if (!operation.Value.TryGetProperty("responses", out JsonElement responses)
                    || !responses.TryGetProperty("400", out JsonElement badRequest)
                    || !badRequest.TryGetProperty("content", out JsonElement content)
                    || !content.TryGetProperty("application/problem+json", out JsonElement media))
                {
                    continue;
                }

                Assert.Equal("#/components/schemas/ValidationProblemDetails", media.GetProperty("schema").GetProperty("$ref").GetString());
                checkedCount++;
            }
        }

        Assert.True(checkedCount > 5, "400 yanitli uc sayisi beklenenden az.");
    }

    [Theory]
    [InlineData("/api/v1/units")]
    [InlineData("/api/v1/reviews")]
    [InlineData("/api/v1/releases")]
    public void The_limit_query_parameter_is_an_integer_between_1_and_200(string path)
    {
        JsonElement parameters = _document.RootElement.GetProperty("paths").GetProperty(path).GetProperty("get").GetProperty("parameters");
        JsonElement limit = parameters.EnumerateArray().Single(p => p.GetProperty("name").GetString() == "limit");
        JsonElement schema = limit.GetProperty("schema");

        Assert.Equal("integer", schema.GetProperty("type").GetString());
        Assert.Equal(1, schema.GetProperty("minimum").GetDecimal());
        Assert.Equal(200, schema.GetProperty("maximum").GetDecimal());
    }

    [Fact]
    public void No_numeric_node_accepts_a_string_or_carries_a_pattern()
    {
        int numeric = 0;
        Visit(_document.RootElement, "#", ref numeric);

        Assert.True(numeric >= 40, $"Sayi dugumu sayisi beklenenden az: {numeric}.");
    }

    private static void Visit(JsonElement node, string path, ref int numeric)
    {
        if (node.ValueKind == JsonValueKind.Object)
        {
            if (node.TryGetProperty("type", out JsonElement type) && type.ValueKind is JsonValueKind.String or JsonValueKind.Array)
            {
                string[] kinds = type.ValueKind == JsonValueKind.String ? [type.GetString()!] : [.. type.EnumerateArray().Select(t => t.GetString()!)];
                if (kinds.Contains("integer", StringComparer.Ordinal) || kinds.Contains("number", StringComparer.Ordinal))
                {
                    numeric++;
                    Assert.False(kinds.Contains("string", StringComparer.Ordinal), $"{path}: sayi dugumu string kabul ediyor.");
                    Assert.False(node.TryGetProperty("pattern", out _), $"{path}: sayi dugumunde pattern var.");
                }
            }

            foreach (JsonProperty property in node.EnumerateObject())
            {
                Visit(property.Value, path + "/" + property.Name, ref numeric);
            }
        }
        else if (node.ValueKind == JsonValueKind.Array)
        {
            int index = 0;
            foreach (JsonElement item in node.EnumerateArray())
            {
                Visit(item, path + "/" + index.ToString(System.Globalization.CultureInfo.InvariantCulture), ref numeric);
                index++;
            }
        }
    }

    [Theory]
    [InlineData("ReviewItemDto")]
    [InlineData("ReviewDetailDto")]
    public void The_review_schemas_carry_onceki_onerilen_and_duzenlenen_as_optional_json(string schemaName)
    {
        JsonElement schema = Schemas.GetProperty(schemaName);
        JsonElement properties = schema.GetProperty("properties");
        string[] required = schema.TryGetProperty("required", out JsonElement list) ? [.. list.EnumerateArray().Select(r => r.GetString()!)] : [];

        foreach (string name in new[] { "onceki", "onerilen", "duzenlenen" })
        {
            Assert.True(properties.TryGetProperty(name, out JsonElement property), $"{schemaName}.{name} yok.");
            Assert.DoesNotContain(name, required);
            Assert.Contains("#/components/schemas/JsonElement", property.GetRawText(), StringComparison.Ordinal);
        }
    }

    [Theory]
    [InlineData("DecisionBody")]
    [InlineData("BulkDecisionItem")]
    public void The_decision_schemas_make_duzenlenen_optional_and_keep_karar_and_gerekce_required(string schemaName)
    {
        JsonElement schema = Schemas.GetProperty(schemaName);
        string[] required = [.. schema.GetProperty("required").EnumerateArray().Select(r => r.GetString()!)];

        Assert.True(schema.GetProperty("properties").TryGetProperty("duzenlenen", out _), $"{schemaName}.duzenlenen yok.");
        Assert.DoesNotContain("duzenlenen", required);
        Assert.Contains("karar", required);
        Assert.Contains("gerekce", required);
    }
}
