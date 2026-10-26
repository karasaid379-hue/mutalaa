using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

/// <summary>Yapilandirma siniflarinin ortak yardimcilari.</summary>
internal static class ConfigurationExtensions
{
    /// <summary>Capa ve sirali metin sutunlarinda bayt siralamasi (Editoryal veritabani 1: COLLATE "C").</summary>
    public const string CCollation = "C";

    /// <summary>
    /// Eszamanlilik belirteci: gercek bir sutun olusturmayan xmin sistem sutunu (golge ozellik; Domain'e alan eklenmez).
    /// </summary>
    public static void UseXmin<T>(this EntityTypeBuilder<T> builder)
        where T : class =>
        builder.Property<uint>("xmin").HasColumnName("xmin").HasColumnType("xid").IsRowVersion();

    /// <summary>
    /// DDL'deki DEFAULT'u korur ama EF'in degeri her zaman kendisinin yazmasini saglar: EF bir alanin CLR varsayilanini
    /// "atanmamis" sayar; ValueGeneratedNever bunu kapatir (plan karari 7).
    /// </summary>
    public static PropertyBuilder<TProperty> HasAlwaysWrittenDefault<TProperty>(this PropertyBuilder<TProperty> property, TProperty value) =>
        property.HasDefaultValue(value).ValueGeneratedNever();

    /// <summary>Tek yabanci anahtar; icerik semasinda NoAction. Ad model sonlandirmada verilir (PostgresNamePolicy).</summary>
    public static void References<TDependent, TPrincipal>(
        this EntityTypeBuilder<TDependent> builder,
        Expression<Func<TDependent, object?>> foreignKey)
        where TDependent : class
        where TPrincipal : class =>
        builder.HasOne<TPrincipal>().WithMany().HasForeignKey(foreignKey).OnDelete(DeleteBehavior.NoAction);
}
