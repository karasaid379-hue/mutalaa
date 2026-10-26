using System.Text;
using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Gocle kurulan semanin pg_dump --schema-only dokumu depodaki anlik goruntuyle (Snapshots/editoryal-sema.sql) karsilastirilir.
/// Bilincli guncelleme: MUTALAA_UPDATE_SNAPSHOTS=1 (dosya yeniden yazilir ve test BILEREK kirmizi biter; CI ortaminda reddedilir).
/// </summary>
public partial class SchemaSnapshotTests(EditorialDatabase<SchemaSnapshotTests> fixture, PostgresFixture postgres) : IClassFixture<EditorialDatabase<SchemaSnapshotTests>>
{
    private const string SnapshotRelativePath = "server/tests/Mutalaa.Api.Tests/Snapshots/editoryal-sema.sql";
    private const string UpdateVariable = "MUTALAA_UPDATE_SNAPSHOTS";

    private TestDatabase Db => fixture.Database;

    [GeneratedRegex(@"^-- Dumped from database version .*$", RegexOptions.CultureInvariant)]
    private static partial Regex DumpedFromLine();

    [GeneratedRegex(@"^-- Dumped by pg_dump version .*$", RegexOptions.CultureInvariant)]
    private static partial Regex DumpedByLine();

    [GeneratedRegex(@"^\\restrict [A-Za-z0-9]+$", RegexOptions.CultureInvariant)]
    private static partial Regex RestrictLine();

    [GeneratedRegex(@"^\\unrestrict [A-Za-z0-9]+$", RegexOptions.CultureInvariant)]
    private static partial Regex UnrestrictLine();

    [Fact]
    public async Task The_schema_dump_matches_the_snapshot()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string actual = await DumpAsync(Db, ct);

        string path = RepoFiles.PathOf(SnapshotRelativePath);
        string? update = Environment.GetEnvironmentVariable(UpdateVariable);
        if (update == "1")
        {
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("CI")))
            {
                Assert.Fail($"{UpdateVariable}=1 CI ortaminda reddedildi: anlik goruntu yalniz yerelde ve bilincli guncellenir.");
            }

            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllBytes(path, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetBytes(actual));
            Assert.Fail($"Anlik goruntu yazildi ({SnapshotRelativePath}); bu test guncelleme kipinde bilerek kirmizi biter. {UpdateVariable} olmadan yeniden calistirin ve farki gozden gecirin.");
        }

        if (!File.Exists(path))
        {
            Assert.Fail($"Anlik goruntu yok: {SnapshotRelativePath}. Ilk uretim icin {UpdateVariable}=1 ile calistirin.");
        }

        string expected = Normalize(RepoFiles.ReadUtf8(path));
        if (!string.Equals(expected, actual, StringComparison.Ordinal))
        {
            Assert.Fail(DescribeDifference(expected, actual));
        }
    }

    [Fact]
    public async Task Two_dumps_of_the_same_database_are_identical()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        string first = await DumpAsync(Db, ct);
        string second = await DumpAsync(Db, ct);

        Assert.Equal(first, second);
    }

    [Fact]
    public async Task A_second_database_migrated_from_scratch_dumps_the_same_schema()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase other = await postgres.CreateDatabaseAsync("schemasnapshotb", ct);
        await other.MigrateAsync(ct);

        Assert.Equal(await DumpAsync(Db, ct), await DumpAsync(other, ct));
    }

    [Fact]
    public async Task The_dump_covers_only_the_two_application_schemas_and_has_no_noise()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string dump = await DumpAsync(Db, ct);

        Assert.DoesNotContain("\r", dump, StringComparison.Ordinal);
        Assert.EndsWith("\n", dump, StringComparison.Ordinal);
        Assert.DoesNotContain("Dumped from database version", dump, StringComparison.Ordinal);
        Assert.DoesNotContain("\\restrict", dump, StringComparison.Ordinal);
        Assert.DoesNotContain("OWNER TO", dump, StringComparison.Ordinal);
        Assert.Contains("CREATE SCHEMA icerik;", dump, StringComparison.Ordinal);
        Assert.Contains("CREATE SCHEMA kimlik;", dump, StringComparison.Ordinal);
        Assert.DoesNotContain("CREATE SCHEMA public;", dump, StringComparison.Ordinal);
        foreach (string line in dump.Split('\n'))
        {
            Assert.Equal(line.TrimEnd(), line);
        }
    }

    /// <summary>Kabin icinde pg_dump; ExitCode 0 dogrulanir, cikti normalize edilir.</summary>
    private async Task<string> DumpAsync(TestDatabase database, CancellationToken ct)
    {
        DotNet.Testcontainers.Containers.ExecResult result = await postgres.ExecAsync(
            [
                "pg_dump", "-U", "postgres", "-d", database.Name,
                "--schema-only", "--no-owner", "--no-privileges", "--schema=icerik", "--schema=kimlik",
            ],
            ct);

        Assert.True(result.ExitCode == 0, $"pg_dump cikis kodu {result.ExitCode}: {result.Stderr}");
        return Normalize(result.Stdout);
    }

    /// <summary>Her kosuda degisen satirlari atar; satir sonu LF, satir sonu bosluklari kirpilir, tek bos satirla biter.</summary>
    private static string Normalize(string dump)
    {
        string text = dump.Replace("\r\n", "\n", StringComparison.Ordinal).Replace('\r', '\n');
        List<string> kept = [];
        foreach (string line in text.Split('\n'))
        {
            if (DumpedFromLine().IsMatch(line) || DumpedByLine().IsMatch(line) || RestrictLine().IsMatch(line) || UnrestrictLine().IsMatch(line))
            {
                continue;
            }

            kept.Add(line.TrimEnd());
        }

        return string.Join('\n', kept).TrimEnd('\n') + "\n";
    }

    private static string DescribeDifference(string expected, string actual)
    {
        string[] e = expected.Split('\n');
        string[] a = actual.Split('\n');
        int count = Math.Min(e.Length, a.Length);
        for (int i = 0; i < count; i++)
        {
            if (!string.Equals(e[i], a[i], StringComparison.Ordinal))
            {
                return $"Sema anlik goruntuden sapti; ilk fark satir {i + 1}:\n  beklenen: {e[i]}\n  gercek:   {a[i]}\n"
                    + $"(beklenen {e.Length} satir, gercek {a.Length} satir). Bilincli degisiklikse {UpdateVariable}=1 ile guncelleyin.";
            }
        }

        return $"Sema anlik goruntuden sapti: satir sayisi farkli (beklenen {e.Length}, gercek {a.Length}); ilk {count} satir ayni. Bilincli degisiklikse {UpdateVariable}=1 ile guncelleyin.";
    }
}
