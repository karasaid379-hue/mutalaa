import { readString } from '@/lib/payload';

/**
 * Which page image of which edition a unit belongs to. The field names of the unit's `attrs` become final in
 * A16 (Elmalılı hazırlığı §6); until then the panel reads `baski` and `sayfa` and shows a notice when they are
 * not there. Both values must match the patterns of `GET /scans/{baski}/{sayfa}`, otherwise no request is made.
 */
export interface ScanRef {
  baski: string;
  sayfa: string;
}

export const ATTR_BASKI = 'baski';
export const ATTR_SAYFA = 'sayfa';

const BASKI_PATTERN = /^[a-z0-9-]{1,64}$/;
const SAYFA_PATTERN = /^c[0-9]{2}-s[0-9]{4}$/;

export function readScanRef(attrs: unknown): ScanRef | null {
  const baski = readString(attrs, ATTR_BASKI);
  const sayfa = readString(attrs, ATTR_SAYFA);
  if (baski === null || sayfa === null) return null;
  if (!BASKI_PATTERN.test(baski) || !SAYFA_PATTERN.test(sayfa)) return null;
  return { baski, sayfa };
}
