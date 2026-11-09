using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;
using Npgsql;
using static Mutalaa.Api.Tests.Support.ReleaseTestKit;

namespace Mutalaa.Api.Tests;

/// <summary>
/// POST /releases/preview (Docker'li): paket uretmeden kalite kapisi raporu. Sentetik icerik <see cref="EndToEndData"/> tohumundan gelir
/// (kaynak kayitlari ve ham Tanzil parcasi gecici klasorde). Onceki yayinlar, yerel PacksDir'e yazilmis sentetik SQLite paketleriyle kurulur;
/// ag cagrilari sahte HttpClient fabrikasiyla yapilir (ag yok).
/// </summary>
public class ReleasePreviewTests(SeededReleaseDatabase<ReleasePreviewTests> fixture)
    : IClassFixture<SeededReleaseDatabase<ReleasePreviewTests>>, IAsyncLifetime
{
    private const string PreviewUrl = "/api/v1/releases/preview";
    private const string PreviousVersion = "2026.11.0";

    private readonly string _work = Path.Combine(Path.GetTempPath(), "mutalaa-api-tests", Guid.NewGuid().ToString("N"));
    private readonly List<ApiFactory> _factories = [];

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private TestDatabase Db => fixture.Database;

    private string PacksDir => Path.Combine(_work, "packs");

    private string TempDir => Path.Combine(_work, "tmp");

    public async ValueTask InitializeAsync()
    {
        Directory.CreateDirectory(_work);
        await ResetAsync(Db, Ct);
    }

    public async ValueTask DisposeAsync()
    {
        foreach (ApiFactory factory in _factories)
        {
            await factory.DisposeAsync();
        }

        try
        {
            Directory.Delete(_work, recursive: true);
        }
        catch (IOException)
        {
            // Gecici klasor; sistem temizler.
        }
    }

    private ApiFactory NewFactory(string? sourcesDir = null, Action<IServiceCollection>? configure = null, PackCatalog? catalog = null)
    {
        Dictionary<string, string?> settings = new(StringComparer.Ordinal)
        {
            ["Mutalaa:Paths:RawDir"] = fixture.RawDir,
            ["Mutalaa:Paths:SourcesDir"] = sourcesDir ?? fixture.SourcesDir,
            ["Mutalaa:Paths:PacksDir"] = PacksDir,
            ["Mutalaa:Paths:TempDir"] = TempDir,
        };
        ApiFactory factory = new(
            Db.ConnectionString,
            "Testing",
            settings,
            services =>
            {
                services.AddSingleton(catalog ?? EndToEndData.Catalog());
                configure?.Invoke(services);
            });
        _factories.Add(factory);
        return factory;
    }

    private static Task<HttpClient> AdminAsync(ApiFactory factory) => ReleaseTestKit.AdminAsync(factory, Ct);

    private static Task<HttpResponseMessage> PreviewAsync(HttpClient client, object body) => client.PostAsJsonAsync(PreviewUrl, body, Ct);

    private static async Task<JsonElement> BodyAsync(HttpResponseMessage response) => await ApiFactory.ReadJsonAsync(response, Ct);

    private static JsonElement? Row(JsonElement report, string kind, string id) =>
        report.GetProperty("rows").EnumerateArray()
            .Cast<JsonElement?>()
            .FirstOrDefault(r => r!.Value.GetProperty("kind").GetString() == kind && r.Value.GetProperty("id").GetString() == id);

    private static void AssertRow(JsonElement report, string kind, string id, string decision, string? rule = null)
    {
        JsonElement? row = Row(report, kind, id);
        Assert.True(row is not null, $"Rapor satiri yok: {kind} {id}");
        Assert.Equal(decision, row.Value.GetProperty("decision").GetString());
        if (rule is not null)
        {
            Assert.Equal(rule, row.Value.GetProperty("rule").GetString());
        }
    }

    private string CopySourcesWithout(params string[] slugs)
    {
        string target = Path.Combine(_work, "sources-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(target);
        foreach (string file in Directory.GetFiles(fixture.SourcesDir))
        {
            if (!slugs.Contains(Path.GetFileNameWithoutExtension(file), StringComparer.Ordinal))
            {
                File.Copy(file, Path.Combine(target, Path.GetFileName(file)));
            }
        }

        return target;
    }

    /// <summary>Onceki yayin: yerel PacksDir'e sentetik bir SQLite paketi ve veritabanina yayinlandi satiri (manifestli).</summary>
    private async Task<ManifestPack> SeedPreviousAsync(
        string flavor,
        IEnumerable<string> anchors,
        string packId = EndToEndData.KucukPack,
        string url = "http://127.0.0.1:1/onceki.db",
        bool writeLocal = true,
        string? shaOverride = null)
    {
        string path = PackFiles.LocalPackPath(PacksDir, flavor, packId, PreviousVersion);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using (SqliteConnection connection = new($"Data Source={path};Pooling=False"))
        {
            await connection.OpenAsync(Ct);
            await using (SqliteCommand create = connection.CreateCommand())
            {
                create.CommandText = "CREATE TABLE unit (anchor TEXT NOT NULL)";
                await create.ExecuteNonQueryAsync(Ct);
            }

            foreach (string anchor in anchors)
            {
                await using SqliteCommand insert = connection.CreateCommand();
                insert.CommandText = "INSERT INTO unit (anchor) VALUES ($a)";
                insert.Parameters.AddWithValue("$a", anchor);
                await insert.ExecuteNonQueryAsync(Ct);
            }
        }

        string sha = await PackFiles.Sha256Async(path, Ct);
        long size = new FileInfo(path).Length;
        if (!writeLocal)
        {
            File.Delete(path);
        }

        ManifestPack pack = new(packId, PreviousVersion, shaOverride ?? sha, size, "1.0.0", [], url, 1);
        Manifest manifest = new(flavor, PreviousVersion, DateTimeOffset.UtcNow, [pack]);
        _ = await InsertReleaseAsync(
            Db,
            new ReleaseSeed(PreviousVersion, flavor, "yayinlandi", Manifest: Encoding.UTF8.GetString(ManifestJson.Write(manifest)), YayinlandiAt: DateTime.UtcNow),
            Ct);
        return pack;
    }

    // --- Kapi gecer ---

    [Fact]
    public async Task Without_a_previous_release_a_passing_gate_is_a_200_with_the_report_and_writes_nothing()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("application/json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await BodyAsync(response);
        Assert.Equal(["derleme", "kapi_raporu", "uyarilar"], body.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal));
        Assert.Equal("dev", body.GetProperty("derleme").GetString());
        Assert.Equal(0, body.GetProperty("uyarilar").GetArrayLength());

        JsonElement report = body.GetProperty("kapi_raporu");
        Assert.Equal(JsonValueKind.Object, report.ValueKind);
        Assert.Equal("dev", report.GetProperty("flavor").GetString());
        Assert.False(report.GetProperty("rejected").GetBoolean());
        Assert.Equal(0, report.GetProperty("violations").GetArrayLength());
        AssertRow(report, "kaynak", EndToEndData.Kucuk, "girdi");
        AssertRow(report, "paket", EndToEndData.KucukPack, "girdi");

        // Onizleme satir ve dosya yazmaz.
        Assert.Equal(0, await CountAsync(Db, Ct));
        Assert.False(Directory.Exists(PacksDir));
    }

    [Fact]
    public async Task The_report_is_the_report_the_gate_planner_produces()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);
        GatePlan plan = await GatePlanner.PlanAsync(
            new GatePlanRequest(
                Db.ConnectionString,
                BuildFlavor.Internal,
                [],
                EndToEndData.Catalog(),
                fixture.SourcesDir,
                fixture.RawDir,
                PromoteFrom: null,
                new NoPreviousPacks(),
                SkipAssembly: true),
            Ct);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "internal" });

        JsonElement report = (await BodyAsync(response)).GetProperty("kapi_raporu");
        using JsonDocument expected = JsonDocument.Parse(plan.Report.ToJson());
        Assert.True(JsonElement.DeepEquals(expected.RootElement, report));
    }

    [Fact]
    public async Task On_internal_only_the_end_to_end_test_sources_enter()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "internal" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement report = (await BodyAsync(response)).GetProperty("kapi_raporu");
        AssertRow(report, "kaynak", EndToEndData.Kucuk, "girdi");
        AssertRow(report, "kaynak", EndToEndData.Ses, "girdi");
        AssertRow(report, "kaynak", EndToEndData.Tefsir, "girmedi", "P-12");
    }

    [Fact]
    public async Task On_public_no_test_source_enters_and_that_is_not_a_rejection()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "public" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement report = (await BodyAsync(response)).GetProperty("kapi_raporu");
        Assert.False(report.GetProperty("rejected").GetBoolean());
        foreach (string slug in new[] { EndToEndData.Kucuk, EndToEndData.Tefsir, EndToEndData.Ses })
        {
            AssertRow(report, "kaynak", slug, "girmedi", "P-12");
        }

        AssertRow(report, "kaynak", EndToEndData.Uthmani, "girdi");
    }

    [Fact]
    public async Task A_missing_source_record_of_a_test_source_does_not_reject_public_because_P_12_decides_first()
    {
        ApiFactory factory = NewFactory(CopySourcesWithout(EndToEndData.Kucuk));
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "public" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task The_default_pack_catalog_works_without_the_test_override()
    {
        ApiFactory factory = NewFactory(catalog: PackCatalog.Default);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.False((await BodyAsync(response)).GetProperty("kapi_raporu").GetProperty("rejected").GetBoolean());
    }

    [Fact]
    public async Task A_pack_selection_that_the_gate_does_not_admit_is_reported_as_a_warning()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "internal", paketler = new[] { EndToEndData.KucukPack, EndToEndData.TefsirPack, "core" } });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        string[] warnings = [.. (await BodyAsync(response)).GetProperty("uyarilar").EnumerateArray().Select(w => w.GetString()!)];
        Assert.Equal([$"uyari: istenen paket kapidan girmedi: {EndToEndData.TefsirPack}"], warnings);
    }

    [Fact]
    public async Task A_selection_whose_dependency_is_not_in_the_manifest_set_is_rejected_by_P_13()
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev", paketler = new[] { EndToEndData.TefsirPack } });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("kalite-kapisi", Code(body));
        JsonElement report = body.GetProperty("kapi_raporu");
        Assert.True(report.GetProperty("rejected").GetBoolean());
        Assert.Contains(report.GetProperty("violations").EnumerateArray(), v => v.GetProperty("rule").GetString() == "P-13");
    }

    // --- Kapi reddeder (422 kalite-kapisi) ---

    [Fact]
    public async Task A_source_without_a_record_file_is_a_422_kalite_kapisi_with_the_report_attached()
    {
        ApiFactory factory = NewFactory(CopySourcesWithout(EndToEndData.Uthmani));
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("kalite-kapisi", Code(body));
        Assert.Equal("urn:mutalaa:problem:kalite-kapisi", body.GetProperty("type").GetString());
        Assert.Equal(422, body.GetProperty("status").GetInt32());
        JsonElement report = body.GetProperty("kapi_raporu");
        Assert.True(report.GetProperty("rejected").GetBoolean());
        Assert.Contains(
            report.GetProperty("violations").EnumerateArray(),
            v => v.GetProperty("rule").GetString() == "P-01"
                && v.GetProperty("subject").GetString() == EndToEndData.Uthmani
                && v.GetProperty("reason").GetString() == "kaynak-kaydi-yok");
        Assert.Equal(0, await CountAsync(Db, Ct));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task A_blank_attribution_text_is_a_P_01_violation(string attribution)
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);
        await Db.ExecuteAsync("UPDATE icerik.source SET atif_metni = @a WHERE slug = @s", Ct, ("a", attribution), ("s", EndToEndData.Kucuk));
        try
        {
            using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

            Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
            JsonElement body = await BodyAsync(response);
            Assert.Equal("kalite-kapisi", Code(body));
            Assert.Contains(
                body.GetProperty("kapi_raporu").GetProperty("violations").EnumerateArray(),
                v => v.GetProperty("rule").GetString() == "P-01" && v.GetProperty("subject").GetString() == EndToEndData.Kucuk && v.GetProperty("reason").GetString() == "atif-metni-bos");
        }
        finally
        {
            await Db.ExecuteAsync("UPDATE icerik.source SET atif_metni = 'Sentetik test verisi (Mutalaa).' WHERE slug = @s", Ct, ("s", EndToEndData.Kucuk));
        }
    }

    // --- Onceki yayin ---

    [Fact]
    public async Task With_a_previous_release_whose_anchors_are_all_still_present_the_gate_passes_without_any_network_call()
    {
        StubHandler network = new((_, _) => throw new InvalidOperationException("Ag cagrisi beklenmiyordu."));
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IHttpClientFactory>(new StubClientFactory(network)));
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst, EndToEndData.KucukSecond]);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.False((await BodyAsync(response)).GetProperty("kapi_raporu").GetProperty("rejected").GetBoolean());
        Assert.Equal(0, network.Calls);
    }

    [Fact]
    public async Task An_anchor_of_the_previous_release_that_vanished_is_a_422_with_a_capa_kayboldu_violation()
    {
        ApiFactory factory = NewFactory();
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst, EndToEndData.KucukSecond, "k:test-kucuk:bolum-1:p99"]);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("kalite-kapisi", Code(body));
        Assert.Contains(
            body.GetProperty("kapi_raporu").GetProperty("violations").EnumerateArray(),
            v => v.GetProperty("subject").GetString() == "k:test-kucuk:bolum-1:p99" && v.GetProperty("reason").GetString()!.StartsWith("capa-kayboldu", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Only_the_flavor_of_the_request_is_compared_with_its_own_previous_release()
    {
        ApiFactory factory = NewFactory();
        _ = await SeedPreviousAsync("internal", [EndToEndData.KucukFirst, "k:test-kucuk:bolum-1:p99"]);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage dev = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.OK, dev.StatusCode);
    }

    [Fact]
    public async Task A_previous_pack_missing_locally_is_downloaded_through_the_resolver_and_verified()
    {
        byte[]? served = null;
        StubHandler network = new((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent(served!) }));
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IHttpClientFactory>(new StubClientFactory(network)));
        ManifestPack pack = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst, EndToEndData.KucukSecond], url: "https://depo.example.test/onceki.db");
        string local = PackFiles.LocalPackPath(PacksDir, "dev", pack.PackId, pack.Version);
        served = await File.ReadAllBytesAsync(local, Ct);
        File.Delete(local);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(1, network.Calls);
        Assert.Single(Directory.GetFiles(Path.Combine(TempDir, "previous", "dev")));
    }

    [Fact]
    public async Task A_previous_pack_that_cannot_be_reached_is_a_503_depo_erisilemiyor()
    {
        StubHandler network = new((_, _) => throw new HttpRequestException("baglanti reddedildi"));
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IHttpClientFactory>(new StubClientFactory(network)));
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst], url: "https://depo.example.test/onceki.db", writeLocal: false);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("depo-erisilemiyor", Code(body));
        Assert.Equal("urn:mutalaa:problem:depo-erisilemiyor", body.GetProperty("type").GetString());
        Assert.DoesNotContain("depo.example.test", body.GetRawText(), StringComparison.Ordinal);

        // Yalniz tohumlanan onceki yayin satiri var; onizleme satir acmadi.
        Assert.Equal(1, await CountAsync(Db, Ct));
    }

    [Fact]
    public async Task A_previous_pack_whose_sha256_differs_from_the_manifest_is_also_a_503()
    {
        StubHandler network = new((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent([1, 2, 3, 4]) }));
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IHttpClientFactory>(new StubClientFactory(network)));
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst], url: "https://depo.example.test/onceki.db", shaOverride: new string('a', 64));
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("depo-erisilemiyor", Code(await BodyAsync(response)));
    }

    [Fact]
    public async Task A_previous_release_without_a_manifest_is_a_422_onceki_yayin_bozuk()
    {
        ApiFactory factory = NewFactory();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(PreviousVersion, "dev", "yayinlandi", YayinlandiAt: DateTime.UtcNow), Ct);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        JsonElement body = await BodyAsync(response);
        Assert.Equal("onceki-yayin-bozuk", Code(body));
        Assert.Equal("urn:mutalaa:problem:onceki-yayin-bozuk", body.GetProperty("type").GetString());
        Assert.False(body.TryGetProperty("kapi_raporu", out _));
    }

    [Fact]
    public async Task A_previous_release_with_an_unreadable_manifest_is_a_422_onceki_yayin_bozuk()
    {
        ApiFactory factory = NewFactory();
        _ = await InsertReleaseAsync(Db, new ReleaseSeed(PreviousVersion, "dev", "yayinlandi", Manifest: "{}", YayinlandiAt: DateTime.UtcNow), Ct);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.Equal("onceki-yayin-bozuk", Code(await BodyAsync(response)));
    }

    // --- Gizli deger ve tek onizleme ---

    [Fact]
    public async Task Messages_from_the_planner_never_leak_the_connection_string_or_its_password()
    {
        string password = new NpgsqlConnectionStringBuilder(Db.ConnectionString).Password!;
        Assert.False(string.IsNullOrEmpty(password));
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IPreviousPackResolver>(new ThrowingResolver(
            new GatePlanException(GatePlanFailure.PreviousPackMissing, $"Depo hatasi: {Db.ConnectionString} ve Password={password} ve token: abc123xyz"))));
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst]);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = "dev" });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        string text = await response.Content.ReadAsStringAsync(Ct);
        Assert.DoesNotContain(password, text, StringComparison.Ordinal);
        Assert.DoesNotContain("abc123xyz", text, StringComparison.Ordinal);
        Assert.DoesNotContain(new NpgsqlConnectionStringBuilder(Db.ConnectionString).Host!, text, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Successful_and_rejected_previews_never_contain_the_connection_string_or_its_password()
    {
        string password = new NpgsqlConnectionStringBuilder(Db.ConnectionString).Password!;
        ApiFactory factory = NewFactory(CopySourcesWithout(EndToEndData.Uthmani));
        using HttpClient admin = await AdminAsync(factory);

        foreach (string flavor in new[] { "dev", "internal", "public" })
        {
            using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = flavor, paketler = new[] { EndToEndData.TefsirPack, "core" } });

            string text = await response.Content.ReadAsStringAsync(Ct);
            Assert.DoesNotContain(password, text, StringComparison.Ordinal);
            Assert.DoesNotContain("Password", text, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain(Db.ConnectionString, text, StringComparison.Ordinal);
        }
    }

    [Fact]
    public async Task A_second_preview_while_one_is_running_is_a_409_cakisma_and_the_first_still_succeeds()
    {
        using GatedResolver gated = new();
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IPreviousPackResolver>(gated));
        ManifestPack pack = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst, EndToEndData.KucukSecond]);
        gated.LocalPath = PackFiles.LocalPackPath(PacksDir, "dev", pack.PackId, pack.Version);
        using HttpClient admin = await AdminAsync(factory);

        Task<HttpResponseMessage> first = PreviewAsync(admin, new { derleme = "dev" });
        await gated.Entered.Task.WaitAsync(TimeSpan.FromSeconds(30), Ct);
        using HttpResponseMessage second = await PreviewAsync(admin, new { derleme = "public" });
        gated.Release.SetResult();
        using HttpResponseMessage firstResponse = await first;

        Assert.Equal(HttpStatusCode.Conflict, second.StatusCode);
        Assert.Equal("cakisma", Code(await BodyAsync(second)));
        Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);

        // Kilit birakildi: sonraki onizleme calisir.
        using HttpResponseMessage third = await PreviewAsync(admin, new { derleme = "public" });
        Assert.Equal(HttpStatusCode.OK, third.StatusCode);
    }

    [Fact]
    public async Task The_gate_is_released_after_a_failed_preview()
    {
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IPreviousPackResolver>(new ThrowingResolver(
            new GatePlanException(GatePlanFailure.PreviousPackMissing, "Onceki yayinin paketi depoda yok."))));
        _ = await SeedPreviousAsync("dev", [EndToEndData.KucukFirst]);
        using HttpClient admin = await AdminAsync(factory);

        using HttpResponseMessage failed = await PreviewAsync(admin, new { derleme = "dev" });
        using HttpResponseMessage later = await PreviewAsync(admin, new { derleme = "public" });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, failed.StatusCode);
        Assert.Equal(HttpStatusCode.OK, later.StatusCode);
    }

    // --- Dogrulama ve kultur ---

    [Theory]
    [InlineData("""{"derleme":"production"}""")]
    [InlineData("""{"derleme":"dev","paketler":["yok-boyle-paket"]}""")]
    [InlineData("""{"derleme":"dev","paketler":["core","core"]}""")]
    [InlineData("""{"derleme":"dev","notlar":"Onizlemede notlar yok."}""")]
    [InlineData("""{"paketler":["core"]}""")]
    public async Task A_bad_preview_body_is_a_400_and_never_reaches_the_planner(string json)
    {
        ApiFactory factory = NewFactory(configure: services => services.AddSingleton<IPreviousPackResolver>(new ThrowingResolver(new InvalidOperationException("planlayici cagrilmamali"))));
        using HttpClient admin = await AdminAsync(factory);
        using StringContent content = new(json, new System.Net.Http.Headers.MediaTypeHeaderValue("application/json"));

        using HttpResponseMessage response = await admin.PostAsync(PreviewUrl, content, Ct);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("dogrulama", Code(await BodyAsync(response)));
    }

    [Theory]
    [InlineData("dev")]
    [InlineData("internal")]
    [InlineData("public")]
    public async Task Flavor_labels_are_culture_independent_under_tr_TR(string flavor)
    {
        ApiFactory factory = NewFactory();
        using HttpClient admin = await AdminAsync(factory);

        await AsyncCultureScope.TurkishAsync(async () =>
        {
            using HttpResponseMessage response = await PreviewAsync(admin, new { derleme = flavor });

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            JsonElement body = await BodyAsync(response);
            Assert.Equal(flavor, body.GetProperty("derleme").GetString());
            Assert.Equal(flavor, body.GetProperty("kapi_raporu").GetProperty("flavor").GetString());
        });
    }

    // --- Sahte cozuculer ---

    private sealed class NoPreviousPacks : IPreviousPackResolver
    {
        public Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("Onceki paket beklenmiyordu.");
    }

    private sealed class ThrowingResolver(Exception exception) : IPreviousPackResolver
    {
        public Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken) => throw exception;
    }

    /// <summary>Ilk cagrida haber verir ve serbest birakilana kadar bekler; sonra yerel paketi doner.</summary>
    private sealed class GatedResolver : IPreviousPackResolver, IDisposable
    {
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public string LocalPath { get; set; } = string.Empty;

        public async Task<string> ResolveAsync(string flavorLabel, ManifestPack pack, CancellationToken cancellationToken)
        {
            Entered.TrySetResult();
            await Release.Task.WaitAsync(cancellationToken);
            return LocalPath;
        }

        public void Dispose() => Release.TrySetResult();
    }
}
