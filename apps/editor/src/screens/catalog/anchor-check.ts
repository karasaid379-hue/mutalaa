// Client-side pre-check of an anchor typed or linked into the units screen (K-26: parsing only with
// `@mutalaa/anchors`). An invalid anchor never reaches the API. The server still has the last word:
// it also answers 400 `capa-gecersiz` (with `capa_hata_kodu`) and shows up in the detail as a problem.
import { AnchorError, format, parse, unitOf, type AnchorErrorCode } from '@mutalaa/anchors';

export type AnchorCheck =
  | { ok: true }
  /** The grammar rejects the anchor; `code` is the error code of `@mutalaa/anchors`. */
  | { ok: false; reason: 'invalid'; code: AnchorErrorCode }
  /** A valid anchor that is not a unit: a word, a word range, a sentence, an `@` range, an ayah range or a topic. */
  | { ok: false; reason: 'not-unit' };

/**
 * Checks that the text is a valid anchor at unit level. The anchor is used as typed (no trim, no case
 * change): an anchor with a space or a capital letter is invalid (`BICIM`).
 */
export function checkUnitAnchor(text: string): AnchorCheck {
  let ref;
  try {
    ref = parse(text);
  } catch (error) {
    if (error instanceof AnchorError) return { ok: false, reason: 'invalid', code: error.code };
    throw error;
  }
  // A range of ayahs and a topic have no text of their own; the other non-unit forms collapse to their unit.
  const kind = ref.anchor.t;
  if (kind === 'qa' || kind === 'konu') return { ok: false, reason: 'not-unit' };
  return format(unitOf(ref)) === format(ref) ? { ok: true } : { ok: false, reason: 'not-unit' };
}
