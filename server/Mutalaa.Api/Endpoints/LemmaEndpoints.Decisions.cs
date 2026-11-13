using System.Globalization;
using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Reviews;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>Otomatik onaya itiraz gövdesi (K-51 madde 9): <c>gerekce</c> zorunlu.</summary>
public sealed record LemmaObjectionRequest(string? Gerekce);

/// <summary>Açılan itiraz kaydı: <c>id</c> review kimliği, <c>durum</c> her zaman <c>acik</c>.</summary>
public sealed record LemmaObjectionResponse(long Id, string Durum);

/// <summary>Etimolojik işaret gövdesi: yeni <c>etymological_only</c> değeri ve gerekçe, ikisi de zorunlu.</summary>
public sealed record EtymologyMarkRequest(bool? EtymologicalOnly, string? Gerekce);

/// <summary>Etimolojik işaret sonucu: denetim izi review kimliği, yeni değer, lemmanın onay yolu (hep <c>editor</c>) ve durumu.</summary>
public sealed record EtymologyMarkResponse(long ReviewId, bool EtymologicalOnly, string OnayYolu, string Status);

public static partial class LemmaEndpoints
{
    private static void MapLemmaDecisionEndpoints(RouteGroupBuilder lemmas)
    {
        lemmas.MapPost("/{id:int}/itiraz", ObjectAsync)
            .WithName("objectToLemmaApproval")
            .RequireAuthorization(AuthPolicies.Editor)
            .WithSummary("Otomatik onaylı Türkçe lemma eşlemesine itiraz eder (editör incelemesi açar; başka bir editör onaylarsa lemma adaya döner).")
            .Produces<LemmaObjectionResponse>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);

        lemmas.MapPost("/{id:int}/etimolojik-isaret", MarkEtymologicalAsync)
            .WithName("markLemmaEtymological")
            .RequireAuthorization(AuthPolicies.Editor)
            .WithSummary("Onaylı Türkçe lemmanın 'yalnızca etimolojik' işaretini editör kararıyla değiştirir (otomatik onaylıda onay yolu editör olur).")
            .Produces<EtymologyMarkResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);
    }

    private static LemmaReviewState StateOf(Lemma row) =>
        new(row.Lang, row.RootId, row.ArLemmaId, row.EtymologicalOnly, row.Origin, row.OnayYolu);

    private static async Task<IResult> ObjectAsync(
        int id,
        LemmaObjectionRequest request,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        ReviewDecider.CheckRequiredGerekce(errors, request.Gerekce);
        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        string? actor = user.Identity?.Name ?? user.FindFirstValue(ClaimTypes.Email);
        if (string.IsNullOrEmpty(actor))
        {
            return ApiProblem.Create(StatusCodes.Status401Unauthorized, ProblemCodes.OturumAcilamadi, "Oturum geçersiz.");
        }

        Lemma? row = await db.Lemmas.AsNoTracking().SingleOrDefaultAsync(l => l.Id == id, cancellationToken);
        if (row is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Lemma bulunamadı.");
        }

        // Aynı lemma için iki eş zamanlı itiraz açık kalmasın: lemma başına danışma kilidi + denetim aynı işlemde.
        string key = id.ToString(CultureInfo.InvariantCulture);
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        string lockKey = "lemma-objection:" + key;
        await db.Database.ExecuteSqlAsync($"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))", cancellationToken);

        List<string?> openProposals = await db.Reviews.AsNoTracking()
            .Where(r => r.HedefTablo == ReviewTargets.Lemma
                && r.HedefAnahtar == key
                && r.Alan == ReviewFields.KokEslemesi
                && r.Durum == ReviewStatus.Acik)
            .Select(r => r.Onerilen)
            .ToListAsync(cancellationToken);
        bool hasOpenObjection = openProposals.Any(LemmaMappingPayload.IsObjection);

        Review review = LemmaObjections.Open(id, row.Status, StateOf(row), actor, request.Gerekce, hasOpenObjection);
        db.Reviews.Add(review);
        await db.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);

        http.Response.Headers.Location = "/api/v1/reviews/" + review.Id.ToString(CultureInfo.InvariantCulture);
        return TypedResults.Json(
            new LemmaObjectionResponse(review.Id, ReviewStatus.Acik.ToLabel()),
            EditorJson.Options,
            statusCode: StatusCodes.Status201Created);
    }

    private static async Task<IResult> MarkEtymologicalAsync(
        int id,
        EtymologyMarkRequest request,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        ReviewDecider.CheckRequiredGerekce(errors, request.Gerekce);
        if (request.EtymologicalOnly is null)
        {
            errors["etymological_only"] = ["etymological_only zorunludur (true ya da false)."];
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        string? actor = user.Identity?.Name ?? user.FindFirstValue(ClaimTypes.Email);
        if (string.IsNullOrEmpty(actor))
        {
            return ApiProblem.Create(StatusCodes.Status401Unauthorized, ProblemCodes.OturumAcilamadi, "Oturum geçersiz.");
        }

        // İzlenen satır: lemma xmin eşzamanlılık belirteci taşır; araya giren karar 412 verir.
        Lemma? row = await db.Lemmas.SingleOrDefaultAsync(l => l.Id == id, cancellationToken);
        if (row is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Lemma bulunamadı.");
        }

        DateTime now = (http.RequestServices.GetService<TimeProvider>() ?? TimeProvider.System).GetUtcNow().UtcDateTime;
        EtymologyMark mark = LemmaEtymology.Apply(id, row.Status, StateOf(row), request.EtymologicalOnly!.Value, actor, request.Gerekce, now);
        ReviewDecider.ApplyMapping(row, mark.Update);
        db.Reviews.Add(mark.Review);
        await db.SaveChangesAsync(cancellationToken);

        return EditorJson.Ok(new EtymologyMarkResponse(mark.Review.Id, row.EtymologicalOnly, row.OnayYolu ?? LemmaApprovalPaths.Editor, row.Status.ToLabel()));
    }
}
