using System.Text.RegularExpressions;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>review.hedef_tablo sabitleri ve hedef_anahtar ayristirma (K-48). Her sinama tr-TR kulturunde de calisir.</summary>
public partial class ReviewTargetsTests
{
    private static readonly string[] Thirteen =
    [
        "source", "unit", "quran_word_fix", "lemma", "lemma_gloss", "root", "tr_root_index", "tr_form", "surah_alias", "xref", "page_map",
        "ayah_box", "audio_timing",
    ];

    [GeneratedRegex(@"hedef_tablo IN \(([^)]*)\)", RegexOptions.CultureInvariant)]
    private static partial Regex CheckList();

    [Fact]
    public void All_lists_the_13_targets_in_the_order_of_the_ddl_check()
    {
        Assert.Equal(Thirteen, ReviewTargets.All);

        Match match = CheckList().Match(EditorialDoc.Section(EditorialDoc.Read(), 8));
        Assert.True(match.Success);
        string[] inDoc = [.. match.Groups[1].Value.Split(',').Select(s => s.Trim().Trim('\''))];
        Assert.Equal(inDoc, ReviewTargets.All);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void IsKnown_is_ordinal_and_case_sensitive(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (string target in Thirteen)
        {
            Assert.True(ReviewTargets.IsKnown(target));
        }

        Assert.False(ReviewTargets.IsKnown("UNIT"));
        Assert.False(ReviewTargets.IsKnown("Unit"));
        Assert.False(ReviewTargets.IsKnown("units"));
        Assert.False(ReviewTargets.IsKnown(string.Empty));
        Assert.False(ReviewTargets.IsKnown(null));
    });

    [Fact]
    public void Status_column_targets_are_the_five_xref_status_tables_and_unit()
    {
        string[] withStatus = [.. Thirteen.Where(ReviewTargets.HasStatusColumn)];

        Assert.Equal(["unit", "quran_word_fix", "lemma", "lemma_gloss", "surah_alias", "xref"], withStatus);
    }

    [Fact]
    public void Only_six_targets_support_review_decisions()
    {
        string[] supported = [.. Thirteen.Where(ReviewTargets.IsSupported)];

        Assert.Equal(["unit", "quran_word_fix", "lemma", "lemma_gloss", "surah_alias", "xref"], supported);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Unit_keys_are_unit_level_anchors(bool turkish) => CultureScope.For(turkish, () =>
    {
        foreach (string key in new[] { "q:2:255", "meal:test:2:255", "tf:test:2-255-257:p3", "tf:test:mukaddime:p4", "rn:test:bolum-1:p4", "h:test:52", "ht:test:test:15", "k:test:bolum:p2" })
        {
            ReviewTarget target = ReviewTargets.Parse("unit", key);

            Assert.Equal("unit", target.Table);
            Assert.Equal(AnchorRef.Parse(key), target.Anchor);
            Assert.Null(target.Id);
            Assert.Null(target.LemmaId);
            Assert.Null(target.SurahNo);
        }
    });

    [Theory]
    [InlineData("q:2:255:3")]
    [InlineData("q:2:255:3-7")]
    [InlineData("q:2:255-257")]
    [InlineData("konu:tevhid")]
    [InlineData("meal:test:2:255@0-5")]
    [InlineData("rn:test:bolum-1:p4:s2")]
    [InlineData("rn:test:bolum-1:p4@1-5")]
    [InlineData("Q:2:255")]
    [InlineData("bozuk")]
    [InlineData("")]
    public void Unit_keys_that_are_not_unit_level_anchors_are_rejected(string key) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse("unit", key)));

    [Fact]
    public void Surah_alias_keys_split_at_the_first_colon()
    {
        ReviewTarget simple = ReviewTargets.Parse("surah_alias", "2:test-ad");
        ReviewTarget withColon = ReviewTargets.Parse("surah_alias", "114:ad:ek:parca");
        ReviewTarget first = ReviewTargets.Parse("surah_alias", "1:a");

        Assert.Equal((2, "test-ad"), (simple.SurahNo!.Value, simple.Alias));
        Assert.Equal((114, "ad:ek:parca"), (withColon.SurahNo!.Value, withColon.Alias));
        Assert.Equal(1, first.SurahNo);
    }

    [Theory]
    [InlineData("0:x")]
    [InlineData("115:x")]
    [InlineData("02:x")]
    [InlineData("+2:x")]
    [InlineData("-1:x")]
    [InlineData("a:x")]
    [InlineData(":x")]
    [InlineData("2:")]
    [InlineData("2")]
    [InlineData("2147483648:x")]
    public void Bad_surah_alias_keys_are_rejected(string key) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse("surah_alias", key)));

    [Theory]
    [InlineData("xref")]
    [InlineData("quran_word_fix")]
    public void Guid_targets_parse_the_canonical_guid_form(string table)
    {
        Guid id = Guid.Parse("0197a3b2-0000-7000-8000-000000000001");

        ReviewTarget target = ReviewTargets.Parse(table, id.ToString("D"));

        Assert.Equal(id, target.Id);
        Assert.Equal(table, target.Table);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, "{" + id.ToString("D") + "}")));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, id.ToString("N"))));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, "bozuk")));
    }

    [Theory]
    [InlineData("lemma", "12", 12)]
    [InlineData("lemma_gloss", "1", 1)]
    [InlineData("lemma", "2147483647", int.MaxValue)]
    public void Lemma_targets_parse_a_canonical_positive_integer(string table, string key, int expected)
    {
        ReviewTarget target = ReviewTargets.Parse(table, key);

        Assert.Equal(expected, target.LemmaId);
        Assert.Equal(table, target.Table);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("012")]
    [InlineData("-1")]
    [InlineData("+1")]
    [InlineData("1.5")]
    [InlineData(" 1")]
    [InlineData("1 ")]
    [InlineData("2147483648")]
    [InlineData("abc")]
    public void Bad_lemma_ids_are_rejected(string key)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse("lemma", key)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse("lemma_gloss", key)));
    }

    [Theory]
    [InlineData("source")]
    [InlineData("root")]
    [InlineData("tr_root_index")]
    [InlineData("tr_form")]
    [InlineData("page_map")]
    [InlineData("ayah_box")]
    [InlineData("audio_timing")]
    public void Unsupported_targets_are_not_parsed(string table) =>
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewTargets.Parse(table, "1")));

    [Theory]
    [InlineData("bilinmeyen")]
    [InlineData("UNIT")]
    [InlineData("")]
    [InlineData(null)]
    public void Unknown_tables_are_a_validation_error(string? table) =>
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, "1")));

    [Theory]
    [InlineData("unit")]
    [InlineData("xref")]
    [InlineData("lemma")]
    [InlineData("surah_alias")]
    public void Empty_keys_are_a_validation_error(string table)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, string.Empty)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewTargets.Parse(table, null)));
    }
}
