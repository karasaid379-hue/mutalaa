using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Mutalaa.Infrastructure.Manifests;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>
/// packages/content-schema/test/fixtures/imza/ dosyalarinin tek uretim yeri (K-45 madde 5).
/// Anahtar RFC 8032 7.1 TEST 1 (herkese acik test vektoru; gizli degil, kid "test-" ile baslar).
/// Girdiler sentetiktir: sha256 degerleri asagidaki sentetik bayt dizilerinin SHA-256'sidir, size_bytes dizinin uzunlugudur.
/// Dosyalar cikti klasorunde data\imza\ altindadir; yeniden yazma yalnizca MUTALAA_UPDATE_FIXTURES=1 ile (CI'da reddedilir).
/// </summary>
internal static class ImzaFixture
{
    public const string SeedHex = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60";
    public const string PublicKeyHex = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a";
    public const string EmptyMessageSignatureHex =
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b";

    public const string Kid = "test-2026-1";
    public const string PublicBaseUrl = "http://192.168.1.50:8333/mutalaa";
    public const string Release = "2026.11.0";

    public const string PublicKeyFileName = "test-acik-anahtar.json";
    public const string SignedManifestFileName = "ornek-manifest.imzali.json";

    private const string RelativeDirectory = "packages/content-schema/test/fixtures/imza";
    private const string UpdateVariable = "MUTALAA_UPDATE_FIXTURES";

    public static readonly DateTimeOffset GeneratedAt = new(2026, 11, 9, 12, 0, 0, TimeSpan.Zero);

    public static SigningKey Key() => new(Convert.FromHexString(SeedHex), Kid);

    public static byte[] PublicKey() => Convert.FromHexString(PublicKeyHex);

    public static Manifest Manifest() => ManifestBuilder.Build(
        "dev",
        Release,
        GeneratedAt,
        PublicBaseUrl,
        [Input("test-kucuk", ["core"], "Küçük deneme paketi", bundled: null), Input("core", [], "Çekirdek (sentetik)", bundled: true)]);

    /// <summary>Imzasiz manifest baytlari.</summary>
    public static byte[] UnsignedManifest() => ManifestJson.Write(Manifest());

    /// <summary>Imzali ornek manifest: dosyaya yazilan baytlar.</summary>
    public static byte[] SignedManifest() => ManifestSigner.Sign(UnsignedManifest(), Key());

    /// <summary>Acik anahtar dosyasi: yalniz acik malzeme.</summary>
    public static byte[] PublicKeyFile()
    {
        byte[] publicKey = Key().GetPublicKey();
        using MemoryStream stream = new();
        JsonWriterOptions options = new()
        {
            Indented = true,
            IndentSize = 2,
            NewLine = "\n",
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };
        using (Utf8JsonWriter writer = new(stream, options))
        {
            writer.WriteStartObject();
            writer.WriteString("kid", Kid);
            writer.WriteString("alg", ManifestSigner.Algorithm);
            writer.WriteString("public_key_base64", Base64Strict.Encode(publicKey));
            writer.WriteString("public_key_hex", Base64Strict.ToHex(publicKey));
            writer.WriteString("kaynak", "RFC 8032 section 7.1 TEST 1 (herkese acik test vektoru)");
            writer.WriteEndObject();
        }

        stream.WriteByte((byte)'\n');
        return stream.ToArray();
    }

    /// <summary>Cikti klasorundeki fikstur dosyasinin baytlari.</summary>
    public static byte[] ReadOutput(string fileName)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "imza", fileName);
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("Fikstur cikti klasorune kopyalanmamis: " + path);
        }

        return File.ReadAllBytes(path);
    }

    /// <summary>Depodaki fikstur dosyasinin yolu (yazma icin).</summary>
    public static string RepoPath(string fileName) =>
        Mutalaa.Api.Tests.Support.RepoFiles.PathOf(RelativeDirectory + "/" + fileName);

    /// <summary>MUTALAA_UPDATE_FIXTURES=1 mi; CI ortaminda istek reddedilir (Assert.Fail).</summary>
    public static bool UpdateRequested()
    {
        if (Environment.GetEnvironmentVariable(UpdateVariable) != "1")
        {
            return false;
        }

        if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("CI")))
        {
            Assert.Fail($"{UpdateVariable}=1 CI ortaminda reddedildi: fikstur yalniz yerelde ve bilincli guncellenir.");
        }

        return true;
    }

    public static string UpdateVariableName => UpdateVariable;

    private static ManifestPackInput Input(string packId, string[] dependsOn, string title, bool? bundled)
    {
        byte[] synthetic = Encoding.UTF8.GetBytes($"sentetik-paket-girdisi:{packId}:{Release}");
        return new ManifestPackInput(
            packId,
            Release,
            Convert.ToHexStringLower(SHA256.HashData(synthetic)),
            synthetic.Length,
            "1.0.0",
            dependsOn,
            1,
            title,
            bundled);
    }
}
