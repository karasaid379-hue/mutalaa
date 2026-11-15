using System.Buffers;
using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;
using MackySoft.Json.Canonicalization;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// Paket tablolari ve sabit tablo sirasi (K-46 madde 1). Sutun listeleri satir degerlerinin sirasidir: unit'te rowid yoktur,
/// unit_search'te ilk deger capadir (yazici bunu unit rowid'ine cevirir).
/// </summary>
public static class PackTables
{
    public const string PackSource = "pack_source";
    public const string Attribution = "attribution";
    public const string Unit = "unit";
    public const string UnitSearch = "unit_search";
    public const string XrefIdx = "xref_idx";
    public const string QuranWord = "quran_word";
    public const string QuranMarker = "quran_marker";
    public const string PageMap = "page_map";
    public const string Sure = "sure";
    public const string TrRootIndex = "tr_root_index";
    public const string WordMorph = "word_morph";
    public const string Root = "root";
    public const string Lemma = "lemma";
    public const string LemmaGloss = "lemma_gloss";
    public const string TrForm = "tr_form";

    /// <summary>Ozet ve yazim sirasi (K-46 madde 1: kelime-kok tablolari tr_root_index'ten sonra gelir; Icerik paketleri 6).</summary>
    public static IReadOnlyList<string> Order { get; } =
        [PackSource, Attribution, Unit, UnitSearch, XrefIdx, QuranWord, QuranMarker, PageMap, Sure, TrRootIndex, WordMorph, Root, Lemma, LemmaGloss, TrForm];

    private static readonly Dictionary<string, string[]> ColumnMap = new(StringComparer.Ordinal)
    {
        [PackSource] = ["source_id"],
        [Attribution] = ["source_id", "title", "version", "source_url", "required_credit", "notice_text"],
        [Unit] = ["anchor", "kind", "role", "parent_path", "ord", "ayah_first", "ayah_last", "label", "text", "marks", "sentences", "attrs", "content_hash", "status", "approved", "successors"],
        [UnitSearch] = ["anchor", "tr_wide", "tr_stem", "ar_norm"],
        [XrefIdx] = ["id", "src_anchor", "src_start", "src_end", "dst_anchor", "dst_start", "dst_end", "type", "score", "confidence", "approved", "folded", "evidence", "data_version"],
        [QuranWord] = ["anchor", "ayah_index", "word", "text_uthmani", "norm", "char_start", "char_end"],
        [QuranMarker] = ["kind", "no", "anchor", "secde_turu"],
        [PageMap] = ["layout", "volume", "page", "line", "start_anchor", "start_offset", "end_anchor", "end_offset"],
        [Sure] = ["no", "name", "name_ar", "ayah_count", "variants"],
        [TrRootIndex] = ["anchor", "span_start", "span_end", "root_id", "tr_lemma_id", "etymological_only"],
        [WordMorph] = ["anchor", "root_id", "lemma_id", "pos", "features"],
        [Root] = ["id", "letters", "occurrences", "ayah_count", "idf_q", "kok_anlami"],
        [Lemma] = ["id", "lang", "text", "text_clean", "root_id", "occurrences", "ar_lemma_id", "etymological_only", "approval"],
        [LemmaGloss] = ["lemma_id", "anlam_kisa", "kuran_anlamlari", "turkce_es_kelime", "yalnizca_etimolojik", "status", "origin"],
        [TrForm] = ["key_wide", "key_narrow", "tr_lemma_id", "freq"],
    };

    /// <summary>Tablonun satir degeri sutunlari (unit'te rowid yok; unit_search'te ilk sutun capa).</summary>
    public static IReadOnlyList<string> Columns(string table) =>
        ColumnMap.TryGetValue(table, out string[]? columns) ? columns : throw new ArgumentException($"Bilinmeyen paket tablosu: {table}", nameof(table));
}

/// <summary>Bir paket satiri: tablo adi ve degerler (string, long, double ya da null).</summary>
public readonly record struct PackRow(string Table, object?[] Values);

/// <summary>
/// Tek kanonik satir sayici. Hem <see cref="PackDigest"/> hem <see cref="SqlitePackWriter"/> bu akisi kullanir: tablolar <see cref="PackTables.Order"/> sirasinda,
/// satirlar tablonun anahtarina gore UTF-8 bayt sirasinda (giris listesinin sirasi onemsizdir) akar. Anahtarlar: pack_source ve attribution source_id;
/// unit, unit_search ve quran_word anchor; xref_idx id; quran_marker (kind, no); page_map (layout, volume, page, line, start_anchor, end_anchor);
/// sure no; tr_root_index (anchor, span_start); word_morph anchor; root id; lemma id; lemma_gloss lemma_id; tr_form (key_narrow, tr_lemma_id).
/// </summary>
public static class PackRows
{
    /// <summary>
    /// real (float) sutun degerinin kisa onlu gosterimi: float.ToString("R") sonucu double'a okunur (0,7f -> 0,7). float'in double'a dogrudan
    /// genisletilmesi 0,699999988 verirdi ve ozet ile SQLite REAL degeri yanlis olurdu.
    /// </summary>
    public static double FromSingle(float value)
    {
        if (!float.IsFinite(value))
        {
            throw new ArgumentOutOfRangeException(nameof(value), value, "Sonlu olmayan gercek sayi pakete yazilamaz.");
        }

        return double.Parse(value.ToString("R", CultureInfo.InvariantCulture), NumberStyles.Float, CultureInfo.InvariantCulture);
    }

    /// <summary>Satirlari kanonik sirada akitir.</summary>
    public static IEnumerable<PackRow> Enumerate(PackContent content)
    {
        ArgumentNullException.ThrowIfNull(content);

        foreach (PackSourceRow r in content.PackSources.OrderBy(r => r.SourceId, Utf8Order.Instance))
        {
            yield return new PackRow(PackTables.PackSource, [r.SourceId]);
        }

        foreach (PackAttributionRow r in content.Attributions.OrderBy(r => r.SourceId, Utf8Order.Instance))
        {
            yield return new PackRow(PackTables.Attribution, [r.SourceId, r.Title, r.Version, r.SourceUrl, r.RequiredCredit, r.NoticeText]);
        }

        foreach (PackUnitRow r in content.Units.OrderBy(r => r.Anchor, Utf8Order.Instance))
        {
            yield return new PackRow(
                PackTables.Unit,
                [r.Anchor, r.Kind, r.Role, r.ParentPath, r.Ord, r.AyahFirst, r.AyahLast, r.Label, r.Text, r.Marks, r.Sentences, r.Attrs, r.ContentHash, r.Status, r.Approved, r.Successors]);
        }

        foreach (PackUnitSearchRow r in content.UnitSearch.OrderBy(r => r.Anchor, Utf8Order.Instance))
        {
            yield return new PackRow(PackTables.UnitSearch, [r.Anchor, r.TrWide, r.TrStem, r.ArNorm]);
        }

        foreach (PackXrefRow r in content.Xrefs.OrderBy(r => r.Id, Utf8Order.Instance))
        {
            yield return new PackRow(
                PackTables.XrefIdx,
                [r.Id, r.SrcAnchor, r.SrcStart, r.SrcEnd, r.DstAnchor, r.DstStart, r.DstEnd, r.Type, r.Score, r.Confidence, r.Approved, r.Folded, r.Evidence, r.DataVersion]);
        }

        foreach (PackQuranWordRow r in content.QuranWords.OrderBy(r => r.Anchor, Utf8Order.Instance))
        {
            yield return new PackRow(PackTables.QuranWord, [r.Anchor, r.AyahIndex, r.Word, r.TextUthmani, r.Norm, r.CharStart, r.CharEnd]);
        }

        foreach (PackQuranMarkerRow r in content.QuranMarkers.OrderBy(r => r.Kind, Utf8Order.Instance).ThenBy(r => r.No))
        {
            yield return new PackRow(PackTables.QuranMarker, [r.Kind, r.No, r.Anchor, r.SecdeTuru]);
        }

        IOrderedEnumerable<PackPageMapRow> pages = content.PageMaps
            .OrderBy(r => r.Layout, Utf8Order.Instance)
            .ThenBy(r => r.Volume ?? long.MinValue)
            .ThenBy(r => r.Page)
            .ThenBy(r => r.Line ?? long.MinValue)
            .ThenBy(r => r.StartAnchor, Utf8Order.Instance)
            .ThenBy(r => r.EndAnchor, Utf8Order.Instance);
        foreach (PackPageMapRow r in pages)
        {
            yield return new PackRow(PackTables.PageMap, [r.Layout, r.Volume, r.Page, r.Line, r.StartAnchor, r.StartOffset, r.EndAnchor, r.EndOffset]);
        }

        foreach (PackSureRow r in content.Sures.OrderBy(r => r.No))
        {
            yield return new PackRow(PackTables.Sure, [r.No, r.Name, r.NameAr, r.AyahCount, r.Variants]);
        }

        foreach (PackTrRootIndexRow r in content.TrRootIndex.OrderBy(r => r.Anchor, Utf8Order.Instance).ThenBy(r => r.SpanStart))
        {
            yield return new PackRow(PackTables.TrRootIndex, [r.Anchor, r.SpanStart, r.SpanEnd, r.RootId, r.TrLemmaId, r.EtymologicalOnly]);
        }

        foreach (PackWordMorphRow r in content.WordMorph.OrderBy(r => r.Anchor, Utf8Order.Instance))
        {
            yield return new PackRow(PackTables.WordMorph, [r.Anchor, r.RootId, r.LemmaId, r.Pos, r.Features]);
        }

        foreach (PackRootRow r in content.Roots.OrderBy(r => r.Id))
        {
            yield return new PackRow(PackTables.Root, [r.Id, r.Letters, r.Occurrences, r.AyahCount, r.IdfQ, r.KokAnlami]);
        }

        foreach (PackLemmaRow r in content.Lemmas.OrderBy(r => r.Id))
        {
            yield return new PackRow(PackTables.Lemma, [r.Id, r.Lang, r.Text, r.TextClean, r.RootId, r.Occurrences, r.ArLemmaId, r.EtymologicalOnly, r.Approval]);
        }

        foreach (PackLemmaGlossRow r in content.LemmaGlosses.OrderBy(r => r.LemmaId))
        {
            yield return new PackRow(PackTables.LemmaGloss, [r.LemmaId, r.AnlamKisa, r.KuranAnlamlari, r.TurkceEsKelime, r.YalnizcaEtimolojik, r.Status, r.Origin]);
        }

        foreach (PackTrFormRow r in content.TrForms.OrderBy(r => r.KeyNarrow, Utf8Order.Instance).ThenBy(r => r.TrLemmaId))
        {
            yield return new PackRow(PackTables.TrForm, [r.KeyWide, r.KeyNarrow, r.TrLemmaId, r.Freq]);
        }
    }

    /// <summary>Tablo basina satir sayisi (satirsiz tablolar 0 ile yer alir; PackTables.Order sirasinda).</summary>
    public static IReadOnlyDictionary<string, int> Count(PackContent content)
    {
        ArgumentNullException.ThrowIfNull(content);

        return new Dictionary<string, int>(StringComparer.Ordinal)
        {
            [PackTables.PackSource] = content.PackSources.Count,
            [PackTables.Attribution] = content.Attributions.Count,
            [PackTables.Unit] = content.Units.Count,
            [PackTables.UnitSearch] = content.UnitSearch.Count,
            [PackTables.XrefIdx] = content.Xrefs.Count,
            [PackTables.QuranWord] = content.QuranWords.Count,
            [PackTables.QuranMarker] = content.QuranMarkers.Count,
            [PackTables.PageMap] = content.PageMaps.Count,
            [PackTables.Sure] = content.Sures.Count,
            [PackTables.TrRootIndex] = content.TrRootIndex.Count,
            [PackTables.WordMorph] = content.WordMorph.Count,
            [PackTables.Root] = content.Roots.Count,
            [PackTables.Lemma] = content.Lemmas.Count,
            [PackTables.LemmaGloss] = content.LemmaGlosses.Count,
            [PackTables.TrForm] = content.TrForms.Count,
        };
    }

    /// <summary>Satirin RFC 8785 (JCS) kanonik JSON dizisi: [tablo, degerler...] (UTF-8 baytlari).</summary>
    public static byte[] Canonical(PackRow row) => CanonicalArray(row.Table, row.Values);

    internal static byte[] CanonicalArray(string first, IReadOnlyList<object?> values)
    {
        ArrayBufferWriter<byte> buffer = new(256);
        using (Utf8JsonWriter writer = new(buffer, new JsonWriterOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }))
        {
            writer.WriteStartArray();
            writer.WriteStringValue(first);
            foreach (object? value in values)
            {
                switch (value)
                {
                    case null:
                        writer.WriteNullValue();
                        break;
                    case string s:
                        writer.WriteStringValue(s);
                        break;
                    case long l:
                        writer.WriteNumberValue(l);
                        break;
                    case int i:
                        writer.WriteNumberValue(i);
                        break;
                    case double d:
                        writer.WriteNumberValue(d);
                        break;
                    default:
                        throw new ArgumentException("Desteklenmeyen paket degeri turu: " + value.GetType().Name, nameof(values));
                }
            }

            writer.WriteEndArray();
        }

        return Rfc8785JsonCanonicalizer.Canonicalize(buffer.WrittenSpan);
    }
}
