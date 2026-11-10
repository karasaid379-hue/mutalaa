using System.Globalization;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>
/// Dosya yardimcilari. Ortak kisim <see cref="PackFiles"/> icindedir (Infrastructure); burada yalniz Yayinlayiciya ozgu dogrulama
/// (gecersiz girdi = kalici <see cref="PublisherException"/>) ve kisa yollar durur.
/// </summary>
internal static class Files
{
    public static string Inv(FormattableString value) => value.ToString(CultureInfo.InvariantCulture);

    public static string LocalPackPath(string outRoot, string flavor, string packId, string version)
    {
        RequirePackId(packId);
        RequireVersion(version);
        return PackFiles.LocalPackPath(outRoot, flavor, packId, version);
    }

    public static string ReleaseDir(string outRoot, string flavor, string surum)
    {
        RequireVersion(surum);
        return Path.Combine(outRoot, flavor, surum);
    }

    public static bool IsValidPackId(string? value) => PackFiles.IsValidPackId(value);

    public static bool IsValidVersion(string? value) => PackFiles.IsValidVersion(value);

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

    public static Task WriteTextAsync(string path, string text, CancellationToken cancellationToken) =>
        PackFiles.WriteTextAsync(path, text, cancellationToken);

    public static Task WriteBytesAsync(string path, byte[] bytes, CancellationToken cancellationToken) =>
        PackFiles.WriteBytesAsync(path, bytes, cancellationToken);

    public static Task<string> Sha256Async(string path, CancellationToken cancellationToken) =>
        PackFiles.Sha256Async(path, cancellationToken);

    public static string Sha256(ReadOnlySpan<byte> data) => PackFiles.Sha256(data);
}
