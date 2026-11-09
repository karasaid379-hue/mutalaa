using Microsoft.Extensions.Configuration;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Infrastructure.Storage;
using Npgsql;

namespace Mutalaa.Publisher;

/// <summary>
/// Testlerin ve ana programin komut katmanina enjekte ettigi dis bagimliliklar. Hepsi istege baglidir; verilmeyen uretim varsayilanina duser.
/// </summary>
public sealed class PublisherHostOptions
{
    /// <summary>Yapilandirmaya en son eklenen degerler (en yuksek oncelik). Gizli degerler testte sentetik uretilir.</summary>
    public IDictionary<string, string?> Configuration { get; } = new Dictionary<string, string?>(StringComparer.Ordinal);

    /// <summary>Ortam adi (varsayilan: DOTNET_ENVIRONMENT, yoksa Production). Kullanici sirlari yalniz Development'ta yuklenir.</summary>
    public string? EnvironmentName { get; set; }

    /// <summary>Depo; verilmezse StorageOptions'tan S3PackStore kurulur (ilk kullanimda).</summary>
    public Func<IPackStore>? StoreFactory { get; set; }

    public TimeProvider? Clock { get; set; }

    /// <summary>git kisa sha; verilmezse <see cref="DataVersions.ShortShaAsync"/>.</summary>
    public Func<CancellationToken, Task<string>>? GitShortSha { get; set; }

    /// <summary>keys generate'in yazacagi secrets.json yolu; verilmezse UserSecretsId'den cozulur.</summary>
    public string? SecretsPath { get; set; }

    /// <summary>Paket katalogu; verilmezse <see cref="PackCatalog.Default"/> (testler sentetik katalog verir).</summary>
    public PackCatalog? Catalog { get; set; }

    public TextWriter? Out { get; set; }

    public TextWriter? Error { get; set; }
}

/// <summary>
/// Komut katmaninin ortak durumu: yapilandirma (sirlar yalniz buradan), depo, sinif tabanli yayin deposu ve cikti yazicilari. Komutlar ve
/// <see cref="Pipeline.ReleasePipeline"/> bunu kurucuda alir. Gizli degerler (baglanti dizesi, Storage:SecretKey, imza tohumu) hicbir
/// ciktiya yazilmaz; <see cref="Redact"/> hata iletilerinden bilinen sirlari siler.
/// </summary>
public sealed class PublisherContext : IAsyncDisposable
{
    private readonly PublisherHostOptions _host;
    private IPackStore? _store;

    public PublisherContext(IConfiguration configuration, ReleaseRepository releases, PublisherHostOptions? host = null)
    {
        ArgumentNullException.ThrowIfNull(configuration);
        ArgumentNullException.ThrowIfNull(releases);

        _host = host ?? new PublisherHostOptions();
        Configuration = configuration;
        Releases = releases;
        Options = PublisherOptions.FromConfiguration(configuration);
        Storage = StorageOptions.FromConfiguration(configuration);
        Clock = _host.Clock ?? TimeProvider.System;
        Out = _host.Out ?? Console.Out;
        Error = _host.Error ?? Console.Error;
    }

    public IConfiguration Configuration { get; }

    public ReleaseRepository Releases { get; }

    public PublisherOptions Options { get; }

    public StorageOptions Storage { get; }

    public TimeProvider Clock { get; }

    public TextWriter Out { get; }

    public TextWriter Error { get; }

    public PackCatalog Catalog => _host.Catalog ?? PackCatalog.Default;

    /// <summary>ConnectionStrings:Editorial; yoksa kullaniciya anlatilabilir hata (exit 1). Deger hicbir yere yazilmaz.</summary>
    public string ConnectionString
    {
        get
        {
            string? value = Configuration.GetConnectionString(DependencyInjection.ConnectionName);
            return string.IsNullOrWhiteSpace(value)
                ? throw new PublisherException(ExitCodes.Other, $"Baglanti dizesi yok: ConnectionStrings:{DependencyInjection.ConnectionName} (dotnet user-secrets ile verilir).")
                : value;
        }
    }

    /// <summary>Depo; ilk cagrida kurulur. Eksik Storage ayari exit 1 verir (anahtar adlari yazilir, deger yazilmaz).</summary>
    public IPackStore GetStore()
    {
        if (_store is not null)
        {
            return _store;
        }

        if (_host.StoreFactory is not null)
        {
            _store = _host.StoreFactory();
            return _store;
        }

        try
        {
            Storage.Validate();
        }
        catch (InvalidOperationException ex)
        {
            throw new PublisherException(ExitCodes.Other, ex.Message, ex);
        }

        _store = S3PackStore.Create(Storage);
        return _store;
    }

    /// <summary>Manifestteki adreslerin tabani; yoksa exit 1.</summary>
    public string PublicBaseUrl =>
        string.IsNullOrWhiteSpace(Storage.PublicBaseUrl)
            ? throw new PublisherException(ExitCodes.Other, "Storage:PublicBaseUrl yok (manifest adresleri icin gerekli).")
            : Storage.PublicBaseUrl;

    /// <summary>Signing:{flavor}:PrivateKey (32 bayt tohumun base64'u) ve Kid; yoksa ya da gecersizse exit 1. Tohum iletiye girmez.</summary>
    public SigningKey GetSigningKey(BuildFlavor flavor)
    {
        string label = flavor.ToLabel();
        string? seed = Configuration[$"Signing:{label}:PrivateKey"];
        string? kid = Configuration[$"Signing:{label}:Kid"];
        if (string.IsNullOrWhiteSpace(seed) || string.IsNullOrWhiteSpace(kid))
        {
            throw new PublisherException(
                ExitCodes.Other,
                $"Imza anahtari yok: Signing:{label}:PrivateKey ve Signing:{label}:Kid verilmeli (keys generate --flavor {label}).");
        }

        try
        {
            return SigningKey.FromSeedBase64(seed, kid);
        }
        catch (ArgumentException)
        {
            throw new PublisherException(ExitCodes.Other, $"Signing:{label}:PrivateKey gecerli bir 32 baytlik base64 tohum degil.");
        }
    }

    /// <summary>
    /// verify icin acik anahtar: once <paramref name="overrideBase64"/>, sonra Signing:{flavor}:PublicKey, sonra ozel anahtardan turetilen.
    /// Hicbiri yoksa exit 1. Gecersiz base64 ya da uzunluk exit 1.
    /// </summary>
    public byte[] GetPublicKey(BuildFlavor flavor, string? overrideBase64)
    {
        string label = flavor.ToLabel();
        string? encoded = string.IsNullOrWhiteSpace(overrideBase64) ? Configuration[$"Signing:{label}:PublicKey"] : overrideBase64;
        if (!string.IsNullOrWhiteSpace(encoded))
        {
            if (!Base64Strict.TryDecode(encoded, out byte[] key) || key.Length != SigningKey.PublicKeyLength)
            {
                throw new PublisherException(ExitCodes.Other, "Acik anahtar gecerli bir 32 baytlik base64 degil.");
            }

            return key;
        }

        return GetSigningKey(flavor).GetPublicKey();
    }

    /// <summary>YYYY.MM.DD-{git kisa sha} (data_version).</summary>
    public Task<string> DataVersionAsync(CancellationToken cancellationToken) =>
        DataVersions.CurrentAsync(Clock, _host.GitShortSha, cancellationToken);

    public string? SecretsPathOverride => _host.SecretsPath;

    /// <summary>Hata iletilerinden bilinen sirlari (baglanti dizesi parolasi, SecretKey, AccessKey, imza tohumlari) siler.</summary>
    public string Redact(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        string result = text;
        foreach (string secret in Secrets())
        {
            result = result.Replace(secret, "***", StringComparison.Ordinal);
        }

        return result;
    }

    public async ValueTask DisposeAsync()
    {
        IPackStore? store = _store;
        _store = null;
        switch (store)
        {
            case IAsyncDisposable asyncDisposable:
                await asyncDisposable.DisposeAsync();
                break;
            case IDisposable disposable:
                disposable.Dispose();
                break;
        }
    }

    private List<string> Secrets()
    {
        List<string> secrets = [];
        Add(secrets, Storage.SecretKey);
        Add(secrets, Storage.AccessKey);

        string? connection = Configuration.GetConnectionString(DependencyInjection.ConnectionName);
        if (!string.IsNullOrWhiteSpace(connection))
        {
            try
            {
                Add(secrets, new NpgsqlConnectionStringBuilder(connection).Password);
            }
            catch (ArgumentException)
            {
                // Bicimi bozuk baglanti dizesi: bastan sona sir sayilir.
                Add(secrets, connection);
            }
        }

        foreach (IConfigurationSection flavor in Configuration.GetSection("Signing").GetChildren())
        {
            Add(secrets, flavor["PrivateKey"]);
        }

        // En uzun sir once: bir sir digerinin parcasi olsa da tam eslesme silinir.
        secrets.Sort((a, b) => b.Length.CompareTo(a.Length));
        return secrets;
    }

    private static void Add(List<string> secrets, string? value)
    {
        if (!string.IsNullOrEmpty(value) && value.Length >= 8 && !secrets.Contains(value, StringComparer.Ordinal))
        {
            secrets.Add(value);
        }
    }
}
