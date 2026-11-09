using System.CommandLine;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>verify --flavor f [--manifest yol] [--embedded-core yol] [--public-key base64]: imza, sema, adres, sha256 ve kapi kurallari. Veritabani gerekmez.</summary>
public sealed class VerifyCommand(PublisherContext context)
{
    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<string> manifest = new("--manifest") { Description = "Manifest dosyasi; verilmezse depodan {flavor}/manifest.json okunur." };
        Option<string> core = new("--embedded-core") { Description = "Gomulu core paket dosyasi; sha256 degeri manifestteki ya da gecmisteki core ile ayni olmali." };
        Option<string> key = new("--public-key") { Description = "Acik anahtar (base64, 32 bayt); verilmezse Signing:{flavor}:PublicKey." };

        Command command = new("verify", "Imza, sema, adres, boyut, sha256 ve kapi kurallarini yeniden denetler.");
        command.Options.Add(flavor);
        command.Options.Add(manifest);
        command.Options.Add(core);
        command.Options.Add(key);
        command.SetAction((parse, cancellationToken) => RunAsync(
            new VerifyRequest(CommandSupport.ParseFlavor(parse.GetValue(flavor)), parse.GetValue(manifest), parse.GetValue(core), parse.GetValue(key)),
            cancellationToken));
        return command;
    }

    public Task<int> RunAsync(VerifyRequest request, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(context, useLock: false, ct => new ReleaseVerifier(context).VerifyAsync(request, ct), cancellationToken);
}
