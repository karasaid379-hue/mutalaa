// @vitest-environment node
// No single-character shortcut in the source (A15.3, WCAG 2.1.4); the running panel is checked in shortcuts.test.tsx.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC = fileURLToPath(new URL('../src/', import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = `${dir}${name}`;
    if (statSync(path).isDirectory()) return sourceFiles(`${path}/`);
    // The generated API types have `[key: string]` index signatures, not key handlers.
    return /\.tsx?$/.test(path) && !path.endsWith('schema.d.ts') ? [path] : [];
  });
}

/** The key names the panel reacts to. Every one is a named key; none is a printable character. */
const NAMED_KEYS = new Set(['Enter', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home']);

describe('no single-character shortcut (source)', () => {
  const files = sourceFiles(SRC).map((path) => ({ path, text: readFileSync(path, 'utf8') }));

  it('reads the source tree', () => {
    expect(files.length).toBeGreaterThan(40);
  });

  it('compares event.key only with named keys', () => {
    const found = new Set<string>();
    for (const { path, text } of files) {
      for (const match of text.matchAll(/\.key\s*[!=]==?\s*(['"`])([^'"`]*)\1/g)) {
        found.add(match[2]!);
        expect(NAMED_KEYS.has(match[2]!), `${path}: key '${match[2]}'`).toBe(true);
      }
    }
    // The handlers exist (the scan is not empty): the shortcut and the viewer keys.
    expect(found.has('Enter')).toBe(true);
    expect(found.has('ArrowUp')).toBe(true);
  });

  it('has no switch on the key, no key code, no access key, no hotkey library and no global key listener', () => {
    const forbidden: [string, RegExp][] = [
      ['switch on key', /switch\s*\(\s*[\w.]*\bkey\b\s*\)/],
      ['keyCode / which / code', /\.(keyCode|which|charCode)\b|\.code\s*[!=]==?/],
      ['accessKey', /accesskey/i],
      ['hotkey library', /hotkey|mousetrap|react-keyboard/i],
      ['onKeyPress', /onKeyPress|keypress/],
      ['global listener', /(window|document)\.addEventListener\(\s*['"]key/],
    ];
    for (const { path, text } of files) {
      for (const [label, pattern] of forbidden) {
        expect(pattern.test(text), `${path}: ${label}`).toBe(false);
      }
    }
  });
});
