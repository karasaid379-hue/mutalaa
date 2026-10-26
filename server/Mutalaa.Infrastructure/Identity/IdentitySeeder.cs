using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Mutalaa.Infrastructure.Identity;

/// <summary>
/// "seed" komutu: editor ve admin rollerini ve ilk yonetici kullanicisini olusturur. Idempotenttir.
/// Ayarlar IConfiguration'dan gelir (dotnet user-secrets): ConnectionStrings:Editorial, Mutalaa:Seed:AdminEmail, Mutalaa:Seed:AdminPassword.
/// Gunluge parola ve e-posta yazilmaz; yalniz ayar adlari ve Identity hata kodlari yazilir.
/// Cikis kodlari: 0 basari, 1 beklenmeyen hata, 2 eksik ayar, 3 Identity reddetti.
/// </summary>
public static class IdentitySeeder
{
    public const int ExitOk = 0;
    public const int ExitUnexpected = 1;
    public const int ExitMissingSetting = 2;
    public const int ExitIdentityRejected = 3;

    public const string AdminEmailKey = "Mutalaa:Seed:AdminEmail";
    public const string AdminPasswordKey = "Mutalaa:Seed:AdminPassword";
    public const string ConnectionStringKey = "ConnectionStrings:Editorial";

    private const string LoggerCategory = "Mutalaa.Seed";

    public static async Task<int> RunAsync(IServiceProvider services, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(services);

        ILogger logger = services.GetRequiredService<ILoggerFactory>().CreateLogger(LoggerCategory);
        IConfiguration configuration = services.GetRequiredService<IConfiguration>();

        List<string> missing = [];
        if (string.IsNullOrWhiteSpace(configuration[ConnectionStringKey]))
        {
            missing.Add(ConnectionStringKey);
        }

        string? email = configuration[AdminEmailKey];
        if (string.IsNullOrWhiteSpace(email))
        {
            missing.Add(AdminEmailKey);
        }

        string? password = configuration[AdminPasswordKey];
        if (string.IsNullOrEmpty(password))
        {
            missing.Add(AdminPasswordKey);
        }

        if (missing.Count > 0)
        {
            logger.LogError("Eksik ayar: {Settings}. Degerleri dotnet user-secrets ile verin.", string.Join(", ", missing));
            return ExitMissingSetting;
        }

        try
        {
            await using AsyncServiceScope scope = services.CreateAsyncScope();
            RoleManager<IdentityRole> roles = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            UserManager<EditorUser> users = scope.ServiceProvider.GetRequiredService<UserManager<EditorUser>>();

            foreach (string roleName in new[] { Roles.Editor, Roles.Admin })
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (await roles.RoleExistsAsync(roleName))
                {
                    continue;
                }

                IdentityResult created = await roles.CreateAsync(new IdentityRole(roleName));
                if (!created.Succeeded)
                {
                    logger.LogError("Rol olusturulamadi ({Role}). Identity hata kodlari: {Codes}", roleName, Codes(created));
                    return ExitIdentityRejected;
                }

                logger.LogInformation("Rol olusturuldu: {Role}", roleName);
            }

            EditorUser? admin = await users.FindByNameAsync(email!);
            if (admin is null)
            {
                admin = new EditorUser { UserName = email, Email = email, EmailConfirmed = true };
                IdentityResult created = await users.CreateAsync(admin, password!);
                if (!created.Succeeded)
                {
                    logger.LogError("Yonetici olusturulamadi. Identity hata kodlari: {Codes}", Codes(created));
                    return ExitIdentityRejected;
                }

                logger.LogInformation("Yonetici kullanici olusturuldu.");
            }
            else
            {
                // Var olan kullanicinin parolasina dokunulmaz.
                logger.LogInformation("Yonetici kullanici zaten var; parolasina dokunulmadi.");
            }

            if (!await users.IsInRoleAsync(admin, Roles.Admin))
            {
                IdentityResult added = await users.AddToRoleAsync(admin, Roles.Admin);
                if (!added.Succeeded)
                {
                    logger.LogError("Yonetici admin rolune eklenemedi. Identity hata kodlari: {Codes}", Codes(added));
                    return ExitIdentityRejected;
                }

                logger.LogInformation("Yonetici {Role} rolune eklendi.", Roles.Admin);
            }

            return ExitOk;
        }
        catch (Exception ex)
        {
            // Istisna iletisi baglanti ayrintisi ya da e-posta icerebilir; yalniz tur adlari yazilir.
            logger.LogError("Seed beklenmeyen hatayla durdu: {ExceptionTypes}", ExceptionTypes(ex));
            return ExitUnexpected;
        }
    }

    private static string Codes(IdentityResult result) =>
        string.Join(", ", result.Errors.Select(e => e.Code));

    private static string ExceptionTypes(Exception exception)
    {
        List<string> names = [];
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            names.Add(current.GetType().Name);
        }

        return string.Join(" <- ", names);
    }
}
