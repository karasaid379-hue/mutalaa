using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Persistence;
using Mutalaa.Infrastructure.Persistence.Converters;
using NpgsqlTypes;

namespace Mutalaa.Api.Tests;

/// <summary>Capa ve aralik donusturuculeri, karsilastiricilar ve enum etiket cevirmeni (veritabani gerektirmez; tr-TR'de de gecer).</summary>
public class ConverterTests
{
    private static void InBothCultures(Action action)
    {
        CultureScope.Invariant(action);
        CultureScope.Turkish(action);
    }

    [Fact]
    public void Anchor_converter_writes_the_canonical_string_and_reads_it_back()
    {
        InBothCultures(() =>
        {
            AnchorRefConverter converter = new();
            foreach (string text in new[] { "q:2:255", "q:2:255:3-7", "meal:elmalili:2:255", "tf:elmalili:2-255-257:p3", "rn:sozler:soz-10:hakikat-3:p4:s2", "h:buhari:52" })
            {
                AnchorRef parsed = AnchorRef.Parse(text);
                string stored = (string)converter.ConvertToProvider(parsed)!;
                Assert.Equal(text, stored);
                Assert.Equal(parsed, (AnchorRef)converter.ConvertFromProvider(stored)!);
            }
        });
    }

    [Fact]
    public void Anchor_converter_rejects_an_anchor_with_a_span()
    {
        AnchorRef withSpan = AnchorRef.Parse("meal:elmalili:2:255@10-48");

        Assert.NotNull(withSpan.Span);
        Assert.Throws<InvalidOperationException>(() => AnchorRefConverter.ToStore(withSpan));
        Assert.Throws<InvalidOperationException>(() => new AnchorRefConverter().ConvertToProvider(withSpan));
    }

    [Theory]
    [InlineData("Q:2:255")]
    [InlineData("q:115:1")]
    [InlineData("q:2:255-255")]
    [InlineData("")]
    public void Anchor_converter_throws_on_an_invalid_database_string(string stored)
    {
        Assert.Throws<AnchorException>(() => new AnchorRefConverter().ConvertFromProvider(stored));
    }

    [Fact]
    public void Anchor_comparer_is_value_based()
    {
        AnchorRefComparer comparer = new();
        AnchorRef a = AnchorRef.Parse("q:2:255");
        AnchorRef b = AnchorRef.Parse("q:2:255");

        Assert.True(comparer.Equals(a, b));
        Assert.Equal(comparer.GetHashCode(a), comparer.GetHashCode(b));
        Assert.False(comparer.Equals(a, AnchorRef.Parse("q:2:256")));
        Assert.Same(a, comparer.Snapshot(a));
    }

    [Fact]
    public void Span_converter_maps_to_the_half_open_range_and_back()
    {
        InBothCultures(() =>
        {
            AnchorSpanRangeConverter converter = new();
            NpgsqlRange<int> range = (NpgsqlRange<int>)converter.ConvertToProvider(new AnchorSpan(3, 8))!;

            Assert.Equal(3, range.LowerBound);
            Assert.Equal(8, range.UpperBound);
            Assert.True(range.LowerBoundIsInclusive);
            Assert.False(range.UpperBoundIsInclusive);
            Assert.Equal(new AnchorSpan(3, 8), (AnchorSpan)converter.ConvertFromProvider(range)!);
        });
    }

    [Theory]
    [InlineData(-1, 4)]
    [InlineData(5, 5)]
    [InlineData(6, 5)]
    public void Span_converter_rejects_invalid_spans_on_write(int start, int end)
    {
        Assert.Throws<InvalidOperationException>(() => AnchorSpanRangeConverter.ToRange(new AnchorSpan(start, end)));
    }

    [Fact]
    public void Span_converter_rejects_non_canonical_ranges_on_read()
    {
        NpgsqlRange<int>[] bad =
        [
            NpgsqlRange<int>.Empty,
            new(3, lowerBoundIsInclusive: true, 8, upperBoundIsInclusive: true),
            new(3, lowerBoundIsInclusive: false, 8, upperBoundIsInclusive: false),
            new(3, lowerBoundIsInclusive: true, lowerBoundInfinite: false, 0, upperBoundIsInclusive: false, upperBoundInfinite: true),
            new(0, lowerBoundIsInclusive: true, lowerBoundInfinite: true, 8, upperBoundIsInclusive: false, upperBoundInfinite: false),
        ];

        foreach (NpgsqlRange<int> range in bad)
        {
            Assert.Throws<InvalidOperationException>(() => AnchorSpanRangeConverter.FromRange(range));
        }
    }

    [Fact]
    public void Span_array_converter_and_comparer_work_element_wise()
    {
        AnchorSpanArrayConverter converter = new();
        AnchorSpan[] spans = [new(0, 10), new(10, 25)];

        NpgsqlRange<int>[] ranges = (NpgsqlRange<int>[])converter.ConvertToProvider(spans)!;
        Assert.Equal(2, ranges.Length);
        Assert.Equal(spans, (AnchorSpan[])converter.ConvertFromProvider(ranges)!);

        AnchorSpanArrayComparer comparer = new();
        AnchorSpan[] copy = (AnchorSpan[])comparer.Snapshot(spans)!;
        Assert.NotSame(spans, copy);
        Assert.True(comparer.Equals(spans, copy));
        Assert.Equal(comparer.GetHashCode(spans), comparer.GetHashCode(copy));
        Assert.False(comparer.Equals(spans, [new AnchorSpan(0, 10)]));
        Assert.Throws<InvalidOperationException>(() => converter.ConvertToProvider(new[] { new AnchorSpan(4, 4) }));
    }

    [Fact]
    public void Label_translator_uses_ordinal_labels_in_every_culture()
    {
        InBothCultures(() =>
        {
            LabelNameTranslator<LicenseStatus> translator = new(LicenseStatusLabels.ToLabel);

            Assert.Equal("ic_kullanim", translator.TranslateMemberName(nameof(LicenseStatus.IcKullanim)));
            Assert.Equal("serbest", translator.TranslateMemberName(nameof(LicenseStatus.Serbest)));
            Assert.Throws<InvalidOperationException>(() => translator.TranslateMemberName("serbest"));
            Assert.Throws<NotSupportedException>(() => translator.TranslateTypeName("LicenseStatus"));
        });
    }

    [Fact]
    public void Enum_definitions_list_license_status_labels_in_numeric_order()
    {
        InBothCultures(() =>
        {
            Assert.Equal(11, PostgresEnums.Definitions.Count);
            Assert.Equal(
                ["serbest", "bekliyor", "ic_kullanim", "kapali"],
                PostgresEnums.Definitions.Single(d => d.Key == "license_status").Value);
            Assert.Equal(
                ["etkin", "kullanim_disi"],
                PostgresEnums.Definitions.Single(d => d.Key == "unit_status").Value);
        });
    }
}
