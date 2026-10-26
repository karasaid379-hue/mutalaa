using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure.Persistence;
using Npgsql;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Test kabindaki tek bir veritabani. Baglam Api'nin kullandigi DI yolundan (AddIcerikDb + AddEditorIdentity, <see cref="ModelFactory"/>) alinir:
/// Identity modeli DI'daki IdentityOptions'a bagli oldugu icin DI'siz kurulan model farkli cikar.
/// Ham baglanti yalniz test duzenegi ve katalog sorgulari icindir; yazilan SQL parametrelidir.
/// </summary>
public sealed class TestDatabase : IAsyncDisposable
{
    private readonly PostgresFixture _owner;
    private ServiceProvider? _services;

    internal TestDatabase(PostgresFixture owner, string name, string connectionString)
    {
        _owner = owner;
        Name = name;
        ConnectionString = connectionString;
    }

    public string Name { get; }

    /// <summary>Bu veritabanina baglanti dizesi (kap kullanicisi; yerel veritabani degil).</summary>
    public string ConnectionString { get; }

    internal IConfiguration Configuration => new ConfigurationBuilder()
        .AddInMemoryCollection(new Dictionary<string, string?> { ["ConnectionStrings:Editorial"] = ConnectionString })
        .Build();

    private ServiceProvider Services => _services ??= ModelFactory.BuildServices(configuration: Configuration);

    /// <summary>Butun goclari uygular ve enum turleri olusunca Npgsql tur onbellegini yeniler.</summary>
    public async Task MigrateAsync(CancellationToken cancellationToken, bool uncachedModel = false)
    {
        // Model onbellegini atlayan ayri saglayici (yerel ayar testleri); varsayilan saglayici onbellekli modeli kullanir.
        ServiceProvider provider = uncachedModel ? ModelFactory.BuildServices(uncachedModel: true, configuration: Configuration) : Services;
        try
        {
            await using (AsyncServiceScope scope = provider.CreateAsyncScope())
            {
                IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
                await context.Database.MigrateAsync(cancellationToken);
            }

            await ReloadTypesAsync(provider, cancellationToken);
        }
        finally
        {
            if (uncachedModel)
            {
                await provider.DisposeAsync();
            }
        }

        if (uncachedModel)
        {
            // Varsayilan saglayicinin veri kaynagi da yeni turleri gormeli.
            await ReloadTypesAsync(Services, cancellationToken);
        }
    }

    /// <summary>DI yolundan yeni bir baglam (kapsamla birlikte); goctan sonra acilir.</summary>
    public DbSession OpenSession() => new(Services.CreateAsyncScope());

    /// <summary>Goc geri alinan (rollback) oturum: her test kendi islemini acar ve sonunda geri alir.</summary>
    public async Task<RollbackSession> OpenRollbackSessionAsync(CancellationToken cancellationToken)
    {
        DbSession session = OpenSession();
        IDbContextTransaction transaction = await session.Context.Database.BeginTransactionAsync(cancellationToken);
        return new RollbackSession(session, transaction);
    }

    /// <summary>
    /// Model onbellegi atlanan yeni bir saglayici (model ve veri kaynagi cagiranin kulturunde sifirdan kurulur);
    /// cagiran yok eder. Veritabani onceden goc edilmis olmali (enum turleri yeni veri kaynagi tarafindan yuklenir).
    /// </summary>
    public ServiceProvider BuildUncachedServices() => ModelFactory.BuildServices(uncachedModel: true, configuration: Configuration);

    /// <summary>Verilen saglayicidan (ornegin <see cref="BuildUncachedServices"/>) islem acan geri alinan oturum.</summary>
    public static async Task<RollbackSession> OpenRollbackSessionAsync(ServiceProvider provider, CancellationToken cancellationToken)
    {
        DbSession session = new(provider.CreateAsyncScope());
        IDbContextTransaction transaction = await session.Context.Database.BeginTransactionAsync(cancellationToken);
        return new RollbackSession(session, transaction);
    }

    /// <summary>Havuzsuz ham baglanti (katalog sorgulari ve test duzenegi).</summary>
    public async Task<NpgsqlConnection> OpenRawConnectionAsync(CancellationToken cancellationToken)
    {
        NpgsqlConnectionStringBuilder builder = new(ConnectionString) { Pooling = false };
        NpgsqlConnection connection = new(builder.ConnectionString);
        try
        {
            await connection.OpenAsync(cancellationToken);
        }
        catch
        {
            await connection.DisposeAsync();
            throw;
        }

        return connection;
    }

    /// <summary>Tek skaler deger (ham baglanti; parametreli).</summary>
    public async Task<T> ScalarAsync<T>(string sql, CancellationToken cancellationToken, params (string Name, object? Value)[] parameters)
    {
        await using NpgsqlConnection connection = await OpenRawConnectionAsync(cancellationToken);
        await using NpgsqlCommand command = new(sql, connection);
        AddParameters(command, parameters);
        object? value = await command.ExecuteScalarAsync(cancellationToken);
        return value is null or DBNull ? default! : (T)value;
    }

    /// <summary>Sonuc dondurmeyen komut (ham baglanti; parametreli).</summary>
    public async Task<int> ExecuteAsync(string sql, CancellationToken cancellationToken, params (string Name, object? Value)[] parameters)
    {
        await using NpgsqlConnection connection = await OpenRawConnectionAsync(cancellationToken);
        await using NpgsqlCommand command = new(sql, connection);
        AddParameters(command, parameters);
        return await command.ExecuteNonQueryAsync(cancellationToken);
    }

    /// <summary>Tek sutunlu sorgu sonucunu metin listesi olarak dondurur (katalog sorgulari).</summary>
    public async Task<IReadOnlyList<string>> ColumnAsync(string sql, CancellationToken cancellationToken, params (string Name, object? Value)[] parameters)
    {
        await using NpgsqlConnection connection = await OpenRawConnectionAsync(cancellationToken);
        await using NpgsqlCommand command = new(sql, connection);
        AddParameters(command, parameters);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        List<string> rows = [];
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(reader.GetString(0));
        }

        return rows;
    }

    public async ValueTask DisposeAsync()
    {
        if (_services is not null)
        {
            await _services.DisposeAsync();
            _services = null;
        }

        // Temizlik en iyi cabadir: kap zaten derleme sonunda yok edilir; bir silme hatasi testin sonucunu degistirmemeli.
        try
        {
            await _owner.DropDatabaseAsync(Name, CancellationToken.None);
        }
        catch (NpgsqlException)
        {
        }
    }

    internal static void AddParameters(DbCommand command, (string Name, object? Value)[] parameters)
    {
        foreach ((string name, object? value) in parameters)
        {
            DbParameter parameter = command.CreateParameter();
            parameter.ParameterName = name;
            parameter.Value = value ?? DBNull.Value;
            command.Parameters.Add(parameter);
        }
    }

    private static async Task ReloadTypesAsync(ServiceProvider provider, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = provider.CreateAsyncScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        NpgsqlConnection connection = (NpgsqlConnection)context.Database.GetDbConnection();
        await connection.OpenAsync(cancellationToken);
        try
        {
            await connection.ReloadTypesAsync(cancellationToken);
        }
        finally
        {
            await connection.CloseAsync();
        }
    }
}

/// <summary>DI kapsami ve baglam.</summary>
public sealed class DbSession(AsyncServiceScope scope) : IAsyncDisposable
{
    public IcerikDbContext Context { get; } = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();

    public IServiceProvider Services => scope.ServiceProvider;

    public ValueTask DisposeAsync() => scope.DisposeAsync();
}

/// <summary>Bir islem icinde calisan oturum; atilinca islem geri alinir (veritabaninda iz kalmaz).</summary>
public sealed class RollbackSession(DbSession session, IDbContextTransaction transaction) : IAsyncDisposable
{
    public IcerikDbContext Context => session.Context;

    /// <summary>Skaler sorgu; baglamin baglantisi ve islemi uzerinden (parametreli).</summary>
    public async Task<T> ScalarAsync<T>(string sql, CancellationToken cancellationToken, params (string Name, object? Value)[] parameters)
    {
        DbConnection connection = Context.Database.GetDbConnection();
        await using DbCommand command = connection.CreateCommand();
        command.CommandText = sql;
        command.Transaction = transaction.GetDbTransaction();
        TestDatabase.AddParameters(command, parameters);
        object? value = await command.ExecuteScalarAsync(cancellationToken);
        return value is null or DBNull ? default! : (T)value;
    }

    /// <summary>Sonuc dondurmeyen ham komut; baglamin baglantisi ve islemi uzerinden (parametreli). Ihlalde PostgresException atar.</summary>
    public async Task<int> ExecuteAsync(string sql, CancellationToken cancellationToken, params (string Name, object? Value)[] parameters)
    {
        DbConnection connection = Context.Database.GetDbConnection();
        await using DbCommand command = connection.CreateCommand();
        command.CommandText = sql;
        command.Transaction = transaction.GetDbTransaction();
        TestDatabase.AddParameters(command, parameters);
        return await command.ExecuteNonQueryAsync(cancellationToken);
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            await transaction.RollbackAsync(CancellationToken.None);
        }
        finally
        {
            await transaction.DisposeAsync();
            await session.DisposeAsync();
        }
    }
}
