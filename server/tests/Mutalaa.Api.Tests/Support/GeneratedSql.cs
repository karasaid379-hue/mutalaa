using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Migrations.Operations;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Veritabani ve dotnet ef gerektirmeden: modelden bos veritabanina ilk gocun SQL'ini (model farklari) bellekte uretir.
/// Gercek goc dosyasi A07.4'te dotnet ef ile uretilir; bu, ayni model farkinin SQL karsiligidir.
/// </summary>
internal static class GeneratedSql
{
    private static readonly Lazy<IReadOnlyList<string>> Commands = new(Generate);

    /// <summary>Uretilen komutlarin metinleri (bildirim sirasiyla).</summary>
    public static IReadOnlyList<string> All => Commands.Value;

    private static IReadOnlyList<string> Generate()
    {
        using ServiceProvider provider = ModelFactory.BuildServices();
        using IServiceScope scope = provider.CreateScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();

        IModel model = context.GetService<IDesignTimeModel>().Model;
        IReadOnlyList<MigrationOperation> operations = context.GetService<IMigrationsModelDiffer>()
            .GetDifferences(source: null, target: model.GetRelationalModel());
        return [.. context.GetService<IMigrationsSqlGenerator>().Generate(operations, model).Select(c => c.CommandText)];
    }
}
