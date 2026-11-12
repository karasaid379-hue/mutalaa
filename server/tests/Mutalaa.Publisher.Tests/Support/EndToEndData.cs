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
    public const string Qac = "qac-morfoloji";
    public const string Wbw = "quranwbw-tr";

    /// <summary>Sentetik kok harfleri (gercek kok degil; \u kacisli, uydurma harf dizileri). Kelime ya da ayet metni degildir.</summary>
    public const string SyntheticRoot1 = "\u0628\u062A\u062B";
    public const string SyntheticRoot2 = "\u062C\u062D\u062E";

    public const string TanzilDate = "2026-11-02";

    public const string KucukPack = "test-kucuk";
    public const string TefsirPack = "tefsir-test-ornek";
    public const string SentetikPack = "hadis-sentetik";
    public const string KelimeKokPack = "kelime-kok";

    /// <summary>Sozluk fiksturu: lemma 1 onayli anlam, 2 ve 3 aday anlam, 4 red anlam tasir; 5. lemmanin anlami yoktur.</summary>
    public const int LemmaApproved = 1;
    public const int LemmaCandidate1 = 2;
    public const int LemmaCandidate2 = 3;
    public const int LemmaRejected = 4;

    /// <summary>Tohumlanan quran_word_fix satirlari: iki onayli (uygulanir), bir aday ve bir red (uygulanmaz).</summary>
    public const string FixApprovedPos = "q:1:1:1";
    public const string FixApprovedRoot = "q:1:1:2";
    public const string FixCandidate = "q:1:1:3";
    public const string FixRejected = "q:1:2:1";

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
        foreach (string slug in new[] { Uthmani, SimpleClean, UstVeri, Kucuk, Tefsir, Ses, Sentetik, Qac, Wbw })
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
        await Exec(insertSource, ("slug", Qac), ("tur", "morfoloji"), ("date", null), ("sha", null), ("notice", null));
        await Exec(insertSource, ("slug", Wbw), ("tur", "kelime_anlami"), ("date", null), ("sha", null), ("notice", null));

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

        // --- Sozluk (K-50): sentetik QAC kokleri, lemmalari ve kelime morfolojisi; hepsi uydurma harf dizisi ve etikettir (gercek kok ya da lemma degildir).
        const string insertRoot =
            """
            INSERT INTO icerik.root (id, letters, occurrences, ayah_count, idf_q, source_id, data_version)
            VALUES (@id, @letters, 3, 2, 0.5, @source, 'test')
            """;
        await Exec(insertRoot, ("id", 1), ("letters", SyntheticRoot1), ("source", Qac));
        await Exec(insertRoot, ("id", 2), ("letters", SyntheticRoot2), ("source", Qac));
        const string insertLemma =
            """
            INSERT INTO icerik.lemma (id, lang, text, text_clean, root_id, occurrences, qac_ref, origin, status, source_id, data_version)
            VALUES (@id, 'ar', @text, @text, @root, 3, @ref, 'qac', 'onayli'::icerik.xref_status, @source, 'test')
            """;
        for (int lemma = 1; lemma <= 5; lemma++)
        {
            await Exec(
                insertLemma,
                ("id", lemma),
                ("text", lemma % 2 == 0 ? SyntheticRoot2 : SyntheticRoot1),
                ("root", lemma % 2 == 0 ? 2 : 1),
                ("ref", string.Create(CultureInfo.InvariantCulture, $"deneme-{lemma}")),
                ("source", Qac));
        }

        // QAC sutunlari (yalniz ilk iki ayetin kelimeleri): pos 'V' ve features sentetiktir; Tanzil sutunlarina dokunulmaz.
        await Exec(
            """
            UPDATE icerik.quran_word
               SET root_id = 1, lemma_id = 1, pos = 'V', features = '{"deneme": "1"}'::jsonb, morph_source = @source
             WHERE ayah_index IN (1, 2)
            """,
            ("source", Qac));

        // --- Anlamlar (K-50 madde 5 ve 8): onayli, iki aday ve bir red; content_hash anlam_kisa'dan.
        const string insertGloss =
            """
            INSERT INTO icerik.lemma_gloss (lemma_id, anlam_kisa, origin, version, content_hash, status)
            VALUES (@id, @anlam, @origin, '1', @hash, @status::icerik.xref_status)
            """;
        (int Lemma, string Status, string Origin)[] glosses =
        [
            (LemmaApproved, "onayli", "editor"),
            (LemmaCandidate1, "aday", "kaynak:quranwbw-tr"),
            (LemmaCandidate2, "aday", "kaynak:quranwbw-tr"),
            (LemmaRejected, "red", "kaynak:quranwbw-tr"),
        ];
        foreach ((int lemma, string status, string origin) in glosses)
        {
            string anlam = string.Create(CultureInfo.InvariantCulture, $"Deneme anlam {lemma}");
            await Exec(insertGloss, ("id", lemma), ("anlam", anlam), ("origin", origin), ("hash", Hash(anlam)), ("status", status));
        }

        // --- Sozluk duzeltmeleri (P-09): iki onayli (biri pos, biri root_id), bir aday, bir red.
        await Exec(
            """
            INSERT INTO icerik.quran_word_fix (anchor, field, new_value, reason, status) VALUES
              (@a1, 'pos', 'N', 'deneme', 'onayli'::icerik.xref_status),
              (@a2, 'root_id', '2', 'deneme', 'onayli'::icerik.xref_status),
              (@a3, 'pos', 'N', 'deneme', 'aday'::icerik.xref_status),
              (@a4, 'pos', 'N', 'deneme', 'red'::icerik.xref_status)
            """,
            ("a1", FixApprovedPos),
            ("a2", FixApprovedRoot),
            ("a3", FixCandidate),
            ("a4", FixRejected));

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
