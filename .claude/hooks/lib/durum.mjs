// Mütâlaa · oturum başlangıcında bağlama eklenecek durum özeti (yan etkisiz).
// Kaynak: docs/10-claude-code/05-ilerleme.md içindeki
// <!-- durum:baslangic --> … <!-- durum:bitis --> bloğu.

export const ILERLEME_YOLU = 'docs/10-claude-code/05-ilerleme.md';
// İşaretler yalnız kendi satırlarında sayılır; metin içinde anılan işaret blok açmaz.
const BLOK = /^[ \t]*<!-- durum:baslangic -->[ \t]*$([\s\S]*?)^[ \t]*<!-- durum:bitis -->[ \t]*$/m;
const AZAMI = 1500;

/** Durum bloğunu çıkarır; blok yoksa null. */
export function extractStatus(markdown) {
  const text = String(markdown ?? '').replace(/\r\n/g, '\n');
  const m = BLOK.exec(text);
  if (!m) return null;
  const body = m[1].trim();
  return body.length > AZAMI ? `${body.slice(0, AZAMI)} …` : body;
}

/** Bağlama eklenecek metni kurar. */
export function buildContext(status) {
  const lines = ['Mütâlaa · oturum başlangıcı'];
  if (status) {
    lines.push(status);
  } else {
    lines.push(`İlerleme dosyası okunamadı (${ILERLEME_YOLU}). /durum ile kontrol et.`);
  }
  lines.push(
    'Kurallar CLAUDE.md dosyasındadır. Aşama yürütmek için /asama <no>, durum için /durum.',
    'Kullanıcıyla Türkçe konuş. Proje klasörünün dışına çıkma.',
  );
  return lines.join('\n');
}
