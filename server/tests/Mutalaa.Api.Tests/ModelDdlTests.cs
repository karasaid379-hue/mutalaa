using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Modelden uretilen CREATE TABLE ifadeleri Editoryal veritabani DDL'iyle (tek dogruluk kaynagi) sutun sutun ve kisit kisit karsilastirilir.
/// Veritabani gerektirmez. Bilinen, bilincli farklar: sutun sirasi (uretilen tsv sutunlari sonda), UNIQUE kisiti yerine tekil dizin,
/// xref_natural_key (A07.4'te ham SQL), xref_vote ve embedding (v1.x).
/// </summary>
public partial class ModelDdlTests
{
    private static readonly string[] DeferredTables = ["xref_vote", "embedding"];

    private static IReadOnlyList<DdlTable> DocTables() =>
        [.. EditorialDoc.ParseTables(EditorialDoc.SqlBlocks(EditorialDoc.Read())).Where(t => !DeferredTables.Contains(t.Name))];

    /// <summary>EF ciktisini belgedeki yazima yaklastirir: sema oneki, enum donusumleri, zaman dilimi ve varsayilan bicimi.</summary>
    internal static string Normalize(string statement)
    {
        string text = statement.Replace("icerik.", string.Empty, StringComparison.Ordinal);
        text = EnumCast().Replace(text, string.Empty);
        text = text.Replace("timestamp with time zone", "timestamptz", StringComparison.Ordinal);
        text = text.Replace("DEFAULT (now())", "DEFAULT now()", StringComparison.Ordinal);
        text = text.Replace("DEFAULT (uuidv7())", "DEFAULT uuidv7()", StringComparison.Ordinal);
        text = text.Replace("DEFAULT FALSE", "DEFAULT false", StringComparison.Ordinal);
        text = text.Replace("DEFAULT TRUE", "DEFAULT true", StringComparison.Ordinal);

        // Kimlik sutunu birincil anahtardir; PostgreSQL NOT NULL yazimini gerektirmez, belgede PRIMARY KEY bunu ima eder.
        text = text.Replace("GENERATED ALWAYS AS IDENTITY,", "GENERATED ALWAYS AS IDENTITY NOT NULL,", StringComparison.Ordinal);
        return text;
    }

    [GeneratedRegex("::[a-z_]+", RegexOptions.CultureInvariant)]
    private static partial Regex EnumCast();

    private static IReadOnlyList<DdlTable> GeneratedTables()
    {
        string sql = string.Join(
            "\n;\n",
            GeneratedSql.All
                .Where(s => s.StartsWith("CREATE TABLE icerik.", StringComparison.Ordinal))
                .Select(Normalize));
        return EditorialDoc.ParseTables(sql);
    }

    [Fact]
    public void Generated_columns_match_the_ddl_column_by_column()
    {
        Dictionary<string, DdlTable> generated = GeneratedTables().ToDictionary(t => t.Name, StringComparer.Ordinal);
        List<string> differences = [];

        foreach (DdlTable doc in DocTables())
        {
            // K-37: belge DDL'i yz_kaydi sutununu tasir; atlama yok.
            if (!generated.TryGetValue(doc.Name, out DdlTable? actual))
            {
                differences.Add($"{doc.Name}: modelde tablo yok");
                continue;
            }

            Dictionary<string, DdlColumn> docColumns = doc.Columns.ToDictionary(c => c.Name, StringComparer.Ordinal);
            Dictionary<string, DdlColumn> modelColumns = actual.Columns.ToDictionary(c => c.Name, StringComparer.Ordinal);

            foreach (string missing in docColumns.Keys.Except(modelColumns.Keys, StringComparer.Ordinal))
            {
                differences.Add($"{doc.Name}.{missing}: modelde yok");
            }

            foreach (string extra in modelColumns.Keys.Except(docColumns.Keys, StringComparer.Ordinal))
            {
                differences.Add($"{doc.Name}.{extra}: belgede yok");
            }

            foreach (string name in docColumns.Keys.Intersect(modelColumns.Keys, StringComparer.Ordinal))
            {
                if (docColumns[name] != modelColumns[name])
                {
                    differences.Add($"{doc.Name}.{name}: belge {docColumns[name]} <> model {modelColumns[name]}");
                }
            }
        }

        Assert.Empty(differences);
        Assert.Equal(DocTables().Count, generated.Count);
    }

    [Fact]
    public void Every_ddl_check_expression_appears_verbatim_in_the_model()
    {
        // Belge metninde bosluklar silinir; model CHECK ifadesi CHECK( ... ) icinde ayni bicimde bulunmali.
        string ddl = WhitespaceFree(EditorialDoc.StripComments(EditorialDoc.SqlBlocks(EditorialDoc.Read())));
        int count = 0;

        ModelFactory.ForEachModel(model =>
        {
            foreach (IEntityType entityType in model.GetEntityTypes().Where(e => string.Equals(e.GetSchema() ?? model.GetDefaultSchema(), "icerik", StringComparison.Ordinal)))
            {
                foreach (ICheckConstraint check in entityType.GetCheckConstraints())
                {
                    string needle = "CHECK(" + WhitespaceFree(check.Sql) + ")";
                    Assert.True(
                        ddl.Contains(needle, StringComparison.Ordinal),
                        $"{entityType.GetTableName()}.{check.Name}: ifade belge DDL'inde yok");
                    count++;
                }
            }
        });

        // Sabit sayi yok: belgedeki CHECK sayisi x 2 model (onbellekli ve yeni kurulmus).
        Assert.True(DocConstraints().Checks.Count > 0);
        Assert.Equal(DocConstraints().Checks.Count * 2, count);
    }

    /// <summary>Belge DDL'indeki (v1 tablolari) CHECK ve yabanci anahtarlar; sayilar belgeden turer.</summary>
    private static DdlConstraints DocConstraints()
    {
        DdlConstraints all = EditorialDoc.ParseConstraints(EditorialDoc.SqlBlocks(EditorialDoc.Read()));
        return new DdlConstraints(
            [.. all.Checks.Where(c => !DeferredTables.Contains(c.Table))],
            [.. all.References.Where(r => !DeferredTables.Contains(r.Table))]);
    }

    [Fact]
    public void The_document_checks_and_the_model_checks_are_the_same_set_in_both_directions()
    {
        DdlConstraints doc = DocConstraints();
        string[] expected = [.. doc.Checks.Select(c => c.Table + ": " + WhitespaceFree(c.Expression)).Order(StringComparer.Ordinal)];

        ModelFactory.ForEachModel(model =>
        {
            string[] actual =
            [
                .. IcerikEntityTypes(model)
                    .SelectMany(e => e.GetCheckConstraints().Select(c => e.GetTableName() + ": " + WhitespaceFree(c.Sql)))
                    .Order(StringComparer.Ordinal),
            ];

            Assert.Equal(expected, actual);
        });

        // Belgede acik adi olan her CHECK, modelde ayni tabloda ayni adla bulunur.
        foreach (DdlCheck named in doc.Checks.Where(c => c.Name is not null))
        {
            ModelFactory.ForEachModel(model =>
                Assert.Contains(
                    IcerikEntityTypes(model).Where(e => string.Equals(e.GetTableName(), named.Table, StringComparison.Ordinal)).SelectMany(e => e.GetCheckConstraints()),
                    c => string.Equals(c.Name, named.Name, StringComparison.Ordinal)));
        }
    }

    [Fact]
    public void The_document_references_and_the_model_foreign_keys_are_the_same_set_in_both_directions()
    {
        DdlConstraints doc = DocConstraints();
        string[] expected = [.. doc.References.Select(Describe).Order(StringComparer.Ordinal)];
        Assert.NotEmpty(expected);

        ModelFactory.ForEachModel(model =>
        {
            string[] actual =
            [
                .. IcerikEntityTypes(model)
                    .SelectMany(e => e.GetForeignKeys())
                    .Select(fk => Describe(new DdlReference(
                        fk.DeclaringEntityType.GetTableName()!,
                        ColumnOf(fk.Properties.Single(), fk.DeclaringEntityType),
                        fk.PrincipalEntityType.GetTableName()!,
                        ColumnOf(fk.PrincipalKey.Properties.Single(), fk.PrincipalEntityType))))
                    .Order(StringComparer.Ordinal),
            ];

            Assert.Equal(expected, actual);
        });
    }

    private static string Describe(DdlReference r) => $"{r.Table}.{r.Column} -> {r.ReferencedTable}.{r.ReferencedColumn}";

    private static string ColumnOf(IProperty property, IEntityType owner) =>
        property.GetColumnName(StoreObjectIdentifier.Table(owner.GetTableName()!, owner.GetSchema()))!;

    private static IEnumerable<IEntityType> IcerikEntityTypes(IModel model) =>
        model.GetEntityTypes().Where(e => string.Equals(e.GetSchema() ?? model.GetDefaultSchema(), "icerik", StringComparison.Ordinal));

    private static string WhitespaceFree(string text) => Whitespace().Replace(text, string.Empty);

    [GeneratedRegex(@"\s+", RegexOptions.CultureInvariant)]
    private static partial Regex Whitespace();
}
