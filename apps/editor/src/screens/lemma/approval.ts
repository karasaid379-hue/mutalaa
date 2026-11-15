import { trLemma } from '@/i18n/tr-lemma';
import type { ReviewItem } from '@/review/types';

// The approval path of a Turkish lemma mapping (K-51 madde 9): `otomatik` is the dictionary-evidence approval of
// the pipeline (not an editor approval), `editor` is an editor approval, a candidate has neither.

export type ApprovalPath = 'otomatik' | 'editor';

/** The path of an API value; anything else (null, unknown) is no path (the value is never guessed). */
export function readApprovalPath(value: string | null | undefined): ApprovalPath | null {
  return value === 'otomatik' || value === 'editor' ? value : null;
}

/** The "Onay yolu" filter of the Turkish mapping tab. */
export type ApprovalFilter = 'hepsi' | 'otomatik' | 'editor' | 'aday';

export const APPROVAL_FILTERS: readonly ApprovalFilter[] = ['hepsi', 'otomatik', 'editor', 'aday'];

export function isApprovalFilter(value: unknown): value is ApprovalFilter {
  return APPROVAL_FILTERS.some((filter) => filter === value);
}

/**
 * Where a listed review stands, read from the list item's `onay_yolu` (the server gives it for lemma items): an
 * objection or any record of an approved lemma carries its path, a candidate has none. A value that is neither
 * path nor empty is unknown (null); it is never guessed.
 */
export function itemApproval(item: ReviewItem): ApprovalPath | 'aday' | null {
  if (item.onay_yolu === null || item.onay_yolu === undefined) return 'aday';
  return readApprovalPath(item.onay_yolu);
}

/** The label of a path (for sentences). */
export function approvalLabel(path: ApprovalPath): string {
  return path === 'otomatik' ? trLemma.approval.otomatik : trLemma.approval.editor;
}
