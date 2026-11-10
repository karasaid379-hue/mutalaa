using System.Net;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Releases;
using Mutalaa.Api.Settings;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Api.Tests;

/// <summary>
/// HttpPreviousPackResolver (Docker gerekmez; sahte HttpMessageHandler): yerel -> onbellek -> adres sirasi, sha256 ve boyut denetimi,
/// zaman asimi, gecersiz adres ve manifest girdileri. Paket baytlari sentetiktir.
/// </summary>
public sealed class HttpPreviousPackResolverTests : IDisposable
{
    private const string Url = "https://depo.example.test/packs/dev/core/2026.11.0/core-2026.11.0.db?imza=cok-gizli-sorgu";

    private static readonly byte[] PackBytes = System.Text.Encoding.UTF8.GetBytes(string.Concat(Enumerable.Repeat("Deneme paket baytlari. ", 40)));

    private readonly string _root = Path.Combine(Path.GetTempPath(), "mutalaa-api-tests", Guid.NewGuid().ToString("N"));

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private string PacksDir => Path.Combine(_root, "packs");

    private string TempDir => Path.Combine(_root, "tmp");

    public void Dispose()
    {
        try
        {
            Directory.Delete(_root, recursive: true);
        }
        catch (IOException)
        {
            // Gecici klasor; sistem temizler.
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private static ManifestPack Pack(byte[]? bytes = null, string url = Url, string packId = "core", string version = "2026.11.0", string? sha = null)
    {
        bytes ??= PackBytes;
        return new ManifestPack(packId, version, sha ?? PackFiles.Sha256(bytes), bytes.Length, "1.0.0", [], url, 1);
    }

    private string LocalPath(ManifestPack pack) => PackFiles.LocalPackPath(PacksDir, "dev", pack.PackId, pack.Version);

    private string CachePath(ManifestPack pack) =>
        Path.Combine(TempDir, "previous", "dev", $"{pack.PackId}-{pack.Version}-{pack.Sha256[..12]}.db");

    private HttpPreviousPackResolver Resolver(StubHandler handler, TimeSpan? timeout = null) =>
        new(
            Options.Create(new ApiOptions { PacksDir = PacksDir, TempDir = TempDir }),
            new StubClientFactory(handler),
            NullLogger<HttpPreviousPackResolver>.Instance)
        {
            Timeout = timeout ?? HttpPreviousPackResolver.DownloadTimeout,
        };

    private static StubHandler Serving(byte[] bytes, HttpStatusCode status = HttpStatusCode.OK) =>
        new((_, _) => Task.FromResult(new HttpResponseMessage(status) { Content = new ByteArrayContent(bytes) }));

    private static StubHandler MustNotBeCalled() =>
        new((_, _) => throw new InvalidOperationException("Ag cagrisi beklenmiyordu."));

    private static async Task<GatePlanException> FailureAsync(Task<string> call) => await Assert.ThrowsAsync<GatePlanException>(() => call);

    private static void WriteFile(string path, byte[] bytes)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path, bytes);
    }

    // --- Yerel ve onbellek ---

    [Fact]
    public async Task A_pack_found_locally_is_used_without_any_network_call()
    {
        ManifestPack pack = Pack();
        WriteFile(LocalPath(pack), PackBytes);
        StubHandler handler = MustNotBeCalled();

        string path = await Resolver(handler).ResolveAsync("dev", pack, Ct);

        Assert.Equal(LocalPath(pack), path);
        Assert.Equal(0, handler.Calls);
    }

    [Fact]
    public async Task A_local_file_with_another_sha256_is_ignored_and_the_cache_is_tried_next()
    {
        ManifestPack pack = Pack();
        WriteFile(LocalPath(pack), [1, 2, 3]);
        WriteFile(CachePath(pack), PackBytes);
        StubHandler handler = MustNotBeCalled();

        string path = await Resolver(handler).ResolveAsync("dev", pack, Ct);

        Assert.Equal(CachePath(pack), path);
        Assert.Equal(0, handler.Calls);
    }

    [Fact]
    public async Task A_cached_pack_with_a_matching_sha256_is_used_without_any_network_call()
    {
        ManifestPack pack = Pack();
        WriteFile(CachePath(pack), PackBytes);
        StubHandler handler = MustNotBeCalled();

        Assert.Equal(CachePath(pack), await Resolver(handler).ResolveAsync("dev", pack, Ct));
        Assert.Equal(0, handler.Calls);
    }

    // --- Indirme ---

    [Fact]
    public async Task A_missing_pack_is_downloaded_to_the_cache_with_a_matching_sha256_and_then_served_from_it()
    {
        ManifestPack pack = Pack();
        StubHandler handler = Serving(PackBytes);
        HttpPreviousPackResolver resolver = Resolver(handler);

        string first = await resolver.ResolveAsync("dev", pack, Ct);
        string second = await resolver.ResolveAsync("dev", pack, Ct);

        Assert.Equal(CachePath(pack), first);
        Assert.Equal(first, second);
        Assert.Equal(PackBytes, await File.ReadAllBytesAsync(first, Ct));
        Assert.Equal(1, handler.Calls);
        Assert.Equal([first], Directory.GetFiles(Path.GetDirectoryName(first)!));
    }

    [Fact]
    public async Task A_download_whose_sha256_differs_from_the_manifest_is_a_mismatch_and_leaves_nothing_behind()
    {
        byte[] other = [.. PackBytes];
        other[0] ^= 0xFF;
        ManifestPack pack = Pack();
        HttpPreviousPackResolver resolver = Resolver(Serving(other));

        GatePlanException failure = await FailureAsync(resolver.ResolveAsync("dev", pack, Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMismatch, failure.Failure);
        Assert.False(File.Exists(CachePath(pack)));
        Assert.Empty(Directory.GetFiles(Path.GetDirectoryName(CachePath(pack))!));
    }

    [Fact]
    public async Task A_declared_length_above_the_manifest_size_is_a_mismatch()
    {
        ManifestPack pack = Pack();
        byte[] bigger = [.. PackBytes, .. PackBytes];
        HttpPreviousPackResolver resolver = Resolver(Serving(bigger));

        GatePlanException failure = await FailureAsync(resolver.ResolveAsync("dev", pack, Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMismatch, failure.Failure);
        Assert.False(File.Exists(CachePath(pack)));
    }

    [Fact]
    public async Task A_stream_without_a_length_that_exceeds_the_manifest_size_is_cut_off_and_is_a_mismatch()
    {
        ManifestPack pack = Pack();
        StubHandler handler = new((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new UnknownLengthContent([.. PackBytes, .. PackBytes]),
        }));

        GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", pack, Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMismatch, failure.Failure);
        Assert.Empty(Directory.GetFiles(Path.GetDirectoryName(CachePath(pack))!));
    }

    [Fact]
    public async Task A_download_shorter_than_the_manifest_size_is_a_mismatch()
    {
        ManifestPack pack = Pack();
        HttpPreviousPackResolver resolver = Resolver(Serving(PackBytes[..^1]));

        GatePlanException failure = await FailureAsync(resolver.ResolveAsync("dev", pack, Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMismatch, failure.Failure);
    }

    [Theory]
    [InlineData(HttpStatusCode.NotFound)]
    [InlineData(HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.InternalServerError)]
    public async Task A_non_success_status_is_a_missing_pack(HttpStatusCode status)
    {
        HttpPreviousPackResolver resolver = Resolver(Serving([], status));

        GatePlanException failure = await FailureAsync(resolver.ResolveAsync("dev", Pack(), Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMissing, failure.Failure);
    }

    [Fact]
    public async Task An_unreachable_address_is_a_missing_pack()
    {
        StubHandler handler = new((_, _) => throw new HttpRequestException("baglanti reddedildi"));

        GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", Pack(), Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMissing, failure.Failure);
        Assert.IsType<HttpRequestException>(failure.InnerException);
    }

    [Fact]
    public async Task A_response_that_does_not_arrive_within_the_timeout_is_a_missing_pack()
    {
        StubHandler handler = new(async (_, ct) =>
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, ct);
            return new HttpResponseMessage(HttpStatusCode.OK);
        });

        GatePlanException failure = await FailureAsync(Resolver(handler, TimeSpan.FromMilliseconds(200)).ResolveAsync("dev", Pack(), Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMissing, failure.Failure);
    }

    [Fact]
    public async Task A_cancelled_request_surfaces_as_cancellation_not_as_a_gate_failure()
    {
        StubHandler handler = new(async (_, ct) =>
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, ct);
            return new HttpResponseMessage(HttpStatusCode.OK);
        });
        using CancellationTokenSource cts = CancellationTokenSource.CreateLinkedTokenSource(Ct);
        Task<string> call = Resolver(handler).ResolveAsync("dev", Pack(), cts.Token);
        await cts.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => call);
    }

    [Theory]
    [InlineData("ftp://depo.example.test/core.db")]
    [InlineData("file:///etc/passwd")]
    [InlineData("javascript:alert(1)")]
    [InlineData("/goreli/yol.db")]
    [InlineData("")]
    public async Task Only_absolute_http_and_https_addresses_are_downloaded(string url)
    {
        StubHandler handler = MustNotBeCalled();

        GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", Pack(url: url), Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMissing, failure.Failure);
        Assert.Equal(0, handler.Calls);
    }

    [Fact]
    public async Task Failure_messages_never_contain_the_address()
    {
        foreach (StubHandler handler in new[]
        {
            Serving([], HttpStatusCode.NotFound),
            new StubHandler((_, _) => throw new HttpRequestException("hata " + Url)),
            Serving([.. PackBytes, .. PackBytes]),
        })
        {
            GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", Pack(), Ct));

            Assert.DoesNotContain("cok-gizli-sorgu", failure.Message, StringComparison.Ordinal);
            Assert.DoesNotContain("depo.example.test", failure.Message, StringComparison.Ordinal);
        }
    }

    // --- Manifest girdisi ---

    [Theory]
    [InlineData("../core")]
    [InlineData("Core")]
    [InlineData("a/b")]
    [InlineData("")]
    public async Task An_invalid_pack_id_in_the_manifest_never_becomes_a_file_path(string packId)
    {
        StubHandler handler = MustNotBeCalled();

        GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", Pack(packId: packId), Ct));

        Assert.Equal(GatePlanFailure.ManifestUnreadable, failure.Failure);
        Assert.Equal(0, handler.Calls);
        Assert.False(Directory.Exists(_root));
    }

    [Theory]
    [InlineData("2026.11")]
    [InlineData("2026.011.0")]
    [InlineData("..\\2026.11.0")]
    public async Task An_invalid_version_in_the_manifest_is_unreadable(string version)
    {
        GatePlanException failure = await FailureAsync(Resolver(MustNotBeCalled()).ResolveAsync("dev", Pack(version: version), Ct));

        Assert.Equal(GatePlanFailure.ManifestUnreadable, failure.Failure);
    }

    [Theory]
    [InlineData("")]
    [InlineData("ABCDEF")]
    [InlineData("0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF")]
    public async Task A_malformed_sha256_in_the_manifest_is_unreadable(string sha)
    {
        GatePlanException failure = await FailureAsync(Resolver(MustNotBeCalled()).ResolveAsync("dev", Pack(sha: sha), Ct));

        Assert.Equal(GatePlanFailure.ManifestUnreadable, failure.Failure);
    }

    [Fact]
    public async Task An_unknown_flavor_label_is_rejected_before_any_file_access()
    {
        await Assert.ThrowsAsync<ArgumentException>(() => Resolver(MustNotBeCalled()).ResolveAsync("../dev", Pack(), Ct));
    }

    [Fact]
    public async Task A_manifest_size_of_zero_or_less_cannot_be_downloaded()
    {
        ManifestPack pack = Pack() with { SizeBytes = 0 };
        StubHandler handler = MustNotBeCalled();

        GatePlanException failure = await FailureAsync(Resolver(handler).ResolveAsync("dev", pack, Ct));

        Assert.Equal(GatePlanFailure.PreviousPackMismatch, failure.Failure);
        Assert.Equal(0, handler.Calls);
    }

    // --- Sahte ag (StubHandler ve StubClientFactory: Support/StubHttp.cs) ---

    /// <summary>Content-Length bildirmeyen icerik (parcali aktarim benzeri).</summary>
    private sealed class UnknownLengthContent(byte[] bytes) : HttpContent
    {
        protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context) => stream.WriteAsync(bytes, 0, bytes.Length);

        protected override bool TryComputeLength(out long length)
        {
            length = 0;
            return false;
        }
    }
}
