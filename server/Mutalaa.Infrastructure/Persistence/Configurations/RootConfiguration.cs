using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class RootConfiguration : IEntityTypeConfiguration<Root>
{
    public void Configure(EntityTypeBuilder<Root> b)
    {
        b.ToTable("root");
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).ValueGeneratedNever();
        b.Property(x => x.Occurrences).HasAlwaysWrittenDefault(0);
        b.Property(x => x.AyahCount).HasAlwaysWrittenDefault(0);
        b.References<Root, Source>(x => x.SourceId);
        b.HasIndex(x => x.Letters).IsUnique().HasDatabaseName("root_letters_key");
        b.UseXmin();
    }
}
