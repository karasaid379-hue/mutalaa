using Microsoft.Extensions.Configuration;
using Mutalaa.Api.Releases;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Yayin talebi kurallari (saf; Docker gerekmez): derleme turu etiketi, paket listesi, notlar, liste imleci ve sir temizleyici.
/// Derleme turu etiketleri kulturden bagimsizdir (tr-TR'de "internal" buyuk I ile bozulmaz).
/// </summary>
public class ReleaseRequestRulesTests
{
    private static readonly PackCatalog Catalog = PackCatalog.Default;

    [Theory]
    [InlineData("dev", BuildFlavor.Dev)]
    [InlineData("internal", BuildFlavor.Internal)]
    [InlineData("public", BuildFlavor.Public)]
    public void The_three_flavor_labels_are_accepted(string label, BuildFlavor expected)
    {
        ReleaseRequestResult result = ReleaseRequestRules.Validate(label, null, null, Catalog);

        Assert.True(result.IsValid);
        Assert.Equal(expected, result.Flavor);
        Assert.Null(result.Packs);
        Assert.Null(result.Notes);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("DEV")]
    [InlineData("Internal")]
    [InlineData("İnternal")]
    [InlineData("ınternal")]
    [InlineData(" dev")]
    [InlineData("dev ")]
    [InlineData("production")]
    public void Any_other_flavor_text_is_a_validation_error_on_derleme(string? label)
    {
        ReleaseRequestResult result = ReleaseRequestRules.Validate(label, null, null, Catalog);

        Assert.False(result.IsValid);
        Assert.Equal(["derleme"], result.Errors.Keys);
    }

    [Fact]
    public async Task Flavor_labels_do_not_depend_on_the_current_culture()
    {
        await AsyncCultureScope.TurkishAsync(() =>
        {
            Assert.Equal(BuildFlavor.Internal, ReleaseRequestRules.Validate("internal", null, null, Catalog).Flavor);
            Assert.False(ReleaseRequestRules.Validate("INTERNAL", null, null, Catalog).IsValid);
            Assert.Equal("internal", BuildFlavor.Internal.ToLabel());
            Assert.Equal("public", BuildFlavor.Public.ToLabel());
            Assert.Equal("dev", BuildFlavor.Dev.ToLabel());
            return Task.CompletedTask;
        });
    }

    [Fact]
    public void Packs_are_checked_against_the_catalog_and_kept_in_the_given_order()
    {
        ReleaseRequestResult result = ReleaseRequestRules.Validate("dev", ["test-kucuk", "core"], null, Catalog);

        Assert.True(result.IsValid);
        Assert.NotNull(result.Packs);
        Assert.Equal(["test-kucuk", "core"], result.Packs);
    }

    [Fact]
    public void An_empty_pack_list_means_all_packs_and_becomes_null()
    {
        Assert.Null(ReleaseRequestRules.Validate("dev", [], null, Catalog).Packs);
        Assert.Null(ReleaseRequestRules.Validate("dev", null, null, Catalog).Packs);
    }

    [Fact]
    public void An_unknown_empty_or_duplicate_pack_is_a_validation_error_on_paketler()
    {
        ReleaseRequestResult unknown = ReleaseRequestRules.Validate("dev", ["core", "yok-boyle-paket"], null, Catalog);
        ReleaseRequestResult blank = ReleaseRequestRules.Validate("dev", ["core", " "], null, Catalog);
        ReleaseRequestResult duplicate = ReleaseRequestRules.Validate("dev", ["core", "test-kucuk", "core"], null, Catalog);
        ReleaseRequestResult wrongCase = ReleaseRequestRules.Validate("dev", ["Core"], null, Catalog);

        foreach (ReleaseRequestResult result in new[] { unknown, blank, duplicate, wrongCase })
        {
            Assert.False(result.IsValid);
            Assert.Equal(["paketler"], result.Errors.Keys);
        }

        Assert.Contains("yok-boyle-paket", unknown.Errors["paketler"][0], StringComparison.Ordinal);
        Assert.Contains("core", duplicate.Errors["paketler"][0], StringComparison.Ordinal);
    }

    [Fact]
    public void Errors_for_several_fields_are_reported_together()
    {
        ReleaseRequestResult result = ReleaseRequestRules.Validate("x", ["yok"], new string('a', ReleaseRequestRules.MaxNotesCodePoints + 1), Catalog);

        Assert.Equal(["derleme", "notlar", "paketler"], result.Errors.Keys.Order(StringComparer.Ordinal));
    }

    [Fact]
    public void Notes_up_to_2000_code_points_are_accepted_and_one_more_is_not()
    {
        string within = new('a', ReleaseRequestRules.MaxNotesCodePoints);

        Assert.Equal(within, ReleaseRequestRules.Validate("dev", null, within, Catalog).Notes);
        Assert.Equal(["notlar"], ReleaseRequestRules.Validate("dev", null, within + "a", Catalog).Errors.Keys);
    }

    [Fact]
    public void Notes_are_counted_in_code_points_not_utf16_units()
    {
        string emoji = char.ConvertFromUtf32(0x1F600);
        string within = string.Concat(Enumerable.Repeat(emoji, ReleaseRequestRules.MaxNotesCodePoints));

        Assert.Equal(ReleaseRequestRules.MaxNotesCodePoints * 2, within.Length);
        Assert.True(ReleaseRequestRules.Validate("dev", null, within, Catalog).IsValid);
        Assert.False(ReleaseRequestRules.Validate("dev", null, within + emoji, Catalog).IsValid);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\n\t ")]
    public void Blank_notes_become_null(string notes)
    {
        Assert.Null(ReleaseRequestRules.Validate("dev", null, notes, Catalog).Notes);
        Assert.Null(ReleaseRequestRules.ValidateNotesOnly(notes, out string? normalized));
        Assert.Null(normalized);
    }

    // Eslesmemis vekil karakter oznitelik argumani olamaz (derleme ust verisi onu U+FFFD yapar); calisma zamaninda kurulur.
    public static TheoryData<string> UnstorableNotes() => new()
    {
        "a\0b",
        "a" + (char)0xD800 + "b",
        "a" + (char)0xDC00,
        "a" + (char)0xD800,
    };

    [Theory]
    [MemberData(nameof(UnstorableNotes))]
    public void Notes_that_PostgreSQL_cannot_store_are_rejected(string notes)
    {
        IDictionary<string, string[]>? errors = ReleaseRequestRules.ValidateNotesOnly(notes, out string? normalized);

        Assert.NotNull(errors);
        Assert.Equal(["notlar"], errors.Keys);
        Assert.Null(normalized);
    }

    [Fact]
    public void A_long_wrong_value_is_shortened_in_the_error_message()
    {
        ReleaseRequestResult result = ReleaseRequestRules.Validate(new string('x', 500), null, null, Catalog);

        Assert.True(result.Errors["derleme"][0].Length < 200);
    }

    // --- Imlec ---

    [Theory]
    [InlineData(1)]
    [InlineData(42)]
    [InlineData(int.MaxValue)]
    public void A_cursor_round_trips_and_is_url_safe_and_unpadded(int id)
    {
        string cursor = ReleaseCursor.Encode(id);

        Assert.True(ReleaseCursor.TryDecode(cursor, out int decoded));
        Assert.Equal(id, decoded);
        Assert.DoesNotContain('=', cursor);
        Assert.DoesNotContain('+', cursor);
        Assert.DoesNotContain('/', cursor);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("42")]
    [InlineData("cjo0Mg==")]
    [InlineData("cjo0Mg ")]
    [InlineData("!!!")]
    public void A_cursor_that_is_not_canonical_is_rejected(string? cursor)
    {
        Assert.False(ReleaseCursor.TryDecode(cursor, out _));
    }

    [Theory]
    [InlineData("r:0")]
    [InlineData("r:042")]
    [InlineData("r:-5")]
    [InlineData("x:42")]
    [InlineData("r:99999999999")]
    [InlineData("r:42:7")]
    public void A_cursor_with_a_bad_payload_is_rejected(string payload)
    {
        string cursor = System.Buffers.Text.Base64Url.EncodeToString(System.Text.Encoding.ASCII.GetBytes(payload));

        Assert.False(ReleaseCursor.TryDecode(cursor, out _));
    }

    // --- Sir temizleyici ---

    private static SecretRedactor RedactorFor(string connection, params (string Key, string Value)[] extra)
    {
        Dictionary<string, string?> values = new(StringComparer.Ordinal) { ["ConnectionStrings:Editorial"] = connection };
        foreach ((string key, string value) in extra)
        {
            values[key] = value;
        }

        return new SecretRedactor(new ConfigurationBuilder().AddInMemoryCollection(values).Build());
    }

    [Fact]
    public void The_redactor_removes_the_connection_string_its_password_and_user()
    {
        const string connection = "Host=db.example.test;Database=icerik;Username=uygulama-kullanicisi;Password=cok-gizli-parola-1";
        SecretRedactor redactor = RedactorFor(connection);

        string text = redactor.Redact($"hata: {connection} ve ayrica cok-gizli-parola-1 ile uygulama-kullanicisi");

        Assert.DoesNotContain("cok-gizli-parola-1", text, StringComparison.Ordinal);
        Assert.DoesNotContain("uygulama-kullanicisi", text, StringComparison.Ordinal);
        Assert.DoesNotContain("db.example.test", text, StringComparison.Ordinal);
    }

    [Fact]
    public void The_redactor_removes_key_value_pairs_and_url_credentials_and_configured_secrets()
    {
        SecretRedactor redactor = RedactorFor("Host=x", ("Storage:SecretKey", "depo-sirri-12345"));

        string text = redactor.Redact("password=abc123; token: xyz789 https://kullanici:parola99@example.test/yol depo-sirri-12345");

        Assert.DoesNotContain("abc123", text, StringComparison.Ordinal);
        Assert.DoesNotContain("xyz789", text, StringComparison.Ordinal);
        Assert.DoesNotContain("parola99", text, StringComparison.Ordinal);
        Assert.DoesNotContain("depo-sirri-12345", text, StringComparison.Ordinal);
        Assert.Contains("example.test/yol", text, StringComparison.Ordinal);
    }

    [Fact]
    public void The_redactor_leaves_anchors_digests_and_slugs_alone()
    {
        SecretRedactor redactor = RedactorFor("Host=x;Password=gizli-parola-9");
        const string safe = "uyari: istenen paket kapidan girmedi: tefsir-test-ornek q:2:255 k:test-kucuk:bolum-1:p1 0123456789abcdef";

        Assert.Equal(safe, redactor.Redact(safe));
    }
}
