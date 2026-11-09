using System.Globalization;
using System.Security.Cryptography;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>Depo testlerinin ortak yardimcilari: kultur kapsami, gecici paket dosyasi, ozet.</summary>
internal static class StorageTestKit
{
    /// <summary>Async eylemi Invariant ya da tr-TR kulturunde calistirir; kultur finally ile geri alinir (yalniz bu mantiksal akis).</summary>
    public static async Task RunAsync(bool turkish, Func<Task> action)
    {
        CultureInfo previous = CultureInfo.CurrentCulture;
        CultureInfo previousUi = CultureInfo.CurrentUICulture;
        CultureInfo culture = turkish ? CultureInfo.GetCultureInfo("tr-TR") : CultureInfo.InvariantCulture;
        try
        {
            CultureInfo.CurrentCulture = culture;
            CultureInfo.CurrentUICulture = culture;
            Assert.Equal(turkish ? "tr-TR" : string.Empty, CultureInfo.CurrentCulture.Name);
            await action();
        }
        finally
        {
            CultureInfo.CurrentCulture = previous;
            CultureInfo.CurrentUICulture = previousUi;
        }
    }

    /// <summary>Test basina benzersiz anahtar oneki (testler ayni kovayi paylasir).</summary>
    public static string NewPrefix() =>
        "t-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..8];

    /// <summary>Sentetik paket govdesi: tohumlu, bu yuzden tekrarlanabilir; icerik sahte (SQLite degil).</summary>
    public static byte[] SyntheticBytes(int length, int seed)
    {
        byte[] bytes = new byte[length];
        new Random(seed).NextBytes(bytes);
        return bytes;
    }

    public static string Sha256Hex(ReadOnlySpan<byte> data) => Convert.ToHexStringLower(SHA256.HashData(data));
}

/// <summary>Gecici dosya (sistem gecici klasoru); Dispose siler.</summary>
internal sealed class TempFile : IDisposable
{
    private TempFile(string path)
    {
        Path = path;
    }

    public string Path { get; }

    public static async Task<TempFile> CreateAsync(byte[] content, CancellationToken cancellationToken)
    {
        string path = System.IO.Path.Combine(
            System.IO.Path.GetTempPath(),
            "mutalaa-s3-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture) + ".db");
        await File.WriteAllBytesAsync(path, content, cancellationToken);
        return new TempFile(path);
    }

    public void Dispose()
    {
        File.Delete(Path);
    }
}
