using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Modelden uretilen ilk goc SQL'i (veritabani ve Docker gerektirmez): enum etiket sirasi, xmin'in sutun olmamasi,
/// varsayilan degerlerin yazilmasi, kimlik ve uretilen sutunlar, tekil dizinler.
/// </summary>
public partial class ModelSqlTests
{
    private static string Sql => string.Join('\n', GeneratedSql.All);

    private static string CreateTable(string table) =>
        GeneratedSql.All.Single(s => s.StartsWith($"CREATE TABLE icerik.{table} (", StringComparison.Ordinal));

    [Fact]
    public void License_status_enum_is_created_in_the_documented_label_order()
    {
        Assert.Contains(
            "CREATE TYPE icerik.license_status AS ENUM ('serbest', 'bekliyor', 'ic_kullanim', 'kapali');",
            Sql,
            StringComparison.Ordinal);
    }

    [Fact]
    public void All_eleven_enum_types_are_created_in_enums_json_label_order()
    {
        Dictionary<string, string[]> json = EnumsJson.Load();
        foreach ((string name, string[] labels) in json.Select(e => (e.Key, e.Value)))
        {
            string expected = $"CREATE TYPE icerik.{name} AS ENUM ({string.Join(", ", labels.Select(l => $"'{l}'"))});";
            Assert.Contains(expected, Sql, StringComparison.Ordinal);
        }

        Assert.Equal(11, TypeStatement().Matches(Sql).Count);
    }

    [GeneratedRegex(@"CREATE TYPE icerik\.[a-z_]+ AS ENUM", RegexOptions.CultureInvariant)]
    private static partial Regex TypeStatement();

    [Fact]
    public void Xmin_is_never_created_as_a_column()
    {
        Assert.Equal(19 + 7, GeneratedSql.All.Count(s => s.StartsWith("CREATE TABLE ", StringComparison.Ordinal)));
        Assert.DoesNotMatch(XminWord(), Sql);
    }

    [GeneratedRegex(@"\bxmin\b", RegexOptions.CultureInvariant)]
    private static partial Regex XminWord();

    [Fact]
    public void Ddl_defaults_are_written_into_the_migration()
    {
        string source = CreateTable("source");
        Assert.Contains("license_status icerik.license_status NOT NULL DEFAULT 'bekliyor'::icerik.license_status", source, StringComparison.Ordinal);
        Assert.Contains("kisitlar jsonb NOT NULL DEFAULT '{}'", source, StringComparison.Ordinal);
        Assert.Contains("embed_ok boolean NOT NULL DEFAULT FALSE", source, StringComparison.Ordinal);
        Assert.Contains("created_at timestamp with time zone NOT NULL DEFAULT (now())", source, StringComparison.Ordinal);

        string unit = CreateTable("unit");
        Assert.Contains("role text NOT NULL DEFAULT 'govde'", unit, StringComparison.Ordinal);
        Assert.Contains("rev integer NOT NULL DEFAULT 1", unit, StringComparison.Ordinal);
        Assert.Contains("marks jsonb NOT NULL DEFAULT '[]'", unit, StringComparison.Ordinal);
        Assert.Contains("metin_durumu icerik.metin_durumu NOT NULL DEFAULT 'taslak'::icerik.metin_durumu", unit, StringComparison.Ordinal);
        Assert.Contains("status icerik.unit_status NOT NULL DEFAULT 'etkin'::icerik.unit_status", unit, StringComparison.Ordinal);

        Assert.Contains("id uuid NOT NULL DEFAULT (uuidv7())", CreateTable("xref"), StringComparison.Ordinal);
        Assert.Contains("id uuid NOT NULL DEFAULT (uuidv7())", CreateTable("quran_word_fix"), StringComparison.Ordinal);
        Assert.Contains("durum icerik.surum_durumu NOT NULL DEFAULT 'hazirlaniyor'::icerik.surum_durumu", CreateTable("release"), StringComparison.Ordinal);
        Assert.Contains("durum icerik.inceleme_durumu NOT NULL DEFAULT 'acik'::icerik.inceleme_durumu", CreateTable("review"), StringComparison.Ordinal);
    }

    [Fact]
    public void Identity_generated_search_and_range_columns_follow_the_ddl()
    {
        foreach (string table in new[] { "unit", "review", "page_map", "release" })
        {
            Assert.Matches(@"\n    id (bigint|integer) GENERATED ALWAYS AS IDENTITY,", CreateTable(table));
        }

        string unit = CreateTable("unit");
        Assert.Contains("tsv_tr tsvector GENERATED ALWAYS AS (to_tsvector('turkish', coalesce(tr_narrow, ''))) STORED", unit, StringComparison.Ordinal);
        Assert.Contains("tsv_ar tsvector GENERATED ALWAYS AS (to_tsvector('arabic', coalesce(ar_norm, ''))) STORED", unit, StringComparison.Ordinal);
        Assert.Contains("ayah_range int4range,", unit, StringComparison.Ordinal);
        Assert.Contains("sentences int4range[],", unit, StringComparison.Ordinal);
        Assert.Contains("src_span int4range,", CreateTable("xref"), StringComparison.Ordinal);
        Assert.Contains("anchor text COLLATE \"C\" NOT NULL", unit, StringComparison.Ordinal);
        Assert.Contains("parent_path text COLLATE \"C\",", unit, StringComparison.Ordinal);
        Assert.Contains("slug text COLLATE \"C\" NOT NULL", CreateTable("source"), StringComparison.Ordinal);
    }

    [Fact]
    public void Indexes_use_documented_names_methods_and_filters()
    {
        Assert.Contains(
            "CREATE UNIQUE INDEX page_map_source_id_volume_page_line_key ON icerik.page_map (source_id, volume, page, line) NULLS NOT DISTINCT;",
            Sql,
            StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX unit_ayah ON icerik.unit USING gist (ayah_range);", Sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX unit_tsv_tr ON icerik.unit USING gin (tsv_tr);", Sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX unit_tsv_ar ON icerik.unit USING gin (tsv_ar);", Sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX xref_queue ON icerik.xref (type, confidence DESC) WHERE status = 'aday';", Sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX review_queue ON icerik.review (hedef_tablo, created_at) WHERE durum = 'acik';", Sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX review_xref ON icerik.review (xref_id) WHERE xref_id IS NOT NULL;", Sql, StringComparison.Ordinal);
    }

    [Fact]
    public void Content_constraints_carry_postgresql_default_names()
    {
        Assert.Contains("CONSTRAINT unit_pkey PRIMARY KEY (id)", CreateTable("unit"), StringComparison.Ordinal);
        Assert.Contains("CONSTRAINT unit_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source (slug)", CreateTable("unit"), StringComparison.Ordinal);
        Assert.Contains("CONSTRAINT unit_run_id_fkey FOREIGN KEY (run_id) REFERENCES icerik.pipeline_run (run_id)", CreateTable("unit"), StringComparison.Ordinal);
        Assert.Contains("CONSTRAINT review_xref_id_fkey FOREIGN KEY (xref_id) REFERENCES icerik.xref (id)", CreateTable("review"), StringComparison.Ordinal);
        Assert.Contains("CONSTRAINT review_yz_kaydi_check CHECK (", CreateTable("review"), StringComparison.Ordinal);

        // icerik tablolarinda pk_/fk_/ix_ yok; kimlik tablolarinda EF adlari kalir.
        string content = string.Join('\n', GeneratedSql.All.Where(s => !s.Contains("kimlik.", StringComparison.Ordinal)));
        Assert.DoesNotMatch(PrefixedName(), content);

        // xref_natural_key EF ile ifade edilmez; A07.4'te goce ham SQL olarak eklenir.
        Assert.DoesNotContain("xref_natural_key", Sql, StringComparison.Ordinal);
    }

    [GeneratedRegex(@"(CONSTRAINT|INDEX) (pk_|fk_|ix_)", RegexOptions.CultureInvariant)]
    private static partial Regex PrefixedName();
}
