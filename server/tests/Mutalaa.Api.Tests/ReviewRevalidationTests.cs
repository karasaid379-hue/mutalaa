using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Yeniden dogrulama kaydi (K-51 madde 8): hat, onayli ve origin = hat bir baglanti icin <c>onerilen.yeniden_dogrula = true</c> kaydi acar.
/// Onay "hala gecerli" (xref onayli kalir, hicbir alan degismez), ret "gecersiz" (xref red). Veri sentetiktir (Docker'li).
/// </summary>
public class ReviewRevalidationTests(EditorialDatabase<ReviewRevalidationTests> fixture)
    : LinkTestBase<ReviewRevalidationTests>(fixture), IClassFixture<EditorialDatabase<ReviewRevalidationTests>>
{
    private async Task<(Xref Xref, Review Review)> SeedAsync(
        XrefStatus status = XrefStatus.Onayli,
        string neden = "uc_metni_degisti",
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        ReviewStatus durum = ReviewStatus.Acik)
    {
        World world = await SeedWorldAsync();
        Xref xref = await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src), status: status);
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = xref.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = xref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Onerilen = JsonSerializer.Serialize(new Dictionary<string, object> { ["yeniden_dogrula"] = true, ["neden"] = neden }),
            Koken = koken,
            Oneren = oneren,
            Durum = durum,
        });
        return (xref, review);
    }

    [Theory]
    [InlineData("uretilmedi")]
    [InlineData("uc_metni_degisti")]
    public async Task Approving_a_revalidation_record_means_still_valid_and_changes_no_link_field(string neden)
    {
        (Xref xref, Review review) = await SeedAsync(neden: neden);
        XrefRow before = await XrefRowAsync(xref.Id);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve("Hala gecerli"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        Assert.Equal(before, await XrefRowAsync(xref.Id));
        Assert.Equal("onaylandi", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task Rejecting_a_revalidation_record_means_invalid_and_the_link_becomes_red()
    {
        (Xref xref, Review review) = await SeedAsync(neden: "uretilmedi");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject("Artik gecerli degil"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("reddedildi", body.GetProperty("durum").GetString());
        Assert.Equal("red", body.GetProperty("hedef_durumu").GetString());
        Assert.Equal("red", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("reddedildi", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Theory]
    [InlineData("""{"type": "atif"}""")]
    [InlineData("""{"dst_anchor": "q:2:256"}""")]
    [InlineData("{}")]
    public async Task A_revalidation_approval_with_an_edited_value_is_422_and_changes_nothing(string edit)
    {
        (Xref xref, Review review) = await SeedAsync();
        XrefRow before = await XrefRowAsync(xref.Id);
        using HttpClient client = await ClientAsync();
        using JsonDocument edited = JsonDocument.Parse(edit);

        using HttpResponseMessage response = await DecideAsync(
            client,
            review.Id,
            Etag(await XminAsync(review.Id)),
            new { karar = "onaylandi", gerekce = "Deneme", duzenlenen = edited.RootElement.Clone() });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal(before, await XrefRowAsync(xref.Id));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Theory]
    [InlineData("aday", true)]
    [InlineData("aday", false)]
    [InlineData("red", true)]
    [InlineData("red", false)]
    public async Task A_revalidation_record_whose_link_is_no_longer_approved_is_409(string status, bool approve)
    {
        (Xref xref, Review review) = await SeedAsync(status: status == "aday" ? XrefStatus.Aday : XrefStatus.Red);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), approve ? Approve() : Reject());

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        Assert.Equal(status, (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task An_editor_cannot_approve_their_own_revalidation_proposal_but_another_editor_can()
    {
        (Xref xref, Review review) = await SeedAsync(koken: XrefOrigin.Editor, oneren: EditorAEmail);
        using HttpClient a = await ClientAsync();
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);

        using (HttpResponseMessage own = await DecideAsync(a, review.Id, Etag(await XminAsync(review.Id)), Approve()))
        {
            Assert.Equal(HttpStatusCode.Conflict, own.StatusCode);
        }

        using HttpResponseMessage other = await DecideAsync(b, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, other.StatusCode);
        Assert.Equal("onayli", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task The_expert_decides_a_revalidation_record_sent_to_the_expert_and_an_editor_cannot()
    {
        (Xref xref, Review review) = await SeedAsync();
        using HttpClient editor = await ClientAsync();
        using HttpRequestMessage handoff = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id.ToString(CultureInfo.InvariantCulture)}/uzmana-gonder")
        {
            Content = JsonContent.Create(new { gerekce = "Uzman gorusu gerekli" }),
        };
        handoff.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));
        using (HttpResponseMessage sent = await editor.SendAsync(handoff, Ct))
        {
            Assert.Equal(HttpStatusCode.OK, sent.StatusCode);
        }

        using (HttpResponseMessage denied = await DecideAsync(editor, review.Id, Etag(await XminAsync(review.Id)), Approve()))
        {
            Assert.Equal(HttpStatusCode.Forbidden, denied.StatusCode);
        }

        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);
        using HttpResponseMessage rejected = await DecideAsync(uzman, review.Id, Etag(await XminAsync(review.Id)), Reject("Uzman: gecersiz"));

        Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
        Assert.Equal("red", (await XrefRowAsync(xref.Id)).Status);
        Assert.Equal("reddedildi", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task Bulk_approval_never_takes_a_revalidation_record_even_when_the_link_looks_like_toplu()
    {
        (Xref xref, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        uint xmin = await XminAsync(review.Id);

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = review.Id, xmin, karar = "onaylandi", gerekce = "Deneme" } } },
            Ct);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("toplu-uygun-degil", await ProblemCodeAsync(response));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal("onayli", (await XrefRowAsync(xref.Id)).Status);
    }

    [Fact]
    public async Task An_ordinary_candidate_review_with_no_flag_still_needs_a_candidate_link()
    {
        World world = await SeedWorldAsync();
        Xref approved = await SeedXrefAsync(XrefType.Iktibas, 0.55f, Evidence(world.Src), status: XrefStatus.Onayli);
        Review review = await SeedLinkReviewAsync(approved);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
    }
}
