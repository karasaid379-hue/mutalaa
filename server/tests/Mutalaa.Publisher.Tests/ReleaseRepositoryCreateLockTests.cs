using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;
using Npgsql;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// ReleaseRepository.CreateAsync danisma kilidi ve requireNoOpen (A14.6a; Docker: gercek PostgreSQL). Satir acan cagrilar pg_advisory_xact_lock ile
/// sirayla calisir; requireNoOpen=true ikinci cagrida ReleaseInProgressException verir; requireNoOpen=false davranisi degismez.
/// </summary>
public class ReleaseRepositoryCreateLockTests(PostgresFixture postgres)
{
    private static NewRelease New(BuildFlavor flavor = BuildFlavor.Dev, string? surum = null) =>
        new(flavor, surum, ReleaseRequests.Yayin, "2026.11.09-abc1234", "test");

    [Fact]
    public void The_create_lock_key_differs_from_the_publisher_lock_key()
    {
        Assert.NotEqual(PublisherLock.Key, ReleaseRepository.CreateLockKey);
        Assert.Equal(0x4D5554414C414132L, ReleaseRepository.CreateLockKey);
    }

    [Fact]
    public async Task Two_concurrent_require_no_open_calls_open_one_row_and_the_other_is_rejected()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        async Task<(Release? Row, ReleaseInProgressException? Error)> CallAsync()
        {
            try
            {
                return (await harness.Releases.CreateAsync(New(), requireNoOpen: true, ct), null);
            }
            catch (ReleaseInProgressException ex)
            {
                return (null, ex);
            }
        }

        (Release? Row, ReleaseInProgressException? Error)[] results =
            await Task.WhenAll(Enumerable.Range(0, 2).Select(_ => Task.Run(CallAsync, ct)));

        Release opened = Assert.Single(results, r => r.Row is not null).Row!;
        ReleaseInProgressException rejected = Assert.Single(results, r => r.Error is not null).Error!;
        Assert.Equal(opened.Id, rejected.OpenRelease.Id);
        Assert.Equal(1L, await harness.Database.ScalarAsync<long>("SELECT count(*) FROM icerik.release", ct));
    }

    [Fact]
    public async Task A_create_call_waits_while_another_session_holds_the_create_lock()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        await using NpgsqlConnection holder = new(harness.Database.ConnectionString);
        await holder.OpenAsync(ct);
        await using (NpgsqlCommand acquire = new("SELECT pg_advisory_lock(@key)", holder))
        {
            acquire.Parameters.AddWithValue("key", ReleaseRepository.CreateLockKey);
            await acquire.ExecuteNonQueryAsync(ct);
        }

        Task<Release> waiting = Task.Run(() => harness.Releases.CreateAsync(New(), ct), ct);
        await Task.Delay(TimeSpan.FromSeconds(1), ct);
        Assert.False(waiting.IsCompleted);

        await using (NpgsqlCommand release = new("SELECT pg_advisory_unlock(@key)", holder))
        {
            release.Parameters.AddWithValue("key", ReleaseRepository.CreateLockKey);
            await release.ExecuteNonQueryAsync(ct);
        }

        Release row = await waiting.WaitAsync(TimeSpan.FromSeconds(30), ct);
        Assert.Equal(ReleaseStatus.Hazirlaniyor, row.Durum);
    }

    [Fact]
    public async Task Require_no_open_rejects_both_open_states_and_ignores_other_flavors_and_closed_rows()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release first = await harness.Releases.CreateAsync(New(), requireNoOpen: true, ct);
        ReleaseInProgressException preparing = await Assert.ThrowsAsync<ReleaseInProgressException>(
            () => harness.Releases.CreateAsync(New(), requireNoOpen: true, ct));
        Assert.Equal((first.Id, ReleaseStatus.Hazirlaniyor), (preparing.OpenRelease.Id, preparing.OpenRelease.Durum));
        Assert.Contains(first.Surum, preparing.Message, StringComparison.Ordinal);

        // Baska derleme turu etkilenmez.
        Release internalRow = await harness.Releases.CreateAsync(New(BuildFlavor.Internal), requireNoOpen: true, ct);
        Assert.Equal(BuildFlavor.Internal, internalRow.Derleme);

        // dogrulandi de acik sayilir.
        await harness.Releases.MarkVerifiedAsync(first.Id, "{}", "{}", "{}", null, ct);
        ReleaseInProgressException verified = await Assert.ThrowsAsync<ReleaseInProgressException>(
            () => harness.Releases.CreateAsync(New(), requireNoOpen: true, ct));
        Assert.Equal(ReleaseStatus.Dogrulandi, verified.OpenRelease.Durum);

        // yayinlandi ve basarisiz satirlar acik degildir.
        await harness.Releases.MarkPublishedAsync(first.Id, ct);
        Release afterPublished = await harness.Releases.CreateAsync(New(), requireNoOpen: true, ct);
        await harness.Releases.MarkFailedAsync(afterPublished.Id, "{}", ct);
        Release afterFailed = await harness.Releases.CreateAsync(New(), requireNoOpen: true, ct);
        Assert.Equal(ReleaseStatus.Hazirlaniyor, afterFailed.Durum);

        // Reddedilen cagri satir ve surum numarasi tuketmez.
        Assert.Equal(4L, await harness.Database.ScalarAsync<long>("SELECT count(*) FROM icerik.release", ct));
    }

    [Fact]
    public async Task Without_require_no_open_open_rows_do_not_block_and_the_two_argument_overload_is_unchanged()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release a = await harness.Releases.CreateAsync(New(), ct);
        Release b = await harness.Releases.CreateAsync(New(), requireNoOpen: false, ct);
        Release c = await harness.Releases.CreateAsync(New(), ct);

        Assert.Equal(["2026.11.0", "2026.11.1", "2026.11.2"], [a.Surum, b.Surum, c.Surum]);
        Assert.All([a, b, c], r => Assert.Equal(ReleaseStatus.Hazirlaniyor, r.Durum));
    }

    [Fact]
    public async Task Concurrent_calls_without_a_version_get_distinct_versions_and_an_explicit_version_conflict_still_throws()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release[] rows = await Task.WhenAll(
            Enumerable.Range(0, 4).Select(_ => Task.Run(() => harness.Releases.CreateAsync(New(), ct), ct)));

        Assert.Equal(4, rows.Select(r => r.Surum).Distinct(StringComparer.Ordinal).Count());
        await Assert.ThrowsAsync<ReleaseConflictException>(() => harness.Releases.CreateAsync(New(surum: rows[0].Surum), ct));
    }
}
