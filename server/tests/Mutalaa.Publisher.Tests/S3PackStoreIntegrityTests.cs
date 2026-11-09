using Amazon.S3;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// S3PackStore.PutPackAsync Integrity dallari ve Integrity sonrasi davranis (Docker'siz: elle yazilmis IAmazonS3 sahtesi, <see cref="FakeS3Client"/>).
/// Gercek depo bu dallara hic girmez; burada yukleme sonrasi HEAD'in bozuk dondugu durumlar uretilir.
/// </summary>
public class S3PackStoreIntegrityTests
{
    private const string Key = "packs/dev/test-kucuk/2026.11.0/test-kucuk-2026.11.0.db";

    private static async Task<(S3PackStore Store, FakeS3Client Fake, TempFile File, string Sha, int Length)> NewAsync(CancellationToken ct)
    {
        (IAmazonS3 client, FakeS3Client fake) = FakeS3Client.Create();
        byte[] bytes = StorageTestKit.SyntheticBytes(5_000, seed: 21);
        TempFile file = await TempFile.CreateAsync(bytes, ct);
        return (new S3PackStore(client, "test-bucket"), fake, file, StorageTestKit.Sha256Hex(bytes), bytes.Length);
    }

    [Fact]
    public async Task A_faithful_store_uploads_and_a_repeat_with_the_same_sha256_is_skipped()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, _) = await NewAsync(ct);
        using TempFile owned = file;

        Assert.Equal(PutResult.Uploaded, await store.PutPackAsync(Key, owned.Path, sha, ct));
        Assert.Equal(PutResult.SkippedSame, await store.PutPackAsync(Key, owned.Path, sha, ct));
        Assert.Equal(1, fake.PutCount);
    }

    [Fact]
    public async Task An_object_that_is_missing_right_after_the_put_is_an_integrity_failure()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, _) = await NewAsync(ct);
        using TempFile owned = file;
        fake.Persist = (_, _, _) => null;

        StorageException ex = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));

        Assert.Equal(StorageFailure.Integrity, ex.Failure);
        Assert.Contains("bulunamadi", ex.Message, StringComparison.Ordinal);

        // Nesne hala yok: ikinci deneme yeniden yukler (atlamaz) ve ayni nedenle yine Integrity verir.
        StorageException again = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));
        Assert.Equal(StorageFailure.Integrity, again.Failure);
        Assert.Equal(2, fake.PutCount);
    }

    [Fact]
    public async Task A_stored_size_that_differs_from_the_file_is_an_integrity_failure_and_a_repeat_never_skips_the_bad_object()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, int length) = await NewAsync(ct);
        using TempFile owned = file;
        fake.Persist = (_, size, hash) => (size - 1, hash);

        StorageException ex = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));

        Assert.Equal(StorageFailure.Integrity, ex.Failure);
        Assert.Contains("boyutu", ex.Message, StringComparison.Ordinal);
        Assert.Equal(length - 1, fake.Objects[Key].Size);

        // Bozuk nesne depoda kaldi; ust verisi (sha256) dogru oldugu halde boyutu yanlis: ikinci deneme "ayni, atlandi" DEMEMELI.
        StorageException again = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));
        Assert.Equal(StorageFailure.Integrity, again.Failure);
        Assert.Equal(1, fake.PutCount);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_missing_or_different_sha256_metadata_is_an_integrity_failure_and_a_repeat_conflicts(bool metadataMissing)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, _) = await NewAsync(ct);
        using TempFile owned = file;
        string other = new('a', 64);
        fake.Persist = (_, size, _) => (size, metadataMissing ? null : other);

        StorageException ex = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));

        Assert.Equal(StorageFailure.Integrity, ex.Failure);
        Assert.Contains("sha256", ex.Message, StringComparison.Ordinal);
        Assert.Contains(metadataMissing ? "yok" : other, ex.Message, StringComparison.Ordinal);

        // Nesne ust verisi eksik ya da baska degerle depoda: ikinci deneme farkli sha256 olarak cakisir (ustune yazilmaz).
        ObjectConflictException conflict = await Assert.ThrowsAsync<ObjectConflictException>(() => store.PutPackAsync(Key, owned.Path, sha, ct));
        Assert.Equal(Key, conflict.Key);
        Assert.Equal(1, fake.PutCount);
    }

    // ---------------------------------------------------------------- yayimlanmamis surumun nesnesi (K-46 madde 3, BC-46)

    [Fact]
    public async Task Without_replace_permission_a_different_sha256_still_conflicts_and_nothing_is_written()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, _) = await NewAsync(ct);
        using TempFile owned = file;
        string other = new('b', 64);
        fake.Objects[Key] = (123, other);

        ObjectConflictException conflict = await Assert.ThrowsAsync<ObjectConflictException>(() => store.PutPackAsync(Key, owned.Path, sha, replaceExisting: false, ct));

        Assert.Equal((Key, other, sha), (conflict.Key, conflict.ExistingSha256, conflict.NewSha256));
        Assert.Equal(0, fake.PutCount);
        Assert.Equal((123L, (string?)other), fake.Objects[Key]);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task With_replace_permission_a_different_or_missing_sha256_is_replaced_and_verified(bool metadataMissing)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, int length) = await NewAsync(ct);
        using TempFile owned = file;
        fake.Objects[Key] = (123, metadataMissing ? null : new string('b', 64));

        PutResult result = await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct);

        Assert.Equal(PutResult.Replaced, result);
        Assert.Equal((long)length, fake.Objects[Key].Size);
        Assert.Equal(sha, fake.Objects[Key].Sha256);
        Assert.Equal(1, fake.PutCount);

        // Ayni icerik ikinci kez: atlanir.
        Assert.Equal(PutResult.SkippedSame, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));
        Assert.Equal(1, fake.PutCount);
    }

    [Fact]
    public async Task With_replace_permission_an_object_with_the_right_sha256_but_a_bad_size_is_repaired()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, int length) = await NewAsync(ct);
        using TempFile owned = file;
        fake.Objects[Key] = (length - 1, sha);

        // Degismez yolda bu bir Integrity hatasidir (yukaridaki testler); degistirilebilir nesnede onarilir.
        Assert.Equal(PutResult.Replaced, await store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));
        Assert.Equal(((long)length, (string?)sha), fake.Objects[Key]);
    }

    [Fact]
    public async Task With_replace_permission_a_head_mismatch_after_the_put_is_still_an_integrity_failure()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        (S3PackStore store, FakeS3Client fake, TempFile file, string sha, _) = await NewAsync(ct);
        using TempFile owned = file;
        fake.Objects[Key] = (123, new string('b', 64));
        fake.Persist = (_, size, hash) => (size - 1, hash);

        StorageException size = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));

        Assert.Equal(StorageFailure.Integrity, size.Failure);
        Assert.Contains("boyutu", size.Message, StringComparison.Ordinal);

        fake.Objects[Key] = (123, new string('b', 64));
        fake.Persist = (_, length, _) => (length, new string('c', 64));

        StorageException meta = await Assert.ThrowsAsync<StorageException>(() => store.PutPackAsync(Key, owned.Path, sha, replaceExisting: true, ct));

        Assert.Equal(StorageFailure.Integrity, meta.Failure);
        Assert.Contains("sha256", meta.Message, StringComparison.Ordinal);
    }
}
