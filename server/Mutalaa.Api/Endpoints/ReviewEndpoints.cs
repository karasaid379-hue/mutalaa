using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.OpenApi;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Reviews;
using Mutalaa.Api.Validation;
using Mutalaa.Domain;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Identity;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Inceleme uclari (K-48): kuyruk, ayrinti, istatistik ve tekil karar editor, admin ve uzman icindir (tekil karar If-Match ister; kaydin durumuna gore
/// yalniz yetkili rol karar verir: <c>acik</c> editor ya da admin, <c>uzmanda</c> uzman). Toplu karar (ya hep ya hic), uzmana gonder, ima ve kalip uclari
/// yalniz editor ya da adminindir. Karar kurali <c>Mutalaa.Domain.Reviews</c>'dedir; burada yukleme, eszamanlilik ve yazma vardir.
/// </summary>
public static partial class ReviewEndpoints
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
            .ProducesProblem(StatusCodes.Status403Forbidden)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status428PreconditionRequired);

        reviews.MapPost("/decisions", DecideBulkAsync)
            .WithName("decideReviews")
            .RequireAuthorization(AuthPolicies.Editor)
            .Produces<BulkDecisionResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status403Forbidden)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity);

        MapReviewActionEndpoints(reviews);

        return editor;
    }

    private static async Task<IResult> ListAsync(
        [FromQuery(Name = "hedef_tablo")] string? hedefTablo,
        string? alan,
        string? durum,
        string? kaynak,
        string? asama,
        string? sira,
        string? sinif,
        [FromQuery(Name = "onay_yolu")] string? onayYolu,
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
            errors["durum"] = ["Geçersiz durum. İzin verilenler: acik, onaylandi, reddedildi, geri_alindi, uzmanda."];
        }

        WritableText.Check(errors, "alan", alan);

        if (kaynak is not null && string.IsNullOrWhiteSpace(kaynak))
        {
            errors["kaynak"] = ["kaynak boş olamaz."];
        }
        else
        {
            WritableText.Check(errors, "kaynak", kaynak);
        }

        ReviewStage? stage = null;
        if (asama is not null)
        {
            if (string.Equals(asama, "ilk", StringComparison.Ordinal))
            {
                stage = ReviewStage.Ilk;
            }
            else if (string.Equals(asama, "ikinci", StringComparison.Ordinal))
            {
                stage = ReviewStage.Ikinci;
            }
            else
            {
                errors["asama"] = ["Geçersiz asama. İzin verilenler: ilk, ikinci."];
            }
        }

        ReviewSort sort = ReviewSort.Olusturma;
        if (sira is not null)
        {
            if (string.Equals(sira, "dalga", StringComparison.Ordinal))
            {
                sort = ReviewSort.Dalga;
                if (hedefTablo is not (ReviewTargets.Lemma or ReviewTargets.LemmaGloss))
                {
                    errors["sira"] = ["sira=dalga yalnız hedef_tablo lemma ya da lemma_gloss iken geçerlidir."];
                }
            }
            else if (string.Equals(sira, "sinif", StringComparison.Ordinal))
            {
                sort = ReviewSort.Sinif;
                if (!string.Equals(hedefTablo, ReviewTargets.Xref, StringComparison.Ordinal))
                {
                    errors["sira"] = ["sira=sinif yalnız hedef_tablo xref iken geçerlidir."];
                }
            }
            else if (!string.Equals(sira, "olusturma", StringComparison.Ordinal))
            {
                errors["sira"] = ["Geçersiz sira. İzin verilenler: olusturma, dalga, sinif."];
            }
        }

        LinkCandidateClass? wantedClass = null;
        if (sinif is not null)
        {
            if (!LinkCandidateClassLabels.TryParseLabel(sinif, out LinkCandidateClass parsedClass))
            {
                errors["sinif"] = ["Geçersiz sinif. İzin verilenler: tutarsiz, toplu, gri, diger."];
            }
            else if (!string.Equals(hedefTablo, ReviewTargets.Xref, StringComparison.Ordinal))
            {
                errors["sinif"] = ["sinif yalnız hedef_tablo xref iken geçerlidir."];
            }
            else
            {
                wantedClass = parsedClass;
            }
        }

        ApprovalFilter? wantedPath = null;
        if (onayYolu is not null)
        {
            ApprovalFilter? parsedPath = onayYolu switch
            {
                "otomatik" => ApprovalFilter.Otomatik,
                "editor" => ApprovalFilter.Editor,
                "aday" => ApprovalFilter.Aday,
                _ => null,
            };
            if (parsedPath is null)
            {
                errors["onay_yolu"] = ["Geçersiz onay_yolu. İzin verilenler: otomatik, editor, aday."];
            }
            else if (!string.Equals(hedefTablo, ReviewTargets.Lemma, StringComparison.Ordinal))
            {
                errors["onay_yolu"] = ["onay_yolu yalnız hedef_tablo lemma iken geçerlidir."];
            }
            else
            {
                wantedPath = parsedPath;
            }
        }

        int take = limit ?? ReviewQueries.DefaultLimit;
        if (take is < 1 or > ReviewQueries.MaxLimit)
        {
            errors["limit"] = [$"limit 1 ile {ReviewQueries.MaxLimit} arasında olmalı."];
        }

        (DateTime CreatedAt, long Id)? after = null;
        WaveCursor? waveAfter = null;
        ClassCursor? classAfter = null;
        if (cursor is not null)
        {
            if (sort == ReviewSort.Sinif)
            {
                if (ReviewCursor.TryDecodeClass(cursor, out ClassCursor classCursor))
                {
                    classAfter = classCursor;
                }
                else
                {
                    errors["cursor"] = ["İmleç geçersiz."];
                }
            }
            else if (sort == ReviewSort.Dalga)
            {
                // Imlec turu etiketlidir: olusturma imleci dalga sirasinda (ve dalga imleci olusturma sirasinda) gecersizdir.
                if (ReviewCursor.TryDecodeWave(cursor, out WaveCursor wave))
                {
                    waveAfter = wave;
                }
                else
                {
                    errors["cursor"] = ["İmleç geçersiz."];
                }
            }
            else if (ReviewCursor.TryDecode(cursor, out DateTime createdAt, out long id))
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

        return TypedResults.Ok(await ReviewQueries.ListAsync(
            db, hedefTablo, alan, status, kaynak, stage, sort, wantedClass, wantedPath, after, waveAfter, classAfter, take, cancellationToken));
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

        Dictionary<string, string[]> textErrors = new(StringComparer.Ordinal);
        ReviewDecider.CheckText(textErrors, string.Empty, body.Gerekce, body.Duzenlenen);
        if (textErrors.Count > 0)
        {
            return ApiProblem.Validation(textErrors);
        }

        Review? review = await db.Reviews.SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (review is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "İnceleme kaydı bulunamadı.");
        }

        if (!ReviewRoles.CanDecide(review.Durum, IsEditorOrAdmin(user), user.IsInRole(Roles.Uzman)))
        {
            return Forbidden(review.Durum);
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

        PreparedDecision prepared;
        try
        {
            prepared = await ReviewDecider.ApplyAsync(
                db,
                review,
                new DecisionInput(approve, body.Duzenlenen, body.Gerekce),
                Actor(user),
                Now(http),
                cancellationToken);
        }
        catch (DomainException)
        {
            // Inceleme satiri okunduktan sonra baska bir karar commit edildi (hedef artik onceki karari yansitiyor): kaybeden istek
            // bayat ETag ile gelmistir, Domain kuralinin 409/422'si degil 412 doner.
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

        int nullIndex = IndexOfNull(items);
        if (nullIndex >= 0)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]>
            {
                [string.Create(CultureInfo.InvariantCulture, $"kararlar[{nullIndex}]")] = ["kararlar öğesi null olamaz."],
            });
        }

        if (items.Any(i => !ReviewDecider.TryParseKarar(i.Karar, out _)))
        {
            return KararError("kararlar");
        }

        Dictionary<string, string[]> textErrors = new(StringComparer.Ordinal);
        for (int i = 0; i < items.Count; i++)
        {
            ReviewDecider.CheckText(textErrors, string.Create(CultureInfo.InvariantCulture, $"kararlar[{i}]."), items[i].Gerekce, items[i].Duzenlenen);
        }

        if (textErrors.Count > 0)
        {
            return ApiProblem.Validation(textErrors);
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

        foreach (long id in ids)
        {
            Review review = reviews[id];
            if (!ReviewRoles.CanDecide(review.Durum, IsEditorOrAdmin(user), user.IsInRole(Roles.Uzman)))
            {
                return Forbidden(review.Durum, new Dictionary<string, object?> { ["kimlik"] = id });
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
                    new DecisionInput(approve, item.Duzenlenen, item.Gerekce, Bulk: true),
                    actor,
                    now,
                    cancellationToken)));
            }
            catch (DomainException e)
            {
                // Baska bir karar araya girdiyse (surum degisti) kaybeden toplu istek 412 alir; yoksa Domain hatasi kodu ile doner.
                (long Id, uint Xmin)[] sent = [.. items.Select(i => (i.Id, i.Xmin))];
                long[] changed = await ReviewChangedSinceAsync(db, sent, cancellationToken);
                if (changed.Length > 0)
                {
                    return Stale(changed);
                }

                if (!DomainExceptionHandler.TryGetStatus(e.Code, out int status))
                {
                    throw;
                }

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

    /// <summary>
    /// Istemcinin okudugu surumden beri veritabaninda degisen inceleme satirlari (kimlik listesi). Yeni, izlenmeyen bir okuma yapar:
    /// hedefi sonradan okuyan istek, baska karar commit edildikten sonra Domain hatasi alirsa 412'yi dogru kapatmak icin kullanilir.
    /// </summary>
    private static async Task<long[]> ReviewChangedSinceAsync(
        IcerikDbContext db,
        IReadOnlyCollection<(long Id, uint Xmin)> expected,
        CancellationToken cancellationToken)
    {
        long[] ids = [.. expected.Select(e => e.Id)];
        var rows = await db.Reviews.AsNoTracking()
            .Where(r => ids.Contains(r.Id))
            .Select(r => new { r.Id, Xmin = EF.Property<uint>(r, RowVersion.Name) })
            .ToListAsync(cancellationToken);
        Dictionary<long, uint> current = rows.ToDictionary(r => r.Id, r => r.Xmin);
        return [.. expected.Where(e => !current.TryGetValue(e.Id, out uint now) || now != e.Xmin).Select(e => e.Id).Order()];
    }

    private static int IndexOfNull(IReadOnlyList<BulkDecisionItem> items)
    {
        for (int i = 0; i < items.Count; i++)
        {
            if (items[i] is null)
            {
                return i;
            }
        }

        return -1;
    }

    private static string Actor(ClaimsPrincipal user) => user.Identity?.Name ?? string.Empty;

    private static bool IsEditorOrAdmin(ClaimsPrincipal user) => user.IsInRole(Roles.Editor) || user.IsInRole(Roles.Admin);

    /// <summary>403 yetki-yok: kaydin durumuna gore karar verecek rol yok (acik: editor ya da admin; uzmanda: uzman).</summary>
    private static IResult Forbidden(ReviewStatus durum, IReadOnlyDictionary<string, object?>? extensions = null) =>
        ApiProblem.Create(
            StatusCodes.Status403Forbidden,
            ProblemCodes.YetkiYok,
            durum == ReviewStatus.Uzmanda
                ? "Uzmana gönderilen kaydın kararını yalnız uzman rolü verir."
                : "Bu kaydın kararını editör ya da yönetici verir; uzman rolü yalnız uzmana gönderilen kayıtlara karar verir.",
            extensions);

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
