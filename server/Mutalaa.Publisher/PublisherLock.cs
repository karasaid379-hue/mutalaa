using Npgsql;

namespace Mutalaa.Publisher;

/// <summary>
/// Yayinlayici danisma kilidi (Backend API 10.2): ayni anda tek Yayinlayici calisir. Kilit <c>pg_try_advisory_lock</c> ile ve AYRI, HAVUZSUZ
/// (<c>Pooling=False</c>) bir baglantida tutulur: havuzlu baglanti havuza donunce oturum kilidi sizar. Atilinca kilit birakilir ve baglanti kapanir.
/// </summary>
public sealed class PublisherLock : IAsyncDisposable
{
    /// <summary>"MUTALAA1" (ASCII) 64 bit tam sayi olarak; veritabani basina tek anahtar.</summary>
    public const long Key = 0x4D5554414C414131L;

    private NpgsqlConnection? _connection;

    private PublisherLock(NpgsqlConnection connection)
    {
        _connection = connection;
    }

    /// <summary>Kilidi almaya calisir; baska bir tutucu varsa null doner (cagiran cikis 1 ile biter).</summary>
    public static async Task<PublisherLock?> TryAcquireAsync(string connectionString, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(connectionString);

        NpgsqlConnectionStringBuilder builder = new(connectionString) { Pooling = false };
        NpgsqlConnection connection = new(builder.ConnectionString);
        try
        {
            await connection.OpenAsync(cancellationToken);
            await using NpgsqlCommand command = new("SELECT pg_try_advisory_lock(@key)", connection);
            command.Parameters.AddWithValue("key", Key);
            bool acquired = (bool)(await command.ExecuteScalarAsync(cancellationToken))!;
            if (!acquired)
            {
                await connection.DisposeAsync();
                return null;
            }

            return new PublisherLock(connection);
        }
        catch
        {
            await connection.DisposeAsync();
            throw;
        }
    }

    public async ValueTask DisposeAsync()
    {
        NpgsqlConnection? connection = _connection;
        _connection = null;
        if (connection is null)
        {
            return;
        }

        try
        {
            await using NpgsqlCommand command = new("SELECT pg_advisory_unlock(@key)", connection);
            command.Parameters.AddWithValue("key", Key);
            await command.ExecuteScalarAsync(CancellationToken.None);
        }
        catch (NpgsqlException)
        {
            // Baglanti kopmus olabilir; oturum kapaninca sunucu kilidi kendiliginden birakir.
        }
        finally
        {
            await connection.DisposeAsync();
        }
    }
}
