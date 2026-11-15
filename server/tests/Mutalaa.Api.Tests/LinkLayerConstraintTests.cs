using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>
/// A18.2 (AddLinkLayer, K-51): lemma.onay_yolu ve kanit kisitlari, lemma_tr_text_clean_key, tr_root_index.unit_hash biçimi,
/// tr_form.data_version, xref_gate kisitlari ve uzmanda enum degeri (Docker'li). Her test kendi islemini acar ve sonunda geri alir.
/// </summary>
public class LinkLayerConstraintTests(EditorialDatabase<LinkLayerConstraintTests> fixture, PostgresFixture postgres) : IClassFixture<EditorialDatabase<LinkLayerConstraintTests>>
{
    private const string CheckViolation = "23514";
    private const string Unique = "23505";
    private const string NotNull = "23502";
    private const string Sha64 = "repeat('a', 64)";

    private const string NoDefaultSql =
        "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'icerik' AND column_default IS NOT NULL "
        + "AND ((table_name = 'tr_root_index' AND column_name = 'unit_hash') OR (table_name = 'tr_form' AND column_name = 'data_version'))";

    private TestDatabase Db => fixture.Database;

    private static async Task<string> AddSourceAsync(RollbackSession session, CancellationToken ct)
    {
        string slug = TestData.UniqueSlug();
        await session.ExecuteAsync(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni) VALUES (@s, 'sozluk', 'Deneme kaynagi', '1', 'Deneme atfi')",
            ct,
            ("s", slug));
        return slug;
    }

    private static Task<int> AddLemmaAsync(
        RollbackSession session,
        CancellationToken ct,
        int id,
        string lang,
        string textClean,
        string slug,
        string status = "aday",
        string? onayYolu = null,
        string? kanit = null) =>
        session.ExecuteAsync(
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version, status, onay_yolu, kanit) "
            + "VALUES (@id, @lang, 'lemma', @tc, @s, 'test', @st::icerik.xref_status, @oy, @k::jsonb)",
            ct,
            ("id", id),
            ("lang", lang),
            ("tc", textClean),
            ("s", slug),
            ("st", status),
            ("oy", (object?)onayYolu ?? DBNull.Value),
            ("k", (object?)kanit ?? DBNull.Value));

    private static async Task AssertViolationAsync(Func<Task> action, string sqlState, string constraint)
    {
        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(action);
        Assert.Equal(sqlState, exception.SqlState);
        Assert.Equal(constraint, exception.ConstraintName);
    }

    [Fact]
    public async Task An_automatic_approval_without_evidence_is_rejected()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await AssertViolationAsync(
            () => AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "onayli", "otomatik"),
            CheckViolation,
            "lemma_otomatik_kanit_check");
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("\"metin\"")]
    [InlineData("42")]
    [InlineData("null")]
    public async Task An_automatic_approval_needs_an_evidence_object_not_another_json_type(string kanit)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await AssertViolationAsync(
            () => AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "onayli", "otomatik", kanit),
            CheckViolation,
            "lemma_otomatik_kanit_check");
    }

    [Fact]
    public async Task An_automatic_approval_with_an_evidence_object_is_accepted()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "onayli", "otomatik", "{\"politika\":\"deneme\"}"));
    }

    [Fact]
    public async Task An_approved_turkish_lemma_needs_an_approval_path()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await AssertViolationAsync(
            () => AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "onayli"),
            CheckViolation,
            "lemma_tr_onayli_onay_yolu_check");
    }

    [Fact]
    public async Task An_approved_turkish_lemma_with_the_editor_path_needs_no_evidence()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "onayli", "editor"));
    }

    [Fact]
    public async Task Candidate_turkish_lemmas_and_approved_arabic_lemmas_need_no_approval_path()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "aday"));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 2, "tr", "kalem", slug, "red"));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 3, "ar", "kitap", slug, "onayli"));
    }

    [Fact]
    public async Task The_approval_path_accepts_only_editor_or_automatic()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await AssertViolationAsync(
            () => AddLemmaAsync(session, ct, 1, "tr", "kitap", slug, "aday", "hat"),
            CheckViolation,
            "lemma_onay_yolu_check");
    }

    [Fact]
    public async Task Turkish_lemma_text_clean_is_unique_but_arabic_lemmas_are_not_restricted()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 2, "ar", "kitap", slug));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 3, "ar", "kitap", slug));

        await AssertViolationAsync(() => AddLemmaAsync(session, ct, 4, "tr", "kitap", slug), Unique, "lemma_tr_text_clean_key");
    }

    [Theory]
    [InlineData("'0123456789abcdef'", true)]
    [InlineData("'0123456789ABCDEF'", false)]
    [InlineData("'0123456789abcde'", false)]
    [InlineData("'0123456789abcdeg'", false)]
    public async Task The_root_index_unit_hash_is_sixteen_lowercase_hex_digits(string hash, bool valid)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        await session.ExecuteAsync("INSERT INTO icerik.root (id, letters, source_id, data_version) VALUES (1, 'kok-1', @s, 'test')", ct, ("s", slug));
        await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug);
        string insert = "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id, unit_hash, data_version) "
            + $"VALUES ('rn:sozler:soz-10:p1', 0, 5, 1, 1, {hash}, 'test')";

        if (valid)
        {
            Assert.Equal(1, await session.ExecuteAsync(insert, ct));
            return;
        }

        await AssertViolationAsync(() => session.ExecuteAsync(insert, ct), CheckViolation, "tr_root_index_unit_hash_check");
    }

    private async Task SeedRootAndLemmaAsync(RollbackSession session, CancellationToken ct)
    {
        string slug = await AddSourceAsync(session, ct);
        await session.ExecuteAsync("INSERT INTO icerik.root (id, letters, source_id, data_version) VALUES (1, 'kok-1', @s, 'test')", ct, ("s", slug));
        await AddLemmaAsync(session, ct, 1, "tr", "kitap", slug);
    }

    [Fact]
    public async Task The_root_index_unit_hash_is_required()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        await SeedRootAndLemmaAsync(session, ct);

        PostgresException hash = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(
            "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id, data_version) VALUES ('rn:sozler:soz-10:p1', 0, 5, 1, 1, 'test')",
            ct));

        Assert.Equal(NotNull, hash.SqlState);
        Assert.Equal("unit_hash", hash.ColumnName);
    }

    [Fact]
    public async Task The_form_data_version_is_required()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        await SeedRootAndLemmaAsync(session, ct);

        PostgresException form = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(
            "INSERT INTO icerik.tr_form (key_wide, key_narrow, tr_lemma_id, freq) VALUES ('a', 'a', 1, 1)",
            ct));

        Assert.Equal(NotNull, form.SqlState);
        Assert.Equal("data_version", form.ColumnName);
    }

    [Fact]
    public async Task The_root_index_unit_hash_and_form_data_version_have_no_default()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        Assert.Equal(0L, await Db.ScalarAsync<long>(NoDefaultSql, ct));
    }

    private static string GateInsert(
        string tur = "'kok'",
        string sinif = "'silver'",
        string sonuc = "'gecti'",
        string kaynaklar = "ARRAY['kaikki']",
        string sha = Sha64,
        string altTur = "'xref'") =>
        "INSERT INTO icerik.xref_gate (tur, alt_tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256, data_version) "
        + $"VALUES ({tur}, {altTur}, {sinif}, '1', {sonuc}, {kaynaklar}, {sha}, 'test')";

    [Fact]
    public async Task A_gate_row_is_keyed_by_type_subtype_and_set_class_and_stamps_the_measurement_time()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        Assert.Equal(1, await session.ExecuteAsync(GateInsert(), ct));
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(sinif: "'altin'"), ct));
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(sinif: "'sentetik'", sonuc: "'kaldi'", kaynaklar: "ARRAY[]::text[]"), ct));
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(tur: "'lemma'", altTur: "''"), ct));

        // Ayni (tur, set sinifi) farkli alt turle ayri satirdir.
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(altTur: "'tr_lemma'"), ct));
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(tur: "'benzer_ayet'", altTur: "'sozluksel'"), ct));
        Assert.Equal(1, await session.ExecuteAsync(GateInsert(tur: "'benzer_ayet'", altTur: "'alim'"), ct));
        Assert.Equal(4L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.xref_gate WHERE tur = 'kok'", ct));
        Assert.Equal(7L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.xref_gate WHERE olculdu_at = now()", ct));

        await AssertViolationAsync(() => session.ExecuteAsync(GateInsert(), ct), Unique, "xref_gate_pkey");

        // Ihlal islemi iptal eder: ayni alt turun ikinci satiri ayri islemde denenir.
        await using RollbackSession second = await Db.OpenRollbackSessionAsync(ct);
        Assert.Equal(1, await second.ExecuteAsync(GateInsert(tur: "'benzer_ayet'", altTur: "'alim'"), ct));
        await AssertViolationAsync(() => second.ExecuteAsync(GateInsert(tur: "'benzer_ayet'", altTur: "'alim'"), ct), Unique, "xref_gate_pkey");
    }

    [Theory]
    [InlineData("'benzer_ayet'", "'sozluksel'")]
    [InlineData("'benzer_ayet'", "'alim'")]
    [InlineData("'kok'", "'tr_lemma'")]
    [InlineData("'kok'", "'xref'")]
    [InlineData("'lemma'", "''")]
    [InlineData("'atif'", "''")]
    [InlineData("'iktibas'", "''")]
    [InlineData("'anlamsal'", "''")]
    public async Task Gate_accepts_every_documented_type_and_subtype_pair(string tur, string altTur)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        Assert.Equal(1, await session.ExecuteAsync(GateInsert(tur: tur, altTur: altTur), ct));
    }

    [Theory]
    [InlineData("'kok'", "''")]
    [InlineData("'kok'", "'alim'")]
    [InlineData("'kok'", "'sozluksel'")]
    [InlineData("'benzer_ayet'", "''")]
    [InlineData("'benzer_ayet'", "'tr_lemma'")]
    [InlineData("'benzer_ayet'", "'xref'")]
    [InlineData("'lemma'", "'xref'")]
    [InlineData("'lemma'", "'tr_lemma'")]
    [InlineData("'atif'", "'sozluksel'")]
    [InlineData("'iktibas'", "'alim'")]
    [InlineData("'kok'", "'bilinmeyen'")]
    [InlineData("'kok'", "'Xref'")]
    public async Task Gate_subtype_check_rejects_inconsistent_or_unknown_pairs(string tur, string altTur)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        await AssertViolationAsync(() => session.ExecuteAsync(GateInsert(tur: tur, altTur: altTur), ct), CheckViolation, "xref_gate_alt_tur_check");
    }

    [Fact]
    public async Task Gate_subtype_is_required_and_has_no_default()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException missing = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(
            "INSERT INTO icerik.xref_gate (tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256, data_version) "
            + $"VALUES ('lemma', 'silver', '1', 'gecti', ARRAY['kaikki'], {Sha64}, 'test')",
            ct));

        Assert.Equal(NotNull, missing.SqlState);
        Assert.Equal("alt_tur", missing.ColumnName);
        Assert.Equal(
            0L,
            await Db.ScalarAsync<long>(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'xref_gate' AND column_name = 'alt_tur' AND column_default IS NOT NULL",
                ct));
    }

    [Theory]
    [InlineData("sinif", "'bronz'", "xref_gate_set_sinifi_check")]
    [InlineData("sinif", "'Silver'", "xref_gate_set_sinifi_check")]
    [InlineData("sonuc", "'basarili'", "xref_gate_sonuc_check")]
    [InlineData("sha", "repeat('A', 64)", "xref_gate_rapor_sha256_check")]
    [InlineData("sha", "repeat('a', 63)", "xref_gate_rapor_sha256_check")]
    [InlineData("sha", "repeat('g', 64)", "xref_gate_rapor_sha256_check")]
    public async Task Gate_checks_reject_invalid_values(string field, string value, string constraint)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string sql = field switch
        {
            "sinif" => GateInsert(sinif: value),
            "sonuc" => GateInsert(sonuc: value),
            _ => GateInsert(sha: value),
        };

        await AssertViolationAsync(() => session.ExecuteAsync(sql, ct), CheckViolation, constraint);
    }

    [Fact]
    public async Task Gate_sources_are_required()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException sources = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(GateInsert(kaynaklar: "NULL"), ct));

        Assert.Equal(NotNull, sources.SqlState);
        Assert.Equal("set_kaynaklari", sources.ColumnName);
    }

    [Fact]
    public async Task Gate_type_must_be_an_xref_type_label()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException type = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(GateInsert(tur: "'yok'"), ct));

        Assert.Equal("22P02", type.SqlState);
    }

    [Fact]
    public async Task The_review_status_enum_gains_uzmanda_after_the_existing_labels()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        Assert.Equal(
            ["acik", "onaylandi", "reddedildi", "geri_alindi", "uzmanda"],
            await Db.ColumnAsync("SELECT enumlabel::text FROM pg_enum WHERE enumtypid = 'icerik.inceleme_durumu'::regtype ORDER BY enumsortorder", ct));
    }

    [Fact]
    public async Task Upgrading_a_database_that_already_holds_turkish_rows_keeps_them_and_leaves_no_default()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("linklayerup", ct);
        await using (DbSession before = fresh.OpenSession())
        {
            await before.Context.GetService<IMigrator>().MigrateAsync("20261112003055_AddLemmaWave", ct);
        }

        await fresh.ExecuteAsync("INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni) VALUES ('test-eski', 'sozluk', 'Deneme', '1', 'Deneme atfi')", ct);
        await fresh.ExecuteAsync("INSERT INTO icerik.root (id, letters, source_id, data_version) VALUES (1, 'kok-1', 'test-eski', 'test')", ct);
        await fresh.ExecuteAsync("INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version) VALUES (1, 'tr', 'a', 'a', 'test-eski', 'test')", ct);
        await fresh.ExecuteAsync("INSERT INTO icerik.tr_form (key_wide, key_narrow, tr_lemma_id, freq) VALUES ('a', 'a', 1, 1)", ct);
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id, data_version) VALUES ('rn:sozler:soz-10:p1', 0, 5, 1, 1, 'test')",
            ct);

        await fresh.MigrateAsync(ct);

        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.tr_form WHERE data_version = 'oncesi'", ct));
        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.tr_root_index WHERE unit_hash = '0000000000000000'", ct));
        Assert.Equal(0L, await fresh.ScalarAsync<long>(NoDefaultSql, ct));
        await using DbSession after = fresh.OpenSession();
        Assert.False(after.Context.Database.HasPendingModelChanges());
    }

    private const string PreviousMigration = "20261112211605_AddLinkLayer";

    private const string GateKeyColumnsSql =
        "SELECT a.attname::text FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey) "
        + "WHERE c.conname = 'xref_gate_pkey' AND c.conrelid = 'icerik.xref_gate'::regclass ORDER BY array_position(c.conkey, a.attnum)";

    private static Task InsertLegacyGateRowAsync(TestDatabase db, string tur, string sinif, string sonuc, CancellationToken ct) =>
        db.ExecuteAsync(
            "INSERT INTO icerik.xref_gate (tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256, data_version) "
            + $"VALUES ('{tur}', '{sinif}', '1', '{sonuc}', ARRAY['kaynak'], {Sha64}, 'test')",
            ct);

    [Fact]
    public async Task AddGateSubtype_gives_old_rows_an_empty_subtype_drops_the_ones_the_check_cannot_hold_and_migrates_down_again()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("gatesubtype", ct);
        await using (DbSession before = fresh.OpenSession())
        {
            await before.Context.GetService<IMigrator>().MigrateAsync(PreviousMigration, ct);
        }

        Assert.Equal(["tur", "set_sinifi"], await fresh.ColumnAsync(GateKeyColumnsSql, ct));
        await InsertLegacyGateRowAsync(fresh, "atif", "sentetik", "kaldi", ct);
        await InsertLegacyGateRowAsync(fresh, "benzer_ayet", "altin", "kaldi", ct);
        await InsertLegacyGateRowAsync(fresh, "iktibas", "sentetik", "gecti", ct);
        await InsertLegacyGateRowAsync(fresh, "kok", "silver", "kaldi", ct);
        await InsertLegacyGateRowAsync(fresh, "lemma", "altin", "gecti", ct);

        // Yukari: bos alt tur kok ve benzer_ayet icin gecersiz; o satirlar silinir (kapi yeniden olculene kadar kapali), digerleri bos alt tur alir.
        await fresh.MigrateAsync(ct);

        Assert.Equal(["tur", "alt_tur", "set_sinifi"], await fresh.ColumnAsync(GateKeyColumnsSql, ct));
        Assert.Equal(
            ["atif|", "iktibas|", "lemma|"],
            await fresh.ColumnAsync("SELECT tur::text || '|' || alt_tur FROM icerik.xref_gate ORDER BY 1", ct));
        Assert.Equal(
            0L,
            await fresh.ScalarAsync<long>(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'xref_gate' AND column_name = 'alt_tur' AND column_default IS NOT NULL",
                ct));
        Assert.Equal(
            ["xref_gate_alt_tur_check"],
            await fresh.ColumnAsync("SELECT conname::text FROM pg_constraint WHERE conrelid = 'icerik.xref_gate'::regclass AND conname = 'xref_gate_alt_tur_check'", ct));
        await using (DbSession after = fresh.OpenSession())
        {
            Assert.False(after.Context.Database.HasPendingModelChanges());
        }

        // Yeni satirlar yazilir; ayni (tur, set sinifi) icin iki alt tur yan yana durur.
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.xref_gate (tur, alt_tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256, data_version) VALUES "
            + $"('kok', 'tr_lemma', 'silver', '2', 'kaldi', ARRAY['k'], {Sha64}, 'test'), ('kok', 'xref', 'silver', '2', 'gecti', ARRAY['k'], {Sha64}, 'test')",
            ct);

        // Asagi: alt turlu satirlar eski semada tutulamaz ve silinir; birincil anahtar (tur, set_sinifi) olur, sutun kalkar.
        await using (DbSession down = fresh.OpenSession())
        {
            await down.Context.GetService<IMigrator>().MigrateAsync(PreviousMigration, ct);
        }

        Assert.Equal(["tur", "set_sinifi"], await fresh.ColumnAsync(GateKeyColumnsSql, ct));
        Assert.Equal(
            0L,
            await fresh.ScalarAsync<long>("SELECT count(*) FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'xref_gate' AND column_name = 'alt_tur'", ct));
        Assert.Equal(
            0L,
            await fresh.ScalarAsync<long>("SELECT count(*) FROM pg_constraint WHERE conrelid = 'icerik.xref_gate'::regclass AND conname = 'xref_gate_alt_tur_check'", ct));
        Assert.Equal(
            ["atif", "iktibas", "lemma"],
            await fresh.ColumnAsync("SELECT tur::text FROM icerik.xref_gate ORDER BY 1", ct));

        // Yeniden yukari: temiz gecis.
        await fresh.MigrateAsync(ct);
        Assert.Equal(["tur", "alt_tur", "set_sinifi"], await fresh.ColumnAsync(GateKeyColumnsSql, ct));
    }
}
