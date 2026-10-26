using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class TrRootIndexConfiguration : IEntityTypeConfiguration<TrRootIndex>
{
    public void Configure(EntityTypeBuilder<TrRootIndex> b)
    {
        b.ToTable("tr_root_index", t => t.HasCheckConstraint("tr_root_index_check", "span_start < span_end"));
        b.HasKey(x => new { x.Anchor, x.SpanStart });
        b.Property(x => x.EtymologicalOnly).HasAlwaysWrittenDefault(false);
        b.References<TrRootIndex, Root>(x => x.RootId);
        b.References<TrRootIndex, Lemma>(x => x.TrLemmaId);
        b.HasIndex(x => new { x.RootId, x.Anchor }).HasDatabaseName("tr_root_index_root");
        b.UseXmin();
    }
}
