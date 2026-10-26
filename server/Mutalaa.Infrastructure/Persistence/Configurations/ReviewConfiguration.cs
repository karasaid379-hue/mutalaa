using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class ReviewConfiguration : IEntityTypeConfiguration<Review>
{
    public void Configure(EntityTypeBuilder<Review> b)
    {
        b.ToTable("review", t =>
        {
            t.HasCheckConstraint(
                "review_hedef_tablo_check",
                "hedef_tablo IN ('source','unit','quran_word_fix','lemma','lemma_gloss','root','tr_root_index','tr_form','surah_alias','xref','page_map','ayah_box','audio_timing')");

            // K-37: G-YZ kaydi. yz_modeli ile yz_kaydi ya ikisi birden bos ya da ikisi birden dolu; doluysa uc anahtarli nesne.
            t.HasCheckConstraint(
                "review_yz_kaydi_check",
                "(yz_modeli IS NULL AND yz_kaydi IS NULL) "
                + "OR (yz_modeli IS NOT NULL AND yz_kaydi IS NOT NULL AND jsonb_typeof(yz_kaydi) = 'object' "
                + "AND yz_kaydi ?& ARRAY['prompt_id','prompt_sha256','input_sha256'] "
                + "AND coalesce(yz_kaydi->>'prompt_sha256','') ~ '^[0-9a-f]{64}$' "
                + "AND coalesce(yz_kaydi->>'input_sha256','') ~ '^[0-9a-f]{64}$')");
        });
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.Onceki).HasColumnType("jsonb");
        b.Property(x => x.Onerilen).HasColumnType("jsonb");
        b.Property(x => x.Durum).HasAlwaysWrittenDefault(ReviewStatus.Acik);
        b.Property(x => x.YzKaydi).HasColumnType("jsonb");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.References<Review, Xref>(x => x.XrefId);
        b.HasIndex(x => new { x.HedefTablo, x.CreatedAt }).HasFilter("durum = 'acik'").HasDatabaseName("review_queue");
        b.HasIndex(x => x.XrefId).HasFilter("xref_id IS NOT NULL").HasDatabaseName("review_xref");
        b.UseXmin();
    }
}
