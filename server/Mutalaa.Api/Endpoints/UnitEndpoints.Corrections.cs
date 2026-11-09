using System.Security.Claims;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Validation;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

public static partial class UnitEndpoints
{
    private static void MapCorrectionEndpoints(RouteGroupBuilder units) =>
        units.MapPost("/{anchor}/corrections", CorrectAsync)
            .WithName("proposeUnitCorrection")
            .WithSummary("Birim metni için düzeltme önerisi açar (inceleme kuyruğuna 'oner' satırı).")
            .Produces<CorrectionResponse>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);

    private static async Task<IResult> CorrectAsync(
        string anchor,
        CorrectionRequest request,
        HttpContext httpContext,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        // Girdi: gerekce bos olamaz, en cok 2000 kod noktasi; metin bos olamaz. Ikisi de NUL ve eslesmemis vekil icermez (PostgreSQL yazamaz).
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        if (string.IsNullOrWhiteSpace(request.Gerekce))
        {
            errors["gerekce"] = ["gerekce boş olamaz."];
        }
        else if (!WritableText.TryCountCodePoints(request.Gerekce, out int gerekceLength))
        {
            errors["gerekce"] = [WritableText.Message("gerekce")];
        }
        else if (gerekceLength > ReviewDecisions.MaxGerekceLength)
        {
            errors["gerekce"] = ["gerekce en çok 2000 karakter olabilir."];
        }

        if (string.IsNullOrWhiteSpace(request.Metin))
        {
            errors["metin"] = ["metin boş olamaz."];
        }
        else
        {
            WritableText.Check(errors, "metin", request.Metin);
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        (AnchorRef? parsed, IResult? problem) = UnitAnchors.Parse(anchor);
        if (problem is not null)
        {
            return problem;
        }

        AnchorRef anchorRef = parsed!;
        string key = anchorRef.ToString();
        var target = await (
            from u in db.Units.AsNoTracking()
            join s in db.Sources.AsNoTracking() on u.SourceId equals s.Slug
            where u.Anchor == anchorRef
            select new { u.Kind, u.Metin, u.ContentHash, SourceKind = s.Tur })
            .FirstOrDefaultAsync(cancellationToken);
        if (target is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Birim bulunamadı.");
        }

        // Hazir kaynak metni (ayet birimi ya da kuran_metni kaynagi; Tanzil) bayt bayt korunur: duzeltme onerilemez.
        if (TextMutability.IsImmutable(target.Kind, target.SourceKind))
        {
            return ApiProblem.Create(
                StatusCodes.Status422UnprocessableEntity,
                ProblemCodes.DegistirilemezMetin,
                "Bu birimin metni değiştirilemez (hazır kaynak metni).");
        }

        // Ilk kayit kurali: NFC yalniz kendi urettigimiz metne uygulanir. Gecersiz Unicode ArgumentException atar.
        string canonical;
        string canonicalHash;
        try
        {
            canonical = TextCanonicalizer.Canonicalize(request.Metin);
            canonicalHash = ContentHash.Compute(canonical);
        }
        catch (ArgumentException)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]> { ["metin"] = ["metin geçerli Unicode değil."] });
        }

        if (canonical.Length == 0)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]> { ["metin"] = ["metin boş olamaz."] });
        }

        // Karsilastirma kanonikleştirmeden sonradir: yalniz bicim farki olan oneri "degisiklik yok"tur.
        if (string.Equals(canonical, target.Metin, StringComparison.Ordinal))
        {
            return ApiProblem.Validation(new Dictionary<string, string[]> { ["metin"] = ["Değişiklik yok: metin mevcut metinle aynı."] });
        }

        string? proposer = user.Identity?.Name ?? user.FindFirstValue(ClaimTypes.Email);
        if (string.IsNullOrEmpty(proposer))
        {
            return ApiProblem.Create(StatusCodes.Status401Unauthorized, ProblemCodes.OturumAcilamadi, "Oturum geçersiz.");
        }

        // Ayni birim icin iki es zamanli oneri ayni anda acik kalmasin: birim basina danismanlik kilidi + denetim ayni islemde.
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        string lockKey = "unit-correction:" + key;
        await db.Database.ExecuteSqlAsync($"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))", cancellationToken);

        bool hasOpen = await db.Reviews.AnyAsync(
            r => r.HedefTablo == ReviewTargets.Unit
                && r.HedefAnahtar == key
                && r.Alan == ReviewFields.Metin
                && r.Durum == ReviewStatus.Acik,
            cancellationToken);
        if (hasOpen)
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.Cakisma,
                "Bu birim için açık bir metin incelemesi var.");
        }

        Review review = new()
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = key,
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Editor,
            Oneren = proposer,
            Onceki = Payload(target.Metin, target.ContentHash),
            Onerilen = Payload(canonical, canonicalHash),
            Gerekce = request.Gerekce,
        };
        db.Reviews.Add(review);
        await db.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);

        httpContext.Response.Headers.Location = "/api/v1/reviews/" + review.Id.ToString(System.Globalization.CultureInfo.InvariantCulture);
        return TypedResults.Json(
            new CorrectionResponse(review.Id, ReviewStatus.Acik.ToLabel()),
            EditorJson.Options,
            statusCode: StatusCodes.Status201Created);
    }

    // jsonb yuku (K-48 bicimi): {"metin": ..., "content_hash": ...}.
    private static string Payload(string metin, string contentHash) =>
        new JsonObject { ["metin"] = metin, ["content_hash"] = contentHash }.ToJsonString(EditorJson.Options);
}
