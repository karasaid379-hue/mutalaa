#!/usr/bin/env node
// Mütâlaa · biçim denetimi (PostToolUse giriş betiği).
// Yazılan ya da düzenlenen dosyada BOM, CRLF, ASCII dışı dosya adı, bozuk JSON/JSONL
// ve kit ön bilgisi sorunlarını arar. Sorun varsa stderr'e yazar ve 2 ile çıkar:
// Claude Code bu mesajı modele gösterir, model dosyayı düzeltir.

import fs from 'node:fs';
import { checkFile } from './lib/metin.mjs';
import { canonical, isInsideCanonical, pathApiFor, projectRootOf, readStdinJson, relativeKey } from './lib/ortak.mjs';

const MAX_BYTES = 5 * 1024 * 1024;

async function main() {
  const input = await readStdinJson();
  const ti = input?.tool_input ?? {};
  const target = ti.file_path ?? ti.notebook_path;
  if (typeof target !== 'string' || target === '') return 0;

  const api = pathApiFor();
  const root = projectRootOf(input);
  const rootC = canonical(root, { cwd: root });
  const targetC = canonical(target, { cwd: input?.cwd || root });
  if (!isInsideCanonical(rootC, targetC)) return 0;

  const abs = api.resolve(input?.cwd || root, target);
  const stat = fs.statSync(abs, { throwIfNoEntry: false });
  if (!stat || !stat.isFile() || stat.size > MAX_BYTES) return 0;

  const problems = checkFile({
    relKey: relativeKey(rootC, targetC),
    ext: api.extname(abs).toLowerCase(),
    buf: fs.readFileSync(abs),
  });
  if (problems.length === 0) return 0;

  process.stderr.write(`Biçim denetimi (${target}):\n- ${problems.join('\n- ')}\nDosyayı düzelt.\n`);
  return 2;
}

try {
  process.exitCode = await main();
} catch (err) {
  // Denetim hatası işi durdurmaz; yalnız kullanıcı görür.
  process.stderr.write(`biçim denetimi çalışmadı: ${err.message}\n`);
  process.exitCode = 1;
}
