// Run: node --test "scripts/ci/*.test.mjs"
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { checkTitle } from './pr-title.mjs';

const SCRIPT = fileURLToPath(new URL('./pr-title.mjs', import.meta.url));

test('valid titles pass', () => {
  for (const t of [
    'ci(infra): add github actions workflows',
    'feat(anchors): parse word-range anchors',
    'fix(search): map dotted capital I before lowercasing',
    'docs(docs): close A07',
    'chore(kit): back up before data deletion',
    'build(pipeline): bump the uv group with 3 updates',
    'test(test-vectors): add offsets 12',
  ]) {
    assert.deepEqual(checkTitle(t), [], t);
  }
});

test('invalid titles fail', () => {
  for (const t of [
    '',
    'Add CI workflows',
    'ci: add workflows',
    'ci(infra) add workflows',
    'ci(unknown): add workflows',
    'wip(infra): add workflows',
    'feat!: break it',
    'feat(api)!: break it',
    'ci(infra): Add workflows',
    'ci(infra): add workflows.',
    'ci(infra): ',
    'ci(infra):add workflows',
    'ci(infra): add workflows\nsecond line',
    `ci(infra): ${'a'.repeat(73)}`,
  ]) {
    assert.notDeepEqual(checkTitle(t), [], JSON.stringify(t));
  }
});

test('length limit counts code points and is waived for dependabot', () => {
  assert.deepEqual(checkTitle(`ci(infra): ${'a'.repeat(72)}`), []);
  assert.notDeepEqual(checkTitle(`ci(infra): ${'a'.repeat(73)}`, 'someone'), []);
  assert.deepEqual(checkTitle(`ci(infra): ${'a'.repeat(120)}`, 'dependabot[bot]'), []);
  // 72 astral characters are 144 UTF-16 units but 72 code points.
  assert.deepEqual(checkTitle(`ci(infra): a${'\u{1D7D8}'.repeat(71)}`), []);
});

test('command line: exit codes and no shell interpretation of the title', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pr-title-'));
  const marker = path.join(dir, 'injected');
  try {
    const run = (title) =>
      spawnSync(process.execPath, [SCRIPT], {
        env: { ...process.env, TITLE: title },
        encoding: 'utf8',
      });
    assert.equal(run('ci(infra): add github actions workflows').status, 0);
    assert.equal(run('Add CI workflows').status, 1);
    const injected = run(`ci(infra): $(touch ${marker}) \`touch ${marker}\` ; touch ${marker}`);
    assert.equal(injected.status, 1);
    assert.equal(fs.existsSync(marker), false, 'title must never reach a shell');
    assert.match(injected.stdout, /Title received/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
