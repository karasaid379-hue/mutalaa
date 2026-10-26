using System.Globalization;
using System.Reflection;
using System.Runtime.CompilerServices;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Domain varliklari Editoryal veritabani DDL'ine (tek dogruluk kaynagi) birebir uyar:
/// her tabloya bir sinif, her sutuna (uretilen sutunlar haric) ayni adli PascalCase ozellik, turler ve bos olabilirlik,
/// NOT NULL ve varsayilansiz sutunlarda required, baslangic degerleri veritabani varsayilaniyla ayni (A07 plani madde 7).
/// Docker gerektirmez.
/// </summary>
public class EntityDocumentTests
{
    /// <summary>v1.x tablolari; v1 semasinda (19 tablo) yer almaz.</summary>
    private static readonly string[] DeferredTables = ["xref_vote", "embedding"];

    private static readonly string[] EntityNamespaces =
    [
        "Mutalaa.Domain.Content",
        "Mutalaa.Domain.Links",
        "Mutalaa.Domain.Reviews",
        "Mutalaa.Domain.Releases",
    ];

    /// <summary>PostgreSQL enum turu -> C# enum ve etiket islevi.</summary>
    private static readonly Dictionary<string, (Type Type, Func<object, string> Label)> Enums = new(StringComparer.Ordinal)
    {
        ["license_status"] = (typeof(LicenseStatus), v => ((LicenseStatus)v).ToLabel()),
        ["derleme_turu"] = (typeof(BuildFlavor), v => ((BuildFlavor)v).ToLabel()),
        ["source_kind"] = (typeof(SourceKind), v => ((SourceKind)v).ToLabel()),
        ["unit_kind"] = (typeof(UnitKind), v => ((UnitKind)v).ToLabel()),
        ["unit_status"] = (typeof(UnitStatus), v => ((UnitStatus)v).ToLabel()),
        ["metin_durumu"] = (typeof(TextStatus), v => ((TextStatus)v).ToLabel()),
        ["xref_type"] = (typeof(XrefType), v => ((XrefType)v).ToLabel()),
        ["xref_status"] = (typeof(XrefStatus), v => ((XrefStatus)v).ToLabel()),
        ["xref_origin"] = (typeof(XrefOrigin), v => ((XrefOrigin)v).ToLabel()),
        ["inceleme_durumu"] = (typeof(ReviewStatus), v => ((ReviewStatus)v).ToLabel()),
        ["surum_durumu"] = (typeof(ReleaseStatus), v => ((ReleaseStatus)v).ToLabel()),
    };

    private static readonly Lazy<IReadOnlyList<DdlTable>> Tables = new(LoadTables);

    public static TheoryData<string> TableNames => new(Tables.Value.Select(t => t.Name));

    [Fact]
    public void Every_v1_table_has_exactly_one_entity_and_vice_versa()
    {
        string[] fromDoc = [.. Tables.Value.Select(t => Pascal(t.Name)).Order(StringComparer.Ordinal)];
        string[] fromDomain = [.. EntityTypes().Select(t => t.Name).Order(StringComparer.Ordinal)];

        Assert.Equal(19, fromDoc.Length);
        Assert.Equal(fromDoc, fromDomain);
    }

    [Fact]
    public void Enum_map_covers_enums_json()
    {
        string[] json = [.. EnumsJson.Load().Keys.Order(StringComparer.Ordinal)];
        string[] mapped = [.. Enums.Keys.Order(StringComparer.Ordinal)];

        Assert.Equal(json, mapped);
    }

    [Theory]
    [MemberData(nameof(TableNames))]
    public void Entity_matches_ddl(string table) => CultureScope.Turkish(() =>
    {
        DdlTable ddl = Tables.Value.Single(t => string.Equals(t.Name, table, StringComparison.Ordinal));
        Type entity = EntityTypes().Single(t => string.Equals(t.Name, Pascal(table), StringComparison.Ordinal));
        Dictionary<string, PropertyInfo> properties = entity
            .GetProperties(BindingFlags.Public | BindingFlags.Instance)
            .ToDictionary(p => p.Name, StringComparer.Ordinal);
        DdlColumn[] columns = [.. ddl.Columns.Where(c => !c.Generated)];
        object instance = Activator.CreateInstance(entity)!;
        NullabilityInfoContext nullability = new();
        List<string> problems = [];

        string[] expectedNames = [.. columns.Select(c => Pascal(c.Name))];
        foreach (string missing in expectedNames.Except(properties.Keys, StringComparer.Ordinal))
        {
            problems.Add($"ozellik yok: {missing}");
        }

        foreach (string extra in properties.Keys.Except(expectedNames, StringComparer.Ordinal))
        {
            problems.Add($"DDL'de sutunu olmayan ozellik: {extra}");
        }

        foreach (DdlColumn column in columns)
        {
            if (!properties.TryGetValue(Pascal(column.Name), out PropertyInfo? property))
            {
                continue;
            }

            string where = $"{table}.{column.Name} ({property.Name})";
            Type clr = ClrType(table, column);
            bool valueType = clr.IsValueType;
            Type expectedType = valueType && !column.NotNull ? typeof(Nullable<>).MakeGenericType(clr) : clr;
            if (property.PropertyType != expectedType)
            {
                problems.Add($"{where}: tur {property.PropertyType} beklenen {expectedType}");
                continue;
            }

            if (property.GetMethod?.IsPublic != true || property.SetMethod?.IsPublic != true)
            {
                problems.Add($"{where}: public get/set degil");
            }

            if (!valueType)
            {
                NullabilityState state = nullability.Create(property).WriteState;
                NullabilityState expectedState = column.NotNull ? NullabilityState.NotNull : NullabilityState.Nullable;
                if (state != expectedState)
                {
                    problems.Add($"{where}: bos olabilirlik {state} beklenen {expectedState}");
                }
            }

            bool expectRequired = column.NotNull && column.Default is null && !column.Identity && (!valueType || clr.IsEnum);
            bool isRequired = property.GetCustomAttribute<RequiredMemberAttribute>() is not null;
            if (isRequired != expectRequired)
            {
                problems.Add($"{where}: required {isRequired} beklenen {expectRequired}");
            }

            if (!isRequired)
            {
                string? initial = CheckInitialValue(column, property, property.GetValue(instance), clr);
                if (initial is not null)
                {
                    problems.Add($"{where}: {initial}");
                }
            }
        }

        if (problems.Count > 0)
        {
            Assert.Fail($"{entity.FullName} <-> {EditorialDoc.RelativePath} '{table}':\n" + string.Join('\n', problems));
        }
    });

    /// <summary>Baslangic degeri veritabani varsayilaniyla ayni mi; degilse aciklama dondurur.</summary>
    private static string? CheckInitialValue(DdlColumn column, PropertyInfo property, object? value, Type clr)
    {
        string? def = column.Default;
        if (def is null || def.EndsWith("()", StringComparison.Ordinal))
        {
            // Varsayilansiz, kimlik ya da now()/uuidv7(): CLR varsayilani kalir (null ya da default(T)).
            object? clrDefault = property.PropertyType.IsValueType ? Activator.CreateInstance(property.PropertyType) : null;
            return Equals(value, clrDefault) ? null : $"baslangic degeri {Show(value)} beklenen CLR varsayilani {Show(clrDefault)} (DEFAULT {def ?? "yok"})";
        }

        if (def.StartsWith('\'') && def.EndsWith('\''))
        {
            string literal = def[1..^1].Replace("''", "'", StringComparison.Ordinal);
            string? actual = clr.IsEnum ? Enums.Values.Single(e => e.Type == clr).Label(value!) : value as string;
            return string.Equals(actual, literal, StringComparison.Ordinal) ? null : $"baslangic degeri {Show(actual)} beklenen DEFAULT {def}";
        }

        if (string.Equals(def, "true", StringComparison.Ordinal) || string.Equals(def, "false", StringComparison.Ordinal))
        {
            bool expected = string.Equals(def, "true", StringComparison.Ordinal);
            return value is bool b && b == expected ? null : $"baslangic degeri {Show(value)} beklenen DEFAULT {def}";
        }

        long number = long.Parse(def, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture);
        return value is not null && Convert.ToInt64(value, CultureInfo.InvariantCulture) == number
            ? null
            : $"baslangic degeri {Show(value)} beklenen DEFAULT {def}";
    }

    private static Type ClrType(string table, DdlColumn column)
    {
        if (string.Equals(column.Name, "anchor", StringComparison.Ordinal) || column.Name.EndsWith("_anchor", StringComparison.Ordinal))
        {
            Assert.Equal("text", column.Type);
            return typeof(AnchorRef);
        }

        if (Enums.TryGetValue(column.Type, out (Type Type, Func<object, string> Label) e))
        {
            return e.Type;
        }

        return column.Type switch
        {
            "text" or "jsonb" => typeof(string),
            "smallint" => typeof(short),
            "integer" => typeof(int),
            "bigint" => typeof(long),
            "real" => typeof(float),
            "boolean" => typeof(bool),
            "uuid" => typeof(Guid),
            "date" => typeof(DateOnly),
            "timestamptz" => typeof(DateTime),
            "int4range" => typeof(AnchorSpan),
            "int4range[]" => typeof(AnchorSpan[]),
            _ when column.Type.StartsWith("char(", StringComparison.Ordinal) => typeof(string),
            _ => throw new InvalidDataException($"{table}.{column.Name}: eslenmemis DDL turu '{column.Type}'"),
        };
    }

    private static IReadOnlyList<DdlTable> LoadTables()
    {
        IReadOnlyList<DdlTable> all = EditorialDoc.ParseTables(EditorialDoc.SqlBlocks(EditorialDoc.Read()));
        foreach (string deferred in DeferredTables)
        {
            Assert.Contains(all, t => string.Equals(t.Name, deferred, StringComparison.Ordinal));
        }

        // Belge DDL'i tek dogruluk kaynagidir (review.yz_kaydi dahil, K-37): sutunlar belgeden oldugu gibi okunur.
        return [.. all.Where(t => !DeferredTables.Contains(t.Name, StringComparer.Ordinal))];
    }

    private static IEnumerable<Type> EntityTypes() =>
        typeof(DomainAssembly).Assembly.GetExportedTypes()
            .Where(t => t.IsClass && !t.IsAbstract && EntityNamespaces.Contains(t.Namespace, StringComparer.Ordinal));

    /// <summary>snake_case -> PascalCase (Invariant; tr-TR altinda 'i' -> 'I').</summary>
    private static string Pascal(string snake) =>
        string.Concat(snake.Split('_').Select(part => char.ToUpperInvariant(part[0]) + part[1..]));

    private static string Show(object? value) => value switch
    {
        null => "null",
        string s => "\"" + s + "\"",
        IFormattable f => f.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? string.Empty,
    };
}
