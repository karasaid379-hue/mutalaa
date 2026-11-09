namespace Mutalaa.Infrastructure.Storage;

/// <summary>StorageException ayrimi: komut katmani cikis kodunu ve mesaji buna gore secer.</summary>
public enum StorageFailure
{
    /// <summary>Baglanti reddi, zaman asimi, 5xx: servis ulasilamaz ya da gecici arizali.</summary>
    Unavailable,

    /// <summary>403: kimlik bilgisi yanlis ya da yetkisiz.</summary>
    AccessDenied,

    /// <summary>404 (kova yok gibi); nesne okumada ve HEAD'de yok sayilir, null doner.</summary>
    NotFound,

    /// <summary>Yukleme sonrasi boyut ya da sha256 uyusmadi.</summary>
    Integrity,

    /// <summary>Var olan anahtara farkli sha256 yazilmak istendi (ObjectConflictException).</summary>
    Conflict,

    /// <summary>Diger depo hatalari (4xx vb.).</summary>
    Other,
}

/// <summary>Depo hatasi (Yayinlayici cikis kodu 4). Ic istisna SDK hatasidir; gizli deger tasimaz.</summary>
public class StorageException : Exception
{
    public StorageException(StorageFailure failure, string message, Exception? inner = null)
        : base(message, inner)
    {
        Failure = failure;
    }

    public StorageFailure Failure { get; }
}

/// <summary>
/// Var olan anahtara farkli sha256 ile yazilmak istendi (Backend API 10.5). Yayinlayici yayini basarisiz isaretler, cikis 4.
/// <see cref="ExistingSha256"/> nesnede x-amz-meta-sha256 yoksa null.
/// </summary>
public sealed class ObjectConflictException : StorageException
{
    public ObjectConflictException(string key, string? existingSha256, string newSha256)
        : base(
            StorageFailure.Conflict,
            $"Anahtar {key} zaten var ve sha256 degeri farkli (mevcut: {existingSha256 ?? "yok"}, yeni: {newSha256}).")
    {
        Key = key;
        ExistingSha256 = existingSha256;
        NewSha256 = newSha256;
    }

    public string Key { get; }

    public string? ExistingSha256 { get; }

    public string NewSha256 { get; }
}
