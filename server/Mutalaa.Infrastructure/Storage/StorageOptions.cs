using Microsoft.Extensions.Configuration;

namespace Mutalaa.Infrastructure.Storage;

/// <summary>
/// S3 uyumlu depo ayarlari (Storage: bolumu; Backend API 10.1). Gizli degerler (AccessKey, SecretKey) dotnet user-secrets ya da
/// ortam degiskeniyle verilir; ToString onlari yazmaz, boylece gunluge ve hata iletisine sizmaz.
/// </summary>
public sealed class StorageOptions
{
    /// <summary>Yapilandirma bolumu adi.</summary>
    public const string SectionName = "Storage";

    /// <summary>Depo adresi (ServiceURL), ornek http://localhost:8333.</summary>
    public string ServiceUrl { get; init; } = string.Empty;

    public string AccessKey { get; init; } = string.Empty;

    public string SecretKey { get; init; } = string.Empty;

    public string Bucket { get; init; } = string.Empty;

    /// <summary>Manifestteki mutlak adreslerin tabani: {PublicBaseUrl}/packs/... (sonda egik cizgi olmaz).</summary>
    public string PublicBaseUrl { get; init; } = string.Empty;

    /// <summary>Storage: bolumunu okur (Microsoft.Extensions.Configuration.Binder gerekmez).</summary>
    public static StorageOptions FromConfiguration(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        IConfigurationSection section = configuration.GetSection(SectionName);
        return new StorageOptions
        {
            ServiceUrl = section["ServiceUrl"] ?? string.Empty,
            AccessKey = section["AccessKey"] ?? string.Empty,
            SecretKey = section["SecretKey"] ?? string.Empty,
            Bucket = section["Bucket"] ?? string.Empty,
            PublicBaseUrl = section["PublicBaseUrl"] ?? string.Empty,
        };
    }

    /// <summary>Eksik zorunlu ayari bildirir; deger yazmaz, yalniz anahtar adini.</summary>
    public void Validate()
    {
        List<string> missing = [];
        if (string.IsNullOrWhiteSpace(ServiceUrl))
        {
            missing.Add(nameof(ServiceUrl));
        }
        else if (!Uri.TryCreate(ServiceUrl, UriKind.Absolute, out Uri? uri)
            || (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
        {
            throw new InvalidOperationException($"{SectionName}:{nameof(ServiceUrl)} mutlak bir http ya da https adresi olmali.");
        }

        if (string.IsNullOrWhiteSpace(AccessKey))
        {
            missing.Add(nameof(AccessKey));
        }

        if (string.IsNullOrWhiteSpace(SecretKey))
        {
            missing.Add(nameof(SecretKey));
        }

        if (string.IsNullOrWhiteSpace(Bucket))
        {
            missing.Add(nameof(Bucket));
        }

        if (missing.Count > 0)
        {
            throw new InvalidOperationException($"Eksik ayar: {string.Join(", ", missing.Select(m => $"{SectionName}:{m}"))}.");
        }
    }

    /// <summary>Gizli degerler maskelenir.</summary>
    public override string ToString() =>
        $"StorageOptions {{ ServiceUrl = {ServiceUrl}, AccessKey = ***, SecretKey = ***, Bucket = {Bucket}, PublicBaseUrl = {PublicBaseUrl} }}";
}
