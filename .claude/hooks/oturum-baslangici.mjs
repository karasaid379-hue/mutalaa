#!/usr/bin/env node
// Mütâlaa · oturum başlangıcı (SessionStart giriş betiği).
// İlerleme dosyasındaki durum bloğunu ve kısa hatırlatmaları bağlama ekler.
// Hiçbir koşulda oturumu durdurmaz.

import fs from 'node:fs';
import { ILERLEME_YOLU, buildContext, extractStatus } from './lib/durum.mjs';
import { pathApiFor, projectRootOf, readStdinJson } from './lib/ortak.mjs';

async function main() {
  const input = await readStdinJson().catch(() => ({}));
  const root = projectRootOf(input);
  const file = pathApiFor().join(root, ...ILERLEME_YOLU.split('/'));
  const markdown = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : null;
  const context = buildContext(markdown === null ? null : extractStatus(markdown));
  process.stdout.write(
    JSON.stringify({ hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: context } }),
  );
}

try {
  await main();
} catch {
  // Bağlam eklenemezse oturum yine başlar.
}
process.exitCode = 0;
