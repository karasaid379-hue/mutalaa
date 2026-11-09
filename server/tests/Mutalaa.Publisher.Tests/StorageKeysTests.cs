using Microsoft.Extensions.Configuration;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>Anahtar duzeni (Backend API 10.5) ve depo ayarlari; Docker gerektirmez.</summary>
public class StorageKeysTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Keys_follow_the_documented_layout(bool turkish)
    {
        await StorageTestKit.RunAsync(turkish, () =>
        {
            Assert.Equal("packs/internal/core/2026.11.0/core-2026.11.0.db", StorageKeys.Pack("internal", "core", "2026.11.0"));
            Assert.Equal("public/manifest.json", StorageKeys.Manifest("public"));
            Assert.Equal("dev/manifests/2026.11.3.json", StorageKeys.ManifestHistory("dev", "2026.11.3"));
            return Task.CompletedTask;
        });
    }

    [Fact]
    public void Cache_control_and_content_types_match_the_document()
    {
        Assert.Equal("public, max-age=31536000, immutable", StorageKeys.PackCacheControl);
        Assert.Equal("no-cache", StorageKeys.ManifestCacheControl);
        Assert.Equal("application/vnd.sqlite3", StorageKeys.PackContentType);
        Assert.Equal("application/json", StorageKeys.ManifestContentType);
        Assert.Equal("sha256", StorageKeys.Sha256MetadataName);
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData("a/b")]
    [InlineData("a\\b")]
    [InlineData("..")]
    [InlineData("a..b")]
    public void Key_segments_reject_empty_separators_and_dot_dot(string segment)
    {
        Assert.ThrowsAny<ArgumentException>(() => StorageKeys.Pack(segment, "core", "1"));
        Assert.ThrowsAny<ArgumentException>(() => StorageKeys.Pack("dev", segment, "1"));
        Assert.ThrowsAny<ArgumentException>(() => StorageKeys.Pack("dev", "core", segment));
        Assert.ThrowsAny<ArgumentException>(() => StorageKeys.Manifest(segment));
        Assert.ThrowsAny<ArgumentException>(() => StorageKeys.ManifestHistory("dev", segment));
    }

    [Fact]
    public void Options_to_string_redacts_secrets()
    {
        StorageOptions options = new()
        {
            ServiceUrl = "http://localhost:8333",
            AccessKey = "test-access-value",
            SecretKey = "test-secret-value",
            Bucket = "mutalaa",
            PublicBaseUrl = "http://localhost:8333/mutalaa",
        };

        string text = options.ToString();

        Assert.DoesNotContain("test-access-value", text, StringComparison.Ordinal);
        Assert.DoesNotContain("test-secret-value", text, StringComparison.Ordinal);
        Assert.Contains("http://localhost:8333", text, StringComparison.Ordinal);
    }

    [Fact]
    public void Options_are_read_from_the_storage_section()
    {
        IConfiguration configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Storage:ServiceUrl"] = "http://localhost:8333",
                ["Storage:AccessKey"] = "test-access",
                ["Storage:SecretKey"] = "test-secret",
                ["Storage:Bucket"] = "mutalaa",
                ["Storage:PublicBaseUrl"] = "http://localhost:8333/mutalaa",
            })
            .Build();

        StorageOptions options = StorageOptions.FromConfiguration(configuration);

        Assert.Equal("http://localhost:8333", options.ServiceUrl);
        Assert.Equal("mutalaa", options.Bucket);
        Assert.Equal("http://localhost:8333/mutalaa", options.PublicBaseUrl);
        options.Validate();
    }

    [Fact]
    public void Validate_names_missing_keys_without_values()
    {
        StorageOptions options = new() { ServiceUrl = "http://localhost:8333", SecretKey = "test-secret-value" };

        InvalidOperationException ex = Assert.Throws<InvalidOperationException>(options.Validate);

        Assert.Contains("Storage:AccessKey", ex.Message, StringComparison.Ordinal);
        Assert.Contains("Storage:Bucket", ex.Message, StringComparison.Ordinal);
        Assert.DoesNotContain("Storage:SecretKey", ex.Message, StringComparison.Ordinal);
        Assert.DoesNotContain("test-secret-value", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Validate_rejects_a_relative_service_url()
    {
        StorageOptions options = new() { ServiceUrl = "localhost:8333", AccessKey = "a", SecretKey = "b", Bucket = "c" };

        Assert.Throws<InvalidOperationException>(options.Validate);
    }
}
