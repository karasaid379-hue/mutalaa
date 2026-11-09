import { describe, expect, test } from 'vitest';
import { normalizeTr, stemTr } from '../src/index.js';
import { readVectors } from './vectors.js';

describe('normalize/tr-govde.jsonl', () => {
  const rows = readVectors<string, string>('normalize/tr-govde.jsonl');

  test('has rows with tg- ids', () => {
    expect(rows.length).toBeGreaterThanOrEqual(40);
    for (const row of rows) expect(row.id).toMatch(/^tg-[0-9]{4}$/u);
  });

  for (const row of rows) {
    test(`${row.id} ${row.note ?? ''}`, () => {
      expect(stemTr(row.input)).toBe(row.expected);
    });

    test(`${row.id} keeps the word count of the wide key`, () => {
      const words = (text: string): number => (text === '' ? 0 : text.split(' ').length);
      expect(words(stemTr(row.input))).toBe(words(normalizeTr(row.input, 'genis')));
    });
  }
});

describe('stemTr', () => {
  test('measured reference stems (A12.0)', () => {
    expect(stemTr('kuran')).toBe('kura');
    expect(stemTr('mümin')).toBe('mum');
    expect(stemTr('iman')).toBe('ima');
    expect(stemTr('sabır')).toBe('sabir');
    expect(stemTr('kitaplar')).toBe('kitap');
  });

  test('circumflex is folded before stemming, other letters are not', () => {
    expect(stemTr('âlemler')).toBe(stemTr('alemler'));
    expect(stemTr('hâlâ')).toBe(stemTr('hala'));
  });

  test('the stem key is built from the Turkish part only', () => {
    expect(stemTr('kitaplar با evlerinde')).toBe('kitap ev');
  });

  test('empty and separator-only input give an empty key', () => {
    expect(stemTr('')).toBe('');
    expect(stemTr(" \t.,;'")).toBe('');
  });

  test('is stable on repeated calls (one shared stemmer instance)', () => {
    const first = stemTr('kitaplar evlerinde');
    expect(stemTr('kitaplar evlerinde')).toBe(first);
  });
});
