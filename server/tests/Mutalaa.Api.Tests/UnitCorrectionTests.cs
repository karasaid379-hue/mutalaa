using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>POST /api/v1/units/{anchor}/corrections: metin duzeltme onerisi (Docker'li).</summary>
public class UnitCorrectionTests(EditorialDatabase<UnitCorrectionTests> fixture)
    : EditorApiTestBase<UnitCorrectionTests>(fixture), IClassFixture<EditorialDatabase<UnitCorrectionTests>>
{
    private const string Anchor = "rn:sozler:soz-10:p1";
    private const string Original = "Deneme paragrafı 1";

    private static Task<HttpResponseMessage> PostAsync(HttpClient client, string anchor, object body) =>
        client.PostAsJsonAsync("/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections", body, Ct);

    private static string Sha256(string text) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text)));

    private async Task SeedEditableAsync(string anchor = Anchor, string metin = Original)
    {
        if (await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.source WHERE slug = 'test-c'", Ct) == 0)
        {
            await SeedSourceAsync("test-c", SourceKind.Risale);
        }

        await SeedUnitAsync("test-c", anchor, metin);
    }

    private async Task<List<Review>> ReviewsAsync()
    {
        await using DbSession session = Db.OpenSession();
        return await session.Context.Reviews.AsNoTracking().OrderBy(r => r.Id).ToListAsync(Ct);
    }

    private static async Task AssertProblemAsync(HttpResponseMessage response, HttpStatusCode status, string code)
    {
        Assert.Equal(status, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal("urn:mutalaa:problem:" + code, ProblemType(await ReadAsync(response)));
    }

    [Fact]
    public async Task A_correction_opens_an_editor_proposal_with_before_and_after_text_and_hashes()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = "Deneme düzeltmesi" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        JsonElement body = await ReadAsync(response);
        long id = body.GetProperty("id").GetInt64();
        Assert.Equal("acik", body.GetProperty("durum").GetString());
        Assert.Equal("/api/v1/reviews/" + id, response.Headers.Location?.OriginalString);

        Review review = Assert.Single(await ReviewsAsync());
        Assert.Equal(id, review.Id);
        Assert.Equal("unit", review.HedefTablo);
        Assert.Equal(Anchor, review.HedefAnahtar);
        Assert.Equal("metin", review.Alan);
        Assert.Equal("oner", review.Eylem);
        Assert.Equal(XrefOrigin.Editor, review.Koken);
        Assert.Equal(ReviewStatus.Acik, review.Durum);
        Assert.Equal(EditorEmail, review.Oneren);
        Assert.Equal("Deneme düzeltmesi", review.Gerekce);
        Assert.Null(review.Inceleyen);

        using JsonDocument before = JsonDocument.Parse(review.Onceki!);
        Assert.Equal(Original, before.RootElement.GetProperty("metin").GetString());
        Assert.Equal(Sha256(Original), before.RootElement.GetProperty("content_hash").GetString());
        using JsonDocument after = JsonDocument.Parse(review.Onerilen!);
        Assert.Equal("Deneme paragrafı 2", after.RootElement.GetProperty("metin").GetString());
        Assert.Equal(Sha256("Deneme paragrafı 2"), after.RootElement.GetProperty("content_hash").GetString());
        Assert.Equal(["content_hash", "metin"], after.RootElement.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task A_correction_does_not_change_the_unit_itself()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = "x" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.Equal(Original, await Db.ScalarAsync<string>("SELECT metin FROM icerik.unit WHERE anchor = @a", Ct, ("a", Anchor)));
    }

    [Fact]
    public async Task The_proposed_text_is_stored_as_NFC_with_the_hash_of_the_canonical_text()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();
        // 'e' + U+0301 (birlesik aksan), CRLF, cift bosluk ve bastaki/sondaki bosluk: kanonik biçim "Deneme eé\nsatir".
        string sent = "  Deneme  é\r\nsatir  ";
        string canonical = "Deneme é\nsatir";

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = sent, gerekce = "NFC denemesi" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Review review = Assert.Single(await ReviewsAsync());
        using JsonDocument after = JsonDocument.Parse(review.Onerilen!);
        string stored = after.RootElement.GetProperty("metin").GetString()!;
        Assert.Equal(canonical, stored);
        Assert.True(Encoding.UTF8.GetBytes(canonical).AsSpan().SequenceEqual(Encoding.UTF8.GetBytes(stored)));
        Assert.Equal(Sha256(canonical), after.RootElement.GetProperty("content_hash").GetString());
    }

    [Fact]
    public async Task A_proposal_that_equals_the_current_text_only_after_canonicalization_is_a_400_no_change()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync(metin: "Deneme é");

        // Birlesik aksanli ve kenarlarinda bosluklu: kanonik hali mevcut metinle ayni.
        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = " Deneme é ", gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task The_identical_text_is_a_400_no_change()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = Original, gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task A_second_proposal_for_a_unit_with_an_open_text_review_is_a_409_conflict_but_another_unit_is_free()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();
        await SeedEditableAsync("rn:sozler:soz-10:p2", "Deneme paragrafı 5");
        using HttpResponseMessage first = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = "x" });

        using HttpResponseMessage second = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 3", gerekce = "y" });
        using HttpResponseMessage other = await PostAsync(client, "rn:sozler:soz-10:p2", new { metin = "Deneme paragrafı 6", gerekce = "z" });

        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        await AssertProblemAsync(second, HttpStatusCode.Conflict, "cakisma");
        Assert.Equal(HttpStatusCode.Created, other.StatusCode);
        Assert.Equal(2, (await ReviewsAsync()).Count);
    }

    [Fact]
    public async Task A_closed_review_does_not_block_a_new_proposal()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Reviews.Add(new Review
            {
                HedefTablo = "unit",
                HedefAnahtar = Anchor,
                Alan = "metin",
                Eylem = "reddet",
                Koken = XrefOrigin.Editor,
                Oneren = "baska@example.test",
                Durum = ReviewStatus.Reddedildi,
            });
            await session.Context.SaveChangesAsync(Ct);
        }

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = "x" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }

    [Fact]
    public async Task Concurrent_proposals_for_one_unit_open_exactly_one_review()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();

        HttpResponseMessage[] responses = await Task.WhenAll(
            Enumerable.Range(2, 6).Select(n => PostAsync(client, Anchor, new { metin = "Deneme paragrafı " + n, gerekce = "x" })));
        try
        {
            Assert.Single(responses, r => r.StatusCode == HttpStatusCode.Created);
            Assert.Equal(5, responses.Count(r => r.StatusCode == HttpStatusCode.Conflict));
            Assert.Single(await ReviewsAsync());
        }
        finally
        {
            foreach (HttpResponseMessage response in responses)
            {
                response.Dispose();
            }
        }
    }

    [Fact]
    public async Task An_ayah_unit_is_unprocessable_even_in_a_non_quran_source()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-m", SourceKind.Meal);
        await SeedUnitAsync("test-m", "q:2:255", "Deneme ayet metni", UnitKind.Ayet);

        using HttpResponseMessage response = await PostAsync(client, "q:2:255", new { metin = "Deneme metni", gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "degistirilemez-metin");
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task A_non_ayah_unit_of_a_quran_text_source_is_unprocessable()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-q", SourceKind.KuranMetni);
        await SeedUnitAsync("test-q", "meal:deneme:2:255", "Deneme meal metni", UnitKind.Meal);

        using HttpResponseMessage response = await PostAsync(client, "meal:deneme:2:255", new { metin = "Deneme metni", gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "degistirilemez-metin");
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task An_ayah_unit_of_a_quran_text_source_is_unprocessable_and_the_text_stays_byte_identical()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-q", SourceKind.KuranMetni);
        await SeedUnitAsync("test-q", "q:2:255", "Deneme ayet metni", UnitKind.Ayet);

        using HttpResponseMessage response = await PostAsync(client, "q:2:255", new { metin = "Deneme ayet metni 2", gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.UnprocessableEntity, "degistirilemez-metin");
        Assert.Equal("Deneme ayet metni", await Db.ScalarAsync<string>("SELECT metin FROM icerik.unit WHERE anchor = 'q:2:255'", Ct));
    }

    [Theory]
    [InlineData("{\"metin\":\"Deneme paragrafı 2\",\"gerekce\":\"\"}")]
    [InlineData("{\"metin\":\"Deneme paragrafı 2\",\"gerekce\":\"   \"}")]
    [InlineData("{\"metin\":\"Deneme paragrafı 2\"}")]
    [InlineData("{\"gerekce\":\"x\"}")]
    [InlineData("{\"metin\":\"\",\"gerekce\":\"x\"}")]
    [InlineData("{\"metin\":\"   \",\"gerekce\":\"x\"}")]
    [InlineData("{\"metin\":\"Deneme paragrafı 2\",\"gerekce\":\"x\",\"fazla\":1}")]
    [InlineData("{\"metin\":\"Deneme\\ud800\",\"gerekce\":\"x\"}")]
    [InlineData("{\"metin\":1,\"gerekce\":\"x\"}")]
    [InlineData("bozuk")]
    public async Task An_invalid_body_is_a_400_and_opens_nothing(string json)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();
        using StringContent content = new(json, Encoding.UTF8, "application/json");

        using HttpResponseMessage response = await client.PostAsync("/api/v1/units/" + Uri.EscapeDataString(Anchor) + "/corrections", content, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task A_reason_of_2001_code_points_is_a_400_and_2000_code_points_are_accepted()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();
        string grin = char.ConvertFromUtf32(0x1F600);

        using HttpResponseMessage over = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = new string('a', 2001) });
        // 2000 kod noktasi = 4000 UTF-16 birimi.
        using HttpResponseMessage within = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = string.Concat(Enumerable.Repeat(grin, 2000)) });

        await AssertProblemAsync(over, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Equal(HttpStatusCode.Created, within.StatusCode);
    }

    [Theory]
    [InlineData("bozuk", HttpStatusCode.BadRequest, "capa-gecersiz")]
    [InlineData("q:2:255:3", HttpStatusCode.BadRequest, "capa-gecersiz")]
    [InlineData("meal:elmalili:2:255@10-48", HttpStatusCode.BadRequest, "capa-gecersiz")]
    [InlineData("rn:sozler:soz-10:p99", HttpStatusCode.NotFound, "bulunamadi")]
    public async Task A_bad_anchor_is_a_400_and_a_missing_unit_a_404(string anchor, HttpStatusCode status, string code)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedEditableAsync();

        using HttpResponseMessage response = await PostAsync(client, anchor, new { metin = "Deneme paragrafı 2", gerekce = "x" });

        await AssertProblemAsync(response, status, code);
        Assert.Empty(await ReviewsAsync());
    }

    [Fact]
    public async Task Without_a_session_a_correction_is_a_401_problem()
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await PostAsync(client, Anchor, new { metin = "Deneme paragrafı 2", gerekce = "x" });

        await AssertProblemAsync(response, HttpStatusCode.Unauthorized, "oturum-acilamadi");
        Assert.Null(response.Headers.Location);
    }
}
