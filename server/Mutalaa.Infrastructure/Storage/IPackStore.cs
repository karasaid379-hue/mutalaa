namespace Mutalaa.Infrastructure.Storage;

/// <summary>PutPackAsync sonucu.</summary>
public enum PutResult
{
    /// <summary>Anahtar yoktu; yuklendi ve HEAD ile dogrulandi.</summary>
    Uploaded,

    /// <summary>Anahtar vardi ve x-amz-meta-sha256 ayniydi; yukleme atlandi.</summary>
    SkippedSame,
}

/// <summary>HEAD sonucu: boyut (bayt) ve x-amz-meta-sha256 (yoksa null).</summary>
public sealed record StoredObject(long Size, string? Sha256);

/// <summary>
/// Paket deposu (Backend API 10.5). Anahtarlar kova icindeki yoldur (<see cref="StorageKeys"/>).
/// Depo hatalari <see cref="StorageException"/> olarak gelir; iptal OperationCanceledException kalir.
/// </summary>
public interface IPackStore
{
    /// <summary>
    /// Paket dosyasini yukler. Anahtar varsa ve sha256 ayniysa atlar (<see cref="PutResult.SkippedSame"/>); farkliysa
    /// <see cref="ObjectConflictException"/>; yoksa yukler ve HEAD ile boyut ve sha256 dogrular (uyusmazlik StorageException, Integrity).
    /// <paramref name="sha256"/> kucuk harf onaltilik 64 karakterdir; cagiran verir, bu sinif dosyayi yeniden ozetlemez.
    /// </summary>
    Task<PutResult> PutPackAsync(string key, string filePath, string sha256, CancellationToken cancellationToken);

    /// <summary>Nesne yoksa null.</summary>
    Task<StoredObject?> HeadAsync(string key, CancellationToken cancellationToken);

    /// <summary>Manifesti tek PUT ile yazar (Cache-Control no-cache, application/json); var olani degistirir.</summary>
    Task PutManifestAsync(string key, ReadOnlyMemory<byte> json, CancellationToken cancellationToken);

    /// <summary>Nesne govdesi; yoksa null.</summary>
    Task<byte[]?> GetAsync(string key, CancellationToken cancellationToken);

    /// <summary>Onekle baslayan butun anahtarlar (sayfalama dahil, anahtar sirasiyla).</summary>
    IAsyncEnumerable<string> ListKeysAsync(string prefix, CancellationToken cancellationToken);
}
