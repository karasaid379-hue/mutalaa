using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class HadithLocationConfiguration : IEntityTypeConfiguration<HadithLocation>
{
    public void Configure(EntityTypeBuilder<HadithLocation> b)
    {
        b.ToTable("hadith_location");
        b.HasKey(x => x.Anchor);
        b.UseXmin();
    }
}
