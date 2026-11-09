using System.Text.Json;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Manifests;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>
/// packages/content-schema/test/fixtures/imza/ dosyalari ayni girdiden yeniden uretilir ve bayt bayt karsilastirilir
/// (Ed25519 belirlenimcidir). Bilincli guncelleme: MUTALAA_UPDATE_FIXTURES=1 (dosyalar yeniden yazilir ve test BILEREK
/// kirmizi biter; CI ortaminda reddedilir). Fikstur anahtari RFC 8032 7.1 TEST 1'dir: herkese acik, gizli degil.
/// </summary>
public class FixtureTests
{
    [Fact]
    public void The_fixture_files_match_the_regenerated_bytes()
    {
        (string Name, byte[] Expected)[] files =
        [
            (ImzaFixture.PublicKeyFileName, ImzaFixture.PublicKeyFile()),
            (ImzaFixture.SignedManifestFileName, ImzaFixture.SignedManifest()),
        ];

        if (ImzaFixture.UpdateRequested())
        {
            foreach ((string name, byte[] bytes) in files)
            {
                string path = ImzaFixture.RepoPath(name);
                Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                File.WriteAllBytes(path, bytes);
            }

            Assert.Fail($"Fikstur dosyalari yazildi; bu test guncelleme kipinde bilerek kirmizi biter. {ImzaFixture.UpdateVariableName} olmadan yeniden calistirin ve farki gozden gecirin.");
        }

        foreach ((string name, byte[] expected) in files)
        {
            Assert.True(
                expected.AsSpan().SequenceEqual(ImzaFixture.ReadOutput(name)),
                $"{name} yeniden uretilen baytlarla ayni degil. Bilerek degistirdiyseniz {ImzaFixture.UpdateVariableName}=1 ile yeniden yazin.");
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_regenerated_bytes_are_the_same_in_every_culture(bool turkish)
    {
        byte[]? signed = null;
        byte[]? publicKey = null;

        CultureScope.For(turkish, () =>
        {
            signed = ImzaFixture.SignedManifest();
            publicKey = ImzaFixture.PublicKeyFile();
        });

        Assert.Equal(ImzaFixture.ReadOutput(ImzaFixture.SignedManifestFileName), signed);
        Assert.Equal(ImzaFixture.ReadOutput(ImzaFixture.PublicKeyFileName), publicKey);
    }

    [Fact]
    public void The_signed_fixture_verifies_with_the_fixture_public_key_file()
    {
        using JsonDocument keyFile = JsonDocument.Parse(ImzaFixture.ReadOutput(ImzaFixture.PublicKeyFileName));
        JsonElement root = keyFile.RootElement;
        Assert.True(Base64Strict.TryDecode(root.GetProperty("public_key_base64").GetString(), out byte[] publicKey));
        Assert.Equal(root.GetProperty("public_key_hex").GetString(), Base64Strict.ToHex(publicKey));
        Assert.Equal(ImzaFixture.PublicKeyHex, Base64Strict.ToHex(publicKey));

        ManifestVerification result = ManifestVerifier.Verify(
            ImzaFixture.ReadOutput(ImzaFixture.SignedManifestFileName),
            publicKey,
            root.GetProperty("kid").GetString());

        Assert.True(result.IsValid);
    }

    [Fact]
    public void The_public_key_file_holds_only_public_material()
    {
        using JsonDocument keyFile = JsonDocument.Parse(ImzaFixture.ReadOutput(ImzaFixture.PublicKeyFileName));

        Assert.Equal(
            ["kid", "alg", "public_key_base64", "public_key_hex", "kaynak"],
            keyFile.RootElement.EnumerateObject().Select(p => p.Name).ToArray());
        string text = System.Text.Encoding.UTF8.GetString(ImzaFixture.ReadOutput(ImzaFixture.PublicKeyFileName));
        Assert.DoesNotContain(ImzaFixture.SeedHex, text, StringComparison.OrdinalIgnoreCase);
        Assert.StartsWith("test-", keyFile.RootElement.GetProperty("kid").GetString(), StringComparison.Ordinal);
    }

    [Fact]
    public void The_signed_fixture_conforms_to_the_schema_and_uses_the_fixed_inputs()
    {
        byte[] schema = File.ReadAllBytes(Path.Combine(AppContext.BaseDirectory, "data", "manifest.schema.json"));
        ManifestSchemaValidator validator = new(System.Text.Encoding.UTF8.GetString(schema));
        byte[] signed = ImzaFixture.ReadOutput(ImzaFixture.SignedManifestFileName);

        Assert.True(validator.Validate(signed, ImzaFixture.PublicBaseUrl).IsValid);
        Manifest manifest = ManifestJson.Read(signed);
        Assert.Equal("dev", manifest.Flavor);
        Assert.Equal("2026.11.0", manifest.Release);
        Assert.Equal(ImzaFixture.GeneratedAt, manifest.GeneratedAt);
        Assert.Equal(["core", "test-kucuk"], manifest.Packs.Select(p => p.PackId).ToArray());
    }
}
