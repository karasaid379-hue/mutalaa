// Validation patterns (Capa semasi 3, binding by K-35 item 2). One pattern per kind.
// Rules: [0-9] never the backslash-d class; no flags (no g, y, i, m); the end anchor is the
// plain dollar sign, which in JavaScript (without the m flag) matches only at the very end of
// the input, so a trailing line feed can never slip through.

const SAYI = '[1-9][0-9]*';
const K3 = '[1-9][0-9]{0,2}'; // sure, ayet, kelime: at most three digits
const SLUG = '[a-z][a-z0-9]*(?:-[a-z0-9]+)*';
const SEG = `(?![ps][0-9]+(?::|@|$))${SLUG}`;
const ARA = '(?:@(?<bas>0|[1-9][0-9]*)-(?<bit>[1-9][0-9]*))?';

export const PATTERN_Q = new RegExp(
  `^q:(?<sure>${K3}):(?:(?<ayet>${K3})(?::(?<ilk>${K3})(?:-(?<son>${K3}))?)?|(?<ayet_ilk>${K3})-(?<ayet_son>${K3}))$`,
);
export const PATTERN_KONU = new RegExp(`^konu:(?<konu>${SLUG})$`);
export const PATTERN_MEAL = new RegExp(
  `^meal:(?<meal>${SLUG}):(?<sure>${K3}):(?<ayet>${K3})${ARA}$`,
);
export const PATTERN_TF = new RegExp(
  `^tf:(?<eser>${SLUG}):(?:(?<sure>${K3})-(?<ilk>${K3})-(?<son>${K3})|(?<bolum>${SEG})):p(?<p>${SAYI})${ARA}$`,
);
export const PATTERN_RN = new RegExp(
  `^rn:(?<yol>${SEG}(?::${SEG})*):p(?<p>${SAYI})(?::s(?<s>${SAYI})|${ARA})$`,
);
export const PATTERN_H = new RegExp(`^h:(?<koleksiyon>${SLUG}):(?<no>${SAYI})${ARA}$`);
export const PATTERN_HT = new RegExp(
  `^ht:(?<ceviri>${SLUG}):(?<koleksiyon>${SLUG}):(?<no>${SAYI})${ARA}$`,
);
export const PATTERN_K = new RegExp(`^k:(?<yol>${SEG}(?::${SEG})*):p(?<p>${SAYI})${ARA}$`);

/** Pattern by prefix. A Map, so inherited names such as "constructor" never match. */
export const PATTERNS_BY_PREFIX: ReadonlyMap<string, RegExp> = new Map([
  ['q', PATTERN_Q],
  ['konu', PATTERN_KONU],
  ['meal', PATTERN_MEAL],
  ['tf', PATTERN_TF],
  ['rn', PATTERN_RN],
  ['h', PATTERN_H],
  ['ht', PATTERN_HT],
  ['k', PATTERN_K],
]);

/** Any character outside the anchor alphabet (K-35 item 1). */
export const OUTSIDE_ALPHABET = /[^a-z0-9:@-]/;

export const MAX_TOTAL_LENGTH = 256;
export const MAX_SLUG_LENGTH = 64;
export const MAX_DEPTH = 8;
export const MAX_NUMBER = 2147483647;
export const MAX_NUMBER_DIGITS = String(MAX_NUMBER);
