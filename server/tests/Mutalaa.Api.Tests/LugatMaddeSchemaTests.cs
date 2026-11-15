using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>
/// AddLugatMadde ve AddLugatAnlam (K-51 madde 9, 10 ve 14): tablonun sutunlari, varsayilanlari ve kisitlari (anlam_no, origin 'kaynak',
/// duzey 1..4, tekillik (source_id, basliksoz, anlam_no)), <c>review.hedef_tablo</c> CHECK'ine ek ve mevcut verinin korunmasi (Docker'li, Testcontainers postgres:18.6-trixie). Sentetik basliksozler.
/// </summary>
public class LugatMaddeSchemaTests(EditorialDatabase<LugatMaddeSchemaTests> fixture, PostgresFixture postgres)
    : IClassFixture<EditorialDatabase<LugatMaddeSchemaTests>>
{
    private const string Unique = "23505";
    private const string ForeignKey = "23503";
    private const string Check = "23514";
    private const string PreviousMigration = "20261112003055_AddLemmaWave";
    private const string LugatTableMigration = "20261113061922_AddLugatMadde";
    private const string UniqueName = "lugat_madde_source_id_basliksoz_anlam_no_key";

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

    private static Task<int> AddMaddeAsync(RollbackSession session, CancellationToken ct, string slug, string basliksoz, string extraColumns = "", string extraValues = "") =>
        session.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, content_hash, data_version" + extraColumns + ") "
            + "VALUES (@s, @b, @b, 1, 'hat', repeat('a', 64), 'test'" + extraValues + ")",
            ct,
            ("s", slug),
            ("b", basliksoz));

    [Fact]
    public async Task The_table_has_the_documented_columns_and_defaults()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        IReadOnlyList<string> columns = await Db.ColumnAsync(
            "SELECT column_name || ' ' || data_type || ' ' || is_nullable || ' ' || coalesce(column_default, '') || ' ' || is_identity || ' ' || coalesce(identity_generation, '') "
            + "FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'lugat_madde' ORDER BY ordinal_position",
            ct);

        Assert.Equal(
            [
                "id integer NO  YES ALWAYS",
                "source_id text NO  NO ",
                "basliksoz text NO  NO ",
                "basliksoz_norm text NO  NO ",
                "osmanlica_yazim text YES  NO ",
                "koken_dil text YES  NO ",
                "tanim_tr text YES  NO ",
                "ar_kok_id integer YES  NO ",
                "kaynaklar jsonb NO '{}'::jsonb NO ",
                "duzey smallint NO  NO ",
                "status USER-DEFINED NO 'aday'::icerik.xref_status NO ",
                "origin text NO  NO ",
                "version text NO '1'::text NO ",
                "content_hash character NO  NO ",
                "data_version text NO  NO ",
                "created_at timestamp with time zone NO now() NO ",
                "updated_at timestamp with time zone NO now() NO ",
                "anlam_no smallint NO 1 NO ",
            ],
            columns);
        Assert.Equal("xref_status", await Db.ScalarAsync<string>(
            "SELECT udt_name FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'lugat_madde' AND column_name = 'status'", ct));
        Assert.Equal(64, await Db.ScalarAsync<int>(
            "SELECT character_maximum_length FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'lugat_madde' AND column_name = 'content_hash'", ct));
    }

    [Fact]
    public async Task A_minimal_candidate_row_takes_the_defaults_aday_one_and_an_empty_sources_object()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await AddMaddeAsync(session, ct, slug, "deneme-sozcuk");

        Assert.Equal("aday", await session.ScalarAsync<string>("SELECT status::text FROM icerik.lugat_madde", ct));
        Assert.Equal("1", await session.ScalarAsync<string>("SELECT version FROM icerik.lugat_madde", ct));
        Assert.Equal("{}", await session.ScalarAsync<string>("SELECT kaynaklar::text FROM icerik.lugat_madde", ct));
        Assert.Null(await session.ScalarAsync<string?>("SELECT tanim_tr FROM icerik.lugat_madde", ct));
    }

    [Fact]
    public async Task Source_headword_and_meaning_number_are_unique_together_and_the_same_headword_is_allowed_in_another_source_or_meaning()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string first = await AddSourceAsync(session, ct);
        string second = await AddSourceAsync(session, ct);
        await AddMaddeAsync(session, ct, first, "deneme-sozcuk");

        Assert.Equal(1, await AddMaddeAsync(session, ct, second, "deneme-sozcuk"));
        Assert.Equal(1, await AddMaddeAsync(session, ct, first, "baska-sozcuk"));
        Assert.Equal(1, await AddMaddeAsync(session, ct, first, "deneme-sozcuk", ", anlam_no", ", 2")); // ayni baslik, ikinci anlam
        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => AddMaddeAsync(session, ct, first, "deneme-sozcuk"));

        Assert.Equal(Unique, exception.SqlState);
        Assert.Equal(UniqueName, exception.ConstraintName);
    }

    [Fact]
    public async Task The_unique_key_is_a_real_constraint_so_the_pipeline_can_target_it_with_ON_CONFLICT_ON_CONSTRAINT()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        await AddMaddeAsync(session, ct, slug, "deneme-sozcuk");

        int affected = await session.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, content_hash, data_version) "
            + "VALUES (@s, 'deneme-sozcuk', 'yeni', 2, 'hat', repeat('b', 64), 'test2') "
            + "ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key DO UPDATE SET duzey = EXCLUDED.duzey, data_version = EXCLUDED.data_version",
            ct,
            ("s", slug));

        Assert.Equal(1, affected);
        Assert.Equal((short)2, await session.ScalarAsync<short>("SELECT duzey FROM icerik.lugat_madde", ct));
        Assert.Equal("deneme-sozcuk", await session.ScalarAsync<string>("SELECT basliksoz_norm FROM icerik.lugat_madde", ct));
    }

    [Fact]
    public async Task The_headword_is_stored_byte_for_byte_and_may_hold_a_colon()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        // Birlesik vurgu ve ':' kaynaktaki gibi kalir (NFC uygulanmaz).
        string headword = "sozcuḱ:ek";

        await AddMaddeAsync(session, ct, slug, headword);

        Assert.Equal(headword, await session.ScalarAsync<string>("SELECT basliksoz FROM icerik.lugat_madde", ct));
    }

    [Fact]
    public async Task An_approved_madde_needs_a_non_blank_definition_but_a_candidate_may_be_empty()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddMaddeAsync(session, ct, slug, "aday-bos")); // aday, tanim NULL
        Assert.Equal(1, await AddMaddeAsync(session, ct, slug, "red-bos", ", status", ", 'red'")); // red, tanim NULL
        Assert.Equal(1, await AddMaddeAsync(session, ct, slug, "onayli-dolu", ", status, tanim_tr", ", 'onayli', 'deneme tanimi'"));

        await using RollbackSession nullDefinition = await Db.OpenRollbackSessionAsync(ct);
        string nullSlug = await AddSourceAsync(nullDefinition, ct);
        PostgresException onNull = await Assert.ThrowsAsync<PostgresException>(
            () => AddMaddeAsync(nullDefinition, ct, nullSlug, "onayli-bos", ", status", ", 'onayli'"));
        Assert.Equal(Check, onNull.SqlState);
        Assert.Equal("lugat_madde_onayli_tanim_check", onNull.ConstraintName);

        await using RollbackSession blankDefinition = await Db.OpenRollbackSessionAsync(ct);
        string blankSlug = await AddSourceAsync(blankDefinition, ct);
        PostgresException onBlank = await Assert.ThrowsAsync<PostgresException>(
            () => AddMaddeAsync(blankDefinition, ct, blankSlug, "onayli-bosluk", ", status, tanim_tr", ", 'onayli', '   '"));
        Assert.Equal("lugat_madde_onayli_tanim_check", onBlank.ConstraintName);
    }

    [Fact]
    public async Task Approving_a_candidate_without_writing_a_definition_violates_the_check()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        await AddMaddeAsync(session, ct, slug, "deneme-sozcuk");

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => session.ExecuteAsync("UPDATE icerik.lugat_madde SET status = 'onayli'", ct));

        Assert.Equal("lugat_madde_onayli_tanim_check", exception.ConstraintName);
    }

    [Fact]
    public async Task Source_and_arabic_root_are_foreign_keys()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession noSource = await Db.OpenRollbackSessionAsync(ct);
        PostgresException missingSource = await Assert.ThrowsAsync<PostgresException>(
            () => AddMaddeAsync(noSource, ct, "kaynak-yok", "deneme-sozcuk"));
        Assert.Equal(ForeignKey, missingSource.SqlState);
        Assert.Equal("lugat_madde_source_id_fkey", missingSource.ConstraintName);

        await using RollbackSession noRoot = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(noRoot, ct);
        PostgresException missingRoot = await Assert.ThrowsAsync<PostgresException>(
            () => AddMaddeAsync(noRoot, ct, slug, "deneme-sozcuk", ", ar_kok_id", ", 999999"));
        Assert.Equal(ForeignKey, missingRoot.SqlState);
        Assert.Equal("lugat_madde_ar_kok_id_fkey", missingRoot.ConstraintName);
    }

    [Fact]
    public async Task The_review_target_check_accepts_lugat_madde_and_still_rejects_unknown_tables()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession accepted = await Db.OpenRollbackSessionAsync(ct);
        Assert.Equal(1, await accepted.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('lugat_madde', 'risale-kelime-frekans:deneme', 'tanim_tr', 'oner', 'hat', 'hat')", ct));

        await using RollbackSession rejected = await Db.OpenRollbackSessionAsync(ct);
        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => rejected.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('lugat', 'x', 'tanim_tr', 'oner', 'hat', 'hat')", ct));
        Assert.Equal("review_hedef_tablo_check", exception.ConstraintName);
    }

    [Fact]
    public async Task ON_CONFLICT_ON_CONSTRAINT_with_the_new_name_updates_the_same_meaning_and_inserts_another_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        const string Upsert =
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, anlam_no, duzey, origin, tanim_tr, content_hash, data_version) "
            + "VALUES (@s, 'deneme-sozcuk', 'deneme-sozcuk', @n, 2, 'kaynak', 'deneme tanimi', repeat('b', 64), 'test2') "
            + "ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key DO UPDATE SET data_version = EXCLUDED.data_version";

        await session.ExecuteAsync(Upsert, ct, ("s", slug), ("n", (short)1));
        await session.ExecuteAsync(Upsert, ct, ("s", slug), ("n", (short)2));
        await session.ExecuteAsync(Upsert, ct, ("s", slug), ("n", (short)2));

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.lugat_madde", ct));
        Assert.Equal("1,2", await session.ScalarAsync<string>("SELECT string_agg(anlam_no::text, ',' ORDER BY anlam_no) FROM icerik.lugat_madde", ct));
    }

    [Fact]
    public async Task The_old_unique_constraint_is_gone_and_the_new_one_is_a_real_unique_constraint()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        IReadOnlyList<string> names = await Db.ColumnAsync(
            "SELECT conname || ' ' || contype::text FROM pg_constraint WHERE conrelid = 'icerik.lugat_madde'::regclass AND contype IN ('u', 'p') ORDER BY conname", ct);

        Assert.Equal(["lugat_madde_pkey p", UniqueName + " u"], names);
    }

    [Fact]
    public async Task The_meaning_number_defaults_to_one_and_a_candidate_may_carry_a_source_definition()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        await session.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, tanim_tr, content_hash, data_version) "
            + "VALUES (@s, 'kaynakli', 'kaynakli', 4, 'kaynak', 'deneme tanimi', repeat('a', 64), 'test')",
            ct,
            ("s", slug));

        Assert.Equal((short)1, await session.ScalarAsync<short>("SELECT anlam_no FROM icerik.lugat_madde", ct));
        Assert.Equal("aday", await session.ScalarAsync<string>("SELECT status::text FROM icerik.lugat_madde", ct));
        Assert.Equal("deneme tanimi", await session.ScalarAsync<string>("SELECT tanim_tr FROM icerik.lugat_madde", ct));
        Assert.Equal((short)4, await session.ScalarAsync<short>("SELECT duzey FROM icerik.lugat_madde", ct));
    }

    [Fact]
    public async Task Migrating_from_AddLugatMadde_gives_existing_rows_anlam_no_one_and_down_drops_only_rows_the_old_schema_cannot_hold()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("lugatanlam", ct);
        await using (DbSession before = fresh.OpenSession())
        {
            await before.Context.GetService<IMigrator>().MigrateAsync(LugatTableMigration, ct);
        }

        string slug = TestData.UniqueSlug();
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni) VALUES (@s, 'risale', 'Deneme kaynagi', '1', 'Deneme atfi')", ct, ("s", slug));
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, content_hash, data_version) VALUES (@s, 'birinci', 'birinci', 1, 'hat', repeat('a', 64), 'test')", ct, ("s", slug));
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, status, tanim_tr, origin, content_hash, data_version) VALUES (@s, 'ikinci', 'ikinci', 2, 'onayli', 'deneme tanimi', 'editor', repeat('b', 64), 'test')", ct, ("s", slug));

        await fresh.MigrateAsync(ct);

        Assert.Equal(2L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.lugat_madde WHERE anlam_no = 1", ct));
        Assert.Equal("onayli", await fresh.ScalarAsync<string>("SELECT status::text FROM icerik.lugat_madde WHERE basliksoz = 'ikinci'", ct));
        Assert.Equal("deneme tanimi", await fresh.ScalarAsync<string>("SELECT tanim_tr FROM icerik.lugat_madde WHERE basliksoz = 'ikinci'", ct));

        // Yeni sema: ikinci anlam ve 'kaynak' koken girer.
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, anlam_no, duzey, origin, tanim_tr, content_hash, data_version) VALUES (@s, 'birinci', 'birinci', 2, 1, 'kaynak', 'ikinci anlam', repeat('c', 64), 'test')", ct, ("s", slug));
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, tanim_tr, content_hash, data_version) VALUES (@s, 'ucuncu', 'ucuncu', 4, 'kaynak', 'kaynak tanimi', repeat('d', 64), 'test')", ct, ("s", slug));

        await using (DbSession down = fresh.OpenSession())
        {
            await down.Context.GetService<IMigrator>().MigrateAsync(LugatTableMigration, ct);
        }

        // Eski sema ikinci anlami ve kaynak kokenini tasiyamaz; oteki satirlar ayni kalir ve eski tekillik geri gelir.
        Assert.Equal(2L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.lugat_madde", ct));
        Assert.Equal("onayli", await fresh.ScalarAsync<string>("SELECT status::text FROM icerik.lugat_madde WHERE basliksoz = 'ikinci'", ct));
        Assert.Equal(0L, await fresh.ScalarAsync<long>(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'icerik' AND table_name = 'lugat_madde' AND column_name = 'anlam_no'", ct));
        PostgresException duplicate = await Assert.ThrowsAsync<PostgresException>(() => fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, content_hash, data_version) VALUES (@s, 'birinci', 'birinci', 1, 'hat', repeat('a', 64), 'test')", ct, ("s", slug)));
        Assert.Equal("lugat_madde_source_id_basliksoz_key", duplicate.ConstraintName);
    }

    [Fact]
    public async Task The_ef_model_round_trips_a_row_and_stamps_updated_at_on_change()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        LugatMadde madde = new()
        {
            SourceId = slug,
            Basliksoz = "deneme-sozcuk",
            BasliksozNorm = "deneme-sozcuk",
            Duzey = 3,
            Origin = LugatMaddeText.HatOrigin,
            ContentHash = LugatMaddeText.ComputeHash("deneme-sozcuk", null),
            DataVersion = "test",
            Kaynaklar = "{\"siklik\": 12}",
        };
        session.Context.Add(madde);
        await session.Context.SaveChangesAsync(ct);

        madde.TanimTr = "deneme tanimi";
        madde.Status = XrefStatus.Onayli;
        await session.Context.SaveChangesAsync(ct);

        Assert.True(madde.Id > 0);
        Assert.Equal("onayli", await session.ScalarAsync<string>("SELECT status::text FROM icerik.lugat_madde WHERE id = @i", ct, ("i", madde.Id)));
        Assert.Equal("{\"siklik\": 12}", await session.ScalarAsync<string>("SELECT kaynaklar::text FROM icerik.lugat_madde WHERE id = @i", ct, ("i", madde.Id)));
    }

    [Fact]
    public async Task Migrating_from_the_previous_migration_keeps_existing_data_and_down_restores_the_previous_review_check()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("lugatmigration", ct);

        // Onceki goce kadar uygula ve mevcut veri yaz.
        await using (DbSession before = fresh.OpenSession())
        {
            IMigrator migrator = before.Context.GetService<IMigrator>();
            await migrator.MigrateAsync(PreviousMigration, ct);
        }

        Assert.Equal(0L, await fresh.ScalarAsync<long>(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'icerik' AND table_name = 'lugat_madde'", ct));
        string slug = TestData.UniqueSlug();
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni) VALUES (@s, 'risale', 'Deneme kaynagi', '1', 'Deneme atfi')", ct, ("s", slug));
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('source', @s, 'metin_durumu', 'oner', 'hat', 'hat')", ct, ("s", slug));
        PostgresException old = await Assert.ThrowsAsync<PostgresException>(() => fresh.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('lugat_madde', 'x:y', 'tanim_tr', 'oner', 'hat', 'hat')", ct));
        Assert.Equal("review_hedef_tablo_check", old.ConstraintName);

        // Son goc: tablo gelir, mevcut veri ayni kalir, yeni hedef kabul edilir.
        await fresh.MigrateAsync(ct);

        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.source WHERE slug = @s", ct, ("s", slug)));
        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'source'", ct));
        Assert.Equal(1, await fresh.ExecuteAsync(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('lugat_madde', 'x:y', 'tanim_tr', 'oner', 'hat', 'hat')", ct));
        await fresh.ExecuteAsync(
            "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, duzey, origin, content_hash, data_version) VALUES (@s, 'deneme', 'deneme', 1, 'hat', repeat('a', 64), 'test')", ct, ("s", slug));

        // Geri alma: lugat_madde tablosu ve ona bagli incelemeler gider; oteki veri ve eski CHECK kalir.
        await using (DbSession down = fresh.OpenSession())
        {
            IMigrator migrator = down.Context.GetService<IMigrator>();
            await migrator.MigrateAsync(PreviousMigration, ct);
            Assert.Equal(PreviousMigration, (await down.Context.Database.GetAppliedMigrationsAsync(ct)).Last());
        }

        Assert.Equal(0L, await fresh.ScalarAsync<long>(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'icerik' AND table_name = 'lugat_madde'", ct));
        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.review", ct));
        Assert.Equal(1L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.source WHERE slug = @s", ct, ("s", slug)));
    }
}
