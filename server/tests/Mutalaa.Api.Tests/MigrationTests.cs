using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests;

/// <summary>Bos veritabanina butun goclar (Docker'li, Testcontainers postgres:18.6-trixie).</summary>
public class MigrationTests(EditorialDatabase<MigrationTests> fixture, PostgresFixture postgres) : IClassFixture<EditorialDatabase<MigrationTests>>
{
    private const string UserTables =
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = @schema AND table_type = 'BASE TABLE' AND table_name <> '__EFMigrationsHistory'";

    private TestDatabase Db => fixture.Database;

    [Fact]
    public async Task All_migrations_are_applied_and_none_is_pending()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using DbSession session = Db.OpenSession();

        IReadOnlyList<string> applied = [.. await session.Context.Database.GetAppliedMigrationsAsync(ct)];
        IReadOnlyList<string> pending = [.. await session.Context.Database.GetPendingMigrationsAsync(ct)];

        Assert.NotEmpty(applied);
        Assert.Equal(session.Context.Database.GetMigrations(), applied);
        Assert.Empty(pending);
    }

    [Fact]
    public async Task The_model_has_no_pending_changes_against_the_migrations()
    {
        await using DbSession session = Db.OpenSession();

        Assert.False(session.Context.Database.HasPendingModelChanges());
    }

    [Fact]
    public async Task The_icerik_schema_has_19_tables_and_the_kimlik_schema_7()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        Assert.Equal(19L, await Db.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));
        Assert.Equal(7L, await Db.ScalarAsync<long>(UserTables, ct, ("schema", "kimlik")));
        Assert.Equal(1L, await Db.ScalarAsync<long>(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'icerik' AND table_name = '__EFMigrationsHistory'", ct));
    }

    [Fact]
    public async Task There_are_eleven_enum_types_in_the_icerik_schema()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        long count = await Db.ScalarAsync<long>(
            "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname = 'icerik' AND t.typtype = 'e'", ct);

        Assert.Equal(11L, count);
        Assert.Equal(PostgresEnums.Definitions.Count, (int)count);
    }

    [Fact]
    public async Task The_test_database_is_utf8_with_the_c_utf8_locale_and_utc()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        Assert.Equal("UTF8", await Db.ScalarAsync<string>("SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()", ct));
        Assert.Equal("C.UTF-8", await Db.ScalarAsync<string>("SELECT datcollate FROM pg_database WHERE datname = current_database()", ct));
        Assert.Equal("UTC", await Db.ScalarAsync<string>("SHOW TimeZone", ct));
        Assert.StartsWith("18.", await Db.ScalarAsync<string>("SHOW server_version", ct), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Migrating_an_empty_database_under_tr_TR_yields_the_same_catalog()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("migrationtr", ct);

        // Henuz goc uygulanmamis: butun goclar bekliyor.
        await using (DbSession session = fresh.OpenSession())
        {
            Assert.Equal(session.Context.Database.GetMigrations(), await session.Context.Database.GetPendingMigrationsAsync(ct));
            Assert.Empty(await session.Context.Database.GetAppliedMigrationsAsync(ct));
        }

        // Model onbellegi atlanir: model ve goc SQL'i tr-TR altinda sifirdan kurulur.
        await AsyncCultureScope.TurkishAsync(() => fresh.MigrateAsync(ct, uncachedModel: true));

        await using (DbSession session = fresh.OpenSession())
        {
            Assert.Empty(await session.Context.Database.GetPendingMigrationsAsync(ct));
            Assert.False(session.Context.Database.HasPendingModelChanges());
        }

        Assert.Equal(19L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));
        Assert.Equal(7L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "kimlik")));
        Assert.Equal(await CatalogAsync(Db, ct), await CatalogAsync(fresh, ct));
    }

    [Fact]
    public async Task Applying_all_migrations_to_a_fresh_database_under_the_invariant_culture_creates_the_full_schema()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("migrationfresh", ct);

        // Henuz hicbir goc uygulanmadi: bu test goclerin kendisini uygular (fikstur veritabanindan bagimsiz).
        await using (DbSession before = fresh.OpenSession())
        {
            Assert.Empty(await before.Context.Database.GetAppliedMigrationsAsync(ct));
            Assert.NotEmpty(await before.Context.Database.GetPendingMigrationsAsync(ct));
        }

        Assert.Equal(0L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));

        await fresh.MigrateAsync(ct);

        await using (DbSession after = fresh.OpenSession())
        {
            IReadOnlyList<string> applied = [.. await after.Context.Database.GetAppliedMigrationsAsync(ct)];
            Assert.NotEmpty(applied);
            Assert.Equal(after.Context.Database.GetMigrations(), applied);
            Assert.Empty(await after.Context.Database.GetPendingMigrationsAsync(ct));
            Assert.False(after.Context.Database.HasPendingModelChanges());
        }

        Assert.Equal(19L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));
        Assert.Equal(7L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "kimlik")));
        Assert.Equal(11L, await fresh.ScalarAsync<long>(EnumTypes, ct));
        Assert.Equal(await CatalogAsync(Db, ct), await CatalogAsync(fresh, ct));
    }

    [Fact]
    public async Task Migrating_down_to_zero_removes_the_schema_and_migrating_up_again_restores_the_same_catalog()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase fresh = await postgres.CreateDatabaseAsync("migrationdown", ct);
        await fresh.MigrateAsync(ct);
        string catalogBefore = await CatalogAsync(fresh, ct);
        long icerikTables = await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik"));
        long kimlikTables = await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "kimlik"));
        Assert.Equal(19L, icerikTables);
        Assert.Equal(7L, kimlikTables);

        // Down: bos surume ("0") geri al.
        await using (DbSession down = fresh.OpenSession())
        {
            IMigrator migrator = down.Context.GetService<IMigrator>();
            await migrator.MigrateAsync(Migration.InitialDatabase, ct);
            Assert.Empty(await down.Context.Database.GetAppliedMigrationsAsync(ct));
        }

        // Down sonrasi icerik'te yalniz (bos) __EFMigrationsHistory kalir; tablo, enum ve kimlik semasi yok.
        Assert.Equal(0L, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));
        Assert.Equal(0L, await fresh.ScalarAsync<long>(EnumTypes, ct));
        Assert.Equal(0L, await fresh.ScalarAsync<long>("SELECT count(*) FROM pg_namespace WHERE nspname = 'kimlik'", ct));
        Assert.Equal(0L, await fresh.ScalarAsync<long>("SELECT count(*) FROM icerik.\"__EFMigrationsHistory\"", ct));

        // Yeniden yukari: ayni katalog.
        await fresh.MigrateAsync(ct);

        await using (DbSession up = fresh.OpenSession())
        {
            Assert.Empty(await up.Context.Database.GetPendingMigrationsAsync(ct));
            Assert.False(up.Context.Database.HasPendingModelChanges());
        }

        Assert.Equal(icerikTables, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "icerik")));
        Assert.Equal(kimlikTables, await fresh.ScalarAsync<long>(UserTables, ct, ("schema", "kimlik")));
        Assert.Equal(11L, await fresh.ScalarAsync<long>(EnumTypes, ct));
        Assert.Equal(catalogBefore, await CatalogAsync(fresh, ct));
    }

    private const string EnumTypes =
        "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname = 'icerik' AND t.typtype = 'e'";

    /// <summary>Sutun, kisit ve dizin tanimlarinin sirali dokumu (veritabani adindan bagimsiz).</summary>
    private static async Task<string> CatalogAsync(TestDatabase db, CancellationToken ct)
    {
        IReadOnlyList<string> columns = await db.ColumnAsync(
            "SELECT table_schema || '.' || table_name || '.' || column_name || ' ' || data_type || ' ' || coalesce(udt_name, '') || ' ' || coalesce(collation_name, '') || ' ' || is_nullable || ' ' || coalesce(column_default, '') || ' ' || coalesce(generation_expression, '') "
            + "FROM information_schema.columns WHERE table_schema IN ('icerik', 'kimlik') ORDER BY table_schema, table_name, column_name",
            ct);
        IReadOnlyList<string> constraints = await db.ColumnAsync(
            "SELECT n.nspname || '.' || c.conrelid::regclass::text || ' ' || c.conname || ' ' || pg_get_constraintdef(c.oid) "
            + "FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname IN ('icerik', 'kimlik') ORDER BY 1",
            ct);
        IReadOnlyList<string> indexes = await db.ColumnAsync(
            "SELECT indexdef FROM pg_indexes WHERE schemaname IN ('icerik', 'kimlik') ORDER BY indexdef",
            ct);
        return string.Join('\n', columns.Concat(constraints).Concat(indexes));
    }
}
