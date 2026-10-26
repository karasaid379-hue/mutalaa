using System.Globalization;
using Microsoft.EntityFrameworkCore;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// IcerikDbContext secenekleri icin tek yol: Api, Yayinlayici, tasarim zamani ve testler bunu kullanir.
/// EnableSensitiveDataLogging hicbir yerde acilmaz.
/// </summary>
public static class IcerikDbContextOptions
{
    public const string MigrationsHistoryTable = "__EFMigrationsHistory";

    /// <summary>
    /// Baglanti dizesi null olabilir (goc uretimi ve model testleri baglanti istemez). Baglanti dizesi dogrudan UseNpgsql'e verilir;
    /// sonradan verilirse enum eslemesi kaybolur.
    /// </summary>
    public static DbContextOptionsBuilder Configure(DbContextOptionsBuilder builder, string? connectionString)
    {
        ArgumentNullException.ThrowIfNull(builder);
        builder.UseNpgsql(connectionString, o =>
        {
            o.SetPostgresVersion(18, 0);
            o.MigrationsHistoryTable(MigrationsHistoryTable, PostgresEnums.Schema);
            PostgresEnums.MapAll(o);
        });
        builder.UseSnakeCaseNamingConvention(CultureInfo.InvariantCulture);
        return builder;
    }
}
