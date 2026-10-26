using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Tests;

/// <summary>Baglam davranisi (veritabani gerektirmez): DI kaydi, updated_at damgasi, anahtar uretimi, varsayilanlar, seed hata yollari.</summary>
public class ContextBehaviorTests
{
    private sealed class FixedTime(DateTimeOffset now) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => now;
    }

    private sealed class CapturingLoggerProvider : ILoggerProvider
    {
        public List<string> Messages { get; } = [];

        public ILogger CreateLogger(string categoryName) => new CapturingLogger(Messages);

        public void Dispose()
        {
        }

        private sealed class CapturingLogger(List<string> messages) : ILogger
        {
            public IDisposable? BeginScope<TState>(TState state)
                where TState : notnull => null;

            public bool IsEnabled(LogLevel logLevel) => true;

            public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
            {
                messages.Add(formatter(state, exception));
                if (exception is not null)
                {
                    messages.Add(exception.ToString());
                }
            }
        }
    }

    private static Source NewSource() => new()
    {
        Slug = "test-kaynak",
        Tur = SourceKind.Meal,
        Baslik = "Deneme kaynagi",
        Surum = "1",
        LicenseName = "Deneme",
        AtifMetni = "Deneme atfi",
    };

    [Fact]
    public void Registration_without_a_connection_string_does_not_throw_and_a_context_can_be_created()
    {
        using ServiceProvider provider = ModelFactory.BuildServices();
        using IServiceScope scope = provider.CreateScope();

        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();

        Assert.NotNull(context.Model);
        Assert.Equal("Npgsql.EntityFrameworkCore.PostgreSQL", context.Database.ProviderName);
    }

    [Fact]
    public void Identity_options_follow_k37()
    {
        using ServiceProvider provider = ModelFactory.BuildServices();
        IdentityOptions options = provider.GetRequiredService<IOptions<IdentityOptions>>().Value;

        Assert.True(options.User.RequireUniqueEmail);
        Assert.Equal(12, options.Password.RequiredLength);
        Assert.False(options.Password.RequireDigit);
        Assert.False(options.Password.RequireLowercase);
        Assert.False(options.Password.RequireUppercase);
        Assert.False(options.Password.RequireNonAlphanumeric);
        Assert.Equal(1, options.Password.RequiredUniqueChars);
        Assert.Equal(5, options.Lockout.MaxFailedAccessAttempts);
        Assert.Equal(TimeSpan.FromMinutes(15), options.Lockout.DefaultLockoutTimeSpan);
        Assert.True(options.Lockout.AllowedForNewUsers);

        using IServiceScope scope = provider.CreateScope();
        Assert.NotNull(scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>());
        Assert.NotNull(scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>());
        Assert.Null(scope.ServiceProvider.GetService<IUserTwoFactorTokenProvider<EditorUser>>());
    }

    [Fact]
    public void Updated_at_is_stamped_in_utc_only_on_modified_rows_that_have_the_column()
    {
        DateTimeOffset now = new(2026, 10, 26, 12, 0, 0, TimeSpan.FromHours(3));
        UpdatedAtInterceptor interceptor = new(new FixedTime(now));
        using ServiceProvider provider = ModelFactory.BuildServices();
        using IServiceScope scope = provider.CreateScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();

        DateTime old = new(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        Source modified = NewSource();
        modified.UpdatedAt = old;
        Source untouched = NewSource();
        untouched.Slug = "test-dokunulmayan";
        untouched.UpdatedAt = old;
        Source explicitlySet = NewSource();
        explicitlySet.Slug = "test-elle";
        explicitlySet.UpdatedAt = old;
        Root root = new() { Id = 1, Letters = "x", SourceId = "test-kaynak", DataVersion = "t" };

        context.AttachRange(modified, untouched, explicitlySet, root);
        modified.Baslik = "Degisti";
        explicitlySet.Baslik = "Degisti";
        explicitlySet.UpdatedAt = new DateTime(2021, 5, 5, 0, 0, 0, DateTimeKind.Utc);
        context.Entry(explicitlySet).Property(x => x.UpdatedAt).IsModified = true;
        root.Letters = "y";

        interceptor.Stamp(context);

        Assert.Equal(new DateTime(2026, 10, 26, 9, 0, 0, DateTimeKind.Utc), modified.UpdatedAt);
        Assert.Equal(DateTimeKind.Utc, modified.UpdatedAt.Kind);
        Assert.Equal(old, untouched.UpdatedAt);
        Assert.Equal(new DateTime(2021, 5, 5, 0, 0, 0, DateTimeKind.Utc), explicitlySet.UpdatedAt);
        Assert.Equal(EntityState.Modified, context.Entry(root).State);
    }

    [Fact]
    public void Database_generated_keys_get_temporary_values_and_literal_defaults_are_always_written()
    {
        using ServiceProvider provider = ModelFactory.BuildServices();
        using IServiceScope scope = provider.CreateScope();
        IcerikDbContext context = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();

        Xref xref = new()
        {
            SrcAnchor = AnchorRef.Parse("q:2:255"),
            DstAnchor = AnchorRef.Parse("q:2:256"),
            Type = XrefType.Atif,
            Origin = XrefOrigin.Hat,
            DataVersion = "t",
            License = LicenseStatus.Serbest,
        };
        context.Add(xref);
        // uuidv7() veritabaninda uretilir: istemci gecici deger tutar, SaveChanges'ta veritabani degeri gelir.
        Assert.True(context.Entry(xref).Property(x => x.Id).IsTemporary);

        QuranWordFix fix = new() { Anchor = AnchorRef.Parse("q:2:255:3"), Field = "pos", NewValue = "N", Reason = "deneme" };
        context.Add(fix);
        Assert.True(context.Entry(fix).Property(x => x.Id).IsTemporary);

        Source source = NewSource();
        source.LicenseStatus = LicenseStatus.Serbest;
        context.Add(source);
        Assert.False(context.Entry(source).Property(x => x.LicenseStatus).IsTemporary);
        Assert.Equal(LicenseStatus.Serbest, source.LicenseStatus);

        ModelFactory.ForEachModel(model =>
        {
            foreach (IProperty property in model.GetEntityTypes()
                .Where(e => e.ClrType.Namespace?.StartsWith("Mutalaa.Domain.", StringComparison.Ordinal) == true)
                .SelectMany(e => e.GetProperties()))
            {
                if (property.GetDefaultValueSql() is null && !property.IsConcurrencyToken && HasNonClrDefault(property))
                {
                    Assert.True(property.ValueGenerated == ValueGenerated.Never, $"{property.DeclaringType.DisplayName()}.{property.Name}: {property.ValueGenerated} default=[{property.GetDefaultValue()}] sql=[{property.GetDefaultValueSql()}]");
                }

                if (property.GetDefaultValueSql() is not null)
                {
                    Assert.True(property.ValueGenerated == ValueGenerated.OnAdd, $"{property.DeclaringType.DisplayName()}.{property.Name}: {property.ValueGenerated}");
                }
            }
        });
    }

    /// <summary>EF kimlik sutunlarina ve SQL varsayilanlarina CLR varsayilanini sentinel olarak yazar; yalniz gercek varsayilanlar sayilir.</summary>
    private static bool HasNonClrDefault(IProperty property)
    {
        object? value = property.GetDefaultValue();
        if (value is null)
        {
            return false;
        }

        object? clrDefault = property.ClrType.IsValueType ? Activator.CreateInstance(property.ClrType) : null;
        return !Equals(value, clrDefault);
    }

    [Fact]
    public async Task Seed_returns_2_and_names_the_missing_settings_only()
    {
        CapturingLoggerProvider logs = new();
        Dictionary<string, string?> values = new() { ["ConnectionStrings:Editorial"] = "Host=127.0.0.1;Port=1;Database=x;Username=u;Password=gizli-parola-123" };
        using ServiceProvider provider = BuildSeedServices(values, logs);

        int exit = await IdentitySeeder.RunAsync(provider, TestContext.Current.CancellationToken);

        Assert.Equal(IdentitySeeder.ExitMissingSetting, exit);
        string log = string.Join('\n', logs.Messages);
        Assert.Contains(IdentitySeeder.AdminEmailKey, log, StringComparison.Ordinal);
        Assert.Contains(IdentitySeeder.AdminPasswordKey, log, StringComparison.Ordinal);
        Assert.DoesNotContain(IdentitySeeder.ConnectionStringKey, log, StringComparison.Ordinal);
        Assert.DoesNotContain("gizli-parola-123", log, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Seed_returns_2_when_the_connection_string_is_missing()
    {
        CapturingLoggerProvider logs = new();
        Dictionary<string, string?> values = new()
        {
            ["Mutalaa:Seed:AdminEmail"] = "yonetici@example.test",
            ["Mutalaa:Seed:AdminPassword"] = "en-az-on-iki-karakter",
        };
        using ServiceProvider provider = BuildSeedServices(values, logs);

        int exit = await IdentitySeeder.RunAsync(provider, TestContext.Current.CancellationToken);

        Assert.Equal(IdentitySeeder.ExitMissingSetting, exit);
        string log = string.Join('\n', logs.Messages);
        Assert.Contains(IdentitySeeder.ConnectionStringKey, log, StringComparison.Ordinal);
        Assert.DoesNotContain("yonetici@example.test", log, StringComparison.Ordinal);
        Assert.DoesNotContain("en-az-on-iki-karakter", log, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Seed_returns_1_on_an_unexpected_error_without_leaking_secrets()
    {
        // Kapali bir kapiya baglanir: veritabani yok, hata hizli doner (Docker gerekmez).
        CapturingLoggerProvider logs = new();
        Dictionary<string, string?> values = new()
        {
            ["ConnectionStrings:Editorial"] = "Host=127.0.0.1;Port=1;Database=x;Username=u;Password=gizli-parola-123;Timeout=2;Pooling=false",
            ["Mutalaa:Seed:AdminEmail"] = "yonetici@example.test",
            ["Mutalaa:Seed:AdminPassword"] = "en-az-on-iki-karakter",
        };
        using ServiceProvider provider = BuildSeedServices(values, logs);

        int exit = await IdentitySeeder.RunAsync(provider, TestContext.Current.CancellationToken);

        Assert.Equal(IdentitySeeder.ExitUnexpected, exit);
        string log = string.Join('\n', logs.Messages);
        Assert.DoesNotContain("gizli-parola-123", log, StringComparison.Ordinal);
        Assert.DoesNotContain("yonetici@example.test", log, StringComparison.Ordinal);
        Assert.DoesNotContain("en-az-on-iki-karakter", log, StringComparison.Ordinal);
    }

    private static ServiceProvider BuildSeedServices(Dictionary<string, string?> values, CapturingLoggerProvider logs)
    {
        IConfiguration configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        ServiceCollection services = new();
        services.AddLogging(b => b.ClearProviders().AddProvider(logs));
        services.AddSingleton(configuration);
        services.AddIcerikDb(configuration);
        services.AddEditorIdentity();
        return services.BuildServiceProvider();
    }
}
