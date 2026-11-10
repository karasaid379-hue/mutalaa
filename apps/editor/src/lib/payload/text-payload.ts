import { readString } from './record';

/** `{ "metin": ..., "content_hash": ... }` as stored in `onceki`, `onerilen` and `duzenlenen` of a unit text review. */
export interface TextPayload {
  metin: string;
  contentHash: string | null;
}

/** Reads a unit text payload; null when the value is not an object with a string `metin`. */
export function readTextPayload(value: unknown): TextPayload | null {
  const metin = readString(value, 'metin');
  if (metin === null) return null;
  return { metin, contentHash: readString(value, 'content_hash') };
}
