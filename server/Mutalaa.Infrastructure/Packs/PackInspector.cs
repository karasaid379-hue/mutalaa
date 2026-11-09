using Microsoft.Data.Sqlite;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>pack_meta'dan okunan, manifestle karsilastirilan alanlar (yoksa null).</summary>
public sealed record PackFileMeta(string? PackId, string? Version, string? Flavor, string? SchemaVersion, string? ContentDigest);

/// <summary>attribution satiri (paket dosyasindan geri okunan).</summary>
public sealed record PackAttributionInfo(string SourceId, string Title, string? Version, string? SourceUrl, string RequiredCredit, string? NoticeText);

/// <summary>
/// Yazilmis bir paket dosyasini salt okunur acar (Pooling=False; Windows acik dosyayi tasitmaz/silemez). Yayinlayici onceki yayinin capalarini ve
/// verify komutu paket ust verisini buradan okur; SQLite API'si Publisher'a sizmaz. Tablo yoksa bos liste doner.
/// </summary>
public static class PackInspector
{
    public static PackFileMeta ReadMeta(string path)
    {
        using SqliteConnection connection = Open(path);
        Dictionary<string, string> meta = new(StringComparer.Ordinal);
        if (TableExists(connection, "pack_meta"))
        {
            using SqliteCommand command = connection.CreateCommand();
            command.CommandText = "SELECT key, value FROM pack_meta";
            using SqliteDataReader reader = command.ExecuteReader();
            while (reader.Read())
            {
                meta[reader.GetString(0)] = reader.GetString(1);
            }
        }

        return new PackFileMeta(
            meta.GetValueOrDefault("pack_id"),
            meta.GetValueOrDefault("version"),
            meta.GetValueOrDefault("flavor"),
            meta.GetValueOrDefault("schema_version"),
            meta.GetValueOrDefault("content_digest"));
    }

    /// <summary>pack_source.source_id degerleri (Ordinal sirali).</summary>
    public static IReadOnlyList<string> ReadPackSources(string path)
    {
        using SqliteConnection connection = Open(path);
        return Column(connection, "pack_source", "SELECT source_id FROM pack_source");
    }

    /// <summary>unit.anchor degerleri (Ordinal sirali). Onceki yayinin capalari (Yayin sureci 4 madde 2).</summary>
    public static IReadOnlyList<string> ReadUnitAnchors(string path)
    {
        using SqliteConnection connection = Open(path);
        return Column(connection, "unit", "SELECT anchor FROM unit");
    }

    public static IReadOnlyList<PackAttributionInfo> ReadAttributions(string path)
    {
        using SqliteConnection connection = Open(path);
        List<PackAttributionInfo> rows = [];
        if (!TableExists(connection, "attribution"))
        {
            return rows;
        }

        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT source_id, title, version, source_url, required_credit, notice_text FROM attribution";
        using SqliteDataReader reader = command.ExecuteReader();
        while (reader.Read())
        {
            rows.Add(new PackAttributionInfo(
                reader.GetString(0),
                reader.GetString(1),
                reader.IsDBNull(2) ? null : reader.GetString(2),
                reader.IsDBNull(3) ? null : reader.GetString(3),
                reader.GetString(4),
                reader.IsDBNull(5) ? null : reader.GetString(5)));
        }

        return rows;
    }

    private static List<string> Column(SqliteConnection connection, string table, string sql)
    {
        List<string> values = [];
        if (!TableExists(connection, table))
        {
            return values;
        }

        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        using SqliteDataReader reader = command.ExecuteReader();
        while (reader.Read())
        {
            values.Add(reader.GetString(0));
        }

        values.Sort(StringComparer.Ordinal);
        return values;
    }

    private static bool TableExists(SqliteConnection connection, string table)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = $name";
        command.Parameters.AddWithValue("$name", table);
        return command.ExecuteScalar() is not null;
    }

    private static SqliteConnection Open(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        SqliteConnectionStringBuilder builder = new() { DataSource = path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        SqliteConnection connection = new(builder.ConnectionString);
        try
        {
            connection.Open();
        }
        catch
        {
            connection.Dispose();
            throw;
        }

        return connection;
    }
}
