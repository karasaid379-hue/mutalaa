using System.Diagnostics;
using System.Globalization;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Tests;

/// <summary>
/// A07 devri: <c>dotnet Mutalaa.Api.dll seed</c> gercek surec olarak calisir; cikis kodlari 0 (basari), 2 (eksik ayar), 3 (Identity reddetti).
/// Ortam Testing: kullanici sirlari yuklenmez, degerler ortam degiskeniyle verilir. Parola her kosuda rastgeledir.
/// </summary>
public class SeedProcessTests(EditorialDatabase<SeedProcessTests> fixture) : IClassFixture<EditorialDatabase<SeedProcessTests>>, IAsyncLifetime
{
    private const string Email = "yonetici@example.test";

    private TestDatabase Db => fixture.Database;

    public ValueTask InitializeAsync() =>
        new(Db.ExecuteAsync(
            "TRUNCATE kimlik.user_roles, kimlik.user_claims, kimlik.user_logins, kimlik.user_tokens, kimlik.role_claims, kimlik.users, kimlik.roles",
            TestContext.Current.CancellationToken));

    public ValueTask DisposeAsync() => ValueTask.CompletedTask;

    private static string ApiDll()
    {
        // Test klasoru .../bin/{Yapilandirma}/net10.0/: ayni yapilandirmanin Api ciktisi kullanilir.
        DirectoryInfo target = new(AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        string tfm = target.Name;
        string configuration = target.Parent!.Name;
        string dll = RepoFiles.PathOf($"server/Mutalaa.Api/bin/{configuration}/{tfm}/Mutalaa.Api.dll");
        Assert.True(File.Exists(dll), $"Derlenmis Api bulunamadi: {dll}");
        return dll;
    }

    private async Task<(int ExitCode, string Output)> RunSeedAsync(string? email, string? password, CancellationToken cancellationToken)
    {
        string dll = ApiDll();
        ProcessStartInfo info = new("dotnet")
        {
            WorkingDirectory = Path.GetDirectoryName(dll)!,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        info.ArgumentList.Add(dll);
        info.ArgumentList.Add("seed");
        info.Environment["ASPNETCORE_ENVIRONMENT"] = "Testing";
        info.Environment["DOTNET_ENVIRONMENT"] = "Testing";
        info.Environment["ConnectionStrings__Editorial"] = Db.ConnectionString;
        info.Environment.Remove("Mutalaa__Seed__AdminEmail");
        info.Environment.Remove("Mutalaa__Seed__AdminPassword");
        if (email is not null)
        {
            info.Environment["Mutalaa__Seed__AdminEmail"] = email;
        }

        if (password is not null)
        {
            info.Environment["Mutalaa__Seed__AdminPassword"] = password;
        }

        using Process process = Process.Start(info) ?? throw new InvalidOperationException("Surec baslamadi.");
        Task<string> stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        Task<string> stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        using CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(90));
        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException)
        {
            process.Kill(entireProcessTree: true);
            throw;
        }

        return (process.ExitCode, await stdout + await stderr);
    }

    private static string RandomPassword() => Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture);

    [Fact]
    public async Task The_seed_process_exits_0_creates_the_admin_and_is_idempotent()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string password = RandomPassword();

        (int first, string firstOutput) = await RunSeedAsync(Email, password, ct);
        (int second, string secondOutput) = await RunSeedAsync(Email, password, ct);

        Assert.Equal(IdentitySeeder.ExitOk, first);
        Assert.Equal(IdentitySeeder.ExitOk, second);
        Assert.Equal(1L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", ct));
        Assert.Equal(["admin", "editor"], await Db.ColumnAsync("SELECT name FROM kimlik.roles ORDER BY name", ct));
        Assert.Equal(["admin"], await Db.ColumnAsync("SELECT r.name FROM kimlik.user_roles ur JOIN kimlik.roles r ON r.id = ur.role_id", ct));
        foreach (string output in new[] { firstOutput, secondOutput })
        {
            Assert.DoesNotContain(password, output, StringComparison.Ordinal);
            Assert.DoesNotContain(Email, output, StringComparison.OrdinalIgnoreCase);
        }
    }

    [Fact]
    public async Task A_missing_password_exits_2_and_names_the_setting_but_not_a_value()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        (int exit, string output) = await RunSeedAsync(Email, password: null, ct);

        Assert.Equal(IdentitySeeder.ExitMissingSetting, exit);
        Assert.Contains(IdentitySeeder.AdminPasswordKey, output, StringComparison.Ordinal);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", ct));
    }

    [Fact]
    public async Task A_password_shorter_than_12_characters_exits_3_and_creates_no_user()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        string tooShort = RandomPassword()[..11];

        (int exit, string output) = await RunSeedAsync(Email, tooShort, ct);

        Assert.Equal(IdentitySeeder.ExitIdentityRejected, exit);
        Assert.DoesNotContain(tooShort, output, StringComparison.Ordinal);
        Assert.Equal(0L, await Db.ScalarAsync<long>("SELECT count(*) FROM kimlik.users", ct));
    }
}
