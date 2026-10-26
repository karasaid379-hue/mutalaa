using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// K-37 madde 4: icerik semasinda anahtar, yabanci anahtar ve tekil dizin adlari PostgreSQL varsayilaniyla aynidir
/// ({tablo}_pkey, {tablo}_{sutunlar}_fkey, {tablo}_{sutunlar}_key); EFCore.NamingConventions'in pk_/fk_/ix_ onekleri kullanilmaz.
/// Tek donguyle verilir; adi acikca verilmemis bir dizin modeli kurarken hata verir, boylece unutulamaz.
/// Kimlik semasi bu politikanin disindadir.
/// </summary>
internal static class PostgresNamePolicy
{
    private const int MaxIdentifierLength = 63;

    public static void Apply(ModelBuilder modelBuilder)
    {
        IMutableModel model = modelBuilder.Model;
        foreach (IMutableEntityType entityType in model.GetEntityTypes())
        {
            string? table = entityType.GetTableName();
            string? schema = entityType.GetSchema() ?? model.GetDefaultSchema();
            if (table is null || !IsDomainEntity(entityType) || !string.Equals(schema, PostgresEnums.Schema, StringComparison.Ordinal))
            {
                continue;
            }

            IMutableKey primaryKey = entityType.FindPrimaryKey()
                ?? throw new InvalidOperationException($"{table} ({entityType.DisplayName()}, sahipli={entityType.IsOwned()}, json={entityType.IsMappedToJson()}): birincil anahtar yok.");
            primaryKey.SetName(Checked($"{table}_pkey"));

            foreach (IMutableForeignKey foreignKey in entityType.GetForeignKeys())
            {
                string columns = string.Join('_', foreignKey.Properties.Select(p => p.GetColumnName()));
                foreignKey.SetConstraintName(Checked($"{table}_{columns}_fkey"));
            }

            foreach (IMutableIndex index in entityType.GetIndexes())
            {
                string name = index.GetDatabaseName() ?? string.Empty;
                if (name.StartsWith("ix_", StringComparison.Ordinal) || name.Length == 0)
                {
                    string columns = string.Join(',', index.Properties.Select(p => p.GetColumnName()));
                    throw new InvalidOperationException(
                        $"{table}({columns}): dizin adi acikca verilmemis (HasDatabaseName); icerik semasinda ix_ oneki kullanilmaz.");
                }

                Checked(name);
            }
        }
    }

    /// <summary>
    /// Yalniz Mutalaa.Domain varliklari. Identity, modeli kurarken gecici varliklar ekleyip sonlandirmada kaldirir
    /// (ornegin IdentityPasskeyData: anahtarsiz, tablo adi alir); bunlara dokunulmaz.
    /// </summary>
    private static bool IsDomainEntity(IMutableEntityType entityType) =>
        entityType.ClrType.Namespace?.StartsWith("Mutalaa.Domain.", StringComparison.Ordinal) == true;

    private static string Checked(string name) =>
        name.Length <= MaxIdentifierLength
            ? name
            : throw new InvalidOperationException($"'{name}' PostgreSQL ad sinirini ({MaxIdentifierLength}) asiyor.");
}
