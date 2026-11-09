using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.OpenApi;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Reviews;
using Mutalaa.Domain;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Inceleme uclari (K-48; yetki: editor): kuyruk, ayrinti, istatistik, tekil karar (If-Match zorunlu) ve toplu karar
/// (ya hep ya hic). Karar kurali <c>Mutalaa.Domain.Reviews</c>'dedir; burada yukleme, eszamanlilik ve yazma vardir.
/// </summary>
public static class ReviewEndpoints
{
    public const int MaxBulk = 100;

    public static RouteGroupBuilder MapReviewEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder reviews = editor.MapGroup("/reviews").WithTags("reviews");

        reviews.MapGet(string.Empty, ListAsync)
            .WithName("listReviews")
            .Produces<ReviewListResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest);

        reviews.MapGet("/stats", StatsAsync)
            .WithName("getReviewStats")
            .Produces<ReviewStatsResponse>();

        reviews.MapGet("/{id:long}", GetAsync)
            .WithName("getReview")
            .Produces<ReviewDetailDto>()
            .ProducesProblem(StatusCodes.Status404NotFound);

        reviews.MapPost("/{id:long}/decision", DecideAsync)
            .WithName("decideReview")
            .AddOpenApiOperationTransformer((operation, _, _) =>
            {
                // If-Match gövdeye değil başlığa bağlanır (ayrıştırma ReviewEtag'dedir); istemci üreticisi görsün diye belgelenir.
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
            })
            .Produces<ReviewDecisionResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status428PreconditionRequired);

        reviews.MapPost("/decisions", DecideBulkAsync)
            .WithName("decideReviews")
            .Produces<BulkDecisionResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);

        return editor;
    }

    private static async Task<IResult> ListAsync(
        [FromQuery(Name = "hedef_tablo")] string? hedefTablo,
        string? alan,
        string? durum,
        string? cursor,
        int? limit,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);

        if (hedefTablo is not null && !ReviewTargets.IsKnown(hedefTablo))
        {
            errors["hedef_tablo"] = [$"Geçersiz hedef_tablo. İzin verilenler: {string.Join(", ", ReviewTargets.All)}."];
        }

        ReviewStatus status = ReviewStatus.Acik;
        if (durum is not null && !ReviewStatusLabels.TryParseLabel(durum, out status))
        {
            errors["durum"] = ["Geçersiz durum. İzin verilenler: acik, onaylandi, reddedildi, geri_alindi."];
        }

        int take = limit ?? ReviewQueries.DefaultLimit;
        if (take is < 1 or > ReviewQueries.MaxLimit)
        {
            errors["limit"] = [$"limit 1 ile {ReviewQueries.MaxLimit} arasında olmalı."];
        }

        (DateTime CreatedAt, long Id)? after = null;
        if (cursor is not null)
        {
            if (ReviewCursor.TryDecode(cursor, out DateTime createdAt, out long id))
            {
                after = (createdAt, id);
            }
            else
            {
                errors["cursor"] = ["İmleç geçersiz."];
            }
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        return TypedResults.Ok(await ReviewQueries.ListAsync(db, hedefTablo, alan, status, after, take, cancellationToken));
    }

    private static async Task<IResult> StatsAsync(IcerikDbContext db, CancellationToken cancellationToken) =>
        TypedResults.Ok(await ReviewQueries.StatsAsync(db, cancellationToken));

    private static async Task<IResult> GetAsync(long id, HttpContext http, IcerikDbContext db, CancellationToken cancellationToken)
    {
        (ReviewDetailDto? detail, uint xmin) = await ReviewQueries.GetAsync(db, id, cancellationToken);
        if (detail is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İnceleme kaydı bulunamadı.");
        }

        http.Response.Headers.ETag = ReviewEtag.Format(xmin);
        return TypedResults.Ok(detail);
    }

    private static async Task<IResult> DecideAsync(
        long id,
        DecisionBody body,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        if (!ReviewDecider.TryParseKarar(body.Karar, out bool approve))
        {
            return KararError("karar");
        }

        Review? review = await db.Reviews.SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (review is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İnceleme kaydı bulunamadı.");
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

        PreparedDecision prepared = await ReviewDecider.ApplyAsync(
            db,
            review,
            new DecisionInput(approve, body.Duzenlenen, body.Gerekce),
            Actor(user),
            Now(http),
            cancellationToken);

        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException)
        {
            // Basarisiz satir review de hedef de olabilir; ikisi de istemcinin yeniden okumasini ister.
            return Stale();
        }

        uint xmin = RowVersion.Get(entry);
        http.Response.Headers.ETag = ReviewEtag.Format(xmin);
        return TypedResults.Ok(new ReviewDecisionResult(
            review.Id,
            review.Durum.ToLabel(),
            review.Eylem,
            ReviewDecider.IsSecondApprovalPending(prepared),
            ReviewDecider.TargetStateLabel(prepared.Target),
            xmin));
    }

    private static async Task<IResult> DecideBulkAsync(
        BulkDecisionBody body,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        IReadOnlyList<BulkDecisionItem> items = body.Kararlar ?? [];
        if (items.Count is < 1 or > MaxBulk)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]> { ["kararlar"] = [$"kararlar 1 ile {MaxBulk} arasında öğe içermeli."] });
        }

        if (items.Any(i => !ReviewDecider.TryParseKarar(i.Karar, out _)))
        {
            return KararError("kararlar");
        }

        long[] ids = [.. items.Select(i => i.Id)];
        if (ids.Distinct().Count() != ids.Length)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]> { ["kararlar"] = ["Aynı kimlik birden çok kez verilemez."] });
        }

        // Hepsi izlenerek yuklenir; sonra tek SaveChanges: ya hep ya hic.
        Dictionary<long, Review> reviews = await db.Reviews
            .Where(r => ids.Contains(r.Id))
            .ToDictionaryAsync(r => r.Id, cancellationToken);

        long[] missing = [.. ids.Where(i => !reviews.ContainsKey(i))];
        if (missing.Length > 0)
        {
            return ApiProblem.Create(
                StatusCodes.Status404NotFound,
                ProblemCodes.Bulunamadi,
                "Bazı inceleme kayıtları bulunamadı; hiçbir karar uygulanmadı.",
                Kimlikler(missing));
        }

        HashSet<(string, string)> targets = new(reviews.Count);
        foreach (long id in ids)
        {
            Review review = reviews[id];
            if (!targets.Add((review.HedefTablo, review.HedefAnahtar)))
            {
                return ApiProblem.Validation(
                    new Dictionary<string, string[]> { ["kararlar"] = ["Aynı hedef için birden çok karar verilemez."] });
            }
        }

        // Once bellekte surum karsilastirmasi: tutmayan varsa hicbiri uygulanmaz ve tam liste doner.
        long[] stale = [.. items.Where(i => i.Xmin != RowVersion.Get(db.Entry(reviews[i.Id]))).Select(i => i.Id)];
        if (stale.Length > 0)
        {
            return Stale(stale);
        }

        string actor = Actor(user);
        DateTime now = Now(http);
        List<(long Id, PreparedDecision Prepared)> prepared = new(items.Count);
        foreach (BulkDecisionItem item in items)
        {
            Review review = reviews[item.Id];
            RowVersion.Expect(db.Entry(review), item.Xmin);
            try
            {
                _ = ReviewDecider.TryParseKarar(item.Karar, out bool approve);
                prepared.Add((item.Id, await ReviewDecider.ApplyAsync(
                    db,
                    review,
                    new DecisionInput(approve, item.Duzenlenen, item.Gerekce),
                    actor,
                    now,
                    cancellationToken)));
            }
            catch (DomainException e) when (DomainExceptionHandler.TryGetStatus(e.Code, out int status))
            {
                // Hicbir sey kaydedilmedi; baglam atilir. Hata kodu Domain'in kodudur, hangi kayit oldugu uzantida.
                return ApiProblem.Create(
                    status,
                    e.Code,
                    e.Message,
                    new Dictionary<string, object?> { ["kimlik"] = item.Id });
            }
        }

        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException e)
        {
            Dictionary<object, long> owners = new(ReferenceEqualityComparer.Instance);
            foreach ((long id, PreparedDecision p) in prepared)
            {
                owners[p.Review] = id;
                owners[p.Target] = id;
            }

            long[] failed = [.. e.Entries
                .Select(entry => owners.TryGetValue(entry.Entity, out long id) ? id : 0L)
                .Where(id => id != 0)
                .Distinct()
                .Order()];
            return Stale(failed.Length > 0 ? failed : ids);
        }

        List<BulkDecisionOutcome> results = [.. prepared.Select(p => new BulkDecisionOutcome(
            p.Id,
            p.Prepared.Review.Durum.ToLabel(),
            p.Prepared.Review.Eylem,
            RowVersion.Get(db.Entry(p.Prepared.Review))))];
        return TypedResults.Ok(new BulkDecisionResult(results));
    }

    private static string Actor(ClaimsPrincipal user) => user.Identity?.Name ?? string.Empty;

    private static DateTime Now(HttpContext http) =>
        (http.RequestServices.GetService<TimeProvider>() ?? TimeProvider.System).GetUtcNow().UtcDateTime;

    private static Dictionary<string, object?> Kimlikler(long[] ids) => new(StringComparer.Ordinal) { ["kimlikler"] = ids };

    /// <summary>412 surum-uyusmazligi; toplu karar tutmayan kimliklerin tam listesini <c>kimlikler</c> uzantisinda verir.</summary>
    private static IResult Stale(long[]? ids = null) =>
        ApiProblem.Create(
            StatusCodes.Status412PreconditionFailed,
            ProblemCodes.SurumUyusmazligi,
            "Kayıt siz okuduktan sonra değişti; yenileyip yeniden deneyin.",
            ids is null ? null : Kimlikler(ids));

    private static IResult KararError(string field) =>
        ApiProblem.Validation(new Dictionary<string, string[]> { [field] = ["karar \"onaylandi\" ya da \"reddedildi\" olmalı."] });
}
