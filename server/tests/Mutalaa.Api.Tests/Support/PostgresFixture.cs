using System.Globalization;
using System.Text.RegularExpressions;
using DotNet.Testcontainers.Containers;
using Npgsql;
using Testcontainers.PostgreSql;

[assembly: AssemblyFixture(typeof(Mutalaa.Api.Tests.Support.PostgresFixture))]

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Derleme duzeyinde tek PostgreSQL kabi (Testcontainers, postgres:18.6-trixie). Kap TEMBELDIR: kurucu ve InitializeAsync Docker'a hic dokunmaz,
/// kap ilk veritabani isteginde baslar. Boylece Docker kapaliyken yalniz Docker'li siniflar duser; AssemblyFixture hatasi butun derlemeyi
/// (Docker'siz testler dahil) dusurecegi icin fikstur baslangicinda hicbir sey yapilmaz.
/// Her test sinifi kendi veritabanini <c>t_{sinif}_{guid8}</c> adiyla acar; kabin icindeki sistem veritabani ve yerel veritabani kullanilmaz.
/// </summary>
public sealed partial class PostgresFixture : IAsyncLifetime
{
    /// <summary>Compose ile ayni ara surum (Docker kapi: yalniz bu imaj; yerel mutalaa-postgres-1 kullanilmaz).</summary>
    public const string Image = "postgres:18.6-trixie";

    private const string AdminUser = "postgres";

    // CREATE/DROP DATABASE ayni sablondan (template1) es zamanli calisirsa "being accessed by other users" hatasi verir; hepsi bu kilitle siralanir.
    private readonly SemaphoreSlim _gate = new(1, 1);
    private PostgreSqlContainer? _container;

    [GeneratedRegex("^[a-z0-9_]{1,63}$", RegexOptions.CultureInvariant)]
    private static partial Regex DatabaseNamePattern();

    /// <summary>Docker'a dokunmaz.</summary>
    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync()
    {
        if (_container is not null)
        {
            await _container.DisposeAsync();
            _container = null;
        }

        _gate.Dispose();
    }

    /// <summary>Yeni bos veritabani acar (kap gerekirse baslatilir). Ad: <c>t_{tag}_{guid8}</c>.</summary>
    public async Task<TestDatabase> CreateDatabaseAsync(string tag, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrEmpty(tag);

        string name = string.Create(CultureInfo.InvariantCulture, $"t_{tag}_{Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..8]}");
        if (!DatabaseNamePattern().IsMatch(name))
        {
            throw new ArgumentException($"Gecersiz veritabani adi: {name}", nameof(tag));
        }

        await _gate.WaitAsync(cancellationToken);
        try
        {
            PostgreSqlContainer container = await StartedContainerAsync(cancellationToken);
            await ExecuteAdminAsync(container, $"CREATE DATABASE \"{name}\"", cancellationToken);

            NpgsqlConnectionStringBuilder builder = new(container.GetConnectionString())
            {
                Database = name,
                IncludeErrorDetail = true,
            };
            return new TestDatabase(this, name, builder.ConnectionString);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Kabin icinde komut calistirir (pg_dump icin).</summary>
    public async Task<ExecResult> ExecAsync(IList<string> command, CancellationToken cancellationToken)
    {
        PostgreSqlContainer container = _container
            ?? throw new InvalidOperationException("Kap henuz baslamadi; once CreateDatabaseAsync cagrilmali.");
        return await container.ExecAsync(command, cancellationToken);
    }

    /// <summary>Veritabanini siler (acik baglantilara ragmen); ardisik CREATE/DROP kilidi altinda.</summary>
    internal async Task DropDatabaseAsync(string name, CancellationToken cancellationToken)
    {
        if (!DatabaseNamePattern().IsMatch(name))
        {
            throw new ArgumentException($"Gecersiz veritabani adi: {name}", nameof(name));
        }

        PostgreSqlContainer? container = _container;
        if (container is null)
        {
            return;
        }

        await _gate.WaitAsync(cancellationToken);
        try
        {
            await ExecuteAdminAsync(container, $"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)", cancellationToken);
        }
        finally
        {
            _gate.Release();
        }
    }

    private async Task<PostgreSqlContainer> StartedContainerAsync(CancellationToken cancellationToken)
    {
        if (_container is not null)
        {
            return _container;
        }

        // Parametresiz kurucu [Obsolete] (CS0618); imaj acikca verilir. initdb: UTF8 + C.UTF-8 (imaj varsayilani en_US.utf8), saat dilimi UTC.
        PostgreSqlContainer container = new PostgreSqlBuilder(Image)
            .WithEnvironment("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C.UTF-8")
            .WithEnvironment("TZ", "UTC")
            .Build();
        try
        {
            await container.StartAsync(cancellationToken);
        }
        catch
        {
            await container.DisposeAsync();
            throw;
        }

        _container = container;
        return container;
    }

    private static async Task ExecuteAdminAsync(PostgreSqlContainer container, string sql, CancellationToken cancellationToken)
    {
        // Yonetim baglantisi havuzsuz: kapatilinca sunucu tarafinda baglanti kalmaz.
        NpgsqlConnectionStringBuilder builder = new(container.GetConnectionString())
        {
            Pooling = false,
            Username = AdminUser,
        };
        await using NpgsqlConnection connection = new(builder.ConnectionString);
        await connection.OpenAsync(cancellationToken);
        await using NpgsqlCommand command = new(sql, connection);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }
}
