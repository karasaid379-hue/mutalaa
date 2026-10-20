import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { packageName } from '../src/index';

describe('package identity', () => {
  it('package.json name, folder name and exported packageName agree', () => {
    const manifest = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    const folder = basename(fileURLToPath(new URL('..', import.meta.url)));
    expect(manifest.name).toBe(`@mutalaa/${folder}`);
    expect(packageName).toBe(manifest.name);
  });
});
