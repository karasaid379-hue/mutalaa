// Mütâlaa · hook'ların ortak yardımcıları.
// Bağımlılık yok; Node 22+ ile çalışır. Saf işlevler test edilebilsin diye
// platform ve realpath dışarıdan verilebilir.

import fs from 'node:fs';
import path from 'node:path';

/** Platforma göre yol API'si (testte 'win32' verilerek Windows davranışı sınanır). */
export function pathApiFor(platform = process.platform) {
  return platform === 'win32' ? path.win32 : path.posix;
}

/** stdin'deki hook girdisini JSON olarak okur. Boşsa {} döner. */
export async function readStdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString('utf8').trim();
  return text ? JSON.parse(text) : {};
}

/** Var olan en yakın üst klasörün gerçek yolunu bulur; yoksa null. */
export function defaultRealpath(p) {
  try {
    return fs.realpathSync.native(p);
  } catch {
    return null;
  }
}

/** Git Bash biçimindeki /c/Users/... yolunu C:\Users\... yapar (yalnız win32). */
export function fromGitBashPath(p, platform = process.platform) {
  if (platform !== 'win32') return p;
  const m = /^\/([a-zA-Z])(\/.*)?$/.exec(p);
  if (!m) return p;
  return `${m[1].toUpperCase()}:${(m[2] ?? '/').replace(/\//g, '\\')}`;
}

/**
 * Yolu karşılaştırmaya hazır mutlak biçime getirir:
 * mutlak yap, var olan en yakın üst klasörü realpath ile çöz, NFC'ye çevir;
 * Windows'ta harf büyüklüğünü katla (NTFS büyük-küçük harf ayırmaz).
 */
export function canonical(p, { platform = process.platform, cwd = process.cwd(), realpath = defaultRealpath } = {}) {
  const api = pathApiFor(platform);
  let abs = api.resolve(cwd, fromGitBashPath(p, platform));
  let cur = abs;
  const tail = [];
  for (;;) {
    const real = realpath(cur);
    if (real) {
      abs = tail.length ? api.join(real, ...tail.slice().reverse()) : real;
      break;
    }
    const parent = api.dirname(cur);
    if (parent === cur) break;
    tail.push(api.basename(cur));
    cur = parent;
  }
  abs = abs.normalize('NFC');
  if (platform === 'win32') abs = abs.toLowerCase();
  // Sondaki ayırıcıyı at (kök dışında).
  const root = api.parse(abs).root;
  while (abs.length > root.length && (abs.endsWith('/') || abs.endsWith('\\'))) abs = abs.slice(0, -1);
  return abs;
}

/** hedef, kök klasörün kendisi ya da içinde mi? (İkisi de canonical olmalı.) */
export function isInsideCanonical(rootC, targetC, platform = process.platform) {
  const api = pathApiFor(platform);
  if (rootC === targetC) return true;
  const rel = api.relative(rootC, targetC);
  const up = rel === '..' || rel.startsWith('../') || rel.startsWith('..\\');
  return rel !== '' && !up && !api.isAbsolute(rel);
}

/** Kökten göreli yol, '/' ayırıcılı ve küçük harfli (Windows) olarak. */
export function relativeKey(rootC, targetC, platform = process.platform) {
  const api = pathApiFor(platform);
  return api.relative(rootC, targetC).split(/[\\/]+/).join('/');
}

/** Proje kökü: Claude Code'un verdiği CLAUDE_PROJECT_DIR, yoksa oturumun cwd'si. */
export function projectRootOf(input, env = process.env) {
  return env.CLAUDE_PROJECT_DIR || input?.cwd || process.cwd();
}

/** PreToolUse kararı için JSON çıktısı. */
export function preToolUseOutput(decision, reason) {
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: decision,
      permissionDecisionReason: reason,
    },
  });
}
