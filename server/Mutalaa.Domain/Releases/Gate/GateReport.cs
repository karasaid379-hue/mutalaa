using System.Globalization;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Kapi raporu satiri. Paket ve kaynak satiri tektir (Count 1). Birim, baglanti ve sozluk satirlari gruplanir:
/// Birim icin Id kaynak slug'i, Baglanti icin tur etiketi, Sozluk icin tablo etiketidir; Count o gruptaki satir sayisidir.
/// Rule yalniz "girmedi" satirinda ve yalniz bir kural verdiyse dolar (icerik-yok ve kullanim-disi kural kodu tasimaz).
/// </summary>
public sealed record GateReportRow(
    GateSubjectKind Kind,
    string Id,
    GateDecision Decision,
    GateRule? Rule,
    string Reason,
    int Count = 1);

/// <summary>
/// Butunluk ihlali (yayini reddeder). Rule null ise kural kodu yoktur (capa sureklilik denetimi).
/// Subject paket, kaynak ya da capa kimligidir.
/// </summary>
public sealed record GateViolation(GateRule? Rule, string Subject, string Reason);

/// <summary>
/// Raporda (JSON ve konsol) gosterilmeyen ihlallerin gerekce basina sayisi: bir (kural, gerekce) grubunda
/// <see cref="GateReport.MaxViolationsShown"/> ihlalden fazlasi varsa fazlasi buraya sayilir.
/// </summary>
public sealed record GateViolationOmission(GateRule? Rule, string Reason, int Count);

/// <summary>
/// Kapi raporu (release.kapi_raporu). Satirlar ve ihlaller kararli sirada tutulur; ToJson ayni girdiyle ayni baytlari verir.
/// <see cref="Violations"/> tam listedir (Rejected ve toplam sayi buradan); JSON ve konsol ciktisi her (kural, gerekce) grubunda ilk
/// <see cref="MaxViolationsShown"/> ihlali gosterir (bir kaynagin tamami taslaga donunce binlerce capa olabilir); gosterilmeyenlerin sayisi
/// <see cref="OmittedViolations"/> ile "violations_omitted" alaninda ve konsolda "ve N tane daha" satirinda yer alir.
/// </summary>
public sealed class GateReport
{
    private GateReport(BuildFlavor flavor, GateReportRow[] rows, GateViolation[] violations)
    {
        Flavor = flavor;
        Rows = rows;
        Violations = violations;
    }

    public BuildFlavor Flavor { get; }

    public IReadOnlyList<GateReportRow> Rows { get; }

    /// <summary>Gerekce (kural + gerekce) basina rapora yazilan en cok ihlal sayisi.</summary>
    public const int MaxViolationsShown = 50;

    public IReadOnlyList<GateViolation> Violations { get; }

    /// <summary>Her (kural, gerekce) grubunda ilk <see cref="MaxViolationsShown"/> ihlal (kararli sirada); JSON ve konsol bunu yazar.</summary>
    public IReadOnlyList<GateViolation> ShownViolations => Limit().Shown;

    /// <summary>Gosterilmeyen ihlallerin grup basina sayisi (kural numarasi, sonra gerekce sirasiyla); sinir asilmadiysa bos.</summary>
    public IReadOnlyList<GateViolationOmission> OmittedViolations => Limit().Omitted;

    /// <summary>Butunluk ihlali varsa true: yayin reddedilir (Yayinlayici cikis kodu 2).</summary>
    public bool Rejected => Violations.Count > 0;

    /// <summary>
    /// Ek butunluk ihlalleriyle (ornegin Infrastructure'daki P-11 ham dosya denetimi ve P-14 terfi denetimi) yeni bir rapor dondurur;
    /// satirlar aynen kalir, ihlaller kararli siraya yeniden dizilir. Bu rapor degismez.
    /// </summary>
    public GateReport WithViolations(IEnumerable<GateViolation> additional)
    {
        ArgumentNullException.ThrowIfNull(additional);
        return Create(Flavor, Rows, Violations.Concat(additional));
    }

    /// <summary>Girdiyi (sira bagimsiz) kararli siraya dizerek rapor olusturur.</summary>
    public static GateReport Create(BuildFlavor flavor, IEnumerable<GateReportRow> rows, IEnumerable<GateViolation> violations)
    {
        ArgumentNullException.ThrowIfNull(rows);
        ArgumentNullException.ThrowIfNull(violations);

        GateReportRow[] sortedRows = [.. rows];
        Array.Sort(sortedRows, CompareRows);
        GateViolation[] sortedViolations = [.. violations];
        Array.Sort(sortedViolations, CompareViolations);
        return new GateReport(flavor, sortedRows, sortedViolations);
    }

    /// <summary>
    /// Belirlenimci JSON (snake_case alan adlari, sabit alan sirasi, bosluksuz). Ornek:
    /// {"flavor":"public","rejected":false,"rows":[{"kind":"kaynak","id":"x","decision":"girdi","rule":null,"reason":"uygun","count":1}],"violations":[]}
    /// </summary>
    public string ToJson()
    {
        using MemoryStream stream = new();
        JsonWriterOptions options = new()
        {
            Indented = false,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };

        using (Utf8JsonWriter writer = new(stream, options))
        {
            writer.WriteStartObject();
            writer.WriteString("flavor", Flavor.ToLabel());
            writer.WriteBoolean("rejected", Rejected);

            writer.WriteStartArray("rows");
            foreach (GateReportRow row in Rows)
            {
                writer.WriteStartObject();
                writer.WriteString("kind", row.Kind.ToLabel());
                writer.WriteString("id", row.Id);
                writer.WriteString("decision", row.Decision.ToLabel());
                WriteRule(writer, row.Rule);
                writer.WriteString("reason", row.Reason);
                writer.WriteNumber("count", row.Count);
                writer.WriteEndObject();
            }

            writer.WriteEndArray();

            writer.WriteStartArray("violations");
            (GateViolation[] shown, GateViolationOmission[] omitted) = Limit();
            foreach (GateViolation violation in shown)
            {
                writer.WriteStartObject();
                WriteRule(writer, violation.Rule);
                writer.WriteString("subject", violation.Subject);
                writer.WriteString("reason", violation.Reason);
                writer.WriteEndObject();
            }

            writer.WriteEndArray();

            // Yalniz sinir asildiysa yazilir (sinirin altindaki raporlarin bicimi degismez): shown + omitted = toplam ihlal.
            if (omitted.Length > 0)
            {
                writer.WriteStartArray("violations_omitted");
                foreach (GateViolationOmission omission in omitted)
                {
                    writer.WriteStartObject();
                    WriteRule(writer, omission.Rule);
                    writer.WriteString("reason", omission.Reason);
                    writer.WriteNumber("count", omission.Count);
                    writer.WriteEndObject();
                }

                writer.WriteEndArray();
            }

            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    /// <summary>
    /// Konsol ihlal satirlari: gosterilen her ihlal icin "IHLAL [kural] konu: gerekce", sinir asilan her grup icin "ve N tane daha [kural] gerekce".
    /// Sayi ve kural kodu kulturden bagimsizdir.
    /// </summary>
    public IReadOnlyList<string> ViolationLines()
    {
        (GateViolation[] shown, GateViolationOmission[] omitted) = Limit();
        List<string> lines = [];
        foreach (GateViolation violation in shown)
        {
            lines.Add($"  IHLAL [{RuleCode(violation.Rule)}] {violation.Subject}: {violation.Reason}");
        }

        foreach (GateViolationOmission omission in omitted)
        {
            lines.Add(string.Create(CultureInfo.InvariantCulture, $"  ve {omission.Count} tane daha [{RuleCode(omission.Rule)}] {omission.Reason}"));
        }

        return lines;
    }

    private static string RuleCode(GateRule? rule) => rule is null ? "-" : rule.Value.ToCode();

    // Violations kararli sirada (kural, konu, gerekce); her (kural, gerekce) grubunun ilk MaxViolationsShown ihlali gosterilir.
    private (GateViolation[] Shown, GateViolationOmission[] Omitted) Limit()
    {
        Dictionary<(int Rule, string Reason), int> counts = [];
        List<GateViolation> shown = [];
        foreach (GateViolation violation in Violations)
        {
            (int, string) key = (RuleNumber(violation.Rule), violation.Reason);
            int seen = counts.GetValueOrDefault(key) + 1;
            counts[key] = seen;
            if (seen <= MaxViolationsShown)
            {
                shown.Add(violation);
            }
        }

        List<GateViolationOmission> omitted = [];
        foreach (((int rule, string reason), int total) in counts.OrderBy(c => c.Key.Rule).ThenBy(c => c.Key.Reason, StringComparer.Ordinal))
        {
            if (total > MaxViolationsShown)
            {
                omitted.Add(new GateViolationOmission(rule == 0 ? null : (GateRule)rule, reason, total - MaxViolationsShown));
            }
        }

        return ([.. shown], [.. omitted]);
    }

    private static void WriteRule(Utf8JsonWriter writer, GateRule? rule)
    {
        if (rule is null)
        {
            writer.WriteNull("rule");
        }
        else
        {
            writer.WriteString("rule", rule.Value.ToCode());
        }
    }

    private static int RuleNumber(GateRule? rule) => rule is null ? 0 : (int)rule.Value;

    private static int CompareRows(GateReportRow a, GateReportRow b)
    {
        int c = ((int)a.Kind).CompareTo((int)b.Kind);
        if (c != 0)
        {
            return c;
        }

        c = string.CompareOrdinal(a.Id, b.Id);
        if (c != 0)
        {
            return c;
        }

        c = ((int)a.Decision).CompareTo((int)b.Decision);
        if (c != 0)
        {
            return c;
        }

        c = RuleNumber(a.Rule).CompareTo(RuleNumber(b.Rule));
        if (c != 0)
        {
            return c;
        }

        c = string.CompareOrdinal(a.Reason, b.Reason);
        return c != 0 ? c : a.Count.CompareTo(b.Count);
    }

    private static int CompareViolations(GateViolation a, GateViolation b)
    {
        int c = RuleNumber(a.Rule).CompareTo(RuleNumber(b.Rule));
        if (c != 0)
        {
            return c;
        }

        c = string.CompareOrdinal(a.Subject, b.Subject);
        return c != 0 ? c : string.CompareOrdinal(a.Reason, b.Reason);
    }
}
