import { describe, expect, it } from 'vitest';
import {
  AnchorError,
  cpToUtf16,
  fromRoute,
  parse,
  snapSpan,
  toRoute,
  toUnitSpan,
  tryParse,
  unitOf,
  coveredAyahs,
  utf16ToCp,
} from '../src/index.js';

function codeOf(input: string): string | undefined {
  try {
    parse(input);
    return undefined;
  } catch (error) {
    return error instanceof AnchorError ? error.code : 'OTHER';
  }
}

describe('error priority (K-35 item 1)', () => {
  it('checks the alphabet before the length', () => {
    expect(codeOf(`Q:${'a'.repeat(300)}`)).toBe('BICIM');
    expect(codeOf(`konu:${'a'.repeat(300)}`)).toBe('UZUNLUK');
  });

  it('checks the pattern before slug, depth and number limits', () => {
    expect(codeOf(`konu:${'a'.repeat(65)}`)).toBe('UZUNLUK');
    expect(codeOf(`konu:${'a'.repeat(65)}@0-5`)).toBe('BICIM');
    expect(codeOf('h:deneme:2147483648')).toBe('UZUNLUK');
    expect(codeOf('h:deneme:99999999999999999999')).toBe('UZUNLUK');
    expect(codeOf('q:1000:1')).toBe('BICIM');
  });

  it('checks limits before the semantic rules', () => {
    expect(codeOf('meal:elmalili:2:255@5-99999999999')).toBe('UZUNLUK');
    expect(codeOf('meal:elmalili:2:255@99999999999-5')).toBe('UZUNLUK');
  });

  it('runs semantic rules in order', () => {
    expect(codeOf('q:115:300-300')).toBe('SURE_ARALIGI');
    expect(codeOf('q:2:287-287')).toBe('AYET_ARALIGI');
    expect(codeOf('q:2:286-285')).toBe('TERS_ARALIK');
    expect(codeOf('q:2:3-3')).toBe('KANONIK_DEGIL');
  });

  it('rejects a trailing line feed and other non-alphabet characters', () => {
    expect(codeOf('q:1:1\n')).toBe('BICIM');
    expect(codeOf('q:1:1\r')).toBe('BICIM');
    expect(codeOf('q:\uFF11:1')).toBe('BICIM'); // full width digit
    expect(codeOf(`q:${String.fromCodePoint(0x0661)}:1`)).toBe('BICIM'); // Arabic-Indic digit
    expect(codeOf('')).toBe('BICIM');
  });

  it('is not tricked by inherited property names', () => {
    expect(codeOf('constructor:1')).toBe('BICIM');
    expect(codeOf('__proto__:1')).toBe('BICIM');
  });

  it('tryParse returns null instead of throwing', () => {
    expect(tryParse('q:2:287')).toBeNull();
    expect(tryParse('q:2:255')).not.toBeNull();
  });
});

describe('routes', () => {
  it('rejects an unknown scheme for toRoute', () => {
    expect(() => toRoute(parse('q:2:255'), 'native', 'http')).toThrow(RangeError);
  });

  it('fromRoute returns null for other schemes and bad routes', () => {
    expect(fromRoute('https://example.org/q/2/255')).toBeNull();
    expect(fromRoute('mutalaa-x://q/2/255')).toBeNull();
    expect(fromRoute('/kuran/2/255')).toBeNull();
    expect(fromRoute('mutalaa://q/2/255/')).toBeNull();
    expect(fromRoute('mutalaa://q:2:255')).toBeNull();
    expect(fromRoute('mutalaa://q/2/255?aralik=')).toBeNull();
    expect(fromRoute('mutalaa://q/2/255?x=1')).toBeNull();
    expect(fromRoute('mutalaa://q/2/255#p1')).toBeNull();
    expect(fromRoute('mutalaa://q/2/287')).toBeNull();
  });

  it('fromRoute decodes the range query', () => {
    expect(fromRoute('mutalaa-dev://meal/elmalili/2/255?aralik=10-48')).toStrictEqual({
      anchor: { t: 'meal', meal: 'elmalili', sure: 2, ayet: 255 },
      span: { start: 10, end: 48 },
    });
  });
});

describe('offset errors (K-35 item 8)', () => {
  const pair = `a${String.fromCodePoint(0x1d400)}b`; // 3 code points, 4 UTF-16 units

  it('cpToUtf16 rejects positions outside [0, code point count]', () => {
    expect(cpToUtf16(pair, 3)).toBe(4);
    expect(() => cpToUtf16(pair, 4)).toThrow(RangeError);
    expect(() => cpToUtf16(pair, -1)).toThrow(RangeError);
    expect(() => cpToUtf16(pair, 1.5)).toThrow(RangeError);
  });

  it('utf16ToCp rejects out of range and the middle of a surrogate pair', () => {
    expect(utf16ToCp(pair, 4)).toBe(3);
    expect(() => utf16ToCp(pair, 2)).toThrow(RangeError);
    expect(() => utf16ToCp(pair, 5)).toThrow(RangeError);
    expect(() => utf16ToCp(pair, -1)).toThrow(RangeError);
  });

  it('snapSpan rejects spans outside 0 <= start <= end <= length', () => {
    expect(() => snapSpan('abc', { start: 2, end: 1 })).toThrow(RangeError);
    expect(() => snapSpan('abc', { start: -1, end: 1 })).toThrow(RangeError);
    expect(() => snapSpan('abc', { start: 0, end: 4 })).toThrow(RangeError);
    expect(snapSpan('abc', { start: 0, end: 3 })).toStrictEqual({ start: 0, end: 3 });
  });
});

describe('results do not share objects with the input', () => {
  const inputs = [
    'q:2:255',
    'q:2:255:3-7',
    'q:2:255-257',
    'konu:tevhid',
    'meal:elmalili:2:255@10-48',
    'tf:elmalili:2-255-257:p3',
    'tf:elmalili:mukaddime:p4',
    'rn:sozler:soz-10:hakikat-3:p4:s2',
    'rn:sozler:soz-10:hakikat-3:p4@120-184',
    'h:buhari:52',
    'ht:naim:tecrid:15',
    'k:kisas-i-enbiya:hz-ibrahim:p2',
  ];

  it.each(inputs)('unitOf, coveredAyahs, toUnitSpan and parse results are independent: %s', (s) => {
    const ref = parse(s);
    const snapshot = structuredClone(ref);

    const unit = unitOf(ref);
    expect(unit.anchor).not.toBe(ref.anchor);
    // mutate every reachable object of the result, then check the input is untouched
    const loose = unit.anchor as unknown as Record<string, unknown>;
    if (Array.isArray(loose['yol'])) (loose['yol'] as string[]).push('x');
    loose['p'] = 999;
    loose['sure'] = 999;

    for (const item of coveredAyahs(ref)) item.ayet = 999;
    const storage = toUnitSpanOrNull(ref);
    if (storage?.span) storage.span[0] = 999;

    expect(ref).toStrictEqual(snapshot);

    // two parses of the same string are independent as well
    const first = parse(s);
    const second = parse(s);
    expect(first.anchor).not.toBe(second.anchor);
    const yol = (first.anchor as { yol?: string[] }).yol;
    if (yol) {
      expect(yol).not.toBe((second.anchor as { yol?: string[] }).yol);
      yol.push('x');
      expect(parse(s)).toStrictEqual(snapshot);
    }
  });
});

function toUnitSpanOrNull(ref: ReturnType<typeof parse>): ReturnType<typeof toUnitSpan> | null {
  try {
    return toUnitSpan(ref);
  } catch {
    return null;
  }
}
