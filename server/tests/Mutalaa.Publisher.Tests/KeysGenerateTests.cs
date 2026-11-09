using System.Text.Json;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>keys generate (Docker'siz): gecici secrets dosyasi yolu enjekte edilir; tohum ciktida yok, --force olmadan ustune yazilmaz.</summary>
public class KeysGenerateTests : IDisposable
{
    private readonly PackTestData.TempDir _dir = new();

    private string SecretsPath => Path.Combine(_dir.Path, "user-secrets", "secrets.json");

    public void Dispose() => _dir.Dispose();

    private async Task<(int Code, string Out, string Error)> RunAsync(params string[] args)
    {
        StringWriter output = new();
        StringWriter error = new();
        PublisherHostOptions host = new()
        {
            EnvironmentName = "Production",
            Out = output,
            Error = error,
            SecretsPath = SecretsPath,
            Clock = new FixedClock(new DateTimeOffset(2026, 11, 9, 12, 0, 0, TimeSpan.Zero)),
        };
        int code = await PublisherApp.RunAsync(args, host, TestContext.Current.CancellationToken);
        return (code, output.ToString(), error.ToString());
    }

    private JsonElement ReadSecrets()
    {
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(SecretsPath));
        return document.RootElement.Clone();
    }

    [Fact]
    public async Task Generates_a_key_pair_and_prints_only_the_public_key_and_kid()
    {
        (int code, string output, string error) = await RunAsync("keys", "generate", "--flavor", "dev");

        Assert.Equal(0, code);
        JsonElement secrets = ReadSecrets();
        string seed = secrets.GetProperty("Signing:dev:PrivateKey").GetString()!;
        string kid = secrets.GetProperty("Signing:dev:Kid").GetString()!;
        string publicKey = secrets.GetProperty("Signing:dev:PublicKey").GetString()!;

        Assert.Equal("dev-2026-1", kid);
        Assert.Contains("kid: dev-2026-1", output, StringComparison.Ordinal);
        Assert.Contains(publicKey, output, StringComparison.Ordinal);
        // Tohum hicbir ciktida yok (ne stdout ne stderr).
        Assert.DoesNotContain(seed, output, StringComparison.Ordinal);
        Assert.DoesNotContain(seed, error, StringComparison.Ordinal);
        // Acik anahtar tohumdan turetilen ile ayni.
        Assert.Equal(publicKey, Base64Strict.Encode(SigningKey.FromSeedBase64(seed, kid).GetPublicKey()));
        Assert.Equal(32, Convert.FromBase64String(seed).Length);
    }

    [Fact]
    public async Task Does_not_overwrite_an_existing_key_without_force()
    {
        await RunAsync("keys", "generate", "--flavor", "dev");
        string before = File.ReadAllText(SecretsPath);

        (int code, string output, string error) = await RunAsync("keys", "generate", "--flavor", "dev");

        Assert.Equal(1, code);
        Assert.Contains("--force", error, StringComparison.Ordinal);
        Assert.DoesNotContain("acik anahtar", output, StringComparison.Ordinal);
        Assert.Equal(before, File.ReadAllText(SecretsPath));
    }

    [Fact]
    public async Task Force_replaces_the_key_and_increments_the_kid_number()
    {
        await RunAsync("keys", "generate", "--flavor", "dev");
        string firstSeed = ReadSecrets().GetProperty("Signing:dev:PrivateKey").GetString()!;

        (int code, string output, string error) = await RunAsync("keys", "generate", "--flavor", "dev", "--force");

        Assert.Equal(0, code);
        JsonElement secrets = ReadSecrets();
        string secondSeed = secrets.GetProperty("Signing:dev:PrivateKey").GetString()!;
        Assert.NotEqual(firstSeed, secondSeed);
        Assert.Equal("dev-2026-2", secrets.GetProperty("Signing:dev:Kid").GetString());
        Assert.DoesNotContain(secondSeed, output + error, StringComparison.Ordinal);
        Assert.DoesNotContain(firstSeed, output + error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Keeps_other_secrets_and_other_flavors()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(SecretsPath)!);
        await File.WriteAllTextAsync(SecretsPath, """{"ConnectionStrings:Editorial":"Host=h;Password=baska-sir-123","Signing:internal:PrivateKey":"mevcut-ic"}""", TestContext.Current.CancellationToken);

        (int code, _, _) = await RunAsync("keys", "generate", "--flavor", "public");

        Assert.Equal(0, code);
        JsonElement secrets = ReadSecrets();
        Assert.Equal("Host=h;Password=baska-sir-123", secrets.GetProperty("ConnectionStrings:Editorial").GetString());
        Assert.Equal("mevcut-ic", secrets.GetProperty("Signing:internal:PrivateKey").GetString());
        Assert.Equal("public-2026-1", secrets.GetProperty("Signing:public:Kid").GetString());
    }

    [Fact]
    public async Task Refuses_a_key_that_exists_in_nested_form()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(SecretsPath)!);
        const string Nested = """{"Signing":{"dev":{"PrivateKey":"elle-yazilmis"}}}""";
        await File.WriteAllTextAsync(SecretsPath, Nested, TestContext.Current.CancellationToken);

        (int code, _, string error) = await RunAsync("keys", "generate", "--flavor", "dev");

        Assert.Equal(1, code);
        Assert.Contains("--force", error, StringComparison.Ordinal);
        Assert.Equal(Nested, File.ReadAllText(SecretsPath));
    }

    [Fact]
    public async Task Leaves_an_invalid_secrets_file_untouched()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(SecretsPath)!);
        await File.WriteAllTextAsync(SecretsPath, "{ bozuk json", TestContext.Current.CancellationToken);

        (int code, _, string error) = await RunAsync("keys", "generate", "--flavor", "dev");

        Assert.Equal(1, code);
        Assert.Contains("dokunulmadi", error, StringComparison.Ordinal);
        Assert.Equal("{ bozuk json", File.ReadAllText(SecretsPath));
    }

    [Fact]
    public async Task Written_file_is_utf8_without_bom_and_leaves_no_temp_file()
    {
        await RunAsync("keys", "generate", "--flavor", "internal");

        byte[] bytes = File.ReadAllBytes(SecretsPath);
        Assert.False(bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF);
        Assert.False(File.Exists(SecretsPath + ".tmp"));
    }
}
