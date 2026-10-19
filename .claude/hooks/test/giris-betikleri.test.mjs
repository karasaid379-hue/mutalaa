// Giriş betiklerini gerçek süreç olarak çalıştırır (Claude Code'un yaptığı gibi:
// stdin'e JSON, ortamda CLAUDE_PROJECT_DIR). Çalıştırma: node --test .claude/hooks/test/

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const HOOKS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Geçici klasörler proje içindeki .tmp/ altında açılır (CLAUDE.md kural 1); testten sonra silinir.
const TMP = path.resolve(HOOKS, '..', '..', '.tmp', 'kit-test');
fs.mkdirSync(TMP, { recursive: true });
after(() => fs.rmSync(TMP, { recursive: true, force: true }));

function makeRoot() {
  // Boşluk ve Türkçe karakter içeren kök: kullanıcının yolunu taklit eder.
  const base = fs.mkdtempSync(path.join(TMP, 'mutalaa test İ ş '));
  const root = path.join(base, 'proje kökü');
  fs.mkdirSync(path.join(root, 'docs', '10-claude-code'), { recursive: true });
  return { base, root };
}

function run(script, input, root) {
  return spawnSync(process.execPath, [path.join(HOOKS, script)], {
    input: JSON.stringify(input),
    env: { ...process.env, CLAUDE_PROJECT_DIR: root },
    encoding: 'utf8',
  });
}

test('klasor-bekcisi: dışarı yazmayı JSON kararıyla reddeder', () => {
  const { base, root } = makeRoot();
  const r = run('klasor-bekcisi.mjs', { tool_name: 'Write', tool_input: { file_path: path.join(base, 'disari.txt') }, cwd: root }, root);
  assert.equal(r.status, 0, r.stderr);
  const out = JSON.parse(r.stdout);
  assert.equal(out.hookSpecificOutput.hookEventName, 'PreToolUse');
  assert.equal(out.hookSpecificOutput.permissionDecision, 'deny');
});

test('klasor-bekcisi: içeri yazmada çıktı üretmez', () => {
  const { root } = makeRoot();
  const r = run('klasor-bekcisi.mjs', { tool_name: 'Write', tool_input: { file_path: path.join(root, 'apps', 'a.ts') }, cwd: root }, root);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, '');
});

test('klasor-bekcisi: içerideki sembolik bağ dışarıyı gösteriyorsa reddeder', (t) => {
  const { base, root } = makeRoot();
  const outsideDir = path.join(base, 'dis-klasor');
  fs.mkdirSync(outsideDir);
  try {
    fs.symlinkSync(outsideDir, path.join(root, 'bag'), 'junction');
  } catch {
    t.skip('Sembolik bağ oluşturulamadı');
    return;
  }
  const r = run('klasor-bekcisi.mjs', { tool_name: 'Write', tool_input: { file_path: path.join(root, 'bag', 'x.txt') }, cwd: root }, root);
  assert.equal(JSON.parse(r.stdout).hookSpecificOutput.permissionDecision, 'deny');
});

test('klasor-bekcisi: bozuk girdide 2 ile çıkar (işlem durur, sebep stderr)', () => {
  const { root } = makeRoot();
  const r = spawnSync(process.execPath, [path.join(HOOKS, 'klasor-bekcisi.mjs')], {
    input: '{bozuk',
    env: { ...process.env, CLAUDE_PROJECT_DIR: root },
    encoding: 'utf8',
  });
  assert.equal(r.status, 2);
  assert.match(r.stderr, /durduruldu/);
});

test('metin-kurali: CRLF dosyada 2 ile çıkar ve sebebi yazar', () => {
  const { root } = makeRoot();
  const file = path.join(root, 'docs', 'a.md');
  fs.writeFileSync(file, 'a\r\nb\r\n');
  const r = run('metin-kurali.mjs', { tool_name: 'Write', tool_input: { file_path: file }, cwd: root }, root);
  assert.equal(r.status, 2);
  assert.match(r.stderr, /CRLF/);
});

test('metin-kurali: temiz dosyada sessiz', () => {
  const { root } = makeRoot();
  const file = path.join(root, 'docs', 'a.md');
  fs.writeFileSync(file, '# Başlık\n');
  const r = run('metin-kurali.mjs', { tool_name: 'Edit', tool_input: { file_path: file }, cwd: root }, root);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stderr, '');
});

test('oturum-baslangici: durum bloğunu additionalContext olarak verir', () => {
  const { root } = makeRoot();
  fs.writeFileSync(
    path.join(root, 'docs', '10-claude-code', '05-ilerleme.md'),
    '# İlerleme\n<!-- durum:baslangic -->\n- Aktif aşama: A02 · Tek depo iskeleti\n<!-- durum:bitis -->\n',
  );
  const r = run('oturum-baslangici.mjs', { hook_event_name: 'SessionStart', source: 'startup', cwd: root }, root);
  assert.equal(r.status, 0);
  const out = JSON.parse(r.stdout);
  assert.equal(out.hookSpecificOutput.hookEventName, 'SessionStart');
  assert.match(out.hookSpecificOutput.additionalContext, /Aktif aşama: A02/);
});

test('oturum-baslangici: ilerleme dosyası yoksa da çalışır', () => {
  const { root } = makeRoot();
  const r = run('oturum-baslangici.mjs', { hook_event_name: 'SessionStart', source: 'clear', cwd: root }, root);
  assert.equal(r.status, 0);
  assert.match(JSON.parse(r.stdout).hookSpecificOutput.additionalContext, /okunamadı/);
});
