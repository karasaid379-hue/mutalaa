using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Mutalaa.Infrastructure;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Auth;

/// <summary>Yetki politikasi adlari (Backend API 6): Editor = editor ya da admin, Admin = yalniz admin.</summary>
public static class AuthPolicies
{
    public const string Editor = "Editor";
    public const string Admin = "Admin";
}

public static class AuthSetup
{
    public const string CookieName = "mutalaa.editor";

    /// <summary>Cerez kayan oturum suresi (Backend API 6: 8 saat, oneri).</summary>
    public static readonly TimeSpan SessionLifetime = TimeSpan.FromHours(8);

    /// <summary>Rol degisikligi ve kilit en gec bu surede acik oturuma yansir (guvenlik damgasi denetimi).</summary>
    public static readonly TimeSpan StampValidationInterval = TimeSpan.FromMinutes(1);

    /// <summary>
    /// Identity (SignInManager), yalniz uygulama cerezi ve yetki politikalari.
    /// Cerez: HttpOnly, SameSite=Strict, Development disinda Secure=Always (Development'ta istege gore), 8 saat kayan.
    /// Yonlendirme yok: oturumsuz 401, yetkisiz 403 (Location basligi yazilmaz); govdeyi UseStatusCodePages ProblemDetails ile doldurur.
    /// </summary>
    public static IServiceCollection AddEditorAuth(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.AddEditorIdentity().AddSignInManager();

        services
            .AddAuthentication(IdentityConstants.ApplicationScheme)
            .AddIdentityCookies(identity =>
                identity.ApplicationCookie!.Configure<IHostEnvironment>((options, environment) =>
                {
                    options.Cookie.Name = CookieName;
                    options.Cookie.HttpOnly = true;
                    options.Cookie.SameSite = SameSiteMode.Strict;
                    options.Cookie.SecurePolicy = environment.IsDevelopment() ? CookieSecurePolicy.SameAsRequest : CookieSecurePolicy.Always;
                    options.ExpireTimeSpan = SessionLifetime;
                    options.SlidingExpiration = true;

                    // AddIdentityCookies'in Events nesnesi (OnValidatePrincipal = SecurityStampValidator) degistirilir, yenisi atanmaz.
                    options.Events.OnRedirectToLogin = context =>
                    {
                        context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                        return Task.CompletedTask;
                    };
                    options.Events.OnRedirectToAccessDenied = context =>
                    {
                        context.Response.StatusCode = StatusCodes.Status403Forbidden;
                        return Task.CompletedTask;
                    };
                }));

        services.Configure<SecurityStampValidatorOptions>(options => options.ValidationInterval = StampValidationInterval);

        services.AddAuthorizationBuilder()
            .AddPolicy(AuthPolicies.Editor, policy => policy.RequireAuthenticatedUser().RequireRole(Roles.Editor, Roles.Admin))
            .AddPolicy(AuthPolicies.Admin, policy => policy.RequireAuthenticatedUser().RequireRole(Roles.Admin));

        return services;
    }
}
