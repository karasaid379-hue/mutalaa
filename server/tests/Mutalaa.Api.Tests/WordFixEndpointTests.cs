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
/// Kelime duzeltmesi adayi (POST /api/v1/word-fixes; K-51 madde 2, A18.4) ve kararda <c>duzenlenen.new_value</c>. Kimlikler ve degerler
/// sentetiktir (kok, lemma, "deneme" metinleri; QAC ya da Kur'an verisi degil) (Docker'li).
/// </summary>
public class WordFixEndpointTests(EditorialDatabase<WordFixEndpointTests> fixture)
    : LinkTestBase<WordFixEndpointTests>(fixture), IClassFixture<EditorialDatabase<WordFixEndpointTests>>
{
    private const string WordAnchor = "q:2:255:3";

    private sealed record Setup(World World, Root Root, Root OtherRoot, Lemma Arabic, Lemma Turkish);

    private async Task<Setup> SeedAsync()
    {
        World world = await SeedWorldAsync();
        string lexicon = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(lexicon, "kok-bir");
        Root other = await SeedRootAsync(lexicon, "kok-iki");
        Lemma arabic = await SeedLemmaAsync(lexicon, root.Id, "ar-lemma");
        Lemma turkish = await SeedLemmaAsync(lexicon, null, "tr-lemma", status: XrefStatus.Aday, origin: "kaikki", lang: "tr");
        return new Setup(world, root, other, arabic, turkish);
    }

    private static Task<HttpResponseMessage> CreateAsync(HttpClient client, object body) => client.PostAsJsonAsync("/api/v1/word-fixes", body, Ct);

    private static object Body(string field, string value, string anchor = WordAnchor, string reason = "Deneme gerekcesi") =>
        new { anchor, field, new_value = value, reason };

    private sealed record FixRow(string Anchor, string Field, string? QacValue, string NewValue, string Reason, string Status, string? Editor);

    private async Task<FixRow?> FixAsync(Guid id)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT anchor, field, qac_value, new_value, reason, status::text, editor FROM icerik.quran_word_fix WHERE id = @id",
            connection);
        command.Parameters.AddWithValue("id", id);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        if (!await reader.ReadAsync(Ct))
        {
            return null;
        }

        return new FixRow(
            reader.GetString(0),
            reader.GetString(1),
            reader.IsDBNull(2) ? null : reader.GetString(2),
            reader.GetString(3),
            reader.GetString(4),
            reader.GetString(5),
            reader.IsDBNull(6) ? null : reader.GetString(6));
    }

    private async Task<long> FixCountAsync() => await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.quran_word_fix", Ct);

    // --- Aday acma ---

    [Fact]
    public async Task A_root_id_candidate_opens_an_aday_fix_and_an_editor_review()
    {
        Setup s = await SeedAsync();
        await Db.ExecuteAsync("UPDATE icerik.quran_word SET root_id = @r WHERE surah = 2 AND ayah = 255 AND word = 3", Ct, ("r", s.Root.Id));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await CreateAsync(client, Body("root_id", s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture)));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Guid id = body.GetProperty("id").GetGuid();
        long reviewId = body.GetProperty("review_id").GetInt64();
        Assert.Equal("aday", body.GetProperty("durum").GetString());
        Assert.Equal("/api/v1/reviews/" + reviewId.ToString(CultureInfo.InvariantCulture), response.Headers.Location?.ToString());

        FixRow fix = (await FixAsync(id))!;
        Assert.Equal(WordAnchor, fix.Anchor);
        Assert.Equal("root_id", fix.Field);
        Assert.Equal(s.Root.Id.ToString(CultureInfo.InvariantCulture), fix.QacValue);
        Assert.Equal(s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture), fix.NewValue);
        Assert.Equal("Deneme gerekcesi", fix.Reason);
        Assert.Equal("aday", fix.Status);
        Assert.Equal(EditorAEmail, fix.Editor);

        JsonElement review = await DetailAsync(client, reviewId);
        Assert.Equal("quran_word_fix", review.GetProperty("hedef_tablo").GetString());
        Assert.Equal(id.ToString("D"), review.GetProperty("hedef_anahtar").GetString());
        Assert.Equal("root_id", review.GetProperty("alan").GetString());
        Assert.Equal("oner", review.GetProperty("eylem").GetString());
        Assert.Equal("editor", review.GetProperty("koken").GetString());
        Assert.Equal(EditorAEmail, review.GetProperty("oneren").GetString());
        Assert.Equal("acik", review.GetProperty("durum").GetString());
        JsonElement proposal = review.GetProperty("onerilen");
        Assert.Equal(s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture), proposal.GetProperty("new_value").GetString());
        Assert.Equal(s.Root.Id.ToString(CultureInfo.InvariantCulture), proposal.GetProperty("qac_value").GetString());
        Assert.Equal("Deneme gerekcesi", proposal.GetProperty("reason").GetString());
        Assert.Equal("aday", review.GetProperty("hedef").GetProperty("status").GetString());
        Assert.Equal(EditorAEmail, review.GetProperty("hedef").GetProperty("editor").GetString());
    }

    [Fact]
    public async Task The_qac_value_is_null_when_the_word_has_no_value_and_pos_and_features_candidates_work()
    {
        await SeedAsync();
        await Db.ExecuteAsync("UPDATE icerik.quran_word SET pos = 'N' WHERE surah = 2 AND ayah = 255 AND word = 4", Ct);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage lemmaless = await CreateAsync(client, Body("pos", "V", "q:2:255:3"));
        using HttpResponseMessage withValue = await CreateAsync(client, Body("pos", "  PRON ", "q:2:255:4"));
        using HttpResponseMessage features = await CreateAsync(client, Body("features", "{\"zaman\": \"deneme\"}", "q:2:255:5"));

        Assert.Equal(HttpStatusCode.Created, lemmaless.StatusCode);
        Assert.Equal(HttpStatusCode.Created, withValue.StatusCode);
        Assert.Equal(HttpStatusCode.Created, features.StatusCode);
        Guid first = (await ApiFactory.ReadJsonAsync(lemmaless, Ct)).GetProperty("id").GetGuid();
        Guid second = (await ApiFactory.ReadJsonAsync(withValue, Ct)).GetProperty("id").GetGuid();
        Assert.Equal("N", (await FixAsync(first))!.QacValue);
        Assert.Equal("PRON", (await FixAsync(second))!.NewValue);
        Assert.Equal(3L, await FixCountAsync());
    }

    [Fact]
    public async Task A_lemma_id_candidate_needs_an_existing_arabic_lemma()
    {
        Setup s = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage ok = await CreateAsync(client, Body("lemma_id", s.Arabic.Id.ToString(CultureInfo.InvariantCulture)));
        using HttpResponseMessage turkish = await CreateAsync(client, Body("lemma_id", s.Turkish.Id.ToString(CultureInfo.InvariantCulture), "q:2:255:4"));
        using HttpResponseMessage missing = await CreateAsync(client, Body("lemma_id", "987654", "q:2:255:5"));

        Assert.Equal(HttpStatusCode.Created, ok.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, turkish.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, missing.StatusCode);
        Assert.Equal(1L, await FixCountAsync());
    }

    [Theory]
    [InlineData("root_id", "987654")] // kok yok
    [InlineData("root_id", "abc")]
    [InlineData("root_id", "007")]
    [InlineData("root_id", "")]
    [InlineData("pos", "")]
    [InlineData("pos", "   ")]
    [InlineData("pos", "123456789012345678901")]
    [InlineData("features", "[1]")]
    [InlineData("features", "metin")]
    [InlineData("features", "{bozuk")]
    [InlineData("kind", "N")] // bilinmeyen alan
    [InlineData("", "N")]
    public async Task An_invalid_field_or_value_is_400_and_writes_nothing(string field, string value)
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await CreateAsync(client, Body(field, value));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal(0L, await FixCountAsync());
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Theory]
    [InlineData("q:2:255")] // ayet
    [InlineData("q:2:255:3-5")] // aralik
    [InlineData("q:2:255-257")]
    [InlineData("meal:elmalili:2:255")]
    [InlineData("konu:tevhid")]
    [InlineData("Q:2:255:3")]
    [InlineData("deneme")]
    [InlineData("q:115:1:1")]
    public async Task A_non_word_or_invalid_anchor_is_400(string anchor)
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await CreateAsync(client, Body("pos", "N", anchor));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal(0L, await FixCountAsync());
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"new_value\": \"N\" }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"new_value\": \"N\", \"reason\": \"  \" }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"reason\": \"Deneme\" }")]
    [InlineData("{ \"field\": \"pos\", \"new_value\": \"N\", \"reason\": \"Deneme\" }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"new_value\": \"N\", \"reason\": \"Deneme\" }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"new_value\": \"N\", \"reason\": \"Deneme\", \"fazla\": 1 }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"new_value\": \"N\", \"reason\": \"a\\u0000b\" }")]
    [InlineData("{ \"anchor\": \"q:2:255:3\", \"field\": \"pos\", \"new_value\": \"\\ud800\", \"reason\": \"Deneme\" }")]
    public async Task A_malformed_body_is_400(string json)
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();
        using StringContent content = new(json, System.Text.Encoding.UTF8, "application/json");

        using HttpResponseMessage response = await client.PostAsync("/api/v1/word-fixes", content, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0L, await FixCountAsync());
    }

    [Fact]
    public async Task A_reason_over_two_thousand_characters_is_400()
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await CreateAsync(client, Body("pos", "N", reason: new string('a', 2001)));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.True((await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("errors").TryGetProperty("reason", out _));
    }

    [Fact]
    public async Task A_word_that_does_not_exist_is_404()
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await CreateAsync(client, Body("pos", "N", "q:2:255:11"));

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(response));
        Assert.Equal(0L, await FixCountAsync());
    }

    [Fact]
    public async Task A_second_candidate_for_the_same_word_and_field_is_409_but_another_field_or_word_is_fine()
    {
        Setup s = await SeedAsync();
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage first = await CreateAsync(client, Body("pos", "N"));

        using HttpResponseMessage again = await CreateAsync(client, Body("pos", "V"));
        using HttpResponseMessage otherField = await CreateAsync(client, Body("root_id", s.Root.Id.ToString(CultureInfo.InvariantCulture)));
        using HttpResponseMessage otherWord = await CreateAsync(client, Body("pos", "V", "q:2:255:4"));

        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, again.StatusCode);
        Assert.Equal("cakisma", await ProblemCodeAsync(again));
        Assert.Equal(HttpStatusCode.Created, otherField.StatusCode);
        Assert.Equal(HttpStatusCode.Created, otherWord.StatusCode);
        Assert.Equal(3L, await FixCountAsync());
        Assert.Equal(3L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Fact]
    public async Task A_rejected_fix_still_blocks_a_new_candidate_for_the_same_word_and_field()
    {
        await SeedAsync();
        using HttpClient client = await ClientAsync();
        using HttpResponseMessage first = await CreateAsync(client, Body("pos", "N"));
        await Db.ExecuteAsync("UPDATE icerik.quran_word_fix SET status = 'red'", Ct);

        using HttpResponseMessage again = await CreateAsync(client, Body("pos", "V"));

        Assert.Equal(HttpStatusCode.Conflict, again.StatusCode);
    }

    // --- Karar ---

    private async Task<(Guid Id, long ReviewId)> OpenAsync(HttpClient client, string field = "root_id", string? value = null, Setup? setup = null)
    {
        Setup s = setup ?? await SeedAsync();
        using HttpResponseMessage created = await CreateAsync(client, Body(field, value ?? s.Root.Id.ToString(CultureInfo.InvariantCulture)));
        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(created, Ct);
        return (body.GetProperty("id").GetGuid(), body.GetProperty("review_id").GetInt64());
    }

    private async Task<HttpResponseMessage> DecideReviewAsync(HttpClient client, long reviewId, object body) =>
        await DecideAsync(client, reviewId, Etag(await XminAsync(reviewId)), body);

    [Fact]
    public async Task The_proposer_cannot_approve_their_own_fix_another_editor_approves_it_plainly()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (Guid id, long reviewId) = await OpenAsync(a);

        using HttpResponseMessage own = await DecideReviewAsync(a, reviewId, Approve());
        Assert.Equal(HttpStatusCode.Conflict, own.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(own));
        Assert.Equal("aday", (await FixAsync(id))!.Status);

        using HttpResponseMessage other = await DecideReviewAsync(b, reviewId, Approve());
        Assert.Equal(HttpStatusCode.OK, other.StatusCode);
        Assert.Equal("onaylandi", (await ApiFactory.ReadJsonAsync(other, Ct)).GetProperty("durum").GetString());
        FixRow fix = (await FixAsync(id))!;
        Assert.Equal("onayli", fix.Status);
    }

    [Fact]
    public async Task Edit_and_approve_applies_the_edited_new_value_after_validating_it_by_the_field()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        Setup s = await SeedAsync();
        (Guid id, long reviewId) = await OpenAsync(a, setup: s);

        using HttpResponseMessage response = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture) }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("duzenle_onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        FixRow fix = (await FixAsync(id))!;
        Assert.Equal("onayli", fix.Status);
        Assert.Equal(s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture), fix.NewValue);

        // Denetim izi: onerilen ozgun oneri, duzenlenen editorun degeri.
        JsonElement detail = await DetailAsync(b, reviewId);
        Assert.Equal(s.Root.Id.ToString(CultureInfo.InvariantCulture), detail.GetProperty("onerilen").GetProperty("new_value").GetString());
        Assert.Equal(s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture), detail.GetProperty("duzenlenen").GetProperty("new_value").GetString());
        Assert.Equal(s.OtherRoot.Id.ToString(CultureInfo.InvariantCulture), detail.GetProperty("hedef").GetProperty("new_value").GetString());
    }

    [Theory]
    [InlineData("root_id", "987654")]
    [InlineData("root_id", "abc")]
    [InlineData("pos", "123456789012345678901")]
    [InlineData("pos", " ")]
    [InlineData("features", "[1]")]
    public async Task An_invalid_edited_value_is_400_and_the_fix_stays_a_candidate(string field, string value)
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (Guid id, long reviewId) = await OpenAsync(a, field, field == "root_id" ? null : field == "features" ? "{}" : "N");

        using HttpResponseMessage response = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = value }));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await FixAsync(id))!.Status);
        Assert.Equal("acik", (await ReviewRowAsync(reviewId)).Durum);
    }

    [Fact]
    public async Task An_edited_lemma_id_must_be_an_existing_arabic_lemma()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        Setup s = await SeedAsync();
        (Guid id, long reviewId) = await OpenAsync(a, "lemma_id", s.Arabic.Id.ToString(CultureInfo.InvariantCulture), s);

        using HttpResponseMessage turkish = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = s.Turkish.Id.ToString(CultureInfo.InvariantCulture) }));
        using HttpResponseMessage ok = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = s.Arabic.Id.ToString(CultureInfo.InvariantCulture) }));

        Assert.Equal(HttpStatusCode.BadRequest, turkish.StatusCode);
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        Assert.Equal("onayli", (await FixAsync(id))!.Status);
    }

    [Fact]
    public async Task An_edit_that_is_not_new_value_or_a_new_value_on_other_targets_is_400()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (_, long reviewId) = await OpenAsync(a, "pos", "N");

        using HttpResponseMessage metin = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { metin = "Deneme paragrafi 9" }));
        using HttpResponseMessage empty = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { }));
        (_, Review alias) = await SeedAliasReviewAsync();
        using HttpResponseMessage elsewhere = await DecideReviewAsync(b, alias.Id, Approve("Duzeltme", new { new_value = "N" }));

        Assert.Equal(HttpStatusCode.BadRequest, metin.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, empty.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, elsewhere.StatusCode);
    }

    [Fact]
    public async Task A_fix_can_be_rejected_by_another_editor_and_a_rejection_cannot_carry_a_value()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (Guid id, long reviewId) = await OpenAsync(a);

        using HttpResponseMessage withValue = await DecideReviewAsync(b, reviewId, new { karar = "reddedildi", gerekce = "Deneme", duzenlenen = new { new_value = "1" } });
        using HttpResponseMessage rejected = await DecideReviewAsync(b, reviewId, Reject());

        Assert.Equal(HttpStatusCode.BadRequest, withValue.StatusCode);
        Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
        Assert.Equal("red", (await FixAsync(id))!.Status);
    }

    [Fact]
    public async Task A_fix_already_decided_cannot_be_edited_again()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (Guid id, long reviewId) = await OpenAsync(a, "pos", "N");
        using HttpResponseMessage approved = await DecideReviewAsync(b, reviewId, Approve());

        using HttpResponseMessage again = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = "V" }));

        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, again.StatusCode);
        Assert.Equal("N", (await FixAsync(id))!.NewValue);
    }

    [Fact]
    public async Task The_review_field_must_still_match_the_fix_field_when_deciding()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        using HttpClient b = await ClientAsync(EditorBEmail, EditorBPassword);
        (_, long reviewId) = await OpenAsync(a, "pos", "N");
        await Db.ExecuteAsync("UPDATE icerik.review SET alan = 'features' WHERE id = @id", Ct, ("id", reviewId));

        using HttpResponseMessage response = await DecideReviewAsync(b, reviewId, Approve("Duzeltme", new { new_value = "{}" }));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task A_fix_candidate_can_be_sent_to_the_expert_who_then_decides_it_with_an_edit()
    {
        using HttpClient a = await ClientAsync(EditorAEmail, EditorAPassword);
        (Guid id, long reviewId) = await OpenAsync(a, "pos", "N");
        using HttpRequestMessage handoff = new(HttpMethod.Post, $"/api/v1/reviews/{reviewId}/uzmana-gonder") { Content = JsonContent.Create(new { gerekce = "Uzman gorusu" }) };
        handoff.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(reviewId)));
        using HttpResponseMessage sent = await a.SendAsync(handoff, Ct);
        using HttpClient uzman = await ReleaseTestKit.UzmanAsync(Factory, Ct);

        using HttpResponseMessage response = await DecideReviewAsync(uzman, reviewId, Approve("Uzman duzeltmesi", new { new_value = "PRON" }));

        Assert.Equal(HttpStatusCode.OK, sent.StatusCode);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("PRON", (await FixAsync(id))!.NewValue);
        Assert.Equal("onayli", (await FixAsync(id))!.Status);
    }
}
