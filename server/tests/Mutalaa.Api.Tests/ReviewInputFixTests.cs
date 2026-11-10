using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Inceleme uclarinda NUL, eslesmemis vekil karakter ve null ogeler: PostgreSQL'e gitmeden 400 dogrulama (alan adi snake_case). Docker'li.
/// </summary>
public class ReviewInputFixTests(EditorialDatabase<ReviewInputFixTests> fixture)
    : ReviewTestBase<ReviewInputFixTests>(fixture), IClassFixture<EditorialDatabase<ReviewInputFixTests>>
{
    private async Task<(Review Review, HttpClient Client)> OpenReviewAsync()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor());
        Review review = await SeedUnitReviewAsync(unit);
        return (review, await ClientAsync());
    }

    private async Task<HttpResponseMessage> DecideRawAsync(HttpClient client, Review review, string json)
    {
        using HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id.ToString(CultureInfo.InvariantCulture)}/decision")
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));
        return await client.SendAsync(request, Ct);
    }

    private static Task<HttpResponseMessage> BulkRawAsync(HttpClient client, string json) =>
        client.PostAsync("/api/v1/reviews/decisions", new StringContent(json, Encoding.UTF8, "application/json"), Ct);

    private static async Task AssertValidationAsync(HttpResponseMessage response, string field)
    {
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("urn:mutalaa:problem:dogrulama", body.GetProperty("type").GetString());
        Assert.True(body.TryGetProperty("errors", out JsonElement errors), "errors alani yok.");
        Assert.True(errors.TryGetProperty(field, out JsonElement messages), $"errors.{field} yok: {errors}");
        Assert.NotEmpty(messages.EnumerateArray());
    }

    private async Task AssertUntouchedAsync(Review review)
    {
        (string durum, _, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Null(inceleyen);
    }

    [Theory]
    [InlineData("\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce \\u0000\"", "gerekce")]
    [InlineData("\"karar\":\"reddedildi\",\"gerekce\":\"Ret \\u0000\"", "gerekce")]
    [InlineData("\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce\",\"duzenlenen\":{\"metin\":\"Deneme \\u0000 3\"}", "duzenlenen.metin")]
    public async Task A_decision_with_NUL_is_a_400_validation_problem_and_changes_nothing(string members, string field)
    {
        (Review review, HttpClient client) = await OpenReviewAsync();
        using (client)
        {
            using HttpResponseMessage response = await DecideRawAsync(client, review, "{" + members + "}");

            await AssertValidationAsync(response, field);
            await AssertUntouchedAsync(review);
        }
    }

    [Theory]
    [InlineData("{\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce \\ud800\"}")]
    [InlineData("{\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce\",\"duzenlenen\":{\"metin\":\"\\udc00\"}}")]
    public async Task A_decision_with_a_lone_surrogate_is_rejected_as_a_400_validation_problem(string json)
    {
        // Gecersiz UTF-16 kacisi JSON okuyucuda reddedilir (alan adi bilinmez); yine de 400 dogrulama ve hicbir sey degismez.
        (Review review, HttpClient client) = await OpenReviewAsync();
        using (client)
        {
            using HttpResponseMessage response = await DecideRawAsync(client, review, json);

            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("urn:mutalaa:problem:dogrulama", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("type").GetString());
            await AssertUntouchedAsync(review);
        }
    }

    [Theory]
    [InlineData("\"gerekce\":\"Gerekce \\u0000\"", "kararlar[0].gerekce")]
    [InlineData("\"gerekce\":\"Gerekce\",\"duzenlenen\":{\"metin\":\"Deneme \\u0000 3\"}", "kararlar[0].duzenlenen.metin")]
    public async Task A_bulk_decision_with_NUL_is_a_400_validation_problem_and_changes_nothing(string members, string field)
    {
        (Review review, HttpClient client) = await OpenReviewAsync();
        using (client)
        {
            string xmin = (await XminAsync(review.Id)).ToString(CultureInfo.InvariantCulture);
            string json = $"{{\"kararlar\":[{{\"id\":{review.Id.ToString(CultureInfo.InvariantCulture)},\"xmin\":{xmin},\"karar\":\"onaylandi\",{members}}}]}}";

            using HttpResponseMessage response = await BulkRawAsync(client, json);

            await AssertValidationAsync(response, field);
            await AssertUntouchedAsync(review);
        }
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public async Task A_quoted_id_or_xmin_in_a_bulk_decision_is_a_400_validation_problem_and_changes_nothing(bool quoteId, bool quoteXmin)
    {
        // Tirnakli sayi artik JSON sayisi degildir (NumberHandling.Strict): govde okunamaz, errors alani olmadan 400 dogrulama.
        (Review review, HttpClient client) = await OpenReviewAsync();
        using (client)
        {
            string id = review.Id.ToString(CultureInfo.InvariantCulture);
            string xmin = (await XminAsync(review.Id)).ToString(CultureInfo.InvariantCulture);
            string json = "{\"kararlar\":[{\"id\":" + (quoteId ? "\"" + id + "\"" : id) + ",\"xmin\":" + (quoteXmin ? "\"" + xmin + "\"" : xmin)
                + ",\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce\"}]}";

            using HttpResponseMessage response = await BulkRawAsync(client, json);

            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("urn:mutalaa:problem:dogrulama", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("type").GetString());
            await AssertUntouchedAsync(review);
        }
    }

    [Fact]
    public async Task The_same_bulk_decision_with_unquoted_numbers_is_accepted()
    {
        (Review review, HttpClient client) = await OpenReviewAsync();
        using (client)
        {
            string xmin = (await XminAsync(review.Id)).ToString(CultureInfo.InvariantCulture);
            string json = "{\"kararlar\":[{\"id\":" + review.Id.ToString(CultureInfo.InvariantCulture) + ",\"xmin\":" + xmin + ",\"karar\":\"onaylandi\",\"gerekce\":\"Gerekce\"}]}";

            using HttpResponseMessage response = await BulkRawAsync(client, json);

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        }
    }

    [Theory]
    [InlineData("{\"kararlar\":[null]}")]
    [InlineData("{\"kararlar\":[null,null]}")]
    public async Task A_null_item_in_the_bulk_decisions_is_a_400_validation_problem(string json)
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkRawAsync(client, json);

        await AssertValidationAsync(response, "kararlar[0]");
    }

    [Theory]
    [InlineData("alan=%00", "alan")]
    [InlineData("alan=me%00tin", "alan")]
    [InlineData("hedef_tablo=%00", "hedef_tablo")]
    public async Task A_NUL_in_a_review_list_filter_is_a_400_validation_problem(string query, string field)
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);

        await AssertValidationAsync(response, field);
    }
}
