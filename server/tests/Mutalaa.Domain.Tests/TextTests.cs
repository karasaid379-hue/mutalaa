using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests;

/// <summary>Vektorlerin kapsamadigi metin davranislari. Karakterler sayisal kod noktasiyla kurulur.</summary>
public class TextTests
{
    private static string Cp(params int[] codePoints) => string.Concat(codePoints.Select(char.ConvertFromUtf32));

    [Fact]
    public void ContentHash_lone_surrogate_throws()
    {
        string lone = ((char)0xD800).ToString();
        Assert.ThrowsAny<ArgumentException>(() => ContentHash.Compute(lone));
    }

    [Fact]
    public void ContentHash_empty_string()
    {
        Assert.Equal("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", ContentHash.Compute(string.Empty));
    }

    [Fact]
    public void Canonicalize_keeps_nbsp_at_edges_and_trims_only_space_tab_lf()
    {
        string nbsp = Cp(0x00A0);
        Assert.Equal(nbsp + "a" + nbsp, TextCanonicalizer.Canonicalize(" \t" + nbsp + "a" + nbsp + "\n "));
    }

    [Fact]
    public void Canonicalize_removes_deletables_before_nfc_and_trim()
    {
        // FEFF + bosluk + metin: silme once, kirpma sonra.
        Assert.Equal("a", TextCanonicalizer.Canonicalize(Cp(0xFEFF) + " a"));

        // e + LRM + COMBINING ACUTE -> silme sonrasi NFC -> e-acute.
        Assert.Equal(Cp(0x00E9), TextCanonicalizer.Canonicalize("e" + Cp(0x200E, 0x0301)));
    }

    [Fact]
    public void Canonicalize_keeps_zwnj_zwj_and_line_separators()
    {
        string kept = "a" + Cp(0x200C, 0x200D, 0x2028, 0x2029, 0x0085) + "b";
        Assert.Equal(kept, TextCanonicalizer.Canonicalize(kept));
    }

    [Fact]
    public void Canonicalize_normalizes_newlines_and_runs_of_blanks()
    {
        Assert.Equal("a b\nc\nd", TextCanonicalizer.Canonicalize("a \t b\r\nc\rd"));
    }

    [Fact]
    public void SnapSpan_rejects_invalid_spans()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.SnapSpan("abc", new Mutalaa.Domain.Anchors.AnchorSpan(2, 1)));
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.SnapSpan("abc", new Mutalaa.Domain.Anchors.AnchorSpan(0, 4)));
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.SnapSpan("abc", new Mutalaa.Domain.Anchors.AnchorSpan(-1, 1)));
    }
}
