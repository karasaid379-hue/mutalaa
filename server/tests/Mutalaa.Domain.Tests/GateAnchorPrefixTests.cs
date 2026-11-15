using Mutalaa.Domain.Content;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Capa onekli paketler (A20.4): birden cok paket tek kaynaktan beslenir (87 Risale kitabi, risale-rnk-metin). Paketin "icerik-yok" karari yalniz kendi onekli
/// birimlerine bakar; baska kitabin onayli birimi paketi sokmaz. Girdi sentetiktir (kitap slug'lari ve "p{n}" capalari yalniz kimliktir).
/// </summary>
public class GateAnchorPrefixTests
{
    private const string Shared = "risale-rnk-metin";

    private static GateInput Input(params GateUnit[] units) => new()
    {
        Sources = [GateFixtures.Src(Shared)],
        Units = units,
        Packs =
        [
            new GatePack("risale-aaa", [], [Shared], true, AnchorPrefix: "rn:aaa"),
            new GatePack("risale-bbb", [], [Shared], true, AnchorPrefix: "rn:bbb"),
        ],
    };

    private static GateUnit Unit(string anchor, TextStatus status) => GateFixtures.Unit(anchor, Shared, status);

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Public_enters_only_the_book_that_has_an_approved_unit(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            GateResult result = GateEvaluator.Evaluate(
                BuildFlavor.Public,
                Input(Unit("rn:aaa:bolum-1:p1", TextStatus.Onayli), Unit("rn:bbb:bolum-1:p1", TextStatus.Taslak)));

            Assert.Contains("risale-aaa", result.IncludedPacks);
            Assert.DoesNotContain("risale-bbb", result.IncludedPacks);
            GateReportRow other = GateFixtures.Row(result, GateSubjectKind.Paket, "risale-bbb");
            Assert.Equal((GateDecision.Girmedi, (GateRule?)null, GateReasons.IcerikYok), (other.Decision, other.Rule, other.Reason));
        });
    }

    [Fact]
    public void Dev_enters_both_books_when_each_has_a_unit_even_unapproved()
    {
        GateResult result = GateEvaluator.Evaluate(
            BuildFlavor.Dev,
            Input(Unit("rn:aaa:bolum-1:p1", TextStatus.Onayli), Unit("rn:bbb:bolum-1:p1", TextStatus.Taslak)));

        Assert.Equal(new[] { "risale-aaa", "risale-bbb" }, result.IncludedPacks.Order(StringComparer.Ordinal));
    }

    [Fact]
    public void A_prefixed_pack_without_any_unit_of_its_prefix_is_icerik_yok_even_when_the_shared_source_has_units()
    {
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, Input(Unit("rn:aaa:bolum-1:p1", TextStatus.Onayli)));

        Assert.Contains("risale-aaa", result.IncludedPacks);
        Assert.DoesNotContain("risale-bbb", result.IncludedPacks);
    }

    [Fact]
    public void A_longer_slug_sharing_the_leading_letters_is_not_the_same_book()
    {
        // rn:aaa-osmanlica ile rn:aaa: onek iki parcali capa onekidir ("rn:aaa-osmanlica" != "rn:aaa"), dizge basi degil.
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, Input(Unit("rn:aaa-osmanlica:bolum-1:p1", TextStatus.Onayli)));

        Assert.DoesNotContain("risale-aaa", result.IncludedPacks);
        Assert.DoesNotContain("risale-bbb", result.IncludedPacks);
    }

    [Fact]
    public void Packs_without_a_prefix_keep_the_source_level_counting()
    {
        GateInput input = new()
        {
            Sources = [GateFixtures.Src(GateFixtures.Regular)],
            Units = [GateFixtures.Unit("q:1:1")],
            Packs = [GateFixtures.Pack("core", [GateFixtures.Regular])],
        };

        Assert.Contains("core", GateEvaluator.Evaluate(BuildFlavor.Public, input).IncludedPacks);
    }

    [Fact]
    public void Prefix_of_keeps_the_first_two_segments()
    {
        Assert.Equal("rn:aaa", GatePack.PrefixOf("rn:aaa:bolum-1:p1:s2"));
        Assert.Equal("rn:aaa", GatePack.PrefixOf("rn:aaa:p1@0-5"));
        Assert.Equal("rn:aaa", GatePack.PrefixOf("rn:aaa"));
        Assert.Equal("konu", GatePack.PrefixOf("konu"));
        Assert.Throws<ArgumentNullException>(() => GatePack.PrefixOf(null!));
    }
}
