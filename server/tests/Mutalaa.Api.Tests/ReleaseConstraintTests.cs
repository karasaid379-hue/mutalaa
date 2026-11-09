using System.Globalization;
using Mutalaa.Api.Tests.Support;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>
/// release tablosunun K-46 kisitlari (Docker'li): talep CHECK'i, kaynak_release_id yabanci anahtari ve
/// durum &lt;&gt; 'basarisiz' kismi tekil dizini (release_surum_derleme_key). Her test kendi islemini acar ve geri alir.
/// </summary>
public class ReleaseConstraintTests(EditorialDatabase<ReleaseConstraintTests> fixture) : IClassFixture<EditorialDatabase<ReleaseConstraintTests>>
{
    private const string InsertRelease =
        "INSERT INTO icerik.release (surum, derleme, durum, data_version, olusturan) VALUES (@v, 'dev', @d::icerik.surum_durumu, 'test', 'test-editor')";

    private TestDatabase Db => fixture.Database;

    private static string UniqueVersion() => "test-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..8];

    private static Task<int> AddAsync(RollbackSession session, string version, string status, CancellationToken ct) =>
        session.ExecuteAsync(InsertRelease, ct, ("v", version), ("d", status));

    // --- release_talep_check ---

    [Fact]
    public async Task Release_talep_check_rejects_an_unknown_request()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(
            "INSERT INTO icerik.release (surum, derleme, data_version, olusturan, talep) VALUES (@v, 'dev', 'test', 'test-editor', 'bilinmiyor')",
            ct,
            ("v", UniqueVersion())));

        Assert.Equal("23514", exception.SqlState);
        Assert.Equal("release_talep_check", exception.ConstraintName);
    }

    [Theory]
    [InlineData("yayin")]
    [InlineData("terfi")]
    [InlineData("geri_alma")]
    public async Task Release_talep_check_accepts_the_three_requests(string request)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        int rows = await session.ExecuteAsync(
            "INSERT INTO icerik.release (surum, derleme, data_version, olusturan, talep, paketler, notlar) VALUES (@v, 'dev', 'test', 'test-editor', @t, ARRAY['core','test-kucuk'], 'Deneme notu')",
            ct,
            ("v", UniqueVersion()),
            ("t", request));

        Assert.Equal(1, rows);
    }

    // --- release_kaynak_release_id_fkey ---

    [Fact]
    public async Task Release_kaynak_release_id_rejects_an_unknown_release()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(
            "INSERT INTO icerik.release (surum, derleme, data_version, olusturan, talep, kaynak_release_id) VALUES (@v, 'public', 'test', 'test-editor', 'terfi', 2147483647)",
            ct,
            ("v", UniqueVersion())));

        Assert.Equal("23503", exception.SqlState);
        Assert.Equal("release_kaynak_release_id_fkey", exception.ConstraintName);
    }

    [Fact]
    public async Task Release_kaynak_release_id_accepts_an_existing_release()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();
        await AddAsync(session, version, "yayinlandi", ct);

        int rows = await session.ExecuteAsync(
            "INSERT INTO icerik.release (surum, derleme, data_version, olusturan, talep, kaynak_release_id) "
            + "SELECT @v, 'public', 'test', 'test-editor', 'terfi', id FROM icerik.release WHERE surum = @src",
            ct,
            ("v", UniqueVersion()),
            ("src", version));

        Assert.Equal(1, rows);
    }

    // --- release_surum_derleme_key (kismi tekil dizin, K-46 madde 3) ---

    [Theory]
    [InlineData("hazirlaniyor", "hazirlaniyor")]
    [InlineData("hazirlaniyor", "yayinlandi")]
    [InlineData("dogrulandi", "geri_cekildi")]
    public async Task Release_partial_unique_index_rejects_a_second_non_failed_release_with_the_same_version_and_flavor(string first, string second)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();
        await AddAsync(session, version, first, ct);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => AddAsync(session, version, second, ct));

        Assert.Equal("23505", exception.SqlState);
        Assert.Equal("release_surum_derleme_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Release_partial_unique_index_accepts_a_retry_after_a_failed_attempt()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();
        await AddAsync(session, version, "basarisiz", ct);

        await AddAsync(session, version, "hazirlaniyor", ct);

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.release WHERE surum = @v", ct, ("v", version)));
    }

    [Fact]
    public async Task Release_partial_unique_index_accepts_any_number_of_failed_attempts()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();

        await AddAsync(session, version, "basarisiz", ct);
        await AddAsync(session, version, "basarisiz", ct);

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.release WHERE surum = @v", ct, ("v", version)));
    }

    [Fact]
    public async Task Release_partial_unique_index_still_rejects_a_second_attempt_after_a_failed_one_succeeded()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();
        await AddAsync(session, version, "basarisiz", ct);
        await AddAsync(session, version, "hazirlaniyor", ct);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => AddAsync(session, version, "hazirlaniyor", ct));

        Assert.Equal("23505", exception.SqlState);
        Assert.Equal("release_surum_derleme_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Release_partial_unique_index_allows_the_same_version_under_another_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string version = UniqueVersion();
        await AddAsync(session, version, "hazirlaniyor", ct);

        int rows = await session.ExecuteAsync(
            "INSERT INTO icerik.release (surum, derleme, data_version, olusturan) VALUES (@v, 'internal', 'test', 'test-editor')",
            ct,
            ("v", version));

        Assert.Equal(1, rows);
    }
}
