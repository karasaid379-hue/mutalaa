using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

public class ReleaseTransitionsTests
{
    private static readonly ReleaseStatus[] All = Enum.GetValues<ReleaseStatus>();

    [Theory]
    [InlineData(ReleaseStatus.Hazirlaniyor, ReleaseStatus.Dogrulandi)]
    [InlineData(ReleaseStatus.Hazirlaniyor, ReleaseStatus.Basarisiz)]
    [InlineData(ReleaseStatus.Dogrulandi, ReleaseStatus.Yayinlandi)]
    [InlineData(ReleaseStatus.Dogrulandi, ReleaseStatus.Basarisiz)]
    [InlineData(ReleaseStatus.Yayinlandi, ReleaseStatus.GeriCekildi)]
    public void Allows_exactly_the_documented_transitions(ReleaseStatus from, ReleaseStatus to)
    {
        foreach (bool turkish in new[] { false, true })
        {
            CultureScope.For(turkish, () =>
            {
                Assert.True(ReleaseTransitions.CanTransition(from, to));
                ReleaseTransitions.Require(from, to);
            });
        }
    }

    [Fact]
    public void Refuses_every_other_transition_including_staying_in_place()
    {
        (ReleaseStatus, ReleaseStatus)[] allowed =
        [
            (ReleaseStatus.Hazirlaniyor, ReleaseStatus.Dogrulandi),
            (ReleaseStatus.Hazirlaniyor, ReleaseStatus.Basarisiz),
            (ReleaseStatus.Dogrulandi, ReleaseStatus.Yayinlandi),
            (ReleaseStatus.Dogrulandi, ReleaseStatus.Basarisiz),
            (ReleaseStatus.Yayinlandi, ReleaseStatus.GeriCekildi),
        ];

        foreach (ReleaseStatus from in All)
        {
            foreach (ReleaseStatus to in All)
            {
                if (!allowed.Contains((from, to)))
                {
                    Assert.False(ReleaseTransitions.CanTransition(from, to), $"{from} -> {to}");
                    Assert.Throws<InvalidOperationException>(() => ReleaseTransitions.Require(from, to));
                }
            }
        }
    }

    [Theory]
    [InlineData(ReleaseStatus.Hazirlaniyor, true)]
    [InlineData(ReleaseStatus.Dogrulandi, true)]
    [InlineData(ReleaseStatus.Yayinlandi, false)]
    [InlineData(ReleaseStatus.Basarisiz, false)]
    [InlineData(ReleaseStatus.GeriCekildi, false)]
    public void Open_means_preparing_or_verified(ReleaseStatus status, bool expected) =>
        Assert.Equal(expected, ReleaseTransitions.IsOpen(status));

    [Fact]
    public void WithViolations_adds_violations_keeps_rows_and_leaves_the_original_unchanged()
    {
        GateReport original = GateReport.Create(
            BuildFlavor.Public,
            [new GateReportRow(GateSubjectKind.Paket, "core", GateDecision.Girdi, null, GateReasons.Uygun)],
            []);

        GateReport merged = original.WithViolations([new GateViolation(GateRule.P11, "q:1:1", "hash-uyusmuyor"), new GateViolation(GateRule.P14, "x", "ozet-uyusmuyor")]);

        Assert.False(original.Rejected);
        Assert.True(merged.Rejected);
        Assert.Equal(original.Rows, merged.Rows);
        Assert.Equal(["P-11", "P-14"], merged.Violations.Select(v => v.Rule!.Value.ToCode()).ToArray());
        Assert.Equal(BuildFlavor.Public, merged.Flavor);
    }

    [Fact]
    public void WithViolations_with_nothing_to_add_is_byte_identical_json()
    {
        GateReport original = GateReport.Create(BuildFlavor.Dev, [], [new GateViolation(GateRule.P01, "a", "kaynak-kaydi-yok")]);

        Assert.Equal(original.ToJson(), original.WithViolations([]).ToJson());
    }
}
