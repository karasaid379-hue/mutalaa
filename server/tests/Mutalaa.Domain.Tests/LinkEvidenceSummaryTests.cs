using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>Kanit ozeti (beyaz liste), kanit duzeltmesi ve vurgulu dizi (A18.4). Metinler sentetiktir ("Deneme paragrafi ...").</summary>
public class LinkEvidenceSummaryTests
{
    private const string Hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private const string Hash16 = "0123456789abcdef";

    [Fact]
    public void Only_whitelisted_keys_pass_and_unknown_keys_are_dropped()
    {
        string json = """
            {"matched_words": 9, "ayah_words": 12, "coverage": 0.75, "identity": 0.9, "phrase_freq": 1,
             "consistent_quote": true, "position": "baslik", "subtype": "sozluksel", "group": "g-1",
             "src_hash": "0123456789abcdef", "dst_hash": "fedcba9876543210", "source_id": "deneme",
             "run_id": "gizli", "llm": {"x": 1}, "context": "ic ayrinti", "edits": 2}
            """;

        using JsonDocument summary = JsonDocument.Parse(LinkEvidenceSummary.Build(json)!);
        string[] names = [.. summary.RootElement.EnumerateObject().Select(p => p.Name)];

        Assert.Equal(
            ["matched_words", "ayah_words", "coverage", "identity", "phrase_freq", "consistent_quote", "position", "subtype", "src_hash", "dst_hash", "source_id", "group"],
            names);
        Assert.Equal(9, summary.RootElement.GetProperty("matched_words").GetInt32());
        Assert.True(summary.RootElement.GetProperty("consistent_quote").GetBoolean());
        Assert.Equal("g-1", summary.RootElement.GetProperty("group").GetString());
    }

    [Fact]
    public void Values_of_the_wrong_type_or_too_long_are_dropped()
    {
        string longText = new('x', LinkEvidenceSummary.MaxStringLength + 1);
        string json = $$"""{"matched_words": "9", "coverage": true, "consistent_quote": "evet", "position": 5, "subtype": "{{longText}}", "group": {"a": 1}, "alternatives": "yok"}""";

        Assert.Equal("{}", LinkEvidenceSummary.Build(json));
    }

    [Fact]
    public void Alternatives_keep_only_scalar_properties_and_at_most_ten_items()
    {
        string items = string.Join(",", Enumerable.Range(1, 14).Select(i => $$"""{"dst_anchor": "q:2:{{i}}", "confidence": 0.5, "gizli": {"x": 1}, "liste": [1]}"""));

        using JsonDocument summary = JsonDocument.Parse(LinkEvidenceSummary.Build($$"""{"alternatives": [{{items}}, 7, "metin", null, [1]]}""")!);
        JsonElement alternatives = summary.RootElement.GetProperty("alternatives");

        Assert.Equal(LinkEvidenceSummary.MaxAlternatives, alternatives.GetArrayLength());
        JsonElement first = alternatives[0];
        Assert.Equal(["dst_anchor", "confidence"], first.EnumerateObject().Select(p => p.Name).ToArray());
    }

    [Fact]
    public void Scalar_alternatives_pass_and_nested_ones_do_not()
    {
        using JsonDocument summary = JsonDocument.Parse(LinkEvidenceSummary.Build("""{"alternatives": [7, "metin", null, [1], true]}""")!);

        Assert.Equal(3, summary.RootElement.GetProperty("alternatives").GetArrayLength());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("  ")]
    [InlineData("{bozuk")]
    [InlineData("[1]")]
    [InlineData("\"metin\"")]
    public void Unreadable_evidence_has_no_summary(string? evidence)
    {
        Assert.Null(LinkEvidenceSummary.Build(evidence));
    }

    [Fact]
    public void An_editor_correction_marks_the_evidence_keeps_the_rest_and_replaces_dst_hash_only_when_given()
    {
        string json = """{"matched_words": 9, "src_hash": "aaaaaaaaaaaaaaaa", "dst_hash": "bbbbbbbbbbbbbbbb", "run_id": "r1"}""";

        using JsonDocument same = JsonDocument.Parse(LinkEvidenceSummary.WithEditorCorrection(json, null));
        Assert.True(same.RootElement.GetProperty("editor_duzeltmesi").GetBoolean());
        Assert.Equal("bbbbbbbbbbbbbbbb", same.RootElement.GetProperty("dst_hash").GetString());
        Assert.Equal("r1", same.RootElement.GetProperty("run_id").GetString());

        using JsonDocument moved = JsonDocument.Parse(LinkEvidenceSummary.WithEditorCorrection(json, Hash16));
        Assert.Equal(Hash16, moved.RootElement.GetProperty("dst_hash").GetString());
        Assert.Equal("aaaaaaaaaaaaaaaa", moved.RootElement.GetProperty("src_hash").GetString());
        Assert.Equal(1, moved.RootElement.EnumerateObject().Count(p => p.Name == "dst_hash"));
        Assert.Equal(1, moved.RootElement.EnumerateObject().Count(p => p.Name == "editor_duzeltmesi"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("{bozuk")]
    [InlineData("[1]")]
    public void An_editor_correction_starts_from_an_empty_object_when_the_evidence_is_unreadable(string? evidence)
    {
        using JsonDocument result = JsonDocument.Parse(LinkEvidenceSummary.WithEditorCorrection(evidence, Hash16));

        Assert.Equal(["dst_hash", "editor_duzeltmesi"], result.RootElement.EnumerateObject().Select(p => p.Name).ToArray());
    }

    [Fact]
    public void Hash16_is_the_first_sixteen_digits()
    {
        Assert.Equal(Hash16, LinkEvidenceSummary.Hash16(Hash));
        Assert.Null(LinkEvidenceSummary.Hash16("kisa"));
        Assert.Null(LinkEvidenceSummary.Hash16(null));
    }

    // --- Vurgulu dizi ---

    private static string Text(int length) => string.Concat(Enumerable.Range(0, length).Select(i => (char)('a' + (i % 26))));

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_highlight_is_the_span_slice_with_forty_code_points_of_context(bool turkish) => CultureScope.For(turkish, () =>
    {
        string text = Text(200);

        HighlightedSequence result = LinkHighlight.Compute(text, Hash, Hash16, new AnchorSpan(100, 110));

        Assert.Equal(text[60..100], result.Sol);
        Assert.Equal(text[100..110], result.Dizi);
        Assert.Equal(text[110..150], result.Sag);
    });

    [Fact]
    public void The_context_is_cut_at_the_unit_edges()
    {
        string text = Text(60);

        HighlightedSequence result = LinkHighlight.Compute(text, Hash, Hash16, new AnchorSpan(5, 58));

        Assert.Equal(text[..5], result.Sol);
        Assert.Equal(text[5..58], result.Dizi);
        Assert.Equal(text[58..], result.Sag);
    }

    [Fact]
    public void A_null_span_highlights_the_whole_unit()
    {
        HighlightedSequence result = LinkHighlight.Compute("Deneme paragrafi 1", Hash, Hash16, null);

        Assert.Equal(string.Empty, result.Sol);
        Assert.Equal("Deneme paragrafi 1", result.Dizi);
        Assert.Equal(string.Empty, result.Sag);
    }

    [Fact]
    public void Offsets_are_code_points_not_utf16_units()
    {
        // U+1F600 iki UTF-16 birimidir ama tek kod noktasi; ofset kod noktasiyla sayilir.
        string text = "ab\U0001F600cd\U0001F600ef";

        HighlightedSequence result = LinkHighlight.Compute(text, Hash, Hash16, new AnchorSpan(2, 5));

        Assert.Equal("ab", result.Sol);
        Assert.Equal("\U0001F600cd", result.Dizi);
        Assert.Equal("\U0001F600ef", result.Sag);
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(5, 5)]
    [InlineData(6, 5)]
    [InlineData(-1, 4)]
    [InlineData(0, 19)]
    public void A_span_outside_the_text_gives_no_highlight(int start, int end)
    {
        Assert.Equal(HighlightedSequence.None, LinkHighlight.Compute("Deneme paragrafi 1", Hash, Hash16, new AnchorSpan(start, end)));
    }

    [Theory]
    [InlineData(null, Hash, Hash16)]
    [InlineData("Deneme", null, Hash16)]
    [InlineData("Deneme", Hash, null)]
    [InlineData("Deneme", Hash, "")]
    [InlineData("Deneme", Hash, "0123456789abcde")]
    [InlineData("Deneme", Hash, "fedcba9876543210")]
    public void A_missing_or_mismatching_hash_gives_no_highlight(string? text, string? contentHash, string? srcHash)
    {
        Assert.Equal(HighlightedSequence.None, LinkHighlight.Compute(text, contentHash, srcHash, new AnchorSpan(0, 3)));
    }

    [Fact]
    public void The_hash_compare_is_ordinal_and_case_sensitive()
    {
        Assert.Equal(HighlightedSequence.None, LinkHighlight.Compute("Deneme", Hash, Hash16.ToUpperInvariant(), new AnchorSpan(0, 3)));
    }
}
