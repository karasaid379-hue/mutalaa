using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class LemmaDalgaConfiguration : IEntityTypeConfiguration<LemmaDalga>
{
    public void Configure(EntityTypeBuilder<LemmaDalga> b)
    {
        b.ToTable("lemma_dalga", t => t.HasCheckConstraint("lemma_dalga_dalga_check", "dalga BETWEEN 0 AND 4"));
        b.HasKey(x => x.LemmaId);
        b.Property(x => x.LemmaId).ValueGeneratedNever();
        b.HasOne<Lemma>().WithOne().HasForeignKey<LemmaDalga>(x => x.LemmaId).OnDelete(DeleteBehavior.NoAction);
        b.HasIndex(x => new { x.Dalga, x.Sira }).HasDatabaseName("lemma_dalga_dalga_sira");
        b.UseXmin();
    }
}
