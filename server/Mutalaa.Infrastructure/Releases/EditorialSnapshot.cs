using Mutalaa.Domain.Releases.Gate;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// source satiri (Editoryal veritabani 3): betimleyici alanlar, atif ve kaynagin kendi bildirimi. Enum sutunlari etiket metnidir;
/// capa sutunlari AnchorRef degil ham metindir.
/// </summary>
public sealed record SourceRow(
    string Slug,
    string Tur,
    string Baslik,
    string? Yazar,
    string Surum,
    string? Provider,
    string? KaynakUrl,
    DateOnly? AlinmaTarihi,
    string? DosyaSha256,
    string? BaskiBilgisi,
    string AtifMetni,
    string? AtifUrl,
    string? NoticeText,
    string? Notlar);

/// <summary>
/// unit satiri (tsv_tr, tsv_ar ve tr_narrow okunmaz). AyahLo ve AyahHi editoryal yari acik aralik [lo, hi) sinirlaridir.
/// SentencesJson: int4range[] dizisi "[[bas, son], ...]" jsonb metni (aralik yoksa null). IsAiDraft: birimin yz_modeli dolu bir
/// review satiri var (yapay zeka taslagi; yalniz onaysiz birimde anlamlidir).
/// </summary>
public sealed record UnitRow(
    string Anchor,
    string Kind,
    string Role,
    string SourceId,
    string? ParentPath,
    long Ord,
    int? AyahLo,
    int? AyahHi,
    string Metin,
    string Marks,
    string? SentencesJson,
    string Attrs,
    string ContentHash,
    string MetinDurumu,
    string Status,
    string? Successors,
    string? TrWide,
    string? TrStem,
    string? ArNorm,
    bool IsAiDraft);

/// <summary>
/// quran_word satiri (Tanzil kelime bolmesi). RootId, LemmaId, Pos, Features (jsonb metni) ve MorphSource QAC sutunlaridir (K-50 madde 3); yalniz
/// morph_source sozluk kaynaklarindan biriyse (PackCatalog.LexiconSourceSlugs) okunur, aksi halde bostur. core paketi bu sutunlari kullanmaz.
/// </summary>
public sealed record QuranWordRow(
    string Anchor,
    int Surah,
    int Ayah,
    int Word,
    int AyahIndex,
    string TextUthmani,
    string Norm,
    int CharStart,
    int CharEnd,
    string SourceId,
    int? RootId = null,
    int? LemmaId = null,
    string? Pos = null,
    string? Features = null,
    string? MorphSource = null);

/// <summary>root satiri (QAC koku; durum ve koken sutunu yoktur, K-50 madde 4). IdfQ real (float) sutundur.</summary>
public sealed record RootRow(int Id, string Letters, int Occurrences, int AyahCount, float? IdfQ, string? KokAnlami, string SourceId);

/// <summary>lemma satiri (lang = 'ar' okunur). Status onayli/aday/red metnidir; pakete yalniz onayli girer.</summary>
public sealed record LemmaRow(
    int Id,
    string Text,
    string TextClean,
    int? RootId,
    int Occurrences,
    int? ArLemmaId,
    bool EtymologicalOnly,
    string Status,
    string SourceId);

/// <summary>lemma_gloss satiri (Arapca lemmaya bagli, sozluk kaynakli). KuranAnlamlari jsonb metnidir.</summary>
public sealed record LemmaGlossRow(
    int LemmaId,
    string AnlamKisa,
    string KuranAnlamlari,
    string? TurkceEsKelime,
    bool YalnizcaEtimolojik,
    string Status,
    string Origin,
    string Version);

/// <summary>quran_word_fix satiri (K-50 madde 4 ve 6): Field root_id, lemma_id, pos ya da features; NewValue metindir (alan turune cevrilir).</summary>
public sealed record QuranWordFixRow(Guid Id, string Anchor, string Field, string NewValue, string Status);

/// <summary>quran_marker satiri.</summary>
public sealed record QuranMarkerRow(string Kind, int No, string Anchor, string? SecdeTuru, string SourceId);

/// <summary>page_map satiri (Line, kaynak duzene gore bos olabilir).</summary>
public sealed record PageMapRow(
    string SourceId,
    int? Volume,
    int Page,
    int? Line,
    string StartAnchor,
    int? StartOffset,
    string EndAnchor,
    int? EndOffset);

/// <summary>
/// xref satiri. Uc araliklari editoryal yari acik int4range sinirlaridir (bos ise null). Score ve Confidence real (float) sutunlardir.
/// LexiconStatus: evidence.lexicon_status (alan yoksa null).
/// </summary>
public sealed record XrefRow(
    Guid Id,
    string SrcAnchor,
    int? SrcLo,
    int? SrcHi,
    string DstAnchor,
    int? DstLo,
    int? DstHi,
    string Type,
    float Score,
    float Confidence,
    string Evidence,
    string Status,
    string DataVersion,
    string? LexiconStatus);

/// <summary>
/// P-09 kapsamindaki satir: quran_word_fix ve lemma_gloss durum sutunu (Status) tasir; tr_root_index ve tr_form durum sutunu tasimaz
/// (LinkedLemmaApproved: bagli Turkce lemma onayli). Id anahtari: quran_word_fix id, lemma_gloss lemma_id, tr_root_index "anchor|span_start",
/// tr_form "key_narrow|tr_lemma_id".
/// </summary>
public sealed record LexicalRow(LexicalKind Kind, string Id, string? Status, bool LinkedLemmaApproved);

/// <summary>Bir derleme turunun en son yayinlandi satiri. Manifest ve Ozetler jsonb metnidir.</summary>
public sealed record PreviousReleaseRow(int Id, string Surum, string? Manifest, string Ozetler, DateTime? YayinlandiAt);

/// <summary>
/// Tek REPEATABLE READ islemden okunmus editoryal anlik goruntu. Buyuk listeler (Units, QuranWords, Xrefs) akisla okunur ve burada
/// toplanir (bellek: satirlar kadar; A13 ilk yayinda 6.236 birim ve 77.429 kelime).
/// </summary>
public sealed class EditorialSnapshot
{
    public IReadOnlyList<SourceRow> Sources { get; init; } = [];

    public IReadOnlyList<UnitRow> Units { get; init; } = [];

    public IReadOnlyList<QuranWordRow> QuranWords { get; init; } = [];

    public IReadOnlyList<QuranMarkerRow> QuranMarkers { get; init; } = [];

    public IReadOnlyList<PageMapRow> PageMaps { get; init; } = [];

    public IReadOnlyList<XrefRow> Xrefs { get; init; } = [];

    /// <summary>Acik review satiri olan baglantilar (public icin P-07 ek kosulu).</summary>
    public IReadOnlySet<Guid> OpenReviewXrefIds { get; init; } = new HashSet<Guid>();

    public IReadOnlyList<LexicalRow> Lexicals { get; init; } = [];

    /// <summary>QAC kokleri (yalniz sozluk kaynaklari; kelime-kok paketi).</summary>
    public IReadOnlyList<RootRow> Roots { get; init; } = [];

    /// <summary>Arapca lemmalar (lang = 'ar'; yalniz sozluk kaynaklari).</summary>
    public IReadOnlyList<LemmaRow> Lemmas { get; init; } = [];

    /// <summary>Arapca sozluk lemmalarina bagli kelime anlamlari (butun durumlar; kapi derleme turune gore secer).</summary>
    public IReadOnlyList<LemmaGlossRow> LemmaGlosses { get; init; } = [];

    /// <summary>Butun quran_word_fix satirlari (durum ne olursa olsun; kapi yalniz onayliyi uygular).</summary>
    public IReadOnlyList<QuranWordFixRow> WordFixes { get; init; } = [];

    /// <summary>Istenen derleme turunun en son yayinlandi yayini; yoksa null.</summary>
    public PreviousReleaseRow? PreviousRelease { get; init; }
}
