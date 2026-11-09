using System.Net;
using System.Net.Http.Json;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Gunluk gizliligi: giris (basarili ve basarisiz), kullanici olusturma, duzeltme ve karar uclari boyunca toplanan butun gunluk
/// iletilerinde e-posta, parola, oturum cerezi degeri ve istek govdesi metni gecmez (Docker'li; sentetik degerler).
/// </summary>
public class ApiLogPrivacyTests(EditorialDatabase<ApiLogPrivacyTests> fixture)
    : EditorApiTestBase<ApiLogPrivacyTests>(fixture), IClassFixture<EditorialDatabase<ApiLogPrivacyTests>>
{
    private const string AdminEmail = "yonetici-gizlilik@example.test";
    private const string AdminPassword = "yonetici-gizli-parola-91";
    private const string NewEditorEmail = "editor-gizlilik@example.test";
    private const string NewEditorPassword = "editor-gizli-parola-92";
    private const string UnknownEmail = "yok-gizlilik@example.test";
    private const string WrongPassword = "yanlis-gizli-parola-93";
    private const string WeakPassword = "kisa-p1";
    private const string RoleEmail = "rol-gizlilik@example.test";
    private const string RolePassword = "rol-gizli-parola-94";

    // Istek govdelerindeki ayirt edici metinler: govde gunluge yazilmaz.
    private const string ProposedMarker = "GIZLI-METIN-ISARETI-5521";
    private const string ReasonMarker = "GIZLI-GEREKCE-ISARETI-5522";
    private const string RejectMarker = "GIZLI-RED-ISARETI-5523";

    private const string SourceSlug = "test-gizlilik";
    private const string UnitAnchor = "rn:sozler:soz-10:p1";

    private static string CookieValue(HttpResponseMessage login)
    {
        Assert.True(login.Headers.TryGetValues("Set-Cookie", out IEnumerable<string>? values), "Set-Cookie yok");
        string header = values!.Single(v => v.StartsWith("mutalaa.editor=", StringComparison.Ordinal));
        string value = header["mutalaa.editor=".Length..].Split(';')[0];
        Assert.True(value.Length > 40, "cerez degeri beklenenden kisa");
        return value;
    }

    private async Task<(HttpClient Client, string Cookie)> LoginAsync(string email, string password, string? role)
    {
        if (role is not null)
        {
            await Factory.AddUserAsync(email, password, role);
        }

        HttpClient client = Factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, email, password, Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        return (client, CookieValue(login));
    }

    [Fact]
    public async Task No_secret_reaches_the_log_through_login_user_creation_correction_and_decision_flows()
    {
        await Db.ExecuteAsync("TRUNCATE icerik.review, icerik.unit, icerik.source CASCADE", Ct);
        await SeedSourceAsync(SourceSlug, SourceKind.Risale);
        await SeedUnitAsync(SourceSlug, UnitAnchor, "Deneme paragrafı 1");

        // Giris: basarili ve basarisiz (yanlis parola, olmayan kullanici).
        (HttpClient admin, string adminCookie) = await LoginAsync(AdminEmail, AdminPassword, Roles.Admin);
        using HttpClient adminClient = admin;
        using HttpClient anonymous = Factory.CreateApiClient();
        (await ApiFactory.LoginAsync(anonymous, AdminEmail, WrongPassword, Ct)).Dispose();
        (await ApiFactory.LoginAsync(anonymous, UnknownEmail, WrongPassword, Ct)).Dispose();

        // Kullanici olusturma: basarili, yinelenen (farkli harf buyuklugu), zayif parola, bilinmeyen rol.
        using (HttpResponseMessage created = await admin.PostAsJsonAsync(
            "/api/v1/users", new { email = NewEditorEmail, parola = NewEditorPassword, roller = new[] { "editor" } }, Ct))
        {
            Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        }

        using (HttpResponseMessage duplicate = await admin.PostAsJsonAsync(
            "/api/v1/users", new { email = NewEditorEmail.ToUpperInvariant(), parola = NewEditorPassword, roller = new[] { "editor" } }, Ct))
        {
            Assert.Equal(HttpStatusCode.Conflict, duplicate.StatusCode);
        }

        using (HttpResponseMessage weak = await admin.PostAsJsonAsync(
            "/api/v1/users", new { email = RoleEmail, parola = WeakPassword, roller = new[] { "editor" } }, Ct))
        {
            Assert.Equal(HttpStatusCode.BadRequest, weak.StatusCode);
        }

        using (HttpResponseMessage unknownRole = await admin.PostAsJsonAsync(
            "/api/v1/users", new { email = RoleEmail, parola = RolePassword, roller = new[] { "bilinmeyen" } }, Ct))
        {
            Assert.Equal(HttpStatusCode.BadRequest, unknownRole.StatusCode);
        }

        // Yeni editor: yanlis parola denemeleri ve basarili giris; sonra duzeltme onerisi.
        (await ApiFactory.LoginAsync(anonymous, NewEditorEmail, WrongPassword, Ct)).Dispose();
        (HttpClient editor, string editorCookie) = await LoginAsync(NewEditorEmail, NewEditorPassword, role: null);
        using HttpClient editorClient = editor;

        string correctionPath = "/api/v1/units/" + Uri.EscapeDataString(UnitAnchor) + "/corrections";
        long reviewId;
        using (HttpResponseMessage proposal = await editor.PostAsJsonAsync(
            correctionPath, new { metin = "Deneme paragrafı " + ProposedMarker, gerekce = ReasonMarker }, Ct))
        {
            Assert.Equal(HttpStatusCode.Created, proposal.StatusCode);
            reviewId = (await ReadAsync(proposal)).GetProperty("id").GetInt64();
        }

        // Duzeltme hatalari: acik inceleme varken ikinci oneri (409), bos gerekce (400), olmayan birim (404).
        using (HttpResponseMessage second = await editor.PostAsJsonAsync(
            correctionPath, new { metin = "Deneme paragrafı " + ProposedMarker + "-2", gerekce = ReasonMarker }, Ct))
        {
            Assert.Equal(HttpStatusCode.Conflict, second.StatusCode);
        }

        using (HttpResponseMessage empty = await editor.PostAsJsonAsync(correctionPath, new { metin = ProposedMarker, gerekce = " " }, Ct))
        {
            Assert.Equal(HttpStatusCode.BadRequest, empty.StatusCode);
        }

        using (HttpResponseMessage missing = await editor.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString("rn:sozler:soz-10:p99") + "/corrections",
            new { metin = ProposedMarker, gerekce = ReasonMarker },
            Ct))
        {
            Assert.Equal(HttpStatusCode.NotFound, missing.StatusCode);
        }

        // Karar: ETag yok (428), eski ETag (412), dogru ETag ile ret (200), ayni karar yine (409), toplu karar hatalari (404, 400).
        string decisionPath = $"/api/v1/reviews/{reviewId}/decision";
        using (HttpResponseMessage noEtag = await admin.PostAsJsonAsync(decisionPath, new { karar = "reddedildi", gerekce = RejectMarker }, Ct))
        {
            Assert.Equal(HttpStatusCode.PreconditionRequired, noEtag.StatusCode);
        }

        string etag;
        using (HttpResponseMessage detail = await admin.GetAsync($"/api/v1/reviews/{reviewId}", Ct))
        {
            Assert.Equal(HttpStatusCode.OK, detail.StatusCode);
            etag = detail.Headers.ETag!.Tag;
        }

        Task<HttpResponseMessage> DecideAsync(string ifMatch)
        {
            HttpRequestMessage request = new(HttpMethod.Post, decisionPath)
            {
                Content = JsonContent.Create(new { karar = "reddedildi", gerekce = RejectMarker }),
            };
            request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
            return admin.SendAsync(request, Ct);
        }

        using (HttpResponseMessage stale = await DecideAsync("\"1\""))
        {
            Assert.Equal(HttpStatusCode.PreconditionFailed, stale.StatusCode);
        }

        string newEtag;
        using (HttpResponseMessage decided = await DecideAsync(etag))
        {
            Assert.Equal(HttpStatusCode.OK, decided.StatusCode);
            newEtag = decided.Headers.ETag!.Tag;
        }

        using (HttpResponseMessage again = await DecideAsync(newEtag))
        {
            Assert.Equal(HttpStatusCode.Conflict, again.StatusCode);
        }

        using (HttpResponseMessage bulkMissing = await admin.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = 987654321L, xmin = 1U, karar = "reddedildi", gerekce = RejectMarker } } },
            Ct))
        {
            Assert.Equal(HttpStatusCode.NotFound, bulkMissing.StatusCode);
        }

        using (HttpResponseMessage bulkInvalid = await admin.PostAsJsonAsync(
            "/api/v1/reviews/decisions",
            new { kararlar = new[] { new { id = reviewId, xmin = 1U, karar = "yanlis", gerekce = RejectMarker } } },
            Ct))
        {
            Assert.Equal(HttpStatusCode.BadRequest, bulkInvalid.StatusCode);
        }

        // Yakalama calisiyor mu: istek satirlari yol ve durumla yazilmis olmali (bos denetimi onler).
        string log = Factory.Logs.Text;
        Assert.Contains("/api/v1/auth/login", log, StringComparison.Ordinal);
        Assert.Contains("/corrections", log, StringComparison.Ordinal);
        Assert.Contains("/decision", log, StringComparison.Ordinal);
        Assert.Contains("responded 428", log, StringComparison.Ordinal);
        Assert.Contains("responded 412", log, StringComparison.Ordinal);

        string[] secrets =
        [
            AdminEmail, NewEditorEmail, UnknownEmail, RoleEmail,
            AdminPassword, NewEditorPassword, WrongPassword, WeakPassword, RolePassword,
            adminCookie, adminCookie[..32], editorCookie, editorCookie[..32],
            ProposedMarker, ReasonMarker, RejectMarker,
        ];
        string[] leaked = [.. secrets.Where(s => log.Contains(s, StringComparison.OrdinalIgnoreCase))];
        Assert.True(leaked.Length == 0, "Gunlukte gizli deger var: " + string.Join(" | ", leaked.Select(s => s.Length > 12 ? s[..12] + "..." : s)));
        Assert.DoesNotContain("mutalaa.editor=", log, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_same_flows_leave_no_secret_in_the_log_under_the_tr_TR_culture()
    {
        await Db.ExecuteAsync("TRUNCATE icerik.review, icerik.unit, icerik.source CASCADE", Ct);
        await SeedSourceAsync(SourceSlug, SourceKind.Risale);
        await SeedUnitAsync(SourceSlug, UnitAnchor, "Deneme paragrafı 1");
        const string dottedEmail = "ISIK.Ilhan-gizlilik@example.test";
        const string dottedPassword = "isik-ilhan-gizli-parola-95";

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            (HttpClient client, string cookie) = await LoginAsync(dottedEmail, dottedPassword, Roles.Editor);
            using HttpClient disposable = client;
            using HttpResponseMessage proposal = await client.PostAsJsonAsync(
                "/api/v1/units/" + Uri.EscapeDataString(UnitAnchor) + "/corrections",
                new { metin = "Deneme paragrafı " + ProposedMarker, gerekce = ReasonMarker },
                Ct);
            Assert.Equal(HttpStatusCode.Created, proposal.StatusCode);

            string log = Factory.Logs.Text;
            Assert.Contains("/corrections", log, StringComparison.Ordinal);
            foreach (string secret in new[] { dottedEmail, "isik.ilhan-gizlilik@example.test", dottedPassword, cookie, ProposedMarker, ReasonMarker })
            {
                Assert.DoesNotContain(secret, log, StringComparison.OrdinalIgnoreCase);
            }
        });
    }
}
