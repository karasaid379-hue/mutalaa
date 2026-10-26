import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  DERLEME_TURU,
  INCELEME_DURUMU,
  LICENSE_STATUS,
  METIN_DURUMU,
  SOURCE_KIND,
  SURUM_DURUMU,
  UNIT_KIND,
  UNIT_STATUS,
  XREF_ORIGIN,
  XREF_STATUS,
  XREF_TYPE,
} from '../src/enums.js';

interface EnumsFile {
  version: number;
  enums: Record<string, string[]>;
}

const json = JSON.parse(
  readFileSync(new URL('../enums.json', import.meta.url), 'utf8'),
) as EnumsFile;

// JSON key -> code constant. A new JSON key without an entry here fails the key-set test.
const IN_CODE: Record<string, readonly string[]> = {
  license_status: LICENSE_STATUS,
  xref_type: XREF_TYPE,
  xref_status: XREF_STATUS,
  xref_origin: XREF_ORIGIN,
  source_kind: SOURCE_KIND,
  derleme_turu: DERLEME_TURU,
  unit_kind: UNIT_KIND,
  unit_status: UNIT_STATUS,
  metin_durumu: METIN_DURUMU,
  inceleme_durumu: INCELEME_DURUMU,
  surum_durumu: SURUM_DURUMU,
};

describe('enums.json <-> src/enums.ts', () => {
  it('code covers exactly the enum keys of the JSON', () => {
    expect(Object.keys(IN_CODE).sort()).toStrictEqual(Object.keys(json.enums).sort());
  });

  it.each(Object.keys(IN_CODE))('%s has the same values in the same order', (key) => {
    expect([...(IN_CODE[key] ?? [])]).toStrictEqual(json.enums[key]);
  });

  it('values are unique within each enum', () => {
    for (const [key, values] of Object.entries(json.enums)) {
      expect(new Set(values).size, key).toBe(values.length);
    }
  });

  it('license_status order is serbest < bekliyor < ic_kullanim < kapali', () => {
    expect([...LICENSE_STATUS]).toStrictEqual(['serbest', 'bekliyor', 'ic_kullanim', 'kapali']);
    expect(json.enums['license_status']).toStrictEqual([
      'serbest',
      'bekliyor',
      'ic_kullanim',
      'kapali',
    ]);
  });
});
