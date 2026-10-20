import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { after, before, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import { checkBytes, checkPaths, scanStrings } from '../scripts/check-lib.mjs';

const script = fileURLToPath(new URL('../scripts/check.mjs', import.meta.url));
// Scratch folder inside the project (.tmp/ is git-ignored); removed after the run.
const scratch = fileURLToPath(new URL('../../../.tmp/vektor-test-birim/', import.meta.url));

const GOOD = '{"id":"a","input":"x","expected":"x"}\n';
const SECOND = '{"id":"b","input":"y","expected":"y"}\n';
const BOM = Buffer.from([0xef, 0xbb, 0xbf]);

/**
 * Wraps raw bytes in an otherwise valid JSONL line.
 * @param {number[]} bytes
 * @returns {Buffer}
 */
function withBytes(bytes) {
  return Buffer.concat([Buffer.from('{"id":"'), Buffer.from(bytes), Buffer.from('"}\n')]);
}

/**
 * A problem expectation: message pattern and, optionally, the line it must be reported on.
 * @typedef {[RegExp, number?]} Expect
 */

/**
 * Files that must be rejected: name, content, expected problems (all must be reported).
 * @type {[string, Buffer | string, Expect[]][]}
 */
const rejected = [
  ['bom', Buffer.concat([BOM, Buffer.from(GOOD)]), [[/BOM found/, 1]]],
  ['bom-only', BOM, [[/BOM found/, 1], [/missing final newline/], [/blank line/, 1]]],
  [
    'bom-newline',
    Buffer.concat([BOM, Buffer.from('\n')]),
    [
      [/BOM found/, 1],
      [/blank line/, 1],
    ],
  ],
  ['bom-mid-file', GOOD + '﻿' + SECOND, [[/BOM \(U\+FEFF\) at the start of a line/, 2]]],
  ['crlf', '{"id":"a","input":"x","expected":"x"}\r\n', [[/CR \(0x0D\) found/]]],
  ['lone-cr-at-end', '{"id":"a"}\r', [[/CR \(0x0D\) found/], [/missing final newline/]]],
  ['lone-cr-between', '{"id":"a"}\r{"id":"b"}\n', [[/CR \(0x0D\) found/], [/invalid JSON/, 1]]],
  ['blank-line', GOOD + '\n' + SECOND, [[/blank line/, 2]]],
  ['u2028-only-line', GOOD + ' \n' + SECOND, [[/blank line/, 2]]],
  ['whitespace-only-line', GOOD + '   \n', [[/blank line/, 2]]],
  ['no-final-newline', '{"id":"a","input":"x","expected":"x"}', [[/missing final newline/]]],
  ['empty-file', '', [[/empty file/, 0]]],
  ['invalid-json', GOOD + '{"id":"b",\n', [[/invalid JSON/, 2]]],
  ['not-an-object-array', '[1,2]\n', [[/not a JSON object/, 1]]],
  ['not-an-object-null', 'null\n', [[/not a JSON object/, 1]]],
  ['not-an-object-string', '"x"\n', [[/not a JSON object/, 1]]],
  ['id-missing', '{"input":"x"}\n', [[/missing or empty string "id"/, 1]]],
  ['id-number', '{"id":1}\n', [[/missing or empty string "id"/, 1]]],
  ['id-null', '{"id":null}\n', [[/missing or empty string "id"/, 1]]],
  ['id-empty-string', '{"id":""}\n', [[/missing or empty string "id"/, 1]]],
  ['id-duplicate-in-file', GOOD + SECOND + GOOD, [[/duplicate id "a" \(first on line 1\)/, 3]]],
  ['utf8-invalid-ff', withBytes([0xff]), [[/invalid UTF-8/]]],
  ['utf8-overlong-c0-80', withBytes([0xc0, 0x80]), [[/invalid UTF-8/]]],
  ['utf8-encoded-surrogate-ed-a0-80', withBytes([0xed, 0xa0, 0x80]), [[/invalid UTF-8/]]],
  ['utf8-truncated-sequence', withBytes([0xe2, 0x82]), [[/invalid UTF-8/]]],
  ['key-duplicate', '{"id":"a","id":"b"}\n', [[/duplicate key "id" in object/, 1]]],
  ['key-duplicate-escaped', String.raw`{"id":"x","a":1,"a":2}` + '\n', [[/duplicate key "a"/, 1]]],
  ['key-duplicate-nested', '{"id":"a","v":{"k":1,"k":2}}\n', [[/duplicate key "k"/, 1]]],
  [
    'key-duplicate-in-array',
    '{"id":"a","v":[{"k":1},{"k":1,"k":2}]}\n',
    [[/duplicate key "k"/, 1]],
  ],
  [
    'surrogate-lone-high-in-value',
    String.raw`{"id":"a","input":"\ud800"}` + '\n',
    [[/lone surrogate in string/, 1]],
  ],
  [
    'surrogate-lone-low-in-value',
    String.raw`{"id":"a","input":"x\udc00y"}` + '\n',
    [[/lone surrogate in string/, 1]],
  ],
  [
    'surrogate-reversed-pair',
    String.raw`{"id":"a","input":"\ude00\ud83d"}` + '\n',
    [[/lone surrogate in string/, 1]],
  ],
  [
    'surrogate-lone-in-key',
    String.raw`{"id":"a","\udc00":1}` + '\n',
    [[/lone surrogate in key/, 1]],
  ],
  ['surrogate-lone-in-id', String.raw`{"id":"\ud800"}` + '\n', [[/lone surrogate in string/, 1]]],
  [
    'surrogate-lone-nested',
    String.raw`{"id":"a","v":[{"k":"\ud83d"}]}` + '\n',
    [[/lone surrogate in string/, 1]],
  ],
];

/**
 * Files that must be accepted.
 * @type {[string, Buffer | string][]}
 */
const accepted = [
  ['clean', GOOD + SECOND],
  ['arabic-and-turkish-utf8', JSON.stringify({ id: 't', input: 'İİıب' }) + '\n'],
  ['surrogate-pair-escaped', String.raw`{"id":"a","input":"😀"}` + '\n'],
  ['surrogate-pair-literal', JSON.stringify({ id: 'a', input: '\u{1F600}' }) + '\n'],
  [
    'same-key-in-different-objects',
    '{"id":"a","v":{"id":1},"w":{"id":2},"x":[{"id":3},{"id":4}]}\n',
  ],
  ['value-equal-to-key-name', '{"id":"a","a":"a","b":"id"}\n'],
  ['escaped-quote-and-backslash', String.raw`{"id":"a","s":"q\"\\","t":"\\\\"}` + '\n'],
];

/**
 * @param {string} name
 * @returns {string} folder holding the sample files of one case
 */
function folderOf(name) {
  return join(scratch, name);
}

/**
 * @param {string} folder
 * @returns {{ status: number, stderr: string }}
 */
function runCli(folder) {
  const result = spawnSync(process.execPath, [script, folder], { encoding: 'utf8' });
  return { status: result.status ?? -1, stderr: result.stderr };
}

describe('test-vectors format checker', () => {
  before(() => {
    rmSync(scratch, { recursive: true, force: true });
    for (const [name, content] of [...rejected, ...accepted]) {
      mkdirSync(folderOf(name), { recursive: true });
      writeFileSync(join(folderOf(name), 'v.jsonl'), content);
    }
    // The same id in two different files is fine: ids are unique per file.
    mkdirSync(folderOf('same-id-in-two-files'), { recursive: true });
    writeFileSync(join(folderOf('same-id-in-two-files'), 'one.jsonl'), GOOD);
    writeFileSync(join(folderOf('same-id-in-two-files'), 'two.jsonl'), GOOD);
    mkdirSync(folderOf('no-vectors'), { recursive: true });
  });

  after(() => {
    rmSync(scratch, { recursive: true, force: true });
  });

  for (const [name, , expectations] of rejected) {
    it(`rejects ${name} with exit 1 and the right reason`, () => {
      const { problems } = checkPaths([folderOf(name)]);
      for (const [pattern, line] of expectations) {
        const hit = problems.find(
          (p) => pattern.test(p.message) && (line === undefined || p.line === line),
        );
        assert.ok(
          hit,
          `expected ${pattern}${line === undefined ? '' : ` on line ${line}`}, got: ${JSON.stringify(problems.map((p) => [p.line, p.message]))}`,
        );
      }
      const cli = runCli(folderOf(name));
      assert.equal(cli.status, 1, cli.stderr);
      assert.match(cli.stderr, /problem\(s\) in 1 file\(s\)/);
    });
  }

  for (const [name] of accepted) {
    it(`accepts ${name} with exit 0 and no problems`, () => {
      assert.deepEqual(checkPaths([folderOf(name)]).problems, []);
      assert.equal(runCli(folderOf(name)).status, 0);
    });
  }

  it('accepts the same id in two different files', () => {
    const result = checkPaths([folderOf('same-id-in-two-files')]);
    assert.equal(result.files, 2);
    assert.deepEqual(result.problems, []);
    assert.equal(runCli(folderOf('same-id-in-two-files')).status, 0);
  });

  it('exits 0 for a folder without vectors', () => {
    assert.equal(runCli(folderOf('no-vectors')).status, 0);
  });

  it('exits 2 for a path that does not exist', () => {
    assert.equal(runCli(folderOf('yok-boyle-klasor')).status, 2);
  });

  it('exits 0 with no argument on the package folder', () => {
    const out = execFileSync(process.execPath, [script], { encoding: 'utf8' });
    assert.match(out, /test-vectors check/);
  });

  it('reports every duplicate key and lone surrogate of a line with scanStrings', () => {
    assert.deepEqual(scanStrings('{"a":1,"b":{"c":1},"c":2}'), []);
    assert.equal(scanStrings('{"a":1,"a":2,"b":{"c":1,"c":2}}').length, 2);
    assert.equal(scanStrings(String.raw`{"\ud800":1}`).length, 1);
  });

  it('checkBytes returns no problems for a clean buffer', () => {
    assert.deepEqual(checkBytes(Buffer.from(GOOD, 'utf8')), []);
  });
});

// Default scan mode (no argument): the checker scans its own package folder, which is the parent
// of scripts/. The tests copy the two scripts into a throw-away package folder under .tmp/ so
// the real mode runs against a controlled tree.
describe('test-vectors default scan (no argument)', () => {
  const fakeScratch = fileURLToPath(
    new URL('../../../.tmp/vektor-test-varsayilan/', import.meta.url),
  );

  /**
   * Builds a fake package folder and returns its path.
   * @param {string} name
   * @param {Record<string, string>} files relative path (forward slashes) -> content
   * @returns {string}
   */
  function fakePackage(name, files) {
    const root = join(fakeScratch, name);
    mkdirSync(join(root, 'scripts'), { recursive: true });
    copyFileSync(join(scriptsDir, 'check.mjs'), join(root, 'scripts', 'check.mjs'));
    copyFileSync(join(scriptsDir, 'check-lib.mjs'), join(root, 'scripts', 'check-lib.mjs'));
    for (const [path, content] of Object.entries(files)) {
      const target = join(root, ...path.split('/'));
      mkdirSync(join(target, '..'), { recursive: true });
      writeFileSync(target, content);
    }
    return root;
  }

  /**
   * @param {string} root
   * @returns {{ status: number, stdout: string, stderr: string }}
   */
  function runDefault(root) {
    const result = spawnSync(process.execPath, [join(root, 'scripts', 'check.mjs')], {
      encoding: 'utf8',
      cwd: root,
    });
    return { status: result.status ?? -1, stdout: result.stdout, stderr: result.stderr };
  }

  const scriptsDir = fileURLToPath(new URL('../scripts/', import.meta.url));
  const BAD = '{"id":"a"}\r\n';

  before(() => {
    rmSync(fakeScratch, { recursive: true, force: true });
  });

  after(() => {
    rmSync(fakeScratch, { recursive: true, force: true });
  });

  it('finds .jsonl files in nested vector folders and catches a broken one', () => {
    const root = fakePackage('nested-broken', {
      'normalize/tr.jsonl': GOOD,
      'anchors/valid.jsonl': GOOD,
      'anchors/deep/er/route.jsonl': GOOD + GOOD,
    });
    const result = runDefault(root);
    assert.equal(result.status, 1, result.stderr);
    assert.match(result.stderr, /route\.jsonl:2: duplicate id "a"/);
    assert.match(result.stderr, /1 problem\(s\) in 3 file\(s\)/);
  });

  it('catches a BOM or CRLF in a nested vector file', () => {
    const root = fakePackage('nested-crlf', { 'offsets/offsets.jsonl': BAD });
    const result = runDefault(root);
    assert.equal(result.status, 1, result.stderr);
    assert.match(result.stderr, /CR \(0x0D\) found/);
  });

  it('passes a clean tree and counts every vector file', () => {
    const root = fakePackage('clean-tree', {
      'normalize/tr.jsonl': GOOD,
      'normalize/ar.jsonl': GOOD,
      'fts-query/query.jsonl': GOOD,
    });
    const result = runDefault(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /3 file\(s\) OK/);
  });

  it('skips test, scripts, node_modules, dist and dot folders even when they hold broken files', () => {
    const root = fakePackage('skipped-folders', {
      'anchors/valid.jsonl': GOOD,
      'test/broken.jsonl': BAD,
      'scripts/broken.jsonl': BAD,
      'node_modules/pkg/broken.jsonl': BAD,
      'dist/broken.jsonl': BAD,
      '.hidden/broken.jsonl': BAD,
      'anchors/.cache/broken.jsonl': BAD,
    });
    const result = runDefault(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /1 file\(s\) OK/);
  });

  it('exits 0 with a notice when the tree holds no vector file at all', () => {
    const root = fakePackage('no-vectors', { 'test/broken.jsonl': BAD });
    const result = runDefault(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /no vector files found/);
  });

  it('does skip nothing when a folder is given explicitly', () => {
    const root = fakePackage('explicit-folder', { 'test/broken.jsonl': BAD });
    const result = spawnSync(
      process.execPath,
      [join(root, 'scripts', 'check.mjs'), join(root, 'test')],
      {
        encoding: 'utf8',
      },
    );
    assert.equal(result.status, 1, result.stderr);
  });
});
