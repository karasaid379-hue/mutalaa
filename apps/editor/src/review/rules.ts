import { readMealAttrs, readString, readTextPayload } from '@/lib/payload';
import type { ReviewItem, UnitDetail } from './types';

// Pre-checks of the decision form. They only close controls early; the API has the last word (K-48),
// and a 409/422 answer is always shown with its own code.

/** The fields of a unit that decide whether its text may be edited (a subset of UnitDetail). */
export type UnitEditInfo = Pick<
  UnitDetail,
  'kind' | 'kaynak_tur' | 'duzeltilebilir' | 'marks' | 'sentences'
> & { attrs?: unknown };

export const IMMUTABLE_UNIT_KIND = 'ayet';
export const IMMUTABLE_SOURCE_KIND = 'kuran_metni';

/**
 * Offset-bearing derived data (non-empty `marks` or any `sentences` range) shifts with a text change and is
 * only recomputed in A20 (Backend API 4.1; BÇ-59). Anything unreadable counts as present, like on the server.
 */
export function hasOffsetData(unit: { marks?: unknown; sentences?: number[][] | null }): boolean {
  if (unit.sentences && unit.sentences.length > 0) return true;
  const marks = unit.marks;
  if (marks === null || marks === undefined) return false;
  return Array.isArray(marks) ? marks.length > 0 : true;
}

/** An open review of a unit text, still in its first approval stage. */
export function isFirstStageUnitText(review: ReviewItem): boolean {
  return (
    review.hedef_tablo === 'unit' &&
    review.alan === 'metin' &&
    review.durum === 'acik' &&
    !review.ikinci_onay_bekliyor
  );
}

/**
 * Whether the decision form may show the "edited text" field: unit + metin, open review, approval,
 * first stage, an editable unit (`duzeltilebilir`, not Tanzil/ayet) and no offset data.
 * A joined meal follower (`attrs.birlesik_ile`) has no text of its own, so its edit field stays closed too (K-49
 * madde 8). Without unit information the answer is false.
 */
export function canEditValue(review: ReviewItem, unit: UnitEditInfo | null | undefined): boolean {
  if (!unit || !isFirstStageUnitText(review)) return false;
  return (
    unit.duzeltilebilir &&
    unit.kind !== IMMUTABLE_UNIT_KIND &&
    unit.kaynak_tur !== IMMUTABLE_SOURCE_KIND &&
    !hasOffsetData(unit) &&
    !readMealAttrs(unit.attrs).follower
  );
}

/** Text the review would apply: the editor's `duzenlenen`, else the original `onerilen`; null when there is none. */
export function proposedText(review: ReviewItem): string | null {
  return (
    readTextPayload(review.duzenlenen)?.metin ?? readTextPayload(review.onerilen)?.metin ?? null
  );
}

export type ApproveBlock = 'closed' | 'own-proposal' | 'same-first-approver';

function sameUser(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  // User names are e-mail addresses; the server compares them ordinal and case-insensitive.
  return a.toLowerCase() === b.toLowerCase();
}

/**
 * Why "Onayla" is closed in advance, or null. `userName` is the signed-in user (e-mail, which is the user name).
 * - closed: the review already has a decision;
 * - own-proposal: an editor-sourced proposal cannot be approved by its proposer (reject is allowed);
 * - same-first-approver: the second approval must come from someone else than the first approver.
 */
export function approveBlockReason(
  review: ReviewItem,
  userName: string | null | undefined,
): ApproveBlock | null {
  if (review.durum !== 'acik') return 'closed';
  if (review.koken === 'editor' && sameUser(review.oneren, userName)) return 'own-proposal';
  if (review.ikinci_onay_bekliyor && sameUser(review.inceleyen, userName))
    return 'same-first-approver';
  return null;
}

/** An open word meaning review (`lemma_gloss` + `anlam_kisa`): approval may carry an edited meaning (K-50 madde 6). */
export function isGlossEditable(review: ReviewItem): boolean {
  return (
    review.hedef_tablo === 'lemma_gloss' && review.alan === 'anlam_kisa' && review.durum === 'acik'
  );
}

/**
 * Meaning the approval would apply: the editor's `duzenlenen.anlam_kisa`, else the candidate's
 * `onerilen.anlam_kisa`; null when there is none. An edit equal to it is not sent (a plain approval).
 */
export function proposedGloss(review: ReviewItem): string | null {
  return readString(review.duzenlenen, 'anlam_kisa') ?? readString(review.onerilen, 'anlam_kisa');
}
