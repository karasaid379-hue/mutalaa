using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class HadithNumberMapConfiguration : IEntityTypeConfiguration<HadithNumberMap>
{
    public void Configure(EntityTypeBuilder<HadithNumberMap> b)
    {
        b.ToTable("hadith_number_map");
        b.HasKey(x => new { x.Collection, x.System, x.Number });
        b.UseXmin();
    }
}
