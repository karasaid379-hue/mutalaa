using System.Security.Cryptography;
using System.Text;
using Mutalaa.Domain.Releases;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// Paket dosyasi yardimcilari (Yayinlayici ve API ortak): yerel yol kurma, sha256 ve OneDrive/Windows kilidine karsi yeniden denemeli
/// UTF-8 (BOM'suz) yazma. Paket kimligi ve surum dosya yoluna girmeden once denetlenir; gecersizse <see cref="ArgumentException"/>.
/// </summary>
public static class PackFiles
{
    private const int Attempts = 3;
    private static readonly TimeSpan Delay = TimeSpan.FromMilliseconds(200);

    /// <summary>{outRoot}/{flavor}/{version}/{packId}-{version}.db</summary>
    public static string LocalPackPath(string outRoot, string flavor, string packId, string version)
    {
        if (!IsValidPackId(packId))
        {
            throw new ArgumentException("Gecersiz paket kimligi; dosya yolu olusturulmadi.", nameof(packId));
        }

        if (!IsValidVersion(version))
        {
            throw new ArgumentException("Gecersiz surum (CalVer YYYY.M.N bekleniyor); dosya yolu olusturulmadi.", nameof(version));
        }

        return Path.Combine(outRoot, flavor, version, $"{packId}-{version}.db");
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

    /// <summary>CalVer YYYY.M.N (<see cref="ReleaseVersion.TryParse"/>; egik cizgi, nokta-nokta ve ASCII disi rakam gecmez).</summary>
    public static bool IsValidVersion(string? value) => ReleaseVersion.TryParse(value, out _);

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
