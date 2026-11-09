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
        new(null, "q:1:4", GateReasons.CapaKayboldu + ":" + GateReasons.CapaSatirYok),
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
        + "{\"rule\":null,\"subject\":\"q:1:4\",\"reason\":\"capa-kayboldu:satir-yok\"},"
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

    private static GateViolation[] ManyLost(int lost, int other)
    {
        string reason = GateReasons.CapaKayboldu + ":" + GateReasons.CapaSatirYok;
        string otherReason = GateReasons.CapaKayboldu + ":onaysiz-birim";
        return
        [
            .. Enumerable.Range(1, lost).Select(i => new GateViolation(null, "q:2:" + i, reason)),
            .. Enumerable.Range(1, other).Select(i => new GateViolation(null, "q:3:" + i, otherReason)),
            new GateViolation(GateRule.P01, "kaynaksiz", GateReasons.KaynakKaydiYok),
        ];
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Violations_are_capped_per_reason_in_json_and_console_but_the_total_is_preserved(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateReport report = GateReport.Create(BuildFlavor.Public, [], ManyLost(lost: 1200, other: 50));

        // Tam liste ve toplam sayi korunur: reddetme karari ve ihlal= sayisi buradan.
        Assert.True(report.Rejected);
        Assert.Equal(1251, report.Violations.Count);

        // Gosterilen: satir-yok grubunda ilk 50 (konu sirasiyla), onaysiz-birim grubunda tamami (50), P-01 tek.
        Assert.Equal(101, report.ShownViolations.Count);
        Assert.Equal(50, report.ShownViolations.Count(v => v.Reason.EndsWith(":satir-yok", StringComparison.Ordinal)));
        GateViolationOmission omission = Assert.Single(report.OmittedViolations);
        Assert.Equal(((GateRule?)null, "capa-kayboldu:satir-yok", 1150), (omission.Rule, omission.Reason, omission.Count));
        Assert.Equal(report.Violations.Count, report.ShownViolations.Count + report.OmittedViolations.Sum(o => o.Count));

        using JsonDocument doc = JsonDocument.Parse(report.ToJson());
        JsonElement root = doc.RootElement;
        Assert.Equal(["flavor", "rejected", "rows", "violations", "violations_omitted"], root.EnumerateObject().Select(p => p.Name));
        Assert.Equal(101, root.GetProperty("violations").GetArrayLength());
        JsonElement omitted = Assert.Single(root.GetProperty("violations_omitted").EnumerateArray());
        Assert.Equal(["rule", "reason", "count"], omitted.EnumerateObject().Select(p => p.Name));
        Assert.Equal(JsonValueKind.Null, omitted.GetProperty("rule").ValueKind);
        Assert.Equal("capa-kayboldu:satir-yok", omitted.GetProperty("reason").GetString());
        Assert.Equal(1150, omitted.GetProperty("count").GetInt32());

        IReadOnlyList<string> lines = report.ViolationLines();
        Assert.Equal(101 + 1, lines.Count);
        Assert.Equal("  ve 1150 tane daha [-] capa-kayboldu:satir-yok", lines[^1]);
        Assert.Equal(1, lines.Count(l => l.StartsWith("  ve ", StringComparison.Ordinal)));
        Assert.Contains("  IHLAL [P-01] kaynaksiz: kaynak-kaydi-yok", lines);
        Assert.Equal(report.ToJson(), GateReport.Create(BuildFlavor.Public, [], ManyLost(1200, 50).Reverse()).ToJson());
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_report_at_the_cap_has_no_omission_field_and_keeps_the_old_shape(bool turkish) => CultureScope.For(turkish, () =>
    {
        GateReport report = GateReport.Create(BuildFlavor.Public, [], ManyLost(lost: GateReport.MaxViolationsShown, other: 0));

        Assert.Empty(report.OmittedViolations);
        using JsonDocument doc = JsonDocument.Parse(report.ToJson());
        Assert.Equal(["flavor", "rejected", "rows", "violations"], doc.RootElement.EnumerateObject().Select(p => p.Name));
        Assert.Equal(GateReport.MaxViolationsShown + 1, doc.RootElement.GetProperty("violations").GetArrayLength());
        Assert.DoesNotContain(report.ViolationLines(), l => l.Contains("tane daha", StringComparison.Ordinal));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Evaluator_caps_a_whole_source_gone_back_to_draft_and_still_rejects_with_the_full_count(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Bir kaynagin tamami taslaga dondu: 500 onceki capa public'te kaybolur (K-47 madde 2); karar ayni (reddet), cikti sinirli.
        string[] previous = [.. Enumerable.Range(1, 500).Select(i => "q:4:" + i)];
        GateInput input = new()
        {
            Sources = [Src(Regular)],
            Units = [.. previous.Select(a => Unit(a, status: Mutalaa.Domain.Content.TextStatus.Taslak))],
            PreviousAnchors = previous,
        };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, input);

        Assert.True(result.Rejected);
        Assert.Equal(500, result.Report.Violations.Count);
        Assert.Equal(GateReport.MaxViolationsShown, result.Report.ShownViolations.Count);
        Assert.Equal(450, Assert.Single(result.Report.OmittedViolations).Count);
        Assert.Contains("\"count\":450", result.Report.ToJson(), StringComparison.Ordinal);
        // Ilk 50 capa kararli sirada (ordinal): q:4:1, q:4:10, q:4:100, ...
        Assert.Equal("q:4:1", result.Report.ShownViolations[0].Subject);
        Assert.False(GateEvaluator.Evaluate(BuildFlavor.Dev, input).Rejected);
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
