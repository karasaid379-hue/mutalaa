using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Microsoft.AspNetCore.Identity;
using Mutalaa.Api.Problems;
using Mutalaa.Infrastructure.Identity;

namespace Mutalaa.Api.Endpoints;

public sealed record LoginRequest(
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Email,
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Parola);

/// <summary>Oturum sahibi: kimlik ve roller.</summary>
public sealed record UserSummary(string Id, string Email);

public sealed record SessionResponse(UserSummary Kullanici, IReadOnlyList<string> Roller);

public static class AuthEndpoints
{
    private const string LogCategory = "Mutalaa.Auth";

    // Kullanici yokken de ayni maliyetli parola dogrulamasi calissin (zamanlama farkindan kullanici varligi sizmasin).
    private static readonly Lazy<(PasswordHasher<EditorUser> Hasher, EditorUser User, string Hash)> Dummy = new(static () =>
    {
        PasswordHasher<EditorUser> hasher = new();
        EditorUser user = new();
        return (hasher, user, hasher.HashPassword(user, "zamanlama-icin-sahte-parola"));
    });

    public static RouteGroupBuilder MapAuthEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder auth = editor.MapGroup("/auth").WithTags("auth");

        auth.MapPost("/login", LoginAsync)
            .AllowAnonymous()
            .WithName("login")
            .Produces<SessionResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest);

        auth.MapPost("/logout", LogoutAsync)
            .WithName("logout")
            .Produces(StatusCodes.Status204NoContent);

        auth.MapGet("/me", MeAsync)
            .WithName("me")
            .Produces<SessionResponse>();

        return editor;
    }

    private static async Task<IResult> LoginAsync(
        LoginRequest request,
        UserManager<EditorUser> users,
        SignInManager<EditorUser> signIn,
        ILoggerFactory loggerFactory)
    {
        ILogger logger = loggerFactory.CreateLogger(LogCategory);
        EditorUser? user = await users.FindByEmailAsync(request.Email.Trim());
        if (user is null)
        {
            (PasswordHasher<EditorUser> hasher, EditorUser dummyUser, string hash) = Dummy.Value;
            hasher.VerifyHashedPassword(dummyUser, hash, request.Parola);
            logger.LogInformation("Oturum acma reddedildi ({Reason}).", "kullanici-yok");
            return Rejected();
        }

        // lockoutOnFailure: kilit yalniz bu yoldan isler (5 hatali denemede 15 dakika; K-37).
        SignInResult result = await signIn.CheckPasswordSignInAsync(user, request.Parola, lockoutOnFailure: true);
        if (!result.Succeeded)
        {
            logger.LogInformation("Oturum acma reddedildi ({Reason}).", result.IsLockedOut ? "kilitli" : "parola");
            return Rejected();
        }

        await signIn.SignInAsync(user, isPersistent: false);
        return TypedResults.Ok(await SessionAsync(users, user));
    }

    private static async Task<IResult> LogoutAsync(SignInManager<EditorUser> signIn)
    {
        await signIn.SignOutAsync();
        return TypedResults.NoContent();
    }

    private static async Task<IResult> MeAsync(ClaimsPrincipal principal, UserManager<EditorUser> users)
    {
        EditorUser? user = await users.GetUserAsync(principal);
        return user is null
            ? ApiProblem.Create(StatusCodes.Status401Unauthorized, ProblemCodes.OturumAcilamadi, "Oturum geçersiz.")
            : TypedResults.Ok(await SessionAsync(users, user));
    }

    internal static async Task<SessionResponse> SessionAsync(UserManager<EditorUser> users, EditorUser user)
    {
        IList<string> roles = await users.GetRolesAsync(user);
        return new SessionResponse(
            new UserSummary(user.Id, user.Email ?? string.Empty),
            [.. roles.Order(StringComparer.Ordinal)]);
    }

    // Kullanici yok, parola yanlis ya da hesap kilitli: hepsi ayni yanit.
    private static IResult Rejected() =>
        ApiProblem.Create(StatusCodes.Status401Unauthorized, ProblemCodes.OturumAcilamadi, "E-posta ya da parola hatalı.");
}
