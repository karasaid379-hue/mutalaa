using Mutalaa.Domain.Content;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests;

/// <summary>KWIC orneklemi ve kod noktasi dilimleme (A17.7). Metinler sentetiktir.</summary>
public class KwicSamplingTests
{
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(8)]
    public void At_most_the_maximum_returns_every_index(int total)
    {
        Assert.Equal(Enumerable.Range(0, total), KwicSampling.SampleIndices(total));
    }

    [Theory]
    [InlineData(9)]
    [InlineData(17)]
    [InlineData(100)]
    [InlineData(2699)]
    public void A_frequent_lemma_gets_eight_increasing_distinct_samples_starting_at_the_first(int total)
    {
        IReadOnlyList<int> picks = KwicSampling.SampleIndices(total);

        Assert.Equal(8, picks.Count);
        Assert.Equal(0, picks[0]);
        Assert.Equal(picks.Distinct().Order(), picks);
        Assert.All(picks, p => Assert.InRange(p, 0, total - 1));
        Assert.Equal(picks, KwicSampling.SampleIndices(total));
    }

    [Fact]
    public void The_selection_is_spread_evenly_over_the_reading_order()
    {
        Assert.Equal([0, 12, 25, 37, 50, 62, 75, 87], KwicSampling.SampleIndices(100));
    }

    [Fact]
    public void Negative_total_and_non_positive_maximum_are_rejected()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => KwicSampling.SampleIndices(-1));
        Assert.Throws<ArgumentOutOfRangeException>(() => KwicSampling.SampleIndices(5, 0));
    }

    [Fact]
    public void Slice_uses_code_point_offsets_not_utf16_offsets()
    {
        // a + U+1F600 (vekil cift, UTF-16'da 2) + b + U+1F601 + c: kod noktasi ofsetleri 0..5.
        string text = "a" + char.ConvertFromUtf32(0x1F600) + "b" + char.ConvertFromUtf32(0x1F601) + "c";

        Assert.Equal("b", CodePointOffsets.Slice(text, 2, 3));
        Assert.Equal(char.ConvertFromUtf32(0x1F600) + "b", CodePointOffsets.Slice(text, 1, 3));
        Assert.Equal(char.ConvertFromUtf32(0x1F601) + "c", CodePointOffsets.Slice(text, 3, 5));
        Assert.Equal(text, CodePointOffsets.Slice(text, 0, 5));
        Assert.Equal(string.Empty, CodePointOffsets.Slice(text, 5, 5));
        Assert.Equal(string.Empty, CodePointOffsets.Slice(text, 0, 0));

        // UTF-16 ofseti olsaydi "b" yerine vekil cift ya da yarim cift gelirdi.
        Assert.NotEqual(text.Substring(2, 1), CodePointOffsets.Slice(text, 2, 3));
    }

    [Theory]
    [InlineData(-1, 2)]
    [InlineData(3, 2)]
    [InlineData(0, 6)]
    [InlineData(6, 6)]
    public void TrySlice_refuses_ranges_outside_the_text(int start, int end)
    {
        string text = "a" + char.ConvertFromUtf32(0x1F600) + "bcd";

        Assert.False(CodePointOffsets.TrySlice(text, start, end, out string slice));
        Assert.Equal(string.Empty, slice);
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.Slice(text, start, end));
    }

    [Fact]
    public void Slice_agrees_with_CpToUtf16_on_every_range()
    {
        string text = "x" + char.ConvertFromUtf32(0x10400) + "y" + char.ConvertFromUtf32(0x1F600) + char.ConvertFromUtf32(0x1F601) + "z";
        int count = CodePointOffsets.CodePointCount(text);

        for (int start = 0; start <= count; start++)
        {
            for (int end = start; end <= count; end++)
            {
                int a = CodePointOffsets.CpToUtf16(text, start);
                int b = CodePointOffsets.CpToUtf16(text, end);
                Assert.Equal(text[a..b], CodePointOffsets.Slice(text, start, end));
            }
        }
    }
}
