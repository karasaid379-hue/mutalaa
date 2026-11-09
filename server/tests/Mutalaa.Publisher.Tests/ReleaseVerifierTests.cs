using Microsoft.Extensions.Configuration;
using System.Text;
using System.Text.Json.Nodes;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Commands;
using Mutalaa.Publisher.Pipeline;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// verify (Docker: yayin once PostgreSQL ve sahte depoyla uretilir; sonra yalniz depo okunur): imza, sema, paket, P-12, P-13, yetim nesne,
/// gomulu core ve cikis kodlari (3 dogrulama, 4 depo).
/// </summary>
public class ReleaseVerifierTests(PostgresFixture postgres)
{
    private static async Task<PublisherHarness> PublishedAsync(PostgresFixture postgres, BuildFlavor flavor = BuildFlavor.Dev, PackCatalog? catalog = null)
    {
        PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, catalog: catalog);
        ReleaseResult result = await harness.Pipeline.PublishAsync(new PublishRequest(flavor, []), TestContext.Current.CancellationToken);
        Assert.Equal(ExitCodes.Success, result.ExitCode);
        return harness;
    }

    private static async Task<IReadOnlyList<VerifyFinding>> VerifyAsync(PublisherHarness harness, BuildFlavor flavor = BuildFlavor.Dev, string? manifestPath = null, string? core = null, string? publicKey = null) =>
        await new ReleaseVerifier(harness.Context).RunAsync(new VerifyRequest(flavor, manifestPath, core, publicKey), TestContext.Current.CancellationToken);

    private static void ReplaceManifest(PublisherHarness harness, string flavor, Func<JsonObject, JsonObject> change)
    {
        JsonObject node = JsonNode.Parse(harness.Store.Peek(PublisherHarness.ManifestKey(flavor))!)!.AsObject();
        byte[] bytes = Encoding.UTF8.GetBytes(change(node).ToJsonString());
        harness.Store.Seed(PublisherHarness.ManifestKey(flavor), bytes, null);
    }

    [Fact]
    public async Task A_clean_release_verifies_with_exit_0_for_the_command()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);

        int code = await new VerifyCommand(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Equal(0, code);
        Assert.Contains("Dogrulama tamam", harness.Out.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_manifest_file_can_be_verified_with_an_explicit_public_key()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublishedAsync(postgres);
        string path = Path.Combine(harness.OutDir, "dev", "2026.11.0", "manifest.json");
        string publicKey = Base64Strict.Encode(harness.Keys[BuildFlavor.Dev].GetPublicKey());

        Assert.Empty(await VerifyAsync(harness, manifestPath: path, publicKey: publicKey));
        IReadOnlyList<VerifyFinding> wrong = await VerifyAsync(harness, manifestPath: path, publicKey: Base64Strict.Encode(harness.Keys[BuildFlavor.Internal].GetPublicKey()));
        Assert.Contains(wrong, f => f.Code == ManifestErrorCodes.SignatureInvalid);
        Assert.NotEmpty(await File.ReadAllBytesAsync(path, ct));
    }

    [Fact]
    public async Task A_tampered_manifest_exits_with_3()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        ReplaceManifest(harness, "dev", node =>
        {
            node["packs"]![0]!["size_bytes"] = 1;
            return node;
        });

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);
        int code = await new VerifyCommand(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Contains(findings, f => f.Code == ManifestErrorCodes.SignatureInvalid);
        Assert.Equal(3, code);
    }

    [Fact]
    public async Task An_unsigned_manifest_exits_with_3()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        ReplaceManifest(harness, "dev", node =>
        {
            node.Remove("signature");
            return node;
        });

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);
        int code = await new VerifyCommand(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Contains(findings, f => f.Code == ManifestErrorCodes.SignatureMissing);
        Assert.Equal(3, code);
    }

    [Theory]
    [InlineData("alg", "rsa")]
    [InlineData("kid", "baska-2026-9")]
    public async Task A_wrong_algorithm_or_unexpected_kid_is_a_finding(string field, string value)
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        ReplaceManifest(harness, "dev", node =>
        {
            node["signature"]![field] = value;
            return node;
        });

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        Assert.Contains(findings, f => f.Code is ManifestErrorCodes.SignatureAlgorithm or ManifestErrorCodes.SignatureKid);
    }

    [Fact]
    public async Task A_missing_manifest_is_a_finding_not_a_crash()
    {
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres);

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        Assert.Equal("manifest-yok", Assert.Single(findings).Code);
    }

    [Fact]
    public async Task A_corrupted_missing_or_wrong_sized_pack_is_reported()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        string corrupted = PublisherHarness.PackKey("dev", "test-kucuk", "2026.11.0");
        ManifestPack pack = harness.ReadStoredManifest("dev").Packs.Single(p => p.PackId == "test-kucuk");
        byte[] bytes = [.. harness.Store.Peek(corrupted)!];
        bytes[^1] ^= 0xFF;
        harness.Store.Seed(corrupted, bytes, pack.Sha256);
        harness.Store.Remove(PublisherHarness.PackKey("dev", "hadis-sentetik", "2026.11.0"));

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        Assert.Contains(findings, f => f.Code == "paket-sha256");
        Assert.Contains(findings, f => f.Code == "paket-yok");
    }

    [Fact]
    public async Task An_object_that_is_in_no_manifest_is_reported()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        harness.Store.Seed(PublisherHarness.PackKey("dev", "yetim", "2026.11.0"), [1, 2, 3], null);

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        VerifyFinding finding = Assert.Single(findings);
        Assert.Equal("nesne-manifestte-yok", finding.Code);
        Assert.Contains("yetim", finding.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Objects_of_an_older_release_in_the_manifest_history_are_not_orphans()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublishedAsync(postgres);
        await harness.ChangeUnitAsync(PublisherHarness.SyntheticAnchor, "Deneme paragrafi 2 duzeltildi", ct);
        await harness.Pipeline.PublishAsync(new PublishRequest(BuildFlavor.Dev, []), ct);

        // 2026.11.0 hadis-sentetik paketi guncel manifestte yok, ama manifest gecmisinde var.
        Assert.True(harness.Store.Contains(PublisherHarness.PackKey("dev", "hadis-sentetik", "2026.11.0")));
        Assert.Empty(await VerifyAsync(harness));
    }

    [Fact]
    public async Task A_missing_history_manifest_is_reported()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        harness.Store.Remove(PublisherHarness.HistoryKey("dev", "2026.11.0"));

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        Assert.Contains(findings, f => f.Code == "manifest-gecmisi-yok");
    }

    [Fact]
    public async Task Embedded_core_must_match_the_core_pack_in_the_manifest_or_its_history()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublishedAsync(postgres);
        string file = Path.Combine(harness.Directory.Path, "core.db");
        await File.WriteAllBytesAsync(file, [1, 2, 3], ct);

        // Katalogda core yok: gomulu core hicbir manifestle eslesemez.
        IReadOnlyList<VerifyFinding> noCore = await VerifyAsync(harness, core: file);
        IReadOnlyList<VerifyFinding> missingFile = await VerifyAsync(harness, core: Path.Combine(harness.Directory.Path, "yok.db"));

        Assert.Contains(noCore, f => f.Code == "gomulu-core-uyusmuyor");
        Assert.Contains(missingFile, f => f.Code == "gomulu-core-yok");
    }

    [Fact]
    public async Task A_store_that_cannot_be_reached_exits_with_4_not_3()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        harness.Store.Fault = (_, _) => new StorageException(StorageFailure.Unavailable, "baglanti reddedildi");

        int code = await new VerifyCommand(harness.Context).RunAsync(new VerifyRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Equal(4, code);
    }

    [Fact]
    public async Task Verify_needs_no_database()
    {
        await using PublisherHarness harness = await PublishedAsync(postgres);
        IConfiguration noDatabase = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Publisher:SchemaDir"] = harness.Configuration["Publisher:SchemaDir"],
                ["Publisher:TempDir"] = harness.Configuration["Publisher:TempDir"],
                ["Storage:PublicBaseUrl"] = PublisherHarness.PublicBaseUrl,
                ["Signing:dev:PublicKey"] = harness.Configuration["Signing:dev:PublicKey"],
            })
            .Build();
        await using PublisherContext context = new(noDatabase, harness.Releases, harness.Host);

        int code = await new VerifyCommand(context).RunAsync(new VerifyRequest(BuildFlavor.Dev), TestContext.Current.CancellationToken);

        Assert.Equal(0, code);
    }

    [Fact]
    public async Task P12_flags_a_test_source_in_a_pack_of_a_flavor_that_does_not_allow_it()
    {
        // test-baska: dev'e girebilir ama internal'a ve public'e giremez (yalniz test-kucuk ve test-ses fiksturudur).
        PackCatalog catalog = new(
        [
            new PackDefinition("test-baska", "Baska test paketi", Bundled: false, DependsOn: [], Sources: [new PackSourceBinding("test-baska", PackSourceRole.Content, Required: true)]),
        ]);
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublisherHarness.CreateAsync(postgres, seed: false, catalog: catalog);
        await harness.InsertSourceAsync("test-baska", ct);
        harness.RegisterSource("test-baska");
        await harness.InsertUnitAsync("k:test-baska:bolum-1:p1", "test-baska", "Deneme paragrafi 3", ct);
        Assert.Equal(0, (await harness.Pipeline.PublishAsync(new PublishRequest(BuildFlavor.Dev, []), ct)).ExitCode);

        // Kapi internal icin test-baska kaynagini suzer (P-12); asagida elle uretilen yapit onu yine de tasir ve verify yakalar.
        ReleaseResult internalDryRun = await harness.Pipeline.PublishAsync(new PublishRequest(BuildFlavor.Internal, [], DryRun: true), ct);
        Assert.Equal(0, internalDryRun.ExitCode);
        Assert.Empty(internalDryRun.Packs!);

        // Dev yapitini internal anahtariyla "internal" olarak yeniden yayimla: P-12 internal'da bu paketi yakalar.
        Manifest dev = harness.ReadStoredManifest("dev");
        foreach (ManifestPack pack in dev.Packs)
        {
            string devKey = PublisherHarness.PackKey("dev", pack.PackId, pack.Version);
            harness.Store.Seed(PublisherHarness.PackKey("internal", pack.PackId, pack.Version), harness.Store.Peek(devKey)!, pack.Sha256);
        }

        Manifest internalManifest = ManifestBuilder.Build(
            "internal",
            dev.Release,
            harness.Clock.GetUtcNow(),
            PublisherHarness.PublicBaseUrl,
            dev.Packs.Select(p => new ManifestPackInput(p.PackId, p.Version, p.Sha256, p.SizeBytes, p.MinAppVersion, p.DependsOn, p.SchemaVersion, p.Title, p.Bundled)));
        byte[] signed = ManifestSigner.Sign(ManifestJson.Write(internalManifest), harness.Keys[BuildFlavor.Internal]);
        harness.Store.Seed(PublisherHarness.ManifestKey("internal"), signed, null);
        harness.Store.Seed(PublisherHarness.HistoryKey("internal", dev.Release), signed, null);

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness, BuildFlavor.Internal);

        Assert.Contains(findings, f => f.Code == "P-12" && f.Message.Contains("test-baska", StringComparison.Ordinal));
        Assert.Contains(findings, f => f.Code == "pack-meta");
    }

    [Fact]
    public async Task P13_flags_a_manifest_whose_dependency_is_missing()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using PublisherHarness harness = await PublishedAsync(postgres);
        Manifest dev = harness.ReadStoredManifest("dev");
        ManifestPack broken = dev.Packs.Single(p => p.PackId == "test-kucuk");
        Manifest changed = ManifestBuilder.Build(
            "dev",
            dev.Release,
            harness.Clock.GetUtcNow(),
            PublisherHarness.PublicBaseUrl,
            dev.Packs.Select(p => new ManifestPackInput(
                p.PackId, p.Version, p.Sha256, p.SizeBytes, p.MinAppVersion, p.PackId == broken.PackId ? ["core"] : p.DependsOn, p.SchemaVersion, p.Title, p.Bundled)));
        byte[] signed = ManifestSigner.Sign(ManifestJson.Write(changed), harness.Keys[BuildFlavor.Dev]);
        harness.Store.Seed(PublisherHarness.ManifestKey("dev"), signed, null);

        IReadOnlyList<VerifyFinding> findings = await VerifyAsync(harness);

        Assert.Contains(findings, f => f.Code == "P-13" && f.Message.Contains("bagimlilik-manifestte-yok", StringComparison.Ordinal));
        Assert.NotEmpty(await File.ReadAllBytesAsync(Path.Combine(harness.OutDir, "dev", "2026.11.0", "manifest.json"), ct));
    }
}
