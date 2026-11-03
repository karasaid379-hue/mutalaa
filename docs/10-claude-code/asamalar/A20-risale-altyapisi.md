# A20 · Risale altyapısı ve metni

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-02](../../00-ozet/02-karar-defteri.md#k-02--i̇lk-içerik-seti) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A07](./A07-editoryal-veritabani.md) · [A13](./A13-yayinlayici-ve-kalite-kapisi.md) · **İnsan adımı:** İ-24 · İ-28
> **Ajanlar:** `arastirmaci` (A20.0 tedarik) · `hat-gelistirici` · `sunucu-gelistirici` (Yayınlayıcı paket tanımları) · `metin-denetcisi` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `paket-yayini` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A20`

## Amaç
Risale-i Nur Külliyatı'nın metni, adresleri, basılı sayfa eşlemesi, âyet atıf dizini ve lügatı içerik hattıyla gelir (K-02). Bu aşama dijital tam metni internette araştırıp seçer ve indirir, kaynak kaydına bağlar, bölüm ağacı ve paragraf (`rn:`) çapalarıyla `unit` olarak yükler, basılı sayfa eşlemesini kurar, `risale-dizin` ve `risale-{kitap}` paketlerinin Yayınlayıcı tanımlarını yazar, Arapça alıntı ve açık atıflardan metinli âyet atıf dizinini çıkarır ve Risale lügatının altyapısını (kaynak kayıtları, `lugat_madde` şeması, başlık söz listesi, anlam taslakları, editör kuyruğu) kurar. Metin kelimesi kelimesine yayımlanır; yapay zekâ özeti yazılmaz (K-25). Onaysız birimler `dev` ve `internal` derlemelerinde "doğrulanmamış" rozetiyle görünür, `public`'e onaylı birimler girer (K-42). Açıkça sentetik `test-risale-ornek` fikstürü birim ve arayüz testleri içindir; A31 okuyucusu gerçek metinle çalışır.

## Okunacak belgeler
- [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md): tamamı; özellikle kitap ve bölüm adresleri, paragraf çapaları, baskılar ve sayfa eşlemesi, âyet atıf dizini, lügat, tarafsızlık ve yayın kuralları
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.2, §3.4 `risale-dizin`, §4 bağlantıların dağılımı, §7 süzme
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2–§6 (`rn` grameri, slug kuralları, haşiye önerisi, kararlılık), §10 sayfa eşlemeleri
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 (`source`, `tur = 'baski'`, `baski_bilgisi`), §4 (`parent_path`, `sentences`, `marks`), §9.1 `page_map`
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları (P-01, P-07, P-12)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 kaynak kaydı ve atıf, §3.5 Risale-i Nur, §3.6 Lügat, §5 yeni kaynak ekleme
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): kaynak kaydı, indirme, kalite kapıları, §10 yapay zekâ · [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): lügat taslağı ilkeleri
- [İktibas ve atıf tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §2 açık atıf grameri, §3 Arapça dizilerin çıkarılması, §5–§6 eşleştirme, §10 altın set, §11 hazır araçlar
- [Arama](../../03-veri/05-arama-fts5.md): §2 içeriksiz tablolar · [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §8 sentetik kaynak

## Kapsam
**Yapılır**
- Külliyat'ın dijital tam metninin tedariki, indirilmesi ve içe alınması (`risale-asil-nusha`); kaynak seçimi ölçümle A20.1'de yapılır.
- Kitap slug listesi, bölüm ağacı, paragraf (`p{n}`), haşiye, dipnot ve cümle adresleri; Arapça alıntı işaretleri; bölüm kalıpları için biçim ve doğrulayıcı.
- Baskı kaydı ve basılı sayfa eşlemesi (`page_map`); içindekilerin dijital kaynaklarla karşılaştırılması.
- Yayınlayıcıda `risale-dizin` ve `risale-{kitap}` paket tanımları.
- Sentetik fikstür kaynağı `test-risale-ornek`, üreteci ve `dev` yayını.
- Lügat altyapısı: kaynak kayıtları, `lugat_madde` şeması, Kelime-Frekans'tan başlık söz listesi ve anlam taslakları, editör kuyruğu, fikstür için sentetik maddeler (A20.6).
- Metinli âyet atıf dizini: açık atıflar ve Arapça alıntılar, `xref` aday satırları, parça metin (A20.7).

**Yapılmaz**
- Risale metnini düzeltmek, sadeleştirmek, özetlemek ya da yapay zekâ ile işlemek (K-25, K-30); metin kaynak dosyadaki gibi saklanır.
- Arap harfli (Osmanlıca) metnin içe alınması ve OCR'ı; sözlük taramalarının toplu OCR'ı ve madde madde içe aktarılması (ayrı iş).
- Lügat kartı ve yoğunluk ayarı (A31). Konu listesi (v1.x).
- Risale okuyucusu ve cihazda ATTACH yönetimi (A31, A23).
- Risale atıf ve iktibas altın setinin etiketlenmesi (İ-13; A18'in etiketleme arayüzü).

## Tedarik
Araştırma tarihi 2 Kasım 2026; A20.0'da yenilenir. Metin, içindekiler yapısı ve basılı sayfa eşlemesi üç ayrı ihtiyaçtır; her biri için en uygun kaynak ayrı seçilir. Metin kaynağı A20.1'de ölçümle kesinleşir; öneri Diyanet deposunun GitHub kopyasıdır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Risale-i Nur Külliyatı tam metni (Diyanet asıl nüsha; paragraf, başlık, haşiye ve dipnot sınırları) | GitHub `alitekdemir/Risale-i-Nur-Diyanet`, commit `1dad9ea73618772d5daecad19e8ccb27c0923d27` (2 Kasım 2026'da HEAD; sürüm etiketi yok). Metin Hizmet Vakfı'nın Diyanet sayfalarından kopyalanmıştır (depo README'si). Üç biçim: `txt/` (298 dosya, 13.810.825 bayt), `obsidian-markdown/` (358 dosya, 27.652.718 bayt; 310 bölüm dosyası; başlık `#`, dipnot `[^n]`, Arapça `class="arabic"`), `html/` (331 dosya, 34.869.485 bayt) | `https://github.com/alitekdemir/Risale-i-Nur-Diyanet/archive/1dad9ea73618772d5daecad19e8ccb27c0923d27.zip` doğrudan dosya (302 ile `codeload`; 47.850.408 bayt, 1.049 girdi; ön örneğin SHA-256 `68b3c3d6a740a07176e668e841d8e39ecdddb3c3c19879f3efea5654d434385f`) | `txt/`: 15 kitap klasörü, 298 dosya (Sözler 36, Mektubat 39, Lem'alar 36, Şuâlar 18, Tarihçe-i Hayat 14, Mesnevî-i Nuriye 16, İşaratü'l-i'caz 27, Sikke-i Tasdik-i Gaybî 8, Barla Lâhikası 20, Kastamonu Lâhikası 13, Emirdağ Lâhikası 1 ve 2 için 15 ve 13, Asâ-yı Musa 26, Küçük Kitaplar 11 eser, Muhakemat 6); `html/`te Muhakemat yok. Boş olmayan satır 47.558 (paragraf ya da başlık; boş satır 232), kelime 2.000.362 (Sözler 281.060). Arapça harf sayısı `txt` ve `html`de aynı (ör. Sözler 95.987). Markdown'da 777 dipnot tanımı, 775 dipnot atfı, 8.238 Arapça işareti. Basılı sayfa numarası yok. Hizmet Vakfı Diyanet sayfasıyla İkinci Söz örneğinde 640 kelimenin 640'ı aynı | `risaleinur.hizmetvakfi.org/diyanet` sayfaları (kaynak site; 2 Kasım 2026'da ulaşılamadı); `risale.online` |
| İçindekiler ağacı (kitap, bölüm, başlık düzeyi, üst yol) | Metnin kendi başlıkları (Diyanet markdown `#`…`######`); karşılaştırma verisi eRisale `toc-tr.json` (`https://www.erisale.com/book-content/toc-tr.json`; 2.566.642 bayt; `Last-Modified` 31 Ekim 2026 14:46 GMT; ETag `6ae5ff4c-2729f2`) | Doğrulama verisi için doğrudan JSON dosyası (200, `application/json`) | 5.354 kayıt: 15 kitap ve kök kaydı; alanlar `bookId, level, isSection, blockIndex, parentPath, urlSegment, sectionIndex, globalSectionIndex, title`; en derin yol 8 (Şuâlar); Sözler 689 başlık, 284 bölüm. Kitap bölünmesi Diyanet klasörlerinden farklı (Emirdağ tek kitap; İman ve Küfür Muvazeneleri ve İlk Dönem Eserleri ayrı) | Hizmet Vakfı Külliyat içindekileri (Sözler 271 düğüm); `risale.online` fihrist verisi (Sözler 376 başlık, derinlik 6) |
| Basılı baskı sayfa eşlemesi (bölüm ve paragraf → basılı sayfa) | Hizmet Vakfı Külliyat görünümü: "Hizmet Vakfı ve Envar Neşriyat'ın Latin harfli Türkçe baskısı" (`https://risaleinur.hizmetvakfi.org/kulliyat`); içindekiler düğümleri `book_id, id, parent_id, slug, sort_order, start_page, title` | `/kulliyat/<kitap>/<sayfa>` sayfaları; içindekiler kitap başına tek istekle, sayfa metni sayfa başına istekle; istek hızı saniyede en çok 1 | Ön ölçüm (31 Ekim–1 Kasım 2026'da alınan 12 sayfa): Sözler 271 düğüm, derinlik en çok 4, 37 birinci düzey, `start_page` 5–856. İkinci Söz örneğinde Diyanet metninin 640 kelimesinin 640'ı Envar sayfa 17–19 metninde bulundu. Öteki kitaplar A20.0'da ölçülür; 2 Kasım 2026'da siteye ulaşılamadı | `risale.online`: 24 eser, toplam 7.811 sayfa (22 eserde metin; Sözler 379 sayfa), paragraf başına `sayfa`, Latin ve Osmanlıca HTML; baskı belirtilmemiş (ayrı `baski` kaydı olarak eklenir) |
| Lügat başlık söz listesi ve sıklık (yalnız kelime ve sıklık) | GitHub `alitekdemir/Risale-i-Nur-Kelime-Frekans`, commit `23f3c5caec91739f5c18d5280399d82bb47dcc02` (2 Kasım 2026'da HEAD; sürüm etiketi yok); `data/eRisale/analysis/terkipsiz/<kitap>_frekans.txt` (sütunlar `kelime,frekans`) | `https://github.com/alitekdemir/Risale-i-Nur-Kelime-Frekans/archive/23f3c5caec91739f5c18d5280399d82bb47dcc02.zip` doğrudan dosya | 20 dosya (15 kitap ve 5 Söz alt kümesi); 15 kitapta birleşik 20.045 benzersiz kelime, toplam frekans 491.225; Sözler 7.991 satır. `terkipli/` altında 20 dosya daha | Metnimizden kendi sıklık sayımımız (A05 normalleştiricisi) |
| Lügat anlam taslağı (Türkçe; editör onayına kadar "doğrulanmamış") | Aynı depo, `data/eRisale/raw/<kitap>.csv` (`"kelime","anlam"`; Külliyat sayfa altı kelime açıklamaları) | Yukarıdaki zip | 15 kitap, 398.772 satır, 46.090 benzersiz kelime, 18 boş `anlam` (Sözler 56.384 satır, 13.725 benzersiz kelime) | Aynı depoda `data/SorularlaRisale/raw/*.csv` (aynı sütunlar, 24 dosya) |
| Lügat köken ve Osmanlıca yazım başvuruları (madde kartı için) | Internet Archive: Redhouse, *A Turkish and English Lexicon*, 1890, `aturkishandenglishlexicon1` (`_djvu.txt` 8.447.120 bayt, SHA-1 `251b719a64ee…`; PDF 181.528.316 bayt; son güncelleme 14 Aralık 2024); Kâmûs-ı Türkî Latin harfli kopya `kamus-i-turki-semseddin-sami-bey` (`_djvu.txt` 5.969.007 bayt, SHA-1 `c1fb2d519f61…` indirilen dosyayla eşleşti; son güncelleme 31 Ağustos 2026); Lugat-ı Nâci 1891, `lugati-naci` (`_djvu.txt` 2.585.323 bayt, SHA-1 `3924d9ddd97c…`; son güncelleme 26 Eylül 2026) | `https://archive.org/download/<kimlik>/<dosya>` doğrudan dosya; boyut ve SHA-1 `https://archive.org/metadata/<kimlik>` kaydından | OCR metin dosyaları: Kâmûs Latin kopyada 130.892 dolu satır, harf oranı 0,714, Arap harfi 0; Osmanlıca başlıklar bozuk okunuyor, Latin açıklamalar okunabilir (kalite A20.6'da örneklemle ölçülür). `lugat-i-naci-1317` (1899) `_djvu.txt` yalnız 92.259 bayt: Osmanlıca OCR kullanılamaz | Kâmûs-ı Türkî 1899 taraması `kamusitrki00emse` (`_djvu.txt` 2.970.789 bayt); `ottomanlexicons.com` (200); HathiTrust kaydı 001771732 (Redhouse); `turki.cagdassozluk.com` (2 Kasım 2026'da ulaşılamadı) |
| Âyet atıf dizini: Arapça alıntı ve açık atıf tespit aracı | PyPI: `ijaza` 2.0.0 (8 Mart 2026; Python ≥3.9; isteğe bağlı `rapidfuzz`), `quran-detector` 0.0.2 (23 Aralık 2025; Python ≥3.12; `python-Levenshtein`), `quran-toolkit` 0.1.0 (7 Ekim 2026; Python ≥3.8; `arabing`; GitHub `asdoost/quran-toolkit`). Kur'an metni Tanzil'den (A10) | Kazanan araç `uv add --directory pipeline <paket>` ile eklenir, sürüm `uv.lock` içinde sabitlenir | PyPI kayıtları 2 Kasım 2026'da okundu; üçü de Python 3.13 ile uyumlu. Kesinlik ve duyarlılık A20.7'de Risale dizileriyle ölçülür | `QDetect` 0.7.2 (13 Haziran 2024); `quran-search-in-text`; kendi eşleştirici (İktibas ve atıf tespiti §5–6) |
| Ayrıştırma ve dönüştürme kitaplıkları | Yeni kitaplık yok: markdown ve metin ayrıştırması standart kitaplık ve `regex` (pipeline bağımlılığı), zip okuma `zipfile` ile | Yok | Ölçüm betikleri 1.049 girdiyi yalnız standart kitaplıkla ayrıştırdı | Yok |

Kendimiz yapacağımız işler: Diyanet markdown ayrıştırıcısı (başlık → bölüm ağacı, satır → paragraf `unit`, dipnot → haşiye ve dipnot, Arapça işaret → `marks`); `rn:` çapa üretimi, kitap slug'ları ve doğrulayıcı; cümle sınırları; içindekiler eşleştirme ve fark raporu; Hizmet Vakfı içindekilerinin `page_map`'e alınması ve paragraf hizalaması; `lugat_madde` şeması, başlık söz listesi ve anlam taslağı içe aktarımı; sözlük OCR metinlerinde başlık söz araması; açık atıf ayrıştırıcısı, seçilen aracın sarılması, normalizasyon ve kalıp katmanları, `xref` yazımı; `risale-dizin` ve `risale-{kitap}` paket tanımları; sentetik fikstür ve üreteci; G-BUT beklenen sayıları.

Metin kaynağı karşılaştırması (A20.1 seçimi için):

| Aday | Kapsam ve yapı | Basılı sayfa | Toplu alma ve sürüm | Sonuç |
|---|---|---|---|---|
| Diyanet GitHub kopyası | 15 kitap klasörü; markdown'da başlık, dipnot ve Arapça işareti; txt'de satır = paragraf | Yok | Tek zip; commit SHA sabit | Metin kaynağı (öneri) |
| Hizmet Vakfı `/diyanet` | Aynı metin (İkinci Söz: 640/640 kelime) | Yok | Toplu dosya yok; sürüm yok; 2 Kasım 2026'da ulaşılamadı | Yedek ve doğrulama |
| Hizmet Vakfı `/kulliyat` (Envar Latin baskısı) | Aynı metin; içindekiler düğümleri | `start_page` ve sayfa görünümü | Toplu dosya yok; kitap başına sayfa | Sayfa eşlemesi kaynağı |
| risale.online | 24 eser (22'sinde metin); Latin ve Osmanlıca HTML; fihrist | Paragraf başına `sayfa` (7.811 sayfa; baskı belirtilmemiş) | Sunucuda işlenmiş sayfa; toplu uç A20.0'da ölçülür | Sayfa eşlemesi ve Osmanlıca yazım için yedek |
| eRisale | 15 kitap; `toc-tr.json` açık | Bloklarda var, içerik şifreli | Blok içerikleri uygulamaya özgü şifreli `.erisale` dosyaları; doğrudan alınabilir biçim yok; İkinci Söz'de 640 kelimenin 531'i eşleşti (0,83) | Yalnız içindekiler karşılaştırması |

Seçilmeyenler (kalite ve erişim): eRisale blok içerikleri (şifreli biçim, metin farkı); `risale.online` metni (baskı belirtilmemiş, toplu uç doğrulanmadı); Hizmet Vakfı sayfaları metin kaynağı olarak (toplu dosya yok, ulaşılamadı); `turki.cagdassozluk.com` (ulaşılamadı).

## Adımlar
### A20.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: GitHub depolarında `git ls-remote https://github.com/<sahip>/<depo>.git HEAD` (commit `1dad9ea7…` ve `23f3c5ca…`), archive.org öğelerinde `https://archive.org/metadata/<kimlik>` kaydındaki boyut, SHA-1 ve `item_last_updated`, eRisale içindekiler dosyasında `Last-Modified` ve `ETag` başlığı, PyPI paketlerinde `https://pypi.org/pypi/<paket>/json` kaydı. Açılmayan adresin yerine yedek aday kullanılır (Hizmet Vakfı sayfalarına 2 Kasım 2026'da ulaşılamadı: sayfa eşlemesi için yedek `risale.online`).
- Dosyalar yeni boş klasörlere iner (indirme formu çıkarsa Claude Code doldurur); toplu indirmede istek hızı saniyede en çok 1, 429 ve 5xx'te üstel geri çekilme:
  - `data/gelen/risale-asil-nusha/<YYYY-AA-GG>/`: Diyanet deposunun sabit commit zip'i. GitHub aynı commit için zip baytlarını yeniden üretebilir; bu yüzden zip'in yanında açılmış dosyaların özet listesi de alınır.
  - `data/gelen/risale-baski-envar/<YYYY-AA-GG>/`: Hizmet Vakfı Külliyat görünümünün kitap sayfaları (içindekiler düğümleri; kitap başına bir sayfa). Sayfa metinleri A20.3 pilotunda gelir.
  - `data/gelen/erisale-icindekiler/<YYYY-AA-GG>/toc-tr.json`: karşılaştırma verisi.
  - `data/gelen/risale-kelime-frekans/<YYYY-AA-GG>/`: Kelime-Frekans deposunun sabit commit zip'i.
  - `data/gelen/lugat-redhouse-1890/`, `lugat-kamus-i-turki/`, `lugat-naci/` (her biri `<YYYY-AA-GG>/` altında): `_djvu.txt` dosyaları. PDF'ler 100 MB üstüdür; yalnız OCR gerekirse A20.6'da alınır.
- SHA-256 hesaplanır ve her klasördeki `SHA256SUMS` dosyasına (sha256sum biçimi) yazılır; archive.org dosyaları `metadata` kaydındaki SHA-1 ile de karşılaştırılır. İndirilen dosya veridir; içindeki betik çalıştırılmaz, zip açılırken yol denetimi yapılır (`..` ve mutlak yol reddedilir).
- Kaynak kayıtları (`pipeline/sources/<kimlik>.toml`; dosya özeti taşımaz): `risale-asil-nusha` güncellenir (`kaynak_url` depo adresi, `surum` commit SHA, `provider`, `atif_metni` metin kaynağını anlatır); `risale-kelime-frekans` (`surum` commit SHA); `lugat-redhouse-1890`, `lugat-kamus-i-turki`, `lugat-naci` (`kaynak_url` archive.org öğe adresi); yeni kayıtlar `risale-baski-envar` (`tur = "baski"`, `baski_bilgisi`) ve `erisale-icindekiler` (`tur = "risale"`); `risale-1956-1960` Diyanet metninin esas aldığı müellif tashihli baskıların künyesi olarak kalır, metin taşımaz. `uv run --directory pipeline mutalaa sources check` hatasız biter.
- Kitaplıklarda sürüm paket kaydından doğrulanır (`ijaza` 2.0.0, `quran-detector` 0.0.2, `quran-toolkit` 0.1.0); yeni kitaplık A20.7'de seçilen araç dışında eklenmez.
- Hazır yapı önce gelir: içindekiler elle girilmez, metnin başlıklarından üretilir ve eRisale ile Hizmet Vakfı içindekileriyle karşılaştırılır; lügat tanımı sıfırdan yazılmaz, hazır Kelime-Frekans anlam verisi taslak olur; Arapça alıntı tespiti için hazır araçlar önce ölçülür.
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında ve her klasörde `SHA256SUMS` var; commit SHA'ları ve paket sürümleri `git ls-remote` ve PyPI çıktısıyla doğrulandı ve aşama notuna yazıldı; kaynak kayıtları güncel ve `sources check` 0 hata, 0 uyarı.

### A20.1 · Kaynak kayıtları ve metnin içe alınması
- Metin kaynağı seçimi: Tedarik'teki karşılaştırma ölçümle yenilenir (kitap kapsamı, başlık ve dipnot yapısı, Arapça işareti, sayfa numarası, toplu alma, sürüm sabitleme). Sonuç `risale-asil-nusha` kaydının `notlar` alanına ve ilerleme dosyasına yazılır. Diyanet kopyasında kitap eksikse (ör. Hizmet Vakfı kitap listesinde olup depoda bulunmayan eser) eksik kitaplar rapora yazılır; başka kaynaktan eklenmesi kapsam değişikliğidir ve kullanıcıya sorulur.
- İçe alma (komut adı öneri: `uv run --directory pipeline mutalaa ingest risale --source risale-asil-nusha`): zip `data/raw/risale-asil-nusha/` altına işlenmeden alınır (değişmez) → ayrıştırma (markdown: başlık, paragraf, dipnot, Arapça işareti) → `staged` → PostgreSQL `unit` (`kind = 'risale'`). Risale metni üçüncü taraf metnidir: karakterler olduğu gibi saklanır (NFC yok, UTF-8, LF), arama metni ayrı sütunda A05 normalleştiricisiyle üretilir. Dosya adları birleşik nokta (U+0307) taşır; dosya → kitap ve bölüm eşlemesi kimlik tablosuyla yapılır, slug adlardan türetilmez.
- Biçim seçimi: markdown önerilir (başlık düzeyi, dipnot, Arapça işareti); `txt` ve `html` ile kelime dizisi eşitliği G-BUT'ta sınanır (ön ölçüm: Sözler'de Arapça harf sayısı `txt` ve `html`de 95.987). Markdown ile `html` başlık düzeyleri farklı (Sözler: 683 ve 381 başlık); yapı eRisale içindekileriyle doğrulanır.
- Kapılar: G-KAY (kayıt geçerli, `atif_metni` dolu), G-BUT (beklenen sayılar: 15 kitap, `txt` boş olmayan satır 47.558, 777 dipnot tanımı; boş birim yok; kontrol karakteri yok; metin kaynak dosyayla bayt bayt aynı), G-CAP (A20.2'den sonra). Beklenen sayılar kitap bazında küçük bir JSON'da tutulur (yalnız sayılar).
- İkinci içe alma 0 değişiklik üretir (idempotent). Birimler `taslak` girer; `onayli` durumuna geçiş yolu (öneri: kaynakla bayt eşitliği G-BUT ile kanıtlanan kitaplarda örneklem okuması sonrası kitap bazında toplu onay; editör panelinde "kitabı onayla" eylemi A15 ucu ister) `/karar` ile yazılır.
- **Bitti sayılır:** `sources check` 0; `qa run --source risale-asil-nusha --gate G-BUT` 0; veritabanında kitap başına birim sayıları ölçümle aynı; ikinci koşuda fark 0; onay yolu kararı karar defterinde.

### A20.2 · Kitap, bölüm ve paragraf adresleri
- Slug listesi (yol öneri: `shared/data/risale-kitaplar.json`): Risale hazırlığındaki kitap tablosu (Sözler … Tarihçe-i Hayat) ve Diyanet deposunun `Küçük Kitaplar` klasöründeki 11 eserin slug'ları (dosya adlarından Çapa şeması §5 kuralıyla türetilir: `divan-i-harb-i-orfi`, `genclik-rehberi`, `hanimlar-rehberi`, `hutbe-i-samiye`, `isarat`, `konferans`, `munazarat`, `nur-cesmesi`, `nurun-ilk-kapisi`, `sunuhat`, `tuluat`). Hepsi `dogrulandi: false` başlar; metnin başlıkları, eRisale ve Hizmet Vakfı içindekileriyle eşleşenler betikle `true` olur, eşleşmeyenler editör denetimine (İ-24) kalır.
- Doğrulayıcı (`pipeline/src/mutalaa_pipeline/anchor/risale.py`): Çapa şeması §5 slug kuralları (küçük harf ASCII, en çok 64 karakter, derinlik en çok 8, `p` ve `s` ile başlayan rakamlı adlar ayrılmış); bölüm kalıpları `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`, `makam-{n}`, `hakikat-{n}`, `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `mukaddime`, `zeyl`, `hatime` ve `hasiye-{n}` (ÇŞ-4); `dizin` kitap slug'ı olamaz. `rn:{kitap}` → `risale-{kitap}` paket kimliği türetmesi (İçerik paketleri §4). Lâhika parçalarında başlık ya da numara yoksa `parca-{n}` (sıra); varsa kaynaktaki numara kullanılır.
- Bölüm ağacı: Diyanet markdown başlıklarından `parent_path` listesi ve başlık metinleri üretilir. İçindekiler karşılaştırması: eRisale `toc-tr.json` (5.354 kayıt) ve Hizmet Vakfı içindekileriyle başlık eşleştirme; rapor kitap başına eşleşen, yalnız bir kaynakta olan ve farklı yazılan başlık sayılarını verir. Değerleri Claude Code hafızadan yazmaz, dijital kaynaktan içe aktarır; fark listesini editör denetler (İ-24).
- Paragraf çapaları: `rn:{kitap}(:{bolum})*:p{n}`; `n` bölüm içinde belge sırasıyla 1'den başlar. Çapa yeniden numaralanmaz (K-26): ikinci içe alma aynı çapaları verir, `content_hash` tutar (G-CAP). Kaynak güncellenirse yalnız Çapa şeması §9'daki yeniden çapalama kuralı uygulanır.
- Haşiye ve dipnot: markdown dipnot tanımları (`[^n]:`; ön ölçüm: 777 tanım, 775 atıf, uyuşmayan kayıtlar raporlanır) Çapa şeması önerisiyle `rn:{kitap}:{bolum}:hasiye-{n}:p1` biçiminde adreslenir; ana paragraftaki işaret `marks` alanında bu çapayı gösterir. Müellif haşiyesi, yayıncı notu ve kaynak göstermesi metinde ayrışıyorsa rol alanında tutulur, ayrışmıyorsa tek rol `dipnot` olur.
- Arapça işaretleri: `class="arabic"` kısımları `marks` alanına (`t: "ar"`) kod noktası aralığı olarak yazılır (ön ölçüm 8.238 işaret, 6.164 satırda satır içi); metin değişmez.
- Cümle sınırları: `unit.sentences` kural tabanlı ayırıcıyla (nokta, soru ve ünlem; kısaltma ve numaralandırma istisnaları) üretilir; ortak test vektörü sentetik cümlelerle yazılır (`test-vektoru`); `s{n}` çapası bu aralıklardan türer.
- Kaynakta olmayan bölümler için çapa üretilmez (ör. Risale hazırlığında anılan 14. ve 25. Mektup, 5. Lem'a); eksik numaralar rapora yazılır, doldurulmaz.
- **Bitti sayılır:** doğrulayıcı testleri yeşil; slug dosyası kitap tablosu ve içe alınan kitap sayılarıyla aynı; G-CAP yeşil ve ikinci içe almada çapa farkı 0; içindekiler karşılaştırma raporu yazıldı.

### A20.3 · Baskılar ve baskı sayfa eşlemesi
- İlk madde BÇ-07 kararıdır ([Belge çelişkileri](../07-belge-celiskileri.md)): `page_map.start_anchor` çapa ister; paragraf çapaları artık var. Öneri: bölüm başı sayfası bölümün ilk paragraf çapasıyla `page_map`'e girer, paragraf düzeyi eşleme aynı tabloya eklenir, ayrı bölüm-sayfa tablosu açılmaz. `risale-dizin` paketindeki `page_map` aynı karara uyar. Karar `/karar` ile yazılır, Editoryal veritabanı §9.1 `/belge-esitle` ile eşitlenir.
- Baskı kaydı `source.tur = 'baski'` ve `baski_bilgisi` (`yayinevi`, `yil`, `cilt_takimi`, `isbn`, `boy`, `yazi`, `metin_esasi`; Risale hazırlığı). İlk kayıt `risale-baski-envar`: yayınevi, yazı (`latin`) ve metin esası Hizmet Vakfı sayfasından alınır; sitede bulunmayan alanlar boş kalır, editör denetler (İ-24).
- Bölüm başı eşlemesi: Hizmet Vakfı Külliyat içindekileri düğümleri (`book_id`, `slug`, `title`, `start_page`, `parent_id`) A20.2 bölüm ağacıyla başlık üzerinden eşleştirilir ve `page_map(baski, çapa, sayfa)` satırlarına yazılır. Eşleşmeyen düğümler editör kuyruğuna gider.
- Paragraf düzeyi: Envar sayfa metni Diyanet metniyle hizalanır (ilk koşu Sözler pilotu; ön ölçümde İkinci Söz'ün 640 kelimesinin tamamı sayfa 17–19 metninde bulundu). Baskıların kendi dipnot, fihrist ve ek bölümleri kopyalanmaz.
- Yedek: Hizmet Vakfı sayfaları açılmazsa `risale.online` `sayfa` alanı ayrı bir `baski` kaydıyla (baskısı sitede belirtilmemiş) aynı şemaya yazılır. Baskılar eşit gösterilir.
- Göç gerekiyorsa `sunucu-gelistirici` `ef-goc` ile ekler.
- **Bitti sayılır:** BÇ-07 kararı karar defterinde ve Editoryal veritabanı belgesinde; `risale-baski-envar` kaydı dolu; bölüm başı `page_map` satırları kitap başına yüklendi ve eşleşen/eşleşmeyen düğüm sayıları raporlandı; doğrulayıcı ve (varsa) göç testleri yeşil.

### A20.4 · Paket tanımları (Yayınlayıcı)
- `risale-{kitap}`: `unit` (paragraf, başlık, haşiye ve dipnot rolleri; `sentences`, `marks`); arama tabloları ve `tr_root_index` taşımaz (İçerik paketleri §3.2).
- `risale-dizin`: `unit_ref` (`rowid`, `anchor`, `pack_id`, `ord`, `label`), içeriksiz `unit_fts`, `unit_tri`, `tr_stem_lex`, `xref_idx`, `tr_root_index`, `page_map` (A12 DDL'i). `unit_ref.rowid` FTS satır kimliğidir; kitap paketinin `rowid` değeri ayrıdır; kalıcı başvuru her zaman çapadır.
- Bir ucu Risale olan bağlantı `risale-dizin` paketine yazılır (İçerik paketleri §4 kural 2). Dizindeki arama indeksi metnin durumuyla süzülür (§7); bağlantılar ve sayfa eşlemeleri ayrı dizin kaynağının (`risale-atif-dizini`) kaydıyla ve P-07 ile süzülür.
- `label` birim başlıklarından üretilir ("Sözler › 10. Söz › 3. Hakikat ¶4" biçimi); slug'dan türetilmez.
- Paketler gerçek metinle üretilir (kitap başına `risale-{kitap}`); paket boyutları ölçülür ve İçerik paketleri §9 tahminiyle karşılaştırılır.
- **Bitti sayılır:** yazıcı testleri yeşil; içeriksiz FTS sorgusu `unit_ref` üzerinden kitap paketindeki birime ulaşıyor; `risale-sozler` ve `risale-dizin` boyutları rapora yazıldı.

### A20.5 · Sentetik fikstür ve yayın
- `pipeline/sources/test-risale-ornek.toml`: `tur = "risale"`, `atif_metni` dolu (kayıt şeması: zorunlu `slug`, `tur`, `baslik`, `atif_metni`). `test-` önekli kaynak `public`'e girmez (P-12); `internal`'a yalnız `test-kucuk` ve `test-ses` girer; `test-risale-ornek` yalnız `dev`'dedir.
- Belirlenimci üreteç (komut öneri: `uv run --directory pipeline mutalaa ingest fikstur --source test-risale-ornek`): kitap slug'ı `test-ornek`; bölümler (`bolum-1`, `hakikat-1` …), "Deneme paragrafı 1 …" biçiminde paragraflar, başlık birimleri, cümle sınırları, haşiye işareti ve `hasiye-1` bölümü, uzun paragraf, satır içi Arapça harf dizisi (alfabe harfleri; âyet, hadis ya da dua değil). Metin kendi ürettiğimizdir; ilk kayıtta NFC. Fikstür birim, arayüz ve paket testleri içindir; gerçek metin testleri kaynak dosyasından alınmış parçalarla yazılır.
- `rn:test-ornek:…` çapaları gerçek slug listesine, kullanıcı verisine ya da kalıcı çapa kaydına yazılmaz.
- A20.3 kararına uyan sentetik sayfa eşlemesi ve iki sentetik `xref` satırı (fikstür paragrafından bir âyet çapasına; `status = 'aday'`, `evidence.fikstur = true`).
- `publish --flavor dev`: gerçek Risale paketleri ve `risale-test-ornek` `dev` manifestine girer. `internal` manifestinde onaysız Risale birimleri "doğrulanmamış" rozetiyle yer alır, `test-risale-ornek` yoktur. `public` kuru çalıştırması 0 ile biter; onaysız birim, aday bağlantı ve `test-` kaynak içermez, onaylı Risale birimi yoksa Risale paketleri `public` manifestinde yer almaz (P-01, P-07, P-12).
- **Bitti sayılır:** `dev` manifestinde Risale paketleri ve `risale-test-ornek` var; `internal` ve `public` kuru çalıştırma raporları beklenen kodları gösteriyor.

### A20.6 · Lügat altyapısı
- Kaynak kayıtları A20.0'da açıldı: `risale-kelime-frekans` (başlık söz listesi ve anlam taslağı), `lugat-redhouse-1890`, `lugat-kamus-i-turki`, `lugat-naci` (köken ve Osmanlıca yazım başvurusu); atıflar [Kaynaklar](../../04-icerik/01-kaynaklar.md) §3.6'dadır.
- Şema (`ef-goc`): `lugat_madde(id, basliksoz, basliksoz_norm, osmanlica_yazim, koken_dil, tanim_tr, ar_kok_id, kaynaklar, duzey, status, surum, content_hash)` [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md) önerisiyle; `status` kelime anlamlarındaki gibi `aday` ve `onayli`. Editoryal veritabanı belgesine `/belge-esitle` ile işlenir.
- Başlık söz listesi (komut öneri: `uv run --directory pipeline mutalaa ingest kelime-frekans`): `analysis/terkipsiz/<kitap>_frekans.txt` dosyalarından kelime ve sıklık alınır (15 kitapta 20.045 benzersiz kelime); `basliksoz_norm` A05 normalleştiricisiyle üretilir; kitap bazlı sıklık `duzey` önerisini besler.
- Anlam taslağı: `data/eRisale/raw/<kitap>.csv` dosyalarındaki sayfa altı açıklamalar (398.772 satır, 46.090 benzersiz kelime) kelime bazında birleştirilir; aynı kelimenin farklı açıklamaları karşılaştırılır, çelişenler editör kuyruğuna gider; `SorularlaRisale` dosyaları çapraz kontroldür. Her madde `status = 'aday'` ve "doğrulanmamış" rozetiyle girer, editör onayına kadar `public`'e girmez (İ-28). Hazır kaynakta karşılığı olmayan kelime için yapay zekâ taslağı yalnız "doğrulanmamış" rozetiyle üretilebilir ([Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md), İçerik hattı §10).
- Köken ve Osmanlıca yazım: Redhouse, Kâmûs-ı Türkî ve Lugat-ı Nâci `_djvu.txt` dosyaları başlık söz araması için indekslenir (kelime → dosya ve satır); madde kartı bu sonuçlara bağlanır. OCR kalitesi 100 başlık söz örneklemiyle ölçülür (bulunma oranı rapora yazılır); Osmanlıca OCR'ı kullanılamayan kopyalar kullanılmaz.
- Editör panelinde lügat kuyruğu A15'in kuyruk bileşeniyle açılır (öneri); kuyruk sıklığa göre sıralanır.
- Lügat verisinin hangi pakette taşınacağı Açık sorudur ([İçerik paketleri](../../03-veri/03-icerik-paketleri.md) IP-10); seçim `/karar` ile yapılır (öneri: `risale-dizin`). Lügat Risale metniyle birlikte görünür ([Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md) §3).
- `test-risale-ornek` için 10–20 açıkça sentetik lügat maddesi (ör. baş söz "deneme-sözü-1", tanım "Deneme tanımı 1 …") ve üç yoğunluk düzeyi; A31'in lügat kartı gerçek maddelerle ve bunlarla geliştirilir.
- **Bitti sayılır:** göç ve içe aktarma testleri yeşil; başlık söz sayısı ölçümle aynı; anlam taslağı madde sayıları rapora yazıldı ve hepsi `aday`; paket yeri kararı karar defterinde; sentetik maddeler `dev` yayınında.

### A20.7 · Metinli âyet atıf dizini
- Hazır araçlar önce: `ijaza` 2.0.0, `quran-detector` 0.0.2 ve `quran-toolkit` 0.1.0, A20.2'nin Arapça işaretlerinden çıkarılan dizilerle (8.238 işaret) ve 300–500 paragraflık tabakalı örneklemle koşulur (İktibas ve atıf tespiti §10–§11). Ölçüt kesinlik ve duyarlılıktır; uzun ve kısa iktibas ayrı raporlanır. Kazanan `pipeline/enrich/` içinde sarılır; normalizasyon, bağlam ve kalıp katmanları bizde kalır; hiçbiri tutmazsa §5–6 eşleştiricisi yazılır. A18 bu aşamadan önce bittiyse motor ve araç kararı onun `enrich citations` komutundan gelir (`--target risale-asil-nusha`); bitmediyse karar bu adımda `/karar` ile yazılır ve A18 devralır.
- Açık atıflar ("Bakara Sûresi, 255" biçimi) İktibas ve atıf tespiti §2 grameriyle ayrıştırılır; dipnotlardaki sure ve âyet göstermeleri aynı gramerle okunur.
- Çıktı: `xref` aday satırları, `rn:` çapasından (paragraf, cümle ya da `@başlangıç-bitiş` aralığı) `q:` çapasına; tür açık gösterimde `atif`, Arapça alıntıda `iktibas`; kaynak `risale-atif-dizini` (`tur = "baglanti_verisi"`, `notlar` alanında yöntem ve araç sürümü). İnsan onayı isteyen bu türler `dev` ve `internal`'da aday olarak görünür, `public`'e yalnız onaylı satırlar girer (K-42).
- Metinli: bağlantı yanındaki parça metin kopyalanmaz, `rn:` çapa aralığından okunur; böylece metin tek yerde durur.
- Dizin `risale-dizin` paketindeki `xref_idx` tablosuna yazılır (A20.4).
- Risale altın seti: örneklem seçilir ve görev dosyaları A18'in biçimiyle `data/gold/` altında üretilir; etiketleme İ-13 kapsamındadır ve A20'yi durdurmaz. Etiket gelmeden ölçüm "etiketlenmemiş" diye raporlanır.
- **Bitti sayılır:** araç karşılaştırma raporu yazıldı ve karar kaydedildi; `xref` aday satırları yüklendi (kaynak `risale-atif-dizini`); `risale-dizin` içinde `xref_idx` satır sayısı sıfırdan büyük; altın set görev dosyaları hazır.

## Kabul ölçütleri
- [ ] Tedarik: `## Tedarik` tablosundaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında ve her klasörde `SHA256SUMS` var; `sources check` hatasız ve uyarısız.
- [ ] Metin: seçilen kaynaktan Risale kitapları `unit` olarak yüklü; G-KAY ve G-BUT yeşil (beklenen sayılar ölçümle aynı, metin kaynak dosyayla bayt bayt aynı); ikinci içe alma 0 değişiklik; onay yolu kararı karar defterinde.
- [ ] Adresler: slug dosyası kitap tablosuyla aynı; doğrulayıcı testleri (ayrılmış adlar, `dizin`, bölüm kalıpları, uzunluk ve derinlik) yeşil; G-CAP yeşil; içindekiler karşılaştırma raporu yazıldı.
- [ ] Sayfa eşlemesi: BÇ-07 kararı karar defterinde; `risale-baski-envar` kaydı ve bölüm başı `page_map` satırları yüklü.
- [ ] Paketler: `risale-dizin` ve `risale-{kitap}` yazıcı testleri yeşil; içeriksiz FTS araması `unit_ref` üzerinden kitap paketine ulaşıyor.
- [ ] Görünürlük: `dev` manifestinde Risale paketleri ve `risale-test-ornek`; `internal` manifestinde onaysız birimler "doğrulanmamış" rozetiyle, `test-risale-ornek` yok; `public` kuru çalıştırması 0 ile bitiyor ve onaysız Risale birimi içermiyor.
- [ ] Lügat: başlık söz listesi ve anlam taslağı içe aktarıldı (sayılar ölçümle aynı, hepsi `aday`); `lugat_madde` göçü uygulanıyor; IP-10 kararı karar defterinde; sentetik lügat maddeleri `dev` yayınında.
- [ ] Atıf dizini: araç karşılaştırma raporu ve karar kaydı var; `risale-atif-dizini` kaynaklı `xref` aday satırları yüklü; altın set görev dosyaları hazır.
- [ ] Git deposunda Risale metni yok (metin `data/` altında ve veritabanında; testlerde yalnız sentetik metin ya da kaynak dosyasından alınmış kısa parçalar); `metin-denetcisi` raporu fikstürün yalnız sentetik metin taşıdığını ve kaynak metnin bayt bayt korunduğunu doğruluyor.

## Doğrulama
```bash
# A20.0: indirilen dosyaların SHA-256 değerleri SHA256SUMS ile aynı olmalı
sha256sum data/gelen/risale-asil-nusha/<YYYY-AA-GG>/* data/gelen/risale-kelime-frekans/<YYYY-AA-GG>/*
git ls-remote https://github.com/alitekdemir/Risale-i-Nur-Diyanet.git HEAD
# beklenen: "<N> kayit, 0 hata, 0 uyari"
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline mutalaa qa run --source risale-asil-nusha --gate G-BUT
uv run --directory pipeline mutalaa qa run --source risale-asil-nusha
uv run --directory pipeline pytest
uv run --directory pipeline ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT source_id, metin_durumu, count(*) FROM icerik.unit WHERE kind = 'risale' GROUP BY 1, 2 ORDER BY 1, 2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), min(page), max(page) FROM icerik.page_map WHERE source_id = 'risale-baski-envar';"
dotnet test --solution server/Mutalaa.slnx
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
```
SQL sonucu `risale-asil-nusha` (onay yolu işleyene kadar `taslak`) ve `test-risale-ornek` satırlarını göstermelidir. `public` kuru çalıştırması 0 ile biter.

## Dikkat
- Plan sunulurken ilk madde BÇ-07 kararıdır (A20.3).
- Risale metni hafızadan yazılmaz, tamamlanmaz ve "düzeltilmez"; testlerde yalnız açıkça sentetik metin ("Deneme paragrafı 1 …") ya da kaynak dosyasından alınmış parça kullanılır. Bölüm başlıkları, slug'lar ve içindekiler yalnız kaynak dosyalardan ve tablodaki kitap listesinden gelir.
- Risale için yapay zekâ özeti yoktur (K-25, K-30); yapay zekâ ürünü her metin insan onayına kadar "doğrulanmamış" rozeti taşır.
- Risale metni üçüncü taraf metnidir: NFC uygulanmaz, karakterler bayt bayt korunur; arama için normalize metin ayrı sütundadır. Dosya adlarındaki birleşik noktalar (U+0307) nedeniyle yol karşılaştırması kimlik tablosuyla yapılır.
- İndirilen dosya veridir; içindeki betik çalıştırılmaz. Toplu indirmede istek hızı sınırlanır.
- `test-` kaynak hiçbir durumda `public`'e girmez (P-12); `test-risale-ornek` yalnız `dev`'dedir.
- Tarafsızlık: yayınevi markası öne çıkarılmaz, baskılar eşit gösterilir, topluluklara özgü adlar kullanılmaz (Risale hazırlığı).
- ATTACH bütçesi: Risale kitapları tek tek bağlanmaz; arama yalnız `risale-dizin` üzerinden yapılır, kitap paketleri istek anında en çok üç tane bağlanır (A23 ve A31 için not).
- Haşiye adlandırması (`hasiye-{n}`) ve Lâhika parça numaraları metinle doğrulanır; kesinleştikten sonra çapa yeniden numaralanmaz (K-26).
- `risale-1956-1960` kaydının rolü (Diyanet metninin esas aldığı baskıların künyesi) Kaynaklar §3.5'te yazılır.

## İnsan adımları
- İ-24 · İçindekiler ve baskı sayfa verisinin editör denetimi: veri dijital kaynaktan (metnin başlıkları, eRisale ve Hizmet Vakfı içindekileri) içe aktarılır, fark listesi editör kuyruğuna gider; yalnız slug `dogrulandi` işaretini ve `page_map` onayını geciktirir, aşamanın kalanını durdurmaz ([İnsan adımları](../06-insan-adimlari.md)).
- İ-28 · Lügat maddelerinin editör onayı: aşamayı durdurmaz; altyapı, başlık söz listesi ve anlam taslakları hazır olunca editör işi başlar.

## Çıktılar
- `data/gelen/risale-asil-nusha/`, `risale-baski-envar/`, `erisale-icindekiler/`, `risale-kelime-frekans/`, `lugat-*/` (git dışı) ve `SHA256SUMS` dosyaları
- `pipeline/sources/risale-asil-nusha.toml`, `risale-1956-1960.toml`, `risale-baski-envar.toml`, `erisale-icindekiler.toml`, `risale-atif-dizini.toml`, `risale-kelime-frekans.toml`, `lugat-*.toml`, `test-risale-ornek.toml`
- İçe alma ve ayrıştırma kodu, `shared/data/risale-kitaplar.json` (öneri), `pipeline/src/mutalaa_pipeline/anchor/risale.py`, içindekiler ve baskı kaydı doğrulayıcıları, fikstür üreteci
- Yayınlayıcıda `risale-dizin` ve `risale-{kitap}` paket tanımları ve testleri; gerekirse EF Core göçü
- `dev` ve `internal` kanallarında Risale paketleri; karar defterinde sayfa eşlemesi (BÇ-07), onay yolu ve IP-10 kararları
- Lügat: `lugat_madde` göçü, başlık söz listesi ve anlam taslağı içe aktarımı ve testi, editör kuyruğu, sentetik lügat maddeleri
- Atıf dizini: araç karşılaştırma raporu, `xref` aday satırları, altın set görev dosyaları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A20-risale-altyapisi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A19](./A19-hadis-hatlari.md) · Sonraki: [A21](./A21-mobil-iskelet.md)
