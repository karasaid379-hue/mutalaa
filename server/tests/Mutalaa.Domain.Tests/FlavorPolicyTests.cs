using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Backend API 7 A13 notu: TryParseLabel basarisizken out degeri Dev'dir; ayristirilamayan etiket en kisitlayici tur (public) sayilir.
/// </summary>
public class FlavorPolicyTests
{
    [Theory]
    [InlineData(null, BuildFlavor.Public, false)]
    [InlineData("", BuildFlavor.Public, false)]
    [InlineData("Public", BuildFlavor.Public, false)]
    [InlineData("dev ", BuildFlavor.Public, false)]
    [InlineData(" dev", BuildFlavor.Public, false)]
    [InlineData("DEV", BuildFlavor.Public, false)]
    [InlineData("Dev", BuildFlavor.Public, false)]
    [InlineData("INTERNAL", BuildFlavor.Public, false)]
    [InlineData("internal ", BuildFlavor.Public, false)]
    [InlineData("staging", BuildFlavor.Public, false)]
    [InlineData("dev", BuildFlavor.Dev, true)]
    [InlineData("internal", BuildFlavor.Internal, true)]
    [InlineData("public", BuildFlavor.Public, true)]
    public void ParseOrMostRestrictive_under_invariant_culture(string? label, BuildFlavor expected, bool parseable) =>
        CultureScope.Invariant(() => Assert_(label, expected, parseable));

    [Theory]
    [InlineData(null, BuildFlavor.Public, false)]
    [InlineData("", BuildFlavor.Public, false)]
    [InlineData("Public", BuildFlavor.Public, false)]
    [InlineData("dev ", BuildFlavor.Public, false)]
    [InlineData(" dev", BuildFlavor.Public, false)]
    [InlineData("DEV", BuildFlavor.Public, false)]
    [InlineData("Dev", BuildFlavor.Public, false)]
    [InlineData("INTERNAL", BuildFlavor.Public, false)]
    [InlineData("internal ", BuildFlavor.Public, false)]
    [InlineData("staging", BuildFlavor.Public, false)]
    [InlineData("dev", BuildFlavor.Dev, true)]
    [InlineData("internal", BuildFlavor.Internal, true)]
    [InlineData("public", BuildFlavor.Public, true)]
    public void ParseOrMostRestrictive_under_turkish_culture(string? label, BuildFlavor expected, bool parseable) =>
        CultureScope.Turkish(() => Assert_(label, expected, parseable));

    private static void Assert_(string? label, BuildFlavor expected, bool parseable)
    {
        Assert.Equal(parseable, BuildFlavorLabels.TryParseLabel(label, out _));
        Assert.Equal(expected, FlavorPolicy.ParseOrMostRestrictive(label));
    }

    [Fact]
    public void Failed_parse_leaves_the_loosest_flavor_in_the_out_value_which_is_why_the_bool_is_checked()
    {
        Assert.False(BuildFlavorLabels.TryParseLabel("garbage", out BuildFlavor naive));

        Assert.Equal(BuildFlavor.Dev, naive);
        Assert.NotEqual(naive, FlavorPolicy.ParseOrMostRestrictive("garbage"));
    }

    [Fact]
    public void Normalize_maps_undefined_values_to_public()
    {
        Assert.Equal(BuildFlavor.Dev, FlavorPolicy.Normalize(BuildFlavor.Dev));
        Assert.Equal(BuildFlavor.Internal, FlavorPolicy.Normalize(BuildFlavor.Internal));
        Assert.Equal(BuildFlavor.Public, FlavorPolicy.Normalize(BuildFlavor.Public));
        Assert.Equal(BuildFlavor.Public, FlavorPolicy.Normalize((BuildFlavor)(-1)));
        Assert.Equal(BuildFlavor.Public, FlavorPolicy.Normalize((BuildFlavor)3));
    }

    [Fact]
    public void Unapproved_units_are_allowed_only_outside_public()
    {
        Assert.True(FlavorPolicy.AllowsUnapprovedUnits(BuildFlavor.Dev));
        Assert.True(FlavorPolicy.AllowsUnapprovedUnits(BuildFlavor.Internal));
        Assert.False(FlavorPolicy.AllowsUnapprovedUnits(BuildFlavor.Public));
        Assert.False(FlavorPolicy.AllowsUnapprovedUnits((BuildFlavor)77));
    }

    [Fact]
    public void Candidate_glosses_are_allowed_only_outside_public()
    {
        Assert.True(FlavorPolicy.AllowsCandidateGlosses(BuildFlavor.Dev));
        Assert.True(FlavorPolicy.AllowsCandidateGlosses(BuildFlavor.Internal));
        Assert.False(FlavorPolicy.AllowsCandidateGlosses(BuildFlavor.Public));
        Assert.False(FlavorPolicy.AllowsCandidateGlosses((BuildFlavor)77));
    }

    [Fact]
    public void Release_request_constants_match_the_documented_values()
    {
        Assert.Equal(["yayin", "terfi", "geri_alma"], ReleaseRequests.All);
        Assert.True(ReleaseRequests.IsValid("terfi"));
        Assert.False(ReleaseRequests.IsValid("Terfi"));
        Assert.False(ReleaseRequests.IsValid("geri-alma"));
        Assert.False(ReleaseRequests.IsValid(null));
    }
}
