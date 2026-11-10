using System.Globalization;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Inceleme uclari testlerinin ortak tabani: iki editor oturumu, sentetik kaynak, birim ve review tohumlari.
/// Veri sentetiktir ("Deneme paragrafi N"); gercek Kur'an, meal ya da Risale metni yoktur.
/// </summary>
public abstract class ReviewTestBase<TTests>(EditorialDatabase<TTests> fixture) : ApiTestBase<TTests>(fixture)
{
    protected const string EditorAEmail = "editor-a@example.test";
    protected const string EditorAPassword = "editor-a-parolasi-123";
    protected const string EditorBEmail = "editor-b@example.test";
    protected const string EditorBPassword = "editor-b-parolasi-123";

    protected const string Current = "Deneme paragrafi 1";
    protected const string Proposed = "Deneme paragrafi 2";
    protected const string Edited = "Deneme paragrafi 3";

    private static int _mealCounter;
    private static int _tefsirCounter;
    private static int _ayetCounter;

    protected static CancellationToken Ct => TestContext.Current.CancellationToken;

    /// <summary>Kullanici yoksa olusturur ve giris yapmis yeni istemci (ayri cerez kabi) dondurur.</summary>
    internal async Task<HttpClient> ClientAsync(string email = EditorAEmail, string password = EditorAPassword, ApiFactory? factory = null)
    {
        factory ??= Factory;
        await using (AsyncServiceScope scope = factory.Services.CreateAsyncScope())
        {
            UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
            if (await users.FindByEmailAsync(email) is null)
            {
                await factory.AddUserAsync(email, password, Roles.Editor);
            }
        }

        HttpClient client = factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, email, password, Ct);
        Assert.Equal(System.Net.HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    protected Task ResetReviewsAsync() => Db.ExecuteAsync("TRUNCATE icerik.review", Ct);

    protected async Task<string> SeedSourceAsync(SourceKind kind = SourceKind.Meal)
    {
        Source source = TestData.NewSource();
        source.Tur = kind;
        await using DbSession session = Db.OpenSession();
        session.Context.Add(source);
        await session.Context.SaveChangesAsync(Ct);
        return source.Slug;
    }

    /// <summary>Benzersiz meal capasi (meal:test:{sure}:{ayet}); sure 2..7, ayet 1..100.</summary>
    protected static string MealAnchor()
    {
        int n = Interlocked.Increment(ref _mealCounter) - 1;
        return $"meal:test:{(2 + (n / 100)).ToString(CultureInfo.InvariantCulture)}:{(1 + (n % 100)).ToString(CultureInfo.InvariantCulture)}";
    }

    /// <summary>Benzersiz ayet capasi (q:3:{ayet}, ayet 1..200); metin sentetiktir, Tanzil metni degildir.</summary>
    protected static string AyetAnchor()
    {
        int n = Interlocked.Increment(ref _ayetCounter);
        return $"q:3:{n.ToString(CultureInfo.InvariantCulture)}";
    }

    protected static string TefsirAnchor()
    {
        int n = Interlocked.Increment(ref _tefsirCounter);
        return $"tf:test:2-1-1:p{n.ToString(CultureInfo.InvariantCulture)}";
    }

    protected async Task<Unit> SeedUnitAsync(
        string sourceId,
        UnitKind kind,
        string anchor,
        string metin = Current,
        TextStatus durum = TextStatus.Taslak)
    {
        Unit unit = TestData.NewUnit(sourceId, anchor);
        unit.Kind = kind;
        unit.Metin = metin;
        unit.ContentHash = ContentHash.Compute(metin);
        unit.MetinDurumu = durum;
        await using DbSession session = Db.OpenSession();
        session.Context.Add(unit);
        await session.Context.SaveChangesAsync(Ct);
        return unit;
    }

    /// <summary>Metin incelemesi: onceki mevcut metin, onerilen yeni metin.</summary>
    protected async Task<Review> SeedUnitReviewAsync(
        Unit unit,
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        string proposed = Proposed,
        string? inceleyen = null,
        ReviewStatus durum = ReviewStatus.Acik,
        string? yzModeli = null)
    {
        Review review = new()
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = unit.Anchor.ToString(),
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Onceki = Payload(unit.Metin),
            Onerilen = Payload(proposed),
            Durum = durum,
            Koken = koken,
            Oneren = oneren,
            Inceleyen = inceleyen,
            YzModeli = yzModeli,
            YzKaydi = yzModeli is null ? null : YzRecord(),
        };
        return await SaveReviewAsync(review);
    }

    protected async Task<Review> SaveReviewAsync(Review review)
    {
        await using DbSession session = Db.OpenSession();
        session.Context.Add(review);
        await session.Context.SaveChangesAsync(Ct);
        return review;
    }

    protected async Task<(SurahAlias Alias, Review Review)> SeedAliasReviewAsync(string alias = "Deneme-sure", XrefOrigin koken = XrefOrigin.Hat, string oneren = "hat", string? onerilen = null)
    {
        SurahAlias row = new() { SurahNo = 1, Alias = alias + "-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6], AliasKey = "deneme", Kind = "yazim" };
        Review review = new()
        {
            HedefTablo = ReviewTargets.SurahAlias,
            HedefAnahtar = "1:" + row.Alias,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = koken,
            Oneren = oneren,
            Onerilen = onerilen,
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(row);
        session.Context.Add(review);
        await session.Context.SaveChangesAsync(Ct);
        return (row, review);
    }

    protected static string Payload(string metin) =>
        JsonSerializer.Serialize(new Dictionary<string, string> { ["metin"] = metin, ["content_hash"] = ContentHash.Compute(metin) });

    protected static string YzRecord() =>
        JsonSerializer.Serialize(new Dictionary<string, string>
        {
            ["prompt_id"] = "deneme-1",
            ["prompt_sha256"] = TestData.Hash('b'),
            ["input_sha256"] = TestData.Hash('c'),
        });

    /// <summary>Veritabanindaki guncel xmin (ham sorgu).</summary>
    protected async Task<uint> XminAsync(long reviewId) =>
        uint.Parse(await Db.ScalarAsync<string>("SELECT xmin::text FROM icerik.review WHERE id = @id", Ct, ("id", reviewId)), CultureInfo.InvariantCulture);

    protected static string Etag(uint xmin) => "\"" + xmin.ToString(CultureInfo.InvariantCulture) + "\"";

    protected static Task<HttpResponseMessage> DecideAsync(HttpClient client, long id, string? ifMatch, object body)
    {
        HttpRequestMessage request = new(HttpMethod.Post, $"/api/v1/reviews/{id.ToString(CultureInfo.InvariantCulture)}/decision")
        {
            Content = JsonContent.Create(body),
        };
        if (ifMatch is not null)
        {
            request.Headers.TryAddWithoutValidation("If-Match", ifMatch);
        }

        return client.SendAsync(request, Ct);
    }

    protected static object Approve(string gerekce = "Deneme gerekcesi", object? duzenlenen = null) =>
        duzenlenen is null
            ? new { karar = "onaylandi", gerekce }
            : new { karar = "onaylandi", gerekce, duzenlenen };

    protected static object Reject(string gerekce = "Deneme ret gerekcesi") => new { karar = "reddedildi", gerekce };

    protected static async Task<string> ProblemCodeAsync(HttpResponseMessage response)
    {
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        JsonElement body = await ApiFactory.ReadJsonAsync(response, Ct);
        string type = body.GetProperty("type").GetString()!;
        Assert.StartsWith("urn:mutalaa:problem:", type, StringComparison.Ordinal);
        Assert.False(string.IsNullOrEmpty(body.GetProperty("traceId").GetString()));
        return type["urn:mutalaa:problem:".Length..];
    }

    /// <summary>Ham sorgu: review satiri alanlari.</summary>
    protected async Task<(string Durum, string Eylem, string? Inceleyen, string? Ikinci)> ReviewRowAsync(long id)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT durum::text, eylem, inceleyen, ikinci_inceleyen FROM icerik.review WHERE id = @id",
            connection);
        command.Parameters.AddWithValue("id", id);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return (
            reader.GetString(0),
            reader.GetString(1),
            reader.IsDBNull(2) ? null : reader.GetString(2),
            reader.IsDBNull(3) ? null : reader.GetString(3));
    }

    protected async Task<(string Metin, string Hash, int Rev, string Durum)> UnitRowAsync(string anchor)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT metin, content_hash, rev, metin_durumu::text FROM icerik.unit WHERE anchor = @a",
            connection);
        command.Parameters.AddWithValue("a", anchor);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return (reader.GetString(0), reader.GetString(1), reader.GetInt32(2), reader.GetString(3));
    }

    protected static AnchorRef Anchor(string text) => AnchorRef.Parse(text);
}
