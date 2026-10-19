#!/usr/bin/env node
// Mütâlaa · klasör bekçisi (PreToolUse giriş betiği).
// Mantık lib/bekci.mjs içindedir. Ayar: .claude/settings.json › hooks › PreToolUse
// ("onFailure": "block": betik başlayamaz, çöker ya da zaman aşımına uğrarsa işlem durur).
// Çıkış: karar varsa stdout'a PreToolUse JSON'u ve 0; karar yoksa çıktısız 0;
// girdi okunamazsa stderr'e açıklama ve 2 (işlem durur).

import { WRITE_TOOLS, decide } from './lib/bekci.mjs';
import { preToolUseOutput, readStdinJson } from './lib/ortak.mjs';

async function main() {
  let input;
  try {
    input = await readStdinJson();
  } catch (err) {
    process.stderr.write(`Klasör bekçisi girdiyi okuyamadı (${err.message}); işlem güvenlik için durduruldu.\n`);
    process.exitCode = 2;
    return;
  }
  try {
    const result = decide(input);
    if (result) process.stdout.write(preToolUseOutput(result.decision, result.reason));
    process.exitCode = 0;
  } catch (err) {
    // Emin olunamıyorsa güvenli taraf: yazma reddedilir, komut kullanıcıya sorulur.
    const write = WRITE_TOOLS.has(input?.tool_name);
    const reason =
      `Klasör bekçisi bu işlemi çözümleyemedi (${err.message}). ` +
      (write ? 'Yazma engellendi.' : 'Komutu onaylamadan önce kontrol et.') +
      ' Kit testleri: node --test ".claude/hooks/test/*.test.mjs"';
    process.stdout.write(preToolUseOutput(write ? 'deny' : 'ask', reason));
    process.exitCode = 0;
  }
}

await main();
