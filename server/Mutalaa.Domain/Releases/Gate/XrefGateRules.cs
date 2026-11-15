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
/// Bir kapinin kimligi: baglanti turu ve alt tur (K-51 madde 5). Etiket "tur" (alt tur bos) ya da "tur/alt_tur"; rapor satirlari ve pack_meta gate_summary
/// anahtarlari bu etiketi kullanir.
/// </summary>
public readonly record struct GateKey(XrefType Type, string SubType)
{
    public string Label => SubType.Length == 0 ? Type.ToLabel() : Type.ToLabel() + "/" + SubType;
}

/// <summary>
/// xref_gate kurallari (K-51 madde 5 ve 11; Yayin sureci 4). Kapi yalniz otomatik turler icin vardir: kok, lemma, benzer_ayet
/// (anlamsal public'e hic girmez; insan onayi isteyen turler kapiya bakmaz). Her kapi tur ve alt turle belirlenir: kok/xref (P-07, Kur'an ici kok
/// baglantilari), kok/tr_lemma (P-09, Turkce -> Arapca kok eslemesinin olcumu), lemma, benzer_ayet/sozluksel (kendi olcumune bagli) ve benzer_ayet/alim
/// (QurSim; kaynagi geregi guvenilir). Altin ya da silver sinifi kapiyi belirler (ikisi de varsa altin); sentetik sinif kapi acmaz ve kapatmaz, yalniz
/// motor testidir. Alt turu tutmayan olcum satiri (ornegin eski bos alt turlu kok satiri) kapiyi acmaz: yeniden olculene kadar kapi kapali kalir.
/// </summary>
public static class XrefGateRules
{
    public const string Altin = "altin";
    public const string Silver = "silver";
    public const string Gecti = "gecti";
    public const string Kaldi = "kaldi";

    /// <summary>Kapisi olan turler (kok, lemma, benzer_ayet).</summary>
    public static bool HasGate(XrefType type) => type is XrefType.Kok or XrefType.Lemma or XrefType.BenzerAyet;

    /// <summary>Kapi kimlikleri, rapor ve cozum sirasiyla: kok/xref, kok/tr_lemma, lemma, benzer_ayet/sozluksel, benzer_ayet/alim.</summary>
    public static IReadOnlyList<GateKey> AllKeys { get; } =
    [
        new(XrefType.Kok, XrefGateSubtypes.Xref),
        new(XrefType.Kok, XrefGateSubtypes.TrLemma),
        new(XrefType.Lemma, XrefGateSubtypes.None),
        new(XrefType.BenzerAyet, XrefGateSubtypes.Sozluksel),
        new(XrefType.BenzerAyet, XrefGateSubtypes.Alim),
    ];

    /// <summary>Kapi kimligi: Turkce lemma eslemesinin (P-09) kapisi.</summary>
    public static GateKey TrLemmaKey { get; } = new(XrefType.Kok, XrefGateSubtypes.TrLemma);

    /// <summary>
    /// Baglanti satirinin kapisi (P-07): kok -> (kok, xref); lemma -> (lemma, ''); benzer_ayet -> alim (evidence.source_id = qursim ya da evidence.qursim
    /// nesnesi var) ya da sozluksel. Kapisi olmayan turde alt tur bos kalir.
    /// </summary>
    public static GateKey GateKeyOf(XrefType type, string? evidenceSourceId, bool hasQursimEvidence) => type switch
    {
        XrefType.Kok => new GateKey(type, XrefGateSubtypes.Xref),
        XrefType.BenzerAyet => new GateKey(
            type,
            hasQursimEvidence || string.Equals(evidenceSourceId, "qursim", StringComparison.Ordinal) ? XrefGateSubtypes.Alim : XrefGateSubtypes.Sozluksel),
        _ => new GateKey(type, XrefGateSubtypes.None),
    };

    /// <summary>Kapi durumu (tur ve alt tur). Tanimsiz sinif ya da sonuc dizgileri ve alt turu tutmayan satirlar yok sayilir.</summary>
    public static XrefTypeGate Resolve(IEnumerable<GateMeasurement> measurements, GateKey key)
    {
        ArgumentNullException.ThrowIfNull(measurements);
        XrefType type = key.Type;

        GateMeasurement? gold = null;
        GateMeasurement? silver = null;
        foreach (GateMeasurement m in measurements)
        {
            if (m.Type != type || !string.Equals(m.SubType, key.SubType, StringComparison.Ordinal) || !IsKnownResult(m.Result))
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
