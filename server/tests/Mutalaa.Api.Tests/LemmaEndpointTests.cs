using System.Net;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests;

/// <summary>
/// GET /api/v1/lemmas/{id}: salt okunur lemma karti (K-50, BC-56 A17 yarisi). Sentetik veri: ayet ve meal metinleri
/// "deneme" metnidir (gercek Kur'an ya da meal metni yok); UTF-16 ve kod noktasi ofsetlerini ayirmak icin vekil cift icerir (Docker'li).
/// </summary>
public class LemmaEndpointTests(EditorialDatabase<LemmaEndpointTests> fixture)
    : LexiconTestBase<LemmaEndpointTests>(fixture), IClassFixture<EditorialDatabase<LemmaEndpointTests>>
{
    private static readonly string Emoji = char.ConvertFromUtf32(0x1F600);

    private async Task<(string Morph, string Quran, string Meal)> SeedSourcesAsync()
    {
        await ResetLexiconAsync();
        string morph = await SeedSourceAsync(SourceKind.Morfoloji);
        string quran = await SeedSourceAsync(SourceKind.KuranMetni);
        string meal = await SeedSourceAsync(SourceKind.Meal);
        return (morph, quran, meal);
    }

    private async Task<JsonElement> GetAsync(HttpClient client, int id)
    {
        using HttpResponseMessage response = await client.GetAsync($"/api/v1/lemmas/{id}", Ct);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return await ApiFactory.ReadJsonAsync(response, Ct);
    }

    [Fact]
    public async Task The_card_carries_root_lemma_pos_distribution_frequency_wave_siblings_and_kwic()
    {
        (string morph, string quran, string meal) = await SeedSourcesAsync();
        Root root = await SeedRootAsync(morph, occurrences: 12, ayahCount: 5, kokAnlami: "deneme kok anlami");
        Lemma lemma = await SeedLemmaAsync(morph, root.Id, "deneme-lemma", occurrences: 4, origin: "qac");
        await SeedWaveAsync(lemma.Id, 2, 17);

        // Dort kelime, uc ayet; ayet 5'te iki kelime. Sozcuk turu: uc N, bir V.
        string ayah5 = "Sol" + Emoji + " kelime sag";
        await SeedWordAsync(morph, "q:3:5:2", 105, 5, 11, lemma.Id, root.Id, "N");
        await SeedWordAsync(morph, "q:3:5:3", 105, 12, 15, lemma.Id, root.Id, "N");
        await SeedWordAsync(morph, "q:3:6:1", 106, 0, 3, lemma.Id, root.Id, "V");
        await SeedWordAsync(morph, "q:3:7:4", 107, 4, 7, lemma.Id, root.Id, "N");
        await SeedUnitAsync(quran, UnitKind.Ayet, "q:3:5", ayah5);
        await SeedUnitAsync(quran, UnitKind.Ayet, "q:3:6", "abc def");
        await SeedUnitAsync(meal, UnitKind.Meal, "meal:elmalili:3:5", "Deneme meali 5", TextStatus.Incelemede);

        // Ayni kok: onayli anlamli, anlamsiz ve adayli kardesler.
        Lemma approved = await SeedLemmaAsync(morph, root.Id, "kardes-bir", occurrences: 9);
        await SeedGlossAsync(approved.Id, "onayli anlam", XrefStatus.Onayli);
        Lemma candidate = await SeedLemmaAsync(morph, root.Id, "kardes-iki", occurrences: 8);
        await SeedGlossAsync(candidate.Id, "aday anlam", XrefStatus.Aday);
        await SeedLemmaAsync(morph, root.Id, "kardes-uc", occurrences: 7);
        Lemma other = await SeedLemmaAsync(morph, (await SeedRootAsync(morph)).Id, "baska-kok", occurrences: 6);
        await SeedGlossAsync(other.Id, "baska kok anlami", XrefStatus.Onayli);
        await SeedGlossAsync(lemma.Id, "kendi anlami", XrefStatus.Onayli);
        using HttpClient client = await ClientAsync();

        JsonElement body = await GetAsync(client, lemma.Id);

        JsonElement info = body.GetProperty("lemma");
        Assert.Equal(lemma.Id, info.GetProperty("id").GetInt32());
        Assert.Equal("deneme-lemma", info.GetProperty("text").GetString());
        Assert.Equal("ar", info.GetProperty("lang").GetString());
        Assert.Equal("onayli", info.GetProperty("status").GetString());
        Assert.Equal("qac", info.GetProperty("origin").GetString());
        Assert.Equal(4, info.GetProperty("occurrences").GetInt32());
        Assert.Equal(root.Id, info.GetProperty("root_id").GetInt32());

        JsonElement kok = body.GetProperty("kok");
        Assert.Equal(root.Id, kok.GetProperty("id").GetInt32());
        Assert.Equal(root.Letters, kok.GetProperty("letters").GetString());
        Assert.Equal(root.LettersBw, kok.GetProperty("letters_bw").GetString());
        Assert.Equal(12, kok.GetProperty("occurrences").GetInt32());
        Assert.Equal(5, kok.GetProperty("ayah_count").GetInt32());
        Assert.Equal(1.5, kok.GetProperty("idf_q").GetDouble(), 3);
        Assert.Equal("deneme kok anlami", kok.GetProperty("kok_anlami").GetString());

        JsonElement[] kinds = [.. body.GetProperty("tur_dagilimi").EnumerateArray()];
        Assert.Equal(["N", "V"], kinds.Select(k => k.GetProperty("pos").GetString()).ToArray());
        Assert.Equal([3, 1], kinds.Select(k => k.GetProperty("sayi").GetInt32()).ToArray());

        Assert.Equal(4, body.GetProperty("siklik").GetProperty("kelime").GetInt32());
        Assert.Equal(3, body.GetProperty("siklik").GetProperty("ayet").GetInt32());
        Assert.Equal(2, body.GetProperty("dalga").GetProperty("dalga").GetInt32());
        Assert.Equal(17, body.GetProperty("dalga").GetProperty("sira").GetInt32());

        // Yalniz ayni kokun, kendisi haric ve yalniz onayli anlamlari.
        JsonElement[] siblings = [.. body.GetProperty("ayni_kok_anlamlari").EnumerateArray()];
        JsonElement sibling = Assert.Single(siblings);
        Assert.Equal(approved.Id, sibling.GetProperty("lemma_id").GetInt32());
        Assert.Equal("onayli anlam", sibling.GetProperty("anlam_kisa").GetString());
        Assert.Equal("kardes-bir", sibling.GetProperty("text").GetString());

        // Az gecisli lemmada hepsi, okuma sirasiyla.
        JsonElement[] kwic = [.. body.GetProperty("kwic").EnumerateArray()];
        Assert.Equal(["q:3:5:2", "q:3:5:3", "q:3:6:1", "q:3:7:4"], kwic.Select(k => k.GetProperty("kelime_capa").GetString()).ToArray());

        // Kod noktasi ofsetiyle dilim: UTF-16 ofseti olsaydi vekil ciftten dolayi bir kod noktasi kayardi.
        JsonElement first = kwic[0];
        Assert.Equal("q:3:5", first.GetProperty("ayet_capa").GetString());
        Assert.Equal("kelime", first.GetProperty("kelime").GetString());
        Assert.Equal("Sol" + Emoji + " ", first.GetProperty("sol").GetString());
        Assert.Equal(" sag", first.GetProperty("sag").GetString());
        Assert.Equal("meal:elmalili:3:5", first.GetProperty("meal").GetProperty("capa").GetString());
        Assert.Equal("Deneme meali 5", first.GetProperty("meal").GetProperty("metin").GetString());
        Assert.Equal("incelemede", first.GetProperty("meal").GetProperty("metin_durumu").GetString());
        Assert.Equal("sag", kwic[1].GetProperty("kelime").GetString());

        // Ayet 6: Tanzil birimi var, meal yok.
        Assert.Equal("abc", kwic[2].GetProperty("kelime").GetString());
        Assert.Equal(JsonValueKind.Null, kwic[2].GetProperty("meal").ValueKind);

        // Ayet 7: ayet birimi yok: dilim alanlari null, kayit yine de listelenir.
        Assert.Equal(JsonValueKind.Null, kwic[3].GetProperty("kelime").ValueKind);
        Assert.Equal(JsonValueKind.Null, kwic[3].GetProperty("sol").ValueKind);
        Assert.Equal(JsonValueKind.Null, kwic[3].GetProperty("sag").ValueKind);
    }

    [Fact]
    public async Task A_lemma_without_root_occurrences_or_wave_returns_nulls_and_empty_lists()
    {
        (string morph, _, _) = await SeedSourcesAsync();
        Lemma lemma = await SeedLemmaAsync(morph, rootId: null, status: XrefStatus.Aday, origin: null);
        using HttpClient client = await ClientAsync();

        JsonElement body = await GetAsync(client, lemma.Id);

        Assert.Equal(JsonValueKind.Null, body.GetProperty("kok").ValueKind);
        Assert.Equal(JsonValueKind.Null, body.GetProperty("dalga").ValueKind);
        Assert.Equal(0, body.GetProperty("tur_dagilimi").GetArrayLength());
        Assert.Equal(0, body.GetProperty("ayni_kok_anlamlari").GetArrayLength());
        Assert.Equal(0, body.GetProperty("kwic").GetArrayLength());
        Assert.Equal(0, body.GetProperty("siklik").GetProperty("kelime").GetInt32());
        Assert.Equal(0, body.GetProperty("siklik").GetProperty("ayet").GetInt32());
        Assert.Equal("aday", body.GetProperty("lemma").GetProperty("status").GetString());
    }

    [Fact]
    public async Task A_missing_lemma_is_a_404_problem_and_a_non_integer_id_does_not_match()
    {
        await SeedSourcesAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage missing = await client.GetAsync("/api/v1/lemmas/987654", Ct);
        using HttpResponseMessage zero = await client.GetAsync("/api/v1/lemmas/0", Ct);
        using HttpResponseMessage text = await client.GetAsync("/api/v1/lemmas/abc", Ct);

        Assert.Equal(HttpStatusCode.NotFound, missing.StatusCode);
        Assert.Equal("bulunamadi", await ProblemCodeAsync(missing));
        Assert.Equal(HttpStatusCode.NotFound, zero.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, text.StatusCode);
    }

    [Fact]
    public async Task Without_a_session_the_endpoint_is_a_401_problem()
    {
        await SeedSourcesAsync();
        using HttpClient anonymous = Factory.CreateApiClient();

        using HttpResponseMessage response = await anonymous.GetAsync("/api/v1/lemmas/1", Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
    }

    [Fact]
    public async Task Only_GET_is_routed_so_other_methods_are_a_405_problem()
    {
        await SeedSourcesAsync();
        using HttpClient client = await ClientAsync();

        using HttpResponseMessage response = await client.PostAsync("/api/v1/lemmas/1", content: null, Ct);

        Assert.Equal(HttpStatusCode.MethodNotAllowed, response.StatusCode);
    }

    [Fact]
    public async Task A_frequent_lemma_gets_a_deterministic_sample_of_eight_in_reading_order()
    {
        (string morph, string quran, _) = await SeedSourcesAsync();
        Root root = await SeedRootAsync(morph);
        Lemma lemma = await SeedLemmaAsync(morph, root.Id, occurrences: 20);
        List<string> anchors = [];
        for (int n = 1; n <= 20; n++)
        {
            string anchor = $"q:3:{n}:1";
            anchors.Add(anchor);
            await SeedWordAsync(morph, anchor, (short)(100 + n), 0, 4, lemma.Id, root.Id);
            await SeedUnitAsync(quran, UnitKind.Ayet, $"q:3:{n}", "kelime " + n);
        }

        using HttpClient client = await ClientAsync();

        JsonElement first = await GetAsync(client, lemma.Id);
        JsonElement second = await GetAsync(client, lemma.Id);

        string[] picked = [.. first.GetProperty("kwic").EnumerateArray().Select(k => k.GetProperty("kelime_capa").GetString()!)];
        Assert.Equal(8, picked.Length);
        Assert.Equal([.. KwicSampling.SampleIndices(20).Select(i => anchors[i])], picked);
        Assert.Equal(picked, second.GetProperty("kwic").EnumerateArray().Select(k => k.GetProperty("kelime_capa").GetString()!).ToArray());
        Assert.Equal(20, first.GetProperty("siklik").GetProperty("kelime").GetInt32());
        Assert.Equal(20, first.GetProperty("siklik").GetProperty("ayet").GetInt32());
    }

    [Fact]
    public async Task Sibling_glosses_are_limited_to_twenty_ordered_by_frequency_then_id_and_only_approved()
    {
        (string morph, _, _) = await SeedSourcesAsync();
        Root root = await SeedRootAsync(morph);
        Lemma self = await SeedLemmaAsync(morph, root.Id, "kendisi");
        await SeedGlossAsync(self.Id, "kendi anlami", XrefStatus.Onayli);
        List<Lemma> siblings = [];
        for (int n = 0; n < 25; n++)
        {
            // Gecis sayisi 3 ve 3 ve 2 ... tekrarli: esitlikte kimlik artan siralar.
            Lemma sibling = await SeedLemmaAsync(morph, root.Id, "kardes-" + n, occurrences: 30 - (n / 2));
            await SeedGlossAsync(sibling.Id, "anlam " + n, XrefStatus.Onayli);
            siblings.Add(sibling);
        }

        Lemma red = await SeedLemmaAsync(morph, root.Id, "reddedilmis", occurrences: 1000);
        await SeedGlossAsync(red.Id, "red anlam", XrefStatus.Red);
        using HttpClient client = await ClientAsync();

        JsonElement body = await GetAsync(client, self.Id);

        int[] ids = [.. body.GetProperty("ayni_kok_anlamlari").EnumerateArray().Select(s => s.GetProperty("lemma_id").GetInt32())];
        Assert.Equal(20, ids.Length);
        Assert.DoesNotContain(self.Id, ids);
        Assert.DoesNotContain(red.Id, ids);
        Assert.Equal([.. siblings.OrderByDescending(s => s.Occurrences).ThenBy(s => s.Id).Take(20).Select(s => s.Id)], ids);
    }

    [Fact]
    public async Task An_offset_beyond_the_ayah_text_gives_null_slices_instead_of_failing()
    {
        (string morph, string quran, _) = await SeedSourcesAsync();
        Lemma lemma = await SeedLemmaAsync(morph, occurrences: 1);
        await SeedWordAsync(morph, "q:3:9:1", 109, 2, 50, lemma.Id);
        await SeedUnitAsync(quran, UnitKind.Ayet, "q:3:9", "kisa metin");
        using HttpClient client = await ClientAsync();

        JsonElement item = (await GetAsync(client, lemma.Id)).GetProperty("kwic")[0];

        Assert.Equal("q:3:9:1", item.GetProperty("kelime_capa").GetString());
        Assert.Equal(JsonValueKind.Null, item.GetProperty("kelime").ValueKind);
        Assert.Equal(JsonValueKind.Null, item.GetProperty("sol").ValueKind);
    }

    [Fact]
    public async Task The_context_is_limited_to_forty_code_points_on_each_side_and_never_splits_a_surrogate_pair()
    {
        (string morph, string quran, _) = await SeedSourcesAsync();
        Lemma lemma = await SeedLemmaAsync(morph, occurrences: 1);

        // 60 vekil cift (kod noktasi 0..59), "hedef" (60..64), 60 vekil cift: UTF-16 ve kod noktasi ofsetleri bariz ayrisir.
        string left = string.Concat(Enumerable.Repeat(Emoji, 60));
        string right = string.Concat(Enumerable.Repeat(Emoji, 60));
        await SeedWordAsync(morph, "q:3:10:1", 110, 60, 65, lemma.Id);
        await SeedUnitAsync(quran, UnitKind.Ayet, "q:3:10", left + "hedef" + right);
        using HttpClient client = await ClientAsync();

        JsonElement item = (await GetAsync(client, lemma.Id)).GetProperty("kwic")[0];

        Assert.Equal("hedef", item.GetProperty("kelime").GetString());
        Assert.Equal(string.Concat(Enumerable.Repeat(Emoji, 40)), item.GetProperty("sol").GetString());
        Assert.Equal(string.Concat(Enumerable.Repeat(Emoji, 40)), item.GetProperty("sag").GetString());
    }

    [Fact]
    public async Task A_follower_meal_with_an_empty_text_is_not_returned_as_the_meal()
    {
        (string morph, string quran, string meal) = await SeedSourcesAsync();
        Lemma lemma = await SeedLemmaAsync(morph, occurrences: 1);
        await SeedWordAsync(morph, "q:3:11:1", 111, 0, 3, lemma.Id);
        await SeedUnitAsync(quran, UnitKind.Ayet, "q:3:11", "abc def");
        await SeedUnitAsync(meal, UnitKind.Meal, "meal:elmalili:3:11", string.Empty);
        using HttpClient client = await ClientAsync();

        JsonElement item = (await GetAsync(client, lemma.Id)).GetProperty("kwic")[0];

        Assert.Equal(JsonValueKind.Null, item.GetProperty("meal").ValueKind);
    }

    [Fact]
    public async Task The_card_is_read_only_and_leaves_the_data_unchanged()
    {
        (string morph, _, _) = await SeedSourcesAsync();
        Lemma lemma = await SeedLemmaAsync(morph, occurrences: 3);
        using HttpClient client = await ClientAsync();
        long before = await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.lemma", Ct);

        await GetAsync(client, lemma.Id);

        Assert.Equal(before, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.lemma", Ct));
    }
}
