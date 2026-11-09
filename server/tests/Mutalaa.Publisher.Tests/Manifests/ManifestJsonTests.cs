using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Manifests;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>ManifestJson ve ManifestBuilder: sabit ozellik sirasi, Title kurali, UTC bicimi, siralama, kultur bagimsizligi.</summary>
public class ManifestJsonTests
{
    private static readonly string[] RootOrder = ["manifest_version", "flavor", "release", "generated_at", "packs"];

    private static readonly string[] PackOrderFull =
    [
        "pack_id", "version", "sha256", "size_bytes", "min_app_version", "depends_on", "url", "schema_version", "title", "bundled",
    ];

    private static string[] Names(JsonElement element) => [.. element.EnumerateObject().Select(p => p.Name)];

    [Fact]
    public void Properties_are_written_in_the_fixed_order()
    {
        byte[] json = ImzaFixture.UnsignedManifest();

        using JsonDocument document = JsonDocument.Parse(json);
        Assert.Equal(RootOrder, Names(document.RootElement));
        JsonElement core = document.RootElement.GetProperty("packs")[0];
        Assert.Equal(PackOrderFull, Names(core));
    }

    [Fact]
    public void Packs_are_sorted_by_pack_id_ordinally_whatever_the_input_order()
    {
        Manifest manifest = ImzaFixture.Manifest();

        Assert.Equal(["core", "test-kucuk"], manifest.Packs.Select(p => p.PackId).ToArray());
    }

    [Fact]
    public void Title_and_bundled_are_omitted_when_null()
    {
        Manifest manifest = ManifestBuilder.Build(
            "dev",
            "2026.11.0",
            ImzaFixture.GeneratedAt,
            ImzaFixture.PublicBaseUrl,
            [new ManifestPackInput("core", "2026.11.0", new string('a', 64), 10, "1.0.0", [], 1)]);

        using JsonDocument document = JsonDocument.Parse(ManifestJson.Write(manifest));

        Assert.Equal(
            ["pack_id", "version", "sha256", "size_bytes", "min_app_version", "depends_on", "url", "schema_version"],
            Names(document.RootElement.GetProperty("packs")[0]));
    }

    [Fact]
    public void Generated_at_is_utc_with_second_precision()
    {
        DateTimeOffset local = new(2026, 11, 9, 15, 0, 0, 987, TimeSpan.FromHours(3));
        Manifest manifest = ManifestBuilder.Build(
            "dev",
            "2026.11.0",
            local,
            ImzaFixture.PublicBaseUrl,
            [new ManifestPackInput("core", "2026.11.0", new string('a', 64), 10, "1.0.0", [], 1)]);

        using JsonDocument document = JsonDocument.Parse(ManifestJson.Write(manifest));

        Assert.Equal("2026-11-09T12:00:00Z", document.RootElement.GetProperty("generated_at").GetString());
    }

    [Fact]
    public void Output_is_bomless_utf8_with_lf_line_endings_and_one_final_lf()
    {
        byte[] json = ImzaFixture.UnsignedManifest();

        Assert.NotEqual(0xEF, json[0]);
        Assert.DoesNotContain((byte)'\r', json);
        Assert.Equal((byte)'\n', json[^1]);
        Assert.NotEqual((byte)'\n', json[^2]);
        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true).GetString(json);
        Assert.Contains("Çekirdek (sentetik)", text, StringComparison.Ordinal);
    }

    [Fact]
    public void Urls_follow_the_storage_layout_and_trailing_slashes_of_the_base_url_are_trimmed()
    {
        Manifest manifest = ManifestBuilder.Build(
            "internal",
            "2026.11.3",
            ImzaFixture.GeneratedAt,
            "http://192.168.1.50:8333/mutalaa//",
            [new ManifestPackInput("core", "2026.11.3", new string('a', 64), 10, "1.0.0", [], 1)]);

        Assert.Equal(
            "http://192.168.1.50:8333/mutalaa/packs/internal/core/2026.11.3/core-2026.11.3.db",
            Assert.Single(manifest.Packs).Url);
    }

    [Fact]
    public void Read_returns_what_was_written()
    {
        Manifest written = ImzaFixture.Manifest();

        Manifest read = ManifestJson.Read(ManifestJson.Write(written));

        Assert.Equal(written.Flavor, read.Flavor);
        Assert.Equal(written.Release, read.Release);
        Assert.Equal(written.GeneratedAt, read.GeneratedAt);
        Assert.Equal(written.ManifestVersion, read.ManifestVersion);
        Assert.Equal(written.Packs.Count, read.Packs.Count);
        for (int i = 0; i < written.Packs.Count; i++)
        {
            Assert.Equal(written.Packs[i].PackId, read.Packs[i].PackId);
            Assert.Equal(written.Packs[i].Sha256, read.Packs[i].Sha256);
            Assert.Equal(written.Packs[i].Url, read.Packs[i].Url);
            Assert.Equal(written.Packs[i].DependsOn, read.Packs[i].DependsOn);
            Assert.Equal(written.Packs[i].Title, read.Packs[i].Title);
            Assert.Equal(written.Packs[i].Bundled, read.Packs[i].Bundled);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_same_bytes_are_produced_in_every_culture(bool turkish)
    {
        byte[] expected = ImzaFixture.UnsignedManifest();
        byte[]? actual = null;

        CultureScope.For(turkish, () => actual = ImzaFixture.UnsignedManifest());

        Assert.Equal(expected, actual);
    }
}
