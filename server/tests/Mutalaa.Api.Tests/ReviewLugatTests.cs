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

/// <summary>
/// Lugat maddesi incelemesi (K-51 madde 9 ve 10): kuyruk (azalan siklik sirasi), ayrinti, Duzenle ve onayla, bos tanimla onay yok,
/// anlam basvurusunun hedefe yazilmamasi, If-Match ve toplu karar. Sentetik basliksozler (Docker'li).
/// </summary>
public class ReviewLugatTests(EditorialDatabase<ReviewLugatTests> fixture)
    : LexiconTestBase<ReviewLugatTests>(fixture), IClassFixture<EditorialDatabase<ReviewLugatTests>>
{
    private const string SourceSlug = "risale-kelime-frekans";

    private static string Proposal(int siklik) =>
        JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["anlam_basvuru"] = new[] { new Dictionary<string, object> { ["anlam"] = "deneme basvurusu", ["sayi"] = 3 } },
            ["siklik"] = siklik,
            ["kitaplar"] = 2,
        });

    private async Task EnsureSourceAsync()
    {
        await ResetLexiconAsync();
        await using DbSession session = Db.OpenSession();
        Source source = TestData.NewSource(SourceSlug);
        source.Tur = SourceKind.Sozluk;
        session.Context.Add(source);
        await session.Context.SaveChangesAsync(Ct);
    }

    private async Task<(LugatMadde Madde, Review Review)> SeedMaddeAsync(
        string basliksoz,
        string? kaynaklar = null,
        XrefStatus status = XrefStatus.Aday,
        string? tanim = null,
        string version = "1",
        int siklik = 10)
    {
        LugatMadde madde = new()
        {
            SourceId = SourceSlug,
            Basliksoz = basliksoz,
            BasliksozNorm = basliksoz,
            Duzey = 1,
            Status = status,
            TanimTr = tanim,
            Origin = LugatMaddeText.HatOrigin,
            Version = version,
            ContentHash = LugatMaddeText.ComputeHash(basliksoz, tanim),
            DataVersion = "test",
            Kaynaklar = kaynaklar ?? JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["siklik"] = siklik,
                ["kitaplar"] = new Dictionary<string, int> { ["deneme-kitap"] = siklik },
                ["sozluk_isabet"] = new[] { new Dictionary<string, object> { ["sozluk"] = "deneme-sozluk", ["bulundu"] = true, ["satir_no"] = 3 } },
            }),
        };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(madde);
            await session.Context.SaveChangesAsync(Ct);
        }

        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.LugatMadde,
            HedefAnahtar = SourceSlug + ":" + basliksoz,
            Alan = ReviewFields.TanimTr,
            Eylem = ReviewActions.Oner,
            Onerilen = Proposal(siklik),
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        return (madde, review);
    }

    private async Task<(string? Tanim, string ContentHash, string Version, string Origin, string Status, string Kaynaklar)> RowAsync(string basliksoz)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT tanim_tr, content_hash, version, origin, status::text, kaynaklar::text FROM icerik.lugat_madde WHERE source_id = @s AND basliksoz = @b",
            connection);
        command.Parameters.AddWithValue("s", SourceSlug);
        command.Parameters.AddWithValue("b", basliksoz);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return (reader.IsDBNull(0) ? null : reader.GetString(0), reader.GetString(1), reader.GetString(2), reader.GetString(3), reader.GetString(4), reader.GetString(5));
    }

    private static long[] Ids(JsonElement body) => [.. body.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("id").GetInt64())];

    private static async Task<long[]> PageThroughAsync(HttpClient client, string query, int limit)
    {
        List<long> all = [];
        string? cursor = null;
        for (int guard = 0; guard < 100; guard++)
        {
            string url = $"/api/v1/reviews?{query}&limit={limit.ToString(CultureInfo.InvariantCulture)}" + (cursor is null ? string.Empty : "&cursor=" + cursor);
            using HttpResponseMessage response = await client.GetAsync(url, Ct);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
            all.AddRange(Ids(body));
            JsonElement next = body.GetProperty("next_cursor");
            if (next.ValueKind == JsonValueKind.Null)
            {
                return [.. all];
            }

            cursor = next.GetString();
        }

        throw new InvalidOperationException("Sayfalama bitmedi.");
    }

    // ---- kuyruk ----

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(100)]
    public async Task The_queue_is_ordered_by_descending_frequency_then_review_id_and_pages_without_gaps(int limit)
    {
        await EnsureSourceAsync();
        (LugatMadde Madde, Review Review)[] seeded =
        [
            await SeedMaddeAsync("a-sozcuk", siklik: 5),
            await SeedMaddeAsync("b-sozcuk", siklik: 900),
            await SeedMaddeAsync("c-sozcuk", siklik: 5),
            await SeedMaddeAsync("d-sozcuk", siklik: 120),
            await SeedMaddeAsync("e:iki-nokta", siklik: 300),
        ];
        // Sayi olmayan, negatif, cok uzun ve eksik siklik 0 sayilir (cast hatasi listeyi 500 yapmaz); en sonda, review.id sirasiyla.
        (LugatMadde Madde, Review Review) text = await SeedMaddeAsync("f-sozcuk", kaynaklar: "{\"siklik\": \"cok\"}");
        (LugatMadde Madde, Review Review) missing = await SeedMaddeAsync("g-sozcuk", kaynaklar: "{}");
        (LugatMadde Madde, Review Review) huge = await SeedMaddeAsync("h-sozcuk", kaynaklar: "{\"siklik\": 99999999999999}");
        using HttpClient client = await ClientAsync();

        long[] paged = await PageThroughAsync(client, "hedef_tablo=lugat_madde&sira=siklik", limit);

        long[] expected =
        [
            seeded[1].Review.Id, // 900
            seeded[4].Review.Id, // 300
            seeded[3].Review.Id, // 120
            seeded[0].Review.Id, // 5 (daha kucuk review.id once)
            seeded[2].Review.Id, // 5
            text.Review.Id,
            missing.Review.Id,
            huge.Review.Id,
        ];
        Assert.Equal(expected, paged);
    }

    [Fact]
    public async Task A_review_whose_madde_row_is_missing_sorts_last_and_a_broken_key_does_not_fail_the_list()
    {
        await EnsureSourceAsync();
        (_, Review known) = await SeedMaddeAsync("a-sozcuk", siklik: 7);
        Review orphan = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.LugatMadde,
            HedefAnahtar = SourceSlug + ":yok-boyle-madde",
            Alan = ReviewFields.TanimTr,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        Review broken = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.LugatMadde,
            HedefAnahtar = "bozuk-anahtar",
            Alan = ReviewFields.TanimTr,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        long[] paged = await PageThroughAsync(client, "hedef_tablo=lugat_madde&sira=siklik", 50);

        Assert.Equal([known.Id, orphan.Id, broken.Id], paged);
    }

    [Fact]
    public async Task Sorting_by_frequency_is_only_valid_for_the_lugat_target_and_cursors_are_typed()
    {
        await EnsureSourceAsync();
        await SeedMaddeAsync("a-sozcuk");
        await SeedMaddeAsync("b-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage noTarget = await client.GetAsync("/api/v1/reviews?sira=siklik", Ct);
        using HttpResponseMessage otherTarget = await client.GetAsync("/api/v1/reviews?hedef_tablo=lemma&sira=siklik", Ct);
        using HttpResponseMessage waveOnLugat = await client.GetAsync("/api/v1/reviews?hedef_tablo=lugat_madde&sira=dalga", Ct);
        using HttpResponseMessage unknown = await client.GetAsync("/api/v1/reviews?hedef_tablo=lugat_madde&sira=bilinmeyen", Ct);
        using HttpResponseMessage garbage = await client.GetAsync("/api/v1/reviews?hedef_tablo=lugat_madde&sira=siklik&cursor=bozuk", Ct);

        Assert.Equal(HttpStatusCode.BadRequest, noTarget.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, otherTarget.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, waveOnLugat.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, unknown.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, garbage.StatusCode);

        // Olusturma imleci siklik sirasinda gecersizdir.
        using HttpResponseMessage first = await client.GetAsync("/api/v1/reviews?hedef_tablo=lugat_madde&limit=1", Ct);
        string creationCursor = (await ApiFactory.ReadJsonAsync(first, Ct)).GetProperty("next_cursor").GetString()!;
        using HttpResponseMessage mismatch = await client.GetAsync($"/api/v1/reviews?hedef_tablo=lugat_madde&sira=siklik&cursor={creationCursor}", Ct);
        Assert.Equal(HttpStatusCode.BadRequest, mismatch.StatusCode);
    }

    [Fact]
    public async Task The_queue_counts_include_the_lugat_queue()
    {
        await EnsureSourceAsync();
        await SeedMaddeAsync("a-sozcuk");
        await SeedMaddeAsync("b-sozcuk");
        using HttpClient client = await ClientAsync();

        JsonElement stats = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews/stats", Ct), Ct);

        JsonElement queue = stats.GetProperty("kuyruklar").EnumerateArray()
            .Single(q => q.GetProperty("hedef_tablo").GetString() == "lugat_madde");
        Assert.Equal("tanim_tr", queue.GetProperty("alan").GetString());
        Assert.Equal(2, queue.GetProperty("acik").GetInt32());
    }

    // ---- ayrinti ----

    [Fact]
    public async Task The_detail_shows_the_target_snapshot_and_the_reference_proposal_and_the_madde_is_not_verified_yet()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("a:b-sozcuk", siklik: 42);
        using HttpClient client = await ClientAsync();

        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);

        Assert.Equal("lugat_madde", detail.GetProperty("hedef_tablo").GetString());
        Assert.Equal(SourceSlug + ":a:b-sozcuk", detail.GetProperty("hedef_anahtar").GetString());
        Assert.Equal(42, detail.GetProperty("onerilen").GetProperty("siklik").GetInt32());
        Assert.Equal("deneme basvurusu", detail.GetProperty("onerilen").GetProperty("anlam_basvuru")[0].GetProperty("anlam").GetString());
        JsonElement target = detail.GetProperty("hedef");
        Assert.Equal("lugat_madde", target.GetProperty("tablo").GetString());
        Assert.Equal(SourceSlug, target.GetProperty("source").GetString());
        Assert.Equal("a:b-sozcuk", target.GetProperty("basliksoz").GetString());
        Assert.Equal("aday", target.GetProperty("status").GetString());
        Assert.Equal("hat", target.GetProperty("origin").GetString());
        Assert.Equal("1", target.GetProperty("version").GetString());
        Assert.False(target.TryGetProperty("tanim_tr", out _));
        Assert.False(detail.GetProperty("dogrulanmis").GetBoolean());
        Assert.False(detail.GetProperty("dogrulanmamis").GetBoolean()); // yz_modeli yok: K-25 rozeti yapay zeka taslagina cikar
        Assert.Equal(JsonValueKind.Null, detail.TryGetProperty("yz_modeli", out JsonElement yz) ? yz.ValueKind : JsonValueKind.Null);
    }

    // ---- karar ----

    [Fact]
    public async Task Editing_and_approving_writes_the_definition_hash_version_and_origin_and_leaves_the_references_alone()
    {
        await EnsureSourceAsync();
        (LugatMadde madde, Review review) = await SeedMaddeAsync("deneme-sozcuk", siklik: 77);
        string sourcesBefore = (await RowAsync("deneme-sozcuk")).Kaynaklar;
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = "  café deneme tanimi " }));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.Equal("onaylandi", body.GetProperty("durum").GetString());
        Assert.Equal("duzenle_onayla", body.GetProperty("eylem").GetString());
        Assert.Equal("onayli", body.GetProperty("hedef_durumu").GetString());

        (string? tanim, string hash, string version, string origin, string status, string sources) = await RowAsync("deneme-sozcuk");
        Assert.Equal("café deneme tanimi", tanim); // NFC ve kenar bosluklari kirpilmis
        Assert.Equal(LugatMaddeText.ComputeHash("deneme-sozcuk", "café deneme tanimi"), hash);
        Assert.Equal(ContentHash.Compute("deneme-sozcuk\ncafé deneme tanimi"), hash);
        Assert.Equal("2", version);
        Assert.Equal("editor", origin);
        Assert.Equal("onayli", status);
        // Basvuru (kaynaklar ve onerilen.anlam_basvuru) maddeye uygulanmaz (K-51 madde 10).
        Assert.Equal(sourcesBefore, sources);
        Assert.DoesNotContain("anlam_basvuru", sources, StringComparison.Ordinal);
        Assert.DoesNotContain("deneme basvurusu", tanim, StringComparison.Ordinal);
        Assert.True(madde.Id > 0);

        // Denetim izi: duzenlenen editor degerini tasir, onerilen hattin ozgun basvurusu olarak kalir.
        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);
        Assert.Equal("café deneme tanimi", detail.GetProperty("duzenlenen").GetProperty("tanim_tr").GetString());
        Assert.Equal(77, detail.GetProperty("onerilen").GetProperty("siklik").GetInt32());
        Assert.Equal("editor", detail.GetProperty("hedef").GetProperty("origin").GetString());
        Assert.Equal("café deneme tanimi", detail.GetProperty("hedef").GetProperty("tanim_tr").GetString());
        Assert.True(detail.GetProperty("dogrulanmis").GetBoolean());
    }

    [Fact]
    public async Task Approving_without_a_definition_is_a_422_even_when_a_reference_meaning_is_proposed_and_changes_nothing()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve());

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("inceleme-desteklenmiyor", await ProblemCodeAsync(response));
        (string? tanim, _, string version, _, string status, _) = await RowAsync("deneme-sozcuk");
        Assert.Null(tanim);
        Assert.Equal("1", version);
        Assert.Equal("aday", status);
        Assert.Equal("acik", (await ReviewRowAsync(review.Id)).Durum);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\t \n ")]
    public async Task A_blank_definition_is_a_400_and_changes_nothing(string value)
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = value }));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.Equal("aday", (await RowAsync("deneme-sozcuk")).Status);
    }

    [Fact]
    public async Task A_definition_over_2000_characters_is_a_400_and_exactly_2000_is_accepted()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage tooLong = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = new string('a', 2001) }));
        Assert.Equal(HttpStatusCode.BadRequest, tooLong.StatusCode);
        Assert.Equal("aday", (await RowAsync("deneme-sozcuk")).Status);

        using HttpResponseMessage exact = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = new string('a', 2000) }));
        Assert.Equal(HttpStatusCode.OK, exact.StatusCode);
    }

    [Fact]
    public async Task A_lugat_edit_with_another_field_or_with_NUL_is_a_400()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage metin = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { metin = "yeni" }));
        using HttpResponseMessage anlam = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { anlam_kisa = "yeni" }));
        using HttpResponseMessage empty = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { }));
        using HttpResponseMessage nul = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = "ab\0cd" }));

        Assert.Equal(HttpStatusCode.BadRequest, metin.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, anlam.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, empty.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, nul.StatusCode);
        Assert.True((await ApiFactory.ReadJsonAsync(nul, Ct)).GetProperty("errors").TryGetProperty("duzenlenen.tanim_tr", out _));
        Assert.Equal("aday", (await RowAsync("deneme-sozcuk")).Status);
    }

    [Fact]
    public async Task A_definition_on_another_target_is_rejected()
    {
        await EnsureSourceAsync();
        (_, Review alias) = await SeedAliasReviewAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, alias.Id, Etag(await XminAsync(alias.Id)), Approve(duzenlenen: new { tanim_tr = "yeni" }));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task A_madde_that_is_no_longer_a_candidate_is_a_409_even_with_a_definition()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk", status: XrefStatus.Onayli, tanim: "eski tanim");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = "yeni" }));

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("durum-gecisi-gecersiz", await ProblemCodeAsync(response));
        Assert.Equal("eski tanim", (await RowAsync("deneme-sozcuk")).Tanim);
    }

    [Fact]
    public async Task A_rejection_marks_the_madde_red_and_does_not_touch_the_definition_or_version_and_a_value_is_a_400()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage withValue = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), new { karar = "reddedildi", gerekce = "Deneme", duzenlenen = new { tanim_tr = "yeni" } });
        Assert.Equal(HttpStatusCode.BadRequest, withValue.StatusCode);

        using HttpResponseMessage plain = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id)), Reject());

        Assert.Equal(HttpStatusCode.OK, plain.StatusCode);
        (string? tanim, string hash, string version, string origin, string status, _) = await RowAsync("deneme-sozcuk");
        Assert.Equal("red", status);
        Assert.Null(tanim);
        Assert.Equal("1", version);
        Assert.Equal("hat", origin);
        Assert.Equal(LugatMaddeText.ComputeHash("deneme-sozcuk", null), hash);
    }

    [Fact]
    public async Task A_missing_madde_row_is_a_404_and_the_if_match_rules_of_k48_apply()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        Review orphan = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.LugatMadde,
            HedefAnahtar = SourceSlug + ":yok-boyle-madde",
            Alan = ReviewFields.TanimTr,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage missing = await DecideAsync(client, orphan.Id, Etag(await XminAsync(orphan.Id)), Approve(duzenlenen: new { tanim_tr = "yeni" }));
        using HttpResponseMessage noHeader = await DecideAsync(client, review.Id, null, Approve(duzenlenen: new { tanim_tr = "yeni" }));
        using HttpResponseMessage stale = await DecideAsync(client, review.Id, Etag(await XminAsync(review.Id) + 1), Approve(duzenlenen: new { tanim_tr = "yeni" }));

        Assert.Equal(HttpStatusCode.NotFound, missing.StatusCode);
        Assert.Equal(HttpStatusCode.PreconditionRequired, noHeader.StatusCode);
        Assert.Equal(HttpStatusCode.PreconditionFailed, stale.StatusCode);
        Assert.Equal("aday", (await RowAsync("deneme-sozcuk")).Status);
    }

    [Fact]
    public async Task The_bulk_endpoint_accepts_a_definition_with_the_same_rules_and_a_bad_item_rejects_the_whole_request()
    {
        await EnsureSourceAsync();
        (_, Review first) = await SeedMaddeAsync("a-sozcuk");
        (_, Review second) = await SeedMaddeAsync("b-sozcuk");
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage bad = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new
            {
                kararlar = new object[]
                {
                    new { id = first.Id, xmin = await XminAsync(first.Id), karar = "onaylandi", gerekce = "Deneme", duzenlenen = new { tanim_tr = "toplu tanim" } },
                    new { id = second.Id, xmin = await XminAsync(second.Id), karar = "onaylandi", gerekce = "Deneme" },
                },
            },
            Ct);
        Assert.Equal(HttpStatusCode.UnprocessableEntity, bad.StatusCode);
        Assert.Equal("aday", (await RowAsync("a-sozcuk")).Status);
        Assert.Equal("aday", (await RowAsync("b-sozcuk")).Status);

        using HttpResponseMessage ok = await client.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new
            {
                kararlar = new object[]
                {
                    new { id = first.Id, xmin = await XminAsync(first.Id), karar = "onaylandi", gerekce = "Deneme", duzenlenen = new { tanim_tr = "toplu tanim" } },
                    new { id = second.Id, xmin = await XminAsync(second.Id), karar = "reddedildi", gerekce = "Deneme" },
                },
            },
            Ct);
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        (string? tanim, _, string version, string origin, string status, _) = await RowAsync("a-sozcuk");
        Assert.Equal("toplu tanim", tanim);
        Assert.Equal("2", version);
        Assert.Equal("editor", origin);
        Assert.Equal("onayli", status);
        Assert.Equal("red", (await RowAsync("b-sozcuk")).Status);
    }

    [Fact]
    public async Task The_decision_endpoint_requires_an_authenticated_editor()
    {
        await EnsureSourceAsync();
        (_, Review review) = await SeedMaddeAsync("deneme-sozcuk");
        using HttpClient anonymous = Factory.CreateApiClient();

        using HttpResponseMessage response = await DecideAsync(anonymous, review.Id, Etag(await XminAsync(review.Id)), Approve(duzenlenen: new { tanim_tr = "yeni" }));

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("aday", (await RowAsync("deneme-sozcuk")).Status);
    }
}
