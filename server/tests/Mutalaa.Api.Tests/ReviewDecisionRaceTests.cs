using System.Data.Common;
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
/// K-48 madde 6: ayni ETag ile yarisan iki karardan kaybeden, incelemeyi kazananin commit'inden ONCE ama hedefi SONRA okursa Domain
/// "hedef artik aday degil" (409) der; dogru yanit bayat surum 412'dir. Yaris, hedef satir okunmadan hemen once calisan bir komut
/// kancasiyla belirlenimci kurulur (kanca ayri, commit edilmis bir baglamda diger kararin etkisini yazar).
/// </summary>
public class ReviewDecisionRaceTests(EditorialDatabase<ReviewDecisionRaceTests> fixture)
    : ReviewTestBase<ReviewDecisionRaceTests>(fixture), IClassFixture<EditorialDatabase<ReviewDecisionRaceTests>>
{
    /// <summary>surah_alias okunmadan once bir kez calisir.</summary>
    private sealed class BeforeAliasReadHook : DbCommandInterceptor
    {
        private Func<Task>? _action;

        public void Arm(Func<Task> action) => _action = action;

        public override async ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<DbDataReader> result,
            CancellationToken cancellationToken = default)
        {
            if (command.CommandText.Contains("surah_alias", StringComparison.Ordinal) && Interlocked.Exchange(ref _action, null) is { } action)
            {
                await action();
            }

            return result;
        }
    }

    private (ApiFactory Factory, BeforeAliasReadHook Hook) HookedFactory()
    {
        BeforeAliasReadHook hook = new();
        ApiFactory factory = CreateFactory(configureServices: services => services.ConfigureDbContext<IcerikDbContext>(o => o.AddInterceptors(hook)));
        return (factory, hook);
    }

    /// <summary>Kazanan karar: review onaylandi ve takma ad onayli (ayri, commit edilmis baglam).</summary>
    private async Task WinnerCommitsAsync(SurahAlias alias, Review review)
    {
        await using DbSession session = Db.OpenSession();
        Review row = await session.Context.Reviews.SingleAsync(r => r.Id == review.Id, Ct);
        row.Durum = ReviewStatus.Onaylandi;
        row.Eylem = ReviewActions.Onayla;
        row.Inceleyen = "kazanan@example.test";
        row.IncelendiAt = DateTime.UtcNow;
        row.Gerekce = "Kazanan karar";
        SurahAlias target = await session.Context.SurahAliases.SingleAsync(s => s.SurahNo == alias.SurahNo && s.Alias == alias.Alias, Ct);
        target.Status = XrefStatus.Onayli;
        await session.Context.SaveChangesAsync(Ct);
    }

    [Fact]
    public async Task A_loser_that_reads_the_review_before_and_the_target_after_the_winner_commits_gets_412_not_409()
    {
        (ApiFactory factory, BeforeAliasReadHook hook) = HookedFactory();
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        uint xmin = await XminAsync(review.Id);
        hook.Arm(() => WinnerCommitsAsync(alias, review));

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(xmin), Reject());

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(response));
        (string durum, string eylem, string? inceleyen, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("onaylandi", durum);
        Assert.Equal("onayla", eylem);
        Assert.Equal("kazanan@example.test", inceleyen);
        Assert.Equal("onayli", await Db.ScalarAsync<string>("SELECT status::text FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias)));
    }

    [Fact]
    public async Task The_same_race_in_a_bulk_is_a_412_naming_the_changed_review_and_nothing_else_is_applied()
    {
        (ApiFactory factory, BeforeAliasReadHook hook) = HookedFactory();
        (SurahAlias aliasOne, Review one) = await SeedAliasReviewAsync();
        (_, Review two) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync(factory: factory);
        uint x1 = await XminAsync(one.Id);
        uint x2 = await XminAsync(two.Id);
        hook.Arm(() => WinnerCommitsAsync(aliasOne, one));

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new
            {
                kararlar = new[]
                {
                    new { id = one.Id, xmin = x1, karar = "onaylandi", gerekce = "Deneme gerekcesi" },
                    new { id = two.Id, xmin = x2, karar = "onaylandi", gerekce = "Deneme gerekcesi" },
                },
            },
            Ct);

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(response));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        long[] ids = [.. body.GetProperty("kimlikler").EnumerateArray().Select(e => e.GetInt64())];
        Assert.Equal([one.Id], ids);
        Assert.Equal("acik", (await ReviewRowAsync(two.Id)).Durum);
    }

    [Fact]
    public async Task A_domain_failure_without_a_concurrent_decision_keeps_its_own_status()
    {
        (_, Review review) = await SeedAliasReviewAsync();
        await Db.ExecuteAsync("UPDATE icerik.surah_alias SET status = 'onayli' WHERE alias = @a", Ct, ("a", review.HedefAnahtar[2..]));
        using HttpClient client = await ClientAsync();
        uint xmin = await XminAsync(review.Id);

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(xmin), Approve());

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
    }
}
