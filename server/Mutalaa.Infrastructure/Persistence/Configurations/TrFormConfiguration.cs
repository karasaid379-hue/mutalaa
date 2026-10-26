using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class TrFormConfiguration : IEntityTypeConfiguration<TrForm>
{
    public void Configure(EntityTypeBuilder<TrForm> b)
    {
        b.ToTable("tr_form");
        b.HasKey(x => new { x.KeyNarrow, x.TrLemmaId });
        b.Property(x => x.Freq).HasAlwaysWrittenDefault(0);
        b.References<TrForm, Lemma>(x => x.TrLemmaId);
        b.HasIndex(x => x.KeyWide).HasDatabaseName("tr_form_wide");
        b.UseXmin();
    }
}
