import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { after, before, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  ANCHOR_ERRORS,
  VECTOR_KINDS,
  checkBytes,
  checkPaths,
  numberLiterals,
  scanStrings,
} from '../scripts/check-lib.mjs';

const script = fileURLToPath(new URL('../scripts/check.mjs', import.meta.url));
// Scratch folder inside the project (.tmp/ is git-ignored); removed after the run.
const scratch = fileURLToPath(new URL('../../../.tmp/vektor-test-birim/', import.meta.url));

const GOOD = '{"id":"a","input":"x","expected":"x"}\n';
const SECOND = '{"id":"b","input":"y","expected":"y"}\n';
const BOM = Buffer.from([0xef, 0xbb, 0xbf]);
// A line that passes the field rules of anchors/valid.jsonl (format only, see the field tests).
const ANCHOR_VALID_LINE =
  '{"id":"an-0001","input":"q:2:255","expected":{"ref":{"anchor":{"t":"q","sure":2,"ayet":255}},' +
  '"canonical":"q:2:255","unit":"q:2:255","unit_span":{"unit":"q:2:255"},' +
  '"ayahs":[{"sure":2,"ayet":255}]}}\n';

// Lines that pass the field rules of normalize/tr.jsonl and normalize/ar.jsonl.
const TR_LINE = '{"id":"tr-0001","input":"x","expected":{"dar":"x","genis":"x"}}\n';
const AR_LINE = '{"id":"ar-0001","input":"x","expected":""}\n';

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
  ['bom-mid-file', GOOD + '\uFEFF' + SECOND, [[/BOM \(U\+FEFF\) at the start of a line/, 2]]],
  ['crlf', '{"id":"a","input":"x","expected":"x"}\r\n', [[/CR \(0x0D\) found/]]],
  ['lone-cr-at-end', '{"id":"a"}\r', [[/CR \(0x0D\) found/], [/missing final newline/]]],
  ['lone-cr-between', '{"id":"a"}\r{"id":"b"}\n', [[/CR \(0x0D\) found/], [/invalid JSON/, 1]]],
  ['blank-line', GOOD + '\n' + SECOND, [[/blank line/, 2]]],
  ['u2028-only-line', GOOD + '\u2028\n' + SECOND, [[/blank line/, 2]]],
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
  [
    'arabic-and-turkish-utf8',
    JSON.stringify({ id: 't', input: 'I\u0307\u0130\u0131\u0628' }) + '\n',
  ],
  ['surrogate-pair-escaped', String.raw`{"id":"a","input":"\ud83d\ude00"}` + '\n'],
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

  // The real vector files are checked by the build task; this test only proves that the default
  // mode runs on the package folder, whatever state the vectors are in.
  it('runs with no argument on the package folder (exit 0 or 1, never a usage error)', () => {
    const result = spawnSync(process.execPath, [script], { encoding: 'utf8' });
    assert.ok(result.status === 0 || result.status === 1, result.stderr);
    assert.match(result.stdout + result.stderr, /test-vectors check/);
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
      'normalize/tr.jsonl': TR_LINE,
      'anchors/valid.jsonl': ANCHOR_VALID_LINE,
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
      'normalize/tr.jsonl': TR_LINE,
      'normalize/ar.jsonl': AR_LINE,
      'fts-query/query.jsonl': GOOD,
    });
    const result = runDefault(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /3 file\(s\) OK/);
  });

  it('skips test, scripts, node_modules, dist and dot folders even when they hold broken files', () => {
    const root = fakePackage('skipped-folders', {
      'anchors/valid.jsonl': ANCHOR_VALID_LINE,
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

// ---------------------------------------------------------------------------------------------
// Field rules of the recognized vector files (A04 vector specification 1-2). Fixture values only
// exercise the format; they are not the expectations of the real vectors. Texts are synthetic.
// ---------------------------------------------------------------------------------------------

/** @typedef {Record<string, any>} Row */

const V = 'anchors/valid.jsonl';
const I = 'anchors/invalid.jsonl';
const CM = 'anchors/compare.jsonl';
const CT = 'anchors/contains.jsonl';
const RO = 'anchors/route.jsonl';
const OF = 'offsets/offsets.jsonl';
const CH = 'content-hash/hash.jsonl';
const NT = 'normalize/tr.jsonl';
const NA = 'normalize/ar.jsonl';

/**
 * @param {string} text
 * @returns {string} SHA-256 of the UTF-8 bytes, lower-case hex
 */
function sha256(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

/**
 * @param {...Row} rows
 * @returns {string} JSONL text
 */
function jsonl(...rows) {
  return rows.map((row) => `${JSON.stringify(row)}\n`).join('');
}

/**
 * Copy of a row with the value at a dot path replaced; undefined deletes the key.
 * @param {Row} row
 * @param {string} path e.g. "expected.ref.span" or "expected.ayahs.0.ayet"
 * @param {unknown} value
 * @returns {Row}
 */
function patch(row, path, value) {
  const copy = structuredClone(row);
  const keys = path.split('.');
  const last = keys.pop() ?? '';
  let target = copy;
  for (const key of keys) {
    target = target[key];
  }
  if (value === undefined) {
    delete target[last];
  } else {
    target[last] = value;
  }
  return copy;
}

/** @type {Row} */
const anchorWords = {
  id: 'an-0001',
  input: 'q:2:255:3-7',
  expected: {
    ref: { anchor: { t: 'q', sure: 2, ayet: 255, ilk: 3, son: 7 } },
    canonical: 'q:2:255:3-7',
    unit: 'q:2:255',
    unit_span: { unit: 'q:2:255', span: [3, 8] },
    ayahs: [{ sure: 2, ayet: 255 }],
  },
};

/** @type {Row} */
const anchorSpan = {
  id: 'an-0007',
  input: 'rn:sozler:soz-10:hakikat-3:p4@120-184',
  expected: {
    ref: {
      anchor: { t: 'rn', yol: ['sozler', 'soz-10', 'hakikat-3'], p: 4 },
      span: { start: 120, end: 184 },
    },
    canonical: 'rn:sozler:soz-10:hakikat-3:p4@120-184',
    unit: 'rn:sozler:soz-10:hakikat-3:p4',
    unit_span: { unit: 'rn:sozler:soz-10:hakikat-3:p4', span: [120, 184] },
    ayahs: [],
  },
  note: 'Risale paragraf\u0131, kod noktas\u0131 aral\u0131\u011f\u0131',
};

/** @type {Row} */
const anchorAyahRange = {
  id: 'an-0008',
  input: 'q:2:255-257',
  expected: {
    ref: { anchor: { t: 'qa', sure: 2, ilk: 255, son: 257 } },
    canonical: 'q:2:255-257',
    unit: 'q:2:255-257',
    unit_span: null,
    ayahs: [
      { sure: 2, ayet: 255 },
      { sure: 2, ayet: 256 },
      { sure: 2, ayet: 257 },
    ],
  },
};

/** @type {Row} */
const invalidRow = { id: 'an-0002', input: 'q:2:255:7-3', expected: 'TERS_ARALIK' };
/** @type {Row} */
const compareRow = { id: 'cm-0001', input: ['q:2:255', 'q:2:256'], expected: -1 };
/** @type {Row} */
const containsRow = { id: 'ct-0001', input: ['q:2:255-257', 'q:2:256'], expected: true };
/** @type {Row} */
const routeRow = {
  id: 'ro-0001',
  input: { capa: 'q:2:255', sema: 'mutalaa-dev' },
  expected: { native: 'mutalaa-dev://q/2/255', web: '/kuran/2/255' },
};
/** @type {Row} */
const offsetsRow = {
  id: 'of-0002',
  input: 'a\u0302b',
  expected: {
    codepoints: 3,
    utf16: 3,
    cp_to_utf16: [
      [0, 0],
      [1, 1],
      [2, 2],
      [3, 3],
    ],
    snap: [{ in: [1, 2], out: [0, 2] }],
  },
  note: 'ayrismis Latin harf',
};
/** @type {Row} */
const hashRaw = {
  id: 'ch-0001',
  input: { text: 'Deneme', op: 'ham' },
  expected: { sha256: sha256('Deneme') },
};
/** @type {Row} */
const hashCanonical = {
  id: 'ch-0002',
  input: { text: '  Deneme\r\n', op: 'kanonik' },
  expected: { sha256: sha256('Deneme'), text: 'Deneme' },
};

/**
 * Recognized files that must pass: name, package-relative path, content.
 * @type {[string, string, string][]}
 */
const fieldAccepted = [
  ['valid-words-and-span', V, jsonl(anchorWords, anchorSpan)],
  ['valid-null-unit-span', V, jsonl(anchorAyahRange)],
  ['valid-unit-span-without-span', V, ANCHOR_VALID_LINE],
  [
    'valid-generated-ids-sort-after-numbers',
    V,
    jsonl(
      anchorWords,
      patch(anchorWords, 'id', 'an-s002-son'),
      patch(anchorWords, 'id', 'an-u-slug-64'),
    ),
  ],
  [
    'invalid-all-error-codes',
    I,
    jsonl(
      ...ANCHOR_ERRORS.map((code, index) => ({
        id: `an-01${index}`,
        input: `q:deneme:${index}`,
        expected: code,
      })),
    ),
  ],
  [
    'compare-all-results',
    CM,
    jsonl(
      compareRow,
      patch(compareRow, 'id', 'cm-0002'),
      patch(patch(compareRow, 'id', 'cm-0003'), 'expected', 1),
    ),
  ],
  ['compare-zero', CM, jsonl(patch(compareRow, 'expected', 0))],
  // "Z" (U+005A) sorts before "a" (U+0061) in code-unit order, unlike a Turkish collator.
  [
    'compare-code-unit-order',
    CM,
    jsonl(patch(compareRow, 'id', 'cm-Z'), patch(compareRow, 'id', 'cm-a')),
  ],
  [
    'contains-true-and-false',
    CT,
    jsonl(containsRow, patch(patch(containsRow, 'id', 'ct-0002'), 'expected', false)),
  ],
  [
    'route-web-string-null-and-absent',
    RO,
    jsonl(
      routeRow,
      {
        id: 'ro-0002',
        input: { capa: 'q:2:255:3' },
        expected: { native: 'mutalaa://q/2/255/3', web: null },
      },
      { id: 'ro-0003', input: { capa: 'q:2:255:3' }, expected: { native: 'mutalaa://q/2/255/3' } },
    ),
  ],
  [
    'offsets-full-minimal-and-astral',
    OF,
    jsonl(
      { id: 'of-0001', input: '', expected: { codepoints: 0, utf16: 0 } },
      offsetsRow,
      {
        id: 'of-0003',
        input: 'x\u{1D400}',
        expected: {
          codepoints: 2,
          utf16: 3,
          cp_to_utf16: [
            [0, 0],
            [1, 1],
            [2, 3],
          ],
        },
      },
      { id: 'of-0004', input: 'x', expected: { codepoints: 1, utf16: 1, snap: [] } },
    ),
  ],
  ['hash-ham-and-kanonik', CH, jsonl(hashRaw, hashCanonical)],
  [
    'hash-kanonik-empty-text',
    CH,
    jsonl(patch(patch(hashCanonical, 'expected.text', ''), 'expected.sha256', sha256(''))),
  ],
  // Files outside VECTOR_KINDS get the basic rules only: free keys, any order, any numbers.
  [
    'unknown-normalize-file',
    'normalize/tr-old.jsonl',
    '{"id":"tr-0002","input":"x","expected":{"dar":"x","genis":"x"},"extra":1.5}\n{"id":"tr-0001","input":"y"}\n',
  ],
  [
    'unknown-search-measurement-file',
    'arama/olcum.jsonl',
    '{"id":"o-2","kategori":"k","sorgu":"s","beklenen":["q:1:1"]}\n{"id":"o-1","kategori":"k","sorgu":"t","beklenen":[]}\n',
  ],
  ['unknown-fts-query-file', 'fts-query/query.jsonl', GOOD],
  ['unknown-nested-anchor-file', 'anchors/deep/valid.jsonl', GOOD],
  ['unknown-anchor-file-name', 'anchors/valid-old.jsonl', GOOD],
];

/**
 * Recognized files that must be rejected: name, path, content, every expected problem. The
 * problem count must match exactly, so one mistake yields one message (no cascades).
 * @type {[string, string, string, Expect[]][]}
 */
const fieldRejected = [
  // Rules shared by every recognized file.
  [
    'common-unknown-top-level-key',
    V,
    jsonl(patch(anchorWords, 'extra', 1)),
    [[/^unknown key "extra"$/, 1]],
  ],
  [
    'common-missing-input',
    CT,
    jsonl(patch(containsRow, 'input', undefined)),
    [[/^missing key "input"$/, 1]],
  ],
  [
    'common-missing-expected',
    OF,
    jsonl(patch(offsetsRow, 'expected', undefined)),
    [[/^missing key "expected"$/, 1]],
  ],
  [
    'common-note-not-string',
    CM,
    jsonl(patch(compareRow, 'note', 5)),
    [[/^note: must be a string, got 5$/, 1]],
  ],
  [
    'common-missing-id',
    I,
    jsonl(patch(invalidRow, 'id', undefined)),
    [[/^missing or empty string "id"$/, 1]],
  ],
  [
    'common-id-order',
    V,
    jsonl(anchorSpan, anchorWords),
    [[/^id "an-0001" is out of order: it sorts before "an-0007" \(line 1\)/, 2]],
  ],
  [
    'common-id-order-code-unit',
    CM,
    jsonl(patch(compareRow, 'id', 'cm-a'), patch(compareRow, 'id', 'cm-Z')),
    [[/^id "cm-Z" is out of order/, 2]],
  ],
  [
    'common-id-order-only-adjacent-inversion',
    CT,
    jsonl(
      patch(containsRow, 'id', 'ct-0001'),
      patch(containsRow, 'id', 'ct-0009'),
      patch(containsRow, 'id', 'ct-0002'),
      patch(containsRow, 'id', 'ct-0003'),
    ),
    [[/^id "ct-0002" is out of order: it sorts before "ct-0009" \(line 2\)/, 3]],
  ],
  [
    'common-duplicate-is-not-also-out-of-order',
    I,
    jsonl(invalidRow, patch(invalidRow, 'id', 'an-0003'), invalidRow),
    [[/^duplicate id "an-0002" \(first on line 1\)$/, 3]],
  ],
  [
    'common-basic-rules-still-apply',
    CM,
    `${JSON.stringify(compareRow)}\r\n`,
    [[/CR \(0x0D\) found/, 0]],
  ],
  [
    'common-float-literal',
    CM,
    '{"id":"cm-0001","input":["a","b"],"expected":1.0}\n',
    [[/^number 1\.0 is not a plain integer/, 1]],
  ],
  [
    'common-exponent-literal',
    V,
    jsonl(anchorSpan).replace('"end":184', '"end":1.84e2'),
    [[/^number 1\.84e2 is not a plain integer/, 1]],
  ],
  [
    'common-fraction',
    OF,
    jsonl(patch(offsetsRow, 'expected.utf16', 1.5)),
    [
      [/^number 1\.5 is not a plain integer/, 1],
      [/^expected\.utf16: must be a non-negative integer, got 1\.5$/, 1],
    ],
  ],
  [
    'common-unsafe-integer',
    OF,
    jsonl(offsetsRow).replace('"codepoints":3', '"codepoints":9007199254740993'),
    [[/^expected\.codepoints: must be a non-negative integer/, 1]],
  ],

  // anchors/valid.jsonl
  [
    'valid-input-not-string',
    V,
    jsonl(patch(anchorWords, 'input', 255)),
    [[/^input: must be a string, got 255$/, 1]],
  ],
  [
    'valid-expected-not-object',
    V,
    jsonl(patch(anchorWords, 'expected', 'q:2:255')),
    [[/^expected: must be an object, got "q:2:255"$/, 1]],
  ],
  [
    'valid-expected-missing-ref',
    V,
    jsonl(patch(anchorWords, 'expected.ref', undefined)),
    [[/^expected: missing key "ref"$/, 1]],
  ],
  [
    'valid-expected-missing-canonical',
    V,
    jsonl(patch(anchorWords, 'expected.canonical', undefined)),
    [[/^expected: missing key "canonical"$/, 1]],
  ],
  [
    'valid-expected-missing-unit',
    V,
    jsonl(patch(anchorWords, 'expected.unit', undefined)),
    [[/^expected: missing key "unit"$/, 1]],
  ],
  [
    'valid-expected-missing-unit-span',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span', undefined)),
    [[/^expected: missing key "unit_span"$/, 1]],
  ],
  [
    'valid-expected-missing-ayahs',
    V,
    jsonl(patch(anchorWords, 'expected.ayahs', undefined)),
    [[/^expected: missing key "ayahs"$/, 1]],
  ],
  [
    'valid-expected-unknown-key',
    V,
    jsonl(patch(anchorWords, 'expected.parsed', true)),
    [[/^expected: unknown key "parsed"$/, 1]],
  ],
  [
    'valid-canonical-not-string',
    V,
    jsonl(patch(anchorWords, 'expected.canonical', null)),
    [[/^expected\.canonical: must be a string, got null$/, 1]],
  ],
  [
    'valid-unit-not-string',
    V,
    jsonl(patch(anchorWords, 'expected.unit', ['q:2:255'])),
    [[/^expected\.unit: must be a string, got an array$/, 1]],
  ],
  [
    'valid-ref-not-object',
    V,
    jsonl(patch(anchorWords, 'expected.ref', 'q:2:255:3-7')),
    [[/^expected\.ref: must be an object/, 1]],
  ],
  [
    'valid-ref-missing-anchor',
    V,
    jsonl(patch(anchorWords, 'expected.ref', {})),
    [[/^expected\.ref: missing key "anchor"$/, 1]],
  ],
  [
    'valid-ref-unknown-key',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.aralik', [120, 184])),
    [[/^expected\.ref: unknown key "aralik"$/, 1]],
  ],
  [
    'valid-anchor-not-object',
    V,
    jsonl(patch(anchorWords, 'expected.ref.anchor', 'q')),
    [[/^expected\.ref\.anchor: must be an object, got "q"$/, 1]],
  ],
  [
    'valid-anchor-missing-t',
    V,
    jsonl(patch(anchorWords, 'expected.ref.anchor.t', undefined)),
    [[/^expected\.ref\.anchor: missing key "t"$/, 1]],
  ],
  [
    'valid-anchor-t-not-string',
    V,
    jsonl(patch(anchorWords, 'expected.ref.anchor.t', 1)),
    [[/^expected\.ref\.anchor\.t: must be a string, got 1$/, 1]],
  ],
  [
    'valid-span-negative',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.span.start', -1)),
    [[/^expected\.ref\.span\.start: must be a non-negative integer, got -1$/, 1]],
  ],
  [
    'valid-span-end-string',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.span.end', '184')),
    [[/^expected\.ref\.span\.end: must be a non-negative integer, got "184"$/, 1]],
  ],
  [
    'valid-span-missing-end',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.span.end', undefined)),
    [[/^expected\.ref\.span: missing key "end"$/, 1]],
  ],
  [
    'valid-span-unknown-key',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.span.len', 64)),
    [[/^expected\.ref\.span: unknown key "len"$/, 1]],
  ],
  [
    'valid-span-as-array',
    V,
    jsonl(patch(anchorSpan, 'expected.ref.span', [120, 184])),
    [[/^expected\.ref\.span: must be an object, got an array$/, 1]],
  ],
  [
    'valid-unit-span-string',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span', 'q:2:255')),
    [[/^expected\.unit_span: must be an object or null, got "q:2:255"$/, 1]],
  ],
  [
    'valid-unit-span-missing-unit',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span.unit', undefined)),
    [[/^expected\.unit_span: missing key "unit"$/, 1]],
  ],
  [
    'valid-unit-span-unknown-key',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span.kind', 'q')),
    [[/^expected\.unit_span: unknown key "kind"$/, 1]],
  ],
  [
    'valid-unit-span-three-items',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span.span', [3, 8, 9])),
    [
      [
        /^expected\.unit_span\.span: must be an array of 2 non-negative integers, got 3 item\(s\)$/,
        1,
      ],
    ],
  ],
  [
    'valid-unit-span-object-span',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span.span', { start: 3, end: 8 })),
    [
      [
        /^expected\.unit_span\.span: must be an array of 2 non-negative integers, got an object$/,
        1,
      ],
    ],
  ],
  [
    'valid-unit-span-negative',
    V,
    jsonl(patch(anchorWords, 'expected.unit_span.span', [-3, 8])),
    [[/^expected\.unit_span\.span\[0\]: must be a non-negative integer, got -3$/, 1]],
  ],
  [
    'valid-ayahs-not-array',
    V,
    jsonl(patch(anchorWords, 'expected.ayahs', {})),
    [[/^expected\.ayahs: must be an array, got an object$/, 1]],
  ],
  [
    'valid-ayahs-item-string',
    V,
    jsonl(patch(anchorWords, 'expected.ayahs', ['2:255'])),
    [[/^expected\.ayahs\[0\]: must be an object, got "2:255"$/, 1]],
  ],
  [
    'valid-ayahs-zero',
    V,
    jsonl(patch(anchorAyahRange, 'expected.ayahs.2.ayet', 0)),
    [[/^expected\.ayahs\[2\]\.ayet: must be a positive integer, got 0$/, 1]],
  ],
  [
    'valid-ayahs-missing-sure',
    V,
    jsonl(patch(anchorWords, 'expected.ayahs.0.sure', undefined)),
    [[/^expected\.ayahs\[0\]: missing key "sure"$/, 1]],
  ],
  [
    'valid-ayahs-unknown-key',
    V,
    jsonl(patch(anchorWords, 'expected.ayahs.0.kelime', 3)),
    [[/^expected\.ayahs\[0\]: unknown key "kelime"$/, 1]],
  ],
  [
    'valid-several-problems-on-one-line',
    V,
    jsonl(patch(patch(anchorWords, 'expected.unit', 1), 'expected.ayahs', null)),
    [
      [/^expected\.unit: must be a string, got 1$/, 1],
      [/^expected\.ayahs: must be an array, got null$/, 1],
    ],
  ],

  // anchors/invalid.jsonl
  [
    'invalid-unknown-code',
    I,
    jsonl(patch(invalidRow, 'expected', 'GECERSIZ')),
    [
      [
        /^expected: must be one of "BICIM", "SURE_ARALIGI", "AYET_ARALIGI", "TERS_ARALIK", "KANONIK_DEGIL", "UZUNLUK", got "GECERSIZ"$/,
        1,
      ],
    ],
  ],
  [
    'invalid-lower-case-code',
    I,
    jsonl(patch(invalidRow, 'expected', 'ters_aralik')),
    [[/^expected: must be one of .*got "ters_aralik"$/, 1]],
  ],
  [
    'invalid-code-as-object',
    I,
    jsonl(patch(invalidRow, 'expected', { code: 'TERS_ARALIK' })),
    [[/^expected: must be one of .*got an object$/, 1]],
  ],
  [
    'invalid-input-not-string',
    I,
    jsonl(patch(invalidRow, 'input', null)),
    [[/^input: must be a string, got null$/, 1]],
  ],

  // anchors/compare.jsonl
  [
    'compare-one-input',
    CM,
    jsonl(patch(compareRow, 'input', ['q:2:255'])),
    [[/^input: must be an array of 2 strings, got 1 item\(s\)$/, 1]],
  ],
  [
    'compare-three-inputs',
    CM,
    jsonl(patch(compareRow, 'input', ['a', 'b', 'c'])),
    [[/^input: must be an array of 2 strings, got 3 item\(s\)$/, 1]],
  ],
  [
    'compare-input-not-array',
    CM,
    jsonl(patch(compareRow, 'input', 'q:2:255 q:2:256')),
    [[/^input: must be an array of 2 strings, got "q:2:255 q:2:256"$/, 1]],
  ],
  [
    'compare-input-number',
    CM,
    jsonl(patch(compareRow, 'input', ['q:2:255', 2])),
    [[/^input\[1\]: must be a string, got 2$/, 1]],
  ],
  [
    'compare-expected-two',
    CM,
    jsonl(patch(compareRow, 'expected', 2)),
    [[/^expected: must be one of -1, 0, 1, got 2$/, 1]],
  ],
  [
    'compare-expected-string',
    CM,
    jsonl(patch(compareRow, 'expected', '0')),
    [[/^expected: must be one of -1, 0, 1, got "0"$/, 1]],
  ],
  [
    'compare-expected-boolean',
    CM,
    jsonl(patch(compareRow, 'expected', true)),
    [[/^expected: must be one of -1, 0, 1, got true$/, 1]],
  ],

  // anchors/contains.jsonl
  [
    'contains-expected-string',
    CT,
    jsonl(patch(containsRow, 'expected', 'true')),
    [[/^expected: must be a boolean, got "true"$/, 1]],
  ],
  [
    'contains-expected-number',
    CT,
    jsonl(patch(containsRow, 'expected', 1)),
    [[/^expected: must be a boolean, got 1$/, 1]],
  ],
  [
    'contains-input-object',
    CT,
    jsonl(patch(containsRow, 'input', { dis: 'a', ic: 'b' })),
    [[/^input: must be an array of 2 strings, got an object$/, 1]],
  ],

  // anchors/route.jsonl
  [
    'route-input-string',
    RO,
    jsonl(patch(routeRow, 'input', 'q:2:255')),
    [[/^input: must be an object, got "q:2:255"$/, 1]],
  ],
  [
    'route-missing-capa',
    RO,
    jsonl(patch(routeRow, 'input.capa', undefined)),
    [[/^input: missing key "capa"$/, 1]],
  ],
  [
    'route-sema-not-string',
    RO,
    jsonl(patch(routeRow, 'input.sema', null)),
    [[/^input\.sema: must be a string, got null$/, 1]],
  ],
  [
    'route-unknown-input-key',
    RO,
    jsonl(patch(routeRow, 'input.scheme', 'mutalaa')),
    [[/^input: unknown key "scheme"$/, 1]],
  ],
  [
    'route-missing-native',
    RO,
    jsonl(patch(routeRow, 'expected.native', undefined)),
    [[/^expected: missing key "native"$/, 1]],
  ],
  [
    'route-native-not-string',
    RO,
    jsonl(patch(routeRow, 'expected.native', null)),
    [[/^expected\.native: must be a string, got null$/, 1]],
  ],
  [
    'route-web-number',
    RO,
    jsonl(patch(routeRow, 'expected.web', 1)),
    [[/^expected\.web: must be a string or null, got 1$/, 1]],
  ],
  [
    'route-unknown-expected-key',
    RO,
    jsonl(patch(routeRow, 'expected.deeplink', 'x')),
    [[/^expected: unknown key "deeplink"$/, 1]],
  ],

  // offsets/offsets.jsonl
  [
    'offsets-input-not-string',
    OF,
    jsonl(patch(offsetsRow, 'input', 3)),
    [[/^input: must be a string, got 3$/, 1]],
  ],
  [
    'offsets-missing-codepoints',
    OF,
    jsonl(patch(offsetsRow, 'expected.codepoints', undefined)),
    [[/^expected: missing key "codepoints"$/, 1]],
  ],
  [
    'offsets-missing-utf16',
    OF,
    jsonl(patch(offsetsRow, 'expected.utf16', undefined)),
    [[/^expected: missing key "utf16"$/, 1]],
  ],
  [
    'offsets-utf16-negative',
    OF,
    jsonl(patch(offsetsRow, 'expected.utf16', -1)),
    [[/^expected\.utf16: must be a non-negative integer, got -1$/, 1]],
  ],
  [
    'offsets-unknown-key',
    OF,
    jsonl(patch(offsetsRow, 'expected.length', 3)),
    [[/^expected: unknown key "length"$/, 1]],
  ],
  [
    'offsets-cp-to-utf16-not-array',
    OF,
    jsonl(patch(offsetsRow, 'expected.cp_to_utf16', {})),
    [[/^expected\.cp_to_utf16: must be an array, got an object$/, 1]],
  ],
  [
    'offsets-cp-to-utf16-three-items',
    OF,
    jsonl(patch(offsetsRow, 'expected.cp_to_utf16.1', [1, 1, 1])),
    [
      [
        /^expected\.cp_to_utf16\[1\]: must be an array of 2 non-negative integers, got 3 item\(s\)$/,
        1,
      ],
    ],
  ],
  [
    'offsets-cp-to-utf16-string',
    OF,
    jsonl(patch(offsetsRow, 'expected.cp_to_utf16.0.1', '0')),
    [[/^expected\.cp_to_utf16\[0\]\[1\]: must be a non-negative integer, got "0"$/, 1]],
  ],
  [
    'offsets-snap-not-array',
    OF,
    jsonl(patch(offsetsRow, 'expected.snap', { in: [1, 2], out: [0, 2] })),
    [[/^expected\.snap: must be an array, got an object$/, 1]],
  ],
  [
    'offsets-snap-missing-out',
    OF,
    jsonl(patch(offsetsRow, 'expected.snap.0.out', undefined)),
    [[/^expected\.snap\[0\]: missing key "out"$/, 1]],
  ],
  [
    'offsets-snap-unknown-key',
    OF,
    jsonl(patch(offsetsRow, 'expected.snap.0.kind', 'mn')),
    [[/^expected\.snap\[0\]: unknown key "kind"$/, 1]],
  ],
  [
    'offsets-snap-in-negative',
    OF,
    jsonl(patch(offsetsRow, 'expected.snap.0.in.0', -1)),
    [[/^expected\.snap\[0\]\.in\[0\]: must be a non-negative integer, got -1$/, 1]],
  ],
  [
    'offsets-snap-out-one-item',
    OF,
    jsonl(patch(offsetsRow, 'expected.snap.0.out', [0])),
    [
      [
        /^expected\.snap\[0\]\.out: must be an array of 2 non-negative integers, got 1 item\(s\)$/,
        1,
      ],
    ],
  ],

  // content-hash/hash.jsonl
  [
    'hash-input-string',
    CH,
    jsonl(patch(hashRaw, 'input', 'Deneme')),
    [[/^input: must be an object, got "Deneme"$/, 1]],
  ],
  [
    'hash-op-unknown',
    CH,
    jsonl(patch(hashRaw, 'input.op', 'NFC')),
    [[/^input\.op: must be one of "ham", "kanonik", got "NFC"$/, 1]],
  ],
  [
    'hash-missing-op',
    CH,
    jsonl(patch(hashRaw, 'input.op', undefined)),
    [[/^input: missing key "op"$/, 1]],
  ],
  [
    'hash-missing-text',
    CH,
    jsonl(patch(hashRaw, 'input.text', undefined)),
    [[/^input: missing key "text"$/, 1]],
  ],
  [
    'hash-input-text-not-string',
    CH,
    jsonl(patch(hashRaw, 'input.text', 5)),
    [[/^input\.text: must be a string, got 5$/, 1]],
  ],
  [
    'hash-unknown-input-key',
    CH,
    jsonl(patch(hashRaw, 'input.normalize', true)),
    [[/^input: unknown key "normalize"$/, 1]],
  ],
  [
    'hash-missing-sha256',
    CH,
    jsonl(patch(hashRaw, 'expected.sha256', undefined)),
    [[/^expected: missing key "sha256"$/, 1]],
  ],
  [
    'hash-sha256-upper-case',
    CH,
    jsonl(patch(hashRaw, 'expected.sha256', sha256('Deneme').toUpperCase())),
    // Long values are cut to 37 code points plus "..." in messages.
    [[/^expected\.sha256: must be 64 lower-case hex digits, got "[0-9A-F]{36}\.\.\.$/, 1]],
  ],
  [
    'hash-sha256-63-digits',
    CH,
    jsonl(patch(hashRaw, 'expected.sha256', sha256('Deneme').slice(1))),
    [[/^expected\.sha256: must be 64 lower-case hex digits/, 1]],
  ],
  [
    'hash-sha256-number',
    CH,
    jsonl(patch(hashRaw, 'expected.sha256', 0)),
    [[/^expected\.sha256: must be 64 lower-case hex digits, got 0$/, 1]],
  ],
  [
    'hash-unknown-expected-key',
    CH,
    jsonl(patch(hashRaw, 'expected.md5', 'x')),
    [[/^expected: unknown key "md5"$/, 1]],
  ],
  [
    'hash-kanonik-without-text',
    CH,
    jsonl(patch(hashCanonical, 'expected.text', undefined)),
    [[/^expected: missing key "text" \(required when input\.op is "kanonik"\)$/, 1]],
  ],
  [
    'hash-ham-with-text',
    CH,
    jsonl(patch(hashRaw, 'expected.text', 'Deneme')),
    [[/^expected\.text: only allowed when input\.op is "kanonik"$/, 1]],
  ],
  [
    'hash-kanonik-text-not-string',
    CH,
    jsonl(patch(hashCanonical, 'expected.text', null)),
    [[/^expected\.text: must be a string, got null$/, 1]],
  ],
];

// ---------------------------------------------------------------------------------------------
// normalize/tr.jsonl and normalize/ar.jsonl (A05.2): closed expected object / string, the escape
// rule and the key invariants. Lines that carry escapes are written with String.raw so that the
// file holds the backslash sequences (JSON.stringify would write the marks raw).
// ---------------------------------------------------------------------------------------------

/** @type {Row} */
const trRow = {
  id: 'tr-0001',
  input: 'Işık',
  expected: { dar: 'ışık', genis: 'isik' },
  note: 'I → ı',
};
/** @type {Row} */
const arRow = { id: 'ar-0001', input: String.raw`\u0628\u064b\u0628`, expected: 'x' };

/**
 * A normalize/tr line with the given raw text for input, expected.dar, expected.genis and note
 * (written as is, so escapes stay escapes).
 * @param {string} input
 * @param {string} dar
 * @param {string} genis
 * @param {string} [note]
 * @returns {string}
 */
function trText(input, dar, genis, note = '') {
  const tail = note === '' ? '' : `,"note":"${note}"`;
  return `{"id":"tr-0001","input":"${input}","expected":{"dar":"${dar}","genis":"${genis}"}${tail}}\n`;
}

/**
 * @param {string} input
 * @param {string} expected
 * @param {string} [note]
 * @returns {string}
 */
function arText(input, expected, note = '') {
  const tail = note === '' ? '' : `,"note":"${note}"`;
  return `{"id":"ar-0001","input":"${input}","expected":"${expected}"${tail}}\n`;
}

/** @type {[string, string, string][]} */
const normalizeAccepted = [
  ['normalize-tr-minimal', NT, jsonl(trRow)],
  ['normalize-tr-escaped-combining-mark', NT, trText(String.raw`a\u0302lem`, 'âlem', 'alem')],
  [
    'normalize-tr-escaped-astral-pair',
    NT,
    trText(String.raw`\ud801\udc00`, String.raw`\ud801\udc28`, String.raw`\ud801\udc28`),
  ],
  ['normalize-tr-empty-keys', NT, trText('', '', '')],
  ['normalize-tr-whitespace-only-input', NT, trText('   ', '', '')],
  ['normalize-tr-equal-word-counts', NT, trText('Âl-i İmrân', 'âl i imrân', 'al i imran')],
  // Raw characters outside the escaped categories stay raw: Latin and Greek letters, No, Nl, Pi/Pf, Sm.
  ['normalize-tr-raw-letters-and-symbols', NT, trText('«½ ⅻ ΟΔΟΣ ß»', 'x', 'x', 'a → b')],
  // Only U+0300-U+036F is folded away in the wide key: Me (U+20DD) and other marks may stay.
  [
    'normalize-tr-wide-keeps-enclosing-mark',
    NT,
    trText('a', String.raw`a\u20dd`, String.raw`a\u20dd`),
  ],
  ['normalize-tr-dar-may-hold-dotless-i', NT, trText('x', 'ışık', 'isik')],
  ['normalize-tr-dar-may-hold-combining-mark', NT, trText('x', String.raw`i\u0307`, 'i')],
  [
    'normalize-tr-raw-space-and-escaped-nbsp',
    NT,
    trText(String.raw`Deneme\u00a0metni`, 'deneme metni', 'deneme metni'),
  ],
  ['normalize-ar-minimal', NA, jsonl(arRow)],
  [
    'normalize-ar-escaped-letters',
    NA,
    arText(String.raw`\u0628\u064b\u0628`, String.raw`\u0628\u0628`),
  ],
  ['normalize-ar-empty-expected', NA, arText('', '')],
  [
    'normalize-ar-latin-and-single-space',
    NA,
    arText(String.raw`abc \u0628`, String.raw`\u0628 \u062a`),
  ],
  ['normalize-ar-raw-guillemets', NA, arText(String.raw`«\u0628»`, String.raw`\u0628`)],
  [
    'normalize-ar-two-ids-in-order',
    NA,
    `${arText('', '')}${arText('', '').replace('ar-0001', 'ar-0002')}`,
  ],
  // The escape rule belongs to the normalize files; other recognized files are not held to it.
  ['escape-rule-not-applied-to-offsets', OF, jsonl(offsetsRow)],
];

/**
 * A raw (unescaped) character inside the input of a normalize/tr line.
 * @param {string} name
 * @param {string} ch
 * @param {RegExp} message
 * @returns {[string, string, string, Expect[]]}
 */
function rawInTr(name, ch, message) {
  return [name, NT, trText(`a${ch}b`, 'x', 'x'), [[message, 1]]];
}

/** @type {[string, string, string, Expect[]][]} */
const normalizeRejected = [
  // Field shapes of normalize/tr.
  [
    'normalize-tr-expected-string',
    NT,
    jsonl(patch(trRow, 'expected', 'x')),
    [[/^expected: must be an object, got "x"$/, 1]],
  ],
  [
    'normalize-tr-missing-genis',
    NT,
    jsonl(patch(trRow, 'expected.genis', undefined)),
    [[/^expected: missing key "genis"$/, 1]],
  ],
  [
    'normalize-tr-missing-dar',
    NT,
    jsonl(patch(trRow, 'expected.dar', undefined)),
    [[/^expected: missing key "dar"$/, 1]],
  ],
  [
    'normalize-tr-unknown-expected-key',
    NT,
    jsonl(patch(trRow, 'expected.stem', 'isik')),
    [[/^expected: unknown key "stem"$/, 1]],
  ],
  [
    'normalize-tr-dar-not-string',
    NT,
    jsonl(patch(trRow, 'expected.dar', 5)),
    [[/^expected\.dar: must be a string, got 5$/, 1]],
  ],
  [
    'normalize-tr-genis-null',
    NT,
    jsonl(patch(trRow, 'expected.genis', null)),
    [[/^expected\.genis: must be a string, got null$/, 1]],
  ],
  [
    'normalize-tr-input-not-string',
    NT,
    jsonl(patch(trRow, 'input', ['Işık'])),
    [[/^input: must be a string, got an array$/, 1]],
  ],
  // Spaces of the keys.
  [
    'normalize-tr-dar-leading-space',
    NT,
    jsonl(patch(trRow, 'expected.dar', ' ışık')),
    [[/^expected\.dar: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-tr-dar-trailing-space',
    NT,
    jsonl(patch(trRow, 'expected.dar', 'ışık ')),
    [[/^expected\.dar: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-tr-genis-leading-space',
    NT,
    jsonl(patch(trRow, 'expected.genis', ' isik')),
    [[/^expected\.genis: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-tr-genis-trailing-space',
    NT,
    jsonl(patch(trRow, 'expected.genis', 'isik ')),
    [[/^expected\.genis: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-tr-dar-single-space-only',
    NT,
    jsonl(patch(patch(trRow, 'expected.dar', ' '), 'expected.genis', '')),
    [[/^expected\.dar: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-tr-dar-double-space',
    NT,
    jsonl(patch(patch(trRow, 'expected.dar', 'a  b'), 'expected.genis', 'a b')),
    [[/^expected\.dar: must not contain two U\+0020 in a row$/, 1]],
  ],
  [
    'normalize-tr-genis-double-space',
    NT,
    jsonl(patch(patch(trRow, 'expected.dar', 'a b'), 'expected.genis', 'a  b')),
    [[/^expected\.genis: must not contain two U\+0020 in a row$/, 1]],
  ],
  // The wide key is folded.
  [
    'normalize-tr-genis-has-combining-circumflex',
    NT,
    trText('x', 'x', String.raw`a\u0302`),
    [[/^expected\.genis: must not contain a character of U\+0300-U\+036F$/, 1]],
  ],
  [
    'normalize-tr-genis-has-first-of-range',
    NT,
    trText('x', 'x', String.raw`a\u0300`),
    [[/^expected\.genis: must not contain a character of U\+0300-U\+036F$/, 1]],
  ],
  [
    'normalize-tr-genis-has-last-of-range',
    NT,
    trText('x', 'x', String.raw`a\u036f`),
    [[/^expected\.genis: must not contain a character of U\+0300-U\+036F$/, 1]],
  ],
  [
    'normalize-tr-genis-has-dotless-i',
    NT,
    jsonl(patch(trRow, 'expected.genis', 'ışik')),
    [[/^expected\.genis: must not contain dotless i \(U\+0131\)$/, 1]],
  ],
  // Same number of words.
  [
    'normalize-tr-word-counts-differ',
    NT,
    jsonl(patch(patch(trRow, 'expected.dar', 'a b'), 'expected.genis', 'a')),
    [
      [
        /^expected: dar has 2 word\(s\) but genis has 1 \(both keys must have the same number\)$/,
        1,
      ],
    ],
  ],
  [
    'normalize-tr-empty-dar-nonempty-genis',
    NT,
    jsonl(patch(patch(trRow, 'expected.dar', ''), 'expected.genis', 'a')),
    [[/^expected: dar has 0 word\(s\) but genis has 1 /, 1]],
  ],
  // Field shapes and spaces of normalize/ar.
  [
    'normalize-ar-expected-object',
    NA,
    jsonl(patch(arRow, 'expected', { dar: 'x', genis: 'x' })),
    [[/^expected: must be a string, got an object$/, 1]],
  ],
  [
    'normalize-ar-expected-number',
    NA,
    jsonl(patch(arRow, 'expected', 3)),
    [[/^expected: must be a string, got 3$/, 1]],
  ],
  [
    'normalize-ar-missing-expected',
    NA,
    jsonl(patch(arRow, 'expected', undefined)),
    [[/^missing key "expected"$/, 1]],
  ],
  [
    'normalize-ar-input-not-string',
    NA,
    jsonl(patch(arRow, 'input', 1)),
    [[/^input: must be a string, got 1$/, 1]],
  ],
  [
    'normalize-ar-leading-space',
    NA,
    arText('', ' a'),
    [[/^expected: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-ar-trailing-space',
    NA,
    arText('', 'a '),
    [[/^expected: must not start or end with U\+0020$/, 1]],
  ],
  [
    'normalize-ar-double-space',
    NA,
    arText('', 'a  b'),
    [[/^expected: must not contain two U\+0020 in a row$/, 1]],
  ],
  // Escape rule: one message per distinct code point of a line, with the escape to write.
  rawInTr('escape-raw-mn', '\u0301', /^raw U\+0301 \(Mn\) must be written as \\u0301$/),
  rawInTr('escape-raw-mc', '\u0903', /^raw U\+0903 \(Mc\) must be written as \\u0903$/),
  rawInTr('escape-raw-me', '\u20dd', /^raw U\+20DD \(Me\) must be written as \\u20dd$/),
  rawInTr('escape-raw-cc-del', '\u007f', /^raw U\+007F \(Cc\) must be written as \\u007f$/),
  rawInTr('escape-raw-cf-zwsp', '\u200b', /^raw U\+200B \(Cf\) must be written as \\u200b$/),
  rawInTr('escape-raw-cf-soft-hyphen', '\u00ad', /^raw U\+00AD \(Cf\) must be written as \\u00ad$/),
  rawInTr('escape-raw-zl', '\u2028', /^raw U\+2028 \(Zl\) must be written as \\u2028$/),
  rawInTr('escape-raw-zp', '\u2029', /^raw U\+2029 \(Zp\) must be written as \\u2029$/),
  rawInTr('escape-raw-zs-nbsp', '\u00a0', /^raw U\+00A0 \(Zs\) must be written as \\u00a0$/),
  rawInTr(
    'escape-raw-zs-ideographic-space',
    '\u3000',
    /^raw U\+3000 \(Zs\) must be written as \\u3000$/,
  ),
  rawInTr('escape-raw-co', '\ue000', /^raw U\+E000 \(Co\) must be written as \\ue000$/),
  rawInTr('escape-raw-cn', '\u0378', /^raw U\+0378 \(Cn\) must be written as \\u0378$/),
  rawInTr(
    'escape-raw-astral-letter',
    '\u{1d400}',
    /^raw U\+1D400 \(outside the BMP\) must be written as \\ud835\\udc00$/,
  ),
  rawInTr(
    'escape-raw-astral-emoji',
    '\u{1f600}',
    /^raw U\+1F600 \(outside the BMP\) must be written as \\ud83d\\ude00$/,
  ),
  rawInTr(
    'escape-raw-astral-cf',
    '\u{e0001}',
    /^raw U\+E0001 \(outside the BMP\) must be written as \\udb40\\udc01$/,
  ),
  // The Arabic blocks, both ends of each (all five blocks of Arama 1.1).
  ...[0x0600, 0x06ff, 0x0750, 0x077f, 0x08a0, 0x08ff, 0xfb50, 0xfdff, 0xfe70, 0xfeff].map((cp) => {
    const hex = cp.toString(16).padStart(4, '0');
    return rawInTr(
      `escape-raw-arabic-block-edge-${hex}`,
      String.fromCodePoint(cp),
      new RegExp(
        `^raw U\\+${hex.toUpperCase()} \\(Arabic block\\) must be written as \\\\u${hex}$`,
      ),
    );
  }),
  [
    'escape-raw-arabic-letter-in-ar-input',
    NA,
    arText('\u0628', 'x'),
    [[/^raw U\+0628 \(Arabic block\) must be written as \\u0628$/, 1]],
  ],
  [
    'escape-raw-arabic-letter-in-ar-expected',
    NA,
    arText('x', '\u0628'),
    [[/^raw U\+0628 \(Arabic block\) must be written as \\u0628$/, 1]],
  ],
  [
    'escape-raw-mark-in-ar-input',
    NA,
    arText('\u0301', 'x'),
    [[/^raw U\+0301 \(Mn\) must be written as \\u0301$/, 1]],
  ],
  // Input, expected and note are all covered.
  [
    'escape-raw-mn-in-dar',
    NT,
    trText('x', 'a\u0301', 'a'),
    [[/^raw U\+0301 \(Mn\) must be written as \\u0301$/, 1]],
  ],
  [
    'escape-raw-mn-in-note',
    NT,
    trText('x', 'x', 'x', 'a\u0301'),
    [[/^raw U\+0301 \(Mn\) must be written as \\u0301$/, 1]],
  ],
  [
    'escape-raw-mn-in-ar-note',
    NA,
    arText('x', 'x', 'a\u0301'),
    [[/^raw U\+0301 \(Mn\) must be written as \\u0301$/, 1]],
  ],
  // The same code point twice in a line is reported once; two different ones twice.
  [
    'escape-same-code-point-reported-once',
    NT,
    trText('a\u0301b\u0301', 'a\u0301', 'a'),
    [[/^raw U\+0301 \(Mn\) must be written as \\u0301$/, 1]],
  ],
  [
    'escape-two-code-points-reported-twice',
    NT,
    trText('a\u0301\u0302', 'x', 'x'),
    [
      [/^raw U\+0301 \(Mn\) /, 1],
      [/^raw U\+0302 \(Mn\) /, 1],
    ],
  ],
  // Each line is judged on its own: the clean first line does not hide the second.
  [
    'escape-reported-on-the-right-line',
    NT,
    `${trText('x', 'x', 'x')}${trText('a\u0301', 'x', 'x').replace('tr-0001', 'tr-0002')}`,
    [[/^raw U\+0301 \(Mn\) /, 2]],
  ],
  // A bad shape and a raw mark in the same line give both messages.
  [
    'escape-and-field-problem-together',
    NT,
    trText('a\u0301', 'x', 'xx yy'),
    [
      [/^raw U\+0301 \(Mn\) /, 1],
      [/^expected: dar has 1 word\(s\) but genis has 2 /, 1],
    ],
  ],
];

fieldAccepted.push(...normalizeAccepted);
fieldRejected.push(...normalizeRejected);

describe('test-vectors field checks (recognized files)', () => {
  const fieldScratch = fileURLToPath(new URL('../../../.tmp/vektor-test-alan/', import.meta.url));

  /**
   * @param {string} name
   * @returns {string} folder of one case, laid out like the package root
   */
  function caseFolder(name) {
    return join(fieldScratch, name);
  }

  /**
   * @param {string} name
   * @param {Record<string, string>} files package-relative path -> content
   */
  function writeCase(name, files) {
    for (const [path, content] of Object.entries(files)) {
      const target = join(caseFolder(name), ...path.split('/'));
      mkdirSync(join(target, '..'), { recursive: true });
      writeFileSync(target, content);
    }
  }

  const sharedValid = jsonl(anchorWords, patch(anchorWords, 'id', 'an-0003'), anchorSpan);
  const sharedInvalid = jsonl(invalidRow, patch(invalidRow, 'id', 'an-0003'));

  before(() => {
    rmSync(fieldScratch, { recursive: true, force: true });
    for (const [name, path, content] of [...fieldAccepted, ...fieldRejected]) {
      writeCase(name, { [path]: content });
    }
    writeCase('shared-ids-distinct', {
      [V]: jsonl(anchorWords, anchorSpan),
      [I]: jsonl(invalidRow, patch(invalidRow, 'id', 'an-0003')),
    });
    writeCase('shared-ids-collide', { [V]: sharedValid, [I]: sharedInvalid });
    // Same id in valid of one package root and invalid of another: no collision.
    writeCase('shared-ids-package-a', { [V]: sharedValid });
    writeCase('shared-ids-package-b', { [I]: sharedInvalid });
    // Same id in compare and contains: ids are unique per file only.
    writeCase('shared-ids-other-files', {
      [CM]: jsonl(patch(compareRow, 'id', 'x-1')),
      [CT]: jsonl(patch(containsRow, 'id', 'x-1')),
    });
  });

  after(() => {
    rmSync(fieldScratch, { recursive: true, force: true });
  });

  it('recognizes exactly the nine files of the specification', () => {
    assert.deepEqual([...VECTOR_KINDS].sort(), [CM, CT, I, RO, V, CH, OF, NT, NA].sort());
  });

  for (const [name] of fieldAccepted) {
    it(`accepts ${name}`, () => {
      assert.deepEqual(checkPaths([caseFolder(name)]).problems, []);
    });
  }

  for (const [name, , , expectations] of fieldRejected) {
    it(`rejects ${name}`, () => {
      const { problems } = checkPaths([caseFolder(name)]);
      const got = JSON.stringify(problems.map((p) => [p.line, p.message]));
      for (const [pattern, line] of expectations) {
        const hit = problems.find(
          (p) => pattern.test(p.message) && (line === undefined || p.line === line),
        );
        assert.ok(
          hit,
          `expected ${pattern}${line === undefined ? '' : ` on line ${line}`}, got: ${got}`,
        );
      }
      assert.equal(problems.length, expectations.length, `unexpected extra problems: ${got}`);
    });
  }

  it('accepts distinct ids across anchors/valid.jsonl and anchors/invalid.jsonl', () => {
    const result = checkPaths([caseFolder('shared-ids-distinct')]);
    assert.equal(result.files, 2);
    assert.deepEqual(result.problems, []);
  });

  it('rejects an id used in both anchors/valid.jsonl and anchors/invalid.jsonl', () => {
    const { problems } = checkPaths([caseFolder('shared-ids-collide')]);
    assert.equal(problems.length, 1, JSON.stringify(problems));
    const [problem] = problems;
    assert.ok(problem);
    // invalid.jsonl sorts before valid.jsonl, so the second file of the pair carries the report.
    assert.match(problem.file, /valid\.jsonl$/);
    assert.doesNotMatch(problem.file, /invalid\.jsonl$/);
    assert.equal(problem.line, 2);
    assert.match(
      problem.message,
      /^id "an-0003" is also used in anchors\/invalid\.jsonl \(line 2\); valid and invalid share one id sequence$/,
    );
  });

  it('finds the collision when the two files or the anchors folder are given as roots', () => {
    const anchors = join(caseFolder('shared-ids-collide'), 'anchors');
    const byFiles = checkPaths([join(anchors, 'invalid.jsonl'), join(anchors, 'valid.jsonl')]);
    assert.equal(byFiles.problems.length, 1, JSON.stringify(byFiles.problems));
    const byFolder = checkPaths([anchors]);
    assert.equal(byFolder.problems.length, 1, JSON.stringify(byFolder.problems));
  });

  it('reports the collision once when the same file is reached through two roots', () => {
    const root = caseFolder('shared-ids-collide');
    const { files, problems } = checkPaths([root, join(root, 'anchors', 'valid.jsonl')]);
    assert.equal(files, 3);
    assert.equal(problems.length, 1, JSON.stringify(problems));
  });

  it('does not compare ids across two package roots', () => {
    const result = checkPaths([
      caseFolder('shared-ids-package-a'),
      caseFolder('shared-ids-package-b'),
    ]);
    assert.deepEqual(result.problems, []);
  });

  it('allows the same id in compare.jsonl and contains.jsonl', () => {
    assert.deepEqual(checkPaths([caseFolder('shared-ids-other-files')]).problems, []);
  });

  it('applies the field rules when a recognized file or its folder is the root', () => {
    const file = join(caseFolder('valid-input-not-string'), 'anchors', 'valid.jsonl');
    assert.match(checkPaths([file]).problems[0]?.message ?? '', /^input: must be a string/);
    const folder = join(caseFolder('hash-ham-with-text'), 'content-hash');
    assert.match(checkPaths([folder]).problems[0]?.message ?? '', /^expected\.text: only allowed/);
  });

  it('applies only the basic rules without a recognized path', () => {
    const line = jsonl(patch(anchorWords, 'expected', 'x'));
    assert.deepEqual(checkBytes(Buffer.from(line)), []);
    assert.deepEqual(checkBytes(Buffer.from(line), 'anchors/other.jsonl'), []);
    assert.equal(checkBytes(Buffer.from(line), V).length, 1);
  });

  it('prints file and line of a field problem on the command line', () => {
    const order = runCli(caseFolder('common-id-order'));
    assert.equal(order.status, 1, order.stderr);
    assert.match(order.stderr, /valid\.jsonl:2: id "an-0001" is out of order/);
    const field = runCli(caseFolder('offsets-snap-missing-out'));
    assert.equal(field.status, 1, field.stderr);
    assert.match(field.stderr, /offsets\.jsonl:1: expected\.snap\[0\]: missing key "out"/);
    const shared = runCli(caseFolder('shared-ids-collide'));
    assert.equal(shared.status, 1, shared.stderr);
    assert.match(
      shared.stderr,
      /valid\.jsonl:2: id "an-0003" is also used in anchors\/invalid\.jsonl/,
    );
    assert.match(shared.stderr, /1 problem\(s\) in 2 file\(s\)/);
  });

  it('exits 0 on the command line for a clean recognized tree', () => {
    assert.equal(runCli(caseFolder('shared-ids-distinct')).status, 0);
  });

  it('lists number literals as written, outside strings only', () => {
    assert.deepEqual(numberLiterals('{"a":"1.5 -2","b":[-1,0,1.0,2e3],"c":true,"d":null}'), [
      '-1',
      '0',
      '1.0',
      '2e3',
    ]);
    assert.deepEqual(numberLiterals(String.raw`{"a":"q\"1","b":7}`), ['7']);
  });
});
