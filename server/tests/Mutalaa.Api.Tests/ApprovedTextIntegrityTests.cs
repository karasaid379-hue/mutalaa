using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Editor duzeltmesi onaylandiktan sonra veritabanindaki <c>unit.metin</c> baytlari ile <c>content_hash</c> (K-26): beklenen deger
/// testte elle yazilmis kanonik metindir ve bagimsiz hesaplanir (SQL sha256 ve System.Security.Cryptography), uretim koduna dayanmaz.
/// Metin sentetiktir; Arapca harf, sedde ya da hareke yoktur (Docker'li).
/// </summary>
public class ApprovedTextIntegrityTests(EditorialDatabase<ApprovedTextIntegrityTests> fixture)
    : ReviewTestBase<ApprovedTextIntegrityTests>(fixture), IClassFixture<EditorialDatabase<ApprovedTextIntegrityTests>>
{
    // Karakterler kodla uretilir; kaynak dosyada gorunmez ya da birlesik karakter bulunmaz.
    private static readonly string CombiningAcute = ((char)0x0301).ToString();
    private static readonly string LeftToRightMark = ((char)0x200E).ToString();
    private static readonly string PrecomposedE = ((char)0x00E9).ToString();

    [Fact]
    public async Task An_approved_correction_stores_the_canonical_text_whose_utf8_sha256_is_the_content_hash()
    {
        // Girdi: 'e' + U+0301 (NFC'de tek kod noktasi), CRLF ve silinen bicim karakteri U+200E.
        string sent = "Deneme e" + CombiningAcute + "\r\n" + LeftToRightMark + "satir";
        // Beklenen kanonik metin elle yazili sabit: NFC U+00E9, LF, U+200E yok.
        string expected = "Deneme " + PrecomposedE + "\nsatir";
        Assert.NotEqual(expected, sent);
        Assert.False(sent.IsNormalized(NormalizationForm.FormC));
        Assert.Equal(14, expected.Length);

        string source = await SeedSourceAsync(SourceKind.Risale);
        string anchor = TestData.UnitAnchor();
        Unit unit = await SeedUnitAsync(source, UnitKind.Risale, anchor);
        using HttpClient editorA = await ClientAsync();
        using HttpClient editorB = await ClientAsync(EditorBEmail, EditorBPassword);

        using HttpResponseMessage proposal = await editorA.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(anchor) + "/corrections",
            new { metin = sent, gerekce = "Kanonik metin denemesi" },
            Ct);
        Assert.Equal(HttpStatusCode.Created, proposal.StatusCode);
        long reviewId = (await ApiFactory.ReadJsonAsync(proposal, Ct)).GetProperty("id").GetInt64();

        using HttpResponseMessage approval = await DecideAsync(editorB, reviewId, Etag(await XminAsync(reviewId)), Approve());
        Assert.Equal(HttpStatusCode.OK, approval.StatusCode);

        (string metin, string hash, int rev, string durum) = await UnitRowAsync(anchor);
        Assert.Equal(expected, metin);
        Assert.True(Encoding.UTF8.GetBytes(expected).AsSpan().SequenceEqual(Encoding.UTF8.GetBytes(metin)), "unit.metin baytlari beklenen kanonik metinle esit olmali.");
        Assert.Equal(2, rev);
        Assert.Equal("onayli", durum);
        Assert.NotEqual(unit.ContentHash, hash);

        string independentCs = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(expected)));
        string independentSql = await Db.ScalarAsync<string>(
            "SELECT encode(sha256(convert_to(metin, 'UTF8')), 'hex') FROM icerik.unit WHERE anchor = @a",
            Ct,
            ("a", anchor));
        Assert.Equal(independentCs, independentSql);
        Assert.Equal(independentCs, hash);

        // Duzeltme onerisinin saklanan yuku de ayni kanonik metni ve ozeti tasir.
        using HttpResponseMessage detailResponse = await editorB.GetAsync($"/api/v1/reviews/{reviewId}", Ct);
        using JsonDocument detail = JsonDocument.Parse(await detailResponse.Content.ReadAsByteArrayAsync(Ct));
        Assert.Equal(expected, detail.RootElement.GetProperty("onerilen").GetProperty("metin").GetString());
        Assert.Equal(independentCs, detail.RootElement.GetProperty("onerilen").GetProperty("content_hash").GetString());
    }
}
