using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Baglanti incelemesinde Duzelt ve onayla (A18.4, K-48 madde 2): hedef, aralik ve tur duzeltmesi; hata yollari; toplu onayin
/// sinif kurali (K-13 politika 1). Veri sentetiktir (Docker'li).
/// </summary>
public class ReviewLinkDecisionTests(EditorialDatabase<ReviewLinkDecisionTests> fixture)
    : LinkTestBase<ReviewLinkDecisionTests>(fixture), IClassFixture<EditorialDatabase<ReviewLinkDecisionTests>>
{
    private async Task<(World World, Xref Xref, Review Review)> SeedAsync(
        XrefType type = XrefType.Iktibas,
        AnchorSpan? dstSpan = null,
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        XrefStatus status = XrefStatus.Aday)
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(type, 0.55f, Evidence(world.Src, ("dst_hash", "0000000000000000"), ("run_id", "r1")), dstSpan: dstSpan, status: status);
        Review review = await SeedLinkReviewAsync(xref, koken, oneren);
        return (world, xref, review);
    }

    private async Task<HttpResponseMessage> EditAsync(HttpClient client, Review review, object duzenlenen, string gerekce = "Deneme gerekcesi") =>
        await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(gerekce, duzenlenen));

    [Fact]
    public async Task Changing_the_target_applies_it_marks_the_origin_editor_and_renews_the_dst_hash()
    {
        (World world, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = OtherAyahAnchor });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("duzenle_onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());

        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("q:2:256", row.DstAnchor);
        Assert.Null(row.DstSpan);
        Assert.Equal("iktibas", row.Type);
        Assert.Equal("editor", row.Origin);
        Assert.Equal("onayli", row.Status);
        using JsonDocument evidence = JsonDocument.Parse(row.Evidence);
        Assert.True(evidence.RootElement.GetProperty("editor_duzeltmesi").GetBoolean());
        Assert.Equal(world.OtherAyah.ContentHash[..16], evidence.RootElement.GetProperty("dst_hash").GetString());
        Assert.Equal(world.Src.ContentHash[..16], evidence.RootElement.GetProperty("src_hash").GetString());
        Assert.Equal("r1", evidence.RootElement.GetProperty("run_id").GetString());

        // Denetim izi: duzenlenen editorun degeri.
        JsonElement detail = await DetailAsync(client, review.Id);
        Assert.Equal("q:2:256", detail.GetProperty("duzenlenen").GetProperty("dst_anchor").GetString());
        Assert.Equal("editor", detail.GetProperty("hedef").GetProperty("origin").GetString());
    }

    [Fact]
    public async Task Correcting_the_span_keeps_the_unit_and_the_dst_hash()
    {
        (_, Xref xref, Review review) = await SeedAsync(dstSpan: new AnchorSpan(1, 3));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_span = new[] { 3, 8 } });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("q:2:255", row.DstAnchor);
        Assert.Equal("[3,8)", row.DstSpan);
        Assert.Equal("editor", row.Origin);
        using JsonDocument evidence = JsonDocument.Parse(row.Evidence);
        Assert.Equal("0000000000000000", evidence.RootElement.GetProperty("dst_hash").GetString());
    }

    [Fact]
    public async Task A_word_range_anchor_sets_the_unit_and_the_word_position_span()
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = "q:2:256:2-4" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("q:2:256", row.DstAnchor);
        Assert.Equal("[2,5)", row.DstSpan);
    }

    [Fact]
    public async Task A_hadith_target_with_a_code_point_span_is_accepted()
    {
        (_, Xref xref, Review review) = await SeedAsync(XrefType.Atif);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = HadithAnchor, dst_span = new[] { 0, 20 } });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("h:buhari:52", row.DstAnchor);
        Assert.Equal("[0,20)", row.DstSpan);
    }

    [Theory]
    [InlineData("atif", "ima")]
    [InlineData("iktibas", "atif")]
    [InlineData("ima", "iktibas")]
    public async Task The_editable_types_change_among_themselves(string from, string to)
    {
        XrefType type = from switch { "atif" => XrefType.Atif, "ima" => XrefType.Ima, _ => XrefType.Iktibas };
        (_, Xref xref, Review review) = await SeedAsync(type);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { type = to });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal(to, row.Type);
        Assert.Equal("editor", row.Origin);
    }

    [Theory]
    [InlineData(XrefType.Kok)]
    [InlineData(XrefType.Lemma)]
    [InlineData(XrefType.BenzerAyet)]
    public async Task The_automatic_types_cannot_change_type_and_nothing_is_written(XrefType type)
    {
        (_, Xref xref, Review review) = await SeedAsync(type);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { type = "iktibas" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_type_cannot_become_an_automatic_type()
    {
        (_, _, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { type = "kok" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }

    [Theory]
    [InlineData(0, 3)] // kelime konumu 1'den baslar
    [InlineData(3, 3)] // bas < son
    [InlineData(5, 3)]
    [InlineData(1, 12)] // q:2:255 10 kelime
    [InlineData(-1, 2)]
    public async Task A_span_outside_the_ayah_words_is_400_and_nothing_changes(int start, int end)
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_span = new[] { start, end } });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Theory]
    [InlineData("q:2:255-257")] // ayet araligi uc olamaz
    [InlineData("rn:sozler:soz-10:p4:s2")] // cumle capasi
    [InlineData("deneme")]
    [InlineData("meal:elmalili:2:255")] // atif/iktibas hedefi ayet ya da hadis olmali
    [InlineData("q:3:1")] // birim yok
    [InlineData("q:115:1")]
    public async Task A_bad_destination_is_400(string anchor)
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = anchor });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task A_span_past_the_hadith_text_is_400()
    {
        (_, _, Review review) = await SeedAsync(XrefType.Atif);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = HadithAnchor, dst_span = new[] { 0, 9999 } });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task An_anchor_with_its_own_span_and_dst_span_together_is_400()
    {
        (_, _, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = "q:2:255:2-3", dst_span = new[] { 1, 2 } });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{ \"metin\": \"Deneme paragrafi 9\" }")]
    [InlineData("{ \"new_value\": \"N\" }")]
    [InlineData("{ \"anlam_kisa\": \"deneme\" }")]
    [InlineData("{ \"type\": \"bilinmeyen\" }")]
    [InlineData("{ \"dst_span\": [1] }")]
    [InlineData("{ \"dst_span\": [1, 2, 3] }")]
    [InlineData("{ \"root_id\": 3, \"etymological_only\": false }")]
    public async Task Malformed_link_edits_are_400(string duzenlenen)
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        using StringContent content = new(
            "{ \"karar\": \"onaylandi\", \"gerekce\": \"Deneme\", \"duzenlenen\": " + duzenlenen + " }",
            System.Text.Encoding.UTF8,
            "application/json");
        using HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id}/decision") { Content = content };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));

        using HttpResponseMessage response = await client.SendAsync(request, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task A_correction_that_collides_with_an_existing_natural_key_is_409_cakisma_and_leaves_everything_unchanged()
    {
        (World world, Xref xref, Review review) = await SeedAsync();
        Xref other = await SeedXrefAsync(
            XrefType.Iktibas,
            0.9f,
            Evidence(world.Src),
            srcSpan: xref.SrcSpan,
            dst: OtherAyahAnchor,
            status: XrefStatus.Onayli);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { dst_anchor = OtherAyahAnchor });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("cakisma", await ProblemCodeAsync(response));
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("q:2:255", row.DstAnchor);
        Assert.Equal("aday", row.Status);
        Assert.Equal("hat", row.Origin);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal("onayli", (await XrefRowAsync(other.Id)).Status);
    }

    [Fact]
    public async Task An_editor_cannot_approve_their_own_correction_proposal_and_another_editor_can()
    {
        (_, Xref xref, Review review) = await SeedAsync(koken: XrefOrigin.Editor, oneren: EditorAEmail);
        using HttpClient own = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient other = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage refused = await EditAsync(own, review, new { type = "ima" });
        Assert.Equal(HttpStatusCode.Conflict, refused.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(refused));
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);

        using HttpResponseMessage accepted = await EditAsync(other, review, new { type = "ima" });
        Assert.Equal(HttpStatusCode.OK, accepted.StatusCode);
        Assert.Equal("ima", (await XrefRowAsync(xref.Id)).Type);
    }

    [Fact]
    public async Task A_target_that_is_not_a_candidate_cannot_be_corrected()
    {
        (_, Xref xref, Review review) = await SeedAsync(status: XrefStatus.Onayli);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { type = "ima" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        Assert.Equal("iktibas", (await XrefRowAsync(xref.Id)).Type);
    }

    [Fact]
    public async Task A_rejection_with_a_correction_is_400()
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(
            client,
            review.Id,
            Etag(await XminAsync(review.Id)),
            new { karar = "reddedildi", gerekce = "Deneme", duzenlenen = new { type = "ima" } });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task An_edit_equal_to_the_current_row_is_a_plain_approval_and_keeps_the_hat_origin()
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await EditAsync(client, review, new { type = "iktibas" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("onayla", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("eylem").GetString());
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("hat", row.Origin);
        Assert.Equal("onayli", row.Status);
        Assert.DoesNotContain("editor_duzeltmesi", row.Evidence, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_plain_approval_without_a_value_still_works()
    {
        (_, Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("onayli", (await XrefRowAsync(xref.Id)).Status);
    }

    // --- Toplu onay ---

    private async Task<HttpResponseMessage> BulkAsync(HttpClient client, params (Review Review, object? Edit)[] items)
    {
        List<object> list = [];
        foreach ((Review review, object? edit) in items)
        {
            uint xmin = await XminAsync(review.Id);
            list.Add(edit is null
                ? new { id = review.Id, xmin, karar = "onaylandi", gerekce = "Deneme" }
                : new { id = review.Id, xmin, karar = "onaylandi", gerekce = "Deneme", duzenlenen = edit });
        }

        return await client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = list }, Ct);
    }

    [Fact]
    public async Task Bulk_approval_passes_for_toplu_candidates()
    {
        World world = await SeedWorldAsync();
        Xref a = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Xref b = await SeedXrefAsync(XrefType.Atif, 0.5f, StrongEvidence(world.Src));
        Review ra = await SeedLinkReviewAsync(a);
        Review rb = await SeedLinkReviewAsync(b);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, (ra, null), (rb, null));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("onayli", (await XrefRowAsync(a.Id)).Status);
        Assert.Equal("onayli", (await XrefRowAsync(b.Id)).Status);
    }

    [Theory]
    [InlineData("tutarsiz")]
    [InlineData("gri")]
    [InlineData("diger")]
    public async Task Bulk_approval_of_a_non_toplu_candidate_is_422_toplu_uygun_degil_and_applies_nothing(string sinif)
    {
        World world = await SeedWorldAsync();
        Xref toplu = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Xref other = sinif switch
        {
            "tutarsiz" => await SeedXrefAsync(XrefType.Atif, 0.2f, Evidence(world.Src)),
            "gri" => await SeedXrefAsync(XrefType.Iktibas, 0.6f, Evidence(world.Src)),
            _ => await SeedXrefAsync(XrefType.Iktibas, 0.9f, Evidence(world.Src)),
        };
        Review rt = await SeedLinkReviewAsync(toplu);
        Review ro = await SeedLinkReviewAsync(other);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, (rt, null), (ro, null));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("toplu-uygun-degil", await ProblemCodeAsync(response));
        Assert.Equal(ro.Id, (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("kimlik").GetInt64());
        Assert.Equal("aday", (await XrefRowAsync(toplu.Id)).Status);
        Assert.Equal("aday", (await XrefRowAsync(other.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(rt.Id)).Durum);
    }

    [Fact]
    public async Task Bulk_approval_with_a_value_on_a_link_is_422_toplu_uygun_degil()
    {
        World world = await SeedWorldAsync();
        Xref toplu = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Review review = await SeedLinkReviewAsync(toplu);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, (review, new { type = "atif" }));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("toplu-uygun-degil", await ProblemCodeAsync(response));
        Assert.Equal("iktibas", (await XrefRowAsync(toplu.Id)).Type);
    }

    [Fact]
    public async Task Bulk_rejection_of_any_class_is_still_allowed()
    {
        World world = await SeedWorldAsync();
        Xref gri = await SeedXrefAsync(XrefType.Iktibas, 0.6f, Evidence(world.Src));
        Review review = await SeedLinkReviewAsync(gri);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = review.Id, xmin = await XminAsync(review.Id), karar = "reddedildi", gerekce = "Deneme" } } },
            Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("red", (await XrefRowAsync(gri.Id)).Status);
    }
}
