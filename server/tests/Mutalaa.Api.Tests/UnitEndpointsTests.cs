using System.Net;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>/api/v1/units: liste (suzgec, arama, imlec sayfalama) ve ayrinti (Docker'li).</summary>
public class UnitEndpointsTests(EditorialDatabase<UnitEndpointsTests> fixture)
    : EditorApiTestBase<UnitEndpointsTests>(fixture), IClassFixture<EditorialDatabase<UnitEndpointsTests>>
{
    private static readonly string[] ListItemFields =
    [
        "anchor", "kind", "role", "source", "ord", "metin_durumu", "status", "rev", "content_hash", "parent_path", "metin",
    ];

    private static readonly string[] DetailFields =
    [
        .. ListItemFields,
        "marks", "attrs", "sentences", "ayah_range", "successors", "data_version", "provenance", "created_at", "updated_at",
        "duzeltilebilir", "kaynak_tur",
    ];

    // Iki kaynak, yedi birim: test-u1 (ord 1..5, ord 3 iki kez), test-u2 (2 birim). Sentetik metinler.
    private async Task SeedAsync()
    {
        await SeedSourceAsync("test-u1", SourceKind.Risale);
        await SeedSourceAsync("test-u2", SourceKind.Risale);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p1", "Deneme paragrafı 1", ord: 1);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p10", "Deneme paragrafı 10", ord: 2);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p2", "Deneme ışık paragrafı", ord: 3);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p3", "Deneme paragrafı 3", ord: 3);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p4", "Deneme paragrafı 4", ord: 5);
        await SeedUnitAsync("test-u2", "rn:mektubat:m-1:p1", "Deneme paragrafı abc", ord: 1);
        await SeedUnitAsync("test-u2", "rn:mektubat:m-1:p2", "Deneme بس paragrafı", ord: 2);
    }

    private static async Task<JsonElement> GetListAsync(HttpClient client, string query)
    {
        using HttpResponseMessage response = await client.GetAsync("/api/v1/units" + query, Ct);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return await ReadAsync(response);
    }

    private static string[] Anchors(JsonElement list) =>
        [.. list.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("anchor").GetString()!)];

    private static async Task AssertProblemAsync(HttpResponseMessage response, HttpStatusCode status, string code)
    {
        Assert.Equal(status, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ReadAsync(response);
        Assert.Equal("urn:mutalaa:problem:" + code, ProblemType(body));
    }

    // Liste

    [Fact]
    public async Task The_list_returns_items_with_exactly_the_documented_fields_and_no_search_vectors()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        string text = await response.Content.ReadAsStringAsync(Ct);
        Assert.DoesNotContain("tsv", text, StringComparison.Ordinal);
        using JsonDocument document = JsonDocument.Parse(text);
        JsonElement list = document.RootElement;
        Assert.Equal(["items", "next_cursor"], list.EnumerateObject().Select(p => p.Name));
        JsonElement first = list.GetProperty("items")[0];
        Assert.Equal(ListItemFields.Order(StringComparer.Ordinal), first.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal("rn:sozler:soz-10:p1", first.GetProperty("anchor").GetString());
        Assert.Equal("risale", first.GetProperty("kind").GetString());
        Assert.Equal("govde", first.GetProperty("role").GetString());
        Assert.Equal("test-u1", first.GetProperty("source").GetString());
        Assert.Equal("taslak", first.GetProperty("metin_durumu").GetString());
        Assert.Equal("etkin", first.GetProperty("status").GetString());
        Assert.Equal(1, first.GetProperty("rev").GetInt32());
        Assert.Equal("Deneme paragrafı 1", first.GetProperty("metin").GetString());
        Assert.Equal(64, first.GetProperty("content_hash").GetString()!.Length);
    }

    [Fact]
    public async Task Items_are_ordered_by_source_ord_and_id_across_pages_with_a_null_cursor_on_the_last_page()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        List<string> seen = [];
        string? cursor = null;
        int pages = 0;
        JsonElement last;
        do
        {
            last = await GetListAsync(client, "?limit=3" + (cursor is null ? string.Empty : "&cursor=" + Uri.EscapeDataString(cursor)));
            seen.AddRange(Anchors(last));
            JsonElement next = last.GetProperty("next_cursor");
            cursor = next.ValueKind == JsonValueKind.Null ? null : next.GetString();
            pages++;
        }
        while (cursor is not null && pages < 10);

        Assert.Equal(3, pages);
        Assert.Equal(JsonValueKind.Null, last.GetProperty("next_cursor").ValueKind);
        Assert.Equal(
            [
                "rn:sozler:soz-10:p1", "rn:sozler:soz-10:p10", "rn:sozler:soz-10:p2", "rn:sozler:soz-10:p3", "rn:sozler:soz-10:p4",
                "rn:mektubat:m-1:p1", "rn:mektubat:m-1:p2",
            ],
            seen);
    }

    [Fact]
    public async Task A_page_exactly_as_large_as_the_result_has_no_next_cursor()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?limit=7");

        Assert.Equal(7, list.GetProperty("items").GetArrayLength());
        Assert.Equal(JsonValueKind.Null, list.GetProperty("next_cursor").ValueKind);
    }

    [Fact]
    public async Task Two_pages_with_a_cursor_in_the_middle_of_equal_ord_values_lose_and_repeat_nothing()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        // limit=3 ilk sayfa p1, p10, p2; ikinci sayfa p3 (ayni ord, daha buyuk id) ile baslar.
        JsonElement first = await GetListAsync(client, "?source=test-u1&limit=3");
        string cursor = first.GetProperty("next_cursor").GetString()!;
        JsonElement second = await GetListAsync(client, "?source=test-u1&limit=3&cursor=" + Uri.EscapeDataString(cursor));

        Assert.Equal(["rn:sozler:soz-10:p1", "rn:sozler:soz-10:p10", "rn:sozler:soz-10:p2"], Anchors(first));
        Assert.Equal(["rn:sozler:soz-10:p3", "rn:sozler:soz-10:p4"], Anchors(second));
        Assert.Equal(JsonValueKind.Null, second.GetProperty("next_cursor").ValueKind);
    }

    [Theory]
    [InlineData("limit=0")]
    [InlineData("limit=201")]
    [InlineData("limit=-1")]
    [InlineData("limit=abc")]
    [InlineData("limit=1.5")]
    public async Task A_limit_outside_1_to_200_is_a_400_validation_problem(string query)
    {
        using HttpClient client = await LoginEditorAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units?" + query, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
    }

    [Theory]
    [InlineData(1)]
    [InlineData(200)]
    public async Task The_limit_bounds_themselves_are_accepted(int limit)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?limit=" + limit);

        Assert.Equal(Math.Min(limit, 7), list.GetProperty("items").GetArrayLength());
    }

    [Theory]
    [InlineData("!!!")]
    [InlineData("YQ")]
    [InlineData("YR")]
    [InlineData("eHl6")]
    [InlineData("MTox")]
    [InlineData("MTE6MjI6")]
    [InlineData("LTE6MTpkZW5lbWU")]
    [InlineData("MDE6MTpkZW5lbWU")]
    public async Task A_malformed_cursor_is_a_400_validation_problem(string cursor)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units?cursor=" + Uri.EscapeDataString(cursor), Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "dogrulama");
    }

    [Fact]
    public async Task The_source_filter_limits_the_list_and_an_unknown_source_is_a_404_not_an_empty_list()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?source=test-u2");
        using HttpResponseMessage unknown = await client.GetAsync("/api/v1/units?source=test-yok", Ct);

        Assert.Equal(["rn:mektubat:m-1:p1", "rn:mektubat:m-1:p2"], Anchors(list));
        await AssertProblemAsync(unknown, HttpStatusCode.NotFound, "bulunamadi");
    }

    [Fact]
    public async Task The_prefix_filter_matches_the_anchor_start()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement p1 = await GetListAsync(client, "?prefix=" + Uri.EscapeDataString("rn:sozler:soz-10:p1"));
        JsonElement mektubat = await GetListAsync(client, "?prefix=" + Uri.EscapeDataString("rn:mektubat:"));
        JsonElement middle = await GetListAsync(client, "?prefix=" + Uri.EscapeDataString("soz-10"));

        Assert.Equal(["rn:sozler:soz-10:p1", "rn:sozler:soz-10:p10"], Anchors(p1));
        Assert.Equal(["rn:mektubat:m-1:p1", "rn:mektubat:m-1:p2"], Anchors(mektubat));
        Assert.Empty(Anchors(middle));
    }

    [Theory]
    [InlineData("rn:sozler:soz-1_")]
    [InlineData("rn:%")]
    [InlineData("%")]
    [InlineData("_")]
    [InlineData("rn:sozler:soz-10:p\\")]
    [InlineData("rn:sozler:soz-10:p\\1")]
    public async Task LIKE_wildcards_in_the_prefix_are_escaped_and_match_nothing(string prefix)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?prefix=" + Uri.EscapeDataString(prefix));

        Assert.Empty(Anchors(list));
    }

    [Fact]
    public async Task A_Turkish_query_matches_with_I_and_dotless_i_folded_in_either_spelling()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement upper = await GetListAsync(client, "?q=" + Uri.EscapeDataString("ISIK"));
        JsonElement lower = await GetListAsync(client, "?q=" + Uri.EscapeDataString("ışık"));
        JsonElement dotted = await GetListAsync(client, "?q=" + Uri.EscapeDataString("İŞİK"));

        Assert.Equal(["rn:sozler:soz-10:p2"], Anchors(upper));
        Assert.Equal(Anchors(upper), Anchors(lower));
        Assert.Equal(Anchors(upper), Anchors(dotted));
    }

    [Fact]
    public async Task An_Arabic_query_searches_the_arabic_key()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?q=" + Uri.EscapeDataString("بس"));

        Assert.Equal(["rn:mektubat:m-1:p2"], Anchors(list));
    }

    [Fact]
    public async Task The_q_filter_combines_with_the_source_filter()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement both = await GetListAsync(client, "?q=paragraf&source=test-u2");

        Assert.Equal(["rn:mektubat:m-1:p1", "rn:mektubat:m-1:p2"], Anchors(both));
    }

    [Theory]
    [InlineData("a_c")]
    [InlineData("a%c")]
    [InlineData("%")]
    [InlineData("_")]
    [InlineData("\\")]
    public async Task LIKE_wildcards_in_q_never_act_as_wildcards(string q)
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        // "abc" metni var; 'a_c' ve 'a%c' joker olsaydi onu bulurdu.
        JsonElement list = await GetListAsync(client, "?q=" + Uri.EscapeDataString(q));

        Assert.Empty(Anchors(list));
    }

    [Fact]
    public async Task A_q_with_only_punctuation_normalizes_to_nothing_and_matches_no_unit()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        JsonElement list = await GetListAsync(client, "?q=" + Uri.EscapeDataString("...!?"));

        Assert.Empty(Anchors(list));
        Assert.Equal(JsonValueKind.Null, list.GetProperty("next_cursor").ValueKind);
    }

    [Fact]
    public async Task A_q_of_1024_code_points_is_accepted_and_1025_is_a_400()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        using HttpResponseMessage ascii = await client.GetAsync("/api/v1/units?q=" + new string('a', 1024), Ct);
        using HttpResponseMessage asciiOver = await client.GetAsync("/api/v1/units?q=" + new string('a', 1025), Ct);
        // U+0130 (Turkce buyuk noktali I) tek UTF-16 birimidir.
        using HttpResponseMessage dotted = await client.GetAsync("/api/v1/units?q=" + Uri.EscapeDataString(new string('İ', 1024)), Ct);
        using HttpResponseMessage dottedOver = await client.GetAsync("/api/v1/units?q=" + Uri.EscapeDataString(new string('İ', 1025)), Ct);

        Assert.Equal(HttpStatusCode.OK, ascii.StatusCode);
        await AssertProblemAsync(asciiOver, HttpStatusCode.BadRequest, "dogrulama");
        Assert.Equal(HttpStatusCode.OK, dotted.StatusCode);
        await AssertProblemAsync(dottedOver, HttpStatusCode.BadRequest, "dogrulama");
    }

    [Fact]
    public async Task The_q_length_counts_code_points_not_utf16_units()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();
        string grin = char.ConvertFromUtf32(0x1F600);

        // 600 kod noktasi = 1200 UTF-16 birimi: kabul. 1025 kod noktasi: red.
        using HttpResponseMessage within = await client.GetAsync("/api/v1/units?q=" + Uri.EscapeDataString(string.Concat(Enumerable.Repeat(grin, 600))), Ct);
        using HttpResponseMessage over = await client.GetAsync("/api/v1/units?q=" + Uri.EscapeDataString(string.Concat(Enumerable.Repeat(grin, 1025))), Ct);

        Assert.Equal(HttpStatusCode.OK, within.StatusCode);
        await AssertProblemAsync(over, HttpStatusCode.BadRequest, "dogrulama");
    }

    [Fact]
    public async Task The_results_are_the_same_under_the_tr_TR_culture()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();
        string[] queries = ["?limit=2", "?q=ISIK", "?q=" + Uri.EscapeDataString("ışık"), "?prefix=rn:sozler:soz-10:p1", "?source=test-u2"];
        List<string> invariant = [];
        foreach (string query in queries)
        {
            invariant.Add((await GetListAsync(client, query)).GetRawText());
        }

        List<string> turkish = [];
        await AsyncCultureScope.TurkishAsync(async () =>
        {
            foreach (string query in queries)
            {
                turkish.Add((await GetListAsync(client, query)).GetRawText());
            }
        });

        Assert.Equal(invariant, turkish);
        Assert.Equal(["rn:sozler:soz-10:p2"], Anchors(JsonDocument.Parse(turkish[1]).RootElement));
    }

    [Fact]
    public async Task Without_a_session_the_list_and_the_detail_are_401_problems_without_a_redirect()
    {
        using HttpClient client = Factory.CreateApiClient();

        foreach (string path in new[] { "/api/v1/units", "/api/v1/units/rn:sozler:soz-10:p1" })
        {
            using HttpResponseMessage response = await client.GetAsync(path, Ct);

            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
            Assert.Null(response.Headers.Location);
        }
    }

    // Ayrinti

    [Fact]
    public async Task The_detail_returns_every_field_with_json_columns_raw_and_an_xmin_etag()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-u1", SourceKind.Risale);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p1", "Deneme paragrafı 1", ord: 4, configure: u =>
        {
            u.Marks = """[{"tur":"vurgu","aralik":[0,6]}]""";
            u.Attrs = """{"not":"deneme"}""";
            u.Sentences = [new AnchorSpan(0, 6), new AnchorSpan(7, 18)];
            u.AyahRange = new AnchorSpan(2, 4);
            u.ParentPath = "rn:sozler:soz-10";
            u.Provenance = """{"kaynak":"deneme"}""";
        });

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/rn:sozler:soz-10:p1", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement unit = await ReadAsync(response);
        Assert.Equal(DetailFields.Order(StringComparer.Ordinal), unit.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal("rn:sozler:soz-10:p1", unit.GetProperty("anchor").GetString());
        Assert.Equal(4L, unit.GetProperty("ord").GetInt64());
        Assert.Equal("rn:sozler:soz-10", unit.GetProperty("parent_path").GetString());
        Assert.Equal("test", unit.GetProperty("data_version").GetString());
        Assert.Equal(JsonValueKind.Array, unit.GetProperty("marks").ValueKind);
        Assert.Equal("vurgu", unit.GetProperty("marks")[0].GetProperty("tur").GetString());
        Assert.Equal(JsonValueKind.Object, unit.GetProperty("attrs").ValueKind);
        Assert.Equal("deneme", unit.GetProperty("provenance").GetProperty("kaynak").GetString());
        Assert.Equal("[[0,6],[7,18]]", unit.GetProperty("sentences").GetRawText().Replace(" ", string.Empty, StringComparison.Ordinal));
        Assert.Equal("[2,4]", unit.GetProperty("ayah_range").GetRawText().Replace(" ", string.Empty, StringComparison.Ordinal));
        Assert.Equal(JsonValueKind.Null, unit.GetProperty("successors").ValueKind);
        Assert.Equal("risale", unit.GetProperty("kaynak_tur").GetString());
        Assert.True(unit.GetProperty("duzeltilebilir").GetBoolean());

        string xmin = await Db.ScalarAsync<string>("SELECT xmin::text FROM icerik.unit WHERE anchor = 'rn:sozler:soz-10:p1'", Ct);
        Assert.Equal("\"" + xmin + "\"", response.Headers.ETag?.Tag);
    }

    [Fact]
    public async Task Without_optional_data_sentences_ayah_range_and_successors_are_null()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-u1", SourceKind.Risale);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p1", "Deneme paragrafı 1");

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/rn:sozler:soz-10:p1", Ct);

        JsonElement unit = await ReadAsync(response);
        Assert.Equal(JsonValueKind.Null, unit.GetProperty("sentences").ValueKind);
        Assert.Equal(JsonValueKind.Null, unit.GetProperty("ayah_range").ValueKind);
        Assert.Equal(JsonValueKind.Null, unit.GetProperty("successors").ValueKind);
        Assert.Equal(JsonValueKind.Null, unit.GetProperty("parent_path").ValueKind);
        Assert.Equal(JsonValueKind.Array, unit.GetProperty("marks").ValueKind);
        Assert.Equal(JsonValueKind.Object, unit.GetProperty("attrs").ValueKind);
    }

    [Fact]
    public async Task A_deprecated_unit_returns_its_successors_as_raw_json()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-u1", SourceKind.Risale);
        await SeedUnitAsync("test-u1", "rn:sozler:soz-10:p1", "Deneme paragrafı 1", configure: u =>
        {
            u.Status = UnitStatus.KullanimDisi;
            u.Successors = """["rn:sozler:soz-10:p2"]""";
        });

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/rn:sozler:soz-10:p1", Ct);

        JsonElement unit = await ReadAsync(response);
        Assert.Equal("kullanim_disi", unit.GetProperty("status").GetString());
        Assert.Equal("rn:sozler:soz-10:p2", unit.GetProperty("successors")[0].GetString());
    }

    [Fact]
    public async Task An_ayah_unit_and_a_unit_of_a_quran_text_source_are_not_correctable_but_a_meal_unit_is()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-q", SourceKind.KuranMetni);
        await SeedSourceAsync("test-m", SourceKind.Meal);
        await SeedUnitAsync("test-q", "q:2:255", "Deneme ayet metni", UnitKind.Ayet);
        await SeedUnitAsync("test-q", "meal:deneme:2:255", "Deneme meal metni", UnitKind.Meal);
        await SeedUnitAsync("test-m", "q:1:1", "Deneme ayet metni", UnitKind.Ayet);
        await SeedUnitAsync("test-m", "meal:deneme:1:1", "Deneme meal metni", UnitKind.Meal);

        bool Correctable(JsonElement unit) => unit.GetProperty("duzeltilebilir").GetBoolean();
        async Task<JsonElement> DetailAsync(string anchor) => await ReadAsync(await client.GetAsync("/api/v1/units/" + Uri.EscapeDataString(anchor), Ct));

        JsonElement ayah = await DetailAsync("q:2:255");
        JsonElement mealInQuranSource = await DetailAsync("meal:deneme:2:255");
        JsonElement ayahInMealSource = await DetailAsync("q:1:1");
        JsonElement meal = await DetailAsync("meal:deneme:1:1");

        Assert.False(Correctable(ayah));
        Assert.Equal("kuran_metni", ayah.GetProperty("kaynak_tur").GetString());
        Assert.False(Correctable(mealInQuranSource));
        Assert.False(Correctable(ayahInMealSource));
        Assert.True(Correctable(meal));
        Assert.Equal("meal", meal.GetProperty("kaynak_tur").GetString());
    }

    [Fact]
    public async Task The_anchor_path_segment_accepts_url_encoded_colons()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-q", SourceKind.KuranMetni);
        await SeedUnitAsync("test-q", "q:2:255", "Deneme ayet metni", UnitKind.Ayet);

        using HttpResponseMessage encoded = await client.GetAsync("/api/v1/units/q%3A2%3A255", Ct);
        using HttpResponseMessage plain = await client.GetAsync("/api/v1/units/q:2:255", Ct);

        Assert.Equal(HttpStatusCode.OK, encoded.StatusCode);
        Assert.Equal(HttpStatusCode.OK, plain.StatusCode);
    }

    [Fact]
    public async Task Text_is_returned_as_is_and_not_escaped_byte_for_byte()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedSourceAsync("test-q", SourceKind.KuranMetni);
        // Sentetik dizgi: Latin harfler, Turkce harf ve iki Arapca harf (U+0628 U+0633); normallestirme ve NFC yok.
        string metin = "Deneme paragrafı بس ışık İ";
        await SeedUnitAsync("test-q", "q:2:255", metin, UnitKind.Ayet);

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/q:2:255", Ct);

        byte[] bytes = await response.Content.ReadAsByteArrayAsync(Ct);
        string raw = Encoding.UTF8.GetString(bytes);
        Assert.DoesNotContain("\\u", raw, StringComparison.Ordinal);
        Assert.Contains(metin, raw, StringComparison.Ordinal);
        using JsonDocument document = JsonDocument.Parse(bytes);
        string roundTrip = document.RootElement.GetProperty("metin").GetString()!;
        Assert.True(Encoding.UTF8.GetBytes(metin).AsSpan().SequenceEqual(Encoding.UTF8.GetBytes(roundTrip)));
    }

    [Theory]
    [InlineData("bozuk", "BICIM")]
    [InlineData("Q:2:255", "BICIM")]
    [InlineData("q:115:1", "SURE_ARALIGI")]
    [InlineData("q:2:287", "AYET_ARALIGI")]
    [InlineData("q:2:255:7-3", "TERS_ARALIK")]
    [InlineData("q:2:255-255", "KANONIK_DEGIL")]
    public async Task A_malformed_anchor_is_a_400_capa_gecersiz_with_the_grammar_error_code(string anchor, string errorCode)
    {
        using HttpClient client = await LoginEditorAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/" + Uri.EscapeDataString(anchor), Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "capa-gecersiz");
        Assert.Equal(errorCode, (await ReadAsync(response)).GetProperty("capa_hata_kodu").GetString());
    }

    [Theory]
    [InlineData("meal:elmalili:2:255@10-48")]
    [InlineData("q:2:255:3")]
    [InlineData("q:2:255:3-7")]
    [InlineData("q:2:255-257")]
    [InlineData("rn:sozler:soz-10:p4:s2")]
    [InlineData("rn:sozler:soz-10:p4@0-5")]
    [InlineData("konu:tevhid")]
    public async Task A_valid_anchor_that_is_not_unit_level_is_a_400_capa_gecersiz(string anchor)
    {
        using HttpClient client = await LoginEditorAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/" + anchor, Ct);

        await AssertProblemAsync(response, HttpStatusCode.BadRequest, "capa-gecersiz");
    }

    [Fact]
    public async Task A_missing_unit_is_a_404_problem()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/units/rn:sozler:soz-10:p99", Ct);

        await AssertProblemAsync(response, HttpStatusCode.NotFound, "bulunamadi");
    }
}
