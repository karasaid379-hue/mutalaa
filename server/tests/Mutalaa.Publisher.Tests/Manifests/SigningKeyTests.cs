using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Manifests;

namespace Mutalaa.Publisher.Tests.Manifests;

/// <summary>SigningKeys.Generate, kid bicimi ve tohumun disari sizmamasi.</summary>
public class SigningKeyTests
{
    [Fact]
    public void Generate_gives_a_32_byte_seed_a_32_byte_public_key_and_the_kid()
    {
        SigningKey key = SigningKeys.Generate("internal", 2026, 3);

        Assert.Equal(32, key.Seed.Length);
        Assert.Equal(32, key.GetPublicKey().Length);
        Assert.Equal("internal-2026-3", key.Kid);
    }

    [Fact]
    public void Two_generations_differ()
    {
        SigningKey first = SigningKeys.Generate("dev", 2026, 1);
        SigningKey second = SigningKeys.Generate("dev", 2026, 1);

        Assert.NotEqual(first.SeedBase64(), second.SeedBase64());
        Assert.NotEqual(first.GetPublicKey(), second.GetPublicKey());
    }

    [Fact]
    public void Seed_base64_round_trips_and_gives_the_same_public_key()
    {
        SigningKey key = SigningKeys.Generate("dev", 2026, 1);

        SigningKey restored = SigningKey.FromSeedBase64(key.SeedBase64(), key.Kid);

        Assert.Equal(key.GetPublicKey(), restored.GetPublicKey());
    }

    [Fact]
    public void ToString_does_not_reveal_the_seed()
    {
        SigningKey key = SigningKeys.Generate("dev", 2026, 1);

        string text = key.ToString();

        Assert.Contains("dev-2026-1", text, StringComparison.Ordinal);
        Assert.Contains("redacted", text, StringComparison.Ordinal);
        Assert.DoesNotContain(key.SeedBase64(), text, StringComparison.Ordinal);
        Assert.DoesNotContain(Base64Strict.ToHex(key.Seed.Span), text, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(key.SeedBase64(), $"{key}", StringComparison.Ordinal);
    }

    [Fact]
    public void An_invalid_seed_does_not_leak_into_the_exception_message()
    {
        const string bad = "c2VjcmV0LXNlZWQtdGhhdC1pcy10b28tc2hvcnQ=";

        ArgumentException ex = Assert.Throws<ArgumentException>(() => SigningKey.FromSeedBase64(bad, "dev-2026-1"));

        Assert.DoesNotContain(bad, ex.Message, StringComparison.Ordinal);
        Assert.Throws<ArgumentException>(() => SigningKey.FromSeedBase64("###", "dev-2026-1"));
    }

    [Theory]
    [InlineData("", 2026, 1)]
    [InlineData("Dev", 2026, 1)]
    [InlineData("dev1", 2026, 1)]
    [InlineData("dev", 999, 1)]
    [InlineData("dev", 2026, 0)]
    public void Invalid_kid_parts_are_rejected(string flavor, int year, int n)
    {
        Assert.ThrowsAny<ArgumentException>(() => SigningKeys.FormatKid(flavor, year, n));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Kid_format_does_not_depend_on_the_culture(bool turkish)
    {
        string? kid = null;

        CultureScope.For(turkish, () => kid = SigningKeys.FormatKid("public", 2026, 12));

        Assert.Equal("public-2026-12", kid);
    }
}
