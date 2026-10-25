import { describe, expect, test } from 'vitest';
import {
  AnchorError,
  compare,
  contains,
  coveredAyahs,
  cpToUtf16,
  format,
  fromRoute,
  parse,
  snapSpan,
  toRoute,
  toUnitSpan,
  unitOf,
  utf16ToCp,
} from '../src/index.js';
import type { Anchor } from '../src/index.js';
import { readVectors } from './vectors.js';

interface ValidExpected {
  ref: { anchor: Anchor; span?: { start: number; end: number } };
  canonical: string;
  unit: string;
  unit_span: { unit: string; span?: [number, number] } | null;
  ayahs: Array<{ sure: number; ayet: number }>;
}

describe('anchors/valid.jsonl', () => {
  const rows = readVectors<string, ValidExpected>('anchors/valid.jsonl');
  test.each(rows)('$id', ({ input, expected }) => {
    const ref = parse(input);
    expect(ref).toStrictEqual(expected.ref);
    expect(format(ref)).toBe(expected.canonical);
    expect(format(unitOf(ref))).toBe(expected.unit);
    if (expected.unit_span === null) {
      expect(() => toUnitSpan(ref)).toThrow();
    } else {
      expect(toUnitSpan(ref)).toStrictEqual(expected.unit_span);
    }
    expect(coveredAyahs(ref)).toStrictEqual(expected.ayahs);
    // round trip
    expect(parse(format(ref))).toStrictEqual(ref);
  });
});

describe('anchors/invalid.jsonl', () => {
  const rows = readVectors<string, string>('anchors/invalid.jsonl');
  test.each(rows)('$id', ({ input, expected }) => {
    let error: unknown;
    try {
      parse(input);
    } catch (e) {
      error = e;
    }
    expect(error).toBeInstanceOf(AnchorError);
    expect((error as AnchorError).code).toBe(expected);
  });
});

describe('anchors/compare.jsonl', () => {
  const rows = readVectors<[string, string], -1 | 0 | 1>('anchors/compare.jsonl');
  test.each(rows)('$id', ({ input, expected }) => {
    const a = parse(input[0]);
    const b = parse(input[1]);
    expect(compare(a, b)).toBe(expected);
    expect(compare(b, a) + expected).toBe(0); // compare(b, a) === -expected, without -0
    expect(compare(a, a)).toBe(0);
    expect(compare(b, b)).toBe(0);
  });
});

describe('anchors/contains.jsonl', () => {
  const rows = readVectors<[string, string], boolean>('anchors/contains.jsonl');
  test.each(rows)('$id', ({ input, expected }) => {
    const dis = parse(input[0]);
    const ic = parse(input[1]);
    expect(contains(dis, ic)).toBe(expected);
    expect(contains(dis, dis)).toBe(true);
    expect(contains(ic, ic)).toBe(true);
  });
});

interface RouteInput {
  capa: string;
  sema?: string;
}

describe('anchors/route.jsonl', () => {
  const rows = readVectors<RouteInput, { native: string; web: string | null }>(
    'anchors/route.jsonl',
  );
  test.each(rows)('$id', ({ input, expected }) => {
    const ref = parse(input.capa);
    expect(toRoute(ref, 'native', input.sema)).toBe(expected.native);
    if (expected.web === null) {
      expect(() => toRoute(ref, 'web', input.sema)).toThrow();
    } else {
      expect(toRoute(ref, 'web', input.sema)).toBe(expected.web);
    }
    // native round trip, in all three schemes
    for (const sema of ['mutalaa', 'mutalaa-internal', 'mutalaa-dev']) {
      expect(fromRoute(toRoute(ref, 'native', sema))).toStrictEqual(ref);
    }
  });
});

interface OffsetsExpected {
  codepoints: number;
  utf16: number;
  cp_to_utf16: Array<[number, number]>;
  snap?: Array<{ in: [number, number]; out: [number, number] }>;
}

describe('offsets/offsets.jsonl', () => {
  const rows = readVectors<string, OffsetsExpected>('offsets/offsets.jsonl');
  test.each(rows)('$id', ({ input, expected }) => {
    expect(Array.from(input).length).toBe(expected.codepoints);
    expect(input.length).toBe(expected.utf16);
    for (const [cp, utf16] of expected.cp_to_utf16) {
      expect(cpToUtf16(input, cp)).toBe(utf16);
      expect(utf16ToCp(input, utf16)).toBe(cp);
    }
    for (const { in: inSpan, out } of expected.snap ?? []) {
      expect(snapSpan(input, { start: inSpan[0], end: inSpan[1] })).toStrictEqual({
        start: out[0],
        end: out[1],
      });
    }
  });
});
