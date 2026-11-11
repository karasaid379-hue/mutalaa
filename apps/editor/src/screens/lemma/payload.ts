import { tryParse } from '@mutalaa/anchors';
import { isRecord, readArray, readBoolean, readNumber, readString } from '@/lib/payload';
import type { ReviewItem } from '@/review/types';

// Readers of the opaque JSON of a word meaning review (`onceki`, `onerilen`, `duzenlenen`, `yz_kaydi`).
// The API types these `unknown`, and the lemma payload shape is not fixed by the contract yet; the fields
// below follow the draft output of Kelime anlamları §5. Nothing is trusted: a reader returns null or an
// empty list instead of throwing, and the screen always offers the raw value next to the readable one.

/** The readable fields of a lemma payload; every field is optional. */
export interface LemmaValue {
  /** The value was a plain string (not an object). */
  plain: string | null;
  anlamKisa: string | null;
  kuranAnlamlari: string[];
  turkceEsKelime: string | null;
  status: string | null;
  eminDegil: boolean | null;
  yalnizcaEtimolojikAdayi: boolean | null;
  dayanakAyetler: string[];
  gerekce: string | null;
  guven: number | null;
  /** Whether at least one known field was found; otherwise only the raw value can be shown. */
  known: boolean;
}

function readStrings(value: unknown, key: string): string[] {
  return (readArray(value, key) ?? []).filter(
    (entry): entry is string => typeof entry === 'string',
  );
}

function emptyValue(): LemmaValue {
  return {
    plain: null,
    anlamKisa: null,
    kuranAnlamlari: [],
    turkceEsKelime: null,
    status: null,
    eminDegil: null,
    yalnizcaEtimolojikAdayi: null,
    dayanakAyetler: [],
    gerekce: null,
    guven: null,
    known: false,
  };
}

/**
 * Reads a lemma payload. null when the value is null or undefined; a type without readable fields gives
 * `known: false` (the screen then shows only the raw value).
 */
export function readLemmaValue(value: unknown): LemmaValue | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return { ...emptyValue(), plain: value, known: true };
  if (!isRecord(value)) return emptyValue();
  const result: LemmaValue = {
    ...emptyValue(),
    anlamKisa: readString(value, 'anlam_kisa'),
    kuranAnlamlari: readStrings(value, 'kuran_anlamlari'),
    turkceEsKelime: readString(value, 'turkce_es_kelime'),
    status: readString(value, 'status'),
    eminDegil: readBoolean(value, 'emin_degil'),
    yalnizcaEtimolojikAdayi: readBoolean(value, 'yalnizca_etimolojik_adayi'),
    dayanakAyetler: readStrings(value, 'dayanak_ayetler'),
    gerekce: readString(value, 'gerekce'),
    guven: readNumber(value, 'guven'),
  };
  result.known =
    result.anlamKisa !== null ||
    result.kuranAnlamlari.length > 0 ||
    result.turkceEsKelime !== null ||
    result.status !== null ||
    result.eminDegil !== null ||
    result.yalnizcaEtimolojikAdayi !== null ||
    result.dayanakAyetler.length > 0 ||
    result.gerekce !== null;
  return result;
}

/** The G-YZ record of an AI draft (K-37): prompt id and the two digests. */
export interface YzRecord {
  promptId: string | null;
  promptSha256: string | null;
  inputSha256: string | null;
}

/** null when `yz_kaydi` is empty or not an object. */
export function readYzRecord(value: unknown): YzRecord | null {
  if (!isRecord(value)) return null;
  return {
    promptId: readString(value, 'prompt_id'),
    promptSha256: readString(value, 'prompt_sha256'),
    inputSha256: readString(value, 'input_sha256'),
  };
}

type ConfidenceSource = Pick<ReviewItem, 'guven' | 'onerilen' | 'yz_kaydi'>;

/**
 * The confidence of a draft: the API's `guven` field first, then a `guven` number inside `onerilen`, then
 * inside `yz_kaydi`. null when none of them has one (the screen then marks the section as missing).
 */
export function readConfidence(review: ConfidenceSource): number | null {
  if (typeof review.guven === 'number' && Number.isFinite(review.guven)) return review.guven;
  return readNumber(review.onerilen, 'guven') ?? readNumber(review.yz_kaydi, 'guven');
}

/** Whether a supporting ayah entry is a valid anchor; parsing is done by `@mutalaa/anchors` only. */
export function isAnchor(text: string): boolean {
  return tryParse(text) !== null;
}
