# İlerleme

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Canlı belge (`/asama` günceller)
> **Bağlı kararlar:** [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)

Bu dosya aşamaların durumunu tutar. Aşağıdaki durum bloğu her oturumun başında Claude Code'a otomatik verilir (`.claude/hooks/oturum-baslangici.mjs`). Bloğun işaret satırlarını (`<!-- durum:baslangic -->`, `<!-- durum:bitis -->`) silmeyin.

<!-- durum:baslangic -->
- Aktif aşama: yok
- Son tamamlanan: yok
- Sıradaki: A00 · Ortam, klasör ve depo hazırlığı
- Bekleyen insan adımları: İ-01 (araç kurulumu)
- Son güncelleme: 2026-10-19
<!-- durum:bitis -->

## Aşama tablosu

Durum değerleri: `bekliyor`, `sürüyor`, `tamam`, `engelli` (neden Not sütununda), `atlandı` (gerekçe Not sütununda). Tarihler `YYYY-AA-GG`.

| No | Aşama | Durum | Başlangıç | Bitiş | Commit | Not |
|---|---|---|---|---|---|---|
| A00 | Ortam, klasör ve depo hazırlığı | bekliyor | | | | |
| A01 | Hukuk ve izin yazışma paketi | bekliyor | | | | |
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

## İlgili dosyalar

- [Aşama haritası](./04-asama-haritasi.md) · [İnsan adımları](./06-insan-adimlari.md) · [Çalışma düzeni](./02-calisma-duzeni.md) · [Claude Code rehberi](./README.md)
