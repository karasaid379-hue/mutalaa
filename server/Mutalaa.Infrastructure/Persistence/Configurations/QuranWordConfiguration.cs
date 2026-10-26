using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class QuranWordConfiguration : IEntityTypeConfiguration<QuranWord>
{
    public void Configure(EntityTypeBuilder<QuranWord> b)
    {
        b.ToTable("quran_word", t => t.HasCheckConstraint("quran_word_check", "char_start < char_end"));
        b.HasKey(x => x.Anchor);
        b.Property(x => x.Features).HasColumnType("jsonb");
        b.References<QuranWord, Root>(x => x.RootId);
        b.References<QuranWord, Lemma>(x => x.LemmaId);
        b.References<QuranWord, Source>(x => x.SourceId);
        b.References<QuranWord, Source>(x => x.MorphSource);
        b.HasIndex(x => new { x.Surah, x.Ayah, x.Word }).IsUnique().HasDatabaseName("quran_word_surah_ayah_word_key");
        b.HasIndex(x => x.RootId).HasDatabaseName("quran_word_root");
        b.HasIndex(x => x.LemmaId).HasDatabaseName("quran_word_lemma");
        b.HasIndex(x => new { x.AyahIndex, x.Word }).HasDatabaseName("quran_word_ayah");
        b.UseXmin();
    }
}
