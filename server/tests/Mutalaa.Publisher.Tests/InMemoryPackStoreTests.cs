using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>Sahte deponun PutPackAsync davranisi gercek S3PackStore ile ayni olmalidir (ayni sha256 ama farkli boyut dahil).</summary>
public class InMemoryPackStoreTests
{
    private const string Key = "packs/dev/test-kucuk/2026.11.0/test-kucuk-2026.11.0.db";

    private static async Task<(InMemoryPackStore Store, TempFile File, string Sha)> NewAsync(CancellationToken ct)
    {
        byte[] bytes = StorageTestKit.SyntheticBytes(2_000, seed: 5);
        TempFile file = await TempFile.CreateAsync(bytes, ct);
        return (new InMemoryPackStore(), file, StorageTestKit.Sha256Hex(bytes));
    }

    [Fact]
    public async Task The_same_sha256_and_size_is_skipped()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (InMemoryPackStore store, TempFile file, string sha) = await NewAsync(ct);
        using TempFile owned = file;

        Assert.Equal(PutResult.Uploaded, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: false, ct));
        Assert.Equal(PutResult.SkippedSame, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));
        Assert.Empty(store.Replaced);
    }

    [Fact]
    public async Task The_same_sha256_with_a_different_size_is_an_integrity_failure_unless_replacing_is_allowed()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (InMemoryPackStore store, TempFile file, string sha) = await NewAsync(ct);
        using TempFile owned = file;
        byte[] bad = [1, 2, 3];
        store.Seed(Key, bad, sha);

        StorageException ex = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, replaceExisting: false, ct));

        Assert.Equal(StorageFailure.Integrity, ex.Failure);
        Assert.Equal(bad, store.Peek(Key));

        Assert.Equal(PutResult.Replaced, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));
        Assert.Equal([Key], store.Replaced);
        Assert.Equal((await File.ReadAllBytesAsync(owned.Path, ct)).LongLength, store.Peek(Key)!.LongLength);
    }

    [Fact]
    public async Task A_different_sha256_is_a_conflict_unless_replacing_is_allowed()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (InMemoryPackStore store, TempFile file, string sha) = await NewAsync(ct);
        using TempFile owned = file;
        store.Seed(Key, [1, 2, 3], new string('a', 64));

        await Assert.ThrowsAsync<ObjectConflictException>(() => store.PutPackAsync(Key, owned.Path, sha, replaceExisting: false, ct));
        Assert.Equal(PutResult.Replaced, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));
    }
}
