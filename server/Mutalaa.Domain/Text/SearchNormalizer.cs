using System.Globalization;
using System.Text;

namespace Mutalaa.Domain.Text;

/// <summary>Bir metnin uc arama anahtari (K-36): dar ve genis Turkce anahtar, Arapca anahtar.</summary>
public readonly record struct SearchKeys(string TrNarrow, string TrWide, string ArNorm);

/// <summary>
/// Arama normallestirmesi, surum 1.0 (K-36). Uc dilde (TypeScript, C#, Python) ayni sonucu verir ve
/// shared/test-vectors/normalize vektorleriyle kilitlidir. Kulturden bagimsizdir: buyuk-kucuk harf
/// kod noktasi basina Rune.ToLowerInvariant ile (Turkce I ve dotted I acik eslemeyle), karsilastirma Ordinal.
/// Hazir kaynak metnini (Tanzil) degistirmez; yalniz ayri arama sutunu icin anahtar uretir.
/// </summary>
public static class SearchNormalizer
{
    /// <summary>Normallestirici surumu; ic kesme listesi degisince kucuk surum artar.</summary>
    public const string NormalizerVersion = "1.0";

    /// <summary>
    /// Kod noktasi basina Turkce kucuk harf: I (U+0049) -> U+0131, U+0130 -> i; digerleri basit kucuk harf.
    /// Dize duzeyinde kucuk harf cagrisi yapilmaz (son sigma baglami uygulanmaz). Eslesmemis vekil oldugu gibi kalir.
    /// </summary>
    public static string LowerTurkish(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        StringBuilder sb = new(text.Length);
        int i = 0;
        while (i < text.Length)
        {
            if (Rune.TryGetRuneAt(text, i, out Rune r))
            {
                sb.Append(LowerRune(r));
                i += r.Utf16SequenceLength;
            }
            else
            {
                sb.Append(text[i]);
                i++;
            }
        }

        return sb.ToString();
    }

    /// <summary>
    /// Ortak on adim (K-36 madde 1): eslesmemis vekil -> U+0020; U+200B -> U+0020; digerleri Cf silinir; NFC;
    /// Arapca bloklarindaki kod noktasi Arapca parcaya, digerleri Turkce parcaya gider, oteki parcada o konum U+0020 olur.
    /// </summary>
    public static (string Tr, string Ar) SplitScripts(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        string paired = ReplaceUnpairedSurrogates(text);

        StringBuilder cleaned = new(paired.Length);
        foreach (Rune r in paired.EnumerateRunes())
        {
            if (r.Value == 0x200B)
            {
                cleaned.Append(' ');
            }
            else if (Rune.GetUnicodeCategory(r) != UnicodeCategory.Format)
            {
                cleaned.Append(r);
            }
        }

        string nfc = NormalizeNfc(cleaned.ToString());

        StringBuilder tr = new(nfc.Length);
        StringBuilder ar = new(nfc.Length);
        foreach (Rune r in nfc.EnumerateRunes())
        {
            if (IsArabicBlock(r.Value))
            {
                ar.Append(r);
                tr.Append(' ');
            }
            else
            {
                tr.Append(r);
                ar.Append(' ');
            }
        }

        return (tr.ToString(), ar.ToString());
    }

    /// <summary>Dar Turkce anahtar: duzeltme isaretleri korunur (K-36 madde 2).</summary>
    public static string TurkishNarrow(string text) => TurkishKeys(text, IcKesme.Entries).Narrow;

    /// <summary>Genis Turkce anahtar: dotless i katlanir, birlesen isaretler silinir; soz sayisi ve sirasi dar anahtarla aynidir.</summary>
    public static string TurkishWide(string text) => TurkishKeys(text, IcKesme.Entries).Wide;

    /// <summary>Arapca anahtar (K-36 madde 4).</summary>
    public static string Arabic(string text) => ArabicKey(SplitScripts(text).Ar);

    /// <summary>Uc anahtari birlikte uretir; on adim bir kez calisir.</summary>
    public static SearchKeys Keys(string text)
    {
        (string tr, string ar) = SplitScripts(text);
        (string narrow, string wide) = TurkishKeysFromPrepared(tr, IcKesme.Entries);
        return new SearchKeys(narrow, wide, ArabicKey(ar));
    }

    /// <summary>Ic kesme listesini disaridan alan surum (en uzun eslesme testi icin).</summary>
    internal static (string Narrow, string Wide) TurkishKeys(string text, IReadOnlyList<string> icKesme)
    {
        ArgumentNullException.ThrowIfNull(icKesme);
        return TurkishKeysFromPrepared(SplitScripts(text).Tr, icKesme);
    }

    private static (string Narrow, string Wide) TurkishKeysFromPrepared(string trText, IReadOnlyList<string> icKesme)
    {
        string lowered = MapApostrophes(LowerTurkish(trText));

        List<string> narrow = [];
        List<string> wide = [];
        foreach (string raw in Words(lowered, includeApostrophe: true))
        {
            string word = TrimApostrophes(raw);
            if (word.Length == 0)
            {
                continue;
            }

            word = RemoveInnerApostrophes(word, icKesme);

            int cut = word.IndexOf('\'', StringComparison.Ordinal);
            if (cut >= 0)
            {
                word = word[..cut];
            }

            word = word.Normalize(NormalizationForm.FormC);
            if (!HasLetterOrNumber(word))
            {
                continue;
            }

            narrow.Add(word);
            wide.Add(Fold(word));
        }

        return (string.Join(' ', narrow), string.Join(' ', wide));
    }

    private static string ArabicKey(string arText)
    {
        StringBuilder sb = new(arText.Length);
        foreach (Rune r in arText.EnumerateRunes())
        {
            int v = r.Value;
            if (IsArabicRemoved(v))
            {
                continue;
            }

            sb.Append(v switch
            {
                0x0623 or 0x0625 or 0x0622 or 0x0671 => new Rune(0x0627),
                0x0649 or 0x0626 => new Rune(0x064A),
                0x0629 => new Rune(0x0647),
                0x0624 => new Rune(0x0648),
                _ => r,
            });
        }

        List<string> words = [];
        foreach (string word in Words(sb.ToString(), includeApostrophe: false))
        {
            if (HasLetterOrNumber(word))
            {
                words.Add(word);
            }
        }

        return string.Join(' ', words);
    }

    // .NET string.Normalize throws ArgumentException on U+FFFE (a noncharacter), but TypeScript and Python do not.
    // U+FFFE has combining class 0 and never composes, so NFC(a + FFFE + b) = NFC(a) + FFFE + NFC(b).
    // Normalizing the pieces between U+FFFE marks gives the same result as the other two languages.
    // Only the pre-split step needs this: later Normalize calls see words, and U+FFFE (Cn) is never a word character.
    private static string NormalizeNfc(string text)
    {
        if (!text.AsSpan().Contains((char)0xFFFE))
        {
            return text.Normalize(NormalizationForm.FormC);
        }

        StringBuilder sb = new(text.Length);
        int start = 0;
        while (true)
        {
            int offset = text.AsSpan(start).IndexOf((char)0xFFFE);
            int mark = offset < 0 ? -1 : start + offset;
            if (mark < 0)
            {
                sb.Append(text[start..].Normalize(NormalizationForm.FormC));
                break;
            }

            sb.Append(text[start..mark].Normalize(NormalizationForm.FormC)).Append((char)0xFFFE);
            start = mark + 1;
        }

        return sb.ToString();
    }

    private static string ReplaceUnpairedSurrogates(string text)
    {
        StringBuilder sb = new(text.Length);
        int i = 0;
        while (i < text.Length)
        {
            char c = text[i];
            if (char.IsHighSurrogate(c) && i + 1 < text.Length && char.IsLowSurrogate(text[i + 1]))
            {
                sb.Append(c).Append(text[i + 1]);
                i += 2;
            }
            else if (char.IsSurrogate(c))
            {
                sb.Append(' ');
                i++;
            }
            else
            {
                sb.Append(c);
                i++;
            }
        }

        return sb.ToString();
    }

    private static Rune LowerRune(Rune r)
    {
        return r.Value switch
        {
            0x49 => new Rune(0x131),
            0x130 => new Rune(0x69),
            _ => Rune.ToLowerInvariant(r),
        };
    }

    private static string MapApostrophes(string text)
    {
        StringBuilder sb = new(text.Length);
        foreach (Rune r in text.EnumerateRunes())
        {
            switch (r.Value)
            {
                case 0x2019:
                case 0x2018:
                case 0x02BC:
                case 0x02BE:
                case 0x02BF:
                case 0x00B4:
                case 0x60:
                    sb.Append('\'');
                    break;
                default:
                    sb.Append(r);
                    break;
            }
        }

        return sb.ToString();
    }

    /// <summary>Sozcuk karakterlerinin (11 kategori, istege bagli U+0027) en uzun dizileri.</summary>
    private static List<string> Words(string text, bool includeApostrophe)
    {
        List<string> words = [];
        StringBuilder current = new();
        foreach (Rune r in text.EnumerateRunes())
        {
            if (IsWordRune(r, includeApostrophe))
            {
                current.Append(r);
            }
            else if (current.Length > 0)
            {
                words.Add(current.ToString());
                current.Clear();
            }
        }

        if (current.Length > 0)
        {
            words.Add(current.ToString());
        }

        return words;
    }

    private static bool IsWordRune(Rune r, bool includeApostrophe)
    {
        if (includeApostrophe && r.Value == 0x27)
        {
            return true;
        }

        return Rune.GetUnicodeCategory(r) switch
        {
            UnicodeCategory.UppercaseLetter
                or UnicodeCategory.LowercaseLetter
                or UnicodeCategory.TitlecaseLetter
                or UnicodeCategory.ModifierLetter
                or UnicodeCategory.OtherLetter
                or UnicodeCategory.NonSpacingMark
                or UnicodeCategory.SpacingCombiningMark
                or UnicodeCategory.EnclosingMark
                or UnicodeCategory.DecimalDigitNumber
                or UnicodeCategory.LetterNumber
                or UnicodeCategory.OtherNumber => true,
            _ => false,
        };
    }

    private static bool HasLetterOrNumber(string word)
    {
        foreach (Rune r in word.EnumerateRunes())
        {
            switch (Rune.GetUnicodeCategory(r))
            {
                case UnicodeCategory.UppercaseLetter:
                case UnicodeCategory.LowercaseLetter:
                case UnicodeCategory.TitlecaseLetter:
                case UnicodeCategory.ModifierLetter:
                case UnicodeCategory.OtherLetter:
                case UnicodeCategory.DecimalDigitNumber:
                case UnicodeCategory.LetterNumber:
                case UnicodeCategory.OtherNumber:
                    return true;
            }
        }

        return false;
    }

    /// <summary>Bastaki ve sondaki U+0027 dizilerini atar; yalniz sozcugun ilk ve son kod noktasina bakilir (U+0027 BMP'dir).</summary>
    private static string TrimApostrophes(string word)
    {
        int start = 0;
        int end = word.Length;
        while (start < end && word[start] == '\'')
        {
            start++;
        }

        while (end > start && word[end - 1] == '\'')
        {
            end--;
        }

        return word[start..end];
    }

    /// <summary>Genis bicimi listedeki en uzun girdiyle baslayan sozcukten o girdinin kesme sayisi kadar ilk kesmeyi siler.</summary>
    private static string RemoveInnerApostrophes(string word, IReadOnlyList<string> icKesme)
    {
        string wide = Fold(word);
        string? best = null;
        foreach (string entry in icKesme)
        {
            if (wide.StartsWith(entry, StringComparison.Ordinal) && (best is null || entry.Length > best.Length))
            {
                best = entry;
            }
        }

        if (best is null)
        {
            return word;
        }

        int remove = 0;
        foreach (Rune r in best.EnumerateRunes())
        {
            if (r.Value == 0x27)
            {
                remove++;
            }
        }

        StringBuilder sb = new(word.Length);
        foreach (Rune r in word.EnumerateRunes())
        {
            if (r.Value == 0x27 && remove > 0)
            {
                remove--;
            }
            else
            {
                sb.Append(r);
            }
        }

        return sb.ToString();
    }

    /// <summary>Genis katlama: U+0131 -> i, NFD, U+0300..U+036F sil, NFC. Kesmelere dokunmaz.</summary>
    private static string Fold(string word)
    {
        StringBuilder sb = new(word.Length);
        foreach (Rune r in word.EnumerateRunes())
        {
            sb.Append(r.Value == 0x131 ? new Rune(0x69) : r);
        }

        string decomposed = sb.ToString().Normalize(NormalizationForm.FormD);
        sb.Clear();
        foreach (Rune r in decomposed.EnumerateRunes())
        {
            if (r.Value is < 0x0300 or > 0x036F)
            {
                sb.Append(r);
            }
        }

        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    private static bool IsArabicBlock(int v)
    {
        return v is (>= 0x0600 and <= 0x06FF)
            or (>= 0x0750 and <= 0x077F)
            or (>= 0x08A0 and <= 0x08FF)
            or (>= 0xFB50 and <= 0xFDFF)
            or (>= 0xFE70 and <= 0xFEFF);
    }

    private static bool IsArabicRemoved(int v)
    {
        return v is (>= 0x064B and <= 0x065F)
            or 0x0670
            or (>= 0x06D6 and <= 0x06ED)
            or 0x0640;
    }
}
