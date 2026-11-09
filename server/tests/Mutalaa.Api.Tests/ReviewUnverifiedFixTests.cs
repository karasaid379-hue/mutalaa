using System.Globalization;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// "dogrulanmamis" rozeti listede ve ayrintida ayni kuralla hesaplanir:
/// yz_modeli dolu ve not (review onaylandi ve hedef onayli). Sentetik veri (Docker'li).
/// </summary>
public class ReviewUnverifiedFixTests(EditorialDatabase<ReviewUnverifiedFixTests> fixture)
    : ReviewTestBase<ReviewUnverifiedFixTests>(fixture), IClassFixture<EditorialDatabase<ReviewUnverifiedFixTests>>
{
    private const string Model = "deneme-model-1";

    private static JsonElement[] Items(JsonElement body) => [.. body.GetProperty("items").EnumerateArray()];

    private async Task<Dictionary<long, bool>> ListUnverifiedAsync(HttpClient client, string durum)
    {
        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?limit=200&durum=" + durum, Ct), Ct);
        return Items(body).ToDictionary(i => i.GetProperty("id").GetInt64(), i => i.GetProperty("dogrulanmamis").GetBoolean());
    }

    private async Task<bool> DetailUnverifiedAsync(HttpClient client, long id)
    {
        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{id.ToString(CultureInfo.InvariantCulture)}", Ct), Ct);
        return body.GetProperty("dogrulanmamis").GetBoolean();
    }

    private async Task<Review> XrefReviewAsync(string src, XrefStatus xrefStatus, ReviewStatus durum)
    {
        Xref xref = TestData.NewXref(src, "meal:elmalili:" + src["q:".Length..]);
        xref.Status = xrefStatus;
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(xref);
            await session.Context.SaveChangesAsync(Ct);
        }

        return await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = xref.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = xref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = durum,
            YzModeli = Model,
            YzKaydi = YzRecord(),
        });
    }

    [Fact]
    public async Task The_list_and_the_detail_agree_on_dogrulanmamis_for_every_target_and_review_status()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);

        Unit approvedUnit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), durum: TextStatus.Onayli);
        Unit draftUnit = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), durum: TextStatus.Taslak);

        // (etiket, review, beklenen dogrulanmamis)
        List<(string Label, Review Review, bool Expected)> cases = [];
        cases.Add(("unit onayli + onaylandi", await SeedUnitReviewAsync(approvedUnit, durum: ReviewStatus.Onaylandi, yzModeli: Model), false));
        cases.Add(("unit taslak + onaylandi", await SeedUnitReviewAsync(draftUnit, durum: ReviewStatus.Onaylandi, yzModeli: Model), true));
        cases.Add(("unit onayli + acik", await SeedUnitReviewAsync(approvedUnit, durum: ReviewStatus.Acik, yzModeli: Model), true));
        cases.Add(("unit onayli + reddedildi", await SeedUnitReviewAsync(approvedUnit, durum: ReviewStatus.Reddedildi, yzModeli: Model), true));
        cases.Add(("unit onayli + geri_alindi", await SeedUnitReviewAsync(approvedUnit, durum: ReviewStatus.GeriAlindi, yzModeli: Model), true));
        cases.Add(("unit onayli + onaylandi + yz yok", await SeedUnitReviewAsync(approvedUnit, durum: ReviewStatus.Onaylandi), false));
        cases.Add(("unit taslak + onaylandi + yz yok", await SeedUnitReviewAsync(draftUnit, durum: ReviewStatus.Onaylandi), false));

        // Birim satiri olmayan, ama gecerli capa: hedef onayli sayilmaz.
        Review missingUnit = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = TestData.UnitAnchor(),
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = ReviewStatus.Onaylandi,
            YzModeli = Model,
            YzKaydi = YzRecord(),
        });
        cases.Add(("unit satiri yok + onaylandi", missingUnit, true));

        (SurahAlias candidateAlias, Review candidateReview) = await SeedAliasReviewAsync("Aday-sure");
        await Db.ExecuteAsync(
            "UPDATE icerik.review SET durum = 'onaylandi', yz_modeli = @m, yz_kaydi = @k::jsonb WHERE id = @id",
            Ct,
            ("m", Model),
            ("k", YzRecord()),
            ("id", candidateReview.Id));
        Assert.Equal(XrefStatus.Aday, candidateAlias.Status);
        cases.Add(("surah_alias aday + onaylandi", candidateReview, true));

        (SurahAlias approvedAlias, Review approvedAliasReview) = await SeedAliasReviewAsync("Onayli-sure");
        await Db.ExecuteAsync("UPDATE icerik.surah_alias SET status = 'onayli' WHERE alias = @a", Ct, ("a", approvedAlias.Alias));
        await Db.ExecuteAsync(
            "UPDATE icerik.review SET durum = 'onaylandi', yz_modeli = @m, yz_kaydi = @k::jsonb WHERE id = @id",
            Ct,
            ("m", Model),
            ("k", YzRecord()),
            ("id", approvedAliasReview.Id));
        cases.Add(("surah_alias onayli + onaylandi", approvedAliasReview, false));

        cases.Add(("xref onayli + onaylandi", await XrefReviewAsync("q:2:250", XrefStatus.Onayli, ReviewStatus.Onaylandi), false));
        cases.Add(("xref aday + onaylandi", await XrefReviewAsync("q:2:251", XrefStatus.Aday, ReviewStatus.Onaylandi), true));
        cases.Add(("xref onayli + acik", await XrefReviewAsync("q:2:252", XrefStatus.Onayli, ReviewStatus.Acik), true));

        // Durum sutunu olmayan hedef: dogrulanmis, review durumundan turetilir.
        Review rootApproved = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Root,
            HedefAnahtar = "1",
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = ReviewStatus.Onaylandi,
            YzModeli = Model,
            YzKaydi = YzRecord(),
        });
        Review rootRejected = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Root,
            HedefAnahtar = "2",
            Alan = "status",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = ReviewStatus.Reddedildi,
            YzModeli = Model,
            YzKaydi = YzRecord(),
        });
        cases.Add(("root onaylandi", rootApproved, false));
        cases.Add(("root reddedildi", rootRejected, true));

        using HttpClient client = await ClientAsync();
        Dictionary<long, bool> listed = [];
        foreach (string durum in new[] { "acik", "onaylandi", "reddedildi", "geri_alindi" })
        {
            foreach ((long id, bool value) in await ListUnverifiedAsync(client, durum))
            {
                listed[id] = value;
            }
        }

        foreach ((string label, Review review, bool expected) in cases)
        {
            Assert.True(listed.TryGetValue(review.Id, out bool inList), $"Listede yok: {label}");
            bool inDetail = await DetailUnverifiedAsync(client, review.Id);
            Assert.True(expected == inList, $"Liste beklenen {expected}, gelen {inList}: {label}");
            Assert.True(expected == inDetail, $"Ayrinti beklenen {expected}, gelen {inDetail}: {label}");
        }
    }

    [Fact]
    public async Task An_open_ai_review_on_an_approved_unit_is_unverified_until_the_review_itself_is_approved()
    {
        await ResetReviewsAsync();
        string source = await SeedSourceAsync(SourceKind.Risale);
        Unit approved = await SeedUnitAsync(source, UnitKind.Risale, TestData.UnitAnchor(), durum: TextStatus.Onayli);
        Review open = await SeedUnitReviewAsync(approved, yzModeli: Model);
        Review done = await SeedUnitReviewAsync(approved, durum: ReviewStatus.Onaylandi, yzModeli: Model);
        using HttpClient client = await ClientAsync();

        Assert.True(await DetailUnverifiedAsync(client, open.Id));
        Assert.False(await DetailUnverifiedAsync(client, done.Id));
        Assert.True((await ListUnverifiedAsync(client, "acik"))[open.Id]);
        Assert.False((await ListUnverifiedAsync(client, "onaylandi"))[done.Id]);
    }
}
