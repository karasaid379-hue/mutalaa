import type { Anchor, AnchorRef } from './types.js';

// Deterministic key order (K-35 item 3). Quran anchors come first, in reading order; then
// meal < tf < tfb < rn < h < ht < k < konu. Other kinds compare field by field in canonical
// string order. Strings are ASCII only, so plain < and > are culture independent. An absent
// optional field sorts before a present one (encoded as -1; real numbers are never negative).

type Part = number | string | readonly string[];

const ABSENT = -1;

function quranKey(anchor: Anchor & { t: 'q' | 'qa' }): Part[] {
  if (anchor.t === 'qa') {
    // class 2: ayah ranges, by end
    return [0, anchor.sure, anchor.ilk, 2, 0, anchor.son];
  }
  if (anchor.ilk === undefined) return [0, anchor.sure, anchor.ayet, 0, 0, 0]; // the ayah itself
  // class 1: words and word ranges, by first word; the single word has end = first word
  return [0, anchor.sure, anchor.ayet, 1, anchor.ilk, anchor.son ?? anchor.ilk];
}

function keyOf(r: AnchorRef): Part[] {
  const a = r.anchor;
  const ss = r.span?.start ?? ABSENT;
  const se = r.span?.end ?? ABSENT;
  switch (a.t) {
    case 'q':
    case 'qa':
      return quranKey(a);
    case 'meal':
      return [1, a.meal, a.sure, a.ayet, ss, se];
    case 'tf':
      return [2, a.eser, a.sure, a.ilk, a.son, a.p, ss, se];
    case 'tfb':
      return [3, a.eser, a.bolum, a.p, ss, se];
    case 'rn':
      return [4, a.yol, a.p, a.s ?? ABSENT, ss, se];
    case 'h':
      return [5, a.koleksiyon, a.no, ss, se];
    case 'ht':
      return [6, a.ceviri, a.koleksiyon, a.no, ss, se];
    case 'k':
      return [7, a.yol, a.p, ss, se];
    case 'konu':
      return [8, a.slug];
  }
}

function comparePart(x: Part, y: Part): -1 | 0 | 1 {
  if (typeof x === 'number' && typeof y === 'number') return x < y ? -1 : x > y ? 1 : 0;
  if (typeof x === 'string' && typeof y === 'string') return x < y ? -1 : x > y ? 1 : 0;
  if (typeof x === 'object' && typeof y === 'object') {
    const common = Math.min(x.length, y.length);
    for (let i = 0; i < common; i++) {
      const c = comparePart(x[i] ?? '', y[i] ?? '');
      if (c !== 0) return c;
    }
    return x.length < y.length ? -1 : x.length > y.length ? 1 : 0; // shorter prefix first
  }
  return 0; // unreachable: the first part (kind) decides before mixed positions are reached
}

/** Total order on anchors (K-35 item 3). Returns -1, 0 or 1. */
export function compare(a: AnchorRef, b: AnchorRef): -1 | 0 | 1 {
  const ka = keyOf(a);
  const kb = keyOf(b);
  const common = Math.min(ka.length, kb.length);
  for (let i = 0; i < common; i++) {
    const c = comparePart(ka[i] ?? 0, kb[i] ?? 0);
    if (c !== 0) return c;
  }
  return ka.length < kb.length ? -1 : ka.length > kb.length ? 1 : 0;
}
