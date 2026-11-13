import { isRecord, readBoolean, readNumber, readString } from '@/lib/payload';
import type { LinkClass } from '@/review/queries';
import type { HighlightedSequence, ReviewStats } from '@/review/types';
import { isLinkClass } from './config';

// Readers of the link candidate snapshot (`hedef` of `GET /reviews/{id}`). The evidence summary is an opaque JSON
// value (`evidence_ozeti`); nothing here trusts its shape: every reader returns null instead of throwing, and
// nothing is computed or invented (a missing value is simply not shown).

/** The class of a record (`sinif`); null when the API gives none or a value the panel does not know. */
export function readLinkClass(value: string | null | undefined): LinkClass | null {
  return isLinkClass(value) ? value : null;
}

/** Open count of a class from `GET /reviews/stats` (`baglanti_siniflari`); undefined while the stats are unknown. */
export function classCount(stats: ReviewStats | undefined, sinif: LinkClass): number | undefined {
  if (!stats) return undefined;
  return stats.baglanti_siniflari.find((entry) => entry.sinif === sinif)?.acik ?? 0;
}

/** One alternative target of the evidence: its scalar entries as text, or a plain value. */
export interface Alternative {
  entries: readonly { key: string | null; value: string }[];
}

export interface EvidenceFacts {
  /** 0 to 1. */
  coverage: number | null;
  matchedWords: number | null;
  ayahWords: number | null;
  /** 0 to 1. */
  identity: number | null;
  phraseFreq: number | null;
  /** True: an explicit citation is consistent with the match; false: it is not; null: unknown. */
  consistentQuote: boolean | null;
  position: string | null;
  subtype: string | null;
  group: string | null;
  editorFix: boolean;
  alternatives: readonly Alternative[];
}

function scalarText(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return null;
}

function readAlternatives(value: unknown): Alternative[] {
  if (!Array.isArray(value)) return [];
  const result: Alternative[] = [];
  for (const item of value) {
    if (isRecord(item)) {
      const entries = Object.entries(item).flatMap(([key, entry]) => {
        const text = scalarText(entry);
        return text === null ? [] : [{ key, value: text }];
      });
      if (entries.length > 0) result.push({ entries });
    } else {
      const text = scalarText(item);
      if (text !== null) result.push({ entries: [{ key: null, value: text }] });
    }
  }
  return result;
}

/** The evidence summary of a candidate; null when the API gave none (null or not an object). */
export function readEvidence(value: unknown): EvidenceFacts | null {
  if (!isRecord(value)) return null;
  const group = value.group;
  return {
    coverage: readNumber(value, 'coverage'),
    matchedWords: readNumber(value, 'matched_words'),
    ayahWords: readNumber(value, 'ayah_words'),
    identity: readNumber(value, 'identity'),
    phraseFreq: readNumber(value, 'phrase_freq'),
    consistentQuote: readBoolean(value, 'consistent_quote'),
    position: readString(value, 'position'),
    subtype: readString(value, 'subtype'),
    group: scalarText(group),
    editorFix: readBoolean(value, 'editor_duzeltmesi') === true,
    alternatives: readAlternatives(value.alternatives),
  };
}

/** Whether the evidence has anything to show in the summary line. */
export function hasSummaryFacts(facts: EvidenceFacts): boolean {
  return (
    facts.coverage !== null ||
    facts.matchedWords !== null ||
    facts.ayahWords !== null ||
    facts.identity !== null ||
    facts.phraseFreq !== null ||
    facts.consistentQuote !== null ||
    facts.position !== null ||
    facts.subtype !== null ||
    facts.group !== null ||
    facts.editorFix
  );
}

export interface Highlight {
  before: string | null;
  sequence: string;
  after: string | null;
}

/**
 * The highlighted sequence (`vurgulu_dizi`) of the source paragraph. The API gives all three parts as null when
 * the paragraph changed after the link was found (the stored offsets no longer fit); then there is nothing to
 * highlight and the card says "Metin güncel değil". A sequence without its middle part is the same case.
 */
export function readHighlight(value: HighlightedSequence | null | undefined): Highlight | null {
  if (!value || value.dizi === null || value.dizi === undefined || value.dizi === '') return null;
  return { before: value.sol ?? null, sequence: value.dizi, after: value.sag ?? null };
}

/** A span `[start, end)` of the snapshot; null when it is missing or not two integers. */
export function readSpan(value: readonly number[] | null | undefined): [number, number] | null {
  if (!value || value.length !== 2) return null;
  const [start, end] = value;
  return Number.isInteger(start) && Number.isInteger(end) ? [start!, end!] : null;
}
