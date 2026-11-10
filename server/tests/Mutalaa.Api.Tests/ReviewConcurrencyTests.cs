using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Eszamanlilik (K-48): ayni ETag ile yarisan istekler ve SaveChanges aninda baska baglamin yazdigi degisiklik.
/// Yaris, kaydetmeden hemen once calisan bir kanca ile belirlenimci kurulur; kanca ayri, commit edilmis bir baglamda yazar.
/// </summary>
public class ReviewConcurrencyTests(EditorialDatabase<ReviewConcurrencyTests> fixture)
    : ReviewTestBase<ReviewConcurrencyTests>(fixture), IClassFixture<EditorialDatabase<ReviewConcurrencyTests>>
{
    /// <summary>Bir sonraki SaveChanges'ten once bir kez calisir (ornegin baska baglamda commit).</summary>
    private sealed class BeforeSaveHook : SaveChangesInterceptor
    {
        private Func<Task>? _action;

        public void Arm(Func<Task> action) => _action = action;

        public override async ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            Func<Task>? action = Interlocked.Exchange(ref _action, null);
            if (action is not null)
            {
                await action();
            }

            return result;
        }
    }

    private (ApiFactory Factory, BeforeSaveHook Hook) HookedFactory()
    {
        BeforeSaveHook hook = new();
        ApiFactory factory = CreateFactory(configureServices: services => services.ConfigureDbContext<IcerikDbContext>(o => o.AddInterceptors(hook)));
        return (factory, hook);
    }

    private async Task<string> AliasStatusAsync(SurahAlias alias) =>
        await Db.ScalarAsync<string>("SELECT status::text FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias));

    private async Task SetRiskyInOtherContextAsync(SurahAlias alias)
    {
        await using DbSession session = Db.OpenSession();
        SurahAlias row = await session.Context.SurahAliases.SingleAsync(s => s.SurahNo == alias.SurahNo && s.Alias == alias.Alias, Ct);
        row.Risky = true;
        await session.Context.SaveChangesAsync(Ct);
    }

    private static object Item(Review review, uint xmin) => new { id = review.Id, xmin, karar = "onaylandi", gerekce = "Deneme gerekcesi" };

    [Fact]
    public async Task Two_requests_with_the_same_ETag_one_succeeds_and_the_other_is_412()
    {
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        for (int round = 0; round < 5; round++)
        {
            (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
            string etag = Etag(await XminAsync(review.Id));

            Task<HttpResponseMessage> approve = DecideAsync(editorA, review.Id, etag, Approve());
            Task<HttpResponseMessage> reject = DecideAsync(editorB, review.Id, etag, Reject());
            using HttpResponseMessage first = await approve;
            using HttpResponseMessage second = await reject;

            HttpStatusCode[] statuses = [.. new[] { first.StatusCode, second.StatusCode }.Order()];
            Assert.Equal([HttpStatusCode.OK, HttpStatusCode.PreconditionFailed], statuses);
            HttpResponseMessage winner = first.StatusCode == HttpStatusCode.OK ? first : second;
            HttpResponseMessage loser = first.StatusCode == HttpStatusCode.OK ? second : first;
            Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(loser));
            string expectedDurum = ReferenceEquals(winner, first) ? "onaylandi" : "reddedildi";
            Assert.Equal(expectedDurum, (await ReviewRowAsync(review.Id)).Durum);
            Assert.Equal(expectedDurum == "onaylandi" ? "onayli" : "red", await AliasStatusAsync(alias));
        }
    }

    [Fact]
    public async Task A_target_changed_in_another_context_before_the_save_is_a_412_even_though_the_target_entry_fails()
    {
        (ApiFactory factory, BeforeSaveHook hook) = HookedFactory();
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        uint xmin = await XminAsync(review.Id);
        hook.Arm(() => SetRiskyInOtherContextAsync(alias));

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(xmin), Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(response));
        Assert.Equal("aday", await AliasStatusAsync(alias));
        Assert.True(await Db.ScalarAsync<bool>("SELECT risky FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias)));
        (string durum, _, _, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Equal(xmin, await XminAsync(review.Id));
    }

    [Fact]
    public async Task A_unit_text_changed_in_another_context_before_the_save_is_a_412_and_the_text_stays()
    {
        (ApiFactory factory, BeforeSaveHook hook) = HookedFactory();
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync(factory: factory);
        hook.Arm(() => Db.ExecuteAsync("UPDATE icerik.unit SET attrs = '{\"not\": 1}' WHERE anchor = @a", Ct, ("a", anchor)));

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        (string metin, _, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", durum);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_review_row_changed_in_another_context_before_the_save_is_a_412()
    {
        (ApiFactory factory, BeforeSaveHook hook) = HookedFactory();
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        hook.Arm(() => Db.ExecuteAsync("UPDATE icerik.review SET sure_ms = 5 WHERE id = @id", Ct, ("id", review.Id)));

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("aday", await AliasStatusAsync(alias));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task In_a_bulk_a_target_changed_before_the_save_is_a_412_naming_the_review_and_nothing_is_applied()
    {
        (ApiFactory factory, BeforeSaveHook hook) = HookedFactory();
        (SurahAlias aliasOne, Review one) = await SeedAliasReviewAsync();
        (SurahAlias aliasTwo, Review two) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        uint x1 = await XminAsync(one.Id);
        uint x2 = await XminAsync(two.Id);
        hook.Arm(() => SetRiskyInOtherContextAsync(aliasTwo));

        using HttpResponseMessage response = await client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = new[] { Item(one, x1), Item(two, x2) } }, Ct);

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(response));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        long[] ids = [.. body.GetProperty("kimlikler").EnumerateArray().Select(e => e.GetInt64())];
        Assert.Contains(two.Id, ids);
        Assert.NotEmpty(ids);
        Assert.Equal("aday", await AliasStatusAsync(aliasOne));
        Assert.Equal("aday", await AliasStatusAsync(aliasTwo));
        Assert.Equal("acik", (await ReviewRowAsync(one.Id)).Durum);
        Assert.Equal("acik", (await ReviewRowAsync(two.Id)).Durum);
    }

    [Fact]
    public async Task In_a_bulk_a_review_row_changed_before_the_save_is_a_412_naming_that_review()
    {
        (ApiFactory factory, BeforeSaveHook hook) = HookedFactory();
        (SurahAlias aliasOne, Review one) = await SeedAliasReviewAsync();
        (_, Review two) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        uint x1 = await XminAsync(one.Id);
        uint x2 = await XminAsync(two.Id);
        hook.Arm(() => Db.ExecuteAsync("UPDATE icerik.review SET sure_ms = 5 WHERE id = @id", Ct, ("id", one.Id)));

        using HttpResponseMessage response = await client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = new[] { Item(one, x1), Item(two, x2) } }, Ct);

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Contains(one.Id, body.GetProperty("kimlikler").EnumerateArray().Select(e => e.GetInt64()));
        Assert.Equal("aday", await AliasStatusAsync(aliasOne));
        Assert.Equal("acik", (await ReviewRowAsync(two.Id)).Durum);
    }

    [Fact]
    public async Task Two_bulks_racing_on_the_same_reviews_one_succeeds_and_the_other_is_412_listing_ids()
    {
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);
        (SurahAlias aliasOne, Review one) = await SeedAliasReviewAsync();
        (SurahAlias aliasTwo, Review two) = await SeedAliasReviewAsync();
        object[] items = [Item(one, await XminAsync(one.Id)), Item(two, await XminAsync(two.Id))];

        Task<HttpResponseMessage> a = editorA.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = items }, Ct);
        Task<HttpResponseMessage> b = editorB.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = items }, Ct);
        using HttpResponseMessage first = await a;
        using HttpResponseMessage second = await b;

        HttpStatusCode[] statuses = [.. new[] { first.StatusCode, second.StatusCode }.Order()];
        Assert.Equal([HttpStatusCode.OK, HttpStatusCode.PreconditionFailed], statuses);
        HttpResponseMessage loser = first.StatusCode == HttpStatusCode.OK ? second : first;
        JsonElement body = await ApiFactory.ReadJsonAsync(loser, Ct);
        Assert.NotEmpty(body.GetProperty("kimlikler").EnumerateArray());
        Assert.Equal("onayli", await AliasStatusAsync(aliasOne));
        Assert.Equal("onayli", await AliasStatusAsync(aliasTwo));
    }

    [Fact]
    public async Task The_ETag_from_before_a_decision_is_a_412_afterwards_and_the_response_carries_the_new_one()
    {
        // Karar xmin'i degistirir: eski ETag artik guncel degildir (409 degil, bellekte 412).
        (_, Review review) = await SeedAliasReviewAsync();
        string oldEtag = Etag(await XminAsync(review.Id));
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage first = await DecideAsync(client, review.Id, oldEtag, Approve());
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        using HttpResponseMessage replay = await DecideAsync(client, review.Id, oldEtag, Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, replay.StatusCode);
        Assert.NotEqual(oldEtag, first.Headers.ETag?.Tag);
        Assert.Equal(Etag(await XminAsync(review.Id)), first.Headers.ETag?.Tag);
    }
}
