// Run-time readers for the opaque JSON of the catalog screens (gate report, digests, marks, sentences).
// Nothing here trusts the shape: a reader returns null (or marks an entry invalid) instead of throwing.
import { cpToUtf16 } from '@mutalaa/anchors';
import { isRecord, readArray, readBoolean, readNumber, readString } from '@/lib/payload';

export interface GateRow {
  kind: string;
  id: string;
  decision: string;
  rule: string | null;
  reason: string;
  count: number;
}

export interface GateViolationEntry {
  rule: string | null;
  subject: string;
  reason: string;
}

export interface GateOmission {
  rule: string | null;
  reason: string;
  count: number;
}

export interface GateReportData {
  flavor: string | null;
  rejected: boolean;
  rows: GateRow[];
  violations: GateViolationEntry[];
  omitted: GateOmission[];
}

/** The report of a release that has not been through the gate yet is an empty object (`{}`). */
export function isEmptyReport(value: unknown): boolean {
  return (
    value === null || value === undefined || (isRecord(value) && Object.keys(value).length === 0)
  );
}

function readRow(value: unknown): GateRow | null {
  const kind = readString(value, 'kind');
  const id = readString(value, 'id');
  const decision = readString(value, 'decision');
  if (kind === null || id === null || decision === null) return null;
  return {
    kind,
    id,
    decision,
    rule: readString(value, 'rule'),
    reason: readString(value, 'reason') ?? '',
    count: readNumber(value, 'count') ?? 1,
  };
}

function readViolation(value: unknown): GateViolationEntry | null {
  const subject = readString(value, 'subject');
  if (subject === null) return null;
  return { rule: readString(value, 'rule'), subject, reason: readString(value, 'reason') ?? '' };
}

function readOmission(value: unknown): GateOmission | null {
  const count = readNumber(value, 'count');
  if (count === null) return null;
  return { rule: readString(value, 'rule'), reason: readString(value, 'reason') ?? '', count };
}

function readAll<T>(items: unknown[] | null, read: (value: unknown) => T | null): T[] | null {
  if (items === null) return [];
  const out: T[] = [];
  for (const item of items) {
    const entry = read(item);
    if (entry === null) return null;
    out.push(entry);
  }
  return out;
}

/**
 * Reads a gate report (`GateReport.ToJson`: flavor, rejected, rows, violations, violations_omitted).
 * Null when it is not an object with a readable `rows` array and `rejected` flag; one unreadable row makes the whole report unreadable.
 */
export function readGateReport(value: unknown): GateReportData | null {
  if (!isRecord(value)) return null;
  const rejected = readBoolean(value, 'rejected');
  const rawRows = readArray(value, 'rows');
  if (rejected === null || rawRows === null) return null;
  const rows = readAll(rawRows, readRow);
  const violations = readAll(readArray(value, 'violations'), readViolation);
  const omitted = readAll(readArray(value, 'violations_omitted'), readOmission);
  if (rows === null || violations === null || omitted === null) return null;
  return { flavor: readString(value, 'flavor'), rejected, rows, violations, omitted };
}

export interface DigestEntry {
  name: string;
  digest: string;
}

export interface DigestsData {
  sources: DigestEntry[];
  packs: DigestEntry[];
}

function readMap(value: unknown, key: string): DigestEntry[] | null {
  if (!isRecord(value)) return null;
  const map = value[key];
  if (map === undefined) return [];
  if (!isRecord(map)) return null;
  const out: DigestEntry[] = [];
  for (const [name, digest] of Object.entries(map)) {
    if (typeof digest !== 'string') return null;
    out.push({ name, digest });
  }
  return out;
}

/** Reads `release.ozetler`: `{ kaynaklar: {slug: digest}, paketler: {id: digest} }` (both optional). */
export function readDigests(value: unknown): DigestsData | null {
  const sources = readMap(value, 'kaynaklar');
  const packs = readMap(value, 'paketler');
  return sources === null || packs === null ? null : { sources, packs };
}

export interface MarkEntry {
  /** 1-based number shown in the table and used to tie a mark to its text segment. */
  index: number;
  type: string;
  start: number | null;
  end: number | null;
  anchor: string | null;
  /** False when the offsets are not integers inside the text, or the range is empty or reversed. */
  valid: boolean;
}

function isOffset(value: number | null, length: number): value is number {
  return value !== null && Number.isInteger(value) && value >= 0 && value <= length;
}

/**
 * Reads `unit.marks` (`[{s, e?, t, a?}]`, offsets in Unicode code points, `[s, e)`). Null when the value is not an array.
 * `length` is the number of code points of the text; an entry outside it is kept but flagged invalid.
 */
export function readMarks(value: unknown, length: number): MarkEntry[] | null {
  if (!Array.isArray(value)) return null;
  return value.map((item, position): MarkEntry => {
    const start = readNumber(item, 's');
    const rawEnd = isRecord(item) ? item.e : undefined;
    const hasEnd = rawEnd !== undefined && rawEnd !== null;
    const end = hasEnd ? readNumber(item, 'e') : null;
    const type = readString(item, 't');
    const valid =
      type !== null &&
      isOffset(start, length) &&
      (!hasEnd || (isOffset(end, length) && start < end));
    return {
      index: position + 1,
      type: type ?? '',
      start,
      end,
      anchor: readString(item, 'a'),
      valid,
    };
  });
}

export interface SentenceEntry {
  index: number;
  start: number;
  end: number;
  valid: boolean;
}

/** Reads `unit.sentences` (`[[start, end], ...]` in code points, `[start, end)`); entries outside the text are flagged invalid. */
export function readSentences(
  value: readonly (readonly number[])[] | null | undefined,
  length: number,
): SentenceEntry[] {
  if (!value) return [];
  return value.map((pair, position) => {
    const start = pair[0];
    const end = pair[1];
    const valid =
      pair.length === 2 &&
      start !== undefined &&
      end !== undefined &&
      Number.isInteger(start) &&
      Number.isInteger(end) &&
      start >= 0 &&
      start < end &&
      end <= length;
    return { index: position + 1, start: start ?? 0, end: end ?? 0, valid };
  });
}

/** Number of Unicode code points of a text. */
export function cpLength(text: string): number {
  let count = 0;
  for (let i = 0; i < text.length; i++) {
    if ((text.codePointAt(i) ?? 0) > 0xffff) i++;
    count++;
  }
  return count;
}

export interface TextSegment {
  text: string;
  /** Numbers of the marks that cover this segment; empty for plain text. */
  marks: number[];
}

export interface MarkedLayout {
  segments: TextSegment[];
  /** Zero-width marks (no `e`): their number and the segment index in front of which they sit. */
  points: { index: number; before: number }[];
}

/**
 * Cuts a text at the boundaries of the valid marks (code point offsets, converted to UTF-16 only here).
 * The text itself is never changed: the segments joined give back the input.
 */
export function layoutMarks(text: string, marks: readonly MarkEntry[]): MarkedLayout {
  const length = cpLength(text);
  const ranges = marks.filter(
    (mark): mark is MarkEntry & { start: number; end: number } =>
      mark.valid && mark.start !== null && mark.end !== null && mark.end <= length,
  );
  const pointMarks = marks.filter((mark) => mark.valid && mark.start !== null && mark.end === null);

  const cuts = new Set<number>([0, length]);
  for (const mark of ranges) {
    cuts.add(mark.start);
    cuts.add(mark.end);
  }
  for (const mark of pointMarks) cuts.add(mark.start ?? 0);
  const sorted = [...cuts].sort((a, b) => a - b);

  const segments: TextSegment[] = [];
  const starts: number[] = [];
  for (let i = 0; i + 1 < sorted.length; i++) {
    const from = sorted[i] ?? 0;
    const to = sorted[i + 1] ?? 0;
    if (from === to) continue;
    segments.push({
      text: text.slice(cpToUtf16(text, from), cpToUtf16(text, to)),
      marks: ranges
        .filter((mark) => mark.start <= from && to <= mark.end)
        .map((mark) => mark.index),
    });
    starts.push(from);
  }
  const points = pointMarks.map((mark) => {
    const at = mark.start ?? 0;
    const found = starts.findIndex((start) => start >= at);
    return { index: mark.index, before: found === -1 ? segments.length : found };
  });
  return { segments, points };
}

/** Indented JSON of any value for display; an empty string when it cannot be serialised. */
export function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? '';
  } catch {
    return '';
  }
}
