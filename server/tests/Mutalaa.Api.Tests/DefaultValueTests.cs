using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Tests;

/// <summary>
/// EF'in gercek INSERT davranisi ve DDL varsayilanlari (Docker'li): bilincle yazilan 0. uye ya da 0 degeri, veritabani DEFAULT'u tarafindan
/// ezilmez (HasDefaultValue + ValueGeneratedNever); hic atanmamis alanlar Domain baslangic degeriyle yazilir.
/// </summary>
public class DefaultValueTests(EditorialDatabase<DefaultValueTests> fixture) : IClassFixture<EditorialDatabase<DefaultValueTests>>
{
    private TestDatabase Db => fixture.Database;

    private async Task<T> ReadAsync<T>(Func<IcerikReader, Task<T>> read, CancellationToken ct)
    {
        await using DbSession session = Db.OpenSession();
        return await read(new IcerikReader(session, ct));
    }

    private sealed record IcerikReader(DbSession Session, CancellationToken Ct);

    private async Task<Source> SaveSourceAsync(Action<Source>? configure, CancellationToken ct)
    {
        Source source = TestData.NewSource();
        configure?.Invoke(source);
        await using DbSession session = Db.OpenSession();
        session.Context.Add(source);
        await session.Context.SaveChangesAsync(ct);
        return source;
    }

    private async Task<Unit> SaveUnitAsync(Action<Unit>? configure, CancellationToken ct)
    {
        Source source = await SaveSourceAsync(null, ct);
        Unit unit = TestData.NewUnit(source.Slug, TestData.UnitAnchor());
        configure?.Invoke(unit);
        await using DbSession session = Db.OpenSession();
        session.Context.Add(unit);
        await session.Context.SaveChangesAsync(ct);
        return unit;
    }

    // unit.rev: veritabani varsayilani 1, CLR varsayilani 0 (varsayilani CLR varsayilanindan farkli gercek sutun).

    [Fact]
    public async Task An_explicit_zero_rev_is_written_and_read_back_not_replaced_by_the_database_default()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Unit unit = await SaveUnitAsync(u => u.Rev = 0, ct);

        Unit read = await ReadAsync(r => r.Session.Context.Units.AsNoTracking().SingleAsync(u => u.Id == unit.Id, r.Ct), ct);

        Assert.Equal(0, read.Rev);
        Assert.Equal(0, await Db.ScalarAsync<int>("SELECT rev FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
    }

    [Fact]
    public async Task A_unit_whose_rev_was_never_assigned_is_written_with_the_domain_initial_value_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Unit unit = await SaveUnitAsync(null, ct);

        Unit read = await ReadAsync(r => r.Session.Context.Units.AsNoTracking().SingleAsync(u => u.Id == unit.Id, r.Ct), ct);

        Assert.Equal(1, unit.Rev);
        Assert.Equal(1, read.Rev);
        Assert.Equal(1, await Db.ScalarAsync<int>("SELECT rev FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
    }

    [Theory]
    [InlineData(TextStatus.Taslak, "taslak")]
    [InlineData(TextStatus.Incelemede, "incelemede")]
    [InlineData(TextStatus.Onayli, "onayli")]
    public async Task Every_metin_durumu_is_written_as_its_own_label(TextStatus status, string label)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Unit unit = await SaveUnitAsync(u => u.MetinDurumu = status, ct);

        Assert.Equal(label, await Db.ScalarAsync<string>("SELECT metin_durumu::text FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
    }

    [Fact]
    public async Task Lemma_gloss_boolean_and_jsonb_defaults_match_the_ddl_when_untouched()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = await SaveSourceAsync(null, ct);
        Lemma lemma = new() { Id = 1, Lang = "ar", Text = "lemma-1", TextClean = "lemma-1", SourceId = source.Slug, DataVersion = "test" };
        LemmaGloss gloss = new() { LemmaId = lemma.Id, AnlamKisa = "Deneme anlami", Origin = "editor", Version = "1", ContentHash = TestData.Hash() };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.AddRange(lemma, gloss);
            await session.Context.SaveChangesAsync(ct);
        }

        LemmaGloss read = await ReadAsync(r => r.Session.Context.LemmaGlosses.AsNoTracking().SingleAsync(g => g.LemmaId == lemma.Id, r.Ct), ct);

        Assert.False(read.YalnizcaEtimolojik);
        Assert.Equal("[]", read.KuranAnlamlari);
        Assert.Equal(XrefStatus.Aday, read.Status);
        Assert.False(await Db.ScalarAsync<bool>("SELECT yalnizca_etimolojik FROM icerik.lemma_gloss WHERE lemma_id = @id", ct, ("id", lemma.Id)));
        Assert.Equal("[]", await Db.ScalarAsync<string>("SELECT kuran_anlamlari::text FROM icerik.lemma_gloss WHERE lemma_id = @id", ct, ("id", lemma.Id)));
    }

    [Fact]
    public async Task Unit_enum_and_default_columns_accept_their_zeroth_member_and_read_it_back()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = await SaveSourceAsync(s => s.Tur = SourceKind.KuranMetni, ct);
        Unit unit = TestData.NewUnit(source.Slug, TestData.UnitAnchor());
        unit.Kind = UnitKind.Ayet;
        unit.MetinDurumu = TextStatus.Taslak;
        unit.Status = UnitStatus.Etkin;
        unit.Role = "govde";
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(unit);
            await session.Context.SaveChangesAsync(ct);
        }

        Unit read = await ReadAsync(r => r.Session.Context.Units.AsNoTracking().SingleAsync(u => u.Id == unit.Id, r.Ct), ct);

        Assert.Equal(UnitKind.Ayet, read.Kind);
        Assert.Equal(TextStatus.Taslak, read.MetinDurumu);
        Assert.Equal(UnitStatus.Etkin, read.Status);
        Assert.Equal(SourceKind.KuranMetni, (await ReadAsync(r => r.Session.Context.Sources.AsNoTracking().SingleAsync(s => s.Slug == source.Slug, r.Ct), ct)).Tur);
        Assert.Equal("ayet", await Db.ScalarAsync<string>("SELECT kind::text FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
        Assert.Equal("taslak", await Db.ScalarAsync<string>("SELECT metin_durumu::text FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
        Assert.Equal("etkin", await Db.ScalarAsync<string>("SELECT status::text FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
    }

    [Fact]
    public async Task Unit_columns_written_with_non_default_members_are_not_replaced_by_defaults()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = await SaveSourceAsync(null, ct);
        Unit unit = TestData.NewUnit(source.Slug, TestData.UnitAnchor());
        unit.Kind = UnitKind.Kitap;
        unit.MetinDurumu = TextStatus.Onayli;
        unit.Role = "dipnot";
        unit.Marks = "[{\"s\":0,\"e\":3,\"t\":\"ar\"}]";
        unit.Attrs = "{\"cilt\":1}";
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(unit);
            await session.Context.SaveChangesAsync(ct);
        }

        Unit read = await ReadAsync(r => r.Session.Context.Units.AsNoTracking().SingleAsync(u => u.Id == unit.Id, r.Ct), ct);

        Assert.Equal(UnitKind.Kitap, read.Kind);
        Assert.Equal(TextStatus.Onayli, read.MetinDurumu);
        Assert.Equal("dipnot", read.Role);
        Assert.Contains("\"t\": \"ar\"", read.Marks, StringComparison.Ordinal);
        Assert.Contains("\"cilt\": 1", read.Attrs, StringComparison.Ordinal);
        Assert.Equal("{}", read.Provenance);
    }

    [Fact]
    public async Task Xref_required_enums_written_as_their_zeroth_member_are_kept_and_other_columns_take_domain_defaults()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Xref xref = TestData.NewXref(type: XrefType.Atif);
        xref.Origin = XrefOrigin.Hat;
        xref.Status = XrefStatus.Aday;
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.Add(xref);
            await session.Context.SaveChangesAsync(ct);
        }

        Xref read = await ReadAsync(r => r.Session.Context.Xrefs.AsNoTracking().SingleAsync(x => x.Id == xref.Id, r.Ct), ct);

        Assert.Equal(XrefType.Atif, read.Type);
        Assert.Equal(XrefOrigin.Hat, read.Origin);
        Assert.Equal(XrefStatus.Aday, read.Status);
        Assert.Equal(0, read.VotesUp);
        Assert.Equal(0, read.VotesDown);
        Assert.Equal("{}", read.Evidence);
        Assert.Equal(0f, read.Score);
    }

    [Fact]
    public async Task Review_and_release_status_defaults_and_zeroth_members_round_trip()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Review review = new() { HedefTablo = "source", HedefAnahtar = "x", Alan = "a", Eylem = "onayla", Koken = XrefOrigin.Hat, Oneren = "test-editor" };
        Release release = new() { Surum = "test-0", Derleme = BuildFlavor.Dev, DataVersion = "test", Olusturan = "test-editor" };
        await using (DbSession session = Db.OpenSession())
        {
            session.Context.AddRange(review, release);
            await session.Context.SaveChangesAsync(ct);
        }

        Assert.Equal("acik", await Db.ScalarAsync<string>("SELECT durum::text FROM icerik.review WHERE id = @id", ct, ("id", review.Id)));
        Assert.Equal("hat", await Db.ScalarAsync<string>("SELECT koken::text FROM icerik.review WHERE id = @id", ct, ("id", review.Id)));
        Assert.Equal("hazirlaniyor", await Db.ScalarAsync<string>("SELECT durum::text FROM icerik.release WHERE id = @id", ct, ("id", release.Id)));
        Assert.Equal("dev", await Db.ScalarAsync<string>("SELECT derleme::text FROM icerik.release WHERE id = @id", ct, ("id", release.Id)));
        Assert.Equal("yayin", await Db.ScalarAsync<string>("SELECT talep FROM icerik.release WHERE id = @id", ct, ("id", release.Id)));
        Assert.Equal(ReleaseRequests.Yayin, release.Talep);
    }

    [Fact]
    public async Task Created_at_and_updated_at_come_from_the_database_default_when_unassigned()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = await SaveSourceAsync(null, ct);

        Source read = await ReadAsync(r => r.Session.Context.Sources.AsNoTracking().SingleAsync(s => s.Slug == source.Slug, r.Ct), ct);

        Assert.True(read.CreatedAt > new DateTime(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        Assert.True(read.UpdatedAt > new DateTime(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        Assert.Equal(DateTimeKind.Utc, read.CreatedAt.Kind);
        Assert.Equal(DateTimeKind.Utc, read.UpdatedAt.Kind);
    }

    [Fact]
    public async Task Updated_at_is_stamped_in_utc_and_advances_only_on_the_modified_source_row()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source changed = await SaveSourceAsync(null, ct);
        Source untouched = await SaveSourceAsync(null, ct);

        // Konteynerin saati ana makineden sapabilir: karsilastirma saglam olsun diye once her iki satirin updated_at degeri uzak gecmise cekilir.
        DateTime old = new(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        await Db.ExecuteAsync("UPDATE icerik.source SET updated_at = @old WHERE slug = ANY(@slugs)", ct, ("old", old), ("slugs", new[] { changed.Slug, untouched.Slug }));

        DateTime before = DateTime.UtcNow;
        await using (DbSession session = Db.OpenSession())
        {
            Source tracked = await session.Context.Sources.SingleAsync(s => s.Slug == changed.Slug, ct);
            Assert.Equal(old, tracked.UpdatedAt);
            tracked.Baslik = "Degisti";
            await session.Context.SaveChangesAsync(ct);
            Assert.Equal(DateTimeKind.Utc, tracked.UpdatedAt.Kind);
        }

        DateTime after = DateTime.UtcNow;
        Source readChanged = await ReadAsync(r => r.Session.Context.Sources.AsNoTracking().SingleAsync(s => s.Slug == changed.Slug, r.Ct), ct);
        Source readUntouched = await ReadAsync(r => r.Session.Context.Sources.AsNoTracking().SingleAsync(s => s.Slug == untouched.Slug, r.Ct), ct);

        Assert.Equal(DateTimeKind.Utc, readChanged.UpdatedAt.Kind);
        Assert.True(readChanged.UpdatedAt > old);
        Assert.InRange(readChanged.UpdatedAt, before.AddSeconds(-1), after.AddSeconds(1));
        Assert.Equal(old, readUntouched.UpdatedAt);
    }

    [Fact]
    public async Task Updated_at_set_explicitly_by_the_caller_is_not_overwritten()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Source source = await SaveSourceAsync(null, ct);
        DateTime explicitValue = new(2021, 5, 5, 12, 0, 0, DateTimeKind.Utc);

        await using (DbSession session = Db.OpenSession())
        {
            Source tracked = await session.Context.Sources.SingleAsync(s => s.Slug == source.Slug, ct);
            tracked.Baslik = "Degisti";
            tracked.UpdatedAt = explicitValue;
            await session.Context.SaveChangesAsync(ct);
        }

        Source read = await ReadAsync(r => r.Session.Context.Sources.AsNoTracking().SingleAsync(s => s.Slug == source.Slug, r.Ct), ct);
        Assert.Equal(explicitValue, read.UpdatedAt);
    }
}
