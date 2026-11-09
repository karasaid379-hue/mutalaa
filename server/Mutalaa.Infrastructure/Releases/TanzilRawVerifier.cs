using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Text;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>Ham Tanzil dosyasi beklenen bicimde degil. Ileti yalniz satir numarasi ve sayilar tasir; satir icerigi asla (Icerik hatti 7).</summary>
public sealed class TanzilFormatException : Exception
{
    public TanzilFormatException(string message)
        : base(message)
    {
    }
}

/// <summary>Bir ayet satiri: sure, ayet ve metin (dosyadaki baytlarin aynen UTF-8 cozumu; hicbir donusum yok).</summary>
public sealed record TanzilVerse(int Sure, int Ayet, string Text);

/// <summary>
/// Tanzil "Text (with aya numbers)" dosyasi (pipeline/src/mutalaa_pipeline/ingest/tanzil_bicim.py ile ayni kati bicim): <c>s|a|metin</c> LF satirlari,
/// ardindan bildirim blogu (ilk ayet olmayan satirdan dosya sonuna; yalniz bos ve '#' satirlari). BOM, CR, sonda LF yoklugu, gecersiz UTF-8, bos metin ve
/// ayet bolgesini bolen satir hatadir. Metin NFC, kirpma ya da satir sonu cevirisinden gecmez (K-26).
/// </summary>
public sealed class TanzilRawFile
{
    private TanzilRawFile(IReadOnlyList<TanzilVerse> verses, string notice)
    {
        Verses = verses;
        Notice = notice;
    }

    public IReadOnlyList<TanzilVerse> Verses { get; }

    /// <summary>Bildirim blogu (dosyadaki baytlarin aynen cozumu; source.notice_text ile bayt bayt ayni olmali).</summary>
    public string Notice { get; }

    /// <exception cref="TanzilFormatException">Bicim bozuksa.</exception>
    public static TanzilRawFile Parse(ReadOnlySpan<byte> data)
    {
        UTF8Encoding strict = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

        if (data.IsEmpty)
        {
            throw new TanzilFormatException("dosya bos");
        }

        if (data.Length >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF)
        {
            throw new TanzilFormatException("BOM var (bayt 0)");
        }

        int cr = data.IndexOf((byte)'\r');
        if (cr >= 0)
        {
            throw new TanzilFormatException($"CR (0x0D) var: bayt {cr.ToString(CultureInfo.InvariantCulture)}");
        }

        if (data[^1] != (byte)'\n')
        {
            throw new TanzilFormatException("dosya LF ile bitmiyor");
        }

        List<TanzilVerse> verses = [];
        int pos = 0;
        int lineNo = 0;
        int noticeStart = -1;
        bool hash = false;
        while (pos < data.Length)
        {
            int end = data[pos..].IndexOf((byte)'\n');
            ReadOnlySpan<byte> line = data.Slice(pos, end);
            lineNo++;

            if (noticeStart < 0)
            {
                if (TryParseVersePrefix(line, out int sure, out int ayet, out int textStart))
                {
                    if (line.Length == textStart)
                    {
                        throw new TanzilFormatException($"satir {lineNo.ToString(CultureInfo.InvariantCulture)}: bos metin");
                    }

                    try
                    {
                        verses.Add(new TanzilVerse(sure, ayet, strict.GetString(line[textStart..])));
                    }
                    catch (DecoderFallbackException)
                    {
                        throw new TanzilFormatException($"satir {lineNo.ToString(CultureInfo.InvariantCulture)}: gecersiz UTF-8");
                    }
                }
                else
                {
                    noticeStart = pos;
                    CheckNoticeLine(line, lineNo, ref hash);
                }
            }
            else
            {
                CheckNoticeLine(line, lineNo, ref hash);
            }

            pos += end + 1;
        }

        if (verses.Count == 0)
        {
            throw new TanzilFormatException("ayet satiri yok");
        }

        if (noticeStart < 0 || !hash)
        {
            throw new TanzilFormatException("bildirim blogu yok");
        }

        try
        {
            return new TanzilRawFile(verses, strict.GetString(data[noticeStart..]));
        }
        catch (DecoderFallbackException)
        {
            throw new TanzilFormatException("bildirim blogu gecersiz UTF-8");
        }
    }

    // Bildirim bolgesinde yalniz bos ve '#' satirlari; ayete benzeyen satir ayet bolgesinin kesildigini gosterir.
    private static void CheckNoticeLine(ReadOnlySpan<byte> line, int lineNo, ref bool hash)
    {
        if (LooksLikeVerse(line))
        {
            throw new TanzilFormatException($"satir {lineNo.ToString(CultureInfo.InvariantCulture)}: ayet bolgesi kesildi ya da ayet numarasi gecersiz");
        }

        if (line.IsEmpty)
        {
            return;
        }

        if (line[0] == (byte)'#')
        {
            hash = true;
            return;
        }

        throw new TanzilFormatException($"satir {lineNo.ToString(CultureInfo.InvariantCulture)}: tanimsiz satir");
    }

    // [0-9]+ '|' [0-9]+ '|' ile baslayan satir (bastaki sifir dahil): AYET_BENZERI.
    private static bool LooksLikeVerse(ReadOnlySpan<byte> line)
    {
        int i = 0;
        int digits = 0;
        while (i < line.Length && line[i] is >= (byte)'0' and <= (byte)'9')
        {
            i++;
            digits++;
        }

        if (digits == 0 || i >= line.Length || line[i] != (byte)'|')
        {
            return false;
        }

        i++;
        digits = 0;
        while (i < line.Length && line[i] is >= (byte)'0' and <= (byte)'9')
        {
            i++;
            digits++;
        }

        return digits > 0 && i < line.Length && line[i] == (byte)'|';
    }

    // AYET_ONEKI: ([1-9][0-9]{0,2}) '|' ([1-9][0-9]{0,2}) '|'
    private static bool TryParseVersePrefix(ReadOnlySpan<byte> line, out int sure, out int ayet, out int textStart)
    {
        sure = 0;
        ayet = 0;
        textStart = 0;
        if (!TryNumber(line, 0, out sure, out int next) || next >= line.Length || line[next] != (byte)'|')
        {
            return false;
        }

        if (!TryNumber(line, next + 1, out ayet, out int next2) || next2 >= line.Length || line[next2] != (byte)'|')
        {
            return false;
        }

        textStart = next2 + 1;
        return true;
    }

    private static bool TryNumber(ReadOnlySpan<byte> line, int start, out int value, out int next)
    {
        value = 0;
        next = start;
        if (start >= line.Length || line[start] is < (byte)'1' or > (byte)'9')
        {
            return false;
        }

        int i = start;
        while (i < line.Length && i - start < 3 && line[i] is >= (byte)'0' and <= (byte)'9')
        {
            value = (value * 10) + (line[i] - (byte)'0');
            i++;
        }

        next = i;
        return true;
    }
}

/// <summary>
/// P-11 ham dosya denetimi (Yayin sureci 4; Backend API 10.3): <c>{rawDir}/{slug}/{alinma_tarihi}/</c> altinda SHA-256'si source.dosya_sha256 olan dosya bulunur
/// (beklenen ad once denenir; ad ne olursa olsun karar ozettir), kati bicimle ayristirilir, her satirin metin baytlarindan <see cref="ContentHash.Compute"/> ile
/// content_hash yeniden hesaplanip birimlerinkiyle <see cref="GateEvaluator.VerifyP11ContentHashes"/> ile karsilastirilir, bildirim blogu source.notice_text ile
/// <see cref="GateEvaluator.VerifyP11Notice"/> ile, satir sayisi birim sayisiyla karsilastirilir. Metin hicbir donusumden gecmez. Ihlal listesi bossa gecti.
/// </summary>
public sealed class TanzilRawVerifier
{
    public const string UthmaniSlug = "tanzil-uthmani";
    public const string SimpleCleanSlug = "tanzil-simple-clean";

    private readonly string _rawDir;

    public TanzilRawVerifier(string rawDir)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(rawDir);
        _rawDir = rawDir;
    }

    /// <summary>Kaynagin ham dosya adi (Tanzil indirme adlari); Tanzil kaynagi degilse null.</summary>
    public static string? ExpectedFileName(string slug) => slug switch
    {
        UthmaniSlug => "quran-uthmani.txt",
        SimpleCleanSlug => "quran-simple-clean.txt",
        _ => null,
    };

    /// <summary>
    /// Tek kaynagi dogrular. unitHashes: capa -> content_hash (null ise birim hash karsilastirmasi yapilmaz; ar_norm kaynagi tanzil-simple-clean'in birimi yoktur).
    /// expectedLineCount: ham dosyadaki ayet satiri sayisi (null ise denetlenmez). unitTexts: capa -> pakete yazilacak birim metni (null ise metin karsilastirmasi
    /// yapilmaz); her metin ham dosyadaki satir metniyle bayt bayt (Ordinal) ayni olmali. Yalniz hash'i denetlemek, metni degistirip hash'i sabit birakan
    /// bir kaydi kacirirdi (K-26).
    /// </summary>
    public IReadOnlyList<GateViolation> Verify(
        SourceRow source,
        IReadOnlyDictionary<string, string>? unitHashes,
        int? expectedLineCount,
        IReadOnlyDictionary<string, string>? unitTexts = null)
    {
        ArgumentNullException.ThrowIfNull(source);

        string slug = source.Slug;
        if (source.AlinmaTarihi is null || string.IsNullOrEmpty(source.DosyaSha256)
            || !string.Equals(Path.GetFileName(slug), slug, StringComparison.Ordinal))
        {
            return [new GateViolation(GateRule.P11, slug, "ham-dosya-konumu-yok")];
        }

        string dir = Path.Combine(_rawDir, slug, source.AlinmaTarihi.Value.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        if (!Directory.Exists(dir))
        {
            return [new GateViolation(GateRule.P11, slug, "ham-dosya-yok")];
        }

        byte[]? data = FindFile(dir, slug, source.DosyaSha256);
        if (data is null)
        {
            return [new GateViolation(GateRule.P11, slug, "ham-dosya-sha256-uyusmuyor")];
        }

        TanzilRawFile file;
        try
        {
            file = TanzilRawFile.Parse(data);
        }
        catch (TanzilFormatException ex)
        {
            return [new GateViolation(GateRule.P11, slug, "ham-dosya-bicimi: " + ex.Message)];
        }

        List<GateViolation> violations = [];
        if (unitHashes is not null)
        {
            Dictionary<string, string> raw = new(StringComparer.Ordinal);
            foreach (TanzilVerse verse in file.Verses)
            {
                string anchor = string.Create(CultureInfo.InvariantCulture, $"q:{verse.Sure}:{verse.Ayet}");
                if (!raw.TryAdd(anchor, ContentHash.Compute(verse.Text)))
                {
                    violations.Add(new GateViolation(GateRule.P11, anchor, "ham-dosyada-tekrar"));
                }
            }

            violations.AddRange(GateEvaluator.VerifyP11ContentHashes(raw, unitHashes));
        }

        if (unitTexts is not null)
        {
            foreach (TanzilVerse verse in file.Verses)
            {
                string anchor = string.Create(CultureInfo.InvariantCulture, $"q:{verse.Sure}:{verse.Ayet}");
                if (unitTexts.TryGetValue(anchor, out string? text) && !string.Equals(text, verse.Text, StringComparison.Ordinal))
                {
                    violations.Add(new GateViolation(GateRule.P11, anchor, "metin-uyusmuyor"));
                }
            }
        }

        violations.AddRange(GateEvaluator.VerifyP11Notice(slug, source.NoticeText, file.Notice));

        if (expectedLineCount is int expected && file.Verses.Count != expected)
        {
            violations.Add(new GateViolation(GateRule.P11, slug, "satir-sayisi-uyusmuyor"));
        }

        return violations;
    }

    /// <summary>
    /// Kapidan giren Tanzil kaynaklarini anlik goruntuye karsi dogrular: tanzil-uthmani etkin birimlerinin hash'leri, METINLERI (ham satirla bayt bayt) ve sayisi;
    /// her birimin content_hash degerinin kendi metninden yeniden hesaplananla ayni olmasi; quran_word.text_uthmani degerinin ayet metninin
    /// [char_start, char_end) kod noktasi dilimi olmasi (hattin kendi degismezi, pipeline export/pg.py); tanzil-simple-clean bildirim ve satir sayisi
    /// (tanzil-uthmani etkin birim sayisi). Kaynak satiri ya da girmeyen kaynak atlanir (P-01 ve suzme kurallari ayridir).
    /// </summary>
    public IReadOnlyList<GateViolation> VerifyAll(EditorialSnapshot snapshot, IReadOnlyCollection<string> includedSourceSlugs)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        ArgumentNullException.ThrowIfNull(includedSourceSlugs);

        Dictionary<string, string> uthmaniHashes = new(StringComparer.Ordinal);
        Dictionary<string, string> uthmaniTexts = new(StringComparer.Ordinal);
        Dictionary<string, string> allUthmaniTexts = new(StringComparer.Ordinal);
        List<GateViolation> consistency = [];
        foreach (UnitRow unit in snapshot.Units)
        {
            if (!string.Equals(unit.SourceId, UthmaniSlug, StringComparison.Ordinal))
            {
                continue;
            }

            allUthmaniTexts[unit.Anchor] = unit.Metin;
            if (string.Equals(unit.Status, "etkin", StringComparison.Ordinal))
            {
                uthmaniHashes[unit.Anchor] = unit.ContentHash;
                uthmaniTexts[unit.Anchor] = unit.Metin;
                if (!string.Equals(ContentHash.Compute(unit.Metin), unit.ContentHash, StringComparison.Ordinal))
                {
                    consistency.Add(new GateViolation(GateRule.P11, unit.Anchor, "hash-metinle-uyusmuyor"));
                }
            }
        }

        List<GateViolation> violations = [];
        foreach (SourceRow source in snapshot.Sources)
        {
            if (!includedSourceSlugs.Contains(source.Slug, StringComparer.Ordinal))
            {
                continue;
            }

            if (string.Equals(source.Slug, UthmaniSlug, StringComparison.Ordinal))
            {
                violations.AddRange(Verify(source, uthmaniHashes, uthmaniHashes.Count, uthmaniTexts));
                violations.AddRange(consistency.OrderBy(v => v.Subject, StringComparer.Ordinal));
                violations.AddRange(VerifyWords(snapshot.QuranWords, allUthmaniTexts));
            }
            else if (string.Equals(source.Slug, SimpleCleanSlug, StringComparison.Ordinal))
            {
                violations.AddRange(Verify(source, null, uthmaniHashes.Count));
            }
        }

        return violations;
    }

    // quran_word.text_uthmani = ayet metninin [char_start, char_end) KOD NOKTASI dilimi (anchor_tanzil.py; export/pg.py ayni degismezi denetler).
    // Kelime bolme kurali burada yeniden uretilmez: yalniz sonucun ayet metniyle tutarliligi denetlenir.
    private static List<GateViolation> VerifyWords(IReadOnlyList<QuranWordRow> words, Dictionary<string, string> ayahTexts)
    {
        List<GateViolation> violations = [];
        foreach (QuranWordRow word in words.Where(w => string.Equals(w.SourceId, UthmaniSlug, StringComparison.Ordinal)).OrderBy(w => w.Anchor, StringComparer.Ordinal))
        {
            string ayah = string.Create(CultureInfo.InvariantCulture, $"q:{word.Surah}:{word.Ayah}");
            if (!ayahTexts.TryGetValue(ayah, out string? text))
            {
                violations.Add(new GateViolation(GateRule.P11, word.Anchor, "kelime-ayeti-yok"));
                continue;
            }

            if (!WordMatches(text, word))
            {
                violations.Add(new GateViolation(GateRule.P11, word.Anchor, "kelime-metni-uyusmuyor"));
            }
        }

        return violations;
    }

    private static bool WordMatches(string ayahText, QuranWordRow word)
    {
        if (word.CharStart < 0 || word.CharEnd <= word.CharStart || word.CharEnd > CodePointOffsets.CodePointCount(ayahText))
        {
            return false;
        }

        int start = CodePointOffsets.CpToUtf16(ayahText, word.CharStart);
        int end = CodePointOffsets.CpToUtf16(ayahText, word.CharEnd);
        return string.Equals(ayahText[start..end], word.TextUthmani, StringComparison.Ordinal);
    }

    // Beklenen ad once; sonra klasordeki dosyalar Ordinal sirayla. Karar SHA-256'dir.
    private static byte[]? FindFile(string dir, string slug, string sha256)
    {
        List<string> candidates = [];
        string? expectedName = ExpectedFileName(slug);
        if (expectedName is not null)
        {
            string expectedPath = Path.Combine(dir, expectedName);
            if (File.Exists(expectedPath))
            {
                candidates.Add(expectedPath);
            }
        }

        foreach (string path in Directory.EnumerateFiles(dir).Order(StringComparer.Ordinal))
        {
            if (!candidates.Contains(path, StringComparer.Ordinal))
            {
                candidates.Add(path);
            }
        }

        foreach (string path in candidates)
        {
            byte[] data = File.ReadAllBytes(path);
            if (string.Equals(Convert.ToHexStringLower(SHA256.HashData(data)), sha256, StringComparison.Ordinal))
            {
                return data;
            }
        }

        return null;
    }
}
