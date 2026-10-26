using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class SurahAliasConfiguration : IEntityTypeConfiguration<SurahAlias>
{
    public void Configure(EntityTypeBuilder<SurahAlias> b)
    {
        b.ToTable("surah_alias", t =>
        {
            t.HasCheckConstraint("surah_alias_surah_no_check", "surah_no BETWEEN 1 AND 114");
            t.HasCheckConstraint("surah_alias_kind_check", "kind IN ('kanonik','yazim','arapca','diger_ad')");
        });
        b.HasKey(x => new { x.SurahNo, x.Alias });
        b.Property(x => x.Risky).HasAlwaysWrittenDefault(false);
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.UseXmin();
    }
}
