using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

/// <summary>
/// xref_natural_key (UNIQUE NULLS NOT DISTINCT (type, src_anchor, src_span, dst_anchor, dst_span)) EF ile ifade edilemez;
/// ilk goce ham SQL olarak eklenir (A07.4). Burada o kolonlar icin tekil dizin ACILMAZ.
/// </summary>
internal sealed class XrefConfiguration : IEntityTypeConfiguration<Xref>
{
    public void Configure(EntityTypeBuilder<Xref> b)
    {
        b.ToTable("xref", t =>
        {
            t.HasCheckConstraint("xref_score_check", "score BETWEEN 0 AND 1");
            t.HasCheckConstraint("xref_confidence_check", "confidence BETWEEN 0 AND 1");
        });
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).HasDefaultValueSql("uuidv7()").ValueGeneratedOnAdd();
        b.Property(x => x.SrcSpan).HasColumnType("int4range");
        b.Property(x => x.DstSpan).HasColumnType("int4range");
        b.Property(x => x.Evidence).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.Property(x => x.VotesUp).HasAlwaysWrittenDefault(0);
        b.Property(x => x.VotesDown).HasAlwaysWrittenDefault(0);
        b.HasIndex(x => new { x.SrcAnchor, x.Type }).HasDatabaseName("xref_src");
        b.HasIndex(x => new { x.DstAnchor, x.Type }).HasDatabaseName("xref_dst");
        b.HasIndex(x => new { x.Type, x.Confidence })
            .IsDescending(false, true)
            .HasFilter("status = 'aday'")
            .HasDatabaseName("xref_queue");
        b.UseXmin();
    }
}
