using System.Globalization;
using Serilog;
using Serilog.Events;
using Serilog.Formatting.Compact;

namespace Mutalaa.Api.Hosting;

public static class LoggingSetup
{
    /// <summary>Serilog:Format = Json ise konsol kompakt JSON yazar (konteyner); aksi halde okunur metin (gelistirme).</summary>
    public const string FormatKey = "Serilog:Format";

    /// <summary>
    /// Serilog konsol gunlugu. Statik onyukleme gunlukcusu yoktur; ayarlar Serilog bolumunden okunur. Diger saglayicilar
    /// (writeToProviders) da calisir. Istek gunlugu yolu ve durumu yazar; sorgu dizesi, cerez, e-posta ve govde yazmaz.
    /// </summary>
    public static WebApplicationBuilder AddApiLogging(this WebApplicationBuilder builder)
    {
        ArgumentNullException.ThrowIfNull(builder);

        // Varsayilan konsol saglayicisi kalirsa her satir iki kez yazilir (writeToProviders diger saglayicilara da iletir).
        builder.Logging.ClearProviders();

        builder.Host.UseSerilog(
            (context, services, configuration) =>
            {
                configuration
                    .ReadFrom.Configuration(context.Configuration)
                    .ReadFrom.Services(services)
                    .Enrich.FromLogContext();

                if (string.Equals(context.Configuration[FormatKey], "Json", StringComparison.Ordinal))
                {
                    configuration.WriteTo.Console(new CompactJsonFormatter());
                }
                else
                {
                    configuration.WriteTo.Console(
                        outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {SourceContext} {Message:lj}{NewLine}{Exception}",
                        formatProvider: CultureInfo.InvariantCulture);
                }
            },
            preserveStaticLogger: true,
            writeToProviders: true);
        return builder;
    }

    public static IApplicationBuilder UseApiRequestLogging(this IApplicationBuilder app)
    {
        ArgumentNullException.ThrowIfNull(app);

        // preserveStaticLogger: Log.Logger sessizdir; istek gunlugu dogrudan DI'daki yapilandirilmis gunlukcuyu kullanir.
        return app.UseSerilogRequestLogging(options =>
        {
            options.Logger = app.ApplicationServices.GetRequiredService<Serilog.ILogger>();
            options.GetLevel = (context, _, exception) =>
                exception is not null || context.Response.StatusCode >= StatusCodes.Status500InternalServerError
                    ? LogEventLevel.Error
                    : context.Request.Path.StartsWithSegments("/health", StringComparison.Ordinal)
                        ? LogEventLevel.Verbose
                        : LogEventLevel.Information;
        });
    }
}
