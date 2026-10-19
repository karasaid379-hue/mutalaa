---
paths:
  - "apps/editor/**"
  - "apps/web/**"
---

# Editör paneli ve web kuralları (`apps/editor`, `apps/web`)

Kaynak: [Proje yapısı](../../docs/02-mimari/03-proje-yapisi.md), [Backend API](../../docs/02-mimari/05-backend-api.md) §4–§6, [Fazlar](../../docs/08-yol-haritasi/01-fazlar.md) Faz 5.

- **Editör (K-13).** React + TypeScript + Vite + shadcn/ui + Tailwind CSS v4. API tipleri elle yazılmaz; `server/Mutalaa.Api/openapi/v1.json` dosyasından üretilir (`gen:api`) ve üretilen istemci kullanılır. Vite `/api` isteklerini `http://localhost:5080` adresine aktarır.
- **İnceleme akışı.** Karar uçları `If-Match` başlığı ister; 412 alınca kayıt yeniden yüklenir. İkinci onay gereken alanlarda (meal ve tefsir metni, `license_status`, `kurul_onay`, `embed_ok`) arayüz ilk ve ikinci onayı ayrı gösterir. Onaysız yapay zekâ taslağı "doğrulanmamış" rozetiyle görünür.
- **Metin.** Hazır kaynak metni (Tanzil) düzenlenemez; arayüz düzeltme düğmesini göstermez. Arama kutusu sorguyu sunucudaki normalizasyona bırakır.
- **Web (Faz 5, K-14).** Next.js; her âyete ve sayfaya ayrı adres (`/kuran/[sure]/[ayet]`, `/mushaf/[sayfa]`). Rotalar çapa gramerinden `packages/anchors` ile üretilir. Paylaşılan paketler (`anchors`, `search`, `reader-core`, `ui-tokens`) kullanılır; kopyalanmaz.
- **Testler:** Vitest ve Testing Library. Görsel denetim gerekiyorsa `arayuz-denetcisi` ajanı kullanılır.
