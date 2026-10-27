// Run: node --test "scripts/ci/*.test.mjs"
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { check, evaluate, fromNuget, fromPnpm } from './check-licenses.mjs';

const SCRIPT = fileURLToPath(new URL('./check-licenses.mjs', import.meta.url));

test('allowed single licenses pass, case-insensitively', () => {
  for (const l of [
    'MIT',
    'mit',
    'Apache-2.0',
    'BSD-3-Clause',
    'ISC',
    'BlueOak-1.0.0',
    'PostgreSQL',
    'MPL-2.0',
  ]) {
    assert.equal(evaluate(l).ok, true, l);
  }
});

test('LGPL is allowed, GPL family is not', () => {
  assert.equal(evaluate('LGPL-3.0-only').ok, true);
  assert.equal(evaluate('LGPL-2.1-or-later').ok, true);
  assert.equal(evaluate('LGPL-3.0+').ok, true);
  for (const l of ['GPL-2.0-only', 'GPL-3.0-or-later', 'AGPL-3.0-only', 'SSPL-1.0', 'BUSL-1.1']) {
    const r = evaluate(l);
    assert.equal(r.ok, false, l);
    assert.match(r.reason, /copyleft/, l);
  }
});

test('unknown, empty and non-SPDX values fail', () => {
  for (const l of [
    '',
    '   ',
    null,
    undefined,
    'UNLICENSED',
    'Unknown',
    'SEE LICENSE IN LICENSE.md',
    'Commercial',
  ]) {
    assert.equal(evaluate(l).ok, false, String(l));
  }
});

test('OR passes with one allowed alternative, AND needs every term', () => {
  assert.equal(evaluate('(MIT OR GPL-3.0-only)').ok, true);
  assert.equal(evaluate('GPL-2.0-only OR MIT').ok, true);
  assert.equal(evaluate('GPL-2.0-only OR AGPL-3.0-only').ok, false);
  assert.equal(evaluate('MIT AND Zlib').ok, true);
  assert.equal(evaluate('MIT AND GPL-3.0-only').ok, false);
  assert.equal(evaluate('(MIT AND BSD-3-Clause) OR GPL-3.0-only').ok, true);
  assert.equal(evaluate('MIT OR (GPL-3.0-only AND Apache-2.0)').ok, true);
  assert.equal(evaluate('GPL-3.0-only AND (MIT OR Apache-2.0)').ok, false);
});

test('WITH exceptions are ignored; malformed expressions fail', () => {
  assert.equal(evaluate('Apache-2.0 WITH LLVM-exception').ok, true);
  assert.equal(evaluate('GPL-2.0-only WITH Classpath-exception-2.0').ok, false);
  for (const l of ['(MIT', 'MIT)', 'MIT OR', 'AND MIT', 'MIT MIT', '()']) {
    const r = evaluate(l);
    assert.equal(r.ok, false, l);
  }
});

test('check reports violations and applies exceptions by name or name@version', () => {
  const packages = [
    { name: 'a', version: '1.0.0', license: 'MIT' },
    { name: 'b', version: '2.0.0', license: 'GPL-3.0-only' },
    { name: 'c', version: '3.0.0', license: 'Unknown' },
    { name: 'd', version: '4.0.0', license: null, errors: ['license url only'] },
  ];
  const r = check(packages, [{ package: 'c@3.0.0', source: 'https://example.invalid/c' }]);
  assert.equal(r.checked, 4);
  assert.deepEqual(
    r.violations.map((v) => v.name),
    ['b', 'd'],
  );
  assert.deepEqual(
    r.excepted.map((v) => v.name),
    ['c'],
  );
  const wrongVersion = check(packages, [{ package: 'c@9.9.9' }]);
  assert.deepEqual(
    wrongVersion.violations.map((v) => v.name),
    ['b', 'c', 'd'],
  );
  const byName = check(packages, [{ package: 'b' }, { package: 'c' }, { package: 'd' }]);
  assert.equal(byName.violations.length, 0);
});

test('validation errors from the nuget tool make a package fail even with a license', () => {
  const r = check([
    { name: 'x', version: '1', license: 'MIT', errors: ['file license not readable'] },
  ]);
  assert.equal(r.violations.length, 1);
});

test('fromPnpm flattens licenses, skips workspace packages, handles empty output', () => {
  const json = JSON.stringify({
    MIT: [
      { name: 'left-pad', versions: ['1.3.0', '1.2.0'] },
      { name: '@mutalaa/anchors', versions: ['0.0.0'] },
    ],
    '(MIT OR Apache-2.0)': [{ name: 'dual', versions: ['2.0.0'] }],
  });
  assert.deepEqual(fromPnpm(json), [
    { name: 'left-pad', version: '1.3.0', license: 'MIT' },
    { name: 'left-pad', version: '1.2.0', license: 'MIT' },
    { name: 'dual', version: '2.0.0', license: '(MIT OR Apache-2.0)' },
  ]);
  assert.deepEqual(fromPnpm('{}'), []);
  assert.deepEqual(fromPnpm(''), []);
  assert.deepEqual(fromPnpm('No licenses in packages found'), []);
  assert.throws(() => fromPnpm('not json'));
});

test('fromNuget maps the nuget-license JSON fields', () => {
  const json = JSON.stringify([
    { PackageId: 'Npgsql', PackageVersion: '10.0.0', License: 'PostgreSQL', ValidationErrors: [] },
    {
      PackageId: 'Odd',
      PackageVersion: '1.0.0',
      ValidationErrors: [{ Error: 'no license', Context: 'Odd' }],
    },
  ]);
  assert.deepEqual(fromNuget(json), [
    { name: 'Npgsql', version: '10.0.0', license: 'PostgreSQL', errors: [] },
    { name: 'Odd', version: '1.0.0', license: null, errors: ['no license'] },
  ]);
});

test('command line: exit codes', () => {
  const run = (kind, input) =>
    spawnSync(process.execPath, [SCRIPT, kind], { input, encoding: 'utf8' });
  const ok = run('pnpm', JSON.stringify({ MIT: [{ name: 'a', versions: ['1.0.0'] }] }));
  assert.equal(ok.status, 0);
  assert.match(ok.stdout, /1 packages checked/);
  const empty = run('pnpm', '{}');
  assert.equal(empty.status, 0);
  assert.match(empty.stdout, /no shipped dependencies/);
  const bad = run('pnpm', JSON.stringify({ 'GPL-3.0-only': [{ name: 'g', versions: ['1.0.0'] }] }));
  assert.equal(bad.status, 1);
  assert.match(bad.stdout, /DISALLOWED: g@1\.0\.0/);
  assert.equal(run('pnpm', 'not json').status, 2);
  assert.equal(run('maven', '{}').status, 2);
});
