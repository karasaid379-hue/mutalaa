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
/// Degistirilemez metin (unit.kind = ayet ya da source.tur = kuran_metni, K-48 madde 5) toplu ve tekil kararda 422
/// <c>degistirilemez-metin</c> olur; toplu istekte oteki kararlar da uygulanmaz (ya hep ya hic). Metinler sentetiktir (Docker'li).
/// </summary>
public class ReviewBulkImmutableTests(EditorialDatabase<ReviewBulkImmutableTests> fixture)
    : ReviewTestBase<ReviewBulkImmutableTests>(fixture), IClassFixture<EditorialDatabase<ReviewBulkImmutableTests>>
{
    private async Task<(SurahAlias Alias, Review Review)> SeedAliasPairAsync()
    {
        string run = Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6];
        SurahAlias alias = new() { SurahNo = 1, Alias = "degismez-" + run, AliasKey = "deneme", Kind = "yazim" };
        Review review = new()
        {
            HedefTablo = ReviewTargets.SurahAlias,
            HedefAnahtar = "1:" + alias.Alias,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.AddRange(alias, review);
        await session.Context.SaveChangesAsync(Ct);
        return (alias, review);
    }

    private async Task<string> AliasStatusAsync(SurahAlias alias) =>
        await Db.ScalarAsync<string>("SELECT status::text FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias));

    private async Task<object> ItemAsync(Review review, string karar = "onaylandi") =>
        new { id = review.Id, xmin = await XminAsync(review.Id), karar, gerekce = "Toplu gerekce" };

    private static Task<HttpResponseMessage> BulkAsync(HttpClient client, IEnumerable<object> items) =>
        client.PostAsJsonAsync("/api/v1/reviews/decisions", new { kararlar = items }, Ct);

    /// <summary>Degismez birim: ayet turu (meal kaynaginda) ya da kuran_metni kaynagi (risale turu).</summary>
    private async Task<(Unit Unit, string Anchor)> SeedImmutableUnitAsync(bool ayetKind)
    {
        string source = await SeedSourceAsync(ayetKind ? SourceKind.Meal : SourceKind.KuranMetni);
        string anchor = ayetKind ? AyetAnchor() : TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, ayetKind ? UnitKind.Ayet : UnitKind.Risale, anchor);
        return (unit, anchor);
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, false)]
    [InlineData(true, true)]
    [InlineData(false, true)]
    public async Task A_bulk_with_an_immutable_text_approval_is_a_422_naming_it_and_applies_no_other_decision(bool ayetKind, bool immutableFirst)
    {
        (SurahAlias alias, Review aliasReview) = await SeedAliasPairAsync();
        (Unit unit, string anchor) = await SeedImmutableUnitAsync(ayetKind);
        Review immutable = await SeedUnitReviewAsync(unit);
        string mutableSource = await SeedSourceAsync(SourceKind.Risale);
        string mutableAnchor = TestData.UnitAnchor();
        Unit mutableUnit = await SeedUnitAsync(mutableSource, UnitKind.Risale, mutableAnchor);
        Review mutableReview = await SeedUnitReviewAsync(mutableUnit);
        using HttpClient client = await ClientAsync();
        object[] items = immutableFirst
            ? [await ItemAsync(immutable), await ItemAsync(aliasReview), await ItemAsync(mutableReview)]
            : [await ItemAsync(aliasReview), await ItemAsync(mutableReview), await ItemAsync(immutable)];

        using HttpResponseMessage response = await BulkAsync(client, items);

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("degistirilemez-metin", await ProblemCodeAsync(response));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal(immutable.Id, body.GetProperty("kimlik").GetInt64());
        Assert.Equal("aday", await AliasStatusAsync(alias));
        Assert.Equal("acik", (await ReviewRowAsync(aliasReview.Id)).Durum);
        Assert.Equal("acik", (await ReviewRowAsync(mutableReview.Id)).Durum);
        Assert.Equal("acik", (await ReviewRowAsync(immutable.Id)).Durum);
        Assert.Equal(Current, (await UnitRowAsync(anchor)).Metin);
        (string metin, _, int rev, string durum) = await UnitRowAsync(mutableAnchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", durum);
    }

    [Fact]
    public async Task A_bulk_that_rejects_an_immutable_text_review_is_allowed()
    {
        (Unit unit, string anchor) = await SeedImmutableUnitAsync(ayetKind: true);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await BulkAsync(client, [await ItemAsync(review, "reddedildi")]);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("reddedildi", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal(Current, (await UnitRowAsync(anchor)).Metin);
    }

    [Fact]
    public async Task A_meal_in_an_immutable_source_cannot_get_a_first_or_a_second_approval_and_its_text_stays()
    {
        // source.tur = kuran_metni, kind = meal: iki asamali onay yolu da 422 doner (K-48 madde 5).
        string source = await SeedSourceAsync(SourceKind.KuranMetni);
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage first = await DecideAsync(editorA, review.Id, Etag(await XminAsync(review.Id)), Approve());
        using HttpResponseMessage second = await DecideAsync(editorB, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, first.StatusCode);
        Assert.Equal("degistirilemez-metin", await ProblemCodeAsync(first));
        Assert.Equal(HttpStatusCode.UnprocessableEntity, second.StatusCode);
        Assert.Equal("degistirilemez-metin", await ProblemCodeAsync(second));
        (string durum, _, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Null(inceleyen);
        Assert.Null(ikinci);
        (string metin, string hash, int rev, string unitDurum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(unit.ContentHash, hash);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", unitDurum);
    }

    [Fact]
    public async Task A_meal_in_an_immutable_source_with_a_first_approval_already_recorded_still_refuses_the_second_approval()
    {
        // Ilk onay veritabaninda (kaynak sonradan kuran_metni olarak duzeltilmis ya da veri elle bozulmus gibi): ikinci onay yine 422.
        string source = await SeedSourceAsync(SourceKind.KuranMetni);
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor, durum: TextStatus.Incelemede);
        Review review = await SeedUnitReviewAsync(unit);
        await Db.ExecuteAsync(
            "UPDATE icerik.review SET inceleyen = @i, incelendi_at = now() WHERE id = @id",
            Ct,
            ("i", EditorAEmail),
            ("id", review.Id));
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage second = await DecideAsync(editorB, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, second.StatusCode);
        Assert.Equal("degistirilemez-metin", await ProblemCodeAsync(second));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
        Assert.Equal(Current, (await UnitRowAsync(anchor)).Metin);
    }
}
