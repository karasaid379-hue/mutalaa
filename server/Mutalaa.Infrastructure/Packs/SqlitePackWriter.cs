using System.Globalization;
using System.Security.Cryptography;
using Microsoft.Data.Sqlite;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>pack_meta anahtarlari (Icerik paketleri 3.1). Ortak anahtarlar SqlitePackWriter.ExpectedMeta'dadir; burada yalniz pakete ozgu olanlar.</summary>
public static class PackMetaKeys
{
    /// <summary>
    /// kelime-kok kunyesi: pakete uygulanan onayli quran_word_fix sayisi (tamsayi metni). Kunye "QAC v0.4 + Mutalaa duzeltmeleri (N adet)" bu degerden
    /// yazilir; attribution satiri bundan etkilenmez (P-11). Diger paketlerde anahtar yoktur.
    /// </summary>
    public const string WordFixCount = "word_fix_count";

    /// <summary>
    /// Tur kapisi ozeti (K-51 madde 5 ve 11): RFC 8785 kanonik JSON <c>{tur: {set_sinifi, sonuc}}</c>. Yalniz kelime-kok (kok, lemma) ve core (benzer_ayet)
    /// paketlerinde bulunur; paket ozetine girer. Uygulama ve rapor "silver ile olculdu" bilgisini buradan okur.
    /// </summary>
    public const string GateSummary = "gate_summary";
}

/// <summary>
/// Yazilan paket dosyasi. SelfCheck her zaman yesildir (kirmizi oz denetim PackWriteException atar ve dosya olusmaz).
/// ContentDigest paketin pack_meta.content_digest degeridir (PackDigest).
/// </summary>
public sealed record PackFile(string Path, string Sha256, long SizeBytes, string ContentDigest, PackSelfCheckReport SelfCheck);

/// <summary>
/// Yazim istegi. OutDir koktur (Publisher:OutDir); dosya {OutDir}/{flavor}/{Version}/{pack_id}-{Version}.db olur. Sources: pakete girmesi gereken
/// kaynak satirlari (oz denetimin attribution gidis-donusu icin). ContentDigest verilirse (cagiran zaten hesapladiysa) yeniden hesaplanmaz.
/// </summary>
public sealed record PackWriteRequest(
    string OutDir,
    string Version,
    string DataVersion,
    IReadOnlyList<SourceRow> Sources,
    string? ContentDigest = null);

/// <summary>
/// SQLite paket yazicisi (Backend API 10.4). Adimlar: {pack_id}-{version}.db.tmp ac (eski artigi sil), ENABLE_FTS5 denetle, page_size=4096,
/// journal_mode=OFF, synchronous=OFF, paketler.json ddl dosyalari, user_version dogrula, satirlari tek islemde hazirlanmis komutlarla yaz
/// (unit rowid 1..n capa sirasiyla; unit_search ayni rowid), sonra dosyalari, pack_meta, ANALYZE, VACUUM, journal_mode=DELETE, oz denetim, baglanti kapat
/// (Pooling=False), .db adina tasi (IOException icin 3 deneme, 200 ms; OneDrive), sha256 ve boyut. Yazim yapmadan ozet icin <see cref="PackDigest.Compute"/>.
/// Zaman disaridan verilir (TimeProvider): built_at ISO 8601 UTC.
/// </summary>
public sealed class SqlitePackWriter
{
    private const int MoveAttempts = 3;
    private static readonly TimeSpan MoveDelay = TimeSpan.FromMilliseconds(200);

    private readonly PackDefinitions _definitions;
    private readonly TimeProvider _clock;

    public SqlitePackWriter(PackDefinitions definitions, TimeProvider? clock = null)
    {
        ArgumentNullException.ThrowIfNull(definitions);
        _definitions = definitions;
        _clock = clock ?? TimeProvider.System;
    }

    /// <exception cref="PackDefinitionException">Paket kimligi tam bir ture eslesmiyorsa.</exception>
    /// <exception cref="PackWriteException">FTS5 yok, DDL ya da yazim hatasi, oz denetim kirmizi ya da dosya tasinamadiysa.</exception>
    public async Task<PackFile> WriteAsync(PackContent content, PackWriteRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(content);
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.OutDir);
        ValidateFileNamePart(request.Version, "surum");
        ValidateFileNamePart(content.PackId, "paket kimligi");

        PackType type = _definitions.Resolve(content.PackId);
        string flavor = content.Flavor.ToLabel();
        string directory = Path.Combine(request.OutDir, flavor, request.Version);
        Directory.CreateDirectory(directory);

        string baseName = content.PackId + "-" + request.Version;
        string tempPath = Path.Combine(directory, baseName + ".db.tmp");
        string finalPath = Path.Combine(directory, baseName + ".db");
        DeleteIfExists(tempPath);

        string digest = request.ContentDigest ?? PackDigest.Compute(content);
        PackSelfCheckReport report;
        try
        {
            report = BuildDatabase(tempPath, type, content, request, flavor, digest, cancellationToken);
        }
        catch
        {
            DeleteIfExists(tempPath);
            throw;
        }

        if (!report.Passed)
        {
            DeleteIfExists(tempPath);
            throw new PackWriteException($"Oz denetim kirmizi ({content.PackId}): {report.FailedNames}", report);
        }

        await MoveWithRetryAsync(tempPath, finalPath, cancellationToken);

        long size = new FileInfo(finalPath).Length;
        string sha256;
        await using (FileStream stream = new(finalPath, FileMode.Open, FileAccess.Read, FileShare.Read, 81920, useAsync: true))
        {
            sha256 = Convert.ToHexStringLower(await SHA256.HashDataAsync(stream, cancellationToken));
        }

        return new PackFile(finalPath, sha256, size, digest, report);
    }

    private PackSelfCheckReport BuildDatabase(
        string tempPath,
        PackType type,
        PackContent content,
        PackWriteRequest request,
        string flavor,
        string digest,
        CancellationToken cancellationToken)
    {
        SqliteConnectionStringBuilder builder = new() { DataSource = tempPath, Pooling = false, Mode = SqliteOpenMode.ReadWriteCreate };
        using SqliteConnection connection = new(builder.ConnectionString);
        try
        {
            connection.Open();
            EnsureFts5(connection);

            Exec(connection, "PRAGMA page_size=4096");
            Exec(connection, "PRAGMA journal_mode=OFF");
            Exec(connection, "PRAGMA synchronous=OFF");

            foreach (string ddl in type.Ddl)
            {
                Exec(connection, _definitions.ReadSql(ddl), ddl);
            }

            long userVersion = ScalarLong(connection, "PRAGMA user_version");
            if (userVersion != content.SchemaVersion)
            {
                throw new PackWriteException(Inv($"user_version {userVersion}, beklenen {content.SchemaVersion} ({content.PackId})."));
            }

            WriteRows(connection, content, cancellationToken);

            foreach (string after in type.After)
            {
                Exec(connection, _definitions.ReadSql(after), after);
            }

            WriteMeta(connection, content, request, flavor, digest);

            Exec(connection, "ANALYZE");
            Exec(connection, "VACUUM");
            Exec(connection, "PRAGMA journal_mode=DELETE");

            PackSelfCheckExpectations expectations = new(
                content.PackId,
                request.Version,
                _definitions.ExpectedTables(type),
                ExpectedMeta(content, request, flavor, digest),
                [.. request.Sources.Where(s => content.PackSources.Any(p => string.Equals(p.SourceId, s.Slug, StringComparison.Ordinal)))]);
            return PackSelfCheck.Run(connection, expectations);
        }
        catch (SqliteException ex)
        {
            throw new PackWriteException($"SQLite hatasi ({content.PackId}): {ex.Message}", ex);
        }
    }

    private static void EnsureFts5(SqliteConnection connection)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "PRAGMA compile_options";
        using SqliteDataReader reader = command.ExecuteReader();
        while (reader.Read())
        {
            if (string.Equals(reader.GetString(0), "ENABLE_FTS5", StringComparison.Ordinal))
            {
                return;
            }
        }

        throw new PackWriteException("SQLite derlemesinde ENABLE_FTS5 yok; paket yazilamaz.");
    }

    private static void WriteRows(SqliteConnection connection, PackContent content, CancellationToken cancellationToken)
    {
        Dictionary<string, long> rowids = new(StringComparer.Ordinal);
        long nextRowid = 1;

        using SqliteTransaction transaction = connection.BeginTransaction();
        Dictionary<string, SqliteCommand> commands = new(StringComparer.Ordinal);
        try
        {
            foreach (PackRow row in PackRows.Enumerate(content))
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (!commands.TryGetValue(row.Table, out SqliteCommand? command))
                {
                    command = Prepare(connection, transaction, row.Table);
                    commands[row.Table] = command;
                }

                SqliteParameterCollection parameters = command.Parameters;
                int offset = 0;
                if (row.Table == PackTables.Unit)
                {
                    long rowid = nextRowid++;
                    rowids[(string)row.Values[0]!] = rowid;
                    parameters[0].Value = rowid;
                    offset = 1;
                    for (int i = 0; i < row.Values.Length; i++)
                    {
                        parameters[i + offset].Value = row.Values[i] ?? DBNull.Value;
                    }
                }
                else if (row.Table == PackTables.UnitSearch)
                {
                    string anchor = (string)row.Values[0]!;
                    if (!rowids.TryGetValue(anchor, out long rowid))
                    {
                        throw new PackWriteException($"unit_search satirinin birimi yok: {anchor}");
                    }

                    parameters[0].Value = rowid;
                    for (int i = 1; i < row.Values.Length; i++)
                    {
                        parameters[i].Value = row.Values[i] ?? DBNull.Value;
                    }
                }
                else
                {
                    for (int i = 0; i < row.Values.Length; i++)
                    {
                        parameters[i].Value = row.Values[i] ?? DBNull.Value;
                    }
                }

                try
                {
                    command.ExecuteNonQuery();
                }
                catch (SqliteException ex)
                {
                    throw new PackWriteException($"{row.Table} satiri yazilamadi: {ex.Message}", ex);
                }
            }

            transaction.Commit();
        }
        finally
        {
            foreach (SqliteCommand command in commands.Values)
            {
                command.Dispose();
            }
        }
    }

    private static SqliteCommand Prepare(SqliteConnection connection, SqliteTransaction transaction, string table)
    {
        IReadOnlyList<string> columns = PackTables.Columns(table);
        List<string> names = [];
        if (table == PackTables.Unit)
        {
            names.Add("rowid");
            names.AddRange(columns);
        }
        else if (table == PackTables.UnitSearch)
        {
            names.Add("rowid");
            names.AddRange(columns.Skip(1));
        }
        else
        {
            names.AddRange(columns);
        }

        SqliteCommand command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = $"INSERT INTO {table} ({string.Join(", ", names)}) VALUES ({string.Join(", ", names.Select((_, i) => "$p" + i.ToString(CultureInfo.InvariantCulture)))})";
        for (int i = 0; i < names.Count; i++)
        {
            SqliteParameter parameter = command.CreateParameter();
            parameter.ParameterName = "$p" + i.ToString(CultureInfo.InvariantCulture);
            command.Parameters.Add(parameter);
        }

        command.Prepare();
        return command;
    }

    private static Dictionary<string, string> ExpectedMeta(PackContent content, PackWriteRequest request, string flavor, string digest)
    {
        Dictionary<string, string> meta = new(StringComparer.Ordinal)
        {
            ["pack_id"] = content.PackId,
            ["version"] = request.Version,
            ["flavor"] = flavor,
            ["schema_version"] = content.SchemaVersion.ToString(CultureInfo.InvariantCulture),
            ["content_digest"] = digest,
            ["normalizer_version"] = SearchNormalizer.NormalizerVersion,
            ["anchors_version"] = PackFormat.AnchorsVersion,
            ["data_version"] = request.DataVersion,
            ["unit_count"] = content.Units.Count.ToString(CultureInfo.InvariantCulture),
        };

        // Kunye (K-50 madde 9): yalniz kelime-kok; "QAC v0.4 + Mutalaa duzeltmeleri (N adet)" cihazda bu degerden yazilir.
        if (content.WordFixCount is { } fixes)
        {
            meta[PackMetaKeys.WordFixCount] = fixes.ToString(CultureInfo.InvariantCulture);
        }

        if (content.GateSummary is { } gateSummary)
        {
            meta[PackMetaKeys.GateSummary] = gateSummary;
        }

        return meta;
    }

    private void WriteMeta(SqliteConnection connection, PackContent content, PackWriteRequest request, string flavor, string digest)
    {
        Dictionary<string, string> meta = ExpectedMeta(content, request, flavor, digest);
        meta["built_at"] = _clock.GetUtcNow().UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture);

        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "INSERT INTO pack_meta (key, value) VALUES ($k, $v)";
        SqliteParameter key = command.CreateParameter();
        key.ParameterName = "$k";
        SqliteParameter value = command.CreateParameter();
        value.ParameterName = "$v";
        command.Parameters.Add(key);
        command.Parameters.Add(value);
        foreach ((string k, string v) in meta.OrderBy(p => p.Key, StringComparer.Ordinal))
        {
            key.Value = k;
            value.Value = v;
            command.ExecuteNonQuery();
        }
    }

    private static async Task MoveWithRetryAsync(string source, string destination, CancellationToken cancellationToken)
    {
        for (int attempt = 1; ; attempt++)
        {
            try
            {
                File.Move(source, destination, overwrite: true);
                return;
            }
            catch (IOException) when (attempt < MoveAttempts)
            {
                await Task.Delay(MoveDelay, cancellationToken);
            }
            catch (IOException ex)
            {
                throw new PackWriteException($"Paket dosyasi tasinamadi: {Path.GetFileName(destination)}", ex);
            }
        }
    }

    private static void DeleteIfExists(string path)
    {
        if (File.Exists(path))
        {
            File.Delete(path);
        }
    }

    private static void ValidateFileNamePart(string value, string what)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(value);
        if (!string.Equals(Path.GetFileName(value), value, StringComparison.Ordinal) || value.Contains("..", StringComparison.Ordinal))
        {
            throw new ArgumentException($"Gecersiz {what}: {value}", nameof(value));
        }
    }

    private static void Exec(SqliteConnection connection, string sql, string? file = null)
    {
        try
        {
            using SqliteCommand command = connection.CreateCommand();
            command.CommandText = sql;
            command.ExecuteNonQuery();
        }
        catch (SqliteException ex)
        {
            throw new PackWriteException($"SQL calistirilamadi{(file is null ? string.Empty : " (" + file + ")")}: {ex.Message}", ex);
        }
    }

    private static long ScalarLong(SqliteConnection connection, string sql)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToInt64(command.ExecuteScalar(), CultureInfo.InvariantCulture);
    }

    private static string Inv(FormattableString value) => value.ToString(CultureInfo.InvariantCulture);
}
