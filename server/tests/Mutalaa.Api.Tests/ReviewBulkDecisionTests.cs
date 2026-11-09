using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>POST /api/v1/reviews/decisions: toplu karar, ya hep ya hic (Docker'li).</summary>
public class ReviewBulkDecisionTests(EditorialDatabase<ReviewBulkDecisionTests> fixture)
    : ReviewTestBase<ReviewBulkDecisionTests>(fixture), IClassFixture<EditorialDatabase<ReviewBulkDecisionTests>>
{
    private sealed record Pair(SurahAlias Alias, Review Review);

    private async Task<List<Pair>> SeedAliasPairsAsync(int count)
    {
        string run = Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6];
        List<Pair> pairs = [];
        await using DbSession session = Db.OpenSession();
        for (int i = 0; i < count; i++)
        {
            SurahAlias alias = new()
            {
                SurahNo = (short)(1 + (i % 100)),
                Alias = $"toplu-{run}-{i.ToString(CultureInfo.InvariantCulture)}",
                AliasKey = "deneme",
                Kind = "yazim",
            };
            Review review = new()
            {
                HedefTablo = ReviewTargets.SurahAlias,
                HedefAnahtar = $"{alias.SurahNo.ToString(CultureInfo.InvariantCulture)}:{alias.Alias}",
                Alan = ReviewFields.Status,
                Eylem = ReviewActions.Oner,
                Koken = XrefOrigin.Hat,
                Oneren = "hat",
            };
            session.Context.AddRange(alias, review);
            pairs.Add(new Pair(alias, review));
        }

        await session.Context.SaveChangesAsync(Ct);
        return pairs;
    }

    private async Task<string> AliasStatusAsync(SurahAlias alias) =>
        await Db.ScalarAsync<string>("SELECT status::text FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias));

    private async Task<object> ItemAsync(Review review, string karar = "onaylandi", string gerekce = "Toplu gerekce") =>
        new { id = review.Id, xmin = await XminAsync(review.Id), karar, gerekce };

    private static Task<HttpResponseMessage> BulkAsync(HttpClient client, IEnumerable<object> items) =>
        client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = items }, Ct);

    private static long[] Ids(JsonElement problem, string name) => [.. problem.GetProperty(name).EnumerateArray().Select(e => e.GetInt64())];

    [Fact]
    public async Task A_bulk_of_mixed_decisions_applies_every_item_in_one_transaction()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(3);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [
            await ItemAsync(pairs[0].Review),
            await ItemAsync(pairs[1].Review, "reddedildi"),
            await ItemAsync(pairs[2].Review),
        ]);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement[] results = [.. (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("sonuclar").EnumerateArray()];
        Assert.Equal(pairs.Select(p => p.Review.Id), results.Select(r => r.GetProperty("id").GetInt64()));
        Assert.Equal(["onaylandi", "reddedildi", "onaylandi"], results.Select(r => r.GetProperty("durum").GetString()));
        Assert.Equal(["onayla", "reddet", "onayla"], results.Select(r => r.GetProperty("eylem").GetString()));
        for (int i = 0; i < pairs.Count; i++)
        {
            Assert.Equal(await XminAsync(pairs[i].Review.Id), results[i].GetProperty("xmin").GetUInt32());
        }

        Assert.Equal(["onayli", "red", "onayli"], [await AliasStatusAsync(pairs[0].Alias), await AliasStatusAsync(pairs[1].Alias), await AliasStatusAsync(pairs[2].Alias)]);
        Assert.Equal(EditorAEmail, (await ReviewRowAsync(pairs[1].Review.Id)).Inceleyen);
    }

    [Fact]
    public async Task A_bulk_of_100_items_succeeds()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(100);
        using HttpClient client = await ClientAsync();
        List<object> items = [];
        foreach (Pair pair in pairs)
        {
            items.Add(await ItemAsync(pair.Review));
        }

        using HttpResponseMessage response = await BulkAsync(client, items);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(100, (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("sonuclar").GetArrayLength());
        Assert.Equal(
            100L,
            await Db.ScalarAsync<long>(
                "SELECT count(*) FROM icerik.surah_alias WHERE alias = ANY(@names) AND status = 'onayli'",
                Ct,
                ("names", pairs.Select(p => p.Alias.Alias).ToArray())));
    }

    [Fact]
    public async Task Zero_and_101_items_a_missing_list_a_repeated_id_and_a_repeated_target_are_400()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(2);
        using HttpClient client = await ClientAsync();
        object first = await ItemAsync(pairs[0].Review);

        using HttpResponseMessage empty = await BulkAsync(client, []);
        using HttpResponseMessage tooMany = await BulkAsync(client, Enumerable.Range(1, 101).Select(i => (object)new { id = (long)i, xmin = 1u, karar = "onaylandi", gerekce = "x" }));
        using HttpResponseMessage missingList = await client.PostAsJsonAsync("/api/v1/reviews/decisions", new { }, Ct);
        using HttpResponseMessage repeated = await BulkAsync(client, [first, first]);
        using HttpResponseMessage badKarar = await BulkAsync(client, [new { id = pairs[1].Review.Id, xmin = 1u, karar = "belki", gerekce = "x" }]);

        foreach (HttpResponseMessage response in new[] { empty, tooMany, missingList, repeated, badKarar })
        {
            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        }

        Assert.Equal("aday", await AliasStatusAsync(pairs[0].Alias));
    }

    [Fact]
    public async Task Two_reviews_on_the_same_target_in_one_bulk_are_a_400_and_apply_nothing()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor());
        Review one = await SeedUnitReviewAsync(unit);
        Review two = await SeedUnitReviewAsync(unit, proposed: Edited);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [await ItemAsync(one), await ItemAsync(two)]);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("acik", (await ReviewRowAsync(one.Id)).Durum);
        Assert.Equal(Current, (await UnitRowAsync(unit.Anchor.ToString())).Metin);
    }

    [Fact]
    public async Task One_stale_xmin_applies_none_and_the_412_lists_every_stale_id()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(4);
        using HttpClient client = await ClientAsync();
        uint x0 = await XminAsync(pairs[0].Review.Id);
        uint x1 = await XminAsync(pairs[1].Review.Id);
        uint x2 = await XminAsync(pairs[2].Review.Id);
        uint x3 = await XminAsync(pairs[3].Review.Id);

        using HttpResponseMessage oneStale = await BulkAsync(client, [
            new { id = pairs[0].Review.Id, xmin = x0, karar = "onaylandi", gerekce = "x" },
            new { id = pairs[1].Review.Id, xmin = x1 + 1, karar = "onaylandi", gerekce = "x" },
        ]);
        using HttpResponseMessage twoStale = await BulkAsync(client, [
            new { id = pairs[0].Review.Id, xmin = x0 + 1, karar = "onaylandi", gerekce = "x" },
            new { id = pairs[1].Review.Id, xmin = x1, karar = "onaylandi", gerekce = "x" },
            new { id = pairs[2].Review.Id, xmin = x2 + 5, karar = "onaylandi", gerekce = "x" },
            new { id = pairs[3].Review.Id, xmin = x3, karar = "onaylandi", gerekce = "x" },
        ]);

        Assert.Equal(HttpStatusCode.PreconditionFailed, oneStale.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(oneStale));
        Assert.Equal([pairs[1].Review.Id], Ids(await ApiFactory.ReadJsonAsync(oneStale, Ct), "kimlikler"));
        Assert.Equal(HttpStatusCode.PreconditionFailed, twoStale.StatusCode);
        Assert.Equal([pairs[0].Review.Id, pairs[2].Review.Id], Ids(await ApiFactory.ReadJsonAsync(twoStale, Ct), "kimlikler"));
        foreach (Pair pair in pairs)
        {
            Assert.Equal("aday", await AliasStatusAsync(pair.Alias));
            Assert.Equal("acik", (await ReviewRowAsync(pair.Review.Id)).Durum);
        }

        Assert.Equal([x0, x1, x2, x3], [await XminAsync(pairs[0].Review.Id), await XminAsync(pairs[1].Review.Id), await XminAsync(pairs[2].Review.Id), await XminAsync(pairs[3].Review.Id)]);
    }

    [Fact]
    public async Task A_domain_error_on_one_item_rolls_the_whole_bulk_back_and_names_the_item()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(3);
        using HttpClient client = await ClientAsync();

        // Ortadaki kayit baska bir istekle zaten karara baglandi.
        using HttpResponseMessage decided = await DecideAsync(client, pairs[1].Review.Id, Etag(await XminAsync(pairs[1].Review.Id)), Reject());
        Assert.Equal(HttpStatusCode.OK, decided.StatusCode);

        using HttpResponseMessage response = await BulkAsync(client, [
            await ItemAsync(pairs[0].Review),
            await ItemAsync(pairs[1].Review),
            await ItemAsync(pairs[2].Review),
        ]);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal(pairs[1].Review.Id, body.GetProperty("kimlik").GetInt64());
        Assert.Equal("aday", await AliasStatusAsync(pairs[0].Alias));
        Assert.Equal("aday", await AliasStatusAsync(pairs[2].Alias));
        Assert.Equal("acik", (await ReviewRowAsync(pairs[0].Review.Id)).Durum);
        Assert.Equal("acik", (await ReviewRowAsync(pairs[2].Review.Id)).Durum);
    }

    [Fact]
    public async Task An_unsupported_item_is_a_422_with_its_id_and_nothing_is_applied()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(1);
        Review unsupported = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Root,
            HedefAnahtar = "1",
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [await ItemAsync(pairs[0].Review), await ItemAsync(unsupported)]);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal(unsupported.Id, (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("kimlik").GetInt64());
        Assert.Equal("aday", await AliasStatusAsync(pairs[0].Alias));
    }

    [Fact]
    public async Task A_missing_review_is_a_404_listing_the_missing_ids_and_nothing_is_applied()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(1);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [
            await ItemAsync(pairs[0].Review),
            new { id = 987654321L, xmin = 1u, karar = "onaylandi", gerekce = "x" },
        ]);
        using HttpResponseMessage single = await BulkAsync(client, [new { id = 987654322L, xmin = 1u, karar = "onaylandi", gerekce = "x" }]);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
        Assert.Equal(new long[] { 987654321L }, Ids(await ApiFactory.ReadJsonAsync(response, Ct), "kimlikler"));
        Assert.Equal(HttpStatusCode.NotFound, single.StatusCode);
        Assert.Equal(new long[] { 987654322L }, Ids(await ApiFactory.ReadJsonAsync(single, Ct), "kimlikler"));
        Assert.Equal("aday", await AliasStatusAsync(pairs[0].Alias));
    }

    [Fact]
    public async Task A_bulk_can_mix_status_targets_and_unit_text_and_applies_the_text_with_its_hash()
    {
        List<Pair> pairs = await SeedAliasPairsAsync(1);
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        Review text = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [await ItemAsync(pairs[0].Review), await ItemAsync(text)]);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Proposed, metin);
        Assert.Equal(Mutalaa.Domain.Text.ContentHash.Compute(Proposed), hash);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
        Assert.Equal("onayli", await AliasStatusAsync(pairs[0].Alias));
    }

    [Fact]
    public async Task A_bulk_gives_the_first_approval_of_a_meal_and_a_different_editor_completes_it_in_a_later_bulk()
    {
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await BulkAsync(editorA, [await ItemAsync(review)]);
        using HttpResponseMessage sameEditor = await BulkAsync(editorA, [await ItemAsync(review)]);
        using HttpResponseMessage second = await BulkAsync(editorB, [await ItemAsync(review)]);

        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal("acik", (await ApiFactory.ReadJsonAsync(first, Ct)).GetProperty("sonuclar")[0].GetProperty("durum").GetString());
        Assert.Equal(HttpStatusCode.Conflict, sameEditor.StatusCode);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);
        Assert.Equal(Proposed, (await UnitRowAsync(anchor)).Metin);
        Assert.Equal(EditorBEmail, (await ReviewRowAsync(review.Id)).Ikinci);
    }
}
