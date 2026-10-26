using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Releases;
using NpgsqlTypes;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class UnitConfiguration : IEntityTypeConfiguration<Unit>
{
    public void Configure(EntityTypeBuilder<Unit> b)
    {
        b.ToTable("unit", t =>
        {
            t.HasCheckConstraint("unit_role_check", "role IN ('govde','baslik','hasiye','dipnot','siir')");
            t.HasCheckConstraint("unit_content_hash_check", "content_hash ~ '^[0-9a-f]{64}$'");
            t.HasCheckConstraint("unit_check", "status = 'etkin' OR successors IS NOT NULL");
        });

        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.Role).HasAlwaysWrittenDefault("govde");
        b.Property(x => x.ParentPath).UseCollation(ConfigurationExtensions.CCollation);
        b.Property(x => x.AyahRange).HasColumnType("int4range");
        b.Property(x => x.Marks).HasColumnType("jsonb").HasAlwaysWrittenDefault("[]");
        b.Property(x => x.Sentences).HasColumnType("int4range[]");
        b.Property(x => x.Attrs).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.ContentHash).HasColumnType("char(64)");
        b.Property(x => x.Rev).HasAlwaysWrittenDefault(1);
        b.Property(x => x.MetinDurumu).HasAlwaysWrittenDefault(TextStatus.Taslak);
        b.Property(x => x.Status).HasAlwaysWrittenDefault(UnitStatus.Etkin);
        b.Property(x => x.Successors).HasColumnType("jsonb");
        b.Property(x => x.Provenance).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");

        // Uretilen arama sutunlari: EF yazmaz, yalniz okur.
        b.Property<NpgsqlTsVector>("TsvTr")
            .HasColumnName("tsv_tr")
            .HasComputedColumnSql("to_tsvector('turkish', coalesce(tr_narrow, ''))", stored: true);
        b.Property<NpgsqlTsVector>("TsvAr")
            .HasColumnName("tsv_ar")
            .HasComputedColumnSql("to_tsvector('arabic', coalesce(ar_norm, ''))", stored: true);

        b.References<Unit, Source>(x => x.SourceId);
        b.References<Unit, PipelineRun>(x => x.RunId);

        b.HasIndex(x => x.Anchor).IsUnique().HasDatabaseName("unit_anchor_key");
        b.HasIndex(x => new { x.SourceId, x.Ord }).HasDatabaseName("unit_source_ord");
        b.HasIndex(x => new { x.ParentPath, x.Ord }).HasDatabaseName("unit_parent");
        b.HasIndex(x => x.AyahRange).HasMethod("gist").HasDatabaseName("unit_ayah");
        b.HasIndex("TsvTr").HasMethod("gin").HasDatabaseName("unit_tsv_tr");
        b.HasIndex("TsvAr").HasMethod("gin").HasDatabaseName("unit_tsv_ar");
        b.UseXmin();
    }
}
