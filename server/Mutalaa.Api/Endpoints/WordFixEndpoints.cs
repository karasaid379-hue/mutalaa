using System.Globalization;
using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Auth;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Reviews;
using Mutalaa.Api.Validation;
using Mutalaa.Domain;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Kelime duzeltmesi adayi (<c>quran_word_fix</c>; K-51 madde 2, A18.4): adayi yalniz editor acar (hat aday uretmez). Duzeltme satiri ve
/// <c>review</c> kaydi (<c>koken = editor</c>, <c>eylem = oner</c>) tek islemde yazilir; karari karar ucu verir
/// (Duzenle ve onayla icin <c>duzenlenen = {"new_value": ...}</c>) ve oneren kendi onerisini onaylayamaz.
/// </summary>
public static class WordFixEndpoints
{
    public static RouteGroupBuilder MapWordFixEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder fixes = editor.MapGroup("/word-fixes").WithTags("word-fixes");

        fixes.MapPost(string.Empty, CreateAsync)
            .WithName("createWordFix")
            .WithSummary("Kelime düzeltmesi adayı açar (quran_word_fix aday + inceleme kaydı). Değer alana göre doğrulanır.")
            .RequireAuthorization(AuthPolicies.Editor)
            .Produces<WordFixResponse>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict);

        return editor;
    }

    private static async Task<IResult> CreateAsync(
        WordFixRequest request,
        HttpContext http,
        ClaimsPrincipal user,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        WritableText.Check(errors, "anchor", request.Anchor);
        WritableText.Check(errors, "field", request.Field);
        WritableText.Check(errors, "new_value", request.NewValue);
        if (string.IsNullOrWhiteSpace(request.Reason))
        {
            errors["reason"] = ["reason boş olamaz."];
        }
        else if (!WritableText.TryCountCodePoints(request.Reason, out int length))
        {
            errors["reason"] = [WritableText.Message("reason")];
        }
        else if (length > ReviewDecisions.MaxGerekceLength)
        {
            errors["reason"] = ["reason en çok 2000 karakter olabilir."];
        }

        if (string.IsNullOrWhiteSpace(request.Anchor))
        {
            errors["anchor"] = ["anchor boş olamaz."];
        }
        else if (!errors.ContainsKey("anchor") && !AnchorRef.TryParse(request.Anchor, out _))
        {
            errors["anchor"] = ["anchor geçerli bir çapa değil."];
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

        AnchorRef anchor = AnchorRef.Parse(request.Anchor!);

        // Girdi denetimi (400) once, sonra kelimenin varligi (404): alan, deger ve kelime kosullari Domain'dedir.
        WordFixFacts? facts = WordFixValues.IsField(request.Field)
            ? await ReviewDecider.LoadWordFixFactsForValueAsync(db, request.Field, request.NewValue, cancellationToken)
            : null;
        _ = WordFixProposals.Open(Guid.Empty, anchor, request.Field, request.NewValue, request.Reason, null, facts, actor);

        QuranWord? word = await db.QuranWords.AsNoTracking().SingleOrDefaultAsync(w => w.Anchor == anchor, cancellationToken);
        if (word is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "anchor ile eşleşen kelime (quran_word) bulunamadı.");
        }

        Guid id = Guid.CreateVersion7();
        (QuranWordFix fix, Review review) = WordFixProposals.Open(
            id,
            anchor,
            request.Field,
            request.NewValue,
            request.Reason,
            CurrentValue(word, request.Field!),
            facts,
            actor);

        // (anchor, field) tekil: onceki duzeltme (aday, onayli ya da red) varsa 409; yarisan iki istek tekil kisitla 409 olur.
        bool exists = await db.QuranWordFixes.AsNoTracking().AnyAsync(f => f.Anchor == anchor && f.Field == fix.Field, cancellationToken);
        if (exists)
        {
            return ApiProblem.Create(
                StatusCodes.Status409Conflict,
                ProblemCodes.Cakisma,
                "Bu kelime ve alan için bir düzeltme kaydı zaten var.");
        }

        db.QuranWordFixes.Add(fix);
        db.Reviews.Add(review);
        await db.SaveChangesAsync(cancellationToken);

        http.Response.Headers.Location = "/api/v1/reviews/" + review.Id.ToString(CultureInfo.InvariantCulture);
        return TypedResults.Json(
            new WordFixResponse(fix.Id, review.Id, fix.Status.ToLabel()),
            EditorJson.Options,
            statusCode: StatusCodes.Status201Created);
    }

    /// <summary>Kelimenin bugunku QAC degeri (metin olarak); degeri yoksa null.</summary>
    private static string? CurrentValue(QuranWord word, string field) => field switch
    {
        ReviewFields.RootId => word.RootId?.ToString(CultureInfo.InvariantCulture),
        ReviewFields.LemmaId => word.LemmaId?.ToString(CultureInfo.InvariantCulture),
        ReviewFields.Pos => word.Pos,
        ReviewFields.Features => word.Features,
        _ => null,
    };
}
