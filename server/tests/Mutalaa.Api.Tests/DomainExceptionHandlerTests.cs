using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain;

namespace Mutalaa.Api.Tests;

/// <summary>DomainException kodlarinin HTTP esleme tablosu (K-48); veritabani gerekmez (baglanti kurulmaz).</summary>
public class DomainExceptionHandlerTests
{
    private const string UnusedConnection = "Host=127.0.0.1;Port=1;Username=x;Password=y;Database=z;Timeout=2;Pooling=false";

    public static TheoryData<string, int> Mapping => new()
    {
        { DomainErrorCodes.Dogrulama, 400 },
        { DomainErrorCodes.Bulunamadi, 404 },
        { DomainErrorCodes.DurumGecisiGecersiz, 409 },
        { DomainErrorCodes.SurumUyusmazligi, 412 },
        { DomainErrorCodes.DegistirilemezMetin, 422 },
        { DomainErrorCodes.IncelemeDesteklenmiyor, 422 },
    };

    [Theory]
    [MemberData(nameof(Mapping))]
    public async Task Each_domain_code_is_written_as_a_problem_with_its_status_type_and_trace_id(string code, int status)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using ApiFactory factory = new(UnusedConnection);
        IProblemDetailsService service = factory.Services.GetRequiredService<IProblemDetailsService>();
        DomainExceptionHandler handler = new(service);
        DefaultHttpContext http = new() { RequestServices = factory.Services };
        http.Request.Headers.Accept = "application/json";
        using MemoryStream body = new();
        http.Response.Body = body;

        bool handled = await handler.TryHandleAsync(http, new DomainException(code, "Deneme iletisi."), ct);

        Assert.True(handled);
        Assert.Equal(status, http.Response.StatusCode);
        body.Position = 0;
        using JsonDocument document = await JsonDocument.ParseAsync(body, cancellationToken: ct);
        JsonElement root = document.RootElement;
        Assert.Equal("urn:mutalaa:problem:" + code, root.GetProperty("type").GetString());
        Assert.Equal(code, root.GetProperty("kod").GetString());
        Assert.Equal(status, root.GetProperty("status").GetInt32());
        Assert.False(string.IsNullOrEmpty(root.GetProperty("traceId").GetString()));
    }

    [Fact]
    public async Task Other_exceptions_and_unknown_codes_are_left_to_the_next_handler()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using ApiFactory factory = new(UnusedConnection);
        DomainExceptionHandler handler = new(factory.Services.GetRequiredService<IProblemDetailsService>());
        DefaultHttpContext http = new() { RequestServices = factory.Services };

        Assert.False(await handler.TryHandleAsync(http, new InvalidOperationException("x"), ct));
        Assert.False(await handler.TryHandleAsync(http, new DomainException("bilinmeyen-kod", "x"), ct));
        Assert.False(DomainExceptionHandler.TryGetStatus("bilinmeyen-kod", out _));
    }
}
