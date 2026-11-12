using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// EditorialSnapshotReader (Docker: postgres:18.6 kabi, goc edilmis veritabani). Sentetik satirlar ham SQL ile eklenir (gercek Kur'an, meal ya da Risale metni yok).
/// Siniftaki testler tek veritabanini paylasir: her test kendi on ekiyle benzersiz slug ve capa kullanir ve yalniz kendi satirlarini denetler.
/// </summary>
public partial class EditorialSnapshotReaderTests(EditorialDatabase<EditorialSnapshotReaderTests> fixture) : IClassFixture<EditorialDatabase<EditorialSnapshotReaderTests>>
{
    private static readonly string HashA = new('a', 64);
    private static readonly string HashB = new('b', 64);

    private TestDatabase Db => fixture.Database;

    [GeneratedRegex("tsv_", RegexOptions.CultureInvariant)]
    private static partial Regex TsvColumn();

    private static string Unique(string prefix) =>
        prefix + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..8];

    private Task InsertSourceAsync(string slug, string tur = "kitap", string? notice = null, CancellationToken ct = default) =>
        Db.ExecuteAsync(
            """
            INSERT INTO icerik.source (slug, tur, baslik, yazar, surum, provider, kaynak_url, alinma_tarihi, dosya_sha256, baski_bilgisi, atif_metni, atif_url, notice_text, notlar)
            VALUES (@slug, @tur::icerik.source_kind, 'Deneme kaynagi', 'Deneme yazari', '1', 'deneme', 'https://example.invalid/k', DATE '2026-11-02', @sha, '{"cilt": 1}'::jsonb,
                    'Sentetik test verisi (Mutalaa).', 'https://example.invalid/a', @notice, 'Deneme notu')
            """,
            ct,
            ("slug", slug),
            ("tur", tur),
            ("sha", HashA),
            ("notice", notice));

    private Task InsertUnitAsync(
        string anchor,
        string sourceId,
        string kind = "kitap",
        string durum = "taslak",
        long ord = 1,
        string metin = "Deneme paragrafi 1",
        int? lo = null,
        int? hi = null,
        CancellationToken ct = default) =>
        Db.ExecuteAsync(
            """
            INSERT INTO icerik.unit (anchor, kind, source_id, ord, ayah_range, metin, marks, sentences, content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, ar_norm, attrs, data_version)
            VALUES (@anchor, @kind::icerik.unit_kind, @source, @ord,
                    CASE WHEN @lo::int IS NULL THEN NULL ELSE int4range(@lo::int, @hi::int) END,
                    @metin, '[{"s": 0, "e": 3, "t": "ar"}]'::jsonb, ARRAY[int4range(0, 14), int4range(15, 30)], @hash, @durum::icerik.metin_durumu,
                    'tn', 'tw', 'ts', 'an', '{"cilt": 1}'::jsonb, 'test')
            """,
            ct,
            ("anchor", anchor),
            ("kind", kind),
            ("source", sourceId),
            ("ord", ord),
            ("lo", lo),
            ("hi", hi),
            ("metin", metin),
            ("hash", HashA),
            ("durum", durum));

    [Fact]
    public async Task It_opens_a_repeatable_read_read_only_transaction()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);

        (string isolation, string readOnly) = await reader.ReadTransactionModeAsync(ct);

        Assert.Equal("repeatable read", isolation);
        Assert.Equal("on", readOnly);
    }

    [Fact]
    public async Task It_reads_source_and_unit_columns_with_enums_as_text_and_ranges_as_bounds()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-okuma-");
        await InsertSourceAsync(slug, "kitap", "bildirim\nsatiri", ct);
        await InsertUnitAsync($"k:{slug}:p1", slug, "kitap", "onayli", lo: 7, hi: 8, ct: ct);
        await InsertUnitAsync($"k:{slug}:p2", slug, "meal", "taslak", ord: 2, ct: ct);

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        IReadOnlyList<SourceRow> sources = await reader.ReadSourcesAsync(ct);
        List<UnitRow> units = [];
        await foreach (UnitRow unit in reader.ReadUnitsAsync(ct))
        {
            if (unit.SourceId == slug)
            {
                units.Add(unit);
            }
        }

        SourceRow source = sources.Single(s => s.Slug == slug);
        Assert.Equal(
            ("kitap", "Deneme kaynagi", "Deneme yazari", "1", "deneme", "https://example.invalid/k", new DateOnly(2026, 11, 2), HashA),
            (source.Tur, source.Baslik, source.Yazar, source.Surum, source.Provider, source.KaynakUrl, source.AlinmaTarihi, source.DosyaSha256));
        Assert.Equal(("Sentetik test verisi (Mutalaa).", "https://example.invalid/a", "bildirim\nsatiri", "Deneme notu"), (source.AtifMetni, source.AtifUrl, source.NoticeText, source.Notlar));
        Assert.Equal(1, JsonDocument.Parse(source.BaskiBilgisi!).RootElement.GetProperty("cilt").GetInt32());

        UnitRow first = Assert.Single(units, u => u.Anchor == $"k:{slug}:p1");
        Assert.Equal(("kitap", "govde", slug, (string?)null, 1L), (first.Kind, first.Role, first.SourceId, first.ParentPath, first.Ord));
        Assert.Equal((7, 8), (first.AyahLo, first.AyahHi));
        Assert.Equal(("onayli", "etkin", (string?)null), (first.MetinDurumu, first.Status, first.Successors));
        Assert.Equal("Deneme paragrafi 1", first.Metin);
        Assert.Equal(HashA, first.ContentHash);
        Assert.Equal(("tw", "ts", "an"), (first.TrWide, first.TrStem, first.ArNorm));
        Assert.False(first.IsAiDraft);
        Assert.Equal(3, JsonDocument.Parse(first.Marks).RootElement[0].GetProperty("e").GetInt32());
        Assert.Equal(1, JsonDocument.Parse(first.Attrs).RootElement.GetProperty("cilt").GetInt32());
        Assert.Equal("[[0, 14], [15, 30]]", first.SentencesJson);

        UnitRow second = units.Single(u => u.Anchor == $"k:{slug}:p2");
        Assert.Equal(("meal", "taslak", (int?)null, (int?)null), (second.Kind, second.MetinDurumu, second.AyahLo, second.AyahHi));
    }

    [Fact]
    public async Task Units_are_ordered_by_anchor_bytes_not_numerically()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-sira-");
        await InsertSourceAsync(slug, ct: ct);
        foreach (string suffix in new[] { "p2", "p10", "p1" })
        {
            await InsertUnitAsync($"k:{slug}:{suffix}", slug, ct: ct);
        }

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        List<string> anchors = [];
        await foreach (UnitRow unit in reader.ReadUnitsAsync(ct))
        {
            if (unit.SourceId == slug)
            {
                anchors.Add(unit.Anchor);
            }
        }

        Assert.Equal([$"k:{slug}:p1", $"k:{slug}:p10", $"k:{slug}:p2"], anchors);
    }

    [Fact]
    public async Task An_unapproved_unit_with_a_review_carrying_an_ai_record_is_an_ai_draft()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-yz-");
        await InsertSourceAsync(slug, ct: ct);
        await InsertUnitAsync($"k:{slug}:p1", slug, ct: ct);
        await InsertUnitAsync($"k:{slug}:p2", slug, ord: 2, ct: ct);
        await InsertUnitAsync($"k:{slug}:p3", slug, ord: 3, ct: ct);
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, yz_modeli, yz_kaydi, oneren)
            VALUES ('unit', @a, 'metin', 'oner', 'hat'::icerik.xref_origin, 'deneme-model',
                    jsonb_build_object('prompt_id', 'p1', 'prompt_sha256', @h1::text, 'input_sha256', @h2::text), 'test-hat')
            """,
            ct,
            ("a", $"k:{slug}:p1"),
            ("h1", HashA),
            ("h2", HashB));
        await Db.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('unit', @a, 'metin', 'oner', 'hat'::icerik.xref_origin, 'test-hat')",
            ct,
            ("a", $"k:{slug}:p2"));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        Dictionary<string, bool> flags = [];
        await foreach (UnitRow unit in reader.ReadUnitsAsync(ct))
        {
            if (unit.SourceId == slug)
            {
                flags[unit.Anchor] = unit.IsAiDraft;
            }
        }

        Assert.Equal(
            [($"k:{slug}:p1", true), ($"k:{slug}:p2", false), ($"k:{slug}:p3", false)],
            flags.OrderBy(p => p.Key, StringComparer.Ordinal).Select(p => (p.Key, p.Value)));
    }

    [Fact]
    public async Task It_streams_xrefs_with_real_scores_spans_evidence_and_the_lexicon_status()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-xref-");
        Guid open = Guid.NewGuid();
        Guid closed = Guid.NewGuid();
        await InsertSourceAsync(slug, ct: ct);
        await InsertUnitAsync($"k:{slug}:p1", slug, ct: ct);
        await InsertUnitAsync($"k:{slug}:p2", slug, ord: 2, ct: ct);
        const string insertXref =
            """
            INSERT INTO icerik.xref (id, src_anchor, src_span, dst_anchor, dst_span, type, score, confidence, evidence, origin, status, data_version)
            VALUES (@id, @src, int4range(3, 8), @dst, NULL, 'kok'::icerik.xref_type, 0.7, 0.9, @ev::jsonb, 'hat'::icerik.xref_origin, 'aday'::icerik.xref_status, 'dv-1')
            """;
        await Db.ExecuteAsync(insertXref, ct, ("id", open), ("src", $"k:{slug}:p1"), ("dst", $"k:{slug}:p2"), ("ev", "{\"lexicon_status\": \"aday\", \"group\": 2}"));
        await Db.ExecuteAsync(
            insertXref.Replace("'kok'", "'lemma'", StringComparison.Ordinal),
            ct,
            ("id", closed),
            ("src", $"k:{slug}:p1"),
            ("dst", $"k:{slug}:p2"),
            ("ev", "{}"));
        string reviewSql = "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, xref_id, alan, eylem, durum, koken, oneren) VALUES ('xref', @k, @x, 'status', 'oner', @d::icerik.inceleme_durumu, 'hat'::icerik.xref_origin, 'test-hat')";
        await Db.ExecuteAsync(reviewSql, ct, ("k", open.ToString()), ("x", open), ("d", "acik"));
        await Db.ExecuteAsync(reviewSql, ct, ("k", closed.ToString()), ("x", closed), ("d", "onaylandi"));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        List<XrefRow> xrefs = [];
        await foreach (XrefRow xref in reader.ReadXrefsAsync(ct))
        {
            if (xref.Id == open || xref.Id == closed)
            {
                xrefs.Add(xref);
            }
        }

        IReadOnlySet<Guid> reviews = await reader.ReadOpenReviewXrefIdsAsync(ct);

        XrefRow a = xrefs.Single(x => x.Id == open);
        Assert.Equal(("kok", "aday", "dv-1", "aday"), (a.Type, a.Status, a.DataVersion, a.LexiconStatus));
        Assert.Equal((3, 8, (int?)null, (int?)null), (a.SrcLo, a.SrcHi, a.DstLo, a.DstHi));
        Assert.Equal(0.7f, a.Score);
        Assert.Equal(0.9f, a.Confidence);
        Assert.Equal(2, JsonDocument.Parse(a.Evidence).RootElement.GetProperty("group").GetInt32());
        Assert.Equal("lemma", xrefs.Single(x => x.Id == closed).Type);
        Assert.Null(xrefs.Single(x => x.Id == closed).LexiconStatus);
        Assert.Contains(open, reviews);
        Assert.DoesNotContain(closed, reviews);
    }

    [Fact]
    public async Task It_reads_quran_words_markers_and_page_maps()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-yapi-");
        await InsertSourceAsync(slug, "mushaf_duzeni", ct: ct);
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index, text_uthmani, norm, char_start, char_end, source_id, data_version)
            VALUES ('q:1:1:1', 1, 1, 1, 1, 'deneme', 'deneme', 0, 6, @s, 'test'), ('q:1:1:2', 1, 1, 2, 1, 'deneme2', 'deneme2', 7, 14, @s, 'test')
            """,
            ct,
            ("s", slug));
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.quran_marker (kind, no, anchor, secde_turu, source_id, data_version)
            VALUES ('cuz', 1, 'q:1:1', NULL, @s, 'test'), ('secde', 1, 'q:1:2', 'recommended', @s, 'test')
            """,
            ct,
            ("s", slug));
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.page_map (source_id, volume, page, line, start_anchor, end_anchor, data_version)
            VALUES (@s, NULL, 2, NULL, 'q:1:2', 'q:1:3', 'test'), (@s, NULL, 1, NULL, 'q:1:1', 'q:1:2', 'test')
            """,
            ct,
            ("s", slug));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        List<QuranWordRow> words = [];
        await foreach (QuranWordRow word in reader.ReadQuranWordsAsync(ct))
        {
            if (word.SourceId == slug)
            {
                words.Add(word);
            }
        }

        IReadOnlyList<QuranMarkerRow> markers = await reader.ReadQuranMarkersAsync(ct);
        IReadOnlyList<PageMapRow> pages = await reader.ReadPageMapsAsync(ct);

        Assert.Equal(["q:1:1:1", "q:1:1:2"], words.Select(w => w.Anchor));
        Assert.Equal((1, 1, 1, 1, "deneme", 0, 6), (words[0].Surah, words[0].Ayah, words[0].Word, words[0].AyahIndex, words[0].TextUthmani, words[0].CharStart, words[0].CharEnd));
        Assert.Equal(
            [("cuz", 1, "q:1:1", (string?)null), ("secde", 1, "q:1:2", "recommended")],
            markers.Where(m => m.SourceId == slug).Select(m => (m.Kind, m.No, m.Anchor, m.SecdeTuru)));
        Assert.Equal(
            [(1, "q:1:1", "q:1:2"), (2, "q:1:2", "q:1:3")],
            pages.Where(p => p.SourceId == slug).Select(p => (p.Page, p.StartAnchor, p.EndAnchor)));
        Assert.All(pages.Where(p => p.SourceId == slug), p => Assert.Null(p.Volume));
    }

    [Fact]
    public async Task It_reads_the_dictionary_rows_and_qac_word_columns_only_for_the_lexicon_sources()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string other = Unique("test-sozluk-");
        await InsertSourceAsync(PackCatalog.QacMorphologySlug, "morfoloji", ct: ct);
        await InsertSourceAsync(PackCatalog.GlossSourceSlug, "kelime_anlami", ct: ct);
        await InsertSourceAsync(other, "sozluk", ct: ct);
        int rootId = 96000 + Random.Shared.Next(0, 1000);
        int lemmaId = rootId + 1000;
        int trLemmaId = rootId + 2000;
        int otherLemmaId = rootId + 3000;
        string letters = string.Create(CultureInfo.InvariantCulture, $"بت{rootId}");
        await Db.ExecuteAsync(
            "INSERT INTO icerik.root (id, letters, occurrences, ayah_count, idf_q, kok_anlami, source_id, data_version) VALUES (@id, @l, 7, 3, 0.25, 'deneme kok', @s, 'test'), (@id2, @l2, 1, 1, NULL, NULL, @o, 'test')",
            ct,
            ("id", rootId),
            ("l", letters),
            ("s", PackCatalog.QacMorphologySlug),
            ("id2", rootId + 1),
            ("l2", letters + "x"),
            ("o", other));
        const string lemmaSql =
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, root_id, occurrences, qac_ref, etymological_only, origin, status, source_id, data_version, onay_yolu) VALUES (@id, @lang, 'deneme', 'deneme-' || @id, @root, 2, @ref, true, 'qac', @st::icerik.xref_status, @s, 'test', CASE WHEN @lang = 'tr' AND @st = 'onayli' THEN 'editor' END)";
        await Db.ExecuteAsync(lemmaSql, ct, ("id", lemmaId), ("lang", "ar"), ("root", rootId), ("ref", "deneme-" + lemmaId), ("st", "onayli"), ("s", PackCatalog.QacMorphologySlug));
        await Db.ExecuteAsync(lemmaSql, ct, ("id", trLemmaId), ("lang", "tr"), ("root", null), ("ref", null), ("st", "onayli"), ("s", PackCatalog.QacMorphologySlug));
        await Db.ExecuteAsync(lemmaSql, ct, ("id", otherLemmaId), ("lang", "ar"), ("root", null), ("ref", "deneme-" + otherLemmaId), ("st", "aday"), ("s", other));
        const string glossSql =
            "INSERT INTO icerik.lemma_gloss (lemma_id, anlam_kisa, kuran_anlamlari, turkce_es_kelime, yalnizca_etimolojik, origin, version, content_hash, status) VALUES (@id, 'Deneme anlam', '[\"a\"]'::jsonb, 'es', true, 'kaynak:quranwbw-tr', '1', @h, 'aday'::icerik.xref_status)";
        await Db.ExecuteAsync(glossSql, ct, ("id", lemmaId), ("h", HashA));
        await Db.ExecuteAsync(glossSql, ct, ("id", trLemmaId), ("h", HashB));
        await Db.ExecuteAsync(glossSql, ct, ("id", otherLemmaId), ("h", HashB));
        int surah = 60 + Random.Shared.Next(0, 50);
        await Db.ExecuteAsync(
            """
            INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index, text_uthmani, norm, char_start, char_end, root_id, lemma_id, pos, features, source_id, morph_source, data_version)
            VALUES (@a1, @sur, 1, 1, 1, 'deneme', 'deneme', 0, 6, @root, @lemma, 'V', '{"b": 2, "a": 1}'::jsonb, @s, @qac, 'test'),
                   (@a2, @sur, 1, 2, 1, 'deneme', 'deneme', 7, 13, @root, @lemma, 'N', '{"c": 3}'::jsonb, @s, @o, 'test'),
                   (@a3, @sur, 1, 3, 1, 'deneme', 'deneme', 14, 20, NULL, NULL, NULL, NULL, @s, NULL, 'test')
            """,
            ct,
            ("a1", $"q:{surah}:1:1"),
            ("a2", $"q:{surah}:1:2"),
            ("a3", $"q:{surah}:1:3"),
            ("sur", surah),
            ("root", rootId),
            ("lemma", lemmaId),
            ("s", PackCatalog.QacMorphologySlug),
            ("qac", PackCatalog.QacMorphologySlug),
            ("o", other));
        Guid fixId = Guid.CreateVersion7();
        await Db.ExecuteAsync(
            "INSERT INTO icerik.quran_word_fix (id, anchor, field, new_value, reason, status) VALUES (@id, @a, 'features', '{\"z\": 1}', 'deneme', 'onayli'::icerik.xref_status)",
            ct,
            ("id", fixId),
            ("a", $"q:{surah}:1:1"));

        try
        {
            await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
            List<QuranWordRow> words = [];
            await foreach (QuranWordRow word in reader.ReadQuranWordsAsync(ct))
            {
                if (word.Surah == surah)
                {
                    words.Add(word);
                }
            }

            IReadOnlyList<RootRow> roots = await reader.ReadRootsAsync(ct);
            IReadOnlyList<LemmaRow> lemmas = await reader.ReadLemmasAsync(ct);
            IReadOnlyList<LemmaGlossRow> glosses = await reader.ReadLemmaGlossesAsync(ct);
            IReadOnlyList<QuranWordFixRow> fixes = await reader.ReadWordFixesAsync(ct);

            // QAC sutunlari yalniz morph_source sozluk kaynagiysa okunur; digerinde (ve kaynaksiz satirda) bostur.
            Assert.Equal(
                [(rootId, lemmaId, "V", PackCatalog.QacMorphologySlug), ((int?)null, (int?)null, (string?)null, (string?)null), (null, null, null, null)],
                words.OrderBy(w => w.Word).Select(w => (w.RootId, w.LemmaId, w.Pos, w.MorphSource)));
            Assert.Equal("{\"a\": 1, \"b\": 2}", words.Single(w => w.Word == 1).Features);
            Assert.All(words.Where(w => w.Word != 1), w => Assert.Null(w.Features));

            RootRow root = Assert.Single(roots, r => r.Id == rootId);
            Assert.Equal((letters, 7, 3, 0.25f, "deneme kok", PackCatalog.QacMorphologySlug), (root.Letters, root.Occurrences, root.AyahCount, root.IdfQ, root.KokAnlami, root.SourceId));
            Assert.DoesNotContain(roots, r => r.Id == rootId + 1);
            Assert.All(roots, r => Assert.Contains(r.SourceId, PackCatalog.LexiconSourceSlugs));

            // Yalniz lang = 'ar' ve sozluk kaynagi; durum metni okunur (pakete yalniz onayli girer).
            LemmaRow lemma = Assert.Single(lemmas, l => l.Id == lemmaId);
            Assert.Equal((rootId, 2, true, "onayli"), (lemma.RootId, lemma.Occurrences, lemma.EtymologicalOnly, lemma.Status));
            Assert.DoesNotContain(lemmas, l => l.Id == trLemmaId || l.Id == otherLemmaId);

            LemmaGlossRow gloss = Assert.Single(glosses, g => g.LemmaId == lemmaId);
            Assert.Equal(("Deneme anlam", "[\"a\"]", "es", true, "aday", "kaynak:quranwbw-tr", "1"), (gloss.AnlamKisa, gloss.KuranAnlamlari, gloss.TurkceEsKelime, gloss.YalnizcaEtimolojik, gloss.Status, gloss.Origin, gloss.Version));
            Assert.DoesNotContain(glosses, g => g.LemmaId == trLemmaId || g.LemmaId == otherLemmaId);

            QuranWordFixRow fix = Assert.Single(fixes, f => f.Id == fixId);
            Assert.Equal(($"q:{surah}:1:1", "features", "{\"z\": 1}", "onayli"), (fix.Anchor, fix.Field, fix.NewValue, fix.Status));

            // Anlik goruntu hepsini tek islemde toplar.
            EditorialSnapshot snapshot = await reader.LoadAsync(BuildFlavor.Dev, ct);
            Assert.Contains(snapshot.Roots, r => r.Id == rootId);
            Assert.Contains(snapshot.Lemmas, l => l.Id == lemmaId);
            Assert.Contains(snapshot.LemmaGlosses, g => g.LemmaId == lemmaId);
            Assert.Contains(snapshot.WordFixes, f => f.Id == fixId);
        }
        finally
        {
            // Bu sinifin baska testi (P-09 durum satirlari) quran_word_fix tablosunda tek satir bekler: kendi satirimizi kaldiririz.
            await Db.ExecuteAsync("DELETE FROM icerik.quran_word_fix WHERE id = @id", CancellationToken.None, ("id", fixId));
        }
    }

    [Fact]
    public async Task It_returns_no_dictionary_rows_when_the_lexicon_tables_hold_none_of_the_lexicon_sources()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string other = Unique("test-bos-");
        await InsertSourceAsync(other, "sozluk", ct: ct);
        int rootId = 97000 + Random.Shared.Next(0, 1000);
        await Db.ExecuteAsync(
            "INSERT INTO icerik.root (id, letters, source_id, data_version) VALUES (@id, @l, @s, 'test')",
            ct,
            ("id", rootId),
            ("l", string.Create(CultureInfo.InvariantCulture, $"جح{rootId}")),
            ("s", other));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);

        Assert.DoesNotContain(await reader.ReadRootsAsync(ct), r => r.SourceId == other);
    }

    [Fact]
    public async Task It_reads_the_lexical_status_rows_for_p09()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-sozluk-");
        await InsertSourceAsync(slug, "kelime_anlami", ct: ct);
        int approvedLemma = 91000 + Random.Shared.Next(0, 1000);
        int candidateLemma = approvedLemma + 1000;
        const string lemmaSql = "INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version, status, onay_yolu) VALUES (@id, 'tr', 'deneme', 'deneme-' || @id, @s, 'test', @st::icerik.xref_status, CASE WHEN @st = 'onayli' THEN 'editor' END)";
        await Db.ExecuteAsync(lemmaSql, ct, ("id", approvedLemma), ("s", slug), ("st", "onayli"));
        await Db.ExecuteAsync(lemmaSql, ct, ("id", candidateLemma), ("s", slug), ("st", "aday"));
        await Db.ExecuteAsync(
            "INSERT INTO icerik.lemma_gloss (lemma_id, anlam_kisa, origin, version, content_hash, status) VALUES (@id, 'deneme', 'editor', '1', @h, 'onayli'::icerik.xref_status)",
            ct,
            ("id", approvedLemma),
            ("h", HashA));
        await Db.ExecuteAsync(
            "INSERT INTO icerik.quran_word_fix (anchor, field, new_value, reason, status) VALUES (@a, 'pos', 'N', 'deneme', 'aday'::icerik.xref_status)",
            ct,
            ("a", $"q:1:{approvedLemma % 100 + 1}:1"));
        await Db.ExecuteAsync(
            "INSERT INTO icerik.tr_form (key_wide, key_narrow, tr_lemma_id, freq, data_version) VALUES (@w, @n, @id, 1, 'test'), (@w, @n, @id2, 1, 'test')",
            ct,
            ("w", slug),
            ("n", slug),
            ("id", approvedLemma),
            ("id2", candidateLemma));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        IReadOnlyList<LexicalRow> rows = await reader.ReadLexicalsAsync(ct);

        LexicalRow gloss = Assert.Single(rows, r => r.Kind == LexicalKind.LemmaGloss && r.Id == approvedLemma.ToString(CultureInfo.InvariantCulture));
        Assert.Equal("onayli", gloss.Status);
        LexicalRow fix = Assert.Single(rows, r => r.Kind == LexicalKind.QuranWordFix);
        Assert.Equal("aday", fix.Status);
        Assert.Equal(
            [($"{slug}|{approvedLemma}", true), ($"{slug}|{candidateLemma}", false)],
            rows.Where(r => r.Kind == LexicalKind.TrForm && r.Id.StartsWith(slug, StringComparison.Ordinal))
                .OrderBy(r => r.Id, StringComparer.Ordinal)
                .Select(r => (r.Id, r.LinkedLemmaApproved)));
        Assert.All(rows.Where(r => r.Kind == LexicalKind.TrForm), r => Assert.Null(r.Status));
    }

    [Fact]
    public async Task It_reads_the_latest_published_release_of_the_requested_flavor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        const string insert =
            """
            INSERT INTO icerik.release (surum, derleme, durum, data_version, olusturan, ozetler, manifest, yayinlandi_at)
            VALUES (@v, @d::icerik.derleme_turu, @st::icerik.surum_durumu, 'test', 'test-editor', @oz::jsonb, @mf::jsonb, @at)
            """;
        DateTime day1 = new(2026, 11, 1, 10, 0, 0, DateTimeKind.Utc);
        DateTime day2 = new(2026, 11, 2, 10, 0, 0, DateTimeKind.Utc);
        await Db.ExecuteAsync(insert, ct, ("v", "2099.1.0"), ("d", "internal"), ("st", "yayinlandi"), ("oz", "{\"paketler\": {\"core\": \"eski\"}}"), ("mf", "{\"release\": \"2099.1.0\"}"), ("at", day1));
        await Db.ExecuteAsync(insert, ct, ("v", "2099.1.1"), ("d", "internal"), ("st", "yayinlandi"), ("oz", "{\"paketler\": {\"core\": \"yeni\"}}"), ("mf", "{\"release\": \"2099.1.1\"}"), ("at", day2));
        await Db.ExecuteAsync(insert, ct, ("v", "2099.1.2"), ("d", "internal"), ("st", "basarisiz"), ("oz", "{}"), ("mf", null), ("at", null));

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        PreviousReleaseRow? previous = await reader.ReadPreviousReleaseAsync(BuildFlavor.Internal, ct);
        PreviousReleaseRow? none = await reader.ReadPreviousReleaseAsync(BuildFlavor.Public, ct);

        Assert.NotNull(previous);
        Assert.Equal("2099.1.1", previous.Surum);
        Assert.Equal("yeni", JsonDocument.Parse(previous.Ozetler).RootElement.GetProperty("paketler").GetProperty("core").GetString());
        Assert.Equal("2099.1.1", JsonDocument.Parse(previous.Manifest!).RootElement.GetProperty("release").GetString());
        Assert.Equal(day2, previous.YayinlandiAt);
        Assert.Null(none);
    }

    [Fact]
    public async Task The_snapshot_does_not_see_rows_committed_after_its_first_read()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string before = Unique("test-once-");
        string after = Unique("test-sonra-");
        await InsertSourceAsync(before, ct: ct);

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        IReadOnlyList<SourceRow> first = await reader.ReadSourcesAsync(ct);
        await InsertSourceAsync(after, ct: ct);
        IReadOnlyList<SourceRow> second = await reader.ReadSourcesAsync(ct);
        await using EditorialSnapshotReader fresh = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        IReadOnlyList<SourceRow> third = await fresh.ReadSourcesAsync(ct);

        Assert.Contains(first, s => s.Slug == before);
        Assert.DoesNotContain(first, s => s.Slug == after);
        Assert.DoesNotContain(second, s => s.Slug == after);
        Assert.Contains(third, s => s.Slug == after);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LoadAsync_collects_every_table_under_either_culture(bool turkish)
    {
        async Task Body()
        {
            CancellationToken ct = TestContext.Current.CancellationToken;
            string slug = Unique("test-yuk-");
            await InsertSourceAsync(slug, ct: ct);
            await InsertUnitAsync($"k:{slug}:p1", slug, "kitap", "onayli", ct: ct);

            await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
            EditorialSnapshot snapshot = await reader.LoadAsync(BuildFlavor.Dev, ct);

            Assert.Contains(snapshot.Sources, s => s.Slug == slug);
            UnitRow unit = Assert.Single(snapshot.Units, u => u.SourceId == slug);
            Assert.Equal("onayli", unit.MetinDurumu);
            Assert.NotNull(snapshot.OpenReviewXrefIds);
            Assert.NotNull(snapshot.Lexicals);
        }

        if (turkish)
        {
            await AsyncCultureScope.TurkishAsync(Body);
        }
        else
        {
            await Body();
        }
    }

    [Fact]
    public async Task Gate_input_builds_from_a_loaded_database_snapshot()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = Unique("test-kapi-");
        await InsertSourceAsync(slug, ct: ct);
        await InsertUnitAsync($"k:{slug}:p1", slug, "kitap", "onayli", ct: ct);

        await using EditorialSnapshotReader reader = await EditorialSnapshotReader.OpenAsync(Db.ConnectionString, ct);
        EditorialSnapshot snapshot = await reader.LoadAsync(BuildFlavor.Dev, ct);
        GateInput input = GateInputBuilder.Build(snapshot, Mutalaa.Infrastructure.Packs.PackCatalog.Default, "pipeline/sources", fileExists: _ => true);

        GateUnit unit = Assert.Single(input.Units, u => u.SourceSlug == slug);
        Assert.Equal(Mutalaa.Domain.Content.TextStatus.Onayli, unit.TextStatus);
        Assert.Contains(input.Sources, s => s.Slug == slug && s.AtifMetni == "Sentetik test verisi (Mutalaa).");
    }

    [Fact]
    public void The_reader_source_never_selects_the_tsv_columns()
    {
        string source = RepoFiles.ReadUtf8(RepoFiles.PathOf("server/Mutalaa.Infrastructure/Releases/EditorialSnapshotReader.cs"));
        string code = string.Join('\n', source.Split('\n').Where(line => !line.TrimStart().StartsWith("///", StringComparison.Ordinal)));

        Assert.DoesNotMatch(TsvColumn(), code);
        Assert.DoesNotContain("SELECT *", code, StringComparison.Ordinal);
        Assert.DoesNotContain("u.*", code, StringComparison.Ordinal);
    }
}
