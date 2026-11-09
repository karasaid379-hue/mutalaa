using Mutalaa.Api.Tests.Support;
using Mutalaa.Publisher.Tests.Support;
using Npgsql;

namespace Mutalaa.Publisher.Tests;

/// <summary>PublisherLock (Docker): pg_try_advisory_lock, ayri havuzsuz baglanti; ikinci tutucu alamaz, birakilinca alinir.</summary>
public class PublisherLockTests(PostgresFixture postgres)
{
    [Fact]
    public async Task A_second_holder_cannot_acquire_the_lock_until_the_first_releases_it()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        string connectionString = harness.Database.ConnectionString;

        await using PublisherLock? first = await PublisherLock.TryAcquireAsync(connectionString, ct);
        Assert.NotNull(first);

        PublisherLock? second = await PublisherLock.TryAcquireAsync(connectionString, ct);
        Assert.Null(second);

        await first.DisposeAsync();
        await using PublisherLock? third = await PublisherLock.TryAcquireAsync(connectionString, ct);
        Assert.NotNull(third);
    }

    [Fact]
    public async Task The_lock_survives_pooled_connection_use_on_the_same_database()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false);
        await using PublisherLock? held = await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct);
        Assert.NotNull(held);

        // Havuzlu baglantilar acilip kapansa da kilit ayri baglantida kalir.
        for (int i = 0; i < 3; i++)
        {
            await using NpgsqlConnection pooled = new(harness.Database.ConnectionString);
            await pooled.OpenAsync(ct);
        }

        Assert.Null(await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct));
    }

    [Fact]
    public async Task A_second_publisher_command_exits_with_1_while_the_lock_is_held()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await using PublisherLock? held = await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct);
        Assert.NotNull(held);

        int code = await new Commands.PublishCommand(harness.Context).RunAsync(new Pipeline.PublishRequest(Mutalaa.Domain.Releases.BuildFlavor.Dev, []), ct);

        Assert.Equal(1, code);
        Assert.Contains("danisma kilidi", harness.Error.ToString(), StringComparison.Ordinal);
        Assert.Equal(0, await harness.CountReleasesAsync(ct));
        Assert.Empty(harness.Store.Writes);
    }

    [Fact]
    public async Task Dry_run_does_not_take_the_lock()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);
        await using PublisherLock? held = await PublisherLock.TryAcquireAsync(harness.Database.ConnectionString, ct);
        Assert.NotNull(held);

        int code = await new Commands.PublishCommand(harness.Context).RunAsync(
            new Pipeline.PublishRequest(Mutalaa.Domain.Releases.BuildFlavor.Dev, [], DryRun: true), ct);

        Assert.Equal(0, code);
    }
}
