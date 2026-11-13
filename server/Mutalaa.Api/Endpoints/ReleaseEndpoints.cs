using System.Globalization;
using System.Security.Claims;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Releases;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Persistence;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Yayin uclari (K-48 madde 7). Okuma (liste, ayrinti) editor; talep acma (olusturma, onizleme, terfi, geri alma) yalniz admin. Talepler
/// <c>release</c> satiri olarak <c>hazirlaniyor</c> acilir; isi Yayinlayici <c>watch</c> yapar (Api ile Publisher birbirine baglanmaz).
/// Ayni derleme turunde acik satir varken yeni talep 409 <c>yayin-suruyor</c> alir.
/// </summary>
public static class ReleaseEndpoints
{
    private const string BasePath = "/api/v1/releases";
    private const int DefaultLimit = 50;
    private const int MaxLimit = 200;

    public static RouteGroupBuilder MapReleaseEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder releases = editor.MapGroup("/releases").WithTags("releases");

        releases.MapGet(string.Empty, ListAsync)
            .WithName("listReleases")
            .RequireAuthorization(AuthPolicies.Editor)
            .Produces<ReleaseListResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest);

        releases.MapGet("/{id:int}", GetAsync)
            .WithName("getRelease")
            .RequireAuthorization(AuthPolicies.Editor)
            .Produces<ReleaseDetail>()
            .ProducesProblem(StatusCodes.Status404NotFound);

        RouteGroupBuilder admin = releases.MapGroup(string.Empty);
        admin.RequireAuthorization(AuthPolicies.Admin);
        admin.ProducesProblem(StatusCodes.Status403Forbidden);

        admin.MapPost(string.Empty, CreateAsync)
            .WithName("createRelease")
            .Produces<ReleaseAccepted>(StatusCodes.Status202Accepted)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status409Conflict);

        admin.MapPost("/preview", PreviewAsync)
            .WithName("previewRelease")
            .Produces<ReleasePreviewResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status409Conflict)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status503ServiceUnavailable);

        admin.MapPost("/{id:int}/promote", PromoteAsync)
            .WithName("promoteRelease")
            .Produces<ReleaseAccepted>(StatusCodes.Status202Accepted)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict);

        admin.MapPost("/{id:int}/rollback", RollbackAsync)
            .WithName("rollbackRelease")
            .Produces<ReleaseAccepted>(StatusCodes.Status202Accepted)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict);

        return editor;
    }

    // --- Okuma ---

    private static async Task<IResult> ListAsync(string? derleme, string? cursor, int? limit, IcerikDbContext db, CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);

        BuildFlavor? flavor = null;
        if (derleme is not null)
        {
            if (BuildFlavorLabels.TryParseLabel(derleme, out BuildFlavor parsed))
            {
                flavor = parsed;
            }
            else
            {
                errors["derleme"] = ["Geçersiz derleme türü. İzin verilenler: dev, internal, public."];
            }
        }

        int? afterId = null;
        if (cursor is not null)
        {
            if (ReleaseCursor.TryDecode(cursor, out int decoded))
            {
                afterId = decoded;
            }
            else
            {
                errors["cursor"] = ["Geçersiz imleç."];
            }
        }

        int take = limit ?? DefaultLimit;
        if (take is < 1 or > MaxLimit)
        {
            errors["limit"] = [string.Create(CultureInfo.InvariantCulture, $"limit 1 ile {MaxLimit} arasında olmalı.")];
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        IQueryable<Release> query = db.Releases.AsNoTracking();
        if (flavor is BuildFlavor wanted)
        {
            query = query.Where(r => r.Derleme == wanted);
        }

        if (afterId is int after)
        {
            query = query.Where(r => r.Id < after);
        }

        var rows = await query
            .OrderByDescending(r => r.Id)
            .Take(take + 1)
            .Select(r => new
            {
                r.Id,
                r.Surum,
                r.Derleme,
                r.Durum,
                r.Talep,
                r.KaynakReleaseId,
                r.Paketler,
                r.Olusturan,
                r.CreatedAt,
                r.YayinlandiAt,
                Xmin = EF.Property<uint>(r, RowVersion.Name),
            })
            .ToListAsync(cancellationToken);

        List<ReleaseSummary> items =
        [
            .. rows.Take(take).Select(r => new ReleaseSummary(
                r.Id,
                r.Surum,
                r.Derleme.ToLabel(),
                r.Durum.ToLabel(),
                r.Talep,
                r.KaynakReleaseId,
                r.Paketler,
                r.Olusturan,
                r.CreatedAt,
                r.YayinlandiAt,
                r.Xmin)),
        ];
        string? next = rows.Count > take ? ReleaseCursor.Encode(items[^1].Id) : null;
        return TypedResults.Ok(new ReleaseListResponse(items, next));
    }

    private static async Task<IResult> GetAsync(int id, HttpContext context, IcerikDbContext db, CancellationToken cancellationToken)
    {
        var found = await db.Releases.AsNoTracking()
            .Where(r => r.Id == id)
            .Select(r => new { Release = r, Xmin = EF.Property<uint>(r, RowVersion.Name) })
            .SingleOrDefaultAsync(cancellationToken);
        if (found is null)
        {
            return NotFound();
        }

        Release row = found.Release;
        context.Response.Headers.ETag = string.Create(CultureInfo.InvariantCulture, $"\"{found.Xmin}\"");
        return TypedResults.Ok(new ReleaseDetail(
            row.Id,
            row.Surum,
            row.Derleme.ToLabel(),
            row.Durum.ToLabel(),
            row.Talep,
            row.KaynakReleaseId,
            row.Paketler,
            row.Olusturan,
            row.CreatedAt,
            row.YayinlandiAt,
            row.Notlar,
            row.DataVersion,
            ParseJson(row.KapiRaporu),
            ParseJson(row.Ozetler),
            row.Manifest is null ? null : ParseJson(row.Manifest),
            found.Xmin));
    }

    // --- Talepler ---

    private static async Task<IResult> CreateAsync(
        CreateReleaseRequest request,
        ClaimsPrincipal user,
        PackCatalog catalog,
        ReleaseRepository releases,
        TimeProvider clock,
        CancellationToken cancellationToken)
    {
        ReleaseRequestResult input = ReleaseRequestRules.Validate(request.Derleme, request.Paketler, request.Notlar, catalog);
        if (!input.IsValid)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]>(input.Errors, StringComparer.Ordinal));
        }

        NewRelease newRelease = new(
            input.Flavor,
            Surum: null,
            ReleaseRequests.Yayin,
            await DataVersions.CurrentAsync(clock, null, cancellationToken),
            UserName(user),
            KaynakReleaseId: null,
            input.Packs,
            input.Notes);
        return await OpenAsync(newRelease, releases, cancellationToken);
    }

    private static async Task<IResult> PreviewAsync(
        PreviewReleaseRequest request,
        PackCatalog catalog,
        ReleasePreviewService preview,
        SecretRedactor redactor,
        CancellationToken cancellationToken)
    {
        ReleaseRequestResult input = ReleaseRequestRules.Validate(request.Derleme, request.Paketler, notlar: null, catalog);
        if (!input.IsValid)
        {
            return ApiProblem.Validation(new Dictionary<string, string[]>(input.Errors, StringComparer.Ordinal));
        }

        GatePlan? plan;
        try
        {
            plan = await preview.TryPlanAsync(input.Flavor, input.Packs ?? [], cancellationToken);
        }
        catch (GatePlanException ex)
        {
            return PlanFailure(ex, redactor);
        }

        if (plan is null)
        {
            return ApiProblem.Create(StatusCodes.Status409Conflict, ProblemCodes.Cakisma, "Başka bir önizleme sürüyor; bitince yeniden deneyin.");
        }

        JsonElement report = ParseJson(plan.Report.ToJson());
        if (plan.Report.Rejected)
        {
            return ApiProblem.Create(
                StatusCodes.Status422UnprocessableEntity,
                ProblemCodes.KaliteKapisi,
                "Kalite kapısı yayını reddetti.",
                new Dictionary<string, object?> { ["kapi_raporu"] = report });
        }

        return TypedResults.Ok(new ReleasePreviewResponse(input.Flavor.ToLabel(), report, [.. plan.Warnings.Select(redactor.Redact)]));
    }

    private static async Task<IResult> PromoteAsync(
        int id,
        ReleaseNotesRequest? request,
        ClaimsPrincipal user,
        ReleaseRepository releases,
        TimeProvider clock,
        CancellationToken cancellationToken)
    {
        if (ReleaseRequestRules.ValidateNotesOnly(request?.Notlar, out string? notes) is { } invalid)
        {
            return ApiProblem.Validation(invalid);
        }

        Release? source = await releases.GetAsync(id, cancellationToken);
        if (source is null)
        {
            return NotFound();
        }

        if (source.Durum != ReleaseStatus.Yayinlandi || source.Derleme != BuildFlavor.Internal)
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.DurumGecisiGecersiz,
                "Yalnız yayımlanmış (yayinlandi) bir internal yayın public'e terfi ettirilebilir.");
        }

        // Terfi kaynak yayinin surumunu tasir ((surum, derleme) tekil: ayni surumle public satir varsa ReleaseConflictException).
        NewRelease newRelease = new(
            BuildFlavor.Public,
            source.Surum,
            ReleaseRequests.Terfi,
            await DataVersions.CurrentAsync(clock, null, cancellationToken),
            UserName(user),
            source.Id,
            Paketler: null,
            notes);
        return await OpenAsync(newRelease, releases, cancellationToken);
    }

    private static async Task<IResult> RollbackAsync(
        int id,
        ReleaseNotesRequest? request,
        ClaimsPrincipal user,
        ReleaseRepository releases,
        TimeProvider clock,
        CancellationToken cancellationToken)
    {
        if (ReleaseRequestRules.ValidateNotesOnly(request?.Notlar, out string? notes) is { } invalid)
        {
            return ApiProblem.Validation(invalid);
        }

        Release? target = await releases.GetAsync(id, cancellationToken);
        if (target is null)
        {
            return NotFound();
        }

        if (target.Durum is not (ReleaseStatus.Yayinlandi or ReleaseStatus.GeriCekildi))
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.DurumGecisiGecersiz,
                "Yalnız yayımlanmış (yayinlandi) ya da geri çekilmiş (geri_cekildi) bir yayına geri alınabilir.");
        }

        Release? live = await releases.LatestPublishedAsync(target.Derleme, cancellationToken);
        if (live is not null && live.Id == target.Id)
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.DurumGecisiGecersiz,
                "Bu yayın zaten güncel; güncel yayına geri alınamaz.");
        }

        // Yeni satir yeni surum alir (CreateAsync verir); hedef kaynak_release_id'de durur.
        NewRelease newRelease = new(
            target.Derleme,
            Surum: null,
            ReleaseRequests.GeriAlma,
            await DataVersions.CurrentAsync(clock, null, cancellationToken),
            UserName(user),
            target.Id,
            Paketler: null,
            notes);
        return await OpenAsync(newRelease, releases, cancellationToken);
    }

    // --- Yardimcilar ---

    /// <summary>Talebi acik satir engeli ile acar: acik satir varsa 409 yayin-suruyor (yayin uzantisiyla), surum cakismasi 409 cakisma.</summary>
    private static async Task<IResult> OpenAsync(NewRelease request, ReleaseRepository releases, CancellationToken cancellationToken)
    {
        try
        {
            Release row = await releases.CreateAsync(request, requireNoOpen: true, cancellationToken);
            string location = string.Create(CultureInfo.InvariantCulture, $"{BasePath}/{row.Id}");
            return TypedResults.Accepted(
                location,
                new ReleaseAccepted(row.Id, row.Surum, row.Derleme.ToLabel(), row.Durum.ToLabel(), row.Talep));
        }
        catch (ReleaseInProgressException ex)
        {
            Release open = ex.OpenRelease;
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.YayinSuruyor,
                $"{open.Derleme.ToLabel()} derlemesinde süren bir yayın var; bitmeden yeni talep açılamaz.",
                new Dictionary<string, object?>
                {
                    ["yayin"] = new ReleaseRef(open.Id, open.Surum, open.Derleme.ToLabel(), open.Durum.ToLabel(), open.Talep),
                });
        }
        catch (ReleaseConflictException)
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.Cakisma,
                $"Bu sürümle ({request.Surum}) {request.Flavor.ToLabel()} derlemesinde başarısız olmayan bir yayın zaten var.");
        }
    }

    /// <summary>Onceki yayin bozuk (manifest yok/okunamiyor) 422 onceki-yayin-bozuk; onceki paket okunamadi (yok/ozet uyusmuyor) 503 depo-erisilemiyor.</summary>
    private static IResult PlanFailure(GatePlanException ex, SecretRedactor redactor)
    {
        string detail = redactor.Redact(ex.Message);
        return ex.Failure switch
        {
            GatePlanFailure.PreviousManifestMissing or GatePlanFailure.ManifestUnreadable =>
                ApiProblem.Create(StatusCodes.Status422UnprocessableEntity, ProblemCodes.OncekiYayinBozuk, detail),
            _ => ApiProblem.Create(StatusCodes.Status503ServiceUnavailable, ProblemCodes.DepoErisilemiyor, detail),
        };
    }

    private static IResult NotFound() =>
        ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Yayın bulunamadı.");

    private static string UserName(ClaimsPrincipal user) =>
        user.Identity?.Name is { Length: > 0 } name ? name : user.FindFirstValue(ClaimTypes.Email) ?? "bilinmiyor";

    /// <summary>Veritabanindan (jsonb) gelen metni ham JSON olarak ayristirir; bozuksa bos nesne (jsonb zaten gecerli JSON tutar).</summary>
    private static JsonElement ParseJson(string json)
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(json);
            return document.RootElement.Clone();
        }
        catch (JsonException)
        {
            using JsonDocument empty = JsonDocument.Parse("{}");
            return empty.RootElement.Clone();
        }
    }
}
