using MackySoft.Json.Canonicalization;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>
/// RFC 8785 test verisi (cyberphone/json-canonicalization @32a4819, 6 girdi/cikti cifti) MackySoft kitapligiyla bayt bayt.
/// Dosyalar cikti klasorunde data\jcs\input ve data\jcs\output altindadir.
/// </summary>
public class JcsRfc8785Tests
{
    public static TheoryData<string> Names => ["arrays", "french", "structures", "unicode", "values", "weird"];

    [Theory]
    [MemberData(nameof(Names))]
    public void Canonical_output_matches_the_rfc_pair_byte_for_byte(string name)
    {
        byte[] input = Read("input", name);
        byte[] expected = Read("output", name);

        byte[] actual = Rfc8785JsonCanonicalizer.Canonicalize(input);

        Assert.Equal(expected, actual);
    }

    [Fact]
    public void There_are_exactly_six_pairs()
    {
        string root = Path.Combine(AppContext.BaseDirectory, "data", "jcs");

        Assert.Equal(6, Directory.GetFiles(Path.Combine(root, "input"), "*.json").Length);
        Assert.Equal(6, Directory.GetFiles(Path.Combine(root, "output"), "*.json").Length);
    }

    [Fact]
    public void Duplicate_property_names_and_negative_zero_are_rejected()
    {
        Assert.Throws<JsonCanonicalizationException>(() => Rfc8785JsonCanonicalizer.Canonicalize("""{"a":1,"a":2}"""u8));
        Assert.Throws<JsonCanonicalizationException>(() => Rfc8785JsonCanonicalizer.Canonicalize("""{"a":-0}"""u8));
    }

    private static byte[] Read(string folder, string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "jcs", folder, name + ".json");
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("RFC 8785 dosyasi cikti klasorune kopyalanmamis: " + path);
        }

        return File.ReadAllBytes(path);
    }
}
