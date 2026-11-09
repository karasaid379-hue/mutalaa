using System.Net;
using System.Reflection;
using Amazon.S3;
using Amazon.S3.Model;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Elle yazilmis IAmazonS3 sahtesi (Docker'siz): yalniz S3PackStore'un kullandigi iki cagriyi (GetObjectMetadataAsync, PutObjectAsync) uygular, gerisi
/// NotSupportedException. Nesne durumu bellekte tutulur; <see cref="Persist"/> PUT sonrasi depoda NE kalacagini belirler (bozuk yukleme senaryolari).
/// DispatchProxy ile uretilir (arayuzun yuzlerce uyesi elle yazilmaz); bu yuzden sinif genel ve miras alinabilirdir.
/// </summary>
public class FakeS3Client : DispatchProxy
{
    /// <summary>PUT sonrasi depoda kalan nesne: (boyut, sha256 ust verisi). null donerse nesne hic yazilmamis sayilir (HEAD 404).</summary>
    public delegate (long Size, string? Sha256)? PersistRule(string key, long receivedSize, string? sha256);

    public Dictionary<string, (long Size, string? Sha256)> Objects { get; } = new(StringComparer.Ordinal);

    public PersistRule Persist { get; set; } = (_, size, sha) => (size, sha);

    public int PutCount { get; private set; }

    public int HeadCount { get; private set; }

    public static (IAmazonS3 Client, FakeS3Client Fake) Create()
    {
        IAmazonS3 client = Create<IAmazonS3, FakeS3Client>();
        return (client, (FakeS3Client)(object)client);
    }

    protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
    {
        ArgumentNullException.ThrowIfNull(targetMethod);
        ArgumentNullException.ThrowIfNull(args);

        switch (targetMethod.Name)
        {
            case "GetObjectMetadataAsync" when args[0] is GetObjectMetadataRequest head:
                HeadCount++;
                return Head(head.Key);
            case "PutObjectAsync" when args[0] is PutObjectRequest put:
                return PutAsync(put);
            default:
                throw new NotSupportedException($"Sahte IAmazonS3 {targetMethod.Name} cagrisini desteklemiyor.");
        }
    }

    private Task<GetObjectMetadataResponse> Head(string key)
    {
        if (!Objects.TryGetValue(key, out (long Size, string? Sha256) stored))
        {
            return Task.FromException<GetObjectMetadataResponse>(new AmazonS3Exception("bulunamadi") { StatusCode = HttpStatusCode.NotFound, ErrorCode = "NotFound" });
        }

        GetObjectMetadataResponse response = new();
        response.ContentLength = stored.Size;
        if (stored.Sha256 is not null)
        {
            response.Metadata["x-amz-meta-sha256"] = stored.Sha256;
        }

        return Task.FromResult(response);
    }

    private async Task<PutObjectResponse> PutAsync(PutObjectRequest request)
    {
        PutCount++;
        using MemoryStream received = new();
        await request.InputStream.CopyToAsync(received);

        string? sha = null;
        foreach (string name in request.Metadata.Keys)
        {
            if (name.EndsWith("sha256", StringComparison.OrdinalIgnoreCase))
            {
                sha = request.Metadata[name];
            }
        }

        (long Size, string? Sha256)? stored = Persist(request.Key, received.Length, sha);
        if (stored is { } value)
        {
            Objects[request.Key] = value;
        }

        return new PutObjectResponse { HttpStatusCode = HttpStatusCode.OK };
    }
}
