using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class QuranMarkerConfiguration : IEntityTypeConfiguration<QuranMarker>
{
    public void Configure(EntityTypeBuilder<QuranMarker> b)
    {
        b.ToTable("quran_marker", t =>
        {
            t.HasCheckConstraint("quran_marker_kind_check", "kind IN ('cuz','hizb','rub','secde')");
            t.HasCheckConstraint("quran_marker_secde_turu_check", "secde_turu IN ('recommended','obligatory')");
            t.HasCheckConstraint("quran_marker_check", "(kind = 'secde') = (secde_turu IS NOT NULL)");
        });
        b.HasKey(x => new { x.Kind, x.No });
        b.References<QuranMarker, Source>(x => x.SourceId);
        b.HasIndex(x => x.Anchor).HasDatabaseName("quran_marker_anchor");
        b.UseXmin();
    }
}
