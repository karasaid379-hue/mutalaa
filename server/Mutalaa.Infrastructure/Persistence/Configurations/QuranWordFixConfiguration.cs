using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class QuranWordFixConfiguration : IEntityTypeConfiguration<QuranWordFix>
{
    public void Configure(EntityTypeBuilder<QuranWordFix> b)
    {
        b.ToTable("quran_word_fix", t => t.HasCheckConstraint(
            "quran_word_fix_field_check",
            "field IN ('root_id','lemma_id','pos','features')"));
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).HasDefaultValueSql("uuidv7()").ValueGeneratedOnAdd();
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.HasIndex(x => new { x.Anchor, x.Field }).IsUnique().HasDatabaseName("quran_word_fix_anchor_field_key");
        b.UseXmin();
    }
}
