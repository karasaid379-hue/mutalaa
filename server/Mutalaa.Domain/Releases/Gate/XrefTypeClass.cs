using System.Collections.Immutable;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Baglanti turu siniflari ve P-07 esikleri (Baglanti modeli 6 ve 8; Yayin sureci 2.3).
/// Insan onayi isteyen turler ile otomatik turler ayri kumelerdir; her tur tam bir kumeye aittir.
/// </summary>
public static class XrefTypeClass
{
    /// <summary>Otomatik turde aday baglantinin pakete girmesi icin alt sinir (dahil).</summary>
    public const double ConfidenceMin = 0.50;

    /// <summary>Otomatik turde onaysiz baglantinin katli (folded) sayildigi sinir (bu degerin alti katlidir).</summary>
    public const double FoldBelow = 0.70;

    public static ImmutableArray<XrefType> HumanApprovalTypes { get; } =
        [XrefType.Atif, XrefType.Iktibas, XrefType.Ima, XrefType.Konu];

    public static ImmutableArray<XrefType> AutomaticTypes { get; } =
        [XrefType.Kok, XrefType.Lemma, XrefType.BenzerAyet, XrefType.Anlamsal];

    /// <summary>atif, iktibas, ima, konu. Tanimsiz deger false.</summary>
    public static bool RequiresHumanApproval(XrefType type) =>
        type is XrefType.Atif or XrefType.Iktibas or XrefType.Ima or XrefType.Konu;

    /// <summary>kok, lemma, benzer_ayet, anlamsal. Tanimsiz deger false.</summary>
    public static bool IsAutomatic(XrefType type) =>
        type is XrefType.Kok or XrefType.Lemma or XrefType.BenzerAyet or XrefType.Anlamsal;

    /// <summary>Public derlemede Turkce sozluk girdisinin onayini isteyen turler (kok, lemma).</summary>
    public static bool RequiresLexiconApproval(XrefType type) => type is XrefType.Kok or XrefType.Lemma;
}
