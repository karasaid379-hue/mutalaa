using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class AyahBoxConfiguration : IEntityTypeConfiguration<AyahBox>
{
    public void Configure(EntityTypeBuilder<AyahBox> b)
    {
        b.ToTable("ayah_box", t => t.HasCheckConstraint("ayah_box_check", "w > 0 AND h > 0"));
        b.HasKey(x => new { x.SourceId, x.Page, x.Anchor, x.Seq });
        b.References<AyahBox, Source>(x => x.SourceId);
        b.UseXmin();
    }
}
