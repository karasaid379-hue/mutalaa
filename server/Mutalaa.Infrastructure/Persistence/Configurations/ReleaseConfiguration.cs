using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Releases;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class ReleaseConfiguration : IEntityTypeConfiguration<Release>
{
    public void Configure(EntityTypeBuilder<Release> b)
    {
        b.ToTable("release", t => t.HasCheckConstraint("release_talep_check", "talep IN ('yayin','terfi','geri_alma')"));
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.Durum).HasAlwaysWrittenDefault(ReleaseStatus.Hazirlaniyor);
        b.Property(x => x.Manifest).HasColumnType("jsonb");
        b.Property(x => x.KapiRaporu).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.Ozetler).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.Property(x => x.Talep).HasAlwaysWrittenDefault(ReleaseRequests.Yayin);
        b.Property(x => x.Paketler).HasColumnType("text[]");

        // Terfide ve geri almada kaynak yayin; ad PostgresNamePolicy ile release_kaynak_release_id_fkey olur.
        b.References<Release, Release>(x => x.KaynakReleaseId);

        // Kismi tekil dizin (K-46 madde 3): basarisiz deneme surum numarasini yakmaz.
        b.HasIndex(x => new { x.Surum, x.Derleme })
            .IsUnique()
            .HasDatabaseName("release_surum_derleme_key")
            .HasFilter("durum <> 'basarisiz'::icerik.surum_durumu");
        b.UseXmin();
    }
}
