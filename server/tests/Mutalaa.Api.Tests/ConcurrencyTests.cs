using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>Iyimser eszamanlilik: xmin sistem sutunu belirtec olarak calisir, gercek bir sutun olusmaz (Docker'li).</summary>
public class ConcurrencyTests(EditorialDatabase<ConcurrencyTests> fixture) : IClassFixture<EditorialDatabase<ConcurrencyTests>>
{
    private TestDatabase Db => fixture.Database;

    [Fact]
    public async Task A_second_context_updating_the_same_source_row_gets_a_concurrency_exception()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source seed = TestData.NewSource();
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(seed);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession first = Db.OpenSession();
        await using DbSession second = Db.OpenSession();
        Source a = await first.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
        Source b = await second.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);

        a.Baslik = "Birinci degisiklik";
        await first.Context.SaveChangesAsync(ct);
        b.Baslik = "Ikinci degisiklik";

        await Assert.ThrowsAsync<DbUpdateConcurrencyException>(() => second.Context.SaveChangesAsync(ct));
        Assert.Equal("Birinci degisiklik", await Db.ScalarAsync<string>("SELECT baslik FROM icerik.source WHERE slug = @s", ct, ("s", seed.Slug)));
    }

    [Fact]
    public async Task A_second_context_updating_the_same_unit_row_gets_a_concurrency_exception()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = TestData.NewSource();
        Unit seed = TestData.NewUnit(source.Slug, TestData.UnitAnchor());
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(source);
            writer.Context.Add(seed);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession first = Db.OpenSession();
        await using DbSession second = Db.OpenSession();
        Unit a = await first.Context.Units.SingleAsync(u => u.Id == seed.Id, ct);
        Unit b = await second.Context.Units.SingleAsync(u => u.Id == seed.Id, ct);

        a.Metin = "Deneme paragrafi 2";
        await first.Context.SaveChangesAsync(ct);
        b.Metin = "Deneme paragrafi 3";

        await Assert.ThrowsAsync<DbUpdateConcurrencyException>(() => second.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Deleting_a_row_changed_by_another_context_gets_a_concurrency_exception()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source seed = TestData.NewSource();
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(seed);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession first = Db.OpenSession();
        await using DbSession second = Db.OpenSession();
        Source a = await first.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
        Source b = await second.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
        a.Notlar = "degisti";
        await first.Context.SaveChangesAsync(ct);

        second.Context.Remove(b);

        await Assert.ThrowsAsync<DbUpdateConcurrencyException>(() => second.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task One_context_can_save_the_same_row_repeatedly_because_the_token_is_refreshed()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source seed = TestData.NewSource();
        await using DbSession session = Db.OpenSession();
        session.Context.Add(seed);
        await session.Context.SaveChangesAsync(ct);

        seed.Baslik = "Bir";
        await session.Context.SaveChangesAsync(ct);
        seed.Baslik = "Iki";
        await session.Context.SaveChangesAsync(ct);

        Assert.Equal("Iki", await Db.ScalarAsync<string>("SELECT baslik FROM icerik.source WHERE slug = @s", ct, ("s", seed.Slug)));
    }

    [Fact]
    public async Task A_stale_context_whose_row_is_unchanged_in_the_database_saves_normally()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source seed = TestData.NewSource();
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(seed);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession reader = Db.OpenSession();
        Source loaded = await reader.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
        loaded.Baslik = "Tek degisiklik";

        Assert.Equal(1, await reader.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task No_real_user_column_named_xmin_exists()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        long viaInformationSchema = await Db.ScalarAsync<long>(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema IN ('icerik', 'kimlik') AND column_name = 'xmin'", ct);
        // pg_attribute sistem sutunlarini (attnum < 0) da listeler: yalniz kullanici sutunlari (attnum > 0) sayilir.
        long viaCatalog = await Db.ScalarAsync<long>(
            "SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
            + "WHERE n.nspname IN ('icerik', 'kimlik') AND a.attnum > 0 AND NOT a.attisdropped AND a.attname = 'xmin'",
            ct);

        Assert.Equal(0L, viaInformationSchema);
        Assert.Equal(0L, viaCatalog);
    }

    [Fact]
    public async Task The_only_column_named_version_is_the_documented_lemma_gloss_text_column_not_a_concurrency_token()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        // Editoryal veritabani 5: lemma_gloss.version kelime anlami surumudur (text); eszamanlilik belirteci degildir.
        IReadOnlyList<string> columns = await Db.ColumnAsync(
            "SELECT table_schema || '.' || table_name || '.' || column_name || ':' || data_type FROM information_schema.columns "
            + "WHERE table_schema IN ('icerik', 'kimlik') AND column_name = 'version' ORDER BY 1",
            ct);

        Assert.Equal(["icerik.lemma_gloss.version:text"], columns);
    }
}
