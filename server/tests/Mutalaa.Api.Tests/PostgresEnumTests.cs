using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Persistence;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>PostgreSQL enum etiketleri ve sirasi, packages/content-schema/enums.json ile birebir (Docker'li).</summary>
public class PostgresEnumTests(EditorialDatabase<PostgresEnumTests> fixture) : IClassFixture<EditorialDatabase<PostgresEnumTests>>
{
    private TestDatabase Db => fixture.Database;

    /// <summary>pg_enum etiketleri enumsortorder sirasiyla (tur adi, etiketler).</summary>
    private async Task<Dictionary<string, string[]>> LoadFromDatabaseAsync(CancellationToken ct)
    {
        await using NpgsqlConnection connection = await Db.OpenRawConnectionAsync(ct);
        await using NpgsqlCommand command = new(
            "SELECT t.typname::text, e.enumlabel::text FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid JOIN pg_namespace n ON n.oid = t.typnamespace "
            + "WHERE n.nspname = 'icerik' ORDER BY t.typname, e.enumsortorder",
            connection);
        await using NpgsqlDataReader reader = await command.ExecuteReaderAsync(ct);
        Dictionary<string, List<string>> grouped = new(StringComparer.Ordinal);
        while (await reader.ReadAsync(ct))
        {
            string type = reader.GetString(0);
            if (!grouped.TryGetValue(type, out List<string>? labels))
            {
                labels = [];
                grouped.Add(type, labels);
            }

            labels.Add(reader.GetString(1));
        }

        return grouped.ToDictionary(g => g.Key, g => g.Value.ToArray(), StringComparer.Ordinal);
    }

    [Fact]
    public async Task Pg_enum_labels_match_enums_json_type_by_type_in_sort_order()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Dictionary<string, string[]> json = EnumsJson.Load();
        Dictionary<string, string[]> database = await LoadFromDatabaseAsync(ct);

        Assert.Equal(11, json.Count);
        Assert.Equal(json.Keys.Order(StringComparer.Ordinal), database.Keys.Order(StringComparer.Ordinal));
        foreach ((string type, string[] labels) in json)
        {
            Assert.True(database[type].SequenceEqual(labels, StringComparer.Ordinal), $"{type}: veritabani [{string.Join(",", database[type])}] != json [{string.Join(",", labels)}]");
        }
    }

    [Fact]
    public async Task Enum_sort_order_values_are_strictly_increasing_per_type()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        long violations = await Db.ScalarAsync<long>(
            "SELECT count(*) FROM (SELECT enumtypid, enumsortorder, lag(enumsortorder) OVER (PARTITION BY enumtypid ORDER BY enumsortorder) AS previous FROM pg_enum) s WHERE previous IS NOT NULL AND enumsortorder <= previous",
            ct);

        Assert.Equal(0L, violations);
    }

    [Fact]
    public async Task Postgres_enum_definitions_in_code_match_the_database()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        Dictionary<string, string[]> database = await LoadFromDatabaseAsync(ct);

        Assert.Equal(database.Count, PostgresEnums.Definitions.Count);
        foreach (KeyValuePair<string, string[]> definition in PostgresEnums.Definitions)
        {
            Assert.True(database[definition.Key].SequenceEqual(definition.Value, StringComparer.Ordinal), definition.Key);
        }
    }

    [Fact]
    public async Task Every_enum_member_round_trips_through_the_database_in_invariant_and_tr_TR()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await RoundTripAsync(ct);
        await AsyncCultureScope.TurkishAsync(() => RoundTripAsync(ct));
    }

    /// <summary>
    /// Her enum'un her uyesi bir kez yazilir ve geri okunur: LabelNameTranslator ve PostgreSQL etiketi tum uyelerde uyusur
    /// (ic_kullanim gibi i/I iceren etiketler tr-TR'de de ayni). Islem geri alinir.
    /// </summary>
    private async Task RoundTripAsync(CancellationToken ct)
    {
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        IcerikDbContext context = session.Context;

        Source baseSource = TestData.NewSource();
        context.Add(baseSource);

        List<Source> sources = [];
        foreach (SourceKind kind in Enum.GetValues<SourceKind>())
        {
            foreach (LicenseStatus license in Enum.GetValues<LicenseStatus>())
            {
                Source source = TestData.NewSource();
                source.Tur = kind;
                source.LicenseStatus = license;
                sources.Add(source);
            }
        }

        context.AddRange(sources);
        await context.SaveChangesAsync(ct);

        List<Unit> units = [];
        int ord = 0;
        foreach (UnitKind kind in Enum.GetValues<UnitKind>())
        {
            foreach (TextStatus text in Enum.GetValues<TextStatus>())
            {
                Unit unit = TestData.NewUnit(baseSource.Slug, $"rn:sozler:soz-10:p{++ord}");
                unit.Kind = kind;
                unit.MetinDurumu = text;
                unit.Status = UnitStatus.Etkin;
                units.Add(unit);
            }
        }

        // kullanim_disi birim successors ister (unit_check).
        Unit retired = TestData.NewUnit(baseSource.Slug, $"rn:sozler:soz-10:p{++ord}");
        retired.Status = UnitStatus.KullanimDisi;
        retired.Successors = "[]";
        units.Add(retired);
        context.AddRange(units);

        List<Xref> xrefs = [];
        foreach (XrefType type in Enum.GetValues<XrefType>())
        {
            foreach (XrefOrigin origin in Enum.GetValues<XrefOrigin>())
            {
                foreach (XrefStatus status in Enum.GetValues<XrefStatus>())
                {
                    Xref xref = TestData.NewXref(src: $"rn:sozler:soz-10:p{++ord}", dst: "q:2:255", type: type);
                    xref.Origin = origin;
                    xref.Status = status;
                    xref.License = (LicenseStatus)(ord % Enum.GetValues<LicenseStatus>().Length);
                    xrefs.Add(xref);
                }
            }
        }

        context.AddRange(xrefs);

        List<Review> reviews = [];
        foreach (ReviewStatus status in Enum.GetValues<ReviewStatus>())
        {
            reviews.Add(new Review { HedefTablo = "source", HedefAnahtar = "x", Alan = "a", Eylem = "onayla", Koken = XrefOrigin.Editor, Oneren = "editor", Durum = status });
        }

        context.AddRange(reviews);

        List<Release> releases = [];
        foreach (ReleaseStatus status in Enum.GetValues<ReleaseStatus>())
        {
            foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
            {
                releases.Add(NewRelease(status, flavor, ++ord));
            }
        }

        context.AddRange(releases);
        await context.SaveChangesAsync(ct);
        context.ChangeTracker.Clear();

        // Geri okuma: izlemesiz yeni sorgular, ayni baglanti ve islem.
        Dictionary<string, Source> readSources = await context.Sources.AsNoTracking().ToDictionaryAsync(s => s.Slug, StringComparer.Ordinal, ct);
        foreach (Source source in sources)
        {
            Assert.Equal(source.Tur, readSources[source.Slug].Tur);
            Assert.Equal(source.LicenseStatus, readSources[source.Slug].LicenseStatus);
        }

        List<Unit> readUnits = await context.Units.AsNoTracking().OrderBy(u => u.Id).ToListAsync(ct);
        Assert.Equal(units.Select(u => (u.Anchor, u.Kind, u.MetinDurumu, u.Status)), readUnits.Select(u => (u.Anchor, u.Kind, u.MetinDurumu, u.Status)));

        Dictionary<string, Xref> readXrefs = (await context.Xrefs.AsNoTracking().ToListAsync(ct)).ToDictionary(x => x.SrcAnchor.ToString(), StringComparer.Ordinal);
        foreach (Xref xref in xrefs)
        {
            Xref read = readXrefs[xref.SrcAnchor.ToString()];
            Assert.Equal((xref.Type, xref.Origin, xref.Status, xref.License), (read.Type, read.Origin, read.Status, read.License));
        }

        Assert.Equal(reviews.Select(r => r.Durum), (await context.Reviews.AsNoTracking().OrderBy(r => r.Id).ToListAsync(ct)).Select(r => r.Durum));
        Assert.Equal(
            releases.Select(r => (r.Durum, r.Derleme)),
            (await context.Releases.AsNoTracking().OrderBy(r => r.Id).ToListAsync(ct)).Select(r => (r.Durum, r.Derleme)));
    }

    private static Release NewRelease(ReleaseStatus status, BuildFlavor flavor, int n) => new()
    {
        Surum = $"test-{n}",
        Derleme = flavor,
        Durum = status,
        DataVersion = "test",
        Olusturan = "test-editor",
    };
}
