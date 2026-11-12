using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Duzenle ve onayla (lemma_gloss + anlam_kisa; K-50 madde 6) ve quran_word_fix alan eslesmesi (A17.4), HTTP uzerinden (Docker'li).
/// Anlam metinleri sentetiktir; content_hash ortak vektorle (shared/test-vectors/content-hash) karsilastirilir.
/// </summary>
public class ReviewGlossEditTests(EditorialDatabase<ReviewGlossEditTests> fixture)
    : LexiconTestBase<ReviewGlossEditTests>(fixture), IClassFixture<EditorialDatabase<ReviewGlossEditTests>>
{
    private async Task<(int LemmaId, Review Review)> SeedAsync(string anlam = "deneme anlami", string? proposal = null, string version = "1", XrefStatus status = XrefStatus.Aday)
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        Lemma lemma = await SeedLemmaAsync(source);
        await SeedGlossAsync(lemma.Id, anlam, status, version: version);
        Review review = await SeedGlossReviewAsync(lemma.Id, proposal ?? GlossProposal(anlam));
        return (lemma.Id, review);
    }

    /// <summary>Ortak content-hash vektorundan (yeni vektor eklenmez) metnin beklenen ozeti.</summary>
    private static string VectorHash(string id)
    {
        string path = RepoFiles.PathOf("shared/test-vectors/content-hash/hash.jsonl");
        foreach (string line in RepoFiles.ReadUtf8(path).Split('\n', StringSplitOptions.RemoveEmptyEntries))
        {
            using JsonDocument document = JsonDocument.Parse(line);
            if (string.Equals(document.RootElement.GetProperty("id").GetString(), id, StringComparison.Ordinal))
            {
                return document.RootElement.GetProperty("expected").GetProperty("sha256").GetString()!;
            }
        }

        throw new InvalidOperationException("Vektor yok: " + id);
    }

    [Fact]
    public async Task Editing_and_approving_a_gloss_renews_text_hash_version_and_origin_and_records_the_audit_trail()
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "İnce ılık ışık" }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("duzenle_onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());

        (string anlam, string hash, string version, string origin, string status) = await GlossRowAsync(lemmaId);
        Assert.Equal("İnce ılık ışık", anlam);
        Assert.Equal(VectorHash("ch-0002"), hash);
        Assert.Equal("2", version);
        Assert.Equal("editor", origin);
        Assert.Equal("onayli", status);

        // Denetim izi: duzenlenen editorun degerini tasir, onerilen hattin ozgun onerisi olarak kalir.
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.Equal("İnce ılık ışık", detail.GetProperty("duzenlenen").GetProperty("anlam_kisa").GetString());
        Assert.Equal("deneme anlami", detail.GetProperty("onerilen").GetProperty("anlam_kisa").GetString());
        Assert.Equal("editor", detail.GetProperty("hedef").GetProperty("origin").GetString());
        Assert.Equal("2", detail.GetProperty("hedef").GetProperty("version").GetString());
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task The_edited_value_is_stored_in_NFC_and_the_hash_follows_the_canonical_text()
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        // "cafe" + U+0301 (birlesik vurgu) ve kenar bosluklari: kanonik deger "caf" + U+00E9.
        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "  café " }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string anlam, string hash, _, _, _) = await GlossRowAsync(lemmaId);
        Assert.Equal("café", anlam);
        Assert.Equal(ContentHash.Compute("café"), hash);
    }

    [Fact]
    public async Task A_value_equal_to_the_proposal_keeps_the_origin_and_does_not_apply_the_distribution()
    {
        (int lemmaId, Review review) = await SeedAsync(anlam: "eski anlam", proposal: GlossProposal("Deneme paragrafi 1"));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "Deneme paragrafi 1" }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string anlam, string hash, string version, string origin, _) = await GlossRowAsync(lemmaId);
        Assert.Equal("Deneme paragrafi 1", anlam);
        Assert.Equal(VectorHash("ch-0001"), hash);
        Assert.Equal("2", version);
        Assert.Equal("kaynak:quranwbw-tr", origin);

        // dagilim ve baskin_pay hedefe uygulanmaz: lemma_gloss'ta yalniz anlam_kisa degisti.
        Assert.Equal("[]", await Db.ScalarAsync<string>("SELECT kuran_anlamlari::text FROM icerik.lemma_gloss WHERE lemma_id = @id", Ct, ("id", lemmaId)));
    }

    [Fact]
    public async Task A_plain_approval_is_a_status_approval_that_leaves_text_version_and_origin_alone()
    {
        (int lemmaId, Review review) = await SeedAsync();
        string hashBefore = (await GlossRowAsync(lemmaId)).ContentHash;
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onayla", body.GetProperty("eylem").GetString());
        (string anlam, string hash, string version, string origin, string status) = await GlossRowAsync(lemmaId);
        Assert.Equal("deneme anlami", anlam);
        Assert.Equal(hashBefore, hash);
        Assert.Equal("1", version);
        Assert.Equal("kaynak:quranwbw-tr", origin);
        Assert.Equal("onayli", status);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\t \n ")]
    public async Task An_empty_or_whitespace_only_value_is_a_400_and_changes_nothing(string value)
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = value }));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await GlossRowAsync(lemmaId)).Status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_value_over_200_characters_is_a_400_and_exactly_200_is_accepted()
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage tooLong = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = new string('a', 201) }));
        Assert.Equal(HttpStatusCode.BadRequest, tooLong.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(tooLong));
        Assert.Equal("aday", (await GlossRowAsync(lemmaId)).Status);

        using HttpResponseMessage exact = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = new string('a', 200) }));
        Assert.Equal(HttpStatusCode.OK, exact.StatusCode);
    }

    [Fact]
    public async Task A_gloss_edit_that_names_the_unit_field_metin_or_has_no_value_is_a_400()
    {
        (_, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage metin = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = "yeni" }));
        using HttpResponseMessage empty = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { }));

        Assert.Equal(HttpStatusCode.BadRequest, metin.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, empty.StatusCode);
    }

    [Fact]
    public async Task A_value_with_NUL_is_a_400_before_the_database_is_reached()
    {
        (_, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "ab\0cd" }));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.True(body.GetProperty("errors").TryGetProperty("duzenlenen.anlam_kisa", out _));
    }

    [Fact]
    public async Task A_gloss_that_is_no_longer_a_candidate_is_a_409_even_with_an_edit()
    {
        (int lemmaId, Review review) = await SeedAsync(status: XrefStatus.Onayli);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "yeni" }));

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        Assert.Equal("deneme anlami", (await GlossRowAsync(lemmaId)).AnlamKisa);
    }

    [Fact]
    public async Task A_rejection_with_a_value_is_a_400_and_a_rejection_without_one_marks_the_gloss_red()
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage withValue = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), new { karar = "reddedildi", gerekce = "Deneme", duzenlenen = new { anlam_kisa = "yeni" } });
        Assert.Equal(HttpStatusCode.BadRequest, withValue.StatusCode);

        using HttpResponseMessage plain = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());
        Assert.Equal(HttpStatusCode.OK, plain.StatusCode);
        Assert.Equal("red", (await GlossRowAsync(lemmaId)).Status);
        Assert.Equal("deneme anlami", (await GlossRowAsync(lemmaId)).AnlamKisa);
    }

    [Fact]
    public async Task An_editor_value_on_another_status_target_is_still_a_422()
    {
        (_, Review review) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = "yeni" }));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }

    [Fact]
    public async Task The_bulk_endpoint_accepts_a_gloss_edit_with_the_same_rules()
    {
        (int lemmaId, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        uint xmin = await XminAsync(review.Id);

        using HttpResponseMessage response = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = review.Id, xmin, karar = "onaylandi", gerekce = "Deneme", duzenlenen = new { anlam_kisa = "toplu anlam" } } } },
            Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        (string anlam, _, string version, string origin, string status) = await GlossRowAsync(lemmaId);
        Assert.Equal("toplu anlam", anlam);
        Assert.Equal("2", version);
        Assert.Equal("editor", origin);
        Assert.Equal("onayli", status);

        // Bozuk deger toplu istegi ya hep ya hic reddeder; kayit degismez.
        (int otherId, Review other) = await SeedAsync();
        using HttpResponseMessage bad = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = other.Id, xmin = await XminAsync(other.Id), karar = "onaylandi", gerekce = "Deneme", duzenlenen = new { anlam_kisa = "   " } } } },
            Ct);
        Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);
        Assert.Equal("aday", (await GlossRowAsync(otherId)).Status);
    }

    [Fact]
    public async Task A_decision_body_with_an_unknown_edit_field_is_still_a_400()
    {
        (_, Review review) = await SeedAsync();
        using HttpClient client = await ClientAsync();
        using StringContent content = new("""{"karar":"onaylandi","gerekce":"x","duzenlenen":{"anlam":"yeni"}}""", Encoding.UTF8, "application/json");
        using HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{review.Id}/decision") { Content = content };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(await XminAsync(review.Id)));

        using HttpResponseMessage response = await client.SendAsync(request, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    // ---- quran_word_fix alan eslesmesi (A17.4) ----

    private async Task<(Guid FixId, Review Review)> SeedFixAsync(string field, string reviewAlan)
    {
        await ResetLexiconAsync();
        QuranWordFix fix = new()
        {
            Anchor = Anchor("q:3:5:2"),
            Field = field,
            QacValue = "eski",
            NewValue = "yeni",
            Reason = "Deneme gerekcesi",
            Editor = "editor-a@example.test",
        };
        Review review = new()
        {
            HedefTablo = ReviewTargets.QuranWordFix,
            HedefAnahtar = Guid.Empty.ToString("D"),
            Alan = reviewAlan,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Editor,
            Oneren = "baska-editor",
        };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(fix);
            await session.Context.SaveChangesAsync(Ct);
        }

        review.HedefAnahtar = fix.Id.ToString("D");
        return (fix.Id, await SaveReviewAsync(review));
    }

    private async Task<string> FixStatusAsync(Guid id) =>
        await Db.ScalarAsync<string>("SELECT status::text FROM icerik.quran_word_fix WHERE id = @id", Ct, ("id", id));

    [Theory]
    [InlineData("root_id")]
    [InlineData("lemma_id")]
    [InlineData("pos")]
    [InlineData("features")]
    public async Task A_matching_field_lets_the_fix_be_approved_or_rejected(string field)
    {
        (Guid fixId, Review review) = await SeedFixAsync(field, field);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage approved = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        Assert.Equal("onayli", await FixStatusAsync(fixId));

        (Guid rejectedId, Review second) = await SeedFixAsync(field, field);
        using HttpResponseMessage rejected = await DecideAsync(client, second.Id, Etag(await XminAsync(second.Id)), Reject());
        Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
        Assert.Equal("red", await FixStatusAsync(rejectedId));
    }

    [Theory]
    [InlineData("pos", "root_id")]
    [InlineData("features", "lemma_id")]
    [InlineData("root_id", "pos")]
    public async Task A_field_mismatch_is_a_422_on_approve_and_reject_and_changes_nothing(string reviewAlan, string fixField)
    {
        (Guid fixId, Review review) = await SeedFixAsync(fixField, reviewAlan);
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage approve = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());
        using HttpResponseMessage reject = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, approve.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(approve));
        Assert.Equal(HttpStatusCode.UnprocessableEntity, reject.StatusCode);
        Assert.Equal("aday", await FixStatusAsync(fixId));
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task A_fix_review_with_an_unsupported_alan_is_refused_as_before()
    {
        (_, Review review) = await SeedFixAsync("pos", "status");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
    }
}
