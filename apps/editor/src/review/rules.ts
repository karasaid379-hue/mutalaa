import {
  isObjectionPayload,
  readMealAttrs,
  readRootMapping,
  readString,
  readTextPayload,
  type RootMapping,
} from '@/lib/payload';
import type { ReviewDetail, ReviewItem, UnitDetail } from './types';

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
 * - closed: the review already has a decision (an open record and one sent to an expert are not closed);
 * - own-proposal: an editor-sourced proposal cannot be approved by its proposer (reject is allowed);
 * - same-first-approver: the second approval must come from someone else than the first approver.
 */
export function approveBlockReason(
  review: ReviewItem,
  userName: string | null | undefined,
): ApproveBlock | null {
  // A record sent to an expert (`uzmanda`) still waits for its decision (only the expert role gives it).
  if (review.durum !== 'acik' && review.durum !== 'uzmanda') return 'closed';
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

/** A Turkish lemma root mapping review (`lemma` + `kok_eslemesi`, K-51 madde 9): a candidate or an objection. */
export function isRootMappingReview(review: Pick<ReviewItem, 'hedef_tablo' | 'alan'>): boolean {
  return review.hedef_tablo === 'lemma' && review.alan === 'kok_eslemesi';
}

/** An objection to an automatic approval (`onerilen.itiraz = true`): approval returns the lemma to a candidate. */
export function isObjectionReview(review: Pick<ReviewItem, 'onerilen'>): boolean {
  return isObjectionPayload(review.onerilen);
}

/** An open candidate mapping review: approval may carry an edited mapping (`root_id`, `ar_lemma_id`, `etymological_only`). */
export function isRootMappingEditable(review: ReviewItem): boolean {
  return isRootMappingReview(review) && review.durum === 'acik' && !isObjectionReview(review);
}

/**
 * The mapping an approval would apply: the editor's `duzenlenen`, else the proposal `onerilen`, else the
 * lemma row as the snapshot shows it. Missing parts are null (the proposal may carry no Arabic lemma).
 */
export function proposedMapping(
  review: Pick<ReviewDetail, 'duzenlenen' | 'onerilen' | 'hedef'>,
): RootMapping {
  const written = readRootMapping(review.duzenlenen) ?? readRootMapping(review.onerilen);
  if (written) return written;
  const target = review.hedef;
  return {
    rootId: target?.root_id ?? null,
    arLemmaId: target?.ar_lemma_id ?? null,
    etymologicalOnly: target?.etymological_only ?? null,
  };
}

/** Largest id the API reads (a 32 bit integer). */
const MAX_ID = 2_147_483_647;

/**
 * An id typed into a field: '' is "none" (null), a positive integer in plain digits is its number, anything
 * else (sign, space, decimal point, too large) is 'invalid'.
 */
export function parseIdInput(text: string): number | null | 'invalid' {
  if (text === '') return null;
  if (!/^[0-9]+$/.test(text)) return 'invalid';
  const value = Number(text);
  return Number.isSafeInteger(value) && value >= 1 && value <= MAX_ID ? value : 'invalid';
}
