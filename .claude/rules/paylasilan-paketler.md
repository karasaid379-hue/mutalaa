---
paths:
  - "packages/**"
  - "shared/**"
---

# Paylaşılan paketler ve test vektörleri (`packages/*`, `shared/*`)

Kaynak: [Proje yapısı](../../docs/02-mimari/03-proje-yapisi.md) §1–§3, [Test stratejisi](../../docs/07-yayin/03-test-stratejisi.md) §2.

- **Platformdan bağımsızlık.** `packages/*` içinde `react-native`, `expo-*`, `next` ve DOM API'si kullanılmaz. Platform işi arayüzle içeri verilir (`player` ses motoru arayüzü, `reader-core` SQL yürütücüsü alır).
- **Yaprak paketler.** `anchors` ve `search` başka iç pakete bağlanmaz. Döngüsel bağımlılık yasaktır. Paket adları `@mutalaa/<klasör>`, iç bağımlılıklar `workspace:*`.
- **Vektörler şartnamedir.** `shared/test-vectors/` dosyaları TypeScript, C# ve Python uygulamalarını aynı anda bağlar. Bir kural değişecekse önce o kuralı gösteren vektör eklenir; üç uygulama aynı değişiklikte geçer. Ayrıntı: `test-vektoru` becerisi.
- **Vektör biçimi.** JSONL, UTF-8, BOM yok, LF, satır başına bir nesne, her satırda benzersiz `id`. Düzen: `anchors/{valid,invalid,compare,contains,route}.jsonl`, `offsets/offsets.jsonl`, `normalize/{tr,ar}.jsonl`, `content-hash/hash.jsonl`, `fts-query/query.jsonl`.
- **Yerel ayar.** `toLocaleLowerCase`, `toLocaleUpperCase` argümansız, `localeCompare` tek argümanla kullanılmaz (ESLint kuralı). Türkçe küçük harf açık eşlemeyle yapılır (`İ→i`, `I→ı`).
- **Ofset.** Ofsetler kod noktasıdır; UTF-16 dönüşümü yalnız `packages/anchors` içindeki `cpToUtf16` ve `utf16ToCp` ile yapılır.
- **Testler** Vitest ile yazılır ve `LANG=tr_TR.UTF-8` altında da geçmelidir. Kurulum dosyası etkin yerel ayarı koşu başında yazar; Windows'ta `LANG` Node'un yerel ayarını değiştirmez (`windows-sorun`).
