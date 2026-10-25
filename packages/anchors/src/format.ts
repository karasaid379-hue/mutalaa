import { AnchorError } from './errors.js';
import type { Anchor, AnchorRef } from './types.js';

/** Canonical string of an anchor, without the span. */
export function formatAnchor(anchor: Anchor): string {
  switch (anchor.t) {
    case 'q': {
      if (anchor.ilk === undefined) return `q:${anchor.sure}:${anchor.ayet}`;
      if (anchor.son === undefined) return `q:${anchor.sure}:${anchor.ayet}:${anchor.ilk}`;
      return `q:${anchor.sure}:${anchor.ayet}:${anchor.ilk}-${anchor.son}`;
    }
    case 'qa':
      return `q:${anchor.sure}:${anchor.ilk}-${anchor.son}`;
    case 'konu':
      return `konu:${anchor.slug}`;
    case 'meal':
      return `meal:${anchor.meal}:${anchor.sure}:${anchor.ayet}`;
    case 'tf':
      return `tf:${anchor.eser}:${anchor.sure}-${anchor.ilk}-${anchor.son}:p${anchor.p}`;
    case 'tfb':
      return `tf:${anchor.eser}:${anchor.bolum}:p${anchor.p}`;
    case 'rn': {
      const base = `rn:${anchor.yol.join(':')}:p${anchor.p}`;
      return anchor.s === undefined ? base : `${base}:s${anchor.s}`;
    }
    case 'h':
      return `h:${anchor.koleksiyon}:${anchor.no}`;
    case 'ht':
      return `ht:${anchor.ceviri}:${anchor.koleksiyon}:${anchor.no}`;
    case 'k':
      return `k:${anchor.yol.join(':')}:p${anchor.p}`;
    default:
      return assertNever(anchor);
  }
}

function assertNever(value: never): never {
  throw new AnchorError('BICIM', JSON.stringify(value));
}

/** True when the grammar allows an `@` span on this anchor. */
export function allowsSpan(anchor: Anchor): boolean {
  switch (anchor.t) {
    case 'q':
    case 'qa':
    case 'konu':
      return false;
    case 'rn':
      return anchor.s === undefined; // a sentence anchor never takes a span
    default:
      return true;
  }
}

/** Canonical string. For a valid ref, parse(format(r)) equals r. */
export function format(r: AnchorRef): string {
  const base = formatAnchor(r.anchor);
  if (r.span === undefined) return base;
  if (!allowsSpan(r.anchor)) throw new AnchorError('BICIM', base);
  return `${base}@${r.span.start}-${r.span.end}`;
}
