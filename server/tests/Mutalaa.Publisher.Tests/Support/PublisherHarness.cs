using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Yayinlayici testlerinin duzenegi (Docker: her harness kendi PostgreSQL veritabanini acar ve goc eder). Sentetik icerik: iki kaynak
/// (test-kucuk = uctan uca fikstur, sentetik-kaynak = public'e girebilen) ve birer onayli birim; katalog iki paketten olusur
/// (test-kucuk ve hadis-sentetik, bagimliliksiz). Gercek Kur'an, meal ya da hadis metni yoktur. Gizli degerler testte uretilir, sabit degildir.
/// </summary>
internal sealed class PublisherHarness : IAsyncDisposable
{
    public const string KucukSlug = "test-kucuk";
    public const string SyntheticSlug = "sentetik-kaynak";
    public const string KucukAnchor = "k:test-kucuk:bolum-1:p1";
    public const string SyntheticAnchor = "k:sentetik-kaynak:bolum-1:p1";
    public const string PublicBaseUrl = "http://example.invalid:8333/mutalaa";

    private readonly ServiceProvider _services;

    private PublisherHarness(
        TestDatabase database,
        PackTestData.TempDir directory,
        ServiceProvider services,
        IConfiguration configuration,
        InMemoryPackStore store,
        FixedClock clock,
        StringWriter output,
        StringWriter error,
        Dictionary<BuildFlavor, SigningKey> keys,
        PackCatalog catalog)
    {
        Database = database;
        Directory = directory;
        _services = services;
        Configuration = configuration;
        Store = store;
        Clock = clock;
        Out = output;
        Error = error;
        Keys = keys;
        Host = new PublisherHostOptions
        {
            Catalog = catalog,
            GitShortSha = _ => Task.FromResult("abc1234"),
            Clock = clock,
            StoreFactory = () => store,
            Out = output,
            Error = error,
            SecretsPath = Path.Combine(directory.Path, "secrets.json"),
            EnvironmentName = "Production",
        };
        Releases = new ReleaseRepository(services.GetRequiredService<IServiceScopeFactory>(), clock);
        Context = new PublisherContext(configuration, Releases, Host);
    }

    public TestDatabase Database { get; }

    public PackTestData.TempDir Directory { get; }

    public IConfiguration Configuration { get; }

    public InMemoryPackStore Store { get; }

    public FixedClock Clock { get; }

    public StringWriter Out { get; }

    public StringWriter Error { get; }

    public Dictionary<BuildFlavor, SigningKey> Keys { get; }

    public PublisherHostOptions Host { get; }

    public ReleaseRepository Releases { get; }

    public PublisherContext Context { get; }

    public ReleasePipeline Pipeline => new(Context);

    public string SourcesDir => Path.Combine(Directory.Path, "sources");

    public string OutDir => Path.Combine(Directory.Path, "out");

    public string ReportsDir => Path.Combine(Directory.Path, "reports");

    public static PackCatalog SyntheticCatalog() => new(
    [
        new PackDefinition("test-kucuk", "Sentetik kucuk kitap", Bundled: false, DependsOn: [], Sources: [new PackSourceBinding(KucukSlug, PackSourceRole.Content, Required: true)]),
        new PackDefinition("hadis-sentetik", "Sentetik hadis", Bundled: false, DependsOn: [], Sources: [new PackSourceBinding(SyntheticSlug, PackSourceRole.Content, Required: true)]),
    ]);

    public static async Task<PublisherHarness> CreateAsync(PostgresFixture postgres, bool seed = true, PackCatalog? catalog = null)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        TestDatabase database = await postgres.CreateDatabaseAsync("pub", ct);
        await database.MigrateAsync(ct);

        PackTestData.TempDir directory = new();
        Dictionary<BuildFlavor, SigningKey> keys = [];
        Dictionary<string, string?> values = new(StringComparer.Ordinal)
        {
            ["ConnectionStrings:Editorial"] = database.ConnectionString,
            ["Storage:ServiceUrl"] = "http://127.0.0.1:1",
            ["Storage:AccessKey"] = "test-access-key-sentetik",
            ["Storage:SecretKey"] = "test-secret-key-sentetik",
            ["Storage:Bucket"] = "mutalaa-test",
            ["Storage:PublicBaseUrl"] = PublicBaseUrl,
            ["Publisher:SchemaDir"] = RepoFiles.PathOf("packages/content-schema/sql"),
            ["Publisher:RawDir"] = Path.Combine(directory.Path, "raw"),
            ["Publisher:OutDir"] = Path.Combine(directory.Path, "out"),
            ["Publisher:SourcesDir"] = Path.Combine(directory.Path, "sources"),
            ["Publisher:ReportsDir"] = Path.Combine(directory.Path, "reports"),
            ["Publisher:TempDir"] = Path.Combine(directory.Path, "tmp"),
            ["Publisher:MinAppVersion"] = "1.0.0",
        };
        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            SigningKey key = SigningKeys.Generate(flavor.ToLabel(), 2026, 1);
            keys[flavor] = key;
            values[$"Signing:{flavor.ToLabel()}:PrivateKey"] = key.SeedBase64();
            values[$"Signing:{flavor.ToLabel()}:Kid"] = key.Kid;
            values[$"Signing:{flavor.ToLabel()}:PublicKey"] = Base64Strict.Encode(key.GetPublicKey());
        }

        IConfiguration configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        ServiceProvider services = ModelFactory.BuildServices(configuration: configuration);
        PublisherHarness harness = new(
            database,
            directory,
            services,
            configuration,
            new InMemoryPackStore(),
            new FixedClock(new DateTimeOffset(2026, 11, 9, 12, 0, 0, TimeSpan.Zero)),
            new StringWriter(),
            new StringWriter(),
            keys,
            catalog ?? SyntheticCatalog());

        System.IO.Directory.CreateDirectory(harness.SourcesDir);
        if (seed)
        {
            await harness.SeedAsync(ct);
        }

        return harness;
    }

    /// <summary>Iki sentetik kaynak, birer onayli birim ve kaynak kayit dosyalari (P-01).</summary>
    public async Task SeedAsync(CancellationToken cancellationToken)
    {
        foreach (string slug in new[] { KucukSlug, SyntheticSlug })
        {
            await InsertSourceAsync(slug, cancellationToken);
            RegisterSource(slug);
        }

        await InsertUnitAsync(KucukAnchor, KucukSlug, "Deneme paragrafi 1", cancellationToken);
        await InsertUnitAsync(SyntheticAnchor, SyntheticSlug, "Deneme paragrafi 2", cancellationToken);
    }

    public void RegisterSource(string slug) => File.WriteAllText(Path.Combine(SourcesDir, slug + ".toml"), "slug = \"" + slug + "\"\n");

    public void UnregisterSource(string slug) => File.Delete(Path.Combine(SourcesDir, slug + ".toml"));

    public Task InsertSourceAsync(string slug, CancellationToken cancellationToken) =>
        Database.ExecuteAsync(
            """
            INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni)
            VALUES (@slug, 'kitap'::icerik.source_kind, 'Deneme kaynagi', '1', 'Sentetik test verisi (Mutalaa).')
            """,
            cancellationToken,
            ("slug", slug));

    public Task InsertUnitAsync(string anchor, string sourceId, string metin, CancellationToken cancellationToken, string durum = "onayli") =>
        Database.ExecuteAsync(
            """
            INSERT INTO icerik.unit (anchor, kind, source_id, ord, metin, marks, sentences, content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, ar_norm, attrs, data_version)
            VALUES (@anchor, 'kitap'::icerik.unit_kind, @source, 1, @metin, '[]'::jsonb, NULL, @hash, @durum::icerik.metin_durumu,
                    'deneme', 'deneme paragrafi', 'deneme paragraf', NULL, '{}'::jsonb, 'test')
            """,
            cancellationToken,
            ("anchor", anchor),
            ("source", sourceId),
            ("metin", metin),
            ("hash", HashOf(metin)),
            ("durum", durum));

    /// <summary>Birimin metnini ve content_hash degerini degistirir (bir sonraki yayinda paket ozeti ve kaynak ozeti degisir).</summary>
    public Task ChangeUnitAsync(string anchor, string metin, CancellationToken cancellationToken) =>
        Database.ExecuteAsync(
            "UPDATE icerik.unit SET metin = @metin, content_hash = @hash WHERE anchor = @anchor",
            cancellationToken,
            ("anchor", anchor),
            ("metin", metin),
            ("hash", HashOf(metin)));

    public static string HashOf(string text) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text)));

    public static string ManifestKey(string flavor) => $"{flavor}/manifest.json";

    public static string HistoryKey(string flavor, string surum) => $"{flavor}/manifests/{surum}.json";

    public static string PackKey(string flavor, string packId, string version) => $"packs/{flavor}/{packId}/{version}/{packId}-{version}.db";

    public Manifest ReadStoredManifest(string flavor) =>
        ManifestJson.Read(Store.Peek(ManifestKey(flavor)) ?? throw new InvalidOperationException("Depoda manifest yok."));

    public async Task<int> CountReleasesAsync(CancellationToken cancellationToken) =>
        (int)await Database.ScalarAsync<long>("SELECT count(*) FROM icerik.release", cancellationToken);

    public async ValueTask DisposeAsync()
    {
        await Context.DisposeAsync();
        await _services.DisposeAsync();
        await Database.DisposeAsync();
        Directory.Dispose();
    }
}
