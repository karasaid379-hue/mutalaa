import { tryParse } from '@mutalaa/anchors';
import { parseIdInput } from '@/review/rules';
import { codePointCount } from '@/lib/text';

// Pre-checks of the "Kelime düzeltmesi öner" form. They only save a round trip: the API checks again and has the
// last word (`POST /word-fixes`). Anchors are read with `@mutalaa/anchors` only.

/** The four corrected fields a word fix may carry. */
export const WORD_FIX_FIELDS = ['root_id', 'lemma_id', 'pos', 'features'] as const;
export type WordFixField = (typeof WORD_FIX_FIELDS)[number];

export function isWordFixField(value: unknown): value is WordFixField {
  return WORD_FIX_FIELDS.some((field) => field === value);
}

/** Limits of the API (Mutalaa.Domain WordFixValues): `pos` 20 and `features` 2.000 code points. */
export const MAX_POS_LENGTH = 20;
export const MAX_FEATURES_LENGTH = 2000;

export type WordFixProblem =
  | 'anchorEmpty'
  | 'anchorInvalid'
  | 'anchorNotWord'
  | 'valueEmpty'
  | 'idInvalid'
  | 'posTooLong'
  | 'featuresTooLong'
  | 'featuresNotObject';

/** A word anchor is one word of an ayah (`q:{sure}:{ayet}:{kelime}`), neither an ayah nor a word range. */
export function checkWordAnchor(text: string): WordFixProblem | null {
  if (text.trim() === '') return 'anchorEmpty';
  const ref = tryParse(text);
  if (ref === null) return 'anchorInvalid';
  const anchor = ref.anchor;
  if (anchor.t !== 'q' || anchor.ilk === undefined || anchor.son !== undefined) {
    return 'anchorNotWord';
  }
  return null;
}

/** The new value against its field: ids are positive integers, `pos` is short, `features` is a JSON object text. */
export function checkWordFixValue(field: WordFixField, value: string): WordFixProblem | null {
  if (value.trim() === '') return 'valueEmpty';
  switch (field) {
    case 'root_id':
    case 'lemma_id':
      return typeof parseIdInput(value.trim()) === 'number' ? null : 'idInvalid';
    case 'pos':
      return codePointCount(value.trim()) > MAX_POS_LENGTH ? 'posTooLong' : null;
    case 'features': {
      if (codePointCount(value) > MAX_FEATURES_LENGTH) return 'featuresTooLong';
      try {
        const parsed: unknown = JSON.parse(value);
        return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
          ? null
          : 'featuresNotObject';
      } catch {
        return 'featuresNotObject';
      }
    }
  }
}
