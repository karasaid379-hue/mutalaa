using System.Diagnostics;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;

namespace Mutalaa.Api.Problems;

public static class ProblemDetailsSetup
{
    /// <summary>
    /// AddProblemDetails + CustomizeProblemDetails: <c>type = urn:mutalaa:problem:{kod}</c>, <c>kod</c> ve <c>traceId</c> uzantilari.
    /// Kod once uzantidan (uc verdiyse), yoksa HTTP durumundan gelir.
    /// </summary>
    public static IServiceCollection AddApiProblemDetails(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.AddProblemDetails(options => options.CustomizeProblemDetails = Customize);
        return services;
    }

    internal static void Customize(ProblemDetailsContext context)
    {
        ProblemDetails problem = context.ProblemDetails;
        int status = problem.Status ?? context.HttpContext.Response.StatusCode;
        problem.Status = status;

        string code = problem.Extensions.TryGetValue(ProblemCodes.ExtensionKey, out object? given) && given is string text && text.Length > 0
            ? text
            : ProblemCodes.ForStatus(status);

        problem.Type = ProblemCodes.TypeUri(code);
        problem.Title = ProblemCodes.TitleForStatus(status) ?? problem.Title;
        problem.Extensions[ProblemCodes.ExtensionKey] = code;

        // Dogrulama hatalarinin alan adlari JSON adlari gibi snake_case olur (istemci form alanina esler).
        if (problem is HttpValidationProblemDetails validation && validation.Errors.Count > 0)
        {
            Dictionary<string, string[]> renamed = new(StringComparer.Ordinal);
            foreach ((string field, string[] messages) in validation.Errors)
            {
                renamed[JsonNamingPolicy.SnakeCaseLower.ConvertName(field)] = messages;
            }

            validation.Errors = renamed;
        }

        // Varsayilan yazici JSON adlandirma ilkesiyle "trace_id" ekleyebilir; belgedeki ad "traceId"dir ve tek olmalidir.
        problem.Extensions.Remove("trace_id");
        problem.Extensions["traceId"] = Activity.Current?.Id ?? context.HttpContext.TraceIdentifier;
    }
}
