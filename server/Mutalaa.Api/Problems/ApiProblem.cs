using Microsoft.AspNetCore.Mvc;

namespace Mutalaa.Api.Problems;

/// <summary>
/// Uclarin hata donusu. Govde IProblemDetailsService uzerinden yazilir (CustomizeProblemDetails: type, kod, traceId);
/// TypedResults.Problem bu hattan gecmedigi icin kullanilmaz.
/// </summary>
public static class ApiProblem
{
    public static IResult Create(int status, string code, string? detail = null, IReadOnlyDictionary<string, object?>? extensions = null)
    {
        ProblemDetails problem = new() { Status = status, Detail = detail };
        problem.Extensions[ProblemCodes.ExtensionKey] = code;
        if (extensions is not null)
        {
            foreach ((string key, object? value) in extensions)
            {
                problem.Extensions[key] = value;
            }
        }

        return new ProblemResult(problem);
    }

    /// <summary>400 dogrulama; <c>errors</c> alani HttpValidationProblemDetails ile ayni biciminde.</summary>
    public static IResult Validation(IDictionary<string, string[]> errors, string? detail = null)
    {
        HttpValidationProblemDetails problem = new(errors) { Status = StatusCodes.Status400BadRequest, Detail = detail };
        problem.Extensions[ProblemCodes.ExtensionKey] = ProblemCodes.Dogrulama;
        return new ProblemResult(problem);
    }

    private sealed class ProblemResult(ProblemDetails problem) : IResult
    {
        public async Task ExecuteAsync(HttpContext httpContext)
        {
            ArgumentNullException.ThrowIfNull(httpContext);

            int status = problem.Status ?? StatusCodes.Status500InternalServerError;
            httpContext.Response.StatusCode = status;
            IProblemDetailsService service = httpContext.RequestServices.GetRequiredService<IProblemDetailsService>();

            // Istemci JSON kabul etmiyorsa (Accept) govde yazilmaz; durum kodu yeterlidir.
            await service.TryWriteAsync(new ProblemDetailsContext { HttpContext = httpContext, ProblemDetails = problem });
        }
    }
}
