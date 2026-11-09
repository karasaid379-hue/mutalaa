using System.Globalization;
using Microsoft.Data.Sqlite;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Depodan indirilen paketin salt okunur SQLite baglantisi (Pooling=False: Windows acik dosyayi silmeye izin vermez). Dispose baglantiyi kapatir ve dosyayi siler.
/// </summary>
internal sealed class PackDb : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly string _path;

    private PackDb(string path)
    {
        _path = path;
        SqliteConnectionStringBuilder builder = new() { DataSource = path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        _connection = new SqliteConnection(builder.ConnectionString);
        _connection.Open();
    }

    public static PackDb FromBytes(byte[] bytes, string directory)
    {
        Directory.CreateDirectory(directory);
        string path = Path.Combine(directory, Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture) + ".db");
        File.WriteAllBytes(path, bytes);
        return new PackDb(path);
    }

    public T Scalar<T>(string sql, params (string Name, object Value)[] parameters)
    {
        using SqliteCommand command = Command(sql, parameters);
        object? value = command.ExecuteScalar();
        return (T)Convert.ChangeType(value ?? throw new InvalidOperationException("Sorgu satir dondurmedi."), typeof(T), CultureInfo.InvariantCulture);
    }

    public List<string> Column(string sql, params (string Name, object Value)[] parameters)
    {
        using SqliteCommand command = Command(sql, parameters);
        using SqliteDataReader reader = command.ExecuteReader();
        List<string> values = [];
        while (reader.Read())
        {
            values.Add(reader.GetString(0));
        }

        return values;
    }

    public List<string> Anchors() => Column("SELECT anchor FROM unit ORDER BY rowid");

    public Dictionary<string, string> Meta()
    {
        using SqliteCommand command = Command("SELECT key, value FROM pack_meta");
        using SqliteDataReader reader = command.ExecuteReader();
        Dictionary<string, string> meta = new(StringComparer.Ordinal);
        while (reader.Read())
        {
            meta[reader.GetString(0)] = reader.GetString(1);
        }

        return meta;
    }

    public void Dispose()
    {
        _connection.Dispose();
        try
        {
            File.Delete(_path);
        }
        catch (IOException)
        {
            // Windows / OneDrive kilidi: temizlik en iyi cabadir.
        }
    }

    private SqliteCommand Command(string sql, (string Name, object Value)[]? parameters = null)
    {
        SqliteCommand command = _connection.CreateCommand();
        command.CommandText = sql;
        foreach ((string name, object value) in parameters ?? [])
        {
            command.Parameters.AddWithValue(name, value);
        }

        return command;
    }
}
