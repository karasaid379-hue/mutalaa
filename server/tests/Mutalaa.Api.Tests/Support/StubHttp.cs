namespace Mutalaa.Api.Tests.Support;

/// <summary>Sahte HTTP iletisi isleyicisi: her istegi sayar ve verilen islevle yanitlar (ag kullanilmaz).</summary>
internal sealed class StubHandler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> respond) : HttpMessageHandler
{
    private int _calls;

    public int Calls => Volatile.Read(ref _calls);

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Interlocked.Increment(ref _calls);
        return respond(request, cancellationToken);
    }
}

/// <summary>Her adli istemciyi ayni sahte isleyiciye baglar.</summary>
internal sealed class StubClientFactory(HttpMessageHandler handler) : IHttpClientFactory
{
    public HttpClient CreateClient(string name) => new(handler, disposeHandler: false);
}
