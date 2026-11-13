using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.lugat_madde satiri (Editoryal veritabani 5; K-51 madde 9 ve 10): Risale lugat maddesi. Hat basliksozu, siklik ve sozluk
/// basvurusuyla <c>aday</c> acar; tanimi editor yazar (<c>tanim_tr</c> bos kalir), onayda <c>onayli</c> olur.
/// </summary>
public sealed class LugatMadde
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public int Id { get; set; }

    public required string SourceId { get; set; }

    /// <summary>Ucuncu taraf basliksoz, bayt bayt.</summary>
    public required string Basliksoz { get; set; }

    public required string BasliksozNorm { get; set; }

    public string? OsmanlicaYazim { get; set; }

    public string? KokenDil { get; set; }

    /// <summary>Editorun yazdigi tanim; kendi urettigimiz metin (ilk kayitta NFC). Aday bos olabilir; onayli bos olamaz (CHECK).</summary>
    public string? TanimTr { get; set; }

    public int? ArKokId { get; set; }

    /// <summary>jsonb: <c>siklik</c> (int), <c>kitaplar</c>, sozluk isabetleri ... salt basvuru; paketlenmez. Anlam basvurusu (<c>anlam_basvuru</c>) burada DEGIL, <c>review.onerilen</c> icindedir (K-51 madde 10).</summary>
    public string Kaynaklar { get; set; } = "{}";

    /// <summary>Okur yogunluk ayarini besleyen duzey.</summary>
    public short Duzey { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    /// <summary><c>hat</c> ya da <c>editor</c> (CHECK).</summary>
    public required string Origin { get; set; }

    /// <summary>Icerik surumu ('1', onayda +1); lemma_gloss.version ile ayni tur.</summary>
    public string Version { get; set; } = "1";

    public required string ContentHash { get; set; }

    public required string DataVersion { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime UpdatedAt { get; set; }
}
