using System.Net;
using Microsoft.AspNetCore.Identity;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Auth;

/// <summary>
/// Yerel gelistirme kolayligi (Backend API 6): Mutalaa:Auth:DevAutoLogin acikken ve ortam Development iken, geri donusum (loopback)
/// adresinden gelen oturumsuz istek seed yoneticisiyle (Mutalaa:Seed:AdminEmail) oturum acar. Baska ortamda acilista hata verir.
/// </summary>
public static class DevAutoLogin
{
    public const string Key = "Mutalaa:Auth:DevAutoLogin";

    public static bool IsEnabled(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);
        return configuration.GetValue<bool>(Key);
    }

    /// <summary>Development disinda acik bayrak acilisi durdurur.</summary>
    public static void EnsureAllowed(IConfiguration configuration, IHostEnvironment environment)
    {
        ArgumentNullException.ThrowIfNull(environment);

        if (IsEnabled(configuration) && !environment.IsDevelopment())
        {
            throw new InvalidOperationException($"{Key} yalniz Development ortaminda acilabilir.");
        }
    }

    /// <summary>RemoteIpAddress null ise (bilinmiyor) loopback sayilmaz.</summary>
    public static bool IsLoopback(IPAddress? address) => address is not null && IPAddress.IsLoopback(address);

    public static IApplicationBuilder UseDevAutoLogin(this IApplicationBuilder app)
    {
        ArgumentNullException.ThrowIfNull(app);
        return app.UseMiddleware<DevAutoLoginMiddleware>();
    }
}

internal sealed class DevAutoLoginMiddleware(RequestDelegate next, IConfiguration configuration)
{
    public async Task InvokeAsync(HttpContext context, UserManager<EditorUser> users, SignInManager<EditorUser> signIn)
    {
        ArgumentNullException.ThrowIfNull(context);

        string? email = configuration[IdentitySeeder.AdminEmailKey];
        if (context.User.Identity?.IsAuthenticated != true
            && DevAutoLogin.IsLoopback(context.Connection.RemoteIpAddress)
            && !string.IsNullOrWhiteSpace(email))
        {
            EditorUser? admin = await users.FindByEmailAsync(email);
            if (admin is not null)
            {
                await signIn.SignInAsync(admin, isPersistent: false);

                // Cerez yalniz yanitta; bu istegin kendisi de oturumlu sayilsin.
                context.User = await signIn.CreateUserPrincipalAsync(admin);
            }
        }

        await next(context);
    }
}
