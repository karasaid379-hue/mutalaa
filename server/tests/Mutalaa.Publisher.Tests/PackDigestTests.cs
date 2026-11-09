using System.Security.Cryptography;
using System.Text;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Publisher.Tests;

/// <summary>PackDigest: paket ozeti (K-46 madde 1). Docker gerektirmez.</summary>
public class PackDigestTests
{
    private static PackContent WithXref(float score, float confidence, string evidence = "{}") => new()
    {
        PackId = "core",
        Flavor = BuildFlavor.Dev,
        Units = [PackTestData.PackUnit("q:1:1", "Deneme paragrafi 1", 1)],
        Xrefs =
        [
            new PackXrefRow("0190a000-0000-7000-8000-000000000001", "q:1:1", null, null, "meal:deneme:1:1", null, null, "atif", PackRows.FromSingle(score), PackRows.FromSingle(confidence), 1, 0, evidence, "test"),
        ],
    };

    [Fact]
    public void Same_input_gives_the_same_lowercase_hex_digest()
    {
        string first = PackDigest.Compute(PackTestData.SmallContent());
        string second = PackDigest.Compute(PackTestData.SmallContent());

        Assert.Equal(first, second);
        Assert.Matches("^[0-9a-f]{64}$", first);
    }

    [Fact]
    public void Row_order_of_the_input_does_not_change_the_digest()
    {
        PackContent content = PackTestData.SmallContent();
        PackContent shuffled = new()
        {
            PackId = content.PackId,
            Flavor = content.Flavor,
            PackSources = content.PackSources,
            Attributions = content.Attributions,
            Units = [content.Units[2], content.Units[0], content.Units[1]],
            UnitSearch = [content.UnitSearch[1], content.UnitSearch[2], content.UnitSearch[0]],
        };

        Assert.Equal(PackDigest.Compute(content), PackDigest.Compute(shuffled));
    }

    [Fact]
    public void Changing_one_field_changes_the_digest()
    {
        PackContent content = PackTestData.SmallContent();
        string baseline = PackDigest.Compute(content);

        PackContent changedText = Clone(content, units: [content.Units[0] with { Text = "Deneme paragrafi 1." }, content.Units[1], content.Units[2]]);
        PackContent changedApproved = Clone(content, units: [content.Units[0], content.Units[1] with { Approved = 1 }, content.Units[2]]);
        PackContent changedSearch = Clone(content, search: [content.UnitSearch[0] with { ArNorm = PackTestData.SyntheticArabic }, content.UnitSearch[1], content.UnitSearch[2]]);
        PackContent changedAttribution = Clone(content, attributions: [content.Attributions[0] with { RequiredCredit = "baska kredi" }]);
        PackContent extraRow = Clone(content, units: [.. content.Units, PackTestData.PackUnit("k:test-kucuk:bolum-1:p4", "Deneme paragrafi 4", 4)]);

        string[] digests = [PackDigest.Compute(changedText), PackDigest.Compute(changedApproved), PackDigest.Compute(changedSearch), PackDigest.Compute(changedAttribution), PackDigest.Compute(extraRow)];
        Assert.All(digests, d => Assert.NotEqual(baseline, d));
        Assert.Equal(digests.Length, digests.Distinct(StringComparer.Ordinal).Count());
    }

    [Fact]
    public void Headers_flavor_pack_id_and_schema_version_are_part_of_the_digest()
    {
        PackContent dev = PackTestData.SmallContent(BuildFlavor.Dev);
        PackContent internalFlavor = PackTestData.SmallContent(BuildFlavor.Internal);
        PackContent otherPack = PackTestData.SmallContent(BuildFlavor.Dev, "tefsir-test-ornek");
        PackContent otherSchema = new()
        {
            PackId = dev.PackId,
            Flavor = dev.Flavor,
            SchemaVersion = 2,
            PackSources = dev.PackSources,
            Attributions = dev.Attributions,
            Units = dev.Units,
            UnitSearch = dev.UnitSearch,
        };

        string[] digests = [PackDigest.Compute(dev), PackDigest.Compute(internalFlavor), PackDigest.Compute(otherPack), PackDigest.Compute(otherSchema)];

        Assert.Equal(4, digests.Distinct(StringComparer.Ordinal).Count());
    }

    [Fact]
    public void The_digest_of_a_fixed_synthetic_pack_is_pinned()
    {
        // Ozet bicimi (basliklar, JCS, satir sirasi, LF ayraci) degisirse bu deger bilerek guncellenir; yayinlanmis paketlerin ozeti degisir.
        // Degeri Node (JSON.stringify + SHA-256) ile bagimsiz olarak da hesaplandi: ayni.
        Assert.Equal("192578d5d911a850e46a267f0fcd7a31ce37d2425d10059ef33e95466f180a69", PackDigest.Compute(PackTestData.SmallContent(BuildFlavor.Dev)));
    }

    [Fact]
    public void Header_rows_come_first_in_the_documented_order()
    {
        PackContent empty = new() { PackId = "core", Flavor = BuildFlavor.Dev };
        string expectedInput =
            "[\"meta\",\"schema_version\",1]\n" +
            "[\"meta\",\"normalizer_version\",\"1.0\"]\n" +
            "[\"meta\",\"flavor\",\"dev\"]\n" +
            "[\"meta\",\"pack_id\",\"core\"]\n";

        string expected = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(expectedInput)));

        Assert.Equal(expected, PackDigest.Compute(empty));
    }

    [Fact]
    public void Row_text_is_hashed_as_its_canonical_json_array()
    {
        PackContent one = new()
        {
            PackId = "test-kucuk",
            Flavor = BuildFlavor.Public,
            PackSources = [new PackSourceRow("test-kucuk")],
        };
        string expectedInput =
            "[\"meta\",\"schema_version\",1]\n" +
            "[\"meta\",\"normalizer_version\",\"1.0\"]\n" +
            "[\"meta\",\"flavor\",\"public\"]\n" +
            "[\"meta\",\"pack_id\",\"test-kucuk\"]\n" +
            "[\"pack_source\",\"test-kucuk\"]\n";

        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(expectedInput))), PackDigest.Compute(one));
    }

    [Fact]
    public void A_float_real_is_hashed_by_its_short_decimal_form_not_the_widened_double()
    {
        // 0,7f dogrudan double'a genisletilince 0,699999988... olur ve ayri bir ozet verir. Pakete kisa onlu deger (0,7) yazilir; ozet de onu kullanir.
        string viaShortForm = PackDigest.Compute(WithXref(0.7f, 0.9f));
        string literalDecimal = PackDigest.Compute(WithDouble(0.7, 0.9));
        string widened = PackDigest.Compute(WithDouble((double)0.7f, 0.9));

        Assert.Equal(literalDecimal, viaShortForm);
        Assert.NotEqual(widened, viaShortForm);
    }

    [Fact]
    public void The_digest_is_independent_of_version_built_at_and_data_version()
    {
        // Bu alanlar PackContent'te yoktur; pack_meta'ya yazici koyar. SqlitePackWriterTests ayni ozeti iki surum ve iki saatle dogrular;
        // burada ozetin yalnizca PackContent'e bagli oldugu (zamansiz, tekrarlanabilir) gosterilir.
        PackContent content = PackTestData.SmallContent();

        string first = PackDigest.Compute(content);
        string second = PackDigest.Compute(content);

        Assert.Equal(first, second);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_digest_is_the_same_under_invariant_and_turkish_cultures(bool turkish)
    {
        string baseline = PackDigest.Compute(WithXref(0.7f, 0.9f));
        string measured = string.Empty;

        CultureScope.For(turkish, () => measured = PackDigest.Compute(WithXref(0.7f, 0.9f)));

        Assert.Equal(baseline, measured);
    }

    [Fact]
    public void Evidence_text_is_part_of_the_digest()
    {
        Assert.NotEqual(
            PackDigest.Compute(WithXref(0.7f, 0.9f, "{}")),
            PackDigest.Compute(WithXref(0.7f, 0.9f, "{\"x\": 1}")));
    }

    private static PackContent WithDouble(double score, double confidence) => new()
    {
        PackId = "core",
        Flavor = BuildFlavor.Dev,
        Units = [PackTestData.PackUnit("q:1:1", "Deneme paragrafi 1", 1)],
        Xrefs =
        [
            new PackXrefRow("0190a000-0000-7000-8000-000000000001", "q:1:1", null, null, "meal:deneme:1:1", null, null, "atif", score, confidence, 1, 0, "{}", "test"),
        ],
    };

    private static PackContent Clone(
        PackContent source,
        IReadOnlyList<PackUnitRow>? units = null,
        IReadOnlyList<PackUnitSearchRow>? search = null,
        IReadOnlyList<PackAttributionRow>? attributions = null) => new()
        {
            PackId = source.PackId,
            Flavor = source.Flavor,
            PackSources = source.PackSources,
            Attributions = attributions ?? source.Attributions,
            Units = units ?? source.Units,
            UnitSearch = search ?? source.UnitSearch,
        };
}
