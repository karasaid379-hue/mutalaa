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

test('Windows: kit ve karar defteri değişikliği serbesttir (kullanıcı yönergesi, 27 Ekim 2026)', () => {
  for (const rel of [
    'CLAUDE.md',
    '.claude\\settings.json',
    '.claude\\settings.local.json',
    '.claude\\skills\\asama\\SKILL.md',
    '.claude\\agents\\inceleyici.md',
    '.claude\\hooks\\lib\\bekci.mjs',
    '.claude\\rules\\mobil.md',
    'docs\\00-ozet\\02-karar-defteri.md',
    'docs\\10-claude-code\\05-ilerleme.md',
  ]) {
    assert.equal(decide(winInput('Edit', { file_path: `${WIN_ROOT}\\${rel}` }), win), null, rel);
  }
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

test('Kabukla kit ve karar defteri değişikliği serbesttir', () => {
  for (const cmd of [
    'echo x >> docs/00-ozet/02-karar-defteri.md',
    "sed -i 's/a/b/' CLAUDE.md",
    'cp yeni.json .claude/settings.json',
    'cd docs/00-ozet && echo x >> 02-karar-defteri.md',
    'cat > .claude/skills/asama/SKILL.md <<EOF\nicerik\nEOF',
  ]) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Git ve silme işleri onay istemez (kural 11, kullanıcı yönergesi)', () => {
  for (const cmd of [
    'rm -fr build-tmp',
    'rm -r -f x',
    'xargs rm -rf < liste.txt',
    'git commit --amend -m x',
    'git stash drop',
    'git stash clear',
    'git branch -D eski',
    'git switch --discard-changes main',
    'git checkout -- src/a.ts',
    'git -C . reset --hard',
    'git reset --hard HEAD~1',
    'git restore src/a.ts',
    'git rebase main',
    'git clean -fd',
    'git push origin main',
    'git push -u origin chore/a08-ci-workflows',
    'git push origin --delete chore/a08-ci-workflows',
    'git commit -m "feat(api): add x"',
    'git switch -c yeni',
    'git checkout -b dal',
    'rm .tmp/a.png',
  ]) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Nadir geri dönüşsüz git işleri ve --no-verify sorulur', () => {
  for (const cmd of [
    'git commit -m x --no-verify',
    'git filter-branch --all',
    'git filter-repo --path x',
    'git update-ref -d refs/heads/x',
    'git gc --prune=now',
    'git reflog expire --all',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
});

test('Zorla push, main silme ve git clean -x kesin yasaktır', () => {
  for (const cmd of [
    'git push --force origin main',
    'git push -f',
    'git push origin main --force',
    'git push -fu origin x',
    'git push --force-with-lease origin main',
    'git push --force-with-lease=main origin main',
    'git push --force-if-includes origin x',
    'git push --mirror',
    'git push origin +main',
    'git push origin :main',
    'git push origin --delete main',
    'git push -d origin refs/heads/main',
    'git -C . push --force',
    'git clean -fdx',
    'git clean -fX',
    'git status && git push --force origin main',
    'pnpm test || git clean -xfd',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
});

test('mobile-v* etiketi itmek ücretli EAS derlemesi başlatır: sorulur', () => {
  for (const cmd of [
    'git push origin mobile-v1.0.0',
    'git push origin refs/tags/mobile-v1.0.0',
    'git push --tags',
    'git push --follow-tags origin main',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
  assert.equal(winDecision('git push origin v1.0.0'), null);
});

test('data/raw, data/gold ve data/backups silinemez; üst klasörleri de', () => {
  for (const cmd of [
    'rm -rf data/gold',
    'rm -rf data/backups/x.dump',
    'rm data/raw/tanzil/x.txt',
    'rm -rf data',
    'rm -rf data/',
    'rm -rf .',
    'rm -rf ./',
    'rm -rf *',
    'rm -rf data/*',
    'rm -rf data/g*',
    'rmdir data/gold',
    'cd data && rm -rf gold',
    'cd data/gold && rm -rf *',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  for (const cmd of ['rm -rf build-tmp', 'rm -rf .tmp/*', 'rm -rf data/staged/x', 'rm -rf data/packs', 'rm -f packages/anchors/dist/a.js']) {
    assert.equal(winDecision(cmd), null, cmd);
  }
  assert.equal(winDecision('cp data/gold/a.json .tmp/'), null, 'okumak serbest');
  assert.equal(winDecision('echo x >> data/backups/not.txt'), null, 'yedek klasörüne yazmak serbest');
});

test('Gizli değer dosyalarına kabuktan erişim yasaktır; varlık denetimi serbesttir', () => {
  for (const cmd of [
    'cat .env',
    'cat infra/local/.env',
    'head -n 3 .env.local',
    'grep PASSWORD .env',
    'cp .env .tmp/e',
    'mv .env x',
    'echo x > .env',
    'echo x >> pipeline/.env',
    'cat < .env',
    'source .env',
    'cat infra/local/s3.json',
    'cat server/keys/dev.pem',
    'cp keys/private.key .tmp/',
    'bash -c "cat .env"; cat .env',
    'dotnet user-secrets list --project server/Mutalaa.Api',
    'env',
    'printenv',
    'set',
    'FOO=1 env',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  for (const cmd of [
    'cat .env.example',
    'cat infra/local/s3.example.json',
    'test -f .env && echo var',
    '[ -f pipeline/.env ] && echo var',
    'ls -la .env',
    'git check-ignore -v .env',
    'git status --short .env',
    'git ls-files --error-unmatch .env.example',
    'git commit -m "docs: mention infra/local/.env in the guide"',
    'echo "see infra/local/.env"',
    'env FOO=1 node x.mjs',
    'printenv HOME_FAKE',
    'dotnet user-secrets set X y --project server/Mutalaa.Api',
    'dotnet user-secrets init --project server/Mutalaa.Api',
    'grep -n monkey docs/a.md',
    'echo monkey.key',
    'pnpm test -- t.key',
  ]) {
    assert.notEqual(winDecision(cmd), 'deny', cmd);
  }
});

test('eas submit ve yayımlama her biçimde yasak; ücretli EAS işi sorulur', () => {
  for (const cmd of [
    'eas submit --platform android',
    'npx eas-cli submit',
    'npx eas-cli@latest submit',
    'pnpm exec eas submit',
    'pnpm dlx eas-cli submit',
    'pnpm --filter @mutalaa/mobile exec eas submit',
    'npm publish',
    'pnpm publish -r',
    'pnpm --filter @mutalaa/anchors publish',
    'pnpm exec npm publish',
    'yarn publish',
    'dotnet nuget push a.nupkg',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  for (const cmd of [
    'eas build --profile internal',
    'npx eas-cli build --platform all',
    'pnpm exec eas update --branch x',
    'eas build:run',
  ]) {
    assert.equal(winDecision(cmd), 'ask', cmd);
  }
  for (const cmd of ['eas build:list', 'eas build:view 123', 'eas whoami', 'dotnet publish server/Mutalaa.Api -o .tmp/yayin', 'grep -rn eas docs']) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Veri silen işlerden önce yedek şart (kural 11)', () => {
  const backup = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1';
  for (const cmd of [
    'docker compose down -v',
    'docker compose down --volumes',
    'docker-compose down -v',
    'docker volume rm mutalaa_pgdata',
    'docker volume prune -f',
    'dotnet ef database drop --force --project server/Mutalaa.Infrastructure',
    'docker compose exec postgres psql -U x -c "DROP SCHEMA icerik CASCADE"',
    'docker compose exec postgres psql -U x -c "drop database mutalaa"',
    `docker compose down -v && ${backup}`,
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  for (const cmd of [
    `${backup} && docker compose down -v`,
    `${backup} && docker compose exec postgres psql -U x -c "DROP SCHEMA icerik CASCADE"`,
    'docker compose down',
    'docker compose up -d',
    'git commit -m "docs: explain DROP SCHEMA backup rule"',
    'echo "DROP DATABASE needs a backup"',
  ]) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Denetçi ajanlar salt okunurdur (hook girdisindeki agent_type)', () => {
  const as = (agent, cmd) => decision(decide({ ...winInput('Bash', { command: cmd }), agent_type: agent }, win));
  for (const agent of ['inceleyici', 'metin-denetcisi', 'lisans-denetcisi', 'arayuz-denetcisi', 'arastirmaci']) {
    for (const cmd of ['echo x > docs/a.md', 'rm src/a.ts', 'sed -i s/a/b/ CLAUDE.md', 'git commit -m x', 'git push origin main', 'git add .', 'git checkout -- a', 'cp a.txt b.txt']) {
      assert.equal(as(agent, cmd), 'deny', `${agent}: ${cmd}`);
    }
    for (const cmd of ['git status --short', 'git diff', 'git log --oneline -3', 'node --test .claude/hooks/test/', 'echo x > .tmp/a.txt', 'cat docs/a.md', 'dotnet test --solution server/Mutalaa.slnx']) {
      assert.equal(as(agent, cmd), null, `${agent}: ${cmd}`);
    }
  }
  assert.equal(as('belge-bekcisi', 'echo x > docs/a.md'), null, 'yazan ajanlar etkilenmez');
  assert.equal(as(undefined, 'git commit -m x'), null, 'ana oturum etkilenmez');
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
  assert.equal(winDecision('Set-Content -Path CLAUDE.md -Value x', WIN_ROOT, 'PowerShell'), null);
  assert.equal(winDecision('Remove-Item -Recurse -Force .tmp\\eski', WIN_ROOT, 'PowerShell'), null);
  assert.equal(winDecision('Remove-Item -Recurse -Force data\\gold', WIN_ROOT, 'PowerShell'), 'deny');
  assert.equal(winDecision('Copy-Item a.txt -Destination data\\raw\\a.txt', WIN_ROOT, 'PowerShell'), 'deny');
});

test('&&, ||, & ve | sonraki komutu ayırır; komut kaybolmaz', () => {
  for (const cmd of [
    'git status && git push --force origin main',
    'pnpm test || git clean -fdx',
    'echo a && rm -rf data/gold',
    'sleep 1 & git push -f origin x',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
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

test('Kabuk sarmalayıcıları yasakları aşamaz: bash -c, eval, cmd /c, powershell -Command', () => {
  for (const cmd of [
    'bash -c "git push -f"',
    "sh -c 'rm -rf data/gold'",
    'bash -c "cat .env"',
    'bash -lc "git push --force origin main"',
    'eval "eas submit"',
    'cmd /c "rd /s /q data\\gold"',
    'powershell -Command "Remove-Item -Recurse data\\gold"',
    'wsl rm -rf data/gold',
    'bash -c "bash -c \'git push -f\'"',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  assert.equal(winDecision('bash -c "echo merhaba"'), null);
  assert.equal(winDecision('bash -c "git status"'), null);
});

test('Çalıştırıcılar ve sarmalayıcılar yasakları aşamaz: timeout, env -i, pnpm exec, uv run, npx', () => {
  for (const cmd of [
    'timeout 5 git push -f',
    'env -i git push --force',
    'nice -n5 rm -rf data/gold',
    'command -p git push -f',
    'pnpm exec rm -rf data/gold',
    'pnpm --filter x exec git push -f',
    'uv run git push -f',
    'npx rimraf data/gold',
    'npx -p eas-cli eas submit',
    'timeout 5 npm publish',
    'corepack pnpm publish',
    'xargs -n1 git push -f',
    'find data -delete',
    'find data/gold -exec rm -rf {} +',
    'mv data/gold .tmp/x',
    'mv data x',
    'uv publish',
    'twine upload dist/*',
    'docker push x/y',
    'eas build --auto-submit',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
});

test('Kabuk sözdizimi yasakları aşamaz: anahtar sözcükler, kaçışlar, küme açılımı', () => {
  for (const cmd of [
    '{ git push -f; }',
    'if true; then git push -f; fi',
    'for i in 1; do rm -rf data/gold; done',
    '! rm -rf data/gold',
    'gi\\t push -f',
    'r\\m -rf data/gold',
    'rm -rf data/g\\old',
    'rm -rf data/{raw,gold}',
    'rm -rf data/{g,r}*',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  // Komut adı değişkenden geliyorsa hook göremez: sorulur.
  assert.equal(winDecision('$g push origin main'), 'ask');
  assert.equal(winDecision('rm${IFS}-rf${IFS}x'), 'ask');
});

test('git yapılandırmasıyla yasaklar aşılamaz: takma ad, kanca, uzak push kuralı, kısaltmalar', () => {
  for (const cmd of [
    "git -c alias.p='push --force' p",
    'git -c core.hooksPath=/dev/null commit -m x',
    'git -c remote.origin.push=+HEAD:main push origin',
    'git config alias.x "push -f"',
    'git config remote.origin.push +HEAD:main',
    'git push --force-w origin main',
    'git push --mirr',
    'git push origin --del main',
    'git stash --all',
    'git stash -a',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  assert.equal(winDecision('git commit -nm x'), 'ask');
  assert.equal(winDecision('git push origin "refs/tags/mobile-*"'), 'ask');
  for (const cmd of ['git clean -nx', 'git clean -n -x', 'git clean --dry-run -fdx', 'git config user.name x', 'git config --get user.name', 'git stash', 'git stash pop', 'git -c user.name=x commit -m y']) {
    assert.equal(winDecision(cmd), null, cmd);
  }
});

test('Gizli değer dosyası: glob, ortam dökümü ve compose config', () => {
  for (const cmd of [
    'cat .e*',
    'cat .en?',
    'cat .e[n]v',
    'tail -n+1 .e[n]v',
    'cat .e{n,n}v',
    'cat s3*',
    'cat /proc/self/environ',
    'env -0',
    'env -u X',
    'printenv -0',
    'export -p',
    'declare -p',
    'compgen -e',
    'docker compose config',
    'docker compose -f docker-compose.yml config',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
});

test('Günlük işi bozmayan yanlış pozitif düzeltmeleri', () => {
  for (const cmd of [
    'grep -rn "\\.env" docs',
    "rg '\\.env' docs",
    "sed -i '/\\.env/d' .gitignore",
    'rg "event.key" apps',
    'grep -rn "item.key" apps',
    "rg --glob '!**/.env' x",
    'git log --grep=.env',
    'git diff -- .env.example',
    'git clean -nx',
    'cat *',
    'ls *',
    'grep -rn x *',
    'pnpm exec dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev',
    'npm run publish',
    "sed -n '/DROP SCHEMA/p' docs/a.md",
    'docker compose config -q',
    'docker compose config --services',
    'env FOO=1 node x.mjs',
    'rg -n timeout',
  ]) {
    assert.notEqual(winDecision(cmd), 'deny', cmd);
  }
});

test('Yedek yalnız gerçekten çalıştırılan komutla sayılır', () => {
  for (const cmd of [
    'echo backup-db.ps1; docker compose down -v',
    'ls scripts/backup-db.ps1; docker compose down -v',
    'docker compose down --volumes=true',
    'docker system prune --volumes -f',
    'docker compose rm -v',
    'dropdb mutalaa',
  ]) {
    assert.equal(winDecision(cmd), 'deny', cmd);
  }
  assert.equal(
    winDecision('powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1 && docker compose down -v'),
    null,
  );
});

test('Denetçi ajanlar: ad alanı öneki, yalnız okuyan git, çıktı dosyası seçenekleri', () => {
  const as = (agent, cmd) => decision(decide({ ...winInput('Bash', { command: cmd }), agent_type: agent }, win));
  for (const cmd of ['git config user.name x', 'git submodule update', 'git diff --output=docs/a.md', 'curl -o docs/a.md http://x', 'tar -xf a.tar', 'patch -p1', 'git stash']) {
    assert.equal(as('inceleyici', cmd), 'deny', cmd);
  }
  assert.equal(as('plugin:inceleyici', 'echo x > docs/a.md'), 'deny', 'ad alanı öneki soyulur');
  for (const cmd of ['git status', 'git diff HEAD~1', 'git log --oneline', 'git show HEAD:docs/a.md', 'git grep x', 'git ls-files']) {
    assert.equal(as('inceleyici', cmd), null, cmd);
  }
});

test('Adı .. ile başlayan proje içi klasör içeride sayılır', () => {
  assert.equal(decide(winInput('Write', { file_path: `${WIN_ROOT}\\..notlar\\a.md` }), win), null);
  assert.equal(decision(decide(winInput('Write', { file_path: `${WIN_ROOT}\\..\\a.md` }), win)), 'deny');
});
