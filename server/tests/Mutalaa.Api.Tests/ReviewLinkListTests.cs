using System.Globalization;
using System.Net;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Baglanti kuyrugu listesi (A18.4): sira=sinif (tutarsiz, toplu, gri, diger; sinif icinde confidence azalan), sinif ve onay_yolu suzgeci,
/// imlec, hata yollari, uzmanda suzgeci, istatistik ve SQL ile Domain sinif kurali uyumu (Docker'li).
/// </summary>
public class ReviewLinkListTests(EditorialDatabase<ReviewLinkListTests> fixture)
    : LinkTestBase<ReviewLinkListTests>(fixture), IClassFixture<EditorialDatabase<ReviewLinkListTests>>
{
    private sealed record Seeded(World World, Review Tutarsiz1, Review Tutarsiz2, Review Toplu, Review Gri1, Review Gri2, Review Diger1, Review Diger2);

    private async Task<Seeded> SeedMixAsync()
    {
        World world = await SeedWorldAsync();

        // Bilerek karisik sirada eklenir.
        Review diger1 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.9f, Evidence(world.Src)));
        Review gri1 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.6f, Evidence(world.Src)));
        Review tutarsiz2 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Atif, 0.2f, Evidence(world.Src)));
        Review toplu = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.97f, StrongEvidence(world.Src)));
        Review gri2 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Atif, 0.7f, Evidence(world.Src)));
        Review tutarsiz1 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.5f, Evidence(world.Src, ("consistent_quote", false))));
        Review diger2 = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.1f, Evidence(world.Src)));
        return new Seeded(world, tutarsiz1, tutarsiz2, toplu, gri1, gri2, diger1, diger2);
    }

    [Fact]
    public async Task The_class_order_is_tutarsiz_toplu_gri_diger_and_confidence_descends_inside_a_class()
    {
        Seeded s = await SeedMixAsync();
        using HttpClient client = await ClientAsync();

        JsonElement list = await ListAsync(client, "hedef_tablo=xref&sira=sinif");

        Assert.Equal(
            [s.Tutarsiz1.Id, s.Tutarsiz2.Id, s.Toplu.Id, s.Gri2.Id, s.Gri1.Id, s.Diger1.Id, s.Diger2.Id],
            Ids(list));
        Assert.Equal(
            ["tutarsiz", "tutarsiz", "toplu", "gri", "gri", "diger", "diger"],
            list.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("sinif").GetString()).ToArray());
        Assert.Equal(JsonValueKind.Null, list.GetProperty("next_cursor").ValueKind);
    }

    [Fact]
    public async Task Equal_confidence_inside_a_class_falls_back_to_the_review_id()
    {
        World world = await SeedWorldAsync();
        Review first = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.5f, Evidence(world.Src)));
        Review second = await SeedLinkReviewAsync(await SeedXrefAsync(XrefType.Iktibas, 0.5f, Evidence(world.Src)));
        using HttpClient client = await ClientAsync();

        Assert.Equal([first.Id, second.Id], Ids(await ListAsync(client, "hedef_tablo=xref&sira=sinif")));
    }

    [Fact]
    public async Task Cursor_paging_walks_the_same_order_without_gaps_or_repeats()
    {
        Seeded s = await SeedMixAsync();
        using HttpClient client = await ClientAsync();
        List<long> seen = [];
        string? cursor = null;

        for (int page = 0; page < 10; page++)
        {
            string query = "hedef_tablo=xref&sira=sinif&limit=2" + (cursor is null ? string.Empty : "&cursor=" + Uri.EscapeDataString(cursor));
            JsonElement list = await ListAsync(client, query);
            seen.AddRange(Ids(list));
            JsonElement next = list.GetProperty("next_cursor");
            if (next.ValueKind == JsonValueKind.Null)
            {
                break;
            }

            cursor = next.GetString();
        }

        Assert.Equal(
            [s.Tutarsiz1.Id, s.Tutarsiz2.Id, s.Toplu.Id, s.Gri2.Id, s.Gri1.Id, s.Diger1.Id, s.Diger2.Id],
            seen);
    }

    [Theory]
    [InlineData("tutarsiz", 2)]
    [InlineData("toplu", 1)]
    [InlineData("gri", 2)]
    [InlineData("diger", 2)]
    public async Task The_class_filter_returns_only_that_class(string sinif, int count)
    {
        await SeedMixAsync();
        using HttpClient client = await ClientAsync();

        JsonElement list = await ListAsync(client, "hedef_tablo=xref&sinif=" + sinif);

        Assert.Equal(count, list.GetProperty("items").GetArrayLength());
        Assert.All(list.GetProperty("items").EnumerateArray(), i => Assert.Equal(sinif, i.GetProperty("sinif").GetString()));
    }

    [Fact]
    public async Task The_class_filter_and_the_class_order_work_together_with_a_cursor()
    {
        Seeded s = await SeedMixAsync();
        using HttpClient client = await ClientAsync();

        JsonElement first = await ListAsync(client, "hedef_tablo=xref&sinif=gri&sira=sinif&limit=1");
        Assert.Equal([s.Gri2.Id], Ids(first));
        JsonElement second = await ListAsync(client, "hedef_tablo=xref&sinif=gri&sira=sinif&limit=1&cursor=" + Uri.EscapeDataString(first.GetProperty("next_cursor").GetString()!));

        Assert.Equal([s.Gri1.Id], Ids(second));
        Assert.Equal(JsonValueKind.Null, second.GetProperty("next_cursor").ValueKind);
    }

    [Theory]
    [InlineData("hedef_tablo=xref&sinif=yok", "sinif")]
    [InlineData("hedef_tablo=xref&sinif=Toplu", "sinif")]
    [InlineData("sinif=toplu", "sinif")]
    [InlineData("hedef_tablo=unit&sinif=toplu", "sinif")]
    [InlineData("sira=sinif", "sira")]
    [InlineData("hedef_tablo=lemma&sira=sinif", "sira")]
    [InlineData("hedef_tablo=xref&sira=sinif&cursor=bozuk", "cursor")]
    [InlineData("hedef_tablo=xref&sira=sinif&cursor=ZGFsZ2E6MTox", "cursor")]
    [InlineData("hedef_tablo=lemma&onay_yolu=yok", "onay_yolu")]
    [InlineData("onay_yolu=otomatik", "onay_yolu")]
    [InlineData("hedef_tablo=xref&onay_yolu=otomatik", "onay_yolu")]
    public async Task Invalid_class_order_cursor_and_approval_arguments_are_400_with_the_field_error(string query, string field)
    {
        await SeedMixAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", await ProblemCodeAsync(response));
        Assert.True((await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("errors").TryGetProperty(field, out _));
    }

    [Fact]
    public async Task A_wave_cursor_is_refused_in_class_order_and_a_class_cursor_in_creation_order()
    {
        await SeedMixAsync();
        using HttpClient client = await ClientAsync();
        JsonElement list = await ListAsync(client, "hedef_tablo=xref&sira=sinif&limit=1");
        string classCursor = list.GetProperty("next_cursor").GetString()!;

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?hedef_tablo=xref&cursor=" + Uri.EscapeDataString(classCursor), Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task A_review_whose_link_is_unreadable_sorts_after_every_class()
    {
        Seeded s = await SeedMixAsync();
        Review orphan = await SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = "bozuk-anahtar",
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });
        using HttpClient client = await ClientAsync();

        JsonElement list = await ListAsync(client, "hedef_tablo=xref&sira=sinif");

        Assert.Equal(orphan.Id, Ids(list)[^1]);
        Assert.Equal(s.Tutarsiz1.Id, Ids(list)[0]);
        Assert.False(list.GetProperty("items").EnumerateArray().Last().TryGetProperty("sinif", out _));
    }

    [Fact]
    public async Task The_expert_state_is_listed_separately_and_the_default_stays_open_only()
    {
        Seeded s = await SeedMixAsync();
        await Db.ExecuteAsync("UPDATE icerik.review SET durum = 'uzmanda' WHERE id = @id", Ct, ("id", s.Gri1.Id));
        using HttpClient client = await ClientAsync();

        JsonElement open = await ListAsync(client, "hedef_tablo=xref&limit=50");
        JsonElement expert = await ListAsync(client, "hedef_tablo=xref&durum=uzmanda");

        Assert.DoesNotContain(s.Gri1.Id, Ids(open));
        Assert.Equal([s.Gri1.Id], Ids(expert));
        Assert.Equal("uzmanda", expert.GetProperty("items")[0].GetProperty("durum").GetString());
    }

    [Fact]
    public async Task An_unknown_status_is_400_and_the_message_lists_uzmanda()
    {
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?durum=yok", Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        string message = (await ApiFactory.ReadJsonAsync(response, Ct)).GetProperty("errors").GetProperty("durum")[0].GetString()!;
        Assert.Contains("uzmanda", message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_stats_carry_the_class_counts_and_the_expert_count()
    {
        Seeded s = await SeedMixAsync();
        await Db.ExecuteAsync("UPDATE icerik.review SET durum = 'uzmanda' WHERE id = @id", Ct, ("id", s.Gri1.Id));
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews/stats", Ct);
        JsonElement stats = await ApiFactory.ReadJsonAsync(response, Ct);

        Assert.Equal(6, stats.GetProperty("toplam_acik").GetInt32());
        Assert.Equal(1, stats.GetProperty("toplam_uzmanda").GetInt32());
        JsonElement[] classes = [.. stats.GetProperty("baglanti_siniflari").EnumerateArray()];
        Assert.Equal(["tutarsiz", "toplu", "gri", "diger"], classes.Select(c => c.GetProperty("sinif").GetString()).ToArray());
        Assert.Equal([2, 1, 1, 2], classes.Select(c => c.GetProperty("acik").GetInt32()).ToArray());
    }

    [Fact]
    public async Task The_stats_list_all_four_classes_even_when_the_queue_is_empty()
    {
        await ResetLinksAsync();
        using HttpClient client = await ClientAsync();

        JsonElement stats = await ApiFactory.ReadJsonAsync(await client.GetAsync("/api/v1/reviews/stats", Ct), Ct);

        Assert.Equal([0, 0, 0, 0], stats.GetProperty("baglanti_siniflari").EnumerateArray().Select(c => c.GetProperty("acik").GetInt32()).ToArray());
        Assert.Equal(0, stats.GetProperty("toplam_uzmanda").GetInt32());
    }

    // --- Turkce lemma onay yolu suzgeci ---

    [Fact]
    public async Task The_approval_path_filter_selects_otomatik_editor_and_candidate_turkish_lemmas()
    {
        await ResetLinksAsync();
        string source = await SeedSourceAsync(SourceKind.Morfoloji);
        Root root = await SeedRootAsync(source);
        Lemma auto = await SeedTrLemmaAsync(source, root.Id, "otomatik");
        Lemma edit = await SeedTrLemmaAsync(source, root.Id, "editor");
        Lemma candidate = await SeedTrLemmaAsync(source, root.Id, null);
        Lemma arabic = await SeedLemmaAsync(source, root.Id);
        Review autoReview = await SeedMappingReviewAsync(auto);
        Review editReview = await SeedMappingReviewAsync(edit);
        Review candidateReview = await SeedMappingReviewAsync(candidate);
        Review arabicReview = await SeedMappingReviewAsync(arabic);
        using HttpClient client = await ClientAsync();

        Assert.Equal([autoReview.Id], Ids(await ListAsync(client, "hedef_tablo=lemma&onay_yolu=otomatik")));
        Assert.Equal([editReview.Id], Ids(await ListAsync(client, "hedef_tablo=lemma&onay_yolu=editor")));
        Assert.Equal([candidateReview.Id], Ids(await ListAsync(client, "hedef_tablo=lemma&onay_yolu=aday")));
        Assert.Equal(4, Ids(await ListAsync(client, "hedef_tablo=lemma")).Length);
        Assert.NotEqual(0, arabicReview.Id);
    }

    private async Task<Lemma> SeedTrLemmaAsync(string source, int rootId, string? onayYolu)
    {
        Lemma lemma = await SeedLemmaAsync(source, rootId, "tr-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6], status: XrefStatus.Aday, origin: "kaikki", lang: "tr");
        if (onayYolu is not null)
        {
            await Db.ExecuteAsync(
                "UPDATE icerik.lemma SET status = 'onayli', onay_yolu = @p, kanit = '{}'::jsonb WHERE id = @id",
                Ct,
                ("p", onayYolu),
                ("id", lemma.Id));
        }

        return lemma;
    }

    private Task<Review> SeedMappingReviewAsync(Lemma lemma) =>
        SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = lemma.Id.ToString(CultureInfo.InvariantCulture),
            Alan = "kok_eslemesi",
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
        });

    // --- SQL ile Domain uyumu ---

    [Fact]
    public async Task The_sql_class_rule_agrees_with_the_domain_classifier_on_a_boundary_matrix()
    {
        World world = await SeedWorldAsync();
        XrefType[] types = [XrefType.Atif, XrefType.Iktibas, XrefType.Ima, XrefType.Kok];
        float[] confidences = [0f, 0.1f, 0.3f, 0.31f, 0.39f, 0.4f, 0.5f, 0.79f, 0.8f, 0.94f, 0.95f, 1f];
        string[] evidences =
        [
            "{}",
            """{"matched_words": 7, "coverage": 1, "phrase_freq": 1}""",
            """{"matched_words": 7, "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""",
            """{"matched_words": 6, "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""",
            """{"matched_words": 9, "coverage": 0.99, "phrase_freq": 1, "consistent_quote": true}""",
            """{"matched_words": 9, "coverage": 1, "phrase_freq": 2, "consistent_quote": true}""",
            """{"matched_words": 9, "coverage": 1, "consistent_quote": true}""",
            """{"matched_words": 9.0, "coverage": 1.0, "phrase_freq": 1.0, "consistent_quote": false}""",
            """{"matched_words": "9", "coverage": 1, "phrase_freq": 1, "consistent_quote": true}""",
            """{"matched_words": 9, "coverage": true, "phrase_freq": 1}""",
            """{"matched_words": 12, "coverage": 1, "phrase_freq": 1, "consistent_quote": "evet"}""",
            """{"consistent_quote": null, "matched_words": 8, "coverage": 1, "phrase_freq": 1}""",
        ];

        List<Xref> xrefs = [];
        List<Review> reviews = [];
        int n = 0;
        foreach (XrefType type in types)
        {
            foreach (float confidence in confidences)
            {
                foreach (string evidence in evidences)
                {
                    n++;
                    xrefs.Add(new Xref
                    {
                        SrcAnchor = Mutalaa.Domain.Anchors.AnchorRef.Parse("rn:sozler:soz-10:p4"),
                        SrcSpan = new Mutalaa.Domain.Anchors.AnchorSpan(n, n + 1),
                        DstAnchor = Mutalaa.Domain.Anchors.AnchorRef.Parse(AyahAnchor),
                        Type = type,
                        Score = confidence,
                        Confidence = confidence,
                        Evidence = evidence,
                        Origin = XrefOrigin.Hat,
                        DataVersion = "test-1",
                    });
                }
            }
        }

        await using (DbSession session = Db.OpenSession())
        {
            session.Context.AddRange(xrefs);
            await session.Context.SaveChangesAsync(Ct);
            reviews = [.. xrefs.Select(x => new Review
            {
                HedefTablo = ReviewTargets.Xref,
                HedefAnahtar = x.Id.ToString("D", CultureInfo.InvariantCulture),
                XrefId = x.Id,
                Alan = ReviewFields.Status,
                Eylem = ReviewActions.Oner,
                Koken = XrefOrigin.Hat,
                Oneren = "hat",
            })];
            session.Context.AddRange(reviews);
            await session.Context.SaveChangesAsync(Ct);
        }

        Dictionary<long, string> expected = [];
        for (int i = 0; i < xrefs.Count; i++)
        {
            expected[reviews[i].Id] = LinkCandidateClassifier.Classify(xrefs[i].Type, xrefs[i].Confidence, xrefs[i].Evidence).ToLabel();
        }

        using HttpClient client = await ClientAsync();
        foreach (string sinif in new[] { "tutarsiz", "toplu", "gri", "diger" })
        {
            List<long> fromSql = [];
            string? cursor = null;
            do
            {
                JsonElement list = await ListAsync(client, "hedef_tablo=xref&limit=200&sinif=" + sinif + (cursor is null ? string.Empty : "&cursor=" + Uri.EscapeDataString(cursor)));
                fromSql.AddRange(Ids(list));
                cursor = list.GetProperty("next_cursor").GetString();
            }
            while (cursor is not null);

            long[] fromDomain = [.. expected.Where(e => e.Value == sinif).Select(e => e.Key).Order()];
            Assert.Equal(fromDomain, fromSql.Order().ToArray());
            Assert.NotEmpty(fromDomain);
        }

        // Her sinifin listedeki etiketi de ayni kuraldan gelir (liste ogesi Domain ile hesaplanir).
        JsonElement sample = await ListAsync(client, "hedef_tablo=xref&sira=sinif&limit=200");
        foreach (JsonElement item in sample.GetProperty("items").EnumerateArray())
        {
            Assert.Equal(expected[item.GetProperty("id").GetInt64()], item.GetProperty("sinif").GetString());
        }

        Assert.Equal(types.Length * confidences.Length * evidences.Length, xrefs.Count);
        Assert.NotNull(world);
    }
}
