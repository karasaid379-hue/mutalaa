using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests;

/// <summary>RowVersion yardimcisi (xmin adi, Get ve Expect) ve review denetim izi sutunlari (K-48).</summary>
public class RowVersionTests(EditorialDatabase<RowVersionTests> fixture) : IClassFixture<EditorialDatabase<RowVersionTests>>
{
    private TestDatabase Db => fixture.Database;

    [Fact]
    public void Name_is_xmin_and_the_model_uses_the_same_name_for_every_content_entity()
    {
        Assert.Equal("xmin", RowVersion.Name);

        ModelFactory.ForEachModel(model =>
        {
            foreach (var entityType in model.GetEntityTypes().Where(t => string.Equals(t.GetSchema(), IcerikDbContext.ContentSchema, StringComparison.Ordinal)))
            {
                Assert.NotNull(entityType.FindProperty(RowVersion.Name));
            }
        });
    }

    [Fact]
    public void Get_reads_and_Expect_sets_the_original_value_of_the_xmin_shadow_property()
    {
        using ServiceProvider provider = ModelFactory.BuildServices();
        using IServiceScope scope = provider.CreateScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        Source source = TestData.NewSource();
        EntityEntry entry = context.Attach(source);

        entry.Property(RowVersion.Name).CurrentValue = 41u;
        entry.Property(RowVersion.Name).OriginalValue = 41u;
        Assert.Equal(41u, RowVersion.Get(entry));

        RowVersion.Expect(entry, 7u);

        Assert.Equal(7u, entry.Property(RowVersion.Name).OriginalValue);
        Assert.Equal(41u, RowVersion.Get(entry));
    }

    [Fact]
    public void Null_entries_are_rejected()
    {
        Assert.Throws<ArgumentNullException>(() => RowVersion.Get(null!));
        Assert.Throws<ArgumentNullException>(() => RowVersion.Expect(null!, 1u));
    }

    [Fact]
    public async Task Expect_with_a_stale_version_conflicts_and_with_the_current_version_saves()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source seed = TestData.NewSource();
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(seed);
            await writer.Context.SaveChangesAsync(ct);
        }

        uint staleVersion;
        await using (DbSession reader = Db.OpenSession())
        {
            Source loaded = await reader.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
            staleVersion = RowVersion.Get(reader.Context.Entry(loaded));
        }

        await using (DbSession other = Db.OpenSession())
        {
            Source loaded = await other.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
            loaded.Baslik = "Baska editor";
            await other.Context.SaveChangesAsync(ct);
        }

        await using (DbSession stale = Db.OpenSession())
        {
            Source loaded = await stale.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
            loaded.Baslik = "Bayat istemci";
            RowVersion.Expect(stale.Context.Entry(loaded), staleVersion);

            await Assert.ThrowsAsync<DbUpdateConcurrencyException>(() => stale.Context.SaveChangesAsync(ct));
        }

        await using (DbSession fresh = Db.OpenSession())
        {
            Source loaded = await fresh.Context.Sources.SingleAsync(s => s.Slug == seed.Slug, ct);
            loaded.Baslik = "Guncel istemci";
            RowVersion.Expect(fresh.Context.Entry(loaded), RowVersion.Get(fresh.Context.Entry(loaded)));

            Assert.Equal(1, await fresh.Context.SaveChangesAsync(ct));
        }

        Assert.Equal("Guncel istemci", await Db.ScalarAsync<string>("SELECT baslik FROM icerik.source WHERE slug = @s", ct, ("s", seed.Slug)));
    }

    [Fact]
    public async Task Review_audit_columns_are_nullable_and_round_trip()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        DateTime second = new(2026, 11, 9, 12, 30, 0, DateTimeKind.Utc);
        Review empty = new() { HedefTablo = "unit", HedefAnahtar = "meal:test:1:1", Alan = "metin", Eylem = "oner", Koken = XrefOrigin.Hat, Oneren = "hat" };
        Review full = new()
        {
            HedefTablo = "unit",
            HedefAnahtar = "meal:test:1:2",
            Alan = "metin",
            Eylem = "duzenle_onayla",
            Koken = XrefOrigin.Editor,
            Oneren = "test-editor-1",
            Onerilen = "{\"metin\":\"Deneme paragrafi 1\"}",
            Duzenlenen = "{\"metin\":\"Deneme paragrafi 2\"}",
            Inceleyen = "test-editor-2",
            IkinciInceleyen = "test-editor-3",
            IkinciIncelendiAt = second,
            IkinciGerekce = "Deneme gerekcesi",
        };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.AddRange(empty, full);
            await session.Context.SaveChangesAsync(ct);
        }

        Assert.Equal(1L, await Db.ScalarAsync<long>(
            "SELECT count(*) FROM icerik.review WHERE id = @id AND duzenlenen IS NULL AND ikinci_incelendi_at IS NULL AND ikinci_gerekce IS NULL",
            ct,
            ("id", empty.Id)));

        await using DbSession read = Db.OpenSession();
        Review loaded = await read.Context.Reviews.AsNoTracking().SingleAsync(r => r.Id == full.Id, ct);
        Assert.Equal("{\"metin\": \"Deneme paragrafi 2\"}", loaded.Duzenlenen);
        Assert.Equal("{\"metin\": \"Deneme paragrafi 1\"}", loaded.Onerilen);
        Assert.Equal(second, loaded.IkinciIncelendiAt);
        Assert.Equal(DateTimeKind.Utc, loaded.IkinciIncelendiAt!.Value.Kind);
        Assert.Equal("Deneme gerekcesi", loaded.IkinciGerekce);
    }
}
