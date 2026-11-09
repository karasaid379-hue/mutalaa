using System.Globalization;
using System.Text.Json;
using Amazon.S3;
using Amazon.S3.Model;
using Docker.DotNet.Models;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using Mutalaa.Infrastructure.Storage;

[assembly: AssemblyFixture(typeof(Mutalaa.Publisher.Tests.Support.SeaweedFixture))]

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Derleme duzeyinde tek SeaweedFS kabi (A13.1 sinamasi; imaj compose ile ayni 4.48). Kap TEMBELDIR (PostgresFixture ornegi):
/// kurucu ve InitializeAsync Docker'a dokunmaz, kap ilk <see cref="GetEndpointAsync"/> cagrisinda baslar; Docker kapaliyken yalniz
/// Docker'li siniflar duser. s3.json test tarafindan uretilir: her kosuda rastgele kimlik (Guid tabanli) ve anonim yalniz Read.
/// infra/local/s3.json OKUNMAZ. Host portu rastgele ve yalniz 127.0.0.1'e yayinlanir.
/// </summary>
public sealed class SeaweedFixture : IAsyncLifetime
{
    public const string Image = "chrislusf/seaweedfs:4.48";

    /// <summary>Test kovasi (kap basina bir kez olusur).</summary>
    public const string Bucket = "mutalaa-test";

    private const int S3Port = 8333;
    private const string ConfigPath = "/etc/seaweedfs/s3.json";

    private readonly SemaphoreSlim _gate = new(1, 1);
    private IContainer? _container;
    private SeaweedEndpoint? _endpoint;

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

    /// <summary>Kapi gerekirse baslatir; adres, kimlik ve kovayi dondurur.</summary>
    public async Task<SeaweedEndpoint> GetEndpointAsync(CancellationToken cancellationToken)
    {
        if (_endpoint is not null)
        {
            return _endpoint;
        }

        await _gate.WaitAsync(cancellationToken);
        try
        {
            _endpoint ??= await StartAsync(cancellationToken);
            return _endpoint;
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Urun ayarlariyla ayni StorageOptions (kimlik yanlis verilebilir).</summary>
    public async Task<StorageOptions> OptionsAsync(CancellationToken cancellationToken)
    {
        SeaweedEndpoint endpoint = await GetEndpointAsync(cancellationToken);
        return endpoint.ToOptions();
    }

    private async Task<SeaweedEndpoint> StartAsync(CancellationToken cancellationToken)
    {
        string accessKey = "ak" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture);
        string secretKey = Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture) + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture);

        // infra/local/s3.example.json bicimi: Admin, Read, Write, List, Tagging; ikinci kimlik anonymous yalniz Read.
        byte[] config = JsonSerializer.SerializeToUtf8Bytes(new
        {
            identities = new object[]
            {
                new
                {
                    name = "mutalaa-test",
                    credentials = new[] { new { accessKey, secretKey } },
                    actions = new[] { "Admin", "Read", "Write", "List", "Tagging" },
                },
                new { name = "anonymous", actions = new[] { "Read" } },
            },
        });

        // Parametresiz kurucu [Obsolete]; imaj adi verilir. Komut compose ile ayni, bir fark: -volume.max acik verilir. Imajin giris betigi
        // -volume.max=0 ekler (birim sayisi = bos disk / 1 GB) ve her yeni kova 7 birim acar; her test ayri kova actigi icin dar diskli
        // CI runner'inda birkac kovadan sonra PUT InternalError doner. Acik deger bu hesabi kapatir (512 birim ~ 70 kova).
        IContainer container = new ContainerBuilder(Image)
            .WithCommand("server", "-dir=/data", "-volume.max=512", "-s3", $"-s3.port={S3Port}", $"-s3.config={ConfigPath}")
            .WithResourceMapping(config, ConfigPath)
            .WithPortBinding(S3Port, assignRandomHostPort: true)
            .WithCreateParameterModifier(BindPortsToLoopback)
            .WithCreateParameterModifier(LimitDataDisk)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilHttpRequestIsSucceeded(request => request
                .ForPort(S3Port)
                .ForPath("/")
                .ForStatusCodeMatching(code => (int)code < 500)))
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
        SeaweedEndpoint endpoint = new(
            $"http://127.0.0.1:{container.GetMappedPublicPort(S3Port).ToString(CultureInfo.InvariantCulture)}",
            accessKey,
            secretKey,
            Bucket);
        await CreateBucketAsync(endpoint, cancellationToken);
        return endpoint;
    }

    // Kova hazir olana kadar yeniden dener (S3 portu acilsa da kimlik yuklemesi gecikebilir).
    private static async Task CreateBucketAsync(SeaweedEndpoint endpoint, CancellationToken cancellationToken)
    {
        using AmazonS3Client client = S3PackStore.CreateClient(endpoint.ToOptions());
        Exception? last = null;
        for (int attempt = 0; attempt < 60; attempt++)
        {
            try
            {
                await client.PutBucketAsync(new PutBucketRequest { BucketName = endpoint.Bucket }, cancellationToken);
                return;
            }
            catch (Exception ex) when (ex is Amazon.Runtime.AmazonServiceException or Amazon.Runtime.AmazonClientException)
            {
                last = ex;
                await Task.Delay(TimeSpan.FromSeconds(1), cancellationToken);
            }
        }

        throw new InvalidOperationException("SeaweedFS kovasi olusturulamadi.", last);
    }

    /// <summary>/data 4 GB'lik bellek ustu diske baglanir: CI runner'inin dar diski her makinede ayni olusur.</summary>
    private static void LimitDataDisk(CreateContainerParameters parameters)
    {
        parameters.HostConfig ??= new HostConfig();
        parameters.HostConfig.Tmpfs = new Dictionary<string, string> { ["/data"] = "rw,size=4g" };
    }

    /// <summary>Testcontainers'in urettigi butun port yayinlarini (rastgele ana makine portu korunur) 127.0.0.1'e baglar.</summary>
    private static void BindPortsToLoopback(CreateContainerParameters parameters)
    {
        if (parameters.HostConfig?.PortBindings is null)
        {
            return;
        }

        foreach (IList<PortBinding> bindings in parameters.HostConfig.PortBindings.Values)
        {
            foreach (PortBinding binding in bindings)
            {
                binding.HostIP = "127.0.0.1";
            }
        }
    }
}

/// <summary>Kapin adresi ve bu kosuya ozgu rastgele kimlik bilgisi (sohbete ve raporlara yazilmaz).</summary>
public sealed record SeaweedEndpoint(string ServiceUrl, string AccessKey, string SecretKey, string Bucket)
{
    public StorageOptions ToOptions() => new()
    {
        ServiceUrl = ServiceUrl,
        AccessKey = AccessKey,
        SecretKey = SecretKey,
        Bucket = Bucket,
        PublicBaseUrl = $"{ServiceUrl}/{Bucket}",
    };

    // Kayit ToString'i gizli degerleri yazmasin.
    public override string ToString() => $"SeaweedEndpoint {{ ServiceUrl = {ServiceUrl}, Bucket = {Bucket} }}";
}
