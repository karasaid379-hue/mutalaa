using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class AudioTimingConfiguration : IEntityTypeConfiguration<AudioTiming>
{
    public void Configure(EntityTypeBuilder<AudioTiming> b)
    {
        b.ToTable("audio_timing", t => t.HasCheckConstraint("audio_timing_check", "start_ms < end_ms"));
        b.HasKey(x => new { x.SourceId, x.Anchor });
        b.Property(x => x.FileSha256).HasColumnType("char(64)");
        b.Property(x => x.Words).HasColumnType("jsonb");
        b.References<AudioTiming, Source>(x => x.SourceId);
        b.UseXmin();
    }
}
