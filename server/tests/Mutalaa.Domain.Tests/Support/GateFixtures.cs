using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>Kapi testleri icin sentetik girdi kurucular. Hicbir dini metin yoktur; capa ve slug yalniz kimliktir.</summary>
internal static class GateFixtures
{
    public const string Regular = "tanzil-uthmani";

    public const string Attribution = "Sentetik test verisi (Mutalaa).";

    public static GateSource Src(string slug, bool registered = true, string? attribution = Attribution) =>
        new(slug, attribution, registered);

    public static GateUnit Unit(
        string anchor,
        string source = Regular,
        TextStatus status = TextStatus.Onayli,
        bool aiDraft = false,
        UnitStatus unitStatus = UnitStatus.Etkin,
        bool hasSuccessors = false) =>
        new(anchor, source, status, aiDraft, unitStatus, hasSuccessors);

    public static Guid Id(int n) => new(n, 0, 0, [0, 0, 0, 0, 0, 0, 0, 0]);

    public static GateXref Xref(
        XrefType type,
        XrefStatus status,
        double confidence = 0.90,
        bool openReview = false,
        bool lexiconApproved = true,
        string src = Regular,
        string dst = Regular,
        bool separateIndex = false,
        int id = 1) =>
        new(Id(id), "q:1:1", "q:1:2", type, status, confidence, openReview, lexiconApproved, src, dst, separateIndex);

    public static GatePack Pack(string id, string[] sources, string[]? dependsOn = null, bool hasContent = true) =>
        new(id, dependsOn ?? [], sources, hasContent);

    public static GateInput WithRegularSource(
        IReadOnlyList<GateUnit>? units = null,
        IReadOnlyList<GateXref>? xrefs = null,
        IReadOnlyList<GateLexical>? lexicals = null) =>
        new()
        {
            Sources = [Src(Regular)],
            Units = units ?? [],
            Xrefs = xrefs ?? [],
            Lexicals = lexicals ?? [],
        };

    public static GateReportRow Single(GateResult result, GateSubjectKind kind) =>
        Assert.Single(result.Report.Rows, r => r.Kind == kind);

    public static GateReportRow Row(GateResult result, GateSubjectKind kind, string id) =>
        Assert.Single(result.Report.Rows, r => r.Kind == kind && string.Equals(r.Id, id, StringComparison.Ordinal));
}
