using System.Runtime.CompilerServices;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Npgsql;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// Editoryal veritabani anlik goruntu okuyucusu (Backend API 10.1): ham Npgsql, tek <c>BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY</c> islemi.
/// Enum sutunlari ::text ile (tur eslemesi ve Npgsql tur onbellegi gerekmez), int4range lower()/upper() ile okunur, siralama COLLATE "C"dir;
/// tsv_tr ve tsv_ar sutunlari HICBIR zaman secilmez. Okuyucu bir baglanti uzerinde calisir: akis (IAsyncEnumerable) yontemleri tamamen
/// tuketilmeden baska bir yontem cagrilmaz (Npgsql ayni baglantida es zamanli komuta izin vermez). <see cref="LoadAsync"/> hepsini sirayla okur.
/// Atilinca islem geri alinir (salt okunur; yazilan sey yoktur) ve baglanti kapanir.
/// </summary>
public sealed class EditorialSnapshotReader : IAsyncDisposable
{
    private const string Schema = "icerik";

    private readonly NpgsqlConnection _connection;
    private bool _transactionOpen;

    private EditorialSnapshotReader(NpgsqlConnection connection)
    {
        _connection = connection;
    }

    /// <summary>Baglantiyi acar ve REPEATABLE READ READ ONLY islemini baslatir.</summary>
    public static async Task<EditorialSnapshotReader> OpenAsync(string connectionString, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(connectionString);

        NpgsqlConnection connection = new(connectionString);
        try
        {
            await connection.OpenAsync(cancellationToken);
            await using NpgsqlCommand begin = new("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY", connection);
            await begin.ExecuteNonQueryAsync(cancellationToken);
        }
        catch
        {
            await connection.DisposeAsync();
            throw;
        }

        return new EditorialSnapshotReader(connection) { _transactionOpen = true };
    }

    /// <summary>Butun tablolari sirayla okur ve <paramref name="flavor"/> icin onceki yayini ekler.</summary>
    public async Task<EditorialSnapshot> LoadAsync(BuildFlavor flavor, CancellationToken cancellationToken)
    {
        IReadOnlyList<SourceRow> sources = await ReadSourcesAsync(cancellationToken);
        List<UnitRow> units = await ToListAsync(ReadUnitsAsync(cancellationToken), cancellationToken);
        List<QuranWordRow> words = await ToListAsync(ReadQuranWordsAsync(cancellationToken), cancellationToken);
        IReadOnlyList<QuranMarkerRow> markers = await ReadQuranMarkersAsync(cancellationToken);
        IReadOnlyList<PageMapRow> pages = await ReadPageMapsAsync(cancellationToken);
        List<XrefRow> xrefs = await ToListAsync(ReadXrefsAsync(cancellationToken), cancellationToken);
        IReadOnlySet<Guid> reviews = await ReadOpenReviewXrefIdsAsync(cancellationToken);
        IReadOnlyList<LexicalRow> lexicals = await ReadLexicalsAsync(cancellationToken);
        IReadOnlyList<RootRow> roots = await ReadRootsAsync(cancellationToken);
        IReadOnlyList<LemmaRow> lemmas = await ReadLemmasAsync(cancellationToken);
        IReadOnlyList<LemmaGlossRow> glosses = await ReadLemmaGlossesAsync(cancellationToken);
        IReadOnlyList<QuranWordFixRow> fixes = await ReadWordFixesAsync(cancellationToken);
        PreviousReleaseRow? previous = await ReadPreviousReleaseAsync(flavor, cancellationToken);

        return new EditorialSnapshot
        {
            Sources = sources,
            Units = units,
            QuranWords = words,
            QuranMarkers = markers,
            PageMaps = pages,
            Xrefs = xrefs,
            OpenReviewXrefIds = reviews,
            Lexicals = lexicals,
            Roots = roots,
            Lemmas = lemmas,
            LemmaGlosses = glosses,
            WordFixes = fixes,
            PreviousRelease = previous,
        };
    }

    /// <summary>Islem kipi (SHOW transaction_isolation, transaction_read_only): beklenen "repeatable read" ve "on". Tanilama ve test icindir.</summary>
    public async Task<(string Isolation, string ReadOnly)> ReadTransactionModeAsync(CancellationToken cancellationToken)
    {
        await using NpgsqlCommand isolation = new("SHOW transaction_isolation", _connection);
        string level = (string)(await isolation.ExecuteScalarAsync(cancellationToken))!;
        await using NpgsqlCommand readOnly = new("SHOW transaction_read_only", _connection);
        string mode = (string)(await readOnly.ExecuteScalarAsync(cancellationToken))!;
        return (level, mode);
    }

    public async Task<IReadOnlyList<SourceRow>> ReadSourcesAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT slug, tur::text, baslik, yazar, surum, provider, kaynak_url, alinma_tarihi, dosya_sha256,
                   baski_bilgisi::text, atif_metni, atif_url, notice_text, notlar
            FROM {Schema}.source
            ORDER BY slug COLLATE "C"
            """;

        List<SourceRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new SourceRow(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                Str(reader, 3),
                reader.GetString(4),
                Str(reader, 5),
                Str(reader, 6),
                reader.IsDBNull(7) ? null : reader.GetFieldValue<DateOnly>(7),
                Str(reader, 8),
                Str(reader, 9),
                reader.GetString(10),
                Str(reader, 11),
                Str(reader, 12),
                Str(reader, 13)));
        }

        return rows;
    }

    /// <summary>Birimler capa bayt sirasiyla akar.</summary>
    public async IAsyncEnumerable<UnitRow> ReadUnitsAsync([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT u.anchor, u.kind::text, u.role, u.source_id, u.parent_path, u.ord,
                   lower(u.ayah_range), upper(u.ayah_range),
                   u.metin, u.marks::text,
                   (SELECT jsonb_agg(jsonb_build_array(lower(r.s), upper(r.s)) ORDER BY r.n)::text
                      FROM unnest(u.sentences) WITH ORDINALITY AS r(s, n)),
                   u.attrs::text, u.content_hash::text, u.metin_durumu::text, u.status::text, u.successors::text,
                   u.tr_wide, u.tr_stem, u.ar_norm,
                   EXISTS (SELECT 1 FROM {Schema}.review rv
                            WHERE rv.hedef_tablo = 'unit' AND rv.hedef_anahtar = u.anchor AND rv.yz_modeli IS NOT NULL)
            FROM {Schema}.unit u
            ORDER BY u.anchor COLLATE "C"
            """;

        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            yield return new UnitRow(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetString(3),
                Str(reader, 4),
                reader.GetInt64(5),
                Int(reader, 6),
                Int(reader, 7),
                reader.GetString(8),
                reader.GetString(9),
                Str(reader, 10),
                reader.GetString(11),
                reader.GetString(12),
                reader.GetString(13),
                reader.GetString(14),
                Str(reader, 15),
                Str(reader, 16),
                Str(reader, 17),
                Str(reader, 18),
                reader.GetBoolean(19));
        }
    }

    /// <summary>
    /// Kelimeler capa bayt sirasiyla akar. QAC sutunlari (root_id, lemma_id, pos, features, morph_source) yalniz morph_source
    /// <see cref="PackCatalog.LexiconSourceSlugs"/> icindeyse okunur; baska satirda bostur (K-50 madde 3).
    /// </summary>
    public async IAsyncEnumerable<QuranWordRow> ReadQuranWordsAsync([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT anchor, surah::int, ayah::int, word::int, ayah_index::int, text_uthmani, norm, char_start, char_end, source_id,
                   CASE WHEN morph_source = ANY(@lex) THEN root_id END,
                   CASE WHEN morph_source = ANY(@lex) THEN lemma_id END,
                   CASE WHEN morph_source = ANY(@lex) THEN pos END,
                   CASE WHEN morph_source = ANY(@lex) THEN features::text END,
                   CASE WHEN morph_source = ANY(@lex) THEN morph_source END
            FROM {Schema}.quran_word
            ORDER BY anchor COLLATE "C"
            """;

        await using NpgsqlCommand command = new(sql, _connection);
        command.Parameters.AddWithValue("lex", PackCatalog.LexiconSourceSlugs.ToArray());
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            yield return new QuranWordRow(
                reader.GetString(0),
                reader.GetInt32(1),
                reader.GetInt32(2),
                reader.GetInt32(3),
                reader.GetInt32(4),
                reader.GetString(5),
                reader.GetString(6),
                reader.GetInt32(7),
                reader.GetInt32(8),
                reader.GetString(9),
                Int(reader, 10),
                Int(reader, 11),
                Str(reader, 12),
                Str(reader, 13),
                Str(reader, 14));
        }
    }

    /// <summary>QAC kokleri (source_id sozluk kaynagi; id sirali). Tablo bossa satir uretmez.</summary>
    public async Task<IReadOnlyList<RootRow>> ReadRootsAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT id, letters, occurrences, ayah_count, idf_q, kok_anlami, source_id
            FROM {Schema}.root
            WHERE source_id = ANY(@lex)
            ORDER BY id
            """;

        List<RootRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        command.Parameters.AddWithValue("lex", PackCatalog.LexiconSourceSlugs.ToArray());
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new RootRow(
                reader.GetInt32(0),
                reader.GetString(1),
                reader.GetInt32(2),
                reader.GetInt32(3),
                reader.IsDBNull(4) ? null : reader.GetFloat(4),
                Str(reader, 5),
                reader.GetString(6)));
        }

        return rows;
    }

    /// <summary>Arapca lemmalar (lang = 'ar', source_id sozluk kaynagi; id sirali). Tablo bossa satir uretmez.</summary>
    public async Task<IReadOnlyList<LemmaRow>> ReadLemmasAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT id, text, text_clean, root_id, occurrences, ar_lemma_id, etymological_only, status::text, source_id
            FROM {Schema}.lemma
            WHERE lang = 'ar' AND source_id = ANY(@lex)
            ORDER BY id
            """;

        List<LemmaRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        command.Parameters.AddWithValue("lex", PackCatalog.LexiconSourceSlugs.ToArray());
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new LemmaRow(
                reader.GetInt32(0),
                reader.GetString(1),
                reader.GetString(2),
                Int(reader, 3),
                reader.GetInt32(4),
                Int(reader, 5),
                reader.GetBoolean(6),
                reader.GetString(7),
                reader.GetString(8)));
        }

        return rows;
    }

    /// <summary>Arapca sozluk lemmalarina bagli anlamlar (butun durumlar; lemma_id sirali). Tablo bossa satir uretmez.</summary>
    public async Task<IReadOnlyList<LemmaGlossRow>> ReadLemmaGlossesAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT g.lemma_id, g.anlam_kisa, g.kuran_anlamlari::text, g.turkce_es_kelime, g.yalnizca_etimolojik, g.status::text, g.origin, g.version
            FROM {Schema}.lemma_gloss g
            JOIN {Schema}.lemma l ON l.id = g.lemma_id
            WHERE l.lang = 'ar' AND l.source_id = ANY(@lex)
            ORDER BY g.lemma_id
            """;

        List<LemmaGlossRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        command.Parameters.AddWithValue("lex", PackCatalog.LexiconSourceSlugs.ToArray());
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new LemmaGlossRow(
                reader.GetInt32(0),
                reader.GetString(1),
                reader.GetString(2),
                Str(reader, 3),
                reader.GetBoolean(4),
                reader.GetString(5),
                reader.GetString(6),
                reader.GetString(7)));
        }

        return rows;
    }

    /// <summary>quran_word_fix satirlari (butun durumlar; id sirali). Tablo bossa satir uretmez.</summary>
    public async Task<IReadOnlyList<QuranWordFixRow>> ReadWordFixesAsync(CancellationToken cancellationToken)
    {
        const string sql = $"SELECT id, anchor, field, new_value, status::text FROM {Schema}.quran_word_fix ORDER BY id";

        List<QuranWordFixRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new QuranWordFixRow(reader.GetGuid(0), reader.GetString(1), reader.GetString(2), reader.GetString(3), reader.GetString(4)));
        }

        return rows;
    }

    public async Task<IReadOnlyList<QuranMarkerRow>> ReadQuranMarkersAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT kind, no::int, anchor, secde_turu, source_id
            FROM {Schema}.quran_marker
            ORDER BY kind COLLATE "C", no
            """;

        List<QuranMarkerRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new QuranMarkerRow(reader.GetString(0), reader.GetInt32(1), reader.GetString(2), Str(reader, 3), reader.GetString(4)));
        }

        return rows;
    }

    public async Task<IReadOnlyList<PageMapRow>> ReadPageMapsAsync(CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT source_id, volume::int, page, line::int, start_anchor, start_offset, end_anchor, end_offset
            FROM {Schema}.page_map
            ORDER BY source_id COLLATE "C", volume NULLS FIRST, page, line NULLS FIRST, id
            """;

        List<PageMapRow> rows = [];
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new PageMapRow(
                reader.GetString(0),
                Int(reader, 1),
                reader.GetInt32(2),
                Int(reader, 3),
                reader.GetString(4),
                Int(reader, 5),
                reader.GetString(6),
                Int(reader, 7)));
        }

        return rows;
    }

    /// <summary>Baglantilar kimlige gore akar.</summary>
    public async IAsyncEnumerable<XrefRow> ReadXrefsAsync([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT id, src_anchor, lower(src_span), upper(src_span), dst_anchor, lower(dst_span), upper(dst_span),
                   type::text, score, confidence, evidence::text, status::text, data_version, evidence->>'lexicon_status'
            FROM {Schema}.xref
            ORDER BY id
            """;

        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            yield return new XrefRow(
                reader.GetGuid(0),
                reader.GetString(1),
                Int(reader, 2),
                Int(reader, 3),
                reader.GetString(4),
                Int(reader, 5),
                Int(reader, 6),
                reader.GetString(7),
                reader.GetFloat(8),
                reader.GetFloat(9),
                reader.GetString(10),
                reader.GetString(11),
                reader.GetString(12),
                Str(reader, 13));
        }
    }

    /// <summary>Acik (durum = acik) review satiri olan baglantilarin kimlikleri.</summary>
    public async Task<IReadOnlySet<Guid>> ReadOpenReviewXrefIdsAsync(CancellationToken cancellationToken)
    {
        const string sql = $"SELECT DISTINCT xref_id FROM {Schema}.review WHERE durum = 'acik' AND xref_id IS NOT NULL";

        HashSet<Guid> ids = [];
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            ids.Add(reader.GetGuid(0));
        }

        return ids;
    }

    /// <summary>P-09 durum satirlari: quran_word_fix, lemma_gloss, tr_root_index ve tr_form.</summary>
    public async Task<IReadOnlyList<LexicalRow>> ReadLexicalsAsync(CancellationToken cancellationToken)
    {
        List<LexicalRow> rows = [];
        await ReadLexicalAsync(
            $"SELECT id::text, status::text, false FROM {Schema}.quran_word_fix ORDER BY id",
            LexicalKind.QuranWordFix,
            rows,
            cancellationToken);
        await ReadLexicalAsync(
            $"SELECT lemma_id::text, status::text, false FROM {Schema}.lemma_gloss ORDER BY lemma_id",
            LexicalKind.LemmaGloss,
            rows,
            cancellationToken);
        await ReadLexicalAsync(
            $"""
            SELECT r.anchor || '|' || r.span_start::text, NULL::text, COALESCE(l.status::text = 'onayli', false)
            FROM {Schema}.tr_root_index r LEFT JOIN {Schema}.lemma l ON l.id = r.tr_lemma_id
            ORDER BY r.anchor COLLATE "C", r.span_start
            """,
            LexicalKind.TrRootIndex,
            rows,
            cancellationToken);
        await ReadLexicalAsync(
            $"""
            SELECT f.key_narrow || '|' || f.tr_lemma_id::text, NULL::text, COALESCE(l.status::text = 'onayli', false)
            FROM {Schema}.tr_form f LEFT JOIN {Schema}.lemma l ON l.id = f.tr_lemma_id
            ORDER BY f.key_narrow COLLATE "C", f.tr_lemma_id
            """,
            LexicalKind.TrForm,
            rows,
            cancellationToken);
        return rows;
    }

    /// <summary>Derleme turunun en son yayinlandi satiri (yayinlandi_at, sonra id azalan); yoksa null.</summary>
    public async Task<PreviousReleaseRow?> ReadPreviousReleaseAsync(BuildFlavor flavor, CancellationToken cancellationToken)
    {
        const string sql = $"""
            SELECT id, surum, manifest::text, ozetler::text, yayinlandi_at
            FROM {Schema}.release
            WHERE derleme::text = @derleme AND durum::text = 'yayinlandi'
            ORDER BY yayinlandi_at DESC NULLS LAST, id DESC
            LIMIT 1
            """;

        await using NpgsqlCommand command = new(sql, _connection);
        command.Parameters.AddWithValue("derleme", flavor.ToLabel());
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return null;
        }

        return new PreviousReleaseRow(
            reader.GetInt32(0),
            reader.GetString(1),
            Str(reader, 2),
            reader.GetString(3),
            reader.IsDBNull(4) ? null : reader.GetFieldValue<DateTime>(4));
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            if (_transactionOpen)
            {
                _transactionOpen = false;
                await using NpgsqlCommand rollback = new("ROLLBACK", _connection);
                await rollback.ExecuteNonQueryAsync(CancellationToken.None);
            }
        }
        catch (NpgsqlException)
        {
            // Baglanti zaten kopmus olabilir; islem sunucuda kendiliginden biter.
        }
        finally
        {
            await _connection.DisposeAsync();
        }
    }

    private async Task ReadLexicalAsync(string sql, LexicalKind kind, List<LexicalRow> rows, CancellationToken cancellationToken)
    {
        await using NpgsqlCommand command = new(sql, _connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new LexicalRow(kind, reader.GetString(0), Str(reader, 1), reader.GetBoolean(2)));
        }
    }

    private static async Task<List<T>> ToListAsync<T>(IAsyncEnumerable<T> source, CancellationToken cancellationToken)
    {
        List<T> list = [];
        await foreach (T item in source.WithCancellation(cancellationToken))
        {
            list.Add(item);
        }

        return list;
    }

    private static string? Str(NpgsqlDataReader reader, int ordinal) => reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);

    private static int? Int(NpgsqlDataReader reader, int ordinal) => reader.IsDBNull(ordinal) ? null : reader.GetInt32(ordinal);
}
