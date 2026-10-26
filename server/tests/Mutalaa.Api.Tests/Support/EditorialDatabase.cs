namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Test sinifi basina bir veritabani (xunit sinif fiksturu): <c>t_{sinif}_{guid8}</c> acilir ve butun goclar uygulanir.
/// Docker'a yalniz bu fikstur kullanan sinif dokunur; Docker'siz siniflar etkilenmez.
/// </summary>
/// <typeparam name="TTests">Veritabani adinda kullanilan test sinifi (sonundaki "Tests" atilir, kucuk harfe cevrilir).</typeparam>
public sealed class EditorialDatabase<TTests>(PostgresFixture postgres) : IAsyncLifetime
{
    public TestDatabase Database { get; private set; } = null!;

    public async ValueTask InitializeAsync()
    {
        CancellationToken cancellationToken = TestContext.Current.CancellationToken;
        Database = await postgres.CreateDatabaseAsync(Tag(), cancellationToken);
        await Database.MigrateAsync(cancellationToken);
    }

    public async ValueTask DisposeAsync()
    {
        if (Database is not null)
        {
            await Database.DisposeAsync();
        }
    }

    /// <summary>Kulturden bagimsiz ASCII kucuk harf (ToLower kullanilmaz).</summary>
    private static string Tag()
    {
        string name = typeof(TTests).Name;
        if (name.EndsWith("Tests", StringComparison.Ordinal))
        {
            name = name[..^"Tests".Length];
        }

        return string.Create(name.Length, name, static (span, source) =>
        {
            for (int i = 0; i < source.Length; i++)
            {
                char c = source[i];
                span[i] = c is >= 'A' and <= 'Z' ? (char)(c + 32) : c;
            }
        });
    }
}
