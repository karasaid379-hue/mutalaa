using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// "Uzmana gonder" ve uzman karari (K-51 madde 2, A18.4): durum gecisi, korunan eylem, yetki (403), If-Match (428, 412), hata yollari
/// ve uzmanin karari. Veri sentetiktir (Docker'li).
/// </summary>
public class ReviewExpertTests(EditorialDatabase<ReviewExpertTests> fixture)
    : LinkTestBase<ReviewExpertTests>(fixture), IClassFixture<EditorialDatabase<ReviewExpertTests>>
{
    private async Task<(Xref Xref, Review Review)> SeedCandidateAsync()
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(XrefType.Iktibas, 0.55f, Evidence(world.Src));
        return (xref, await SeedLinkReviewAsync(xref));
    }

    private async Task<HttpResponseMessage> HandoffAsync(HttpClient client, long id, object body, string? ifMatch)
    {
        HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{id.ToString(CultureInfo.InvariantCulture)}/uzmana-gonder")
        {
            Content = JsonContent.Create(body),
        };
        if (ifMatch is not null)
        {
            request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
        }

        return await client.SendAsync(request, Ct);
    }

    private async Task<HttpResponseMessage> HandoffAsync(HttpClient client, Review review, string gerekce = "Uzman gorusu gerekli") =>
        await HandoffAsync(client, review.Id, new { gerekce }, Etag(await XminAsync(review.Id)));

    [Fact]
    public async Task An_editor_sends_an_open_record_to_the_expert_and_the_original_action_is_kept()
    {
        (_, Review review) = await SeedCandidateAsync();
        uint before = await XminAsync(review.Id);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await HandoffAsync(client, review);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("uzmanda", body.GetProperty("durum").GetString());
        Assert.Equal("oner", body.GetProperty("eylem").GetString());
        Assert.Equal(review.Id, body.GetProperty("id").GetInt64());
        uint after = body.GetProperty("xmin").GetUInt32();
        Assert.NotEqual(before, after);
        Assert.Equal(Etag(after), response.Headers.ETag?.Tag);

        (string durum, string eylem, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("uzmanda", durum);
        Assert.Equal("oner", eylem);
        Assert.Equal(EditorAEmail, inceleyen);
        Assert.Null(ikinci);
        Assert.Equal("Uzman gorusu gerekli", await Db.ScalarAsync<string>("SELECT gerekce FROM icerik.review WHERE id = @id", Ct, ("id", review.Id)));
        Assert.Null(await Db.ScalarAsync<string?>("SELECT ikinci_gerekce FROM icerik.review WHERE id = @id", Ct, ("id", review.Id)));

        // Detay: durum uzmanda, hedef hala aday.
        JsonElement detail = await DetailAsync(client, review.Id);
        Assert.Equal("uzmanda", detail.GetProperty("durum").GetString());
        Assert.Equal("aday", detail.GetProperty("hedef").GetProperty("status").GetString());
    }

    [Fact]
    public async Task An_admin_may_send_too_and_the_new_state_is_listed_under_the_expert_filter()
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);

        using HttpResponseMessage response = await HandoffAsync(admin, review);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        using HttpClient client = await ClientAsync();
        Assert.Equal([review.Id], Ids(await ListAsync(client, "durum=uzmanda")));
        Assert.Empty(Ids(await ListAsync(client, "durum=acik")));
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{ \"gerekce\": \"\" }")]
    [InlineData("{ \"gerekce\": \"   \" }")]
    [InlineData("{ \"gerekce\": null }")]
    public async Task A_missing_or_blank_reason_is_400(string json)
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient client = await ClientAsync();
        using StringContent content = new(json, System.Text.Encoding.UTF8, "application/json");
        using HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id}/uzmana-gonder") { Content = content };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));

        using HttpResponseMessage response = await client.SendAsync(request, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.True((await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("errors").TryGetProperty("gerekce", out _));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_reason_over_two_thousand_characters_or_with_nul_is_400()
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage tooLong = await HandoffAsync(client, review.Id, new { gerekce = new string('a', 2001) }, Etag(await XminAsync(review.Id)));
        using HttpResponseMessage withNul = await HandoffAsync(client, review.Id, new { gerekce = "a\u0000b" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.BadRequest, tooLong.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, withNul.StatusCode);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_missing_if_match_is_428_and_a_stale_one_is_412()
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage missing = await HandoffAsync(client, review.Id, new { gerekce = "Deneme" }, null);
        using HttpResponseMessage stale = await HandoffAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(1));
        using HttpResponseMessage bad = await HandoffAsync(client, review.Id, new { gerekce = "Deneme" }, "*");

        Assert.Equal(HttpStatusCode.PreconditionRequired, missing.StatusCode);
        Assert.Equal("surum-gerekli", await ProblemCodeAsync(missing));
        Assert.Equal(HttpStatusCode.PreconditionFailed, stale.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(stale));
        Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task An_unknown_review_is_404()
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await HandoffAsync(client, 999999, new { gerekce = "Deneme" }, Etag(1));

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task Sending_a_second_time_or_after_a_decision_is_409()
    {
        (Xref xref, Review review) = await SeedCandidateAsync();
        Review decided = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.55f, "{}"));
        await Db.ExecuteAsync("UPDATE icerik.review SET durum = 'onaylandi' WHERE id = @id", Ct, ("id", decided.Id));
        Assert.NotNull(xref);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage first = await HandoffAsync(client, review);
        using HttpResponseMessage second = await HandoffAsync(client, review);
        using HttpResponseMessage afterDecision = await HandoffAsync(client, decided);

        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, second.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(second));
        Assert.Equal(HttpStatusCode.Conflict, afterDecision.StatusCode);
    }

    [Fact]
    public async Task A_unit_text_review_cannot_be_sent_because_of_the_two_stage_flow_and_an_unsupported_target_is_422()
    {
        await SeedWorldAsync();
        string source = await SeedSourceAsync(SourceKind.Meal);
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, MealAnchor());
        Review textReview = await SeedUnitReviewAsync(unit);
        Review sourceReview = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Source,
            HedefAnahtar = source,
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage text = await HandoffAsync(client, textReview);
        using HttpResponseMessage unsupported = await HandoffAsync(client, sourceReview);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, text.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(text));
        Assert.Equal(HttpStatusCode.UnprocessableEntity, unsupported.StatusCode);
        Assert.Equal("acik", (await ReviewRowAsync(textReview.Id)).Durum);
    }

    [Fact]
    public async Task An_expert_cannot_send_records_because_the_endpoint_is_editor_only()
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await HandoffAsync(uzman, review);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Equal("yetki-yok", await ProblemCodeAsync(response));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    // --- Karar ---

    private async Task<(Xref Xref, Review Review)> SeedSentAsync()
    {
        (Xref xref, Review review) = await SeedCandidateAsync();
        using HttpClient editor = await ClientAsync();
        using HttpResponseMessage sent = await HandoffAsync(editor, review);
        Assert.Equal(HttpStatusCode.OK, sent.StatusCode);
        return (xref, review);
    }

    [Fact]
    public async Task Only_the_expert_decides_an_expert_record_editors_and_admins_get_403()
    {
        (Xref xref, Review review) = await SeedSentAsync();
        using HttpClient editor = await ClientAsync();
        using HttpClient other = await ClientAsync(EditorBEmail, EditorBPassword);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);

        foreach (HttpClient client in new[] { editor, other, admin })
        {
            using HttpResponseMessage approve = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());
            using HttpResponseMessage reject = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

            Assert.Equal(HttpStatusCode.Forbidden, approve.StatusCode);
            Assert.Equal("yetki-yok", await ProblemCodeAsync(approve));
            Assert.Equal(HttpStatusCode.Forbidden, reject.StatusCode);
        }

        Assert.Equal("uzmanda", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task The_expert_approves_an_expert_record_like_an_open_one()
    {
        (Xref xref, Review review) = await SeedSentAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), Approve("Uzman onayi"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        (string durum, _, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("onaylandi", durum);
        Assert.Equal("uzman@example.test", inceleyen);
        Assert.Equal("onayli", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task The_expert_rejects_an_expert_record()
    {
        (Xref xref, Review review) = await SeedSentAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), Reject("Uzman reddi"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("reddedildi", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("durum").GetString());
        Assert.Equal("red", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task The_expert_can_correct_a_link_while_deciding()
    {
        (Xref xref, Review review) = await SeedSentAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), Approve("Uzman duzeltmesi", new { type = "ima" }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        XrefRow row = await XrefRowAsync(xref.Id);
        Assert.Equal("ima", row.Type);
        Assert.Equal("editor", row.Origin);
    }

    [Fact]
    public async Task The_expert_decision_still_needs_if_match_and_a_valid_reason()
    {
        (_, Review review) = await SeedSentAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage noMatch = await DecideAsync(uzman, review.Id, null, Approve());
        using HttpResponseMessage noReason = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), new { karar = "onaylandi", gerekce = " " });

        Assert.Equal(HttpStatusCode.PreconditionRequired, noMatch.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, noReason.StatusCode);
        Assert.Equal("uzmanda", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task An_expert_cannot_decide_an_open_record()
    {
        (Xref xref, Review review) = await SeedCandidateAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Equal("yetki-yok", await ProblemCodeAsync(response));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task An_unknown_record_is_404_before_the_role_is_asked()
    {
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideAsync(uzman, 999999, Etag(1), Approve());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task The_expert_can_read_the_queue_the_detail_and_the_stats()
    {
        (_, Review review) = await SeedSentAsync();
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        Assert.Equal([review.Id], Ids(await ListAsync(uzman, "durum=uzmanda")));
        Assert.Equal("uzmanda", (await DetailAsync(uzman, review.Id)).GetProperty("durum").GetString());
        using HttpResponseMessage stats = await uzman.GetAsync("/api/v1/reviews/stats", Ct);
        Assert.Equal(1, (await ApiFactory.ReadJsonAsync(stats, Ct)).GetProperty("toplam_uzmanda").GetInt32());
    }

    [Fact]
    public async Task A_bulk_decision_that_includes_an_expert_record_is_403_with_the_record_id_and_applies_nothing()
    {
        World world = await SeedWorldAsync();
        Xref toplu = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Xref sent = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src));
        Review openReview = await SeedLinkReviewAsync(toplu);
        Review expertReview = await SeedLinkReviewAsync(sent, durum: ReviewStatus.Uzmanda);
        using HttpClient editor = await ClientAsync();

        using HttpResponseMessage response = await editor.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new
            {
                kararlar = new[]
                {
                    new { id = openReview.Id, xmin = await XminAsync(openReview.Id), karar = "onaylandi", gerekce = "Deneme" },
                    new { id = expertReview.Id, xmin = await XminAsync(expertReview.Id), karar = "onaylandi", gerekce = "Deneme" },
                },
            },
            Ct);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Equal("yetki-yok", await ProblemCodeAsync(response));
        Assert.Equal(expertReview.Id, (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("kimlik").GetInt64());
        Assert.Equal("aday", (await XrefRowAsync(toplu.Id)).Status);
        Assert.Equal("aday", (await XrefRowAsync(sent.Id)).Status);
    }

    [Fact]
    public async Task Two_concurrent_handoffs_let_exactly_one_win_and_the_loser_is_412_or_409()
    {
        (_, Review review) = await SeedCandidateAsync();
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        string etag = Etag(await XminAsync(review.Id));

        Task<HttpResponseMessage> first = HandoffAsync(a, review.Id, new { gerekce = "Birinci" }, etag);
        Task<HttpResponseMessage> second = HandoffAsync(b, review.Id, new { gerekce = "Ikinci" }, etag);
        HttpResponseMessage[] results = await Task.WhenAll(first, second);

        Assert.Single(results, r => r.StatusCode == HttpStatusCode.OK);
        Assert.Single(results, r => r.StatusCode is HttpStatusCode.PreconditionFailed or HttpStatusCode.Conflict);
        Assert.Equal("uzmanda", (await ReviewRowAsync(review.Id)).Durum);
        foreach (HttpResponseMessage r in results)
        {
            r.Dispose();
        }
    }
}
