using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>Kapiya giren kaynak. Registered: hem pipeline/sources/{slug}.toml hem source satiri var. AtifMetni kaynak satirindan gelir.</summary>
public sealed record GateSource(string Slug, string? AtifMetni, bool Registered);

/// <summary>
/// Kapiya giren birim ozeti. Anchor kanonik capa dizgisidir (birim duzeyi); metin tasimaz.
/// IsAiDraft: yapay zeka urunu metin (provenance). HasSuccessors: kullanim disi birimin yonlendirmesi var.
/// HashPrefix: content_hash'in ilk 16 hanesi (K-51 madde 1; ofsetli satirlarin ozet denetimi); null ise ozet denetimi yapilmaz.
/// </summary>
public sealed record GateUnit(
    string Anchor,
    string SourceSlug,
    TextStatus TextStatus,
    bool IsAiDraft,
    UnitStatus Status,
    bool HasSuccessors,
    string? HashPrefix = null);

/// <summary>
/// Kapiya giren baglanti. Confidence double'dir: float sutun double'a "R" bicimiyle cevrilir (0,7 -> 0,699999988 olmasin).
/// LexiconApproved: evidence.lexicon_status onayli ya da alan yok. SrcSourceSlug ve DstSourceSlug uclarin eserinin kaynak slug'idir.
/// DstIsSeparateIndex: hedef, kaynak kaydi olan ayri bir dizine aittir (risale-atif-dizini); hedef eserin gorunurlugu aranmaz.
/// SrcHash ve DstHash: evidence.src_hash ve dst_hash (uc birimlerin content_hash ilk 16 hanesi; K-51 madde 1). Alan yoksa null: o uc denetlenmez.
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
    bool DstIsSeparateIndex,
    string? SrcHash = null,
    string? DstHash = null);

/// <summary>
/// Paket adayi. HasContent: pakete yazilacak veri var (yoksa "girmedi · icerik-yok", kural kodu yok). HasStructure: paket yapi satiri (kelime, isaret,
/// sayfa; core) tasiyor ve bu satirlar var; yapi satirlari birim suzmesinden (P-08/P-10) etkilenmeden paket icerigi sayilir. Geriye uyumlu: varsayilan false.
/// </summary>
public sealed record GatePack(
    string PackId,
    IReadOnlyList<string> DependsOn,
    IReadOnlyList<string> SourceSlugs,
    bool HasContent,
    bool HasStructure = false);

/// <summary>P-09 kapsamindaki sozluk ve duzeltme tablolari.</summary>
public enum LexicalKind
{
    QuranWordFix = 0,
    LemmaGloss = 1,
    TrRootIndex = 2,
    TrForm = 3,

    /// <summary>Turkce lemma (lemma tablosu, lang = 'tr'; K-51 madde 9). Pakette kelime-kok lemma satiri olur.</summary>
    TrLemma = 4,
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
        LexicalKind.TrLemma => "lemma_tr",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };
}

/// <summary>
/// P-09 satiri. quran_word_fix ve lemma_gloss durum sutunu tasir (Status). tr_root_index ve tr_form durum sutunu tasimaz,
/// yalniz onayli veri tasir; bagli Turkce lemma onayliysa girer (LinkedLemmaApproved).
/// ApplyDefect: yalniz quran_word_fix icin; duzeltme uygulanamiyorsa (deger alan turune cevrilemiyor, gosterdigi root_id ya da lemma_id yok,
/// kelime yok) kisa ASCII neden. Duzeltme bu derlemede uygulanacaksa (onayli) ve ApplyDefect doluysa yayin reddedilir (kural kodu yok).
/// K-51 madde 1 ve 9 alanlari (hepsi isteye bagli, varsayilan bos):
/// LemmaId: TrLemma satirinda lemma kimligi, TrRootIndex ve TrForm satirinda bagli Turkce lemmanin kimligi (kapi, bagli lemmanin kararini izler).
/// OnayYolu ve HasKanit: yalniz TrLemma; onay_yolu ("editor" ya da "otomatik") ve kanit sutununun bir nesne olup olmadigi.
/// UnitAnchor ve UnitHash: yalniz TrRootIndex; satirin birimi ve satir uretilirken kaydedilen content_hash ilk 16 hanesi (ozet denetimi, "ozet-tutmadi").
/// </summary>
public sealed record GateLexical(
    LexicalKind Kind,
    string Id,
    XrefStatus? Status,
    bool LinkedLemmaApproved,
    string? ApplyDefect = null,
    int? LemmaId = null,
    string? OnayYolu = null,
    bool HasKanit = false,
    string? UnitAnchor = null,
    string? UnitHash = null);

/// <summary>
/// xref_gate satiri (K-51 madde 5 ve 11): bir turun bir set sinifi icin son olcum sonucu. SetClass altin, silver ya da sentetik; Result gecti ya da kaldi.
/// Bilinmeyen sinif ve sonuc dizgileri kapi acmaz (olculmemis sayilir).
/// </summary>
public sealed record GateMeasurement(XrefType Type, string SetClass, string Result);

/// <summary>Kapi girdisi (Yayin sureci 2). Tum liste alanlari varsayilan bostur.</summary>
public sealed record GateInput
{
    public IReadOnlyList<GateSource> Sources { get; init; } = [];

    public IReadOnlyList<GateUnit> Units { get; init; } = [];

    public IReadOnlyList<GateXref> Xrefs { get; init; } = [];

    public IReadOnlyList<GatePack> Packs { get; init; } = [];

    public IReadOnlyList<GateLexical> Lexicals { get; init; } = [];

    /// <summary>xref_gate satirlari (tur bazinda olcum sonuclari; K-51 madde 5). Bos ise hicbir tur olculmemistir.</summary>
    public IReadOnlyList<GateMeasurement> Gates { get; init; } = [];

    /// <summary>
    /// Onceki surumden manifeste tasinan (bu calistirmada yeniden uretilmeyen) paket kimlikleri. P-13 manifest kumesi
    /// = kapidan giren paketler + bunlar.
    /// </summary>
    public IReadOnlyCollection<string> CarriedPackIds { get; init; } = [];

    /// <summary>Onceki yayinin butun capalari (Yayin sureci 4 madde 2; kural kodu yok). Bos ise sureklilik denetlenmez.</summary>
    public IReadOnlyCollection<string> PreviousAnchors { get; init; } = [];
}
