using System.Globalization;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Identity;

CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddIcerikDb(builder.Configuration);
builder.Services.AddEditorIdentity();

var app = builder.Build();

// Yonetim komutu: dotnet run --project server/Mutalaa.Api -- seed
if (args is ["seed"])
{
    Environment.ExitCode = await IdentitySeeder.RunAsync(app.Services, CancellationToken.None);
    return;
}

app.Run();

// WebApplicationFactory<Program> icin.
public partial class Program;
