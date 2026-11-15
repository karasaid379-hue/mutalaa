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
            t.HasCheckConstraint(
                "xref_gate_alt_tur_check",
                "alt_tur IN ('','sozluksel','alim','tr_lemma','xref') AND ((tur = 'benzer_ayet' AND alt_tur IN ('sozluksel','alim')) OR (tur = 'kok' AND alt_tur IN ('tr_lemma','xref')) OR (tur NOT IN ('benzer_ayet','kok') AND alt_tur = ''))");
        });
        b.HasKey(x => new { x.Tur, x.AltTur, x.SetSinifi });
        b.Property(x => x.SetKaynaklari).HasColumnType("text[]");
        b.Property(x => x.RaporSha256).HasColumnType("char(64)");
        b.Property(x => x.OlculduAt).HasDefaultValueSql("now()");
        b.UseXmin();
    }
}
