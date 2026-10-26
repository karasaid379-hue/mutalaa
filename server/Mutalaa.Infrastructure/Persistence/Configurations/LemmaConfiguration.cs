using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class LemmaConfiguration : IEntityTypeConfiguration<Lemma>
{
    public void Configure(EntityTypeBuilder<Lemma> b)
    {
        b.ToTable("lemma", t => t.HasCheckConstraint("lemma_lang_check", "lang IN ('ar','tr')"));
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).ValueGeneratedNever();
        b.Property(x => x.Occurrences).HasAlwaysWrittenDefault(0);
        b.Property(x => x.EtymologicalOnly).HasAlwaysWrittenDefault(false);
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.References<Lemma, Root>(x => x.RootId);
        b.References<Lemma, Lemma>(x => x.ArLemmaId);
        b.References<Lemma, Source>(x => x.SourceId);
        b.UseXmin();
    }
}
