using System.Text.Json.Nodes;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// shared/test-vectors/anchors altindaki ortak vektorler. Her Theory Invariant ve tr-TR kulturunde ayri kosar.
/// </summary>
public class AnchorVectorTests
{
    private const string ValidFile = "anchors/valid.jsonl";
    private const string InvalidFile = "anchors/invalid.jsonl";
    private const string CompareFile = "anchors/compare.jsonl";
    private const string ContainsFile = "anchors/contains.jsonl";
    private const string RouteFile = "anchors/route.jsonl";

    public static TheoryData<string> ValidIds => VectorFile.Ids(ValidFile);

    public static TheoryData<string> InvalidIds => VectorFile.Ids(InvalidFile);

    public static TheoryData<string> CompareIds => VectorFile.Ids(CompareFile);

    public static TheoryData<string> ContainsIds => VectorFile.Ids(ContainsFile);

    public static TheoryData<string> RouteIds => VectorFile.Ids(RouteFile);

    // ---- valid ----

    [Theory]
    [MemberData(nameof(ValidIds))]
    public void Valid_Invariant(string id) => CultureScope.Invariant(() => CheckValid(id));

    [Theory]
    [MemberData(nameof(ValidIds))]
    public void Valid_trTR(string id) => CultureScope.Turkish(() => CheckValid(id));

    private static void CheckValid(string id)
    {
        VectorCase v = VectorFile.Get(ValidFile, id);
        string input = v.Input!.GetValue<string>();
        JsonObject expected = v.Expected!.AsObject();

        AnchorRef r = AnchorRef.Parse(input);

        Assert.True(AnchorRef.TryParse(input, out AnchorRef? viaTry));
        Assert.Equal(r, viaTry);

        if (expected.TryGetPropertyValue("ref", out JsonNode? refNode))
        {
            AnchorJson.AssertSame(id, refNode, AnchorJson.Ref(r));
        }

        if (expected.TryGetPropertyValue("canonical", out JsonNode? canonical))
        {
            Assert.Equal(canonical!.GetValue<string>(), r.ToString());
            Assert.Equal(r, AnchorRef.Parse(r.ToString()));
        }

        if (expected.TryGetPropertyValue("unit", out JsonNode? unit))
        {
            Assert.Equal(unit!.GetValue<string>(), r.UnitOf().ToString());
        }

        if (expected.TryGetPropertyValue("unit_span", out JsonNode? unitSpan))
        {
            if (unitSpan is null)
            {
                Assert.Throws<InvalidOperationException>(() => r.ToUnitSpan());
            }
            else
            {
                AnchorJson.AssertSame(id, unitSpan, AnchorJson.UnitSpanJson(r.ToUnitSpan()));
            }
        }

        if (expected.TryGetPropertyValue("ayahs", out JsonNode? ayahs))
        {
            AnchorJson.AssertSame(id, ayahs, AnchorJson.Ayahs(r.CoveredAyahs()));
        }
    }

    // ---- invalid ----

    [Theory]
    [MemberData(nameof(InvalidIds))]
    public void Invalid_Invariant(string id) => CultureScope.Invariant(() => CheckInvalid(id));

    [Theory]
    [MemberData(nameof(InvalidIds))]
    public void Invalid_trTR(string id) => CultureScope.Turkish(() => CheckInvalid(id));

    private static void CheckInvalid(string id)
    {
        VectorCase v = VectorFile.Get(InvalidFile, id);
        string input = v.Input!.GetValue<string>();
        string expected = v.Expected!.GetValue<string>();

        AnchorException ex = Assert.Throws<AnchorException>(() => AnchorRef.Parse(input));
        Assert.Equal(expected, ex.CodeName);

        Assert.False(AnchorRef.TryParse(input, out AnchorRef? result));
        Assert.Null(result);
    }

    // ---- compare ----

    [Theory]
    [MemberData(nameof(CompareIds))]
    public void Compare_Invariant(string id) => CultureScope.Invariant(() => CheckCompare(id));

    [Theory]
    [MemberData(nameof(CompareIds))]
    public void Compare_trTR(string id) => CultureScope.Turkish(() => CheckCompare(id));

    private static void CheckCompare(string id)
    {
        VectorCase v = VectorFile.Get(CompareFile, id);
        JsonArray pair = v.Input!.AsArray();
        AnchorRef a = AnchorRef.Parse(pair[0]!.GetValue<string>());
        AnchorRef b = AnchorRef.Parse(pair[1]!.GetValue<string>());
        int expected = v.Expected!.GetValue<int>();

        Assert.Equal(expected, a.CompareTo(b));
        Assert.Equal(-expected, b.CompareTo(a));
        if (expected == 0)
        {
            Assert.Equal(a, b);
            Assert.Equal(a.GetHashCode(), b.GetHashCode());
        }
        else
        {
            Assert.NotEqual(a, b);
        }
    }

    // ---- contains ----

    [Theory]
    [MemberData(nameof(ContainsIds))]
    public void Contains_Invariant(string id) => CultureScope.Invariant(() => CheckContains(id));

    [Theory]
    [MemberData(nameof(ContainsIds))]
    public void Contains_trTR(string id) => CultureScope.Turkish(() => CheckContains(id));

    private static void CheckContains(string id)
    {
        VectorCase v = VectorFile.Get(ContainsFile, id);
        JsonArray pair = v.Input!.AsArray();
        AnchorRef outer = AnchorRef.Parse(pair[0]!.GetValue<string>());
        AnchorRef inner = AnchorRef.Parse(pair[1]!.GetValue<string>());

        Assert.Equal(v.Expected!.GetValue<bool>(), outer.Contains(inner));
    }

    // ---- route ----

    [Theory]
    [MemberData(nameof(RouteIds))]
    public void Route_Invariant(string id) => CultureScope.Invariant(() => CheckRoute(id));

    [Theory]
    [MemberData(nameof(RouteIds))]
    public void Route_trTR(string id) => CultureScope.Turkish(() => CheckRoute(id));

    private static void CheckRoute(string id)
    {
        VectorCase v = VectorFile.Get(RouteFile, id);
        JsonObject input = v.Input!.AsObject();
        JsonObject expected = v.Expected!.AsObject();
        AnchorRef r = AnchorRef.Parse(input["capa"]!.GetValue<string>());
        string? scheme = input["sema"]?.GetValue<string>();

        Assert.Equal(expected["native"]!.GetValue<string>(), r.ToRoute(RouteTarget.Native, scheme));

        JsonNode? web = expected["web"];
        if (web is null)
        {
            Assert.Throws<NotSupportedException>(() => r.ToRoute(RouteTarget.Web, scheme));
        }
        else
        {
            Assert.Equal(web.GetValue<string>(), r.ToRoute(RouteTarget.Web, scheme));
        }
    }
}
