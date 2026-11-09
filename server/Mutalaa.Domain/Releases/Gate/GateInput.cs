using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>Kapiya giren kaynak. Registered: hem pipeline/sources/{slug}.toml hem source satiri var. AtifMetni kaynak satirindan gelir.</summary>
public sealed record GateSource(string Slug, string? AtifMetni, bool Registered);

/// <summary>
/// Kapiya giren birim ozeti. Anchor kanonik capa dizgisidir (birim duzeyi); metin tasimaz.
/// IsAiDraft: yapay zeka urunu metin (provenance). HasSuccessors: kullanim disi birimin yonlendirmesi var.
/// </summary>
public sealed record GateUnit(
    string Anchor,
    string SourceSlug,
    TextStatus TextStatus,
    bool IsAiDraft,
    UnitStatus Status,
    bool HasSuccessors);

/// <summary>
/// Kapiya giren baglanti. Confidence double'dir: float sutun double'a "R" bicimiyle cevrilir (0,7 -> 0,699999988 olmasin).
/// LexiconApproved: evidence.lexicon_status onayli ya da alan yok. SrcSourceSlug ve DstSourceSlug uclarin eserinin kaynak slug'idir.
/// DstIsSeparateIndex: hedef, kaynak kaydi olan ayri bir dizine aittir (risale-atif-dizini); hedef eserin gorunurlugu aranmaz.
/// </summary>
public sealed record GateXref(
    Guid Id,
    string SrcAnchor,
    string DstAnchor,
    XrefType Type,
    XrefStatus Status,
    double Confidence,
    bool HasOpenReview,
    bool LexiconApproved,
    string SrcSourceSlug,
    string DstSourceSlug,
    bool DstIsSeparateIndex);

/// <summary>Paket adayi. HasContent: pakete yazilacak veri var (yoksa "girmedi · icerik-yok", kural kodu yok).</summary>
public sealed record GatePack(
    string PackId,
    IReadOnlyList<string> DependsOn,
    IReadOnlyList<string> SourceSlugs,
    bool HasContent);

/// <summary>P-09 kapsamindaki sozluk ve duzeltme tablolari.</summary>
public enum LexicalKind
{
    QuranWordFix = 0,
    LemmaGloss = 1,
    TrRootIndex = 2,
    TrForm = 3,
}

/// <summary>LexicalKind icin tablo etiketi (rapor satiri kimligi). Acik switch; tanimsiz deger ArgumentOutOfRangeException atar.</summary>
public static class LexicalKindLabels
{
    public static string ToLabel(this LexicalKind value) => value switch
    {
        LexicalKind.QuranWordFix => "quran_word_fix",
        LexicalKind.LemmaGloss => "lemma_gloss",
        LexicalKind.TrRootIndex => "tr_root_index",
        LexicalKind.TrForm => "tr_form",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };
}

/// <summary>
/// P-09 satiri. quran_word_fix ve lemma_gloss durum sutunu tasir (Status). tr_root_index ve tr_form durum sutunu tasimaz,
/// yalniz onayli veri tasir; bagli Turkce lemma onayliysa girer (LinkedLemmaApproved).
/// </summary>
public sealed record GateLexical(LexicalKind Kind, string Id, XrefStatus? Status, bool LinkedLemmaApproved);

/// <summary>Kapi girdisi (Yayin sureci 2). Tum liste alanlari varsayilan bostur.</summary>
public sealed record GateInput
{
    public IReadOnlyList<GateSource> Sources { get; init; } = [];

    public IReadOnlyList<GateUnit> Units { get; init; } = [];

    public IReadOnlyList<GateXref> Xrefs { get; init; } = [];

    public IReadOnlyList<GatePack> Packs { get; init; } = [];

    public IReadOnlyList<GateLexical> Lexicals { get; init; } = [];

    /// <summary>
    /// Onceki surumden manifeste tasinan (bu calistirmada yeniden uretilmeyen) paket kimlikleri. P-13 manifest kumesi
    /// = kapidan giren paketler + bunlar.
    /// </summary>
    public IReadOnlyCollection<string> CarriedPackIds { get; init; } = [];

    /// <summary>Onceki yayinin butun capalari (Yayin sureci 4 madde 2; kural kodu yok). Bos ise sureklilik denetlenmez.</summary>
    public IReadOnlyCollection<string> PreviousAnchors { get; init; } = [];
}
