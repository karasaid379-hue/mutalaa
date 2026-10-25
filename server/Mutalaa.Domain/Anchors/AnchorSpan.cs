namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Kod noktasi araligi <c>[Start, End)</c>; baslangic dahil, bitis haric (K-26).
/// </summary>
public readonly record struct AnchorSpan(int Start, int End);

/// <summary>
/// Bir ayet (sure, ayet).
/// </summary>
public readonly record struct AyahRef(int Sure, int Ayet);

/// <summary>
/// Depolama bicimi: uc birim capasi ve isteye bagli aralik (<c>xref</c>, <c>xref_idx</c>).
/// </summary>
public readonly record struct UnitSpan(AnchorRef Unit, AnchorSpan? Span);

/// <summary>
/// <see cref="AnchorRef.ToRoute(RouteTarget, string?)"/> hedefi.
/// </summary>
public enum RouteTarget
{
    /// <summary>Yerel (uygulama ici derin baglanti) rota.</summary>
    Native,

    /// <summary>Web rotasi (yalniz Capa semasi 11 tablosundaki bicimler).</summary>
    Web,
}
