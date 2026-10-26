using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class PageMapConfiguration : IEntityTypeConfiguration<PageMap>
{
    public void Configure(EntityTypeBuilder<PageMap> b)
    {
        b.ToTable("page_map", t => t.HasCheckConstraint(
            "page_map_line_type_check",
            "line_type IN ('ayet','sure_adi','besmele')"));
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.Centered).HasAlwaysWrittenDefault(false);
        b.Property(x => x.Glyphs).HasColumnType("jsonb");
        b.References<PageMap, Source>(x => x.SourceId);

        // DDL'deki UNIQUE NULLS NOT DISTINCT kisiti EF'te NULLS NOT DISTINCT tekil dizin olarak uretilir.
        b.HasIndex(x => new { x.SourceId, x.Volume, x.Page, x.Line })
            .IsUnique()
            .AreNullsDistinct(false)
            .HasDatabaseName("page_map_source_id_volume_page_line_key");
        b.HasIndex(x => x.StartAnchor).HasDatabaseName("page_map_start");
        b.UseXmin();
    }
}
