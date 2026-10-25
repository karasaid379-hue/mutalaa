// JSONL format checker for shared/test-vectors (Proje yapisi 1.2).
// Basic rules (every .jsonl file): UTF-8, no BOM, LF only, final newline, no blank lines,
// one JSON object per line, unique non-empty string "id" per file, no duplicate keys,
// no lone surrogates.
// Field rules (A04 vector specification 1-2, A05.2 for normalize/) apply to the recognized files
// only, which are named by their path relative to the package root (VECTOR_KINDS). Other files
// (fts-query/, arama/olcum.jsonl ...) get the basic rules only.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';

/** Directory names skipped when scanning the package folder by default. */
export const DEFAULT_SKIP = new Set(['node_modules', 'scripts', 'test', 'dist']);

const LF = 0x0a;
const CR = 0x0d;

/**
 * Scans the strings of one line that is already known to be valid JSON. Reports duplicate object
 * keys (at any depth; keys are compared after unescaping, so "a" and "a" are the same key)
 * and lone surrogates in any string, keys included. JSON.parse cannot report either: it keeps the
 * last duplicate silently and accepts "\ud800", but other readers (C#, strict parsers) differ.
 * @param {string} json
 * @returns {string[]} messages
 */
export function scanStrings(json) {
  /** @type {string[]} */
  const messages = [];
  /** @type {{ keys: Set<string> | null, expectKey: boolean }[]} */
  const stack = [];
  let i = 0;
  while (i < json.length) {
    const ch = json[i];
    if (ch === '"') {
      let j = i + 1;
      while (json[j] !== '"') {
        j += json[j] === '\\' ? 2 : 1;
      }
      /** @type {string} */
      const text = JSON.parse(json.slice(i, j + 1));
      const top = stack[stack.length - 1];
      const isKey = top !== undefined && top.keys !== null && top.expectKey;
      const label = JSON.stringify(text);
      if (!text.isWellFormed()) {
        messages.push(`lone surrogate in ${isKey ? 'key' : 'string'} ${label}`);
      }
      if (isKey && top !== undefined && top.keys !== null) {
        if (top.keys.has(text)) {
          messages.push(`duplicate key ${label} in object`);
        }
        top.keys.add(text);
        top.expectKey = false;
      }
      i = j + 1;
      continue;
    }
    if (ch === '{') {
      stack.push({ keys: new Set(), expectKey: true });
    } else if (ch === '[') {
      stack.push({ keys: null, expectKey: false });
    } else if (ch === '}' || ch === ']') {
      stack.pop();
    } else if (ch === ',') {
      const top = stack[stack.length - 1];
      if (top !== undefined && top.keys !== null) {
        top.expectKey = true;
      }
    }
    i += 1;
  }
  return messages;
}

const NUMBER_CHAR = /^[0-9.eE+-]$/;
const PLAIN_INTEGER = /^-?(0|[1-9][0-9]*)$/;

/**
 * Lists the number literals of one line that is already known to be valid JSON, as written in
 * the source. JSON.parse turns 1.0 and 1e0 into the integer 1, but Python reads them as float and
 * C# GetInt32 rejects them, so the recognized files must write integers plainly.
 * @param {string} json
 * @returns {string[]}
 */
export function numberLiterals(json) {
  /** @type {string[]} */
  const found = [];
  let i = 0;
  while (i < json.length) {
    const ch = json.charAt(i);
    if (ch === '"') {
      let j = i + 1;
      while (json.charAt(j) !== '"') {
        j += json.charAt(j) === '\\' ? 2 : 1;
      }
      i = j + 1;
      continue;
    }
    if (ch === '-' || (ch >= '0' && ch <= '9')) {
      let j = i + 1;
      while (j < json.length && NUMBER_CHAR.test(json.charAt(j))) {
        j += 1;
      }
      found.push(json.slice(i, j));
      i = j;
      continue;
    }
    i += 1;
  }
  return found;
}

// ---------------------------------------------------------------------------------------------
// Field rules. A rule appends messages of the form "<path>: <problem>" to `out`; the top-level
// object has the empty path, so its messages read "missing key ..." / "unknown key ...".
// ---------------------------------------------------------------------------------------------

/** @typedef {(value: unknown, path: string, out: string[]) => void} Rule */
/** @typedef {{ rule: Rule, required: boolean }} Field */

/**
 * @param {unknown} value
 * @returns {value is Record<string, unknown>}
 */
function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Short description of a value for messages (code-point safe truncation).
 * @param {unknown} value
 * @returns {string}
 */
function describe(value) {
  if (value === null) {
    return 'null';
  }
  if (Array.isArray(value)) {
    return 'an array';
  }
  if (typeof value === 'object') {
    return 'an object';
  }
  const text = JSON.stringify(value);
  const chars = [...text];
  return chars.length > 40 ? `${chars.slice(0, 37).join('')}...` : text;
}

/**
 * @param {string} path
 * @param {string} message
 * @returns {string}
 */
function at(path, message) {
  return path === '' ? message : `${path}: ${message}`;
}

/**
 * @param {string} path
 * @param {string} key
 * @returns {string}
 */
function child(path, key) {
  return path === '' ? key : `${path}.${key}`;
}

/**
 * @param {Rule} rule
 * @returns {Field}
 */
function req(rule) {
  return { rule, required: true };
}

/**
 * @param {Rule} rule
 * @returns {Field}
 */
function opt(rule) {
  return { rule, required: false };
}

/** @type {Rule} */
function anyValue() {}

/** @type {Rule} */
function string(value, path, out) {
  if (typeof value !== 'string') {
    out.push(at(path, `must be a string, got ${describe(value)}`));
  }
}

/** @type {Rule} */
function stringOrNull(value, path, out) {
  if (value !== null && typeof value !== 'string') {
    out.push(at(path, `must be a string or null, got ${describe(value)}`));
  }
}

/** @type {Rule} */
function boolean(value, path, out) {
  if (typeof value !== 'boolean') {
    out.push(at(path, `must be a boolean, got ${describe(value)}`));
  }
}

/** Non-negative integer: counts, offsets, positions. @type {Rule} */
function count(value, path, out) {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) {
    out.push(at(path, `must be a non-negative integer, got ${describe(value)}`));
  }
}

/** Positive integer: sure and ayet numbers. @type {Rule} */
function positive(value, path, out) {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 1) {
    out.push(at(path, `must be a positive integer, got ${describe(value)}`));
  }
}

/**
 * @param {readonly (string | number)[]} allowed
 * @returns {Rule}
 */
function oneOf(allowed) {
  const list = allowed.map((v) => JSON.stringify(v)).join(', ');
  return (value, path, out) => {
    if (
      (typeof value !== 'string' && typeof value !== 'number') ||
      !allowed.some((v) => v === value)
    ) {
      out.push(at(path, `must be one of ${list}, got ${describe(value)}`));
    }
  };
}

/**
 * @param {RegExp} pattern
 * @param {string} label what the pattern means, for the message
 * @returns {Rule}
 */
function matches(pattern, label) {
  return (value, path, out) => {
    if (typeof value !== 'string' || !pattern.test(value)) {
      out.push(at(path, `must be ${label}, got ${describe(value)}`));
    }
  };
}

/**
 * @param {Rule} item
 * @returns {Rule}
 */
function arrayOf(item) {
  return (value, path, out) => {
    if (!Array.isArray(value)) {
      out.push(at(path, `must be an array, got ${describe(value)}`));
      return;
    }
    value.forEach((element, index) => item(element, `${path}[${index}]`, out));
  };
}

/**
 * Fixed-length array.
 * @param {Rule[]} items
 * @param {string} label e.g. "2 strings"
 * @returns {Rule}
 */
function tuple(items, label) {
  return (value, path, out) => {
    if (!Array.isArray(value) || value.length !== items.length) {
      const got = Array.isArray(value) ? `${value.length} item(s)` : describe(value);
      out.push(at(path, `must be an array of ${label}, got ${got}`));
      return;
    }
    items.forEach((rule, index) => rule(value[index], `${path}[${index}]`, out));
  };
}

/**
 * Object with the given fields. Closed objects reject unknown keys.
 * @param {Record<string, Field>} fields
 * @param {{ open?: boolean, nullable?: boolean }} [options]
 * @returns {Rule}
 */
function object(fields, { open = false, nullable = false } = {}) {
  return (value, path, out) => {
    if (nullable && value === null) {
      return;
    }
    if (!isRecord(value)) {
      out.push(at(path, `must be an object${nullable ? ' or null' : ''}, got ${describe(value)}`));
      return;
    }
    if (!open) {
      for (const key of Object.keys(value)) {
        if (!Object.hasOwn(fields, key)) {
          out.push(at(path, `unknown key ${JSON.stringify(key)}`));
        }
      }
    }
    for (const [key, field] of Object.entries(fields)) {
      if (!Object.hasOwn(value, key)) {
        if (field.required) {
          out.push(at(path, `missing key ${JSON.stringify(key)}`));
        }
        continue;
      }
      field.rule(value[key], child(path, key), out);
    }
  };
}

const stringPair = tuple([string, string], '2 strings');
const countPair = tuple([count, count], '2 non-negative integers');

/** Error codes of the anchor parsers (Capa semasi 7). */
export const ANCHOR_ERRORS = Object.freeze([
  'BICIM',
  'SURE_ARALIGI',
  'AYET_ARALIGI',
  'TERS_ARALIK',
  'KANONIK_DEGIL',
  'UZUNLUK',
]);

/**
 * content-hash: expected.text exists exactly when input.op is "kanonik".
 * @param {Record<string, unknown>} line
 * @param {string[]} out
 */
function hashTextRule(line, out) {
  const input = line['input'];
  const expected = line['expected'];
  if (!isRecord(input) || !isRecord(expected)) {
    return;
  }
  const hasText = Object.hasOwn(expected, 'text');
  if (input['op'] === 'kanonik' && !hasText) {
    out.push('expected: missing key "text" (required when input.op is "kanonik")');
  } else if (input['op'] === 'ham' && hasText) {
    out.push('expected.text: only allowed when input.op is "kanonik"');
  }
}

// ---------------------------------------------------------------------------------------------
// Escape rule (A04 vector specification 1; same rule as dizgi_yaz in the Python generator):
// these categories, characters outside the BMP and the Arabic blocks are never written raw in a
// line, only as lower-case \uXXXX (a surrogate pair outside the BMP). U+0020 is written raw.
// Only the kinds with `escapes: true` are checked (normalize/tr and normalize/ar).
// ---------------------------------------------------------------------------------------------

/** @type {readonly (readonly [string, RegExp])[]} */
const ESCAPED_CATEGORIES = Object.freeze(
  ['Mn', 'Mc', 'Me', 'Cc', 'Cf', 'Zl', 'Zp', 'Zs', 'Co', 'Cs', 'Cn'].map(
    (name) => /** @type {const} */ ([name, new RegExp(`^\\p{${name}}$`, 'u')]),
  ),
);

/** Arabic blocks (Arama 1.1): such a code point is always written as an escape. */
const ARABIC_BLOCKS = Object.freeze([
  [0x0600, 0x06ff],
  [0x0750, 0x077f],
  [0x08a0, 0x08ff],
  [0xfb50, 0xfdff],
  [0xfe70, 0xfeff],
]);

/**
 * @param {number} value
 * @returns {string} four lower-case hex digits (at least)
 */
function hex4(value) {
  return value.toString(16).padStart(4, '0');
}

/**
 * Raw characters of one line that must have been written as escapes.
 * @param {string} content the line as written
 * @returns {string[]} one message per distinct code point
 */
function rawEscapeProblems(content) {
  /** @type {string[]} */
  const out = [];
  const seen = new Set();
  for (const ch of content) {
    const cp = ch.codePointAt(0) ?? 0;
    if (cp === 0x20 || seen.has(cp)) {
      continue;
    }
    /** @type {string | null} */
    let reason = null;
    let escape = `\\u${hex4(cp)}`;
    if (cp > 0xffff) {
      const offset = cp - 0x10000;
      reason = 'outside the BMP';
      escape = `\\u${hex4(0xd800 + (offset >> 10))}\\u${hex4(0xdc00 + (offset & 0x3ff))}`;
    } else if (ARABIC_BLOCKS.some(([first, last]) => cp >= (first ?? 0) && cp <= (last ?? 0))) {
      reason = 'Arabic block';
    } else {
      reason = ESCAPED_CATEGORIES.find(([, pattern]) => pattern.test(ch))?.[0] ?? null;
    }
    if (reason !== null) {
      seen.add(cp);
      out.push(`raw U+${hex4(cp).toUpperCase()} (${reason}) must be written as ${escape}`);
    }
  }
  return out;
}

/**
 * A search key: no leading, trailing or doubled U+0020.
 * @param {unknown} value
 * @param {string} path
 * @param {string[]} out
 * @returns {boolean} true when the value is a string without such a problem
 */
function cleanSpaces(value, path, out) {
  if (typeof value !== 'string') {
    return false;
  }
  let clean = true;
  if (value.startsWith(' ') || value.endsWith(' ')) {
    out.push(at(path, 'must not start or end with U+0020'));
    clean = false;
  }
  if (value.includes('  ')) {
    out.push(at(path, 'must not contain two U+0020 in a row'));
    clean = false;
  }
  return clean;
}

/**
 * @param {string} text a key that passed cleanSpaces
 * @returns {number} words separated by U+0020 (the empty key has none)
 */
function wordCount(text) {
  return text === '' ? 0 : text.split(' ').length;
}

/**
 * normalize/tr: both keys are well-formed, the wide key is folded (K-36 article 2) and both keys
 * carry the same number of words.
 * @param {Record<string, unknown>} line
 * @param {string[]} out
 */
function normalizeTrRule(line, out) {
  const expected = line['expected'];
  if (!isRecord(expected)) {
    return;
  }
  const dar = expected['dar'];
  const genis = expected['genis'];
  const darClean = cleanSpaces(dar, 'expected.dar', out);
  const genisClean = cleanSpaces(genis, 'expected.genis', out);
  if (typeof genis === 'string') {
    if (/[\u0300-\u036f]/.test(genis)) {
      out.push('expected.genis: must not contain a character of U+0300-U+036F');
    }
    if (genis.includes('\u0131')) {
      out.push('expected.genis: must not contain dotless i (U+0131)');
    }
  }
  if (darClean && genisClean && typeof dar === 'string' && typeof genis === 'string') {
    const darWords = wordCount(dar);
    const genisWords = wordCount(genis);
    if (darWords !== genisWords) {
      out.push(
        `expected: dar has ${darWords} word(s) but genis has ${genisWords} (both keys must have the same number)`,
      );
    }
  }
}

/**
 * normalize/ar: the key has no leading, trailing or doubled U+0020.
 * @param {Record<string, unknown>} line
 * @param {string[]} out
 */
function normalizeArRule(line, out) {
  cleanSpaces(line['expected'], 'expected', out);
}

/**
 * @typedef {object} Kind
 * @property {Rule} input
 * @property {Rule} expected
 * @property {(line: Record<string, unknown>, out: string[]) => void} [extra] cross-field rule
 * @property {boolean} [escapes] apply the escape rule to the whole line
 */

/**
 * Recognized vector files, by path relative to the package root (A04 vector specification 2).
 * @type {ReadonlyMap<string, Kind>}
 */
const KINDS = new Map([
  [
    'anchors/valid.jsonl',
    {
      input: string,
      expected: object({
        ref: req(
          object({
            anchor: req(object({ t: req(string) }, { open: true })),
            span: opt(object({ start: req(count), end: req(count) })),
          }),
        ),
        canonical: req(string),
        unit: req(string),
        unit_span: req(object({ unit: req(string), span: opt(countPair) }, { nullable: true })),
        ayahs: req(arrayOf(object({ sure: req(positive), ayet: req(positive) }))),
      }),
    },
  ],
  ['anchors/invalid.jsonl', { input: string, expected: oneOf(ANCHOR_ERRORS) }],
  ['anchors/compare.jsonl', { input: stringPair, expected: oneOf([-1, 0, 1]) }],
  ['anchors/contains.jsonl', { input: stringPair, expected: boolean }],
  [
    'anchors/route.jsonl',
    {
      input: object({ capa: req(string), sema: opt(string) }),
      expected: object({ native: req(string), web: opt(stringOrNull) }),
    },
  ],
  [
    'offsets/offsets.jsonl',
    {
      input: string,
      expected: object({
        codepoints: req(count),
        utf16: req(count),
        cp_to_utf16: opt(arrayOf(countPair)),
        snap: opt(arrayOf(object({ in: req(countPair), out: req(countPair) }))),
      }),
    },
  ],
  [
    'content-hash/hash.jsonl',
    {
      input: object({ text: req(string), op: req(oneOf(['ham', 'kanonik'])) }),
      expected: object({
        sha256: req(matches(/^[0-9a-f]{64}$/, '64 lower-case hex digits')),
        text: opt(string),
      }),
      extra: hashTextRule,
    },
  ],
  [
    'normalize/tr.jsonl',
    {
      input: string,
      expected: object({ dar: req(string), genis: req(string) }),
      extra: normalizeTrRule,
      escapes: true,
    },
  ],
  [
    'normalize/ar.jsonl',
    { input: string, expected: string, extra: normalizeArRule, escapes: true },
  ],
]);

/** Package-relative paths of the recognized vector files. */
export const VECTOR_KINDS = Object.freeze([...KINDS.keys()]);

/** Folders that hold recognized vector files (a scan root with this name is a vector folder). */
const VECTOR_FOLDERS = new Set(VECTOR_KINDS.map((key) => key.slice(0, key.indexOf('/'))));

/** Files that share one id sequence: an id may not appear in both (vector specification 1). */
const ID_PARTNERS = new Map([
  ['anchors/valid.jsonl', 'anchors/invalid.jsonl'],
  ['anchors/invalid.jsonl', 'anchors/valid.jsonl'],
]);

/** @type {Map<Kind, Rule>} */
const lineRules = new Map();

/**
 * Top-level rule of one kind: only id, input, expected, note; input and expected required.
 * @param {Kind} kind
 * @returns {Rule}
 */
function lineRule(kind) {
  let rule = lineRules.get(kind);
  if (rule === undefined) {
    rule = object({
      id: opt(anyValue), // checked by the basic rules
      input: req(kind.input),
      expected: req(kind.expected),
      note: opt(string),
    });
    lineRules.set(kind, rule);
  }
  return rule;
}

/**
 * Field messages of one parsed line of a recognized file.
 * @param {string} content the line as written
 * @param {Record<string, unknown>} value the parsed line
 * @param {Kind} kind
 * @returns {string[]}
 */
function checkFields(content, value, kind) {
  /** @type {string[]} */
  const out = [];
  for (const literal of numberLiterals(content)) {
    if (!PLAIN_INTEGER.test(literal)) {
      out.push(`number ${literal} is not a plain integer (numbers in this file are integers)`);
    }
  }
  lineRule(kind)(value, '', out);
  kind.extra?.(value, out);
  if (kind.escapes === true) {
    out.push(...rawEscapeProblems(content));
  }
  return out;
}

/**
 * Checks one JSONL file and returns its problems and the line of every accepted id.
 * @param {Uint8Array} bytes
 * @param {string} key package-relative path; unknown keys get the basic rules only
 * @returns {{ problems: { line: number, message: string }[], ids: Map<string, number> }}
 */
function inspect(bytes, key) {
  /** @type {{ line: number, message: string }[]} */
  const problems = [];
  /** @type {Map<string, number>} */
  const seen = new Map();
  const kind = KINDS.get(key);

  if (bytes.length === 0) {
    return { problems: [{ line: 0, message: 'empty file' }], ids: seen };
  }
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    problems.push({ line: 1, message: 'UTF-8 BOM found' });
  }
  if (bytes.includes(CR)) {
    problems.push({ line: 0, message: 'CR (0x0D) found; only LF line endings are allowed' });
  }

  /** @type {string} */
  let text;
  try {
    text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    problems.push({ line: 0, message: 'invalid UTF-8' });
    return { problems, ids: seen };
  }

  if (bytes[bytes.length - 1] !== LF) {
    problems.push({ line: 0, message: 'missing final newline' });
  }

  const lines = text.split('\n');
  if (lines[lines.length - 1] === '') {
    lines.pop();
  }

  /**
   * Previous accepted id, for the order rule of recognized files.
   * @type {{ id: string, line: number } | null}
   */
  let previous = null;
  lines.forEach((raw, index) => {
    const no = index + 1;
    // A leading BOM is reported once above; strip it so line 1 can still be parsed.
    const line = no === 1 ? raw.replace(/^\uFEFF/, '') : raw;
    const content = line.endsWith('\r') ? line.slice(0, -1) : line;
    if (no > 1 && content.startsWith('\uFEFF')) {
      problems.push({ line: no, message: 'BOM (U+FEFF) at the start of a line' });
      return;
    }
    if (content.trim() === '') {
      problems.push({ line: no, message: 'blank line' });
      return;
    }
    /** @type {unknown} */
    let value;
    try {
      value = JSON.parse(content);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      problems.push({ line: no, message: `invalid JSON: ${detail}` });
      return;
    }
    if (!isRecord(value)) {
      problems.push({ line: no, message: 'line is not a JSON object' });
      return;
    }
    for (const message of scanStrings(content)) {
      problems.push({ line: no, message });
    }
    if (kind !== undefined) {
      for (const message of checkFields(content, value, kind)) {
        problems.push({ line: no, message });
      }
    }
    const id = value['id'];
    if (typeof id !== 'string' || id === '') {
      problems.push({ line: no, message: 'missing or empty string "id"' });
      return;
    }
    const first = seen.get(id);
    if (first !== undefined) {
      problems.push({ line: no, message: `duplicate id "${id}" (first on line ${first})` });
      return;
    }
    seen.set(id, no);
    // Code-unit order (JavaScript < on strings), not locale order: "Z" sorts before "a".
    if (kind !== undefined && previous !== null && id < previous.id) {
      problems.push({
        line: no,
        message: `id "${id}" is out of order: it sorts before "${previous.id}" (line ${previous.line}); lines must be in code-unit order of id`,
      });
    }
    previous = { id, line: no };
  });

  return { problems, ids: seen };
}

/**
 * Checks the bytes of one JSONL file.
 * @param {Uint8Array} bytes
 * @param {string} [key] path relative to the package root ('anchors/valid.jsonl'); with a
 *   recognized path the field rules apply too, otherwise only the basic rules
 * @returns {{ line: number, message: string }[]} violations (line 0 = whole file)
 */
export function checkBytes(bytes, key = '') {
  return inspect(bytes, key).problems;
}

/**
 * Walks a folder and returns its .jsonl files with their path relative to the folder.
 * @param {string} dir
 * @param {string} prefix relative path of dir, '' or ending with '/'
 * @param {Set<string>} skip
 * @returns {{ file: string, key: string }[]}
 */
function walk(dir, prefix, skip) {
  /** @type {{ file: string, key: string }[]} */
  const found = [];
  const names = readdirSync(dir).sort();
  for (const name of names) {
    if (skip.has(name) || name.startsWith('.')) {
      continue;
    }
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      found.push(...walk(full, `${prefix}${name}/`, skip));
    } else if (name.endsWith('.jsonl')) {
      found.push({ file: full, key: `${prefix}${name}` });
    }
  }
  return found;
}

/**
 * Lists .jsonl files under a path (a file is returned as is). Order is code-unit order.
 * @param {string} path
 * @param {Set<string>} skip directory names to skip below the given root
 * @returns {string[]}
 */
export function listJsonl(path, skip = new Set()) {
  if (statSync(path).isFile()) {
    return [path];
  }
  return walk(path, '', skip).map((entry) => entry.file);
}

/**
 * Lists the vector files under a scan root with their package-relative path (key) and the
 * package root they belong to (base). The package root is found without path.relative(), which
 * lower-cases Windows paths and breaks on the U+0130 in the project folder name:
 * - a folder named like a vector folder (anchors, offsets, content-hash) is inside the package
 *   root, so its files are keyed "<folder>/<path>";
 * - any other folder is taken as the package root;
 * - a file is keyed "<parent folder>/<file name>".
 * @param {string} root
 * @param {Set<string>} skip
 * @returns {{ file: string, key: string, base: string }[]}
 */
export function listVectors(root, skip = new Set()) {
  const full = resolve(root);
  if (statSync(full).isFile()) {
    const folder = dirname(full);
    return [{ file: root, key: `${basename(folder)}/${basename(full)}`, base: dirname(folder) }];
  }
  const name = basename(full);
  if (VECTOR_FOLDERS.has(name)) {
    const base = dirname(full);
    return walk(root, `${name}/`, skip).map((entry) => ({ ...entry, base }));
  }
  return walk(root, '', skip).map((entry) => ({ ...entry, base: full }));
}

/**
 * Checks every .jsonl file under the given roots.
 * @param {string[]} roots
 * @param {Set<string>} skip
 * @returns {{ files: number, problems: { file: string, line: number, message: string }[] }}
 */
export function checkPaths(roots, skip = new Set()) {
  /** @type {{ file: string, line: number, message: string }[]} */
  const problems = [];
  /**
   * Package root -> key -> ids of that file (with their line), for ID_PARTNERS.
   * @type {Map<string, Map<string, Map<string, number>>>}
   */
  const shared = new Map();
  let files = 0;
  for (const root of roots) {
    for (const { file, key, base } of listVectors(root, skip)) {
      files += 1;
      const { problems: own, ids } = inspect(readFileSync(file), key);
      for (const problem of own) {
        problems.push({ file, ...problem });
      }
      const partnerKey = ID_PARTNERS.get(key);
      if (partnerKey === undefined) {
        continue;
      }
      let group = shared.get(base);
      if (group === undefined) {
        group = new Map();
        shared.set(base, group);
      }
      if (group.has(key)) {
        continue; // the same file reached through two roots
      }
      group.set(key, ids);
      const partner = group.get(partnerKey);
      if (partner === undefined) {
        continue;
      }
      for (const [id, line] of ids) {
        const other = partner.get(id);
        if (other !== undefined) {
          problems.push({
            file,
            line,
            message: `id "${id}" is also used in ${partnerKey} (line ${other}); valid and invalid share one id sequence`,
          });
        }
      }
    }
  }
  return { files, problems };
}
