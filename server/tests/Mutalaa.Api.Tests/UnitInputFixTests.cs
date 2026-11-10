using System.Net;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Birim uclarinda NUL ve eslesmemis vekil karakter: PostgreSQL'e gitmeden 400 dogrulama (alan adi snake_case). Docker'li.
/// </summary>
public class UnitInputFixTests(EditorialDatabase<UnitInputFixTests> fixture)
    : EditorApiTestBase<UnitInputFixTests>(fixture), IClassFixture<EditorialDatabase<UnitInputFixTests>>
{
    private const string Anchor = "rn:sozler:soz-10:p1";

    private async Task<HttpClient> SeededClientAsync()
    {
        HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-fix", SourceKind.Risale);
        await SeedUnitAsync("test-fix", Anchor, "Deneme paragrafı 1");
        return client;
    }

    /// <summary>Ham JSON govdesi: serilestirici eslesmemis vekili U+FFFD'ye cevirdigi icin kacis dizisi elle yazilir.</summary>
    private static Task<HttpResponseMessage> PostRawAsync(HttpClient client, string path, string json) =>
        client.PostAsync(path, new StringContent(json, Encoding.UTF8, "application/json"), Ct);

    private static string CorrectionsPath => "/api/v1/units/" + Uri.EscapeDataString(Anchor) + "/corrections";

    private static async Task AssertValidationAsync(HttpResponseMessage response, string field)
    {
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ReadAsync(response);
        Assert.Equal("urn:mutalaa:problem:dogrulama", ProblemType(body));
        Assert.True(body.TryGetProperty("errors", out JsonElement errors), "errors alani yok.");
        Assert.True(errors.TryGetProperty(field, out JsonElement messages), $"errors.{field} yok: {errors}");
        Assert.NotEmpty(messages.EnumerateArray());
    }

    [Theory]
    [InlineData("\"metin\":\"Deneme \\u0000 2\",\"gerekce\":\"Deneme gerekcesi\"", "metin")]
    [InlineData("\"metin\":\"Deneme paragrafı 2\",\"gerekce\":\"Gerekce \\u0000\"", "gerekce")]
    public async Task A_correction_with_NUL_is_a_400_validation_problem(string members, string field)
    {
        using HttpClient client = await SeededClientAsync();

        using HttpResponseMessage response = await PostRawAsync(client, CorrectionsPath, "{" + members + "}");

        await AssertValidationAsync(response, field);
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Theory]
    [InlineData("\"metin\":\"Deneme \\ud800\",\"gerekce\":\"Deneme gerekcesi\"")]
    [InlineData("\"metin\":\"Deneme \\udc00 2\",\"gerekce\":\"Deneme gerekcesi\"")]
    [InlineData("\"metin\":\"Deneme paragrafı 2\",\"gerekce\":\"Gerekce \\ud800\"")]
    public async Task A_correction_with_a_lone_surrogate_is_rejected_as_a_400_validation_problem(string members)
    {
        // Gecersiz UTF-16 kacisi JSON okuyucuda reddedilir (alan adi bilinmez); yine de 400 dogrulama ve veritabanina gitmez.
        using HttpClient client = await SeededClientAsync();

        using HttpResponseMessage response = await PostRawAsync(client, CorrectionsPath, "{" + members + "}");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("urn:mutalaa:problem:dogrulama", ProblemType(await ReadAsync(response)));
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Theory]
    [InlineData("q=a%00b", "q")]
    [InlineData("q=%00", "q")]
    [InlineData("prefix=rn%00", "prefix")]
    [InlineData("source=test-fix%00", "source")]
    public async Task A_NUL_in_a_unit_list_filter_is_a_400_validation_problem(string query, string field)
    {
        using HttpClient client = await SeededClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units?" + query, Ct);

        await AssertValidationAsync(response, field);
    }

    [Fact]
    public async Task A_unit_cursor_whose_payload_holds_NUL_is_a_400_validation_problem()
    {
        using HttpClient client = await SeededClientAsync();
        string payload = Convert.ToBase64String(Encoding.UTF8.GetBytes("1:1:test\0fix")).TrimEnd('=').Replace('+', '-').Replace('/', '_');

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units?cursor=" + payload, Ct);

        await AssertValidationAsync(response, "cursor");
    }
}
