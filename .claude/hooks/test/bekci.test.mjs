// Klasör bekçisi testleri. Çalıştırma: node --test .claude/hooks/test/
// Windows davranışı platform: 'win32' ve sahte realpath ile sınanır.

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { decide, scanCommand, tokenize } from '../lib/bekci.mjs';
import { canonical } from '../lib/ortak.mjs';

const WIN_ROOT = 'C:\\Users\\MEHMET SAİD\\OneDrive\\Masaüstü\\mutalaa-docs';
const win = { platform: 'win32', realpath: () => null, env: { CLAUDE_PROJECT_DIR: WIN_ROOT } };
const winInput = (tool, toolInput, cwd = WIN_ROOT) => ({ tool_name: tool, tool_input: toolInput, cwd });

const POSIX_ROOT = '/home/erdem/mutalaa';
const posix = { platform: 'linux', realpath: () => null, env: { CLAUDE_PROJECT_DIR: POSIX_ROOT } };
const posixInput = (tool, toolInput, cwd = POSIX_ROOT) => ({ tool_name: tool, tool_input: toolInput, cwd });

const decision = (r) => (r === null ? null : r.decision);

test('Windows: proje içine yazma serbest', () => {
  assert.equal(decide(winInput('Write', { file_path: `${WIN_ROOT}\\apps\\mobile\\app\\index.tsx` }), win), null);
  assert.equal(decide(winInput('Edit', { file_path: `${WIN_ROOT}\\docs\\README.md` }), win), null);
});

test('Windows: harf büyüklüğü ve eğik çizgi farkı içeride sayılır', () => {
  const p = 'c:/users/mehmet saİd/onedrive/masaüstü/mutalaa-docs/server/x.cs';
  assert.equal(decide(winInput('Write', { file_path: p }), win), null);
});

test('Windows: proje dışına yazma reddedilir', () => {
  const r = decide(winInput('Write', { file_path: 'C:\\Users\\MEHMET SAİD\\OneDrive\\Masaüstü\\quran-app-docs\\a.md' }), win);
  assert.equal(decision(r), 'deny');
  assert.match(r.reason, /dışına yazma engellendi/);
});

test('Windows: ortak önekli kardeş klasör dışarıda sayılır', () => {
  const r = decide(winInput('Write', { file_path: `${WIN_ROOT}-yedek\\a.md` }), win);
  assert.equal(decision(r), 'deny');
});

test('Windows: göreli .. ile dışarı çıkma reddedilir', () => {
  assert.equal(decision(decide(winInput('Write', { file_path: '..\\quran-app-docs\\x.md' }), win)), 'deny');
});

test('Windows: başka sürücü ve geçici klasör reddedilir', () => {
  assert.equal(decision(decide(winInput('Write', { file_path: 'D:\\x.txt' }), win)), 'deny');
  assert.equal(
    decision(decide(winInput('Write', { file_path: 'C:\\Users\\MEHMET SAİD\\AppData\\Local\\Temp\\a.txt' }), win)),
    'deny',
  );
});

test('Windows: data/raw ve .git içine yazma reddedilir', () => {
  assert.equal(decision(decide(winInput('Write', { file_path: `${WIN_ROOT}\\data\\raw\\tanzil\\x.txt` }), win)), 'deny');
  assert.equal(decision(decide(winInput('Edit', { file_path: `${WIN_ROOT}\\.git\\config` }), win)), 'deny');
  assert.equal(decision(decide(winInput('Write', { file_path: `${WIN_ROOT}\\data\\staged\\x.jsonl` }), win)), null);
});

test('Windows: kit ve karar defteri değişikliği onay ister', () => {
  for (const rel of [
    'CLAUDE.md',
    '.claude\\settings.json',
    '.claude\\settings.local.json',
    '.claude\\skills\\asama\\SKILL.md',
    '.claude\\agents\\inceleyici.md',
    '.claude\\hooks\\lib\\bekci.mjs',
    '.claude\\rules\\mobil.md',
    'docs\\00-ozet\\02-karar-defteri.md',
  ]) {
    assert.equal(decision(decide(winInput('Edit', { file_path: `${WIN_ROOT}\\${rel}` }), win)), 'ask', rel);
  }
  assert.equal(decision(decide(winInput('Edit', { file_path: `${WIN_ROOT}\\docs\\10-claude-code\\05-ilerleme.md` }), win)), null);
});

test('NotebookEdit notebook_path alanıyla denetlenir', () => {
  assert.equal(decision(decide(winInput('NotebookEdit', { notebook_path: 'D:\\n.ipynb' }), win)), 'deny');
});

test('Windows: Bash komutlarında proje dışı yol onay ister', () => {
  const ask = (cmd, cwd) => decision(decide(winInput('Bash', { command: cmd }, cwd), win));
  assert.equal(ask('cat C:/Users/MEHMET\\ SAİD/Desktop/x'), 'ask');
  assert.equal(ask('ls /c/Users/someone'), 'ask');
  assert.equal(ask('ls /d'), 'ask');
  assert.equal(ask('echo x > C:\\temp\\a.txt'), 'ask');
  assert.equal(ask('cd ..'), 'ask');
  assert.equal(ask('cat ../../gizli', `${WIN_ROOT}\\apps`), 'ask');
  assert.equal(ask('cat ~/.ssh/id_rsa'), 'ask');
  assert.equal(ask('echo $HOME'), 'ask');
  assert.equal(ask('type %USERPROFILE%\\x'), 'ask');
  assert.equal(ask('robocopy . \\\\sunucu\\pay'), 'ask');
});

test('Windows: olağan geliştirme komutları karar üretmez', () => {
  const none = (cmd, cwd) => decide(winInput('Bash', { command: cmd }, cwd), win);
  for (const cmd of [
    'pnpm install',
    'pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs',
    'dotnet ef migrations add Init --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api',
    'uv run mutalaa ingest tanzil --variant uthmani',
    'curl -s http://localhost:8333/mutalaa/dev/manifest.json',
    'adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"',
    'docker compose cp postgres:/tmp/mutalaa.dump data/backups/mutalaa.dump',
    'git log --oneline HEAD~3..HEAD',
    'node --test .claude/hooks/test/ 2>/dev/null',
    `node "${WIN_ROOT}\\.claude\\hooks\\klasor-bekcisi.mjs"`,
    '"/c/Users/MEHMET SAİD/OneDrive/Masaüstü/mutalaa-docs/apps/mobile"',
    'git diff -- docs/',
  ]) {
    assert.equal(none(cmd), null, cmd);
  }
  assert.equal(none('cat ../README.md', `${WIN_ROOT}\\docs`), null);
});

test('PowerShell aracı da denetlenir', () => {
  const r = decide(winInput('PowerShell', { command: 'Get-Content $env:USERPROFILE\\x.txt' }), win);
  assert.equal(decision(r), 'ask');
  assert.equal(decide(winInput('PowerShell', { command: 'Get-ChildItem docs' }), win), null);
});

test('Okuma araçlarına karışmaz', () => {
  assert.equal(decide(winInput('Read', { file_path: 'D:\\x.txt' }), win), null);
  assert.equal(decide(winInput('Grep', { pattern: 'x', path: 'D:\\' }), win), null);
});

test('POSIX: yazma sınırı ve komut taraması', () => {
  assert.equal(decide(posixInput('Write', { file_path: `${POSIX_ROOT}/a.ts` }), posix), null);
  assert.equal(decision(decide(posixInput('Write', { file_path: '/home/erdem/diger/a.ts' }), posix)), 'deny');
  assert.equal(decision(decide(posixInput('Write', { file_path: '/tmp/x' }), posix)), 'deny');
  assert.equal(decision(decide(posixInput('Bash', { command: 'cat /etc/passwd' }), posix)), 'ask');
  assert.equal(decide(posixInput('Bash', { command: 'ls /tmp/x && echo ok > /dev/null' }), posix), null);
  assert.equal(decide(posixInput('Bash', { command: `ls ${POSIX_ROOT}/apps` }), posix), null);
});

test('tokenize tırnak ve işleçlere uyar', () => {
  assert.deepEqual(tokenize('a "b c" d'), ['a', 'b c', 'd']);
  assert.deepEqual(tokenize('x>y'), ['x', 'y']);
  assert.ok(tokenize('--out=../a').includes('../a'));
});

test('scanCommand ev klasörü başvurularını ayrı döndürür', () => {
  const rootC = canonical(WIN_ROOT, { platform: 'win32', realpath: () => null, cwd: WIN_ROOT });
  const r = scanCommand('ls ~ && dir C:\\Windows', { rootC, cwd: WIN_ROOT, platform: 'win32', realpath: () => null });
  assert.deepEqual(r.homeRefs, ['~']);
  assert.deepEqual(r.outside, ['C:\\Windows']);
});

// --- Kabuk komutlarının proje içindeki etkileri, Windows ayrıntıları, git ---

const winDecision = (cmd, cwd, tool = 'Bash') => decision(decide(winInput(tool, { command: cmd }, cwd), win));

test('Windows: ortam değişkeniyle ev ve geçici klasör başvurusu onay ister', () => {
  for (const cmd of [
    'cp x "$USERPROFILE/Desktop/x"',
    'echo x > "${TEMP}/a.txt"',
    'ls $LOCALAPPDATA',
    'cat $OneDrive/notlar.txt',
    'cd',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
  assert.equal(winDecision('echo $TEMPLATE_DIR'), null);
});

test('Windows: Git Bash kökleri proje dışıdır; seçenekler yol sayılmaz', () => {
  assert.equal(winDecision('echo x > /tmp/a.txt'), 'ask');
  assert.equal(winDecision('cp a.txt /usr/local/a.txt'), 'ask');
  assert.equal(winDecision('cmd /c dir'), null);
  assert.equal(winDecision('taskkill /f /im node.exe'), null);
  assert.equal(winDecision('dotnet build server/Mutalaa.slnx /p:TreatWarningsAsErrors=true'), null);
  assert.equal(winDecision('ls /d'), 'ask');
});

test('Kabukla korunan yere yazma: data/raw ve .git reddedilir', () => {
  for (const cmd of [
    'cp a.json data/raw/',
    'mv data/raw/tanzil/x.txt .tmp/',
    'echo x >> data/raw/not.txt',
    'touch data/raw/x',
    'rm -Rf .git',
    'tee data/raw/a.txt < x',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  assert.equal(winDecision('cp data/raw/tanzil/x.txt .tmp/'), null, 'data/raw\'dan okumak serbest');
});

test('Kabukla kit ve karar defteri değişikliği onay ister', () => {
  for (const cmd of [
    'echo x >> docs/00-ozet/02-karar-defteri.md',
    "sed -i 's/a/b/' CLAUDE.md",
    'cp yeni.json .claude/settings.json',
    'cd docs/00-ozet && echo x >> 02-karar-defteri.md',
    'cat > .claude/skills/asama/SKILL.md <<EOF\nicerik\nEOF',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
});

test('Özyinelemeli silme ve geri dönüşü zor git işlemleri onay ister', () => {
  for (const cmd of [
    'rm -fr build-tmp',
    'rm -r -f x',
    'xargs rm -rf < liste.txt',
    'git commit --amend -m x',
    'git commit -m x --no-verify',
    'git stash drop',
    'git branch -D eski',
    'git switch --discard-changes main',
    'git checkout -- src/a.ts',
    'git -C . reset --hard',
    'git push origin main',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
  for (const cmd of ['git commit -m "feat(api): add x"', 'git switch -c yeni', 'git stash', 'git checkout -b dal', 'rm .tmp/a.png']) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Heredoc gövdesi komut sayılmaz; kabuğa verilen gövde taranır', () => {
  assert.equal(winDecision("cat > .tmp/x.md <<'EOF'\na > data/raw/b\nrm -rf /\nEOF"), null);
  assert.equal(winDecision("bash <<'EOF'\nrm -rf data/raw\nEOF"), 'deny');
  assert.equal(winDecision('cat <<< "x" && echo y > data/raw/z'), 'deny');
});

test('Monitor aracı kabuk gibi denetlenir', () => {
  assert.equal(winDecision('tail -f $TEMP/log.txt', WIN_ROOT, 'Monitor'), 'ask');
  assert.equal(winDecision('tail -f .tmp/log.txt', WIN_ROOT, 'Monitor'), null);
  assert.equal(decide(winInput('Monitor', { ws: { url: 'ws://localhost:1' } }), win), null);
});

test('PowerShell dosya komutları da denetlenir', () => {
  assert.equal(winDecision('Set-Content -Path CLAUDE.md -Value x', WIN_ROOT, 'PowerShell'), 'ask');
  assert.equal(winDecision('Remove-Item -Recurse -Force .tmp\\eski', WIN_ROOT, 'PowerShell'), 'ask');
  assert.equal(winDecision('Copy-Item a.txt -Destination data\\raw\\a.txt', WIN_ROOT, 'PowerShell'), 'deny');
});

test('&&, ||, & ve | sonraki komutu ayırır; komut kaybolmaz', () => {
  for (const cmd of [
    'git status && git push origin main',
    'pnpm test || git reset --hard',
    'echo a && rm -rf build-tmp',
    'sleep 1 & git clean -fd',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
  assert.equal(winDecision('true && cp a.txt data/raw/a.txt'), 'deny');
  assert.equal(winDecision('cd pipeline && uv run pytest && cd ..'), null);
  assert.equal(winDecision('cd pipeline && cd ../..'), 'ask');
  assert.equal(winDecision('pnpm lint && pnpm test'), null);
});

test('Alt kabuktaki ve komut yerine koymadaki cd dışarıdaki komutları etkilemez', () => {
  assert.equal(winDecision('(cd pipeline && uv run pytest) && dotnet publish server/Mutalaa.Api -o ../yayin'), 'ask');
  assert.equal(winDecision('(cd pipeline && uv run pytest) && echo x > data/raw/y'), 'deny');
  assert.equal(winDecision('echo $(cd pipeline && pwd) > data/raw/z'), 'deny');
  assert.equal(winDecision('echo `cd pipeline; pwd` && cp a.txt ../b.txt'), 'ask');
  assert.equal(winDecision('(cd pipeline && cat ../CLAUDE.md)'), null);
  assert.equal(winDecision('cd pipeline && (cd src && ls) && cat ../pyproject.toml'), null);
});

test('>& dosya ve < dosya yönlendirmeleri yol taramasına girer', () => {
  assert.equal(winDecision('echo x >& ../disari.txt'), 'ask');
  assert.equal(winDecision('cat < ../gizli.txt'), 'ask');
  assert.equal(winDecision('pnpm test > .tmp/test.log 2>&1'), null);
  assert.equal(winDecision('echo x >&2'), null);
  assert.equal(winDecision('psql -At < .tmp/a03-kontrol.sql'), null);
});

test('Adı .. ile başlayan proje içi klasör içeride sayılır', () => {
  assert.equal(decide(winInput('Write', { file_path: `${WIN_ROOT}\\..notlar\\a.md` }), win), null);
  assert.equal(decision(decide(winInput('Write', { file_path: `${WIN_ROOT}\\..\\a.md` }), win)), 'deny');
});
