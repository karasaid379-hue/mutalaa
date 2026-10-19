// Biçim denetimi testleri. Çalıştırma: node --test .claude/hooks/test/

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { checkFile, frontmatter } from '../lib/metin.mjs';

const f = (relKey, text, ext = relKey.slice(relKey.lastIndexOf('.'))) => ({
  relKey,
  ext,
  buf: Buffer.isBuffer(text) ? text : Buffer.from(text, 'utf8'),
});

test('temiz dosyada sorun yok', () => {
  assert.deepEqual(checkFile(f('docs/a.md', '# Başlık\nTürkçe metin: ışık, İstanbul.\n')), []);
});

test('BOM yakalanır', () => {
  const buf = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from('x\n')]);
  assert.match(checkFile(f('docs/a.md', buf)).join(), /BOM/);
});

test('CRLF yakalanır, .ps1 serbest', () => {
  assert.match(checkFile(f('src/a.ts', 'a\r\nb\r\n')).join(), /CRLF/);
  assert.deepEqual(checkFile(f('scripts/backup-db.ps1', 'a\r\nb\r\n')), []);
});

test('ASCII dışı dosya adı yakalanır', () => {
  assert.match(checkFile(f('docs/yazismalar/kurul-ön-görüşme.md', 'x\n')).join(), /ASCII/);
});

test('JSON ve JSONL ayrıştırılır; tsconfig yorumlara izin verir', () => {
  assert.match(checkFile(f('package.json', '{ "a": 1, }')).join(), /JSON ayrıştırılamadı/);
  assert.deepEqual(checkFile(f('tsconfig.base.json', '{ // yorum\n "a": 1 }')), []);
  assert.deepEqual(checkFile(f('shared/test-vectors/anchors/valid.jsonl', '{"id":"an-001"}\n\n{"id":"an-002"}\n')), []);
  assert.match(checkFile(f('shared/test-vectors/anchors/valid.jsonl', '{"id":1}\n{bozuk\n')).join(), /JSONL satırları ayrıştırılamadı: 2/);
});

test('ikili dosya atlanır', () => {
  assert.deepEqual(checkFile(f('assets/db/core.db', Buffer.from([0x53, 0x51, 0x00, 0x0d, 0x0a]))), []);
});

test('ajan ön bilgisi denetlenir', () => {
  const ok = '---\nname: inceleyici\ndescription: İnceleme yapar.\ntools: Read, Grep\n---\nGövde\n';
  assert.deepEqual(checkFile(f('.claude/agents/inceleyici.md', ok)), []);
  assert.match(checkFile(f('.claude/agents/inceleyici.md', '---\ndescription: x\n---\n')).join(), /"name" alanı yok/);
  assert.match(checkFile(f('.claude/agents/inceleyici.md', '---\nname: baska\ndescription: x\n---\n')).join(), /aynı olmalı/);
  assert.match(checkFile(f('.claude/agents/inceleyici.md', '---\nname: inceleyici\ndescription: x\n')).join(), /kapanmamış/);
  assert.match(checkFile(f('.claude/agents/inceleyici.md', 'Gövde\n')).join(), /YAML ön bilgisiyle/);
});

test('beceri ön bilgisi denetlenir', () => {
  const ok = '---\nname: asama\ndescription: Bir aşamayı yürütür.\n---\nGövde\n';
  assert.deepEqual(checkFile(f('.claude/skills/asama/SKILL.md', ok)), []);
  assert.match(checkFile(f('.claude/skills/asama/SKILL.md', '---\nname: asama\n---\n')).join(), /description/);
  const folded = '---\nname: asama\ndescription: >-\n  Uzun açıklama.\n---\nGövde\n';
  assert.deepEqual(checkFile(f('.claude/skills/asama/SKILL.md', folded)), []);
});

test('kural dosyasında ön bilgi isteğe bağlıdır ama kapanmalıdır', () => {
  assert.deepEqual(checkFile(f('.claude/rules/mobil.md', '# Mobil\n')), []);
  assert.deepEqual(checkFile(f('.claude/rules/mobil.md', '---\npaths:\n  - "apps/mobile/**"\n---\n# Mobil\n')), []);
  assert.match(checkFile(f('.claude/rules/mobil.md', '---\npaths:\n  - "apps/mobile/**"\n# Mobil\n')).join(), /kapanmamış/);
});

test('frontmatter ayrıştırıcı', () => {
  assert.equal(frontmatter('# yok'), null);
  const fm = frontmatter('---\nname: "a"\ndescription: \'b\'\n---\n');
  assert.equal(fm.keys.get('name'), 'a');
  assert.equal(fm.keys.get('description'), 'b');
});
