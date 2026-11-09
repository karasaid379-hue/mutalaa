using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Onizleme testleri icin sinif veritabani: butun goclar uygulanir ve <see cref="EndToEndData"/> sentetik icerigiyle bir kez tohumlanir
/// (Tanzil parcasi fiksturleri ham dosya olarak <see cref="RawDir"/> altina, kaynak kayitlari <see cref="SourcesDir"/> altina yazilir).
/// Testler bu veritabanini degistirmez; degistirenler isi bitirince geri alir.
/// </summary>
public sealed class SeededReleaseDatabase<TTests>(PostgresFixture postgres) : IAsyncLifetime
{
    public TestDatabase Database { get; private set; } = null!;

    /// <summary>Ham Tanzil dosyalari (P-11) ve kaynak kayitlari (P-01) bu klasorun altindadir.</summary>
    public string RootDir { get; private set; } = string.Empty;

    public string RawDir => Path.Combine(RootDir, "raw");

    public string SourcesDir => Path.Combine(RootDir, "sources");

    public async ValueTask InitializeAsync()
    {
        CancellationToken cancellationToken = TestContext.Current.CancellationToken;
        RootDir = Path.Combine(Path.GetTempPath(), "mutalaa-api-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(RootDir);

        Database = await postgres.CreateDatabaseAsync("releasepreview", cancellationToken);
        await Database.MigrateAsync(cancellationToken);
        _ = await EndToEndData.SeedAsync(Database, RawDir, SourcesDir, cancellationToken);
    }

    public async ValueTask DisposeAsync()
    {
        if (Database is not null)
        {
            await Database.DisposeAsync();
        }

        try
        {
            if (RootDir.Length > 0)
            {
                Directory.Delete(RootDir, recursive: true);
            }
        }
        catch (IOException)
        {
            // Gecici klasor; sistem temizler.
        }
    }
}
