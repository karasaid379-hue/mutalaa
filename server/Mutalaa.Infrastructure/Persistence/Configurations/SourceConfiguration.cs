using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class SourceConfiguration : IEntityTypeConfiguration<Source>
{
    public void Configure(EntityTypeBuilder<Source> b)
    {
        b.ToTable("source", t => t.HasCheckConstraint(
            "source_check",
            "kurul_onay IS NULL OR (kurul_onay ?& ARRAY['onay_no','onayli_surum'] AND kurul_onay_tarihi IS NOT NULL AND kurul_onay_ozeti IS NOT NULL)"));

        b.HasKey(x => x.Slug);
        b.Property(x => x.Slug).UseCollation(ConfigurationExtensions.CCollation);
        b.Property(x => x.DosyaSha256).HasColumnType("char(64)");
        b.Property(x => x.BaskiBilgisi).HasColumnType("jsonb");
        b.Property(x => x.LicenseStatus).HasAlwaysWrittenDefault(LicenseStatus.Bekliyor);
        b.Property(x => x.LisansSha256).HasColumnType("char(64)");
        b.Property(x => x.Kisitlar).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.EmbedOk).HasAlwaysWrittenDefault(false);
        b.Property(x => x.KurulGerekli).HasAlwaysWrittenDefault(false);
        b.Property(x => x.KurulOnay).HasColumnType("jsonb");
        b.Property(x => x.KurulOnayOzeti).HasColumnType("char(64)");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
        b.UseXmin();
    }
}
