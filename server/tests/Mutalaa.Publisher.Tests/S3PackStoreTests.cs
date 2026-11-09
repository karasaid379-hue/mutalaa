using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using Amazon.Runtime;
using Amazon.S3;
using Amazon.S3.Model;
using Mutalaa.Infrastructure.Storage;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// S3PackStore ve SeaweedFS 4.48 sinamasi (A13.1; Backend API 10.5). Docker'li: kap ilk kullanimda baslar (SeaweedFixture).
/// Her test benzersiz anahtar onekiyle calisir. Kultur testleri Invariant ve tr-TR altinda kosar.
/// "Measure_" testleri olcum yapar ve sonucu test ciktisina yazar (A13.1 sinama raporu).
/// </summary>
public class S3PackStoreTests(SeaweedFixture seaweed)
{
    private const string PackKeyTail = "pack/1/p-1.db";

    private static readonly HttpClient Http = new();

    private static string ObjectUrl(SeaweedEndpoint endpoint, string key) => $"{endpoint.ServiceUrl}/{endpoint.Bucket}/{key}";

    private static void Note(string line) => TestContext.Current.TestOutputHelper?.WriteLine(line);

    // ---------------------------------------------------------------- PUT / GET / HEAD

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Put_pack_uploads_and_get_returns_the_same_bytes(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
            using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
            string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
            byte[] bytes = StorageTestKit.SyntheticBytes(1_500_000, seed: 1);
            using TempFile file = await TempFile.CreateAsync(bytes, ct);

            PutResult result = await store.PutPackAsync(key, file.Path, StorageTestKit.Sha256Hex(bytes), ct);

            Assert.Equal(PutResult.Uploaded, result);
            Assert.Equal(bytes, await store.GetAsync(key, ct));
            // Yol bicimi (ForcePathStyle): {ServiceUrl}/{kova}/{anahtar}; anonim GET 200 ve ayni bayt.
            using HttpResponseMessage response = await Http.GetAsync(ObjectUrl(endpoint, key), ct);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal(bytes, await response.Content.ReadAsByteArrayAsync(ct));
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task The_pack_file_is_not_locked_after_upload(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            byte[] bytes = StorageTestKit.SyntheticBytes(10_000, seed: 2);
            TempFile file = await TempFile.CreateAsync(bytes, ct);

            await store.PutPackAsync($"{StorageTestKit.NewPrefix()}/{PackKeyTail}", file.Path, StorageTestKit.Sha256Hex(bytes), ct);

            // Akis kapanmadiysa dosya baska bir akisla ozel (FileShare.None) acilamaz: .NET paylasim kipini Windows'ta isletim sistemiyle,
            // Unix'te danisma kilidiyle (flock) uygular. Yalniz silmeyi denemek Linux'ta kanit vermezdi (acik dosya orada silinebilir).
            using (FileStream exclusive = new(file.Path, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                Assert.Equal(bytes.Length, exclusive.Length);
            }

            file.Dispose();
            Assert.False(File.Exists(file.Path));
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Head_returns_size_and_sha256_metadata(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
            byte[] bytes = StorageTestKit.SyntheticBytes(70_000, seed: 3);
            string sha = StorageTestKit.Sha256Hex(bytes);
            using TempFile file = await TempFile.CreateAsync(bytes, ct);
            await store.PutPackAsync(key, file.Path, sha, ct);

            StoredObject? head = await store.HeadAsync(key, ct);

            Assert.NotNull(head);
            Assert.Equal(70_000, head.Size);
            Assert.Equal(sha, head.Sha256);
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Head_of_a_missing_key_is_null(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));

            Assert.Null(await store.HeadAsync($"{StorageTestKit.NewPrefix()}/yok.db", ct));
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Get_of_a_missing_key_is_null(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));

            Assert.Null(await store.GetAsync($"{StorageTestKit.NewPrefix()}/yok.json", ct));
        });
    }

    // ---------------------------------------------------------------- Idempotentlik ve cakisma

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_second_put_with_the_same_sha256_is_skipped_and_does_not_upload(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
            byte[] original = StorageTestKit.SyntheticBytes(20_000, seed: 4);
            string sha = StorageTestKit.Sha256Hex(original);
            using TempFile first = await TempFile.CreateAsync(original, ct);
            Assert.Equal(PutResult.Uploaded, await store.PutPackAsync(key, first.Path, sha, ct));

            // Ayni sha256 beyaniyla baska icerik: yukleme atlanirsa depodaki bayt degismez.
            using TempFile second = await TempFile.CreateAsync(StorageTestKit.SyntheticBytes(20_000, seed: 5), ct);
            PutResult result = await store.PutPackAsync(key, second.Path, sha, ct);

            Assert.Equal(PutResult.SkippedSame, result);
            Assert.Equal(original, await store.GetAsync(key, ct));
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_second_put_with_a_different_sha256_throws_object_conflict_and_keeps_the_object(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
            byte[] original = StorageTestKit.SyntheticBytes(20_000, seed: 6);
            byte[] other = StorageTestKit.SyntheticBytes(20_000, seed: 7);
            string originalSha = StorageTestKit.Sha256Hex(original);
            string otherSha = StorageTestKit.Sha256Hex(other);
            using TempFile first = await TempFile.CreateAsync(original, ct);
            await store.PutPackAsync(key, first.Path, originalSha, ct);
            using TempFile second = await TempFile.CreateAsync(other, ct);

            ObjectConflictException ex = await Assert.ThrowsAsync<ObjectConflictException>(
                () => store.PutPackAsync(key, second.Path, otherSha, ct));

            Assert.Equal(key, ex.Key);
            Assert.Equal(originalSha, ex.ExistingSha256);
            Assert.Equal(otherSha, ex.NewSha256);
            Assert.Equal(StorageFailure.Conflict, ex.Failure);
            Assert.IsAssignableFrom<StorageException>(ex);
            Assert.Equal(original, await store.GetAsync(key, ct));
        });
    }

    [Fact]
    public async Task Put_pack_rejects_a_malformed_sha256_before_any_request()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using S3PackStore store = S3PackStore.Create(new StorageOptions
        {
            ServiceUrl = "http://127.0.0.1:1",
            AccessKey = "test-access",
            SecretKey = "test-secret",
            Bucket = "test-bucket",
        });

        await Assert.ThrowsAsync<ArgumentException>(() => store.PutPackAsync("a/b.db", "yok.db", "ABC", ct));
        await Assert.ThrowsAsync<ArgumentException>(() => store.PutPackAsync("a/b.db", "yok.db", new string('A', 64), ct));
    }

    // ---------------------------------------------------------------- Manifest

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Put_manifest_then_get_returns_the_exact_bytes_and_overwrites(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            string key = $"{StorageTestKit.NewPrefix()}/manifest.json";
            // Sentetik manifest; Turkce karakter bayt bayt gelmeli (UTF-8, BOM yok, CRLF yok).
            byte[] first = System.Text.Encoding.UTF8.GetBytes("{\"deneme\":\"Deneme İıŞş\",\"n\":1}\n");
            byte[] second = System.Text.Encoding.UTF8.GetBytes("{\"deneme\":\"ikinci\",\"n\":2}\n");

            await store.PutManifestAsync(key, first, ct);
            Assert.Equal(first, await store.GetAsync(key, ct));

            await store.PutManifestAsync(key, second, ct);
            Assert.Equal(second, await store.GetAsync(key, ct));
        });
    }

    // ---------------------------------------------------------------- Yanit basliklari, Range, anonim erisim

    [Fact]
    public async Task Anonymous_get_returns_200_with_cache_control_and_content_type_for_pack_and_manifest()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
        string prefix = StorageTestKit.NewPrefix();
        string packKey = $"{prefix}/{PackKeyTail}";
        string manifestKey = $"{prefix}/manifest.json";
        byte[] bytes = StorageTestKit.SyntheticBytes(5_000, seed: 8);
        using TempFile file = await TempFile.CreateAsync(bytes, ct);
        await store.PutPackAsync(packKey, file.Path, StorageTestKit.Sha256Hex(bytes), ct);
        await store.PutManifestAsync(manifestKey, "{\"n\":1}"u8.ToArray(), ct);

        using HttpResponseMessage pack = await Http.GetAsync(ObjectUrl(endpoint, packKey), ct);
        using HttpResponseMessage manifest = await Http.GetAsync(ObjectUrl(endpoint, manifestKey), ct);

        Assert.Equal(HttpStatusCode.OK, pack.StatusCode);
        Assert.Equal(StorageKeys.PackCacheControl, string.Join(", ", pack.Headers.GetValues("Cache-Control")));
        Assert.Equal(StorageKeys.PackContentType, pack.Content.Headers.ContentType?.MediaType);
        Assert.Equal(HttpStatusCode.OK, manifest.StatusCode);
        Assert.Equal(StorageKeys.ManifestCacheControl, string.Join(", ", manifest.Headers.GetValues("Cache-Control")));
        Assert.Equal(StorageKeys.ManifestContentType, manifest.Content.Headers.ContentType?.MediaType);
        Note($"Measure: pack Content-Type='{pack.Content.Headers.ContentType}', Cache-Control='{string.Join(", ", pack.Headers.GetValues("Cache-Control"))}'");
        Note($"Measure: manifest Content-Type='{manifest.Content.Headers.ContentType}', Cache-Control='{string.Join(", ", manifest.Headers.GetValues("Cache-Control"))}'");
    }

    [Fact]
    public async Task A_range_request_returns_206_with_the_exact_slice()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
        string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
        byte[] bytes = StorageTestKit.SyntheticBytes(100_000, seed: 9);
        using TempFile file = await TempFile.CreateAsync(bytes, ct);
        await store.PutPackAsync(key, file.Path, StorageTestKit.Sha256Hex(bytes), ct);
        using HttpRequestMessage request = new(HttpMethod.Get, ObjectUrl(endpoint, key))
        {
            Headers = { Range = new RangeHeaderValue(1_000, 1_999) },
        };

        using HttpResponseMessage response = await Http.SendAsync(request, ct);

        Assert.Equal(HttpStatusCode.PartialContent, response.StatusCode);
        byte[] slice = await response.Content.ReadAsByteArrayAsync(ct);
        Assert.Equal(1_000, slice.Length);
        Assert.Equal(bytes[1_000..2_000], slice);
        Assert.Equal(1_000, response.Content.Headers.ContentRange?.From);
        Assert.Equal(1_999, response.Content.Headers.ContentRange?.To);
        Assert.Equal(100_000, response.Content.Headers.ContentRange?.Length);
    }

    [Fact]
    public async Task An_anonymous_put_is_rejected_with_403()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        string key = $"{StorageTestKit.NewPrefix()}/anonim.json";

        using HttpResponseMessage response = await Http.PutAsync(ObjectUrl(endpoint, key), new ByteArrayContent("{}"u8.ToArray()), ct);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
        Assert.Null(await store.HeadAsync(key, ct));
    }

    // ---------------------------------------------------------------- Listeleme

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task List_keys_filters_by_prefix_and_pages_through_all_results(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
            // Sayfa boyutu 2: bes anahtar uc sayfada gelir.
            using S3PackStore store = S3PackStore.Create(endpoint.ToOptions(), pageSize: 2);
            string prefix = StorageTestKit.NewPrefix();
            string[] mine = [.. Enumerable.Range(1, 5).Select(i => $"{prefix}/a/{i}.json")];
            string otherKey = $"{prefix}-baska/a/1.json";
            foreach (string key in mine)
            {
                await store.PutManifestAsync(key, "{}"u8.ToArray(), ct);
            }

            await store.PutManifestAsync(otherKey, "{}"u8.ToArray(), ct);

            List<string> listed = [];
            await foreach (string key in store.ListKeysAsync($"{prefix}/", ct))
            {
                listed.Add(key);
            }

            Assert.Equal(mine, listed);
            Assert.DoesNotContain(otherKey, listed);
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task List_keys_with_no_match_is_empty_and_null_safe(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            using S3PackStore store = S3PackStore.Create(await seaweed.OptionsAsync(ct));
            List<string> listed = [];

            await foreach (string key in store.ListKeysAsync($"{StorageTestKit.NewPrefix()}/yok/", ct))
            {
                listed.Add(key);
            }

            Assert.Empty(listed);
        });
    }

    // ---------------------------------------------------------------- Hata ayrimi

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Wrong_credentials_surface_as_storage_exception_access_denied(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
            StorageOptions wrong = new()
            {
                ServiceUrl = endpoint.ServiceUrl,
                AccessKey = endpoint.AccessKey,
                SecretKey = "yanlis-" + Guid.NewGuid().ToString("N", System.Globalization.CultureInfo.InvariantCulture),
                Bucket = endpoint.Bucket,
            };
            using S3PackStore store = S3PackStore.Create(wrong);

            StorageException head = await Assert.ThrowsAsync<StorageException>(() => store.HeadAsync("yok/anahtar.db", ct));
            StorageException put = await Assert.ThrowsAsync<StorageException>(
                () => store.PutManifestAsync("yok/manifest.json", "{}"u8.ToArray(), ct));

            Assert.Equal(StorageFailure.AccessDenied, head.Failure);
            Assert.Equal(StorageFailure.AccessDenied, put.Failure);
            Assert.DoesNotContain(wrong.SecretKey, head.ToString(), StringComparison.Ordinal);
            Assert.DoesNotContain(wrong.SecretKey, put.ToString(), StringComparison.Ordinal);
        });
    }

    [Fact]
    public async Task Measure_operations_on_a_bucket_that_was_never_created()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        StorageOptions options = new()
        {
            ServiceUrl = endpoint.ServiceUrl,
            AccessKey = endpoint.AccessKey,
            SecretKey = endpoint.SecretKey,
            Bucket = "kova-yok-" + Guid.NewGuid().ToString("N", System.Globalization.CultureInfo.InvariantCulture)[..8],
        };
        using S3PackStore store = S3PackStore.Create(options);

        // Olcum: SeaweedFS her islemde ne yapar? Hata gelirse StorageException olmali (Outcome baska istisnayi gecirmez).
        // Okumalar ONCE (PUT kovayi kendiliginden olusturabilir; sonra yapilan okuma anlamsiz olur).
        string head = await Outcome(async () => Describe(await store.HeadAsync("a/manifest.json", ct)));
        string get = await Outcome(async () => Describe(await store.GetAsync("a/manifest.json", ct)));
        string list = await Outcome(async () =>
        {
            int count = 0;
            await foreach (string key in store.ListKeysAsync("a/", ct))
            {
                count++;
                _ = key;
            }

            return $"ok, {count} keys";
        });
        string put = await Outcome(async () =>
        {
            await store.PutManifestAsync("a/manifest.json", "{}"u8.ToArray(), ct);
            return "ok";
        });
        string headAfterPut = await Outcome(async () => Describe(await store.HeadAsync("a/manifest.json", ct)));

        Note($"Measure: never-created bucket HEAD -> {head}; GET -> {get}; LIST -> {list}; PUT -> {put}; HEAD after PUT -> {headAfterPut}");

        // Olculen davranis SeaweedFS 4.48 icin sabitlenir (surum yukseltmesinde degisirse test haber verir): okumalar kova yoksa NotFound (HEAD null),
        // PUT kovayi kendiliginden olusturur ve ardindan nesne gorunur.
        Assert.Equal("ok, null", head);
        Assert.Equal("StorageException(NotFound)", get);
        Assert.Equal("StorageException(NotFound)", list);
        Assert.Equal("ok", put);
        Assert.Equal("ok, found", headAfterPut);
    }

    private static string Describe(object? result) => result is null ? "ok, null" : "ok, found";

    private static async Task<string> Outcome(Func<Task<string>> action)
    {
        try
        {
            return await action();
        }
        catch (StorageException ex)
        {
            return $"StorageException({ex.Failure})";
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_closed_service_surfaces_as_storage_exception_unavailable(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await StorageTestKit.RunAsync(turkish, async () =>
        {
            // Docker gerekmez: bos bir loopback portu al ve kapat; baglanti reddedilir.
            int port = FreePort();
            using S3PackStore store = S3PackStore.Create(new StorageOptions
            {
                ServiceUrl = $"http://127.0.0.1:{port.ToString(System.Globalization.CultureInfo.InvariantCulture)}",
                AccessKey = "test-access",
                SecretKey = "test-secret",
                Bucket = "test-bucket",
            });

            // SDK varsayilan yeniden denemesi (geri cekilmeli) yuzunden her cagri saniyeler surer; tek islem denenir.
            StorageException head = await Assert.ThrowsAsync<StorageException>(() => store.HeadAsync("a/b.db", ct));

            Assert.Equal(StorageFailure.Unavailable, head.Failure);
        });
    }

    [Fact]
    public async Task Cancellation_is_not_wrapped_in_storage_exception()
    {
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(TestContext.Current.CancellationToken);
        using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
        using CancellationTokenSource cancelled = new();
        await cancelled.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => store.HeadAsync("a/b.db", cancelled.Token));
    }

    private static int FreePort()
    {
        TcpListener listener = new(IPAddress.Loopback, 0);
        listener.Start();
        try
        {
            return ((IPEndPoint)listener.LocalEndpoint).Port;
        }
        finally
        {
            listener.Stop();
        }
    }

    // ---------------------------------------------------------------- Olcumler (A13.1 sinama raporu)

    [Fact]
    public async Task Measure_the_metadata_key_format_of_x_amz_meta_sha256()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        using S3PackStore store = S3PackStore.Create(endpoint.ToOptions());
        string key = $"{StorageTestKit.NewPrefix()}/{PackKeyTail}";
        byte[] bytes = StorageTestKit.SyntheticBytes(3_000, seed: 10);
        string sha = StorageTestKit.Sha256Hex(bytes);
        using TempFile file = await TempFile.CreateAsync(bytes, ct);
        await store.PutPackAsync(key, file.Path, sha, ct);

        // SDK tarafi: istemci ust veriyi hangi anahtarla verir?
        using AmazonS3Client raw = S3PackStore.CreateClient(endpoint.ToOptions());
        GetObjectMetadataResponse metadata = await raw.GetObjectMetadataAsync(new GetObjectMetadataRequest { BucketName = endpoint.Bucket, Key = key }, ct);
        string[] sdkKeys = [.. metadata.Metadata.Keys];
        Note($"Measure: SDK GetObjectMetadata Metadata.Keys = [{string.Join(", ", sdkKeys)}]");

        // Tel tarafi: HEAD yanitindaki baslik adi.
        using HttpRequestMessage head = new(HttpMethod.Head, ObjectUrl(endpoint, key));
        using HttpResponseMessage response = await Http.SendAsync(head, ct);
        string[] wireHeaders = [.. response.Headers.Select(h => h.Key).Where(n => n.StartsWith("x-amz-meta", StringComparison.OrdinalIgnoreCase))];
        Note($"Measure: HTTP HEAD x-amz-meta headers = [{string.Join(", ", wireHeaders)}]");
        response.Headers.TryGetValues("x-amz-meta-sha256", out IEnumerable<string>? values);
        Note($"Measure: HTTP HEAD x-amz-meta-sha256 = {string.Join(",", values ?? [])}");

        Assert.Single(sdkKeys);
        Assert.Contains("x-amz-meta-sha256", wireHeaders, StringComparer.OrdinalIgnoreCase);
        Assert.Equal(sha, Assert.Single(values!));
        Assert.Equal(sha, (await store.HeadAsync(key, ct))?.Sha256);
    }

    [Fact]
    public async Task Measure_checksum_behaviour_of_the_sdk_default_against_seaweedfs()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        SeaweedEndpoint endpoint = await seaweed.GetEndpointAsync(ct);
        byte[] bytes = StorageTestKit.SyntheticBytes(200_000, seed: 11);
        string prefix = StorageTestKit.NewPrefix();

        // SDK 4 varsayilani WHEN_SUPPORTED; urun WHEN_REQUIRED kullanir. Uc govde turu: aranabilir akis, ContentBody, aranamayan akis.
        foreach (RequestChecksumCalculation mode in new[] { RequestChecksumCalculation.WHEN_SUPPORTED, RequestChecksumCalculation.WHEN_REQUIRED })
        {
            AmazonS3Config config = new()
            {
                ServiceURL = endpoint.ServiceUrl,
                ForcePathStyle = true,
                AuthenticationRegion = "us-east-1",
                RequestChecksumCalculation = mode,
                ResponseChecksumValidation = mode == RequestChecksumCalculation.WHEN_SUPPORTED
                    ? ResponseChecksumValidation.WHEN_SUPPORTED
                    : ResponseChecksumValidation.WHEN_REQUIRED,
            };
            using AmazonS3Client client = new(new BasicAWSCredentials(endpoint.AccessKey, endpoint.SecretKey), config);
            foreach (string kind in new[] { "seekable-stream", "content-body", "non-seekable-stream" })
            {
                string result = await TryPutAsync(client, endpoint, $"{prefix}/{mode}/{kind}", bytes, kind, ct);
                Note($"Measure: {mode} PutObject {kind} -> {result}");

                // Urunun kullandigi mod (WHEN_REQUIRED) ve gercekten kullandigi govde turleri (aranabilir akis, ContentBody) saglama toplami sorunu cikarmamali.
                if (mode == RequestChecksumCalculation.WHEN_REQUIRED && kind != "non-seekable-stream")
                {
                    Assert.StartsWith("OK (HTTP 200, readback matches)", result, StringComparison.Ordinal);
                }
            }
        }

        // Bilgi testi: sonuc ne olursa olsun gecer; urun kodu (WHEN_REQUIRED, aranabilir dosya akisi) calismali.
        using S3PackStore product = S3PackStore.Create(endpoint.ToOptions());
        using TempFile file = await TempFile.CreateAsync(bytes, ct);
        Assert.Equal(PutResult.Uploaded, await product.PutPackAsync($"{prefix}/product.db", file.Path, StorageTestKit.Sha256Hex(bytes), ct));
    }

    private static async Task<string> TryPutAsync(AmazonS3Client client, SeaweedEndpoint endpoint, string key, byte[] bytes, string kind, CancellationToken ct)
    {
        try
        {
            using Stream stream = kind == "non-seekable-stream" ? new ForwardOnlyStream(bytes) : new MemoryStream(bytes);
            PutObjectRequest request = new() { BucketName = endpoint.Bucket, Key = key };
            if (kind == "content-body")
            {
                request.ContentBody = "Deneme paragrafi 1";
            }
            else
            {
                request.InputStream = stream;
                if (kind == "non-seekable-stream")
                {
                    request.Headers.ContentLength = bytes.Length;
                }
            }

            PutObjectResponse response = await client.PutObjectAsync(request, ct);
            using GetObjectResponse get = await client.GetObjectAsync(endpoint.Bucket, key, ct);
            using MemoryStream copy = new();
            await get.ResponseStream.CopyToAsync(copy, ct);
            bool same = kind == "content-body" || copy.ToArray().AsSpan().SequenceEqual(bytes);
            return $"OK (HTTP {(int)response.HttpStatusCode}, readback {(same ? "matches" : "DIFFERS")})";
        }
        catch (Exception ex) when (ex is AmazonServiceException or AmazonClientException)
        {
            return $"FAILED ({ex.GetType().Name}: {ex.Message})";
        }
    }

    /// <summary>Aranamayan okuma akisi (SDK'yi aws-chunked yoluna zorlar); yalniz olcum icin.</summary>
    private sealed class ForwardOnlyStream(byte[] bytes) : Stream
    {
        private readonly MemoryStream _inner = new(bytes);

        public override bool CanRead => true;

        public override bool CanSeek => false;

        public override bool CanWrite => false;

        public override long Length => throw new NotSupportedException();

        public override long Position
        {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }

        public override void Flush()
        {
        }

        public override int Read(byte[] buffer, int offset, int count) => _inner.Read(buffer, offset, count);

        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();

        public override void SetLength(long value) => throw new NotSupportedException();

        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _inner.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
