using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>Vektorlerin kapsamadigi davranislar.</summary>
public class AnchorRefBehaviorTests
{
    [Theory]
    [InlineData("rn:sozler:soz-10:hakikat-3:p4@120-184")]
    [InlineData("k:kisas-i-enbiya:hz-ibrahim:p2")]
    [InlineData("q:2:255:3-7")]
    public void Equal_values_parsed_twice_are_equal_and_hash_equal(string input)
    {
        AnchorRef a = AnchorRef.Parse(input);
        AnchorRef b = AnchorRef.Parse(input);

        Assert.Equal(a, b);
        Assert.True(a == b);
        Assert.Equal(a.GetHashCode(), b.GetHashCode());
        Assert.Equal(input, a.ToString());
    }

    [Fact]
    public void Different_paths_are_not_equal()
    {
        Assert.NotEqual(AnchorRef.Parse("rn:sozler:a:p1"), AnchorRef.Parse("rn:sozler:b:p1"));
    }

    [Theory]
    [InlineData("q:2:255:99999999999999999999")]
    [InlineData("rn:a:p2147483648")]
    [InlineData("rn:a:p2147483648:s1")]
    [InlineData("h:a:99999999999999999999999")]
    [InlineData("meal:a:2:255@0-2147483648")]
    public void Number_overflow_does_not_throw_in_TryParse(string input)
    {
        Assert.False(AnchorRef.TryParse(input, out AnchorRef? result));
        Assert.Null(result);
    }

    [Fact]
    public void Number_overflow_is_UZUNLUK()
    {
        AnchorException ex = Assert.Throws<AnchorException>(() => AnchorRef.Parse("rn:a:p2147483648"));
        Assert.Equal(AnchorErrorCode.Uzunluk, ex.Code);
        Assert.Equal("UZUNLUK", ex.CodeName);
    }

    [Fact]
    public void Max_int_is_accepted()
    {
        AnchorRef r = AnchorRef.Parse("rn:a:p2147483647");
        Assert.Equal(int.MaxValue, r.P);
    }

    [Fact]
    public void Null_and_empty_input()
    {
        Assert.False(AnchorRef.TryParse(null, out _));
        Assert.False(AnchorRef.TryParse(string.Empty, out _));
        Assert.Throws<ArgumentNullException>(() => AnchorRef.Parse(null!));
        Assert.Equal("BICIM", Assert.Throws<AnchorException>(() => AnchorRef.Parse(string.Empty)).CodeName);
    }

    [Fact]
    public void Trailing_newline_is_BICIM()
    {
        Assert.Equal("BICIM", Assert.Throws<AnchorException>(() => AnchorRef.Parse("q:1:1\n")).CodeName);
    }

    [Fact]
    public void Non_ascii_digits_are_BICIM()
    {
        // U+0662 ARABIC-INDIC DIGIT TWO; [0-9] eslemez.
        string arabicTwo = char.ConvertFromUtf32(0x0662);
        Assert.False(AnchorRef.TryParse("q:" + arabicTwo + ":1", out _));
        Assert.Equal("BICIM", Assert.Throws<AnchorException>(() => AnchorRef.Parse("q:" + arabicTwo + ":1")).CodeName);
    }

    [Fact]
    public void Turkish_dotted_capital_I_is_not_folded()
    {
        // U+0130 (I with dot above) ve buyuk I ASCII kucuk harf degildir.
        Assert.False(AnchorRef.TryParse("konu:" + char.ConvertFromUtf32(0x0130) + "nce", out _));
        Assert.False(AnchorRef.TryParse("konu:TEVHID", out _));
    }

    [Fact]
    public void Invalid_scheme_and_target_are_rejected()
    {
        AnchorRef r = AnchorRef.Parse("q:2:255");
        Assert.Throws<ArgumentException>(() => r.ToRoute(RouteTarget.Native, "baska"));
        Assert.Throws<ArgumentOutOfRangeException>(() => r.ToRoute((RouteTarget)99));
    }

    [Fact]
    public void CompareTo_null_is_greater()
    {
        Assert.Equal(1, AnchorRef.Parse("q:1:1").CompareTo(null));
    }

    [Fact]
    public void Sorting_follows_quran_reading_order()
    {
        string[] input = ["q:2:256", "q:2:255-257", "q:2:255:9", "q:2:255:2-3", "q:2:255:2", "q:2:255", "q:2:255-256"];
        string[] sorted = [.. input.Select(AnchorRef.Parse).Order().Select(a => a.ToString())];

        Assert.Equal(["q:2:255", "q:2:255:2", "q:2:255:2-3", "q:2:255:9", "q:2:255-256", "q:2:255-257", "q:2:256"], sorted);
    }
}
