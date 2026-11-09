using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Validation;
using Mutalaa.Domain;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Reviews;

/// <summary>Karar girdisi (tekil ve toplu ortak): karar etiketi cozulmus, duzenlenen deger henuz jsonb'ye cevrilmemis.</summary>
internal sealed record DecisionInput(bool Approve, DecisionEdit? Edit, string? Gerekce);

/// <summary>Uygulanmis ama henuz kaydedilmemis karar: izlenen review ve izlenen hedef satiri.</summary>
internal sealed record PreparedDecision(Review Review, object Target);

/// <summary>
/// Karari Domain kuraliyla hesaplar ve izlenen review ile hedef satirina yazar; <c>SaveChanges</c> cagiranindir
/// (tekil karar tek, toplu karar tum kararlar icin tek kayit yapar). Kural Domain'dedir; burada yalniz yukleme ve yazma vardir.
/// </summary>
internal static class ReviewDecider
{
    public const string ApproveLabel = "onaylandi";
    public const string RejectLabel = "reddedildi";

    public static bool TryParseKarar(string? karar, out bool approve)
    {
        approve = false;
        switch (karar)
        {
            case ApproveLabel:
                approve = true;
                return true;
            case RejectLabel:
                return true;
            default:
                return false;
        }
    }

    /// <summary>
    /// Karar metinleri (<c>gerekce</c> ve <c>duzenlenen.metin</c>) PostgreSQL'e yazilabilir mi (NUL ve eslesmemis vekil yok).
    /// Hata alan adi <paramref name="prefix"/> + alan (ornegin <c>kararlar[0].gerekce</c>).
    /// </summary>
    public static void CheckText(IDictionary<string, string[]> errors, string prefix, string? gerekce, DecisionEdit? edit)
    {
        WritableText.Check(errors, prefix + "gerekce", gerekce);
        if (edit is not null)
        {
            WritableText.Check(errors, prefix + "duzenlenen.metin", edit.Metin);
        }
    }

    public static async Task<PreparedDecision> ApplyAsync(
        IcerikDbContext db,
        Review review,
        DecisionInput input,
        string actor,
        DateTime now,
        CancellationToken cancellationToken)
    {
        if (!ReviewDecisions.IsSupported(review.HedefTablo, review.Alan))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{review.HedefTablo}' hedefinde '{review.Alan}' alani icin inceleme desteklenmiyor.");
        }

        ReviewTarget target = ReviewTargets.Parse(review.HedefTablo, review.HedefAnahtar);
        (object entity, ReviewTargetState state) = await LoadTargetAsync(db, target, cancellationToken);

        ReviewDecisionRequest request = new()
        {
            Actor = actor,
            Gerekce = input.Gerekce,
            Duzenlenen = BuildEdited(input.Edit),
            Now = now,
        };

        ReviewOutcome outcome = input.Approve
            ? ReviewDecisions.Approve(review, request, state)
            : ReviewDecisions.Reject(review, request, state);

        outcome.ApplyTo(review);
        ApplyToTarget(entity, outcome);
        return new PreparedDecision(review, entity);
    }

    /// <summary>Kararin ardindan hedefin durum etiketi (durum sutunlu hedefte status, birimde metin_durumu).</summary>
    public static string? TargetStateLabel(object target) => target switch
    {
        Unit unit => unit.MetinDurumu.ToLabel(),
        SurahAlias alias => alias.Status.ToLabel(),
        Xref xref => xref.Status.ToLabel(),
        QuranWordFix fix => fix.Status.ToLabel(),
        Lemma lemma => lemma.Status.ToLabel(),
        LemmaGloss gloss => gloss.Status.ToLabel(),
        _ => null,
    };

    /// <summary>Ikinci onay bekliyor mu: yalniz birim hedefinde (tur meal ya da tefsir) anlamlidir.</summary>
    public static bool IsSecondApprovalPending(PreparedDecision prepared) =>
        prepared.Target is Unit unit && ReviewVerification.IsSecondApprovalPending(prepared.Review, unit.Kind);

    /// <summary>Duzenlenen deger <c>{"metin", "content_hash"}</c> jsonb'si olur; ozet kanonik metinden hesaplanir.</summary>
    private static string? BuildEdited(DecisionEdit? edit)
    {
        if (edit is null)
        {
            return null;
        }

        if (string.IsNullOrEmpty(edit.Metin))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.metin bos olamaz.");
        }

        string canonical;
        try
        {
            canonical = TextCanonicalizer.Canonicalize(edit.Metin);
        }
        catch (ArgumentException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.metin gecerli Unicode degil.", e);
        }

        return JsonSerializer.Serialize(new Dictionary<string, string>
        {
            ["metin"] = canonical,
            ["content_hash"] = ContentHash.Compute(canonical),
        });
    }

    private static async Task<(object Entity, ReviewTargetState State)> LoadTargetAsync(
        IcerikDbContext db,
        ReviewTarget target,
        CancellationToken cancellationToken)
    {
        switch (target.Table)
        {
            case ReviewTargets.Unit:
                {
                    Unit unit = await db.Units.SingleOrDefaultAsync(u => u.Anchor == target.Anchor, cancellationToken)
                        ?? throw Missing();
                    SourceKind kind = await db.Sources.AsNoTracking()
                        .Where(s => s.Slug == unit.SourceId)
                        .Select(s => s.Tur)
                        .SingleAsync(cancellationToken);
                    return (unit, ReviewTargetState.ForUnit(new UnitReviewState(unit.Kind, kind, unit.MetinDurumu, unit.Metin, unit.ContentHash, unit.Rev)));
                }

            case ReviewTargets.SurahAlias:
                {
                    short surahNo = (short)target.SurahNo!.Value;
                    string alias = target.Alias!;
                    SurahAlias row = await db.SurahAliases.SingleOrDefaultAsync(s => s.SurahNo == surahNo && s.Alias == alias, cancellationToken)
                        ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            case ReviewTargets.Xref:
                {
                    Guid id = target.Id!.Value;
                    Xref row = await db.Xrefs.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            case ReviewTargets.QuranWordFix:
                {
                    Guid id = target.Id!.Value;
                    QuranWordFix row = await db.QuranWordFixes.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            case ReviewTargets.Lemma:
                {
                    int id = target.LemmaId!.Value;
                    Lemma row = await db.Lemmas.SingleOrDefaultAsync(x => x.Id == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            case ReviewTargets.LemmaGloss:
                {
                    int id = target.LemmaId!.Value;
                    LemmaGloss row = await db.LemmaGlosses.SingleOrDefaultAsync(x => x.LemmaId == id, cancellationToken) ?? throw Missing();
                    return (row, ReviewTargetState.ForStatus(row.Status));
                }

            default:
                throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, $"'{target.Table}' icin inceleme desteklenmiyor.");
        }
    }

    private static DomainException Missing() =>
        new(DomainErrorCodes.Bulunamadi, "Incelemenin hedef kaydi bulunamadi.");

    private static void ApplyToTarget(object entity, ReviewOutcome outcome)
    {
        switch (entity)
        {
            case Unit unit:
                if (outcome.UnitText is { } text)
                {
                    unit.Metin = text.Metin;
                    unit.ContentHash = text.ContentHash;
                    unit.Rev = text.Rev;
                    unit.TrNarrow = text.TrNarrow;
                    unit.TrWide = text.TrWide;
                    unit.ArNorm = text.ArNorm;
                    unit.TrStem = text.TrStem;
                }

                if (outcome.UnitMetinDurumu is { } durum)
                {
                    unit.MetinDurumu = durum;
                }

                break;
            case SurahAlias alias when outcome.TargetStatus is { } status:
                alias.Status = status;
                break;
            case Xref xref when outcome.TargetStatus is { } status:
                xref.Status = status;
                break;
            case QuranWordFix fix when outcome.TargetStatus is { } status:
                fix.Status = status;
                break;
            case Lemma lemma when outcome.TargetStatus is { } status:
                lemma.Status = status;
                break;
            case LemmaGloss gloss when outcome.TargetStatus is { } status:
                gloss.Status = status;
                break;
            default:
                break;
        }
    }
}
