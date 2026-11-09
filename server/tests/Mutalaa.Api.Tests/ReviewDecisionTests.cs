using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>POST /api/v1/reviews/{id}/decision: durum hedefleri, birim metni, ikinci onay, dort goz ve hata kodlari (Docker'li).</summary>
public class ReviewDecisionTests(EditorialDatabase<ReviewDecisionTests> fixture)
    : ReviewTestBase<ReviewDecisionTests>(fixture), IClassFixture<EditorialDatabase<ReviewDecisionTests>>
{
    private static int _lemmaCounter = 1000;

    private async Task<string> AliasStatusAsync(SurahAlias alias) =>
        await Db.ScalarAsync<string>("SELECT status::text FROM icerik.surah_alias WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias));

    private async Task<(string? TrNarrow, string? TrWide, string? ArNorm, string? TrStem, DateTime UpdatedAt)> UnitSearchAsync(string anchor)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT tr_narrow, tr_wide, ar_norm, tr_stem, updated_at FROM icerik.unit WHERE anchor = @a",
            connection);
        command.Parameters.AddWithValue("a", anchor);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return (
            reader.IsDBNull(0) ? null : reader.GetString(0),
            reader.IsDBNull(1) ? null : reader.GetString(1),
            reader.IsDBNull(2) ? null : reader.GetString(2),
            reader.IsDBNull(3) ? null : reader.GetString(3),
            reader.GetDateTime(4));
    }

    private async Task<(int LemmaId, Review Review)> SeedGlossReviewAsync()
    {
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        int lemmaId = Interlocked.Increment(ref _lemmaCounter);
        Lemma lemma = new() { Id = lemmaId, Lang = "ar", Text = "deneme", TextClean = "deneme", SourceId = source, DataVersion = "test" };
        LemmaGloss gloss = new() { LemmaId = lemmaId, AnlamKisa = "deneme anlami", Origin = "test", Version = "1", ContentHash = TestData.Hash() };
        Review review = new()
        {
            HedefTablo = ReviewTargets.LemmaGloss,
            HedefAnahtar = lemmaId.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.AnlamKisa,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.AddRange(lemma, gloss, review);
        await session.Context.SaveChangesAsync(Ct);
        return (lemmaId, review);
    }

    [Fact]
    public async Task Approving_a_surah_alias_sets_status_onayli_and_writes_the_review_row()
    {
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal(review.Id, body.GetProperty("id").GetInt64());
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayla", body.GetProperty("eylem").GetString());
        Assert.False(body.GetProperty("ikinci_onay_bekliyor").GetBoolean());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        Assert.Equal("onayli", await AliasStatusAsync(alias));
        (string durum, string eylem, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("onaylandi", durum);
        Assert.Equal("onayla", eylem);
        Assert.Equal(EditorAEmail, inceleyen);
        Assert.Null(ikinci);
        Assert.NotNull(await Db.ScalarAsync<DateTime?>("SELECT incelendi_at FROM icerik.review WHERE id = @id", Ct, ("id", review.Id)));

        // Yeni ETag, govdedeki xmin ve veritabani ayni.
        uint xmin = await XminAsync(review.Id);
        Assert.Equal(xmin, body.GetProperty("xmin").GetUInt32());
        Assert.Equal(Etag(xmin), response.Headers.ETag?.Tag);
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task Rejecting_a_surah_alias_sets_status_red_and_the_review_is_reddedildi()
    {
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("red", await AliasStatusAsync(alias));
        (string durum, string eylem, _, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("reddedildi", durum);
        Assert.Equal("reddet", eylem);
    }

    [Fact]
    public async Task A_second_decision_on_a_decided_review_is_a_409()
    {
        (_, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage first = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        using HttpResponseMessage second = await DecideAsync(client, review.Id, first.Headers.ETag!.Tag, Reject());

        Assert.Equal(HttpStatusCode.Conflict, second.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(second));
    }

    [Fact]
    public async Task A_target_that_is_not_a_candidate_any_more_is_a_409()
    {
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        await Db.ExecuteAsync("UPDATE icerik.surah_alias SET status = 'onayli' WHERE surah_no = @n AND alias = @a", Ct, ("n", alias.SurahNo), ("a", alias.Alias));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task A_missing_If_Match_is_428_and_malformed_ones_are_400()
    {
        (_, Review review) = await SeedAliasReviewAsync();
        uint xmin = await XminAsync(review.Id);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage missing = await DecideAsync(client, review.Id, null, Approve());
        Assert.Equal(HttpStatusCode.PreconditionRequired, missing.StatusCode);
        Assert.Equal("surum-gerekli", await ProblemCodeAsync(missing));

        foreach (string bad in new[] { "*", "W/" + Etag(xmin), Etag(xmin) + ", " + Etag(xmin + 1), xmin.ToString(CultureInfo.InvariantCulture), "\"\"", "\"-1\"", "\"abc\"", "\"99999999999\"" })
        {
            using HttpResponseMessage response = await DecideAsync(client, review.Id, bad, Approve());
            Assert.True(response.StatusCode == HttpStatusCode.BadRequest, $"If-Match {bad} -> {(int)response.StatusCode}");
            Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        }

        // Hicbiri karari uygulamadi.
        (string durum, _, _, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
    }

    [Fact]
    public async Task A_stale_ETag_is_a_412_and_changes_nothing()
    {
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        uint xmin = await XminAsync(review.Id);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(xmin + 1), Approve());

        Assert.Equal(HttpStatusCode.PreconditionFailed, response.StatusCode);
        Assert.Equal("surum-uyusmazligi", await ProblemCodeAsync(response));
        Assert.Equal("aday", await AliasStatusAsync(alias));
        Assert.Equal(xmin, await XminAsync(review.Id));
    }

    [Fact]
    public async Task A_missing_review_is_a_404()
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, 987654321, "\"1\"", Approve());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task A_review_whose_target_row_is_gone_is_a_404()
    {
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.SurahAlias,
            HedefAnahtar = "1:yok-boyle-bir-ad",
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
    }

    [Theory]
    [InlineData("{\"karar\":\"onaylandi\",\"gerekce\":\"\"}")]
    [InlineData("{\"karar\":\"onaylandi\",\"gerekce\":\"   \"}")]
    [InlineData("{\"karar\":\"onaylandi\"}")]
    [InlineData("{\"karar\":\"belki\",\"gerekce\":\"x\"}")]
    [InlineData("{\"gerekce\":\"x\"}")]
    [InlineData("{\"karar\":\"onaylandi\",\"gerekce\":\"x\",\"bilinmeyen\":1}")]
    [InlineData("{\"karar\":\"reddedildi\",\"gerekce\":\"x\",\"duzenlenen\":{\"metin\":\"Deneme paragrafi 9\"}}")]
    [InlineData("{bozuk")]
    public async Task An_invalid_decision_body_is_a_400_and_leaves_the_review_open(string json)
    {
        (_, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();
        using HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id}/decision")
        {
            Content = new StringContent(json, System.Text.Encoding.UTF8, "application/json"),
        };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));

        using HttpResponseMessage response = await client.SendAsync(request, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        (string durum, _, _, _) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
    }

    [Fact]
    public async Task A_gerekce_over_2000_code_points_is_a_400()
    {
        (_, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(new string('a', 2001)));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Approving_a_lemma_gloss_anlam_kisa_review_sets_the_gloss_status_and_advances_updated_at()
    {
        (int lemmaId, Review review) = await SeedGlossReviewAsync();

        // updated_at bir saat geriye alinir: konteyner ile ana makine saati arasindaki farka bagli olmasin.
        await Db.ExecuteAsync("UPDATE icerik.lemma_gloss SET updated_at = now() - interval '1 hour' WHERE lemma_id = @id", Ct, ("id", lemmaId));
        DateTime before = await Db.ScalarAsync<DateTime>("SELECT updated_at FROM icerik.lemma_gloss WHERE lemma_id = @id", Ct, ("id", lemmaId));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("onayli", await Db.ScalarAsync<string>("SELECT status::text FROM icerik.lemma_gloss WHERE lemma_id = @id", Ct, ("id", lemmaId)));
        DateTime after = await Db.ScalarAsync<DateTime>("SELECT updated_at FROM icerik.lemma_gloss WHERE lemma_id = @id", Ct, ("id", lemmaId));
        Assert.True(after > before);
    }

    [Fact]
    public async Task Approving_an_xref_review_works_and_a_rejected_xref_becomes_red()
    {
        Xref approveXref = TestData.NewXref();
        Xref rejectXref = TestData.NewXref(type: XrefType.Iktibas);
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.AddRange(approveXref, rejectXref);
            await session.Context.SaveChangesAsync(Ct);
        }

        Review approveReview = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = approveXref.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = approveXref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        Review rejectReview = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = rejectXref.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = rejectXref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage approved = await DecideAsync(client, approveReview.Id, Etag(await XminAsync(approveReview.Id)), Approve());
        using HttpResponseMessage rejected = await DecideAsync(client, rejectReview.Id, Etag(await XminAsync(rejectReview.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
        Assert.Equal("onayli", await Db.ScalarAsync<string>("SELECT status::text FROM icerik.xref WHERE id = @id", Ct, ("id", approveXref.Id)));
        Assert.Equal("red", await Db.ScalarAsync<string>("SELECT status::text FROM icerik.xref WHERE id = @id", Ct, ("id", rejectXref.Id)));
    }

    [Fact]
    public async Task A_value_edit_on_a_status_target_is_422_inceleme_desteklenmiyor()
    {
        (SurahAlias alias, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = "Deneme paragrafi 9" }));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        Assert.Equal("aday", await AliasStatusAsync(alias));
    }

    [Theory]
    [InlineData("root", "status")]
    [InlineData("tr_form", "status")]
    [InlineData("xref", "tur")]
    [InlineData("unit", "status")]
    [InlineData("surah_alias", "alias")]
    [InlineData("lemma_gloss", "status")]
    public async Task An_unsupported_target_or_field_is_422_inceleme_desteklenmiyor(string hedefTablo, string alan)
    {
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = hedefTablo,
            HedefAnahtar = "1",
            Alan = alan,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task A_malformed_target_key_is_a_400()
    {
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = "bir-guid-degil",
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
    }

    // Birim metni (meal/tefsir disi: tek onay)

    [Fact]
    public async Task Approving_a_text_review_applies_the_new_text_with_hash_rev_and_search_keys()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        // updated_at bir saat geriye alinir: konteyner ile ana makine saati arasindaki farka bagli olmasin.
        await Db.ExecuteAsync("UPDATE icerik.unit SET tr_stem = 'eski', updated_at = now() - interval '1 hour' WHERE anchor = @a", Ct, ("a", anchor));
        (_, _, _, _, DateTime updatedBefore) = await UnitSearchAsync(anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Proposed, metin);
        Assert.Equal(ContentHash.Compute(TextCanonicalizer.Canonicalize(Proposed)), hash);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
        SearchKeys keys = SearchNormalizer.Keys(Proposed);
        (string? narrow, string? wide, string? arNorm, string? stem, DateTime updatedAfter) = await UnitSearchAsync(anchor);
        Assert.Equal(keys.TrNarrow, narrow);
        Assert.Equal(keys.TrWide, wide);
        Assert.Equal(keys.ArNorm, arNorm);
        Assert.Null(stem);
        Assert.True(updatedAfter > updatedBefore);
        Assert.Equal("onayla", (await ReviewRowAsync(review.Id)).Eylem);
    }

    [Fact]
    public async Task Approving_with_an_edited_value_applies_it_and_keeps_the_original_proposal()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = Edited }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(Edited, (await UnitRowAsync(anchor)).Metin);
        Assert.Equal("duzenle_onayla", (await ReviewRowAsync(review.Id)).Eylem);
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.Equal(Edited, detail.GetProperty("duzenlenen").GetProperty("metin").GetString());
        Assert.Equal(ContentHash.Compute(Edited), detail.GetProperty("duzenlenen").GetProperty("content_hash").GetString());
        Assert.Equal(Proposed, detail.GetProperty("onerilen").GetProperty("metin").GetString());
    }

    [Fact]
    public async Task Rejecting_a_text_review_leaves_the_unit_text_unchanged()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(unit.ContentHash, hash);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", durum);
        Assert.Equal("reddedildi", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_unit_text_changed_after_the_review_opened_makes_the_target_stale_and_is_a_409()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        string other = "Deneme paragrafi 7";
        await Db.ExecuteAsync(
            "UPDATE icerik.unit SET metin = @m, content_hash = @h WHERE anchor = @a",
            Ct,
            ("m", other),
            ("h", ContentHash.Compute(other)),
            ("a", anchor));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        Assert.Equal(other, (await UnitRowAsync(anchor)).Metin);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task An_immutable_unit_text_cannot_be_approved_but_can_be_rejected(bool ayetKind)
    {
        // ayet birimi ya da kuran_metni kaynagi: iki yol da degismez metindir.
        string source = await SeedSourceAsync(ayetKind ? SourceKind.Meal : SourceKind.KuranMetni);
        string anchor = ayetKind ? AyetAnchor() : TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, ayetKind ? UnitKind.Ayet : UnitKind.Risale, anchor);
        Review toApprove = await SeedUnitReviewAsync(unit);
        Review toReject = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage approve = await DecideAsync(client, toApprove.Id, Etag(await XminAsync(toApprove.Id)), Approve());
        using HttpResponseMessage reject = await DecideAsync(client, toReject.Id, Etag(await XminAsync(toReject.Id)), Reject());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, approve.StatusCode);
        Assert.Equal("degistirilemez-metin", await ProblemCodeAsync(approve));
        Assert.Equal(HttpStatusCode.OK, reject.StatusCode);
        Assert.Equal(Current, (await UnitRowAsync(anchor)).Metin);
        Assert.Equal("acik", (await ReviewRowAsync(toApprove.Id)).Durum);
    }

    // Ikinci onay (meal ve tefsir)

    [Fact]
    public async Task The_first_approval_of_a_draft_meal_keeps_the_review_open_and_moves_the_unit_to_incelemede()
    {
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("acik", body.GetProperty("durum").GetString());
        Assert.True(body.GetProperty("ikinci_onay_bekliyor").GetBoolean());
        Assert.Equal("incelemede", body.GetProperty("hedef_durumu").GetString());
        (string durum, _, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("acik", durum);
        Assert.Equal(EditorAEmail, inceleyen);
        Assert.Null(ikinci);
        (string metin, _, int rev, string unitDurum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("incelemede", unitDurum);
    }

    [Fact]
    public async Task The_first_approval_of_an_approved_meal_keeps_its_text_and_status()
    {
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor, durum: TextStatus.Onayli);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string metin, _, int rev, string unitDurum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("onayli", unitDurum);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task The_same_editor_cannot_give_the_second_approval_but_a_different_editor_applies_the_value()
    {
        string source = await SeedSourceAsync(SourceKind.Tefsir);
        string anchor = TefsirAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Tefsir, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);
        using HttpResponseMessage first = await DecideAsync(editorA, review.Id, Etag(await XminAsync(review.Id)), Approve("Birinci gerekce"));
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        using HttpResponseMessage sameEditor = await DecideAsync(editorA, review.Id, first.Headers.ETag!.Tag, Approve("Ikinci gerekce"));
        using HttpResponseMessage otherEditor = await DecideAsync(editorB, review.Id, first.Headers.ETag!.Tag, Approve("Ikinci gerekce"));

        Assert.Equal(HttpStatusCode.Conflict, sameEditor.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(sameEditor));
        Assert.Equal(HttpStatusCode.OK, otherEditor.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(otherEditor, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.False(body.GetProperty("ikinci_onay_bekliyor").GetBoolean());
        (string durum, _, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("onaylandi", durum);
        Assert.Equal(EditorAEmail, inceleyen);
        Assert.Equal(EditorBEmail, ikinci);
        (string metin, string hash, int rev, string unitDurum) = await UnitRowAsync(anchor);
        Assert.Equal(Proposed, metin);
        Assert.Equal(ContentHash.Compute(Proposed), hash);
        Assert.Equal(2, rev);
        Assert.Equal("onayli", unitDurum);
        JsonElement detail = await ApiFactory.ReadJsonAsync(await editorB.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.Equal(EditorBEmail, detail.GetProperty("ikinci_inceleyen").GetString());
        Assert.Equal("Ikinci gerekce", detail.GetProperty("ikinci_gerekce").GetString());
        Assert.Equal("Birinci gerekce", detail.GetProperty("gerekce").GetString());
        Assert.Equal(JsonValueKind.String, detail.GetProperty("ikinci_incelendi_at").ValueKind);
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task An_edit_given_at_the_first_approval_is_what_the_second_approval_applies_and_the_second_cannot_edit()
    {
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);
        using HttpResponseMessage first = await DecideAsync(editorA, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = Edited }));
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal("duzenle_onayla", (await ReviewRowAsync(review.Id)).Eylem);

        using HttpResponseMessage withEdit = await DecideAsync(editorB, review.Id, first.Headers.ETag!.Tag, Approve(duzenlenen: new { metin = "Deneme paragrafi 8" }));
        using HttpResponseMessage plain = await DecideAsync(editorB, review.Id, first.Headers.ETag!.Tag, Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, withEdit.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(withEdit));
        Assert.Equal(HttpStatusCode.OK, plain.StatusCode);
        Assert.Equal(Edited, (await UnitRowAsync(anchor)).Metin);
    }

    [Fact]
    public async Task A_second_stage_rejection_returns_the_unit_to_taslak()
    {
        string source = await SeedSourceAsync();
        string anchor = MealAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Meal, anchor);
        Review review = await SeedUnitReviewAsync(unit);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);
        using HttpResponseMessage first = await DecideAsync(editorA, review.Id, Etag(await XminAsync(review.Id)), Approve());
        Assert.Equal("incelemede", (await UnitRowAsync(anchor)).Durum);

        using HttpResponseMessage rejected = await DecideAsync(editorB, review.Id, first.Headers.ETag!.Tag, Reject());

        Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
        (string durum, string eylem, string? inceleyen, string? ikinci) = await ReviewRowAsync(review.Id);
        Assert.Equal("reddedildi", durum);
        Assert.Equal("reddet", eylem);
        Assert.Equal(EditorAEmail, inceleyen);
        Assert.Equal(EditorBEmail, ikinci);
        (string metin, _, int rev, string unitDurum) = await UnitRowAsync(anchor);
        Assert.Equal(Current, metin);
        Assert.Equal(1, rev);
        Assert.Equal("taslak", unitDurum);
    }

    // Dort goz

    [Fact]
    public async Task An_editor_cannot_approve_their_own_proposal_but_can_reject_it()
    {
        (SurahAlias aliasA, Review approveReview) = await SeedAliasReviewAsync(koken: XrefOrigin.Editor, oneren: EditorAEmail);
        (SurahAlias aliasB, Review rejectReview) = await SeedAliasReviewAsync(koken: XrefOrigin.Editor, oneren: EditorAEmail);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage own = await DecideAsync(editorA, approveReview.Id, Etag(await XminAsync(approveReview.Id)), Approve());
        using HttpResponseMessage ownReject = await DecideAsync(editorA, rejectReview.Id, Etag(await XminAsync(rejectReview.Id)), Reject());
        using HttpResponseMessage other = await DecideAsync(editorB, approveReview.Id, Etag(await XminAsync(approveReview.Id)), Approve());

        Assert.Equal(HttpStatusCode.Conflict, own.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(own));
        Assert.Equal(HttpStatusCode.OK, ownReject.StatusCode);
        Assert.Equal("red", await AliasStatusAsync(aliasB));
        Assert.Equal(HttpStatusCode.OK, other.StatusCode);
        Assert.Equal("onayli", await AliasStatusAsync(aliasA));
    }

    [Fact]
    public async Task The_same_approvals_work_under_the_tr_TR_culture_and_the_four_eyes_check_is_culture_invariant()
    {
        // Oneren buyuk harfli ("EDITOR-A@EXAMPLE.TEST"): tr-TR ToLower'i "edıtor-a" verip dort goz denetimini atlatirdi.
        (SurahAlias ownAlias, Review own) = await SeedAliasReviewAsync(koken: XrefOrigin.Editor, oneren: EditorAEmail.ToUpperInvariant());
        (SurahAlias freeAlias, Review free) = await SeedAliasReviewAsync();
        using HttpClient editorA = await ClientAsync();

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage blocked = await DecideAsync(editorA, own.Id, Etag(await XminAsync(own.Id)), Approve());
            using HttpResponseMessage allowed = await DecideAsync(editorA, free.Id, Etag(await XminAsync(free.Id)), Approve());

            Assert.Equal(HttpStatusCode.Conflict, blocked.StatusCode);
            Assert.Equal(HttpStatusCode.OK, allowed.StatusCode);
        });

        Assert.Equal("aday", await AliasStatusAsync(ownAlias));
        Assert.Equal("onayli", await AliasStatusAsync(freeAlias));
        Assert.Equal(EditorAEmail, (await ReviewRowAsync(free.Id)).Inceleyen);
    }

    [Fact]
    public async Task A_text_decision_under_tr_TR_gives_the_same_stored_keys_as_the_invariant_normalizer()
    {
        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        const string text = "Deneme IŞIK İNCE paragrafi";
        Review review = await SeedUnitReviewAsync(unit, proposed: text);
        using HttpClient client = await ClientAsync();

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        });

        SearchKeys keys = SearchNormalizer.Keys(text);
        (string? narrow, string? wide, _, _, _) = await UnitSearchAsync(anchor);
        Assert.Equal(keys.TrNarrow, narrow);
        Assert.Equal(keys.TrWide, wide);
        Assert.Equal(ContentHash.Compute(text), (await UnitRowAsync(anchor)).Hash);
    }
}
