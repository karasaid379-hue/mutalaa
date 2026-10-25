import { format } from './format.js';
import { tryParse } from './parse.js';
import { ROUTE_SCHEMES } from './types.js';
import type { Anchor, AnchorRef } from './types.js';

// Routes (Capa semasi 11, K-35 item 6). Only plain string operations are used: no URL class
// (Hermes has an incomplete one).

const DEFAULT_SCHEME = 'mutalaa';

function checkScheme(sema: string): void {
  if (!(ROUTE_SCHEMES as readonly string[]).includes(sema)) {
    throw new RangeError(`toRoute: unknown scheme ${JSON.stringify(sema)}`);
  }
}

function nativeRoute(r: AnchorRef, sema: string): string {
  const path = format({ anchor: r.anchor }).split(':').join('/');
  const query = r.span === undefined ? '' : `?aralik=${r.span.start}-${r.span.end}`;
  return `${sema}://${path}${query}`;
}

/** Web route table of Capa semasi 11; null where the table has no entry. */
function webRoute(r: AnchorRef): string | null {
  const a: Anchor = r.anchor;
  const spanned = r.span !== undefined;
  switch (a.t) {
    case 'q':
      if (a.ilk === undefined) return `/kuran/${a.sure}/${a.ayet}`;
      if (a.son === undefined) return null; // a single word is not in the table
      return `/kuran/${a.sure}/${a.ayet}?k=${a.ilk}-${a.son}`;
    case 'qa':
      return `/kuran/${a.sure}/${a.ilk}-${a.son}`;
    case 'konu':
      return `/konu/${a.slug}`;
    case 'meal':
      return spanned ? null : `/meal/${a.meal}/${a.sure}#${a.ayet}`;
    case 'tf':
      return spanned ? null : `/tefsir/${a.eser}/${a.sure}/${a.ilk}#p${a.p}`;
    case 'rn':
      return a.s === undefined ? `/risale/${a.yol.join('/')}#p${a.p}` : null;
    case 'h':
      return spanned ? null : `/hadis/${a.koleksiyon}/${a.no}`;
    default:
      return null; // tfb, ht, k
  }
}

/**
 * Route for an anchor. `native` is mechanical for every kind. `web` follows the table only
 * and throws for any other kind.
 */
export function toRoute(r: AnchorRef, hedef: 'native' | 'web', sema?: string): string {
  if (hedef === 'native') {
    const scheme = sema ?? DEFAULT_SCHEME;
    checkScheme(scheme);
    return nativeRoute(r, scheme);
  }
  const route = webRoute(r);
  if (route === null) {
    throw new RangeError(`toRoute: no web route for ${format(r)}`);
  }
  return route;
}

/** Anchor from a native route; null for other schemes or an invalid route. */
export function fromRoute(url: string): AnchorRef | null {
  if (typeof url !== 'string') return null;
  const sep = url.indexOf('://');
  if (sep < 0) return null;
  const scheme = url.slice(0, sep);
  if (!(ROUTE_SCHEMES as readonly string[]).includes(scheme)) return null;

  const rest = url.slice(sep + 3);
  const q = rest.indexOf('?');
  const path = q < 0 ? rest : rest.slice(0, q);
  if (path.includes(':') || path.includes('@')) return null;

  let canonical = path.split('/').join(':');
  if (q >= 0) {
    const query = rest.slice(q + 1);
    const key = 'aralik=';
    if (!query.startsWith(key)) return null;
    canonical += `@${query.slice(key.length)}`;
  }
  return tryParse(canonical);
}
