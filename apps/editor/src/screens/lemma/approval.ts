import { trLemma } from '@/i18n/tr-lemma';
import { readString } from '@/lib/payload';
import { isObjectionReview } from '@/review/rules';
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
 * Where a listed review stands, read from the list item alone (the list carries no lemma row): an objection
 * (`onerilen.itiraz`) belongs to an approved lemma and its `onceki` holds the path the lemma had when it was
 * opened; any other open mapping review is a candidate. An objection whose path is unreadable is null (it
 * appears under "Hepsi" only).
 */
export function itemApproval(item: ReviewItem): ApprovalPath | 'aday' | null {
  if (!isObjectionReview(item)) return 'aday';
  return readApprovalPath(readString(item.onceki, 'onay_yolu'));
}

export function matchesApprovalFilter(item: ReviewItem, filter: ApprovalFilter): boolean {
  return filter === 'hepsi' || itemApproval(item) === filter;
}

/** The label of a path (for sentences). */
export function approvalLabel(path: ApprovalPath): string {
  return path === 'otomatik' ? trLemma.approval.otomatik : trLemma.approval.editor;
}
