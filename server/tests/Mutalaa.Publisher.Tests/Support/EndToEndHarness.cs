using System.Globalization;
using System.Text.Json;
using Amazon.S3;
using Amazon.S3.Model;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>Komut satiri calistirmasinin sonucu.</summary>
internal sealed record CliResult(int Code, string Out, string Error);

/// <summary>Kapi raporunun bir satiri (release.kapi_raporu JSON'u).</summary>
internal sealed record GateRow(string Kind, string Id, string Decision, string? Rule, string Reason, int Count);

/// <summary>
/// A13.5 uctan uca duzenek: GERCEK PostgreSQL (PostgresFixture) + GERCEK SeaweedFS (SeaweedFixture). Her duzenek kendi veritabanini ve kendi kovasini acar
/// (kovalar test arasinda paylasilmaz: depo anahtarlari derleme turune gore sabittir). Fikstur icerigi <see cref="EndToEndData"/> ile tohumlanir.
/// Gizli degerler (depo anahtarlari, imza tohumlari) testte uretilir ve hicbir ciktiya yazilmaz.
/// </summary>
internal sealed class EndToEndHarness : IAsyncDisposable
{
    private readonly ServiceProvider _services;
    private readonly Dictionary<string, string?> _values;
    private readonly S3PackStore _reader;

    private EndToEndHarness(
        TestDatabase database,
        PackTestData.TempDir directory,
        ServiceProvider services,
        Dictionary<string, string?> values,
        StorageOptions storage,
        FixedClock clock,
        Dictionary<BuildFlavor, SigningKey> keys,
        PackCatalog catalog)
    {
        Database = database;
        Directory = directory;
        _services = services;
        _values = values;
        Storage = storage;
        Clock = clock;
        Keys = keys;
        Catalog = catalog;
        Configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        _reader = S3PackStore.Create(storage);
        Out = new StringWriter();
        Error = new StringWriter();
        Host = new PublisherHostOptions
        {
            Catalog = catalog,
            GitShortSha = _ => Task.FromResult("abc1234"),
            Clock = clock,
            StoreFactory = () => S3PackStore.Create(storage),
            Out = Out,
            Error = Error,
            SecretsPath = Path.Combine(directory.Path, "secrets.json"),
            EnvironmentName = "Production",
        };
        Releases = new ReleaseRepository(services.GetRequiredService<IServiceScopeFactory>(), clock);
        Context = new PublisherContext(Configuration, Releases, Host);
    }

    public TestDatabase Database { get; }

    public PackTestData.TempDir Directory { get; }

    public StorageOptions Storage { get; }

    public IConfiguration Configuration { get; }

    public FixedClock Clock { get; }

    public StringWriter Out { get; }

    public StringWriter Error { get; }

    public Dictionary<BuildFlavor, SigningKey> Keys { get; }

    public PackCatalog Catalog { get; }

    public PublisherHostOptions Host { get; }

    public ReleaseRepository Releases { get; }

    public PublisherContext Context { get; }

    public SeededContent Content { get; private set; } = null!;

    /// <summary>Dogrudan okuma/yazma icin ikinci bir depo istemcisi (Context kendi istemcisini kullanir).</summary>
    public IPackStore Reader => _reader;

    public ReleasePipeline Pipeline => new(Context);

    public string RawDir => Path.Combine(Directory.Path, "raw");

    public string SourcesDir => Path.Combine(Directory.Path, "sources");

    public string OutDir => Path.Combine(Directory.Path, "out");

    public string ReportsDir => Path.Combine(Directory.Path, "reports");

    public static async Task<EndToEndHarness> CreateAsync(PostgresFixture postgres, SeaweedFixture seaweed, bool seed = true)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        string bucket = "e2e-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..12];
        using (AmazonS3Client admin = S3PackStore.CreateClient(endpoint.ToOptions()))
        {
            await admin.PutBucketAsync(new PutBucketRequest { BucketName = bucket }, ct);
        }

        StorageOptions storage = new()
        {
            ServiceUrl = endpoint.ServiceUrl,
            AccessKey = endpoint.AccessKey,
            SecretKey = endpoint.SecretKey,
            Bucket = bucket,
            PublicBaseUrl = $"{endpoint.ServiceUrl}/{bucket}",
        };

        TestDatabase database = await postgres.CreateDatabaseAsync("e2e", ct);
        await database.MigrateAsync(ct);

        PackTestData.TempDir directory = new();
        Dictionary<BuildFlavor, SigningKey> keys = [];
        Dictionary<string, string?> values = new(StringComparer.Ordinal)
        {
            ["ConnectionStrings:Editorial"] = database.ConnectionString,
            ["Storage:ServiceUrl"] = storage.ServiceUrl,
            ["Storage:AccessKey"] = storage.AccessKey,
            ["Storage:SecretKey"] = storage.SecretKey,
            ["Storage:Bucket"] = storage.Bucket,
            ["Storage:PublicBaseUrl"] = storage.PublicBaseUrl,
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

        ServiceProvider services = ModelFactory.BuildServices(configuration: new ConfigurationBuilder().AddInMemoryCollection(values).Build());
        EndToEndHarness harness = new(
            database,
            directory,
            services,
            values,
            storage,
            new FixedClock(new DateTimeOffset(2026, 11, 9, 12, 0, 0, TimeSpan.Zero)),
            keys,
            EndToEndData.Catalog());

        if (seed)
        {
            harness.Content = await EndToEndData.SeedAsync(database, harness.RawDir, harness.SourcesDir, ct);
        }

        return harness;
    }

    // ------------------------------------------------------------------ icerik degisiklikleri

    /// <summary>Birimin metnini ve content_hash degerini degistirir (sentetik birimler; Tanzil birimine dokunulmaz).</summary>
    public Task ChangeUnitAsync(string anchor, string metin, CancellationToken cancellationToken) =>
        Database.ExecuteAsync(
            "UPDATE icerik.unit SET metin = @metin, content_hash = @hash WHERE anchor = @anchor",
            cancellationToken,
            ("anchor", anchor),
            ("metin", metin),
            ("hash", EndToEndData.Hash(metin)));

    public void UnregisterSource(string slug) => File.Delete(Path.Combine(SourcesDir, slug + ".toml"));

    public void RegisterSource(string slug) => EndToEndData.RegisterSource(SourcesDir, slug);

    // ------------------------------------------------------------------ yayin kisayollari

    public Task<ReleaseResult> PublishAsync(
        BuildFlavor flavor,
        string[]? packs = null,
        string? version = null,
        bool stop = false,
        bool dryRun = false) =>
        Pipeline.PublishAsync(new PublishRequest(flavor, packs ?? [], dryRun, version, StopAtVerified: stop), TestContext.Current.CancellationToken);

    /// <summary>Komut satirini surec disinda calistirir (PublisherApp.RunAsync): ayri ana bilgisayar, ayri veritabani baglami, ayri depo istemcisi.</summary>
    public async Task<CliResult> RunCliAsync(params string[] args)
    {
        StringWriter output = new();
        StringWriter error = new();
        PublisherHostOptions host = new()
        {
            EnvironmentName = "Production",
            Catalog = Catalog,
            GitShortSha = _ => Task.FromResult("abc1234"),
            Clock = Clock,
            StoreFactory = () => S3PackStore.Create(Storage),
            Out = output,
            Error = error,
            SecretsPath = Path.Combine(Directory.Path, "secrets.json"),
        };
        foreach ((string key, string? value) in _values)
        {
            host.Configuration[key] = value;
        }

        int code = await PublisherApp.RunAsync(args, host, TestContext.Current.CancellationToken);
        return new CliResult(code, output.ToString(), error.ToString());
    }

    // ------------------------------------------------------------------ depo ve paket okuma

    public async Task<byte[]> ManifestBytesAsync(BuildFlavor flavor, CancellationToken cancellationToken) =>
        await Reader.GetAsync(StorageKeys.Manifest(flavor.ToLabel()), cancellationToken)
            ?? throw new InvalidOperationException($"Depoda {flavor.ToLabel()} manifesti yok.");

    public async Task<Manifest> ReadManifestAsync(BuildFlavor flavor, CancellationToken cancellationToken) =>
        ManifestJson.Read(await ManifestBytesAsync(flavor, cancellationToken));

    public async Task<List<string>> AllKeysAsync(CancellationToken cancellationToken)
    {
        List<string> keys = [];
        await foreach (string key in Reader.ListKeysAsync(string.Empty, cancellationToken))
        {
            keys.Add(key);
        }

        return keys;
    }

    public async Task<PackDb> OpenPackAsync(BuildFlavor flavor, string packId, CancellationToken cancellationToken)
    {
        Manifest manifest = await ReadManifestAsync(flavor, cancellationToken);
        ManifestPack pack = manifest.Packs.Single(p => string.Equals(p.PackId, packId, StringComparison.Ordinal));
        byte[] bytes = await Reader.GetAsync(StorageKeys.Pack(flavor.ToLabel(), pack.PackId, pack.Version), cancellationToken)
            ?? throw new InvalidOperationException($"Depoda paket yok: {packId} {pack.Version}.");
        return PackDb.FromBytes(bytes, Path.Combine(Directory.Path, "indirilen"));
    }

    // ------------------------------------------------------------------ yayin satiri ve kapi raporu

    public async Task<Release> GetReleaseAsync(BuildFlavor flavor, string surum, CancellationToken cancellationToken) =>
        await Releases.FindAsync(flavor, surum, cancellationToken)
            ?? throw new InvalidOperationException($"Yayin satiri yok: {flavor.ToLabel()} {surum}.");

    public async Task<int> CountReleasesAsync(CancellationToken cancellationToken) =>
        (int)await Database.ScalarAsync<long>("SELECT count(*) FROM icerik.release", cancellationToken);

    public static IReadOnlyList<GateRow> GateRows(Release row)
    {
        using JsonDocument document = JsonDocument.Parse(row.KapiRaporu);
        return
        [
            .. document.RootElement.GetProperty("rows").EnumerateArray().Select(r => new GateRow(
                r.GetProperty("kind").GetString()!,
                r.GetProperty("id").GetString()!,
                r.GetProperty("decision").GetString()!,
                r.GetProperty("rule").GetString(),
                r.GetProperty("reason").GetString()!,
                r.GetProperty("count").GetInt32())),
        ];
    }

    public static IReadOnlyList<(string? Rule, string Subject, string Reason)> Violations(Release row)
    {
        using JsonDocument document = JsonDocument.Parse(row.KapiRaporu);
        return
        [
            .. document.RootElement.GetProperty("violations").EnumerateArray().Select(v => (
                v.TryGetProperty("rule", out JsonElement rule) && rule.ValueKind == JsonValueKind.String ? rule.GetString() : null,
                v.GetProperty("subject").GetString()!,
                v.GetProperty("reason").GetString()!)),
        ];
    }

    public async ValueTask DisposeAsync()
    {
        await Context.DisposeAsync();
        _reader.Dispose();
        await _services.DisposeAsync();
        await Database.DisposeAsync();
        Directory.Dispose();
    }
}
