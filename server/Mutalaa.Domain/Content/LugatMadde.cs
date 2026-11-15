using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.lugat_madde satiri (Editoryal veritabani 5; K-52 madde 9, 10 ve 14): Risale lugat maddesi. Hat, lugat kaynagindan tanimli
/// (<c>origin = 'kaynak'</c>, bayt bayt) ya da yalniz Risale basliksozunden tanimsiz (<c>origin = 'hat'</c>) <c>aday</c> acar;
/// editor kaynak tanimini degistirmeden onaylar ya da duzenleyip onaylar (<c>origin = 'editor'</c>), tanimsiz adayin tanimini yazar.
/// </summary>
public sealed class LugatMadde
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public int Id { get; set; }

    public required string SourceId { get; set; }

    /// <summary>Ucuncu taraf basliksoz, bayt bayt.</summary>
    public required string Basliksoz { get; set; }

    public required string BasliksozNorm { get; set; }

    /// <summary>Ayni (kaynak, basliksoz) icin kaynak sirasiyla anlam sirasi (1'den; K-52 madde 14). Veritabani varsayilani 1.</summary>
    public short AnlamNo { get; set; } = 1;

    public string? OsmanlicaYazim { get; set; }

    public string? KokenDil { get; set; }

    /// <summary>
    /// Editorun yazdigi (<c>origin = 'editor'</c>; ilk kayitta NFC) ya da lugat kaynagindan gelen (<c>origin = 'kaynak'</c>; bayt bayt, NFC yok) tanim.
    /// <c>hat</c> adayi bos olabilir; onayli bos olamaz (CHECK).
    /// </summary>
    public string? TanimTr { get; set; }

    public int? ArKokId { get; set; }

    /// <summary>jsonb: <c>siklik</c> (int), <c>kitaplar</c>, sozluk isabetleri ... salt basvuru; paketlenmez. Anlam basvurusu (<c>anlam_basvuru</c>) burada DEGIL, <c>review.onerilen</c> icindedir (K-52 madde 10).</summary>
    public string Kaynaklar { get; set; } = "{}";

    /// <summary>Risale siklik duzeyi: 1..3 siklik, 4 = Risale baslik soz listesinde yok (CHECK 1..4).</summary>
    public short Duzey { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    /// <summary><c>hat</c> (tanimsiz aday), <c>kaynak</c> (lugat kaynagindan tanim) ya da <c>editor</c> (CHECK).</summary>
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
