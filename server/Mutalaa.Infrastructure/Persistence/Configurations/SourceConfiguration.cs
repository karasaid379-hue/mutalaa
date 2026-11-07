using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class SourceConfiguration : IEntityTypeConfiguration<Source>
{
    public void Configure(EntityTypeBuilder<Source> b)
    {
        b.ToTable("source");

        b.HasKey(x => x.Slug);
        b.Property(x => x.Slug).UseCollation(ConfigurationExtensions.CCollation);
        b.Property(x => x.DosyaSha256).HasColumnType("char(64)");
        b.Property(x => x.BaskiBilgisi).HasColumnType("jsonb");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
        b.UseXmin();
    }
}
