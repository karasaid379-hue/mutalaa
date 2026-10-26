using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Infrastructure;

public static class DependencyInjection
{
    /// <summary>Baglanti dizesi ayar anahtari: ConnectionStrings:Editorial.</summary>
    public const string ConnectionName = "Editorial";

    /// <summary>
    /// Editoryal veritabani baglami (Api ve Yayinlayici). ConnectionStrings:Editorial yoksa kayit hata vermez
    /// (dotnet ef goc uretimi baglanti istemez); ilk baglantida EF baglanti dizesi eksik hatasi verir.
    /// Otomatik goc yoktur.
    /// </summary>
    public static IServiceCollection AddIcerikDb(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        string? connectionString = configuration.GetConnectionString(ConnectionName);
        services.AddSingleton<UpdatedAtInterceptor>();
        services.AddDbContext<IcerikDbContext>((provider, options) =>
        {
            IcerikDbContextOptions.Configure(options, string.IsNullOrWhiteSpace(connectionString) ? null : connectionString);
            options.AddInterceptors(provider.GetRequiredService<UpdatedAtInterceptor>());
        });
        return services;
    }

    /// <summary>Editor kimligi (yalniz Api): parola en az 12 karakter, 5 hatali denemede 15 dakika kilit (K-37).</summary>
    public static IServiceCollection AddEditorIdentity(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services
            .AddIdentityCore<EditorUser>(o =>
            {
                o.User.RequireUniqueEmail = true;
                o.Password.RequiredLength = 12;
                o.Password.RequireDigit = false;
                o.Password.RequireLowercase = false;
                o.Password.RequireUppercase = false;
                o.Password.RequireNonAlphanumeric = false;
                o.Password.RequiredUniqueChars = 1;
                o.Lockout.MaxFailedAccessAttempts = 5;
                o.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
                o.Lockout.AllowedForNewUsers = true;
            })
            .AddRoles<Microsoft.AspNetCore.Identity.IdentityRole>()
            .AddEntityFrameworkStores<IcerikDbContext>();
        return services;
    }
}
