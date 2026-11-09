using System.Collections.Concurrent;
using System.Diagnostics.CodeAnalysis;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Data.Sqlite;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>Paket bicimi sabitleri (Icerik paketleri 3.1).</summary>
public static class PackFormat
{
    /// <summary>PRAGMA user_version ve pack_meta.schema_version. Henuz yayimlanmis paket yok; BC-47 sonrasi da 1 kalir.</summary>
    public const int SchemaVersion = 1;

    /// <summary>pack_meta.anchors_version.</summary>
    public const string AnchorsVersion = "1";
}

/// <summary>paketler.json'daki bir paket turu: kimlik deseni, paket yazimindan once calisan DDL dosyalari ve satirlardan sonra calisan dosyalar.</summary>
public sealed class PackType
{
    internal PackType(string name, string pattern, IReadOnlyList<string> ddl, IReadOnlyList<string> after)
    {
        Name = name;
        Pattern = pattern;
        Ddl = ddl;
        After = after;
        PackIdRegex = new Regex(pattern, RegexOptions.CultureInvariant);
    }

    public string Name { get; }

    public string Pattern { get; }

    public IReadOnlyList<string> Ddl { get; }

    /// <summary>paketler.json "sonra": satirlar yazildiktan sonra calisir (FTS rebuild, rank, optimize).</summary>
    public IReadOnlyList<string> After { get; }

    internal Regex PackIdRegex { get; }
}

/// <summary>
/// packages/content-schema/sql/paketler.json okuyucusu (Backend API 10.4 adim 2): tur desenleri ve DDL listeleri baska yerde tekrarlanmaz.
/// SchemaDir (Publisher:SchemaDir) goreli verilebilir; calisma dizinine gore cozulur (Path.GetFullPath) ve yollar Path.Combine ile kurulur.
/// </summary>
public sealed class PackDefinitions
{
    public const string FileName = "paketler.json";

    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    // Paket kimligi gramer: kucuk harf ASCII, rakam ve tire. "$" son satir sonundan once de eslesir; bu yuzden \z kullanilir ve desenler yalniz bu denetimden gecen kimliklere uygulanir.
    private static readonly Regex PackIdShape = new(@"^[a-z0-9]+(-[a-z0-9]+)*\z", RegexOptions.CultureInvariant);

    private readonly ConcurrentDictionary<string, IReadOnlyList<string>> _expectedTables = new(StringComparer.Ordinal);

    private PackDefinitions(string schemaDir, int version, IReadOnlyList<PackType> types)
    {
        SchemaDir = schemaDir;
        Version = version;
        Types = types;
    }

    /// <summary>DDL klasorunun tam yolu.</summary>
    public string SchemaDir { get; }

    /// <summary>paketler.json "version".</summary>
    public int Version { get; }

    /// <summary>paketler.json'daki siraya gore turler.</summary>
    public IReadOnlyList<PackType> Types { get; }

    /// <summary>schemaDir goreli ya da mutlak olabilir; goreli yol calisma dizinine gore cozulur.</summary>
    public static PackDefinitions Load(string schemaDir)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(schemaDir);

        string dir = Path.GetFullPath(schemaDir);
        string file = Path.Combine(dir, FileName);
        if (!File.Exists(file))
        {
            throw new PackDefinitionException($"{FileName} bulunamadi: {file}");
        }

        return Parse(ReadStrict(file), dir);
    }

    /// <summary>JSON metninden okur (testler); schemaDir DDL dosyalarinin klasorudur.</summary>
    public static PackDefinitions Parse(string json, string schemaDir)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentException.ThrowIfNullOrWhiteSpace(schemaDir);

        try
        {
            using JsonDocument document = JsonDocument.Parse(json);
            JsonElement root = document.RootElement;
            int version = root.GetProperty("version").GetInt32();
            List<PackType> types = [];
            foreach (JsonProperty property in root.GetProperty("turler").EnumerateObject())
            {
                string pattern = property.Value.GetProperty("desen").GetString()
                    ?? throw new PackDefinitionException($"{property.Name}: desen bos.");
                types.Add(new PackType(
                    property.Name,
                    pattern,
                    ReadList(property.Value.GetProperty("ddl")),
                    ReadList(property.Value.GetProperty("sonra"))));
            }

            if (types.Count == 0)
            {
                throw new PackDefinitionException($"{FileName}: tur yok.");
            }

            return new PackDefinitions(Path.GetFullPath(schemaDir), version, types);
        }
        catch (Exception ex) when (ex is JsonException or KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException)
        {
            throw new PackDefinitionException($"{FileName} gecersiz: {ex.Message}", ex);
        }
    }

    /// <summary>Paket kimligi tam bir ture eslesmelidir; hicbirine ya da birden fazlasina eslesirse PackDefinitionException.</summary>
    public PackType Resolve(string packId)
    {
        if (!TryResolveCore(packId, out PackType? type, out string error))
        {
            throw new PackDefinitionException(error);
        }

        return type;
    }

    public bool TryResolve(string? packId, [NotNullWhen(true)] out PackType? type)
        => TryResolveCore(packId, out type, out _);

    /// <summary>paketler.json'daki bir dosyanin (ornegin 10-metin.sql) metni; ad yalniz dosya adidir.</summary>
    public string ReadSql(string fileName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(fileName);
        if (!string.Equals(Path.GetFileName(fileName), fileName, StringComparison.Ordinal))
        {
            throw new PackDefinitionException($"DDL dosya adi yol icermemeli: {fileName}");
        }

        string path = Path.Combine(SchemaDir, fileName);
        if (!File.Exists(path))
        {
            throw new PackDefinitionException($"DDL dosyasi bulunamadi: {path}");
        }

        return ReadStrict(path);
    }

    /// <summary>
    /// Turun DDL dosyalarini bos bir bellek ici SQLite'ta calistirir ve gercek tablo kumesini (FTS5 golge tablolari haric, Ordinal sirali) dondurur.
    /// Beklenen tablo kumesi bu yolla paketler.json'dan turetilir; baska yerde tekrarlanmaz.
    /// </summary>
    public IReadOnlyList<string> ExpectedTables(PackType type)
    {
        ArgumentNullException.ThrowIfNull(type);

        return _expectedTables.GetOrAdd(type.Name, _ =>
        {
            SqliteConnectionStringBuilder builder = new() { DataSource = ":memory:", Pooling = false };
            using SqliteConnection connection = new(builder.ConnectionString);
            connection.Open();
            foreach (string ddl in type.Ddl)
            {
                using SqliteCommand command = connection.CreateCommand();
                command.CommandText = ReadSql(ddl);
                command.ExecuteNonQuery();
            }

            return UserTables(connection);
        });
    }

    /// <summary>Bagli veritabanindaki gercek tablolar (sqlite_ ve FTS5 golge tablolari haric, Ordinal sirali).</summary>
    public static IReadOnlyList<string> UserTables(SqliteConnection connection)
    {
        ArgumentNullException.ThrowIfNull(connection);

        List<string> tables = [];
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'";
        using SqliteDataReader reader = command.ExecuteReader();
        while (reader.Read())
        {
            string name = reader.GetString(0);
            if (!IsFtsShadow(name))
            {
                tables.Add(name);
            }
        }

        tables.Sort(StringComparer.Ordinal);
        return tables;
    }

    private static bool IsFtsShadow(string name) =>
        (name.StartsWith("unit_fts_", StringComparison.Ordinal) || name.StartsWith("unit_tri_", StringComparison.Ordinal))
        && (name.EndsWith("_data", StringComparison.Ordinal) || name.EndsWith("_idx", StringComparison.Ordinal)
            || name.EndsWith("_docsize", StringComparison.Ordinal) || name.EndsWith("_config", StringComparison.Ordinal)
            || name.EndsWith("_content", StringComparison.Ordinal));

    private static List<string> ReadList(JsonElement array) =>
        [.. array.EnumerateArray().Select(e => e.GetString() ?? throw new PackDefinitionException("Dosya adi bos."))];

    private static string ReadStrict(string path)
    {
        string text = StrictUtf8.GetString(File.ReadAllBytes(path));
        return text.Length > 0 && text[0] == '﻿' ? throw new PackDefinitionException($"Dosyada BOM var: {path}") : text;
    }

    private bool TryResolveCore(string? packId, [NotNullWhen(true)] out PackType? type, out string error)
    {
        type = null;
        if (packId is null || !PackIdShape.IsMatch(packId))
        {
            error = $"Gecersiz paket kimligi: {packId}";
            return false;
        }

        List<PackType> matches = [.. Types.Where(t => t.PackIdRegex.IsMatch(packId))];
        if (matches.Count == 1)
        {
            type = matches[0];
            error = string.Empty;
            return true;
        }

        error = matches.Count == 0
            ? $"Paket kimligi hicbir ture eslesmiyor: {packId}"
            : $"Paket kimligi birden fazla ture eslesiyor: {packId} ({string.Join(", ", matches.Select(t => t.Name))})";
        return false;
    }
}
