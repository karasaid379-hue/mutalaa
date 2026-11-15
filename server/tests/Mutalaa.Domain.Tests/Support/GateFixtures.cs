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
        bool hasSuccessors = false,
        string? hash = null) =>
        new(anchor, source, status, aiDraft, unitStatus, hasSuccessors, hash);

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

    public static GatePack Pack(string id, string[] sources, string[]? dependsOn = null, bool hasContent = true, bool hasStructure = false) =>
        new(id, dependsOn ?? [], sources, hasContent, hasStructure);

    public static GateInput WithRegularSource(
        IReadOnlyList<GateUnit>? units = null,
        IReadOnlyList<GateXref>? xrefs = null,
        IReadOnlyList<GateLexical>? lexicals = null,
        IReadOnlyList<GateMeasurement>? gates = null) =>
        new()
        {
            Sources = [Src(Regular)],
            Units = units ?? [],
            Xrefs = xrefs ?? [],
            Lexicals = lexicals ?? [],
            Gates = gates ?? [],
        };

    /// <summary>
    /// xref_gate olcum satiri. Alt tur verilmezse turun baglanti kapisi alt turu kullanilir (kok: xref, benzer_ayet: sozluksel, digerleri bos);
    /// Turkce lemma kapisi icin <see cref="TrLemmaGate"/>, alim kapisi icin <see cref="AlimGate"/> kullanilir.
    /// </summary>
    public static GateMeasurement Gate(XrefType type, string setClass, string result, string? subType = null) =>
        new(type, setClass, result, subType ?? XrefGateRules.GateKeyOf(type, null, false).SubType);

    /// <summary>kok/tr_lemma kapisi (P-09: Turkce lemma eslemesinin olcumu).</summary>
    public static GateMeasurement TrLemmaGate(string setClass, string result) => Gate(XrefType.Kok, setClass, result, XrefGateSubtypes.TrLemma);

    /// <summary>benzer_ayet/alim kapisi (QurSim).</summary>
    public static GateMeasurement AlimGate(string setClass, string result) => Gate(XrefType.BenzerAyet, setClass, result, XrefGateSubtypes.Alim);

    /// <summary>Bes kapinin (kok/xref, kok/tr_lemma, lemma, benzer_ayet/sozluksel, benzer_ayet/alim) hepsi silver ile gecen hali (public'te otomatik satirlari acar).</summary>
    public static GateMeasurement[] OpenGates() =>
    [
        Gate(XrefType.Kok, "silver", "gecti"),
        TrLemmaGate("silver", "gecti"),
        Gate(XrefType.Lemma, "silver", "gecti"),
        Gate(XrefType.BenzerAyet, "silver", "gecti"),
        AlimGate("silver", "gecti"),
    ];

    public static GateReportRow Single(GateResult result, GateSubjectKind kind) =>
        Assert.Single(result.Report.Rows, r => r.Kind == kind);

    public static GateReportRow Row(GateResult result, GateSubjectKind kind, string id) =>
        Assert.Single(result.Report.Rows, r => r.Kind == kind && string.Equals(r.Id, id, StringComparison.Ordinal));
}
