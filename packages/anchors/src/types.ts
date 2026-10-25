// Anchor types (Capa semasi 11). Offsets are Unicode code points, ranges are half open.

export type Anchor =
  | { t: 'q'; sure: number; ayet: number; ilk?: number; son?: number } // ilk alone: a word
  | { t: 'qa'; sure: number; ilk: number; son: number } // ayah range
  | { t: 'konu'; slug: string }
  | { t: 'meal'; meal: string; sure: number; ayet: number }
  | { t: 'tf'; eser: string; sure: number; ilk: number; son: number; p: number }
  | { t: 'tfb'; eser: string; bolum: string; p: number }
  | { t: 'rn'; yol: string[]; p: number; s?: number } // yol[0] is the book
  | { t: 'h'; koleksiyon: string; no: number }
  | { t: 'ht'; ceviri: string; koleksiyon: string; no: number }
  | { t: 'k'; yol: string[]; p: number };

/** Code point span, [start, end). */
export interface Span {
  start: number;
  end: number;
}

export interface AnchorRef {
  anchor: Anchor;
  span?: Span;
}

/** Local route schemes, chosen by build flavor (K-35 item 6). */
export const ROUTE_SCHEMES = ['mutalaa', 'mutalaa-internal', 'mutalaa-dev'] as const;
