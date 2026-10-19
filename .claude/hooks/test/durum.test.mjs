// Oturum başlangıcı testleri. Çalıştırma: node --test .claude/hooks/test/

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { buildContext, extractStatus } from '../lib/durum.mjs';

test('durum bloğu çıkarılır', () => {
  const md = '# İlerleme\n<!-- durum:baslangic -->\n- Aktif aşama: A03\n<!-- durum:bitis -->\nKalan\n';
  assert.equal(extractStatus(md), '- Aktif aşama: A03');
});

test('CRLF dosyada da çalışır', () => {
  const md = '<!-- durum:baslangic -->\r\n- Aktif aşama: A00\r\n<!-- durum:bitis -->\r\n';
  assert.equal(extractStatus(md), '- Aktif aşama: A00');
});

test('işaretler yoksa null', () => {
  assert.equal(extractStatus('# İlerleme'), null);
  assert.equal(extractStatus('<!-- durum:bitis --> <!-- durum:baslangic -->'), null);
});

test('uzun blok kısaltılır', () => {
  const md = `<!-- durum:baslangic -->\n${'x'.repeat(4000)}\n<!-- durum:bitis -->\n`;
  assert.ok(extractStatus(md).length < 1600);
});

test('metin içinde anılan işaretler blok açmaz', () => {
  const md = 'Bloğun işaretlerini (`<!-- durum:baslangic -->`, `<!-- durum:bitis -->`) silmeyin.\n\n<!-- durum:baslangic -->\n- Aktif aşama: yok\n<!-- durum:bitis -->\n';
  assert.equal(extractStatus(md), '- Aktif aşama: yok');
});

test('gerçek ilerleme dosyasından durum çıkarılır', () => {
  const file = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'docs', '10-claude-code', '05-ilerleme.md');
  const status = extractStatus(fs.readFileSync(file, 'utf8'));
  assert.ok(status, 'durum bloğu bulunamadı');
  assert.match(status, /^- Aktif aşama:/m);
  assert.match(status, /^- Sıradaki:/m);
  assert.ok(!status.includes('`'), status);
});

test('bağlam metni kurulur', () => {
  assert.match(buildContext('- Aktif aşama: A03'), /Aktif aşama: A03/);
  assert.match(buildContext(null), /İlerleme dosyası okunamadı/);
  assert.match(buildContext(null), /Türkçe/);
});
