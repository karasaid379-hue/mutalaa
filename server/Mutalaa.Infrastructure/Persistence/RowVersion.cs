using Microsoft.EntityFrameworkCore.ChangeTracking;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// Iyimser eszamanlilik belirteci yardimcisi: <c>xmin</c> sistem sutunu golge ozelliktir (Domain'e alan eklenmez).
/// Okuma yolu satirin <see cref="Get"/> degerini istemciye verir; yazma yolu istemcinin gonderdigi degeri
/// <see cref="Expect"/> ile beklenen deger yapar ve SaveChanges uyusmazlikta DbUpdateConcurrencyException atar
/// (Api bunu 409 <c>surum-uyusmazligi</c> yapar).
/// </summary>
public static class RowVersion
{
    /// <summary>Golge ozellik ve sistem sutununun adi.</summary>
    public const string Name = "xmin";

    /// <summary>Izlenen satirin okunan <c>xmin</c> degeri.</summary>
    public static uint Get(EntityEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        return (uint)entry.Property(Name).CurrentValue!;
    }

    /// <summary>Guncellemenin dayanacagi surumu belirtir: <c>xmin</c> orijinal degeri istemcinin gonderdigi deger olur.</summary>
    public static void Expect(EntityEntry entry, uint value)
    {
        ArgumentNullException.ThrowIfNull(entry);
        entry.Property(Name).OriginalValue = value;
    }
}
