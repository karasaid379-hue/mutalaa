import { describe, expect, it } from 'vitest';
import { checkUnitAnchor } from '@/screens/catalog/anchor-check';
import {
  cpLength,
  layoutMarks,
  readDigests,
  readMarks,
  readSentences,
} from '@/screens/catalog/readers';
import { isPreparing, pollInterval, RELEASE_POLL_MS } from '@/screens/catalog/polling';

describe('checkUnitAnchor', () => {
  it.each([
    'q:2:255',
    'q:1:1',
    'rn:deneme:p1',
    'rn:deneme:bolum-1:p4',
    'meal:deneme:2:255',
    'h:deneme:15',
  ])('accepts the unit anchor %s', (anchor) => {
    expect(checkUnitAnchor(anchor)).toEqual({ ok: true });
  });

  it.each([
    ['q:115:1', 'SURE_ARALIGI'],
    ['q:2:287', 'AYET_ARALIGI'],
    ['q:2:255:7-3', 'TERS_ARALIK'],
    ['q:2:255-255', 'KANONIK_DEGIL'],
    ['Q:2:255', 'BICIM'],
    [' q:2:255', 'BICIM'],
    ['q:2:255 ', 'BICIM'],
    ['', 'BICIM'],
    ['q:2:255@0-10', 'BICIM'],
  ] as const)('rejects %j with %s', (anchor, code) => {
    expect(checkUnitAnchor(anchor)).toEqual({ ok: false, reason: 'invalid', code });
  });

  it.each([
    'q:2:255:3',
    'q:2:255:3-7',
    'q:2:255-257',
    'rn:deneme:p1:s2',
    'rn:deneme:p1@0-5',
    'konu:deneme',
  ])('rejects the valid non-unit anchor %s', (anchor) => {
    expect(checkUnitAnchor(anchor)).toEqual({ ok: false, reason: 'not-unit' });
  });
});

describe('marks', () => {
  const text = 'a😀b';

  it('reads offsets as code points', () => {
    expect(cpLength(text)).toBe(3);
    const marks = readMarks([{ s: 1, e: 2, t: 'ar' }], cpLength(text))!;
    const { segments } = layoutMarks(text, marks);
    expect(segments.map((segment) => segment.text)).toEqual(['a', '😀', 'b']);
    expect(segments.map((segment) => segment.marks)).toEqual([[], [1], []]);
  });

  it('gives back the stored text however the marks overlap', () => {
    const stored = '  Deneme 😀 paragrafı\n ';
    const length = cpLength(stored);
    const marks = readMarks(
      [
        { s: 2, e: 9, t: 'a' },
        { s: 5, e: 12, t: 'b' },
        { s: 0, e: length, t: 'c' },
        { s: 7, t: 'nokta' },
        { s: length, t: 'son' },
      ],
      length,
    )!;
    const { segments, points } = layoutMarks(stored, marks);
    expect(segments.map((segment) => segment.text).join('')).toBe(stored);
    // A segment inside two ranges carries both numbers.
    const both = segments.find((segment) => segment.marks.includes(1) && segment.marks.includes(2));
    expect(both?.marks).toEqual([1, 2, 3]);
    // The point at the very end sits after the last segment.
    expect(points.find((point) => point.index === 5)?.before).toBe(segments.length);
  });

  it('flags a range outside the text, an empty range and a missing type, and does not draw them', () => {
    const marks = readMarks(
      [
        { s: 0, e: 99, t: 'a' },
        { s: 2, e: 2, t: 'b' },
        { s: 1, e: 2 },
        { s: -1, e: 2, t: 'c' },
        { s: 1.5, e: 2, t: 'd' },
        'metin',
      ],
      3,
    )!;
    expect(marks.map((mark) => mark.valid)).toEqual([false, false, false, false, false, false]);
    const { segments, points } = layoutMarks(text, marks);
    expect(segments).toEqual([{ text, marks: [] }]);
    expect(points).toEqual([]);
  });

  it('is null for a value that is not an array', () => {
    expect(readMarks({}, 3)).toBeNull();
    expect(readMarks(null, 3)).toBeNull();
    expect(readMarks('x', 3)).toBeNull();
  });

  it('reads sentence ranges and flags the ones outside the text', () => {
    expect(readSentences(null, 5)).toEqual([]);
    const entries = readSentences(
      [
        [0, 3],
        [3, 9],
        [4, 4],
      ],
      5,
    );
    expect(entries.map((entry) => entry.valid)).toEqual([true, false, false]);
  });
});

describe('readDigests', () => {
  it('reads both maps and tolerates a missing one', () => {
    expect(readDigests({ kaynaklar: { a: 'x' }, paketler: { p: 'y' } })).toEqual({
      sources: [{ name: 'a', digest: 'x' }],
      packs: [{ name: 'p', digest: 'y' }],
    });
    expect(readDigests({})).toEqual({ sources: [], packs: [] });
  });

  it.each([[null], ['metin'], [{ kaynaklar: [] }], [{ paketler: { p: 1 } }]])(
    'is null for %j',
    (value) => {
      expect(readDigests(value)).toBeNull();
    },
  );
});

describe('polling', () => {
  it('polls every 5 seconds only while a release is being prepared and polling is on', () => {
    expect(RELEASE_POLL_MS).toBe(5000);
    expect(isPreparing('hazirlaniyor')).toBe(true);
    for (const durum of [
      'dogrulandi',
      'yayinlandi',
      'basarisiz',
      'geri_cekildi',
      undefined,
      null,
    ]) {
      expect(isPreparing(durum)).toBe(false);
    }
    expect(pollInterval(true, true)).toBe(5000);
    expect(pollInterval(false, true)).toBe(false);
    expect(pollInterval(true, false)).toBe(false);
  });
});
