using System.Globalization;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure.Identity;
using Npgsql;

namespace Mutalaa.Api.Tests.Support;

/// <summary>Sentetik <c>icerik.release</c> satiri (test tohumu). Varsayilanlar gecerli, bos bir yayin talebidir.</summary>
internal sealed record ReleaseSeed(
    string Surum,
    string Derleme = "dev",
    string Durum = "hazirlaniyor",
    string Talep = "yayin",
    int? KaynakReleaseId = null,
    string[]? Paketler = null,
    string? Notlar = null,
    string? Manifest = null,
    string KapiRaporu = "{}",
    string Ozetler = "{}",
    DateTime? YayinlandiAt = null,
    string Olusturan = "test-editor",
    string DataVersion = "2026.11.10-abc1234");

/// <summary>Veritabanindan okunan yayin satiri.</summary>
internal sealed record ReleaseRow(
    int Id,
    string Surum,
    string Derleme,
    string Durum,
    string Talep,
    int? KaynakReleaseId,
    string[]? Paketler,
    string? Notlar,
    string Olusturan,
    string DataVersion);

/// <summary>Yayin uc testlerinin ortak yardimcilari: sentetik kullanicilar, oturum, satir tohumu ve okuma.</summary>
internal static class ReleaseTestKit
{
    // Sentetik degerler: gercek hesap degildir.
    public const string AdminEmail = "yonetici@example.test";
    public const string AdminPassword = "yonetici-parolasi-123";
    public const string EditorEmail = "editor@example.test";
    public const string EditorPassword = "editor-parolasi-1234";

    private const string IdentityAndReleaseTables =
        "TRUNCATE kimlik.user_roles, kimlik.user_claims, kimlik.user_logins, kimlik.user_tokens, kimlik.role_claims, kimlik.users, kimlik.roles, icerik.release";

    /// <summary>Kimlik tablolarini ve yayin satirlarini temizler (her testin basinda).</summary>
    public static Task ResetAsync(TestDatabase db, CancellationToken cancellationToken) =>
        db.ExecuteAsync(IdentityAndReleaseTables, cancellationToken);

    public static Task<HttpClient> AdminAsync(ApiFactory factory, CancellationToken cancellationToken) =>
        SignInAsync(factory, AdminEmail, AdminPassword, Roles.Admin, cancellationToken);

    public static Task<HttpClient> EditorAsync(ApiFactory factory, CancellationToken cancellationToken) =>
        SignInAsync(factory, EditorEmail, EditorPassword, Roles.Editor, cancellationToken);

    /// <summary>Yalniz <c>uzman</c> rolunde kullanici (K-51 madde 2).</summary>
    public static Task<HttpClient> UzmanAsync(ApiFactory factory, CancellationToken cancellationToken) =>
        SignInAsync(factory, "uzman@example.test", "uzman-parolasi-123456", Roles.Uzman, cancellationToken);

    private static async Task<HttpClient> SignInAsync(ApiFactory factory, string email, string password, string role, CancellationToken cancellationToken)
    {
        await using (AsyncServiceScope scope = factory.Services.CreateAsyncScope())
        {
            UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
            if (await users.FindByEmailAsync(email) is null)
            {
                await factory.AddUserAsync(email, password, role);
            }
        }

        HttpClient client = factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, email, password, cancellationToken);
        Assert.Equal(System.Net.HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    public static Task<HttpResponseMessage> PostAsync(HttpClient client, string url, object? body, CancellationToken cancellationToken) =>
        body is null ? client.PostAsync(url, content: null, cancellationToken) : client.PostAsJsonAsync(url, body, cancellationToken);

    /// <summary>Bu ayin <paramref name="number"/>. surumu (UTC bugun): <c>ReleaseVersion.Next</c> ile ayni ay.</summary>
    public static string MonthVersion(int number)
    {
        DateTime today = DateTime.UtcNow;
        return string.Create(CultureInfo.InvariantCulture, $"{today.Year:D4}.{today.Month}.{number}");
    }

    public static async Task<int> InsertReleaseAsync(TestDatabase db, ReleaseSeed seed, CancellationToken cancellationToken) =>
        await db.ScalarAsync<int>(
            """
            INSERT INTO icerik.release
                (surum, derleme, durum, data_version, olusturan, talep, kaynak_release_id, paketler, notlar, manifest, kapi_raporu, ozetler, yayinlandi_at)
            VALUES
                (@surum, @derleme::icerik.derleme_turu, @durum::icerik.surum_durumu, @dv, @olusturan, @talep, @kaynak, @paketler, @notlar,
                 @manifest::jsonb, @kapi::jsonb, @ozet::jsonb, @yay)
            RETURNING id
            """,
            cancellationToken,
            ("surum", seed.Surum),
            ("derleme", seed.Derleme),
            ("durum", seed.Durum),
            ("dv", seed.DataVersion),
            ("olusturan", seed.Olusturan),
            ("talep", seed.Talep),
            ("kaynak", seed.KaynakReleaseId),
            ("paketler", seed.Paketler),
            ("notlar", seed.Notlar),
            ("manifest", seed.Manifest),
            ("kapi", seed.KapiRaporu),
            ("ozet", seed.Ozetler),
            ("yay", seed.YayinlandiAt is { } at ? DateTime.SpecifyKind(at, DateTimeKind.Utc) : null));

    public static Task<long> CountAsync(TestDatabase db, CancellationToken cancellationToken) =>
        db.ScalarAsync<long>("SELECT count(*) FROM icerik.release", cancellationToken);

    public static async Task<ReleaseRow> ReadAsync(TestDatabase db, int id, CancellationToken cancellationToken)
    {
        await using NpgsqlConnection connection = await db.OpenRawConnectionAsync(cancellationToken);
        await using NpgsqlCommand command = new(
            "SELECT id, surum, derleme::text, durum::text, talep, kaynak_release_id, paketler, notlar, olusturan, data_version FROM icerik.release WHERE id = @id",
            connection);
        command.Parameters.AddWithValue("id", id);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        Assert.True(await reader.ReadAsync(cancellationToken), "Yayin satiri yok: " + id.ToString(CultureInfo.InvariantCulture));
        return new ReleaseRow(
            reader.GetInt32(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.GetString(4),
            reader.IsDBNull(5) ? null : reader.GetInt32(5),
            reader.IsDBNull(6) ? null : reader.GetFieldValue<string[]>(6),
            reader.IsDBNull(7) ? null : reader.GetString(7),
            reader.GetString(8),
            reader.GetString(9));
    }

    public static string? Code(JsonElement problem) => problem.GetProperty("kod").GetString();
}
