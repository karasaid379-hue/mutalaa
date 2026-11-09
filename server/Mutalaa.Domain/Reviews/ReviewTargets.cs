using System.Globalization;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// review.hedef_tablo degerleri (Editoryal veritabani 8, CHECK listesiyle ayni) ve hedef_anahtar ayristirma.
/// Anahtar bicimi hedefe gore degisir: unit = capa, surah_alias = <c>{surah_no}:{alias}</c> (ilk ':' ile bolunur),
/// xref ve quran_word_fix = Guid, lemma ve lemma_gloss = tamsayi lemma_id.
/// </summary>
public static class ReviewTargets
{
    public const string Source = "source";
    public const string Unit = "unit";
    public const string QuranWordFix = "quran_word_fix";
    public const string Lemma = "lemma";
    public const string LemmaGloss = "lemma_gloss";
    public const string Root = "root";
    public const string TrRootIndex = "tr_root_index";
    public const string TrForm = "tr_form";
    public const string SurahAlias = "surah_alias";
    public const string Xref = "xref";
    public const string PageMap = "page_map";
    public const string AyahBox = "ayah_box";
    public const string AudioTiming = "audio_timing";

    private static readonly string[] AllTargets =
    [
        Source, Unit, QuranWordFix, Lemma, LemmaGloss, Root, TrRootIndex, TrForm, SurahAlias, Xref, PageMap, AyahBox, AudioTiming,
    ];

    /// <summary>13 hedef; CHECK listesindeki sirayla.</summary>
    public static IReadOnlyList<string> All => AllTargets;

    /// <summary>Tablo adi CHECK listesinde mi (Ordinal, buyuk-kucuk harf duyarli).</summary>
    public static bool IsKnown(string? hedefTablo) => hedefTablo is not null && Array.IndexOf(AllTargets, hedefTablo) >= 0;

    /// <summary>
    /// Kendi <c>status</c> (xref_status) ya da <c>metin_durumu</c> sutunu olan hedef: dogrulanmis bu sutundan turetilir.
    /// Ote hedefler yalniz onayli veri tasir (Editoryal veritabani 8).
    /// </summary>
    public static bool HasStatusColumn(string? hedefTablo) =>
        hedefTablo is Lemma or LemmaGloss or QuranWordFix or SurahAlias or Xref or Unit;

    /// <summary>Inceleme akisi (onay, ret) bu hedef icin desteklenir mi; hedef_anahtar ayristirilabilir mi.</summary>
    public static bool IsSupported(string? hedefTablo) =>
        hedefTablo is Unit or SurahAlias or Xref or QuranWordFix or Lemma or LemmaGloss;

    /// <summary>
    /// hedef_anahtar'i hedefe gore ayristirir.
    /// </summary>
    /// <exception cref="DomainException">
    /// <c>dogrulama</c>: bilinmeyen tablo, bos ya da bozuk anahtar. <c>inceleme-desteklenmiyor</c>: bilinen ama desteklenmeyen hedef.
    /// </exception>
    public static ReviewTarget Parse(string? hedefTablo, string? hedefAnahtar)
    {
        if (!IsKnown(hedefTablo))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Bilinmeyen hedef_tablo.");
        }

        if (!IsSupported(hedefTablo))
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, $"'{hedefTablo}' icin inceleme desteklenmiyor.");
        }

        if (string.IsNullOrEmpty(hedefAnahtar))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "hedef_anahtar bos olamaz.");
        }

        switch (hedefTablo)
        {
            case Unit:
                return ReviewTarget.ForAnchor(ParseUnitAnchor(hedefAnahtar));
            case SurahAlias:
                return ParseSurahAlias(hedefAnahtar);
            case Xref:
            case QuranWordFix:
                return ReviewTarget.ForId(hedefTablo, ParseGuid(hedefAnahtar));
            default:
                return ReviewTarget.ForLemma(hedefTablo!, ParseCanonicalInt(hedefAnahtar, "lemma_id", int.MaxValue));
        }
    }

    private static AnchorRef ParseUnitAnchor(string key)
    {
        if (!AnchorRef.TryParse(key, out AnchorRef? anchor))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "hedef_anahtar gecerli bir capa degil.");
        }

        // Birim duzeyi: '@' araligi, kelime, cumle, ayet araligi ve konu capasi birim degildir.
        bool unitLevel = anchor.Span is null
            && anchor.Kind is not (AnchorKind.Qa or AnchorKind.Konu)
            && anchor.UnitOf().Equals(anchor);
        if (!unitLevel)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "hedef_anahtar birim duzeyinde bir capa olmali (kelime, aralik ve cumle capasi degil).");
        }

        return anchor;
    }

    private static ReviewTarget ParseSurahAlias(string key)
    {
        int colon = key.IndexOf(':', StringComparison.Ordinal);
        if (colon <= 0 || colon == key.Length - 1)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "surah_alias anahtari '{surah_no}:{alias}' biciminde olmali.");
        }

        int surahNo = ParseCanonicalInt(key[..colon], "surah_no", 114);
        return ReviewTarget.ForSurahAlias(surahNo, key[(colon + 1)..]);
    }

    private static Guid ParseGuid(string key)
    {
        if (!Guid.TryParseExact(key, "D", out Guid id))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "hedef_anahtar bir Guid olmali.");
        }

        return id;
    }

    /// <summary>1..max, ASCII rakam, bastaki sifir ve isaret yok (kanonik).</summary>
    private static int ParseCanonicalInt(string text, string name, int max)
    {
        if (!int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out int value)
            || value < 1
            || value > max
            || !string.Equals(value.ToString(CultureInfo.InvariantCulture), text, StringComparison.Ordinal))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} 1..{max.ToString(CultureInfo.InvariantCulture)} arasinda kanonik bir tamsayi olmali.");
        }

        return value;
    }
}

/// <summary>
/// Ayristirilmis hedef_anahtar. Hedefe gore tek bir kimlik dolu olur: Anchor (unit), SurahNo ve Alias (surah_alias),
/// Id (xref, quran_word_fix) ya da LemmaId (lemma, lemma_gloss). Deger tur oldugu icin varlik adlari (EntityDocumentTests) etkilenmez.
/// </summary>
public readonly record struct ReviewTarget
{
    public required string Table { get; init; }

    public AnchorRef? Anchor { get; init; }

    public int? SurahNo { get; init; }

    public string? Alias { get; init; }

    public Guid? Id { get; init; }

    public int? LemmaId { get; init; }

    internal static ReviewTarget ForAnchor(AnchorRef anchor) => new() { Table = ReviewTargets.Unit, Anchor = anchor };

    internal static ReviewTarget ForSurahAlias(int surahNo, string alias) =>
        new() { Table = ReviewTargets.SurahAlias, SurahNo = surahNo, Alias = alias };

    internal static ReviewTarget ForId(string table, Guid id) => new() { Table = table, Id = id };

    internal static ReviewTarget ForLemma(string table, int lemmaId) => new() { Table = table, LemmaId = lemmaId };
}
