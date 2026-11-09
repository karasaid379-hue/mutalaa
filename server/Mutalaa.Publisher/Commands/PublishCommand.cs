using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>publish --flavor f [--pack id]... [--dry-run] [--version YYYY.M.N]: kapi, paketler, imzali manifest ve yukleme (Backend API 10.1).</summary>
public sealed class PublishCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string[]> packs = CommandSupport.PackOption();
        Option<bool> dryRun = new("--dry-run") { Description = "Yalniz kapi raporu; release satiri ve depo yazilmaz." };
        Option<string> version = new("--version") { Description = "Yayin surumu (YYYY.M.N); verilmezse ayin siradaki numarasi." };

        Command command = new("publish", "Derleme, imza ve yukleme tek adimda.");
        command.Options.Add(flavor);
        command.Options.Add(packs);
        command.Options.Add(dryRun);
        command.Options.Add(version);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new PublishRequest(
                CommandSupport.ParseFlavor(parse.GetValue(flavor)),
                parse.GetValue(packs) ?? [],
                parse.GetValue(dryRun),
                parse.GetValue(version)),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(PublishRequest request, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(
            context,
            useLock: !request.DryRun,
            ct => new ReleasePipeline(context).PublishAsync(request, ct),
            cancellationToken);
}
