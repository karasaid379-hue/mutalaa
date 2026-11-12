using System.Globalization;
using System.Net;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// GET /api/v1/reviews?sira=dalga (K-50 madde 7) ve genisleyen hedef anlik gorunumleri (A17.7). Sentetik veri (Docker'li).
/// </summary>
public class ReviewWaveListTests(EditorialDatabase<ReviewWaveListTests> fixture)
    : LexiconTestBase<ReviewWaveListTests>(fixture), IClassFixture<EditorialDatabase<ReviewWaveListTests>>
{
    private sealed record Seeded(string Source, List<(int LemmaId, long ReviewId, short? Dalga, int? Sira)> Items);

    /// <summary>
    /// Yirmi dort lemma_gloss incelemesi: dalga 0..3 ve karisik sira, ayni (dalga, sira) ciftinde iki lemma (kimlikle ayrilir),
    /// dalgasi olmayan uc kayit ve bozuk hedef_anahtar'li bir kayit (ham SQL). Olusturma sirasi bilerek dalga sirasindan farklidir.
    /// </summary>
    private async Task<Seeded> SeedWavesAsync(string hedefTablo = ReviewTargets.LemmaGloss)
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        List<(int LemmaId, long ReviewId, short? Dalga, int? Sira)> items = [];

        // (dalga, sira) olusturma sirasinin tersine yakin karisik dizilis; iki cift ayni (dalga, sira) tasir.
        (short? Dalga, int Sira)[] plan =
        [
            (3, 4), (0, 2), (1, 7), (2, 1), (0, 9), (3, 1), (1, 2), (2, 8), (0, 1), (1, 1), (2, 3), (3, 3),
            (1, 7), (2, 1), (0, 5), (0, 5), (1, 3), (2, 2), (3, 2), (0, 3), (null, 0), (null, 0), (null, 0), (0, 4),
        ];
        foreach ((short? dalga, int sira) in plan)
        {
            Lemma lemma = await SeedLemmaAsync(source);
            if (hedefTablo == ReviewTargets.LemmaGloss)
            {
                await SeedGlossAsync(lemma.Id);
            }

            if (dalga is { } w)
            {
                await SeedWaveAsync(lemma.Id, w, sira);
            }

            Review review = await SaveReviewAsync(new Review
            {
                HedefTablo = hedefTablo,
                HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
                Alan = hedefTablo == ReviewTargets.Lemma ? ReviewFields.Status : ReviewFields.AnlamKisa,
                Eylem = ReviewActions.Oner,
                Koken = XrefOrigin.Hat,
                Oneren = "hat",
            });
            items.Add((lemma.Id, review.Id, dalga, dalga is null ? null : sira));
        }

        // Bozuk anahtar: tamsayiya cevirmeye calisan bir birlesim bunun yuzunden listeyi 500 yapardi.
        Review broken = await SaveReviewAsync(new Review
        {
            HedefTablo = hedefTablo,
            HedefAnahtar = "bozuk-anahtar",
            Alan = hedefTablo == ReviewTargets.Lemma ? ReviewFields.Status : ReviewFields.AnlamKisa,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        items.Add((0, broken.Id, null, null));
        return new Seeded(source, items);
    }

    /// <summary>Beklenen sira: (dalga, sira, lemma_id, review.id) artan; dalgasizlar sonda (dalga 5, sira en buyuk, lemma 0, review.id).</summary>
    private static long[] ExpectedOrder(Seeded seeded) =>
    [
        .. seeded.Items
            .OrderBy(i => i.Dalga is null ? 5 : (int)i.Dalga)
            .ThenBy(i => i.Sira ?? int.MaxValue)
            .ThenBy(i => i.Dalga is null ? 0 : i.LemmaId)
            .ThenBy(i => i.ReviewId)
            .Select(i => i.ReviewId),
    ];

    private static long[] Ids(JsonElement body) => [.. body.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("id").GetInt64())];

    private async Task<long[]> PageThroughAsync(HttpClient client, string query, int limit)
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

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(5)]
    [InlineData(7)]
    [InlineData(100)]
    public async Task Paging_by_wave_follows_the_documented_order_without_repeats_or_gaps(int limit)
    {
        Seeded seeded = await SeedWavesAsync();
        using HttpClient client = await ClientAsync();

        long[] paged = await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=dalga", limit);

        Assert.Equal(seeded.Items.Count, paged.Length);
        Assert.Equal(paged.Length, paged.Distinct().Count());
        Assert.Equal(ExpectedOrder(seeded), paged);
    }

    [Fact]
    public async Task Reviews_without_a_wave_and_with_a_broken_key_come_last_and_the_list_does_not_fail()
    {
        Seeded seeded = await SeedWavesAsync();
        using HttpClient client = await ClientAsync();

        long[] paged = await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=dalga", 50);

        long[] withoutWave = [.. seeded.Items.Where(i => i.Dalga is null).Select(i => i.ReviewId).Order()];
        Assert.Equal(withoutWave, paged[^withoutWave.Length..]);
        Assert.Equal(4, withoutWave.Length);
    }

    [Fact]
    public async Task The_wave_order_also_works_for_lemma_status_reviews()
    {
        Seeded seeded = await SeedWavesAsync(ReviewTargets.Lemma);
        using HttpClient client = await ClientAsync();

        long[] paged = await PageThroughAsync(client, "hedef_tablo=lemma&sira=dalga", 5);

        Assert.Equal(ExpectedOrder(seeded), paged);
    }

    [Fact]
    public async Task The_default_and_olusturma_orders_stay_in_creation_order()
    {
        Seeded seeded = await SeedWavesAsync();
        using HttpClient client = await ClientAsync();
        long[] byCreation = [.. seeded.Items.Select(i => i.ReviewId).Order()];

        long[] withoutSira = await PageThroughAsync(client, "hedef_tablo=lemma_gloss", 7);
        long[] explicitSira = await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=olusturma", 7);
        long[] noTable = await PageThroughAsync(client, "sira=olusturma", 7);

        Assert.Equal(byCreation, withoutSira);
        Assert.Equal(byCreation, explicitSira);
        Assert.Equal(byCreation, noTable);
        Assert.NotEqual(ExpectedOrder(seeded), byCreation);
    }

    [Fact]
    public async Task The_other_filters_still_apply_in_wave_order()
    {
        Seeded seeded = await SeedWavesAsync();
        long decided = seeded.Items[1].ReviewId;
        await Db.ExecuteAsync("UPDATE icerik.review SET durum = 'onaylandi' WHERE id = @id", Ct, ("id", decided));
        using HttpClient client = await ClientAsync();

        long[] open = await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=dalga&durum=acik&alan=anlam_kisa&asama=ilk", 4);
        long[] closed = await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=dalga&durum=onaylandi", 4);

        Assert.DoesNotContain(decided, open);
        Assert.Equal(seeded.Items.Count - 1, open.Length);
        Assert.Equal([decided], closed);
        Assert.Empty(await PageThroughAsync(client, "hedef_tablo=lemma_gloss&sira=dalga&alan=status", 4));
    }

    [Theory]
    [InlineData("sira=dalga")]
    [InlineData("hedef_tablo=unit&sira=dalga")]
    [InlineData("hedef_tablo=xref&sira=dalga")]
    [InlineData("hedef_tablo=quran_word_fix&sira=dalga")]
    [InlineData("hedef_tablo=lemma_gloss&sira=bilinmeyen")]
    [InlineData("hedef_tablo=lemma_gloss&sira=Dalga")]
    [InlineData("hedef_tablo=lemma_gloss&sira=")]
    public async Task A_wave_order_on_another_table_or_an_unknown_order_is_a_400_problem(string query)
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        Assert.True(body.GetProperty("errors").TryGetProperty("sira", out _));
    }

    [Fact]
    public async Task Cursors_are_typed_a_creation_cursor_is_refused_in_wave_order_and_a_wave_cursor_in_creation_order()
    {
        await SeedWavesAsync();
        using HttpClient client = await ClientAsync();
        JsonElement creation = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?hedef_tablo=lemma_gloss&limit=2", Ct), Ct);
        JsonElement wave = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews?hedef_tablo=lemma_gloss&sira=dalga&limit=2", Ct), Ct);
        string creationCursor = creation.GetProperty("next_cursor").GetString()!;
        string waveCursor = wave.GetProperty("next_cursor").GetString()!;

        using HttpResponseMessage creationInWave = await client.GetAsync($"/api/v1/reviews?hedef_tablo=lemma_gloss&sira=dalga&cursor={creationCursor}", Ct);
        using HttpResponseMessage waveInCreation = await client.GetAsync($"/api/v1/reviews?hedef_tablo=lemma_gloss&cursor={waveCursor}", Ct);
        using HttpResponseMessage waveInExplicit = await client.GetAsync($"/api/v1/reviews?hedef_tablo=lemma_gloss&sira=olusturma&cursor={waveCursor}", Ct);
        using HttpResponseMessage garbage = await client.GetAsync("/api/v1/reviews?hedef_tablo=lemma_gloss&sira=dalga&cursor=!!!", Ct);

        foreach (HttpResponseMessage response in new[] { creationInWave, waveInCreation, waveInExplicit, garbage })
        {
            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        }
    }

    // ---- genisleyen anlik gorunumler ----

    [Fact]
    public async Task The_gloss_snapshot_carries_origin_quran_meanings_turkish_equivalent_etymological_flag_and_version()
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        Lemma lemma = await SeedLemmaAsync(source);
        await SeedGlossAsync(
            lemma.Id,
            version: "3",
            origin: "editor",
            turkceEsKelime: "deneme es kelimesi",
            etimolojik: true,
            kuranAnlamlari: """["birinci madde","ikinci madde"]""");
        Review review = await SeedGlossReviewAsync(lemma.Id, GlossProposal("deneme anlami"));
        using HttpClient client = await ClientAsync();

        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);

        JsonElement target = detail.GetProperty("hedef");
        Assert.Equal("lemma_gloss", target.GetProperty("tablo").GetString());
        Assert.Equal("editor", target.GetProperty("origin").GetString());
        Assert.Equal("3", target.GetProperty("version").GetString());
        Assert.Equal("deneme es kelimesi", target.GetProperty("turkce_es_kelime").GetString());
        Assert.True(target.GetProperty("yalnizca_etimolojik").GetBoolean());
        Assert.Equal(JsonValueKind.Array, target.GetProperty("kuran_anlamlari").ValueKind);
        Assert.Equal(["birinci madde", "ikinci madde"], target.GetProperty("kuran_anlamlari").EnumerateArray().Select(e => e.GetString()).ToArray());
        Assert.Equal("deneme anlami", target.GetProperty("anlam_kisa").GetString());
        Assert.Equal("aday", target.GetProperty("status").GetString());
    }

    [Fact]
    public async Task The_gloss_snapshot_omits_empty_optional_values_and_keeps_an_empty_meanings_array()
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        Lemma lemma = await SeedLemmaAsync(source);
        await SeedGlossAsync(lemma.Id);
        Review review = await SeedGlossReviewAsync(lemma.Id);
        using HttpClient client = await ClientAsync();

        JsonElement target = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        Assert.False(target.TryGetProperty("turkce_es_kelime", out _));
        Assert.False(target.GetProperty("yalnizca_etimolojik").GetBoolean());
        Assert.Equal(0, target.GetProperty("kuran_anlamlari").GetArrayLength());
        Assert.Equal("kaynak:quranwbw-tr", target.GetProperty("origin").GetString());
        Assert.Equal("1", target.GetProperty("version").GetString());
    }

    [Fact]
    public async Task The_lemma_snapshot_carries_root_id_occurrences_etymological_only_and_origin()
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(source);
        Lemma lemma = await SeedLemmaAsync(source, root.Id, occurrences: 42, status: XrefStatus.Aday, origin: "qac");
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement target = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        Assert.Equal("lemma", target.GetProperty("tablo").GetString());
        Assert.Equal(root.Id, target.GetProperty("root_id").GetInt32());
        Assert.Equal(42, target.GetProperty("occurrences").GetInt32());
        Assert.False(target.GetProperty("etymological_only").GetBoolean());
        Assert.Equal("qac", target.GetProperty("origin").GetString());
        Assert.Equal("ar", target.GetProperty("lang").GetString());
    }

    [Fact]
    public async Task A_rootless_lemma_snapshot_has_no_root_id()
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Lemma lemma = await SeedLemmaAsync(source, rootId: null, status: XrefStatus.Aday);
        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement target = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        Assert.False(target.TryGetProperty("root_id", out _));
    }

    [Fact]
    public async Task The_fix_snapshot_carries_reason_and_editor()
    {
        await ResetLexiconAsync();
        QuranWordFix fix = new()
        {
            Anchor = Anchor("q:3:5:2"),
            Field = "pos",
            QacValue = "eski",
            NewValue = "yeni",
            Reason = "Deneme gerekcesi",
            Editor = "editor-a@example.test",
        };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(fix);
            await session.Context.SaveChangesAsync(Ct);
        }

        Review review = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.QuranWordFix,
            HedefAnahtar = fix.Id.ToString("D"),
            Alan = ReviewFields.Pos,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Editor,
            Oneren = "editor-a@example.test",
        });
        using HttpClient client = await ClientAsync();

        JsonElement target = (await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct)).GetProperty("hedef");

        Assert.Equal("quran_word_fix", target.GetProperty("tablo").GetString());
        Assert.Equal("pos", target.GetProperty("field").GetString());
        Assert.Equal("eski", target.GetProperty("qac_value").GetString());
        Assert.Equal("yeni", target.GetProperty("new_value").GetString());
        Assert.Equal("Deneme gerekcesi", target.GetProperty("reason").GetString());
        Assert.Equal("editor-a@example.test", target.GetProperty("editor").GetString());
    }

    [Fact]
    public async Task The_unverified_flag_still_follows_yz_modeli_for_a_hazir_kaynak_candidate()
    {
        await ResetLexiconAsync();
        string source = await SeedSourceAsync(SourceKind.KelimeAnlami);
        Lemma lemma = await SeedLemmaAsync(source);
        await SeedGlossAsync(lemma.Id);
        Review review = await SeedGlossReviewAsync(lemma.Id, GlossProposal("deneme anlami"));
        using HttpClient client = await ClientAsync();

        JsonElement detail = await ApiFactory.ReadJsonAsync(await client.GetAsync($"/api/v1/reviews/{review.Id}", Ct), Ct);

        // Hazir kaynak adayinda yz_modeli bos: K-25 rozeti cikmaz; dogrulanmis hedef onayli olana dek false.
        Assert.False(detail.GetProperty("dogrulanmamis").GetBoolean());
        Assert.False(detail.GetProperty("dogrulanmis").GetBoolean());
    }
}
