using System.Net;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Inceleme uclari metni kacissiz (UTF-8) yazar, birim uclariyla ayni: ham govdede <c>\u</c> kacisi yoktur ve dizgi bayt esittir.
/// Metin sentetiktir: Latin harfler, Turkce harfler ve iki Arapca harf (U+0628 U+0633); gercek Kur'an, meal ya da Risale metni degil.
/// </summary>
public class ReviewJsonTextTests(EditorialDatabase<ReviewJsonTextTests> fixture)
    : ReviewTestBase<ReviewJsonTextTests>(fixture), IClassFixture<EditorialDatabase<ReviewJsonTextTests>>
{
    // Kesme isareti, &, <, > ve + ASP.NET Core'un varsayilan kodlayicisinda ' gibi kacislanir; UnsafeRelaxedJsonEscaping kacislamaz.
    private const string CurrentText = "Deneme'nin بس İşığı & <b> + 1";
    private const string ProposedText = "Deneme'nin بس İşığı & <b> + 2";
    private const string EditedText = "Deneme'nin بس İşığı & <b> + 3";

    private static async Task<(string Raw, byte[] Bytes)> RawAsync(HttpResponseMessage response)
    {
        byte[] bytes = await response.Content.ReadAsByteArrayAsync(Ct);
        return (Encoding.UTF8.GetString(bytes), bytes);
    }

    private static void AssertSameBytes(string expected, string actual) =>
        Assert.True(Encoding.UTF8.GetBytes(expected).AsSpan().SequenceEqual(Encoding.UTF8.GetBytes(actual)), "Dizgi bayt bayt esit olmali.");

    [Fact]
    public async Task The_review_detail_writes_the_target_snapshot_and_the_payload_texts_unescaped_and_byte_equal()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor, CurrentText);
        Review review = await SeedUnitReviewAsync(unit, proposed: ProposedText);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string raw, byte[] bytes) = await RawAsync(response);
        Assert.DoesNotContain("\\u", raw, StringComparison.Ordinal);
        Assert.Contains(CurrentText, raw, StringComparison.Ordinal);
        Assert.Contains(ProposedText, raw, StringComparison.Ordinal);
        using JsonDocument document = JsonDocument.Parse(bytes);
        JsonElement root = document.RootElement;
        AssertSameBytes(CurrentText, root.GetProperty("hedef").GetProperty("metin").GetString()!);
        AssertSameBytes(CurrentText, root.GetProperty("onceki").GetProperty("metin").GetString()!);
        AssertSameBytes(ProposedText, root.GetProperty("onerilen").GetProperty("metin").GetString()!);
    }

    [Fact]
    public async Task The_review_list_writes_the_payload_texts_unescaped_and_byte_equal()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), CurrentText);
        await SeedUnitReviewAsync(unit, proposed: ProposedText);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string raw, byte[] bytes) = await RawAsync(response);
        Assert.DoesNotContain("\\u", raw, StringComparison.Ordinal);
        Assert.Contains(CurrentText, raw, StringComparison.Ordinal);
        Assert.Contains(ProposedText, raw, StringComparison.Ordinal);
        using JsonDocument document = JsonDocument.Parse(bytes);
        JsonElement item = document.RootElement.GetProperty("items").EnumerateArray().Single();
        AssertSameBytes(CurrentText, item.GetProperty("onceki").GetProperty("metin").GetString()!);
        AssertSameBytes(ProposedText, item.GetProperty("onerilen").GetProperty("metin").GetString()!);
    }

    [Fact]
    public async Task A_decision_with_an_edited_text_answers_unescaped_and_the_detail_then_shows_the_edit_byte_equal()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor, CurrentText);
        Review review = await SeedUnitReviewAsync(unit, proposed: ProposedText);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage decision = await DecideAsync(
            client,
            review.Id,
            Etag(await XminAsync(review.Id)),
            Approve("Gerekçe: ışık İ", new { metin = EditedText }));
        using HttpResponseMessage detail = await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct);

        Assert.Equal(HttpStatusCode.OK, decision.StatusCode);
        (string decisionRaw, _) = await RawAsync(decision);
        Assert.DoesNotContain("\\u", decisionRaw, StringComparison.Ordinal);
        Assert.Equal(HttpStatusCode.OK, detail.StatusCode);
        (string raw, byte[] bytes) = await RawAsync(detail);
        Assert.DoesNotContain("\\u", raw, StringComparison.Ordinal);
        Assert.Contains(EditedText, raw, StringComparison.Ordinal);
        Assert.Contains("Gerekçe: ışık İ", raw, StringComparison.Ordinal);
        using JsonDocument document = JsonDocument.Parse(bytes);
        JsonElement root = document.RootElement;
        AssertSameBytes(EditedText, root.GetProperty("duzenlenen").GetProperty("metin").GetString()!);
        AssertSameBytes(EditedText, root.GetProperty("hedef").GetProperty("metin").GetString()!);
        AssertSameBytes("Gerekçe: ışık İ", root.GetProperty("gerekce").GetString()!);
        Assert.Equal(EditedText, (await UnitRowAsync(anchor)).Metin);
    }

    [Fact]
    public async Task A_problem_body_with_a_turkish_message_is_written_unescaped()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), CurrentText);
        Review review = await SeedUnitReviewAsync(unit, proposed: ProposedText);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage stale = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id) + 1), Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, stale.StatusCode);
        (string raw, _) = await RawAsync(stale);
        Assert.DoesNotContain("\\u", raw, StringComparison.Ordinal);
        Assert.Contains("değişti", raw, StringComparison.Ordinal);
    }
}
