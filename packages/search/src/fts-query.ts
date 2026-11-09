// FTS5 query builder (Arama 3). Pure string work: no SQLite, no other workspace package. Sure
// names and stems are injected (resolveSure, stem), so the result is deterministic and the
// shared vectors (fts-query/query.jsonl) can fix it. All normalization goes through this
// package's own normalizeTr / normalizeAr functions.
//
// Rule 9 (escape): every word that reaches an FTS5 expression is written as a double-quoted
// FTS5 string with inner quotes doubled; no user text is ever written bare.
import { isArabicBlock, normalizeAr, normalizeTr } from './normalize.js';

/** Longest accepted input, in code points (K-44 item 6). */
export const MAX_QUERY_CODE_POINTS = 1024;

/** One code point is at most two UTF-16 units: a cheap check before counting code points. */
const MAX_QUERY_UNITS = MAX_QUERY_CODE_POINTS * 2;

/** Source groups of the `kaynak:` filter (Arama 3 item 8). */
export type FtsSource = 'kuran' | 'meal' | 'tefsir' | 'hadis' | 'risale';

const SOURCES: ReadonlySet<string> = new Set(['kuran', 'meal', 'tefsir', 'hadis', 'risale']);

/** Address found in the query; the range check against the sure table is the caller's job. */
export interface FtsAddress {
  sure: number;
  ayet: number;
}

export interface FtsQuery {
  /** "2:255" or "<sure name> 255" (null when the query is not an address). */
  address: FtsAddress | null;
  /** `unit_fts` MATCH expression (null when nothing is left to search). */
  match: string | null;
  /** `unit_tri` MATCH expression: Arabic terms of at least 3 characters. */
  tri: string | null;
  /** Narrow keys for the narrow filter (terms with a circumflex; every term with `exact`). */
  narrow: string[];
  /** Value of `kök:` (normalizeAr applied). */
  kok: string | null;
  /** Value of `kaynak:` when it names one of the five groups. */
  kaynak: FtsSource | null;
  /** Terms and filters that were dropped (one-character terms, invalid filters). */
  ignored: string[];
  /** The input exceeded 1.024 code points; nothing else is produced. */
  tooLong: boolean;
}

export interface BuildFtsQueryOptions {
  /** Wide key of a sure name -> sure number (from the `sure` table of the core pack). */
  resolveSure?: (nameKey: string) => number | undefined;
  /**
   * Narrow word -> stem (`stemTr`); undefined or '' adds no `tr_stem` branch. The index stems
   * the narrow word (vowel harmony needs the dotless i), so the query must do the same.
   */
  stem?: (narrowWord: string) => string | undefined;
  /** The last term is a prefix even without `*` (search while typing). */
  implicitPrefix?: boolean;
  /** "Tam yazimla ara": the narrow filter covers every Turkish term. */
  exact?: boolean;
}

interface Term {
  expr: string;
  /** The expression contains OR and needs parentheses next to other terms. */
  hasOr: boolean;
}

interface Word {
  script: 'tr' | 'ar';
  /** Search word: wide key for Turkish, ar_norm word for Arabic. */
  key: string;
  /** Narrow word (Turkish only). */
  narrow: string;
  prefix: boolean;
}

interface Piece {
  kind: 'bare' | 'phrase';
  text: string;
}

type Item = { word: Word } | { terms: Term[] };

const CIRCUMFLEX = /[âîû]/u;
const WHITESPACE = /^\s$/u;
const ADDRESS_NUMBERS = /^([0-9]{1,3}):([0-9]{1,3})$/u;
const NAME_AND_AYET = /^(.+?)[\s:]+([0-9]{1,3})$/u;

/** FTS5 string: double quotes around it, inner double quotes doubled (rule 9). */
function quote(text: string): string {
  return `"${text.replaceAll('"', '""')}"`;
}

/** Length in code points. */
function size(text: string): number {
  return Array.from(text).length;
}

function wordsOf(key: string): string[] {
  return key === '' ? [] : key.split(' ');
}

/** Splits the input into bare tokens and double-quoted phrases (an open quote runs to the end). */
function scan(input: string): Piece[] {
  const chars = [...input];
  const pieces: Piece[] = [];
  let i = 0;
  while (i < chars.length) {
    const ch = chars[i] as string;
    if (WHITESPACE.test(ch)) {
      i += 1;
    } else if (ch === '"') {
      let j = i + 1;
      while (j < chars.length && chars[j] !== '"') j += 1;
      pieces.push({ kind: 'phrase', text: chars.slice(i + 1, j).join('') });
      i = j + 1;
    } else {
      let j = i;
      while (j < chars.length && chars[j] !== '"' && !WHITESPACE.test(chars[j] as string)) j += 1;
      pieces.push({ kind: 'bare', text: chars.slice(i, j).join('') });
      i = j;
    }
  }
  return pieces;
}

/** Positive integer from up to three digits, or undefined. */
function positiveInt(digits: string): number | undefined {
  const value = Number.parseInt(digits, 10);
  return value >= 1 ? value : undefined;
}

/** Rule 1: "2:255" or "<sure name> 255" / "<sure name>:255"; the range check is the caller's. */
function detectAddress(
  text: string,
  resolveSure: BuildFtsQueryOptions['resolveSure'],
): FtsAddress | null {
  const numbers = ADDRESS_NUMBERS.exec(text);
  if (numbers !== null) {
    const sure = positiveInt(numbers[1] as string);
    const ayet = positiveInt(numbers[2] as string);
    return sure !== undefined && ayet !== undefined ? { sure, ayet } : null;
  }
  const named = NAME_AND_AYET.exec(text);
  if (named === null || resolveSure === undefined) return null;
  const nameKey = normalizeTr(named[1] as string, 'genis');
  const ayet = positiveInt(named[2] as string);
  if (nameKey === '' || ayet === undefined) return null;
  const sure = resolveSure(nameKey);
  return sure !== undefined && Number.isSafeInteger(sure) && sure >= 1 ? { sure, ayet } : null;
}

/** Filter name of a token prefix (`kök:` is also accepted as `kok:`), or null. */
function filterName(prefix: string): 'kok' | 'kaynak' | null {
  const key = normalizeTr(prefix, 'genis');
  return key === 'kok' || key === 'kaynak' ? key : null;
}

/** Words of one bare token; a trailing `*` makes its last word a prefix (rule 4). */
function tokenWords(token: string): Word[] {
  let body = token;
  let star = false;
  while (body.endsWith('*')) {
    body = body.slice(0, -1);
    star = true;
  }
  const tr = wordsOf(normalizeTr(body, 'genis'));
  const narrow = wordsOf(normalizeTr(body, 'dar'));
  const ar = wordsOf(normalizeAr(body));
  const out: Word[] = [
    ...tr.map((key, index): Word => ({
      script: 'tr',
      key,
      narrow: narrow[index] ?? key,
      prefix: false,
    })),
    ...ar.map((key): Word => ({ script: 'ar', key, narrow: '', prefix: false })),
  ];
  if (star) {
    const last = [...body].at(-1);
    const script = last !== undefined && isArabicBlock(last.codePointAt(0) as number) ? 'ar' : 'tr';
    const target = [...out].reverse().find((w) => w.script === script) ?? out.at(-1);
    if (target !== undefined) target.prefix = true;
  }
  return out;
}

/** Term for one word (rules 2-4, 6); null when the word is dropped. */
function wordTerm(word: Word, stem: BuildFtsQueryOptions['stem'], ignored: string[]): Term | null {
  if (size(word.key) < 2) {
    ignored.push(word.script === 'tr' ? word.narrow : word.key);
    return null;
  }
  const column = word.script === 'tr' ? 'tr_wide' : 'ar_norm';
  const base = `${column} : ${quote(word.key)}`;
  if (word.prefix) return { expr: `${base}*`, hasOr: false };
  const stemmed = word.script === 'tr' ? stem?.(word.narrow) : undefined;
  if (stemmed === undefined || stemmed === '') return { expr: base, hasOr: false };
  return { expr: `${base} OR tr_stem : ${quote(stemmed)}`, hasOr: true };
}

/** Terms of a double-quoted phrase (rule 5): one phrase per script, no stem, no prefix. */
function phraseTerms(text: string, exact: boolean, narrow: string[], ignored: string[]): Term[] {
  const terms: Term[] = [];
  const trWide = normalizeTr(text, 'genis');
  const trNarrow = normalizeTr(text, 'dar');
  const parts: ReadonlyArray<readonly [string, string, string]> = [
    ['tr_wide', trWide, trNarrow],
    ['ar_norm', normalizeAr(text), ''],
  ];
  for (const [column, key, narrowKey] of parts) {
    if (key === '') continue;
    if (size(key) < 2) {
      ignored.push(column === 'tr_wide' ? narrowKey : key);
      continue;
    }
    terms.push({ expr: `${column} : ${quote(key)}`, hasOr: false });
    if (column === 'tr_wide' && (exact || CIRCUMFLEX.test(narrowKey))) narrow.push(narrowKey);
  }
  return terms;
}

function emptyResult(tooLong: boolean): FtsQuery {
  return {
    address: null,
    match: null,
    tri: null,
    narrow: [],
    kok: null,
    kaynak: null,
    ignored: [],
    tooLong,
  };
}

/** Builds the FTS5 expressions of one user query (Arama 3, rules 1-9). */
export function buildFtsQuery(input: string, options: BuildFtsQueryOptions = {}): FtsQuery {
  if (input.length > MAX_QUERY_UNITS || size(input) > MAX_QUERY_CODE_POINTS) {
    return emptyResult(true);
  }

  const exact = options.exact === true;
  const result = emptyResult(false);
  const narrow: string[] = [];

  // Filters (rules 7-8); everything else is kept in input order.
  const rest: Piece[] = [];
  for (const piece of scan(input)) {
    const colon = piece.kind === 'bare' ? piece.text.indexOf(':') : -1;
    const name = colon > 0 ? filterName(piece.text.slice(0, colon)) : null;
    if (name === null) {
      rest.push(piece);
      continue;
    }
    const value = piece.text.slice(colon + 1);
    if (name === 'kok') {
      const key = normalizeAr(value);
      if (key === '') result.ignored.push(piece.text);
      else result.kok = key;
    } else {
      const key = normalizeTr(value, 'genis');
      if (SOURCES.has(key)) result.kaynak = key as FtsSource;
      else result.ignored.push(piece.text);
    }
  }

  // Rule 1: address (bare tokens only; a quoted phrase makes it an ordinary query).
  if (rest.every((p) => p.kind === 'bare') && rest.length > 0) {
    result.address = detectAddress(rest.map((p) => p.text).join(' '), options.resolveSure);
  }

  // Words and phrases in input order.
  const items: Item[] = [];
  for (const piece of rest) {
    if (piece.kind === 'phrase') {
      items.push({ terms: phraseTerms(piece.text, exact, narrow, result.ignored) });
    } else {
      for (const word of tokenWords(piece.text)) items.push({ word });
    }
  }
  const last = items.at(-1);
  if (options.implicitPrefix === true && last !== undefined && 'word' in last) {
    last.word.prefix = true;
  }

  const terms: Term[] = [];
  const triParts: string[] = [];
  for (const item of items) {
    if ('terms' in item) {
      terms.push(...item.terms);
      continue;
    }
    const { word } = item;
    const term = wordTerm(word, options.stem, result.ignored);
    if (term === null) continue;
    terms.push(term);
    if (word.script === 'tr' && (exact || CIRCUMFLEX.test(word.narrow))) narrow.push(word.narrow);
    if (word.script === 'ar' && !word.prefix && size(word.key) >= 3) triParts.push(quote(word.key));
  }

  const parenthesize = terms.length > 1;
  result.match =
    terms.length === 0
      ? null
      : terms.map((t) => (t.hasOr && parenthesize ? `(${t.expr})` : t.expr)).join(' AND ');
  result.tri = triParts.length === 0 ? null : triParts.join(' AND ');
  result.narrow = [...new Set(narrow)];
  return result;
}
