using System.Security.Claims;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Primitives;
using Microsoft.OpenApi;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Validation;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Persistence;
using Mutalaa.Infrastructure.Reviews;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Risale kitap katalogu (<c>shared/data/risale-kitaplar.json</c>, Infrastructure'a gomulu kaynak). Tek kayit: testler kitap listesini
/// (ornegin dogrulanmis bir kitap) bunu degistirerek verir; elle ikinci bir kitap listesi yazilmaz.
/// </summary>
public sealed record RisaleBookCatalog(IReadOnlyList<RisaleBook> Books)
{
    public RisaleBook? Find(string slug) => Books.FirstOrDefault(b => string.Equals(b.Slug, slug, StringComparison.Ordinal));
}

/// <summary>Katalogdaki kitap ve birim sayilari (liste).</summary>
public record RisaleBookDto(
    string Slug,
    string Baslik,
    string Dil,
    string Yon,
    bool Dogrulandi,
    long BirimSayisi,
    long TaslakSayisi,
    long OnayliSayisi);

/// <summary>Kitap ayrintisi: kitap ozeti (If-Match degeri) ve onkosul gostergeleri.</summary>
public sealed record RisaleBookDetailDto(
    string Slug,
    string Baslik,
    string Dil,
    string Yon,
    bool Dogrulandi,
    long BirimSayisi,
    long TaslakSayisi,
    long OnayliSayisi,
    string Ozet,
    bool GbutKaniti,
    long KanitsizBirimSayisi)
    : RisaleBookDto(Slug, Baslik, Dil, Yon, Dogrulandi, BirimSayisi, TaslakSayisi, OnayliSayisi);

/// <summary>Kitap onayi govdesi. <c>ornek_okuma_yapildi</c> tur 2 (orneklem okumasi) beyanidir; <c>true</c> degilse 422 <c>on-kosul-eksik</c>.</summary>
public sealed record RisaleBookApproveBody(string? Gerekce, bool? OrnekOkumaYapildi);

public sealed record RisaleBookApproveResult(string Kitap, long ReviewId, int OnaylananBirimSayisi, string Ozet);

/// <summary>
/// Risale kitap uclari (K-51 madde 11). Okuma (liste, ayrinti) editor; kitabi toplu onaylama yalniz admin. Onay kurali
/// <c>Mutalaa.Domain.Reviews.RisaleBookApproval</c>'dadir; burada katalog cozumu, If-Match, tek islem ve yazma vardir. Ikinci onay kurali
/// Risale'ye uygulanmaz (K-48: yalniz meal ve tefsir).
/// </summary>
public static class RisaleBookEndpoints
{
    public static RouteGroupBuilder MapRisaleBookEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder books = editor.MapGroup("/risale/books").WithTags("risale");

        books.MapGet(string.Empty, ListAsync)
            .WithName("listRisaleBooks")
            .WithSummary("Risale kitaplarını (katalog sırasıyla) birim ve durum sayılarıyla listeler.")
            .Produces<IReadOnlyList<RisaleBookDto>>();

        books.MapGet("/{kitap}", GetAsync)
            .WithName("getRisaleBook")
            .WithSummary("Tek kitabın ayrıntısını, kitap özetini (ETag) ve onay önkoşullarını döndürür.")
            .Produces<RisaleBookDetailDto>()
            .ProducesProblem(StatusCodes.Status404NotFound);

        books.MapPost("/{kitap}/approve", ApproveAsync)
            .WithName("approveRisaleBook")
            .WithSummary("Kitabın bütün taslak birimlerini tek işlemde onaylar (yalnız admin; If-Match kitap özeti).")
            .RequireAuthorization(AuthPolicies.Admin)
            .AddOpenApiOperationTransformer((operation, _, _) =>
            {
                operation.Parameters ??= [];
                operation.Parameters.Add(new OpenApiParameter
                {
                    Name = "If-Match",
                    In = ParameterLocation.Header,
                    Required = true,
                    Description = "Kitap özeti (GET /risale/books/{kitap} ETag değeri): \"{64 küçük harf onaltılık}\" (yalnız güçlü ve tek etiket).",
                    Schema = new OpenApiSchema { Type = JsonSchemaType.String },
                });
                return Task.CompletedTask;
            })
            .Produces<RisaleBookApproveResult>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status403Forbidden)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status412PreconditionFailed)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .ProducesProblem(StatusCodes.Status428PreconditionRequired);

        return editor;
    }

    private static async Task<IResult> ListAsync(RisaleBookCatalog catalog, IcerikDbContext db, CancellationToken cancellationToken)
    {
        IReadOnlyDictionary<string, RisaleBookCounts> counts = await RisaleBookStore.CountsAsync(db, cancellationToken);
        List<RisaleBookDto> result = [.. catalog.Books.Select(b =>
        {
            counts.TryGetValue(b.Slug, out RisaleBookCounts? c);
            return new RisaleBookDto(b.Slug, b.Title, b.Language, b.Direction, b.Verified, c?.Total ?? 0, c?.Draft ?? 0, c?.Approved ?? 0);
        })];
        return EditorJson.Ok(result);
    }

    private static async Task<IResult> GetAsync(string kitap, HttpContext http, RisaleBookCatalog catalog, IcerikDbContext db, CancellationToken cancellationToken)
    {
        if (catalog.Find(kitap) is not { } book)
        {
            return NotFound();
        }

        List<RisaleBookUnit> units = await RisaleBookStore.LoadUnitsAsync(db, book.Slug, cancellationToken);
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(book.Verified, units);
        http.Response.Headers.ETag = RisaleBookApproval.FormatEtag(assessment.Digest);
        return EditorJson.Ok(new RisaleBookDetailDto(
            book.Slug,
            book.Title,
            book.Language,
            book.Direction,
            book.Verified,
            assessment.Total,
            assessment.Draft,
            assessment.Approved,
            assessment.Digest,
            assessment.GbutEvidence,
            assessment.WithoutEvidence));
    }

    private static async Task<IResult> ApproveAsync(
        string kitap,
        RisaleBookApproveBody body,
        HttpContext http,
        ClaimsPrincipal user,
        RisaleBookCatalog catalog,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        if (catalog.Find(kitap) is not { } book)
        {
            return NotFound();
        }

        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        if (RisaleBookApproval.CheckGerekce(body.Gerekce) is { } gerekceError)
        {
            errors["gerekce"] = [gerekceError];
        }
        else
        {
            WritableText.Check(errors, "gerekce", body.Gerekce);
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        if (ParseIfMatch(http.Request, out string expectedDigest) is { } headerError)
        {
            return headerError;
        }

        string actor = user.Identity?.Name ?? string.Empty;
        DateTime now = (http.RequestServices.GetService<TimeProvider>() ?? TimeProvider.System).GetUtcNow().UtcDateTime;
        bool sampleReading = body.OrnekOkumaYapildi == true;

        // Tek islem: kitap kilitlenir, durum bu kilit altinda okunur, birimler ve review satiri birlikte yazilir ya da hic yazilmaz.
        // Donen her problem yanitinda islem geri alinir (using).
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        await RisaleBookStore.LockAsync(db, book.Slug, cancellationToken);
        List<RisaleBookUnit> units = await RisaleBookStore.LoadUnitsAsync(db, book.Slug, cancellationToken);
        RisaleBookAssessment assessment = RisaleBookApproval.Assess(book.Verified, units);
        RisaleApprovalVerdict verdict = RisaleBookApproval.Decide(assessment, expectedDigest, sampleReading);

        switch (verdict.Outcome)
        {
            case RisaleApprovalOutcome.Stale:
                return Stale();
            case RisaleApprovalOutcome.PrerequisitesMissing:
                return ApiProblem.Create(
                    StatusCodes.Status422UnprocessableEntity,
                    ProblemCodes.OnKosulEksik,
                    "Kitap onayı için önkoşullar eksik: " + string.Join(", ", verdict.Missing) + ".",
                    new Dictionary<string, object?> { ["eksikler"] = verdict.Missing });
            case RisaleApprovalOutcome.NothingToApprove:
                return ApiProblem.Create(
                    StatusCodes.Status422UnprocessableEntity,
                    ProblemCodes.OnaylanacakBirimYok,
                    "Kitapta onaylanacak taslak birim yok.");
            default:
                break;
        }

        string[] drafts = [.. units.Where(u => u.MetinDurumu == TextStatus.Taslak).Select(u => u.Anchor)];
        int approved = await RisaleBookStore.ApproveDraftsAsync(db, drafts, now, cancellationToken);
        if (approved != drafts.Length)
        {
            // Kilit altinda olmamasi gereken sapma (kitap satirlari kilitli); sessizce eksik onaylamak yerine istemci yeniden okusun.
            return Stale();
        }

        Review review = new()
        {
            HedefTablo = ReviewTargets.Source,
            HedefAnahtar = RisaleBookApproval.TargetKey(book.Slug),
            Alan = ReviewFields.MetinDurumu,
            Eylem = ReviewActions.Onayla,
            Onceki = new JsonObject
            {
                ["ozet"] = assessment.Digest,
                ["birim_sayisi"] = assessment.Total,
                ["taslak_sayisi"] = assessment.Draft,
                ["onayli_sayisi"] = assessment.Approved,
            }.ToJsonString(EditorJson.Options),
            Onerilen = new JsonObject
            {
                ["metin_durumu"] = "onayli",
                ["onaylanan_birim_sayisi"] = approved,
                ["gbut_kaniti"] = true,
                ["slug_dogrulandi"] = true,
                ["ornek_okuma_yapildi"] = true,
            }.ToJsonString(EditorJson.Options),
            Durum = ReviewStatus.Onaylandi,
            Koken = XrefOrigin.Editor,
            Oneren = actor,
            Inceleyen = actor,
            IncelendiAt = now,
            Gerekce = body.Gerekce,
        };
        db.Reviews.Add(review);
        await db.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);

        http.Response.Headers.ETag = RisaleBookApproval.FormatEtag(assessment.Digest);
        return EditorJson.Ok(new RisaleBookApproveResult(book.Slug, review.Id, approved, assessment.Digest));
    }

    /// <summary>Baslik yoksa 428; <c>*</c>, zayif etiket, liste ya da bozuk bicim 400 (yalniz <c>"{64 hex}"</c> gecerli).</summary>
    private static IResult? ParseIfMatch(HttpRequest request, out string digest)
    {
        digest = string.Empty;
        StringValues values = request.Headers.IfMatch;
        if (values.Count == 0 || (values.Count == 1 && string.IsNullOrWhiteSpace(values[0])))
        {
            return ApiProblem.Create(
                StatusCodes.Status428PreconditionRequired,
                ProblemCodes.SurumGerekli,
                "If-Match başlığı zorunludur; kitap özetini (ETag) gönderin.");
        }

        if (values.Count == 1 && RisaleBookApproval.TryParseEtag(values[0], out digest))
        {
            return null;
        }

        return ApiProblem.Create(
            StatusCodes.Status400BadRequest,
            ProblemCodes.Dogrulama,
            "If-Match yalnız tek ve güçlü bir kitap özeti kabul eder: \"{64 küçük harf onaltılık}\" (\"*\", W/ ve liste yok).");
    }

    private static IResult NotFound() =>
        ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Kitap bulunamadı.");

    private static IResult Stale() =>
        ApiProblem.Create(
            StatusCodes.Status412PreconditionFailed,
            ProblemCodes.SurumUyusmazligi,
            "Kitap siz okuduktan sonra değişti; yenileyip yeniden deneyin.");
}
