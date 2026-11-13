using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>
/// "Ima olarak isaretle" ve "Kalip listesine ekle" (K-48 madde 2, A18.4): yeni ima satiri, kapali denetim kayitlari, hata yollari.
/// Kalip anahtari Arapca arama anahtaridir; testte kullanilan Arapca harfler sentetiktir (rastgele harf dizisi, Kur'an metni degil).
/// </summary>
public class ReviewImaKalipTests(EditorialDatabase<ReviewImaKalipTests> fixture)
    : LinkTestBase<ReviewImaKalipTests>(fixture), IClassFixture<EditorialDatabase<ReviewImaKalipTests>>
{
    private const string Arab = "بتث جحخ";

    private static string ArabKey => SearchNormalizer.Keys(Arab).ArNorm.Trim();

    private async Task<(World World, Xref Xref, Review Review)> SeedAsync(
        XrefType type = XrefType.Iktibas,
        AnchorSpan? dstSpan = null,
        XrefStatus status = XrefStatus.Aday,
        ReviewStatus durum = ReviewStatus.Acik)
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(type, 0.55f, Evidence(world.Src, ("dst_hash", "0000000000000000"), ("source_id", "deneme"), ("run_id", "r1")), dstSpan: dstSpan, status: status);
        Review review = await SeedLinkReviewAsync(xref, durum: durum);
        return (world, xref, review);
    }

    private static Task<HttpResponseMessage> ImaAsync(HttpClient client, long id, object body) =>
        client.PostAsJsonAsync($"/api/v1/reviews/{id.ToString(CultureInfo.InvariantCulture)}/ima", body, Ct);

    private static Task<HttpResponseMessage> KalipAsync(HttpClient client, long id, object body, string? ifMatch)
    {
        HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{id.ToString(CultureInfo.InvariantCulture)}/kalip") { Content = JsonContent.Create(body) };
        if (ifMatch is not null)
        {
            request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
        }

        return client.SendAsync(request, Ct);
    }

    // --- Ima ---

    [Fact]
    public async Task Ima_opens_an_approved_editor_row_to_the_same_target_keeps_the_candidate_and_writes_an_audit_record()
    {
        (World world, Xref xref, Review review) = await SeedAsync(dstSpan: new AnchorSpan(3, 8));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Basligi ayetin manasi" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Guid imaId = body.GetProperty("id").GetGuid();
        long auditId = body.GetProperty("review_id").GetInt64();
        Assert.Equal("ima", body.GetProperty("type").GetString());
        Assert.Equal("onayli", body.GetProperty("status").GetString());
        Assert.Equal("/api/v1/reviews/" + auditId.ToString(CultureInfo.InvariantCulture), response.Headers.Location?.ToString());

        XrefRow ima = await XrefRowAsync(imaId);
        Assert.Equal("ima", ima.Type);
        Assert.Equal("editor", ima.Origin);
        Assert.Equal("onayli", ima.Status);
        Assert.Equal(1f, ima.Confidence);
        Assert.Equal("rn:sozler:soz-10:p4", ima.SrcAnchor);
        Assert.Equal("q:2:255", ima.DstAnchor);
        Assert.Equal((await XrefRowAsync(xref.Id)).SrcSpan, ima.SrcSpan);
        Assert.Equal("[3,8)", ima.DstSpan);
        using JsonDocument evidence = JsonDocument.Parse(ima.Evidence);
        Assert.True(evidence.RootElement.GetProperty("editor_ima").GetBoolean());
        Assert.Equal(world.Src.ContentHash[..16], evidence.RootElement.GetProperty("src_hash").GetString());
        Assert.Equal("0000000000000000", evidence.RootElement.GetProperty("dst_hash").GetString());
        Assert.False(evidence.RootElement.TryGetProperty("run_id", out _));

        // Ozgun aday ve onun incelemesi dokunulmaz.
        XrefRow original = await XrefRowAsync(xref.Id);
        Assert.Equal("iktibas", original.Type);
        Assert.Equal("aday", original.Status);
        Assert.Equal("hat", original.Origin);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);

        // Denetim kaydi: kapali, onaylandi, yeni satiri gosterir.
        JsonElement audit = await DetailAsync(client, auditId);
        Assert.Equal("onaylandi", audit.GetProperty("durum").GetString());
        Assert.Equal("ima_isaretle", audit.GetProperty("eylem").GetString());
        Assert.Equal("editor", audit.GetProperty("koken").GetString());
        Assert.Equal(EditorAEmail, audit.GetProperty("oneren").GetString());
        Assert.Equal(EditorAEmail, audit.GetProperty("inceleyen").GetString());
        Assert.Equal(imaId.ToString("D"), audit.GetProperty("hedef_anahtar").GetString());
        Assert.Equal(imaId, audit.GetProperty("xref_id").GetGuid());
        Assert.Equal(review.Id, long.Parse(audit.GetProperty("onceki").GetProperty("kaynak_review").GetString()!, CultureInfo.InvariantCulture));
        Assert.Equal("Basligi ayetin manasi", audit.GetProperty("gerekce").GetString());
    }

    [Fact]
    public async Task Ima_works_for_atif_and_the_new_row_is_not_open_for_decision()
    {
        (_, _, Review review) = await SeedAsync(XrefType.Atif);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });
        long auditId = (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("review_id").GetInt64();

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        using HttpResponseMessage decide = await DecideAsync(client, auditId, Etag(await XminAsync(auditId)), Approve());
        Assert.Equal(HttpStatusCode.Conflict, decide.StatusCode);
    }

    [Fact]
    public async Task A_second_ima_for_the_same_end_is_409_cakisma()
    {
        (_, _, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage first = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        using HttpResponseMessage second = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, second.StatusCode);
        Assert.Equal("cakisma", await ProblemCodeAsync(second));
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.xref WHERE type = 'ima'", Ct));
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review WHERE eylem = 'ima_isaretle'", Ct));
    }

    [Theory]
    [InlineData(XrefType.Kok)]
    [InlineData(XrefType.Lemma)]
    [InlineData(XrefType.BenzerAyet)]
    public async Task Ima_is_422_for_the_automatic_types(XrefType type)
    {
        (_, _, Review review) = await SeedAsync(type);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.xref WHERE type = 'ima'", Ct));
    }

    [Fact]
    public async Task Ima_on_an_ima_candidate_is_409()
    {
        (_, _, Review review) = await SeedAsync(XrefType.Ima);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
    }

    [Theory]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    [InlineData(ReviewStatus.Uzmanda)]
    public async Task Ima_needs_an_open_review(ReviewStatus durum)
    {
        (_, _, Review review) = await SeedAsync(durum: durum);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.xref WHERE type = 'ima'", Ct));
    }

    [Fact]
    public async Task Ima_needs_a_candidate_row()
    {
        (_, _, Review review) = await SeedAsync(status: XrefStatus.Onayli);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
    }

    [Fact]
    public async Task Ima_on_a_non_link_review_is_422_and_on_an_unknown_review_404()
    {
        await SeedWorldAsync();
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

        using HttpResponseMessage nonLink = await ImaAsync(client, lemmaReview.Id, new { gerekce = "Deneme" });
        using HttpResponseMessage unknown = await ImaAsync(client, 999999, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, nonLink.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, unknown.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(unknown));
    }

    [Fact]
    public async Task Ima_is_404_when_the_link_of_the_review_is_gone()
    {
        (_, Xref xref, Review review) = await SeedAsync();
        await Db.ExecuteAsync("UPDATE icerik.review SET hedef_anahtar = @k, xref_id = NULL WHERE id = @id", Ct, ("k", Guid.NewGuid().ToString("D")), ("id", review.Id));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await ImaAsync(client, review.Id, new { gerekce = "Deneme" });

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.NotNull(xref);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{ \"gerekce\": \"\" }")]
    [InlineData("{ \"gerekce\": \"  \" }")]
    public async Task Ima_needs_a_reason(string json)
    {
        (_, _, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        using StringContent content = new(json, System.Text.Encoding.UTF8, "application/json");

        using HttpResponseMessage response = await client.PostAsync($"/api/v1/reviews/{review.Id}/ima", content, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.xref WHERE type = 'ima'", Ct));
    }

    // --- Kalip ---

    private async Task<(Xref Xref, Review Review)> SeedPatternAsync(string? phraseKey = Arab, XrefType type = XrefType.Iktibas, ReviewStatus durum = ReviewStatus.Acik)
    {
        World world = await SeedWorldAsync();
        List<(string, object?)> extra = [];
        if (phraseKey is not null)
        {
            extra.Add(("phrase_key", phraseKey));
        }

        Xref xref = await SeedXrefAsync(type, 0.55f, Evidence(world.Src, [.. extra]));
        return (xref, await SeedLinkReviewAsync(xref, durum: durum));
    }

    [Fact]
    public async Task Adding_to_the_pattern_list_rejects_the_candidate_and_writes_a_closed_audit_record_with_the_key()
    {
        (Xref xref, Review review) = await SeedPatternAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await KalipAsync(client, review.Id, new { gerekce = "Kalip ifade" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("reddedildi", body.GetProperty("durum").GetString());
        Assert.Equal("reddet", body.GetProperty("eylem").GetString());
        Assert.Equal(ArabKey, body.GetProperty("anahtar").GetString());
        Assert.NotEmpty(ArabKey);
        long auditId = body.GetProperty("denetim_review_id").GetInt64();
        Assert.Equal(Etag(body.GetProperty("xmin").GetUInt32()), response.Headers.ETag?.Tag);

        Assert.Equal("red", (await XrefRowAsync(xref.Id)).Status);
        (string durum, string eylem, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("reddedildi", durum);
        Assert.Equal("reddet", eylem);
        Assert.Equal(EditorAEmail, inceleyen);

        // Hat bu kayitlardan kalip listesini disa aktarir: eylem = kalip_ekle, durum = onaylandi, onerilen.anahtar.
        JsonElement audit = await DetailAsync(client, auditId);
        Assert.Equal("kalip_ekle", audit.GetProperty("eylem").GetString());
        Assert.Equal("onaylandi", audit.GetProperty("durum").GetString());
        Assert.Equal("editor", audit.GetProperty("koken").GetString());
        Assert.Equal(ArabKey, audit.GetProperty("onerilen").GetProperty("anahtar").GetString());
        Assert.Equal("Kalip ifade", audit.GetProperty("onerilen").GetProperty("gerekce").GetString());
        Assert.Equal(xref.Id, audit.GetProperty("xref_id").GetGuid());
        Assert.Equal(
            ArabKey,
            await Db.ScalarAsync<string>("SELECT onerilen->>'anahtar' FROM icerik.review WHERE eylem = 'kalip_ekle' AND durum = 'onaylandi'", Ct));
    }

    [Fact]
    public async Task Without_a_phrase_key_the_key_comes_from_the_matched_slice_of_the_source_text()
    {
        World world = await SeedWorldAsync();
        string text = "Deneme paragrafi baslangic " + Arab + " ve devami";
        Unit src = await SeedUnitAsync(world.RisaleSource, UnitKind.Risale, "rn:sozler:soz-12:p1", text, TextStatus.Onayli);
        Xref xref = await SeedXrefAsync(XrefType.Iktibas, 0.55f, Evidence(src), src: "rn:sozler:soz-12:p1", srcSpan: new AnchorSpan(27, 34));
        Review review = await SeedLinkReviewAsync(xref);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await KalipAsync(client, review.Id, new { gerekce = "Kalip ifade" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(ArabKey, (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("anahtar").GetString());
    }

    [Fact]
    public async Task A_stale_source_hash_or_a_key_that_cannot_be_derived_is_422_and_nothing_is_written()
    {
        World world = await SeedWorldAsync();
        string text = "Deneme paragrafi baslangic " + Arab + " ve devami";
        Unit src = await SeedUnitAsync(world.RisaleSource, UnitKind.Risale, "rn:sozler:soz-12:p1", text, TextStatus.Onayli);
        Xref stale = await SeedXrefAsync(XrefType.Iktibas, 0.55f, Evidence(src, ("src_hash", "ffffffffffffffff")), src: "rn:sozler:soz-12:p1", srcSpan: new AnchorSpan(27, 34));
        Xref latin = await SeedXrefAsync(XrefType.Iktibas, 0.55f, Evidence(world.Src), srcSpan: new AnchorSpan(1, 5));
        Review staleReview = await SeedLinkReviewAsync(stale);
        Review latinReview = await SeedLinkReviewAsync(latin);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage a = await KalipAsync(client, staleReview.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(staleReview.Id)));
        using HttpResponseMessage b = await KalipAsync(client, latinReview.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(latinReview.Id)));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, a.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(a));
        Assert.Equal(HttpStatusCode.UnprocessableEntity, b.StatusCode);
        Assert.Equal("aday", (await XrefRowAsync(stale.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(latinReview.Id)).Durum);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review WHERE eylem = 'kalip_ekle'", Ct));
    }

    [Theory]
    [InlineData(XrefType.Atif)]
    [InlineData(XrefType.Ima)]
    [InlineData(XrefType.Kok)]
    public async Task Only_an_iktibas_candidate_can_join_the_pattern_list(XrefType type)
    {
        (_, Review review) = await SeedPatternAsync(type: type);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }

    [Theory]
    [InlineData(ReviewStatus.Uzmanda)]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    public async Task The_pattern_list_needs_an_open_review(ReviewStatus durum)
    {
        (Xref xref, Review review) = await SeedPatternAsync(durum: durum);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review WHERE eylem = 'kalip_ekle'", Ct));
    }

    [Fact]
    public async Task The_pattern_list_needs_if_match_a_fresh_version_a_reason_and_an_existing_review()
    {
        (Xref xref, Review review) = await SeedPatternAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage missing = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, null);
        using HttpResponseMessage stale = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(1));
        using HttpResponseMessage noReason = await KalipAsync(client, review.Id, new { gerekce = " " }, Etag(await XminAsync(review.Id)));
        using HttpResponseMessage unknown = await KalipAsync(client, 999999, new { gerekce = "Deneme" }, Etag(1));

        Assert.Equal(HttpStatusCode.PreconditionRequired, missing.StatusCode);
        Assert.Equal("surum-gerekli", await ProblemCodeAsync(missing));
        Assert.Equal(HttpStatusCode.PreconditionFailed, stale.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, noReason.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, unknown.StatusCode);
        Assert.Equal("aday", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task The_pattern_list_is_422_on_a_non_link_review()
    {
        await SeedWorldAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Lemma lemma = await SeedLemmaAsync(source);
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

        using HttpResponseMessage response = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(review.Id)));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
    }

    [Fact]
    public async Task A_decision_after_the_pattern_list_is_409_because_the_candidate_is_already_rejected()
    {
        (_, Review review) = await SeedPatternAsync();
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage added = await KalipAsync(client, review.Id, new { gerekce = "Deneme" }, Etag(await XminAsync(review.Id)));

        using HttpResponseMessage decide = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, added.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, decide.StatusCode);
    }
}
