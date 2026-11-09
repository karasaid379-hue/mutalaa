namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Kalite kapisi kural kodlari (Yayin sureci 4). Sayisal deger kodun numarasidir (P07 = 7).
/// P-02...P-06 yoktur ve numaralar yeniden verilmez; enum'a eklenmez.
/// </summary>
public enum GateRule
{
    P01 = 1,
    P07 = 7,
    P08 = 8,
    P09 = 9,
    P10 = 10,
    P11 = 11,
    P12 = 12,
    P13 = 13,
    P14 = 14,
}

/// <summary>GateRule icin kod ("P-01") eslemesi. Acik switch; yansima, Enum.ToString ve kulturlu donusum yok.</summary>
public static class GateRuleCodes
{
    /// <summary>Kural kodunu ("P-07") dondurur; tanimsiz sayisal deger ArgumentOutOfRangeException atar.</summary>
    public static string ToCode(this GateRule rule) => rule switch
    {
        GateRule.P01 => "P-01",
        GateRule.P07 => "P-07",
        GateRule.P08 => "P-08",
        GateRule.P09 => "P-09",
        GateRule.P10 => "P-10",
        GateRule.P11 => "P-11",
        GateRule.P12 => "P-12",
        GateRule.P13 => "P-13",
        GateRule.P14 => "P-14",
        _ => throw new ArgumentOutOfRangeException(nameof(rule), rule, null),
    };

    /// <summary>Kodu tam (Ordinal, buyuk-kucuk harf duyarli, kirpmasiz) eslestirir; "P-02"..."P-06" ve bilinmeyen kodlar false verir.</summary>
    public static bool TryParse(string? code, out GateRule rule)
    {
        switch (code)
        {
            case "P-01":
                rule = GateRule.P01;
                return true;
            case "P-07":
                rule = GateRule.P07;
                return true;
            case "P-08":
                rule = GateRule.P08;
                return true;
            case "P-09":
                rule = GateRule.P09;
                return true;
            case "P-10":
                rule = GateRule.P10;
                return true;
            case "P-11":
                rule = GateRule.P11;
                return true;
            case "P-12":
                rule = GateRule.P12;
                return true;
            case "P-13":
                rule = GateRule.P13;
                return true;
            case "P-14":
                rule = GateRule.P14;
                return true;
            default:
                rule = default;
                return false;
        }
    }
}
