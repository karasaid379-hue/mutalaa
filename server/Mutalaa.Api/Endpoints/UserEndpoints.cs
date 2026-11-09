using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

public sealed record UserDto(string Id, string Email, IReadOnlyList<string> Roller, bool Kilitli);

public sealed record CreateUserRequest(
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Email,
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Parola,
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string[] Roller);

public sealed record SetRolesRequest([property: Required(ErrorMessage = "{0} alanı zorunludur.")] string[] Roller);

public sealed record IdentityErrorDto(string Kod, string Aciklama);

/// <summary>Editor hesaplari (yalniz admin): liste, olusturma, rol degisimi. Kendi kendine kayit yoktur.</summary>
public static class UserEndpoints
{
    private static readonly string[] AllowedRoles = [Roles.Editor, Roles.Admin];

    // Rol degisimlerini siralar: iki yoneticinin ayni anda birbirinin admin rolunu almasi son yoneticiyi silemez.
    private const long RoleChangeLockKey = 0x4d55_5441_4c41_4101;

    public static RouteGroupBuilder MapUserEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder users = editor.MapGroup("/users").WithTags("users");
        users.RequireAuthorization(AuthPolicies.Admin);
        users.ProducesProblem(StatusCodes.Status403Forbidden);

        users.MapGet(string.Empty, ListAsync)
            .WithName("listUsers")
            .Produces<IReadOnlyList<UserDto>>();

        users.MapPost(string.Empty, CreateAsync)
            .WithName("createUser")
            .Produces<UserDto>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status409Conflict);

        users.MapPut("/{id}/roles", SetRolesAsync)
            .WithName("setUserRoles")
            .Produces<UserDto>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict);

        return editor;
    }

    private static async Task<IResult> ListAsync(IcerikDbContext db, CancellationToken cancellationToken)
    {
        var accounts = await db.Users
            .AsNoTracking()
            .OrderBy(u => u.Email)
            .Select(u => new { u.Id, u.Email, u.LockoutEnd })
            .ToListAsync(cancellationToken);
        var memberships = await (
            from userRole in db.UserRoles.AsNoTracking()
            join role in db.Roles.AsNoTracking() on userRole.RoleId equals role.Id
            select new { userRole.UserId, role.Name })
            .ToListAsync(cancellationToken);

        ILookup<string, string> rolesByUser = memberships.ToLookup(m => m.UserId, m => m.Name ?? string.Empty, StringComparer.Ordinal);
        DateTimeOffset now = DateTimeOffset.UtcNow;
        List<UserDto> result = [.. accounts.Select(a => new UserDto(
            a.Id,
            a.Email ?? string.Empty,
            [.. rolesByUser[a.Id].Order(StringComparer.Ordinal)],
            a.LockoutEnd is { } end && end > now))];
        return TypedResults.Ok(result);
    }

    private static async Task<IResult> CreateAsync(
        CreateUserRequest request,
        UserManager<EditorUser> users,
        RoleManager<IdentityRole> roles,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        if (RoleError(request.Roller) is { } invalid)
        {
            return invalid;
        }

        await EnsureRolesAsync(roles);

        // Kullanici ve roller birlikte: rol eklenemezse kullanici da olusmaz.
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        string email = request.Email.Trim();
        EditorUser user = new() { UserName = email, Email = email, EmailConfirmed = true };
        IdentityResult created = await users.CreateAsync(user, request.Parola);
        if (!created.Succeeded)
        {
            return FromIdentity(created);
        }

        string[] desired = Distinct(request.Roller);
        if (desired.Length > 0)
        {
            IdentityResult added = await users.AddToRolesAsync(user, desired);
            if (!added.Succeeded)
            {
                return FromIdentity(added);
            }
        }

        await transaction.CommitAsync(cancellationToken);
        return TypedResults.Json(
            new UserDto(user.Id, email, [.. desired.Order(StringComparer.Ordinal)], Kilitli: false),
            statusCode: StatusCodes.Status201Created);
    }

    private static async Task<IResult> SetRolesAsync(
        string id,
        SetRolesRequest request,
        UserManager<EditorUser> users,
        RoleManager<IdentityRole> roles,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        if (RoleError(request.Roller) is { } invalid)
        {
            return invalid;
        }

        await EnsureRolesAsync(roles);

        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        await db.Database.ExecuteSqlAsync($"SELECT pg_advisory_xact_lock({RoleChangeLockKey})", cancellationToken);

        EditorUser? user = await users.FindByIdAsync(id);
        if (user is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Kullanıcı bulunamadı.");
        }

        string[] desired = Distinct(request.Roller);
        IList<string> current = await users.GetRolesAsync(user);
        string[] toRemove = [.. current.Except(desired, StringComparer.Ordinal)];
        string[] toAdd = [.. desired.Except(current, StringComparer.Ordinal)];

        if (toRemove.Contains(Roles.Admin, StringComparer.Ordinal))
        {
            IList<EditorUser> admins = await users.GetUsersInRoleAsync(Roles.Admin);
            if (admins.All(a => string.Equals(a.Id, user.Id, StringComparison.Ordinal)))
            {
                return ApiProblem.Create(
                    StatusCodes.Status409Conflict,
                    ProblemCodes.DurumGecisiGecersiz,
                    "Son yöneticinin admin rolü alınamaz.");
            }
        }

        if (toRemove.Length > 0)
        {
            IdentityResult removed = await users.RemoveFromRolesAsync(user, toRemove);
            if (!removed.Succeeded)
            {
                return FromIdentity(removed);
            }
        }

        if (toAdd.Length > 0)
        {
            IdentityResult added = await users.AddToRolesAsync(user, toAdd);
            if (!added.Succeeded)
            {
                return FromIdentity(added);
            }
        }

        if (toRemove.Length > 0 || toAdd.Length > 0)
        {
            // Acik oturumlar en gec bir dakika icinde (SecurityStampValidator) yeni rolleri gorur ya da duser.
            IdentityResult stamp = await users.UpdateSecurityStampAsync(user);
            if (!stamp.Succeeded)
            {
                return FromIdentity(stamp);
            }
        }

        await transaction.CommitAsync(cancellationToken);
        bool locked = user.LockoutEnd is { } end && end > DateTimeOffset.UtcNow;
        return TypedResults.Ok(new UserDto(user.Id, user.Email ?? string.Empty, [.. desired.Order(StringComparer.Ordinal)], locked));
    }

    private static string[] Distinct(string[] roles) => [.. roles.Distinct(StringComparer.Ordinal)];

    private static IResult? RoleError(string[] roles)
    {
        string[] unknown = [.. roles.Where(r => !AllowedRoles.Contains(r, StringComparer.Ordinal)).Distinct(StringComparer.Ordinal)];
        return unknown.Length == 0
            ? null
            : ApiProblem.Validation(
                new Dictionary<string, string[]> { ["roller"] = [$"Geçersiz rol: {string.Join(", ", unknown)}. İzin verilenler: {string.Join(", ", AllowedRoles)}."] });
    }

    private static async Task EnsureRolesAsync(RoleManager<IdentityRole> roles)
    {
        foreach (string name in AllowedRoles)
        {
            if (!await roles.RoleExistsAsync(name))
            {
                await roles.CreateAsync(new IdentityRole(name));
            }
        }
    }

    /// <summary>Basarisiz Identity sonucu: ayni e-posta 409, digerleri 400 dogrulama + hatalar listesi.</summary>
    private static IResult FromIdentity(IdentityResult result)
    {
        if (result.Errors.Any(e => e.Code is "DuplicateEmail" or "DuplicateUserName"))
        {
            return ApiProblem.Create(StatusCodes.Status409Conflict, ProblemCodes.Cakisma, "Bu e-posta adresiyle kayıtlı bir kullanıcı var.");
        }

        IdentityErrorDto[] errors = [.. result.Errors.Select(e => new IdentityErrorDto(e.Code, Describe(e)))];
        return ApiProblem.Create(
            StatusCodes.Status400BadRequest,
            ProblemCodes.Dogrulama,
            "Kullanıcı bilgileri kabul edilmedi.",
            new Dictionary<string, object?> { ["hatalar"] = errors });
    }

    private static string Describe(IdentityError error) => error.Code switch
    {
        "PasswordTooShort" => "Parola en az 12 karakter olmalı.",
        "PasswordRequiresUniqueChars" => "Parola yeterince çeşitli karakter içermeli.",
        "InvalidEmail" => "E-posta adresi geçersiz.",
        "InvalidUserName" => "Kullanıcı adı geçersiz.",
        _ => error.Description,
    };
}
