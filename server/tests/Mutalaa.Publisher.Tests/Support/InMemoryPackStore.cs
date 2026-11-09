using System.Runtime.CompilerServices;
using Mutalaa.Infrastructure.Storage;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Bellek ici sahte depo (IPackStore sozlesmesi: ayni sha256 atlanir, farkli sha256 ObjectConflictException; replaceExisting ile degistirilir). Hata enjeksiyonu: <see cref="Fault"/>
/// islem adi ("put-pack", "head", "put-manifest", "get", "list") ve anahtarla cagrilir; bir istisna donerse firlatilir. Her yazma <see cref="Writes"/> listesine eklenir.
/// </summary>
internal sealed class InMemoryPackStore : IPackStore
{
    private readonly Dictionary<string, (byte[] Bytes, string? Sha256)> _objects = new(StringComparer.Ordinal);

    public List<string> Writes { get; } = [];

    public Func<string, string, Exception?>? Fault { get; set; }

    public IReadOnlyCollection<string> Keys => _objects.Keys;

    public bool Contains(string key) => _objects.ContainsKey(key);

    public bool Remove(string key) => _objects.Remove(key);

    public byte[]? Peek(string key) => _objects.TryGetValue(key, out (byte[] Bytes, string? Sha256) value) ? value.Bytes : null;

    /// <summary>Sozlesmeyi atlayarak nesne yazar (cakisma/kurcalama senaryolari).</summary>
    public void Seed(string key, byte[] bytes, string? sha256) => _objects[key] = (bytes, sha256);

    /// <summary>Degistirme izniyle (replaceExisting) yazilan anahtarlar (Writes listesine de girer).</summary>
    public List<string> Replaced { get; } = [];

    public async Task<PutResult> PutPackAsync(string key, string filePath, string sha256, bool replaceExisting, CancellationToken cancellationToken)
    {
        Throw("put-pack", key);
        bool exists = _objects.TryGetValue(key, out (byte[] Bytes, string? Sha256) existing);
        long size = new FileInfo(filePath).Length;
        bool sameSha = exists && string.Equals(existing.Sha256, sha256, StringComparison.OrdinalIgnoreCase);

        // Gercek S3PackStore ile ayni sozlesme: ayni sha256 ve ayni boyut atlanir; ayni sha256 ama farkli boyut bozuk nesnedir (degistirme kapaliyken
        // Integrity, acikken yeniden yazilir); farkli sha256 degistirme kapaliyken cakismadir.
        if (sameSha && existing.Bytes.LongLength == size)
        {
            return PutResult.SkippedSame;
        }

        if (exists && !replaceExisting)
        {
            throw sameSha
                ? new StorageException(StorageFailure.Integrity, $"Depodaki {key} ayni sha256 ust verisini tasiyor ama boyutu uyusmuyor (beklenen: {size}, depoda: {existing.Bytes.LongLength}).")
                : new ObjectConflictException(key, existing.Sha256, sha256);
        }

        _objects[key] = (await File.ReadAllBytesAsync(filePath, cancellationToken), sha256);
        Writes.Add(key);
        if (exists)
        {
            Replaced.Add(key);
        }

        return exists ? PutResult.Replaced : PutResult.Uploaded;
    }

    public Task<StoredObject?> HeadAsync(string key, CancellationToken cancellationToken)
    {
        Throw("head", key);
        return Task.FromResult(_objects.TryGetValue(key, out (byte[] Bytes, string? Sha256) value) ? new StoredObject(value.Bytes.LongLength, value.Sha256) : null);
    }

    public Task PutManifestAsync(string key, ReadOnlyMemory<byte> json, CancellationToken cancellationToken)
    {
        Throw("put-manifest", key);
        _objects[key] = (json.ToArray(), null);
        Writes.Add(key);
        return Task.CompletedTask;
    }

    public Task<byte[]?> GetAsync(string key, CancellationToken cancellationToken)
    {
        Throw("get", key);
        return Task.FromResult(_objects.TryGetValue(key, out (byte[] Bytes, string? Sha256) value) ? value.Bytes : null);
    }

    public async IAsyncEnumerable<string> ListKeysAsync(string prefix, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        Throw("list", prefix);
        foreach (string key in _objects.Keys.Where(k => k.StartsWith(prefix, StringComparison.Ordinal)).Order(StringComparer.Ordinal))
        {
            yield return key;
        }

        await Task.CompletedTask;
    }

    private void Throw(string operation, string key)
    {
        Exception? fault = Fault?.Invoke(operation, key);
        if (fault is not null)
        {
            throw fault;
        }
    }
}

/// <summary>Sabit saat (TimeProvider); Advance ile ilerletilebilir.</summary>
internal sealed class FixedClock(DateTimeOffset start) : TimeProvider
{
    private DateTimeOffset _now = start;

    public override DateTimeOffset GetUtcNow() => _now;

    public void Advance(TimeSpan span) => _now += span;
}
