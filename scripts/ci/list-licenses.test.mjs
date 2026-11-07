// Run: node --test "scripts/ci/*.test.mjs"
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { format, fromNuget, fromPnpm, summarize } from './list-licenses.mjs';

const SCRIPT = fileURLToPath(new URL('./list-licenses.mjs', import.meta.url));
// Temporary files stay inside the project (.tmp/ is ignored by git).
const TMP = fileURLToPath(new URL('../../.tmp/ci-test/', import.meta.url));

const run = (args, input) =>
  spawnSync(process.execPath, [SCRIPT, ...args], { input, encoding: 'utf8' });

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

test('fromNuget maps the nuget-license JSON fields and rejects a non-array', () => {
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
  assert.throws(() => fromNuget('{}'), /JSON array/);
});

test('fromNuget and fromPnpm reject entries with missing or renamed fields', () => {
  assert.throws(() => fromNuget(JSON.stringify([{ Foo: 1 }])), /no PackageId/);
  assert.throws(() => fromNuget(JSON.stringify([{ PackageId: 'X' }])), /no PackageVersion/);
  assert.throws(
    () => fromNuget(JSON.stringify([{ PackageId: 'X', PackageVersion: '1', License: 3 }])),
    /non-text License/,
  );
  assert.throws(
    () =>
      fromNuget(JSON.stringify([{ PackageId: 'X', PackageVersion: '1', ValidationErrors: 'e' }])),
    /non-array ValidationErrors/,
  );
  assert.throws(() => fromPnpm('[]'), /JSON object/);
  assert.throws(() => fromPnpm(JSON.stringify({ MIT: 'a' })), /not an array/);
  assert.throws(() => fromPnpm(JSON.stringify({ MIT: [{ versions: ['1'] }] })), /no package name/);
});

test('format sorts ordinally and shows missing licenses and tool notes', () => {
  const lines = format([
    { name: 'b', version: '1.0.0', license: 'GPL-3.0-only' },
    { name: 'a', version: '2.0.0', license: 'MIT' },
    { name: 'a', version: '10.0.0', license: '' },
    { name: 'İ-paket', version: '1', license: 'Unknown' },
    { name: 'c', version: '1', license: null, errors: ['license url only'] },
  ]);
  assert.deepEqual(lines, [
    '  a@10.0.0: (none declared)',
    '  a@2.0.0: MIT',
    '  b@1.0.0: GPL-3.0-only',
    '  c@1: (none declared) [license url only]',
    '  İ-paket@1: Unknown',
  ]);
});

test('summarize counts packages per license, sorted by license', () => {
  assert.equal(
    summarize([
      { name: 'a', version: '1', license: 'MIT' },
      { name: 'b', version: '1', license: 'Apache-2.0' },
      { name: 'c', version: '1', license: 'MIT' },
      { name: 'd', version: '1', license: null },
    ]),
    '(none declared) 1, Apache-2.0 1, MIT 2',
  );
  assert.equal(summarize([]), '');
});

test('command line: every license is listed and none stops the run', () => {
  const input = JSON.stringify({
    MIT: [{ name: 'a', versions: ['1.0.0'] }],
    'GPL-3.0-only': [{ name: 'g', versions: ['1.0.0'] }],
    UNLICENSED: [{ name: 'u', versions: ['0.1.0'] }],
  });
  const r = run(['pnpm'], input);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^pnpm: 3 packages$/m);
  assert.match(r.stdout, /^ {2}g@1\.0\.0: GPL-3\.0-only$/m);
  assert.match(r.stdout, /^ {2}u@0\.1\.0: UNLICENSED$/m);
  assert.match(r.stdout, /^licenses: GPL-3\.0-only 1, MIT 1, UNLICENSED 1$/m);
  const nuget = run(
    ['nuget'],
    JSON.stringify([{ PackageId: 'X', PackageVersion: '1', ValidationErrors: [{ Error: 'e' }] }]),
  );
  assert.equal(nuget.status, 0, nuget.stderr);
  assert.match(nuget.stdout, /X@1: \(none declared\) \[e\]/);
});

test('command line: exit code 2 for unreadable input, bad arguments and an empty NuGet list', () => {
  const empty = run(['pnpm'], '{}');
  assert.equal(empty.status, 0);
  assert.match(empty.stdout, /no shipped dependencies to list/);
  // An empty NuGet result is an error (the server always has dependencies); an empty pnpm result is fine.
  assert.equal(run(['nuget'], '[]').status, 2);
  assert.equal(run(['nuget'], '{}').status, 2);
  assert.equal(run(['pnpm'], 'not json').status, 2);
  assert.equal(run(['maven'], '{}').status, 2);
  assert.equal(run(['pnpm', '--json'], '{}').status, 2);
  assert.equal(run(['pnpm', 'a.json', 'b.json'], '{}').status, 2);
  assert.equal(run(['pnpm', 'does-not-exist.json']).status, 2);
});

test('command line: a renamed NuGet field is exit code 2, not a corrupt list', () => {
  const r = run(['nuget'], JSON.stringify([{ Foo: 1 }]));
  assert.equal(r.status, 2);
  assert.match(r.stderr, /no PackageId/);
});

test('command line: --json write errors are exit code 2; an empty NuGet list writes no file', () => {
  fs.mkdirSync(TMP, { recursive: true });
  const missingDir = `${TMP}no-such-dir/list.json`;
  const bad = run(
    ['pnpm', '--json', missingDir],
    JSON.stringify({ MIT: [{ name: 'a', versions: ['1'] }] }),
  );
  assert.equal(bad.status, 2);
  assert.match(bad.stderr, /cannot write/);
  const out = `${TMP}empty-nuget.json`;
  fs.rmSync(out, { force: true });
  try {
    assert.equal(run(['nuget', '--json', out], '[]').status, 2);
    assert.equal(fs.existsSync(out), false);
  } finally {
    fs.rmSync(out, { force: true });
  }
});

test('command line: --json writes the normalized list', () => {
  fs.mkdirSync(TMP, { recursive: true });
  const out = `${TMP}list-licenses.json`;
  try {
    const r = run(
      ['pnpm', '--json', out],
      JSON.stringify({ MIT: [{ name: 'a', versions: ['1'] }] }),
    );
    assert.equal(r.status, 0, r.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(out, 'utf8')), [
      { name: 'a', version: '1', license: 'MIT' },
    ]);
  } finally {
    fs.rmSync(out, { force: true });
  }
});
