using Mutalaa.Domain.Releases;

namespace Mutalaa.Infrastructure.Packs;

// Paket satir kayitlari (Icerik paketleri 3). Sutun adlari ve sirasi PackTables'tadir. Tam sayilar long (SQLite INTEGER), gercek sayilar double (REAL).
// unit tablosunda rowid yoktur (yazici capa sirasina gore 1..n verir); unit_search satiri capa ile anahtarlanir.

public sealed record PackSourceRow(string SourceId);

/// <summary>attribution satiri: baslik -> Title, surum -> Version, atif_url ?? kaynak_url -> SourceUrl, atif_metni -> RequiredCredit, notice_text aynen.</summary>
public sealed record PackAttributionRow(string SourceId, string Title, string? Version, string? SourceUrl, string RequiredCredit, string? NoticeText);

/// <summary>unit satiri. Text editoryal metin'dir, AYNEN (Tanzil bayt bayt). AyahLast pakette kapali aralik sinirdir (editoryal hi - 1).</summary>
public sealed record PackUnitRow(
    string Anchor,
    string Kind,
    string Role,
    string? ParentPath,
    long Ord,
    long? AyahFirst,
    long? AyahLast,
    string Label,
    string Text,
    string? Marks,
    string? Sentences,
    string? Attrs,
    string ContentHash,
    string Status,
    long Approved,
    string? Successors);

public sealed record PackUnitSearchRow(string Anchor, string? TrWide, string? TrStem, string? ArNorm);

/// <summary>xref_idx satiri. Start/End editoryal yari acik aralik sinirlari aynen (src_start = lower, src_end = upper).</summary>
public sealed record PackXrefRow(
    string Id,
    string SrcAnchor,
    long? SrcStart,
    long? SrcEnd,
    string DstAnchor,
    long? DstStart,
    long? DstEnd,
    string Type,
    double Score,
    double Confidence,
    long Approved,
    long Folded,
    string Evidence,
    string DataVersion);

public sealed record PackQuranWordRow(string Anchor, long AyahIndex, long Word, string TextUthmani, string Norm, long CharStart, long CharEnd);

public sealed record PackQuranMarkerRow(string Kind, long No, string Anchor, string? SecdeTuru);

public sealed record PackPageMapRow(string Layout, long? Volume, long Page, long? Line, string StartAnchor, long? StartOffset, string EndAnchor, long? EndOffset);

/// <summary>sure satiri. A13'te sure adlari onayli degildir (Ad uydurulmaz): tablo bos kalir.</summary>
public sealed record PackSureRow(long No, string Name, string NameAr, long AyahCount, string Variants);

public sealed record PackTrRootIndexRow(string Anchor, long SpanStart, long SpanEnd, long RootId, long TrLemmaId, long EtymologicalOnly);

/// <summary>word_morph satiri (kelime-kok): QAC tabani uzerine onayli quran_word_fix duzeltmeleri uygulanmis hali. Features kanonik (RFC 8785) JSON metnidir.</summary>
public sealed record PackWordMorphRow(string Anchor, long? RootId, long? LemmaId, string? Pos, string? Features);

/// <summary>root satiri (kelime-kok). IdfQ editoryal real (float) sutunun kisa onlu gosterimidir (PackRows.FromSingle).</summary>
public sealed record PackRootRow(long Id, string Letters, long Occurrences, long AyahCount, double? IdfQ, string? KokAnlami);

/// <summary>
/// lemma satiri (kelime-kok): lang = 'ar' (QAC) ya da 'tr' (K-51 madde 9). Approval onayin yolunu tasir: 'qac' (QAC sozlugu, ar), 'editor' (editor onayi)
/// ya da 'auto' (sozluk kanitiyla otomatik onay; uygulama ayri isaretler). Turkce satirda Occurrences editoryal freq (kulturel siklik) degeridir.
/// </summary>
public sealed record PackLemmaRow(
    long Id,
    string Lang,
    string Text,
    string TextClean,
    long? RootId,
    long Occurrences,
    long? ArLemmaId,
    long EtymologicalOnly,
    string Approval);

/// <summary>lemma.approval degerleri (Icerik paketleri 3.3).</summary>
public static class LemmaApprovals
{
    public const string Qac = "qac";
    public const string Editor = "editor";
    public const string Auto = "auto";
}

/// <summary>lemma_gloss satiri (kelime-kok). Status 'onayli' ya da 'aday' (aday yalniz dev ve internal'da); Origin editoryal lemma_gloss.origin degeridir.</summary>
public sealed record PackLemmaGlossRow(
    long LemmaId,
    string AnlamKisa,
    string KuranAnlamlari,
    string? TurkceEsKelime,
    long YalnizcaEtimolojik,
    string Status,
    string Origin);

/// <summary>tr_form satiri (kelime-kok).</summary>
public sealed record PackTrFormRow(string KeyWide, string KeyNarrow, long TrLemmaId, long Freq);

/// <summary>
/// Bir paketin yazilacak butun satirlari ve ozet basliklari. Liste sirasi onemsizdir: PackRows satirlari kanonik sirada (anahtar bayt sirasi) sayar;
/// ozet de yazici da onu kullanir. version, built_at, data_version ve content_digest icerik degildir (ozete girmez).
/// </summary>
public sealed class PackContent
{
    public required string PackId { get; init; }

    public required BuildFlavor Flavor { get; init; }

    public int SchemaVersion { get; init; } = PackFormat.SchemaVersion;

    public IReadOnlyList<PackSourceRow> PackSources { get; init; } = [];

    public IReadOnlyList<PackAttributionRow> Attributions { get; init; } = [];

    public IReadOnlyList<PackUnitRow> Units { get; init; } = [];

    public IReadOnlyList<PackUnitSearchRow> UnitSearch { get; init; } = [];

    public IReadOnlyList<PackXrefRow> Xrefs { get; init; } = [];

    public IReadOnlyList<PackQuranWordRow> QuranWords { get; init; } = [];

    public IReadOnlyList<PackQuranMarkerRow> QuranMarkers { get; init; } = [];

    public IReadOnlyList<PackPageMapRow> PageMaps { get; init; } = [];

    public IReadOnlyList<PackSureRow> Sures { get; init; } = [];

    public IReadOnlyList<PackTrRootIndexRow> TrRootIndex { get; init; } = [];

    public IReadOnlyList<PackWordMorphRow> WordMorph { get; init; } = [];

    public IReadOnlyList<PackRootRow> Roots { get; init; } = [];

    public IReadOnlyList<PackLemmaRow> Lemmas { get; init; } = [];

    public IReadOnlyList<PackLemmaGlossRow> LemmaGlosses { get; init; } = [];

    public IReadOnlyList<PackTrFormRow> TrForms { get; init; } = [];

    /// <summary>
    /// Uygulanan onayli quran_word_fix sayisi (yalniz kelime-kok; diger paketlerde null). pack_meta'da <see cref="PackMetaKeys.WordFixCount"/>
    /// anahtariyla tasinir; paket ozetine girmez (ozet satirlardan turer, duzeltme sayisi word_morph satirlarinda zaten gorunur).
    /// </summary>
    public int? WordFixCount { get; init; }

    /// <summary>
    /// Kapi ozeti (pack_meta <see cref="PackMetaKeys.GateSummary"/>; K-51 madde 5 ve 11): RFC 8785 kanonik JSON <c>{"kok":{"set_sinifi":"silver","sonuc":"gecti"}}</c>;
    /// yalniz altin ya da silver sinifinda olcumu olan turler yazilir (kok ve lemma kelime-kok'te, benzer_ayet core'da). Olcum yoksa <c>{}</c>.
    /// Diger paketlerde null (anahtar yok). Paket ozetine girer.
    /// </summary>
    public string? GateSummary { get; init; }
}
