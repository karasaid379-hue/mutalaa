using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Persistence.Configurations;

internal sealed class LugatMaddeConfiguration : IEntityTypeConfiguration<LugatMadde>
{
    public void Configure(EntityTypeBuilder<LugatMadde> b)
    {
        b.ToTable("lugat_madde", t =>
        {
            t.HasCheckConstraint("lugat_madde_origin_check", "origin IN ('hat','editor','kaynak')");
            t.HasCheckConstraint("lugat_madde_anlam_no_check", "anlam_no >= 1");
            t.HasCheckConstraint("lugat_madde_duzey_check", "duzey BETWEEN 1 AND 4");
            t.HasCheckConstraint("lugat_madde_content_hash_check", "content_hash ~ '^[0-9a-f]{64}$'");

            // K-51 madde 10: onayli maddenin tanimi dolu olur; aday bos tanimla acilir.
            t.HasCheckConstraint("lugat_madde_onayli_tanim_check", "status <> 'onayli' OR (tanim_tr IS NOT NULL AND btrim(tanim_tr) <> '')");
        });
        b.HasKey(x => x.Id);
        b.Property(x => x.Id).UseIdentityAlwaysColumn();
        b.Property(x => x.AnlamNo).HasAlwaysWrittenDefault((short)1);
        b.Property(x => x.Kaynaklar).HasColumnType("jsonb").HasAlwaysWrittenDefault("{}");
        b.Property(x => x.Status).HasAlwaysWrittenDefault(XrefStatus.Aday);
        b.Property(x => x.Version).HasAlwaysWrittenDefault("1");
        b.Property(x => x.ContentHash).HasColumnType("char(64)");
        b.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
        b.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
        b.References<LugatMadde, Source>(x => x.SourceId);
        b.References<LugatMadde, Root>(x => x.ArKokId);
        b.HasAlternateKey(x => new { x.SourceId, x.Basliksoz, x.AnlamNo }).HasName("lugat_madde_source_id_basliksoz_anlam_no_key");
        b.UseXmin();
    }
}
