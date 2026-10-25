// Search normalization (K-36, normalizer_version 1.0). The same algorithm is implemented in
// C# (Mutalaa.Domain/Text/SearchNormalizer.cs) and Python (mutalaa_pipeline.normalize); the three
// are locked together by shared/test-vectors/normalize/{tr,ar}.jsonl.
//
// Rules that keep the result independent of the device locale and the JS engine defaults:
// - iteration is by code point (for...of), never by UTF-16 code unit;
// - lower casing is done per code point with an explicit I/dotted I mapping, never on the whole
//   string (final sigma context) and never with a locale-aware call;
// - character classes come from Unicode property escapes, never from \w or similar.
import { IC_KESME } from './generated/ic-kesme.js';

/** Version stored next to every search column; bumped when this algorithm or its lists change. */
export const NORMALIZER_VERSION = '1.0' as const;

/** Narrow key keeps diacritics; wide key folds them (and dotless i) away. */
export type TrKey = 'dar' | 'genis';

export interface SearchKeys {
  trNarrow: string;
  trWide: string;
  arNorm: string;
}

const SPACE = ' ';
const APOSTROPHE = "'";

/** Apostrophe look-alikes folded into U+0027 before words are split (K-36 item 2). */
const APOSTROPHE_VARIANTS: ReadonlySet<number> = new Set([
  0x2019, 0x2018, 0x02bc, 0x02be, 0x02bf, 0x00b4, 0x0060,
]);

/** Arabic script blocks (K-36 item 1d): inclusive code point ranges. */
const ARABIC_BLOCKS: ReadonlyArray<readonly [number, number]> = [
  [0x0600, 0x06ff],
  [0x0750, 0x077f],
  [0x08a0, 0x08ff],
  [0xfb50, 0xfdff],
  [0xfe70, 0xfeff],
];

/** Word characters: Lu Ll Lt Lm Lo Mn Mc Me Nd Nl No (a single code point). */
const WORD_CHAR = /^[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Mn}\p{Mc}\p{Me}\p{Nd}\p{Nl}\p{No}]$/u;
/** At least one letter or number: Lu Ll Lt Lm Lo Nd Nl No. */
const HAS_LETTER_OR_NUMBER = /[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Nd}\p{Nl}\p{No}]/u;
const FORMAT_CHAR = /^\p{Cf}$/u;
/** Combining marks removed by the wide key (U+0300-U+036F). */
const WIDE_MARKS = /[\u0300-\u036f]/gu;
const DOTLESS_I = /\u0131/g;

function isArabicBlock(cp: number): boolean {
  for (const [first, last] of ARABIC_BLOCKS) {
    if (cp >= first && cp <= last) return true;
  }
  return false;
}

/** A lone UTF-16 surrogate: for...of yields it as a one-unit string. */
function isLoneSurrogate(cp: number): boolean {
  return cp >= 0xd800 && cp <= 0xdfff;
}

/**
 * K-36 item 1 (a-d): lone surrogates become U+0020, U+200B becomes U+0020, other format
 * characters (Cf) are removed, NFC, then the text is divided by script. Each code point goes to
 * exactly one of the two parts; the other part gets one U+0020 at that position.
 */
export function splitScripts(text: string): { tr: string; ar: string } {
  const cleaned: string[] = [];
  for (const ch of text) {
    const cp = ch.codePointAt(0) as number;
    if (isLoneSurrogate(cp) || cp === 0x200b) {
      cleaned.push(SPACE);
    } else if (!FORMAT_CHAR.test(ch)) {
      cleaned.push(ch);
    }
  }
  const composed = cleaned.join('').normalize('NFC');

  const tr: string[] = [];
  const ar: string[] = [];
  for (const ch of composed) {
    if (isArabicBlock(ch.codePointAt(0) as number)) {
      ar.push(ch);
      tr.push(SPACE);
    } else {
      tr.push(ch);
      ar.push(SPACE);
    }
  }
  return { tr: tr.join(''), ar: ar.join('') };
}

/**
 * Simple lower case of one code point with the explicit Turkish mapping first:
 * I (U+0049) -> dotless i (U+0131), dotted I (U+0130) -> i. Never call this on a whole string.
 */
function lowerCodePoint(ch: string): string {
  const cp = ch.codePointAt(0) as number;
  if (cp === 0x49) return '\u0131';
  if (cp === 0x130) return 'i';
  return ch.toLowerCase();
}

/** Wide folding of one word: dotless i -> i, NFD, remove U+0300-U+036F, NFC. */
function foldWide(word: string): string {
  return word.replace(DOTLESS_I, 'i').normalize('NFD').replace(WIDE_MARKS, '').normalize('NFC');
}

/** Longest list entry that is a plain prefix of the wide form (no boundary condition). */
function longestIcKesme(wide: string, icKesme: readonly string[]): string {
  let best = '';
  for (const entry of icKesme) {
    if (entry.length > best.length && wide.startsWith(entry)) best = entry;
  }
  return best;
}

function removeFirstApostrophes(word: string, count: number): string {
  let result = word;
  let from = 0;
  for (let i = 0; i < count; i += 1) {
    const at = result.indexOf(APOSTROPHE, from);
    if (at < 0) break;
    result = result.slice(0, at) + result.slice(at + 1);
    from = at;
  }
  return result;
}

function countApostrophes(text: string): number {
  let count = 0;
  for (const ch of text) {
    if (ch === APOSTROPHE) count += 1;
  }
  return count;
}

/** K-36 item 2 and 3 for one word (apostrophes are still inside); '' means "drop the word". */
function processTurkishWord(raw: string, icKesme: readonly string[]): string {
  let word = raw;
  // Leading and trailing apostrophe runs are dropped; only the first and last code point count.
  let start = 0;
  let end = word.length;
  while (start < end && word[start] === APOSTROPHE) start += 1;
  while (end > start && word[end - 1] === APOSTROPHE) end -= 1;
  word = word.slice(start, end);
  if (word === '') return '';

  const entry = longestIcKesme(foldWide(word), icKesme);
  if (entry !== '') word = removeFirstApostrophes(word, countApostrophes(entry));

  const cut = word.indexOf(APOSTROPHE);
  if (cut >= 0) word = word.slice(0, cut);

  word = word.normalize('NFC');
  return HAS_LETTER_OR_NUMBER.test(word) ? word : '';
}

/** Turkish words (narrow form) of the Turkish part produced by {@link splitScripts}. */
function turkishWords(tr: string, icKesme: readonly string[]): string[] {
  const words: string[] = [];
  let current: string[] = [];
  const flush = (): void => {
    if (current.length === 0) return;
    const word = processTurkishWord(current.join(''), icKesme);
    if (word !== '') words.push(word);
    current = [];
  };
  for (const ch of tr) {
    const cp = ch.codePointAt(0) as number;
    const lowered = lowerCodePoint(ch);
    const mapped = APOSTROPHE_VARIANTS.has(cp) ? APOSTROPHE : lowered;
    if (mapped === APOSTROPHE || isWordText(mapped)) {
      current.push(mapped);
    } else {
      flush();
    }
  }
  flush();
  return words;
}

function assertTrKey(key: string): asserts key is TrKey {
  if (key !== 'dar' && key !== 'genis') {
    throw new RangeError(`Unknown Turkish key: ${String(key)}`);
  }
}

/**
 * Turkish key with an explicit in-word apostrophe list. The public {@link normalizeTr} passes the
 * generated list; tests pass artificial lists (for example to check the longest match).
 */
export function normalizeTrWith(text: string, key: TrKey, icKesme: readonly string[]): string {
  assertTrKey(key);
  const words = turkishWords(splitScripts(text).tr, icKesme);
  return (key === 'dar' ? words : words.map(foldWide)).join(SPACE);
}

/** True when every code point of the text is a word character (a lower-cased code point can in
 * theory expand to several). */
function isWordText(text: string): boolean {
  if (text === '') return false;
  for (const ch of text) {
    if (!WORD_CHAR.test(ch)) return false;
  }
  return true;
}

/** Turkish key (K-36 item 2-3): `dar` keeps diacritics, `genis` folds them. */
export function normalizeTr(text: string, key: TrKey): string {
  return normalizeTrWith(text, key, IC_KESME);
}

const ARABIC_FOLD: ReadonlyMap<number, string> = new Map([
  [0x0623, '\u0627'],
  [0x0625, '\u0627'],
  [0x0622, '\u0627'],
  [0x0671, '\u0627'],
  [0x0649, '\u064a'],
  [0x0629, '\u0647'],
  [0x0624, '\u0648'],
  [0x0626, '\u064a'],
]);

function isArabicDeleted(cp: number): boolean {
  return (
    (cp >= 0x064b && cp <= 0x065f) ||
    cp === 0x0670 ||
    (cp >= 0x06d6 && cp <= 0x06ed) ||
    cp === 0x0640
  );
}

/** Arabic key of the Arabic part produced by {@link splitScripts}. */
function arabicKey(ar: string): string {
  const words: string[] = [];
  let current: string[] = [];
  const flush = (): void => {
    if (current.length === 0) return;
    const word = current.join('');
    if (HAS_LETTER_OR_NUMBER.test(word)) words.push(word);
    current = [];
  };
  for (const ch of ar) {
    const cp = ch.codePointAt(0) as number;
    if (isArabicDeleted(cp)) continue;
    const mapped = ARABIC_FOLD.get(cp) ?? ch;
    if (WORD_CHAR.test(mapped)) {
      current.push(mapped);
    } else {
      flush();
    }
  }
  flush();
  return words.join(SPACE);
}

/** Arabic key (K-36 item 4): marks removed, letters merged, words split on non-word characters. */
export function normalizeAr(text: string): string {
  return arabicKey(splitScripts(text).ar);
}

/** All three search keys of a text; the shared preparation step runs once. */
export function searchKeys(text: string): SearchKeys {
  const { tr, ar } = splitScripts(text);
  const words = turkishWords(tr, IC_KESME);
  return {
    trNarrow: words.join(SPACE),
    trWide: words.map(foldWide).join(SPACE),
    arNorm: arabicKey(ar),
  };
}
