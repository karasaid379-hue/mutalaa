using Microsoft.OpenApi;

namespace Mutalaa.Api.Hosting;

public static class OpenApiSetup
{
    /// <summary>
    /// OpenAPI 3.1 belgesi "v1". <c>servers</c> temizlenir: belge ortamdan ve adresten bagimsiz, belirlenimci olur
    /// (derlemede uretilen server/Mutalaa.Api/openapi/v1.json bayt bayt ayni).
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
                return Task.CompletedTask;
            });
        });
        return services;
    }

    /// <summary>Belge uretimi (dotnet getdocument / GetDocument.Insider) uygulamayi baslatir; veritabani ve arka plan isleri atlanir.</summary>
    public static bool IsDocumentGeneration() =>
        string.Equals(System.Reflection.Assembly.GetEntryAssembly()?.GetName().Name, "GetDocument.Insider", StringComparison.Ordinal);
}
