using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>Dosya yardimcilari: UTF-8 (BOM'suz), OneDrive/Windows kilidi icin yeniden denemeli yazma ve sha256.</summary>
internal static class Files
{
    private const int Attempts = 3;
    private static readonly TimeSpan Delay = TimeSpan.FromMilliseconds(200);

    public static string Inv(FormattableString value) => value.ToString(CultureInfo.InvariantCulture);

    public static string LocalPackPath(string outRoot, string flavor, string packId, string version) =>
        Path.Combine(outRoot, flavor, version, $"{packId}-{version}.db");

    public static string ReleaseDir(string outRoot, string flavor, string surum) => Path.Combine(outRoot, flavor, surum);

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
