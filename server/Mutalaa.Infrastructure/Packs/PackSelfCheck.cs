using System.Buffers;
using System.Globalization;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>Oz denetimin tek maddesi. Detail kisa ve icerik tasimaz (metin, belirtec ya da kaynak satiri yazilmaz).</summary>
public sealed record SelfCheckItem(string Name, bool Passed, string Detail);

/// <summary>Oz denetim raporu (self-check.json). Madde sirasi sabittir; JSON kararlidir.</summary>
public sealed class PackSelfCheckReport
{
    public PackSelfCheckReport(string packId, string version, IReadOnlyList<SelfCheckItem> items)
    {
        PackId = packId;
        Version = version;
        Items = items;
    }

    public string PackId { get; }

    public string Version { get; }

    public IReadOnlyList<SelfCheckItem> Items { get; }

    public bool Passed => Items.All(i => i.Passed);

    /// <summary>Kirmizi maddelerin adlari (virgulle); hepsi yesilse bos.</summary>
    public string FailedNames => string.Join(", ", Items.Where(i => !i.Passed).Select(i => i.Name));

    /// <summary>ToJson ciktisini UTF-8 (BOM yok) olarak yazar (self-check.json); var olan dosyanin ustune yazar.</summary>
    public async Task WriteToFileAsync(string path, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        await File.WriteAllTextAsync(path, ToJson(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false), cancellationToken);
    }

    /// <summary>{"pack_id","version","passed","checks":[{"name","passed","detail"}]}; girintili, LF satir sonu.</summary>
    public string ToJson()
    {
        ArrayBufferWriter<byte> buffer = new(512);
        using (Utf8JsonWriter writer = new(buffer, new JsonWriterOptions { Indented = true, NewLine = "\n", Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }))
        {
            writer.WriteStartObject();
            writer.WriteString("pack_id", PackId);
            writer.WriteString("version", Version);
            writer.WriteBoolean("passed", Passed);
            writer.WriteStartArray("checks");
            foreach (SelfCheckItem item in Items)
            {
                writer.WriteStartObject();
                writer.WriteString("name", item.Name);
                writer.WriteBoolean("passed", item.Passed);
                writer.WriteString("detail", item.Detail);
                writer.WriteEndObject();
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        return new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetString(buffer.WrittenSpan) + "\n";
    }
}

/// <summary>
/// Oz denetimin beklentileri. ExpectedMeta: pack_meta anahtari -> beklenen deger (built_at yalniz ISO 8601 UTC olarak denetlenir). ExpectedTables
/// paketler.json turunden gelir. Sources: pakete girmesi gereken kaynak satirlari (attribution gidis-donusu ve pack_source icin).
/// </summary>
public sealed record PackSelfCheckExpectations(
    string PackId,
    string Version,
    IReadOnlyList<string> ExpectedTables,
    IReadOnlyDictionary<string, string> ExpectedMeta,
    IReadOnlyList<SourceRow> Sources);

/// <summary>
/// Paket oz denetimi (Backend API 10.4 adim 5, Icerik paketleri 8 madde 5). Yazicinin kapanmadan once calistirdigi denetimler; ayni sinif verify
/// komutunda dosya uzerinde de calisir. Maddeler: integrity_check, user_version, tablo kumesi, pack_meta, unit sayisi, yoklama capasi
/// (q:2:255 varsa o, yoksa ilk capa; tam 1 satir), FTS sorgusu (paketin unit_search ilk satirindan turetilen belirtec; metin elle yazilmaz),
/// attribution gidis-donusu (Domain VerifyP11Attribution ve VerifyP11Notice) ve pack_source kayitlari. unit_search yoksa FTS maddesi atlanir.
/// </summary>
public static class PackSelfCheck
{
    private const string ProbeAnchor = "q:2:255";

    public static PackSelfCheckReport RunOnFile(string path, PackSelfCheckExpectations expectations)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        SqliteConnectionStringBuilder builder = new() { DataSource = path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        using SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        return Run(connection, expectations);
    }

    public static PackSelfCheckReport Run(SqliteConnection connection, PackSelfCheckExpectations expectations)
    {
        ArgumentNullException.ThrowIfNull(connection);
        ArgumentNullException.ThrowIfNull(expectations);

        IReadOnlyList<string> tables = PackDefinitions.UserTables(connection);
        HashSet<string> tableSet = new(tables, StringComparer.Ordinal);
        Dictionary<string, string> meta = ReadMeta(connection, tableSet);

        List<SelfCheckItem> items =
        [
            IntegrityCheck(connection),
            UserVersionCheck(connection),
            TablesCheck(tables, expectations.ExpectedTables),
            MetaCheck(meta, expectations.ExpectedMeta),
            UnitCountCheck(connection, tableSet, meta),
            ProbeAnchorCheck(connection, tableSet),
            FtsCheck(connection, tableSet),
            AttributionCheck(connection, tableSet, expectations.Sources),
            PackSourceCheck(connection, tableSet, expectations.Sources),
        ];
        return new PackSelfCheckReport(expectations.PackId, expectations.Version, items);
    }

    private static SelfCheckItem IntegrityCheck(SqliteConnection connection)
    {
        List<string> results = Strings(connection, "PRAGMA integrity_check");
        bool ok = results.Count == 1 && string.Equals(results[0], "ok", StringComparison.Ordinal);
        return new SelfCheckItem("integrity_check", ok, ok ? "ok" : $"{results.Count} bulgu");
    }

    private static SelfCheckItem UserVersionCheck(SqliteConnection connection)
    {
        long version = Scalar(connection, "PRAGMA user_version");
        bool ok = version == PackFormat.SchemaVersion;
        return new SelfCheckItem("user_version", ok, Inv($"{version}"));
    }

    private static SelfCheckItem TablesCheck(IReadOnlyList<string> actual, IReadOnlyList<string> expected)
    {
        string[] want = [.. expected.Order(StringComparer.Ordinal)];
        string[] missing = [.. want.Except(actual, StringComparer.Ordinal)];
        string[] extra = [.. actual.Except(want, StringComparer.Ordinal)];
        bool ok = missing.Length == 0 && extra.Length == 0;
        return new SelfCheckItem(
            "tables",
            ok,
            ok ? Inv($"{actual.Count} tablo") : $"eksik: [{string.Join(",", missing)}] fazla: [{string.Join(",", extra)}]");
    }

    private static SelfCheckItem MetaCheck(Dictionary<string, string> meta, IReadOnlyDictionary<string, string> expected)
    {
        List<string> problems = [];
        foreach (string key in expected.Keys.Order(StringComparer.Ordinal))
        {
            if (!meta.TryGetValue(key, out string? value))
            {
                problems.Add(key + ":yok");
            }
            else if (!string.Equals(value, expected[key], StringComparison.Ordinal))
            {
                problems.Add(key + ":uyusmuyor");
            }
        }

        if (!meta.TryGetValue("built_at", out string? builtAt)
            || !DateTimeOffset.TryParseExact(builtAt, "yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out _))
        {
            problems.Add("built_at:gecersiz");
        }

        foreach (string key in new[] { "pack_id", "version", "flavor", "schema_version", "content_digest", "normalizer_version", "anchors_version", "data_version", "unit_count" })
        {
            if (!meta.ContainsKey(key) && !expected.ContainsKey(key))
            {
                problems.Add(key + ":yok");
            }
        }

        bool ok = problems.Count == 0;
        return new SelfCheckItem("pack_meta", ok, ok ? Inv($"{meta.Count} anahtar") : string.Join(",", problems));
    }

    private static SelfCheckItem UnitCountCheck(SqliteConnection connection, HashSet<string> tables, Dictionary<string, string> meta)
    {
        if (!tables.Contains("unit"))
        {
            return new SelfCheckItem("unit_count", true, "atlandi: unit tablosu yok");
        }

        long count = Scalar(connection, "SELECT count(*) FROM unit");
        bool parsed = meta.TryGetValue("unit_count", out string? raw)
            && long.TryParse(raw, NumberStyles.None, CultureInfo.InvariantCulture, out long declared)
            && declared == count;
        return new SelfCheckItem("unit_count", parsed, Inv($"{count}"));
    }

    private static SelfCheckItem ProbeAnchorCheck(SqliteConnection connection, HashSet<string> tables)
    {
        if (!tables.Contains("unit"))
        {
            return new SelfCheckItem("probe_anchor", true, "atlandi: unit tablosu yok");
        }

        string? anchor = null;
        using (SqliteCommand has = connection.CreateCommand())
        {
            has.CommandText = "SELECT anchor FROM unit WHERE anchor = $a";
            has.Parameters.AddWithValue("$a", ProbeAnchor);
            anchor = has.ExecuteScalar() as string;
        }

        if (anchor is null)
        {
            using SqliteCommand first = connection.CreateCommand();
            first.CommandText = "SELECT anchor FROM unit ORDER BY rowid LIMIT 1";
            anchor = first.ExecuteScalar() as string;
        }

        if (anchor is null)
        {
            return new SelfCheckItem("probe_anchor", true, "atlandi: unit bos");
        }

        using SqliteCommand count = connection.CreateCommand();
        count.CommandText = "SELECT count(*) FROM unit WHERE anchor = $a";
        count.Parameters.AddWithValue("$a", anchor);
        long rows = Convert.ToInt64(count.ExecuteScalar(), CultureInfo.InvariantCulture);
        bool ok = rows == 1;
        return new SelfCheckItem("probe_anchor", ok, Inv($"{anchor} satir={rows}"));
    }

    private static SelfCheckItem FtsCheck(SqliteConnection connection, HashSet<string> tables)
    {
        if (!tables.Contains("unit_search") || !tables.Contains("unit_fts"))
        {
            return new SelfCheckItem("fts_query", true, "atlandi: unit_search yok");
        }

        long rowid;
        string? arNorm;
        string? trWide;
        string? trStem;
        using (SqliteCommand command = connection.CreateCommand())
        {
            command.CommandText = "SELECT rowid, ar_norm, tr_wide, tr_stem FROM unit_search ORDER BY rowid LIMIT 1";
            using SqliteDataReader reader = command.ExecuteReader();
            if (!reader.Read())
            {
                return new SelfCheckItem("fts_query", true, "atlandi: unit_search bos");
            }

            rowid = reader.GetInt64(0);
            arNorm = reader.IsDBNull(1) ? null : reader.GetString(1);
            trWide = reader.IsDBNull(2) ? null : reader.GetString(2);
            trStem = reader.IsDBNull(3) ? null : reader.GetString(3);
        }

        (string Column, string? Text)[] candidates = [("ar_norm", arNorm), ("tr_wide", trWide), ("tr_stem", trStem)];
        bool any = false;
        foreach ((string column, string? text) in candidates)
        {
            string? token = FirstToken(text);
            if (token is null)
            {
                continue;
            }

            any = true;
            using SqliteCommand query = connection.CreateCommand();
            query.CommandText = "SELECT rowid FROM unit_fts WHERE unit_fts MATCH $q";
            query.Parameters.AddWithValue("$q", column + " : \"" + token.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"");
            List<long> hits = [];
            try
            {
                using SqliteDataReader reader = query.ExecuteReader();
                while (reader.Read())
                {
                    hits.Add(reader.GetInt64(0));
                }
            }
            catch (SqliteException)
            {
                continue;
            }

            if (hits.Contains(rowid))
            {
                return new SelfCheckItem("fts_query", true, Inv($"sutun={column} rowid={rowid} sonuc={hits.Count}"));
            }
        }

        return new SelfCheckItem("fts_query", !any, any ? "belirtec arama sonucunda bulunamadi" : "atlandi: unit_search ilk satirinda belirtec yok");
    }

    private static SelfCheckItem AttributionCheck(SqliteConnection connection, HashSet<string> tables, IReadOnlyList<SourceRow> sources)
    {
        if (!tables.Contains("attribution"))
        {
            return new SelfCheckItem("attribution_roundtrip", false, "attribution tablosu yok");
        }

        Dictionary<string, (string Title, string? Version, string? SourceUrl, string Credit, string? Notice)> rows = new(StringComparer.Ordinal);
        using (SqliteCommand command = connection.CreateCommand())
        {
            command.CommandText = "SELECT source_id, title, version, source_url, required_credit, notice_text FROM attribution";
            using SqliteDataReader reader = command.ExecuteReader();
            while (reader.Read())
            {
                rows[reader.GetString(0)] = (
                    reader.GetString(1),
                    reader.IsDBNull(2) ? null : reader.GetString(2),
                    reader.IsDBNull(3) ? null : reader.GetString(3),
                    reader.GetString(4),
                    reader.IsDBNull(5) ? null : reader.GetString(5));
            }
        }

        List<string> problems = [];
        foreach (SourceRow source in sources.OrderBy(s => s.Slug, StringComparer.Ordinal))
        {
            if (!rows.TryGetValue(source.Slug, out var packRow))
            {
                problems.Add(source.Slug + ":satir-yok");
                continue;
            }

            foreach (GateViolation v in GateEvaluator.VerifyP11Attribution(source.Slug, source.AtifMetni, source.AtifUrl ?? source.KaynakUrl, packRow.Credit, packRow.SourceUrl))
            {
                problems.Add(source.Slug + ":" + v.Reason);
            }

            foreach (GateViolation v in GateEvaluator.VerifyP11Notice(source.Slug, source.NoticeText, packRow.Notice))
            {
                problems.Add(source.Slug + ":" + v.Reason);
            }

            if (!string.Equals(packRow.Title, source.Baslik, StringComparison.Ordinal))
            {
                problems.Add(source.Slug + ":baslik-uyusmuyor");
            }

            if (!string.Equals(packRow.Version, source.Surum, StringComparison.Ordinal))
            {
                problems.Add(source.Slug + ":surum-uyusmuyor");
            }
        }

        foreach (string slug in rows.Keys.Except(sources.Select(s => s.Slug), StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            problems.Add(slug + ":beklenmeyen-satir");
        }

        bool ok = problems.Count == 0;
        return new SelfCheckItem("attribution_roundtrip", ok, ok ? Inv($"{rows.Count} kaynak") : string.Join(",", problems));
    }

    private static SelfCheckItem PackSourceCheck(SqliteConnection connection, HashSet<string> tables, IReadOnlyList<SourceRow> sources)
    {
        if (!tables.Contains("pack_source"))
        {
            return new SelfCheckItem("pack_source", false, "pack_source tablosu yok");
        }

        string[] actual = [.. Strings(connection, "SELECT source_id FROM pack_source").Order(StringComparer.Ordinal)];
        string[] expected = [.. sources.Select(s => s.Slug).Order(StringComparer.Ordinal)];
        bool ok = actual.SequenceEqual(expected, StringComparer.Ordinal);
        return new SelfCheckItem("pack_source", ok, ok ? Inv($"{actual.Length} kaynak") : $"beklenen [{string.Join(",", expected)}] bulunan [{string.Join(",", actual)}]");
    }

    private static Dictionary<string, string> ReadMeta(SqliteConnection connection, HashSet<string> tables)
    {
        Dictionary<string, string> meta = new(StringComparer.Ordinal);
        if (!tables.Contains("pack_meta"))
        {
            return meta;
        }

        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT key, value FROM pack_meta";
        using SqliteDataReader reader = command.ExecuteReader();
        while (reader.Read())
        {
            meta[reader.GetString(0)] = reader.GetString(1);
        }

        return meta;
    }

    private static string? FirstToken(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return null;
        }

        foreach (string part in text.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        {
            if (part.Length > 0)
            {
                return part;
            }
        }

        return null;
    }

    private static List<string> Strings(SqliteConnection connection, string sql)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        using SqliteDataReader reader = command.ExecuteReader();
        List<string> values = [];
        while (reader.Read())
        {
            values.Add(reader.GetString(0));
        }

        return values;
    }

    private static long Scalar(SqliteConnection connection, string sql)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToInt64(command.ExecuteScalar(), CultureInfo.InvariantCulture);
    }

    private static string Inv(FormattableString value) => value.ToString(CultureInfo.InvariantCulture);
}
