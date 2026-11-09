using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using Mutalaa.Domain.Releases;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>Dosya yardimcilari: UTF-8 (BOM'suz), OneDrive/Windows kilidi icin yeniden denemeli yazma ve sha256.</summary>
internal static class Files
{
    private const int Attempts = 3;
    private static readonly TimeSpan Delay = TimeSpan.FromMilliseconds(200);

    public static string Inv(FormattableString value) => value.ToString(CultureInfo.InvariantCulture);

    public static string LocalPackPath(string outRoot, string flavor, string packId, string version)
    {
        RequirePackId(packId);
        RequireVersion(version);
        return Path.Combine(outRoot, flavor, version, $"{packId}-{version}.db");
    }

    public static string ReleaseDir(string outRoot, string flavor, string surum)
    {
        RequireVersion(surum);
        return Path.Combine(outRoot, flavor, surum);
    }

    /// <summary>manifest.schema.json packId deseni: kucuk harfle baslar; kucuk harf, rakam ve tire (yalniz ASCII).</summary>
    public static bool IsValidPackId(string? value)
    {
        if (string.IsNullOrEmpty(value) || value[0] is < 'a' or > 'z')
        {
            return false;
        }

        return value.All(c => c is (>= 'a' and <= 'z') or (>= '0' and <= '9') or '-');
    }

    /// <summary>CalVer YYYY.M.N (ReleaseVersion.TryParse; egik cizgi, nokta-nokta ve ASCII disi rakam gecmez).</summary>
    public static bool IsValidVersion(string? value) => ReleaseVersion.TryParse(value, out _);

    // Veritabani ya da manifestten gelen deger dosya yoluna girmeden once denetlenir (OutDir disina yazma imkansiz; CLAUDE.md kural 1).
    // Girdi hatasidir ve yeniden denemeyle duzelmez.
    public static void RequireVersion(string value)
    {
        if (!IsValidVersion(value))
        {
            throw new PublisherException(ExitCodes.Other, "Gecersiz surum (CalVer YYYY.M.N bekleniyor); dosya yolu olusturulmadi.", isPermanent: true);
        }
    }

    private static void RequirePackId(string value)
    {
        if (!IsValidPackId(value))
        {
            throw new PublisherException(ExitCodes.Other, "Gecersiz paket kimligi; dosya yolu olusturulmadi.", isPermanent: true);
        }
    }

    public static async Task WriteTextAsync(string path, string text, CancellationToken cancellationToken) =>
        await WriteBytesAsync(path, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetBytes(text), cancellationToken);

    public static async Task WriteBytesAsync(string path, byte[] bytes, CancellationToken cancellationToken)
    {
        string? directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        for (int attempt = 1; ; attempt++)
        {
            try
            {
                await File.WriteAllBytesAsync(path, bytes, cancellationToken);
                return;
            }
            catch (IOException) when (attempt < Attempts)
            {
                await Task.Delay(Delay, cancellationToken);
            }
        }
    }

    public static async Task<string> Sha256Async(string path, CancellationToken cancellationToken)
    {
        await using FileStream stream = new(path, FileMode.Open, FileAccess.Read, FileShare.Read, 81920, useAsync: true);
        return Convert.ToHexStringLower(await SHA256.HashDataAsync(stream, cancellationToken));
    }

    public static string Sha256(ReadOnlySpan<byte> data) => Convert.ToHexStringLower(SHA256.HashData(data));
}
