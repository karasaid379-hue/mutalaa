using Microsoft.Extensions.Logging;

namespace Mutalaa.Api.Tests.Support;

/// <summary>Gunluk iletilerini (ve istisna metinlerini) toplar; gizli deger sizintisi testleri icin.</summary>
internal sealed class CapturingLoggerProvider : ILoggerProvider
{
    private readonly List<string> _messages = [];

    public IReadOnlyList<string> Messages
    {
        get
        {
            lock (_messages)
            {
                return [.. _messages];
            }
        }
    }

    public string Text => string.Join('\n', Messages);

    public ILogger CreateLogger(string categoryName) => new CapturingLogger(_messages);

    public void Dispose()
    {
    }

    private sealed class CapturingLogger(List<string> messages) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            lock (messages)
            {
                messages.Add(formatter(state, exception));
                if (exception is not null)
                {
                    messages.Add(exception.ToString());
                }
            }
        }
    }
}
