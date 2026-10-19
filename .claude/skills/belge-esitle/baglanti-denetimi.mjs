#!/usr/bin/env node
// Mütâlaa · Markdown bağlantı denetimi.
// Kullanım (proje kökünden): node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs CLAUDE.md .claude
// Göreli bağlantıların hedef dosyasını ve #başlık çapalarını (GitHub kuralı) denetler.
// Kırık bağlantı varsa dosya:satır listesiyle 1, yoksa 0 ile çıkar. Bağımlılık yoktur.

import fs from 'node:fs';
import path from 'node:path';

const SKIP_DIRS = new Set(['node_modules', '.git', '.tmp', 'data', 'dist', 'bin', 'obj', '.expo']);

function collect(target, out) {
  if (!fs.existsSync(target)) return;
  const st = fs.statSync(target);
  if (st.isFile()) {
    if (target.endsWith('.md')) out.push(target);
    return;
  }
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) continue;
    collect(path.join(target, entry.name), out);
  }
}

/** GitHub başlık çapası: küçük harf; harf, işaret, rakam, alt çizgi, tire ve boşluk dışını sil; boşluk → tire. */
export function slugify(heading) {
  const text = heading
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\*+/g, '');
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{M}\p{N}\p{Pc} -]/gu, '')
    .replace(/ /g, '-');
}

/** Kod blokları ve satır içi kod dışındaki satırları verir. */
function* proseLines(text) {
  let fence = null;
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = /^\s*(`{3,}|~{3,})/.exec(line);
    if (m) {
      if (fence === null) fence = m[1][0];
      else if (m[1][0] === fence) fence = null;
      continue;
    }
    if (fence !== null) continue;
    // raw: başlık çapası için; line: bağlantı araması için (satır içi kod çıkarılmış)
    yield { no: i + 1, raw: line, line: line.replace(/`[^`]*`/g, '') };
  }
}

const anchorCache = new Map();
export function anchorsOf(file) {
  if (anchorCache.has(file)) return anchorCache.get(file);
  const seen = new Map();
  const set = new Set();
  for (const { raw } of proseLines(fs.readFileSync(file, 'utf8'))) {
    const m = /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(raw);
    if (!m) continue;
    const base = slugify(m[2]);
    const n = seen.get(base) ?? 0;
    set.add(n === 0 ? base : `${base}-${n}`);
    seen.set(base, n + 1);
  }
  anchorCache.set(file, set);
  return set;
}

function decode(s) {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

export function checkFile(file) {
  const broken = [];
  const text = fs.readFileSync(file, 'utf8');
  const linkRe = /!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g;
  for (const { no, line } of proseLines(text)) {
    for (const m of line.matchAll(linkRe)) {
      const target = m[1];
      if (/^[a-z][a-z0-9+.-]*:/i.test(target)) continue; // http:, https:, mailto:, computer: …
      const [rawPath, rawAnchor] = target.split('#');
      const dest = rawPath ? path.resolve(path.dirname(file), decode(rawPath)) : file;
      if (!fs.existsSync(dest)) {
        broken.push(`${file}:${no}: hedef yok → ${target}`);
        continue;
      }
      if (rawAnchor !== undefined && rawAnchor !== '' && dest.endsWith('.md')) {
        const anchor = decode(rawAnchor).normalize('NFC');
        const anchors = new Set([...anchorsOf(dest)].map((a) => a.normalize('NFC')));
        if (!anchors.has(anchor)) broken.push(`${file}:${no}: çapa yok → ${target}`);
      }
    }
  }
  return broken;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]).endsWith(path.join('belge-esitle', 'baglanti-denetimi.mjs'));
if (isMain) {
  const targets = process.argv.slice(2);
  if (targets.length === 0) targets.push('docs');
  const files = [];
  for (const t of targets) collect(t, files);
  const broken = files.flatMap(checkFile);
  if (broken.length) {
    process.stdout.write(`${broken.join('\n')}\n\n${files.length} dosya, ${broken.length} kırık bağlantı.\n`);
    process.exit(1);
  }
  process.stdout.write(`${files.length} dosya denetlendi, kırık bağlantı yok.\n`);
}
