using Mutalaa.Api.Validation;

namespace Mutalaa.Api.Tests;

/// <summary>WritableText: NUL ve eslesmemis vekil karakter reddi (saf islev).</summary>
public class WritableTextTests
{
    [Fact]
    public void Ordinary_text_is_writable_and_counted_in_code_points()
    {
        Assert.True(WritableText.TryCountCodePoints("Deneme paragrafı 1", out int plain));
        Assert.Equal(18, plain);

        // Vekil cifti tek kod noktasidir.
        Assert.True(WritableText.TryCountCodePoints("a\U0001F600b", out int pair));
        Assert.Equal(3, pair);

        Assert.True(WritableText.TryCountCodePoints(null, out int none));
        Assert.Equal(0, none);
        Assert.True(WritableText.TryCountCodePoints(string.Empty, out int empty));
        Assert.Equal(0, empty);
    }

    // Nitelik argumanlari eslesmemis vekili tasiyamaz (meta veri UTF-8); belirtecler testte degistirilir.
    [Theory]
    [InlineData("a{NUL}b")]
    [InlineData("{NUL}")]
    [InlineData("a{HI}b")]
    [InlineData("{HI}")]
    [InlineData("{LO}")]
    [InlineData("a{LO}{HI}")]
    [InlineData("sonu yuksek vekil {HI}")]
    public void NUL_and_unpaired_surrogates_are_not_writable(string template)
    {
        string text = template
            .Replace("{NUL}", "\0", StringComparison.Ordinal)
            .Replace("{HI}", ((char)0xD800).ToString(), StringComparison.Ordinal)
            .Replace("{LO}", ((char)0xDC00).ToString(), StringComparison.Ordinal);

        Assert.False(WritableText.TryCountCodePoints(text, out int count));
        Assert.Equal(0, count);
        Assert.False(WritableText.IsWritable(text));
    }

    [Fact]
    public void Check_adds_an_error_under_the_snake_case_field_only_when_the_text_is_not_writable()
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);

        Assert.True(WritableText.Check(errors, "gerekce", "temiz"));
        Assert.Empty(errors);

        Assert.False(WritableText.Check(errors, "duzenlenen.metin", "a\0b"));
        Assert.Equal(["duzenlenen.metin alanı geçersiz karakter içeriyor (NUL ya da eşleşmemiş vekil karakter)."], errors["duzenlenen.metin"]);
    }
}
