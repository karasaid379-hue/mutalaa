// @vitest-environment node
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const root = new URL('../', import.meta.url);
const manifest = JSON.parse(readFileSync(new URL('package.json', root), 'utf8')) as {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
  peerDependencies?: Record<string, string>;
  optionalDependencies?: Record<string, string>;
};
const entries = Object.entries({
  ...manifest.dependencies,
  ...manifest.devDependencies,
  ...manifest.peerDependencies,
  ...manifest.optionalDependencies,
});
const external = entries.filter(([name]) => !name.startsWith('@mutalaa/'));
const internal = entries.filter(([name]) => name.startsWith('@mutalaa/'));

describe('editor dependencies (Proje yapisi 2, A15 Tedarik)', () => {
  it('has dependencies at all', () => {
    expect(external.length).toBeGreaterThan(10);
  });

  it('allows only @mutalaa/anchors and @mutalaa/search, as workspace links', () => {
    expect(internal.map(([name]) => name).sort()).toEqual(['@mutalaa/anchors', '@mutalaa/search']);
    for (const [, range] of internal) expect(range).toBe('workspace:*');
  });

  it('pins every external dependency to an exact version', () => {
    const exact = /^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$/;
    const loose = external.filter(([, range]) => !exact.test(range));
    expect(loose).toEqual([]);
  });

  it('has no platform packages (react-native, expo, next) and no react-router-dom', () => {
    const banned = /^(react-native(-.*)?|expo(-.*)?|next(\/.*)?|react-router-dom)$/;
    expect(external.map(([name]) => name).filter((name) => banned.test(name))).toEqual([]);
  });

  it('uses Base UI, not Radix (radix-ui, @radix-ui/*)', () => {
    const radix = external
      .map(([name]) => name)
      .filter((n) => n === 'radix-ui' || n.startsWith('@radix-ui/'));
    expect(radix).toEqual([]);
    expect(external.map(([name]) => name)).toContain('@base-ui/react');
  });

  it('keeps only client.ts and the generated schema.d.ts in src/api', () => {
    const dir = new URL('src/api/', root);
    expect(existsSync(dir)).toBe(true);
    const files = readdirSync(fileURLToPath(dir)).sort();
    const allowed = ['client.ts', 'schema.d.ts'];
    expect(files.filter((f) => !allowed.includes(f))).toEqual([]);
    expect(files).toContain('client.ts');
  });
});
