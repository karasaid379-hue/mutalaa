import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);

/** Folder of the @mutalaa/test-vectors workspace package (shared/test-vectors). */
export const vectorRoot = dirname(require.resolve('@mutalaa/test-vectors/package.json'));

/** Shared data folder next to the vectors (shared/data). */
export const sharedDataRoot = join(vectorRoot, '..', 'data');

export interface VectorRow<I, E> {
  id: string;
  input: I;
  expected: E;
  note?: string;
}

/** Read a JSONL vector file: split on LF only, one JSON object per line. */
export function readVectors<I, E>(relativePath: string): VectorRow<I, E>[] {
  const content = readFileSync(join(vectorRoot, relativePath), 'utf8');
  const lines = content.split('\n');
  if (lines.at(-1) === '') lines.pop();
  return lines.map((line) => JSON.parse(line) as VectorRow<I, E>);
}
