using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Manifests;
using NSec.Cryptography;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>
/// Ed25519 imzasi (K-45). RFC 8032 7.1 TEST 1 vektoru NSec'in her platformda (Windows, Linux CI) yuklendigini ve dogru
/// calistigini kanitlar; gerisi imzali manifestin gidis-donusu ve bozulma durumlaridir.
/// </summary>
public class ManifestSignatureTests
{
    private static JsonObject SignedNode() => JsonNode.Parse(ImzaFixture.SignedManifest())!.AsObject();

    private static byte[] Bytes(JsonNode node) => Encoding.UTF8.GetBytes(node.ToJsonString());

    private static ManifestVerification Verify(byte[] manifest, string? expectedKid = ImzaFixture.Kid) =>
        ManifestVerifier.Verify(manifest, ImzaFixture.PublicKey(), expectedKid);

    private static string[] Codes(ManifestVerification result) => [.. result.Errors.Select(e => e.Code)];

    // ---- RFC 8032 7.1 TEST 1 ----

    [Fact]
    public void Rfc8032_test1_seed_gives_the_published_public_key()
    {
        SigningKey key = new(Convert.FromHexString(ImzaFixture.SeedHex), ImzaFixture.Kid);

        Assert.Equal(ImzaFixture.PublicKeyHex, Base64Strict.ToHex(key.GetPublicKey()));
    }

    [Fact]
    public void Rfc8032_test1_empty_message_signature_matches_byte_for_byte()
    {
        using Key key = Key.Import(
            SignatureAlgorithm.Ed25519,
            Convert.FromHexString(ImzaFixture.SeedHex),
            KeyBlobFormat.RawPrivateKey);

        byte[] signature = SignatureAlgorithm.Ed25519.Sign(key, ReadOnlySpan<byte>.Empty);

        Assert.Equal(ImzaFixture.EmptyMessageSignatureHex, Base64Strict.ToHex(signature));
        PublicKey publicKey = PublicKey.Import(SignatureAlgorithm.Ed25519, ImzaFixture.PublicKey(), KeyBlobFormat.RawPublicKey);
        Assert.True(SignatureAlgorithm.Ed25519.Verify(publicKey, ReadOnlySpan<byte>.Empty, signature));
    }

    // ---- Gidis-donus ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_signed_manifest_verifies_with_the_public_key_and_expected_kid(bool turkish)
    {
        ManifestVerification? result = null;

        CultureScope.For(turkish, () => result = Verify(ImzaFixture.SignedManifest()));

        Assert.NotNull(result);
        Assert.True(result.IsValid);
        Assert.Empty(result.Errors);
    }

    [Fact]
    public void The_signature_object_is_last_and_has_alg_kid_and_a_64_byte_value()
    {
        using JsonDocument document = JsonDocument.Parse(ImzaFixture.SignedManifest());

        JsonProperty last = document.RootElement.EnumerateObject().Last();
        Assert.Equal("signature", last.Name);
        Assert.Equal(["alg", "kid", "value"], last.Value.EnumerateObject().Select(p => p.Name).ToArray());
        Assert.Equal("ed25519", last.Value.GetProperty("alg").GetString());
        Assert.Equal(ImzaFixture.Kid, last.Value.GetProperty("kid").GetString());
        Assert.True(Base64Strict.TryDecode(last.Value.GetProperty("value").GetString(), out byte[] value));
        Assert.Equal(64, value.Length);
    }

    [Fact]
    public void Same_input_gives_the_same_signed_bytes()
    {
        Assert.Equal(ImzaFixture.SignedManifest(), ImzaFixture.SignedManifest());
    }

    [Fact]
    public void Reformatting_the_signed_manifest_keeps_the_signature_valid()
    {
        // Imza kanonik baytlar uzerindedir: bosluk ve girinti degisimi imzayi bozmaz.
        byte[] compact = Bytes(SignedNode());

        Assert.NotEqual(ImzaFixture.SignedManifest(), compact);
        Assert.True(Verify(compact).IsValid);
    }

    [Fact]
    public void The_canonical_input_excludes_only_the_signature()
    {
        byte[] fromSigned = ManifestCanonicalizer.Canonicalize(ImzaFixture.SignedManifest());
        byte[] fromUnsigned = ManifestCanonicalizer.Canonicalize(ImzaFixture.UnsignedManifest());

        Assert.Equal(fromUnsigned, fromSigned);
        Assert.DoesNotContain("signature", Encoding.UTF8.GetString(fromSigned), StringComparison.Ordinal);
    }

    // ---- Bozulmalar ----

    [Fact]
    public void A_tampered_manifest_is_rejected()
    {
        JsonObject node = SignedNode();
        node["packs"]![0]!["size_bytes"] = 1;

        ManifestVerification result = Verify(Bytes(node));

        Assert.False(result.IsValid);
        Assert.Equal([ManifestErrorCodes.SignatureInvalid], Codes(result));
    }

    [Fact]
    public void A_manifest_signed_with_another_key_is_rejected()
    {
        SigningKey other = SigningKeys.Generate("test", 2026, 1);
        byte[] signed = ManifestSigner.Sign(ImzaFixture.UnsignedManifest(), other);

        ManifestVerification result = Verify(signed);

        Assert.Equal([ManifestErrorCodes.SignatureInvalid], Codes(result));
    }

    [Fact]
    public void A_manifest_without_signature_is_rejected()
    {
        ManifestVerification result = Verify(ImzaFixture.UnsignedManifest());

        Assert.False(result.IsValid);
        Assert.Equal([ManifestErrorCodes.SignatureMissing], Codes(result));
    }

    [Fact]
    public void An_unexpected_kid_is_rejected_and_no_expected_kid_skips_the_check()
    {
        ManifestVerification wrong = Verify(ImzaFixture.SignedManifest(), "test-2026-2");
        ManifestVerification any = Verify(ImzaFixture.SignedManifest(), expectedKid: null);

        Assert.Equal([ManifestErrorCodes.SignatureKid], Codes(wrong));
        Assert.True(any.IsValid);
    }

    [Fact]
    public void A_wrong_algorithm_is_rejected()
    {
        JsonObject node = SignedNode();
        node["signature"]!["alg"] = "rsa";

        Assert.Equal([ManifestErrorCodes.SignatureAlgorithm], Codes(Verify(Bytes(node))));
    }

    [Theory]
    [InlineData("###")]
    [InlineData("")]
    [InlineData(" AAAA")]
    public void A_value_that_is_not_base64_is_rejected(string value)
    {
        JsonObject node = SignedNode();
        node["signature"]!["value"] = value;

        Assert.Equal([ManifestErrorCodes.SignatureBase64], Codes(Verify(Bytes(node))));
    }

    [Fact]
    public void A_63_byte_signature_is_rejected()
    {
        JsonObject node = SignedNode();
        node["signature"]!["value"] = Convert.ToBase64String(new byte[63]);

        Assert.Equal([ManifestErrorCodes.SignatureLength], Codes(Verify(Bytes(node))));
    }

    [Fact]
    public void Invalid_json_and_non_object_roots_are_reported_not_thrown()
    {
        Assert.Equal([ManifestErrorCodes.InvalidJson], Codes(Verify("{\"a\":"u8.ToArray())));
        Assert.Equal([ManifestErrorCodes.InvalidJson], Codes(Verify("[1]"u8.ToArray())));
    }

    [Fact]
    public void A_duplicate_property_name_is_rejected_as_invalid_json()
    {
        string text = Encoding.UTF8.GetString(ImzaFixture.SignedManifest()).Replace(
            "\"flavor\": \"dev\"",
            "\"flavor\": \"dev\",\n  \"flavor\": \"public\"",
            StringComparison.Ordinal);

        Assert.Equal([ManifestErrorCodes.InvalidJson], Codes(Verify(Encoding.UTF8.GetBytes(text))));
    }

    [Fact]
    public void A_public_key_of_the_wrong_length_is_reported()
    {
        ManifestVerification result = ManifestVerifier.Verify(ImzaFixture.SignedManifest(), new byte[31]);

        Assert.Equal([ManifestErrorCodes.PublicKeyInvalid], Codes(result));
    }

    [Fact]
    public void Signing_a_manifest_that_already_has_a_signature_fails()
    {
        Assert.Throws<ArgumentException>(() => ManifestSigner.Sign(ImzaFixture.SignedManifest(), ImzaFixture.Key()));
    }

    [Fact]
    public void A_generated_key_signs_and_verifies()
    {
        SigningKey key = SigningKeys.Generate("dev", 2026, 1);

        byte[] signed = ManifestSigner.Sign(ImzaFixture.UnsignedManifest(), key);

        Assert.True(ManifestVerifier.Verify(signed, key.GetPublicKey(), "dev-2026-1").IsValid);
        Assert.False(ManifestVerifier.Verify(signed, ImzaFixture.PublicKey(), "dev-2026-1").IsValid);
    }
}
