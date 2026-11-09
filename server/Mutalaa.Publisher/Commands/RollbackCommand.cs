using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>rollback --flavor f --to surum: yeni release satiri; hedefin paketleri yeni surumle yeniden imzalanir (talep = geri_alma).</summary>
public sealed class RollbackCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string> to = new("--to") { Description = "Donulecek yayin surumu (YYYY.M.N).", Required = true };
        Option<string> output = new("--out") { Description = "Cikti kok klasoru (varsayilan Publisher:OutDir)." };

        Command command = new("rollback", "Manifesti onceki bir yayina cevirir (yeni yayin satiri olarak).");
        command.Options.Add(flavor);
        command.Options.Add(to);
        command.Options.Add(output);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new RollbackRequest(CommandSupport.ParseFlavor(parse.GetValue(flavor)), parse.GetValue(to)!, parse.GetValue(output)),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(RollbackRequest request, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(context, useLock: true, ct => new ReleasePipeline(context).RollbackAsync(request, ct), cancellationToken);
}
