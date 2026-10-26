using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Npgsql.EntityFrameworkCore.PostgreSQL.Infrastructure;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// 11 PostgreSQL enum turunun tek kaydi (Editoryal veritabani 2). Cevirmen ornekleri statiktir: EF cevirmenleri ReferenceEquals ile
/// karsilastirir, her secenek kurulumunda yeni ornek ManyServiceProvidersCreatedWarning'i istisnaya cevirir.
/// Npgsql MapEnum etiketleri alfabetik dizdigi icin (efcore.pg #3667) etiket sirasi ayrica HasPostgresEnum ile, sayisal sirada verilir.
/// </summary>
public static class PostgresEnums
{
    public const string Schema = "icerik";

    private static readonly LabelNameTranslator<LicenseStatus> LicenseStatusTranslator = new(LicenseStatusLabels.ToLabel);
    private static readonly LabelNameTranslator<BuildFlavor> BuildFlavorTranslator = new(BuildFlavorLabels.ToLabel);
    private static readonly LabelNameTranslator<SourceKind> SourceKindTranslator = new(SourceKindLabels.ToLabel);
    private static readonly LabelNameTranslator<UnitKind> UnitKindTranslator = new(UnitKindLabels.ToLabel);
    private static readonly LabelNameTranslator<UnitStatus> UnitStatusTranslator = new(UnitStatusLabels.ToLabel);
    private static readonly LabelNameTranslator<TextStatus> TextStatusTranslator = new(TextStatusLabels.ToLabel);
    private static readonly LabelNameTranslator<XrefType> XrefTypeTranslator = new(XrefTypeLabels.ToLabel);
    private static readonly LabelNameTranslator<XrefStatus> XrefStatusTranslator = new(XrefStatusLabels.ToLabel);
    private static readonly LabelNameTranslator<XrefOrigin> XrefOriginTranslator = new(XrefOriginLabels.ToLabel);
    private static readonly LabelNameTranslator<ReviewStatus> ReviewStatusTranslator = new(ReviewStatusLabels.ToLabel);
    private static readonly LabelNameTranslator<ReleaseStatus> ReleaseStatusTranslator = new(ReleaseStatusLabels.ToLabel);

    /// <summary>PostgreSQL tur adi ve sayisal sirada etiketler.</summary>
    public static IReadOnlyList<KeyValuePair<string, string[]>> Definitions { get; } =
    [
        Define<LicenseStatus>("license_status", LicenseStatusLabels.ToLabel),
        Define<BuildFlavor>("derleme_turu", BuildFlavorLabels.ToLabel),
        Define<SourceKind>("source_kind", SourceKindLabels.ToLabel),
        Define<UnitKind>("unit_kind", UnitKindLabels.ToLabel),
        Define<UnitStatus>("unit_status", UnitStatusLabels.ToLabel),
        Define<TextStatus>("metin_durumu", TextStatusLabels.ToLabel),
        Define<XrefType>("xref_type", XrefTypeLabels.ToLabel),
        Define<XrefStatus>("xref_status", XrefStatusLabels.ToLabel),
        Define<XrefOrigin>("xref_origin", XrefOriginLabels.ToLabel),
        Define<ReviewStatus>("inceleme_durumu", ReviewStatusLabels.ToLabel),
        Define<ReleaseStatus>("surum_durumu", ReleaseStatusLabels.ToLabel),
    ];

    /// <summary>Modele 11 enum turunu etiket sirasiyla yazar.</summary>
    public static void AddToModel(ModelBuilder modelBuilder)
    {
        foreach (KeyValuePair<string, string[]> definition in Definitions)
        {
            modelBuilder.HasPostgresEnum(Schema, definition.Key, definition.Value);
        }
    }

    /// <summary>Npgsql secenek kurucusuna 11 CLR enum eslemesini ekler.</summary>
    public static void MapAll(NpgsqlDbContextOptionsBuilder options)
    {
        ArgumentNullException.ThrowIfNull(options);
        options.MapEnum<LicenseStatus>("license_status", Schema, LicenseStatusTranslator);
        options.MapEnum<BuildFlavor>("derleme_turu", Schema, BuildFlavorTranslator);
        options.MapEnum<SourceKind>("source_kind", Schema, SourceKindTranslator);
        options.MapEnum<UnitKind>("unit_kind", Schema, UnitKindTranslator);
        options.MapEnum<UnitStatus>("unit_status", Schema, UnitStatusTranslator);
        options.MapEnum<TextStatus>("metin_durumu", Schema, TextStatusTranslator);
        options.MapEnum<XrefType>("xref_type", Schema, XrefTypeTranslator);
        options.MapEnum<XrefStatus>("xref_status", Schema, XrefStatusTranslator);
        options.MapEnum<XrefOrigin>("xref_origin", Schema, XrefOriginTranslator);
        options.MapEnum<ReviewStatus>("inceleme_durumu", Schema, ReviewStatusTranslator);
        options.MapEnum<ReleaseStatus>("surum_durumu", Schema, ReleaseStatusTranslator);
    }

    private static KeyValuePair<string, string[]> Define<T>(string name, Func<T, string> toLabel)
        where T : struct, Enum =>
        new(name, [.. Enum.GetValues<T>().OrderBy(v => Convert.ToInt32(v, System.Globalization.CultureInfo.InvariantCulture)).Select(toLabel)]);
}
