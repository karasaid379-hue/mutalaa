using System.CommandLine;
using System.Globalization;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>watch [--interval sn] [--once]: API'nin hazirlaniyor biraktigi talepleri sirayla isler (yayin, terfi, geri_alma).</summary>
public sealed class WatchCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<int> interval = new("--interval") { Description = "Yoklama araligi (saniye).", DefaultValueFactory = _ => 5 };
        Option<bool> once = new("--once") { Description = "Tek tur: bekleyen talepleri isle ve cik." };

        Command command = new("watch", "Bekleyen yayin taleplerini isler.");
        command.Options.Add(interval);
        command.Options.Add(once);
        command.SetAction((parse, cancellationToken) => RunAsync(parse.GetValue(interval), parse.GetValue(once), cancellationToken));
        return command;
    }

    /// <summary>--once: tek tur, ilk sifirdan farkli kodu dondurur. Aksi halde iptale kadar yoklar; kilit alinamazsa tur hata yazar ve sonraki tur denenir.</summary>
    public async Task<int> RunAsync(int intervalSeconds, bool once, CancellationToken cancellationToken)
    {
        if (intervalSeconds < 1)
        {
            context.Error.WriteLine("--interval en az 1 saniye olmali.");
            return ExitCodes.Other;
        }

        while (true)
        {
            int code = await CommandSupport.ExecuteAsync(context, useLock: true, ct => TickAsync(once, ct), cancellationToken);
            if (once)
            {
                return code;
            }

            try
            {
                await Task.Delay(TimeSpan.FromSeconds(intervalSeconds), cancellationToken);
            }
            catch (OperationCanceledException)
            {
                return ExitCodes.Success;
            }
        }
    }

    private async Task<ReleaseResult> TickAsync(bool once, CancellationToken cancellationToken)
    {
        ReleasePipeline pipeline = new(context);
        List<int> attempted = [];
        ReleaseResult? first = null;
        while (true)
        {
            Release? row = await context.Releases.ClaimNextPendingAsync(attempted, cancellationToken);
            if (row is null)
            {
                break;
            }

            attempted.Add(row.Id);
            context.Out.WriteLine(string.Create(CultureInfo.InvariantCulture, $"talep: {row.Talep} {row.Derleme.ToLabel()} {row.Surum} (id {row.Id})"));
            ReleaseResult result;
            try
            {
                result = await pipeline.ProcessRequestAsync(row, cancellationToken);
            }
            catch (PublisherException ex)
            {
                result = ReleaseResult.Fail(ex.ExitCode, ex.Message, row.Surum);
            }
            catch (StorageException ex)
            {
                result = ReleaseResult.Fail(ExitCodes.Storage, string.Create(CultureInfo.InvariantCulture, $"Depo hatasi ({ex.Failure}): {ex.Message}"), row.Surum);
            }

            CommandSupport.Report(context, result);
            if (!result.Success)
            {
                first ??= result;
            }
        }

        if (attempted.Count == 0 && once)
        {
            return ReleaseResult.Ok(null, null, "Bekleyen talep yok.");
        }

        return first ?? ReleaseResult.Ok(null, null, attempted.Count == 0 ? "Bekleyen talep yok." : "Talepler islendi.");
    }
}
