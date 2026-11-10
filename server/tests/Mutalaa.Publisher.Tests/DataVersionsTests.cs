using System.Text.RegularExpressions;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>DataVersions: data_version = YYYY.MM.DD-{git kisa sha | nogit}; saat TimeProvider'dan, tarih UTC.</summary>
public partial class DataVersionsTests
{
    [GeneratedRegex("^[0-9]{4}\\.[0-9]{2}\\.[0-9]{2}-(nogit|[0-9a-f]{4,40})$", RegexOptions.CultureInvariant)]
    private static partial Regex Shape();

    [Fact]
    public async Task Formats_the_date_in_utc_with_the_injected_sha()
    {
        FixedClock clock = new(new DateTimeOffset(2026, 11, 9, 23, 30, 0, TimeSpan.FromHours(-3)));

        string value = await DataVersions.CurrentAsync(clock, _ => Task.FromResult("abc1234"), TestContext.Current.CancellationToken);

        Assert.Equal("2026.11.10-abc1234", value);
    }

    [Fact]
    public async Task Uses_nogit_when_git_is_not_available()
    {
        FixedClock clock = new(new DateTimeOffset(2026, 1, 5, 12, 0, 0, TimeSpan.Zero));

        string value = await DataVersions.CurrentAsync(clock, _ => Task.FromResult(DataVersions.NoGit), TestContext.Current.CancellationToken);

        Assert.Equal("2026.01.05-nogit", value);
        Assert.Matches(Shape(), value);
    }

    [Fact]
    public async Task The_default_git_probe_returns_a_short_sha_or_nogit()
    {
        string sha = await DataVersions.ShortShaAsync(TestContext.Current.CancellationToken);

        Assert.Matches("^(nogit|[0-9a-f]{4,40})$", sha);
    }

    [Fact]
    public async Task The_default_current_value_matches_the_documented_shape()
    {
        FixedClock clock = new(new DateTimeOffset(2026, 11, 9, 12, 0, 0, TimeSpan.Zero));

        string value = await DataVersions.CurrentAsync(clock, null, TestContext.Current.CancellationToken);

        Assert.Matches(Shape(), value);
        Assert.StartsWith("2026.11.09-", value, StringComparison.Ordinal);
    }
}
