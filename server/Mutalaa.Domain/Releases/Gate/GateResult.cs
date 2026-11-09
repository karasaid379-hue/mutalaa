namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Tek baglantinin kapi sonucu. Approved = durum onayli ("dogrulanmamis" rozeti icin tersi); Folded = anlamsal ya da
/// (otomatik tur, onaysiz, confidence &lt; 0,70). Included false ise Rule P-07 olur.
/// Detail yalniz Reason "uc-birim-girmedi" iken dolar (K-47): hangi ucun hangi nedenle disarida kaldigi ("kaynak=P-10:onaysiz-birim,hedef=kullanim-disi");
/// kapi raporu satirinda gerekce "uc-birim-girmedi:" + Detail olarak yazilir. Geriye uyumlu: varsayilan bos.
/// </summary>
public readonly record struct XrefVerdict(bool Included, bool Approved, bool Folded, GateRule? Rule, string Reason, string Detail = "");

/// <summary>
/// Kapi sonucu: rapor ve pakete girebilecek kumeler. Girmeyen oge kumede yoktur.
/// Birim kumesi capa dizgisiyle, sozluk kumesi "{tablo_etiketi}:{id}" anahtariyla, baglanti karari Guid ile anahtarlanir.
/// </summary>
public sealed class GateResult
{
    public GateResult(
        GateReport report,
        IReadOnlySet<string> includedPacks,
        IReadOnlySet<string> includedSources,
        IReadOnlySet<string> includedUnits,
        IReadOnlySet<string> includedLexicals,
        IReadOnlyDictionary<Guid, XrefVerdict> xrefVerdicts)
    {
        Report = report;
        IncludedPacks = includedPacks;
        IncludedSources = includedSources;
        IncludedUnits = includedUnits;
        IncludedLexicals = includedLexicals;
        XrefVerdicts = xrefVerdicts;
    }

    public GateReport Report { get; }

    public bool Rejected => Report.Rejected;

    public IReadOnlySet<string> IncludedPacks { get; }

    public IReadOnlySet<string> IncludedSources { get; }

    public IReadOnlySet<string> IncludedUnits { get; }

    public IReadOnlySet<string> IncludedLexicals { get; }

    public IReadOnlyDictionary<Guid, XrefVerdict> XrefVerdicts { get; }

    /// <summary>Baglanti pakete giriyor mu (karar yoksa false).</summary>
    public bool IsXrefIncluded(Guid id) => XrefVerdicts.TryGetValue(id, out XrefVerdict v) && v.Included;
}
