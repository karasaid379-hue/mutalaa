using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Releases;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class PipelineRunConfiguration : IEntityTypeConfiguration<PipelineRun>
{
    public void Configure(EntityTypeBuilder<PipelineRun> b)
    {
        b.ToTable("pipeline_run", t => t.HasCheckConstraint(
            "pipeline_run_durum_check",
            "durum IN ('calisiyor','basarili','basarisiz')"));
        b.HasKey(x => x.RunId);
        b.Property(x => x.RunId).ValueGeneratedNever();
        b.Property(x => x.ParmakIzi).HasColumnType("char(64)");
        b.Property(x => x.Manifest).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.UseXmin();
    }
}
