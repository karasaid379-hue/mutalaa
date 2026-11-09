using System.Net;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>/api/v1/sources: salt okunur kaynak kaydi ve birim sayisi (Docker'li).</summary>
public class SourceEndpointsTests(EditorialDatabase<SourceEndpointsTests> fixture)
    : EditorApiTestBase<SourceEndpointsTests>(fixture), IClassFixture<EditorialDatabase<SourceEndpointsTests>>
{
    private static readonly string[] ExpectedFields =
    [
        "slug", "tur", "baslik", "yazar", "surum", "provider", "kaynak_url", "alinma_tarihi", "dosya_sha256", "baski_bilgisi",
        "atif_metni", "atif_url", "notice_text", "notlar", "created_at", "updated_at", "birim_sayisi",
    ];

    private async Task SeedTwoSourcesAsync()
    {
        // Eklenme sirasi slug sirasinin tersi: liste ekleme sirasina degil slug'a gore donmeli.
        await SeedSourceAsync("test-b-kuran", SourceKind.KuranMetni);
        await SeedSourceAsync("test-a-risale", SourceKind.Risale, s =>
        {
            s.Baslik = "Deneme risalesi";
            s.Yazar = "Deneme yazari";
            s.Provider = "deneme-saglayici";
            s.KaynakUrl = "https://example.test/kaynak";
            s.AlinmaTarihi = new DateOnly(2026, 1, 2);
            s.DosyaSha256 = TestData.Hash('b');
            s.BaskiBilgisi = """{"yayinevi":"Deneme yayinevi","yil":1999,"cilt":[1,2]}""";
            s.AtifUrl = "https://example.test/atif";
            s.NoticeText = "Deneme notu";
            s.Notlar = "Deneme notlari";
        });
        await SeedUnitAsync("test-a-risale", "rn:sozler:soz-10:p1", "Deneme paragrafı 1", ord: 1);
        await SeedUnitAsync("test-a-risale", "rn:sozler:soz-10:p2", "Deneme paragrafı 2", ord: 2);
    }

    [Fact]
    public async Task The_list_returns_every_source_in_slug_order_with_snake_case_fields_and_unit_counts()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedTwoSourcesAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/sources", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement[] sources = [.. (await ReadAsync(response)).EnumerateArray()];
        Assert.Equal(["test-a-risale", "test-b-kuran"], sources.Select(s => s.GetProperty("slug").GetString()));
        Assert.Equal(ExpectedFields.Order(StringComparer.Ordinal), sources[0].EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal(2L, sources[0].GetProperty("birim_sayisi").GetInt64());
        Assert.Equal(0L, sources[1].GetProperty("birim_sayisi").GetInt64());
        Assert.Equal("risale", sources[0].GetProperty("tur").GetString());
        Assert.Equal("kuran_metni", sources[1].GetProperty("tur").GetString());
        Assert.Equal(JsonValueKind.Null, sources[1].GetProperty("baski_bilgisi").ValueKind);
        Assert.Equal(JsonValueKind.Null, sources[1].GetProperty("yazar").ValueKind);
    }

    [Fact]
    public async Task The_detail_returns_the_record_with_the_json_columns_as_objects_not_strings()
    {
        using HttpClient client = await LoginEditorAsync();
        await SeedTwoSourcesAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/sources/test-a-risale", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement source = await ReadAsync(response);
        Assert.Equal("Deneme risalesi", source.GetProperty("baslik").GetString());
        Assert.Equal("Deneme yazari", source.GetProperty("yazar").GetString());
        Assert.Equal("2026-01-02", source.GetProperty("alinma_tarihi").GetString());
        Assert.Equal(TestData.Hash('b'), source.GetProperty("dosya_sha256").GetString());
        Assert.Equal("Deneme notu", source.GetProperty("notice_text").GetString());
        Assert.Equal(2L, source.GetProperty("birim_sayisi").GetInt64());

        JsonElement print = source.GetProperty("baski_bilgisi");
        Assert.Equal(JsonValueKind.Object, print.ValueKind);
        Assert.Equal("Deneme yayinevi", print.GetProperty("yayinevi").GetString());
        Assert.Equal(1999, print.GetProperty("yil").GetInt32());
        Assert.Equal(2, print.GetProperty("cilt").GetArrayLength());
        Assert.True(source.GetProperty("created_at").TryGetDateTimeOffset(out _));
    }

    [Fact]
    public async Task An_unknown_slug_is_a_404_problem()
    {
        using HttpClient client = await LoginEditorAsync();

        using HttpResponseMessage response = await client.GetAsync("/api/v1/sources/test-yok", Ct);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal("urn:mutalaa:problem:bulunamadi", ProblemType(await ReadAsync(response)));
    }

    [Theory]
    [InlineData("POST", "/api/v1/sources")]
    [InlineData("PUT", "/api/v1/sources")]
    [InlineData("PATCH", "/api/v1/sources")]
    [InlineData("DELETE", "/api/v1/sources")]
    [InlineData("POST", "/api/v1/sources/test-a-risale")]
    [InlineData("PUT", "/api/v1/sources/test-a-risale")]
    [InlineData("PATCH", "/api/v1/sources/test-a-risale")]
    [InlineData("DELETE", "/api/v1/sources/test-a-risale")]
    public async Task Methods_other_than_GET_are_405_with_an_Allow_header_for_an_editor_and_for_anonymous(string method, string path)
    {
        using HttpClient editor = await LoginEditorAsync();
        await SeedTwoSourcesAsync();
        using HttpClient anonymous = Factory.CreateApiClient();

        foreach (HttpClient client in new[] { editor, anonymous })
        {
            using HttpRequestMessage request = new(new HttpMethod(method), path);
            if (method is "POST" or "PUT" or "PATCH")
            {
                request.Content = new StringContent("{}", Encoding.UTF8, "application/json");
            }

            using HttpResponseMessage response = await client.SendAsync(request, Ct);

            Assert.Equal(HttpStatusCode.MethodNotAllowed, response.StatusCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
            Assert.Equal(["GET"], response.Content.Headers.Allow);
            Assert.Equal("urn:mutalaa:problem:yontem-desteklenmiyor", ProblemType(await ReadAsync(response)));
        }

        // Kayit degismedi.
        Assert.Equal(2L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.source", Ct));
    }

    [Theory]
    [InlineData("/api/v1/sources")]
    [InlineData("/api/v1/sources/test-a-risale")]
    public async Task Without_a_session_a_GET_is_a_401_problem_with_no_redirect(string path)
    {
        using HttpClient client = Factory.CreateApiClient();

        using HttpResponseMessage response = await client.GetAsync(path, Ct);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Null(response.Headers.Location);
    }
}
