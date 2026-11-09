using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Routing;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Endpoints;
using Mutalaa.Api.Hosting;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Settings;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence;
using Scalar.AspNetCore;

CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;

// Icerik koku derleme klasoru: appsettings*.json oradan okunur; calisma dizini (dotnet run: depo koku) goreli data/... yollarini belirler.
var builder = WebApplication.CreateBuilder(new WebApplicationOptions { Args = args, ContentRootPath = AppContext.BaseDirectory });

builder.AddApiLogging();

builder.Services.AddIcerikDb(builder.Configuration);
builder.Services.AddEditorAuth();

builder.Services
    .AddOptions<ApiOptions>()
    .Bind(builder.Configuration.GetSection(ApiOptions.SectionName))
    .PostConfigure(options => options.Normalize());

// JSON alanlari veritabani sutunlariyla ayni (snake_case); taniminmayan alan 400.
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow;
});

builder.Services.AddReleaseServices();
builder.Services.AddValidation();
builder.Services.AddApiProblemDetails();
builder.Services.AddExceptionHandler<DomainExceptionHandler>();
builder.Services.AddExceptionHandler<ApiExceptionHandler>();
builder.Services.AddApiOpenApi();
builder.Services.AddHealthChecks().AddDbContextCheck<IcerikDbContext>("postgres", tags: ["ready"]);

var app = builder.Build();

// Yonetim komutu: dotnet run --project server/Mutalaa.Api -- seed
if (args is ["seed"])
{
    Environment.ExitCode = await IdentitySeeder.RunAsync(app.Services, CancellationToken.None);
    return;
}

bool documentGeneration = OpenApiSetup.IsDocumentGeneration();
if (!documentGeneration)
{
    DevAutoLogin.EnsureAllowed(app.Configuration, app.Environment);
}

ApiFeatures features = ApiFeatures.From(app.Configuration);

// Sira onemli: hata yakalayici en disarida; durum sayfalari kimlik dogrulamadan once ki 401/403/404/405 govdesi ProblemDetails olsun.
app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseApiRequestLogging();
app.UseAuthentication();
if (!documentGeneration && DevAutoLogin.IsEnabled(app.Configuration))
{
    app.UseDevAutoLogin();
}

app.UseAuthorization();

// Saglik: anonim, yalniz GET/HEAD.
app.MapHealthChecks("/health/live", new HealthCheckOptions { Predicate = _ => false })
    .WithMetadata(new HttpMethodMetadata(["GET", "HEAD"]))
    .AllowAnonymous()
    .ExcludeFromDescription();
app.MapHealthChecks("/health/ready", new HealthCheckOptions { Predicate = check => check.Tags.Contains("ready") })
    .WithMetadata(new HttpMethodMetadata(["GET", "HEAD"]))
    .AllowAnonymous()
    .ExcludeFromDescription();

RouteGroupBuilder v1 = app.MapGroup("/api/v1");
if (features.Editor)
{
    v1.MapEditorEndpoints();
}

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi().ExcludeFromDescription();
    app.MapScalarApiReference(options => options.DisableDefaultFonts()).ExcludeFromDescription();
}

if (!documentGeneration)
{
    ApiOptions paths = app.Services.GetRequiredService<Microsoft.Extensions.Options.IOptions<ApiOptions>>().Value;
    app.Logger.LogInformation(
        "Api basliyor: ortam {Environment}; icerik koku {ContentRoot}; calisma dizini {WorkingDirectory}; ozellikler editor={Editor} public={Public}.",
        app.Environment.EnvironmentName,
        app.Environment.ContentRootPath,
        Directory.GetCurrentDirectory(),
        features.Editor,
        features.Public);
    app.Logger.LogInformation(
        "Dosya yollari: ham {RawDir}; kaynaklar {SourcesDir}; paketler {PacksDir}; gecici {TempDir}.",
        paths.RawDir,
        paths.SourcesDir,
        paths.PacksDir,
        paths.TempDir);
}

app.Run();

// WebApplicationFactory<Program> icin.
public partial class Program;
