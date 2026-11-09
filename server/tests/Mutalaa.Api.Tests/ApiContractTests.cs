using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>
/// API sozlesmesi: yanit alan adlari snake_case, depodaki OpenAPI belgesi calisan uygulamayla ve uc tablosuyla ayni, her hata turu
/// ayni ProblemDetails bicimini tasir (Docker'li; sentetik veri).
/// </summary>
public class ApiContractTests(EditorialDatabase<ApiContractTests> fixture)
    : EditorApiTestBase<ApiContractTests>(fixture), IClassFixture<EditorialDatabase<ApiContractTests>>
{
    private const string OpenApiPath = "server/Mutalaa.Api/openapi/v1.json";
    private const string SourceSlug = "test-a-risale";
    private const string UnitAnchor = "rn:sozler:soz-10:p1";

    // Ham JSON (jsonb) icerikleri: adin kendisi snake_case olmali, ici istemci verisidir ve gezilmez.
    private static readonly HashSet<string> RawJsonNames = new(StringComparer.Ordinal)
    {
        "baski_bilgisi", "marks", "attrs", "provenance", "successors", "onceki", "onerilen", "duzenlenen", "yz_kaydi", "kapi_raporu",
        "ozetler", "manifest",
    };

    private static readonly Regex SnakeCase = new("^[a-z][a-z0-9_]*$", RegexOptions.CultureInvariant);

    private static readonly Regex RouteParameter = new(@"\{([A-Za-z0-9_]+)(:[^}]*)?\}", RegexOptions.CultureInvariant);

    private static readonly string[] OperationMethods = ["get", "put", "post", "delete", "options", "head", "patch", "trace"];

    /// <summary>Ozyinelemeli ad denetimi; denetlenen ad sayisini dondurur (bos denetimi yakalamak icin).</summary>
    private static int CollectBadNames(JsonElement element, string path, List<string> bad)
    {
        int checkedNames = 0;
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                foreach (JsonProperty property in element.EnumerateObject())
                {
                    checkedNames++;
                    string here = path + "." + property.Name;
                    if (!SnakeCase.IsMatch(property.Name))
                    {
                        bad.Add(here);
                    }

                    if (!RawJsonNames.Contains(property.Name))
                    {
                        checkedNames += CollectBadNames(property.Value, here, bad);
                    }
                }

                break;
            case JsonValueKind.Array:
                int index = 0;
                foreach (JsonElement item in element.EnumerateArray())
                {
                    checkedNames += CollectBadNames(item, path + "[" + index.ToString(CultureInfo.InvariantCulture) + "]", bad);
                    index++;
                }

                break;
        }

        return checkedNames;
    }

    private static string Join(IEnumerable<string> values) => string.Join(", ", values);

    private async Task<HttpClient> EditorBAsync()
    {
        await Factory.AddUserAsync("editor-b@example.test", "editor-b-parolasi-123", Roles.Editor);
        HttpClient client = Factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, "editor-b@example.test", "editor-b-parolasi-123", Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    // --- snake_case ---

    [Fact]
    public async Task Every_property_name_in_the_source_unit_review_release_and_decision_responses_is_snake_case()
    {
        using HttpClient editor = await LoginEditorAsync();
        await Db.ExecuteAsync("TRUNCATE icerik.release", Ct);
        await SeedSourceAsync(SourceSlug, SourceKind.Risale, s => s.BaskiBilgisi = """{"YayinEvi":"Deneme","IcNesne":{"BirAnahtar":1}}""");
        await SeedUnitAsync(SourceSlug, UnitAnchor, "Deneme paragrafı 1", configure: u =>
        {
            u.Marks = """[{"Tur":"deneme"}]""";
            u.Attrs = """{"BirAnahtar":1}""";
            u.Provenance = """{"KaynakAdi":"deneme"}""";
        });
        _ = await ReleaseTestKit.InsertReleaseAsync(
            Db,
            new ReleaseSeed(
                ReleaseTestKit.MonthVersion(1),
                Manifest: """{"ManifestAnahtari":{"IcAnahtar":1}}""",
                KapiRaporu: """{"KapiAnahtari":1}""",
                Ozetler: """{"OzetAnahtari":1}""",
                Notlar: "Deneme notu"),
            Ct);

        // Bir inceleme kaydi: editor duzeltme onerir (Onceki/Onerilen jsonb dolu).
        using HttpResponseMessage proposal = await editor.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(UnitAnchor) + "/corrections",
            new { metin = "Deneme paragrafı 2", gerekce = "Deneme gerekcesi" },
            Ct);
        Assert.Equal(HttpStatusCode.Created, proposal.StatusCode);
        long reviewId = (await ReadAsync(proposal)).GetProperty("id").GetInt64();
        int releaseId = await Db.ScalarAsync<int>("SELECT id FROM icerik.release LIMIT 1", Ct);

        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);
        using HttpClient editorB = await EditorBAsync();

        // Karar yaniti icin guncel ETag.
        using HttpResponseMessage reviewDetail = await editor.GetAsync($"/api/v1/reviews/{reviewId}", Ct);
        string etag = reviewDetail.Headers.ETag!.Tag;
        using HttpRequestMessage decision = new(HttpMethod.Post, $"/api/v1/reviews/{reviewId}/decision")
        {
            Content = JsonContent.Create(new { karar = "reddedildi", gerekce = "Deneme ret gerekcesi" }),
        };
        decision.Headers.TryAddWithoutValidation("If-Match", etag);
        using HttpResponseMessage decided = await editorB.SendAsync(decision, Ct);
        Assert.Equal(HttpStatusCode.OK, decided.StatusCode);

        (string Name, HttpResponseMessage Response)[] responses =
        [
            ("proposal 201", proposal),
            ("decision 200", decided),
            ("GET /sources", await editor.GetAsync("/api/v1/sources", Ct)),
            ("GET /sources/{slug}", await editor.GetAsync("/api/v1/sources/" + SourceSlug, Ct)),
            ("GET /units", await editor.GetAsync("/api/v1/units?source=" + SourceSlug, Ct)),
            ("GET /units/{anchor}", await editor.GetAsync("/api/v1/units/" + Uri.EscapeDataString(UnitAnchor), Ct)),
            ("GET /reviews", await editor.GetAsync("/api/v1/reviews?durum=reddedildi", Ct)),
            ("GET /reviews/stats", await editor.GetAsync("/api/v1/reviews/stats", Ct)),
            ("GET /reviews/{id}", reviewDetail),
            ("GET /releases", await editor.GetAsync("/api/v1/releases", Ct)),
            ("GET /releases/{id}", await editor.GetAsync($"/api/v1/releases/{releaseId}", Ct)),
            ("GET /auth/me", await editor.GetAsync("/api/v1/auth/me", Ct)),
            ("GET /users", await admin.GetAsync("/api/v1/users", Ct)),
        ];

        List<string> bad = [];
        foreach ((string name, HttpResponseMessage response) in responses)
        {
            Assert.True(response.IsSuccessStatusCode, $"{name}: durum {(int)response.StatusCode}");
            JsonElement body = await ReadAsync(response);
            int before = bad.Count;
            int checkedNames = CollectBadNames(body, name, bad);
            Assert.True(checkedNames >= 2, $"{name}: yalniz {checkedNames} alan adi denetlendi (bos yanit?)");
            Assert.True(bad.Count == before, $"{name}: snake_case olmayan alanlar: {Join(bad.Skip(before))}");
            response.Dispose();
        }

        // Ham JSON icerigi yeniden adlandirilmaz: istemci verisi oldugu gibi doner.
        using HttpResponseMessage unitDetail = await editor.GetAsync("/api/v1/units/" + Uri.EscapeDataString(UnitAnchor), Ct);
        JsonElement unit = await ReadAsync(unitDetail);
        Assert.Equal(1, unit.GetProperty("attrs").GetProperty("BirAnahtar").GetInt32());
    }

    // --- OpenAPI ---

    /// <summary>"YONTEM yol operationId [durumlar]" satirlari; belge surumlerini karsilastirmak icin.</summary>
    private static SortedSet<string> Operations(JsonElement document)
    {
        SortedSet<string> operations = new(StringComparer.Ordinal);
        foreach (JsonProperty path in document.GetProperty("paths").EnumerateObject())
        {
            foreach (JsonProperty operation in path.Value.EnumerateObject())
            {
                if (!OperationMethods.Contains(operation.Name, StringComparer.Ordinal))
                {
                    continue;
                }

                string id = operation.Value.GetProperty("operationId").GetString()!;
                string statuses = Join(operation.Value.GetProperty("responses").EnumerateObject().Select(r => r.Name).Order(StringComparer.Ordinal));
                operations.Add($"{operation.Name.ToUpperInvariant()} {path.Name} {id} [{statuses}]");
            }
        }

        return operations;
    }

    private static JsonElement CommittedDocument()
    {
        using JsonDocument document = JsonDocument.Parse(RepoFiles.ReadUtf8(RepoFiles.PathOf(OpenApiPath)));
        return document.RootElement.Clone();
    }

    [Fact]
    public async Task The_committed_openapi_document_has_the_same_operations_as_the_document_the_running_app_serves()
    {
        // Gelistirme ortami /openapi/v1.json'i sunar (Testing'de eslenmez); derleme-zamani uretimden bagimsiz, calisma zamani hizmetidir.
        ApiFactory development = CreateFactory("Development");
        using HttpClient client = development.CreateClient();

        using HttpResponseMessage response = await client.GetAsync("/openapi/v1.json", Ct);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        SortedSet<string> runtime = Operations(await ReadAsync(response));
        SortedSet<string> committed = Operations(CommittedDocument());
        string[] onlyCommitted = [.. committed.Except(runtime, StringComparer.Ordinal)];
        string[] onlyRuntime = [.. runtime.Except(committed, StringComparer.Ordinal)];

        Assert.NotEmpty(runtime);
        Assert.True(
            onlyCommitted.Length == 0 && onlyRuntime.Length == 0,
            $"Depodaki openapi/v1.json bayat; Release derlemesiyle yeniden uretin.{Environment.NewLine}"
            + $"Yalniz depodaki belgede: [{string.Join("; ", onlyCommitted)}]{Environment.NewLine}"
            + $"Yalniz calisan uygulamada: [{string.Join("; ", onlyRuntime)}]");
    }

    [Fact]
    public void The_committed_openapi_document_lists_exactly_the_non_health_endpoints_of_the_expected_table()
    {
        // Saglik uclari ExcludeFromDescription ile belge disindadir. Sablon kisitlari ({id:int}) belgede yoktur.
        string[] fromTable =
        [
            .. ExpectedEndpoints.All
                .Where(r => !ExpectedEndpoints.IsHealth(r))
                .Select(r => r.Method + " " + RouteParameter.Replace(r.Pattern, "{$1}"))
                .Order(StringComparer.Ordinal),
        ];
        string[] fromDocument =
        [
            .. CommittedDocument().GetProperty("paths").EnumerateObject()
                .SelectMany(path => path.Value.EnumerateObject()
                    .Where(operation => OperationMethods.Contains(operation.Name, StringComparer.Ordinal))
                    .Select(operation => operation.Name.ToUpperInvariant() + " " + path.Name))
                .Order(StringComparer.Ordinal),
        ];

        string[] extra = [.. fromDocument.Except(fromTable, StringComparer.Ordinal)];
        string[] missing = [.. fromTable.Except(fromDocument, StringComparer.Ordinal)];
        Assert.True(
            extra.Length == 0 && missing.Length == 0,
            $"openapi/v1.json ile uc tablosu ayni degil. Belgede fazla: [{string.Join("; ", extra)}]; belgede eksik: [{string.Join("; ", missing)}]");
    }

    [Fact]
    public void Operation_ids_in_the_committed_openapi_document_are_unique_camelCase_names()
    {
        string[] ids =
        [
            .. CommittedDocument().GetProperty("paths").EnumerateObject()
                .SelectMany(path => path.Value.EnumerateObject().Where(o => OperationMethods.Contains(o.Name, StringComparer.Ordinal)))
                .Select(operation => operation.Value.GetProperty("operationId").GetString()!),
        ];

        Assert.Equal(ids.Length, ids.Distinct(StringComparer.Ordinal).Count());
        Assert.All(ids, id => Assert.Matches("^[a-z][A-Za-z0-9]*$", id));
    }

    // --- ProblemDetails ---

    [Fact]
    public async Task Every_error_status_returns_a_urn_typed_problem_with_a_trace_id_and_a_matching_code()
    {
        using HttpClient editor = await LoginEditorAsync();
        await SeedSourceAsync(SourceSlug, SourceKind.Risale);
        await SeedUnitAsync(SourceSlug, UnitAnchor, "Deneme paragrafı 1");
        await SeedSourceAsync("test-kuran", SourceKind.KuranMetni);
        await SeedUnitAsync("test-kuran", "q:3:1", "Deneme ayeti 1", UnitKind.Ayet);
        using HttpClient admin = await ReleaseTestKit.AdminAsync(Factory, Ct);
        using HttpClient anonymous = Factory.CreateApiClient();

        using HttpResponseMessage proposal = await editor.PostAsJsonAsync(
            "/api/v1/units/" + Uri.EscapeDataString(UnitAnchor) + "/corrections",
            new { metin = "Deneme paragrafı 2", gerekce = "Deneme gerekcesi" },
            Ct);
        Assert.Equal(HttpStatusCode.Created, proposal.StatusCode);
        long reviewId = (await ReadAsync(proposal)).GetProperty("id").GetInt64();
        uint xmin = uint.Parse(await Db.ScalarAsync<string>("SELECT xmin::text FROM icerik.review WHERE id = @id", Ct, ("id", reviewId)), CultureInfo.InvariantCulture);
        string adminId = await Db.ScalarAsync<string>("SELECT id FROM kimlik.users WHERE email = @e", Ct, ("e", ReleaseTestKit.AdminEmail));

        HttpRequestMessage Decision(string? ifMatch)
        {
            HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{reviewId}/decision")
            {
                Content = JsonContent.Create(new { karar = "reddedildi", gerekce = "Deneme ret gerekcesi" }),
            };
            if (ifMatch is not null)
            {
                request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
            }

            return request;
        }

        (string Name, HttpStatusCode Status, string Code, Func<Task<HttpResponseMessage>> Send)[] cases =
        [
            ("400", HttpStatusCode.BadRequest, "dogrulama", () => anonymous.PostAsJsonAsync("/api/v1/auth/login", new { }, Ct)),
            ("401", HttpStatusCode.Unauthorized, "oturum-acilamadi", () => anonymous.GetAsync("/api/v1/auth/me", Ct)),
            ("403", HttpStatusCode.Forbidden, "yetki-yok", () => editor.GetAsync("/api/v1/users", Ct)),
            ("404", HttpStatusCode.NotFound, "bulunamadi", () => editor.GetAsync("/api/v1/sources/test-yok", Ct)),
            ("405", HttpStatusCode.MethodNotAllowed, "yontem-desteklenmiyor", () => editor.DeleteAsync("/api/v1/sources", Ct)),
            (
                "409",
                HttpStatusCode.Conflict,
                "durum-gecisi-gecersiz",
                () => admin.PutAsJsonAsync($"/api/v1/users/{adminId}/roles", new { roller = new[] { "editor" } }, Ct)),
            (
                "412",
                HttpStatusCode.PreconditionFailed,
                "surum-uyusmazligi",
                () => editor.SendAsync(Decision("\"" + (xmin + 1).ToString(CultureInfo.InvariantCulture) + "\""), Ct)),
            (
                "422",
                HttpStatusCode.UnprocessableEntity,
                "degistirilemez-metin",
                () => editor.PostAsJsonAsync("/api/v1/units/" + Uri.EscapeDataString("q:3:1") + "/corrections", new { metin = "Deneme ayeti 2", gerekce = "Deneme" }, Ct)),
            ("428", HttpStatusCode.PreconditionRequired, "surum-gerekli", () => editor.SendAsync(Decision(null), Ct)),
        ];

        List<string> failures = [];
        foreach ((string name, HttpStatusCode status, string code, Func<Task<HttpResponseMessage>> send) in cases)
        {
            using HttpResponseMessage response = await send();
            foreach (string deviation in await ProblemChecks.DeviationsAsync(response, status, code, Ct))
            {
                failures.Add($"{name}: {deviation}");
            }
        }

        ProblemChecks.AssertNone(failures, "Hata yanitlari");

        // Reddedilen son yonetici ve degistirilemez ayet: hicbir sey degismedi.
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.user_roles ur JOIN kimlik.roles r ON r.id = ur.role_id WHERE r.name = 'admin'", Ct));
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.review", Ct));
    }
}
