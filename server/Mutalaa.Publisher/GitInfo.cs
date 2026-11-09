using System.ComponentModel;
using System.Diagnostics;
using System.Text.RegularExpressions;

namespace Mutalaa.Publisher;

/// <summary>data_version = {YYYY.MM.DD}-{git kisa sha}; git yoksa ya da depo degilse "nogit" (plan: Etiket ve ust veri).</summary>
public static partial class GitInfo
{
    public const string NoGit = "nogit";

    [GeneratedRegex("^[0-9a-f]{4,40}$", RegexOptions.CultureInvariant)]
    private static partial Regex ShaPattern();

    public static async Task<string> ShortShaAsync(CancellationToken cancellationToken)
    {
        try
        {
            ProcessStartInfo info = new("git")
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            info.ArgumentList.Add("rev-parse");
            info.ArgumentList.Add("--short");
            info.ArgumentList.Add("HEAD");

            using Process? process = Process.Start(info);
            if (process is null)
            {
                return NoGit;
            }

            using CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(10));
            Task<string> output = process.StandardOutput.ReadToEndAsync(timeout.Token);
            await process.WaitForExitAsync(timeout.Token);
            string sha = (await output).Trim();
            return process.ExitCode == 0 && ShaPattern().IsMatch(sha) ? sha : NoGit;
        }
        catch (Exception ex) when (ex is Win32Exception or InvalidOperationException or IOException)
        {
            return NoGit;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return NoGit;
        }
    }
}
