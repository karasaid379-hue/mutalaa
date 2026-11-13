using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Endpoints;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Api.Tests;

/// <summary>
/// POST /api/v1/risale/books/{kitap}/approve ile GET /risale/books ve /risale/books/{kitap} (K-51 madde 11; Docker'li): onkosullar (422),
/// If-Match kitap ozeti (428, 400, 412), yetki, tek islemde toplu onay, metnin degismemesi ve tek review satiri. Veriler sentetiktir
/// ("Deneme paragrafi N"); gercek Risale metni yoktur. Kitap katalogu testte degistirilir (dogrulanmis kitap), 87 kitabin JSON'u okunmaz.
/// </summary>
public class RisaleBookApprovalEndpointsTests(EditorialDatabase<RisaleBookApprovalEndpointsTests> fixture)
    : ApiTestBase<RisaleBookApprovalEndpointsTests>(fixture), IClassFixture<EditorialDatabase<RisaleBookApprovalEndpointsTests>>
{
    private const string Book = "deneme-kitap";
    private const string RelatedBook = "deneme-kitap-osmanlica"; // ayni onekle baslar: capa oneki "rn:deneme-kitap:" ona dokunmamali
    private const string UnverifiedBook = "deneme-dogrulanmamis";
    private const string SourceSlug = "test-risale-onay";
    private const string Reason = "Deneme onay gerekcesi";

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static readonly RisaleBook[] Catalog =
    [
        new(Book, "Deneme kitap", "tr", "ltr", 1, Verified: true),
        new(RelatedBook, "Deneme kitap Osmanlica", "ota", "rtl", 2, Verified: true),
        new(UnverifiedBook, "Deneme dogrulanmamis", "tr", "ltr", 3, Verified: false),
    ];

    private sealed record Seeded(string Anchor, string Metin, string Hash, TextStatus Durum);

    private ApiFactory CatalogFactory() =>
        CreateFactory(configureServices: services => services.AddSingleton(new RisaleBookCatalog(Catalog)));

    private async Task ResetAsync()
    {
        await Db.ExecuteAsync("TRUNCATE icerik.review, icerik.unit, icerik.pipeline_run, icerik.source CASCADE", Ct);
        await using DbSession session = Db.OpenSession();
        Source source = TestData.NewSource(SourceSlug);
        source.Tur = SourceKind.Risale;
        session.Context.Sources.Add(source);
        await session.Context.SaveChangesAsync(Ct);
    }

    /// <summary>Hat calismasi satiri (G-BUT kanitinin kaynagi: durum basarili ve manifest.qa_rapor dolu).</summary>
    private async Task<Guid> SeedRunAsync(string durum = "basarili", string manifest = """{"qa_rapor":"deneme-rapor-1"}""")
    {
        Guid runId = Guid.CreateVersion7();
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.pipeline_run (run_id, komut, git_commit, parmak_izi, baslangic, bitis, durum, manifest)
            VALUES (@id, 'export pg', 'abc1234', @fp, now(), now(), @durum, @manifest::jsonb)
            """,
            Ct,
            ("id", runId),
            ("fp", TestData.Hash('f')),
            ("durum", durum),
            ("manifest", manifest));
        return runId;
    }

    private async Task<List<Seeded>> SeedUnitsAsync(string slug, TextStatus[] statuses, Guid? runId, string metinPrefix = "Deneme paragrafi")
    {
        List<Seeded> seeded = [];
        await using DbSession session = Db.OpenSession();
        for (int i = 0; i < statuses.Length; i++)
        {
            string anchor = string.Create(CultureInfo.InvariantCulture, $"rn:{slug}:bolum-1:p{i + 1}");
            string metin = string.Create(CultureInfo.InvariantCulture, $"{metinPrefix} {slug} {i + 1}");
            string hash = ContentHash.Compute(metin);
            Unit unit = TestData.NewUnit(SourceSlug, anchor);
            unit.Metin = metin;
            unit.ContentHash = hash;
            unit.MetinDurumu = statuses[i];
            unit.Ord = i + 1;
            unit.RunId = runId;
            session.Context.Units.Add(unit);
            seeded.Add(new Seeded(anchor, metin, hash, statuses[i]));
        }

        await session.Context.SaveChangesAsync(Ct);
        return seeded;
    }

    private static string DigestOf(IEnumerable<Seeded> units) =>
        ContentDigest.Compute(units.Select(u => new ContentDigestEntry(u.Anchor, u.Hash)));

    private static HttpRequestMessage Approve(string slug, string? ifMatch, object? body)
    {
        HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/risale/books/{slug}/approve")
        {
            Content = body is null ? null : JsonContent.Create(body),
        };
        if (ifMatch is not null)
        {
            request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
        }

        return request;
    }

    private static object Body(bool? sample = true, string? gerekce = Reason) =>
        sample is null ? new { gerekce } : new { gerekce, ornek_okuma_yapildi = sample };

    private static string Etag(string digest) => "\"" + digest + "\"";

    private static async Task<JsonElement> ReadAsync(HttpResponseMessage response) => await ApiFactory.ReadJsonAsync(response, Ct);

    private static async Task<string> CodeAsync(HttpResponseMessage response, HttpStatusCode status)
    {
        Assert.Equal(status, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ReadAsync(response);
        string type = body.GetProperty("type").GetString()!;
        Assert.StartsWith("urn:mutalaa:problem:", type, StringComparison.Ordinal);
        string code = type["urn:mutalaa:problem:".Length..];
        Assert.Equal(code, body.GetProperty("kod").GetString());
        return code;
    }

    private async Task<string[]> StatusesAsync(string slug) =>
        [.. await Db.ColumnAsync(
            "SELECT metin_durumu::text FROM icerik.unit WHERE starts_with(anchor, @p) ORDER BY anchor COLLATE \"C\"",
            Ct,
            ("p", "rn:" + slug + ":"))];

    private Task<int> ReviewCountAsync() => Db.ScalarAsync<int>("SELECT count(*)::int FROM icerik.review", Ct);

    private async Task AssertNothingChangedAsync(string slug, int expectedDrafts)
    {
        string[] statuses = await StatusesAsync(slug);
        Assert.Equal(expectedDrafts, statuses.Count(s => s == "taslak"));
        Assert.Equal(0, await ReviewCountAsync());
    }

    // --- basari ---

    [Fact]
    public async Task An_admin_approves_only_the_draft_units_of_the_book_in_one_step_and_writes_one_review_row()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak, TextStatus.Onayli, TextStatus.Incelemede, TextStatus.Taslak], run);
        List<Seeded> related = await SeedUnitsAsync(RelatedBook, [TextStatus.Taslak, TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string digest = DigestOf(units);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(digest), Body()), Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(Etag(digest), response.Headers.ETag?.Tag);
        JsonElement result = await ReadAsync(response);
        Assert.Equal(Book, result.GetProperty("kitap").GetString());
        Assert.Equal(3, result.GetProperty("onaylanan_birim_sayisi").GetInt32());
        Assert.Equal(digest, result.GetProperty("ozet").GetString());
        long reviewId = result.GetProperty("review_id").GetInt64();

        // Yalniz taslaklar onayli oldu; onayli ve incelemede olana dokunulmadi; benzer slug'li kitap (onekle baslayan) taslak kaldi.
        Assert.Equal(["onayli", "onayli", "onayli", "incelemede", "onayli"], await StatusesAsync(Book));
        Assert.Equal(["taslak", "taslak"], await StatusesAsync(RelatedBook));

        // Metin, content_hash ve rev degismedi (BC-59 korumasi).
        foreach (Seeded unit in units)
        {
            await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
            await using Npgsql.NpgsqlCommand command = new("SELECT metin, content_hash, rev FROM icerik.unit WHERE anchor = @a", connection);
            command.Parameters.AddWithValue("a", unit.Anchor);
            await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
            Assert.True(await reader.ReadAsync(Ct));
            Assert.Equal(unit.Metin, reader.GetString(0));
            Assert.Equal(unit.Hash, reader.GetString(1));
            Assert.Equal(1, reader.GetInt32(2));
        }

        // Tek review satiri: hedef_tablo source, hedef_anahtar risale:{kitap}, onaylandi, denetim sutunlari.
        Assert.Equal(1, await ReviewCountAsync());
        await using (Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct))
        await using (Npgsql.NpgsqlCommand command = new(
            "SELECT id, hedef_tablo, hedef_anahtar, alan, eylem, durum::text, koken::text, oneren, inceleyen, gerekce, incelendi_at, onceki->>'ozet', onerilen->>'metin_durumu', ikinci_inceleyen FROM icerik.review",
            connection))
        await using (Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct))
        {
            Assert.True(await reader.ReadAsync(Ct));
            Assert.Equal(reviewId, reader.GetInt64(0));
            Assert.Equal("source", reader.GetString(1));
            Assert.Equal("risale:" + Book, reader.GetString(2));
            Assert.Equal("metin_durumu", reader.GetString(3));
            Assert.Equal("onayla", reader.GetString(4));
            Assert.Equal("onaylandi", reader.GetString(5));
            Assert.Equal("editor", reader.GetString(6));
            Assert.Equal(ReleaseTestKit.AdminEmail, reader.GetString(7));
            Assert.Equal(ReleaseTestKit.AdminEmail, reader.GetString(8));
            Assert.Equal(Reason, reader.GetString(9));
            Assert.False(reader.IsDBNull(10));
            Assert.Equal(digest, reader.GetString(11));
            Assert.Equal("onayli", reader.GetString(12));
            Assert.True(reader.IsDBNull(13)); // ikinci onay Risale'ye uygulanmaz
            Assert.False(await reader.ReadAsync(Ct));
        }

        // Onay ozeti degistirmez: ayrinti ayni ETag'i verir, taslak sayisi 0.
        using HttpResponseMessage detail = await admin.GetAsync($"/api/v1/risale/books/{Book}", Ct);
        JsonElement body = await ReadAsync(detail);
        Assert.Equal(digest, body.GetProperty("ozet").GetString());
        Assert.Equal(0, body.GetProperty("taslak_sayisi").GetInt64());
        Assert.Equal(4, body.GetProperty("onayli_sayisi").GetInt64());
        Assert.Equal(related.Count, (await StatusesAsync(RelatedBook)).Length);
    }

    [Fact]
    public async Task A_second_call_with_the_same_digest_finds_nothing_to_approve_and_writes_no_second_review_row()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string etag = Etag(DigestOf(units));

        using HttpResponseMessage first = await admin.SendAsync(Approve(Book, etag, Body()), Ct);
        using HttpResponseMessage second = await admin.SendAsync(Approve(Book, etag, Body()), Ct);

        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        Assert.Equal("onaylanacak-birim-yok", await CodeAsync(second, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(1, await ReviewCountAsync());
        Assert.Equal(["onayli", "onayli"], await StatusesAsync(Book));
    }

    [Fact]
    public async Task Two_concurrent_approvals_of_the_same_book_produce_exactly_one_success_and_one_review_row()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak, TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string etag = Etag(DigestOf(units));

        HttpResponseMessage[] responses = await Task.WhenAll(
            admin.SendAsync(Approve(Book, etag, Body()), Ct),
            admin.SendAsync(Approve(Book, etag, Body()), Ct));
        try
        {
            Assert.Single(responses, r => r.StatusCode == HttpStatusCode.OK);
            HttpResponseMessage loser = Assert.Single(responses, r => r.StatusCode != HttpStatusCode.OK);
            Assert.Equal("onaylanacak-birim-yok", await CodeAsync(loser, HttpStatusCode.UnprocessableEntity));
            Assert.Equal(1, await ReviewCountAsync());
        }
        finally
        {
            foreach (HttpResponseMessage response in responses)
            {
                response.Dispose();
            }
        }
    }

    [Fact]
    public async Task Units_that_are_no_longer_active_are_not_approved_and_do_not_enter_the_digest()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);
        await Db.ExecuteAsync(
            "UPDATE icerik.unit SET status = 'kullanim_disi', successors = '[\"rn:deneme-kitap:bolum-1:p1\"]'::jsonb WHERE anchor = @a",
            Ct,
            ("a", units[1].Anchor));
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units.Take(1))), Body()), Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(["onayli", "taslak"], await StatusesAsync(Book));
    }

    // --- onkosullar (422) ---

    [Fact]
    public async Task Units_without_a_run_or_with_a_failed_or_report_less_run_lack_the_gbut_evidence()
    {
        await ResetAsync();
        Guid failed = await SeedRunAsync(durum: "basarisiz");
        Guid noReport = await SeedRunAsync(manifest: """{"source_id":"x"}""");
        Guid emptyReport = await SeedRunAsync(manifest: """{"qa_rapor":""}""");
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        foreach (Guid? run in new Guid?[] { null, failed, noReport, emptyReport })
        {
            await Db.ExecuteAsync("TRUNCATE icerik.unit CASCADE", Ct);
            List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);

            using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), Body()), Ct);

            Assert.Equal("on-kosul-eksik", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
            Assert.Equal(["gbut-kaniti-yok"], Missing(await ReadAsync(response)));
            await AssertNothingChangedAsync(Book, 2);
        }
    }

    [Fact]
    public async Task One_unit_without_evidence_among_good_ones_blocks_the_whole_book()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);
        await Db.ExecuteAsync("UPDATE icerik.unit SET run_id = NULL WHERE anchor = @a", Ct, ("a", units[1].Anchor));
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), Body()), Ct);

        Assert.Equal("on-kosul-eksik", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(["gbut-kaniti-yok"], Missing(await ReadAsync(response)));
        await AssertNothingChangedAsync(Book, 2);
    }

    [Fact]
    public async Task An_unverified_slug_returns_422_on_kosul_eksik_with_slug_dogrulanmadi()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(UnverifiedBook, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(UnverifiedBook, Etag(DigestOf(units)), Body()), Ct);

        Assert.Equal("on-kosul-eksik", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(["slug-dogrulanmadi"], Missing(await ReadAsync(response)));
        await AssertNothingChangedAsync(UnverifiedBook, 1);
    }

    [Theory]
    [InlineData("absent")]
    [InlineData("false")]
    public async Task Without_the_sample_reading_declaration_the_approval_is_422_ornek_okuma_yok(string variant)
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        object body = variant == "absent" ? Body(sample: null) : Body(sample: false);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), body), Ct);

        Assert.Equal("on-kosul-eksik", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(["ornek-okuma-yok"], Missing(await ReadAsync(response)));
        await AssertNothingChangedAsync(Book, 1);
    }

    [Fact]
    public async Task Every_missing_prerequisite_is_reported_together_in_the_fixed_order()
    {
        await ResetAsync();
        List<Seeded> units = await SeedUnitsAsync(UnverifiedBook, [TextStatus.Taslak], runId: null);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(UnverifiedBook, Etag(DigestOf(units)), Body(sample: false)), Ct);

        Assert.Equal("on-kosul-eksik", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(["gbut-kaniti-yok", "slug-dogrulanmadi", "ornek-okuma-yok"], Missing(await ReadAsync(response)));
    }

    [Fact]
    public async Task A_book_with_no_draft_unit_returns_422_onaylanacak_birim_yok()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Onayli, TextStatus.Incelemede], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), Body()), Ct);

        Assert.Equal("onaylanacak-birim-yok", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
        Assert.Equal(0, await ReviewCountAsync());
    }

    [Fact]
    public async Task A_catalog_book_without_any_unit_returns_422_onaylanacak_birim_yok()
    {
        await ResetAsync();
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf([])), Body()), Ct);

        Assert.Equal("onaylanacak-birim-yok", await CodeAsync(response, HttpStatusCode.UnprocessableEntity));
    }

    // --- If-Match ---

    [Fact]
    public async Task A_missing_if_match_returns_428_and_a_malformed_one_returns_400()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string digest = DigestOf(units);

        using HttpResponseMessage missing = await admin.SendAsync(Approve(Book, null, Body()), Ct);
        Assert.Equal("surum-gerekli", await CodeAsync(missing, HttpStatusCode.PreconditionRequired));

        foreach (string bad in new[] { "*", "W/" + Etag(digest), digest, Etag(digest.ToUpperInvariant()), Etag(digest) + ", " + Etag(digest), "\"123\"" })
        {
            using HttpResponseMessage response = await admin.SendAsync(Approve(Book, bad, Body()), Ct);
            Assert.Equal("dogrulama", await CodeAsync(response, HttpStatusCode.BadRequest));
        }

        await AssertNothingChangedAsync(Book, 1);
    }

    [Fact]
    public async Task A_digest_that_does_not_match_returns_412_even_when_prerequisites_are_missing()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        await SeedUnitsAsync(UnverifiedBook, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(UnverifiedBook, Etag(TestData.Hash('0')), Body(sample: false)), Ct);

        Assert.Equal("surum-uyusmazligi", await CodeAsync(response, HttpStatusCode.PreconditionFailed));
        await AssertNothingChangedAsync(UnverifiedBook, 1);
    }

    [Fact]
    public async Task A_content_hash_change_after_the_client_read_the_digest_returns_412_and_approves_nothing()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string readDigest = DigestOf(units);

        // Istemci ozeti okuduktan sonra bir birimin metni (ve content_hash'i) degisti.
        await Db.ExecuteAsync("UPDATE icerik.unit SET content_hash = @h WHERE anchor = @a", Ct, ("h", TestData.Hash('9')), ("a", units[0].Anchor));

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(readDigest), Body()), Ct);

        Assert.Equal("surum-uyusmazligi", await CodeAsync(response, HttpStatusCode.PreconditionFailed));
        await AssertNothingChangedAsync(Book, 2);
    }

    [Fact]
    public async Task A_unit_added_after_the_client_read_the_digest_returns_412()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        string readDigest = DigestOf(units);
        await using (DbSession session = Db.OpenSession())
        {
            Unit extra = TestData.NewUnit(SourceSlug, "rn:" + Book + ":bolum-2:p1");
            extra.Metin = "Deneme paragrafi ek";
            extra.ContentHash = ContentHash.Compute(extra.Metin);
            extra.RunId = run;
            session.Context.Units.Add(extra);
            await session.Context.SaveChangesAsync(Ct);
        }

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(readDigest), Body()), Ct);

        Assert.Equal("surum-uyusmazligi", await CodeAsync(response, HttpStatusCode.PreconditionFailed));
        await AssertNothingChangedAsync(Book, 2);
    }

    // --- yetki, dogrulama, bulunamadi ---

    [Fact]
    public async Task An_editor_gets_403_and_an_anonymous_caller_401_and_nothing_changes()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        ApiFactory factory = CatalogFactory();
        using HttpClient editor = await ReleaseTestKit.EditorAsync(factory, Ct);
        using HttpClient anonymous = factory.CreateApiClient();
        string etag = Etag(DigestOf(units));

        using HttpResponseMessage forbidden = await editor.SendAsync(Approve(Book, etag, Body()), Ct);
        using HttpResponseMessage unauthorized = await anonymous.SendAsync(Approve(Book, etag, Body()), Ct);

        Assert.Equal("yetki-yok", await CodeAsync(forbidden, HttpStatusCode.Forbidden));
        Assert.Equal("oturum-acilamadi", await CodeAsync(unauthorized, HttpStatusCode.Unauthorized));
        await AssertNothingChangedAsync(Book, 1);
    }

    [Fact]
    public async Task An_unknown_book_returns_404_and_a_book_outside_the_catalog_cannot_be_approved()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync("deneme-katalog-disi", [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage approve = await admin.SendAsync(Approve("deneme-katalog-disi", Etag(DigestOf(units)), Body()), Ct);
        using HttpResponseMessage detail = await admin.GetAsync("/api/v1/risale/books/yok", Ct);

        Assert.Equal("bulunamadi", await CodeAsync(approve, HttpStatusCode.NotFound));
        Assert.Equal("bulunamadi", await CodeAsync(detail, HttpStatusCode.NotFound));
        await AssertNothingChangedAsync("deneme-katalog-disi", 1);
    }

    [Theory]
    [InlineData("""{"ornek_okuma_yapildi":true}""")]
    [InlineData("""{"gerekce":"   ","ornek_okuma_yapildi":true}""")]
    [InlineData("""{"gerekce":"Deneme","ornek_okuma_yapildi":true,"bilinmeyen":1}""")]
    [InlineData("""{"gerekce":"Deneme","ornek_okuma_yapildi":"evet"}""")]
    public async Task An_invalid_body_returns_400_dogrulama_and_changes_nothing(string json)
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/risale/books/{Book}/approve")
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
        request.Headers.TryAddWithoutValidation("If-Match", Etag(DigestOf(units)));

        using HttpResponseMessage response = await admin.SendAsync(request, Ct);

        Assert.Equal("dogrulama", await CodeAsync(response, HttpStatusCode.BadRequest));
        await AssertNothingChangedAsync(Book, 1);
    }

    [Fact]
    public async Task A_gerekce_over_2000_code_points_returns_400()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), Body(gerekce: new string('a', 2001))), Ct);

        Assert.Equal("dogrulama", await CodeAsync(response, HttpStatusCode.BadRequest));
        await AssertNothingChangedAsync(Book, 1);
    }

    // --- okuma uclari ---

    [Fact]
    public async Task The_list_is_in_catalog_order_with_counts_and_an_editor_can_read_it()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak, TextStatus.Onayli], run);
        await SeedUnitsAsync(RelatedBook, [TextStatus.Taslak], run);
        using HttpClient editor = await ReleaseTestKit.EditorAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await editor.GetAsync("/api/v1/risale/books", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement list = await ReadAsync(response);
        Assert.Equal([Book, RelatedBook, UnverifiedBook], list.EnumerateArray().Select(b => b.GetProperty("slug").GetString()).ToArray());
        JsonElement first = list[0];
        Assert.Equal("Deneme kitap", first.GetProperty("baslik").GetString());
        Assert.Equal("tr", first.GetProperty("dil").GetString());
        Assert.Equal("ltr", first.GetProperty("yon").GetString());
        Assert.True(first.GetProperty("dogrulandi").GetBoolean());
        Assert.Equal(3, first.GetProperty("birim_sayisi").GetInt64());
        Assert.Equal(2, first.GetProperty("taslak_sayisi").GetInt64());
        Assert.Equal(1, first.GetProperty("onayli_sayisi").GetInt64());
        Assert.Equal(1, list[1].GetProperty("birim_sayisi").GetInt64());
        Assert.Equal(0, list[2].GetProperty("birim_sayisi").GetInt64());
        Assert.False(list[2].GetProperty("dogrulandi").GetBoolean());
    }

    [Fact]
    public async Task The_detail_returns_the_digest_as_etag_and_body_and_reports_the_evidence()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak, TextStatus.Taslak], run);
        await Db.ExecuteAsync("UPDATE icerik.unit SET run_id = NULL WHERE anchor = @a", Ct, ("a", units[0].Anchor));
        using HttpClient editor = await ReleaseTestKit.EditorAsync(CatalogFactory(), Ct);

        using HttpResponseMessage response = await editor.GetAsync($"/api/v1/risale/books/{Book}", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement body = await ReadAsync(response);
        string digest = DigestOf(units);
        Assert.Equal(digest, body.GetProperty("ozet").GetString());
        Assert.Equal(Etag(digest), response.Headers.ETag?.Tag);
        Assert.False(body.GetProperty("gbut_kaniti").GetBoolean());
        Assert.Equal(1, body.GetProperty("kanitsiz_birim_sayisi").GetInt64());
        Assert.Equal(2, body.GetProperty("birim_sayisi").GetInt64());
    }

    [Fact]
    public async Task The_approval_row_appears_in_the_review_list_and_detail_without_breaking_them()
    {
        await ResetAsync();
        Guid run = await SeedRunAsync();
        List<Seeded> units = await SeedUnitsAsync(Book, [TextStatus.Taslak], run);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(CatalogFactory(), Ct);
        using HttpResponseMessage approved = await admin.SendAsync(Approve(Book, Etag(DigestOf(units)), Body()), Ct);
        Assert.Equal(HttpStatusCode.OK, approved.StatusCode);
        long id = (await ReadAsync(approved)).GetProperty("review_id").GetInt64();

        using HttpResponseMessage list = await admin.GetAsync("/api/v1/reviews?hedef_tablo=source&durum=onaylandi", Ct);
        using HttpResponseMessage detail = await admin.GetAsync($"/api/v1/reviews/{id}", Ct);

        Assert.Equal(HttpStatusCode.OK, list.StatusCode);
        JsonElement items = (await ReadAsync(list)).GetProperty("items");
        Assert.Equal(1, items.GetArrayLength());
        Assert.Equal("risale:" + Book, items[0].GetProperty("hedef_anahtar").GetString());
        Assert.False(items[0].GetProperty("dogrulanmamis").GetBoolean());
        Assert.Equal(HttpStatusCode.OK, detail.StatusCode);
        Assert.Equal("source", (await ReadAsync(detail)).GetProperty("hedef_tablo").GetString());

        // Karar uclari bu satiri desteklemez; zaten karar verilmis oldugu icin 409.
        using HttpRequestMessage decision = new(HttpMethod.Post, $"/api/v1/reviews/{id}/decision")
        {
            Content = JsonContent.Create(new { karar = "reddedildi", gerekce = "Deneme" }),
        };
        decision.Headers.TryAddWithoutValidation("If-Match", "\"" + (await Db.ScalarAsync<string>("SELECT xmin::text FROM icerik.review WHERE id = @id", Ct, ("id", id))) + "\"");
        using HttpResponseMessage decided = await admin.SendAsync(decision, Ct);
        Assert.Equal("inceleme-desteklenmiyor", await CodeAsync(decided, HttpStatusCode.UnprocessableEntity));
    }

    private static string[] Missing(JsonElement problem) =>
        [.. problem.GetProperty("eksikler").EnumerateArray().Select(e => e.GetString()!)];
}
