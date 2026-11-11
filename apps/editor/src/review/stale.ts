import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { readTextPayload } from '@/lib/payload';
import type { ReviewDetail } from './types';

// "The record changed" view after a 412: which visible fields differ between what the editor was looking
// at and the fresh record. Pure functions; the panel component only draws the result.

export interface FieldChange {
  /** API field name (key of tr.labels.reviewField). */
  field: string;
  before: string;
  after: string;
  /** Present for text payloads (`onerilen`, `duzenlenen`): the two texts, for TextDiff. */
  text?: { before: string; after: string };
}

type Scalar =
  | 'durum'
  | 'eylem'
  | 'koken'
  | 'oneren'
  | 'inceleyen'
  | 'ikinci_inceleyen'
  | 'gerekce'
  | 'ikinci_gerekce';
type Flag = 'dogrulanmamis' | 'ikinci_onay_bekliyor';
type Payload = 'onerilen' | 'duzenlenen';

const SCALARS: readonly Scalar[] = [
  'durum',
  'eylem',
  'koken',
  'oneren',
  'inceleyen',
  'ikinci_inceleyen',
  'gerekce',
  'ikinci_gerekce',
];
const FLAGS: readonly Flag[] = ['dogrulanmamis', 'ikinci_onay_bekliyor'];
const PAYLOADS: readonly Payload[] = ['onerilen', 'duzenlenen'];

const NONE = '—';

function scalarText(field: Scalar, value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return NONE;
  if (field === 'durum') return labelOf(tr.labels.status, value);
  if (field === 'eylem') return labelOf(tr.labels.action, value);
  if (field === 'koken') return labelOf(tr.labels.origin, value);
  return value;
}

function payloadText(value: unknown): string {
  if (value === null || value === undefined) return NONE;
  const text = readTextPayload(value);
  return text ? text.metin : JSON.stringify(value);
}

/** Visible field differences between two versions of the same review (empty when only `xmin` moved). */
export function describeChanges(before: ReviewDetail, after: ReviewDetail): FieldChange[] {
  const changes: FieldChange[] = [];
  for (const field of SCALARS) {
    const a = scalarText(field, before[field]);
    const b = scalarText(field, after[field]);
    if (a !== b) changes.push({ field, before: a, after: b });
  }
  for (const field of FLAGS) {
    if (before[field] !== after[field]) {
      changes.push({
        field,
        before: before[field] ? tr.ui.yes : tr.ui.no,
        after: after[field] ? tr.ui.yes : tr.ui.no,
      });
    }
  }
  for (const field of PAYLOADS) {
    const a = payloadText(before[field]);
    const b = payloadText(after[field]);
    if (a === b) continue;
    const textBefore = readTextPayload(before[field]);
    const textAfter = readTextPayload(after[field]);
    const change: FieldChange = { field, before: a, after: b };
    if (textBefore || textAfter) {
      change.text = { before: textBefore?.metin ?? '', after: textAfter?.metin ?? '' };
    }
    changes.push(change);
  }
  return changes;
}
