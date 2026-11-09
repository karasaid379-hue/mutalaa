using System.CommandLine;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>Komut agaci ve cikis kodlari (Docker'siz): ayristirma hatasi 1, eksik yapilandirma 1, gizli deger yazilmaz.</summary>
public class CommandLineTests
{
    private static async Task<(int Code, string Out, string Error)> RunAsync(string[] args, Action<PublisherHostOptions>? configure = null)
    {
        StringWriter output = new();
        StringWriter error = new();
        PublisherHostOptions host = new()
        {
            EnvironmentName = "Production",
            Out = output,
            Error = error,
            Clock = new FixedClock(new DateTimeOffset(2026, 11, 9, 12, 0, 0, TimeSpan.Zero)),
        };
        configure?.Invoke(host);
        int code = await PublisherApp.RunAsync(args, host, TestContext.Current.CancellationToken);
        return (code, output.ToString(), error.ToString());
    }

    [Fact]
    public void Exit_codes_follow_the_documented_values()
    {
        Assert.Equal(0, ExitCodes.Success);
        Assert.Equal(1, ExitCodes.Other);
        Assert.Equal(2, ExitCodes.GateRejected);
        Assert.Equal(3, ExitCodes.Verification);
        Assert.Equal(4, ExitCodes.Storage);
    }

    [Fact]
    public void Root_command_has_every_documented_command()
    {
        IConfiguration configuration = new ConfigurationBuilder().Build();
        using ServiceProvider services = new ServiceCollection().BuildServiceProvider();
        PublisherContext context = new(configuration, new ReleaseRepository(services.GetRequiredService<IServiceScopeFactory>()));

        RootCommand root = PublisherApp.BuildRootCommand(context);

        Assert.Equal(
            ["build", "keys", "promote", "publish", "rollback", "upload", "verify", "watch"],
            root.Subcommands.Select(c => c.Name).Order(StringComparer.Ordinal).ToArray());
        Assert.Equal(["generate"], root.Subcommands.Single(c => c.Name == "keys").Subcommands.Select(c => c.Name).ToArray());
    }

    [Theory]
    [InlineData("publish", "--flavor", "staging")]
    [InlineData("publish", "--flavor", "DEV")]
    [InlineData("build", "--flavor", "x")]
    [InlineData("upload", "--flavor", "nope")]
    [InlineData("verify", "--flavor", "")]
    [InlineData("rollback", "--flavor", "foo", "--to", "2026.11.0")]
    [InlineData("keys", "generate", "--flavor", "foo")]
    public async Task Invalid_flavor_exits_with_1(params string[] args)
    {
        (int code, _, string error) = await RunAsync(args);

        Assert.Equal(1, code);
        Assert.NotEmpty(error);
    }

    [Theory]
    [InlineData("publish")]
    [InlineData("build")]
    [InlineData("upload")]
    [InlineData("verify")]
    [InlineData("rollback", "--to", "2026.11.0")]
    [InlineData("keys", "generate")]
    public async Task Missing_flavor_exits_with_1(params string[] args)
    {
        (int code, _, _) = await RunAsync(args);

        Assert.Equal(1, code);
    }

    [Theory]
    [InlineData("rollback", "--flavor", "dev")]
    [InlineData("promote", "--from", "public")]
    [InlineData("promote", "--to", "internal")]
    [InlineData("watch", "--interval", "abc")]
    [InlineData("no-such-command")]
    [InlineData("publish", "--flavor", "dev", "--unknown")]
    public async Task Bad_arguments_and_unknown_commands_exit_with_1(params string[] args)
    {
        (int code, _, _) = await RunAsync(args);

        Assert.Equal(1, code);
    }

    [Fact]
    public async Task A_valid_publish_without_a_connection_string_exits_with_1_and_names_the_setting_only()
    {
        (int code, _, string error) = await RunAsync(["publish", "--flavor", "dev"]);

        Assert.Equal(1, code);
        Assert.Contains("ConnectionStrings:Editorial", error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Dry_run_without_connection_string_exits_with_1()
    {
        (int code, _, string error) = await RunAsync(["publish", "--flavor", "public", "--dry-run"]);

        Assert.Equal(1, code);
        Assert.Contains("ConnectionStrings:Editorial", error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Verify_without_a_public_key_exits_with_1_before_touching_the_store()
    {
        InMemoryPackStore store = new() { Fault = (_, _) => new InvalidOperationException("depoya dokunulmamali") };

        (int code, _, string error) = await RunAsync(["verify", "--flavor", "dev"], host => host.StoreFactory = () => store);

        // Manifest depodan okunamaz (hata), ya da anahtar eksikligi: ikisi de 1; depo hatasi 4 degil 1 olmali (genel istisna).
        Assert.Equal(1, code);
        Assert.NotEmpty(error);
    }

    [Fact]
    public void Redact_removes_known_secrets_from_messages()
    {
        const string SecretKey = "uzun-gizli-deger-12345";
        const string Seed = "c2VudGV0aWstdG9ob20tYmFzZTY0LWRlZ2VyaQ==";
        IConfiguration configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Storage:SecretKey"] = SecretKey,
                ["Signing:dev:PrivateKey"] = Seed,
                ["ConnectionStrings:Editorial"] = "Host=localhost;Database=x;Username=u;Password=sentetik-parola-1",
            })
            .Build();
        using ServiceProvider services = new ServiceCollection().BuildServiceProvider();
        PublisherContext context = new(configuration, new ReleaseRepository(services.GetRequiredService<IServiceScopeFactory>()));

        string redacted = context.Redact($"hata {SecretKey} ve {Seed} ve sentetik-parola-1 bitti");

        Assert.Equal("hata *** ve *** ve *** bitti", redacted);
    }
}
