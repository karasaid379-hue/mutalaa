using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// Baglanti incelemesinde Duzelt ve onayla (A18.4, K-48 madde 2): hedefi degistir, araligi duzelt, tur degistir.
/// Kontrol sirasi ortak siradir (desteklenmeyen hedef 422, girdi 400, kayit durumu 409, dort goz 409, hedef durumu 409, deger 400/422).
/// </summary>
public static partial class ReviewDecisions
{
    /// <summary>Hedef (xref, status) mi (Ordinal).</summary>
    public static bool IsLinkTarget(string? hedefTablo, string? alan) =>
        string.Equals(hedefTablo, ReviewTargets.Xref, StringComparison.Ordinal)
        && string.Equals(alan, ReviewFields.Status, StringComparison.Ordinal);

    internal static bool IsLinkTarget(Review review) => IsLinkTarget(review.HedefTablo, review.Alan);

    /// <summary>
    /// Duzenlenen degeri okur, mevcut satira uygular ve sonucu hesaplar. Hicbir sey degismiyorsa (deger mevcut satirla ayni) onay duz onaydir:
    /// koken ve kanit korunur. Aksi halde <c>xref.origin = editor</c> ve kanita <c>editor_duzeltmesi = true</c> yazilir; hedef birim degistiyse
    /// kanittaki <c>dst_hash</c> yeni birimin ozetine gecer.
    /// </summary>
    private static ReviewOutcome ApproveLink(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        LinkRowState row = target.LinkRow
            ?? throw new InvalidOperationException("Duzeltilen baglanti icin satir durumu verilmeli.");
        RequireCandidate(target);

        LinkEditValue edit = LinkEditPayload.Read(request.Duzenlenen, "duzenlenen")
            ?? throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen bos olamaz.");

        ResolvedLinkEdit resolved = LinkEdits.Resolve(row.Type, row.DstAnchor, row.DstSpan, edit);
        LinkDstFacts facts = target.LinkDst ?? default;
        if (resolved.DstUnitChanged && !facts.UnitExists)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Hedef birim bulunamadi.");
        }

        LinkEdits.ValidateDstSpan(resolved.DstAnchor, resolved.DstSpan, facts);

        LinkUpdate? update = null;
        if (resolved.Changed)
        {
            string? dstHash = resolved.DstUnitChanged ? LinkEvidenceSummary.Hash16(facts.ContentHash) : null;
            update = new LinkUpdate(
                resolved.Type,
                resolved.DstAnchor,
                resolved.DstSpan,
                XrefOrigin.Editor,
                LinkEvidenceSummary.WithEditorCorrection(row.Evidence, dstHash));
        }

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = update is null ? ReviewActions.Onayla : ReviewActions.DuzenleOnayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = LinkEditPayload.ToPayload(edit),
            TargetStatus = XrefStatus.Onayli,
            Link = update,
        };
    }

    /// <summary>
    /// Toplu onay yalniz "toplu" sinifindaki baglanti adayinda gecer (K-13 politika 1): siniflama kurali <see cref="LinkCandidateClassifier"/>'dir.
    /// Baska sinif ya da kayitli deger (<c>duzenlenen</c>) tasiyan istek 422 <c>toplu-uygun-degil</c>.
    /// </summary>
    public static void RequireBulkEligible(XrefType type, float confidence, string? evidenceJson, bool hasEdit)
    {
        LinkCandidateClass sinif = LinkCandidateClassifier.Classify(type, confidence, evidenceJson);
        if (sinif != LinkCandidateClass.Toplu)
        {
            throw new DomainException(
                DomainErrorCodes.TopluUygunDegil,
                $"Toplu onay yalniz 'toplu' sinifindaki baglanti adaylarina uygulanir (bu aday: '{sinif.ToLabel()}'); tek tek inceleyin.");
        }

        if (hasEdit)
        {
            throw new DomainException(DomainErrorCodes.TopluUygunDegil, "Toplu onay duzenlenen deger tasimaz; duzeltme tek tek yapilir.");
        }
    }

    /// <summary>
    /// <c>quran_word_fix</c> adayinda Duzenle ve onayla (K-51 madde 2): <c>duzenlenen = {"new_value": ...}</c> alana gore dogrulanir
    /// (<see cref="WordFixValues"/>); onayda duzeltmenin <c>new_value</c> alani yeni deger olur.
    /// </summary>
    private static ReviewOutcome ApproveWordFix(Review review, ReviewDecisionRequest request, ReviewTargetState target, string actor, string gerekce)
    {
        RequireFieldMatch(review, target);
        RequireCandidate(target);

        string raw = WordFixPayload.ReadNewValue(request.Duzenlenen, "duzenlenen")
            ?? throw new DomainException(DomainErrorCodes.Dogrulama, "duzenlenen.new_value zorunludur.");
        string field = target.Field
            ?? throw new InvalidOperationException("quran_word_fix hedefi icin duzeltmenin alani verilmeli.");
        string value = WordFixValues.Normalize(field, raw, target.FixFacts, "duzenlenen.new_value");

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Onaylandi,
            Eylem = ReviewActions.DuzenleOnayla,
            Inceleyen = actor,
            IncelendiAt = request.Now,
            Gerekce = gerekce,
            Duzenlenen = WordFixPayload.ToPayload(value),
            TargetStatus = XrefStatus.Onayli,
            WordFixNewValue = value,
        };
    }
}
