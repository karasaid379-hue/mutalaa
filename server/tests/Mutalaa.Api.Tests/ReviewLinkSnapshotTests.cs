using System.Globalization;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Baglanti incelemesi hedef anlik goruntusu (A18.4): tur, araliklar, puanlar, koken, kanit ozeti (beyaz liste), vurgulu dizi ve sinif;
/// listede sinif, dalga ve onay yolu. Veri sentetiktir (Docker'li).
/// </summary>
public class ReviewLinkSnapshotTests(EditorialDatabase<ReviewLinkSnapshotTests> fixture)
    : LinkTestBase<ReviewLinkSnapshotTests>(fixture), IClassFixture<EditorialDatabase<ReviewLinkSnapshotTests>>
{
    private async Task<(World World, Xref Xref, Review Review)> SeedCandidateAsync(
        Func<World, string> evidence,
        AnchorSpan? srcSpan,
        AnchorSpan? dstSpan = null,
        XrefType type = XrefType.Iktibas,
        float confidence = 0.55f)
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(type, confidence, evidence(world), srcSpan: srcSpan, dstSpan: dstSpan);
        Review review = await SeedLinkReviewAsync(xref);
        return (world, xref, review);
    }

    [Fact]
    public async Task The_detail_snapshot_carries_type_spans_scores_origin_class_and_the_whitelisted_evidence()
    {
        (World world, Xref xref, Review review) = await SeedCandidateAsync(
            w => Evidence(w.Src, ("matched_words", 9), ("ayah_words", 12), ("coverage", 0.75), ("phrase_freq", 2), ("position", "baslik"), ("run_id", "gizli"), ("llm", new { x = 1 })),
            new AnchorSpan(60, 70),
            new AnchorSpan(3, 8));
        using HttpClient client = await ClientAsync();

        JsonElement detail = await DetailAsync(client, review.Id);
        JsonElement hedef = detail.GetProperty("hedef");

        Assert.Equal("xref", hedef.GetProperty("tablo").GetString());
        Assert.Equal(xref.Id.ToString("D"), hedef.GetProperty("id").GetString());
        Assert.Equal("rn:sozler:soz-10:p4", hedef.GetProperty("src_anchor").GetString());
        Assert.Equal("q:2:255", hedef.GetProperty("dst_anchor").GetString());
        Assert.Equal("iktibas", hedef.GetProperty("type").GetString());
        Assert.Equal([60, 70], hedef.GetProperty("src_span").EnumerateArray().Select(e => e.GetInt32()).ToArray());
        Assert.Equal([3, 8], hedef.GetProperty("dst_span").EnumerateArray().Select(e => e.GetInt32()).ToArray());
        Assert.Equal(0.55f, hedef.GetProperty("score").GetSingle());
        Assert.Equal(0.55f, hedef.GetProperty("confidence").GetSingle());
        Assert.Equal("hat", hedef.GetProperty("origin").GetString());
        Assert.Equal("aday", hedef.GetProperty("status").GetString());
        Assert.Equal("gri", hedef.GetProperty("sinif").GetString());
        Assert.Equal("gri", detail.GetProperty("sinif").GetString());

        JsonElement evidence = hedef.GetProperty("evidence_ozeti");
        Assert.Equal(9, evidence.GetProperty("matched_words").GetInt32());
        Assert.Equal(12, evidence.GetProperty("ayah_words").GetInt32());
        Assert.Equal(0.75, evidence.GetProperty("coverage").GetDouble());
        Assert.Equal("baslik", evidence.GetProperty("position").GetString());
        Assert.Equal(world.Src.ContentHash[..16], evidence.GetProperty("src_hash").GetString());
        Assert.False(evidence.TryGetProperty("run_id", out _));
        Assert.False(evidence.TryGetProperty("llm", out _));
    }

    [Fact]
    public async Task Missing_spans_are_omitted_meaning_the_whole_unit()
    {
        (_, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src), srcSpan: new AnchorSpan(1, 2));
        await Db.ExecuteAsync("UPDATE icerik.xref SET src_span = NULL, dst_span = NULL", Ct);
        using HttpClient client = await ClientAsync();

        JsonElement hedef = (await DetailAsync(client, review.Id)).GetProperty("hedef");

        Assert.False(hedef.TryGetProperty("src_span", out _));
        Assert.False(hedef.TryGetProperty("dst_span", out _));
        JsonElement highlight = hedef.GetProperty("vurgulu_dizi");
        Assert.Equal(string.Empty, highlight.GetProperty("sol").GetString());
        Assert.Equal(SrcText, highlight.GetProperty("dizi").GetString());
        Assert.Equal(string.Empty, highlight.GetProperty("sag").GetString());
    }

    [Fact]
    public async Task The_highlighted_sequence_is_the_code_point_slice_with_forty_points_of_context()
    {
        (_, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src), new AnchorSpan(60, 70));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(CodePointOffsets.Slice(SrcText, 20, 60), highlight.GetProperty("sol").GetString());
        Assert.Equal(CodePointOffsets.Slice(SrcText, 60, 70), highlight.GetProperty("dizi").GetString());
        Assert.Equal(CodePointOffsets.Slice(SrcText, 70, 110), highlight.GetProperty("sag").GetString());
    }

    [Fact]
    public async Task The_context_is_clipped_at_the_unit_start_and_end()
    {
        int length = CodePointOffsets.CodePointCount(SrcText);
        (_, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src), new AnchorSpan(3, length - 2));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(CodePointOffsets.Slice(SrcText, 0, 3), highlight.GetProperty("sol").GetString());
        Assert.Equal(CodePointOffsets.Slice(SrcText, length - 2, length), highlight.GetProperty("sag").GetString());
    }

    [Fact]
    public async Task Supplementary_characters_count_as_one_code_point_in_the_slice()
    {
        World world = await SeedWorldAsync();
        string text = "ab\U0001F600cd\U0001F600ef";
        Unit src = await SeedUnitAsync(world.RisaleSource, UnitKind.Risale, "rn:sozler:soz-11:p1", text, TextStatus.Onayli);
        Xref xref = await SeedXrefAsync(evidence: Evidence(src), src: "rn:sozler:soz-11:p1", srcSpan: new AnchorSpan(2, 5));
        Review review = await SeedLinkReviewAsync(xref);
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal("ab", highlight.GetProperty("sol").GetString());
        Assert.Equal("\U0001F600cd", highlight.GetProperty("dizi").GetString());
        Assert.Equal("\U0001F600ef", highlight.GetProperty("sag").GetString());
    }

    [Fact]
    public async Task A_src_hash_that_does_not_match_the_unit_gives_null_fields()
    {
        (_, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src, ("src_hash", "ffffffffffffffff")), new AnchorSpan(60, 70));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("sol").ValueKind);
        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("dizi").ValueKind);
        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("sag").ValueKind);
    }

    [Fact]
    public async Task A_unit_text_changed_after_the_candidate_was_written_gives_null_fields()
    {
        (World world, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src), new AnchorSpan(60, 70));
        string changed = SrcText + " degisti";
        await Db.ExecuteAsync(
            "UPDATE icerik.unit SET metin = @m, content_hash = @h WHERE anchor = 'rn:sozler:soz-10:p4'",
            Ct,
            ("m", changed),
            ("h", ContentHash.Compute(changed)));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("dizi").ValueKind);
        Assert.NotEqual(world.Src.ContentHash, ContentHash.Compute(changed));
    }

    [Fact]
    public async Task A_missing_src_hash_gives_null_fields_because_the_offsets_cannot_be_trusted()
    {
        (_, _, Review review) = await SeedCandidateAsync(_ => "{}", new AnchorSpan(60, 70));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("dizi").ValueKind);
    }

    [Theory]
    [InlineData(500, 520)] // metin disinda
    [InlineData(10, 9999)]
    public async Task A_span_outside_the_unit_text_gives_null_fields(int start, int end)
    {
        (_, _, Review review) = await SeedCandidateAsync(w => Evidence(w.Src), new AnchorSpan(start, end));
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("sol").ValueKind);
        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("dizi").ValueKind);
        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("sag").ValueKind);
    }

    [Fact]
    public async Task A_source_unit_that_does_not_exist_gives_null_fields()
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(evidence: Evidence(world.Src), src: "rn:sozler:soz-99:p9", srcSpan: new AnchorSpan(1, 4));
        Review review = await SeedLinkReviewAsync(xref);
        using HttpClient client = await ClientAsync();

        JsonElement highlight = (await DetailAsync(client, review.Id)).GetProperty("hedef").GetProperty("vurgulu_dizi");

        Assert.Equal(JsonValueKind.Null, highlight.GetProperty("dizi").ValueKind);
    }

    [Fact]
    public async Task A_quran_source_end_is_never_sliced_because_its_span_is_a_word_position()
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(
            XrefType.Kok,
            0.8f,
            Evidence(world.Ayah),
            src: AyahAnchor,
            srcSpan: new AnchorSpan(2, 4),
            dst: OtherAyahAnchor);
        Review review = await SeedLinkReviewAsync(xref);
        using HttpClient client = await ClientAsync();

        JsonElement hedef = (await DetailAsync(client, review.Id)).GetProperty("hedef");

        Assert.Equal(JsonValueKind.Null, hedef.GetProperty("vurgulu_dizi").GetProperty("dizi").ValueKind);
        Assert.Equal([2, 4], hedef.GetProperty("src_span").EnumerateArray().Select(e => e.GetInt32()).ToArray());
        Assert.Equal("kok", hedef.GetProperty("type").GetString());
    }

    [Fact]
    public async Task Non_xref_snapshots_do_not_carry_link_fields()
    {
        World world = await SeedWorldAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(source);
        Lemma lemma = await SeedLemmaAsync(source, root.Id);
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement detail = await DetailAsync(client, review.Id);

        Assert.False(detail.GetProperty("hedef").TryGetProperty("vurgulu_dizi", out _));
        Assert.False(detail.GetProperty("hedef").TryGetProperty("evidence_ozeti", out _));
        Assert.False(detail.TryGetProperty("sinif", out _));
        Assert.NotNull(world);
    }

    [Fact]
    public async Task The_list_item_carries_the_class_of_xref_targets_only()
    {
        World world = await SeedWorldAsync();
        Xref strong = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Review strongReview = await SeedLinkReviewAsync(strong);
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Lemma lemma = await SeedLemmaAsync(source);
        Review lemmaReview = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement list = await ListAsync(client, "limit=10");
        JsonElement strongItem = list.GetProperty("items").EnumerateArray().Single(i => i.GetProperty("id").GetInt64() == strongReview.Id);
        JsonElement lemmaItem = list.GetProperty("items").EnumerateArray().Single(i => i.GetProperty("id").GetInt64() == lemmaReview.Id);

        Assert.Equal("toplu", strongItem.GetProperty("sinif").GetString());
        Assert.False(lemmaItem.TryGetProperty("sinif", out _));
    }

    [Fact]
    public async Task The_list_item_carries_the_wave_and_the_approval_path_of_lemma_targets()
    {
        await ResetLinksAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(source);
        Lemma ar = await SeedLemmaAsync(source, root.Id);
        Lemma tr = await SeedLemmaAsync(source, root.Id, "tr-deneme", status: XrefStatus.Aday, origin: "kaikki", lang: "tr");
        await Db.ExecuteAsync(
            "UPDATE icerik.lemma SET status = 'onayli', onay_yolu = 'otomatik', kanit = '{}'::jsonb WHERE id = @id",
            Ct,
            ("id", tr.Id));
        await SeedWaveAsync(tr.Id, 2, 5);
        Review trReview = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = tr.Id.ToString(CultureInfo.InvariantCulture),
            Alan = "kok_eslemesi",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Editor,
            Oneren = "editor-x",
            Onerilen = "{\"itiraz\": true, \"gerekce\": \"Deneme\"}",
        });
        Review noWave = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = ar.Id.ToString(CultureInfo.InvariantCulture),
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement list = await ListAsync(client, "hedef_tablo=lemma&limit=10");
        JsonElement trItem = list.GetProperty("items").EnumerateArray().Single(i => i.GetProperty("id").GetInt64() == trReview.Id);
        JsonElement arItem = list.GetProperty("items").EnumerateArray().Single(i => i.GetProperty("id").GetInt64() == noWave.Id);

        Assert.Equal(2, trItem.GetProperty("dalga").GetInt32());
        Assert.Equal("otomatik", trItem.GetProperty("onay_yolu").GetString());
        Assert.False(arItem.TryGetProperty("dalga", out _));
        Assert.False(arItem.TryGetProperty("onay_yolu", out _));

        JsonElement detail = await DetailAsync(client, trReview.Id);
        Assert.Equal(2, detail.GetProperty("dalga").GetInt32());
        Assert.Equal("otomatik", detail.GetProperty("onay_yolu").GetString());
    }
}
