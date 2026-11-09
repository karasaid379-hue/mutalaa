using System.Net;
using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Kaynak, birim ve tarama uclari testlerinin ortak tabani: icerik tablolarini her testte bosaltir, editor olusturup giris yapar,
/// sentetik kaynak ve birim ekler (gercek Kur'an, meal ya da Risale metni yoktur).
/// </summary>
public abstract class EditorApiTestBase<TTests>(EditorialDatabase<TTests> fixture) : ApiTestBase<TTests>(fixture)
{
    protected const string EditorEmail = "editor@example.test";
    protected const string EditorPassword = "editor-parolasi-1234";

    protected static CancellationToken Ct => TestContext.Current.CancellationToken;

    /// <summary>Icerik tablolarini bosaltir, bir editor olusturur ve giris yapmis istemciyi dondurur (testte bir kez cagrilir).</summary>
    internal async Task<HttpClient> LoginEditorAsync(ApiFactory? factory = null)
    {
        factory ??= Factory;
        await Db.ExecuteAsync("TRUNCATE icerik.review, icerik.unit, icerik.source CASCADE", Ct);
        await factory.AddUserAsync(EditorEmail, EditorPassword, Roles.Editor);
        HttpClient client = factory.CreateApiClient();
        using HttpResponseMessage login = await ApiFactory.LoginAsync(client, EditorEmail, EditorPassword, Ct);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        return client;
    }

    internal async Task<Source> SeedSourceAsync(string slug, SourceKind tur = SourceKind.Risale, Action<Source>? configure = null)
    {
        Source source = TestData.NewSource(slug);
        source.Tur = tur;
        configure?.Invoke(source);
        await using DbSession session = Db.OpenSession();
        session.Context.Sources.Add(source);
        await session.Context.SaveChangesAsync(Ct);
        return source;
    }

    /// <summary>Birim ekler; arama sutunlari (tr_wide, ar_norm) metinden uretilir. Kimligi dondurur.</summary>
    internal async Task<long> SeedUnitAsync(
        string sourceId,
        string anchor,
        string metin,
        UnitKind kind = UnitKind.Risale,
        long ord = 1,
        Action<Unit>? configure = null)
    {
        SearchKeys keys = SearchNormalizer.Keys(metin);
        Unit unit = new()
        {
            Anchor = AnchorRef.Parse(anchor),
            Kind = kind,
            SourceId = sourceId,
            Ord = ord,
            Metin = metin,
            ContentHash = ContentHash.Compute(metin),
            DataVersion = "test",
            TrNarrow = keys.TrNarrow,
            TrWide = keys.TrWide,
            ArNorm = keys.ArNorm,
        };
        configure?.Invoke(unit);
        await using DbSession session = Db.OpenSession();
        session.Context.Units.Add(unit);
        await session.Context.SaveChangesAsync(Ct);
        return unit.Id;
    }

    internal static async Task<JsonElement> ReadAsync(HttpResponseMessage response) =>
        await ApiFactory.ReadJsonAsync(response, Ct);

    protected static string ProblemType(JsonElement body) => body.GetProperty("type").GetString()!;
}
