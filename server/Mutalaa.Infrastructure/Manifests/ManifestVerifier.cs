using System.Text.Json;
using MackySoft.Json.Canonicalization;
using NSec.Cryptography;

namespace Mutalaa.Infrastructure.Manifests;

/// <summary>Manifest denetim hatasi: kararli kod ve insan okur mesaj.</summary>
public sealed record ManifestError(string Code, string Message);

/// <summary>Kararli hata kodlari (komut katmani ve testler bunlara bakar; yeniden adlandirilmaz).</summary>
public static class ManifestErrorCodes
{
    public const string InvalidJson = "json-gecersiz";
    public const string SignatureMissing = "imza-yok";
    public const string SignatureAlgorithm = "imza-alg";
    public const string SignatureKid = "imza-kid";
    public const string SignatureBase64 = "imza-base64";
    public const string SignatureLength = "imza-uzunluk";
    public const string SignatureInvalid = "imza-gecersiz";
    public const string PublicKeyInvalid = "acik-anahtar-gecersiz";
    public const string SchemaMismatch = "sema-uyumsuz";
    public const string PackIdDuplicate = "pack-id-tekrar";
    public const string UrlMismatch = "url-uyumsuz";
}

/// <summary>Imza denetimi sonucu. IsValid ise Errors bostur.</summary>
public sealed record ManifestVerification(bool IsValid, IReadOnlyList<ManifestError> Errors)
{
    public static ManifestVerification Ok { get; } = new(true, []);

    public static ManifestVerification Fail(params ManifestError[] errors) => new(false, errors);
}

/// <summary>
/// Manifest imzasini acik anahtarla dogrular (K-45). Imza yoksa, alg ed25519 degilse, kid beklenenle uyusmuyorsa,
/// deger katil base64 ya da 64 bayt degilse ya da imza tutmuyorsa IsValid false olur; hepsi birlikte raporlanir
/// (imza hesabi yalniz onceki yapi denetimleri gecince yapilir). Bozuk JSON bir ManifestError'dur, istisna degildir.
/// </summary>
public static class ManifestVerifier
{
    public static ManifestVerification Verify(ReadOnlySpan<byte> manifestJson, ReadOnlySpan<byte> publicKey, string? expectedKid = null)
    {
        if (publicKey.Length != SigningKey.PublicKeyLength)
        {
            return ManifestVerification.Fail(new ManifestError(
                ManifestErrorCodes.PublicKeyInvalid,
                $"Acik anahtar {SigningKey.PublicKeyLength} bayt olmali (verilen: {publicKey.Length})."));
        }

        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(manifestJson.ToArray());
        }
        catch (JsonException ex)
        {
            return ManifestVerification.Fail(new ManifestError(ManifestErrorCodes.InvalidJson, "Manifest JSON degil: " + ex.Message));
        }

        using (document)
        {
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return ManifestVerification.Fail(new ManifestError(ManifestErrorCodes.InvalidJson, "Manifest kok degeri nesne degil."));
            }

            if (!root.TryGetProperty(ManifestCanonicalizer.SignatureProperty, out JsonElement signature)
                || signature.ValueKind != JsonValueKind.Object)
            {
                return ManifestVerification.Fail(new ManifestError(ManifestErrorCodes.SignatureMissing, "Manifestte signature alani yok."));
            }

            List<ManifestError> errors = [];
            CheckAlgorithm(signature, errors);
            CheckKid(signature, expectedKid, errors);
            byte[] signatureBytes = DecodeValue(signature, errors);

            if (errors.Count > 0)
            {
                return new ManifestVerification(false, errors);
            }

            byte[] canonical;
            try
            {
                canonical = ManifestCanonicalizer.Canonicalize(root);
            }
            catch (Exception ex) when (ex is JsonException or JsonCanonicalizationException or InvalidOperationException)
            {
                return ManifestVerification.Fail(new ManifestError(ManifestErrorCodes.InvalidJson, "Manifest kanoniklestirilemedi: " + ex.Message));
            }

            PublicKey key = PublicKey.Import(SignatureAlgorithm.Ed25519, publicKey, KeyBlobFormat.RawPublicKey);
            return SignatureAlgorithm.Ed25519.Verify(key, canonical, signatureBytes)
                ? ManifestVerification.Ok
                : ManifestVerification.Fail(new ManifestError(ManifestErrorCodes.SignatureInvalid, "Imza acik anahtarla dogrulanmadi."));
        }
    }

    private static void CheckAlgorithm(JsonElement signature, List<ManifestError> errors)
    {
        bool ok = signature.TryGetProperty("alg", out JsonElement alg)
            && alg.ValueKind == JsonValueKind.String
            && string.Equals(alg.GetString(), ManifestSigner.Algorithm, StringComparison.Ordinal);
        if (!ok)
        {
            errors.Add(new ManifestError(ManifestErrorCodes.SignatureAlgorithm, $"signature.alg '{ManifestSigner.Algorithm}' olmali."));
        }
    }

    private static void CheckKid(JsonElement signature, string? expectedKid, List<ManifestError> errors)
    {
        string? kid = signature.TryGetProperty("kid", out JsonElement element) && element.ValueKind == JsonValueKind.String
            ? element.GetString()
            : null;
        if (string.IsNullOrEmpty(kid))
        {
            errors.Add(new ManifestError(ManifestErrorCodes.SignatureKid, "signature.kid yok ya da bos."));
        }
        else if (expectedKid is not null && !string.Equals(kid, expectedKid, StringComparison.Ordinal))
        {
            errors.Add(new ManifestError(ManifestErrorCodes.SignatureKid, $"signature.kid beklenenle uyusmuyor (beklenen: {expectedKid}, gelen: {kid})."));
        }
    }

    private static byte[] DecodeValue(JsonElement signature, List<ManifestError> errors)
    {
        string? value = signature.TryGetProperty("value", out JsonElement element) && element.ValueKind == JsonValueKind.String
            ? element.GetString()
            : null;
        if (!Base64Strict.TryDecode(value, out byte[] bytes))
        {
            errors.Add(new ManifestError(ManifestErrorCodes.SignatureBase64, "signature.value gecerli base64 degil."));
            return [];
        }

        if (bytes.Length != ManifestSigner.SignatureLength)
        {
            errors.Add(new ManifestError(
                ManifestErrorCodes.SignatureLength,
                $"signature.value {ManifestSigner.SignatureLength} bayt olmali (cozulen: {bytes.Length})."));
        }

        return bytes;
    }
}
