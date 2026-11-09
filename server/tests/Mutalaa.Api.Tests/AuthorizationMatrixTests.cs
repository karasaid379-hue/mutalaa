using System.Globalization;
using System.Net;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http.Metadata;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>Bir ucun yetki sinifi: kimlik dogrulamasiz, editor (editor ya da admin) ya da yalniz admin.</summary>
internal enum Access
{
    Anonymous,
    Editor,
    Admin,
}

/// <summary>
/// Beklenen tablonun bir satiri. <see cref="Pattern"/> yol sablonudur (<c>RoutePattern.RawText</c>); <see cref="Path"/> ayni ucun
/// ornek istek yoludur (parametreler doldurulmus). <see cref="Body"/> yetkinin gectigini gostermeye yeter, bilerek gecersizdir
/// (400/404 yetki gectigini kanitlar) ve hicbir satir acmaz ya da degistirmez.
/// </summary>
internal sealed record ExpectedEndpoint(string Method, string Pattern, Access Access, string Path, string? Body = null, bool EndsSession = false)
{
    public string Key => Method + " " + Pattern;
}

/// <summary>
/// API uc tablosu (Backend API 6): kodda sabit. Yeni uc eklemek bu tabloya satir eklemeyi gerektirir; tabloda olmayan uc ya da
/// bulunmayan satir <see cref="AuthorizationMatrixTests"/> testini kirar. Yetki degisikligi de burada gorunur olur.
/// </summary>
internal static class ExpectedEndpoints
{
    // Gecersiz ama yetkiyi gecen govdeler: dogrulama 400 verir, yan etki yoktur.
    private const string EmptyJson = "{}";
    private const string InvalidDerleme = """{"derleme":"yok"}""";
    private const string UnknownRole = """{"roller":["bilinmeyen"]}""";
    private const string CreateUserWithUnknownRole = """{"email":"matris@example.test","parola":"matris-parolasi-123456","roller":["bilinmeyen"]}""";

    public static readonly IReadOnlyList<ExpectedEndpoint> All =
    [
        // Anonim: giris ve saglik.
        new("POST", "/api/v1/auth/login", Access.Anonymous, "/api/v1/auth/login", EmptyJson),
        new("GET", "/health/live", Access.Anonymous, "/health/live"),
        new("HEAD", "/health/live", Access.Anonymous, "/health/live"),
        new("GET", "/health/ready", Access.Anonymous, "/health/ready"),
        new("HEAD", "/health/ready", Access.Anonymous, "/health/ready"),

        // Editor (editor ya da admin).
        new("POST", "/api/v1/auth/logout", Access.Editor, "/api/v1/auth/logout", EndsSession: true),
        new("GET", "/api/v1/auth/me", Access.Editor, "/api/v1/auth/me"),
        new("GET", "/api/v1/sources", Access.Editor, "/api/v1/sources"),
        new("GET", "/api/v1/sources/{slug}", Access.Editor, "/api/v1/sources/test-yok"),
        new("GET", "/api/v1/units", Access.Editor, "/api/v1/units"),
        new("GET", "/api/v1/units/{anchor}", Access.Editor, "/api/v1/units/q:1:1"),
        new("POST", "/api/v1/units/{anchor}/corrections", Access.Editor, "/api/v1/units/q:1:1/corrections", EmptyJson),
        new("GET", "/api/v1/scans/{baski}/{sayfa}", Access.Editor, "/api/v1/scans/test-baski/c01-s0001"),
        new("GET", "/api/v1/reviews", Access.Editor, "/api/v1/reviews"),
        new("GET", "/api/v1/reviews/stats", Access.Editor, "/api/v1/reviews/stats"),
        new("GET", "/api/v1/reviews/{id:long}", Access.Editor, "/api/v1/reviews/1"),
        new("POST", "/api/v1/reviews/{id:long}/decision", Access.Editor, "/api/v1/reviews/1/decision", """{"karar":"yanlis"}"""),
        new("POST", "/api/v1/reviews/decisions", Access.Editor, "/api/v1/reviews/decisions", """{"kararlar":[]}"""),
        new("GET", "/api/v1/releases", Access.Editor, "/api/v1/releases"),
        new("GET", "/api/v1/releases/{id:int}", Access.Editor, "/api/v1/releases/1"),

        // Admin.
        new("GET", "/api/v1/users", Access.Admin, "/api/v1/users"),
        new("POST", "/api/v1/users", Access.Admin, "/api/v1/users", CreateUserWithUnknownRole),
        new("PUT", "/api/v1/users/{id}/roles", Access.Admin, "/api/v1/users/yok/roles", UnknownRole),
        new("POST", "/api/v1/releases", Access.Admin, "/api/v1/releases", InvalidDerleme),
        new("POST", "/api/v1/releases/preview", Access.Admin, "/api/v1/releases/preview", InvalidDerleme),
        new("POST", "/api/v1/releases/{id:int}/promote", Access.Admin, "/api/v1/releases/1/promote"),
        new("POST", "/api/v1/releases/{id:int}/rollback", Access.Admin, "/api/v1/releases/1/rollback"),
    ];

    public static bool IsHealth(ExpectedEndpoint row) => row.Pattern.StartsWith("/health/", StringComparison.Ordinal);
}

/// <summary>
/// Yetki matrisi: calisan uygulamanin butun uclari (<c>EndpointDataSource</c>) kodda sabit tabloyla birebir ayni olmali; her ucun
/// ust verisi (<c>IAuthorizeData</c>, <c>IAllowAnonymous</c>, politika adi) ve canli davranisi (anonim, editor, admin) tabloya uymali.
/// Gelistirme uclari (OpenAPI, Scalar) Testing ortaminda eslenmez; eslenirse tablo kirilir ve bu dogrudur (Docker'li).
/// </summary>
public class AuthorizationMatrixTests(EditorialDatabase<AuthorizationMatrixTests> fixture)
    : ApiTestBase<AuthorizationMatrixTests>(fixture), IClassFixture<EditorialDatabase<AuthorizationMatrixTests>>
{
    // Yetkinin gectigini gosteren durumlar: bos govdeler 400/422, olmayan kayitlar 404, on kosullar 412/428, cakisma 409.
    private static readonly HashSet<int> Passed = [200, 201, 202, 204, 400, 404, 409, 412, 422, 428];

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private sealed record Found(string Method, string Pattern, RouteEndpoint Endpoint)
    {
        public string Key => Method + " " + Pattern;
    }

    /// <summary>Uc kumesi: anahtar (HTTP yontemi ya da "*", sablonun ham metni).</summary>
    private static List<Found> Discover(IServiceProvider services)
    {
        EndpointDataSource source = services.GetRequiredService<EndpointDataSource>();
        List<Found> found = [];
        foreach (RouteEndpoint endpoint in source.Endpoints.OfType<RouteEndpoint>())
        {
            // MapGroup birlestirmesi bos sablonlu uclara sondaki "/" ekler ("/api/v1/users/"); okunur tablo icin atilir.
            string pattern = endpoint.RoutePattern.RawText ?? string.Empty;
            if (pattern.Length > 1 && pattern.EndsWith('/'))
            {
                pattern = pattern[..^1];
            }

            IReadOnlyList<string> methods = endpoint.Metadata.GetMetadata<IHttpMethodMetadata>()?.HttpMethods ?? ["*"];
            foreach (string method in methods.Count == 0 ? ["*"] : methods)
            {
                found.Add(new Found(method.ToUpperInvariant(), pattern, endpoint));
            }
        }

        return found;
    }

    private static HttpRequestMessage Build(ExpectedEndpoint row)
    {
        HttpRequestMessage request = new(new HttpMethod(row.Method), row.Path);
        if (row.Body is not null)
        {
            request.Content = new StringContent(row.Body, Encoding.UTF8, "application/json");
        }

        return request;
    }

    private async Task<string> SnapshotAsync()
    {
        string[] tables = ["kimlik.users", "kimlik.user_roles", "icerik.release", "icerik.review", "icerik.unit", "icerik.source"];
        List<string> counts = [];
        foreach (string table in tables)
        {
            long count = await Db.ScalarAsync<long>("SELECT count(*) FROM " + table, Ct);
            counts.Add(string.Create(CultureInfo.InvariantCulture, $"{table}={count}"));
        }

        return string.Join(", ", counts);
    }

    [Fact]
    public void The_expected_table_has_no_duplicate_rows()
    {
        string[] duplicates = [.. ExpectedEndpoints.All.GroupBy(r => r.Key, StringComparer.Ordinal).Where(g => g.Count() > 1).Select(g => g.Key)];

        Assert.True(duplicates.Length == 0, "Tabloda yinelenen satir: " + string.Join(", ", duplicates));
    }

    [Fact]
    public void The_endpoint_set_of_the_running_app_equals_the_expected_table_exactly()
    {
        List<Found> found = Discover(Factory.Services);

        string[] foundKeys = [.. found.Select(f => f.Key)];
        string[] expectedKeys = [.. ExpectedEndpoints.All.Select(r => r.Key)];
        string[] extra = [.. foundKeys.Except(expectedKeys, StringComparer.Ordinal).Order(StringComparer.Ordinal)];
        string[] missing = [.. expectedKeys.Except(foundKeys, StringComparer.Ordinal).Order(StringComparer.Ordinal)];
        string[] duplicated = [.. foundKeys.GroupBy(k => k, StringComparer.Ordinal).Where(g => g.Count() > 1).Select(g => g.Key)];

        Assert.True(
            extra.Length == 0 && missing.Length == 0 && duplicated.Length == 0,
            $"Uc kumesi tabloyla ayni degil.{Environment.NewLine}"
            + $"Tabloda OLMAYAN (fazla) uclar: [{string.Join("; ", extra)}]{Environment.NewLine}"
            + $"Calisan uygulamada BULUNMAYAN (eksik) satirlar: [{string.Join("; ", missing)}]{Environment.NewLine}"
            + $"Ayni anahtarla birden cok ucu olanlar: [{string.Join("; ", duplicated)}]");
    }

    [Fact]
    public void Every_endpoint_carries_the_expected_authorization_metadata()
    {
        // Anonim: IAllowAnonymous var ve Admin politikasi yok (giris ucu editor grubundan Editor politikasini devralir ama
        // AllowAnonymous onu etkisiz kilar). Editor: yalniz "Editor". Admin: "Editor" (grup) ve "Admin" birlikte aranir.
        List<string> failures = [];
        foreach (Found item in Discover(Factory.Services))
        {
            ExpectedEndpoint? row = ExpectedEndpoints.All.FirstOrDefault(r => string.Equals(r.Key, item.Key, StringComparison.Ordinal));
            if (row is null)
            {
                continue; // Fazla uc: kume testi bildirir.
            }

            IReadOnlyList<IAuthorizeData> data = item.Endpoint.Metadata.GetOrderedMetadata<IAuthorizeData>();
            bool anonymous = item.Endpoint.Metadata.GetMetadata<IAllowAnonymous>() is not null;
            string[] policies = [.. data.Select(d => d.Policy ?? "(politikasiz)").Order(StringComparer.Ordinal)];

            if (data.Any(d => !string.IsNullOrEmpty(d.Roles) || !string.IsNullOrEmpty(d.AuthenticationSchemes)))
            {
                failures.Add($"{item.Key}: rol ya da sema ile ayrica kisitlanmis (yalniz politika adi kullanilir)");
            }

            switch (row.Access)
            {
                case Access.Anonymous:
                    if (!anonymous)
                    {
                        failures.Add($"{item.Key}: anonim olmali ama IAllowAnonymous yok");
                    }

                    if (policies.Contains("Admin", StringComparer.Ordinal))
                    {
                        failures.Add($"{item.Key}: anonim ucta Admin politikasi var");
                    }

                    break;
                case Access.Editor:
                    AssertPolicies(item.Key, anonymous, policies, ["Editor"], failures);
                    break;
                case Access.Admin:
                    AssertPolicies(item.Key, anonymous, policies, ["Admin", "Editor"], failures);
                    break;
            }
        }

        ProblemChecks.AssertNone(failures, "Yetki ust verisi");
    }

    private static void AssertPolicies(string key, bool anonymous, string[] actual, string[] expected, List<string> failures)
    {
        if (anonymous)
        {
            failures.Add($"{key}: IAllowAnonymous var, yetki isteyen uc anonim acilmis");
        }

        if (!actual.SequenceEqual(expected, StringComparer.Ordinal))
        {
            failures.Add($"{key}: politikalar [{string.Join(", ", actual)}], beklenen [{string.Join(", ", expected)}]");
        }
    }

    [Fact]
    public async Task Anonymous_calls_get_401_problems_without_Location_except_the_anonymous_endpoints()
    {
        using HttpClient anonymous = Factory.CreateApiClient();
        List<string> failures = [];

        foreach (ExpectedEndpoint row in ExpectedEndpoints.All)
        {
            using HttpRequestMessage request = Build(row);
            using HttpResponseMessage response = await anonymous.SendAsync(request, Ct);

            if (row.Access == Access.Anonymous)
            {
                int expected = ExpectedEndpoints.IsHealth(row) ? 200 : 400;
                if ((int)response.StatusCode != expected)
                {
                    failures.Add($"{row.Key}: anonim ucta durum {(int)response.StatusCode}, beklenen {expected}");
                }

                continue;
            }

            foreach (string deviation in await ProblemChecks.DeviationsAsync(response, HttpStatusCode.Unauthorized, "oturum-acilamadi", Ct))
            {
                failures.Add($"{row.Key}: {deviation}");
            }
        }

        ProblemChecks.AssertNone(failures, "Anonim cagrilar");
    }

    [Fact]
    public async Task Editor_calls_pass_on_editor_endpoints_and_get_403_problems_without_Location_on_admin_endpoints()
    {
        using HttpClient editor = await ReleaseTestKit.EditorAsync(Factory, Ct);
        string before = await SnapshotAsync();
        List<string> failures = [];

        foreach (ExpectedEndpoint row in ExpectedEndpoints.All)
        {
            using HttpClient? fresh = row.EndsSession ? await ReleaseTestKit.EditorAsync(Factory, Ct) : null;
            HttpClient client = fresh ?? editor;
            using HttpRequestMessage request = Build(row);
            using HttpResponseMessage response = await client.SendAsync(request, Ct);

            if (row.Access == Access.Admin)
            {
                foreach (string deviation in await ProblemChecks.DeviationsAsync(response, HttpStatusCode.Forbidden, "yetki-yok", Ct))
                {
                    failures.Add($"{row.Key}: {deviation}");
                }
            }
            else if (!Passed.Contains((int)response.StatusCode))
            {
                failures.Add($"{row.Key}: editor icin durum {(int)response.StatusCode}, yetki gecmeliydi {{{string.Join(",", Passed.Order())}}}");
            }
        }

        ProblemChecks.AssertNone(failures, "Editor cagrilari");

        // Gecersiz govdeler yan etki birakmadi.
        Assert.Equal(before, await SnapshotAsync());
    }

    [Fact]
    public async Task Admin_calls_pass_on_every_endpoint_and_leave_no_side_effects()
    {
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);
        string before = await SnapshotAsync();
        List<string> failures = [];

        foreach (ExpectedEndpoint row in ExpectedEndpoints.All)
        {
            using HttpClient? fresh = row.EndsSession ? await ReleaseTestKit.AdminAsync(Factory, Ct) : null;
            HttpClient client = fresh ?? admin;
            using HttpRequestMessage request = Build(row);
            using HttpResponseMessage response = await client.SendAsync(request, Ct);

            if (!Passed.Contains((int)response.StatusCode))
            {
                failures.Add($"{row.Key}: admin icin durum {(int)response.StatusCode}, yetki gecmeliydi {{{string.Join(",", Passed.Order())}}}");
            }
        }

        ProblemChecks.AssertNone(failures, "Admin cagrilari");
        Assert.Equal(before, await SnapshotAsync());
    }

    [Fact]
    public async Task There_is_no_fallback_policy_and_unknown_paths_are_anonymous_404_problems_not_401()
    {
        IAuthorizationPolicyProvider provider = Factory.Services.GetRequiredService<IAuthorizationPolicyProvider>();
        Assert.Null(await provider.GetFallbackPolicyAsync());
        Assert.Null(Factory.Services.GetRequiredService<IOptions<AuthorizationOptions>>().Value.FallbackPolicy);

        using HttpClient anonymous = Factory.CreateApiClient();
        List<string> failures = [];
        string[] paths = ["/", "/yok", "/api/v1", "/api/v1/auth", "/api/v1/yok", "/api/v1/users/x/yok", "/openapi/v1.json", "/scalar"];
        foreach (string path in paths)
        {
            using HttpResponseMessage response = await anonymous.GetAsync(path, Ct);
            foreach (string deviation in await ProblemChecks.DeviationsAsync(response, HttpStatusCode.NotFound, "bulunamadi", Ct))
            {
                failures.Add($"GET {path}: {deviation}");
            }
        }

        ProblemChecks.AssertNone(failures, "Bilinmeyen yollar");
    }

    [Fact]
    public async Task Writes_to_the_read_only_source_endpoints_are_405_problems_with_Allow_GET_for_anonymous_editor_and_admin_alike()
    {
        // Neden anonim istek 401 degil 405 alir: yol sablonu eslesir ama HTTP yontemi eslesmez; yonlendirme (UseRouting, yetkiden
        // ONCE calisir) bu durumda yetki ust verisi tasimayan sentetik bir "405" ucu secer. Yetki ara katmani degerlendirecek bir
        // IAuthorizeData bulamaz, istek dogrudan 405 olur. Bu bir sizinti degildir: bir yolun hangi yontemleri destekledigi
        // zaten herkese acik OpenAPI sozlesmesindedir; yetki gerektiren veri (kaynak kayitlari) donmez.
        // 405 ucu EndpointDataSource'ta gorunmez; bu yuzden matristen ayri sinanir.
        using HttpClient anonymous = Factory.CreateApiClient();
        using HttpClient editor = await ReleaseTestKit.EditorAsync(Factory, Ct);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);
        string before = await SnapshotAsync();
        List<string> failures = [];

        string[] paths = ["/api/v1/sources", "/api/v1/sources/test-a-risale"];
        string[] methods = ["POST", "PUT", "PATCH", "DELETE"];
        (string Name, HttpClient Client)[] callers = [("anonim", anonymous), ("editor", editor), ("admin", admin)];

        foreach (string path in paths)
        {
            foreach (string method in methods)
            {
                foreach ((string name, HttpClient client) in callers)
                {
                    using HttpRequestMessage request = new(new HttpMethod(method), path);
                    if (method is "POST" or "PUT" or "PATCH")
                    {
                        request.Content = new StringContent("{}", Encoding.UTF8, "application/json");
                    }

                    using HttpResponseMessage response = await client.SendAsync(request, Ct);
                    foreach (string deviation in await ProblemChecks.DeviationsAsync(response, HttpStatusCode.MethodNotAllowed, "yontem-desteklenmiyor", Ct))
                    {
                        failures.Add($"{name} {method} {path}: {deviation}");
                    }

                    if (!response.Content.Headers.Allow.SequenceEqual(["GET"], StringComparer.Ordinal))
                    {
                        failures.Add($"{name} {method} {path}: Allow '{string.Join(",", response.Content.Headers.Allow)}', beklenen 'GET'");
                    }
                }
            }
        }

        ProblemChecks.AssertNone(failures, "Kaynak yazma yontemleri");
        Assert.Equal(before, await SnapshotAsync());
    }

    [Fact]
    public async Task With_the_editor_feature_off_no_api_endpoint_is_mapped_and_all_api_paths_are_404_but_health_stays_200()
    {
        ApiFactory off = CreateFactory(settings: new Dictionary<string, string?> { ["Mutalaa:Features:Editor"] = "false" });

        string[] mapped = [.. Discover(off.Services).Select(f => f.Key).Order(StringComparer.Ordinal)];
        string[] healthKeys = [.. ExpectedEndpoints.All.Where(ExpectedEndpoints.IsHealth).Select(r => r.Key).Order(StringComparer.Ordinal)];
        Assert.True(
            mapped.SequenceEqual(healthKeys, StringComparer.Ordinal),
            $"Ozellik kapaliyken yalniz saglik uclari eslenmeliydi. Eslenen: [{string.Join("; ", mapped)}]");

        // Canli: yetkisiz istemci bile 401 degil 404 gorur (uc hic yok); saglik 200.
        using HttpClient client = off.CreateApiClient();
        List<string> failures = [];
        foreach (ExpectedEndpoint row in ExpectedEndpoints.All)
        {
            using HttpRequestMessage request = Build(row);
            using HttpResponseMessage response = await client.SendAsync(request, Ct);
            if (ExpectedEndpoints.IsHealth(row))
            {
                if (response.StatusCode != HttpStatusCode.OK)
                {
                    failures.Add($"{row.Key}: durum {(int)response.StatusCode}, beklenen 200");
                }

                continue;
            }

            foreach (string deviation in await ProblemChecks.DeviationsAsync(response, HttpStatusCode.NotFound, "bulunamadi", Ct))
            {
                failures.Add($"{row.Key}: {deviation}");
            }
        }

        ProblemChecks.AssertNone(failures, "Editor ozelligi kapali");
    }
}
