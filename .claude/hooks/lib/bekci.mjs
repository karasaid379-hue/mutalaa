// Mütâlaa · klasör bekçisinin mantığı (yan etkisiz; testler bunu içe aktarır).
//
// 1. Write / Edit / MultiEdit / NotebookEdit: proje klasörünün dışına yazmayı ve
//    korunan yerlere (data/raw, .git) yazmayı reddeder. Kit ve karar defteri
//    dosyaları kullanıcı yönergesiyle (27 Ekim 2026, K-31 güncellemesi) serbesttir.
// 2. Bash / PowerShell / Monitor: komutta proje dışını gösteren bir yol ya da ev
//    klasörü başvurusu varsa kullanıcı onayı ister. Komutun yazdığı ya da sildiği
//    hedefleri (yönlendirme, cp, mv, rm, tee, sed -i, touch, mkdir, PowerShell
//    dosya komutları) korunan yer kurallarından geçirir. Git ve silme işleri onay
//    istemez; yerine kesin yasaklar (deny) vardır: zorla push, git clean -x,
//    data/raw|gold|backups silme, gizli değer dosyalarına kabuktan erişim, eas
//    submit ve yayımlama, yedeksiz veri silme, denetçi ajanların yazması. Ücretli
//    EAS işi (build, update, mobile-v* etiketi itme) onay ister (CLAUDE.md kural 11).
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

// Proje içinde onay isteyen yer kalmadı (kullanıcı yönergesi, 27 Ekim 2026): CLAUDE.md,
// ayarlar, kit dosyaları ve karar defteri Claude Code'un yetkisindedir. Karar defteri
// yalnız /karar ile değişir; bu bir yordam kuralıdır, teknik engel değil.
const ASK_INSIDE = [];

// Silinmesi yasak veri klasörleri (ham kaynak, insan emeği, yedekler) ve üst klasörleri.
const PROTECTED_DELETE = /^data\/(raw|gold|backups)(\/|$)/;
const PROTECTED_DELETE_DIRS = ['data', 'data/raw', 'data/gold', 'data/backups'];

// Salt okuma sözü veren denetçi ajanlar (hook girdisindeki agent_type): dosya yazmaz, git'i değiştirmez.
const AUDITOR_AGENTS = new Set(['inceleyici', 'metin-denetcisi', 'lisans-denetcisi', 'arayuz-denetcisi', 'arastirmaci']);
const AUDITOR_WRITE_OK = /^\.tmp\//;

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
    // Argümansız `env` ortamın tamamını yazar (gizli değerler dahil); sarmalayıcı olarak atılmadan önce işaretlenir.
    if (c.argv.some((w) => commandName(w) === 'env') && c.argv.every((w) => ENV_ASSIGN.test(w) || commandName(w) === 'env')) {
      c.dumpEnv = true;
    }
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
 * @returns {{ targets: string[], deletes: boolean, risky: { decision: 'deny' | 'ask', reason: string } | null }}
 */
export function commandEffects(argv) {
  const res = { targets: [], deletes: false, risky: null };
  if (!argv.length) return res;
  const name = commandName(argv[0]);
  const args = argv.slice(1);
  switch (name) {
    case 'rm':
    case 'rmdir':
    case 'unlink':
    case 'shred':
      res.targets = nonOptions(args);
      res.deletes = true;
      return res;
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
        res.deletes = ['remove-item', 'ri', 'del', 'erase', 'rd'].includes(name);
      }
      return res;
  }
}

/** git komut satırından alt komutu ve seçenekleri ayırır (-C ve -c değerleri atlanır). */
export function gitParts(args) {
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
  const opts = sub === undefined ? [] : rest.slice(rest.indexOf(sub) + 1);
  return { sub, opts };
}

const FORCE_LONG = ['--force', '--force-with-lease', '--force-if-includes', '--mirror'];
const isForceOption = (o) =>
  FORCE_LONG.includes(o) || o.startsWith('--force-with-lease=') || /^-[A-Za-z]*f[A-Za-z]*$/.test(o);
const MAIN_BRANCH = /(^|\/)(main|master)$/;
const MOBILE_TAG = /(^|[:/])mobile-v/;

/**
 * Git komutunun kararı: kesin yasak (deny), nadir geri dönüşsüz iş ya da ücretli iş için onay (ask) ya da null.
 * Kullanıcı yönergesi (27 Ekim 2026): push, reset, restore, rebase, amend, stash drop, dal silme sorulmaz.
 * @returns {null | { decision: 'deny' | 'ask', reason: string }}
 */
export function riskyGit(args) {
  const { sub, opts } = gitParts(args);
  const has = (...xs) => opts.some((o) => xs.includes(o));
  const deny = (reason) => ({ decision: 'deny', reason });
  const ask = (reason) => ({ decision: 'ask', reason });
  switch (sub) {
    case 'push': {
      const refspecs = opts.filter((o) => !o.startsWith('-')).slice(1); // ilki uzak depodur
      if (opts.some(isForceOption)) return deny('Zorla push yasaktır (CLAUDE.md kural 11).');
      if (refspecs.some((r) => r.startsWith('+'))) return deny('"+" önekli refspec zorla push demektir; yasaktır.');
      const deleting = has('--delete') || opts.some((o) => /^-[A-Za-z]*d[A-Za-z]*$/.test(o));
      if (refspecs.some((r) => r.startsWith(':') && MAIN_BRANCH.test(r.slice(1))) || (deleting && refspecs.some((r) => MAIN_BRANCH.test(r)))) {
        return deny('main dalı silinemez.');
      }
      if (has('--tags', '--follow-tags') || refspecs.some((r) => MOBILE_TAG.test(r))) {
        return ask('mobile-v* etiketi ücretli bir EAS derlemesi başlatır (CLAUDE.md kural 11); maliyeti söyle.');
      }
      return null;
    }
    case 'clean':
      return opts.some((o) => /^-[A-Za-z]*[xX][A-Za-z]*$/.test(o))
        ? deny('git clean -x/-X git dışı klasörleri (data/, .env) siler; yasaktır.')
        : null;
    case 'filter-branch':
    case 'filter-repo':
    case 'update-ref':
    case 'gc':
      return ask(`git ${sub} geçmişi ya da nesneleri geri dönüşsüz değiştirir; kullanıcıya göster.`);
    case 'commit':
      return has('--no-verify', '-n') ? ask('git commit --no-verify denetimleri atlar.') : null;
    case 'reflog':
      return has('expire', 'delete') ? ask('git reflog expire/delete geri kurtarma yolunu siler.') : null;
    default:
      return null;
  }
}

const AUDITOR_GIT_WRITE = new Set([
  'add', 'commit', 'push', 'reset', 'restore', 'checkout', 'switch', 'stash', 'rebase', 'merge', 'cherry-pick',
  'revert', 'tag', 'branch', 'clean', 'rm', 'mv', 'apply', 'am', 'pull', 'fetch', 'init', 'clone', 'worktree',
]);

const SECRET_FILE = /(^|[\\/])\.env([.*?[][^\\/]*)?$|(^|[\\/])s3\.json$/i;
const SECRET_KEY_FILE = /\.(pem|key|p12|keystore|jks)$/i;
const SECRET_READERS = new Set([
  'cat', 'head', 'tail', 'less', 'more', 'type', 'get-content', 'gc', 'cp', 'mv', 'tee', 'source', '.', 'xxd', 'od',
  'strings', 'base64', 'sed', 'awk', 'grep', 'rg', 'egrep', 'fgrep', 'openssl', 'copy', 'copy-item', 'move-item',
]);
const EXISTENCE_ONLY = new Set(['test', '[', '[[', 'ls', 'dir']);
const NO_ARG_SCAN = new Set(['echo', 'printf']);
const DESTROYS_DATA_TEXT = /\bdrop\s+(schema|database)\b/i;
const isEas = (w) => /^(eas|eas-cli)(@.*)?$/.test(commandName(w));

function isSecretFile(word, strict) {
  const w = String(word);
  const base = w.split(/[\\/]/).pop().toLowerCase();
  if (base.endsWith('.example')) return false;
  return SECRET_FILE.test(w) || (strict && SECRET_KEY_FILE.test(w));
}

/**
 * Bir basit komutun kesin yasakları ve ücretli iş uyarıları (komut başı eşleşmesine bağlı değildir:
 * npx, pnpm dlx, pnpm exec ile sarılmış biçimler de yakalanır).
 * @param {{ argv: string[], writes: string[], reads: string[], dumpEnv?: boolean }} c
 * @param {{ backup: boolean }} state aynı komut satırında yedek betiği daha önce çalıştı mı
 * @returns {{ deny: string[], ask: string[] }}
 */
export function commandDanger(c, state) {
  const out = { deny: [], ask: [] };
  const argv = c.argv;
  if (!argv.length && !c.dumpEnv && !c.writes.length && !c.reads.length) return out;
  const name = argv.length ? commandName(argv[0]) : '';
  const args = argv.slice(1);
  const pos = nonOptions(args);

  if (argv.some((w) => /backup-db\.ps1$/i.test(w))) state.backup = true;

  // Mağazaya gönderim ve yayımlama: hiç çalıştırılmaz. Ücretli EAS işi sorulur.
  const easAt = argv.findIndex(isEas);
  if (easAt !== -1) {
    const sub = nonOptions(argv.slice(easAt + 1))[0] ?? '';
    if (sub === 'submit') out.deny.push('`eas submit` hiç çalıştırılmaz; mağazaya gönderimi kullanıcı elle yapar (CLAUDE.md kural 11).');
    else if (sub === 'build' || sub === 'update' || (sub.startsWith('build:') && sub !== 'build:list' && sub !== 'build:view')) {
      out.ask.push(`Ücretli EAS işi (eas ${sub}); tahmini maliyeti söyle (CLAUDE.md kural 11).`);
    }
  }
  if (['npm', 'pnpm', 'yarn', 'npx'].includes(name) && pos.includes('publish')) {
    out.deny.push('Paket yayımlama hiç çalıştırılmaz; kullanıcı elle yapar (CLAUDE.md kural 11).');
  }
  if (name === 'dotnet' && pos.includes('nuget') && pos.includes('push')) {
    out.deny.push('`dotnet nuget push` hiç çalıştırılmaz; kullanıcı elle yapar (CLAUDE.md kural 11).');
  }

  // Gizli değerler (kural 8).
  if (c.dumpEnv || ((name === 'printenv' || name === 'set') && args.length === 0)) {
    out.deny.push('Ortam değişkenlerinin tamamını yazmak gizli değer sızdırabilir (CLAUDE.md kural 8).');
  }
  if (name === 'dotnet' && pos.includes('user-secrets') && pos.includes('list')) {
    out.deny.push('`dotnet user-secrets list` gizli değerleri yazar; sohbete düşmemeli (CLAUDE.md kural 8, 11).');
  }
  const gitSubName = name === 'git' ? gitParts(args).sub : undefined;
  const existenceOnly =
    EXISTENCE_ONLY.has(name) || (name === 'git' && ['check-ignore', 'status', 'ls-files'].includes(gitSubName));
  if (!existenceOnly) {
    const skipArgs = NO_ARG_SCAN.has(name) || (name === 'git' && (gitSubName === 'commit' || gitSubName === 'tag'));
    const words = [...(skipArgs ? [] : args), ...c.writes, ...c.reads];
    for (const w of [...words]) {
      const eq = w.indexOf('=');
      if (eq > 0 && eq < w.length - 1) words.push(w.slice(eq + 1));
    }
    const strict = SECRET_READERS.has(name);
    for (const w of words) {
      if (isSecretFile(w, strict)) {
        out.deny.push(`${w}: gizli değer dosyasına kabuktan erişilmez (CLAUDE.md kural 8). Varlığını test -f ya da git check-ignore ile denetle.`);
      }
    }
  }

  // Veri silen işten önce yedek (CLAUDE.md kural 11): aynı komut satırında önce scripts/backup-db.ps1 çalışmalı.
  const destroys =
    ((name === 'docker' || name === 'docker-compose') &&
      ((pos.includes('down') && args.some((a) => a === '-v' || a === '--volumes')) ||
        (pos.includes('volume') && (pos.includes('rm') || pos.includes('remove') || pos.includes('prune'))))) ||
    (name === 'dotnet' && pos.includes('ef') && pos.includes('database') && pos.includes('drop')) ||
    (!['git', 'echo', 'printf', 'grep', 'rg', 'cat'].includes(name) && args.some((a) => DESTROYS_DATA_TEXT.test(a)));
  if (destroys && !state.backup) {
    out.deny.push(
      'Veri silen iş: önce aynı komut satırında yedek al: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1 (CLAUDE.md kural 11).',
    );
  }

  // Denetçi ajanlar git geçmişini ve çalışma ağacını değiştirmez.
  if (state.auditor && name === 'git' && AUDITOR_GIT_WRITE.has(gitSubName ?? '')) {
    out.deny.push(`Denetçi ajanlar salt okunurdur; git ${gitSubName} yasak.`);
  }
  return out;
}

/** Silinecek hedef korunan veri klasörü ya da onu kapsayan üst klasör mü? (key: kökten göreli, küçük harfli, '/' ayırıcılı) */
export function isProtectedDelete(key) {
  if (PROTECTED_DELETE.test(key)) return true;
  if (key === '' || key === 'data') return true;
  if (/[*?[]/.test(key)) {
    const re = new RegExp(
      `^${key
        .replace(/[.+^${}()|\\]/g, (m) => `\\${m}`)
        .replace(/\*\*/g, '\u0000')
        .replace(/\*/g, '[^/]*')
        .replace(/\?/g, '[^/]')
        .replace(/\u0000/g, '.*')}$`,
    );
    return PROTECTED_DELETE_DIRS.some((d) => re.test(d));
  }
  return false;
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
export function scanEffects(cmd, { rootC, cwd, platform = process.platform, realpath = defaultRealpath, auditor = false }) {
  const api = pathApiFor(platform);
  const deny = [];
  const ask = [];
  const state = { backup: false, auditor };
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
    if (eff.risky) (eff.risky.decision === 'deny' ? deny : ask).push(eff.risky.reason);
    const danger = commandDanger(c, state);
    deny.push(...danger.deny);
    ask.push(...danger.ask);
    const items = [
      ...c.writes.map((raw) => ({ raw, del: false })),
      ...eff.targets.map((raw) => ({ raw, del: eff.deletes })),
    ];
    for (const { raw, del } of items) {
      if (!raw || URL_LIKE.test(raw) || SAFE_SPECIAL.has(raw.toLowerCase()) || HOME_REF.test(raw)) continue;
      if (platform === 'win32' && raw.startsWith('/') && !/^\/[A-Za-z](\/|$)/.test(raw)) continue; // dışarıda; scanCommand yakalar
      const targetC = canonical(raw, { platform, cwd: here, realpath });
      if (!isInsideCanonical(rootC, targetC, platform)) continue; // dışarıda; scanCommand yakalar
      const key = relativeKey(rootC, targetC, platform).toLowerCase();
      const r = insideRule(key);
      if (r?.decision === 'deny') deny.push(`${raw}: ${r.reason}`);
      else if (r?.decision === 'ask') ask.push(`${raw}: ${r.reason}`);
      if (del && isProtectedDelete(key)) {
        deny.push(`${raw}: data/raw, data/gold ve data/backups (ham kaynak, insan emeği, yedekler) silinmez; üst klasörleri de silinemez.`);
      }
      if (auditor && !AUDITOR_WRITE_OK.test(key)) {
        deny.push(`${raw}: denetçi ajanlar salt okunurdur; yalnız .tmp/ altına yazabilir.`);
      }
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
    const auditor = AUDITOR_AGENTS.has(String(input?.agent_type ?? ''));
    const effects = scanEffects(command, { rootC, cwd, platform, realpath, auditor });
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
