using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>upload --flavor f [--surum s] [--out klasor]: dogrulandi yayini depoya yukler (tekrar calistirilabilir).</summary>
public sealed class UploadCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string> surum = new("--surum") { Description = "Yuklenecek yayin surumu; verilmezse en son acik yayin." };
        Option<string> output = new("--out") { Description = "Cikti kok klasoru (varsayilan Publisher:OutDir)." };

        Command command = new("upload", "Uretilmis (dogrulandi) yayini depoya yukler.");
        command.Options.Add(flavor);
        command.Options.Add(surum);
        command.Options.Add(output);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new UploadRequest(CommandSupport.ParseFlavor(parse.GetValue(flavor)), parse.GetValue(surum), parse.GetValue(output)),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(UploadRequest request, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(context, useLock: true, ct => new ReleasePipeline(context).UploadAsync(request, ct), cancellationToken);
}
