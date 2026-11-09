using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>build --flavor f [--out klasor] [--pack id]... [--version v]: dogrulandi'da durur, depoya yuklemez.</summary>
public sealed class BuildCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string[]> packs = CommandSupport.PackOption();
        Option<string> version = new("--version") { Description = "Yayin surumu (YYYY.M.N); verilmezse ayin siradaki numarasi." };
        Option<string> output = new("--out") { Description = "Cikti kok klasoru (varsayilan Publisher:OutDir); {flavor}/{surum}/ altina yazilir." };

        Command command = new("build", "Kapi, paketler, sha256 ve imzali manifest; yukleme yapmaz.");
        command.Options.Add(flavor);
        command.Options.Add(packs);
        command.Options.Add(version);
        command.Options.Add(output);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new PublishRequest(
                CommandSupport.ParseFlavor(parse.GetValue(flavor)),
                parse.GetValue(packs) ?? [],
                DryRun: false,
                Version: parse.GetValue(version),
                OutDir: parse.GetValue(output),
                StopAtVerified: true),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(PublishRequest request, CancellationToken cancellationToken)
    {
        PublishRequest build = request with { StopAtVerified = true, DryRun = false };
        return CommandSupport.ExecuteAsync(context, useLock: true, ct => new ReleasePipeline(context).PublishAsync(build, ct), cancellationToken);
    }
}
