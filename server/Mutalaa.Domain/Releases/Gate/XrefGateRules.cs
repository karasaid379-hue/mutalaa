using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>Tur kapisinin durumu (K-51 madde 5 ve 11).</summary>
public enum XrefGateStatus
{
    /// <summary>xref_gate'te altin ya da silver sinifinda satir yok (yalniz sentetik satir kapi acmaz): tur olculmemis sayilir.</summary>
    NotMeasured = 0,

    /// <summary>Kapiyi belirleyen satir (altin, yoksa silver) "kaldi".</summary>
    Failed = 1,

    /// <summary>Kapiyi belirleyen satir (altin, yoksa silver) "gecti": otomatik turun aday satirlari public'e girebilir.</summary>
    Passed = 2,
}

/// <summary>Bir turun kapi durumu ve kapiyi belirleyen set sinifi (olculmediyse SetClass null).</summary>
public readonly record struct XrefTypeGate(XrefGateStatus Status, string? SetClass, string? Result)
{
    public static XrefTypeGate NotMeasured { get; } = new(XrefGateStatus.NotMeasured, null, null);

    public bool Opens => Status == XrefGateStatus.Passed;
}

/// <summary>
/// xref_gate kurallari (K-51 madde 5 ve 11; Yayin sureci 4). Kapi yalniz otomatik turler icin vardir: kok, lemma, benzer_ayet
/// (anlamsal public'e hic girmez; insan onayi isteyen turler kapiya bakmaz). Altin ya da silver sinifi kapiyi belirler (ikisi de varsa altin);
/// sentetik sinif kapi acmaz ve kapatmaz, yalniz motor testidir.
/// </summary>
public static class XrefGateRules
{
    public const string Altin = "altin";
    public const string Silver = "silver";
    public const string Gecti = "gecti";
    public const string Kaldi = "kaldi";

    /// <summary>Kapisi olan turler (kok, lemma, benzer_ayet).</summary>
    public static bool HasGate(XrefType type) => type is XrefType.Kok or XrefType.Lemma or XrefType.BenzerAyet;

    /// <summary>Turun kapi durumu. Tanimsiz sinif ya da sonuc dizgileri yok sayilir.</summary>
    public static XrefTypeGate Resolve(IEnumerable<GateMeasurement> measurements, XrefType type)
    {
        ArgumentNullException.ThrowIfNull(measurements);

        GateMeasurement? gold = null;
        GateMeasurement? silver = null;
        foreach (GateMeasurement m in measurements)
        {
            if (m.Type != type || !IsKnownResult(m.Result))
            {
                continue;
            }

            if (string.Equals(m.SetClass, Altin, StringComparison.Ordinal))
            {
                gold = m;
            }
            else if (string.Equals(m.SetClass, Silver, StringComparison.Ordinal))
            {
                silver = m;
            }
        }

        GateMeasurement? decisive = gold ?? silver;
        if (decisive is null)
        {
            return XrefTypeGate.NotMeasured;
        }

        return new XrefTypeGate(
            string.Equals(decisive.Result, Gecti, StringComparison.Ordinal) ? XrefGateStatus.Passed : XrefGateStatus.Failed,
            decisive.SetClass,
            decisive.Result);
    }

    /// <summary>Kapi durumunun P-07 ve P-09 gerekcesi: olculmediyse kapi-olculmedi, kaldiysa kapi-gecmedi; gectiyse null.</summary>
    public static string? ReasonWhenClosed(XrefTypeGate gate) => gate.Status switch
    {
        XrefGateStatus.Passed => null,
        XrefGateStatus.Failed => GateReasons.KapiGecmedi,
        _ => GateReasons.KapiOlculmedi,
    };

    private static bool IsKnownResult(string result) =>
        string.Equals(result, Gecti, StringComparison.Ordinal) || string.Equals(result, Kaldi, StringComparison.Ordinal);
}
