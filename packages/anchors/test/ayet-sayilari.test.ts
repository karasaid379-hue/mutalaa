import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { AYET_SAYILARI } from '../src/generated/ayet-sayilari.js';
import { sharedDataRoot } from './vectors.js';

describe('AYET_SAYILARI', () => {
  it('has 114 entries that sum to 6236, with Bakara = 286', () => {
    expect(AYET_SAYILARI).toHaveLength(114);
    expect(AYET_SAYILARI.reduce((sum, n) => sum + n, 0)).toBe(6236);
    expect(AYET_SAYILARI[1]).toBe(286);
  });

  it('equals the generated copy shared/data/ayet-sayilari.json', () => {
    const json = JSON.parse(readFileSync(join(sharedDataRoot, 'ayet-sayilari.json'), 'utf8')) as {
      sayilar: number[];
    };
    expect([...AYET_SAYILARI]).toStrictEqual(json.sayilar);
  });
});
