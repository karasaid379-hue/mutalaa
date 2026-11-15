namespace Mutalaa.Domain.Links;

/// <summary>
/// icerik.xref_gate satiri (K-51 madde 5 ve 11): tur bazinda yayin kapisi sonucu. <c>qa gold</c> yazar, Yayinlayici okur.
/// Birincil anahtar (Tur, AltTur, SetSinifi): her kapi (tur ve alt tur) ve set sinifi icin son olcum tutulur; sentetik sinif satiri kapi acmaz ama kayitlidir.
/// Alt tur (K-51 madde 5): benzer_ayet icin sozluksel ya da alim, kok icin tr_lemma ya da xref; lemma ve ote turler icin bos dizgi.
/// </summary>
public sealed class XrefGate
{
    public required XrefType Tur { get; set; }

    /// <summary>Kapi alt turu (<see cref="XrefGateSubtypes"/>); alt turu olmayan turlerde bos dizgi.</summary>
    public required string AltTur { get; set; }

    /// <summary>altin, silver ya da sentetik (<see cref="XrefGateSetClasses"/>).</summary>
    public required string SetSinifi { get; set; }

    public required string SetSurumu { get; set; }

    /// <summary>gecti ya da kaldi (<see cref="XrefGateResults"/>).</summary>
    public required string Sonuc { get; set; }

    /// <summary>Set manifestindeki kaynak kimlikleri (source_id); dondulugu denetimi icin saklanir.</summary>
    public required string[] SetKaynaklari { get; set; }

    /// <summary>Olcum raporunun SHA-256 ozeti (kucuk harf, 64 hane).</summary>
    public required string RaporSha256 { get; set; }

    public required string DataVersion { get; set; }

    /// <summary>Veritabani now() yazar (UTC).</summary>
    public DateTime OlculduAt { get; set; }
}

/// <summary>xref_gate.set_sinifi degerleri (K-51 madde 10 ve 11).</summary>
public static class XrefGateSetClasses
{
    public const string Altin = "altin";
    public const string Silver = "silver";
    public const string Sentetik = "sentetik";
}

/// <summary>xref_gate.sonuc degerleri.</summary>
public static class XrefGateResults
{
    public const string Gecti = "gecti";
    public const string Kaldi = "kaldi";
}

/// <summary>
/// xref_gate.alt_tur degerleri (K-51 madde 5). benzer_ayet: <see cref="Sozluksel"/> (Tanzil n-gram, kendi olcumune bagli) ya da <see cref="Alim"/> (QurSim:
/// alim kaynakli, kaynagi geregi guvenilir sayilir). kok: <see cref="TrLemma"/> (Turkce -> Arapca kok esleme olcumu, P-09) ya da <see cref="Xref"/>
/// (Kur'an ici kok baglantilarinin tutarliligi, P-07). Oteki turler bos dizgi (<see cref="None"/>) tasir.
/// </summary>
public static class XrefGateSubtypes
{
    public const string None = "";
    public const string Sozluksel = "sozluksel";
    public const string Alim = "alim";
    public const string TrLemma = "tr_lemma";
    public const string Xref = "xref";

    /// <summary>Tur ve alt tur tutarli mi (veritabani CHECK kisitinin esi): benzer_ayet yalniz sozluksel|alim, kok yalniz tr_lemma|xref, ote turler bos.</summary>
    public static bool IsValid(XrefType type, string subtype) => type switch
    {
        XrefType.BenzerAyet => subtype is Sozluksel or Alim,
        XrefType.Kok => subtype is TrLemma or Xref,
        _ => subtype.Length == 0,
    };
}
