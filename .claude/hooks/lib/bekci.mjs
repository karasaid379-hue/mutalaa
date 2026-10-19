// Mütâlaa · klasör bekçisinin mantığı (yan etkisiz; testler bunu içe aktarır).
//
// 1. Write / Edit / MultiEdit / NotebookEdit: proje klasörünün dışına yazmayı ve
//    korunan yerlere (data/raw, .git) yazmayı reddeder; kitin ve kararların
//    dosyalarında kullanıcı onayı ister.
// 2. Bash / PowerShell / Monitor: komutta proje dışını gösteren bir yol ya da ev
//    klasörü başvurusu varsa kullanıcı onayı ister. Komutun yazdığı ya da sildiği
//    hedefleri (yönlendirme, cp, mv, rm, tee, sed -i, touch, mkdir, PowerShell
//    dosya komutları) aynı korunan yer kurallarından geçirir. Özyinelemeli silme
//    ve geri dönüşü zor git işlemleri onay ister.
//
// Sınır: Claude Code'un çalıştırdığı bir programın (node, python, dotnet …) kendi
// içinde açtığı dosyaları göremez; bunu yalnız işletim sistemi düzeyinde bir
// kum havuzu engeller (docs/10-claude-code/01-kurulum.md, "Klasör sınırı").
//
// Okumalar Claude Code'un kendi permissions.blockReadsOutsideWorkingDirectories
// ayarıyla engellenir; bu modül okumaya karışmaz. Hiçbir zaman "allow" vermez:
// karar vermediğinde normal izin akışı sürer.

import {
  canonical,
  defaultRealpath,
  fromGitBashPath,
  isInsideCanonical,
  pathApiFor,
  projectRootOf,
  relativeKey,
} from './ortak.mjs';

export const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
export const SHELL_TOOLS = new Set(['Bash', 'PowerShell', 'Monitor']);

const DENY_INSIDE = [
  { re: /(^|\/)\.git(\/|$)/, why: '.git klasörü elle değiştirilmez; git komutlarını kullan.' },
  {
    re: /^data\/raw(\/|$)/,
    why: 'data/raw değişmez ham kaynaktır (K-26). Bu klasöre yalnız `uv run mutalaa ingest` yazar.',
  },
];

const ASK_INSIDE = [
  { re: /^claude\.md$/, why: 'CLAUDE.md projenin anayasasıdır; değişikliği kullanıcı onaylar.' },
  { re: /^\.claude\/settings(\.local)?\.json$/, why: 'Claude Code ayarları değişiyor; kullanıcı onaylar.' },
  {
    re: /^\.claude\/(hooks|agents|skills|rules)(\/|$)/,
    why: 'Kit dosyası (ajan, beceri, kural ya da hook) değişiyor; kullanıcı onaylar.',
  },
  {
    re: /^docs\/00-ozet\/02-karar-defteri\.md$/,
    why: 'Karar defteri tek doğruluk kaynağıdır; değişikliği kullanıcı onaylar (/karar).',
  },
];

const SAFE_SPECIAL = new Set(['/dev/null', '/dev/stdin', '/dev/stdout', '/dev/stderr', 'nul', 'con']);
const POSIX_SAFE_PREFIXES = ['/dev/', '/proc/', '/usr/bin/', '/bin/', '/usr/lib/', '/tmp/'];
// Git Bash'te bu kökler Git kurulumuna ya da sistem klasörlerine gider: proje dışıdır.
const GITBASH_ROOTS = /^\/(tmp|usr|etc|home|mnt|opt|var|bin|lib|proc|sys|root|srv|run|cygdrive|mingw64|mingw32)(\/|$)/i;
// Seçeneklerini "/x" biçiminde alan Windows komutları; "/c", "/f" gibi değerler yol değildir.
const WINDOWS_SLASH_OPTION_COMMANDS = new Set([
  'cmd', 'taskkill', 'tasklist', 'where', 'findstr', 'robocopy', 'xcopy', 'ipconfig', 'netsh', 'sc', 'reg',
  'schtasks', 'icacls', 'attrib', 'chcp', 'timeout', 'start', 'shutdown', 'msiexec', 'wsl',
]);

const ENV_NAMES = 'HOME|USERPROFILE|HOMEPATH|HOMEDRIVE|APPDATA|LOCALAPPDATA|TEMP|TMP|TMPDIR|ONEDRIVE\\w*|PROGRAMDATA|PUBLIC';
const HOME_REF = new RegExp(
  `(^~([\\\\/]|$))|(\\$\\{?(${ENV_NAMES})\\}?(?![A-Za-z0-9_]))|(%(${ENV_NAMES})%)|(\\$env:(${ENV_NAMES})(?![A-Za-z0-9_]))`,
  'i',
);
const URL_LIKE = /^[a-z][a-z0-9+.-]*:\/\//i;
const CONTAINER_PATH = /^[A-Za-z0-9_.-]{2,}:\//; // postgres:/tmp/x (docker compose cp)
const WIN_DRIVE = /^[A-Za-z]:[\\/]/;
const GITBASH_DRIVE = /^\/[A-Za-z](\/|$)/;
const UNC = /^\\\\[^\\]/;
const ENV_ASSIGN = /^[A-Za-z_][A-Za-z0-9_]*=/;
const WRAPPERS = new Set(['env', 'command', 'builtin', 'exec', 'nice', 'time', 'nohup', 'sudo', 'xargs']);

/** Kabuk komutunu kaba biçimde parçalar: tırnaklara uyar, işleçlerde böler. */
export function tokenize(cmd) {
  const tokens = lex(cmd).filter((t) => t.t === 'w').map((t) => t.v);
  // --out=../x ve -o=../x biçimlerindeki sağ tarafı da aday yap.
  const extra = [];
  for (const t of tokens) {
    const eq = t.indexOf('=');
    if (eq > 0 && eq < t.length - 1) extra.push(t.slice(eq + 1));
  }
  return [...tokens, ...extra];
}

const SHELL_INTERPRETER = /(^|[\s;&|(])(bash|sh|zsh|dash|pwsh|powershell)(\.exe)?(\s|$)/i;

/**
 * Heredoc gövdelerini çıkarır; gövdedeki metin veri sayılır. Gövde bir kabuğa
 * veriliyorsa (bash <<EOF) gövde komut olarak taranır, çıkarılmaz.
 */
export function stripHeredocs(cmd) {
  const lines = String(cmd ?? '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  const pending = [];
  for (const line of lines) {
    if (pending.length) {
      const { delim, keep } = pending[0];
      if (line.replace(/^\t+/, '') === delim) pending.shift();
      else if (keep) out.push(line);
      continue;
    }
    out.push(line);
    for (const m of line.matchAll(/(^|[^<])<<(?!<)-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2/g)) {
      const before = line.slice(0, m.index + m[1].length);
      pending.push({ delim: m[3], keep: SHELL_INTERPRETER.test(before) });
    }
  }
  return out.join('\n');
}

/**
 * Komutu kelime ve işleç belirteçlerine ayırır (yaklaşık bir kabuk sözdizimi).
 * @returns {{t: 'w' | 'op', v: string}[]}
 */
export function lex(cmd) {
  const src = stripHeredocs(cmd);
  const out = [];
  let cur = '';
  let has = false;
  let quote = null;
  const push = () => {
    if (has) out.push({ t: 'w', v: cur });
    cur = '';
    has = false;
  };
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quote) {
      if (ch === quote) quote = null;
      else if (ch === '\\' && quote === '"' && i + 1 < src.length && '"\\$`'.includes(src[i + 1])) cur += src[++i];
      else cur += ch;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      has = true;
      continue;
    }
    if (ch === '\n') {
      push();
      out.push({ t: 'op', v: ';' });
      continue;
    }
    if (/\s/.test(ch)) {
      push();
      continue;
    }
    if (ch === '>' || ch === '<') {
      if (has && /^\d+$/.test(cur)) {
        cur = '';
        has = false;
      } else {
        push();
      }
      let op = ch;
      if (src[i + 1] === ch) {
        op += ch;
        i++;
        if (ch === '<' && src[i + 1] === '<') {
          op += '<';
          i++;
        }
      }
      if (src[i + 1] === '&') {
        op += '&';
        i++;
      } else if (op === '>' && src[i + 1] === '|') {
        i++;
      }
      out.push({ t: 'op', v: op });
      continue;
    }
    if (ch === '&' && src[i + 1] === '>') {
      push();
      i++;
      let op = '>';
      if (src[i + 1] === '>') {
        op = '>>';
        i++;
      }
      out.push({ t: 'op', v: op });
      continue;
    }
    if (';|&()`'.includes(ch)) {
      push();
      let op = ch;
      if ((ch === '|' || ch === '&') && src[i + 1] === ch) {
        op += ch;
        i++;
      }
      out.push({ t: 'op', v: op });
      continue;
    }
    cur += ch;
    has = true;
  }
  push();
  return out;
}

/** Belirteçleri basit komutlara böler; yönlendirme hedeflerini ayrı toplar. */
export function simpleCommands(tokens) {
  const cmds = [];
  let inTick = false;
  let cur = { argv: [], writes: [], reads: [] };
  const flush = () => {
    if (cur.argv.length || cur.writes.length || cur.reads.length) cmds.push(cur);
    cur = { argv: [], writes: [], reads: [] };
  };
  for (let i = 0; i < tokens.length; i++) {
    const tk = tokens[i];
    if (tk.t === 'w') {
      cur.argv.push(tk.v);
      continue;
    }
    if (tk.v === '>' || tk.v === '>>') {
      const n = tokens[i + 1];
      if (n && n.t === 'w') {
        cur.writes.push(n.v);
        i++;
      }
      continue;
    }
    if (tk.v === '>&' || tk.v === '>>&') {
      // >&2 ve >&- tanımlayıcı kopyasıdır; bash'te ">& dosya" dosyaya yazar.
      const n = tokens[i + 1];
      if (n && n.t === 'w') {
        if (!/^(\d+|-)$/.test(n.v)) cur.writes.push(n.v);
        i++;
      }
      continue;
    }
    if (tk.v.startsWith('<')) {
      // "< dosya" okunur ve yol taramasına girer; <<, <<< ve <& sonrası veri ya da tanımlayıcıdır.
      const n = tokens[i + 1];
      if (n && n.t === 'w') {
        if (tk.v === '<') cur.reads.push(n.v);
        i++;
      }
      continue;
    }
    flush(); // ; | || & && ( ) ` komutları ayırır
    // Alt kabuk ve komut yerine koyma: içerideki cd dışarıyı etkilemez; tarayıcılar
    // açılışta çalışma dizinini saklar, kapanışta geri alır.
    if (tk.v === '(' || tk.v === ')' || tk.v === '`') {
      const open = tk.v === '`' ? !inTick : tk.v === '(';
      if (tk.v === '`') inTick = !inTick;
      cmds.push({ argv: [], writes: [], reads: [], open, close: !open });
    }
  }
  flush();
  // Önekteki ortam atamalarını ve sarmalayıcıları at: FOO=1 env nice cmd …
  for (const c of cmds) {
    while (c.argv.length && (ENV_ASSIGN.test(c.argv[0]) || WRAPPERS.has(commandName(c.argv[0])))) c.argv.shift();
  }
  return cmds;
}

function commandName(word) {
  const base = String(word).split(/[\\/]/).pop().toLowerCase();
  return base.replace(/\.(exe|cmd|bat)$/, '');
}

function nonOptions(args) {
  const out = [];
  let end = false;
  for (const a of args) {
    if (!end && a === '--') {
      end = true;
      continue;
    }
    if (!end && a.startsWith('-') && a !== '-') continue;
    out.push(a);
  }
  return out;
}

function optionValue(args, names) {
  const vals = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const lower = a.toLowerCase();
    for (const n of names) {
      if (lower === n) {
        if (i + 1 < args.length) vals.push(args[i + 1]);
      } else if (lower.startsWith(`${n}=`) || lower.startsWith(`${n}:`)) {
        vals.push(a.slice(n.length + 1));
      }
    }
  }
  return vals;
}

const PS_WRITE = new Set([
  'set-content', 'add-content', 'out-file', 'clear-content', 'new-item', 'remove-item', 'copy-item', 'move-item',
  'rename-item', 'sc', 'ac', 'ni', 'ri', 'del', 'erase', 'rd', 'cpi', 'copy', 'mi', 'move', 'rni', 'ren',
]);

/**
 * Bir basit komutun yazdığı ya da sildiği hedefler.
 * @returns {{ targets: string[], recursiveDelete: boolean, risky: string | null }}
 */
export function commandEffects(argv) {
  const res = { targets: [], recursiveDelete: false, risky: null };
  if (!argv.length) return res;
  const name = commandName(argv[0]);
  const args = argv.slice(1);
  switch (name) {
    case 'rm':
      res.targets = nonOptions(args);
      res.recursiveDelete = args.some((a) => /^-[A-Za-z]*[rR]/.test(a) || a === '--recursive');
      return res;
    case 'rmdir':
    case 'unlink':
    case 'shred':
    case 'truncate':
    case 'touch':
    case 'mkdir':
    case 'tee':
      res.targets = nonOptions(args);
      return res;
    case 'cp':
    case 'install':
    case 'ln': {
      const dir = optionValue(args, ['-t', '--target-directory']);
      const pos = nonOptions(args);
      res.targets = dir.length ? dir : pos.slice(-1);
      return res;
    }
    case 'mv':
      res.targets = [...optionValue(args, ['-t', '--target-directory']), ...nonOptions(args)];
      return res;
    case 'sed':
      if (args.some((a) => /^-[A-Za-z]*i/.test(a) || a.startsWith('--in-place'))) res.targets = nonOptions(args);
      return res;
    case 'git':
      res.risky = riskyGit(args);
      return res;
    default:
      if (PS_WRITE.has(name)) {
        res.targets = [
          ...optionValue(args, ['-path', '-literalpath', '-destination', '-filepath']),
          ...nonOptions(args),
        ];
        res.recursiveDelete = ['remove-item', 'ri', 'del', 'erase', 'rd'].includes(name) && args.some((a) => /^-r(ecurse)?$/i.test(a));
      }
      return res;
  }
}

/** Geri dönüşü zor git işlemi mi? Öyleyse kısa açıklama döner. */
export function riskyGit(args) {
  const rest = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '-C' || a === '-c' || a === '--git-dir' || a === '--work-tree') {
      i++;
      continue;
    }
    rest.push(a);
  }
  const sub = rest.find((a) => !a.startsWith('-'));
  const opts = rest.slice(rest.indexOf(sub) + 1);
  const has = (...xs) => opts.some((o) => xs.includes(o));
  switch (sub) {
    case 'push':
    case 'reset':
    case 'clean':
    case 'restore':
    case 'rebase':
    case 'filter-branch':
    case 'filter-repo':
    case 'update-ref':
    case 'gc':
      return `git ${sub}`;
    case 'commit':
      return has('--amend', '--no-verify', '-n') ? 'git commit --amend / --no-verify' : null;
    case 'stash':
      return has('drop', 'clear') ? 'git stash drop / clear' : null;
    case 'branch':
      return has('-D', '-d', '--delete', '-f', '--force', '-M') ? 'git branch silme ya da zorlama' : null;
    case 'switch':
      return has('--discard-changes', '-f', '--force', '-C') ? 'git switch değişiklikleri atarak' : null;
    case 'checkout':
      return has('--', '.', '-f', '--force') ? 'git checkout ile değişiklikleri atma' : null;
    case 'reflog':
      return has('expire', 'delete') ? 'git reflog expire / delete' : null;
    case 'tag':
      return has('-d', '--delete', '-f', '--force') ? 'git tag silme ya da zorlama' : null;
    default:
      return null;
  }
}

/** Bir kelimenin proje dışını gösterip göstermediği. 'home' | 'outside' | null */
function classifyWord(t, { rootC, cwd, platform, realpath, slashOptions }) {
  if (!t || URL_LIKE.test(t)) return null;
  if (HOME_REF.test(t)) return 'home';
  if (SAFE_SPECIAL.has(t.toLowerCase())) return null;
  if (CONTAINER_PATH.test(t) && !WIN_DRIVE.test(t)) return null;
  if (UNC.test(t)) return 'outside';
  let candidate = null;
  if (WIN_DRIVE.test(t)) {
    candidate = t;
  } else if (platform === 'win32' && t.startsWith('/') && !t.startsWith('//')) {
    if (/^\/[A-Za-z]\//.test(t)) candidate = fromGitBashPath(t, platform);
    else if (/^\/[A-Za-z]$/.test(t)) {
      if (slashOptions) return null;
      candidate = fromGitBashPath(t, platform);
    } else if (GITBASH_ROOTS.test(t)) return 'outside';
    else if (t.indexOf('/', 1) !== -1) return 'outside';
    else return null; // /p:Ayar, /nologo gibi seçenekler
  } else if (platform !== 'win32' && t.startsWith('/') && !t.startsWith('//')) {
    if (POSIX_SAFE_PREFIXES.some((p) => t.startsWith(p))) return null;
    candidate = t;
  } else if (t.split(/[\\/]+/).includes('..')) {
    candidate = t;
  }
  if (candidate === null) return null;
  const c = canonical(candidate, { platform, cwd, realpath });
  return isInsideCanonical(rootC, c, platform) ? null : 'outside';
}

/**
 * Komuttaki proje dışı yolları bulur.
 * @returns {{ outside: string[], homeRefs: string[] }}
 */
export function scanCommand(cmd, { rootC, cwd, platform = process.platform, realpath = defaultRealpath }) {
  const api = pathApiFor(platform);
  const outside = [];
  const homeRefs = [];
  let here = cwd;
  const stack = [];
  for (const c of simpleCommands(lex(cmd))) {
    if (c.open) {
      stack.push(here);
      continue;
    }
    if (c.close) {
      if (stack.length) here = stack.pop();
      continue;
    }
    const slashOptions = c.argv.length > 0 && WINDOWS_SLASH_OPTION_COMMANDS.has(commandName(c.argv[0]));
    const words = [...c.argv, ...c.writes, ...c.reads];
    for (const w of [...words]) {
      const eq = w.indexOf('=');
      if (eq > 0 && eq < w.length - 1) words.push(w.slice(eq + 1));
    }
    if (c.argv.length === 1 && commandName(c.argv[0]) === 'cd') homeRefs.push('cd');
    for (const raw of words) {
      const t = raw.replace(/[,;]+$/, '');
      const k = classifyWord(t, { rootC, cwd: here, platform, realpath, slashOptions });
      if (k === 'home') homeRefs.push(t);
      else if (k === 'outside') outside.push(t);
    }
    if (c.argv.length >= 2 && commandName(c.argv[0]) === 'cd') {
      const to = c.argv[1];
      if (to !== '-' && !HOME_REF.test(to)) here = api.resolve(here, fromGitBashPath(to, platform));
    }
  }
  return { outside, homeRefs };
}

/** Proje içi hedef için korunan yer kuralı: deny, ask ya da null. */
function insideRule(key) {
  for (const rule of DENY_INSIDE) if (rule.re.test(key)) return { decision: 'deny', reason: rule.why };
  for (const rule of ASK_INSIDE) if (rule.re.test(key)) return { decision: 'ask', reason: rule.why };
  return null;
}

/**
 * Kabuk komutunun proje içindeki korunan yerlere etkisi.
 * @returns {{ deny: string[], ask: string[] }} gerekçeler
 */
export function scanEffects(cmd, { rootC, cwd, platform = process.platform, realpath = defaultRealpath }) {
  const api = pathApiFor(platform);
  const deny = [];
  const ask = [];
  let here = cwd;
  const stack = [];
  for (const c of simpleCommands(lex(cmd))) {
    if (c.open) {
      stack.push(here);
      continue;
    }
    if (c.close) {
      if (stack.length) here = stack.pop();
      continue;
    }
    if (c.argv.length >= 2 && commandName(c.argv[0]) === 'cd') {
      const to = c.argv[1];
      if (to !== '-' && !HOME_REF.test(to)) here = api.resolve(here, fromGitBashPath(to, platform));
    }
    const eff = commandEffects(c.argv);
    if (eff.risky) ask.push(`Geri dönüşü zor işlem (${eff.risky}); kullanıcı onaylar (CLAUDE.md kural 11).`);
    if (eff.recursiveDelete) ask.push('Özyinelemeli silme; kullanıcı onaylar (CLAUDE.md kural 11).');
    for (const raw of [...c.writes, ...eff.targets]) {
      if (!raw || URL_LIKE.test(raw) || SAFE_SPECIAL.has(raw.toLowerCase()) || HOME_REF.test(raw)) continue;
      if (platform === 'win32' && raw.startsWith('/') && !/^\/[A-Za-z](\/|$)/.test(raw)) continue; // dışarıda; scanCommand yakalar
      const targetC = canonical(raw, { platform, cwd: here, realpath });
      if (!isInsideCanonical(rootC, targetC, platform)) continue; // dışarıda; scanCommand yakalar
      const key = relativeKey(rootC, targetC, platform).toLowerCase();
      const r = insideRule(key);
      if (r?.decision === 'deny') deny.push(`${raw}: ${r.reason}`);
      else if (r?.decision === 'ask') ask.push(`${raw}: ${r.reason}`);
    }
  }
  return { deny, ask };
}

/**
 * Hook kararı. null: karar yok (normal izin akışı).
 * @returns {null | { decision: 'deny' | 'ask', reason: string }}
 */
export function decide(input, { env = process.env, platform = process.platform, realpath = defaultRealpath } = {}) {
  const tool = input?.tool_name;
  const ti = input?.tool_input ?? {};
  const root = projectRootOf(input, env);
  const cwd = input?.cwd || root;
  const rootC = canonical(root, { platform, cwd: root, realpath });

  if (WRITE_TOOLS.has(tool)) {
    const target = ti.file_path ?? ti.notebook_path ?? ti.path;
    if (typeof target !== 'string' || target === '') return null;
    const targetC = canonical(target, { platform, cwd, realpath });
    if (!isInsideCanonical(rootC, targetC, platform)) {
      return {
        decision: 'deny',
        reason:
          `Proje klasörünün dışına yazma engellendi: ${target}. ` +
          'Mütâlaa yalnız kendi klasöründe çalışır (CLAUDE.md › Klasör sınırı). ' +
          'Geçici dosyalar için proje içindeki .tmp/ klasörünü kullan.',
      };
    }
    return insideRule(relativeKey(rootC, targetC, platform).toLowerCase());
  }

  if (SHELL_TOOLS.has(tool)) {
    const command = typeof ti.command === 'string' ? ti.command : '';
    if (command === '') return null;
    const effects = scanEffects(command, { rootC, cwd, platform, realpath });
    if (effects.deny.length) return { decision: 'deny', reason: effects.deny.slice(0, 3).join(' ') };
    const { outside, homeRefs } = scanCommand(command, { rootC, cwd, platform, realpath });
    const reasons = [];
    if (outside.length || homeRefs.length) {
      const shown = [...outside, ...homeRefs].slice(0, 3).join(', ');
      reasons.push(
        `Komut proje klasörünün dışını gösteriyor olabilir (${shown}). ` +
          'Mütâlaa yalnız kendi klasöründe çalışır; komutu onaylamadan önce kontrol et.',
      );
    }
    reasons.push(...effects.ask);
    if (reasons.length) return { decision: 'ask', reason: reasons.slice(0, 3).join(' ') };
    return null;
  }
  return null;
}
