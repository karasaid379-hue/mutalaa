using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Links;

/// <summary>
/// icerik.xref satiri (Editoryal veritabani 7; K-27). Uclar birim duzeyindedir; aralik ayri sutundadir
/// (Kur'an ucunda kelime konumu, metin biriminde kod noktasi).
/// </summary>
public sealed class Xref
{
    /// <summary>Veritabani uuidv7() yazar.</summary>
    public Guid Id { get; set; }

    public required AnchorRef SrcAnchor { get; set; }

    /// <summary>
    /// Kaynak ucun araligi: Kur'an ucunda kelime konumu [ilk, son+1) (AnchorSpan anlami 3), metin biriminde kod noktasi (anlam 1).
    /// </summary>
    public AnchorSpan? SrcSpan { get; set; }

    public required AnchorRef DstAnchor { get; set; }

    /// <summary>Hedef ucun araligi; SrcSpan ile ayni anlam kurallari.</summary>
    public AnchorSpan? DstSpan { get; set; }

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required XrefType Type { get; set; }

    public float Score { get; set; }

    public float Confidence { get; set; }

    /// <summary>jsonb.</summary>
    public string Evidence { get; set; } = "{}";

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required XrefOrigin Origin { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    public int VotesUp { get; set; }

    public int VotesDown { get; set; }

    public required string DataVersion { get; set; }
}
