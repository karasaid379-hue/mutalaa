// @vitest-environment node
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// Amiri Quran 1.003 from google/fonts commit 6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec (A15 Tedarik).
// The panel copy must stay byte for byte equal to the downloaded source file.
const EXPECTED_SIZE = 136920;
const EXPECTED_SHA256 = 'e2a47644762d16bdfb6d33e0d8db8c6ff30beae84150ef5a705316bbd829455c';

describe('Amiri Quran font copy', () => {
  const bytes = readFileSync(new URL('../public/fonts/AmiriQuran-Regular.ttf', import.meta.url));

  it('has the recorded size', () => {
    expect(bytes.length).toBe(EXPECTED_SIZE);
  });

  it('has the recorded SHA-256', () => {
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(EXPECTED_SHA256);
  });

  it('ships the OFL licence next to the font', () => {
    const licence = readFileSync(new URL('../public/fonts/OFL.txt', import.meta.url), 'utf8');
    expect(licence).toContain('SIL OPEN FONT LICENSE');
  });
});
