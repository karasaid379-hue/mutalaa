using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>"seed" komutu gercek veritabaniyla (Docker'li): idempotentlik, parola korunumu, cikis kodlari, gunluk ve kilit ayari.</summary>
public class SeedTests(EditorialDatabase<SeedTests> fixture) : IClassFixture<EditorialDatabase<SeedTests>>, IAsyncLifetime
{
    // Sentetik degerler: gercek parola ya da e-posta degildir.
    private const string Email = "yonetici@example.test";
    private const string Password = "deneme-parolasi-123";
    private const string OtherPassword = "baska-parola-456789";

    private TestDatabase Db => fixture.Database;

    /// <summary>Sinifin testleri ayni veritabanini paylasir: her test temiz kimlik tablolariyla baslar.</summary>
    public ValueTask InitializeAsync() =>
        new(Db.ExecuteAsync("TRUNCATE kimlik.user_roles, kimlik.user_claims, kimlik.user_logins, kimlik.user_tokens, kimlik.role_claims, kimlik.users, kimlik.roles", TestContext.Current.CancellationToken));

    public ValueTask DisposeAsync() => ValueTask.CompletedTask;

    private ServiceProvider BuildServices(CapturingLoggerProvider logs, string? email = Email, string? password = Password)
    {
        Dictionary<string, string?> values = new() { ["ConnectionStrings:Editorial"] = Db.ConnectionString };
        if (email is not null)
        {
            values["Mutalaa:Seed:AdminEmail"] = email;
        }

        if (password is not null)
        {
            values["Mutalaa:Seed:AdminPassword"] = password;
        }

        IConfiguration configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        ServiceCollection services = new();
        services.AddLogging(b => b.ClearProviders().AddProvider(logs));
        services.AddSingleton(configuration);
        services.AddIcerikDb(configuration);
        services.AddEditorIdentity();
        return services.BuildServiceProvider();
    }

    private async Task<long> CountAsync(string table, CancellationToken ct) =>
        await Db.ScalarAsync<long>($"SELECT count(*) FROM kimlik.{table}", ct);

    [Fact]
    public async Task Running_the_seed_twice_creates_two_roles_one_user_and_puts_the_user_in_the_admin_role()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using ServiceProvider provider = BuildServices(logs);

        int first = await IdentitySeeder.RunAsync(provider, ct);
        int second = await IdentitySeeder.RunAsync(provider, ct);

        Assert.Equal(IdentitySeeder.ExitOk, first);
        Assert.Equal(IdentitySeeder.ExitOk, second);
        Assert.Equal(2L, await CountAsync("roles", ct));
        Assert.Equal(1L, await CountAsync("users", ct));
        Assert.Equal(1L, await CountAsync("user_roles", ct));
        Assert.Equal(["admin", "editor"], await Db.ColumnAsync("SELECT name FROM kimlik.roles ORDER BY name", ct));
        Assert.Equal(
            ["admin"],
            await Db.ColumnAsync(
                "SELECT r.name FROM kimlik.user_roles ur JOIN kimlik.roles r ON r.id = ur.role_id JOIN kimlik.users u ON u.id = ur.user_id WHERE u.user_name = @e",
                ct,
                ("e", Email)));
        Assert.Equal(Email, await Db.ScalarAsync<string>("SELECT email FROM kimlik.users", ct));
    }

    [Fact]
    public async Task A_second_run_with_a_different_password_does_not_change_the_password_hash()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using (ServiceProvider first = BuildServices(logs))
        {
            Assert.Equal(IdentitySeeder.ExitOk, await IdentitySeeder.RunAsync(first, ct));
        }

        string before = await Db.ScalarAsync<string>("SELECT password_hash FROM kimlik.users", ct);

        await using (ServiceProvider second = BuildServices(logs, password: OtherPassword))
        {
            Assert.Equal(IdentitySeeder.ExitOk, await IdentitySeeder.RunAsync(second, ct));
        }

        Assert.False(string.IsNullOrEmpty(before));
        Assert.Equal(before, await Db.ScalarAsync<string>("SELECT password_hash FROM kimlik.users", ct));
        Assert.Equal(1L, await CountAsync("users", ct));

        // Ilk parola hala dogru, ikincisi degil: parola gercekten degismedi.
        await using ServiceProvider check = BuildServices(logs);
        await using AsyncServiceScope scope = check.CreateAsyncScope();
        UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
        EditorUser user = (await users.FindByNameAsync(Email))!;
        Assert.True(await users.CheckPasswordAsync(user, Password));
        Assert.False(await users.CheckPasswordAsync(user, OtherPassword));
    }

    [Fact]
    public async Task Missing_settings_return_exit_code_2_and_create_nothing()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using ServiceProvider noEmail = BuildServices(logs, email: null);
        await using ServiceProvider noPassword = BuildServices(logs, password: null);

        Assert.Equal(IdentitySeeder.ExitMissingSetting, await IdentitySeeder.RunAsync(noEmail, ct));
        Assert.Equal(IdentitySeeder.ExitMissingSetting, await IdentitySeeder.RunAsync(noPassword, ct));

        Assert.Equal(0L, await CountAsync("roles", ct));
        Assert.Equal(0L, await CountAsync("users", ct));
        Assert.Contains(IdentitySeeder.AdminEmailKey, logs.Text, StringComparison.Ordinal);
        Assert.Contains(IdentitySeeder.AdminPasswordKey, logs.Text, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("abcdefghijk", IdentitySeeder.ExitIdentityRejected, 0L)]
    [InlineData("abcdefghijkl", IdentitySeeder.ExitOk, 1L)]
    public async Task The_password_must_be_at_least_12_characters_and_a_rejected_user_is_not_created(string password, int exitCode, long users)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using ServiceProvider provider = BuildServices(logs, password: password);

        int exit = await IdentitySeeder.RunAsync(provider, ct);

        Assert.Equal(exitCode, exit);
        Assert.Equal(users, await CountAsync("users", ct));
        Assert.DoesNotContain(password, logs.Text, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_log_never_contains_the_password_or_the_email()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using ServiceProvider provider = BuildServices(logs);

        await IdentitySeeder.RunAsync(provider, ct);
        await IdentitySeeder.RunAsync(provider, ct);
        await using ServiceProvider rejected = BuildServices(logs, email: "baska@example.test", password: "kisa");
        await IdentitySeeder.RunAsync(rejected, ct);

        Assert.NotEmpty(logs.Messages);
        string log = logs.Text;
        Assert.DoesNotContain(Password, log, StringComparison.Ordinal);
        Assert.DoesNotContain("kisa", log, StringComparison.Ordinal);
        Assert.DoesNotContain(Email, log, StringComparison.Ordinal);
        Assert.DoesNotContain("baska@example.test", log, StringComparison.Ordinal);
        Assert.DoesNotContain("yonetici", log, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Five_failed_attempts_lock_the_account_for_about_15_minutes_against_a_real_database()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        CapturingLoggerProvider logs = new();
        await using ServiceProvider provider = BuildServices(logs);
        Assert.Equal(IdentitySeeder.ExitOk, await IdentitySeeder.RunAsync(provider, ct));

        await using AsyncServiceScope scope = provider.CreateAsyncScope();
        UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
        EditorUser user = (await users.FindByNameAsync(Email))!;
        Assert.True(await users.GetLockoutEnabledAsync(user));

        for (int attempt = 1; attempt <= 4; attempt++)
        {
            await users.AccessFailedAsync(user);
            Assert.False(await users.IsLockedOutAsync(user), $"{attempt}. hatali denemede kilitlenmemeli");
        }

        DateTimeOffset before = DateTimeOffset.UtcNow;
        await users.AccessFailedAsync(user);
        DateTimeOffset after = DateTimeOffset.UtcNow;

        Assert.True(await users.IsLockedOutAsync(user));
        DateTimeOffset lockoutEnd = (await users.GetLockoutEndDateAsync(user))!.Value;
        Assert.InRange(lockoutEnd, before.AddMinutes(15).AddSeconds(-5), after.AddMinutes(15).AddSeconds(5));

        // Kilit veritabanina yazildi (yeni bir baglamdan okunur).
        await using AsyncServiceScope other = provider.CreateAsyncScope();
        UserManager<EditorUser> reader = other.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();
        EditorUser reloaded = (await reader.FindByNameAsync(Email))!;
        Assert.True(await reader.IsLockedOutAsync(reloaded));
        // timestamptz mikrosaniye hassasiyetindedir (.NET 100 ns): bire bir esitlik beklenmez.
        Assert.InRange((await reader.GetLockoutEndDateAsync(reloaded))!.Value, lockoutEnd.AddMilliseconds(-1), lockoutEnd.AddMilliseconds(1));
    }
}
