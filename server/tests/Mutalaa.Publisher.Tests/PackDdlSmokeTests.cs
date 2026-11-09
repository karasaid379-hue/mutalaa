using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Data.Sqlite;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// Paket DDL duman testi (A12.6, K-44; Icerik paketleri 3, Arama 2).
/// packages/content-schema/sql/paketler.json'daki her tur icin bos bir SQLite dosyasinda ddl ve sonra
/// dosyalari sirayla uygulanir; tablo kumesi, user_version, FTS5/trigram ve icerigi bos tablo kurallari denetlenir.
/// DDL dosyalari ve paketler.json cikti klasorunun data\sql\ altina kopyalanir. Docker gerektirmez.
/// </summary>
public class PackDdlSmokeTests
{
    private static readonly string[] Common = ["pack_meta", "pack_source", "attribution"];

    // Beklenen tablo kumesi (FTS5 golge tablolari haric). Gercek DDL ile karsilastirilir.
    private static readonly Dictionary<string, string[]> ExpectedTables = new(StringComparer.Ordinal)
    {
        ["core"] = [.. Common, "unit", "xref_idx", "unit_search", "unit_fts", "unit_tri", "quran_word", "quran_marker", "sure", "page_map"],
        ["metin"] = [.. Common, "unit", "xref_idx", "tr_root_index", "unit_search", "unit_fts", "unit_tri", "page_map"],
        ["risale-kitap"] = [.. Common, "unit"],
        ["risale-dizin"] = [.. Common, "unit_ref", "xref_idx", "tr_root_index", "unit_fts", "unit_tri", "page_map"],
        ["kelime-kok"] = [.. Common, "word_morph", "root", "lemma", "lemma_gloss", "tr_form", "tr_root_index"],
        ["mushaf-a-cuz"] = [.. Common, "page_font", "page_line", "glyph_word"],
        ["mushaf-b"] = [.. Common, "page_image", "ayah_box", "page_map"],
        ["ses-katalog"] = [.. Common, "okuyucu", "kayit", "kayit_sure"],
        ["ses-zaman"] = [.. Common, "ayet_zaman", "kelime_zaman", "ozel_bolut"],
    };

    // Her pack_id tam olarak bir ture eslesir (desenler birbirini dislar).
    private static readonly (string PackId, string Tur)[] PackIdMatches =
    [
        ("core", "core"),
        ("tefsir-elmalili", "metin"),
        ("hadis-tecrid", "metin"),
        ("hadis-kutub-i-sitte", "metin"),
        ("test-kucuk", "metin"),
        ("tefsir-test-ornek", "metin"),
        ("risale-sozler", "risale-kitap"),
        ("risale-dizin", "risale-dizin"),
        ("kelime-kok", "kelime-kok"),
        ("mushaf-a-cuz-01", "mushaf-a-cuz"),
        ("mushaf-a-cuz-09", "mushaf-a-cuz"),
        ("mushaf-a-cuz-10", "mushaf-a-cuz"),
        ("mushaf-a-cuz-30", "mushaf-a-cuz"),
        ("mushaf-b", "mushaf-b"),
        ("ses-katalog", "ses-katalog"),
        ("ses-zaman-alafasy", "ses-zaman"),
    ];

    // Hicbir ture eslesmemesi gerekenler.
    private static readonly string[] PackIdNoMatch =
    [
        "mushaf-a-cuz-00",
        "mushaf-a-cuz-31",
        "mushaf-a-cuz-1",
        "mushaf-a-cuz-100",
        "Core",
        "core-x",
        "tefsir-",
        "test-",
        "Test-kucuk",
        "test_kucuk",
        "hadis_tecrid",
        "ses-zaman",
        "risale-",
    ];

    // Uydurma harf dizisi (gercek metin degil); ortadaki uc harf alt dize olarak aranir.
    private const string SyntheticText = "بتثجحخ";
    private const string SyntheticQuery = "\"ثجح\"";

    public static TheoryData<string> Turler()
    {
        TheoryData<string> data = [];
        foreach (string tur in ExpectedTables.Keys)
        {
            data.Add(tur);
        }

        return data;
    }

    private static string DataPath(string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", name);
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("Dosya cikti klasorune kopyalanmamis: " + path);
        }

        return path;
    }

    private static string ReadData(string name) =>
        new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(DataPath(name)));

    private static JsonElement LoadManifest() => JsonDocument.Parse(ReadData("sql/paketler.json")).RootElement.Clone();

    private static JsonElement TurOf(string tur) => LoadManifest().GetProperty("turler").GetProperty(tur);

    private static string[] Files(JsonElement element) =>
        [.. element.EnumerateArray().Select(e => e.GetString()!)];

    private static void Exec(SqliteConnection conn, string sql)
    {
        using SqliteCommand cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    private static T Scalar<T>(SqliteConnection conn, string sql)
    {
        using SqliteCommand cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        return (T)Convert.ChangeType(cmd.ExecuteScalar()!, typeof(T), System.Globalization.CultureInfo.InvariantCulture);
    }

    private static List<string> Strings(SqliteConnection conn, string sql)
    {
        using SqliteCommand cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        using SqliteDataReader reader = cmd.ExecuteReader();
        List<string> result = [];
        while (reader.Read())
        {
            result.Add(reader.GetString(0));
        }

        return result;
    }

    private static bool IsFtsShadow(string name) =>
        (name.StartsWith("unit_fts_", StringComparison.Ordinal) || name.StartsWith("unit_tri_", StringComparison.Ordinal))
        && (name.EndsWith("_data", StringComparison.Ordinal) || name.EndsWith("_idx", StringComparison.Ordinal)
            || name.EndsWith("_docsize", StringComparison.Ordinal) || name.EndsWith("_config", StringComparison.Ordinal)
            || name.EndsWith("_content", StringComparison.Ordinal));

    private static string[] UserTables(SqliteConnection conn)
    {
        string[] tables = [.. Strings(conn, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
            .Where(n => !IsFtsShadow(n))];
        Array.Sort(tables, StringComparer.Ordinal);
        return tables;
    }

    private static string[] Sorted(IEnumerable<string> values)
    {
        string[] array = [.. values];
        Array.Sort(array, StringComparer.Ordinal);
        return array;
    }

    /// <summary>Gecici SQLite dosyasi olusturur, ddl ve (istenirse) sonra dosyalarini uygular, eylemi calistirir, dosyayi siler.</summary>
    private static void WithPack(string tur, bool applyAfter, Action<SqliteConnection> action)
    {
        JsonElement def = TurOf(tur);
        string dir = Path.Combine(Path.GetTempPath(), "mutalaa-ddl-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        string file = Path.Combine(dir, "pack.sqlite");
        try
        {
            SqliteConnectionStringBuilder builder = new() { DataSource = file, Pooling = false, Mode = SqliteOpenMode.ReadWriteCreate };
            using SqliteConnection conn = new(builder.ConnectionString);
            conn.Open();
            foreach (string ddl in Files(def.GetProperty("ddl")))
            {
                Exec(conn, ReadData("sql/" + ddl));
            }

            action(conn);

            if (applyAfter)
            {
                foreach (string sonra in Files(def.GetProperty("sonra")))
                {
                    Exec(conn, ReadData("sql/" + sonra));
                }
            }
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    // ---- paketler.json ----

    [Fact]
    public void Manifest_has_version_1_and_nine_types()
    {
        JsonElement root = LoadManifest();

        Assert.Equal(1, root.GetProperty("version").GetInt32());
        Assert.Equal(Sorted(ExpectedTables.Keys), Sorted(root.GetProperty("turler").EnumerateObject().Select(p => p.Name)));
    }

    [Fact]
    public void Every_referenced_sql_file_exists_and_every_sql_file_is_referenced()
    {
        JsonElement turler = LoadManifest().GetProperty("turler");
        HashSet<string> referenced = new(StringComparer.Ordinal);
        foreach (JsonProperty tur in turler.EnumerateObject())
        {
            foreach (string f in Files(tur.Value.GetProperty("ddl")).Concat(Files(tur.Value.GetProperty("sonra"))))
            {
                referenced.Add(f);
                Assert.True(File.Exists(DataPath("sql/" + f)), f);
            }
        }

        string sqlDir = Path.GetDirectoryName(DataPath("sql/paketler.json"))!;
        string[] onDisk = Sorted(Directory.GetFiles(sqlDir, "*.sql").Select(p => Path.GetFileName(p)));
        Assert.Equal(Sorted(referenced), onDisk);
    }

    [Fact]
    public void Pack_id_patterns_compile_and_match_exactly_one_type()
    {
        JsonElement turler = LoadManifest().GetProperty("turler");
        Dictionary<string, Regex> patterns = new(StringComparer.Ordinal);
        foreach (JsonProperty tur in turler.EnumerateObject())
        {
            patterns[tur.Name] = new Regex(tur.Value.GetProperty("desen").GetString()!, RegexOptions.CultureInvariant);
        }

        foreach ((string packId, string expected) in PackIdMatches)
        {
            string[] matched = Sorted(patterns.Where(p => p.Value.IsMatch(packId)).Select(p => p.Key));
            Assert.True(matched.Length == 1 && string.Equals(matched[0], expected, StringComparison.Ordinal),
                $"{packId}: beklenen {expected}, eslesen [{string.Join(", ", matched)}]");
        }

        foreach (string packId in PackIdNoMatch)
        {
            string[] matched = [.. patterns.Where(p => p.Value.IsMatch(packId)).Select(p => p.Key)];
            Assert.True(matched.Length == 0, $"{packId} hicbir ture eslesmemeli, eslesen [{string.Join(", ", matched)}]");
        }
    }

    [Fact]
    public void Risale_dizin_does_not_match_the_risale_kitap_pattern()
    {
        JsonElement turler = LoadManifest().GetProperty("turler");
        Regex kitap = new(turler.GetProperty("risale-kitap").GetProperty("desen").GetString()!, RegexOptions.CultureInvariant);
        Regex dizin = new(turler.GetProperty("risale-dizin").GetProperty("desen").GetString()!, RegexOptions.CultureInvariant);

        Assert.DoesNotMatch(kitap, "risale-dizin");
        Assert.Matches(dizin, "risale-dizin");
        Assert.Matches(kitap, "risale-sozler");
        Assert.DoesNotMatch(dizin, "risale-sozler");
    }

    // ---- DDL duman testleri ----

    [Fact]
    public void Sqlite_supports_fts5_and_trigram()
    {
        using SqliteConnection conn = new("Data Source=:memory:;Pooling=False");
        conn.Open();

        string version = Scalar<string>(conn, "SELECT sqlite_version()");
        TestContext.Current.SendDiagnosticMessage("sqlite_version() = " + version);
        Assert.True(Version.Parse(version) >= new Version(3, 34, 0), "trigram icin SQLite 3.34 ve ustu gerekir: " + version);
        Assert.Contains("ENABLE_FTS5", Strings(conn, "PRAGMA compile_options"));
    }

    [Theory]
    [MemberData(nameof(Turler))]
    public void Ddl_applies_and_creates_the_expected_table_set(string tur)
    {
        WithPack(tur, applyAfter: true, conn =>
        {
            Assert.Equal(Sorted(ExpectedTables[tur]), UserTables(conn));
            Assert.Equal(1, Scalar<int>(conn, "PRAGMA user_version"));
            Assert.DoesNotContain("tr_stem_lex", UserTables(conn));
        });
    }

    [Theory]
    [MemberData(nameof(Turler))]
    public void Trigram_table_exists_only_where_expected_and_substring_search_works(string tur)
    {
        bool hasTri = ExpectedTables[tur].Contains("unit_tri");

        WithPack(tur, applyAfter: false, conn =>
        {
            List<string> tables = Strings(conn, "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'unit_tri'");
            Assert.Equal(hasTri, tables.Count == 1);
            if (!hasTri)
            {
                return;
            }

            if (ExpectedTables[tur].Contains("unit_search"))
            {
                // Icerikli: unit_search satiri, sonra dosyalari 'rebuild' ile fts/trigram dizinlerini doldurur.
                Exec(conn, $"INSERT INTO unit_search(rowid, tr_wide, tr_stem, ar_norm) VALUES (1, 'a', 'a', '{SyntheticText}')");
                foreach (string sonra in Files(TurOf(tur).GetProperty("sonra")))
                {
                    Exec(conn, ReadData("sql/" + sonra));
                }
            }
            else
            {
                // Iceriksiz (risale-dizin): satirlar dogrudan yazilir.
                Exec(conn, $"INSERT INTO unit_tri(rowid, ar_norm) VALUES (1, '{SyntheticText}')");
                foreach (string sonra in Files(TurOf(tur).GetProperty("sonra")))
                {
                    Exec(conn, ReadData("sql/" + sonra));
                }
            }

            using SqliteCommand cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT rowid FROM unit_tri WHERE unit_tri MATCH $q";
            cmd.Parameters.AddWithValue("$q", SyntheticQuery);
            using SqliteDataReader reader = cmd.ExecuteReader();
            List<long> rows = [];
            while (reader.Read())
            {
                rows.Add(reader.GetInt64(0));
            }

            Assert.Equal([1L], rows);
        });
    }

    [Theory]
    [InlineData("core")]
    [InlineData("metin")]
    [InlineData("risale-kitap")]
    public void Unit_approved_is_integer_not_null_default_1(string tur)
    {
        WithPack(tur, applyAfter: false, conn =>
        {
            using SqliteCommand cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT type, \"notnull\", dflt_value FROM pragma_table_info('unit') WHERE name = 'approved'";
            using SqliteDataReader reader = cmd.ExecuteReader();

            Assert.True(reader.Read());
            Assert.Equal("INTEGER", reader.GetString(0));
            Assert.Equal(1, reader.GetInt32(1));
            Assert.Equal("1", reader.GetString(2));
        });
    }

    [Fact]
    public void Rebuild_fails_on_contentless_tables_of_risale_dizin()
    {
        WithPack("risale-dizin", applyAfter: false, conn =>
        {
            Assert.Throws<SqliteException>(() => Exec(conn, "INSERT INTO unit_fts(unit_fts) VALUES('rebuild')"));
            Assert.Throws<SqliteException>(() => Exec(conn, "INSERT INTO unit_tri(unit_tri) VALUES('rebuild')"));
        });
    }

    [Fact]
    public void Rebuild_works_on_content_tables_of_core()
    {
        WithPack("core", applyAfter: false, conn =>
        {
            Exec(conn, "INSERT INTO unit_fts(unit_fts) VALUES('rebuild')");
            Exec(conn, "INSERT INTO unit_tri(unit_tri) VALUES('rebuild')");
        });
    }

    [Theory]
    [InlineData("core")]
    [InlineData("metin")]
    [InlineData("risale-kitap")]
    public void Unit_status_default_is_a_value_of_the_unit_status_enum(string tur)
    {
        using JsonDocument enums = JsonDocument.Parse(ReadData("enums.json"));
        string[] unitStatus = [.. enums.RootElement.GetProperty("enums").GetProperty("unit_status").EnumerateArray().Select(e => e.GetString()!)];

        WithPack(tur, applyAfter: false, conn =>
        {
            using SqliteCommand cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT dflt_value FROM pragma_table_info('unit') WHERE name = 'status'";
            string dflt = (string)cmd.ExecuteScalar()!;

            Assert.Equal("'etkin'", dflt);
            Assert.Contains("etkin", unitStatus);
        });
    }
}
