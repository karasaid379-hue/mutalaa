import type { Span } from './types.js';

// Offsets (Capa semasi 8): code point positions, [start, end). Conversion to UTF-16 happens
// only here. Invalid positions throw RangeError (K-35 item 8).

const NONSPACING_MARK = /^\p{Mn}$/u;

function checkInt(value: number, name: string): void {
  if (!Number.isSafeInteger(value)) throw new RangeError(`${name} must be an integer`);
}

/** UTF-16 index of code point position `cp`; cp in [0, number of code points]. */
export function cpToUtf16(text: string, cp: number): number {
  checkInt(cp, 'cp');
  if (cp < 0) throw new RangeError('cp out of range');
  let index = 0;
  let count = 0;
  for (const ch of text) {
    if (count === cp) return index;
    index += ch.length;
    count++;
  }
  if (count === cp) return index;
  throw new RangeError('cp out of range');
}

/** Code point position of UTF-16 index `i`; throws inside a surrogate pair. */
export function utf16ToCp(text: string, i: number): number {
  checkInt(i, 'i');
  if (i < 0 || i > text.length) throw new RangeError('i out of range');
  let index = 0;
  let count = 0;
  for (const ch of text) {
    if (index === i) return count;
    if (index > i) break; // i fell between the two units of a pair
    index += ch.length;
    count++;
  }
  if (index === i) return count;
  throw new RangeError('i is inside a surrogate pair');
}

/**
 * Snap a span to cluster boundaries: a start on a nonspacing mark (Mn) moves back, an end
 * before an Mn moves forward. Only Mn counts. Requires 0 <= start <= end <= length.
 */
export function snapSpan(text: string, s: Span): Span {
  checkInt(s.start, 'start');
  checkInt(s.end, 'end');
  const points = Array.from(text);
  if (s.start < 0 || s.start > s.end || s.end > points.length) {
    throw new RangeError('span out of range');
  }
  const isMark = (position: number): boolean => {
    const ch = points[position];
    return ch !== undefined && NONSPACING_MARK.test(ch);
  };
  let start = s.start;
  while (start > 0 && isMark(start)) start--;
  let end = s.end;
  while (end < points.length && isMark(end)) end++;
  return { start, end };
}
