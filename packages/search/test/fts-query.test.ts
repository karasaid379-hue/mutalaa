import { describe, expect, test } from 'vitest';
import { MAX_QUERY_CODE_POINTS, buildFtsQuery, stemTr } from '../src/index.js';
import type { BuildFtsQueryOptions, FtsQuery } from '../src/index.js';
import { readVectors } from './vectors.js';

interface QueryInput {
  query: string;
  stems?: Record<string, string>;
  sures?: Record<string, number>;
  implicitPrefix?: boolean;
  exact?: boolean;
}

/** Options from the fixed lookups of a vector (Map: no prototype keys such as "constructor"). */
function optionsOf(input: QueryInput): BuildFtsQueryOptions {
  const stems = new Map(Object.entries(input.stems ?? {}));
  const sures = new Map(Object.entries(input.sures ?? {}));
  const options: BuildFtsQueryOptions = {
    stem: (narrow) => stems.get(narrow),
    resolveSure: (key) => sures.get(key),
  };
  if (input.implicitPrefix !== undefined) options.implicitPrefix = input.implicitPrefix;
  if (input.exact !== undefined) options.exact = input.exact;
  return options;
}

/**
 * True when an FTS5 expression built by the query builder is well formed: every user word sits in
 * a double-quoted string (inner quotes doubled, string closed) and the only text outside the
 * strings is column filters, AND, OR, parentheses, `:` and the prefix star.
 */
function isSafeExpression(expression: string): boolean {
  let outside = '';
  let i = 0;
  while (i < expression.length) {
    const ch = expression[i] as string;
    if (ch !== '"') {
      outside += ch;
      i += 1;
      continue;
    }
    i += 1;
    for (;;) {
      if (i >= expression.length) return false; // unterminated string
      if (expression[i] === '"') {
        if (expression[i + 1] === '"') {
          i += 2;
          continue;
        }
        break;
      }
      i += 1;
    }
    i += 1;
    outside += '"';
  }
  const rest = outside
    .replace(/"\*?/gu, '')
    .replace(/\b(?:tr_wide|tr_stem|ar_norm)\b/gu, '')
    .replace(/\b(?:AND|OR)\b/gu, '')
    .replace(/[():\s]/gu, '');
  return rest === '';
}

describe('fts-query/query.jsonl', () => {
  const rows = readVectors<QueryInput, FtsQuery>('fts-query/query.jsonl');

  test('has rows with fq- ids (Arabic rows fq-ar- come from the pipeline generator)', () => {
    expect(rows.length).toBeGreaterThanOrEqual(40);
    for (const row of rows) expect(row.id).toMatch(/^fq-(?:ar-)?[0-9]{4}$/u);
    for (const row of rows.filter((r) => r.id.startsWith('fq-ar-'))) {
      expect(row.id).toMatch(/^fq-ar-000[12]$/u);
    }
  });

  for (const row of rows) {
    test(`${row.id} ${row.note ?? ''}`.slice(0, 120), () => {
      expect(buildFtsQuery(row.input.query, optionsOf(row.input))).toEqual(row.expected);
    });

    test(`${row.id} produces well-formed expressions`, () => {
      const result = buildFtsQuery(row.input.query, optionsOf(row.input));
      if (result.match !== null) expect(isSafeExpression(result.match)).toBe(true);
      if (result.tri !== null) expect(isSafeExpression(result.tri)).toBe(true);
    });
  }
});

describe('buildFtsQuery: escape (rule 9)', () => {
  const hostile = [
    'a" OR "b',
    '"',
    '""',
    '"""',
    'NEAR(a b, 5)',
    'NEAR/3',
    'a AND b OR c NOT d',
    'tr_wide:secret',
    'ar_norm : "x"',
    '{tr_wide tr_stem}: x',
    '^kitap',
    '-kitap +nur',
    '*',
    '**kitap**',
    'ki*tap',
    '(kitap',
    'kitap)',
    '((()))',
    "kitap' OR 1=1 --",
    'kitap";DROP TABLE unit;--',
    'kök:"x"',
    'kaynak:"meal"',
    '\\ \u0000 \u0001',
    '\ud800 lone surrogate',
    'kitap​nur­ev',
  ];
  const stem = (wide: string): string => `${wide}"G`;

  for (const query of hostile) {
    test(`stays well formed: ${JSON.stringify(query)}`, () => {
      for (const options of [{}, { stem }, { stem, implicitPrefix: true }, { exact: true }]) {
        const result = buildFtsQuery(query, options);
        if (result.match !== null) expect(isSafeExpression(result.match)).toBe(true);
        if (result.tri !== null) expect(isSafeExpression(result.tri)).toBe(true);
      }
    });
  }

  test('a quote in the injected stem is doubled', () => {
    const result = buildFtsQuery('kitap', { stem: () => 'a"b' });
    expect(result.match).toBe('tr_wide : "kitap" OR tr_stem : "a""b"');
  });

  test('random mixes of syntax characters never give a malformed expression', () => {
    const alphabet = [
      '"',
      ' ',
      '(',
      ')',
      ':',
      '*',
      '-',
      '+',
      '^',
      'NEAR',
      'AND',
      'OR',
      'NOT',
      'ab',
      'kök',
      'kaynak',
      'بتث',
      'â',
    ];
    // 32-bit LCG (Math.imul keeps the product exact); the high bits are used because the low bits
    // of a power-of-two modulus have a short period.
    let seed = 12345;
    const next = (bound: number): number => {
      seed = (Math.imul(seed, 1103515245) + 12345) >>> 0;
      return (seed >>> 16) % bound;
    };
    const usedElements = new Set<number>();
    const usedLengths = new Set<number>();
    for (let run = 0; run < 400; run += 1) {
      let query = '';
      const length = 1 + next(12);
      usedLengths.add(length);
      for (let i = 0; i < length; i += 1) {
        const index = next(alphabet.length);
        usedElements.add(index);
        query += alphabet[index] as string;
      }
      const result = buildFtsQuery(query, { stem: (w) => `${w}1`, implicitPrefix: run % 2 === 0 });
      if (result.match !== null) expect(isSafeExpression(result.match), query).toBe(true);
      if (result.tri !== null) expect(isSafeExpression(result.tri), query).toBe(true);
    }
    // The generator really reaches every alphabet element (space and a-circumflex included) and
    // every length 1..12.
    expect(usedElements.size).toBe(alphabet.length);
    expect(usedLengths.size).toBe(12);
  });
});

describe('buildFtsQuery: Arabic script (synthetic letters, no Quran text)', () => {
  // U+0628 U+062A U+062B and similar are plain letters, not words of any text.
  const word = 'بتث';
  const harakat = 'بَتُث';

  test('an Arabic term goes to ar_norm and to the trigram table (3+ characters)', () => {
    const result = buildFtsQuery(word);
    expect(result.match).toBe(`ar_norm : "${word}"`);
    expect(result.tri).toBe(`"${word}"`);
  });

  test('marks are removed by normalizeAr before the query is built', () => {
    expect(buildFtsQuery(harakat).match).toBe(`ar_norm : "${word}"`);
  });

  test('a 2-character Arabic term has no trigram part', () => {
    const two = 'بت';
    const result = buildFtsQuery(two);
    expect(result.match).toBe(`ar_norm : "${two}"`);
    expect(result.tri).toBeNull();
  });

  test('a one-character Arabic term is ignored', () => {
    const result = buildFtsQuery('ب');
    expect(result.match).toBeNull();
    expect(result.ignored).toEqual(['ب']);
  });

  test('Arabic terms get no stem branch', () => {
    const result = buildFtsQuery(`${word} kitap`, { stem: (w) => `${w}G` });
    expect(result.match).toBe(`ar_norm : "${word}" AND (tr_wide : "kitap" OR tr_stem : "kitapG")`);
    expect(result.tri).toBe(`"${word}"`);
  });

  test('two Arabic terms: trigram expression joins the long ones with AND', () => {
    const other = 'جحخد';
    const result = buildFtsQuery(`${word} بت ${other}`);
    expect(result.tri).toBe(`"${word}" AND "${other}"`);
  });

  test('an Arabic phrase is an ar_norm phrase without trigram part', () => {
    const result = buildFtsQuery(`"${word} ${word}"`);
    expect(result.match).toBe(`ar_norm : "${word} ${word}"`);
    expect(result.tri).toBeNull();
  });

  test('a prefix star on an Arabic term gives a prefix query and no trigram part', () => {
    const result = buildFtsQuery(`${word}*`);
    expect(result.match).toBe(`ar_norm : "${word}"*`);
    expect(result.tri).toBeNull();
  });

  test('kok: value goes through normalizeAr', () => {
    const result = buildFtsQuery(`kök:${harakat}`);
    expect(result.kok).toBe(word);
    expect(result.match).toBeNull();
    expect(buildFtsQuery(`kok:${word}`).kok).toBe(word);
  });

  test('mixed scripts in one token give a term per script, Turkish first', () => {
    const result = buildFtsQuery(`kitap${word}`);
    expect(result.match).toBe(`tr_wide : "kitap" AND ar_norm : "${word}"`);
  });
});

describe('buildFtsQuery: length limit (K-44 item 6)', () => {
  test('the limit is 1.024 code points', () => {
    expect(MAX_QUERY_CODE_POINTS).toBe(1024);
  });

  test('1.024 code points are processed, 1.025 give tooLong and nothing else', () => {
    const ok = buildFtsQuery('a'.repeat(1024));
    expect(ok.tooLong).toBe(false);
    expect(ok.match).not.toBeNull();
    const long = buildFtsQuery('a'.repeat(1025));
    expect(long).toEqual({
      address: null,
      match: null,
      tri: null,
      narrow: [],
      kok: null,
      kaynak: null,
      ignored: [],
      tooLong: true,
    });
  });

  test('code points are counted, not UTF-16 units', () => {
    const astral = '\u{1d400}';
    expect(buildFtsQuery(astral.repeat(1024)).tooLong).toBe(false);
    expect(buildFtsQuery(astral.repeat(1025)).tooLong).toBe(true);
  });

  test('a long input does not call the stem or the sure resolver', () => {
    const calls: string[] = [];
    buildFtsQuery('b '.repeat(600), {
      stem: (w) => {
        calls.push(w);
        return w;
      },
      resolveSure: (k) => {
        calls.push(k);
        return 1;
      },
    });
    expect(calls).toEqual([]);
  });

  test('two calls give independent results', () => {
    const a = buildFtsQuery('a'.repeat(1025));
    a.ignored.push('x');
    expect(buildFtsQuery('a'.repeat(1025)).ignored).toEqual([]);
  });
});

describe('buildFtsQuery: phrase has no stem branch (Arama 3 item 5)', () => {
  test('a quoted phrase is exactly the wide phrase, however stems are offered', () => {
    const asked: string[] = [];
    const result = buildFtsQuery('"nur ışığı"', {
      stem: (narrow) => {
        asked.push(narrow);
        return { nur: 'G3', ışığı: 'G4', 'nur ışığı': 'G5' }[narrow];
      },
    });
    expect(result.match).toBe('tr_wide : "nur isigi"');
    expect(result.match).not.toContain('tr_stem');
    expect(asked).toEqual([]);
  });

  test('the same words outside quotes do get the stem branch', () => {
    const result = buildFtsQuery('nur ışığı', {
      stem: (narrow) => ({ nur: 'G3', ışığı: 'G4' })[narrow as 'nur' | 'ışığı'],
    });
    expect(result.match).toBe(
      '(tr_wide : "nur" OR tr_stem : "G3") AND (tr_wide : "isigi" OR tr_stem : "G4")',
    );
  });
});

describe('buildFtsQuery with the real stemmer', () => {
  test('the stem branch uses stemTr output', () => {
    const result = buildFtsQuery('kitaplar', { stem: stemTr });
    expect(result.match).toBe('tr_wide : "kitaplar" OR tr_stem : "kitap"');
  });

  test('the query stems the narrow word, like the index (vowel harmony needs the dotless i)', () => {
    // Stemming the wide word "agaclari" would give another stem than the index value.
    const result = buildFtsQuery('ağaçları', { stem: stemTr });
    expect(result.match).toBe('tr_wide : "agaclari" OR tr_stem : "agac"');
    expect(stemTr('ağaçları')).toBe('agac');
    expect(stemTr('agaclari')).not.toBe('agac');
  });

  test('locale independent: dotted and dotless I', () => {
    const upper = buildFtsQuery('Iİ', { stem: stemTr });
    const lower = buildFtsQuery('ıi', { stem: stemTr });
    expect(upper).toEqual(lower);
  });
});
