using System.Globalization;
using NSec.Cryptography;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>Anahtar uretimi ve kid bicimi (K-45 madde 3: {derleme}-{YYYY}-{n}).</summary>
public static class SigningKeys
{
    /// <summary>Taze Ed25519 anahtari uretir (NSec Key.Create). flavor kucuk harf ASCII (dev, internal, public, test).</summary>
    public static SigningKey Generate(string flavor, int year, int n)
    {
        string kid = FormatKid(flavor, year, n);
        using Key key = Key.Create(
            SignatureAlgorithm.Ed25519,
            new KeyCreationParameters { ExportPolicy = KeyExportPolicies.AllowPlaintextExport });
        byte[] seed = key.Export(KeyBlobFormat.RawPrivateKey);
        try
        {
            return new SigningKey(seed, kid);
        }
        finally
        {
            Array.Clear(seed);
        }
    }

    /// <summary>"{flavor}-{YYYY}-{n}"; flavor [a-z]+, yil 1000..9999, n >= 1 degilse ArgumentException.</summary>
    public static string FormatKid(string flavor, int year, int n)
    {
        ArgumentException.ThrowIfNullOrEmpty(flavor);
        foreach (char c in flavor)
        {
            if (c is < 'a' or > 'z')
            {
                throw new ArgumentException("flavor yalniz kucuk harf ASCII olmali.", nameof(flavor));
            }
        }

        ArgumentOutOfRangeException.ThrowIfLessThan(year, 1000);
        ArgumentOutOfRangeException.ThrowIfGreaterThan(year, 9999);
        ArgumentOutOfRangeException.ThrowIfLessThan(n, 1);

        return string.Create(CultureInfo.InvariantCulture, $"{flavor}-{year}-{n}");
    }
}
