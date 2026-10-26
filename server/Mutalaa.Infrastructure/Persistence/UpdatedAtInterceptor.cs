using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// updated_at sutunu olan varliklarda (Source, Unit, LemmaGloss ...) degistirilen satirlara UTC zaman yazar.
/// Cagiran updated_at'i kendisi degistirdiyse dokunmaz. timestamptz sutunlarina yalniz UTC (Kind=Utc) deger yazilir.
/// </summary>
public sealed class UpdatedAtInterceptor(TimeProvider? timeProvider = null) : SaveChangesInterceptor
{
    private const string PropertyName = "UpdatedAt";

    private readonly TimeProvider _time = timeProvider ?? TimeProvider.System;

    public override InterceptionResult<int> SavingChanges(DbContextEventData eventData, InterceptionResult<int> result)
    {
        Stamp(eventData.Context);
        return base.SavingChanges(eventData, result);
    }

    public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
        DbContextEventData eventData,
        InterceptionResult<int> result,
        CancellationToken cancellationToken = default)
    {
        Stamp(eventData.Context);
        return base.SavingChangesAsync(eventData, result, cancellationToken);
    }

    /// <summary>Degistirilen (Modified) satirlarin updated_at degerini yazar; SaveChanges oncesi cagrilir.</summary>
    public void Stamp(DbContext? context)
    {
        if (context is null)
        {
            return;
        }

        DateTime now = _time.GetUtcNow().UtcDateTime;
        foreach (EntityEntry entry in context.ChangeTracker.Entries())
        {
            if (entry.State != EntityState.Modified)
            {
                continue;
            }

            Microsoft.EntityFrameworkCore.Metadata.IProperty? property = entry.Metadata.FindProperty(PropertyName);
            if (property is null || property.ClrType != typeof(DateTime))
            {
                continue;
            }

            PropertyEntry updatedAt = entry.Property(PropertyName);
            if (!updatedAt.IsModified)
            {
                updatedAt.CurrentValue = now;
                updatedAt.IsModified = true;
            }
        }
    }
}
