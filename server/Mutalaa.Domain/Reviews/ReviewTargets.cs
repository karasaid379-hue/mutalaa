using System.Globalization;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// review.hedef_tablo degerleri (Editoryal veritabani 8, CHECK listesiyle ayni) ve hedef_anahtar ayristirma.
/// Anahtar bicimi hedefe gore degisir: unit = capa, surah_alias = <c>{surah_no}:{alias}</c> (ilk ':' ile bolunur),
/// xref ve quran_word_fix = Guid, lemma ve lemma_gloss = tamsayi lemma_id, lugat_madde = <c>{source_id}:{anlam_no}:{basliksoz}</c>
/// (K-52 madde 14; ilk iki ':' kaynak kimligini ve anlam sirasini ayirir, basliksoz ':' tasiyabilir). Eski bicim
/// <c>{source_id}:{basliksoz}</c> (ikinci parca yalniz rakam degilse) <c>anlam_no = 1</c> sayilir.
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
    public const string LugatMadde = "lugat_madde";

    private static readonly string[] AllTargets =
    [
        Source, Unit, QuranWordFix, Lemma, LemmaGloss, Root, TrRootIndex, TrForm, SurahAlias, Xref, PageMap, AyahBox, AudioTiming, LugatMadde,
    ];

    /// <summary>14 hedef; CHECK listesindeki sirayla.</summary>
    public static IReadOnlyList<string> All => AllTargets;

    /// <summary>Tablo adi CHECK listesinde mi (Ordinal, buyuk-kucuk harf duyarli).</summary>
    public static bool IsKnown(string? hedefTablo) => hedefTablo is not null && Array.IndexOf(AllTargets, hedefTablo) >= 0;

    /// <summary>
    /// Kendi <c>status</c> (xref_status) ya da <c>metin_durumu</c> sutunu olan hedef: dogrulanmis bu sutundan turetilir.
    /// Ote hedefler yalniz onayli veri tasir (Editoryal veritabani 8).
    /// </summary>
    public static bool HasStatusColumn(string? hedefTablo) =>
        hedefTablo is Lemma or LemmaGloss or QuranWordFix or SurahAlias or Xref or Unit or LugatMadde;

    /// <summary>Inceleme akisi (onay, ret) bu hedef icin desteklenir mi; hedef_anahtar ayristirilabilir mi.</summary>
    public static bool IsSupported(string? hedefTablo) =>
        hedefTablo is Unit or SurahAlias or Xref or QuranWordFix or Lemma or LemmaGloss or LugatMadde;

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
            case LugatMadde:
                return ParseLugatMadde(hedefAnahtar);
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

    /// <summary>Lugat maddesinin <c>review.hedef_anahtar</c> degeri: <c>{source_id}:{anlam_no}:{basliksoz}</c> (anlam_no kanonik, 1..32767).</summary>
    public static string LugatKey(string sourceId, int anlamNo, string basliksoz)
    {
        ArgumentNullException.ThrowIfNull(sourceId);
        ArgumentNullException.ThrowIfNull(basliksoz);
        return sourceId + ":" + anlamNo.ToString(CultureInfo.InvariantCulture) + ":" + basliksoz;
    }

    /// <summary>
    /// <c>{source_id}:{anlam_no}:{basliksoz}</c> ya da eski <c>{source_id}:{basliksoz}</c> (anlam_no = 1). Ikinci parca yalniz ASCII rakamsa
    /// yeni bicimdir ve anlam_no kanonik tamsayi olmalidir; aksi halde tum kalan eski bicimin basliksozudur.
    /// </summary>
    private static ReviewTarget ParseLugatMadde(string key)
    {
        int colon = key.IndexOf(':', StringComparison.Ordinal);
        if (colon <= 0 || colon == key.Length - 1)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "lugat_madde anahtari '{source_id}:{anlam_no}:{basliksoz}' biciminde olmali.");
        }

        string sourceId = key[..colon];
        foreach (char c in sourceId)
        {
            if (!(c is >= 'a' and <= 'z' || c is >= '0' and <= '9' || c == '-'))
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "lugat_madde anahtarinda source_id kucuk harf ASCII, rakam ve '-' olmali.");
            }
        }

        string rest = key[(colon + 1)..];
        short anlamNo = 1;
        string basliksoz = rest;
        int second = rest.IndexOf(':', StringComparison.Ordinal);
        if (second > 0 && IsAsciiDigits(rest.AsSpan(0, second)))
        {
            anlamNo = (short)ParseCanonicalInt(rest[..second], "anlam_no", short.MaxValue);
            basliksoz = rest[(second + 1)..];
        }

        if (string.IsNullOrWhiteSpace(basliksoz))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "lugat_madde anahtarinda basliksoz bos olamaz.");
        }

        return ReviewTarget.ForLugatMadde(sourceId, anlamNo, basliksoz);
    }

    private static bool IsAsciiDigits(ReadOnlySpan<char> text)
    {
        foreach (char c in text)
        {
            if (c is < '0' or > '9')
            {
                return false;
            }
        }

        return text.Length > 0;
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
/// Id (xref, quran_word_fix), LemmaId (lemma, lemma_gloss) ya da SourceId, AnlamNo ve Basliksoz (lugat_madde). Deger tur oldugu icin varlik adlari (EntityDocumentTests) etkilenmez.
/// </summary>
public readonly record struct ReviewTarget
{
    public required string Table { get; init; }

    public AnchorRef? Anchor { get; init; }

    public int? SurahNo { get; init; }

    public string? Alias { get; init; }

    public Guid? Id { get; init; }

    public int? LemmaId { get; init; }

    public string? SourceId { get; init; }

    public string? Basliksoz { get; init; }

    /// <summary>lugat_madde: kaynak sirasiyla anlam sirasi (eski anahtar bicimi 1 sayilir).</summary>
    public short? AnlamNo { get; init; }

    internal static ReviewTarget ForAnchor(AnchorRef anchor) => new() { Table = ReviewTargets.Unit, Anchor = anchor };

    internal static ReviewTarget ForSurahAlias(int surahNo, string alias) =>
        new() { Table = ReviewTargets.SurahAlias, SurahNo = surahNo, Alias = alias };

    internal static ReviewTarget ForId(string table, Guid id) => new() { Table = table, Id = id };

    internal static ReviewTarget ForLemma(string table, int lemmaId) => new() { Table = table, LemmaId = lemmaId };

    internal static ReviewTarget ForLugatMadde(string sourceId, short anlamNo, string basliksoz) =>
        new() { Table = ReviewTargets.LugatMadde, SourceId = sourceId, AnlamNo = anlamNo, Basliksoz = basliksoz };
}
