namespace Mutalaa.Domain.Links;

/// <summary>
/// icerik.xref_gate satiri (K-51 madde 5 ve 11): tur bazinda yayin kapisi sonucu. <c>qa gold</c> yazar, Yayinlayici okur.
/// Birincil anahtar (Tur, SetSinifi): her set sinifi icin son olcum tutulur; sentetik sinif satiri kapi acmaz ama kayitlidir.
/// </summary>
public sealed class XrefGate
{
    public required XrefType Tur { get; set; }

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
