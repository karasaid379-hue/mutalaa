using System.Globalization;
using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Baglanti kuyrugu testlerinin ortak tabani (A18.4): sentetik Risale birimi, ayet birimleri ve kelimeleri, baglanti ve review tohumlari.
/// Metin sentetiktir ("Deneme paragrafi ..."); Kur'an, meal ya da Risale metni yoktur. Ayet birimlerinin metni de sentetiktir, yalniz kelime sayisi gerekir.
/// </summary>
public abstract class LinkTestBase<TTests>(EditorialDatabase<TTests> fixture) : LexiconTestBase<TTests>(fixture)
{
    /// <summary>Kaynak birimin metni: 120 kod noktasindan uzun, vurgulu dizi pencereleri (±40) sinanabilsin.</summary>
    protected static readonly string SrcText = string.Concat(Enumerable.Range(0, 26).Select(i => (char)('a' + i)))
        + " " + string.Concat(Enumerable.Range(0, 26).Select(i => (char)('A' + i)))
        + " " + string.Concat(Enumerable.Range(0, 10).Select(i => i.ToString(CultureInfo.InvariantCulture)))
        + " Deneme paragrafi ikinci yari: " + string.Concat(Enumerable.Range(0, 26).Select(i => (char)('a' + i)))
        + " " + string.Concat(Enumerable.Range(0, 26).Select(i => (char)('A' + i)));

    protected const string AyahAnchor = "q:2:255";
    protected const string OtherAyahAnchor = "q:2:256";
    protected const string HadithAnchor = "h:buhari:52";
    protected const string HadithText = "Deneme hadis metni: yirmi uc dort bes alti yedi sekiz dokuz on bir";

    private static int _srcCounter = 1;

    /// <summary>Tohumlanan kaynaklar ve birimler.</summary>
    protected sealed record World(string RisaleSource, string QuranSource, string HadithSource, Unit Src, Unit Ayah, Unit OtherAyah, Unit Hadith);

    protected Task ResetLinksAsync() => Db.ExecuteAsync(
        "TRUNCATE icerik.review, icerik.xref, icerik.lemma_dalga, icerik.lemma_gloss, icerik.quran_word_fix, icerik.quran_word, icerik.lemma, icerik.root, icerik.unit, icerik.source CASCADE",
        Ct);

    /// <summary>Tablolari temizler; Risale birimi (kaynak ucu), q:2:255 (10 kelime), q:2:256 (5 kelime) ve h:buhari:52 birimlerini ekler.</summary>
    protected async Task<World> SeedWorldAsync()
    {
        await ResetLinksAsync();
        string risale = await SeedSourceAsync(SourceKind.Risale);
        string quran = await SeedSourceAsync(SourceKind.KuranMetni);
        string hadith = await SeedSourceAsync(SourceKind.Hadis);

        Unit src = await SeedUnitAsync(risale, UnitKind.Risale, "rn:sozler:soz-10:p4", SrcText, TextStatus.Onayli);
        Unit ayah = await SeedUnitAsync(quran, UnitKind.Ayet, AyahAnchor, "deneme ayet metni bir", TextStatus.Onayli);
        Unit other = await SeedUnitAsync(quran, UnitKind.Ayet, OtherAyahAnchor, "deneme ayet metni iki", TextStatus.Onayli);
        Unit hadithUnit = await SeedUnitAsync(hadith, UnitKind.Hadis, HadithAnchor, HadithText, TextStatus.Onayli);

        for (int w = 1; w <= 10; w++)
        {
            await SeedWordAsync(quran, $"q:2:255:{w.ToString(CultureInfo.InvariantCulture)}", 1, (w - 1) * 5, (w * 5) - 1, null);
        }

        for (int w = 1; w <= 5; w++)
        {
            await SeedWordAsync(quran, $"q:2:256:{w.ToString(CultureInfo.InvariantCulture)}", 2, (w - 1) * 5, (w * 5) - 1, null);
        }

        return new World(risale, quran, hadith, src, ayah, other, hadithUnit);
    }

    /// <summary>Kanit: <c>src_hash</c> kaynak birimin ozetinin ilk 16 hanesidir (Yayinlayici ve vurgulu dizi ister).</summary>
    protected static string Evidence(Unit src, params (string Name, object? Value)[] extra)
    {
        Dictionary<string, object?> map = new(StringComparer.Ordinal) { ["src_hash"] = src.ContentHash[..16] };
        foreach ((string name, object? value) in extra)
        {
            map[name] = value;
        }

        return JsonSerializer.Serialize(map);
    }

    protected async Task<Xref> SeedXrefAsync(
        XrefType type = XrefType.Iktibas,
        float confidence = 0.5f,
        string evidence = "{}",
        string src = "rn:sozler:soz-10:p4",
        AnchorSpan? srcSpan = null,
        string dst = AyahAnchor,
        AnchorSpan? dstSpan = null,
        XrefStatus status = XrefStatus.Aday,
        XrefOrigin origin = XrefOrigin.Hat)
    {
        int n = Interlocked.Increment(ref _srcCounter);
        Xref xref = new()
        {
            SrcAnchor = AnchorRef.Parse(src),
            SrcSpan = srcSpan ?? new AnchorSpan(n, n + 3),
            DstAnchor = AnchorRef.Parse(dst),
            DstSpan = dstSpan,
            Type = type,
            Score = confidence,
            Confidence = confidence,
            Evidence = evidence,
            Origin = origin,
            Status = status,
            DataVersion = "test-1",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(xref);
        await session.Context.SaveChangesAsync(Ct);
        return xref;
    }

    protected Task<Review> SeedLinkReviewAsync(
        Xref xref,
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        ReviewStatus durum = ReviewStatus.Acik,
        string? inceleyen = null) =>
        SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = xref.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = xref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = koken,
            Oneren = oneren,
            Durum = durum,
            Inceleyen = inceleyen,
        });

    protected sealed record XrefRow(string Type, string SrcAnchor, string? SrcSpan, string DstAnchor, string? DstSpan, string Origin, string Status, string Evidence, float Confidence);

    protected async Task<XrefRow> XrefRowAsync(Guid id)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT type::text, src_anchor, src_span::text, dst_anchor, dst_span::text, origin::text, status::text, evidence::text, confidence FROM icerik.xref WHERE id = @id",
            connection);
        command.Parameters.AddWithValue("id", id);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return new XrefRow(
            reader.GetString(0),
            reader.GetString(1),
            reader.IsDBNull(2) ? null : reader.GetString(2),
            reader.GetString(3),
            reader.IsDBNull(4) ? null : reader.GetString(4),
            reader.GetString(5),
            reader.GetString(6),
            reader.GetString(7),
            reader.GetFloat(8));
    }

    protected async Task<JsonElement> DetailAsync(HttpClient client, long reviewId)
    {
        using HttpResponseMessage response = await client.GetAsync($"/api/v1/reviews/{reviewId.ToString(CultureInfo.InvariantCulture)}", Ct);
        Assert.Equal(System.Net.HttpStatusCode.OK, response.StatusCode);
        return await ApiFactory.ReadJsonAsync(response, Ct);
    }

    protected async Task<JsonElement> ListAsync(HttpClient client, string query)
    {
        using HttpResponseMessage response = await client.GetAsync("/api/v1/reviews?" + query, Ct);
        Assert.Equal(System.Net.HttpStatusCode.OK, response.StatusCode);
        return await ApiFactory.ReadJsonAsync(response, Ct);
    }

    protected static long[] Ids(JsonElement list) => [.. list.GetProperty("items").EnumerateArray().Select(i => i.GetProperty("id").GetInt64())];

    protected static string StrongEvidence(Unit src) =>
        Evidence(src, ("matched_words", 9), ("coverage", 1), ("phrase_freq", 1), ("consistent_quote", true));
}
