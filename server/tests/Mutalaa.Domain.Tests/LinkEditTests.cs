using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Tests;

/// <summary>Baglanti duzeltmesi kurallari (A18.4): tur gecisleri, hedef capa, hedef araligi ve duzenlenen deger jsonb'si.</summary>
public class LinkEditTests
{
    private static readonly AnchorRef Ayah = AnchorRef.Parse("q:2:255");

    private static string CodeOf(Action action) => Assert.Throws<DomainException>(action).Code;

    private static LinkDstFacts Ayah10Words => new(true, 120, 10, "0123456789abcdef0123");

    private static LinkDstFacts Text40 => new(true, 40, 0, "0123456789abcdef0123");

    // --- Tur gecisleri ---

    [Theory]
    [InlineData(XrefType.Atif, XrefType.Iktibas)]
    [InlineData(XrefType.Atif, XrefType.Ima)]
    [InlineData(XrefType.Iktibas, XrefType.Atif)]
    [InlineData(XrefType.Iktibas, XrefType.Ima)]
    [InlineData(XrefType.Ima, XrefType.Atif)]
    [InlineData(XrefType.Ima, XrefType.Iktibas)]
    public void Atif_iktibas_and_ima_change_among_themselves(XrefType from, XrefType to)
    {
        Assert.True(LinkTypeTransitions.IsAllowed(from, to));
    }

    [Theory]
    [InlineData(XrefType.Kok)]
    [InlineData(XrefType.Lemma)]
    [InlineData(XrefType.BenzerAyet)]
    [InlineData(XrefType.Konu)]
    [InlineData(XrefType.Anlamsal)]
    public void Other_types_cannot_be_changed_or_become_an_editable_type(XrefType other)
    {
        Assert.False(LinkTypeTransitions.IsAllowed(other, XrefType.Iktibas));
        Assert.False(LinkTypeTransitions.IsAllowed(XrefType.Atif, other));
        Assert.False(LinkTypeTransitions.IsEditable(other));
        Assert.True(LinkTypeTransitions.IsAllowed(other, other));
    }

    [Fact]
    public void Resolve_refuses_a_forbidden_transition_with_inceleme_desteklenmiyor()
    {
        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => LinkEdits.Resolve(XrefType.Kok, Ayah, null, new LinkEditValue(null, null, XrefType.Iktibas))));
        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue(null, null, XrefType.BenzerAyet))));
    }

    // --- Cozum ---

    [Fact]
    public void A_type_only_edit_keeps_the_target_and_the_span()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Atif, Ayah, new AnchorSpan(3, 8), new LinkEditValue(null, null, XrefType.Ima));

        Assert.Equal(XrefType.Ima, result.Type);
        Assert.Equal(Ayah, result.DstAnchor);
        Assert.Equal(new AnchorSpan(3, 8), result.DstSpan);
        Assert.True(result.TypeChanged);
        Assert.False(result.DstUnitChanged);
        Assert.False(result.DstSpanChanged);
        Assert.True(result.Changed);
    }

    [Fact]
    public void A_span_only_edit_corrects_the_span_of_the_current_target()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Iktibas, Ayah, new AnchorSpan(3, 8), new LinkEditValue(null, new AnchorSpan(2, 6), null));

        Assert.Equal(new AnchorSpan(2, 6), result.DstSpan);
        Assert.True(result.DstSpanChanged);
        Assert.False(result.DstUnitChanged);
        Assert.False(result.TypeChanged);
    }

    [Fact]
    public void A_new_unit_anchor_without_a_span_means_the_whole_unit()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Iktibas, Ayah, new AnchorSpan(3, 8), new LinkEditValue("q:3:7", null, null));

        Assert.Equal(AnchorRef.Parse("q:3:7"), result.DstAnchor);
        Assert.Null(result.DstSpan);
        Assert.True(result.DstUnitChanged);
        Assert.True(result.DstSpanChanged);
    }

    [Fact]
    public void A_word_range_anchor_is_split_into_the_unit_and_a_word_position_span()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue("q:2:256:3-7", null, null));

        Assert.Equal(AnchorRef.Parse("q:2:256"), result.DstAnchor);
        Assert.Equal(new AnchorSpan(3, 8), result.DstSpan);
    }

    [Fact]
    public void A_single_word_anchor_gives_a_one_word_span()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue("q:2:255:3", null, null));

        Assert.Equal(Ayah, result.DstAnchor);
        Assert.Equal(new AnchorSpan(3, 4), result.DstSpan);
        Assert.False(result.DstUnitChanged);
    }

    [Fact]
    public void An_anchor_carrying_its_own_span_cannot_come_with_dst_span()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue("q:2:255:3-7", new AnchorSpan(1, 2), null))));
    }

    [Theory]
    [InlineData("q:2:255-257")] // ayet araligi uc olamaz
    [InlineData("rn:sozler:soz-10:p4:s2")] // cumle capasi toUnitSpan'de hata verir
    [InlineData("deneme")] // capa degil
    [InlineData("Q:2:255")]
    [InlineData("q:115:1")]
    public void A_bad_destination_anchor_is_a_validation_error(string anchor)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue(anchor, null, null))));
    }

    [Theory]
    [InlineData("meal:elmalili:2:255")]
    [InlineData("konu:tevhid")]
    [InlineData("rn:sozler:soz-10:p4")]
    public void The_target_of_an_editable_type_must_be_an_ayah_or_a_hadith(string anchor)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.Resolve(XrefType.Iktibas, Ayah, null, new LinkEditValue(anchor, null, null))));
    }

    [Fact]
    public void A_hadith_target_is_allowed_and_other_types_may_point_anywhere()
    {
        Assert.Equal(AnchorRef.Parse("h:buhari:52"), LinkEdits.Resolve(XrefType.Atif, Ayah, null, new LinkEditValue("h:buhari:52", null, null)).DstAnchor);
        Assert.Equal(AnchorRef.Parse("meal:elmalili:2:255"), LinkEdits.Resolve(XrefType.BenzerAyet, Ayah, null, new LinkEditValue("meal:elmalili:2:255", null, null)).DstAnchor);
    }

    [Fact]
    public void An_edit_equal_to_the_current_row_changes_nothing()
    {
        ResolvedLinkEdit result = LinkEdits.Resolve(XrefType.Iktibas, Ayah, new AnchorSpan(3, 8), new LinkEditValue("q:2:255:3-7", null, XrefType.Iktibas));

        Assert.False(result.Changed);
    }

    // --- Aralik siniri ---

    [Theory]
    [InlineData(1, 11)]
    [InlineData(3, 8)]
    [InlineData(10, 11)]
    public void A_quran_word_span_inside_the_ayah_is_valid(int start, int end)
    {
        LinkEdits.ValidateDstSpan(Ayah, new AnchorSpan(start, end), Ayah10Words);
    }

    [Theory]
    [InlineData(0, 3)] // kelime konumu 1'den baslar
    [InlineData(3, 3)] // bas < son
    [InlineData(5, 3)]
    [InlineData(1, 12)] // 10 kelime: son en cok 11
    [InlineData(11, 12)]
    [InlineData(-1, 3)]
    public void A_quran_word_span_outside_the_ayah_is_a_validation_error(int start, int end)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LinkEdits.ValidateDstSpan(Ayah, new AnchorSpan(start, end), Ayah10Words)));
    }

    [Fact]
    public void A_quran_span_needs_a_known_word_count()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.ValidateDstSpan(Ayah, new AnchorSpan(1, 2), new LinkDstFacts(true, 100, 0, null))));
    }

    [Theory]
    [InlineData(0, 40)]
    [InlineData(10, 30)]
    [InlineData(39, 40)]
    public void A_text_span_inside_the_code_point_length_is_valid(int start, int end)
    {
        LinkEdits.ValidateDstSpan(AnchorRef.Parse("h:buhari:52"), new AnchorSpan(start, end), Text40);
    }

    [Theory]
    [InlineData(-1, 5)]
    [InlineData(5, 5)]
    [InlineData(9, 3)]
    [InlineData(0, 41)]
    public void A_text_span_outside_the_code_point_length_is_a_validation_error(int start, int end)
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.ValidateDstSpan(AnchorRef.Parse("h:buhari:52"), new AnchorSpan(start, end), Text40)));
    }

    [Fact]
    public void A_text_span_needs_the_unit_row_and_a_topic_node_takes_no_span()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.ValidateDstSpan(AnchorRef.Parse("h:buhari:52"), new AnchorSpan(0, 3), new LinkDstFacts(false, 0, 0, null))));
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => LinkEdits.ValidateDstSpan(AnchorRef.Parse("konu:tevhid"), new AnchorSpan(0, 3), Text40)));
    }

    [Fact]
    public void No_span_is_always_valid()
    {
        LinkEdits.ValidateDstSpan(Ayah, null, default);
    }

    // --- Duzenlenen jsonb ---

    [Fact]
    public void The_payload_round_trips()
    {
        LinkEditValue value = new("q:2:255", new AnchorSpan(3, 8), XrefType.Ima);

        string json = LinkEditPayload.ToPayload(value);
        using JsonDocument document = JsonDocument.Parse(json);

        Assert.Equal(value, LinkEditPayload.Read(json, "duzenlenen"));
        Assert.Equal(3, document.RootElement.GetProperty("dst_span")[0].GetInt32());
        Assert.Equal(8, document.RootElement.GetProperty("dst_span")[1].GetInt32());
        Assert.Equal("ima", document.RootElement.GetProperty("type").GetString());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("null")]
    public void An_absent_payload_means_no_value(string? json)
    {
        Assert.Null(LinkEditPayload.Read(json, "duzenlenen"));
        Assert.False(LinkEditPayload.TryRead(json, out _));
    }

    [Theory]
    [InlineData("{bozuk")]
    [InlineData("[1]")]
    [InlineData("{}")]
    [InlineData("""{"dst_anchor": 5}""")]
    [InlineData("""{"dst_anchor": ""}""")]
    [InlineData("""{"type": "bilinmeyen"}""")]
    [InlineData("""{"type": 3}""")]
    [InlineData("""{"dst_span": [1]}""")]
    [InlineData("""{"dst_span": [1, 2, 3]}""")]
    [InlineData("""{"dst_span": ["a", "b"]}""")]
    [InlineData("""{"dst_span": [1.5, 2]}""")]
    [InlineData("""{"dst_span": "1-2"}""")]
    [InlineData("""{"metin": "x"}""")]
    public void A_malformed_payload_is_a_validation_error(string json)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LinkEditPayload.Read(json, "duzenlenen")));
        Assert.False(LinkEditPayload.TryRead(json, out _));
    }
}
