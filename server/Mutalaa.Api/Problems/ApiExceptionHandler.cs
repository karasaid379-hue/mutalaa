using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace Mutalaa.Api.Problems;

/// <summary>
/// Genel hata yakalayici. Eslesme: DbUpdateConcurrencyException 412 (DbUpdateException'dan once), PostgreSQL 23505/23503 409,
/// BadHttpRequestException ve JsonException 400, digerleri 500. Domain hata turu (DomainException) eklendiginde onun yakalayicisi bundan once kayitlanir.
/// Gunluge istisna iletisi yazilmaz (e-posta, baglanti ayrintisi icerebilir); yalniz tur adlari.
/// </summary>
public sealed class ApiExceptionHandler(IProblemDetailsService problemDetails, ILogger<ApiExceptionHandler> logger) : IExceptionHandler
{
    private const string UniqueViolation = "23505";
    private const string ForeignKeyViolation = "23503";

    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(httpContext);
        ArgumentNullException.ThrowIfNull(exception);

        (int status, string code, string detail) = Map(exception);
        if (status >= StatusCodes.Status500InternalServerError)
        {
            logger.LogError("Islenemeyen hata ({ExceptionTypes}); yanit {Status} {Code}.", TypeNames(exception), status, code);
        }

        httpContext.Response.StatusCode = status;
        ProblemDetails problem = new() { Status = status, Detail = detail };
        problem.Extensions[ProblemCodes.ExtensionKey] = code;
        return await problemDetails.TryWriteAsync(new ProblemDetailsContext { HttpContext = httpContext, ProblemDetails = problem, Exception = exception });
    }

    internal static (int Status, string Code, string Detail) Map(Exception exception) => exception switch
    {
        DbUpdateConcurrencyException => (StatusCodes.Status412PreconditionFailed, ProblemCodes.SurumUyusmazligi, "Kayıt siz okuduktan sonra değişti; yenileyip yeniden deneyin."),
        DbUpdateException { InnerException: PostgresException { SqlState: UniqueViolation or ForeignKeyViolation } } =>
            (StatusCodes.Status409Conflict, ProblemCodes.Cakisma, "İşlem mevcut bir kayıtla çakıştı."),
        BadHttpRequestException bad => (bad.StatusCode, ProblemCodes.ForStatus(bad.StatusCode), "İstek gövdesi ya da parametreleri geçersiz."),
        JsonException => (StatusCodes.Status400BadRequest, ProblemCodes.Dogrulama, "İstek gövdesi geçerli bir JSON değil."),
        _ => (StatusCodes.Status500InternalServerError, ProblemCodes.SunucuHatasi, "Beklenmeyen bir hata oluştu."),
    };

    private static string TypeNames(Exception exception)
    {
        List<string> names = [];
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            names.Add(current.GetType().Name);
        }

        return string.Join(" <- ", names);
    }
}
