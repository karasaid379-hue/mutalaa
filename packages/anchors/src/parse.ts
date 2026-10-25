import { AnchorError } from './errors.js';
import { AYET_SAYILARI } from './generated/ayet-sayilari.js';
import {
  MAX_DEPTH,
  MAX_NUMBER_DIGITS,
  MAX_SLUG_LENGTH,
  MAX_TOTAL_LENGTH,
  OUTSIDE_ALPHABET,
  PATTERNS_BY_PREFIX,
} from './patterns.js';
import type { Anchor, AnchorRef, Span } from './types.js';

type Groups = Readonly<Record<string, string | undefined>>;

const SLUG_GROUPS = ['konu', 'meal', 'eser', 'bolum', 'koleksiyon', 'ceviri'] as const;
const BIG_NUMBER_GROUPS = ['p', 's', 'no', 'bas', 'bit'] as const;

/** True when a digit string (no leading zero, except "0") exceeds 2147483647. */
function exceedsMaxNumber(digits: string): boolean {
  if (digits.length !== MAX_NUMBER_DIGITS.length) return digits.length > MAX_NUMBER_DIGITS.length;
  return digits > MAX_NUMBER_DIGITS; // same length, all ASCII digits
}

/** K-35 item 1, step 4: slug 64, depth 8 (path length, book included), number 2147483647. */
function checkLimits(groups: Groups, input: string): void {
  for (const name of SLUG_GROUPS) {
    const value = groups[name];
    if (value !== undefined && value.length > MAX_SLUG_LENGTH) {
      throw new AnchorError('UZUNLUK', input);
    }
  }
  const yol = groups['yol'];
  if (yol !== undefined) {
    const parts = yol.split(':');
    if (parts.length > MAX_DEPTH) throw new AnchorError('UZUNLUK', input);
    for (const part of parts) {
      if (part.length > MAX_SLUG_LENGTH) throw new AnchorError('UZUNLUK', input);
    }
  }
  for (const name of BIG_NUMBER_GROUPS) {
    const value = groups[name];
    if (value !== undefined && exceedsMaxNumber(value)) throw new AnchorError('UZUNLUK', input);
  }
}

function text(groups: Groups, name: string, input: string): string {
  const value = groups[name];
  if (value === undefined) throw new AnchorError('BICIM', input); // unreachable for a matched pattern
  return value;
}

function int(groups: Groups, name: string, input: string): number {
  return Number(text(groups, name, input));
}

function optInt(groups: Groups, name: string): number | undefined {
  const value = groups[name];
  return value === undefined ? undefined : Number(value);
}

function spanOf(groups: Groups): Span | undefined {
  const bas = groups['bas'];
  const bit = groups['bit'];
  if (bas === undefined || bit === undefined) return undefined;
  return { start: Number(bas), end: Number(bit) };
}

function buildAnchor(prefix: string, g: Groups, input: string): Anchor {
  switch (prefix) {
    case 'q': {
      const sure = int(g, 'sure', input);
      if (g['ayet_ilk'] !== undefined) {
        return { t: 'qa', sure, ilk: int(g, 'ayet_ilk', input), son: int(g, 'ayet_son', input) };
      }
      const anchor: Anchor = { t: 'q', sure, ayet: int(g, 'ayet', input) };
      const ilk = optInt(g, 'ilk');
      if (ilk !== undefined) anchor.ilk = ilk;
      const son = optInt(g, 'son');
      if (son !== undefined) anchor.son = son;
      return anchor;
    }
    case 'konu':
      return { t: 'konu', slug: text(g, 'konu', input) };
    case 'meal':
      return {
        t: 'meal',
        meal: text(g, 'meal', input),
        sure: int(g, 'sure', input),
        ayet: int(g, 'ayet', input),
      };
    case 'tf': {
      const eser = text(g, 'eser', input);
      if (g['bolum'] !== undefined) {
        return { t: 'tfb', eser, bolum: text(g, 'bolum', input), p: int(g, 'p', input) };
      }
      return {
        t: 'tf',
        eser,
        sure: int(g, 'sure', input),
        ilk: int(g, 'ilk', input),
        son: int(g, 'son', input),
        p: int(g, 'p', input),
      };
    }
    case 'rn': {
      const anchor: Anchor = {
        t: 'rn',
        yol: text(g, 'yol', input).split(':'),
        p: int(g, 'p', input),
      };
      const s = optInt(g, 's');
      if (s !== undefined) anchor.s = s;
      return anchor;
    }
    case 'h':
      return {
        t: 'h',
        koleksiyon: text(g, 'koleksiyon', input),
        no: int(g, 'no', input),
      };
    case 'ht':
      return {
        t: 'ht',
        ceviri: text(g, 'ceviri', input),
        koleksiyon: text(g, 'koleksiyon', input),
        no: int(g, 'no', input),
      };
    default:
      return { t: 'k', yol: text(g, 'yol', input).split(':'), p: int(g, 'p', input) };
  }
}

function ayahCount(sure: number): number {
  return AYET_SAYILARI[sure - 1] ?? 0;
}

/** K-35 item 1, step 5: SURE_ARALIGI, AYET_ARALIGI, TERS_ARALIK, KANONIK_DEGIL, in this order. */
function checkSemantics(anchor: Anchor, span: Span | undefined, input: string): void {
  let sure: number | undefined;
  const ayahs: number[] = [];
  switch (anchor.t) {
    case 'q':
      sure = anchor.sure;
      ayahs.push(anchor.ayet);
      break;
    case 'qa':
    case 'tf':
      sure = anchor.sure;
      ayahs.push(anchor.ilk, anchor.son);
      break;
    case 'meal':
      sure = anchor.sure;
      ayahs.push(anchor.ayet);
      break;
    default:
      break;
  }
  if (sure !== undefined) {
    if (sure < 1 || sure > 114) throw new AnchorError('SURE_ARALIGI', input);
    const count = ayahCount(sure);
    if (ayahs.some((a) => a < 1 || a > count)) throw new AnchorError('AYET_ARALIGI', input);
  }

  // Reversed ranges. A span with start >= end is also "reversed" (K-35, vectors).
  if (anchor.t === 'q' && anchor.ilk !== undefined && anchor.son !== undefined) {
    if (anchor.ilk > anchor.son) throw new AnchorError('TERS_ARALIK', input);
  }
  if ((anchor.t === 'qa' || anchor.t === 'tf') && anchor.ilk > anchor.son) {
    throw new AnchorError('TERS_ARALIK', input);
  }
  if (span !== undefined && span.start >= span.end) throw new AnchorError('TERS_ARALIK', input);

  // Non-canonical single-element ranges.
  if (anchor.t === 'q' && anchor.ilk !== undefined && anchor.ilk === anchor.son) {
    throw new AnchorError('KANONIK_DEGIL', input);
  }
  if (anchor.t === 'qa' && anchor.ilk === anchor.son) {
    throw new AnchorError('KANONIK_DEGIL', input);
  }
}

/** Parse an anchor string. Throws AnchorError (priority: K-35 item 1). */
export function parse(s: string): AnchorRef {
  if (typeof s !== 'string') throw new AnchorError('BICIM');
  if (OUTSIDE_ALPHABET.test(s)) throw new AnchorError('BICIM', s);
  if (s.length > MAX_TOTAL_LENGTH) throw new AnchorError('UZUNLUK', s);

  const colon = s.indexOf(':');
  const prefix = colon < 0 ? '' : s.slice(0, colon);
  const pattern = PATTERNS_BY_PREFIX.get(prefix);
  if (pattern === undefined) throw new AnchorError('BICIM', s);
  const match = pattern.exec(s);
  const groups = match?.groups;
  if (groups === undefined) throw new AnchorError('BICIM', s);

  checkLimits(groups, s);
  const anchor = buildAnchor(prefix, groups, s);
  const span = spanOf(groups);
  checkSemantics(anchor, span, s);
  return span === undefined ? { anchor } : { anchor, span };
}

/** Like parse, but returns null for an invalid anchor. */
export function tryParse(s: string): AnchorRef | null {
  try {
    return parse(s);
  } catch (error) {
    if (error instanceof AnchorError) return null;
    throw error;
  }
}
