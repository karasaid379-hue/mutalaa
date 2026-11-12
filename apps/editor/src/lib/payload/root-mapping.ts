import { isRecord, readBoolean, readNumber, readString } from './record';

// Readers of the opaque JSON of a Turkish lemma root mapping review (`lemma` + `kok_eslemesi`, K-51 madde 9):
// the proposal and the edited value are `{root_id, ar_lemma_id, etymological_only}`, an objection to an automatic
// approval is `{itiraz: true, gerekce}`. Nothing is trusted; a reader returns null instead of throwing.

export interface RootMapping {
  rootId: number | null;
  arLemmaId: number | null;
  etymologicalOnly: boolean | null;
}

function readId(record: unknown, key: string): number | null {
  const value = readNumber(record, key);
  return value !== null && Number.isSafeInteger(value) && value > 0 ? value : null;
}

/** The mapping value of a payload; null when it is not an object or carries none of the three fields. */
export function readRootMapping(value: unknown): RootMapping | null {
  if (!isRecord(value)) return null;
  const mapping: RootMapping = {
    rootId: readId(value, 'root_id'),
    arLemmaId: readId(value, 'ar_lemma_id'),
    etymologicalOnly: readBoolean(value, 'etymological_only'),
  };
  return mapping.rootId === null && mapping.arLemmaId === null && mapping.etymologicalOnly === null
    ? null
    : mapping;
}

/** Whether a proposal is an objection to an automatic approval (`onerilen.itiraz = true`). */
export function isObjectionPayload(value: unknown): boolean {
  return isRecord(value) && value.itiraz === true;
}

/** The reason an objection carries (`onerilen.gerekce`), or null. */
export function readObjectionReason(value: unknown): string | null {
  return isObjectionPayload(value) ? readString(value, 'gerekce') : null;
}
