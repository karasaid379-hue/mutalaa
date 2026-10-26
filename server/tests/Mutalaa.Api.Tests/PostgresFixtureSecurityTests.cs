using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text.RegularExpressions;
using Mutalaa.Api.Tests.Support;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>G-01: test kabi rastgele parola kullanir ve yalniz 127.0.0.1'e yayinlanir (Docker'li).</summary>
public partial class PostgresFixtureSecurityTests(PostgresFixture postgres)
{
    [GeneratedRegex("^[0-9a-f]{32}$", RegexOptions.CultureInvariant)]
    private static partial Regex RandomPasswordPattern();

    [Fact]
    public async Task The_container_password_is_random_and_not_the_default()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase database = await postgres.CreateDatabaseAsync("fixturesecurity", ct);

        NpgsqlConnectionStringBuilder builder = new(database.ConnectionString);

        Assert.NotNull(builder.Password);
        Assert.NotEqual("postgres", builder.Password);
        Assert.Matches(RandomPasswordPattern(), builder.Password);
    }

    [Fact]
    public async Task The_wrong_password_is_rejected_by_the_server()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using TestDatabase database = await postgres.CreateDatabaseAsync("fixturepassword", ct);
        NpgsqlConnectionStringBuilder wrong = new(database.ConnectionString) { Password = "postgres", Pooling = false };

        await using NpgsqlConnection connection = new(wrong.ConnectionString);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => connection.OpenAsync(ct));
        Assert.Equal("28P01", exception.SqlState);
    }

    [Fact]
    public async Task The_published_port_is_not_reachable_through_a_non_loopback_address_of_this_machine()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        int port = await postgres.PublishedPortAsync(ct);

        IPAddress[] external =
        [
            .. NetworkInterface.GetAllNetworkInterfaces()
                .Where(n => n.OperationalStatus == OperationalStatus.Up && n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                .SelectMany(n => n.GetIPProperties().UnicastAddresses)
                .Select(a => a.Address)
                .Where(a => a.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(a)),
        ];
        Assert.True(external.Length > 0, "Sinama icin loopback disinda etkin bir IPv4 adresi gerekir.");

        foreach (IPAddress address in external)
        {
            using TcpClient client = new();
            using CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(5));
            bool connected;
            try
            {
                await client.ConnectAsync(address, port, timeout.Token);
                connected = true;
            }
            catch (SocketException)
            {
                connected = false;
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                connected = false;
            }

            Assert.False(connected, $"Port {port}, {address} uzerinden erisilebilir: kap yalniz 127.0.0.1'e baglanmali.");
        }

        // Kontrol: loopback uzerinden erisim vardir.
        using TcpClient loopback = new();
        await loopback.ConnectAsync(IPAddress.Loopback, port, ct);
        Assert.True(loopback.Connected);
    }
}
