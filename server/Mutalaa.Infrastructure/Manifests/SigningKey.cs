using System.Diagnostics;
using NSec.Cryptography;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>
/// Ed25519 imza anahtari: 32 baytlik ham tohum ve kid ({derleme}-{YYYY}-{n}). Tohum gizlidir:
/// ToString, hata iletileri ve hata ayiklayici gosterimi tohumu yazmaz. Tohumu disari veren tek yol
/// SeedBase64'tur (kullanici sirlarina yazmak icin); cagiran bunu gunluge ve ekrana basmaz.
/// </summary>
[DebuggerDisplay("SigningKey {Kid}")]
public sealed class SigningKey
{
    public const int SeedLength = 32;
    public const int PublicKeyLength = 32;

    private readonly byte[] _seed;

    public SigningKey(ReadOnlySpan<byte> seed, string kid)
    {
        ArgumentException.ThrowIfNullOrEmpty(kid);
        if (seed.Length != SeedLength)
        {
            throw new ArgumentException($"Tohum {SeedLength} bayt olmali (verilen: {seed.Length}).", nameof(seed));
        }

        _seed = seed.ToArray();
        Kid = kid;
    }

    public string Kid { get; }

    /// <summary>Ham tohum (yalniz imzalama icin; gunluge yazilmaz).</summary>
    public ReadOnlyMemory<byte> Seed => _seed;

    /// <summary>Tohumun base64 gosterimi (Signing:{f}:PrivateKey degeri).</summary>
    public string SeedBase64() => Base64Strict.Encode(_seed);

    /// <summary>base64 tohumdan anahtar kurar; base64 degilse ya da 32 bayt degilse ArgumentException atar (tohum iletiye girmez).</summary>
    public static SigningKey FromSeedBase64(string seedBase64, string kid)
    {
        if (!Base64Strict.TryDecode(seedBase64, out byte[] seed))
        {
            throw new ArgumentException("Tohum gecerli base64 degil.", nameof(seedBase64));
        }

        return new SigningKey(seed, kid);
    }

    /// <summary>32 baytlik ham acik anahtar.</summary>
    public byte[] GetPublicKey()
    {
        using Key key = ToNSecKey();
        return key.PublicKey.Export(KeyBlobFormat.RawPublicKey);
    }

    /// <summary>NSec anahtari (cagiran Dispose eder).</summary>
    internal Key ToNSecKey() => Key.Import(SignatureAlgorithm.Ed25519, _seed, KeyBlobFormat.RawPrivateKey);

    public override string ToString() => $"SigningKey {{ Kid = {Kid}, Seed = <redacted> }}";
}
