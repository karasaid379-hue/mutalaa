# Sözlük

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Onaylı
> **Bağlı kararlar:** [K-42](./02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)

Dokümanlarda geçen terimler, alfabetik sırayla. Kod içinde geçen değerler `kod` biçiminde yazılmıştır.

| Terim | Anlamı |
|---|---|
| **Âyet berkenar** | Her sayfanın tam bir âyetle başlayıp tam bir âyetle bittiği Türk mushaf düzeni. Mushaf B'nin hedeflediği düzen. |
| **`ATTACH`** | SQLite'ta birden fazla veritabanı dosyasını tek bağlantıda birlikte sorgulama komutu. İçerik paketleri bu yolla birlikte aranır. |
| **Bağlantı (`xref`)** | İki metin birimi arasındaki türü, puanı, güveni, kanıtı ve onay durumu belli ilişki. Bütün bağlantılar tek tabloda tutulur. |
| **Bağlantılar paneli** | Bir kelime ya da kelime grubu seçildiğinde açılan, sonuçları esere göre gruplayan çalışma paneli. |
| **bm25** | SQLite FTS5'in sonuçları ilgiye göre sıralama fonksiyonu. |
| **Çapa (kalıcı adres)** | Her metin biriminin hiç değişmeyen adresi. Örnek: `q:2:255:3-7`, `rn:sozler:soz-10:hakikat-3:p4`. Ayrıntı: [Çapa şeması](../03-veri/01-capa-semasi.md). |
| **`content_hash`** | Bir metin biriminin kanonik metninin SHA-256 özeti. İçerik değişirse vurguların yerini yeniden bulmak için kullanılır. |
| **Derleme türü** | `dev` (ekip), `internal` (davetli test), `public` (mağaza). Pakete hangi içeriğin gireceğini editoryal kalite belirler. |
| **EAS** | Expo Application Services. Bulutta derleme (Build) ve uygulama içi güncelleme (Update) hizmeti. |
| **Editör paneli** | Otomatik üretilen bağlantıları, kelime anlamlarını ve OCR satırlarını insanın onayladığı iç web aracı. |
| **Editoryal veritabanı** | İçeriğin ana kopyasının tutulduğu PostgreSQL 18 veritabanı. Uygulamalar buna doğrudan bağlanmaz; paketleri kullanır. |
| **FTS5** | SQLite'ın tam metin arama eklentisi. |
| **Glif fontu (QPC)** | Her mushaf sayfası için ayrı font; her kelime tek bir glif olarak çizilir. Mushaf A bu yolla çalışır. |
| **HLC** | Hybrid Logical Clock. Cihaz saatine güvenmeden olayları sıralayan mantıksal saat. Senkron birleştirmede kullanılır. |
| **İçerik hattı** | Kaynak metinleri alan, temizleyen, adresleyen, zenginleştiren ve editoryal veritabanına yazan Python programı. |
| **İçerik paketi** | Cihaza inen sürümlü SQLite dosyası (`core`, `tefsir-elmalili`, `hadis-tecrid` vb.). |
| **İktibas** | Bir metnin içinde başka bir metinden, burada çoğunlukla bir âyetten yapılan alıntı. |
| **İmlâî yazım** | Standart Arapça imla. Kitaplarda geçen âyet alıntıları çoğu zaman bu yazımla verilir. |
| **Kalite kapısı** | Yayınlayıcının paket üretirken uyguladığı denetim (P-01, P-07…P-14): kaynak kaydı olmayan içerik pakete girmez, onaysız birim `public`'e girmez, `test-` önekli kaynak `public`'e girmez. Ayrıntı: [Yayın süreci](../07-yayin/01-yayin-sureci.md). |
| **Kaynak kaydı** | `pipeline/sources/{kimlik}.toml` dosyası: kaynağın adı, adresi, sürümü ve atıf satırı; varsa kaynağın kendi bildirimi. İndirilen dosyanın özeti `data/gelen/<kaynak>/<YYYY-AA-GG>/SHA256SUMS` dosyasındadır. Kaydı olmayan kaynak içerik hattına alınmaz. Ayrıntı: [Kaynaklar](../04-icerik/01-kaynaklar.md). |
| **KFGQPC** | Kral Fahd Mushaf Basım Kompleksi. Uthmanic Hafs ve QPC fontlarının üreticisi. |
| **Kök** | Arapça kelimenin anlam taşıyan üç (bazen dört) harfli iskeleti. Örnek: ص ب ر. |
| **Lemma** | Bir kelimenin sözlük başı biçimi. Kelime anlamları lemma başına yazılır. |
| **Lügat** | Risale-i Nur'daki Osmanlıca ve Arapça kökenli kelimelerin anlam sözlüğü. |
| **LWW** | Last Writer Wins. Aynı kayıt iki yerde değiştiğinde son yazanın geçerli olduğu birleştirme kuralı. |
| **Manifest** | Paketlerin sürümünü, özetini (SHA-256), boyutunu, bağımlılıklarını ve adresini listeleyen, her derlemede imzalı `manifest.json` dosyası. |
| **Meal** | Kur'an âyetlerinin Türkçe anlamı. Bu projede şimdilik Elmalılı meali. |
| **Mushaf A / B / C** | Üç mushaf görünümü: A · Medine düzeni (QPC sayfa fontları), B · Türk hattı (sayfa görselleri), C · akan Unicode metin. |
| **QAC** | Quranic Arabic Corpus. Kur'an'daki her kelime için kök, lemma ve dil bilgisi etiketi veren veri seti. |
| **QF** | Quran Foundation (Quran.com). Font, ses ve veri API'leri sunar. |
| **QUL** | Quranic Universal Library (Tarteel). Kur'an verilerini SQLite ve JSON olarak dağıtır. |
| **RRF** | Reciprocal Rank Fusion. Farklı sıralamaları tek "Önerilen" listede birleştirme yöntemi. |
| **Riyâ** | Gösteriş. Uygulama ilerlemeyi yarıştıran özellikler koymaz. |
| **Tanzil** | Kur'an metnini Uthmani ve sade biçimlerde dağıtan proje. Metin dağıtıldığı hâliyle, bayt bayt saklanır; kaynağın kendi bildirimi atıf olarak gösterilir. |
| **Tecrîd-i Sarîh** | Zebîdî'nin Sahîh-i Buhârî muhtasarı. Türkçe tercümesi Babanzâde Ahmed Naim ve Kâmil Miras'a aittir. |
| **Tedarik** | Her aşamanın ilk işi: gerekli yapıların (metin, veri, yazı tipi, ses, görsel, kitaplık, araç) internette ve GitHub'da araştırılması, kullanılacakların aşama dosyasındaki `## Tedarik` bölümüne yazılması ve indirilmesi. Hazır yapı önce gelir ([K-42](./02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)). |
| **Uthmani (Resm-i Osmânî)** | Mushaflarda kullanılan geleneksel Kur'an imlası. |
| **Yayınlayıcı (Publisher)** | Onaylı içerikten paketleri üreten, kalite kapısını uygulayan, manifesti imzalayıp depoya yükleyen .NET konsol uygulaması. |

## İlgili dosyalar
- [Karar defteri](./02-karar-defteri.md) · [Ürün özeti](./01-urun-ozeti.md) · [README](../README.md)
