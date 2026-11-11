// Unit tests of the pure helpers in src/lib (A15.3).
import { describe, expect, it } from 'vitest';
import { formatDateTime, compareTr, formatNumber } from '@/lib/format';
import { formatIfMatch } from '@/lib/etag';
import {
  isRecord,
  readArray,
  readBoolean,
  readNumber,
  readString,
  readTextPayload,
} from '@/lib/payload';
import { canDecide, canManageUsers, canPublish } from '@/lib/roles';
import { loginHref, safeNext } from '@/lib/safe-next';
import { pickSample, randomBelow, sampleSize } from '@/lib/sample';
import { codePointCount, findUnwritable, isWritable, stripUnwritable } from '@/lib/text';
import { diffText, segmentWords } from '@/lib/text-diff';

describe('safeNext', () => {
  it.each([
    ['/kuyruk/ocr', '/kuyruk/ocr'],
    ['/kuyruk/ocr?kayit=7', '/kuyruk/ocr?kayit=7'],
    ['/birimler?q=a#b', '/birimler?q=a#b'],
    ['/a/../kuyruk/lemma', '/kuyruk/lemma'],
  ])('accepts the local path %s', (raw, expected) => {
    expect(safeNext(raw)).toBe(expected);
  });

  it.each([
    'https://evil.example/',
    'http://evil.example/x',
    '//evil.example/x',
    '/.//evil.example/x',
    '/..//evil.example/x',
    '/a/..//evil.example/x',
    '/%2e//evil.example/x',
    '/\\evil.example',
    '\\\\evil.example',
    'javascript:alert(1)',
    'kuyruk/ocr',
    '/ab\ncd',
    '/ab\tcd',
    '/giris',
    '/giris?sonraki=%2Fa',
    '/yetki-yok',
    '',
    null,
    undefined,
  ])('rejects %j', (raw) => {
    expect(safeNext(raw as string | null | undefined)).toBe('/');
  });

  it('uses the given fallback', () => {
    expect(safeNext('https://evil.example', '/kaynaklar')).toBe('/kaynaklar');
  });

  it('builds the login address with an encoded return path', () => {
    expect(loginHref('/kuyruk/ocr?kayit=7')).toBe('/giris?sonraki=%2Fkuyruk%2Focr%3Fkayit%3D7');
  });
});

describe('text safety', () => {
  it('counts code points, not UTF-16 units', () => {
    expect(codePointCount('')).toBe(0);
    expect(codePointCount('abc')).toBe(3);
    expect(codePointCount('\u{1F600}')).toBe(1); // surrogate pair, 2 units
    expect(codePointCount('a\u{1F600}b')).toBe(3);
    expect(codePointCount('\uD800')).toBe(1); // lone surrogate counts as one
  });

  it('finds NUL and lone surrogates and nothing else', () => {
    expect(findUnwritable('Deneme')).toEqual({ nul: false, loneSurrogate: false });
    expect(findUnwritable('a\u0000b')).toEqual({ nul: true, loneSurrogate: false });
    expect(findUnwritable('a\uD800b')).toEqual({ nul: false, loneSurrogate: true });
    expect(findUnwritable('a\uDC00b')).toEqual({ nul: false, loneSurrogate: true });
    expect(findUnwritable('\uD83D')).toEqual({ nul: false, loneSurrogate: true });
    expect(findUnwritable('\u{1F600}')).toEqual({ nul: false, loneSurrogate: false });
    expect(isWritable('Deneme paragrafı 1')).toBe(true);
    expect(isWritable('x\u0000')).toBe(false);
  });

  it('strips only the unwritable characters', () => {
    expect(stripUnwritable('a\u0000b\uD800c\uDC00d\u{1F600}e')).toBe('abcd\u{1F600}e');
    const arabic = '\u0628\u064e \u062a';
    expect(stripUnwritable(arabic)).toBe(arabic);
  });
});

describe('sample', () => {
  it.each([
    [0, 0],
    [1, 1],
    [9, 1],
    [10, 1],
    [11, 2],
    [20, 2],
    [21, 3],
    [100, 10],
  ])('size for %i records is %i (ceil(n/10))', (total, expected) => {
    expect(sampleSize(total)).toBe(expected);
  });

  it('rejects values in the biased tail (rejection sampling)', () => {
    // max 3: limit is 2^32 - (2^32 mod 3) = 4294967295; the value 4294967295 itself must be thrown away.
    const values = [4294967295, 4294967294];
    let calls = 0;
    const result = randomBelow(3, () => values[calls++]!);
    expect(calls).toBe(2);
    expect(result).toBe(4294967294 % 3);
  });

  it('maps a uniform random value into the range', () => {
    expect(randomBelow(1, () => 123)).toBe(0);
    expect(randomBelow(10, () => 4294967289)).toBe(4294967289 % 10);
    expect(() => randomBelow(0)).toThrow(RangeError);
  });

  it('draws distinct items with a partial Fisher-Yates shuffle and keeps the input', () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const copy = items.slice();
    const sample = pickSample(items, 3, () => 0);
    expect(sample).toEqual([1, 2, 3]);
    expect(items).toEqual(copy);
    const random = pickSample(items, 4);
    expect(new Set(random).size).toBe(4);
    for (const item of random) expect(items).toContain(item);
    expect(pickSample(items, 99)).toHaveLength(10);
    expect(pickSample(items, 0)).toEqual([]);
  });

  it('is roughly uniform over many draws with the real random source', () => {
    const counts = new Map<number, number>();
    const items = [0, 1, 2, 3, 4];
    for (let i = 0; i < 5000; i++) {
      const [first] = pickSample(items, 1);
      counts.set(first!, (counts.get(first!) ?? 0) + 1);
    }
    for (const item of items) expect(counts.get(item) ?? 0).toBeGreaterThan(800);
  });
});

describe('text diff', () => {
  it('splits into words, spaces and punctuation and joins back to the original', () => {
    const text = 'Deneme paragrafı 1, düzeltilmiş.';
    const segments = segmentWords(text);
    expect(segments.join('')).toBe(text);
    expect(segments).toContain('paragrafı');
  });

  it('never separates a combining mark from its letter', () => {
    const word = '\u0628\u064e\u0651'; // beh + fatha + shadda (synthetic letters, not a quotation)
    const segments = segmentWords(`${word} \u062a`);
    expect(segments[0]).toBe(word);
    expect(segments.join('')).toBe(`${word} \u062a`);
    expect(segmentWords('e\u0301 a')[0]).toBe('e\u0301');
  });

  it('shows a word whose mark changed as one removed and one added word', () => {
    const before = '\u0628\u064e \u062a';
    const after = '\u0628\u064f \u062a';
    expect(diffText(before, after)).toEqual([
      { kind: 'removed', text: '\u0628\u064e' },
      { kind: 'added', text: '\u0628\u064f' },
      { kind: 'same', text: ' \u062a' },
    ]);
  });

  it('diffs words and merges neighbours', () => {
    expect(diffText('Deneme paragrafı 1', 'Deneme paragrafı 1 düzeltilmiş')).toEqual([
      { kind: 'same', text: 'Deneme paragrafı 1' },
      { kind: 'added', text: ' düzeltilmiş' },
    ]);
    expect(diffText('a b c', 'a x c')).toEqual([
      { kind: 'same', text: 'a ' },
      { kind: 'removed', text: 'b' },
      { kind: 'added', text: 'x' },
      { kind: 'same', text: ' c' },
    ]);
    expect(diffText('aynı', 'aynı')).toEqual([{ kind: 'same', text: 'aynı' }]);
    expect(diffText('', '')).toEqual([]);
  });

  it('does not normalize: canonically equal but different texts differ', () => {
    const composed = '\u00e9';
    const decomposed = 'e\u0301';
    expect(diffText(composed, decomposed).some((part) => part.kind !== 'same')).toBe(true);
  });
});

describe('payload readers', () => {
  it('read typed values and return null for anything else', () => {
    const value = { a: 'x', n: 3, b: true, list: [1], bad: Number.NaN };
    expect(readString(value, 'a')).toBe('x');
    expect(readString(value, 'n')).toBeNull();
    expect(readNumber(value, 'n')).toBe(3);
    expect(readNumber(value, 'bad')).toBeNull();
    expect(readBoolean(value, 'b')).toBe(true);
    expect(readArray(value, 'list')).toEqual([1]);
    expect(readString(null, 'a')).toBeNull();
    expect(readString([], 'a')).toBeNull();
    expect(isRecord([])).toBe(false);
    expect(isRecord(null)).toBe(false);
  });

  it('reads the unit text payload', () => {
    expect(readTextPayload({ metin: 'Deneme', content_hash: 'h' })).toEqual({
      metin: 'Deneme',
      contentHash: 'h',
    });
    expect(readTextPayload({ metin: 'Deneme' })).toEqual({ metin: 'Deneme', contentHash: null });
    expect(readTextPayload({ alias: 'Deneme-sure' })).toBeNull();
    expect(readTextPayload('Deneme')).toBeNull();
  });
});

describe('roles', () => {
  it('uses the server role names', () => {
    expect(canDecide(['editor'])).toBe(true);
    expect(canDecide(['admin'])).toBe(true);
    expect(canDecide([])).toBe(false);
    expect(canDecide(undefined)).toBe(false);
    expect(canPublish(['editor'])).toBe(false);
    expect(canPublish(['admin'])).toBe(true);
    expect(canManageUsers(['editor', 'admin'])).toBe(true);
    expect(canManageUsers(['editor'])).toBe(false);
  });
});

describe('format', () => {
  it('writes the If-Match value as a quoted xmin', () => {
    expect(formatIfMatch(123)).toBe('"123"');
    expect(formatIfMatch(4294967295)).toBe('"4294967295"');
  });

  it('formats numbers and dates for tr-TR and orders with the Turkish collator', () => {
    expect(formatNumber(1234567)).toBe('1.234.567');
    expect(formatDateTime(null)).toBe('');
    expect(formatDateTime('değil')).toBe('değil');
    expect(formatDateTime('2026-11-01T10:00:00Z')).toMatch(/2026/);
    // Turkish: i before ı before j; ç after c.
    expect(['j', 'ı', 'i', 'ç', 'c'].sort(compareTr)).toEqual(['c', 'ç', 'ı', 'i', 'j']);
  });
});
