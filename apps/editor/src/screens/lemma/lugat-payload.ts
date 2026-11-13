import { isRecord, readArray, readNumber, readString } from '@/lib/payload';
import type { ReviewItem } from '@/review/types';

// Readers of the opaque `onerilen` of a lügat madde review (K-51 madde 10):
// `{anlam_basvuru: [{anlam, sayi}], siklik, kitaplar}`. It is reference data only. Nothing is trusted: a reader
// returns null or an empty list instead of throwing, and the card also offers the raw value.

export interface ReferenceMeaning {
  anlam: string;
  /** How many dictionary or list entries gave this meaning; null when absent. */
  sayi: number | null;
}

export interface LugatReference {
  meanings: ReferenceMeaning[];
  /** Total frequency; null when absent or not a non-negative integer. */
  siklik: number | null;
  /** Books the word occurs in: a count (number) or a list of book slugs; both end as a count. */
  kitaplar: number | null;
  /** At least one known field was found; otherwise only the raw value can be shown. */
  known: boolean;
}

function isCount(value: number | null): value is number {
  return value !== null && Number.isInteger(value) && value >= 0;
}

function readMeaning(entry: unknown): ReferenceMeaning | null {
  if (typeof entry === 'string') return { anlam: entry, sayi: null };
  if (!isRecord(entry)) return null;
  const anlam = readString(entry, 'anlam');
  if (anlam === null) return null;
  const sayi = readNumber(entry, 'sayi');
  return { anlam, sayi: isCount(sayi) ? sayi : null };
}

/** Reads `onerilen`; null when the value is null or undefined. A value without known fields gives `known: false`. */
export function readLugatReference(value: unknown): LugatReference | null {
  if (value === null || value === undefined) return null;
  if (!isRecord(value)) return { meanings: [], siklik: null, kitaplar: null, known: false };
  const meanings = (readArray(value, 'anlam_basvuru') ?? [])
    .map(readMeaning)
    .filter((entry): entry is ReferenceMeaning => entry !== null);
  const siklik = readNumber(value, 'siklik');
  const books = readNumber(value, 'kitaplar');
  const bookList = readArray(value, 'kitaplar');
  const kitaplar = isCount(books) ? books : bookList !== null ? bookList.length : null;
  const frequency = isCount(siklik) ? siklik : null;
  return {
    meanings,
    siklik: frequency,
    kitaplar,
    known: meanings.length > 0 || frequency !== null || kitaplar !== null,
  };
}

/** Total frequency of a list item (`onerilen.siklik`), the key of the queue order; null when absent. */
export function readFrequency(item: Pick<ReviewItem, 'onerilen'>): number | null {
  return readLugatReference(item.onerilen)?.siklik ?? null;
}
