namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Capa turu. Etiketler Capa semasi 11'deki <c>t</c> alaniyla aynidir.
/// </summary>
public enum AnchorKind
{
    /// <summary>q: ayet, kelime ya da kelime araligi.</summary>
    Q,

    /// <summary>q: ayet araligi (kendi metni yok).</summary>
    Qa,

    /// <summary>konu: konu dugumu.</summary>
    Konu,

    /// <summary>meal: meal paragrafi.</summary>
    Meal,

    /// <summary>tf: ayete bagli tefsir paragrafi.</summary>
    Tf,

    /// <summary>tf: ayetten bagimsiz tefsir bolumu.</summary>
    Tfb,

    /// <summary>rn: Risale paragrafi ya da cumlesi.</summary>
    Rn,

    /// <summary>h: hadis.</summary>
    H,

    /// <summary>ht: hadis cevirisi.</summary>
    Ht,

    /// <summary>k: kitap paragrafi.</summary>
    K,
}
