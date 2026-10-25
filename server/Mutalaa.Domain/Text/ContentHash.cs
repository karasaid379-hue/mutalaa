using System.Security.Cryptography;
using System.Text;

namespace Mutalaa.Domain.Text;

/// <summary>
/// <c>content_hash</c>: metnin UTF-8 baytlarinin SHA-256 ozeti, 64 kucuk harf onaltilik (Capa semasi 7).
/// </summary>
public static class ContentHash
{
    // BOM yok; tek basina vekil gibi gecersiz dizilerde sessizce ? yazmak yerine hata verir.
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    /// <summary>Metni oldugu gibi (donusum uygulamadan) ozetler.</summary>
    /// <exception cref="EncoderFallbackException">Metin gecerli Unicode degilse (ornegin tek basina vekil).</exception>
    public static string Compute(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        byte[] bytes = StrictUtf8.GetBytes(text);
        return Convert.ToHexStringLower(SHA256.HashData(bytes));
    }
}
