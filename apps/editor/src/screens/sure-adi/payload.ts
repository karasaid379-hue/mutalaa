import { isRecord, readArray, readBoolean, readNumber, readString } from '@/lib/payload';
import { compareTr } from '@/lib/format';
import type { ReviewItem } from '@/review/types';

// Readers of the `onerilen` value of a surah name review (K-43 madde 4): `kind`, `alias`, `risky`, `kaynaklar`,
// `anlam`, `tanzil_fark`, `yazimlar`. Nothing is trusted: every reader returns null or an empty list.

/** One entry of `kaynaklar` (file and line of the source, or the rule that produced the spelling). */
export interface SourceRef {
  kaynak: string | null;
  dosya: string | null;
  satir: number | null;
  yol: string | null;
  alan: string | null;
  kural: string | null;
}

/** One side of the Tanzil difference: the three values the pipeline compares. */
export interface FarkSide {
  ayet: string | null;
  yer: string | null;
  inis_sirasi: string | null;
}

export interface TanzilFark {
  /** Names of the fields that differ (`ayet`, `yer`, `inis_sirasi`). */
  alanlar: string[];
  vikipedi: FarkSide;
  tanzil: FarkSide;
}

export interface SureAdiPayload {
  kind: string | null;
  alias: string | null;
  /** null when the value is missing or not a boolean: such a row is treated as risky (single decision only). */
  risky: boolean | null;
  anlam: string | null;
  yazimlar: string[];
  kaynaklar: SourceRef[];
  tanzilFark: TanzilFark | null;
}

function stringOrNumber(record: unknown, key: string): string | null {
  const text = readString(record, key);
  if (text !== null) return text;
  const number = readNumber(record, key);
  return number === null ? null : String(number);
}

function readSide(value: unknown): FarkSide {
  return {
    ayet: stringOrNumber(value, 'ayet'),
    yer: stringOrNumber(value, 'yer'),
    inis_sirasi: stringOrNumber(value, 'inis_sirasi'),
  };
}

function readStrings(value: unknown, key: string): string[] {
  return (readArray(value, key) ?? []).filter(
    (entry): entry is string => typeof entry === 'string',
  );
}

function readSource(value: unknown): SourceRef {
  return {
    kaynak: readString(value, 'kaynak'),
    dosya: readString(value, 'dosya'),
    satir: readNumber(value, 'satir'),
    yol: readString(value, 'yol'),
    alan: readString(value, 'alan'),
    kural: readString(value, 'kural'),
  };
}

function readFark(value: unknown): TanzilFark | null {
  if (!isRecord(value)) return null;
  const record = value;
  return {
    alanlar: readStrings(record, 'alanlar'),
    vikipedi: readSide(record.vikipedi),
    tanzil: readSide(record.tanzil),
  };
}

/** Reads `onerilen` of a surah name review; null when it is not an object. */
export function readSureAdiPayload(value: unknown): SureAdiPayload | null {
  if (!isRecord(value)) return null;
  return {
    kind: readString(value, 'kind'),
    alias: readString(value, 'alias'),
    risky: readBoolean(value, 'risky'),
    anlam: readString(value, 'anlam'),
    yazimlar: readStrings(value, 'yazimlar'),
    kaynaklar: (readArray(value, 'kaynaklar') ?? []).map(readSource),
    tanzilFark: readFark(value.tanzil_fark),
  };
}

/** Only an explicit `risky: false` may join a bulk approval; missing or unreadable counts as risky. */
export function isBulkSelectable(payload: SureAdiPayload | null): boolean {
  return payload !== null && payload.risky === false;
}

const SURE_NO = /^[0-9]{1,3}$/;

/**
 * The surah number of `hedef_anahtar` (`{surah_no}:{alias}`, split at the first colon). Only the number is
 * read; the rest of the key is not interpreted here. null when the part before the first colon is not a number.
 */
export function surahNoOf(hedefAnahtar: string): number | null {
  const index = hedefAnahtar.indexOf(':');
  const head = index < 0 ? hedefAnahtar : hedefAnahtar.slice(0, index);
  return SURE_NO.test(head) ? Number(head) : null;
}

/** Order of the kinds inside a group (pipeline `KIND_SIRASI`): kanonik, yazim, diger_ad, arapca; unknown last. */
const KIND_ORDER: Readonly<Record<string, number>> = {
  kanonik: 0,
  yazim: 1,
  diger_ad: 2,
  arapca: 3,
};

export function kindRank(kind: string | null): number {
  return kind !== null && Object.hasOwn(KIND_ORDER, kind) ? (KIND_ORDER[kind] ?? 4) : 4;
}

export interface SureAdiRow {
  item: ReviewItem;
  payload: SureAdiPayload | null;
  /** Shown name: `onerilen.alias`, else the raw `hedef_anahtar` (the key is not taken apart). */
  alias: string;
  selectable: boolean;
}

export interface SureAdiGroup {
  /** The surah number; null for keys whose number could not be read (shown last). */
  sure: number | null;
  rows: SureAdiRow[];
}

function toRow(item: ReviewItem): SureAdiRow {
  const payload = readSureAdiPayload(item.onerilen);
  return {
    item,
    payload,
    alias: payload?.alias ?? item.hedef_anahtar,
    selectable: isBulkSelectable(payload),
  };
}

function compareRows(a: SureAdiRow, b: SureAdiRow): number {
  return (
    kindRank(a.payload?.kind ?? null) - kindRank(b.payload?.kind ?? null) ||
    compareTr(a.alias, b.alias) ||
    a.item.id - b.item.id
  );
}

/**
 * Groups the records by surah: numeric surah order (unreadable numbers last), inside a group the kind order
 * and then `Collator('tr')` on the name (the id breaks ties so the order is stable).
 */
export function groupBySurah(items: readonly ReviewItem[]): SureAdiGroup[] {
  const groups = new Map<number | null, SureAdiRow[]>();
  for (const item of items) {
    const key = surahNoOf(item.hedef_anahtar);
    const rows = groups.get(key);
    if (rows) rows.push(toRow(item));
    else groups.set(key, [toRow(item)]);
  }
  return [...groups.entries()]
    .map(([sure, rows]) => ({ sure, rows: rows.sort(compareRows) }))
    .sort((a, b) => {
      if (a.sure === null) return b.sure === null ? 0 : 1;
      if (b.sure === null) return -1;
      return a.sure - b.sure;
    });
}
