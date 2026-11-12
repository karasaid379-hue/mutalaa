using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class XrefGateConfiguration : IEntityTypeConfiguration<XrefGate>
{
    public void Configure(EntityTypeBuilder<XrefGate> b)
    {
        b.ToTable("xref_gate", t =>
        {
            t.HasCheckConstraint("xref_gate_set_sinifi_check", "set_sinifi IN ('altin','silver','sentetik')");
            t.HasCheckConstraint("xref_gate_sonuc_check", "sonuc IN ('gecti','kaldi')");
            t.HasCheckConstraint("xref_gate_rapor_sha256_check", "rapor_sha256 ~ '^[0-9a-f]{64}$'");
        });
        b.HasKey(x => new { x.Tur, x.SetSinifi });
        b.Property(x => x.SetKaynaklari).HasColumnType("text[]");
        b.Property(x => x.RaporSha256).HasColumnType("char(64)");
        b.Property(x => x.OlculduAt).HasDefaultValueSql("now()");
        b.UseXmin();
    }
}
