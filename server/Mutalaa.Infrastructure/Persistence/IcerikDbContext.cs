using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Conventions;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence.Converters;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// Editoryal veritabani baglami (Editoryal veritabani 12). Icerik tablolari <c>icerik</c>, Identity tablolari <c>kimlik</c> semasindadir.
/// Secenekler IcerikDbContextOptions.Configure ile kurulur.
/// </summary>
public sealed class IcerikDbContext(DbContextOptions<IcerikDbContext> options)
    : IdentityDbContext<EditorUser, IdentityRole, string>(options)
{
    public const string ContentSchema = PostgresEnums.Schema;
    public const string IdentitySchema = "kimlik";

    public DbSet<Source> Sources => Set<Source>();

    public DbSet<Unit> Units => Set<Unit>();

    public DbSet<Root> Roots => Set<Root>();

    public DbSet<Lemma> Lemmas => Set<Lemma>();

    public DbSet<LemmaGloss> LemmaGlosses => Set<LemmaGloss>();

    public DbSet<QuranWord> QuranWords => Set<QuranWord>();

    public DbSet<QuranWordFix> QuranWordFixes => Set<QuranWordFix>();

    public DbSet<TrRootIndex> TrRootIndexes => Set<TrRootIndex>();

    public DbSet<TrForm> TrForms => Set<TrForm>();

    public DbSet<SurahAlias> SurahAliases => Set<SurahAlias>();

    public DbSet<Xref> Xrefs => Set<Xref>();

    public DbSet<Review> Reviews => Set<Review>();

    public DbSet<PageMap> PageMaps => Set<PageMap>();

    public DbSet<AyahBox> AyahBoxes => Set<AyahBox>();

    public DbSet<AudioTiming> AudioTimings => Set<AudioTiming>();

    public DbSet<HadithNumberMap> HadithNumberMaps => Set<HadithNumberMap>();

    public DbSet<HadithLocation> HadithLocations => Set<HadithLocation>();

    public DbSet<Release> Releases => Set<Release>();

    public DbSet<PipelineRun> PipelineRuns => Set<PipelineRun>();

    protected override void ConfigureConventions(ModelConfigurationBuilder configurationBuilder)
    {
        ArgumentNullException.ThrowIfNull(configurationBuilder);
        base.ConfigureConventions(configurationBuilder);

        // Her capa sutunu donusturucu ve bayt siralamasi alir; bir sutun unutulamaz.
        configurationBuilder.Properties<AnchorRef>()
            .HaveConversion<AnchorRefConverter, AnchorRefComparer>()
            .UseCollation("C");
        configurationBuilder.Properties<AnchorSpan>().HaveConversion<AnchorSpanRangeConverter>();
        configurationBuilder.Properties<AnchorSpan[]>().HaveConversion<AnchorSpanArrayConverter, AnchorSpanArrayComparer>();

        // Belgede olmayan yabanci anahtar dizinleri acilmaz (K-37 madde 5).
        configurationBuilder.Conventions.Remove(typeof(ForeignKeyIndexConvention));
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        ArgumentNullException.ThrowIfNull(modelBuilder);
        base.OnModelCreating(modelBuilder);

        modelBuilder.HasDefaultSchema(ContentSchema);
        PostgresEnums.AddToModel(modelBuilder);
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(IcerikDbContext).Assembly);
        ConfigureIdentityTables(modelBuilder);
        PostgresNamePolicy.Apply(modelBuilder);
    }

    private static void ConfigureIdentityTables(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<EditorUser>(b =>
        {
            b.ToTable("users", IdentitySchema);
            b.HasIndex(u => u.NormalizedUserName).HasDatabaseName("ix_users_normalized_user_name");
            b.HasIndex(u => u.NormalizedEmail).HasDatabaseName("ix_users_normalized_email");
        });
        modelBuilder.Entity<IdentityRole>(b =>
        {
            b.ToTable("roles", IdentitySchema);
            b.HasIndex(r => r.NormalizedName).HasDatabaseName("ix_roles_normalized_name");
        });
        modelBuilder.Entity<IdentityUserRole<string>>(b =>
        {
            b.ToTable("user_roles", IdentitySchema);
            b.HasIndex(x => x.RoleId).HasDatabaseName("ix_user_roles_role_id");
        });
        modelBuilder.Entity<IdentityUserClaim<string>>(b =>
        {
            b.ToTable("user_claims", IdentitySchema);
            b.HasIndex(x => x.UserId).HasDatabaseName("ix_user_claims_user_id");
        });
        modelBuilder.Entity<IdentityUserLogin<string>>(b =>
        {
            b.ToTable("user_logins", IdentitySchema);
            b.HasIndex(x => x.UserId).HasDatabaseName("ix_user_logins_user_id");
        });
        modelBuilder.Entity<IdentityUserToken<string>>().ToTable("user_tokens", IdentitySchema);
        modelBuilder.Entity<IdentityRoleClaim<string>>(b =>
        {
            b.ToTable("role_claims", IdentitySchema);
            b.HasIndex(x => x.RoleId).HasDatabaseName("ix_role_claims_role_id");
        });
    }
}
