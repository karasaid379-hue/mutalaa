import { tryParse } from '@mutalaa/anchors';
import { isRecord, readArray, readBoolean, readNumber, readString } from '@/lib/payload';
import type { ReviewItem } from '@/review/types';

// Readers of the opaque JSON of a word meaning review (`onceki`, `onerilen`, `duzenlenen`, `yz_kaydi`).
// The API types these `unknown`, and the lemma payload shape is not fixed by the contract yet; the fields
// below follow the draft output of Kelime anlamları §5 and the ready-source candidate of K-50 madde 5. Nothing is trusted: a reader returns null or an
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
 * The confidence of a draft: the API's `guven` field first (for a ready-source candidate it is the dominant
 * share, K-50 madde 5), then `baskin_pay` or `guven` inside `onerilen`, then `guven` inside `yz_kaydi`. null
 * when none of them has one (the screen then says the record carries no confidence).
 */
export function readConfidence(review: ConfidenceSource): number | null {
  if (typeof review.guven === 'number' && Number.isFinite(review.guven)) return review.guven;
  return (
    readNumber(review.onerilen, 'baskin_pay') ??
    readNumber(review.onerilen, 'guven') ??
    readNumber(review.yz_kaydi, 'guven')
  );
}

/** Whether a supporting ayah entry is a valid anchor; parsing is done by `@mutalaa/anchors` only. */
export function isAnchor(text: string): boolean {
  return tryParse(text) !== null;
}

/**
 * Share of the dominant ready meaning at and above which a lemma counts as consistent ("tutarlı"); below it
 * it is a "tutarsız hazır anlam" (K-50 madde 5; the threshold never changes the candidate set).
 */
export const CONSISTENT_SHARE_THRESHOLD = 0.8;

export type Consistency = 'tutarli' | 'tutarsiz';

/** Consistency mark of a dominant share. */
export function consistencyOf(share: number): Consistency {
  return share >= CONSISTENT_SHARE_THRESHOLD ? 'tutarli' : 'tutarsiz';
}

/** One entry of the ready-source distribution (`onerilen.dagilim`): the meaning and how many words carry it. */
export interface DistributionEntry {
  anlam: string;
  sayi: number;
}

/** The ready-source distribution of a candidate; an unreadable entry is dropped. It is never applied to the target. */
export function readDistribution(value: unknown): DistributionEntry[] {
  return (readArray(value, 'dagilim') ?? []).flatMap((entry) => {
    const anlam = readString(entry, 'anlam');
    const sayi = readNumber(entry, 'sayi');
    return anlam !== null && sayi !== null ? [{ anlam, sayi }] : [];
  });
}

/** Whether a number can be a share or a confidence (0 to 1 inclusive). */
export function isShare(value: number): boolean {
  return value >= 0 && value <= 1;
}

type CandidateSource = Pick<ReviewItem, 'yz_modeli' | 'onerilen'> & {
  hedef?: { origin?: string | null } | null;
};

/**
 * Whether the record is a ready-source candidate (K-50 madde 5), as opposed to an AI draft: no AI model, and
 * either the target's origin is `kaynak:<slug>` or the proposal carries a `baskin_pay`. Only a ready-source
 * candidate has a dominant share and a consistent or inconsistent mark; the confidence of an AI draft is a
 * plain "Güven".
 */
export function isReadyCandidate(review: CandidateSource): boolean {
  if (typeof review.yz_modeli === 'string' && review.yz_modeli !== '') return false;
  const origin = review.hedef?.origin;
  return (
    (typeof origin === 'string' && origin.startsWith('kaynak:')) ||
    readNumber(review.onerilen, 'baskin_pay') !== null
  );
}

/** Whether a text has Arabic letters (the four Arabic blocks); other values are shown as technical left to right text. */
export function hasArabicLetters(text: string): boolean {
  return /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/u.test(text);
}
