using System.Globalization;
using System.Security.Cryptography;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Releases;
using Npgsql;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>Bir baglanti satirinin ad ve kimligi (kimlikler belirlenimcidir: ayni veri her veritabaninda ayni ozeti verir).</summary>
internal sealed record SeededXref(string Name, Guid Id, string Type, string Src, string Dst, string Status, float Confidence);

/// <summary>Tohumlanan icerigin ozeti (testler beklentilerini buradan kurar).</summary>
internal sealed record SeededContent(
    IReadOnlyDictionary<string, SeededXref> Xrefs,
    string UthmaniNotice,
    string SimpleCleanNotice,
    TanzilRawFile Uthmani,
    string ProbeArabicToken);

/// <summary>
/// Uctan uca fikstur veritabani (A13.5). Her icerik durumundan ornek tasir: Tanzil kaynagi (data/raw altinda gecici dizinde ham dosya, dosya_sha256 ve notice_text),
/// onayli ve onaysiz birim, yapay zeka taslagi (review.yz_modeli dolu), onayli/aday/red ve esigin altinda/ustunde baglantilar, test-kucuk, test-tefsir-ornek, test-ses
/// kaynagi ve sozluk satirlari. KUR'AN, MEAL YA DA HADIS METNI ELLE YAZILMAZ: Tanzil metni yalniz pipeline/tests/fixtures/tanzil/*-parca.txt dosyalarindan
/// (ilk 40 ayet, 2:33'te biter) gelir ve her satir content_hash ile eklenir; digerleri "Deneme paragrafi N ..." sentetik metindir.
/// </summary>
internal static class EndToEndData
{
    public const string Uthmani = "tanzil-uthmani";
    public const string SimpleClean = "tanzil-simple-clean";
    public const string UstVeri = "tanzil-ust-veri";
    public const string Kucuk = "test-kucuk";
    public const string Tefsir = "test-tefsir-ornek";
    public const string Ses = "test-ses";
    public const string Sentetik = "hadis-sentetik";

    public const string TanzilDate = "2026-11-02";

    public const string KucukPack = "test-kucuk";
    public const string TefsirPack = "tefsir-test-ornek";
    public const string SentetikPack = "hadis-sentetik";

    public const string SentetikApproved = "k:hadis-sentetik:bolum-1:p1";
    public const string SentetikDraft = "k:hadis-sentetik:bolum-1:p2";
    public const string SentetikAi = "k:hadis-sentetik:bolum-1:p3";
    public const string KucukFirst = "k:test-kucuk:bolum-1:p1";
    public const string KucukSecond = "k:test-kucuk:bolum-1:p2";
    public const string TefsirFirst = "tf:test-ornek:1-1-1:p1";

    /// <summary>"Isik" sozcugu (test-kucuk metni; Turkce I/ı tuzagi): kod noktasiyla yazilir.</summary>
    public const string Light = "Işık";

    /// <summary>Gercek katalog + sentetik hadis paketi (public'e girebilen, test- onekli olmayan kaynak).</summary>
    public static Mutalaa.Infrastructure.Packs.PackCatalog Catalog() => new(
    [
        .. Mutalaa.Infrastructure.Packs.PackCatalog.Default.All,
        new Mutalaa.Infrastructure.Packs.PackDefinition(
            SentetikPack,
            "Sentetik hadis (test)",
            Bundled: false,
            DependsOn: [Mutalaa.Infrastructure.Packs.PackCatalog.CorePackId],
            Sources: [new Mutalaa.Infrastructure.Packs.PackSourceBinding(Sentetik, Mutalaa.Infrastructure.Packs.PackSourceRole.Content, Required: true)]),
    ]);

    public static byte[] FixtureBytes(string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "tanzil", name);
        Assert.True(File.Exists(path), "Fikstur cikti klasorune kopyalanmamis: " + path);
        return File.ReadAllBytes(path);
    }

    public static string Hash(string text) => ContentHash.Compute(text);

    public static async Task<SeededContent> SeedAsync(TestDatabase database, string rawDir, string sourcesDir, CancellationToken cancellationToken)
    {
        byte[] uthmaniBytes = FixtureBytes("uthmani-parca.txt");
        byte[] simpleBytes = FixtureBytes("simple-clean-parca.txt");
        TanzilRawFile uthmani = TanzilRawFile.Parse(uthmaniBytes);
        TanzilRawFile simple = TanzilRawFile.Parse(simpleBytes);

        PlaceRaw(rawDir, Uthmani, "quran-uthmani.txt", uthmaniBytes);
        PlaceRaw(rawDir, SimpleClean, "quran-simple-clean.txt", simpleBytes);
        Directory.CreateDirectory(sourcesDir);
        foreach (string slug in new[] { Uthmani, SimpleClean, UstVeri, Kucuk, Tefsir, Ses, Sentetik })
        {
            RegisterSource(sourcesDir, slug);
        }

        await using NpgsqlConnection connection = await database.OpenRawConnectionAsync(cancellationToken);

        async Task Exec(string sql, params (string Name, object? Value)[] parameters)
        {
            await using NpgsqlCommand command = new(sql, connection);
            TestDatabase.AddParameters(command, parameters);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }

        // --- Kaynaklar
        const string insertSource =
            """
            INSERT INTO icerik.source (slug, tur, baslik, surum, alinma_tarihi, dosya_sha256, atif_metni, notice_text)
            VALUES (@slug, @tur::icerik.source_kind, 'Sentetik kaynak (test)', '1', @date, @sha, 'Sentetik test verisi (Mutalaa).', @notice)
            """;
        DateOnly date = DateOnly.ParseExact(TanzilDate, "yyyy-MM-dd", CultureInfo.InvariantCulture);
        await Exec(insertSource, ("slug", Uthmani), ("tur", "kuran_metni"), ("date", date), ("sha", Sha(uthmaniBytes)), ("notice", uthmani.Notice));
        await Exec(insertSource, ("slug", SimpleClean), ("tur", "kuran_metni"), ("date", date), ("sha", Sha(simpleBytes)), ("notice", simple.Notice));
        await Exec(insertSource, ("slug", UstVeri), ("tur", "mushaf_duzeni"), ("date", null), ("sha", null), ("notice", null));
        await Exec(insertSource, ("slug", Kucuk), ("tur", "kitap"), ("date", null), ("sha", null), ("notice", null));
        await Exec(insertSource, ("slug", Tefsir), ("tur", "tefsir"), ("date", null), ("sha", null), ("notice", null));
        await Exec(insertSource, ("slug", Ses), ("tur", "ses"), ("date", null), ("sha", null), ("notice", null));
        await Exec(insertSource, ("slug", Sentetik), ("tur", "kitap"), ("date", null), ("sha", null), ("notice", null));

        // --- Tanzil birimleri: her satir content_hash ile; ar_norm tanzil-simple-clean metninden (K-44 madde 2); hepsi onayli.
        Dictionary<(int, int), string> simpleText = simple.Verses.ToDictionary(v => (v.Sure, v.Ayet), v => v.Text);
        string probeToken = string.Empty;
        const string insertAyah =
            """
            INSERT INTO icerik.unit (anchor, kind, source_id, ord, ayah_range, metin, marks, content_hash, metin_durumu, ar_norm, attrs, data_version)
            VALUES (@anchor, 'ayet'::icerik.unit_kind, @source, @ord, int4range(@lo, @hi), @metin, '[]'::jsonb, @hash, 'onayli'::icerik.metin_durumu, @ar, '{}'::jsonb, 'test')
            """;
        const string insertWord =
            """
            INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index, text_uthmani, norm, char_start, char_end, source_id, data_version)
            VALUES (@anchor, @surah, @ayah, @word, @index, @text, @norm, @start, @end, @source, 'test')
            """;
        for (int i = 0; i < uthmani.Verses.Count; i++)
        {
            TanzilVerse verse = uthmani.Verses[i];
            int index = i + 1;
            string anchor = string.Create(CultureInfo.InvariantCulture, $"q:{verse.Sure}:{verse.Ayet}");
            string arNorm = SearchNormalizer.Arabic(simpleText[(verse.Sure, verse.Ayet)]);
            if (probeToken.Length == 0)
            {
                probeToken = arNorm.Split(' ', StringSplitOptions.RemoveEmptyEntries)[0];
            }

            await Exec(
                insertAyah,
                ("anchor", anchor),
                ("source", Uthmani),
                ("ord", (long)index),
                ("lo", index),
                ("hi", index + 1),
                ("metin", verse.Text),
                ("hash", Hash(verse.Text)),
                ("ar", arNorm));

            int word = 0;
            int from = 0;
            while (from < verse.Text.Length)
            {
                int space = verse.Text.IndexOf(' ', from);
                int end = space < 0 ? verse.Text.Length : space;
                if (end > from)
                {
                    word++;
                    string text = verse.Text[from..end];
                    int start = verse.Text[..from].EnumerateRunes().Count();
                    string norm = SearchNormalizer.Arabic(text);
                    await Exec(
                        insertWord,
                        ("anchor", string.Create(CultureInfo.InvariantCulture, $"{anchor}:{word}")),
                        ("surah", verse.Sure),
                        ("ayah", verse.Ayet),
                        ("word", word),
                        ("index", index),
                        ("text", text),
                        ("norm", norm.Length == 0 ? text : norm),
                        ("start", start),
                        ("end", start + text.EnumerateRunes().Count()),
                        ("source", Uthmani));
                }

                from = end + 1;
            }
        }

        // --- Yapi: bir isaret ve bir sayfa (tanzil-ust-veri).
        await Exec(
            "INSERT INTO icerik.quran_marker (kind, no, anchor, secde_turu, source_id, data_version) VALUES ('cuz', 1, 'q:1:1', NULL, @s, 'test')",
            ("s", UstVeri));
        await Exec(
            "INSERT INTO icerik.page_map (source_id, volume, page, line, start_anchor, end_anchor, data_version) VALUES (@s, NULL, 1, NULL, 'q:1:1', 'q:1:7', 'test')",
            ("s", UstVeri));

        // --- Metin birimleri (sentetik). Onayli, taslak ve yapay zeka taslagi.
        await InsertTextUnitAsync(Exec, SentetikApproved, "kitap", Sentetik, 1, "Deneme paragrafi 1 (onayli).", "onayli");
        await InsertTextUnitAsync(Exec, SentetikDraft, "kitap", Sentetik, 2, "Deneme paragrafi 2 (taslak).", "taslak");
        await InsertTextUnitAsync(Exec, SentetikAi, "kitap", Sentetik, 3, "Deneme paragrafi 3 (yapay zeka taslagi).", "taslak");
        await Exec(
            """
            INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, yz_modeli, yz_kaydi, oneren)
            VALUES ('unit', @a, 'metin', 'oner', 'hat'::icerik.xref_origin, 'deneme-model',
                    jsonb_build_object('prompt_id', 'p1', 'prompt_sha256', @h1::text, 'input_sha256', @h2::text), 'test-hat')
            """,
            ("a", SentetikAi),
            ("h1", new string('a', 64)),
            ("h2", new string('b', 64)));

        await InsertTextUnitAsync(Exec, KucukFirst, "kitap", Kucuk, 1, "Deneme paragrafi 4 " + Light + " ile baslar.", "onayli");
        await InsertTextUnitAsync(Exec, KucukSecond, "kitap", Kucuk, 2, "Deneme paragrafi 5 (ikinci).", "onayli");
        await InsertTextUnitAsync(Exec, TefsirFirst, "tefsir", Tefsir, 1, "Deneme paragrafi 6 (tefsir ornegi).", "onayli", ayahLo: 1, ayahHi: 2);

        // --- Baglantilar (P-07): her durumdan ve esigin altinda/ustunden.
        SeededXref[] xrefs =
        [
            new("atif-onayli", XrefId(1), "atif", "q:1:1", SentetikApproved, "onayli", 0.80f),
            new("atif-aday", XrefId(2), "atif", "q:1:2", SentetikApproved, "aday", 0.80f),
            new("atif-red", XrefId(3), "atif", "q:1:3", SentetikApproved, "red", 0.80f),
            new("kok-yuksek", XrefId(4), "kok", "q:1:1", "q:1:2", "aday", 0.90f),
            new("kok-orta", XrefId(5), "kok", "q:1:2", "q:1:3", "aday", 0.60f),
            new("kok-dusuk", XrefId(6), "kok", "q:1:3", "q:1:4", "aday", 0.30f),
            new("iktibas-kucuk", XrefId(7), "iktibas", "q:1:1", KucukFirst, "aday", 0.80f),
            new("ima-tefsir", XrefId(8), "ima", "q:1:1", TefsirFirst, "onayli", 0.80f),
        ];
        foreach (SeededXref xref in xrefs)
        {
            await Exec(
                """
                INSERT INTO icerik.xref (id, src_anchor, dst_anchor, type, score, confidence, evidence, origin, status, data_version)
                VALUES (@id, @src, @dst, @type::icerik.xref_type, 0.5, @conf, '{}'::jsonb, @origin::icerik.xref_origin, @status::icerik.xref_status, 'dv-1')
                """,
                ("id", xref.Id),
                ("src", xref.Src),
                ("dst", xref.Dst),
                ("type", xref.Type),
                ("conf", xref.Confidence),
                ("origin", xref.Status == "onayli" ? "editor" : "hat"),
                ("status", xref.Status));
        }

        // --- Sozluk duzeltmeleri (P-09): biri onayli, biri aday.
        await Exec(
            "INSERT INTO icerik.quran_word_fix (anchor, field, new_value, reason, status) VALUES ('q:1:1:1', 'pos', 'N', 'deneme', 'onayli'::icerik.xref_status), ('q:1:1:2', 'pos', 'N', 'deneme', 'aday'::icerik.xref_status)");

        return new SeededContent(
            xrefs.ToDictionary(x => x.Name, x => x, StringComparer.Ordinal),
            uthmani.Notice,
            simple.Notice,
            uthmani,
            probeToken);
    }

    public static void RegisterSource(string sourcesDir, string slug) =>
        File.WriteAllText(Path.Combine(sourcesDir, slug + ".toml"), "slug = \"" + slug + "\"\n");

    private static Guid XrefId(int n) => Guid.Parse(string.Create(CultureInfo.InvariantCulture, $"00000000-0000-7000-8000-{n:D12}"));

    private static string Sha(byte[] data) => Convert.ToHexStringLower(SHA256.HashData(data));

    private static void PlaceRaw(string rawDir, string slug, string fileName, byte[] data)
    {
        string dir = Path.Combine(rawDir, slug, TanzilDate);
        Directory.CreateDirectory(dir);
        File.WriteAllBytes(Path.Combine(dir, fileName), data);
    }

    private static async Task InsertTextUnitAsync(
        Func<string, (string Name, object? Value)[], Task> exec,
        string anchor,
        string kind,
        string source,
        long ord,
        string metin,
        string durum,
        int? ayahLo = null,
        int? ayahHi = null)
    {
        SearchKeys keys = SearchNormalizer.Keys(metin);
        await exec(
            """
            INSERT INTO icerik.unit (anchor, kind, source_id, ord, ayah_range, metin, marks, content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, attrs, data_version)
            VALUES (@anchor, @kind::icerik.unit_kind, @source, @ord,
                    CASE WHEN @lo::int IS NULL THEN NULL ELSE int4range(@lo::int, @hi::int) END,
                    @metin, '[]'::jsonb, @hash, @durum::icerik.metin_durumu, @narrow, @wide, @stem, '{}'::jsonb, 'test')
            """,
            [
                ("anchor", anchor),
                ("kind", kind),
                ("source", source),
                ("ord", ord),
                ("lo", ayahLo),
                ("hi", ayahHi),
                ("metin", metin),
                ("hash", Hash(metin)),
                ("durum", durum),
                ("narrow", keys.TrNarrow),
                ("wide", keys.TrWide),
                ("stem", keys.TrWide),
            ]);
    }
}
