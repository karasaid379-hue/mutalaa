using System.Globalization;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Kelime katmani (kok, lemma, anlam, dalga, kelime) testlerinin ortak tabani: sentetik tohumlar ("deneme" metinleri;
/// gercek Kur'an, meal ya da sozluk metni yoktur). Kimlikler sayaclidir; her test kendi tablolarini <see cref="ResetLexiconAsync"/> ile temizler.
/// </summary>
public abstract class LexiconTestBase<TTests>(EditorialDatabase<TTests> fixture) : ReviewTestBase<TTests>(fixture)
{
    private static int _rootCounter = 100;
    private static int _lemmaCounter = 5000;

    protected Task ResetLexiconAsync() => Db.ExecuteAsync(
        "TRUNCATE icerik.review, icerik.lemma_dalga, icerik.lemma_gloss, icerik.quran_word_fix, icerik.quran_word, icerik.lemma, icerik.root, icerik.unit, icerik.source CASCADE",
        Ct);

    protected static int NextRootId() => Interlocked.Increment(ref _rootCounter);

    protected static int NextLemmaId() => Interlocked.Increment(ref _lemmaCounter);

    protected async Task<Root> SeedRootAsync(string sourceId, string letters = "deneme-kok", int occurrences = 10, int ayahCount = 4, string? kokAnlami = null)
    {
        Root root = new()
        {
            Id = NextRootId(),
            Letters = letters + "-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6],
            LettersBw = "bw-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..6],
            Occurrences = occurrences,
            AyahCount = ayahCount,
            IdfQ = 1.5f,
            KokAnlami = kokAnlami,
            SourceId = sourceId,
            DataVersion = "test",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(root);
        await session.Context.SaveChangesAsync(Ct);
        return root;
    }

    protected async Task<Lemma> SeedLemmaAsync(
        string sourceId,
        int? rootId = null,
        string text = "deneme-lemma",
        int occurrences = 0,
        XrefStatus status = XrefStatus.Onayli,
        string? origin = "qac",
        string lang = "ar")
    {
        int id = NextLemmaId();
        Lemma lemma = new()
        {
            Id = id,
            Lang = lang,
            Text = text,
            TextClean = text,
            RootId = rootId,
            Occurrences = occurrences,
            QacRef = lang == "ar" ? "qac-" + id.ToString(CultureInfo.InvariantCulture) : null,
            Origin = origin,
            Status = status,
            SourceId = sourceId,
            DataVersion = "test",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(lemma);
        await session.Context.SaveChangesAsync(Ct);
        return lemma;
    }

    protected async Task<LemmaGloss> SeedGlossAsync(
        int lemmaId,
        string anlam = "deneme anlami",
        XrefStatus status = XrefStatus.Aday,
        string origin = "kaynak:quranwbw-tr",
        string version = "1",
        string? turkceEsKelime = null,
        bool etimolojik = false,
        string kuranAnlamlari = "[]")
    {
        LemmaGloss gloss = new()
        {
            LemmaId = lemmaId,
            AnlamKisa = anlam,
            Status = status,
            Origin = origin,
            Version = version,
            ContentHash = ContentHash.Compute(anlam),
            TurkceEsKelime = turkceEsKelime,
            YalnizcaEtimolojik = etimolojik,
            KuranAnlamlari = kuranAnlamlari,
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(gloss);
        await session.Context.SaveChangesAsync(Ct);
        return gloss;
    }

    protected async Task SeedWaveAsync(int lemmaId, short dalga, int sira)
    {
        await using DbSession session = Db.OpenSession();
        session.Context.Add(new LemmaDalga { LemmaId = lemmaId, Dalga = dalga, Sira = sira, DataVersion = "test" });
        await session.Context.SaveChangesAsync(Ct);
    }

    /// <summary>Kelime satiri (quran_word); metin sentetiktir. <paramref name="ayahIndex"/> kuresel ayet sirasidir (okuma sirasi).</summary>
    protected async Task SeedWordAsync(
        string sourceId,
        string anchor,
        short ayahIndex,
        int charStart,
        int charEnd,
        int? lemmaId,
        int? rootId = null,
        string? pos = "N")
    {
        AnchorRef parsed = AnchorRef.Parse(anchor);
        QuranWord word = new()
        {
            Anchor = parsed,
            Surah = (short)parsed.Sure,
            Ayah = (short)parsed.Ayet,
            Word = (short)parsed.Ilk,
            AyahIndex = ayahIndex,
            TextUthmani = "deneme",
            Norm = "deneme",
            CharStart = charStart,
            CharEnd = charEnd,
            LemmaId = lemmaId,
            RootId = rootId,
            Pos = pos,
            SourceId = sourceId,
            DataVersion = "test",
        };
        await using DbSession session = Db.OpenSession();
        session.Context.Add(word);
        await session.Context.SaveChangesAsync(Ct);
    }

    protected Task<Review> SeedGlossReviewAsync(int lemmaId, string? onerilen = null, XrefOrigin koken = XrefOrigin.Hat, ReviewStatus durum = ReviewStatus.Acik) =>
        SaveReviewAsync(new Review
        {
            HedefTablo = ReviewTargets.LemmaGloss,
            HedefAnahtar = lemmaId.ToString(CultureInfo.InvariantCulture),
            Alan = ReviewFields.AnlamKisa,
            Eylem = ReviewActions.Oner,
            Onerilen = onerilen,
            Durum = durum,
            Koken = koken,
            Oneren = "hat",
        });

    /// <summary>Hazir kaynak adayinin onerilen biciminde jsonb: <c>{anlam_kisa, dagilim, baskin_pay}</c>.</summary>
    protected static string GlossProposal(string anlam, double baskinPay = 0.9) =>
        System.Text.Json.JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["anlam_kisa"] = anlam,
            ["dagilim"] = new[] { new Dictionary<string, object> { ["anlam"] = anlam, ["sayi"] = 5 } },
            ["baskin_pay"] = baskinPay,
        });

    protected async Task<(string AnlamKisa, string ContentHash, string Version, string Origin, string Status)> GlossRowAsync(int lemmaId)
    {
        await using Npgsql.NpgsqlConnection connection = await Db.OpenRawConnectionAsync(Ct);
        await using Npgsql.NpgsqlCommand command = new(
            "SELECT anlam_kisa, content_hash, version, origin, status::text FROM icerik.lemma_gloss WHERE lemma_id = @id",
            connection);
        command.Parameters.AddWithValue("id", lemmaId);
        await using Npgsql.NpgsqlDataReader reader = await command.ExecuteReaderAsync(Ct);
        Assert.True(await reader.ReadAsync(Ct));
        return (reader.GetString(0), reader.GetString(1), reader.GetString(2), reader.GetString(3), reader.GetString(4));
    }
}
