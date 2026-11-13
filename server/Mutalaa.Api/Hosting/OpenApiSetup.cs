using Microsoft.OpenApi;

namespace Mutalaa.Api.Hosting;

public static class OpenApiSetup
{
    private const string ProblemDetailsId = "ProblemDetails";
    private const string ValidationProblemDetailsId = "ValidationProblemDetails";
    private const string ProblemMediaType = "application/problem+json";

    /// <summary>
    /// OpenAPI 3.1 belgesi "v1". <c>servers</c> temizlenir: belge ortamdan ve adresten bagimsiz, belirlenimci olur
    /// (derlemede uretilen server/Mutalaa.Api/openapi/v1.json bayt bayt ayni). Belge donusturucusu hata ve limit semalarini
    /// gercek govdeye uydurur (<see cref="DescribeProblemsAndLimits"/>).
    /// </summary>
    public static IServiceCollection AddApiOpenApi(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.AddOpenApi("v1", options =>
        {
            options.OpenApiVersion = OpenApiSpecVersion.OpenApi3_1;
            options.AddDocumentTransformer((document, _, _) =>
            {
                document.Servers = [];
                DescribeProblemsAndLimits(document);
                return Task.CompletedTask;
            });
        });
        return services;
    }

    /// <summary>
    /// (1) <c>ProblemDetails</c> gercek govdeyi anlatir: <c>kod</c> ve <c>traceId</c> her yanitta, ucun tipli uzantilari
    /// (<c>kapi_raporu</c>, <c>yayin</c>, <c>kimlikler</c>, <c>kimlik</c>, <c>hatalar</c>) yalniz ilgili yanitta bulunur; ek alan serbesttir.
    /// (2) Her 400 problem yaniti <c>ValidationProblemDetails</c> kullanir (<c>errors</c>: alan -> iletiler; alan dogrulamasinda dolu).
    /// (3) <c>limit</c> sorgu parametresi 1..200 tam sayidir (gecersiz deger yine 400 dogrulama).
    /// </summary>
    internal static void DescribeProblemsAndLimits(OpenApiDocument document)
    {
        document.Components ??= new OpenApiComponents();
        document.Components.Schemas ??= new Dictionary<string, IOpenApiSchema>(StringComparer.Ordinal);

        document.Components.Schemas[ProblemDetailsId] = ProblemDetailsSchema();
        document.Components.Schemas[ValidationProblemDetailsId] = new OpenApiSchema
        {
            Description = "400 dogrulama yaniti. errors yalniz alan dogrulamasinda dolu olur (alan adi snake_case; ic ice alan 'duzenlenen.metin' "
                + "ve liste ogesi 'kararlar[0].gerekce' gibi yazilir); basliklar ve bozuk JSON gibi alansiz 400'lerde yoktur.",
            AllOf = [new OpenApiSchemaReference(ProblemDetailsId, document)],
            Properties = new Dictionary<string, IOpenApiSchema>(StringComparer.Ordinal)
            {
                ["errors"] = new OpenApiSchema
                {
                    Type = JsonSchemaType.Object,
                    Description = "Alan adi -> iletiler.",
                    AdditionalProperties = new OpenApiSchema
                    {
                        Type = JsonSchemaType.Array,
                        Items = new OpenApiSchema { Type = JsonSchemaType.String },
                    },
                },
            },
        };

        if (document.Paths is null)
        {
            return;
        }

        foreach (IOpenApiPathItem path in document.Paths.Values)
        {
            if (path.Operations is null)
            {
                continue;
            }

            foreach (OpenApiOperation operation in path.Operations.Values)
            {
                PointBadRequestAtValidation(operation, document);
                NarrowLimit(operation);
            }
        }
    }

    private static void PointBadRequestAtValidation(OpenApiOperation operation, OpenApiDocument document)
    {
        if (operation.Responses is null
            || !operation.Responses.TryGetValue("400", out IOpenApiResponse? response)
            || response.Content is null
            || !response.Content.TryGetValue(ProblemMediaType, out OpenApiMediaType? media))
        {
            return;
        }

        media.Schema = new OpenApiSchemaReference(ValidationProblemDetailsId, document);
    }

    private static void NarrowLimit(OpenApiOperation operation)
    {
        if (operation.Parameters is null)
        {
            return;
        }

        foreach (IOpenApiParameter parameter in operation.Parameters)
        {
            if (parameter is OpenApiParameter { In: ParameterLocation.Query } query && string.Equals(query.Name, "limit", StringComparison.Ordinal))
            {
                query.Schema = new OpenApiSchema
                {
                    Type = JsonSchemaType.Integer,
                    Format = "int32",
                    Minimum = "1",
                    Maximum = "200",
                };
            }
        }
    }

    private static OpenApiSchema ProblemDetailsSchema() => new()
    {
        Type = JsonSchemaType.Object,
        Description = "RFC 9457 hata govdesi. type her zaman 'urn:mutalaa:problem:{kod}'; kod ve traceId her yanitta bulunur. "
            + "Ucun tipli uzantilari yalniz ilgili yanitta gelir; tanimsiz ek alanlar da olabilir.",
        AdditionalProperties = new OpenApiSchema(), // bos sema: her ek alan serbest (additionalProperties true)
        Properties = new Dictionary<string, IOpenApiSchema>(StringComparer.Ordinal)
        {
            ["type"] = new OpenApiSchema { Type = JsonSchemaType.String },
            ["title"] = new OpenApiSchema { Type = JsonSchemaType.String },
            ["status"] = new OpenApiSchema { Type = JsonSchemaType.Integer, Format = "int32" },
            ["detail"] = new OpenApiSchema { Type = JsonSchemaType.String },
            ["instance"] = new OpenApiSchema { Type = JsonSchemaType.String },
            ["kod"] = new OpenApiSchema
            {
                Type = JsonSchemaType.String,
                Description = "Makine tarafindan okunur hata kodu (type son parcasiyla ayni): dogrulama, capa-gecersiz, degistirilemez-metin, "
                    + "oturum-acilamadi, yetki-yok, bulunamadi, yontem-desteklenmiyor, durum-gecisi-gecersiz, cakisma, surum-uyusmazligi, "
                    + "surum-gerekli, inceleme-desteklenmiyor, toplu-uygun-degil, yayin-suruyor, kalite-kapisi, onceki-yayin-bozuk, depo-erisilemiyor, hata, sunucu-hatasi.",
            },
            ["traceId"] = new OpenApiSchema { Type = JsonSchemaType.String, Description = "Istek izleme kimligi (gunluk iliskilendirme)." },
            ["kapi_raporu"] = new OpenApiSchema
            {
                Type = JsonSchemaType.Object,
                Description = "kalite-kapisi (422): kapi raporu (GateReport JSON'u).",
                AdditionalProperties = new OpenApiSchema(), // bos sema: her ek alan serbest (additionalProperties true)
            },
            ["yayin"] = new OpenApiSchema
            {
                Type = JsonSchemaType.Object,
                Description = "yayin-suruyor (409): derleme turunde acik olan yayin satiri {id, surum, derleme, durum, talep}.",
                AdditionalProperties = new OpenApiSchema(), // bos sema: her ek alan serbest (additionalProperties true)
            },
            ["kimlikler"] = new OpenApiSchema
            {
                Type = JsonSchemaType.Array,
                Items = new OpenApiSchema { Type = JsonSchemaType.Integer, Format = "int64" },
                Description = "Toplu karar: bulunamayan (404) ya da surumu tutmayan (412) inceleme kayitlarinin tam listesi.",
            },
            ["kimlik"] = new OpenApiSchema
            {
                Type = JsonSchemaType.Integer,
                Format = "int64",
                Description = "Toplu karar: hataya yol acan inceleme kaydi (400, 409, 422).",
            },
            ["hatalar"] = new OpenApiSchema
            {
                Type = JsonSchemaType.Array,
                Items = new OpenApiSchema
                {
                    Type = JsonSchemaType.Object,
                    Properties = new Dictionary<string, IOpenApiSchema>(StringComparer.Ordinal)
                    {
                        ["kod"] = new OpenApiSchema { Type = JsonSchemaType.String },
                        ["aciklama"] = new OpenApiSchema { Type = JsonSchemaType.String },
                    },
                },
                Description = "Kullanici olusturma (400): Identity hata kodlari ve aciklamalari.",
            },
        },
    };

    /// <summary>Belge uretimi (dotnet getdocument / GetDocument.Insider) uygulamayi baslatir; veritabani ve arka plan isleri atlanir.</summary>
    public static bool IsDocumentGeneration() =>
        string.Equals(System.Reflection.Assembly.GetEntryAssembly()?.GetName().Name, "GetDocument.Insider", StringComparison.Ordinal);
}
