import { readFileSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// Allowed workspace dependency graph (Proje yapisi 2). The only @mutalaa/* dev dependency
// allowed on top of this is @mutalaa/test-vectors, and only for anchors and search.
const allowed: Record<string, string[]> = {
  anchors: [],
  search: [],
  'content-schema': ['anchors'],
  'reader-core': ['anchors', 'content-schema', 'search'],
  player: ['anchors'],
  'ui-tokens': [],
};
const withTestVectors = new Set(['anchors', 'search']);

const packagesDir = new URL('../../', import.meta.url);

function workspaceDependencies(folder: string): string[] {
  const manifest = JSON.parse(
    readFileSync(new URL(`${folder}/package.json`, packagesDir), 'utf8'),
  ) as Record<string, Record<string, string> | undefined>;
  return ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']
    .flatMap((field) => Object.keys(manifest[field] ?? {}))
    .filter((name) => name.startsWith('@mutalaa/'))
    .map((name) => name.slice('@mutalaa/'.length));
}

describe('workspace dependency graph', () => {
  it('has exactly the six expected packages', () => {
    const folders = readdirSync(packagesDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && entry.name !== 'node_modules')
      .map((entry) => entry.name)
      .sort();
    expect(folders).toEqual(Object.keys(allowed).sort());
  });

  for (const [folder, dependencies] of Object.entries(allowed)) {
    it(`${folder} depends on ${dependencies.join(', ') || 'no workspace package'}`, () => {
      const expected = [...dependencies];
      if (withTestVectors.has(folder)) expected.push('test-vectors');
      expect(workspaceDependencies(folder).sort()).toEqual(expected.sort());
    });
  }

  it('test-vectors is a dev dependency of anchors and search, never a runtime one', () => {
    for (const folder of withTestVectors) {
      const manifest = JSON.parse(
        readFileSync(new URL(`${folder}/package.json`, packagesDir), 'utf8'),
      ) as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> };
      expect(manifest.devDependencies?.['@mutalaa/test-vectors']).toBe('workspace:*');
      expect(manifest.dependencies?.['@mutalaa/test-vectors']).toBeUndefined();
    }
  });
});
