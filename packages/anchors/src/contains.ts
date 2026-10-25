import type { Anchor, AnchorRef, Span } from './types.js';

// Containment (Capa semasi 11 and K-35 item 4). The same anchor always contains itself.
// Different kinds never contain each other (meal and tefsir relate to ayahs via coveredAyahs).

function spanCovers(outer: Span | undefined, inner: Span | undefined): boolean {
  if (outer === undefined) return true; // a unit without a span contains its own spans
  return inner !== undefined && outer.start <= inner.start && inner.end <= outer.end;
}

function sameYol(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((part, i) => part === b[i]);
}

type QAnchor = Anchor & { t: 'q' };
type QAyahRange = Anchor & { t: 'qa' };

function quranContains(outer: QAnchor | QAyahRange, inner: Anchor): boolean {
  if (inner.t !== 'q' && inner.t !== 'qa') return false;
  if (inner.sure !== outer.sure) return false;

  if (outer.t === 'qa') {
    // every ayah, word, word range and inner ayah range inside [ilk, son]
    const first = inner.t === 'qa' ? inner.ilk : inner.ayet;
    const last = inner.t === 'qa' ? inner.son : inner.ayet;
    return outer.ilk <= first && last <= outer.son;
  }

  if (inner.t !== 'q' || inner.ayet !== outer.ayet) return false;
  if (outer.ilk === undefined) return true; // the ayah contains itself, its words and ranges
  // a word range contains the words and ranges inside it
  if (inner.ilk === undefined) return false;
  const outerLast = outer.son ?? outer.ilk;
  const innerLast = inner.son ?? inner.ilk;
  return outer.ilk <= inner.ilk && innerLast <= outerLast;
}

/** True when `dis` contains `ic` (same anchor counts). */
export function contains(dis: AnchorRef, ic: AnchorRef): boolean {
  const a = dis.anchor;
  const b = ic.anchor;
  switch (a.t) {
    case 'q':
    case 'qa':
      return quranContains(a, b);
    case 'konu':
      return b.t === 'konu' && a.slug === b.slug;
    case 'meal':
      return (
        b.t === 'meal' &&
        a.meal === b.meal &&
        a.sure === b.sure &&
        a.ayet === b.ayet &&
        spanCovers(dis.span, ic.span)
      );
    case 'tf':
      return (
        b.t === 'tf' &&
        a.eser === b.eser &&
        a.sure === b.sure &&
        a.ilk === b.ilk &&
        a.son === b.son &&
        a.p === b.p &&
        spanCovers(dis.span, ic.span)
      );
    case 'tfb':
      return (
        b.t === 'tfb' &&
        a.eser === b.eser &&
        a.bolum === b.bolum &&
        a.p === b.p &&
        spanCovers(dis.span, ic.span)
      );
    case 'rn': {
      if (b.t !== 'rn' || !sameYol(a.yol, b.yol) || a.p !== b.p) return false;
      // a paragraph without a span contains its sentences; a spanned paragraph does not
      if (a.s === undefined && dis.span === undefined) return true;
      return a.s === b.s && spanCovers(dis.span, ic.span);
    }
    case 'h':
      return (
        b.t === 'h' &&
        a.koleksiyon === b.koleksiyon &&
        a.no === b.no &&
        spanCovers(dis.span, ic.span)
      );
    case 'ht':
      return (
        b.t === 'ht' &&
        a.ceviri === b.ceviri &&
        a.koleksiyon === b.koleksiyon &&
        a.no === b.no &&
        spanCovers(dis.span, ic.span)
      );
    case 'k':
      return b.t === 'k' && sameYol(a.yol, b.yol) && a.p === b.p && spanCovers(dis.span, ic.span);
  }
}
