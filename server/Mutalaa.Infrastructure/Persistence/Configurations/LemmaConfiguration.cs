using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class LemmaConfiguration : IEntityTypeConfiguration<Lemma>
{
    public void Configure(EntityTypeBuilder<Lemma> b)
    {
        b.ToTable("lemma", t =>
        {
            t.HasCheckConstraint("lemma_lang_check", "lang IN ('ar','tr')");
            t.HasCheckConstraint("lemma_onay_yolu_check", "onay_yolu IS NULL OR onay_yolu IN ('editor','otomatik')");
            t.HasCheckConstraint("lemma_tr_onayli_onay_yolu_check", "NOT (lang = 'tr' AND status = 'onayli') OR onay_yolu IS NOT NULL");
            t.HasCheckConstraint("lemma_otomatik_kanit_check", "onay_yolu IS DISTINCT FROM 'otomatik' OR (kanit IS NOT NULL AND jsonb_typeof(kanit) = 'object')");
        });
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).ValueGeneratedNever();
        b.Property(x => x.Occurrences).HasAlwaysWrittenDefault(0);
        b.Property(x => x.EtymologicalOnly).HasAlwaysWrittenDefault(false);
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.References<Lemma, Root>(x => x.RootId);
        b.References<Lemma, Lemma>(x => x.ArLemmaId);
        b.References<Lemma, Source>(x => x.SourceId);
        b.HasIndex(x => x.QacRef).IsUnique().HasFilter("lang = 'ar'").HasDatabaseName("lemma_qac_ref_key");
        b.Property(x => x.Kanit).HasColumnType("jsonb");
        b.HasIndex(x => new { x.Lang, x.TextClean }).IsUnique().HasFilter("lang = 'tr'").HasDatabaseName("lemma_tr_text_clean_key");
        b.UseXmin();
    }
}
