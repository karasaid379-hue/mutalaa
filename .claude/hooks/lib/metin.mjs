// Mütâlaa · yazılan dosyanın biçim denetimi (yan etkisiz; testler bunu içe aktarır).
// Kurallar: docs/02-mimari/04-yerel-gelistirme.md §10.2 ve docs/02-mimari/03-proje-yapisi.md §5.
//   - Dosyalar BOM'suz UTF-8'dir.
//   - Satır sonu LF'dir; yalnız .ps1, .cmd, .bat CRLF olabilir.
//   - Depodaki dosya adları ASCII'dir.
//   - JSON ve JSONL dosyaları ayrıştırılabilir olmalıdır.
//   - Kit dosyalarının (ajan, beceri, kural) ön bilgisi kapalı ve gerekli alanları dolu olmalıdır.

const BINARY_EXT = new Set([
  '.db', '.sqlite', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.zip', '.gz', '.7z',
  '.ttf', '.otf', '.woff', '.woff2', '.mp3', '.m4a', '.ogg', '.wav', '.mp4', '.dll', '.exe', '.so',
  '.dylib', '.jar', '.keystore', '.jks', '.p12', '.dump', '.bin', '.tif', '.tiff',
]);
const CRLF_OK = new Set(['.ps1', '.cmd', '.bat']);

function isBinary(ext, buf) {
  if (BINARY_EXT.has(ext)) return true;
  const n = Math.min(buf.length, 8000);
  for (let i = 0; i < n; i++) if (buf[i] === 0) return true;
  return false;
}

/** YAML ön bilgisini kaba biçimde ayırır: { ok, keys: Map } ya da null (ön bilgi yok). */
export function frontmatter(text) {
  if (!text.startsWith('---\n')) return null;
  const end = text.indexOf('\n---', 4);
  if (end === -1) return { ok: false, keys: new Map() };
  const after = text.slice(end + 4, end + 5);
  if (after !== '' && after !== '\n') return { ok: false, keys: new Map() };
  const keys = new Map();
  for (const line of text.slice(4, end).split('\n')) {
    const m = /^([A-Za-z][\w-]*):(.*)$/.exec(line);
    if (m) keys.set(m[1], m[2].trim().replace(/^["']|["']$/g, ''));
  }
  return { ok: true, keys };
}

function checkKitFile(relKey, text) {
  const problems = [];
  const agent = /^\.claude\/agents\/([^/]+)\.md$/.exec(relKey);
  const skill = /^\.claude\/skills\/([^/]+)\/skill\.md$/i.exec(relKey);
  const rule = /^\.claude\/rules\/.+\.md$/.test(relKey);
  if (!agent && !skill && !rule) return problems;
  const fm = frontmatter(text);
  if (fm === null) {
    if (agent || skill) problems.push('Kit dosyası YAML ön bilgisiyle (--- … ---) başlamalı.');
    return problems;
  }
  if (!fm.ok) {
    problems.push('YAML ön bilgisi kapanmamış: ikinci "---" satırı eksik.');
    return problems;
  }
  if (agent || skill) {
    const expected = (agent ?? skill)[1];
    const name = fm.keys.get('name');
    if (!name) problems.push('Ön bilgide "name" alanı yok.');
    else if (name !== expected) problems.push(`"name: ${name}" klasör/dosya adıyla (${expected}) aynı olmalı.`);
    if (!fm.keys.get('description') && !text.includes('\ndescription: >') && !text.includes('\ndescription: |')) {
      problems.push('Ön bilgide "description" alanı yok ya da boş.');
    }
  }
  return problems;
}

/**
 * @param {{ relKey: string, ext: string, buf: Buffer }} f relKey: kökten göreli, '/' ayırıcılı.
 * @returns {string[]} sorun listesi (boşsa sorun yok)
 */
export function checkFile({ relKey, ext, buf }) {
  const problems = [];
  if (/[^\x20-\x7e]/.test(relKey)) {
    problems.push(`Dosya adı ASCII olmalı: ${relKey} (docs/02-mimari/04 §10.2).`);
  }
  if (isBinary(ext, buf)) return problems;
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    problems.push('Dosya UTF-8 BOM ile başlıyor; BOM\'suz UTF-8 kaydet.');
  }
  const text = buf.toString('utf8');
  if (!CRLF_OK.has(ext) && text.includes('\r\n')) {
    problems.push('Dosyada CRLF satır sonu var; LF kullan (.gitattributes).');
  }
  const lowerKey = relKey.toLowerCase();
  const name = lowerKey.split('/').pop() ?? '';
  const jsonc = name.startsWith('tsconfig') || name.startsWith('jsconfig') || lowerKey.startsWith('.vscode/');
  if (ext === '.json' && !jsonc) {
    try {
      JSON.parse(text.replace(/^\ufeff/, ''));
    } catch (err) {
      problems.push(`JSON ayrıştırılamadı: ${err.message}`);
    }
  }
  if (ext === '.jsonl') {
    const bad = [];
    text.split('\n').forEach((line, i) => {
      if (line.trim() === '') return;
      try {
        JSON.parse(line);
      } catch {
        bad.push(i + 1);
      }
    });
    if (bad.length) problems.push(`JSONL satırları ayrıştırılamadı: ${bad.slice(0, 10).join(', ')}${bad.length > 10 ? ' …' : ''}`);
  }
  problems.push(...checkKitFile(lowerKey, text.replace(/\r\n/g, '\n')));
  return problems;
}
