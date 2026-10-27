// Kitin kendi kendini denetlemesi: ajan, beceri ve kural ön bilgisi, ayarlar,
// aşama dosyaları, ilerleme dosyası ve bağlantılar.
// Çalıştırma (proje kökünden): node --test ".claude/hooks/test/*.test.mjs"

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { checkFile as checkLinks } from '../../skills/belge-esitle/baglanti-denetimi.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const at = (...p) => path.join(ROOT, ...p);
const read = (...p) => fs.readFileSync(at(...p), 'utf8');

// Claude Code 2.1.30x'te tanınan ön bilgi alanları ve araç adları.
const AGENT_KEYS = new Set(['name', 'description', 'tools', 'disallowedTools', 'model', 'effort', 'permissionMode',
  'mcpServers', 'hooks', 'maxTurns', 'autoCompactWindow', 'skills', 'initialPrompt', 'memory', 'background',
  'omitClaudeMd', 'isolation', 'color']);
const SKILL_KEYS = new Set(['name', 'description', 'when_to_use', 'argument-hint', 'arguments',
  'disable-model-invocation', 'user-invocable', 'allowed-tools', 'disallowed-tools', 'model', 'effort', 'context',
  'agent', 'background', 'hooks', 'paths', 'shell', 'metadata', 'license', 'compatibility']);
const TOOLS = new Set(['Read', 'Write', 'Edit', 'NotebookEdit', 'Glob', 'Grep', 'Bash', 'PowerShell', 'Monitor', 'LSP',
  'WebFetch', 'WebSearch', 'Skill', 'Agent', 'TodoWrite', 'TaskCreate', 'TaskGet', 'TaskList', 'TaskUpdate',
  'TaskStop', 'ToolSearch', 'EnterWorktree', 'ExitWorktree', 'SendMessage']);
const COLORS = new Set(['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan']);
const MODELS = new Set(['inherit', 'sonnet', 'opus', 'haiku', 'fable']);

/**
 * Kitte kullanılan YAML alt kümesini ayrıştırır: düz değer, tırnaklı değer, `>-`/`|` blok ve `- öğe` listesi.
 * Düz değerde ": " ya da " #" varsa hata verir (gerçek YAML ayrıştırıcısı ön bilgiyi bozuk sayar).
 */
function parseFrontmatter(text, file) {
  const src = text.replace(/\r\n/g, '\n');
  assert.ok(src.startsWith('---\n'), `${file}: ön bilgi yok`);
  const end = src.indexOf('\n---\n', 3);
  assert.ok(end > 0, `${file}: ön bilgi kapanmamış`);
  const lines = src.slice(4, end).split('\n');
  const data = {};
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') continue;
    const m = /^([A-Za-z][\w-]*):(?: (.*))?$/.exec(line);
    assert.ok(m, `${file}: anlaşılmayan satır: ${line}`);
    const [, key, rawValue = ''] = m;
    const value = rawValue.trim();
    if (value === '' || value === '>-' || value === '>' || value === '|' || value === '|-') {
      const block = [];
      while (i + 1 < lines.length && /^\s+/.test(lines[i + 1])) block.push(lines[++i]);
      if (value === '') {
        assert.ok(block.every((b) => /^\s+- /.test(b)), `${file}: ${key} listesi bozuk`);
        data[key] = block.map((b) => b.replace(/^\s+- /, '').trim().replace(/^["']|["']$/g, ''));
      } else {
        data[key] = block.map((b) => b.trim()).join(' ');
      }
      continue;
    }
    if (/^".*"$/.test(value) || /^'.*'$/.test(value)) {
      data[key] = value.slice(1, -1);
      continue;
    }
    assert.ok(!/: /.test(value) && !/ #/.test(value), `${file}: ${key} düz değeri ": " ya da " #" içeriyor; tırnakla ya da >- kullan`);
    assert.ok(!/^[[{&*!|>%@`]/.test(value), `${file}: ${key} YAML özel karakteriyle başlıyor; tırnakla`);
    data[key] = value;
  }
  return { data, body: src.slice(end + 5) };
}

const list = (v) => (Array.isArray(v) ? v : String(v).split(',').map((s) => s.trim()).filter(Boolean));

const skillDirs = fs.readdirSync(at('.claude', 'skills'), { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);
const skills = new Map(
  skillDirs.map((name) => [name, parseFrontmatter(read('.claude', 'skills', name, 'SKILL.md'), `skills/${name}`)]),
);

test('beceriler: ad, açıklama, bilinen alanlar, enjeksiyon yok', () => {
  assert.ok(skills.size >= 16, `beceri sayısı ${skills.size}`);
  for (const [name, { data, body }] of skills) {
    for (const k of Object.keys(data)) assert.ok(SKILL_KEYS.has(k), `skills/${name}: bilinmeyen alan ${k}`);
    assert.equal(data.name, name, `skills/${name}: name klasör adıyla aynı olmalı`);
    assert.match(name, /^[a-z][a-z0-9-]*$/);
    assert.ok(data.description && data.description.length <= 1536, `skills/${name}: açıklama boş ya da uzun`);
    if ('disable-model-invocation' in data) assert.match(data['disable-model-invocation'], /^(true|false)$/);
    assert.ok(!/(^|\s)!`/.test(body), `skills/${name}: dinamik komut enjeksiyonu kullanma`);
    assert.ok(body.split('\n').length <= 500, `skills/${name}: 500 satırı aşıyor`);
  }
});

test('ajanlar: ad, açıklama, araçlar, model, renk, önceden yüklenen beceriler', () => {
  const files = fs.readdirSync(at('.claude', 'agents')).filter((f) => f.endsWith('.md'));
  assert.ok(files.length >= 11, `ajan sayısı ${files.length}`);
  for (const f of files) {
    const { data } = parseFrontmatter(read('.claude', 'agents', f), `agents/${f}`);
    const name = f.slice(0, -3);
    for (const k of Object.keys(data)) assert.ok(AGENT_KEYS.has(k), `agents/${f}: bilinmeyen alan ${k}`);
    assert.equal(data.name, name);
    assert.match(name, /^[a-z][a-z0-9-]*$/);
    assert.ok(data.description, `agents/${f}: açıklama yok`);
    for (const key of ['tools', 'disallowedTools']) {
      if (data[key] === undefined) continue;
      for (const t of list(data[key])) assert.ok(TOOLS.has(t), `agents/${f}: bilinmeyen araç ${t}`);
    }
    if (data.model !== undefined) assert.ok(MODELS.has(data.model), `agents/${f}: model ${data.model}`);
    if (data.color !== undefined) assert.ok(COLORS.has(data.color), `agents/${f}: renk ${data.color}`);
    for (const s of data.skills ?? []) {
      assert.ok(skills.has(s), `agents/${f}: beceri yok ${s}`);
      assert.notEqual(skills.get(s).data['disable-model-invocation'], 'true', `agents/${f}: ${s} önceden yüklenemez`);
    }
  }
});

test('kurallar: yalnız paths alanı ve liste', () => {
  for (const f of fs.readdirSync(at('.claude', 'rules')).filter((x) => x.endsWith('.md'))) {
    const { data } = parseFrontmatter(read('.claude', 'rules', f), `rules/${f}`);
    assert.deepEqual(Object.keys(data), ['paths'], `rules/${f}`);
    assert.ok(Array.isArray(data.paths) && data.paths.length > 0, `rules/${f}: paths listesi`);
  }
});

test('settings.json: geçerli JSON, kip, okuma sınırı, hook betikleri var', () => {
  const s = JSON.parse(read('.claude', 'settings.json'));
  assert.ok(['default', 'manual', 'acceptEdits', 'plan', 'dontAsk'].includes(s.permissions.defaultMode));
  assert.equal(s.permissions.blockReadsOutsideWorkingDirectories, true);
  assert.equal(s.autoMemoryEnabled, false);
  assert.equal(s.enableArtifact, false, 'proje dışındaki karalama klasörü kapalı olmalı');
  assert.equal(s.env.CLAUDE_CODE_USE_POWERSHELL_TOOL, '0', 'komutlar yalnız Git Bash ile');
  for (const k of ['ASPNETCORE_ENVIRONMENT', 'DOTNET_ENVIRONMENT']) {
    assert.equal(s.env[k], 'Development', `${k}: kullanıcı sırları yalnız Development ortamında yüklenir`);
  }
  for (const r of ['Read(**/.env)', 'Read(**/.env.*)', 'Read(!**/.env.example)', 'Edit(**/.env)', 'Edit(**/.env.local)', 'Edit(/data/raw/**)']) {
    assert.ok(s.permissions.deny.includes(r), `deny: ${r}`);
  }
  assert.ok(s.permissions.deny.indexOf('Read(!**/.env.example)') > s.permissions.deny.indexOf('Read(**/.env.*)'));
  // Politika (27 Ekim 2026): terminal komutları sorulmaz (yalın Bash), kesin yasaklar deny'dadır,
  // ücretli EAS işi ve proje dışına yazan kurulumlar sorulur. Klasör bekçisi git ve silme korumalarını taşır.
  assert.ok(s.permissions.allow.includes('Bash'), 'allow: yalın Bash');
  for (const r of ['Bash(git push --force *)', 'Bash(git push -f *)', 'Bash(git push --force-with-lease *)', 'Bash(eas submit *)', 'Bash(npm publish *)', 'Bash(pnpm publish *)', 'Bash(dotnet nuget push *)']) {
    assert.ok(s.permissions.deny.includes(r), `deny: ${r}`);
  }
  for (const r of ['Bash(eas build *)', 'Bash(eas update *)', 'WebFetch', 'WebSearch']) assert.ok(s.permissions.ask.includes(r), `ask: ${r}`);
  for (const r of ['WebFetch', 'WebSearch']) assert.ok(!s.permissions.allow.includes(r), `web erişimi sorulmalı: ${r}`);
  for (const r of ['Bash(git push *)', 'Bash(git reset *)', 'Bash(rm -rf *)', 'Bash(git rebase *)']) {
    assert.ok(!s.permissions.ask.includes(r) && !s.permissions.deny.includes(r), `onaysız olmalı: ${r}`);
  }
  const pre = s.hooks.PreToolUse[0];
  for (const tool of ['Write', 'Edit', 'NotebookEdit', 'Bash', 'PowerShell', 'Monitor']) {
    assert.ok(pre.matcher.split('|').includes(tool), `PreToolUse eşleyicisi: ${tool}`);
  }
  assert.equal(pre.hooks[0].onFailure, 'block', 'klasör bekçisi çalışamazsa işlem durmalı');
  for (const rule of [...s.permissions.allow, ...s.permissions.ask, ...s.permissions.deny]) {
    assert.match(rule, /^(Bash|PowerShell|Read|Edit|WebFetch)(\(.+\))?$|^WebSearch$/, `kural biçimi: ${rule}`);
    assert.ok(!rule.startsWith('Write('), `Write(...) kuralı denetlenmez; Read/Edit kullan: ${rule}`);
  }
  for (const [event, groups] of Object.entries(s.hooks)) {
    for (const g of groups) {
      for (const h of g.hooks) {
        assert.equal(h.type, 'command', event);
        assert.equal(h.command, 'node', `${event}: exec biçimi node ile`);
        assert.ok(Array.isArray(h.args) && h.args.length === 1, `${event}: args`);
        const rel = h.args[0].replace('${CLAUDE_PROJECT_DIR}/', '');
        assert.ok(fs.existsSync(at(...rel.split('/'))), `${event}: betik yok ${rel}`);
      }
    }
  }
});

const STAGES = Array.from({ length: 41 }, (_, i) => `A${String(i).padStart(2, '0')}`);
const stageFiles = fs.readdirSync(at('docs', '10-claude-code', 'asamalar')).filter((f) => f.endsWith('.md'));

test('aşama dosyaları: A00–A40 var ve zorunlu bölümleri taşıyor', () => {
  for (const id of STAGES) {
    const matches = stageFiles.filter((f) => f.startsWith(`${id}-`));
    assert.equal(matches.length, 1, `${id} için tek dosya olmalı (bulunan: ${matches.join(', ')})`);
    const text = read('docs', '10-claude-code', 'asamalar', matches[0]);
    assert.ok(text.startsWith(`# ${id} · `), `${matches[0]}: başlık "# ${id} · …" olmalı`);
    for (const h of ['## Amaç', '## Okunacak belgeler', '## Kapsam', '## Adımlar', '## Kabul ölçütleri', '## Doğrulama', '## İlgili dosyalar']) {
      assert.ok(text.includes(`\n${h}`), `${matches[0]}: "${h}" bölümü yok`);
    }
    assert.ok(text.includes(`/asama ${id}`), `${matches[0]}: başlatma komutu yok`);
  }
});

test('ilerleme dosyası: durum işaretleri ve 41 aşama satırı', () => {
  const md = read('docs', '10-claude-code', '05-ilerleme.md');
  assert.ok(md.includes('<!-- durum:baslangic -->') && md.includes('<!-- durum:bitis -->'));
  for (const id of STAGES) assert.match(md, new RegExp(`^\\| ${id} \\|`, 'm'), `ilerleme: ${id} satırı yok`);
});

test('bağlantılar: docs, CLAUDE.md ve .claude içinde kırık bağlantı yok', () => {
  const files = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!['node_modules', '.git', '.tmp'].includes(e.name)) walk(p);
      } else if (e.name.endsWith('.md')) files.push(p);
    }
  };
  walk(at('docs'));
  walk(at('.claude'));
  files.push(at('CLAUDE.md'));
  const broken = files.flatMap((f) => checkLinks(f));
  assert.deepEqual(broken, []);
});

// Aşama haritası, aşama dosyası başlıkları, insan adımları ve belge çelişkileri birbiriyle tutarlı mı?
const MAP = read('docs', '10-claude-code', '04-asama-haritasi.md');
const mapRows = new Map(
  MAP.split('\n')
    .filter((l) => /^\| \[A\d\d\]/.test(l))
    .map((l) => {
      const cells = l.split('|').map((c) => c.trim());
      return [cells[1].slice(1, 4), { prereq: cells[4], human: cells[5] }];
    }),
);
const ids = (s, re) => new Set([...String(s).matchAll(re)].map((m) => m[0]));
const expandRange = (s) => {
  const out = new Set(ids(s, /A\d\d/g));
  for (const m of String(s).matchAll(/A(\d\d) … A(\d\d)/g)) {
    for (let i = Number(m[1]); i <= Number(m[2]); i++) out.add(`A${String(i).padStart(2, '0')}`);
  }
  return out;
};
const headerOf = (id) => {
  const f = stageFiles.find((x) => x.startsWith(`${id}-`));
  const line = read('docs', '10-claude-code', 'asamalar', f).split('\n').find((l) => l.startsWith('> **Faz:**'));
  assert.ok(line, `${f}: "> **Faz:**" satırı yok`);
  const [, onk = '', insan = ''] = /\*\*Önkoşul:\*\*(.*?)· \*\*İnsan adımı:\*\*(.*)$/.exec(line) ?? [];
  return { f, onk, insan };
};

test('aşama haritası: her aşamanın satırı var; önkoşul ve insan adımları aşama dosyasıyla aynı', () => {
  for (const id of STAGES) {
    const row = mapRows.get(id);
    assert.ok(row, `harita: ${id} satırı yok`);
    const { f, onk, insan } = headerOf(id);
    const linked = new Set([...onk.matchAll(/\[(A\d\d)\]\(/g)].map((m) => m[1]));
    assert.deepEqual([...linked].sort(), [...expandRange(row.prereq)].sort(), `${f}: önkoşullar haritayla farklı`);
    assert.deepEqual([...ids(insan, /İ-\d\d/g)].sort(), [...ids(row.human, /İ-\d\d/g)].sort(), `${f}: insan adımları haritayla farklı`);
  }
});

test('aşama haritası: bağımlılık grafiği tablodaki önkoşullarla uyumlu', () => {
  const graph = /```mermaid\n([\s\S]*?)```/.exec(MAP)[1];
  const edges = new Set();
  for (const line of graph.split('\n')) {
    const nodes = line.split('-->').map((s) => s.trim()).filter((s) => /^A\d\d$/.test(s));
    for (let i = 0; i + 1 < nodes.length; i++) edges.add(`${nodes[i]}>${nodes[i + 1]}`);
  }
  for (const e of edges) {
    const [a, b] = e.split('>');
    assert.ok(expandRange(mapRows.get(b).prereq).has(a), `grafik: ${a} --> ${b} tabloda yok`);
  }
  for (const [b, row] of mapRows) {
    if (b === 'A33') continue; // grafikte yalnız A32 --> A33 gösterilir (haritadaki not)
    for (const a of ids(row.prereq, /A\d\d/g)) assert.ok(edges.has(`${a}>${b}`), `grafik: ${a} --> ${b} eksik`);
  }
});

test('insan adımları: anılan her İ numarası listede var', () => {
  const list = read('docs', '10-claude-code', '06-insan-adimlari.md');
  const defined = ids(list.split('\n').filter((l) => /^\| İ-\d\d \|/.test(l)).join('\n'), /İ-\d\d/g);
  const files = [at('CLAUDE.md')];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith('.md')) files.push(p);
    }
  };
  walk(at('docs', '10-claude-code'));
  walk(at('.claude'));
  for (const f of files) {
    for (const i of ids(fs.readFileSync(f, 'utf8'), /İ-\d\d/g)) assert.ok(defined.has(i), `${path.relative(ROOT, f)}: ${i} insan adımları listesinde yok`);
  }
});

test('belge çelişkileri: numaralar tekil, aşamalar var, durumlar geçerli', () => {
  const md = read('docs', '10-claude-code', '07-belge-celiskileri.md');
  const rows = md.split('\n').filter((l) => /^\| BÇ-\d\d \|/.test(l));
  const seen = new Set();
  for (const l of rows) {
    const cells = l.split('|').map((c) => c.trim());
    const [no, , , , asama, durum] = cells.slice(1);
    assert.ok(!seen.has(no), `${no} iki kez var`);
    seen.add(no);
    for (const a of ids(asama, /A\d\d/g)) assert.ok(STAGES.includes(a), `${no}: aşama ${a} yok`);
    assert.match(durum, /^(açık|çözüldü \(\d{4}-\d{2}-\d{2}\))/, `${no}: durum "${durum}"`);
  }
});

test('PR başlığı denetimi: tür ve kapsam listesi Proje yapısı §6 ve /commit ile aynı', async () => {
  const { TYPES, SCOPES } = await import(pathToFileURL(at('scripts', 'ci', 'pr-title.mjs')).href);
  // Parantez içi açıklamaları (iç içe olanlar dahil) at, sonra kod biçimli sözcükleri al.
  const words = (text) => {
    let t = text;
    for (let prev = ''; prev !== t; ) {
      prev = t;
      t = t.replace(/\([^()]*\)/g, '');
    }
    return [...t.matchAll(/`([a-z][a-z-]*)`/g)].map((m) => m[1]);
  };
  const doc = read('docs', '02-mimari', '03-proje-yapisi.md');
  const line = doc.split('\n').find((l) => l.includes('Türler:') && l.includes('Kapsamlar:'));
  assert.ok(line, 'Proje yapısı §6: "Türler: … Kapsamlar: …" satırı yok');
  const [typeText, scopeText] = line.split('Kapsamlar:');
  assert.deepEqual(words(typeText.split('Türler:')[1]), TYPES, 'Proje yapısı §6 türleri');
  assert.deepEqual(words(scopeText.split('Squash')[0]), SCOPES, 'Proje yapısı §6 kapsamları');

  const skill = read('.claude', 'skills', 'commit', 'SKILL.md').split('\n');
  const types = skill.find((l) => l.startsWith('- **Türler:**'));
  const scopes = skill.find((l) => l.startsWith('- **Kapsamlar:**'));
  assert.deepEqual(words(types.split(':**')[1]), TYPES, '/commit türleri');
  assert.deepEqual(words(scopes.split(':**')[1]), SCOPES, '/commit kapsamları');
});
