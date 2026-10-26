using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class LemmaGlossConfiguration : IEntityTypeConfiguration<LemmaGloss>
{
    public void Configure(EntityTypeBuilder<LemmaGloss> b)
    {
        b.ToTable("lemma_gloss");
        b.HasKey(x => x.LemmaId);
        b.Property(x => x.LemmaId).ValueGeneratedNever();
        b.Property(x => x.KuranAnlamlari).HasColumnType("jsonb").HasAlwaysWrittenDefault("[]");
        b.Property(x => x.YalnizcaEtimolojik).HasAlwaysWrittenDefault(false);
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.Property(x => x.ContentHash).HasColumnType("char(64)");
        b.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
        b.HasOne<Lemma>().WithOne().HasForeignKey<LemmaGloss>(x => x.LemmaId).OnDelete(DeleteBehavior.NoAction);
        b.UseXmin();
    }
}
