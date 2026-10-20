// JSONL format checker for shared/test-vectors (Proje yapisi 1.2).
// Rules: UTF-8, no BOM, LF only, final newline, no blank lines,
// one JSON object per line, unique non-empty string "id" per file.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

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

/**
 * Checks the bytes of one JSONL file.
 * @param {Uint8Array} bytes
 * @returns {{ line: number, message: string }[]} violations (line 0 = whole file)
 */
export function checkBytes(bytes) {
  /** @type {{ line: number, message: string }[]} */
  const problems = [];

  if (bytes.length === 0) {
    return [{ line: 0, message: 'empty file' }];
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
    return problems;
  }

  if (bytes[bytes.length - 1] !== LF) {
    problems.push({ line: 0, message: 'missing final newline' });
  }

  const lines = text.split('\n');
  if (lines[lines.length - 1] === '') {
    lines.pop();
  }

  const seen = new Map();
  lines.forEach((raw, index) => {
    const no = index + 1;
    // A leading BOM is reported once above; strip it so line 1 can still be parsed.
    const line = no === 1 ? raw.replace(/^\uFEFF/, '') : raw;
    const content = line.endsWith('\r') ? line.slice(0, -1) : line;
    if (no > 1 && content.startsWith('﻿')) {
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
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      problems.push({ line: no, message: 'line is not a JSON object' });
      return;
    }
    for (const message of scanStrings(content)) {
      problems.push({ line: no, message });
    }
    const id = /** @type {Record<string, unknown>} */ (value)['id'];
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
  });

  return problems;
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
  /** @type {string[]} */
  const found = [];
  const names = readdirSync(path).sort();
  for (const name of names) {
    if (skip.has(name) || name.startsWith('.')) {
      continue;
    }
    const full = join(path, name);
    if (statSync(full).isDirectory()) {
      found.push(...listJsonl(full, skip));
    } else if (name.endsWith('.jsonl')) {
      found.push(full);
    }
  }
  return found;
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
  let files = 0;
  for (const root of roots) {
    for (const file of listJsonl(root, skip)) {
      files += 1;
      for (const problem of checkBytes(readFileSync(file))) {
        problems.push({ file, ...problem });
      }
    }
  }
  return { files, problems };
}
