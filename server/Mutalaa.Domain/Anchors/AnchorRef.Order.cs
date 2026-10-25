using System.Collections.Immutable;

namespace Mutalaa.Domain.Anchors;

// Siralama ve kapsama: Capa semasi 11, K-35 madde 3 ve 4.
public sealed partial record AnchorRef
{
    /// <summary>
    /// Belirlenimci anahtar sirasi (K-35 madde 3). Kur'an capalari okuma sirasiyla (q ve qa), sonra
    /// meal &lt; tf &lt; tfb &lt; rn &lt; h &lt; ht &lt; k &lt; konu. Sonuc -1, 0 ya da 1 olur.
    /// </summary>
    public int CompareTo(AnchorRef? other)
    {
        if (other is null)
        {
            return 1;
        }

        int c = Math.Sign(Rank(Kind).CompareTo(Rank(other.Kind)));
        if (c != 0)
        {
            return c;
        }

        switch (Kind)
        {
            case AnchorKind.Q:
            case AnchorKind.Qa:
                return Math.Sign(QuranKey(this).CompareTo(QuranKey(other)));
            case AnchorKind.Meal:
                return First(
                    string.CompareOrdinal(Meal, other.Meal),
                    Sure.CompareTo(other.Sure),
                    Ayet.CompareTo(other.Ayet),
                    CompareSpan(Span, other.Span));
            case AnchorKind.Tf:
                return First(
                    string.CompareOrdinal(Eser, other.Eser),
                    Sure.CompareTo(other.Sure),
                    Ilk.CompareTo(other.Ilk),
                    Son.CompareTo(other.Son),
                    P.CompareTo(other.P),
                    CompareSpan(Span, other.Span));
            case AnchorKind.Tfb:
                return First(
                    string.CompareOrdinal(Eser, other.Eser),
                    string.CompareOrdinal(Bolum, other.Bolum),
                    P.CompareTo(other.P),
                    CompareSpan(Span, other.Span));
            case AnchorKind.Rn:
                // Cumle numarasi araliktan once karsilastirilir: p4 < p4@0-5 < p4:s1.
                return First(
                    CompareYol(Yol, other.Yol),
                    P.CompareTo(other.P),
                    S.CompareTo(other.S),
                    CompareSpan(Span, other.Span));
            case AnchorKind.H:
                return First(
                    string.CompareOrdinal(Koleksiyon, other.Koleksiyon),
                    No.CompareTo(other.No),
                    CompareSpan(Span, other.Span));
            case AnchorKind.Ht:
                return First(
                    string.CompareOrdinal(Ceviri, other.Ceviri),
                    string.CompareOrdinal(Koleksiyon, other.Koleksiyon),
                    No.CompareTo(other.No),
                    CompareSpan(Span, other.Span));
            case AnchorKind.K:
                return First(
                    CompareYol(Yol, other.Yol),
                    P.CompareTo(other.P),
                    CompareSpan(Span, other.Span));
            case AnchorKind.Konu:
                return Math.Sign(string.CompareOrdinal(Slug, other.Slug));
            default:
                throw new InvalidOperationException();
        }
    }

    private static int Rank(AnchorKind kind) => kind switch
    {
        AnchorKind.Q or AnchorKind.Qa => 0,
        AnchorKind.Meal => 1,
        AnchorKind.Tf => 2,
        AnchorKind.Tfb => 3,
        AnchorKind.Rn => 4,
        AnchorKind.H => 5,
        AnchorKind.Ht => 6,
        AnchorKind.K => 7,
        AnchorKind.Konu => 8,
        _ => throw new InvalidOperationException(),
    };

    /// <summary>
    /// (sure, baslangic ayeti, alt sira, kelime baslangici, bitis var mi, bitis).
    /// Alt sira: ayet 0, kelime ya da kelime araligi 1, ayet araligi 2.
    /// </summary>
    private static (int, int, int, int, int, int) QuranKey(AnchorRef a)
    {
        if (a.Kind == AnchorKind.Qa)
        {
            return (a.Sure, a.Ilk, 2, 0, 1, a.Son);
        }

        if (a.Ilk == 0)
        {
            return (a.Sure, a.Ayet, 0, 0, 0, 0);
        }

        return (a.Sure, a.Ayet, 1, a.Ilk, a.Son > 0 ? 1 : 0, a.Son);
    }

    private static int First(params int[] results)
    {
        foreach (int r in results)
        {
            if (r != 0)
            {
                return Math.Sign(r);
            }
        }

        return 0;
    }

    private static int CompareYol(ImmutableArray<string> a, ImmutableArray<string> b)
    {
        int n = Math.Min(a.Length, b.Length);
        for (int i = 0; i < n; i++)
        {
            int c = string.CompareOrdinal(a[i], b[i]);
            if (c != 0)
            {
                return Math.Sign(c);
            }
        }

        return a.Length.CompareTo(b.Length);
    }

    /// <summary>Aralik olmayan once gelir; sonra baslangic, sonra bitis.</summary>
    private static int CompareSpan(AnchorSpan? a, AnchorSpan? b)
    {
        if (a is null)
        {
            return b is null ? 0 : -1;
        }

        if (b is null)
        {
            return 1;
        }

        return First(a.Value.Start.CompareTo(b.Value.Start), a.Value.End.CompareTo(b.Value.End));
    }

    /// <summary>
    /// <paramref name="inner"/> bu capanin kapsami icinde mi (K-35 madde 4). Ayni capa her zaman kapsar;
    /// farkli turler birbirini kapsamaz.
    /// </summary>
    public bool Contains(AnchorRef inner)
    {
        ArgumentNullException.ThrowIfNull(inner);
        if (Equals(inner))
        {
            return true;
        }

        bool outerQuran = Kind is AnchorKind.Q or AnchorKind.Qa;
        bool innerQuran = inner.Kind is AnchorKind.Q or AnchorKind.Qa;
        if (outerQuran || innerQuran)
        {
            return outerQuran && innerQuran && ContainsQuran(this, inner);
        }

        if (Kind != inner.Kind || Kind == AnchorKind.Konu)
        {
            return false;
        }

        // Cumle capasi yalniz kendini kapsar.
        if (S > 0 || !SameBase(this, inner))
        {
            return false;
        }

        // Araliksiz birim kendi araliklarini ve cumlelerini kapsar.
        if (Span is not { } outerSpan)
        {
            return true;
        }

        // Araliklu birim cumleyi kapsamaz; [a, b) icindeki [c, d) kapsanir.
        return inner.S == 0
            && inner.Span is { } innerSpan
            && outerSpan.Start <= innerSpan.Start
            && innerSpan.End <= outerSpan.End;
    }

    private static bool ContainsQuran(AnchorRef outer, AnchorRef inner)
    {
        if (outer.Sure != inner.Sure)
        {
            return false;
        }

        if (outer.Kind == AnchorKind.Qa)
        {
            if (inner.Kind == AnchorKind.Qa)
            {
                return outer.Ilk <= inner.Ilk && inner.Son <= outer.Son;
            }

            return outer.Ilk <= inner.Ayet && inner.Ayet <= outer.Son;
        }

        // outer: ayet, kelime ya da kelime araligi.
        if (inner.Kind == AnchorKind.Qa || outer.Ayet != inner.Ayet)
        {
            return false;
        }

        if (outer.Ilk == 0)
        {
            return true;
        }

        if (inner.Ilk == 0)
        {
            return false;
        }

        int outerLast = outer.Son > 0 ? outer.Son : outer.Ilk;
        int innerLast = inner.Son > 0 ? inner.Son : inner.Ilk;
        return outer.Ilk <= inner.Ilk && innerLast <= outerLast;
    }

    /// <summary>Cumle numarasi ve aralik disindaki butun alanlar esit mi.</summary>
    private static bool SameBase(AnchorRef a, AnchorRef b)
    {
        return (a with { S = 0, Span = null }).Equals(b with { S = 0, Span = null });
    }
}
