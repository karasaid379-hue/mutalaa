import { format, formatAnchor } from './format.js';
import type { Anchor, AnchorRef } from './types.js';

/** Independent copy of an anchor (the path array of rn and k is copied too). */
function cloneAnchor(a: Anchor): Anchor {
  switch (a.t) {
    case 'rn':
    case 'k':
      return { ...a, yol: [...a.yol] };
    default:
      return { ...a };
  }
}

/**
 * Unit anchor (K-35 item 5): word(s) to ayah, span dropped, sentence to paragraph.
 * The result never shares objects with the input.
 */
export function unitOf(r: AnchorRef): AnchorRef {
  const a = r.anchor;
  switch (a.t) {
    case 'q':
      return { anchor: { t: 'q', sure: a.sure, ayet: a.ayet } };
    case 'rn':
      return { anchor: { t: 'rn', yol: [...a.yol], p: a.p } };
    default:
      return { anchor: cloneAnchor(a) }; // qa, konu and the rest stay; an `@` span is dropped
  }
}

/** Ayahs covered by an anchor (q, qa, tf, meal); an empty list for other kinds. */
export function coveredAyahs(r: AnchorRef): Array<{ sure: number; ayet: number }> {
  const a = r.anchor;
  switch (a.t) {
    case 'q':
    case 'meal':
      return [{ sure: a.sure, ayet: a.ayet }];
    case 'qa':
    case 'tf': {
      const out: Array<{ sure: number; ayet: number }> = [];
      for (let ayet = a.ilk; ayet <= a.son; ayet++) out.push({ sure: a.sure, ayet });
      return out;
    }
    default:
      return [];
  }
}

/**
 * Storage form (xref, xref_idx): unit string plus an optional half open span.
 * Words: q:2:255:3-7 gives q:2:255 + [3, 8). A `@a-b` span gives base + [a, b).
 * Throws for an ayah range and for a sentence anchor (K-35 item 5).
 */
export function toUnitSpan(r: AnchorRef): { unit: string; span?: [number, number] } {
  const a = r.anchor;
  if (a.t === 'qa') {
    throw new RangeError('toUnitSpan: ayah range has no unit span; use coveredAyahs');
  }
  if (a.t === 'rn' && a.s !== undefined) {
    throw new RangeError('toUnitSpan: sentence anchor needs content data');
  }
  if (a.t === 'q') {
    const unit = formatAnchor({ t: 'q', sure: a.sure, ayet: a.ayet });
    if (a.ilk === undefined) return { unit };
    return { unit, span: [a.ilk, (a.son ?? a.ilk) + 1] };
  }
  const unit = format({ anchor: a });
  if (r.span === undefined) return { unit };
  return { unit, span: [r.span.start, r.span.end] };
}
