using System.CommandLine;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;
using Npgsql;

namespace Mutalaa.Publisher.Commands;

/// <summary>Komutlar arasi ortak parcalar: --flavor secenegi, danisma kilidi ve istisna -> cikis kodu esleme.</summary>
public static class CommandSupport
{
    public static readonly string[] FlavorValues = ["dev", "internal", "public"];

    /// <summary>Ortak --flavor secenegi (dev|internal|public). Gecersiz deger ayristirma hatasidir (cikis 1).</summary>
    public static Option<string> FlavorOption(bool required = true)
    {
        Option<string> option = new("--flavor")
        {
            Description = "Derleme turu: dev, internal ya da public.",
            Required = required,
        };
        option.AcceptOnlyFromAmong(FlavorValues);
        return option;
    }

    public static Option<string[]> PackOption() => new("--pack")
    {
        Description = "Yalniz bu paketleri derle (tekrarlanabilir); oteki paketler onceki surumden tasinir.",
        AllowMultipleArgumentsPerToken = false,
    };

    public static BuildFlavor ParseFlavor(string? label) =>
        BuildFlavorLabels.TryParseLabel(label, out BuildFlavor flavor)
            ? flavor
            : throw new PublisherException(ExitCodes.Other, $"Gecersiz derleme turu: {label}");

    /// <summary>
    /// Komut govdesini calistirir: istege bagli danisma kilidi (alinamazsa 1), sonucu yazar, istisnalari cikis koduna cevirir.
    /// Hata iletilerinden bilinen sirlar silinir; ic istisna yigini yazilmaz.
    /// </summary>
    public static async Task<int> ExecuteAsync(PublisherContext context, bool useLock, Func<CancellationToken, Task<ReleaseResult>> action, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(action);

        try
        {
            PublisherLock? held = null;
            if (useLock)
            {
                held = await PublisherLock.TryAcquireAsync(context.ConnectionString, cancellationToken);
                if (held is null)
                {
                    context.Error.WriteLine("Baska bir Yayinlayici calisiyor (danisma kilidi alinamadi).");
                    return ExitCodes.Other;
                }
            }

            await using (held)
            {
                ReleaseResult result = await action(cancellationToken);
                Report(context, result);
                return result.ExitCode;
            }
        }
        catch (Exception ex)
        {
            return HandleException(context, ex);
        }
    }

    public static void Report(PublisherContext context, ReleaseResult result)
    {
        string message = context.Redact(result.Message);
        if (result.Success)
        {
            context.Out.WriteLine(message);
        }
        else
        {
            context.Error.WriteLine(message);
        }
    }

    public static int HandleException(PublisherContext context, Exception exception)
    {
        switch (exception)
        {
            case PublisherException ex:
                context.Error.WriteLine(context.Redact(ex.Message));
                return ex.ExitCode;
            case StorageException ex:
                context.Error.WriteLine(context.Redact($"Depo hatasi ({ex.Failure}): {ex.Message}"));
                return ExitCodes.Storage;
            case OperationCanceledException:
                context.Error.WriteLine("Islem iptal edildi.");
                return ExitCodes.Other;
            case NpgsqlException ex:
                context.Error.WriteLine(context.Redact($"Veritabani hatasi: {ex.GetType().Name}: {ex.Message}"));
                return ExitCodes.Other;
            default:
                context.Error.WriteLine(context.Redact($"Beklenmeyen hata: {exception.GetType().Name}: {exception.Message}"));
                return ExitCodes.Other;
        }
    }
}
