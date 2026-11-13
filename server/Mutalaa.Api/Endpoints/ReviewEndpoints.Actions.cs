using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.OpenApi;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Reviews;
using Mutalaa.Domain;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Inceleme kaydi uzerindeki ek eylemler (A18.4, yetki: editor ya da admin): "Uzmana gonder" (K-51 madde 2), "Ima olarak isaretle" ve "Kalip listesine ekle"
/// (K-48 madde 2). Kurallar Domain'dedir (<c>ReviewHandoff</c>, <c>LinkQueueActions</c>); burada yukleme, eszamanlilik ve yazma vardir.
/// </summary>
public static partial class ReviewEndpoints
{
    private static void MapReviewActionEndpoints(RouteGroupBuilder reviews)
    {
        reviews.MapPost("/{id:long}/uzmana-gonder", HandoffAsync)
            .WithName("sendReviewToExpert")
            .WithSummary("Açık kaydı uzmana gönderir (durum uzmanda; özgün eylem korunur). Kararı yalnız uzman rolü verir.")
            .RequireAuthorization(AuthPolicies.Editor)
            .AddOpenApiOperationTransformer(IfMatchHeader)
            .Produces<ReviewHandoffResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status428PreconditionRequired);

        reviews.MapPost("/{id:long}/ima", MarkImaAsync)
            .WithName("markReviewLinkAsIma")
            .WithSummary("Bağlantı adayının kaynak ucundan aynı hedefe yeni bir ima satırı açar (editör, onaylı, güven 1); özgün aday korunur.")
            .RequireAuthorization(AuthPolicies.Editor)
            .Produces<ImaMarkResult>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);

        reviews.MapPost("/{id:long}/kalip", AddPatternAsync)
            .WithName("addReviewLinkToPatternList")
            .WithSummary("İktibas adayının eşleşen dizisini kalıp listesine ekler (kapalı denetim kaydı) ve adayı reddeder.")
            .RequireAuthorization(AuthPolicies.Editor)
            .AddOpenApiOperationTransformer(IfMatchHeader)
            .Produces<PatternAddResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status428PreconditionRequired);
    }

    private static Task IfMatchHeader(OpenApiOperation operation, Microsoft.AspNetCore.OpenApi.OpenApiOperationTransformerContext context, CancellationToken cancellationToken)
    {
        // If-Match govdeye degil basliga baglanir (ayristirma ReviewEtag'dedir); istemci uretici gorsun diye belgelenir.
        operation.Parameters ??= [];
        operation.Parameters.Add(new OpenApiParameter
        {
            Name = "If-Match",
            In = ParameterLocation.Header,
            Required = true,
            Description = "Kaydın ETag değeri: \"{xmin}\" (yalnız güçlü ve tek etiket).",
            Schema = new OpenApiSchema { Type = JsonSchemaType.String },
        });
        return Task.CompletedTask;
    }

    private static async Task<IResult> HandoffAsync(
        long id,
        ReviewReasonBody body,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        ReviewDecider.CheckRequiredGerekce(errors, body.Gerekce);
        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        Review? review = await db.Reviews.SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (review is null)
        {
            return NotFoundReview();
        }

        if (ReviewEtag.TryParseIfMatch(http.Request, out uint expected) is { } headerError)
        {
            return headerError;
        }

        EntityEntry<Review> entry = db.Entry(review);
        if (expected != RowVersion.Get(entry))
        {
            return Stale();
        }

        RowVersion.Expect(entry, expected);

        try
        {
            ReviewHandoff.ToExpert(review, Actor(user), body.Gerekce, Now(http)).ApplyTo(review);
        }
        catch (DomainException)
        {
            // Baska bir karar araya girdiyse (surum degisti) kaybeden istek 412 alir; yoksa Domain hatasi kodu ile doner.
            if ((await ReviewChangedSinceAsync(db, [(review.Id, expected)], cancellationToken)).Length > 0)
            {
                return Stale();
            }

            throw;
        }

        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException)
        {
            return Stale();
        }

        uint xmin = RowVersion.Get(entry);
        http.Response.Headers.ETag = ReviewEtag.Format(xmin);
        return EditorJson.Ok(new ReviewHandoffResult(review.Id, review.Durum.ToLabel(), review.Eylem, xmin));
    }

    private static async Task<IResult> MarkImaAsync(
        long id,
        ReviewReasonBody body,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        ReviewDecider.CheckRequiredGerekce(errors, body.Gerekce);
        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        Review? review = await db.Reviews.AsNoTracking().SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (review is null)
        {
            return NotFoundReview();
        }

        Xref? source = await LoadLinkOfAsync(db, review, track: false, cancellationToken);
        if (source is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İncelemenin bağlantı kaydı bulunamadı.");
        }

        (Xref ima, Review audit) = LinkQueueActions.MarkIma(source, review, Guid.CreateVersion7(), Actor(user), body.Gerekce, Now(http));
        db.Xrefs.Add(ima);
        db.Reviews.Add(audit);

        // Ayni dogal anahtarli satir (ayni uc, ayni aralik, ima) varsa tekil kisit 409 cakisma verir (ApiExceptionHandler).
        await db.SaveChangesAsync(cancellationToken);

        http.Response.Headers.Location = "/api/v1/reviews/" + audit.Id.ToString(CultureInfo.InvariantCulture);
        return TypedResults.Json(
            new ImaMarkResult(ima.Id, audit.Id, ima.Type.ToLabel(), ima.Status.ToLabel()),
            EditorJson.Options,
            statusCode: StatusCodes.Status201Created);
    }

    private static async Task<IResult> AddPatternAsync(
        long id,
        ReviewReasonBody body,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        ReviewDecider.CheckRequiredGerekce(errors, body.Gerekce);
        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        Review? review = await db.Reviews.SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (review is null)
        {
            return NotFoundReview();
        }

        if (ReviewEtag.TryParseIfMatch(http.Request, out uint expected) is { } headerError)
        {
            return headerError;
        }

        EntityEntry<Review> entry = db.Entry(review);
        if (expected != RowVersion.Get(entry))
        {
            return Stale();
        }

        RowVersion.Expect(entry, expected);

        Xref? source = await LoadLinkOfAsync(db, review, track: true, cancellationToken);
        if (source is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İncelemenin bağlantı kaydı bulunamadı.");
        }

        // Kaynak birimin metni (eslesen dizinin anahtari kanitta yoksa buradan turetilir); Kur'an kaynakta aralik kelime konumudur.
        string? srcText = null;
        string? srcHash = null;
        if (source.SrcAnchor.Kind != AnchorKind.Q)
        {
            AnchorRef srcAnchor = source.SrcAnchor;
            var src = await db.Units.AsNoTracking()
                .Where(u => u.Anchor == srcAnchor)
                .Select(u => new { u.Metin, u.ContentHash })
                .SingleOrDefaultAsync(cancellationToken);
            srcText = src?.Metin;
            srcHash = src?.ContentHash;
        }

        Review audit;
        string key;
        try
        {
            (ReviewOutcome reject, audit, key) = LinkQueueActions.AddToPatternList(review, source, srcText, srcHash, Actor(user), body.Gerekce, Now(http));
            reject.ApplyTo(review);
            source.Status = reject.TargetStatus ?? XrefStatus.Red;
        }
        catch (DomainException)
        {
            if ((await ReviewChangedSinceAsync(db, [(review.Id, expected)], cancellationToken)).Length > 0)
            {
                return Stale();
            }

            throw;
        }

        db.Reviews.Add(audit);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException)
        {
            return Stale();
        }

        uint xmin = RowVersion.Get(entry);
        http.Response.Headers.ETag = ReviewEtag.Format(xmin);
        return EditorJson.Ok(new PatternAddResult(review.Id, review.Durum.ToLabel(), review.Eylem, xmin, key, audit.Id));
    }

    /// <summary>Baglanti incelemesinin xref satiri; inceleme baglanti hedefi degilse 422, anahtar bozuk ya da satir yoksa null.</summary>
    private static async Task<Xref?> LoadLinkOfAsync(IcerikDbContext db, Review review, bool track, CancellationToken cancellationToken)
    {
        if (!ReviewDecisions.IsLinkTarget(review.HedefTablo, review.Alan))
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, "Bu eylem yalniz baglanti adayi incelemesinde kullanilir.");
        }

        if (!Guid.TryParseExact(review.HedefAnahtar, "D", out Guid xrefId))
        {
            return null;
        }

        IQueryable<Xref> query = track ? db.Xrefs : db.Xrefs.AsNoTracking();
        return await query.SingleOrDefaultAsync(x => x.Id == xrefId, cancellationToken);
    }

    private static IResult NotFoundReview() =>
        ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İnceleme kaydı bulunamadı.");
}
