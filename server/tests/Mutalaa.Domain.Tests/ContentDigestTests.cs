using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests;

public class ContentDigestTests
{
    private const string HashA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private const string HashB = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";
    private const string EmptyDigest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    // sha256sum ile elle hesaplandi: printf 'q:1:1\t<A>\nq:1:2\t<B>\n' | sha256sum
    private const string HandComputed = "dbec0835f2b8025712d24d8797ef31fb37a730481180165bdf12721e4627c9bb";

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Empty_source_is_the_sha256_of_empty_input(bool turkish) => CultureScope.For(turkish, () =>
    {
        Assert.Equal(EmptyDigest, ContentDigest.Compute([]));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Known_example_matches_hand_computed_digest(bool turkish) => CultureScope.For(turkish, () =>
    {
        ContentDigestEntry[] entries = [new("q:1:1", HashA), new("q:1:2", HashB)];

        Assert.Equal(HandComputed, ContentDigest.Compute(entries));

        // Ayni dizgiyi ContentHash (UTF-8 SHA-256) ile bagimsiz hesapla.
        Assert.Equal(HandComputed, ContentHash.Compute("q:1:1\t" + HashA + "\nq:1:2\t" + HashB + "\n"));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Input_order_does_not_matter(bool turkish) => CultureScope.For(turkish, () =>
    {
        ContentDigestEntry[] forward = [new("q:1:1", HashA), new("q:1:2", HashB), new("q:2:10", HashA), new("q:2:9", HashB)];
        ContentDigestEntry[] reversed = [.. forward.Reverse()];
        ContentDigestEntry[] shuffled = [forward[2], forward[0], forward[3], forward[1]];

        string expected = ContentDigest.Compute(forward);

        Assert.Equal(expected, ContentDigest.Compute(reversed));
        Assert.Equal(expected, ContentDigest.Compute(shuffled));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Anchors_are_ordered_by_bytes_not_numerically_nor_by_utf16(bool turkish) => CultureScope.For(turkish, () =>
    {
        // Metin sirasi: "q:2:10" < "q:2:9" (sayisal degil).
        string textual = ContentHash.Compute("q:2:10\t" + HashA + "\nq:2:9\t" + HashB + "\n");
        Assert.Equal(textual, ContentDigest.Compute([new("q:2:9", HashB), new("q:2:10", HashA)]));

        // U+FF5E (BMP, UTF-8 EF BD 9E) ile U+1F600 (UTF-8 F0 9F 98 80): UTF-8 sirasinda BMP once gelir;
        // UTF-16 Ordinal sirasinda vekil cift (D83D) 0xFF5E'den once gelirdi.
        string bmp = char.ConvertFromUtf32(0xFF5E);
        string astral = char.ConvertFromUtf32(0x1F600);
        Assert.True(string.CompareOrdinal(astral, bmp) < 0);

        string utf8Order = ContentHash.Compute(bmp + "\t" + HashA + "\n" + astral + "\t" + HashB + "\n");
        string utf16Order = ContentHash.Compute(astral + "\t" + HashB + "\n" + bmp + "\t" + HashA + "\n");

        Assert.NotEqual(utf8Order, utf16Order);
        Assert.Equal(utf8Order, ContentDigest.Compute([new(astral, HashB), new(bmp, HashA)]));
    });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Digest_changes_when_any_hash_or_anchor_changes(bool turkish) => CultureScope.For(turkish, () =>
    {
        string baseline = ContentDigest.Compute([new("q:1:1", HashA), new("q:1:2", HashB)]);

        Assert.NotEqual(baseline, ContentDigest.Compute([new("q:1:1", HashA), new("q:1:2", HashA)]));
        Assert.NotEqual(baseline, ContentDigest.Compute([new("q:1:1", HashA), new("q:1:3", HashB)]));
        Assert.NotEqual(baseline, ContentDigest.Compute([new("q:1:1", HashA)]));
        Assert.Matches("^[0-9a-f]{64}$", baseline);
    });

    [Fact]
    public void Digest_is_identical_under_turkish_culture_for_dotted_and_dotless_i()
    {
        // Turkce I/i/dotless-i/dotted-I kod noktalariyla; kulturlu donusum/karsilastirma olsaydi sonuc ayrilirdi.
        string dotlessI = char.ConvertFromUtf32(0x0131);
        string dottedI = char.ConvertFromUtf32(0x0130);
        ContentDigestEntry[] entries =
        [
            new("rn:I", HashA),
            new("rn:i", HashB),
            new("rn:" + dotlessI, HashA),
            new("rn:" + dottedI, HashB),
        ];
        string invariant = string.Empty;
        string turkish = string.Empty;

        CultureScope.Invariant(() => invariant = ContentDigest.Compute(entries));
        CultureScope.Turkish(() => turkish = ContentDigest.Compute(entries));

        Assert.Equal(invariant, turkish);
        Assert.Equal(invariant, ContentDigest.Compute([.. entries.Reverse()]));
    }

    [Fact]
    public void Duplicate_anchor_separator_characters_and_invalid_unicode_are_rejected()
    {
        Assert.Throws<ArgumentException>(() => ContentDigest.Compute([new("q:1:1", HashA), new("q:1:1", HashB)]));
        Assert.Throws<ArgumentException>(() => ContentDigest.Compute([new("q:1:1\t", HashA)]));
        Assert.Throws<ArgumentException>(() => ContentDigest.Compute([new("q:1:1", HashA + "\n")]));
        Assert.ThrowsAny<ArgumentException>(() => ContentDigest.Compute([new(((char)0xD800).ToString(), HashA)]));
        Assert.Throws<ArgumentNullException>(() => ContentDigest.Compute(null!));
    }
}
