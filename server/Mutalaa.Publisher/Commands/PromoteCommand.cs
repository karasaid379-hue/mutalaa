using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>promote [--from internal] [--to public] [--surum s] [--dry-run]: yayinlandi internal yayini ayni surumle public icin uretir (P-14).</summary>
public sealed class PromoteCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> from = new("--from") { Description = "Kaynak derleme turu (yalniz internal).", DefaultValueFactory = _ => "internal" };
        from.AcceptOnlyFromAmong("internal");
        Option<string> to = new("--to") { Description = "Hedef derleme turu (yalniz public).", DefaultValueFactory = _ => "public" };
        to.AcceptOnlyFromAmong("public");
        Option<string> surum = new("--surum") { Description = "Terfi edilecek internal yayin surumu; verilmezse en son yayinlandi olan." };
        Option<string[]> packs = CommandSupport.PackOption();
        Option<bool> dryRun = new("--dry-run") { Description = "Yalniz kapi ve P-14 raporu; release satiri ve depo yazilmaz." };
        Option<string> output = new("--out") { Description = "Cikti kok klasoru (varsayilan Publisher:OutDir)." };

        Command command = new("promote", "Ic kanalda test edilen yayini public icin uretir ve yukler (yalniz kullanici karariyla).");
        command.Options.Add(from);
        command.Options.Add(to);
        command.Options.Add(surum);
        command.Options.Add(packs);
        command.Options.Add(dryRun);
        command.Options.Add(output);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new PromoteRequest(parse.GetValue(surum), parse.GetValue(packs) ?? [], parse.GetValue(dryRun), parse.GetValue(output)),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(PromoteRequest request, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(context, useLock: !request.DryRun, ct => new ReleasePipeline(context).PromoteAsync(request, ct), cancellationToken);
}
