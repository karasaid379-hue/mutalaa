using System.Net;
using System.Runtime.CompilerServices;
using Amazon.Runtime;
using Amazon.S3;
using Amazon.S3.Model;

namespace Mutalaa.Infrastructure.Storage;

/// <summary>
/// AWSSDK.S3 ile S3 uyumlu depo (SeaweedFS, Backend API 10.5). ServiceURL ve ForcePathStyle = true; saglama toplami
/// ayarlari ACIKCA WHEN_REQUIRED: SDK 4 varsayilani WHEN_SUPPORTED aws-chunked/trailer ile gonderir ve S3 uyumlu depolarda
/// sorun cikarabilir (SeaweedFS issue 11528, 11582, 11583, 11640, 11655). Yeniden deneme SDK varsayilanidir.
/// Hata ayrimi: 403 AccessDenied, kova/baska 404 NotFound, baglanti ve 5xx Unavailable; hepsi StorageException.
/// Check-then-put atomik degildir; tek Yayinlayici calisir (danisma kilidi, Backend API 10.6).
/// </summary>
public sealed class S3PackStore : IPackStore, IDisposable
{
    /// <summary>Bolge yalniz imza icindir; ServiceURL verildiginde adres bolgeden turetilmez.</summary>
    internal const string SigningRegion = "us-east-1";

    private const int DefaultPageSize = 1000;

    private readonly IAmazonS3 _client;
    private readonly bool _ownsClient;
    private readonly string _bucket;
    private readonly int _pageSize;

    /// <summary>Hazir istemciyle (test ve ozel kurulum); istemci bu sinifa ait degildir.</summary>
    public S3PackStore(IAmazonS3 client, string bucket, int pageSize = DefaultPageSize)
        : this(client, bucket, pageSize, ownsClient: false)
    {
    }

    private S3PackStore(IAmazonS3 client, string bucket, int pageSize, bool ownsClient)
    {
        ArgumentNullException.ThrowIfNull(client);
        ArgumentException.ThrowIfNullOrWhiteSpace(bucket);
        ArgumentOutOfRangeException.ThrowIfLessThan(pageSize, 1);

        _client = client;
        _bucket = bucket;
        _pageSize = pageSize;
        _ownsClient = ownsClient;
    }

    /// <summary>Ayarlardan istemci kurar; istemciyi bu nesne kapatir.</summary>
    public static S3PackStore Create(StorageOptions options, int pageSize = DefaultPageSize)
    {
        ArgumentNullException.ThrowIfNull(options);
        options.Validate();

        return new S3PackStore(CreateClient(options), options.Bucket, pageSize, ownsClient: true);
    }

    /// <summary>Urun ayarlariyla AmazonS3Client (testler de ayni ayari kullanir).</summary>
    public static AmazonS3Client CreateClient(StorageOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);

        AmazonS3Config config = new()
        {
            ServiceURL = options.ServiceUrl,
            ForcePathStyle = true,
            AuthenticationRegion = SigningRegion,
            RequestChecksumCalculation = RequestChecksumCalculation.WHEN_REQUIRED,
            ResponseChecksumValidation = ResponseChecksumValidation.WHEN_REQUIRED,
        };
        return new AmazonS3Client(new BasicAWSCredentials(options.AccessKey, options.SecretKey), config);
    }

    public void Dispose()
    {
        if (_ownsClient)
        {
            _client.Dispose();
        }
    }

    public async Task<PutResult> PutPackAsync(string key, string filePath, string sha256, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);
        ArgumentException.ThrowIfNullOrWhiteSpace(filePath);
        RequireSha256(sha256);

        long size = new FileInfo(filePath).Length;

        StoredObject? existing = await HeadAsync(key, cancellationToken);
        if (existing is not null)
        {
            if (existing.Sha256 is not null && string.Equals(existing.Sha256, sha256, StringComparison.OrdinalIgnoreCase))
            {
                // Ust veri tek basina yetmez: onceki bozuk bir yukleme (Integrity) sha256 ust verisini dogru, boyutu yanlis birakmis olabilir; o nesne "ayni" sayilmaz.
                if (existing.Size != size)
                {
                    throw new StorageException(StorageFailure.Integrity, $"Depodaki {key} ayni sha256 ust verisini tasiyor ama boyutu uyusmuyor (beklenen: {size}, depoda: {existing.Size}).");
                }

                return PutResult.SkippedSame;
            }

            throw new ObjectConflictException(key, existing.Sha256, sha256);
        }

        // Akis acik kalinca Windows dosyayi kilitler; using ile PUT biter bitmez kapanir.
        FileStream stream = new(filePath, FileMode.Open, FileAccess.Read, FileShare.Read, bufferSize: 81920, FileOptions.Asynchronous | FileOptions.SequentialScan);
        await using (stream)
        {
            PutObjectRequest request = new()
            {
                BucketName = _bucket,
                Key = key,
                InputStream = stream,
                AutoCloseStream = false,
                ContentType = StorageKeys.PackContentType,
            };
            request.Headers.CacheControl = StorageKeys.PackCacheControl;
            request.Metadata[StorageKeys.Sha256MetadataName] = sha256;

            await Call("PUT", key, () => _client.PutObjectAsync(request, cancellationToken), cancellationToken);
        }

        StoredObject? stored = await HeadAsync(key, cancellationToken);
        if (stored is null)
        {
            throw new StorageException(StorageFailure.Integrity, $"Yukleme sonrasi {key} bulunamadi.");
        }

        if (stored.Size != size)
        {
            throw new StorageException(StorageFailure.Integrity, $"Yukleme sonrasi {key} boyutu uyusmuyor (beklenen: {size}, depoda: {stored.Size}).");
        }

        if (stored.Sha256 is null || !string.Equals(stored.Sha256, sha256, StringComparison.OrdinalIgnoreCase))
        {
            throw new StorageException(StorageFailure.Integrity, $"Yukleme sonrasi {key} sha256 ust verisi uyusmuyor (beklenen: {sha256}, depoda: {stored.Sha256 ?? "yok"}).");
        }

        return PutResult.Uploaded;
    }

    public async Task<StoredObject?> HeadAsync(string key, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);

        GetObjectMetadataResponse response;
        try
        {
            response = await _client.GetObjectMetadataAsync(new GetObjectMetadataRequest { BucketName = _bucket, Key = key }, cancellationToken);
        }
        catch (AmazonS3Exception ex) when (ex.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }
        catch (Exception ex) when (IsStorageFailure(ex, cancellationToken))
        {
            throw Wrap(ex, "HEAD", key);
        }

        return new StoredObject(response.ContentLength, ReadSha256(response.Metadata));
    }

    public async Task PutManifestAsync(string key, ReadOnlyMemory<byte> json, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);

        using MemoryStream stream = new(json.ToArray(), writable: false);
        PutObjectRequest request = new()
        {
            BucketName = _bucket,
            Key = key,
            InputStream = stream,
            AutoCloseStream = false,
            ContentType = StorageKeys.ManifestContentType,
        };
        request.Headers.CacheControl = StorageKeys.ManifestCacheControl;

        await Call("PUT", key, () => _client.PutObjectAsync(request, cancellationToken), cancellationToken);
    }

    public async Task<byte[]?> GetAsync(string key, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);

        try
        {
            using GetObjectResponse response = await _client.GetObjectAsync(new GetObjectRequest { BucketName = _bucket, Key = key }, cancellationToken);
            using MemoryStream buffer = new();
            await response.ResponseStream.CopyToAsync(buffer, cancellationToken);
            return buffer.ToArray();
        }
        catch (AmazonS3Exception ex) when (ex.StatusCode == HttpStatusCode.NotFound && IsNoSuchKey(ex))
        {
            return null;
        }
        catch (Exception ex) when (IsStorageFailure(ex, cancellationToken))
        {
            throw Wrap(ex, "GET", key);
        }
        catch (IOException ex)
        {
            throw new StorageException(StorageFailure.Unavailable, $"GET {key}: govde okunamadi.", ex);
        }
    }

    public async IAsyncEnumerable<string> ListKeysAsync(string prefix, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(prefix);

        string? token = null;
        while (true)
        {
            ListObjectsV2Request request = new()
            {
                BucketName = _bucket,
                Prefix = prefix,
                MaxKeys = _pageSize,
                ContinuationToken = token,
            };
            ListObjectsV2Response response = await Call("LIST", prefix, () => _client.ListObjectsV2Async(request, cancellationToken), cancellationToken);

            // AWSSDK 4: koleksiyonlar varsayilan null; bos sayfada S3Objects null gelebilir.
            foreach (S3Object item in response.S3Objects ?? [])
            {
                if (item.Key is not null)
                {
                    yield return item.Key;
                }
            }

            if (response.IsTruncated != true || string.IsNullOrEmpty(response.NextContinuationToken))
            {
                yield break;
            }

            token = response.NextContinuationToken;
        }
    }

    // Sorgu: SDK 4'te deger turleri nullable; NoSuchKey ile NoSuchBucket ayrilir (kova yoksa nesne okuma null degil hatadir).
    private static bool IsNoSuchKey(AmazonS3Exception ex) =>
        !string.Equals(ex.ErrorCode, "NoSuchBucket", StringComparison.Ordinal);

    // x-amz-meta-sha256: SDK yanitta anahtari "x-amz-meta-sha256" ya da "sha256" olarak verebilir; iki bicim de ve buyuk/kucuk harf kabul edilir.
    private static string? ReadSha256(MetadataCollection? metadata)
    {
        if (metadata is null)
        {
            return null;
        }

        foreach (string name in metadata.Keys)
        {
            if (string.Equals(name, StorageKeys.Sha256MetadataName, StringComparison.OrdinalIgnoreCase)
                || string.Equals(name, "x-amz-meta-" + StorageKeys.Sha256MetadataName, StringComparison.OrdinalIgnoreCase))
            {
                string? value = metadata[name];
                return string.IsNullOrWhiteSpace(value) ? null : value;
            }
        }

        return null;
    }

    private static void RequireSha256(string sha256)
    {
        ArgumentException.ThrowIfNullOrEmpty(sha256);
        if (sha256.Length != 64 || !sha256.All(c => c is (>= '0' and <= '9') or (>= 'a' and <= 'f')))
        {
            throw new ArgumentException("sha256 kucuk harf onaltilik 64 karakter olmali.", nameof(sha256));
        }
    }

    private static async Task<TResponse> Call<TResponse>(string operation, string key, Func<Task<TResponse>> action, CancellationToken cancellationToken)
    {
        try
        {
            return await action();
        }
        catch (Exception ex) when (IsStorageFailure(ex, cancellationToken))
        {
            throw Wrap(ex, operation, key);
        }
    }

    // AWSSDK 4'te AmazonServiceException (yanit var) ve AmazonClientException (yanit yok) kardes siniflardir; ikisi de sarilir.
    // Baglanti reddi SDK'dan ham HttpRequestException ve SocketException olarak gelir (olculdu), govde okuma kopmasi (yalniz GET) IOException,
    // HttpClient zaman asimi TaskCanceledException; hepsi Unavailable. Cagiranin kendi iptali sarilmaz.
    private static bool IsStorageFailure(Exception ex, CancellationToken cancellationToken) => ex switch
    {
        AmazonServiceException or AmazonClientException => true,
        HttpRequestException or System.Net.Sockets.SocketException or TimeoutException => true,
        OperationCanceledException => !cancellationToken.IsCancellationRequested,
        _ => false,
    };

    // Baglanti reddi, zaman asimi ve 5xx Unavailable; 403 AccessDenied; 404 NotFound; kalan 4xx Other.
    private static StorageException Wrap(Exception ex, string operation, string key)
    {
        if (ex is AmazonServiceException service)
        {
            int status = (int)service.StatusCode;
            string code = string.IsNullOrEmpty(service.ErrorCode) ? status.ToString(System.Globalization.CultureInfo.InvariantCulture) : service.ErrorCode;
            if (service.StatusCode == HttpStatusCode.Forbidden)
            {
                return new StorageException(StorageFailure.AccessDenied, $"{operation} {key}: erisim reddedildi ({code}).", ex);
            }

            if (service.StatusCode == HttpStatusCode.NotFound)
            {
                return new StorageException(StorageFailure.NotFound, $"{operation} {key}: bulunamadi ({code}).", ex);
            }

            if (status >= 500)
            {
                return new StorageException(StorageFailure.Unavailable, $"{operation} {key}: depo hatasi ({code}).", ex);
            }

            if (status > 0)
            {
                return new StorageException(StorageFailure.Other, $"{operation} {key}: depo istegi reddetti ({code}).", ex);
            }
        }

        // Yanit yok: baglanti reddi, DNS, zaman asimi (SDK AmazonServiceException ya da AmazonClientException sarar).
        return new StorageException(StorageFailure.Unavailable, $"{operation} {key}: depoya ulasilamadi.", ex);
    }
}
