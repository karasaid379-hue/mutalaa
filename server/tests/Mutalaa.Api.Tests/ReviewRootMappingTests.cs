using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Turkce lemma kok eslemesi incelemesi (A18.2, K-51 madde 9): onay, Duzenle ve onayla, ret, otomatik onaya itiraz, etimolojik isaret ve
/// lemma karti / hedef anlik goruntusu; HTTP uzerinden (Docker'li). Veri sentetiktir (kimlikler, "deneme" metinleri; sozluk ya da Kur'an metni yok).
/// </summary>
public class ReviewRootMappingTests(EditorialDatabase<ReviewRootMappingTests> fixture)
    : LexiconTestBase<ReviewRootMappingTests>(fixture), IClassFixture<EditorialDatabase<ReviewRootMappingTests>>
{
    private const string KokEslemesi = "kok_eslemesi";

    private static int _trCounter;

    private sealed record Seed(string Source, Root Root, Root OtherRoot, Lemma Arabic, Lemma ArabicOfOtherRoot);

    private async Task<Seed> SeedBaseAsync()
    {
        await ResetLexiconAsync();
        await Db.ExecuteAsync("TRUNCATE icerik.tr_root_index", Ct);
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(source, "kok-bir");
        Root other = await SeedRootAsync(source, "kok-iki");
        Lemma arabic = await SeedLemmaAsync(source, root.Id, "ar-lemma-bir");
        Lemma arabicOther = await SeedLemmaAsync(source, other.Id, "ar-lemma-iki");
        return new Seed(source, root, other, arabic, arabicOther);
    }

    private static string KanitFor(Root root) =>
        JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["politika"] = "k51-madde-9",
            ["politika_surumu"] = "1",
            ["yontem"] = "deneme",
            ["yontem_surumu"] = "1",
            ["kaynaklar"] = new[]
            {
                new Dictionary<string, string> { ["source_id"] = "deneme-a", ["surum"] = "1", ["madde"] = "m1", ["alan"] = "root", ["deger"] = "x" },
                new Dictionary<string, string> { ["source_id"] = "deneme-b", ["surum"] = "1", ["madde"] = "m2", ["alan"] = "etymon", ["deger"] = "y" },
            },
            ["qac"] = new Dictionary<string, object> { ["root_id"] = root.Id, ["letters"] = root.Letters, ["eslesme"] = "kok_harfleri" },
            ["karar"] = "onayli",
            ["neden"] = "yapisal_kanit",
        });

    private async Task<Lemma> SeedTrLemmaAsync(
        string source,
        XrefStatus status = XrefStatus.Aday,
        string? onayYolu = null,
        string? kanit = null,
        int? rootId = null,
        int? arLemmaId = null,
        bool etymological = false,
        string? origin = "kaikki",
        int? freq = null)
    {
        int id = NextLemmaId();
        string text = "tr-deneme-" + Interlocked.Increment(ref _trCounter).ToString(CultureInfo.InvariantCulture);
        Lemma lemma = new()
        {
            Id = id,
            Lang = "tr",
            Text = text,
            TextClean = text,
            RootId = rootId,
            ArLemmaId = arLemmaId,
            EtymologicalOnly = etymological,
            Origin = origin,
            Status = status,
            OnayYolu = onayYolu,
            Kanit = kanit,
            Freq = freq,
            SourceId = source,
            DataVersion = "test",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(lemma);
        await session.Context.SaveChangesAsync(Ct);
        return lemma;
    }

    private Task<Lemma> SeedAutoApprovedAsync(Seed seed, bool etymological = false) =>
        SeedTrLemmaAsync(seed.Source, XrefStatus.Onayli, LemmaApprovalPaths.Otomatik, KanitFor(seed.Root), seed.Root.Id, seed.Arabic.Id, etymological, freq: 7);

    private static string ProposalJson(int rootId, int? arId, bool etymological = false) =>
        JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            ["root_id"] = rootId,
            ["ar_lemma_id"] = arId,
            ["etymological_only"] = etymological,
            ["neden"] = "deneme neden",
            ["kanit_ozeti"] = new Dictionary<string, object> { ["kaynak_sayisi"] = 1 },
        });

    private Task<Review> SeedMappingReviewAsync(Lemma lemma, string? onerilen, XrefOrigin koken = XrefOrigin.Hat, string oneren = "hat") =>
        SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = KokEslemesi,
            Eylem = ReviewActions.Oner,
            Onerilen = onerilen,
            Koken = koken,
            Oneren = oneren,
        });

    private sealed record LemmaRow(string Status, string? OnayYolu, string? Origin, int? RootId, int? ArLemmaId, bool Etymological, string? Kanit);

    private async Task<LemmaRow> RowAsync(int id)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT status::text, onay_yolu, origin, root_id, ar_lemma_id, etymological_only, kanit::text FROM icerik.lemma WHERE id = @id",
            connection);
        command.Parameters.AddWithValue("id", id);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return new LemmaRow(
            reader.GetString(0),
            reader.IsDBNull(1) ? null : reader.GetString(1),
            reader.IsDBNull(2) ? null : reader.GetString(2),
            reader.IsDBNull(3) ? null : reader.GetInt32(3),
            reader.IsDBNull(4) ? null : reader.GetInt32(4),
            reader.GetBoolean(5),
            reader.IsDBNull(6) ? null : reader.GetString(6));
    }

    private async Task<HttpResponseMessage> DecideAsync(HttpClient client, Review review, object body) =>
        await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), body);

    private static Task<HttpResponseMessage> PostAsync(HttpClient client, string path, object body) => client.PostAsJsonAsync(path, body, Ct);

    private static async Task<string> CodeAsync(HttpResponseMessage response) => await ProblemCodeAsync(response);

    private Task<HttpClient> EditorA() => ClientAsync(EditorAEmail, EditorAPassword);

    private Task<HttpClient> EditorB() => ClientAsync(EditorBEmail, EditorBPassword);

    // Onay, Duzenle ve onayla, ret

    [Fact]
    public async Task Approving_the_hat_proposal_applies_it_as_an_editor_approval_and_keeps_the_hat_origin()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source, kanit: null);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await DecideAsync(client, review, Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("onayli", row.Status);
        Assert.Equal("editor", row.OnayYolu);
        Assert.Equal("kaikki", row.Origin);
        Assert.Equal(seed.Root.Id, row.RootId);
        Assert.Equal(seed.Arabic.Id, row.ArLemmaId);
        Assert.False(row.Etymological);
    }

    [Fact]
    public async Task Edit_and_approve_writes_the_edited_mapping_marks_the_origin_editor_and_records_the_value()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await DecideAsync(
            client,
            review,
            Approve(duzenlenen: new { root_id = seed.OtherRoot.Id, ar_lemma_id = seed.ArabicOfOtherRoot.Id, etymological_only = true }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("duzenle_onayla", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("eylem").GetString());
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("onayli", row.Status);
        Assert.Equal("editor", row.OnayYolu);
        Assert.Equal("editor", row.Origin);
        Assert.Equal(seed.OtherRoot.Id, row.RootId);
        Assert.Equal(seed.ArabicOfOtherRoot.Id, row.ArLemmaId);
        Assert.True(row.Etymological);

        // Denetim izi: duzenlenen editorun degeri, onerilen hattin ozgun onerisi.
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.Equal(seed.OtherRoot.Id, detail.GetProperty("duzenlenen").GetProperty("root_id").GetInt32());
        Assert.True(detail.GetProperty("duzenlenen").GetProperty("etymological_only").GetBoolean());
        Assert.Equal(seed.Root.Id, detail.GetProperty("onerilen").GetProperty("root_id").GetInt32());
        Assert.Equal("deneme neden", detail.GetProperty("onerilen").GetProperty("neden").GetString());
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());
        Assert.Equal("editor", detail.GetProperty("hedef").GetProperty("onay_yolu").GetString());
    }

    [Fact]
    public async Task An_edit_without_ar_lemma_id_clears_the_arabic_counterpart()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source, arLemmaId: seed.Arabic.Id, rootId: seed.Root.Id);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await DecideAsync(client, review, Approve(duzenlenen: new { root_id = seed.Root.Id, etymological_only = false }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal(seed.Root.Id, row.RootId);
        Assert.Null(row.ArLemmaId);
        Assert.Equal("editor", row.Origin);
    }

    [Fact]
    public async Task A_proposal_without_values_can_be_approved_only_with_an_edit()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, onerilen: null);
        using HttpClient client = await EditorA();

        using (HttpResponseMessage rejected = await DecideAsync(client, review, Approve()))
        {
            Assert.Equal(HttpStatusCode.BadRequest, rejected.StatusCode);
            Assert.Equal("dogrulama", await CodeAsync(rejected));
        }

        Assert.Equal("aday", (await RowAsync(lemma.Id)).Status);
        using HttpResponseMessage ok = await DecideAsync(client, review, Approve(duzenlenen: new { root_id = seed.Root.Id, etymological_only = false }));
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        Assert.Equal("editor", (await RowAsync(lemma.Id)).Origin);
    }

    [Fact]
    public async Task Values_are_validated_against_the_database_and_nothing_changes_on_failure()
    {
        Seed seed = await SeedBaseAsync();
        Lemma turkishPeer = await SeedTrLemmaAsync(seed.Source);
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        object[] bad =
        [
            new { root_id = 999999, etymological_only = false },
            new { root_id = seed.Root.Id, ar_lemma_id = 999999, etymological_only = false },
            new { root_id = seed.Root.Id, ar_lemma_id = turkishPeer.Id, etymological_only = false },
            new { root_id = seed.Root.Id, ar_lemma_id = seed.ArabicOfOtherRoot.Id, etymological_only = false },
            new { root_id = 0, etymological_only = false },
            new { root_id = seed.Root.Id },
            new { ar_lemma_id = seed.Arabic.Id, etymological_only = false },
        ];
        foreach (object edit in bad)
        {
            using HttpResponseMessage response = await DecideAsync(client, review, Approve(duzenlenen: edit));
            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("dogrulama", await CodeAsync(response));
        }

        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("aday", row.Status);
        Assert.Null(row.OnayYolu);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Fact]
    public async Task Edit_fields_of_other_targets_are_rejected_for_a_mapping_and_mapping_fields_for_other_targets()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using HttpResponseMessage withMetin = await DecideAsync(client, review, Approve(duzenlenen: new { metin = "Deneme paragrafi 9" }));
        Assert.Equal(HttpStatusCode.BadRequest, withMetin.StatusCode);
        using HttpResponseMessage mixed = await DecideAsync(client, review, Approve(duzenlenen: new { root_id = seed.Root.Id, etymological_only = false, anlam_kisa = "x" }));
        Assert.Equal(HttpStatusCode.BadRequest, mixed.StatusCode);

        Lemma arabicWithGloss = await SeedLemmaAsync(seed.Source, seed.Root.Id, "gloss-lemma");
        await SeedGlossAsync(arabicWithGloss.Id);
        Review glossReview = await SeedGlossReviewAsync(arabicWithGloss.Id, GlossProposal("deneme anlami"));
        using HttpResponseMessage onGloss = await DecideAsync(client, glossReview, Approve(duzenlenen: new { root_id = seed.Root.Id, etymological_only = false }));
        Assert.Equal(HttpStatusCode.BadRequest, onGloss.StatusCode);
    }

    [Fact]
    public async Task Rejecting_a_mapping_marks_the_lemma_red_and_takes_no_edited_value()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using (HttpResponseMessage withValue = await DecideAsync(client, review, new { karar = "reddedildi", gerekce = "g", duzenlenen = new { root_id = seed.Root.Id, etymological_only = false } }))
        {
            Assert.Equal(HttpStatusCode.BadRequest, withValue.StatusCode);
        }

        using HttpResponseMessage response = await DecideAsync(client, review, Reject());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("red", (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("hedef_durumu").GetString());
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("red", row.Status);
        Assert.Null(row.OnayYolu);
        Assert.Null(row.RootId);
    }

    [Fact]
    public async Task A_target_that_is_not_a_candidate_a_decided_review_and_an_own_proposal_are_409()
    {
        Seed seed = await SeedBaseAsync();
        Lemma approved = await SeedAutoApprovedAsync(seed);
        Review onApproved = await SeedMappingReviewAsync(approved, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        Lemma candidate = await SeedTrLemmaAsync(seed.Source);
        Review decided = await SeedMappingReviewAsync(candidate, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        Review own = await SeedMappingReviewAsync(await SeedTrLemmaAsync(seed.Source), ProposalJson(seed.Root.Id, null), XrefOrigin.Editor, EditorAEmail);
        using HttpClient client = await EditorA();

        using (HttpResponseMessage response = await DecideAsync(client, onApproved, Approve()))
        {
            Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(response));
        }

        using (HttpResponseMessage first = await DecideAsync(client, decided, Approve()))
        {
            Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        }

        using (HttpResponseMessage again = await DecideAsync(client, decided, Approve()))
        {
            Assert.Equal(HttpStatusCode.Conflict, again.StatusCode);
        }

        using (HttpResponseMessage ownApproval = await DecideAsync(client, own, Approve()))
        {
            Assert.Equal(HttpStatusCode.Conflict, ownApproval.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(ownApproval));
        }

        using HttpClient other = await EditorB();
        using HttpResponseMessage otherApproval = await DecideAsync(other, own, Approve());
        Assert.Equal(HttpStatusCode.OK, otherApproval.StatusCode);
    }

    [Fact]
    public async Task An_arabic_lemma_has_no_mapping_review_and_still_gets_422_for_both_decisions()
    {
        Seed seed = await SeedBaseAsync();
        Review review = await SeedMappingReviewAsync(seed.Arabic, ProposalJson(seed.Root.Id, null));
        using HttpClient client = await EditorA();

        foreach (object body in new[] { Approve(), Reject() })
        {
            using HttpResponseMessage response = await DecideAsync(client, review, body);
            Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
            Assert.Equal("inceleme-desteklenmiyor", await CodeAsync(response));
        }
    }

    [Fact]
    public async Task A_plain_status_approval_of_a_turkish_lemma_sets_the_editor_path_instead_of_failing_the_database_check()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source, rootId: seed.Root.Id);
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await DecideAsync(client, review, Approve());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("onayli", row.Status);
        Assert.Equal("editor", row.OnayYolu);
    }

    [Fact]
    public async Task The_bulk_decision_endpoint_applies_the_same_mapping_rules()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await PostAsync(
            client,
            "/api/v1/reviews/decisions",
            new
            {
                kararlar = new[]
                {
                    new
                    {
                        id = review.Id,
                        xmin = await XminAsync(review.Id),
                        karar = "onaylandi",
                        gerekce = "Deneme gerekcesi",
                        duzenlenen = (object)new { root_id = seed.Root.Id, ar_lemma_id = seed.Arabic.Id, etymological_only = true },
                    },
                },
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("onayli", row.Status);
        Assert.True(row.Etymological);
        Assert.Equal("editor", row.OnayYolu);
    }

    // Itiraz

    [Fact]
    public async Task An_objection_opens_an_editor_review_and_another_editors_approval_returns_the_lemma_to_candidate_keeping_the_evidence()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient opener = await EditorA();

        using HttpResponseMessage opened = await PostAsync(opener, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Deneme itiraz gerekcesi" });

        Assert.Equal(HttpStatusCode.Created, opened.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(opened, Ct);
        long reviewId = body.GetProperty("id").GetInt64();
        Assert.Equal("acik", body.GetProperty("durum").GetString());
        Assert.Equal("/api/v1/reviews/" + reviewId.ToString(CultureInfo.InvariantCulture), opened.Headers.Location?.OriginalString);

        JsonElement detail = await ApiFactory.ReadJsonAsync(await opener.GetAsync($"/api/v1/reviews/{reviewId}", Ct), Ct);
        Assert.Equal("lemma", detail.GetProperty("hedef_tablo").GetString());
        Assert.Equal(lemma.Id.ToString(CultureInfo.InvariantCulture), detail.GetProperty("hedef_anahtar").GetString());
        Assert.Equal(KokEslemesi, detail.GetProperty("alan").GetString());
        Assert.Equal("oner", detail.GetProperty("eylem").GetString());
        Assert.Equal("editor", detail.GetProperty("koken").GetString());
        Assert.Equal(EditorAEmail, detail.GetProperty("oneren").GetString());
        Assert.True(detail.GetProperty("onerilen").GetProperty("itiraz").GetBoolean());
        Assert.Equal("Deneme itiraz gerekcesi", detail.GetProperty("onerilen").GetProperty("gerekce").GetString());
        Assert.Equal("otomatik", detail.GetProperty("onceki").GetProperty("onay_yolu").GetString());

        // Ayni editor kendi itirazini onaylayamaz.
        using (HttpResponseMessage own = await DecideAsync(opener, reviewId, Etag(await XminAsync(reviewId)), Approve()))
        {
            Assert.Equal(HttpStatusCode.Conflict, own.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(own));
        }

        Assert.Equal("onayli", (await RowAsync(lemma.Id)).Status);

        using HttpClient other = await EditorB();
        string kanitBefore = (await RowAsync(lemma.Id)).Kanit!;
        using HttpResponseMessage approved = await DecideAsync(other, reviewId, Etag(await XminAsync(reviewId)), Approve("Itiraz haklı"));

        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        JsonElement result = await ApiFactory.ReadJsonAsync(approved, Ct);
        Assert.Equal("onaylandi", result.GetProperty("durum").GetString());
        Assert.Equal("aday", result.GetProperty("hedef_durumu").GetString());
        LemmaRow row = await RowAsync(lemma.Id);
        Assert.Equal("aday", row.Status);
        Assert.Null(row.OnayYolu);
        Assert.Equal(seed.Root.Id, row.RootId);
        Assert.Equal("kaikki", row.Origin);
        using (JsonDocument before = JsonDocument.Parse(kanitBefore))
        using (JsonDocument after = JsonDocument.Parse(row.Kanit!))
        {
            Assert.Equal(before.RootElement.GetRawText(), after.RootElement.GetRawText());
        }
    }

    [Fact]
    public async Task Rejecting_an_objection_leaves_the_lemma_untouched_and_a_new_objection_can_then_be_opened()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient a = await EditorA();
        using HttpClient b = await EditorB();
        LemmaRow before = await RowAsync(lemma.Id);

        long first = (await ApiFactory.ReadJsonAsync(await PostAsync(a, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Ilk itiraz" }), Ct)).GetProperty("id").GetInt64();
        using (HttpResponseMessage duplicate = await PostAsync(b, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Ikinci itiraz" }))
        {
            Assert.Equal(HttpStatusCode.Conflict, duplicate.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(duplicate));
        }

        using (HttpResponseMessage rejected = await DecideAsync(b, first, Etag(await XminAsync(first)), Reject("Itiraz yersiz")))
        {
            Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
            Assert.Equal("reddedildi", (await ApiFactory.ReadJsonAsync(rejected, Ct)).GetProperty("durum").GetString());
        }

        Assert.Equal(before, await RowAsync(lemma.Id));

        using HttpResponseMessage reopened = await PostAsync(b, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Yeni kanitla itiraz" });
        Assert.Equal(HttpStatusCode.Created, reopened.StatusCode);
    }

    [Fact]
    public async Task The_opener_can_withdraw_their_own_objection_by_rejecting_it()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient a = await EditorA();
        long id = (await ApiFactory.ReadJsonAsync(await PostAsync(a, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Geri cekilecek" }), Ct)).GetProperty("id").GetInt64();

        using HttpResponseMessage withdrawn = await DecideAsync(a, id, Etag(await XminAsync(id)), Reject("Vazgectim"));

        Assert.Equal(HttpStatusCode.OK, withdrawn.StatusCode);
        Assert.Equal("onayli", (await RowAsync(lemma.Id)).Status);
    }

    [Fact]
    public async Task An_objection_approval_carries_no_edited_value_and_is_409_when_the_lemma_is_no_longer_auto_approved()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient a = await EditorA();
        using HttpClient b = await EditorB();
        long id = (await ApiFactory.ReadJsonAsync(await PostAsync(a, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Itiraz" }), Ct)).GetProperty("id").GetInt64();

        using (HttpResponseMessage withValue = await DecideAsync(b, id, Etag(await XminAsync(id)), Approve(duzenlenen: new { root_id = seed.Root.Id, etymological_only = false })))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, withValue.StatusCode);
            Assert.Equal("inceleme-desteklenmiyor", await CodeAsync(withValue));
        }

        // Baska bir yolla (etimolojik isaret) lemma editor yoluna gecti: itiraz artik otomatik onaya degil.
        using (HttpResponseMessage marked = await PostAsync(b, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "Isaret" }))
        {
            Assert.Equal(HttpStatusCode.OK, marked.StatusCode);
        }

        using HttpResponseMessage stale = await DecideAsync(b, id, Etag(await XminAsync(id)), Approve());
        Assert.Equal(HttpStatusCode.Conflict, stale.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(stale));
        Assert.Equal("onayli", (await RowAsync(lemma.Id)).Status);
    }

    [Fact]
    public async Task An_objection_is_refused_for_every_lemma_that_is_not_auto_approved_turkish()
    {
        Seed seed = await SeedBaseAsync();
        Lemma editorApproved = await SeedTrLemmaAsync(seed.Source, XrefStatus.Onayli, LemmaApprovalPaths.Editor, rootId: seed.Root.Id);
        Lemma candidate = await SeedTrLemmaAsync(seed.Source);
        Lemma red = await SeedTrLemmaAsync(seed.Source, XrefStatus.Red);
        using HttpClient client = await EditorA();

        foreach (Lemma lemma in new[] { editorApproved, candidate, red })
        {
            using HttpResponseMessage response = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Itiraz" });
            Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(response));
        }

        using HttpResponseMessage arabic = await PostAsync(client, $"/api/v1/lemmas/{seed.Arabic.Id}/itiraz", new { gerekce = "Itiraz" });
        Assert.Equal(HttpStatusCode.UnprocessableEntity, arabic.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await CodeAsync(arabic));

        using HttpResponseMessage missing = await PostAsync(client, "/api/v1/lemmas/987654/itiraz", new { gerekce = "Itiraz" });
        Assert.Equal(HttpStatusCode.NotFound, missing.StatusCode);
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Theory]
    [InlineData("""{}""")]
    [InlineData("""{"gerekce": ""}""")]
    [InlineData("""{"gerekce": "   "}""")]
    [InlineData("""{"gerekce": "bilinmeyen alan", "x": 1}""")]
    public async Task An_objection_needs_a_non_blank_gerekce_and_no_unknown_fields(string json)
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await client.PostAsync(
            $"/api/v1/lemmas/{lemma.Id}/itiraz",
            new StringContent(json, System.Text.Encoding.UTF8, "application/json"),
            Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await CodeAsync(response));
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Fact]
    public async Task An_objection_gerekce_over_2000_code_points_or_with_a_NUL_is_400()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient client = await EditorA();

        using HttpResponseMessage tooLong = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = new string('a', 2001) });
        using HttpResponseMessage nul = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "bozuk\0metin" });
        using HttpResponseMessage exact = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = new string('a', 2000) });

        Assert.Equal(HttpStatusCode.BadRequest, tooLong.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, nul.StatusCode);
        Assert.Equal(HttpStatusCode.Created, exact.StatusCode);
    }

    [Fact]
    public async Task An_admin_can_object_and_decide_too_and_an_anonymous_caller_is_401()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        await Factory.AddUserAsync("admin-itiraz@example.test", "admin-itiraz-parolasi-1", Roles.Admin);
        using HttpClient admin = Factory.CreateApiClient();
        using (HttpResponseMessage login = await ApiFactory.LoginAsync(admin, "admin-itiraz@example.test", "admin-itiraz-parolasi-1", Ct))
        {
            Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        }

        using HttpClient anonymous = Factory.CreateApiClient();
        using (HttpResponseMessage denied = await PostAsync(anonymous, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "x" }))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, denied.StatusCode);
        }

        using (HttpResponseMessage deniedMark = await PostAsync(anonymous, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "x" }))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, deniedMark.StatusCode);
        }

        using HttpResponseMessage opened = await PostAsync(admin, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Yonetici itirazi" });
        Assert.Equal(HttpStatusCode.Created, opened.StatusCode);
        long id = (await ApiFactory.ReadJsonAsync(opened, Ct)).GetProperty("id").GetInt64();

        using HttpClient editor = await EditorA();
        using HttpResponseMessage approved = await DecideAsync(editor, id, Etag(await XminAsync(id)), Approve());
        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        Assert.Equal("aday", (await RowAsync(lemma.Id)).Status);
    }

    // Etimolojik isaret

    [Fact]
    public async Task Marking_an_auto_approved_lemma_changes_the_value_moves_it_to_the_editor_path_and_keeps_the_evidence()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        string kanitBefore = (await RowAsync(lemma.Id)).Kanit!;
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "Anlam kaymis" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.True(body.GetProperty("etymological_only").GetBoolean());
        Assert.Equal("editor", body.GetProperty("onay_yolu").GetString());
        Assert.Equal("onayli", body.GetProperty("status").GetString());
        long reviewId = body.GetProperty("review_id").GetInt64();

        LemmaRow row = await RowAsync(lemma.Id);
        Assert.True(row.Etymological);
        Assert.Equal("editor", row.OnayYolu);
        Assert.Equal("editor", row.Origin);
        Assert.Equal("onayli", row.Status);
        Assert.Equal(seed.Root.Id, row.RootId);
        using (JsonDocument before = JsonDocument.Parse(kanitBefore))
        using (JsonDocument after = JsonDocument.Parse(row.Kanit!))
        {
            Assert.Equal(before.RootElement.GetRawText(), after.RootElement.GetRawText());
        }

        // Denetim izi: kapanmis review satiri.
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{reviewId}", Ct), Ct);
        Assert.Equal("etimolojik_isaretle", detail.GetProperty("eylem").GetString());
        Assert.Equal("onaylandi", detail.GetProperty("durum").GetString());
        Assert.Equal("editor", detail.GetProperty("koken").GetString());
        Assert.Equal(EditorAEmail, detail.GetProperty("inceleyen").GetString());
        Assert.Equal("Anlam kaymis", detail.GetProperty("gerekce").GetString());
        Assert.False(detail.GetProperty("onceki").GetProperty("etymological_only").GetBoolean());
        Assert.True(detail.GetProperty("onerilen").GetProperty("etymological_only").GetBoolean());
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());

        // Kapanmis kayit kuyrukta gorunmez.
        JsonElement queue = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?hedef_tablo=lemma", Ct), Ct);
        Assert.Empty(queue.GetProperty("items").EnumerateArray());

        // Isareti geri almak ayni uctan yapilir; ikinci kez ayni deger 400.
        using HttpResponseMessage cleared = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = false, gerekce = "Geri alindi" });
        Assert.Equal(HttpStatusCode.OK, cleared.StatusCode);
        Assert.False((await RowAsync(lemma.Id)).Etymological);
        using HttpResponseMessage same = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = false, gerekce = "Ayni" });
        Assert.Equal(HttpStatusCode.BadRequest, same.StatusCode);
    }

    [Fact]
    public async Task Marking_an_auto_approved_lemma_closes_the_door_on_a_later_objection_because_it_is_now_editor_approved()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient client = await EditorA();
        (await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "Isaret" })).Dispose();

        using HttpResponseMessage objection = await PostAsync(client, $"/api/v1/lemmas/{lemma.Id}/itiraz", new { gerekce = "Itiraz" });

        Assert.Equal(HttpStatusCode.Conflict, objection.StatusCode);
    }

    [Fact]
    public async Task The_etymological_mark_has_exact_error_statuses()
    {
        Seed seed = await SeedBaseAsync();
        Lemma candidate = await SeedTrLemmaAsync(seed.Source, rootId: seed.Root.Id);
        Lemma rootless = await SeedTrLemmaAsync(seed.Source, XrefStatus.Onayli, LemmaApprovalPaths.Editor);
        Lemma ok = await SeedAutoApprovedAsync(seed);
        using HttpClient client = await EditorA();

        using (HttpResponseMessage onCandidate = await PostAsync(client, $"/api/v1/lemmas/{candidate.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "g" }))
        {
            Assert.Equal(HttpStatusCode.Conflict, onCandidate.StatusCode);
            Assert.Equal("durum-gecisi-gecersiz", await CodeAsync(onCandidate));
        }

        using (HttpResponseMessage onRootless = await PostAsync(client, $"/api/v1/lemmas/{rootless.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "g" }))
        {
            Assert.Equal(HttpStatusCode.Conflict, onRootless.StatusCode);
        }

        using (HttpResponseMessage arabic = await PostAsync(client, $"/api/v1/lemmas/{seed.Arabic.Id}/etimolojik-isaret", new { etymological_only = true, gerekce = "g" }))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, arabic.StatusCode);
            Assert.Equal("inceleme-desteklenmiyor", await CodeAsync(arabic));
        }

        using (HttpResponseMessage unchanged = await PostAsync(client, $"/api/v1/lemmas/{ok.Id}/etimolojik-isaret", new { etymological_only = false, gerekce = "g" }))
        {
            Assert.Equal(HttpStatusCode.BadRequest, unchanged.StatusCode);
            Assert.Equal("dogrulama", await CodeAsync(unchanged));
        }

        using (HttpResponseMessage missing = await PostAsync(client, "/api/v1/lemmas/987654/etimolojik-isaret", new { etymological_only = true, gerekce = "g" }))
        {
            Assert.Equal(HttpStatusCode.NotFound, missing.StatusCode);
        }

        foreach (string json in new[] { """{"gerekce": "g"}""", """{"etymological_only": true}""", """{"etymological_only": true, "gerekce": " "}""", """{"etymological_only": "true", "gerekce": "g"}""" })
        {
            using HttpResponseMessage bad = await client.PostAsync(
                $"/api/v1/lemmas/{ok.Id}/etimolojik-isaret",
                new StringContent(json, System.Text.Encoding.UTF8, "application/json"),
                Ct);
            Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);
        }

        // Hicbiri satir degistirmedi ya da denetim kaydi acmadi.
        Assert.Equal("otomatik", (await RowAsync(ok.Id)).OnayYolu);
        Assert.False((await RowAsync(ok.Id)).Etymological);
        Assert.Equal(0, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }

    [Fact]
    public async Task Other_http_methods_on_the_new_routes_are_not_routed_and_the_card_route_stays_get_only()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        using HttpClient client = await EditorA();

        using HttpResponseMessage get = await client.GetAsync($"/api/v1/lemmas/{lemma.Id}/itiraz", Ct);
        using HttpResponseMessage put = await client.PutAsJsonAsync($"/api/v1/lemmas/{lemma.Id}/etimolojik-isaret", new { }, Ct);
        using HttpResponseMessage post = await client.PostAsJsonAsync($"/api/v1/lemmas/{lemma.Id}", new { }, Ct);

        Assert.Contains(get.StatusCode, new[] { HttpStatusCode.MethodNotAllowed, HttpStatusCode.NotFound });
        Assert.Contains(put.StatusCode, new[] { HttpStatusCode.MethodNotAllowed, HttpStatusCode.NotFound });
        Assert.Equal(HttpStatusCode.MethodNotAllowed, post.StatusCode);
    }

    // Lemma karti ve hedef anlik goruntusu

    private async Task SeedTrIndexAsync(Seed seed, Lemma lemma, string anchor, string metin, int start, int end, bool staleHash = false)
    {
        Unit unit = await SeedUnitAsync(seed.Source, UnitKind.Meal, anchor, metin, TextStatus.Onayli);
        string hash = staleHash ? new string('0', 16) : unit.ContentHash[..16];
        await using DbSession session = Db.OpenSession();
        session.Context.Add(new TrRootIndex
        {
            Anchor = unit.Anchor,
            SpanStart = start,
            SpanEnd = end,
            RootId = seed.Root.Id,
            TrLemmaId = lemma.Id,
            UnitHash = hash,
            DataVersion = "test",
        });
        await session.Context.SaveChangesAsync(Ct);
    }

    [Fact]
    public async Task The_lemma_card_of_a_turkish_lemma_carries_the_approval_path_evidence_summary_root_letters_counterpart_frequency_and_three_examples()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        string longText = new string('a', 60) + " hedef " + new string('b', 60);
        await SeedTrIndexAsync(seed, lemma, "meal:elmalili:2:3", longText, 61, 66);
        await SeedTrIndexAsync(seed, lemma, "meal:elmalili:2:10", "Deneme kisa metin hedef sonu", 18, 23);
        await SeedTrIndexAsync(seed, lemma, "meal:elmalili:2:4", "hedef basta", 0, 5);
        await SeedTrIndexAsync(seed, lemma, "meal:elmalili:2:50", "dorduncu hedef", 9, 14);
        using HttpClient client = await EditorA();

        using HttpResponseMessage response = await client.GetAsync($"/api/v1/lemmas/{lemma.Id}", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        JsonElement info = body.GetProperty("lemma");
        Assert.Equal("tr", info.GetProperty("lang").GetString());
        Assert.Equal("otomatik", info.GetProperty("onay_yolu").GetString());
        Assert.Equal(seed.Arabic.Id, info.GetProperty("ar_lemma_id").GetInt32());
        Assert.Equal(7, info.GetProperty("freq").GetInt32());
        Assert.Equal(seed.Root.Letters, body.GetProperty("kok").GetProperty("letters").GetString());

        JsonElement tr = body.GetProperty("tr");
        Assert.Equal(seed.Root.Letters, tr.GetProperty("root_letters").GetString());
        Assert.Equal("ar-lemma-bir", tr.GetProperty("ar_lemma_text").GetString());
        JsonElement summary = tr.GetProperty("kanit_ozeti");
        Assert.Equal(2, summary.GetProperty("kaynak_sayisi").GetInt32());
        Assert.Equal("kok_harfleri", summary.GetProperty("qac_eslesme").GetString());
        Assert.Equal("onayli", summary.GetProperty("karar").GetString());
        Assert.Equal("yapisal_kanit", summary.GetProperty("neden").GetString());

        // En cok uc ornek, okuma sirasinda (2:3, 2:4, 2:10; "2:10" sayisal olarak 2:4'ten sonra gelir).
        JsonElement[] kwic = [.. tr.GetProperty("kwic").EnumerateArray()];
        Assert.Equal(3, kwic.Length);
        Assert.Equal("meal:elmalili:2:3", kwic[0].GetProperty("capa").GetString());
        Assert.Equal("meal:elmalili:2:4", kwic[1].GetProperty("capa").GetString());
        Assert.Equal("meal:elmalili:2:10", kwic[2].GetProperty("capa").GetString());

        // Pencere: kelimenin iki yaninda en cok 40 kod noktasi.
        Assert.Equal("hedef", kwic[0].GetProperty("kelime").GetString());
        Assert.Equal(40, kwic[0].GetProperty("sol").GetString()!.Length);
        Assert.Equal(40, kwic[0].GetProperty("sag").GetString()!.Length);
        Assert.Equal("hedef", kwic[1].GetProperty("kelime").GetString());
        Assert.Equal(string.Empty, kwic[1].GetProperty("sol").GetString());
        Assert.Equal(" basta", kwic[1].GetProperty("sag").GetString());
        Assert.Equal("Deneme kisa metin ", kwic[2].GetProperty("sol").GetString());
        Assert.Equal("hedef", kwic[2].GetProperty("kelime").GetString());
        Assert.Equal(" sonu", kwic[2].GetProperty("sag").GetString());
    }

    [Fact]
    public async Task A_stale_index_row_or_an_empty_index_gives_null_windows_or_an_empty_list()
    {
        Seed seed = await SeedBaseAsync();
        Lemma stale = await SeedAutoApprovedAsync(seed);
        await SeedTrIndexAsync(seed, stale, "meal:elmalili:2:3", "hedef basta", 0, 5, staleHash: true);
        Lemma empty = await SeedTrLemmaAsync(seed.Source, kanit: null);
        using HttpClient client = await EditorA();

        JsonElement[] staleKwic = [.. (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/lemmas/{stale.Id}", Ct), Ct)).GetProperty("tr").GetProperty("kwic").EnumerateArray()];
        JsonElement emptyBody = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/lemmas/{empty.Id}", Ct), Ct);

        JsonElement only = Assert.Single(staleKwic);
        Assert.Equal("meal:elmalili:2:3", only.GetProperty("capa").GetString());
        Assert.Equal(JsonValueKind.Null, only.GetProperty("sol").ValueKind);
        Assert.Equal(JsonValueKind.Null, only.GetProperty("kelime").ValueKind);
        Assert.Equal(JsonValueKind.Null, only.GetProperty("sag").ValueKind);
        Assert.Empty(emptyBody.GetProperty("tr").GetProperty("kwic").EnumerateArray());
        Assert.Equal(JsonValueKind.Null, emptyBody.GetProperty("tr").GetProperty("kanit_ozeti").ValueKind);
        Assert.Equal(JsonValueKind.Null, emptyBody.GetProperty("tr").GetProperty("root_letters").ValueKind);
        Assert.Equal(JsonValueKind.Null, emptyBody.GetProperty("lemma").GetProperty("onay_yolu").ValueKind);
    }

    [Fact]
    public async Task An_arabic_lemma_card_has_no_turkish_block()
    {
        Seed seed = await SeedBaseAsync();
        using HttpClient client = await EditorA();

        JsonElement body = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/lemmas/{seed.Arabic.Id}", Ct), Ct);

        Assert.Equal(JsonValueKind.Null, body.GetProperty("tr").ValueKind);
        Assert.Equal(JsonValueKind.Null, body.GetProperty("lemma").GetProperty("onay_yolu").ValueKind);
    }

    [Fact]
    public async Task The_review_detail_snapshot_of_a_turkish_lemma_carries_the_card_fields()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedAutoApprovedAsync(seed);
        await SeedTrIndexAsync(seed, lemma, "meal:elmalili:2:3", "Deneme hedef metni", 7, 12);
        Review review = await SeedMappingReviewAsync(lemma, LemmaMappingPayload.ToObjectionPayload("deneme"), XrefOrigin.Editor, EditorAEmail);
        using HttpClient client = await EditorB();

        JsonElement hedef = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        Assert.Equal("lemma", hedef.GetProperty("tablo").GetString());
        Assert.Equal("tr", hedef.GetProperty("lang").GetString());
        Assert.Equal("otomatik", hedef.GetProperty("onay_yolu").GetString());
        Assert.Equal(seed.Root.Letters, hedef.GetProperty("root_letters").GetString());
        Assert.Equal(seed.Arabic.Id, hedef.GetProperty("ar_lemma_id").GetInt32());
        Assert.Equal("ar-lemma-bir", hedef.GetProperty("ar_lemma_text").GetString());
        Assert.Equal(7, hedef.GetProperty("freq").GetInt32());
        Assert.Equal(2, hedef.GetProperty("kanit_ozeti").GetProperty("kaynak_sayisi").GetInt32());
        JsonElement example = Assert.Single(hedef.GetProperty("kwic").EnumerateArray());
        Assert.Equal("hedef", example.GetProperty("kelime").GetString());
        Assert.Equal("Deneme ", example.GetProperty("sol").GetString());
    }

    [Fact]
    public async Task The_review_detail_snapshot_of_an_arabic_lemma_gains_no_turkish_only_fields()
    {
        Seed seed = await SeedBaseAsync();
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = seed.Arabic.Id.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await EditorA();

        JsonElement hedef = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        foreach (string absent in new[] { "onay_yolu", "kanit_ozeti", "root_letters", "ar_lemma_id", "ar_lemma_text", "freq", "kwic" })
        {
            Assert.False(hedef.TryGetProperty(absent, out _), absent);
        }
    }

    [Fact]
    public async Task The_mapping_queue_is_listed_by_alan_and_counted_in_the_stats()
    {
        Seed seed = await SeedBaseAsync();
        Lemma lemma = await SeedTrLemmaAsync(seed.Source);
        Review review = await SeedMappingReviewAsync(lemma, ProposalJson(seed.Root.Id, seed.Arabic.Id));
        using HttpClient client = await EditorA();

        JsonElement list = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews?hedef_tablo=lemma&alan={KokEslemesi}", Ct), Ct);
        JsonElement stats = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews/stats", Ct), Ct);

        Assert.Equal(review.Id, Assert.Single(list.GetProperty("items").EnumerateArray()).GetProperty("id").GetInt64());
        JsonElement queue = Assert.Single(stats.GetProperty("kuyruklar").EnumerateArray(), q => q.GetProperty("alan").GetString() == KokEslemesi);
        Assert.Equal(1, queue.GetProperty("acik").GetInt32());
    }
}
