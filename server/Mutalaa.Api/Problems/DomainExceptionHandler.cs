using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Mutalaa.Domain;

namespace Mutalaa.Api.Problems;

/// <summary>
/// Domain kural ihlallerini (<see cref="DomainException"/>) ProblemDetails'e cevirir (K-48): kod HTTP durumuna burada eslenir,
/// Domain HTTP bilmez. <see cref="ApiExceptionHandler"/>'dan once kayitlanir; tanimsiz kod icin false doner ve istisna 500 olur.
/// Mesajlar Domain'in sabit Turkce'siz metinleridir (kullanici verisi, e-posta ya da baglanti ayrintisi icermez).
/// </summary>
public sealed class DomainExceptionHandler(IProblemDetailsService problemDetails) : IExceptionHandler
{
    /// <summary>Domain hata kodunun HTTP durumu (Backend API 6, K-48); tanimsiz kod false.</summary>
    public static bool TryGetStatus(string code, out int status)
    {
        switch (code)
        {
            case DomainErrorCodes.Dogrulama:
                status = StatusCodes.Status400BadRequest;
                return true;
            case DomainErrorCodes.Bulunamadi:
                status = StatusCodes.Status404NotFound;
                return true;
            case DomainErrorCodes.DurumGecisiGecersiz:
                status = StatusCodes.Status409Conflict;
                return true;
            case DomainErrorCodes.SurumUyusmazligi:
                status = StatusCodes.Status412PreconditionFailed;
                return true;
            case DomainErrorCodes.DegistirilemezMetin:
            case DomainErrorCodes.IncelemeDesteklenmiyor:
            case DomainErrorCodes.TopluUygunDegil:
                status = StatusCodes.Status422UnprocessableEntity;
                return true;
            default:
                status = 0;
                return false;
        }
    }

    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(httpContext);
        ArgumentNullException.ThrowIfNull(exception);

        if (exception is not DomainException domain || !TryGetStatus(domain.Code, out int status))
        {
            return false;
        }

        httpContext.Response.StatusCode = status;
        ProblemDetails problem = new() { Status = status, Detail = domain.Message };
        problem.Extensions[ProblemCodes.ExtensionKey] = domain.Code;
        return await problemDetails.TryWriteAsync(new ProblemDetailsContext { HttpContext = httpContext, ProblemDetails = problem, Exception = exception });
    }
}
