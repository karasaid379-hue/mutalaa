using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;
using Npgsql;

namespace Mutalaa.Publisher.Tests;

/// <summary>ReleaseRepository (Docker: gercek PostgreSQL): surum atama, durum gecisleri, talep alanlari, FOR UPDATE SKIP LOCKED.</summary>
public class ReleaseRepositoryTests(PostgresFixture postgres)
{
    private static NewRelease New(BuildFlavor flavor = BuildFlavor.Dev, string? surum = null, string talep = ReleaseRequests.Yayin, int? source = null, string[]? packs = null, string? notes = null) =>
        new(flavor, surum, talep, "2026.11.09-abc1234", "test", source, packs, notes);

    [Fact]
    public async Task Assigns_versions_per_month_with_one_counter_for_all_flavors()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release first = await harness.Releases.CreateAsync(New(BuildFlavor.Dev), ct);
        Release second = await harness.Releases.CreateAsync(New(BuildFlavor.Internal), ct);
        Release third = await harness.Releases.CreateAsync(New(BuildFlavor.Dev), ct);

        Assert.Equal(["2026.11.0", "2026.11.1", "2026.11.2"], [first.Surum, second.Surum, third.Surum]);

        harness.Clock.Advance(TimeSpan.FromDays(30));
        Release december = await harness.Releases.CreateAsync(New(BuildFlavor.Public), ct);
        Assert.Equal("2026.12.0", december.Surum);
    }

    [Fact]
    public async Task A_failed_release_does_not_burn_its_version_number()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release first = await harness.Releases.CreateAsync(New(), ct);
        await harness.Releases.MarkFailedAsync(first.Id, "{}", ct);
        Release retry = await harness.Releases.CreateAsync(New(), ct);

        Assert.Equal("2026.11.0", first.Surum);
        Assert.Equal("2026.11.0", retry.Surum);
        Assert.NotEqual(first.Id, retry.Id);
        Assert.Equal(ReleaseStatus.Basarisiz, (await harness.Releases.GetAsync(first.Id, ct))!.Durum);
    }

    [Fact]
    public async Task An_explicit_version_conflicts_only_with_a_non_failed_release_of_the_same_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        Release dev = await harness.Releases.CreateAsync(New(BuildFlavor.Dev, "2026.11.5"), ct);

        await Assert.ThrowsAsync<ReleaseConflictException>(() => harness.Releases.CreateAsync(New(BuildFlavor.Dev, "2026.11.5"), ct));
        Release other = await harness.Releases.CreateAsync(New(BuildFlavor.Internal, "2026.11.5"), ct);
        await harness.Releases.MarkFailedAsync(dev.Id, "{}", ct);
        Release again = await harness.Releases.CreateAsync(New(BuildFlavor.Dev, "2026.11.5"), ct);

        Assert.Equal(BuildFlavor.Internal, other.Derleme);
        Assert.NotEqual(dev.Id, again.Id);
        Assert.Equal(again.Id, (await harness.Releases.FindAsync(BuildFlavor.Dev, "2026.11.5", ct))!.Id);
    }

    [Theory]
    [InlineData("2026.011.0")]
    [InlineData("2026.13.0")]
    [InlineData("abc")]
    public async Task Rejects_an_invalid_explicit_version(string surum)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);

        await Assert.ThrowsAsync<ArgumentException>(() => harness.Releases.CreateAsync(New(surum: surum), ct));
    }

    [Fact]
    public async Task Walks_the_documented_state_machine_and_refuses_other_transitions()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release row = await harness.Releases.CreateAsync(New(), ct);
        Assert.Equal(ReleaseStatus.Hazirlaniyor, row.Durum);

        await Assert.ThrowsAsync<InvalidOperationException>(() => harness.Releases.MarkPublishedAsync(row.Id, ct));
        await Assert.ThrowsAsync<InvalidOperationException>(() => harness.Releases.MarkWithdrawnAsync(row.Id, ct));

        await harness.Releases.MarkVerifiedAsync(row.Id, """{"manifest_version":1}""", """{"rejected":false}""", """{"kaynaklar":{},"paketler":{}}""", ["test-kucuk"], ct);
        Release verified = (await harness.Releases.GetAsync(row.Id, ct))!;
        Assert.Equal(ReleaseStatus.Dogrulandi, verified.Durum);
        Assert.Contains("manifest_version", verified.Manifest, StringComparison.Ordinal);
        Assert.Equal(["test-kucuk"], verified.Paketler!);
        Assert.Null(verified.YayinlandiAt);

        await harness.Releases.MarkPublishedAsync(row.Id, ct);
        Release published = (await harness.Releases.GetAsync(row.Id, ct))!;
        Assert.Equal(ReleaseStatus.Yayinlandi, published.Durum);
        Assert.Equal((DateTime?)harness.Clock.GetUtcNow().UtcDateTime, published.YayinlandiAt);

        await Assert.ThrowsAsync<InvalidOperationException>(() => harness.Releases.MarkFailedAsync(row.Id, "{}", ct));
        await harness.Releases.MarkWithdrawnAsync(row.Id, ct);
        Assert.Equal(ReleaseStatus.GeriCekildi, (await harness.Releases.GetAsync(row.Id, ct))!.Durum);
        await Assert.ThrowsAsync<InvalidOperationException>(() => harness.Releases.MarkPublishedAsync(row.Id, ct));
    }

    [Fact]
    public async Task Stores_request_fields_and_defaults_the_request_to_publish()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release source = await harness.Releases.CreateAsync(New(BuildFlavor.Internal), ct);

        Release promotion = await harness.Releases.CreateAsync(
            New(BuildFlavor.Public, source.Surum, ReleaseRequests.Terfi, source.Id, ["test-kucuk", "hadis-sentetik"], "terfi notu"),
            ct);

        Release read = (await harness.Releases.GetAsync(promotion.Id, ct))!;
        Assert.Equal((ReleaseRequests.Terfi, source.Id, "terfi notu"), (read.Talep, read.KaynakReleaseId, read.Notlar));
        Assert.Equal(["test-kucuk", "hadis-sentetik"], read.Paketler!);
        Assert.Equal(ReleaseRequests.Yayin, (await harness.Releases.GetAsync(source.Id, ct))!.Talep);
    }

    [Fact]
    public async Task Latest_published_orders_by_publication_time_and_can_exclude_a_row()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release first = await PublishedAsync(harness, BuildFlavor.Dev, ct);
        harness.Clock.Advance(TimeSpan.FromHours(1));
        Release second = await PublishedAsync(harness, BuildFlavor.Dev, ct);
        await PublishedAsync(harness, BuildFlavor.Internal, ct);

        Assert.Equal(second.Id, (await harness.Releases.LatestPublishedAsync(BuildFlavor.Dev, ct))!.Id);
        Assert.Equal(first.Id, (await harness.Releases.LatestPublishedAsync(BuildFlavor.Dev, second.Id, ct))!.Id);
        Assert.Null(await harness.Releases.LatestPublishedAsync(BuildFlavor.Public, ct));
    }

    [Fact]
    public async Task Find_open_returns_the_latest_unpublished_row_of_the_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release done = await PublishedAsync(harness, BuildFlavor.Dev, ct);
        Release open = await harness.Releases.CreateAsync(New(), ct);
        await harness.Releases.CreateAsync(New(BuildFlavor.Internal), ct);

        Assert.Equal(open.Id, (await harness.Releases.FindOpenAsync(BuildFlavor.Dev, ReleaseRequests.Yayin, ct))!.Id);
        Assert.Null(await harness.Releases.FindOpenAsync(BuildFlavor.Dev, ReleaseRequests.Terfi, ct));
        await harness.Releases.MarkFailedAsync(open.Id, "{}", ct);
        Assert.Null(await harness.Releases.FindOpenAsync(BuildFlavor.Dev, null, ct));
        Assert.NotEqual(done.Id, open.Id);
    }

    [Fact]
    public async Task Claim_takes_the_oldest_pending_row_and_skips_excluded_and_non_pending_rows()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release verified = await harness.Releases.CreateAsync(New(BuildFlavor.Dev), ct);
        await harness.Releases.MarkVerifiedAsync(verified.Id, "{}", "{}", "{}", null, ct);
        Release a = await harness.Releases.CreateAsync(New(BuildFlavor.Internal), ct);
        Release b = await harness.Releases.CreateAsync(New(BuildFlavor.Public, talep: ReleaseRequests.Terfi), ct);

        Release? first = await harness.Releases.ClaimNextPendingAsync(null, ct);
        Release? second = await harness.Releases.ClaimNextPendingAsync([a.Id], ct);
        Release? none = await harness.Releases.ClaimNextPendingAsync([a.Id, b.Id], ct);

        Assert.Equal(a.Id, first!.Id);
        Assert.Equal(b.Id, second!.Id);
        Assert.Equal(ReleaseRequests.Terfi, second.Talep);
        Assert.Null(none);
    }

    [Fact]
    public async Task Claim_skips_a_row_locked_by_another_transaction()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        Release locked = await harness.Releases.CreateAsync(New(BuildFlavor.Dev), ct);
        Release free = await harness.Releases.CreateAsync(New(BuildFlavor.Internal), ct);

        await using NpgsqlConnection connection = await harness.Database.OpenRawConnectionAsync(ct);
        await using NpgsqlTransaction transaction = await connection.BeginTransactionAsync(ct);
        await using (NpgsqlCommand command = new("SELECT id FROM icerik.release WHERE id = @id FOR UPDATE", connection, transaction))
        {
            command.Parameters.AddWithValue("id", locked.Id);
            await command.ExecuteScalarAsync(ct);
        }

        Release? claimed = await harness.Releases.ClaimNextPendingAsync(null, ct);

        Assert.Equal(free.Id, claimed!.Id);
        await transaction.RollbackAsync(ct);
    }

    private static async Task<Release> PublishedAsync(PublisherHarness harness, BuildFlavor flavor, CancellationToken ct)
    {
        Release row = await harness.Releases.CreateAsync(New(flavor), ct);
        await harness.Releases.MarkVerifiedAsync(row.Id, "{}", "{}", "{}", null, ct);
        await harness.Releases.MarkPublishedAsync(row.Id, ct);
        return (await harness.Releases.GetAsync(row.Id, ct))!;
    }
}
