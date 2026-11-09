namespace Mutalaa.Domain.Releases.Gate;

/// <summary>Kapi raporu satirinin karari: pakete girdi ya da girmedi.</summary>
public enum GateDecision
{
    Girdi = 0,
    Girmedi = 1,
}

/// <summary>Kapi raporu satirinin konusu.</summary>
public enum GateSubjectKind
{
    Paket = 0,
    Kaynak = 1,
    Birim = 2,
    Baglanti = 3,
    Sozluk = 4,
}

/// <summary>Rapor JSON etiketleri. Acik switch; yansima ve kulturlu donusum yok.</summary>
public static class GateLabels
{
    public static string ToLabel(this GateDecision value) => value switch
    {
        GateDecision.Girdi => "girdi",
        GateDecision.Girmedi => "girmedi",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };

    public static string ToLabel(this GateSubjectKind value) => value switch
    {
        GateSubjectKind.Paket => "paket",
        GateSubjectKind.Kaynak => "kaynak",
        GateSubjectKind.Birim => "birim",
        GateSubjectKind.Baglanti => "baglanti",
        GateSubjectKind.Sozluk => "sozluk",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, null),
    };
}
