using System.Net;
using System.Text;
using Mutalaa.Api.Tests.Support;

namespace Mutalaa.Api.Tests;

/// <summary>
/// GET /api/v1/scans/{baski}/{sayfa}: OCR sayfa gorseli (Docker'li: oturum icin editoryal veritabani). RawDir testte gecici bir klasordur.
/// </summary>
public class ScanEndpointsTests(EditorialDatabase<ScanEndpointsTests> fixture)
    : EditorApiTestBase<ScanEndpointsTests>(fixture), IClassFixture<EditorialDatabase<ScanEndpointsTests>>
{
    private const string Baski = "test-baski";

    // Sentetik gorsel baytlari: gercek goruntu degil, yalniz PNG imzasi + ayirt edici yuk.
    private static byte[] Png(string tag) => [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, .. Encoding.ASCII.GetBytes(tag)];

    private static string NewTempRoot()
    {
        string root = Path.Combine(Path.GetTempPath(), "mutalaa-scan-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "raw"));
        return root;
    }

    private static void Put(string root, string relative, byte[] bytes)
    {
        string path = Path.Combine(root, "raw", relative);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path, bytes);
    }

    private async Task<(HttpClient Client, string Root)> StartAsync(Action<string>? seed = null, bool rawDirExists = true)
    {
        string root = NewTempRoot();
        seed?.Invoke(root);
        string rawDir = rawDirExists ? Path.Combine(root, "raw") : Path.Combine(root, "yok");
        ApiFactory factory = CreateFactory(settings: new Dictionary<string, string?> { ["Mutalaa:Paths:RawDir"] = rawDir });
        return (await LoginEditorAsync(factory), root);
    }

    private static void Cleanup(string root)
    {
        if (Directory.Exists(root))
        {
            // Baglantilar once kendileri silinir (hedefleri degil); ozyinelemeli silme baglanti noktasinda yol hatasi verir.
            RemoveLinks(new DirectoryInfo(root));
            Directory.Delete(root, recursive: true);
        }
    }

    private static void RemoveLinks(DirectoryInfo directory)
    {
        foreach (FileSystemInfo entry in directory.EnumerateFileSystemInfos())
        {
            if (entry.LinkTarget is not null)
            {
                entry.Delete();
            }
            else if (entry is DirectoryInfo child)
            {
                RemoveLinks(child);
            }
        }
    }

    [Fact]
    public async Task A_page_that_exists_only_in_an_older_dated_folder_is_found_and_the_newest_copy_wins()
    {
        (HttpClient client, string root) = await StartAsync(r =>
        {
            Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("eski-1"));
            Put(r, Baski + "/2026-01-01/c01-s0003.png", Png("eski-3"));
            Put(r, Baski + "/2026-02-01/c01-s0001.png", Png("yeni-1"));
            Put(r, Baski + "/2026-02-01/c01-s0002.png", Png("yeni-2"));
        });
        try
        {
            using HttpResponseMessage newest = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);
            using HttpResponseMessage newOnly = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0002", Ct);
            using HttpResponseMessage oldOnly = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0003", Ct);

            Assert.Equal(HttpStatusCode.OK, newest.StatusCode);
            Assert.Equal(Png("yeni-1"), await newest.Content.ReadAsByteArrayAsync(Ct));
            Assert.Equal(Png("yeni-2"), await newOnly.Content.ReadAsByteArrayAsync(Ct));
            Assert.Equal(HttpStatusCode.OK, oldOnly.StatusCode);
            Assert.Equal(Png("eski-3"), await oldOnly.Content.ReadAsByteArrayAsync(Ct));
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Fact]
    public async Task The_response_is_private_no_store_and_has_the_image_content_type()
    {
        (HttpClient client, string root) = await StartAsync(r => Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("a")));
        try
        {
            using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal("image/png", response.Content.Headers.ContentType?.MediaType);
            string cacheControl = string.Join(", ", response.Headers.GetValues("Cache-Control"));
            Assert.Contains("private", cacheControl, StringComparison.Ordinal);
            Assert.Contains("no-store", cacheControl, StringComparison.Ordinal);
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Theory]
    [InlineData("png", "image/png")]
    [InlineData("jpg", "image/jpeg")]
    [InlineData("jpeg", "image/jpeg")]
    [InlineData("tif", "image/tiff")]
    [InlineData("tiff", "image/tiff")]
    public async Task The_content_type_follows_the_file_extension(string extension, string contentType)
    {
        (HttpClient client, string root) = await StartAsync(r => Put(r, Baski + "/2026-01-01/c01-s0001." + extension, Png(extension)));
        try
        {
            using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal(contentType, response.Content.Headers.ContentType?.MediaType);
            Assert.Equal(Png(extension), await response.Content.ReadAsByteArrayAsync(Ct));
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Fact]
    public async Task Folders_that_are_not_dated_and_unsupported_extensions_are_ignored()
    {
        (HttpClient client, string root) = await StartAsync(r =>
        {
            Put(r, Baski + "/son/c01-s0001.png", Png("tarihsiz"));
            Put(r, Baski + "/2026-1-1/c01-s0001.png", Png("bozuk-tarih"));
            Put(r, Baski + "/2026-01-01/c01-s0002.txt", Encoding.ASCII.GetBytes("deneme"));
            Put(r, Baski + "/2026-01-01/c01-s0003.png", Png("tamam"));
        });
        try
        {
            using HttpResponseMessage undated = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);
            using HttpResponseMessage text = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0002", Ct);
            using HttpResponseMessage ok = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0003", Ct);

            Assert.Equal(HttpStatusCode.NotFound, undated.StatusCode);
            Assert.Equal(HttpStatusCode.NotFound, text.StatusCode);
            Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Theory]
    [InlineData("test-yok", "c01-s0001")]
    [InlineData(Baski, "c01-s0099")]
    [InlineData(Baski, "c99-s9999")]
    public async Task A_missing_book_or_page_is_a_404_problem(string baski, string sayfa)
    {
        (HttpClient client, string root) = await StartAsync(r => Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("a")));
        try
        {
            using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{baski}/{sayfa}", Ct);

            Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
            Assert.Equal("urn:mutalaa:problem:bulunamadi", ProblemType(await ReadAsync(response)));
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Fact]
    public async Task A_missing_raw_directory_is_a_404()
    {
        (HttpClient client, string root) = await StartAsync(rawDirExists: false);
        try
        {
            using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);

            Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Theory]
    [InlineData("Test-baski", "c01-s0001")]
    [InlineData("test_baski", "c01-s0001")]
    [InlineData("test.baski", "c01-s0001")]
    [InlineData("test%20baski", "c01-s0001")]
    [InlineData("test-baski%0A", "c01-s0001")]
    [InlineData("ı", "c01-s0001")]
    [InlineData(Baski, "c1-s1")]
    [InlineData(Baski, "c01-s00001")]
    [InlineData(Baski, "C01-S0001")]
    [InlineData(Baski, "c01-s0001.png")]
    [InlineData(Baski, "c01-s0001%0A")]
    [InlineData(Baski, "c0١-s0001")]
    [InlineData("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "c01-s0001")]
    public async Task A_page_or_book_outside_the_pattern_is_a_400_validation_problem(string baski, string sayfa)
    {
        (HttpClient client, string root) = await StartAsync(r => Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("a")));
        try
        {
            using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{baski}/{sayfa}", Ct);

            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
            Assert.Equal("urn:mutalaa:problem:dogrulama", ProblemType(await ReadAsync(response)));
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Theory]
    [InlineData("..%2fdisari/c01-s0001")]
    [InlineData("..%2F..%2Fdisari/c01-s0001")]
    [InlineData("%2e%2e%2fdisari/c01-s0001")]
    [InlineData("%2e%2e/disari/c01-s0001")]
    [InlineData("../disari/c01-s0001")]
    [InlineData("..%5cdisari/c01-s0001")]
    [InlineData("..%255cdisari/c01-s0001")]
    [InlineData("test-baski/..%2f..%2fdisari%2f2026-01-01%2fc01-s0001")]
    [InlineData("test-baski/%2e%2e%2fc01-s0001")]
    [InlineData("%2Fetc%2Fpasswd/c01-s0001")]
    [InlineData("C%3A%5CWindows/c01-s0001")]
    [InlineData("test-baski/..%5c..%5cdisari%5c2026-01-01%5cc01-s0001")]
    public async Task Path_escape_attempts_never_return_a_file_from_outside_the_raw_directory(string path)
    {
        string secret = "disaridaki-gizli-icerik";
        (HttpClient client, string root) = await StartAsync(r =>
        {
            Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("ic"));

            // RawDir disinda (kardes klasor): "disari" altinda ayni desende bir dosya.
            string outside = Path.Combine(r, "disari", "2026-01-01");
            Directory.CreateDirectory(outside);
            File.WriteAllBytes(Path.Combine(outside, "c01-s0001.png"), Png(secret));
        });
        try
        {
            using HttpResponseMessage response = await client.GetAsync("/api/v1/scans/" + path, Ct);

            Assert.True(
                response.StatusCode is HttpStatusCode.BadRequest or HttpStatusCode.NotFound,
                $"beklenmeyen durum: {(int)response.StatusCode}");
            byte[] body = await response.Content.ReadAsByteArrayAsync(Ct);
            Assert.DoesNotContain(secret, Encoding.Latin1.GetString(body), StringComparison.Ordinal);
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    [Fact]
    public async Task Links_to_folders_and_files_outside_the_raw_directory_are_not_followed()
    {
        string secret = "disaridaki-gizli-icerik";
        (HttpClient client, string root) = await StartAsync(r =>
        {
            // RawDir disinda iki klasor: bir baski klasoru ve bir tarih klasoru; ikisinde de ayni desende dosya var.
            foreach (string outside in new[] { "disari-baski/2026-01-01", "disari-tarih" })
            {
                string dir = Path.Combine(r, outside);
                Directory.CreateDirectory(dir);
                File.WriteAllBytes(Path.Combine(dir, "c01-s0001.png"), Png(secret));
            }
        });
        try
        {
            string raw = Path.Combine(root, "raw");
            string outsideBook = Path.Combine(root, "disari-baski");
            string outsideDate = Path.Combine(root, "disari-tarih");
            List<string> linked = [];

            // Baski klasoru ve tarih klasoru disariyi gosterir (sembolik bag; Windows'ta ayricalik yoksa baglanti noktasi/junction).
            if (!TryLinkDirectory(Path.Combine(raw, "baglanti"), outsideBook))
            {
                Assert.Skip("Klasor baglantisi olusturulamadi.");
            }

            linked.Add("baglanti");
            Directory.CreateDirectory(Path.Combine(raw, "tarih-baglanti"));
            if (TryLinkDirectory(Path.Combine(raw, "tarih-baglanti", "2026-01-01"), outsideDate))
            {
                linked.Add("tarih-baglanti");
            }

            // Dosya baglantisi yalniz sembolik bag ile olur (ayricalik ister); olusmazsa bu durum atlanir.
            Directory.CreateDirectory(Path.Combine(raw, "dosya-baglanti", "2026-01-01"));
            try
            {
                File.CreateSymbolicLink(
                    Path.Combine(raw, "dosya-baglanti", "2026-01-01", "c01-s0001.png"),
                    Path.Combine(outsideDate, "c01-s0001.png"));
                linked.Add("dosya-baglanti");
            }
            catch (Exception e) when (e is UnauthorizedAccessException or IOException or PlatformNotSupportedException)
            {
                // Bu durum bu makinede sinanamadi.
            }

            foreach (string baski in linked)
            {
                using HttpResponseMessage response = await client.GetAsync($"/api/v1/scans/{baski}/c01-s0001", Ct);
                Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            }
        }
        finally
        {
            client.Dispose();
            Cleanup(root);
        }
    }

    private static bool TryLinkDirectory(string link, string target)
    {
        try
        {
            Directory.CreateSymbolicLink(link, target);
            return true;
        }
        catch (Exception e) when (e is UnauthorizedAccessException or IOException or PlatformNotSupportedException)
        {
            if (!OperatingSystem.IsWindows())
            {
                return false;
            }
        }

        // Windows: ayricalik gerektirmeyen baglanti noktasi (junction); .NET bunu da baglanti (LinkTarget) sayar.
        using System.Diagnostics.Process process = new()
        {
            StartInfo = new System.Diagnostics.ProcessStartInfo("cmd.exe")
            {
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                ArgumentList = { "/c", "mklink", "/J", link, target },
            },
        };
        process.Start();
        process.StandardOutput.ReadToEnd();
        process.StandardError.ReadToEnd();
        process.WaitForExit();
        return process.ExitCode == 0 && new DirectoryInfo(link).LinkTarget is not null;
    }

    [Fact]
    public async Task Without_a_session_the_request_is_a_401_problem_without_a_redirect_location()
    {
        (HttpClient editor, string root) = await StartAsync(r => Put(r, Baski + "/2026-01-01/c01-s0001.png", Png("a")));
        try
        {
            using HttpClient anonymous = Factory.CreateApiClient();

            using HttpResponseMessage response = await anonymous.GetAsync($"/api/v1/scans/{Baski}/c01-s0001", Ct);

            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
            Assert.Null(response.Headers.Location);
            Assert.Equal("urn:mutalaa:problem:oturum-acilamadi", ProblemType(await ReadAsync(response)));
        }
        finally
        {
            editor.Dispose();
            Cleanup(root);
        }
    }
}
