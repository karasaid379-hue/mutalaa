using System.CommandLine;
using System.Globalization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Commands;

namespace Mutalaa.Publisher;

/// <summary>
/// Yayinlayici giris noktasi (Backend API 10.1). Ana bilgisayar <c>Host.CreateApplicationBuilder</c> ile ve <c>Args = null</c> ile kurulur
/// (komut argumanlari yapilandirmaya verilmez; yoksa --flavor yapilandirma anahtari sanilirdi). Kullanici sirlari yalniz Development ortaminda
/// yuklenir. appsettings.json cikti klasorunden okunur, goreli yollar calisma dizinine gore cozulur. Testler <see cref="RunAsync"/> ile
/// islem disinda cagirir; <see cref="PublisherHostOptions"/> yapilandirma, depo, saat ve cikti yazicilarini enjekte eder.
/// </summary>
public static class PublisherApp
{
    public static async Task<int> RunAsync(string[] args, PublisherHostOptions? options = null, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(args);

        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;

        PublisherHostOptions host = options ?? new PublisherHostOptions();
        TextWriter error = host.Error ?? Console.Error;

        try
        {
            HostApplicationBuilderSettings settings = new()
            {
                Args = null,
                ContentRootPath = AppContext.BaseDirectory,
            };
            if (!string.IsNullOrWhiteSpace(host.EnvironmentName))
            {
                settings.EnvironmentName = host.EnvironmentName;
            }

            HostApplicationBuilder builder = Host.CreateApplicationBuilder(settings);
            builder.Logging.SetMinimumLevel(LogLevel.Warning);
            if (host.Configuration.Count > 0)
            {
                builder.Configuration.AddInMemoryCollection(host.Configuration);
            }

            builder.Services.AddIcerikDb(builder.Configuration);
            builder.Services.AddSingleton(provider =>
                new ReleaseRepository(provider.GetRequiredService<IServiceScopeFactory>(), host.Clock));
            builder.Services.AddSingleton(provider =>
                new PublisherContext(provider.GetRequiredService<IConfiguration>(), provider.GetRequiredService<ReleaseRepository>(), host));

            using IHost app = builder.Build();
            await using PublisherContext context = app.Services.GetRequiredService<PublisherContext>();
            return await InvokeAsync(args, context, host, cancellationToken);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // Ana bilgisayar kurulamadi (yapilandirma/DI): ileti yazilir, gizli deger yazilmaz.
            error.WriteLine($"Yayinlayici baslatilamadi: {ex.GetType().Name}: {ex.Message}");
            return ExitCodes.Other;
        }
    }

    /// <summary>Komut agacini kurar (testler ayristirma icin kullanir).</summary>
    public static RootCommand BuildRootCommand(PublisherContext context)
    {
        ArgumentNullException.ThrowIfNull(context);

        RootCommand root = new("Mutalaa Yayinlayici: icerik paketlerini uretir, imzalar, yayimlar ve dogrular.");
        root.Subcommands.Add(new PublishCommand(context).Create());
        root.Subcommands.Add(new BuildCommand(context).Create());
        root.Subcommands.Add(new UploadCommand(context).Create());
        root.Subcommands.Add(new VerifyCommand(context).Create());
        root.Subcommands.Add(new PromoteCommand(context).Create());
        root.Subcommands.Add(new RollbackCommand(context).Create());
        root.Subcommands.Add(new WatchCommand(context).Create());
        root.Subcommands.Add(new KeysCommand(context).Create());
        return root;
    }

    private static async Task<int> InvokeAsync(string[] args, PublisherContext context, PublisherHostOptions host, CancellationToken cancellationToken)
    {
        RootCommand root = BuildRootCommand(context);
        ParseResult parse = root.Parse(args);
        InvocationConfiguration configuration = new()
        {
            Output = host.Out ?? Console.Out,
            Error = host.Error ?? Console.Error,
            EnableDefaultExceptionHandler = false,
        };

        try
        {
            int code = await parse.InvokeAsync(configuration, cancellationToken);
            // Ayristirma hatasi ve yardim disindaki her kod komutun kendi kodudur; ayristirma hatasi System.CommandLine'da 1'dir.
            return code;
        }
        catch (Exception ex)
        {
            return CommandSupport.HandleException(context, ex);
        }
    }
}
