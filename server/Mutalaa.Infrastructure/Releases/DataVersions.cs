using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Text.RegularExpressions;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// data_version = {YYYY.MM.DD}-{git kisa sha}; git yoksa ya da calisma dizini depo degilse "nogit" (Yayin sureci: Etiket ve ust veri).
/// Saat <see cref="TimeProvider"/> ile verilir; git kisa sha'si enjekte edilebilir (testler).
/// </summary>
public static partial class DataVersions
{
    public const string NoGit = "nogit";

    [GeneratedRegex("^[0-9a-f]{4,40}$", RegexOptions.CultureInvariant)]
    private static partial Regex ShaPattern();

    /// <summary>Bugunun (UTC) tarihi ve git kisa sha'siyla data_version; <paramref name="shortSha"/> null ise <see cref="ShortShaAsync"/>.</summary>
    public static async Task<string> CurrentAsync(
        TimeProvider clock,
        Func<CancellationToken, Task<string>>? shortSha,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(clock);

        string sha = shortSha is null ? await ShortShaAsync(cancellationToken) : await shortSha(cancellationToken);
        return Format(clock.GetUtcNow(), sha);
    }

    public static string Format(DateTimeOffset now, string shortSha) =>
        string.Create(CultureInfo.InvariantCulture, $"{now.UtcDateTime:yyyy.MM.dd}-{shortSha}");

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
