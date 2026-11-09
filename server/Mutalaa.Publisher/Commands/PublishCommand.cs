using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>publish --flavor f [--pack id]... [--dry-run] [--version YYYY.M.N] [--restart]: kapi, paketler, imzali manifest ve yukleme (Backend API 10.1).</summary>
public sealed class PublishCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string[]> packs = CommandSupport.PackOption();
        Option<bool> dryRun = new("--dry-run") { Description = "Yalniz kapi raporu; release satiri ve depo yazilmaz." };
        Option<string> version = new("--version") { Description = "Yayin surumu (YYYY.M.N); verilmezse ayin siradaki numarasi." };
        Option<bool> restart = new("--restart")
        {
            Description = "Acik 'dogrulandi' yayin satirini basarisiz yapar ve ayni surumle bastan derleyip yukler (yerel cikti kaybolduysa ya da depoyla tutarsizsa). Surum depoda canli manifestte ya da manifests/ gecmisinde gorunuyorsa reddedilir (cikis 1; upload ile tamamlayin); depo denetlenemezse satira dokunulmaz (cikis 4).",
        };

        Command command = new("publish", "Derleme, imza ve yukleme tek adimda.");
        command.Options.Add(flavor);
        command.Options.Add(packs);
        command.Options.Add(dryRun);
        command.Options.Add(version);
        command.Options.Add(restart);
        command.Validators.Add(result =>
        {
            if (result.GetValue(restart) && result.GetValue(dryRun))
            {
                result.AddError(ReleasePipeline.RestartWithDryRunMessage);
            }
        });
        command.SetAction((parse, cancellationToken) => RunAsync(
            new PublishRequest(
                CommandSupport.ParseFlavor(parse.GetValue(flavor)),
                parse.GetValue(packs) ?? [],
                parse.GetValue(dryRun),
                parse.GetValue(version),
                Restart: parse.GetValue(restart)),
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
