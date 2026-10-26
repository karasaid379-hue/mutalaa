using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Api.Tests;

/// <summary>Capa donusturucusu gercek veritabaniyla (Docker'li): yazma, okuma, bozuk satir ve C siralamasi.</summary>
public class AnchorConverterTests(EditorialDatabase<AnchorConverterTests> fixture) : IClassFixture<EditorialDatabase<AnchorConverterTests>>
{
    private TestDatabase Db => fixture.Database;

    private async Task<string> NewSourceAsync(CancellationToken ct)
    {
        await using DbSession session = Db.OpenSession();
        Source source = TestData.NewSource();
        session.Context.Add(source);
        await session.Context.SaveChangesAsync(ct);
        return source.Slug;
    }

    private Task InsertRawUnitAsync(string sourceId, string anchor, CancellationToken ct, string? parentPath = null) =>
        Db.ExecuteAsync(
            "INSERT INTO icerik.unit (anchor, kind, source_id, parent_path, ord, metin, content_hash, data_version) "
            + "VALUES (@anchor, 'risale'::icerik.unit_kind, @source, @parent, 1, 'Deneme paragrafi 1', @hash, 'test')",
            ct,
            ("anchor", anchor),
            ("source", sourceId),
            ("parent", parentPath),
            ("hash", TestData.Hash()));

    [Fact]
    public async Task Writing_an_anchor_with_a_span_fails_and_leaves_no_row()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);
        await using DbSession session = Db.OpenSession();
        Unit unit = TestData.NewUnit(slug, "meal:elmalili:2:255");
        unit.Anchor = AnchorRef.Parse("meal:elmalili:2:255@3-8");
        Assert.NotNull(unit.Anchor.Span);
        session.Context.Add(unit);

        Exception exception = await Assert.ThrowsAnyAsync<Exception>(() => session.Context.SaveChangesAsync(ct));

        // EF yazma hatasini DbUpdateException ile sarabilir; asil istisna zincirde aranir.
        Assert.NotNull(TestData.FindInChain<InvalidOperationException>(exception));
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM icerik.unit WHERE source_id = @s", ct, ("s", slug)));
    }

    [Fact]
    public async Task A_valid_unit_anchor_is_written_and_read_back_equal()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);
        Unit unit = TestData.NewUnit(slug, "rn:sozler:soz-10:hakikat-3:p4:s2");
        AnchorRef anchor = unit.Anchor;
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(unit);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession reader = Db.OpenSession();
        Unit read = await reader.Context.Units.AsNoTracking().SingleAsync(u => u.SourceId == slug, ct);

        Assert.Equal(anchor, read.Anchor);
        Assert.Equal("rn:sozler:soz-10:hakikat-3:p4:s2", read.Anchor.ToString());
        Assert.Equal("rn:sozler:soz-10:hakikat-3:p4:s2", await Db.ScalarAsync<string>("SELECT anchor FROM icerik.unit WHERE source_id = @s", ct, ("s", slug)));
    }

    [Fact]
    public async Task Anchor_comparison_in_a_query_uses_the_converted_canonical_string()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);
        await using (DbSession writer = Db.OpenSession())
        {
            writer.Context.Add(TestData.NewUnit(slug, "rn:sozler:soz-10:p1"));
            writer.Context.Add(TestData.NewUnit(slug, "rn:sozler:soz-10:p2"));
            await writer.Context.SaveChangesAsync(ct);
        }

        AnchorRef wanted = AnchorRef.Parse("rn:sozler:soz-10:p2");
        await using DbSession reader = Db.OpenSession();
        Unit found = await reader.Context.Units.AsNoTracking().SingleAsync(u => u.SourceId == slug && u.Anchor == wanted, ct);

        Assert.Equal(wanted, found.Anchor);
    }

    [Fact]
    public async Task An_invalid_anchor_string_in_the_database_throws_an_anchor_exception_on_read()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);
        await InsertRawUnitAsync(slug, "zzz", ct);
        await using DbSession session = Db.OpenSession();

        Exception exception = await Assert.ThrowsAnyAsync<Exception>(
            () => session.Context.Units.AsNoTracking().Where(u => u.SourceId == slug).ToListAsync(ct));

        Assert.NotNull(TestData.FindInChain<AnchorException>(exception));
    }

    [Fact]
    public async Task A_non_canonical_anchor_string_in_the_database_also_throws_on_read()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);
        await InsertRawUnitAsync(slug, "Q:2:255", ct);
        await using DbSession session = Db.OpenSession();

        Exception exception = await Assert.ThrowsAnyAsync<Exception>(
            () => session.Context.Units.AsNoTracking().Where(u => u.SourceId == slug).ToListAsync(ct));

        Assert.NotNull(TestData.FindInChain<AnchorException>(exception));
    }

    [Theory]
    [InlineData("icerik.unit", "anchor")]
    [InlineData("icerik.unit", "parent_path")]
    [InlineData("icerik.source", "slug")]
    [InlineData("icerik.xref", "src_anchor")]
    [InlineData("icerik.xref", "dst_anchor")]
    [InlineData("icerik.quran_word", "anchor")]
    [InlineData("icerik.quran_word_fix", "anchor")]
    [InlineData("icerik.page_map", "start_anchor")]
    public async Task Anchor_and_slug_columns_use_the_c_collation(string table, string column)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string[] parts = table.Split('.');

        string collation = await Db.ScalarAsync<string>(
            "SELECT collation_name FROM information_schema.columns WHERE table_schema = @schema AND table_name = @table AND column_name = @column",
            ct,
            ("schema", parts[0]),
            ("table", parts[1]),
            ("column", column));

        Assert.Equal("C", collation);
    }

    [Fact]
    public async Task Ordering_and_prefix_queries_follow_byte_order_at_the_boundaries()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string slug = await NewSourceAsync(ct);

        // Ham SQL yalniz test duzenegi: capa gecerliligini atlayip bayt siralamasini yoklar (okuma EF ile yapilmaz).
        string[] paths = ["rn:sozler:soz-10", "rn:sozler:soz-2", "rn:sozlerx:soz-1", "rn:sozle", "rn:Sozler:soz-1", "rn:sozler:", "rn:sozler_:soz-1"];
        int n = 0;
        foreach (string path in paths)
        {
            await InsertRawUnitAsync(slug, $"zzz-{++n}", ct, parentPath: path);
        }

        IReadOnlyList<string> ordered = await Db.ColumnAsync(
            "SELECT parent_path FROM icerik.unit WHERE source_id = @s ORDER BY parent_path", ct, ("s", slug));
        Assert.Equal(paths.Order(StringComparer.Ordinal), ordered);

        IReadOnlyList<string> prefixed = await Db.ColumnAsync(
            "SELECT parent_path FROM icerik.unit WHERE source_id = @s AND parent_path LIKE 'rn:sozler:%' ORDER BY parent_path", ct, ("s", slug));
        Assert.Equal(["rn:sozler:", "rn:sozler:soz-10", "rn:sozler:soz-2"], prefixed);

        IReadOnlyList<string> range = await Db.ColumnAsync(
            "SELECT parent_path FROM icerik.unit WHERE source_id = @s AND parent_path >= 'rn:sozler:' AND parent_path < 'rn:sozler;' ORDER BY parent_path", ct, ("s", slug));
        Assert.Equal(prefixed, range);
    }

    [Fact]
    public async Task Xref_anchors_round_trip_and_an_invalid_xref_anchor_throws_on_read()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Xref xref = TestData.NewXref(src: "q:2:255:3-7", dst: "tf:elmalili:2-255-257:p3");
        xref.Type = XrefType.Konu;
        await using (DbSession writer = Db.OpenSession())
        {
            // Kelime araligi capanin kendi parcasidir (q:2:255:3-7), '@' araligi degil: yazilabilir.
            Assert.Null(xref.SrcAnchor.Span);
            writer.Context.Add(xref);
            await writer.Context.SaveChangesAsync(ct);
        }

        await using DbSession reader = Db.OpenSession();
        Xref read = await reader.Context.Xrefs.AsNoTracking().SingleAsync(x => x.Id == xref.Id, ct);
        Assert.Equal(xref.SrcAnchor, read.SrcAnchor);
        Assert.Equal(xref.DstAnchor, read.DstAnchor);

        await Db.ExecuteAsync("UPDATE icerik.xref SET dst_anchor = 'zzz' WHERE id = @id", ct, ("id", xref.Id));
        await using DbSession bad = Db.OpenSession();
        Exception exception = await Assert.ThrowsAnyAsync<Exception>(() => bad.Context.Xrefs.AsNoTracking().Where(x => x.Id == xref.Id).ToListAsync(ct));
        Assert.NotNull(TestData.FindInChain<AnchorException>(exception));
    }
}
