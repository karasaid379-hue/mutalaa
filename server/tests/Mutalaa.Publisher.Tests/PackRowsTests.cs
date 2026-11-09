using System.Text;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Publisher.Tests;

/// <summary>PackRows: tek kanonik satir sayici (sabit tablo sirasi, UTF-8 bayt sirasi, JCS) ve Utf8Order. Docker gerektirmez.</summary>
public class PackRowsTests
{
    private static PackContent Mixed() => new()
    {
        PackId = "core",
        Flavor = BuildFlavor.Dev,
        PackSources = [new PackSourceRow("b-kaynak"), new PackSourceRow("a-kaynak")],
        Attributions =
        [
            new PackAttributionRow("b-kaynak", "B", "1", null, "kredi b", null),
            new PackAttributionRow("a-kaynak", "A", null, "https://example.invalid/a", "kredi a", "bildirim"),
        ],
        Units =
        [
            PackTestData.PackUnit("q:1:2", "Deneme paragrafi 2", 2),
            PackTestData.PackUnit("q:1:10", "Deneme paragrafi 10", 10),
            PackTestData.PackUnit("q:1:1", "Deneme paragrafi 1", 1),
        ],
        UnitSearch = [new PackUnitSearchRow("q:1:2", "b", null, null), new PackUnitSearchRow("q:1:1", "a", null, null)],
        QuranMarkers = [new PackQuranMarkerRow("secde", 2, "q:1:1", "recommended"), new PackQuranMarkerRow("cuz", 10, "q:1:1", null), new PackQuranMarkerRow("cuz", 2, "q:1:1", null)],
        PageMaps =
        [
            new PackPageMapRow("medine-604", null, 2, null, "q:1:1", null, "q:1:2", null),
            new PackPageMapRow("medine-604", null, 1, null, "q:1:1", null, "q:1:2", null),
        ],
    };

    [Fact]
    public void Tables_come_in_the_fixed_order_and_rows_in_key_byte_order()
    {
        PackRow[] rows = [.. PackRows.Enumerate(Mixed())];

        string[] tableOrder = [.. rows.Select(r => r.Table).Distinct(StringComparer.Ordinal)];
        Assert.Equal(["pack_source", "attribution", "unit", "unit_search", "quran_marker", "page_map"], tableOrder);
        Assert.Equal(PackTables.Order.Where(t => tableOrder.Contains(t)), tableOrder);

        Assert.Equal(["a-kaynak", "b-kaynak"], rows.Where(r => r.Table == "pack_source").Select(r => (string)r.Values[0]!));
        // Bayt sirasi sozlugu sirasidir: "q:1:1" < "q:1:10" < "q:1:2" (sayisal sira degil).
        Assert.Equal(["q:1:1", "q:1:10", "q:1:2"], rows.Where(r => r.Table == "unit").Select(r => (string)r.Values[0]!));
        Assert.Equal(["q:1:1", "q:1:2"], rows.Where(r => r.Table == "unit_search").Select(r => (string)r.Values[0]!));
        Assert.Equal(
            [("cuz", 2L), ("cuz", 10L), ("secde", 2L)],
            rows.Where(r => r.Table == "quran_marker").Select(r => ((string)r.Values[0]!, (long)r.Values[1]!)));
        Assert.Equal([1L, 2L], rows.Where(r => r.Table == "page_map").Select(r => (long)r.Values[2]!));
    }

    [Fact]
    public void Row_values_match_the_column_lists_and_unit_has_no_rowid()
    {
        PackRow[] rows = [.. PackRows.Enumerate(Mixed())];

        foreach (PackRow row in rows)
        {
            Assert.Equal(PackTables.Columns(row.Table).Count, row.Values.Length);
        }

        Assert.DoesNotContain("rowid", PackTables.Columns("unit"));
        Assert.Equal("anchor", PackTables.Columns("unit_search")[0]);
        Assert.Throws<ArgumentException>(() => PackTables.Columns("yok"));
    }

    [Fact]
    public void Count_reports_every_table_including_empty_ones()
    {
        IReadOnlyDictionary<string, int> counts = PackRows.Count(Mixed());

        Assert.Equal(PackTables.Order.Order(StringComparer.Ordinal), counts.Keys.Order(StringComparer.Ordinal));
        Assert.Equal(3, counts["unit"]);
        Assert.Equal(2, counts["unit_search"]);
        Assert.Equal(0, counts["xref_idx"]);
        Assert.Equal(0, counts["sure"]);
        Assert.Equal(PackRows.Enumerate(Mixed()).Count(), counts.Values.Sum());
    }

    [Fact]
    public void Same_input_in_a_different_order_gives_the_same_row_sequence()
    {
        PackContent a = Mixed();
        PackContent b = new()
        {
            PackId = a.PackId,
            Flavor = a.Flavor,
            PackSources = [.. a.PackSources.Reverse()],
            Attributions = [.. a.Attributions.Reverse()],
            Units = [.. a.Units.Reverse()],
            UnitSearch = [.. a.UnitSearch.Reverse()],
            QuranMarkers = [.. a.QuranMarkers.Reverse()],
            PageMaps = [.. a.PageMaps.Reverse()],
        };

        string[] first = [.. PackRows.Enumerate(a).Select(r => Encoding.UTF8.GetString(PackRows.Canonical(r)))];
        string[] second = [.. PackRows.Enumerate(b).Select(r => Encoding.UTF8.GetString(PackRows.Canonical(r)))];

        Assert.Equal(first, second);
    }

    [Fact]
    public void Canonical_is_an_rfc8785_array_with_the_table_first()
    {
        PackRow row = new("xref_idx", ["id-1", "q:2:255", null, null, "k:a:p1", 3L, 8L, "atif", 0.5, PackRows.FromSingle(0.7f), 1L, 0L, "{}", "test"]);

        string json = Encoding.UTF8.GetString(PackRows.Canonical(row));

        Assert.Equal("[\"xref_idx\",\"id-1\",\"q:2:255\",null,null,\"k:a:p1\",3,8,\"atif\",0.5,0.7,1,0,\"{}\",\"test\"]", json);
    }

    [Fact]
    public void Canonical_writes_non_ascii_text_unescaped_in_utf8()
    {
        PackRow row = new("unit", [PackTestData.SyntheticArabic, "Işık \"tırnak\" \\ ters"]);

        string json = Encoding.UTF8.GetString(PackRows.Canonical(row));

        Assert.Contains(PackTestData.SyntheticArabic, json, StringComparison.Ordinal);
        Assert.Contains("Işık \\\"tırnak\\\" \\\\ ters", json, StringComparison.Ordinal);
        Assert.DoesNotContain("\\u", json, StringComparison.Ordinal);
    }

    [Fact]
    public void Canonical_rejects_unsupported_value_types()
    {
        Assert.Throws<ArgumentException>(() => PackRows.Canonical(new PackRow("unit", [1.5m])));
    }

    [Theory]
    [InlineData(0.7f, 0.7)]
    [InlineData(0.9f, 0.9)]
    [InlineData(0.1f, 0.1)]
    [InlineData(0.5f, 0.5)]
    [InlineData(1f, 1.0)]
    [InlineData(0f, 0.0)]
    public void FromSingle_gives_the_short_decimal_value_not_the_widened_float(float value, double expected)
    {
        Assert.Equal(expected, PackRows.FromSingle(value));
    }

    [Fact]
    public void FromSingle_differs_from_the_direct_widening()
    {
        // 0,7f -> double 0,699999988079071: kisa onlu gosterim bu degeri 0,7 yapar.
        Assert.NotEqual(0.7, (double)0.7f);
        Assert.Equal(0.7, PackRows.FromSingle(0.7f));
        Assert.Throws<ArgumentOutOfRangeException>(() => PackRows.FromSingle(float.NaN));
        Assert.Throws<ArgumentOutOfRangeException>(() => PackRows.FromSingle(float.PositiveInfinity));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void FromSingle_and_canonical_numbers_ignore_the_current_culture(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            Assert.Equal(0.7, PackRows.FromSingle(0.7f));
            Assert.Equal("[\"x\",0.7]", Encoding.UTF8.GetString(PackRows.Canonical(new PackRow("x", [PackRows.FromSingle(0.7f)]))));
        });
    }

    [Fact]
    public void Utf8Order_orders_supplementary_characters_after_the_bmp_unlike_ordinal()
    {
        string bmp = "a�";
        string supplementary = "a\U0001F600";

        // UTF-16 Ordinal: vekil birimi (D83D) FFFD'den kucuktur; UTF-8 bayt sirasi tersidir.
        Assert.True(string.CompareOrdinal(supplementary, bmp) < 0);
        Assert.True(Utf8Order.Instance.Compare(supplementary, bmp) > 0);
        Assert.True(Utf8Order.Instance.Compare(bmp, supplementary) < 0);
    }

    [Theory]
    [InlineData("q:1:1", "q:1:10")]
    [InlineData("q:1:10", "q:1:2")]
    [InlineData("a", "ab")]
    [InlineData("", "a")]
    [InlineData("Z", "a")]
    [InlineData("a", "a\U00010000")]
    [InlineData("퟿", "")]
    public void Utf8Order_agrees_with_the_utf8_byte_sequence_comparison(string smaller, string larger)
    {
        byte[] a = Encoding.UTF8.GetBytes(smaller);
        byte[] b = Encoding.UTF8.GetBytes(larger);

        Assert.True(a.AsSpan().SequenceCompareTo(b) < 0);
        Assert.True(Utf8Order.Instance.Compare(smaller, larger) < 0);
        Assert.True(Utf8Order.Instance.Compare(larger, smaller) > 0);
        Assert.Equal(0, Utf8Order.Instance.Compare(smaller, smaller));
    }

    [Fact]
    public void Utf8Order_places_null_first()
    {
        Assert.True(Utf8Order.Instance.Compare(null, "a") < 0);
        Assert.True(Utf8Order.Instance.Compare("a", null) > 0);
        Assert.Equal(0, Utf8Order.Instance.Compare(null, null));
    }
}
