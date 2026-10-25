import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  NORMALIZER_VERSION,
  normalizeAr,
  normalizeTr,
  searchKeys,
  splitScripts,
} from '../src/index.js';
import { normalizeTrWith } from '../src/normalize.js';
import { IC_KESME } from '../src/generated/ic-kesme.js';
import { readVectors, sharedDataRoot } from './vectors.js';

interface TrExpected {
  dar: string;
  genis: string;
}

describe('normalize/tr.jsonl', () => {
  const rows = readVectors<string, TrExpected>('normalize/tr.jsonl');
  test('has rows', () => {
    expect(rows.length).toBeGreaterThan(0);
  });
  test.each(rows)('$id', ({ input, expected }) => {
    expect(normalizeTr(input, 'dar')).toBe(expected.dar);
    expect(normalizeTr(input, 'genis')).toBe(expected.genis);
    expect(searchKeys(input)).toMatchObject({
      trNarrow: expected.dar,
      trWide: expected.genis,
    });
  });
});

describe('normalize/ar.jsonl', () => {
  const rows = readVectors<string, string>('normalize/ar.jsonl');
  test('has rows', () => {
    expect(rows.length).toBeGreaterThan(0);
  });
  test.each(rows)('$id', ({ input, expected }) => {
    expect(normalizeAr(input)).toBe(expected);
    expect(searchKeys(input).arNorm).toBe(expected);
  });
});

describe('in-word apostrophe list', () => {
  test('generated IC_KESME equals shared/data/ic-kesme.txt', () => {
    const content = readFileSync(join(sharedDataRoot, 'ic-kesme.txt'), 'utf8');
    const lines = content.split('\n');
    if (lines.at(-1) === '') lines.pop();
    expect([...IC_KESME]).toStrictEqual(lines);
  });

  test('the longest matching entry wins, whatever the list order', () => {
    const list = ["a'b", "a'bc'd"];
    for (const ordered of [list, [...list].reverse()]) {
      expect(normalizeTrWith("A'Bc'd", 'dar', ordered)).toBe('abcd');
      expect(normalizeTrWith("a'bc'd'e", 'dar', ordered)).toBe('abcd');
    }
    // Only the short entry is a prefix here: the second apostrophe starts the suffix.
    expect(normalizeTrWith("a'bx'd", 'dar', list)).toBe('abx');
    // Without any list the first apostrophe already starts the suffix.
    expect(normalizeTrWith("a'bc'd", 'dar', [])).toBe('a');
  });

  test('prefix match has no word boundary', () => {
    expect(normalizeTrWith("kur'anlar", 'dar', ["kur'an"])).toBe('kuranlar');
  });
});

describe('lone surrogates', () => {
  test.each([
    ['lone high surrogate', 'a\ud800b', 'a b'],
    ['lone low surrogate', 'a\udc00b', 'a b'],
    ['reversed pair', 'a\udc00\ud800b', 'a b'],
    ['high surrogate at the end', 'ab\ud800', 'ab'],
    ['valid pair is kept', '\ud801\udc00', '\ud801\udc28'],
  ])('%s', (_name, input, expected) => {
    expect(normalizeTr(input, 'dar')).toBe(expected);
    expect(normalizeTr(input, 'genis')).toBe(expected);
  });

  test('splitScripts replaces a lone surrogate with one space', () => {
    expect(splitScripts('a\ud800b')).toStrictEqual({ tr: 'a b', ar: '   ' });
    expect(splitScripts('a\udc00b').tr).toBe('a b');
    expect(splitScripts('\ud83d\ude00').tr).toBe('\ud83d\ude00');
  });

  test('Arabic key treats a lone surrogate as a separator', () => {
    expect(normalizeAr('\u0628\ud800\u0628')).toBe('\u0628 \u0628');
  });
});

describe('splitScripts', () => {
  test('each code point goes to exactly one part, the other gets one space', () => {
    expect(splitScripts('ab\u0628c')).toStrictEqual({ tr: 'ab c', ar: '  \u0628 ' });
  });

  test('a code point outside the BMP takes one position, not two', () => {
    expect(splitScripts('\ud83d\ude00\u0628')).toStrictEqual({
      tr: '\ud83d\ude00 ',
      ar: ' \u0628',
    });
  });

  test('U+200B becomes a space, other format characters vanish', () => {
    expect(splitScripts('a\u200bb\u00adc').tr).toBe('a bc');
  });

  test('NFC is applied after format characters are removed', () => {
    expect(splitScripts('e\u200e\u0301').tr).toBe('\u00e9');
  });
});

describe('edge cases', () => {
  test('dotted and dotless I are mapped first, whatever the locale', () => {
    expect(normalizeTr('\u0130I\u0131i', 'dar')).toBe('i\u0131\u0131i');
    expect(normalizeTr('\u0130I\u0131i', 'genis')).toBe('iiii');
  });

  test('input that is not in NFC is composed before lower casing', () => {
    expect(normalizeTr('I\u0307', 'dar')).toBe('i');
    expect(normalizeTr('a\u0302lem', 'dar')).toBe('\u00e2lem');
  });

  test('empty and blank input give empty keys', () => {
    expect(searchKeys('')).toStrictEqual({ trNarrow: '', trWide: '', arNorm: '' });
    expect(searchKeys(' \t\n ')).toStrictEqual({ trNarrow: '', trWide: '', arNorm: '' });
  });

  test('mixed text yields independent Turkish and Arabic keys', () => {
    const keys = searchKeys('Deneme \u0628\u064e\u0628 Metin');
    expect(keys.trNarrow).toBe('deneme metin');
    expect(keys.arNorm).toBe('\u0628\u0628');
  });

  test('calls do not change the input and return fresh objects', () => {
    const input = 'Kur\u2019an\u2019\u0131n \u0628\u064e';
    const copy = `${input}`;
    const list = [...IC_KESME];
    const first = searchKeys(input);
    const second = searchKeys(input);
    expect(input).toBe(copy);
    expect(first).toStrictEqual(second);
    expect(first).not.toBe(second);
    expect([...IC_KESME]).toStrictEqual(list);
  });

  test('an unknown Turkish key throws instead of acting like the wide key', () => {
    for (const bad of ['', 'DAR', 'narrow', 'wide', undefined, null, 1]) {
      expect(() => normalizeTr('Deneme', bad as never)).toThrow(RangeError);
      expect(() => normalizeTrWith('Deneme', bad as never, [])).toThrow(RangeError);
    }
  });

  test('searchKeys agrees with the single-key functions', () => {
    for (const input of ["Kur'an\u2019\u0131n \u0628\u064e \u0130MAN", 'a\ud800b', '']) {
      expect(searchKeys(input)).toStrictEqual({
        trNarrow: normalizeTr(input, 'dar'),
        trWide: normalizeTr(input, 'genis'),
        arNorm: normalizeAr(input),
      });
    }
  });

  test('the generated list is frozen', () => {
    expect(Object.isFrozen(IC_KESME)).toBe(true);
  });
});

describe('NORMALIZER_VERSION', () => {
  test('is 1.0', () => {
    expect(NORMALIZER_VERSION).toBe('1.0');
  });
});
