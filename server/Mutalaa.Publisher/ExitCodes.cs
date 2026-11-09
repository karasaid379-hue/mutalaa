namespace Mutalaa.Publisher;

/// <summary>Yayinlayici cikis kodlari (Backend API 10.1): 0 basari, 2 kapi reddi, 3 dogrulama, 4 depo, 1 diger (komut satiri ayristirma hatasi ve kilit dahil).</summary>
public static class ExitCodes
{
    public const int Success = 0;
    public const int Other = 1;
    public const int GateRejected = 2;
    public const int Verification = 3;
    public const int Storage = 4;
}

/// <summary>
/// Beklenen, kullaniciya anlatilabilir hata: iletide gizli deger bulunmaz. Komut katmani iletiyi yazar ve <see cref="ExitCode"/> ile biter.
/// </summary>
public sealed class PublisherException : Exception
{
    public PublisherException(int exitCode, string message)
        : base(message)
    {
        ExitCode = exitCode;
    }

    public PublisherException(int exitCode, string message, Exception innerException)
        : base(message, innerException)
    {
        ExitCode = exitCode;
    }

    public int ExitCode { get; }
}
