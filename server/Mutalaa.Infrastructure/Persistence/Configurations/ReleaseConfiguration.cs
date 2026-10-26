using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Releases;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class ReleaseConfiguration : IEntityTypeConfiguration<Release>
{
    public void Configure(EntityTypeBuilder<Release> b)
    {
        b.ToTable("release");
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.Durum).HasAlwaysWrittenDefault(ReleaseStatus.Hazirlaniyor);
        b.Property(x => x.Manifest).HasColumnType("jsonb");
        b.Property(x => x.KapiRaporu).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.KaynakDurumu).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.Ozetler).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.HasIndex(x => new { x.Surum, x.Derleme }).IsUnique().HasDatabaseName("release_surum_derleme_key");
        b.UseXmin();
    }
}
