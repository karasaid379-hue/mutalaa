using System.Globalization;
using System.Security.Cryptography;
using Microsoft.Data.Sqlite;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// SqlitePackWriter (Backend API 10.4): sentetik "Deneme paragrafi" ve "Isik" metni, gercek SQLite dosyasi. Docker gerektirmez.
/// Hicbir test gercek Kur'an, meal, tefsir, hadis ya da Risale metni kullanmaz.
/// </summary>
public class SqlitePackWriterTests
{
    private static readonly DateTimeOffset Clock1 = new(2026, 11, 9, 10, 0, 0, TimeSpan.Zero);
    private static readonly DateTimeOffset Clock2 = new(2026, 12, 1, 8, 30, 15, TimeSpan.Zero);

    private static SqlitePackWriter Writer(DateTimeOffset? now = null) => new(PackTestData.Definitions(), new FixedClock(now ?? Clock1));

    private static SqliteConnection OpenReadOnly(string path)
    {
        SqliteConnectionStringBuilder builder = new() { DataSource = path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        return connection;
    }

    private static List<string> Strings(SqliteConnection connection, string sql, params (string Name, object Value)[] parameters)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        foreach ((string name, object value) in parameters)
        {
            command.Parameters.AddWithValue(name, value);
        }

        using SqliteDataReader reader = command.ExecuteReader();
        List<string> values = [];
        while (reader.Read())
        {
            values.Add(Convert.ToString(reader.GetValue(0), CultureInfo.InvariantCulture)!);
        }

        return values;
    }

    private static Dictionary<string, string> Meta(SqliteConnection connection)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT key, value FROM pack_meta";
        using SqliteDataReader reader = command.ExecuteReader();
        Dictionary<string, string> meta = new(StringComparer.Ordinal);
        while (reader.Read())
        {
            meta[reader.GetString(0)] = reader.GetString(1);
        }

        return meta;
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Writes_a_pack_with_the_expected_file_meta_and_pragmas(bool turkish)
    {
        async Task Body()
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            using PackTestData.TempDir temp = new();
            PackContent content = PackTestData.SmallContent();

            PackFile file = await Writer().WriteAsync(content, PackTestData.Request(temp.Path), ct);

            string expectedPath = Path.Combine(temp.Path, "dev", "2026.11.0", "test-kucuk-2026.11.0.db");
            Assert.Equal(expectedPath, file.Path);
            Assert.True(File.Exists(file.Path));
            Assert.False(File.Exists(file.Path + ".tmp"));
            Assert.Equal(new FileInfo(file.Path).Length, file.SizeBytes);
            Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(await File.ReadAllBytesAsync(file.Path, ct))), file.Sha256);
            Assert.Equal(PackDigest.Compute(content), file.ContentDigest);
            Assert.True(file.SelfCheck.Passed, file.SelfCheck.ToJson());
            Assert.Equal(9, file.SelfCheck.Items.Count);

            using SqliteConnection connection = OpenReadOnly(file.Path);
            Assert.Equal(["1"], Strings(connection, "PRAGMA user_version"));
            Assert.Equal(["4096"], Strings(connection, "PRAGMA page_size"));
            Assert.Equal(["delete"], Strings(connection, "PRAGMA journal_mode"));
            Assert.Equal(["ok"], Strings(connection, "PRAGMA integrity_check"));

            Dictionary<string, string> meta = Meta(connection);
            Assert.Equal(
                [
                    ("anchors_version", "1"),
                    ("built_at", "2026-11-09T10:00:00Z"),
                    ("content_digest", file.ContentDigest),
                    ("data_version", "2026.11.09-abcdef0"),
                    ("flavor", "dev"),
                    ("normalizer_version", "1.0"),
                    ("pack_id", "test-kucuk"),
                    ("schema_version", "1"),
                    ("unit_count", "3"),
                    ("version", "2026.11.0"),
                ],
                meta.OrderBy(p => p.Key, StringComparer.Ordinal).Select(p => (p.Key, p.Value)));
        }

        if (turkish)
        {
            await AsyncCultureScope.TurkishAsync(Body);
        }
        else
        {
            await Body();
        }
    }

    [Fact]
    public async Task The_synthetic_light_word_is_found_through_the_fts_table()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();

        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);

        using SqliteConnection connection = OpenReadOnly(file.Path);
        List<string> anchors = Strings(
            connection,
            "SELECT u.anchor FROM unit_fts f JOIN unit u ON u.rowid = f.rowid WHERE unit_fts MATCH $q",
            ("$q", "tr_wide : \"isik\""));
        Assert.Equal(["k:test-kucuk:bolum-1:p3"], anchors);
        Assert.Equal(["Deneme paragrafi 3 Işık sözcüğü"], Strings(connection, "SELECT text FROM unit WHERE anchor = 'k:test-kucuk:bolum-1:p3'"));
        SelfCheckItem fts = file.SelfCheck.Items.Single(i => i.Name == "fts_query");
        Assert.True(fts.Passed);
        Assert.DoesNotContain("atlandi", fts.Detail, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Unit_rowids_follow_the_anchor_byte_order_and_unit_search_shares_them()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackContent shuffled = new()
        {
            PackId = "test-kucuk",
            Flavor = BuildFlavor.Dev,
            PackSources = [new PackSourceRow("test-kucuk")],
            Attributions = [new PackAttributionRow("test-kucuk", "Deneme kaynagi", "1", null, "Sentetik test verisi (Mutalaa).", null)],
            Units =
            [
                PackTestData.PackUnit("k:test-kucuk:bolum-1:p2", "Deneme paragrafi 2", 2),
                PackTestData.PackUnit("k:test-kucuk:bolum-1:p10", "Deneme paragrafi 10", 10),
                PackTestData.PackUnit("k:test-kucuk:bolum-1:p1", "Deneme paragrafi 1", 1),
            ],
            UnitSearch =
            [
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p2", "iki", "iki", null),
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p10", "on", "on", null),
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p1", "bir", "bir", null),
            ],
        };

        PackFile file = await Writer().WriteAsync(shuffled, PackTestData.Request(temp.Path), ct);

        using SqliteConnection connection = OpenReadOnly(file.Path);
        Assert.Equal(
            ["1=k:test-kucuk:bolum-1:p1", "2=k:test-kucuk:bolum-1:p10", "3=k:test-kucuk:bolum-1:p2"],
            Strings(connection, "SELECT rowid || '=' || anchor FROM unit ORDER BY rowid"));
        Assert.Equal(
            ["1=bir", "2=on", "3=iki"],
            Strings(connection, "SELECT rowid || '=' || tr_wide FROM unit_search ORDER BY rowid"));
    }

    [Fact]
    public async Task The_approved_column_and_the_closed_ayah_range_are_written_as_given()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackContent content = PackTestData.SmallContent();
        PackContent withRange = new()
        {
            PackId = content.PackId,
            Flavor = content.Flavor,
            PackSources = content.PackSources,
            Attributions = content.Attributions,
            Units = [content.Units[0] with { AyahFirst = 7, AyahLast = 7 }, content.Units[1] with { AyahFirst = 7, AyahLast = 9 }, content.Units[2]],
            UnitSearch = content.UnitSearch,
        };

        PackFile file = await Writer().WriteAsync(withRange, PackTestData.Request(temp.Path), ct);

        using SqliteConnection connection = OpenReadOnly(file.Path);
        Assert.Equal(
            ["p1|1|7|7", "p2|0|7|9", "p3|1||"],
            Strings(connection, "SELECT substr(anchor, 22) || '|' || approved || '|' || ifnull(ayah_first, '') || '|' || ifnull(ayah_last, '') FROM unit ORDER BY rowid"));
        Assert.Equal(["integer"], Strings(connection, "SELECT typeof(approved) FROM unit LIMIT 1"));
    }

    [Fact]
    public async Task The_file_can_be_moved_and_deleted_right_after_the_write()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();

        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);

        string moved = file.Path + ".moved";
        File.Move(file.Path, moved);
        File.Delete(moved);
        Assert.False(File.Exists(moved));
        Assert.False(File.Exists(file.Path));
        Assert.False(File.Exists(file.Path + ".tmp"));
    }

    [Fact]
    public async Task A_stale_tmp_file_is_removed_before_writing()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        string directory = Path.Combine(temp.Path, "dev", "2026.11.0");
        Directory.CreateDirectory(directory);
        string stale = Path.Combine(directory, "test-kucuk-2026.11.0.db.tmp");
        await File.WriteAllTextAsync(stale, "artik dosya", ct);

        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);

        Assert.False(File.Exists(stale));
        Assert.True(file.SelfCheck.Passed);
    }

    [Fact]
    public async Task Version_and_built_at_do_not_change_the_content_digest()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackContent content = PackTestData.SmallContent();

        PackFile first = await Writer(Clock1).WriteAsync(content, PackTestData.Request(temp.Path, "2026.11.0"), ct);
        PackFile second = await Writer(Clock2).WriteAsync(content, PackTestData.Request(temp.Path, "2026.12.3"), ct);

        Assert.Equal(first.ContentDigest, second.ContentDigest);
        Assert.NotEqual(first.Path, second.Path);
        Assert.NotEqual(first.Sha256, second.Sha256);
        using SqliteConnection connection = OpenReadOnly(second.Path);
        Dictionary<string, string> meta = Meta(connection);
        Assert.Equal("2026.12.3", meta["version"]);
        Assert.Equal("2026-12-01T08:30:15Z", meta["built_at"]);
        Assert.Equal(first.ContentDigest, meta["content_digest"]);
    }

    [Fact]
    public async Task A_given_content_digest_is_used_instead_of_recomputing()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        string given = new('a', 64);

        PackFile file = await Writer().WriteAsync(
            PackTestData.SmallContent(),
            PackTestData.Request(temp.Path) with { ContentDigest = given },
            ct);

        Assert.Equal(given, file.ContentDigest);
        using SqliteConnection connection = OpenReadOnly(file.Path);
        Assert.Equal(given, Meta(connection)["content_digest"]);
    }

    [Fact]
    public async Task Core_rows_quran_tables_and_probe_anchor_are_written()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        string arabic = PackTestData.SyntheticArabic + " " + new string([.. PackTestData.SyntheticArabic.Reverse()]);
        PackContent core = new()
        {
            PackId = "core",
            Flavor = BuildFlavor.Public,
            PackSources = [new PackSourceRow("tanzil-uthmani"), new PackSourceRow("tanzil-simple-clean"), new PackSourceRow("tanzil-ust-veri")],
            Attributions =
            [
                new PackAttributionRow("tanzil-uthmani", "Deneme kaynagi", "1", null, "kredi 1", "bildirim\nsatiri"),
                new PackAttributionRow("tanzil-simple-clean", "Deneme kaynagi", "1", null, "kredi 2", null),
                new PackAttributionRow("tanzil-ust-veri", "Deneme kaynagi", "1", null, "kredi 3", null),
            ],
            Units =
            [
                PackTestData.PackUnit("q:2:254", "Deneme paragrafi 254", 1, kind: "ayet", ayahFirst: 261, ayahLast: 261),
                PackTestData.PackUnit("q:2:255", "Deneme paragrafi 255", 2, kind: "ayet", ayahFirst: 262, ayahLast: 262),
            ],
            UnitSearch =
            [
                new PackUnitSearchRow("q:2:254", "deneme", "deneme", arabic),
                new PackUnitSearchRow("q:2:255", "deneme", "deneme", arabic),
            ],
            QuranWords = [new PackQuranWordRow("q:2:255:1", 262, 1, PackTestData.SyntheticArabic, PackTestData.SyntheticArabic, 0, 6)],
            QuranMarkers = [new PackQuranMarkerRow("cuz", 1, "q:2:254", null)],
            PageMaps = [new PackPageMapRow("medine-604", null, 42, null, "q:2:254", null, "q:2:255", null)],
        };
        SourceRow[] sources =
        [
            PackTestData.Source("tanzil-uthmani", atifMetni: "kredi 1", notice: "bildirim\nsatiri"),
            PackTestData.Source("tanzil-simple-clean", atifMetni: "kredi 2"),
            PackTestData.Source("tanzil-ust-veri", atifMetni: "kredi 3"),
        ];

        PackFile file = await Writer().WriteAsync(core, PackTestData.Request(temp.Path, "2026.11.0", sources), ct);

        Assert.True(file.SelfCheck.Passed, file.SelfCheck.ToJson());
        SelfCheckItem probe = file.SelfCheck.Items.Single(i => i.Name == "probe_anchor");
        Assert.Contains("q:2:255", probe.Detail, StringComparison.Ordinal);
        using SqliteConnection connection = OpenReadOnly(file.Path);
        Assert.Equal(["q:2:255:1|0|6"], Strings(connection, "SELECT anchor || '|' || char_start || '|' || char_end FROM quran_word"));
        Assert.Equal(["cuz|1|q:2:254"], Strings(connection, "SELECT kind || '|' || no || '|' || anchor FROM quran_marker"));
        Assert.Equal(["medine-604|42"], Strings(connection, "SELECT layout || '|' || page FROM page_map"));
        Assert.Equal(["0"], Strings(connection, "SELECT count(*) FROM sure"));
        Assert.Equal(["bildirim\nsatiri"], Strings(connection, "SELECT notice_text FROM attribution WHERE source_id = 'tanzil-uthmani'"));
        Assert.Equal(["public"], [Meta(connection)["flavor"]]);
    }

    [Fact]
    public async Task The_probe_falls_back_to_the_first_anchor_when_the_pack_has_no_q_2_255()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();

        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);

        SelfCheckItem probe = file.SelfCheck.Items.Single(i => i.Name == "probe_anchor");
        Assert.True(probe.Passed);
        Assert.Contains("k:test-kucuk:bolum-1:p1 ", probe.Detail, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_failing_self_check_throws_with_the_report_and_leaves_no_files()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        SourceRow different = PackTestData.Source("test-kucuk", atifMetni: "baska atif metni");

        PackWriteException ex = await Assert.ThrowsAsync<PackWriteException>(() =>
            Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path, "2026.11.0", different), ct));

        Assert.NotNull(ex.Report);
        Assert.False(ex.Report.Passed);
        Assert.Equal("attribution_roundtrip", ex.Report.Items.Single(i => !i.Passed).Name);
        Assert.Contains("attribution_roundtrip", ex.Message, StringComparison.Ordinal);
        string directory = Path.Combine(temp.Path, "dev", "2026.11.0");
        Assert.Empty(Directory.GetFiles(directory));
    }

    [Fact]
    public async Task A_missing_unit_for_a_unit_search_row_fails_the_write()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackContent content = PackTestData.SmallContent();
        PackContent broken = new()
        {
            PackId = content.PackId,
            Flavor = content.Flavor,
            PackSources = content.PackSources,
            Attributions = content.Attributions,
            Units = content.Units,
            UnitSearch = [.. content.UnitSearch, new PackUnitSearchRow("k:test-kucuk:bolum-1:p99", "x", "x", null)],
        };

        PackWriteException ex = await Assert.ThrowsAsync<PackWriteException>(() =>
            Writer().WriteAsync(broken, PackTestData.Request(temp.Path), ct));

        Assert.Contains("p99", ex.Message, StringComparison.Ordinal);
        Assert.Empty(Directory.GetFiles(Path.Combine(temp.Path, "dev", "2026.11.0")));
    }

    [Fact]
    public async Task A_pack_id_matching_no_type_and_unsafe_file_names_are_rejected()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackContent unknown = new() { PackId = "bilinmeyen", Flavor = BuildFlavor.Dev };

        await Assert.ThrowsAsync<PackDefinitionException>(() => Writer().WriteAsync(unknown, PackTestData.Request(temp.Path), ct));
        await Assert.ThrowsAsync<ArgumentException>(() => Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path, "../x"), ct));
        await Assert.ThrowsAsync<ArgumentException>(() => Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path, "2026..1"), ct));
    }

    [Fact]
    public async Task Cancellation_stops_the_write_and_removes_the_temporary_file()
    {
        using PackTestData.TempDir temp = new();
        using CancellationTokenSource cts = new();
        await cts.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), cts.Token));

        Assert.Empty(Directory.GetFiles(Path.Combine(temp.Path, "dev", "2026.11.0")));
    }

    [Fact]
    public async Task The_self_check_json_is_stable_and_has_no_text_content()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();

        PackFile first = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path, "2026.11.0"), ct);
        PackFile second = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path, "2026.11.0"), ct);

        string json = first.SelfCheck.ToJson();
        Assert.Equal(json, second.SelfCheck.ToJson());
        Assert.StartsWith("{\n  \"pack_id\": \"test-kucuk\",\n  \"version\": \"2026.11.0\",\n  \"passed\": true,\n  \"checks\": [", json, StringComparison.Ordinal);
        Assert.EndsWith("}\n", json, StringComparison.Ordinal);
        Assert.DoesNotContain("\r", json, StringComparison.Ordinal);
        Assert.DoesNotContain("Deneme paragrafi", json, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_report_can_be_written_as_self_check_json_without_a_bom()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);
        string path = Path.Combine(temp.Path, "self-check.json");

        await file.SelfCheck.WriteToFileAsync(path, ct);

        byte[] bytes = await File.ReadAllBytesAsync(path, ct);
        Assert.NotEqual((byte)0xEF, bytes[0]);
        Assert.Equal(file.SelfCheck.ToJson(), System.Text.Encoding.UTF8.GetString(bytes));
    }

    [Fact]
    public async Task RunOnFile_verifies_an_existing_pack_and_detects_a_wrong_expectation()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        PackFile file = await Writer().WriteAsync(PackTestData.SmallContent(), PackTestData.Request(temp.Path), ct);
        PackDefinitions definitions = PackTestData.Definitions();
        IReadOnlyList<string> tables = definitions.ExpectedTables(definitions.Resolve("test-kucuk"));
        Dictionary<string, string> meta = new(StringComparer.Ordinal) { ["pack_id"] = "test-kucuk", ["version"] = "2026.11.0", ["flavor"] = "dev" };

        PackSelfCheckReport ok = PackSelfCheck.RunOnFile(file.Path, new PackSelfCheckExpectations("test-kucuk", "2026.11.0", tables, meta, [PackTestData.Source("test-kucuk")]));
        meta["flavor"] = "public";
        PackSelfCheckReport wrong = PackSelfCheck.RunOnFile(file.Path, new PackSelfCheckExpectations("test-kucuk", "2026.11.0", tables, meta, [PackTestData.Source("test-kucuk")]));

        Assert.True(ok.Passed, ok.ToJson());
        Assert.False(wrong.Passed);
        Assert.Equal("pack_meta", Assert.Single(wrong.Items, i => !i.Passed).Name);
    }

    private sealed class FixedClock(DateTimeOffset now) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => now;
    }
}
