# İlerleme

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Canlı belge (`/asama` günceller)
> **Bağlı kararlar:** [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)

Bu dosya aşamaların durumunu tutar. Aşağıdaki durum bloğu her oturumun başında Claude Code'a otomatik verilir (`.claude/hooks/oturum-baslangici.mjs`). Bloğun işaret satırlarını (`<!-- durum:baslangic -->`, `<!-- durum:bitis -->`) silmeyin.

<!-- durum:baslangic -->
- Aktif aşama: yok
- Son tamamlanan: A00 · Ortam, klasör ve depo hazırlığı (2026-10-20)
- Sıradaki: A02 · Tek depo iskeleti (A01, İ-02 gönderimini bekliyor; A02'nin önkoşulu yalnız A00)
- Bekleyen insan adımları: İ-01 (Docker ilk açılış, yönetici ayarları); İ-02 … İ-08 taslakları hazır, gönderim ve onay bekliyor (öncelik İ-02)
- Son güncelleme: 2026-10-20
<!-- durum:bitis -->

## Aşama tablosu

Durum değerleri: `bekliyor`, `sürüyor`, `tamam`, `engelli` (neden Not sütununda), `atlandı` (gerekçe Not sütununda). Tarihler `YYYY-AA-GG`.

| No | Aşama | Durum | Başlangıç | Bitiş | Commit | Not |
|---|---|---|---|---|---|---|
| A00 | Ortam, klasör ve depo hazırlığı | tamam | 2026-10-19 | 2026-10-20 | `7fc54af` kök git dosyaları; `ec4526c` push politikası; `57f424f` belge düzeltmeleri | Hook, ajan ve beceri sayımı VS Code'da `/hooks` ve `/agents` olmadığı için diskten kanıtlandı; yerleşik `/doctor` çıktısı Claude Code'a görünmez, `doctor` becerisi ayar dosyası ayrıştırmasını yaptı (bozuk dosya yok). Klasör bekçisi: `Write Z:` reddedildi, `echo > /z/...` için hook `ask` kararı oturum kaydında. Yönetici gerektiren Windows ayarları ve Docker İ-01'de. Yol kararı: yerinde kal (OneDrive; klasör "Her zaman bu cihazda tut", yoğun işlerde eşitleme duraklatılır, Android derlemesi EAS bulutunda) |
| A01 | Hukuk ve izin yazışma paketi | engelli | 2026-10-20 | | yazışma taslakları, insan adımları, belge eşitleme | A01.1–A01.6 tamam (7 taslak, 5 açıdan inceleme ve doğrulama uygulandı); A01.7 inceleme düzeltmeleri işlendi; İ-02 gönderimi bekleniyor (Faz 0 çıkış ölçütü: Kurul'a talep gitti; cevap ya da takip tarihi kayıtlı) |
| A02 | Tek depo iskeleti | bekliyor | | | | |
| A03 | Yerel altyapı | bekliyor | | | | |
| A04 | Çapa grameri ve ortak test vektörleri | bekliyor | | | | |
| A05 | Arama normalizasyonu | bekliyor | | | | |
| A06 | Lisans defteri v1 ve ortak enum şeması | bekliyor | | | | |
| A07 | Editoryal veritabanı | bekliyor | | | | |
| A08 | CI iş akışları | bekliyor | | | | |
| A09 | Elmalılı OCR pilotu | bekliyor | | | | |
| A10 | Tanzil alımı ve değişmezlik testleri | bekliyor | | | | |
| A11 | Kur'an yapısı ve sayfa eşlemesi | bekliyor | | | | |
| A12 | Arama indeksi ve paket şeması | bekliyor | | | | |
| A13 | Yayınlayıcı ve yayın kapısı | bekliyor | | | | |
| A14 | API editör uçları | bekliyor | | | | |
| A15 | Editör paneli | bekliyor | | | | |
| A16 | Elmalılı meali | bekliyor | | | | |
| A17 | Kelime katmanı | bekliyor | | | | |
| A18 | Bağlantılar ve altın setler | bekliyor | | | | |
| A19 | Hadis hatları | bekliyor | | | | |
| A20 | Risale altyapısı (metinsiz) | bekliyor | | | | |
| A21 | Mobil iskelet | bekliyor | | | | |
| A22 | Tasarım vitrini ve `ui-tokens` | bekliyor | | | | |
| A23 | Cihaz veri katmanı | bekliyor | | | | |
| A24 | Okuyucu: Mushaf C | bekliyor | | | | |
| A25 | Seçim, kelime kartı, Bağlantılar | bekliyor | | | | |
| A26 | Mushaf A | bekliyor | | | | |
| A27 | Ses sistemi | bekliyor | | | | |
| A28 | Arama ekranı | bekliyor | | | | |
| A29 | Kütüphane ve Depolama yöneticisi | bekliyor | | | | |
| A30 | Defterim, hatim ve yedekleme | bekliyor | | | | |
| A31 | Hadis ve Risale okuyucuları | bekliyor | | | | |
| A32 | Ayarlar, ilk açılış, erişilebilirlik, öz test | bekliyor | | | | |
| A33 | Uçtan uca testler ve iç dağıtım | bekliyor | | | | |
| A34 | Mağaza v1 yayın hazırlığı | bekliyor | | | | |
| A35 | Hesap ve KVKK | bekliyor | | | | |
| A36 | Senkron ve bağlantı oyları | bekliyor | | | | |
| A37 | Elmalılı tefsir paketi | bekliyor | | | | |
| A38 | Web | bekliyor | | | | |
| A39 | Takvim ve lisans olayları | bekliyor | | | | Olay geldikçe tekrar çalışır |
| A40 | Mushaf B | bekliyor | | | | Lisans gelince |

## Oturum günlüğü

Her aşama oturumunun sonunda bir satır eklenir: `YYYY-AA-GG · Aşama · ne yapıldı · sıradaki adım`.

- 2026-10-19 · Kit · Claude Code kiti kuruldu (CLAUDE.md, `.claude/`, `docs/10-claude-code/`) · A00
- 2026-10-19 · A00 · sürüm tablosu, kök git dosyaları (`7fc54af`), pnpm 12.14.0 kurulumu, push politikası ve klasör adı kararları, belge düzeltmeleri · kabul kanıtları
- 2026-10-20 · A00 · `doctor` taraması, hook/ajan/beceri sayımının disk kanıtı, A00.2 ve Kurulum §5 belge düzeltmesi, aşama kapandı · A01
- 2026-10-20 · A01 · 7 yazışma taslağı yazıldı; araştırma (5 kurum) ve beş açılı inceleme/doğrulama uygulandı; belgeler eşitlendi (lisans defteri, yayın kapısı, BÇ-29…BÇ-34) · İ-02 gönderimi; sıradaki A02

## İlgili dosyalar

- [Aşama haritası](./04-asama-haritasi.md) · [İnsan adımları](./06-insan-adimlari.md) · [Çalışma düzeni](./02-calisma-duzeni.md) · [Claude Code rehberi](./README.md)
