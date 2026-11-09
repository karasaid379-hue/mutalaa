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
/// Kapi raporu (release.kapi_raporu). Satirlar ve ihlaller kararli sirada tutulur; ToJson ayni girdiyle ayni baytlari verir.
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

    public IReadOnlyList<GateViolation> Violations { get; }

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
            foreach (GateViolation violation in Violations)
            {
                writer.WriteStartObject();
                WriteRule(writer, violation.Rule);
                writer.WriteString("subject", violation.Subject);
                writer.WriteString("reason", violation.Reason);
                writer.WriteEndObject();
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
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
