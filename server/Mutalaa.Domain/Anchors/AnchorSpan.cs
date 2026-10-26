namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Yari acik tamsayi araligi <c>[Start, End)</c>; baslangic dahil, bitis haric (K-26). Birimi baglama gore uc anlam tasir:
/// <list type="number">
/// <item><description>Kod noktasi araligi: birim metninde (<c>@</c> araligi, <c>unit.sentences</c>, metin birimi ucunda <c>xref.*_span</c>).</description></item>
/// <item><description>Kuresel ayet sirasi araligi 1..6236: <c>unit.ayah_range</c> (kod noktasi degildir).</description></item>
/// <item><description>Kelime konumu araligi: Kur'an ucunda <c>xref.*_span</c> (<c>q:2:255:3-7</c> icin <c>[3, 8)</c>).</description></item>
/// </list>
/// Tur birimi tasimaz; hangisi oldugu kullanildigi sutundan bellidir.
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
