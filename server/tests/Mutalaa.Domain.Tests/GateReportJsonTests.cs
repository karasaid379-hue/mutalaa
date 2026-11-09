using System.Text.Json;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.GateFixtures;

namespace Mutalaa.Domain.Tests;

public class GateReportJsonTests
{
    private static GateReportRow[] SampleRows() =>
    [
        new(GateSubjectKind.Baglanti, "atif", GateDecision.Girmedi, GateRule.P07, GateReasons.AdayPublic, 2),
        new(GateSubjectKind.Kaynak, "test-kucuk", GateDecision.Girmedi, GateRule.P12, GateReasons.TestKaynagi),
        new(GateSubjectKind.Paket, "core", GateDecision.Girdi, null, GateReasons.Uygun),
        new(GateSubjectKind.Paket, "kelime-kok", GateDecision.Girmedi, null, GateReasons.IcerikYok),
        new(GateSubjectKind.Kaynak, "tanzil-uthmani", GateDecision.Girdi, null, GateReasons.Uygun),
        new(GateSubjectKind.Birim, "tanzil-uthmani", GateDecision.Girdi, null, GateReasons.Uygun, 6236),
    ];

    private static GateViolation[] SampleViolations() =>
    [
        new(GateRule.P13, "b", "kendine-bagimlilik"),
        new(null, "q:1:4", GateReasons.CapaKayip),
        new(GateRule.P01, "kaynaksiz", GateReasons.KaynakKaydiYok),
    ];

    private const string Expected =
        "{\"flavor\":\"public\",\"rejected\":true,\"rows\":["
        + "{\"kind\":\"paket\",\"id\":\"core\",\"decision\":\"girdi\",\"rule\":null,\"reason\":\"uygun\",\"count\":1},"
        + "{\"kind\":\"paket\",\"id\":\"kelime-kok\",\"decision\":\"girmedi\",\"rule\":null,\"reason\":\"icerik-yok\",\"count\":1},"
        + "{\"kind\":\"kaynak\",\"id\":\"tanzil-uthmani\",\"decision\":\"girdi\",\"rule\":null,\"reason\":\"uygun\",\"count\":1},"
        + "{\"kind\":\"kaynak\",\"id\":\"test-kucuk\",\"decision\":\"girmedi\",\"rule\":\"P-12\",\"reason\":\"test-oneki\",\"count\":1},"
        + "{\"kind\":\"birim\",\"id\":\"tanzil-uthmani\",\"decision\":\"girdi\",\"rule\":null,\"reason\":\"uygun\",\"count\":6236},"
        + "{\"kind\":\"baglanti\",\"id\":\"atif\",\"decision\":\"girmedi\",\"rule\":\"P-07\",\"reason\":\"aday-public\",\"count\":2}"
        + "],\"violations\":["
        + "{\"rule\":null,\"subject\":\"q:1:4\",\"reason\":\"capa-sureklilik-kayip\"},"
        + "{\"rule\":\"P-01\",\"subject\":\"kaynaksiz\",\"reason\":\"kaynak-kaydi-yok\"},"
        + "{\"rule\":\"P-13\",\"subject\":\"b\",\"reason\":\"kendine-bagimlilik\"}"
        + "]}";

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Json_is_snake_case_in_a_stable_order_whatever_the_input_order(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateReport forward = GateReport.Create(BuildFlavor.Public, SampleRows(), SampleViolations());
        GateReport reversed = GateReport.Create(BuildFlavor.Public, SampleRows().Reverse(), SampleViolations().Reverse());

        Assert.Equal(Expected, forward.ToJson());
        Assert.Equal(Expected, reversed.ToJson());
        Assert.Equal(forward.ToJson(), forward.ToJson());
        Assert.True(forward.Rejected);
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Empty_report_serializes_with_empty_arrays_and_is_not_rejected(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateReport report = GateReport.Create(BuildFlavor.Dev, [], []);

        Assert.False(report.Rejected);
        Assert.Equal("{\"flavor\":\"dev\",\"rejected\":false,\"rows\":[],\"violations\":[]}", report.ToJson());
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Json_parses_back_with_documented_property_names(bool turkish) => CultureScope.For(turkish, () =>
    {
        using JsonDocument doc = JsonDocument.Parse(GateReport.Create(BuildFlavor.Internal, SampleRows(), SampleViolations()).ToJson());
        JsonElement root = doc.RootElement;

        Assert.Equal(["flavor", "rejected", "rows", "violations"], root.EnumerateObject().Select(p => p.Name));
        Assert.Equal("internal", root.GetProperty("flavor").GetString());
        JsonElement first = root.GetProperty("rows")[0];
        Assert.Equal(["kind", "id", "decision", "rule", "reason", "count"], first.EnumerateObject().Select(p => p.Name));
        Assert.Equal(["rule", "subject", "reason"], root.GetProperty("violations")[0].EnumerateObject().Select(p => p.Name));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Same_input_gives_byte_identical_json_from_the_evaluator(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateInput Build(bool reverse)
        {
            GateSource[] sources = [Src(Regular), Src("test-kucuk"), Src("test-ses"), Src("test-tefsir-ornek")];
            GateUnit[] units = [Unit("q:1:1"), Unit("q:1:2", status: Mutalaa.Domain.Content.TextStatus.Taslak), Unit("k:test-kucuk:bolum-1:p1", source: "test-kucuk")];
            GatePack[] packs = [Pack("core", [Regular]), Pack("test-kucuk", ["test-kucuk"]), Pack("tefsir-test-ornek", ["test-tefsir-ornek"])];
            GateXref[] xrefs =
            [
                Xref(Mutalaa.Domain.Links.XrefType.Atif, Mutalaa.Domain.Links.XrefStatus.Aday, id: 1),
                Xref(Mutalaa.Domain.Links.XrefType.Kok, Mutalaa.Domain.Links.XrefStatus.Aday, 0.4, id: 2),
                Xref(Mutalaa.Domain.Links.XrefType.Kok, Mutalaa.Domain.Links.XrefStatus.Onayli, 0.4, id: 3),
            ];

            return new GateInput
            {
                Sources = reverse ? [.. sources.Reverse()] : sources,
                Units = reverse ? [.. units.Reverse()] : units,
                Packs = reverse ? [.. packs.Reverse()] : packs,
                Xrefs = reverse ? [.. xrefs.Reverse()] : xrefs,
            };
        }

        string a = GateEvaluator.Evaluate(BuildFlavor.Public, Build(false)).Report.ToJson();
        string b = GateEvaluator.Evaluate(BuildFlavor.Public, Build(true)).Report.ToJson();

        Assert.Equal(a, b);
        Assert.Contains("\"rule\":\"P-12\"", a, StringComparison.Ordinal);
        Assert.Contains("\"rule\":\"P-07\"", a, StringComparison.Ordinal);
        Assert.Contains("\"rule\":\"P-10\"", a, StringComparison.Ordinal);
    });
}
