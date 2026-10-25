using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using System.Globalization;
using System.Text.RegularExpressions;

namespace Mutalaa.Domain.Anchors;

// Ayristirma: Capa semasi 2 ve 3; hata onceligi K-35 madde 1-2.
public sealed partial record AnchorRef
{
    private const int MaxLength = 256;
    private const int MaxSlugLength = 64;
    private const int MaxDepth = 8;

    // Capa semasi 3'teki desen parcalari. [0-9] kullanilir, \d kullanilmaz.
    private const string K3 = "[1-9][0-9]{0,2}";
    private const string Sayi = "[1-9][0-9]*";
    private const string SlugPattern = "[a-z][a-z0-9]*(?:-[a-z0-9]+)*";
    private const string SegPattern = "(?![ps][0-9]+(?::|@|\\z))" + SlugPattern;
    private const string Ara = "(?:@(?<bas>0|[1-9][0-9]*)-(?<bit>[1-9][0-9]*))?";

    [GeneratedRegex(
        "^q:(?<sure>" + K3 + "):(?:(?<ayet>" + K3 + ")(?::(?<ilk>" + K3 + ")(?:-(?<son>" + K3 + "))?)?|(?<ayet_ilk>" + K3 + ")-(?<ayet_son>" + K3 + "))\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex QPattern();

    [GeneratedRegex("^konu:(?<konu>" + SlugPattern + ")\\z", RegexOptions.CultureInvariant)]
    private static partial Regex KonuPattern();

    [GeneratedRegex(
        "^meal:(?<meal>" + SlugPattern + "):(?<sure>" + K3 + "):(?<ayet>" + K3 + ")" + Ara + "\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex MealPattern();

    [GeneratedRegex(
        "^tf:(?<eser>" + SlugPattern + "):(?:(?<sure>" + K3 + ")-(?<ilk>" + K3 + ")-(?<son>" + K3 + ")|(?<bolum>" + SegPattern + ")):p(?<p>" + Sayi + ")" + Ara + "\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex TfPattern();

    [GeneratedRegex(
        "^rn:(?<yol>" + SegPattern + "(?::" + SegPattern + ")*):p(?<p>" + Sayi + ")(?::s(?<s>" + Sayi + ")|" + Ara + ")\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex RnPattern();

    [GeneratedRegex(
        "^h:(?<koleksiyon>" + SlugPattern + "):(?<no>" + Sayi + ")" + Ara + "\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex HPattern();

    [GeneratedRegex(
        "^ht:(?<ceviri>" + SlugPattern + "):(?<koleksiyon>" + SlugPattern + "):(?<no>" + Sayi + ")" + Ara + "\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex HtPattern();

    [GeneratedRegex(
        "^k:(?<yol>" + SegPattern + "(?::" + SegPattern + ")*):p(?<p>" + Sayi + ")" + Ara + "\\z",
        RegexOptions.CultureInvariant)]
    private static partial Regex KPattern();

    /// <summary>
    /// Dizgiyi ayristirir; gecersizse <see cref="AnchorException"/> firlatir.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="s"/> null ise.</exception>
    /// <exception cref="AnchorException">Gecersiz capa; <see cref="AnchorException.Code"/> hata kodunu verir.</exception>
    public static AnchorRef Parse(string s)
    {
        ArgumentNullException.ThrowIfNull(s);
        AnchorErrorCode? error = ParseCore(s, out AnchorRef? result);
        if (error is { } code)
        {
            throw new AnchorException(code);
        }

        return result!;
    }

    /// <summary>
    /// Dizgiyi ayristirir; hicbir durumda (sayi tasmasi dahil) istisna firlatmaz.
    /// </summary>
    public static bool TryParse(string? s, [NotNullWhen(true)] out AnchorRef? result)
    {
        if (s is null)
        {
            result = null;
            return false;
        }

        return ParseCore(s, out result) is null;
    }

    /// <summary>Hata kodunu dondurur (basarida null).</summary>
    internal static AnchorErrorCode? ParseCore(string s, out AnchorRef? result)
    {
        result = null;

        // 1. Karakter kumesi [a-z0-9:@-].
        foreach (char c in s)
        {
            bool ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ':' || c == '@' || c == '-';
            if (!ok)
            {
                return AnchorErrorCode.Bicim;
            }
        }

        // 2. Toplam uzunluk.
        if (s.Length > MaxLength)
        {
            return AnchorErrorCode.Uzunluk;
        }

        // 3. Desen, 4. sinirlar (slug, derinlik, sayi).
        AnchorRef? candidate;
        AnchorErrorCode? error = Build(s, out candidate);
        if (error is not null)
        {
            return error;
        }

        // 5. Anlam denetimleri.
        error = Validate(candidate!);
        if (error is not null)
        {
            return error;
        }

        result = candidate;
        return null;
    }

    private static AnchorErrorCode? Build(string s, out AnchorRef? candidate)
    {
        candidate = null;

        if (s.StartsWith("q:", StringComparison.Ordinal))
        {
            Match m = QPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            if (m.Groups["ayet_ilk"].Success)
            {
                if (!Int(m.Groups["sure"], out int sure) || !Int(m.Groups["ayet_ilk"], out int ilk) || !Int(m.Groups["ayet_son"], out int son))
                {
                    return AnchorErrorCode.Uzunluk;
                }

                candidate = new AnchorRef { Kind = AnchorKind.Qa, Sure = sure, Ilk = ilk, Son = son };
                return null;
            }

            if (!Int(m.Groups["sure"], out int s1) || !Int(m.Groups["ayet"], out int ayet))
            {
                return AnchorErrorCode.Uzunluk;
            }

            int kIlk = 0;
            int kSon = 0;
            if (m.Groups["ilk"].Success && !Int(m.Groups["ilk"], out kIlk))
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (m.Groups["son"].Success && !Int(m.Groups["son"], out kSon))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Q, Sure = s1, Ayet = ayet, Ilk = kIlk, Son = kSon };
            return null;
        }

        if (s.StartsWith("konu:", StringComparison.Ordinal))
        {
            Match m = KonuPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            string slug = m.Groups["konu"].Value;
            if (slug.Length > MaxSlugLength)
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Konu, Slug = slug };
            return null;
        }

        if (s.StartsWith("meal:", StringComparison.Ordinal))
        {
            Match m = MealPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            string meal = m.Groups["meal"].Value;
            if (meal.Length > MaxSlugLength)
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (!Int(m.Groups["sure"], out int sure) || !Int(m.Groups["ayet"], out int ayet) || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Meal, Meal = meal, Sure = sure, Ayet = ayet, Span = span };
            return null;
        }

        if (s.StartsWith("tf:", StringComparison.Ordinal))
        {
            Match m = TfPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            string eser = m.Groups["eser"].Value;
            if (eser.Length > MaxSlugLength)
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (!Int(m.Groups["p"], out int p) || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (m.Groups["bolum"].Success)
            {
                string bolum = m.Groups["bolum"].Value;
                if (bolum.Length > MaxSlugLength)
                {
                    return AnchorErrorCode.Uzunluk;
                }

                candidate = new AnchorRef { Kind = AnchorKind.Tfb, Eser = eser, Bolum = bolum, P = p, Span = span };
                return null;
            }

            if (!Int(m.Groups["sure"], out int sure) || !Int(m.Groups["ilk"], out int ilk) || !Int(m.Groups["son"], out int son))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Tf, Eser = eser, Sure = sure, Ilk = ilk, Son = son, P = p, Span = span };
            return null;
        }

        if (s.StartsWith("rn:", StringComparison.Ordinal))
        {
            Match m = RnPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            if (!TryYol(m.Groups["yol"].Value, out ImmutableArray<string> yol)
                || !Int(m.Groups["p"], out int p)
                || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            int cumle = 0;
            if (m.Groups["s"].Success && !Int(m.Groups["s"], out cumle))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Rn, Yol = yol, P = p, S = cumle, Span = span };
            return null;
        }

        if (s.StartsWith("ht:", StringComparison.Ordinal))
        {
            Match m = HtPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            string ceviri = m.Groups["ceviri"].Value;
            string koleksiyon = m.Groups["koleksiyon"].Value;
            if (ceviri.Length > MaxSlugLength || koleksiyon.Length > MaxSlugLength)
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (!Int(m.Groups["no"], out int no) || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.Ht, Ceviri = ceviri, Koleksiyon = koleksiyon, No = no, Span = span };
            return null;
        }

        if (s.StartsWith("h:", StringComparison.Ordinal))
        {
            Match m = HPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            string koleksiyon = m.Groups["koleksiyon"].Value;
            if (koleksiyon.Length > MaxSlugLength)
            {
                return AnchorErrorCode.Uzunluk;
            }

            if (!Int(m.Groups["no"], out int no) || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.H, Koleksiyon = koleksiyon, No = no, Span = span };
            return null;
        }

        if (s.StartsWith("k:", StringComparison.Ordinal))
        {
            Match m = KPattern().Match(s);
            if (!m.Success)
            {
                return AnchorErrorCode.Bicim;
            }

            if (!TryYol(m.Groups["yol"].Value, out ImmutableArray<string> yol)
                || !Int(m.Groups["p"], out int p)
                || !TrySpan(m, out AnchorSpan? span))
            {
                return AnchorErrorCode.Uzunluk;
            }

            candidate = new AnchorRef { Kind = AnchorKind.K, Yol = yol, P = p, Span = span };
            return null;
        }

        return AnchorErrorCode.Bicim;
    }

    private static bool Int(Group g, out int value)
    {
        return int.TryParse(g.ValueSpan, NumberStyles.None, CultureInfo.InvariantCulture, out value);
    }

    /// <summary>Yol derinligi ve her ogenin uzunlugu sinirlar icindeyse true.</summary>
    private static bool TryYol(string yol, out ImmutableArray<string> parts)
    {
        string[] split = yol.Split(':');
        parts = ImmutableArray<string>.Empty;
        if (split.Length > MaxDepth)
        {
            return false;
        }

        foreach (string part in split)
        {
            if (part.Length > MaxSlugLength)
            {
                return false;
            }
        }

        parts = [.. split];
        return true;
    }

    /// <summary>Aralik grubu yoksa span null ve true; sayi tasarsa false.</summary>
    private static bool TrySpan(Match m, out AnchorSpan? span)
    {
        span = null;
        if (!m.Groups["bas"].Success)
        {
            return true;
        }

        if (!Int(m.Groups["bas"], out int bas) || !Int(m.Groups["bit"], out int bit))
        {
            return false;
        }

        span = new AnchorSpan(bas, bit);
        return true;
    }

    private static AnchorErrorCode? Validate(AnchorRef a)
    {
        bool hasSure = a.Kind is AnchorKind.Q or AnchorKind.Qa or AnchorKind.Meal or AnchorKind.Tf;
        if (hasSure && (a.Sure < 1 || a.Sure > AyetSayilari.Sayilar.Length))
        {
            return AnchorErrorCode.SureAraligi;
        }

        if (hasSure)
        {
            int n = AyetSayilari.Sayilar[a.Sure - 1];
            bool tooBig = a.Kind switch
            {
                AnchorKind.Q or AnchorKind.Meal => a.Ayet > n,
                _ => a.Ilk > n || a.Son > n,
            };
            if (tooBig)
            {
                return AnchorErrorCode.AyetAraligi;
            }
        }

        bool reversed = a.Kind switch
        {
            AnchorKind.Q => a.Ilk > 0 && a.Son > 0 && a.Ilk > a.Son,
            AnchorKind.Qa or AnchorKind.Tf => a.Ilk > a.Son,
            _ => false,
        };
        if (reversed || (a.Span is { } span && span.Start >= span.End))
        {
            return AnchorErrorCode.TersAralik;
        }

        bool notCanonical = a.Kind switch
        {
            AnchorKind.Q => a.Ilk > 0 && a.Son > 0 && a.Ilk == a.Son,
            AnchorKind.Qa => a.Ilk == a.Son,
            _ => false,
        };
        return notCanonical ? AnchorErrorCode.KanonikDegil : null;
    }
}
