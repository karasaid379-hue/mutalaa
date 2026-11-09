using System.Text.Json;
using System.Text.RegularExpressions;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

public class ReleaseVersionTests
{
    [Theory]
    [InlineData("2026.11.0", 2026, 11, 0)]
    [InlineData("2026.1.7", 2026, 1, 7)]
    [InlineData("2026.12.123", 2026, 12, 123)]
    [InlineData("0001.9.10", 1, 9, 10)]
    [InlineData("2026.11.2147483647", 2026, 11, int.MaxValue)]
    public void TryParse_accepts_calver(string text, int year, int month, int number)
    {
        foreach (bool turkish in new[] { false, true })
        {
            CultureScope.For(turkish, () =>
            {
                Assert.True(ReleaseVersion.TryParse(text, out ReleaseVersion v));
                Assert.Equal(new ReleaseVersion(year, month, number), v);
                Assert.Equal(text, v.ToString());
            });
        }
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("2026")]
    [InlineData("2026.11")]
    [InlineData("2026.11.0.1")]
    [InlineData("26.11.0")]
    [InlineData("02026.11.0")]
    [InlineData("2026.0.1")]
    [InlineData("2026.00.1")]
    [InlineData("2026.01.1")]
    [InlineData("2026.13.0")]
    [InlineData("2026.99.0")]
    [InlineData("2026.11.01")]
    [InlineData("2026.11.00")]
    [InlineData("2026.11.")]
    [InlineData("2026..1")]
    [InlineData("2026.11.-1")]
    [InlineData("2026.11.+1")]
    [InlineData("2026.11.1.5")]
    [InlineData(" 2026.11.1")]
    [InlineData("2026.11.1 ")]
    [InlineData("2026.11.2147483648")]
    [InlineData("2026.11.99999999999999999999")]
    [InlineData("2026-11-1")]
    [InlineData("v2026.11.1")]
    [InlineData("2026.11.1\n")]
    public void TryParse_rejects_everything_else(string? text)
    {
        foreach (bool turkish in new[] { false, true })
        {
            CultureScope.For(turkish, () =>
            {
                Assert.False(ReleaseVersion.TryParse(text, out ReleaseVersion v));
                Assert.Equal(default, v);
            });
        }
    }

    [Fact]
    public void TryParse_rejects_non_ascii_digits()
    {
        // ARABIC-INDIC DIGIT: ayrik kod noktalariyla yazilir.
        string arabicTwo = char.ConvertFromUtf32(0x0662);
        Assert.False(ReleaseVersion.TryParse("2026.11." + arabicTwo, out _));
        Assert.False(ReleaseVersion.TryParse(arabicTwo + "026.11.1", out _));
        Assert.False(ReleaseVersion.TryParse("2026." + arabicTwo + ".1", out _));
    }

    [Fact]
    public void Next_without_any_version_starts_at_zero()
    {
        ReleaseVersion v = ReleaseVersion.Next(new DateOnly(2026, 11, 9), []);

        Assert.Equal("2026.11.0", v.ToString());
    }

    [Fact]
    public void Next_is_one_more_than_the_largest_number_of_the_same_month_numerically()
    {
        // Metin sirasinda "2026.11.9" > "2026.11.10"; sayisal en buyuk 10'dur.
        string[] existing = ["2026.11.0", "2026.11.9", "2026.11.10", "2026.11.2"];

        Assert.Equal("2026.11.11", ReleaseVersion.Next(new DateOnly(2026, 11, 30), existing).ToString());
    }

    [Fact]
    public void Next_ignores_other_months_other_years_and_unparseable_values()
    {
        string[] existing = ["2026.10.5", "2025.11.8", "2027.11.3", "2026.11.x", "2026.11.01", "bozuk", string.Empty, "2026.11.1"];

        Assert.Equal("2026.11.2", ReleaseVersion.Next(new DateOnly(2026, 11, 1), existing).ToString());
        Assert.Equal("2026.12.0", ReleaseVersion.Next(new DateOnly(2026, 12, 1), existing).ToString());
        Assert.Equal("2026.10.6", ReleaseVersion.Next(new DateOnly(2026, 10, 31), existing).ToString());
    }

    [Fact]
    public void Next_overflow_throws()
    {
        Assert.Throws<InvalidOperationException>(() => ReleaseVersion.Next(new DateOnly(2026, 11, 1), ["2026.11.2147483647"]));
        Assert.Throws<ArgumentNullException>(() => ReleaseVersion.Next(new DateOnly(2026, 11, 1), null!));
    }

    [Fact]
    public void Next_gives_the_same_result_under_turkish_culture()
    {
        string[] existing = ["2026.11.0", "2026.11.1"];
        string invariant = string.Empty;
        string turkish = string.Empty;

        CultureScope.Invariant(() => invariant = ReleaseVersion.Next(new DateOnly(2026, 11, 9), existing).ToString());
        CultureScope.Turkish(() => turkish = ReleaseVersion.Next(new DateOnly(2026, 11, 9), existing).ToString());

        Assert.Equal("2026.11.2", invariant);
        Assert.Equal(invariant, turkish);
    }

    [Fact]
    public void Ordering_is_numeric()
    {
        ReleaseVersion[] sorted = [.. new[]
        {
            new ReleaseVersion(2026, 11, 10),
            new ReleaseVersion(2026, 2, 3),
            new ReleaseVersion(2026, 11, 9),
            new ReleaseVersion(2025, 12, 99),
        }.Order()];

        Assert.Equal(["2025.12.99", "2026.2.3", "2026.11.9", "2026.11.10"], sorted.Select(v => v.ToString()));
    }

    [Fact]
    public void Parser_agrees_with_manifest_schema_pattern()
    {
        string schemaPath = FindUpwards(Path.Combine("packages", "content-schema", "manifest.schema.json"));
        using JsonDocument doc = JsonDocument.Parse(File.ReadAllText(schemaPath));
        string pattern = doc.RootElement.GetProperty("properties").GetProperty("release").GetProperty("pattern").GetString()!;
        Regex regex = new(pattern, RegexOptions.CultureInvariant);

        // Taşma disinda desenle ayni; N'nin int'e sigmasi ek kisittir (desen sinirsiz hane kabul eder).
        string[] candidates =
        [
            "2026.11.0", "2026.1.0", "2026.12.5", "2026.13.0", "2026.0.0", "2026.01.0", "2026.11.00", "2026.11.01", "2026.11.10",
            "026.11.0", "20266.11.0", "2026.11", "2026.11.0.0", "2026.11.", ".11.0", "2026.11.0\n", " 2026.11.0",
            "٢026.11.0", "2026.11.٢", "2026.٢.1", "2026.11.-0",
        ];

        foreach (string c in candidates)
        {
            Assert.True(regex.IsMatch(c) == ReleaseVersion.TryParse(c, out _), c);
        }
    }

    private static string FindUpwards(string relative)
    {
        DirectoryInfo? dir = new(AppContext.BaseDirectory);
        while (dir is not null)
        {
            string candidate = Path.Combine(dir.FullName, relative);
            if (File.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new FileNotFoundException($"{relative} bulunamadi.");
    }
}
