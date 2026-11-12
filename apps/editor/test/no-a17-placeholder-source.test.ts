// @vitest-environment node
// A17.7 closing check (BÇ-56, A17 half): the placeholders and closed buttons that waited for A17 are gone; the
// count of `phase="A17"` in the panel source is 0 and the phase type no longer offers it.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC = fileURLToPath(new URL('../src/', import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = `${dir}${name}`;
    if (statSync(path).isDirectory()) return sourceFiles(`${path}/`);
    return /\.tsx?$/.test(path) && !path.endsWith('schema.d.ts') ? [path] : [];
  });
}

describe('no A17 placeholder left in the source', () => {
  const files = sourceFiles(SRC).map((path) => ({ path, text: readFileSync(path, 'utf8') }));

  it('reads the source tree', () => {
    expect(files.length).toBeGreaterThan(40);
  });

  it('has no phase="A17" anywhere (count 0)', () => {
    const hits = files.filter(({ text }) => /phase=["'{]+A17/.test(text)).map(({ path }) => path);
    expect(hits).toEqual([]);
  });

  it('has no "A17" phase literal in the OpenQuestionButton type', () => {
    const text = readFileSync(`${SRC}components/open-question-button.tsx`, 'utf8');
    expect(text).not.toMatch(/phase:[^;]*'A17'/);
    expect(text).toMatch(/phase:[^;]*'S-16'/);
  });

  it('shows no "not in the API yet" note on the lemma screen', () => {
    for (const { path, text } of files) {
      if (!path.includes('/screens/lemma/') && !path.endsWith('tr-lemma.ts')) continue;
      expect(text, path).not.toContain('MissingSection');
    }
  });
});
