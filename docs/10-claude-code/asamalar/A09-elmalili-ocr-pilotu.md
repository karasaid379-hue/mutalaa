# A09 · Elmalılı OCR pilotu ve yol seçimi (OCR motorları ve hazır metin adayları, K-38)

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · [A06](./A06-kaynak-kayitlari-ve-enumlar.md) · **İnsan adımı:** [İ-09, İ-10, İ-17](../06-insan-adimlari.md)
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · **Tahmini oturum:** 2–4 Claude Code oturumu; insan emeği ayrıca
> **Başlat:** `/asama A09`

## Amaç
Elmalılı'nın özgün baskısı (baskı kimliği `elmalili-1935`) için iki belirsizlik ölçümle kapanır: baskının yazı türü (K-03 düzeltmesi: Türkçe metin büyük olasılıkla Latin harfli, âyetler Arapça harfli; Doğrulanacak) ve metin yolu. Yol, OCR motorlarıyla hazır metin adaylarının (K-38; meal için Vikikaynak "Kur'an" ve Tanzil `tr.yazir`, tefsir için archive.org metin katmanı ve YEK 2021 tenkitli metni) aynı altın örneklemde yarıştırılmasıyla seçilir. En az iki OCR motoru ve kayıtlı hazır metin adayları 40 sayfalık tabakalı örneklemde ölçülür; insan yazımı altın metne karşı CER ve WER hesaplanır, hazır metin için ayrıca sadeleştirme izi sayılır ve tam metin denetimi yapılır. Maliyet tahmin edilir ve yol kararı `/karar` ile yazılır. Hazır metin yolu yalnız eşik geçilirse geçerlidir (başlangıç önerisi: meal bloklarında CER ≤ %1, sadeleştirme izi 0; eşik pilottan sonra kesinleşir); geçilmezse OCR yolu aynen sürer. Faz 0 çıkış ölçütü "OCR yöntemi ya da hazır metin yolu ölçümle seçildi ve yazıldı" bu aşamayla sağlanır. Meal aktarımı ve düzeltme turları A16'dadır.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §3 kaynak baskı ve tarama standardı, §4 OCR ve değerlendirme, §5 (yalnız Yol A çıkarsa), §8 QA ölçütleri, §11 açık sorular
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §3 `mutalaa.toml` ve Kraken notu, §4 komutlar, §5 veri soyu, §7 günlük, §10 yapay zekâ politikası, §11 maliyet, §12 çalıştırma manifesti
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.3 (`elmalili-meal`, `elmalili-tefsir`), §4 (seçilmeyen adaylar), §5 (yeni kaynak ekleme)
- [Karar defteri](../../00-ozet/02-karar-defteri.md): K-03 ve 18 Ekim 2026 düzeltmesi; [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 1–4 (kontrollü hazır metin, çıkarılmış metin, `taslak` başlangıç durumu); [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1, 2 ve 4 (tedarik, indirme, kaynak kaydı)
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.4 (OCR adayları)

## Kapsam
**Yapılır**
- Tedarik doğrulaması ve indirme (A09.0): `## Tedarik` tablosundaki kaynakların `data/gelen/<kaynak>/<YYYY-AA-GG>/` altına alınması, `SHA256SUMS`, kaynak kayıtları.
- `uv run mutalaa ingest scans` komutu ve taramaların `data/raw` altına kaydı; tarama kaynağının (adres ya da nüsha, tarih) kaynak kaydına işlenmesi.
- Yazı türünün tarama üzerinde doğrulanması; baskı doğrulama listesinin eldeki nüsha için doldurulması.
- 40 sayfalık örneklem ve altın metin için karşılaştırma aracı (altın metni insanlar yazar, İ-10).
- `ocr run` (en az iki motor), `ocr eval` (CER, WER ve alt ölçüler), görsel model için `llm estimate`.
- Hazır metin adaylarının kaydı ve kilidi, internetteki aday taramaların kimlik ve ofset sınaması, hazır metnin aynı altın örneklemde CER ve sadeleştirme izi ölçümü, tam metin denetimi (A09.6–A09.9). Bunun için yalnız ölçüme yetecek asgari okuyucu yazılır: kilitli dosyadan (Vikikaynak wikitext, Tanzil metin dosyası, `djvu.txt` ya da metin katmanlı PDF) altın örneklemin karşılığı çıkarılır. Bu okuyucu ölçüm içindir; kalıcı değildir: `ingest/` altına konmaz, `data/staged` ya da PostgreSQL'e yazmaz, ölçüm dışında kullanılmaz. `pipeline/src/mutalaa_pipeline/qa/` altında ölçüm aracının yanında durur ve yalnız sentetik girdiyle (açıkça uydurma metin içeren küçük wikitext, metin dosyası ve PDF örnekleri) birim testlidir; gerçek aday metin teste girmez. Kalıcı okuyucular, `ingest register` ve çıkarılmış metin test vektörü A16'ya kalır.
- Pilot raporu, yol kararı (hazır metin mi OCR mı) ve `pipeline/mutalaa.toml` güncellemesi.

**Yapılmaz**
- Meal bloklarının âyetlere bölünmesi, Tanzil eşleştirmesi, inceleme kuyruğu, G-MET ve G-HIZ kapıları, 6.442 sayfanın tamamının OCR'ı (A16).
- Kalıcı hazır metin içe aktarımı: HTML, EPUB ve PDF okuyucuları, `ingest register` komutu ve çıkarılmış metin test vektörü (K-38 madde 3). Bunlar planlıdır, henüz yoktur; A16'nın hazır metin dalına bırakılır.
- Hazır metnin pakete ya da `public`/`internal` derlemeye alınması: aday yalnız ölçülür; onaysız birim `public`'e girmez (K-42 madde 5) ve hazır metin A16'da `taslak` olarak içe alınır (K-38 madde 4).
- Tefsir metni (A37). Latin harfine aktarım kılavuzunun uygulanması (A16; Yol A çıkarsa bu aşamada yalnız aktarım doğruluğu ölçülür). Tefsir için hazır metin adayları (archive.org metin katmanı, YEK 2021) yalnız aynı ölçümün küçük bir örneğiyle denenir; kalıcı karar A37'dedir.
- Editör panelindeki OCR kuyruğu (A15).

## Tedarik
Ölçüm tarihi 1–2 Kasım 2026. Ölçütler: özgün baskıya sadakat, eksiksizlik, biçim, sürüm sabitleme, doğrudan alınabilirlik. Aşağıdaki sayımlar yalnız sayım ve biçim bilgisidir.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Özgün baskı sayfa görselleri (1935–1938; altın örneklem ve OCR girdisi) | Basılı nüshanın taranması: 1935 baskısı, olmazsa 1960/1971 ofset takımı; 400 dpi gri tonlama, kayıpsız TIFF (İ-09, koşullu). İnternette bu baskının taraması bulunamadı (ön bulgular tablonun altında); internet adayları A09.7'de sınanır | Basılı takım: kullanıcı edinir ve tarar, dosyalar `data/gelen/elmalili-1935/<YYYY-AA-GG>/` altına konur. İnternet adaylarının sayfaları: IIIF `https://iiif.archive.org/iiif/<öğe>$<yaprak>/full/full/0/default.jpg` (tek sayfa; `HakDiniKuranDili$10` için `info.json` 200) ya da `https://archive.org/download/<öğe>/<dosya>` | Princeton: 8 cilt, 6.442 sayfa; YEK 2021 önsözü: 9 cilt (9. cilt fihrist; c. 1: 1935, c. 2–6: 1936, c. 7–9: 1938). Cilt başına sayfa sayısı elde edilen nüshada A09.1'de sayılır | HathiTrust 1935 kaydı 102700938 (8 cilt) ve 1960 kaydı 007373234 (9 cilt): yalnız arama, görüntü yok |
| Meal: hazır metin adayı 1 | Vikikaynak `Kur'an/<Sure> Suresi` (tr.wikisource.org; 125 başlık = 114 sure sayfası + 11 yönlendirme); sürüm: sayfa başına `revid`, aralık 74319–158621; 114 sayfanın `başlık TAB revid` listesinin SHA-256'sı `965a6249…b308a`; biçim wikitext, âyet işareti `kısım` şablonu | MediaWiki API: `https://tr.wikisource.org/w/api.php?action=query&prop=revisions&rvprop=ids\|timestamp\|size\|sha1\|content&rvslots=main&titles=<50 başlık>&format=json` (50 başlık/istek, istekler arası 1,5 sn, kimlikli `User-Agent`). Toplu yol: `https://dumps.wikimedia.org/trwikisource/20261001/trwikisource-20261001-pages-articles.xml.bz2` (25.341.657 bayt, SHA-1 `909ca820…bb00`) | 114/114 sure; `kısım` işareti 6.238, benzersiz âyet 6.236 (Tanzil sayımıyla birebir); numarasız 3 işaret (Sâd 59/60, Secde 28/29, Kasas 47/48) ve 2 aralıklı işaret (Tekvîr 8-9, Mutaffifîn 4-5); `revid` aralığı 1 ve 2 Kasım 2026'da aynı | Tanzil `tr.yazir`; dump |
| Meal: hazır metin adayı 2 | Tanzil `tr.yazir` ("Elmalılı Hamdi Yazır"; üstbilgi: "Last Update: June 4, 2010", "Source: Tanzil.net"); biçimler `txt-2` (sure, âyet ve metin sütunları) ve `xml` | `https://tanzil.net/trans/?transID=tr.yazir&type=txt-2` ve `…&type=xml` (doğrudan dosya, 200) | 6.236 âyet satırı (+13 üstbilgi satırı), 944.235 bayt, SHA-256 `4c9a6bea…f926` (1 ve 2 Kasım 2026'daki iki ayrı indirmede aynı); XML 1.100.494 bayt, SHA-256 `5097940d…ba43` | fawazahmed0/quran-api `editions/tur-elmalilihamdiya.json` @ `93e6f64925ae76273520d636fcaaf061129f2316` (1.494.041 bayt; Tanzil metninin yansıması, aynı sözcük kümesi) |
| Tefsir: hazır metin adayları (A37'ye girdi) | (1) archive.org `HakDiniKuranDili`: `…_djvu.txt` (11.444.009 bayt, SHA-1 `735617d9…5e1b`), Eser Neşriyat 3. Baskı 1979 sayfa numaralarına uydurulmuş Latin harfli dijital metin. (2) YEK 2021 tenkitli metin, archive.org `hak-dini-kuran-dili-1-6-elmalili-muhammed-hamdi-yazir-yek-yay` (Text PDF 257.728.381 bayt, SHA-1 `0cc7e395…d733`; `…_djvu.txt` 13.692.391 bayt, SHA-1 `933d450d…27cc`); katalog kaydına göre hazırlayanlar A. C. Köksal ve M. Kaya | `https://archive.org/download/<öğe>/<dosya>` (302 sonra 200; boyutlar HEAD ile doğrulandı); özetler `https://archive.org/metadata/<öğe>` | `HakDiniKuranDili`: 8.928 yaprak, sayfa numarası okunan yaprak 0, metnin yaklaşık %3'ü Arap yazısı; YEK: 300 ppi, `…_page_numbers.json` 1.031.656 bayt; yaprak ve cilt sayımı A09.0'da | `Elmalili0110OrjinalYenda` (`…_djvu.txt` 13.033.115 bayt, yeni dizgi). Sadeleştirilmiş takımlar aday olamaz |
| Metin okuyucuları (ölçüm için) | `mwparserfromhell` 0.7.2 (wikitext); standart kitaplık (Tanzil biçimi ve `djvu.txt`); `pypdf` 6.21.4 (PDF metin katmanı) | `uv add --directory pipeline mwparserfromhell pypdf` | PyPI: 0.7.2 (2025-07-01, cp313 tekeri), 6.21.4 (2026-10-28) | Düzenli ifade |
| CER ve WER hesabı | `rapidfuzz` 3.14.6 (zaten bağımlılık): `rapidfuzz.distance.Levenshtein.editops` yer değiştirme, silme ve eklemeyi sayar (proje ortamında denendi); WER için aynı işlev sözcük dizilerinde | Yok (kurulu) | PyPI: 3.14.6 (2026-08-30, cp313) | `jiwer` 4.0.0 (2025-06-19) |
| Görsel okuma ve dönüştürme | `pillow` 13.0.0 (PNG ve TIFF dönüştürme, küçültülmüş kopya); gerekirse `pypdfium2` 5.14.0 (PDF sayfasını görsele) | `uv add --directory pipeline pillow` | PyPI: pillow 13.0.0 (2026-10-16, cp313), pypdfium2 5.14.0 (2026-10-04) | `pikepdf` 10.17.0 |
| OCR motoru 1 | Tesseract 5: `tesserocr` 2.12.0 (PyPI, 2026-10-22; `cp313-cp313-win_amd64.whl` 23.142.504 bayt, motor tekerin içinde) ve `tessdata_best` @ `e12c65a915945e4c28e237a9b52bc4a8f39a0cec` (`tur.traineddata` 7.456.265, `ara.traineddata` 12.603.724, `osd.traineddata` 10.562.727 bayt) | `uv add --directory pipeline --optional ocr tesserocr`; dil dosyaları `https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/e12c65a915945e4c28e237a9b52bc4a8f39a0cec/<dil>.traineddata` (3'ü de 200) | Tesseract'ın kendi etiketi 5.5.4 (`git ls-remote`); tekerin motor sürümü `tesserocr.tesseract_version()` ile A09.0'da okunur | `tesseract` komutu (UB-Mannheim Windows yükleyicisi 5.5.3.20260724: sunucu 2 Kasım 2026'da 403 verdi; winget kaydı 5.4.0.20240606) ya da Docker kabı; `pytesseract` 0.3.13 |
| OCR motoru 2 | `kraken` 7.1.1 (PyPI, 2026-09-04; Python ≥3.10 ve <3.14, 3.13 sınıflandırıcısı). Modeller (Zenodo): CATMuS-Print [Large], Latin harfli basılı metin, `catmus-print-fondue-large.mlmodel` 22.874.456 bayt, DOI 10.5281/zenodo.10592716; Printed Arabic-Script Base Model (OpenITI), `all_arabic_scripts.mlmodel` 16.277.053 bayt, DOI 10.5281/zenodo.7050270; Printed Ottoman Base Model (OpenITI), `ottoman_best.mlmodel` 16.282.182 bayt, DOI 10.5281/zenodo.7050342 | `uv add --directory pipeline --optional ocr kraken`; model dosyaları `https://zenodo.org/api/records/<kayıt>/files/<dosya>/content` (3'ü de 200, boyutlar kayıtla aynı) | PyPI kaydı; model boyutları Zenodo kaydıyla eşleşti. Türkçe Latin harfli 1930'lar dizgisi için hazır model yok: CATMuS-Print genel Latin modelidir, ölçüm yetersizse altın sayfalarla ince ayar (A09.3) | eScriptorium (Kraken arayüzü); öteki Zenodo modelleri |
| Görsel yapay zekâ modeli | Anthropic Messages API (ücretli): `claude-opus-5-5` (girdi 4 $, çıktı 20 $ / MTok), `claude-sonnet-5-5` (2 $ ve 10 $), `claude-haiku-5-5` (0,10 $ ve 0,50 $; 100.000 belirteçlik isteme kadar) (modeller ve fiyat sayfaları, 2 Kasım 2026); SDK `anthropic` 2.3.0 (2026-10-23; zaten bağımlılık). Görsel: 28×28 pikselik yama = 1 görsel belirteç, sayısı ⌈genişlik/28⌉ × ⌈yükseklik/28⌉; görsel başına en çok 8000×8000 piksel | API; anahtar `pipeline/.env` içinde (İ-17, hesap: altyapı); ücretli iş: tahmini maliyet kullanıcıya gösterilir, `llm estimate` 2–3 sayfayla ölçer | models, vision ve pricing sayfaları 200; kimlikler modeller sayfasında geçiyor. `pipeline/mutalaa.toml` içindeki `[llm] model` yer tutucusu A09.5'te seçilen kimlikle değişir | Yok (görsel model başka sağlayıcıyla yarıştırılmaz; ölçüm Tesseract ve Kraken ile sürer) |

Ön bulgular (1–2 Kasım 2026; yalnız künye, sayım ve biçim bakışı):
- **İnternette 1935 taraması yok.** archive.org başlık ve yazar sorgularında Hak Dini Kur'an Dili adıyla yaklaşık 30 öğe çıktı; 1935–1975 tarihli öğe yok. Örnek sayfalarına bakılan öğelerden `HakDiniKuranDili`, bir dijital metnin sayfa görseli dökümüdür, taranmış baskı değildir (metinde "3. Baskı, Eser Neşriyat ve Dağıtım, İstanbul 1979" sayfa numaralarına uygunluk notu var; `page_numbers.json` 8.928 yaprağın hiçbirinde sayfa numarası okumadı). `hak-dini-kuran-dili-cilt-1-elmalili-hamdi-yazir` (10 PDF), `Elmalili0110OrjinalYenda` (600 ppi) ve `cilt-6` yeni dizgidir; `…-yek-yay` YEK 2021 baskısıdır (1. baskı, 1500 adet); `hak-dini-kuran-dili-osm-c-1` … `-osmanlica.-c-7` Arap harfli el yazması sayfalarıdır. Sure sure PDF öğelerinin (`ElmaliliKuranTefsiri`, `Elmalili-Tefsiri`) 1938 tarih etiketi yükleyicinin girdisidir; sayfalarına A09.7'de bakılır.
- **HathiTrust.** Katalog kayıtları açılıyor (1935: htid `uc1.l0070344825` … `uc1.l0071187314`, v.1–v.8). Tam metin araması otomatik isteği Cloudflare doğrulamasına takıyor ("Just a moment…", 1 Kasım 2026); sayfa numarası doğrulaması A09.7'de `WebFetch` ile denenir, olmazsa künye düzeyinde kalınır.
- **Seçilmeyenler.** İBB Atatürk Kitaplığı reprodüksiyonu başvuru gerektirir. Millî Kütüphane ve İBB sitelerinde doğrudan indirilebilir 1935 kopyası bulunamadı. Açık Kuran (`api.acikkuran.com` 1 ve 2 Kasım'da çözümlenmedi; GitHub deposu sunucu kodu, veri kümesi yok) ve kuranmeali.com (otomatik istek 403) doğrudan alma yolu vermediği için seçilmedi.
- **Yazı türü.** Wikimedia Commons'taki tek fotoğraf (`File:Elmalı 35 baskısı.jpg`, 613×487 px) 7. cildin Fihrist başlık sayfasını gösteriyor; künye Latin harfli ("Matbaai Ebüzziya, İstanbul"). Bu, K-03 düzeltmesindeki Latin harf varsayımını destekler; sayfa üzerinde A09.1'de doğrulanır.
- **Yakınlık vekil ölçüsü.** Aday âyetlerin sözcük üç-gramlarının `HakDiniKuranDili` metninde bulunma oranı: Vikikaynak 0,843; Tanzil `tr.yazir` 0,162; sadeleştirilmiş `tur-elmallsadelesti` 0,245. Ölçü Eser 1979 dijital metnine göredir, 1935 baskısına değil; sadakati yalnız 1935 sayfalarından yazılan altın metin belirler.

Kendimiz yapacağımız işler: altın metin (İ-10, insan emeği); örneklem seçim betiği; `ingest scans`, `ocr run`, `ocr eval` ve `llm estimate` komutları ile motor bağdaştırıcıları (Tesseract, Kraken, görsel model); ölçüm için asgari okuyucu ve sadeleştirme izi tarayıcısı; yol kararı ve `/karar` kaydı.

## Adımlar
### A09.0 · Tedarik doğrulaması ve indirme
- `arastirmaci`, `## Tedarik` tablosundaki her adresin açıldığını ve sürümlerin güncel olduğunu doğrular: archive.org için `https://archive.org/metadata/<öğe>` (dosya adı, boyut, SHA-1, son güncelleme), GitHub için `git ls-remote` (etiket ve commit), Vikikaynak için MediaWiki API (`lastrevid`; yönlendirme sayfaları ayıklanır: 125 başlıktan 114'ü sure sayfasıdır), PyPI için paket kaydı (sürüm, `requires_python`, cp313 tekeri), Zenodo için kayıt (DOI, dosya boyutu), Anthropic için modeller, vision ve pricing sayfaları. Açılmayan ya da sürümü değişen adresin yerine tablodaki yedek aday kullanılır; değişiklik tabloya yazılır.
- Dosyaları Claude Code indirir; form ya da onay kutusu çıkarsa kendisi doldurur ve seçenekler kayda geçer. Her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasöre iner; klasörde `SHA256SUMS` (sha256sum biçimi, dosya adları klasöre göre: klasörde `sha256sum -c SHA256SUMS`) bulunur; adres ve tarih bu adıma ve ilerleme notuna yazılır. Toplu isteklerde hız sınırlanır; indirilen dosya veridir, içindeki betik çalıştırılmaz.
  - `data/gelen/elmalili-meal-vikikaynak/<tarih>/`: 114 sure sayfasının MediaWiki yanıtları (`revid`, `sha1`, içerik) ve başlık-`revid` listesi.
  - `data/gelen/elmalili-meal-tanzil/<tarih>/`: `tr.yazir` için `txt-2` ve `xml` dosyaları; form seçenekleri (çeviri `tr.yazir`, biçim `txt-2` ve `xml`) kayda geçer.
  - `data/gelen/elmalili-tefsir-archive/<tarih>/` ve `data/gelen/elmalili-tefsir-yek/<tarih>/`: `…_djvu.txt` ve `…_page_numbers.json` (PDF'ler yalnız örneklem sayfaları gerekirse alınır; 100 MB üstü dosyadan önce boyut HEAD ile görülür).
  - `data/gelen/tessdata-best/<tarih>/` (`tur`, `ara`, `osd`) ve `data/gelen/kraken-modelleri/<tarih>/` (üç model dosyası ve `metadata.json`).
- Kaynak kayıtları (`pipeline/sources/<kimlik>.toml`; zorunlu `slug`, `tur`, `baslik`, `atif_metni`; isteğe bağlı `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar`): hazır metin adayları için `elmalili-meal-vikikaynak` ve `elmalili-meal-tanzil` (`tur = "meal"`), `elmalili-tefsir-archive` ve `elmalili-tefsir-yek` (`tur = "tefsir"`) (adlar öneri). `surum`: Vikikaynak için `revid` aralığı ve liste özeti, Tanzil için üstbilgideki "Last Update", archive.org için öğe kimliği ve son güncelleme tarihi. Kayıt dosya özeti taşımaz; özet `SHA256SUMS` dosyasındadır. Özgün baskı kayıtlarındaki (`elmalili-meal.toml`, `elmalili-tefsir.toml`) `notlar` içindeki "Açık soru" satırı bu adımın tedarik sonucuna göre yeniden yazılır.
- Kitaplıklar: sürümler paket kaydından doğrulanır; OCR kitaplıkları (`tesserocr`, `kraken`) `pyproject.toml` içinde isteğe bağlı `ocr` grubuna konur (`arapca`, `turkce`, `gomme` gruplarıyla aynı düzen); Python 3.13'te bağımlılık çözümlemesi çakışırsa Kraken `pipeline/ocr-kraken/` altındaki ayrı uv projesine taşınır (İçerik hattı §3).
- **Bitti sayılır:** tablodaki her adres açıldı ve sürümler tabloyla uyumlu (fark varsa tablo güncel); dosyalar `data/gelen/<kaynak>/<tarih>/` altında ve `SHA256SUMS` doğrulanıyor; kaynak kayıtları yazıldı; `uv run --directory pipeline mutalaa sources check` 0 hata, 0 uyarı; `ocr` grubu kuruluyor ve `tesserocr.tesseract_version()` çıktısı not edildi.

### A09.1 · Taramalar ve yazı türü (İ-09)
- Görsel kaynağı sırası (K-38): önce internetteki taramalar; sınama A09.7'dedir ve A09.0'dan hemen sonra, bu adımdan önce yapılır (A09.7'nin numarası değişmez). `## Tedarik` ön bulgusuna göre 1935 baskısının ya da 1960/1971 ofsetinin alınabilir taraması bulunamadı; sınama bunu doğrularsa görsel kaynağı basılı nüshanın taranmasıdır ve İ-09 `bekliyor` olur. Bekleme yalnız taramaya bağlı alt adımları (bu adımın görüntü işleri, A09.2–A09.5) bağlar; A09.0, A09.6, A09.7 ve A09.8'in otomatik kısımları sürer. Özgün baskı taraması hazır metin yolunda da gerekir: altın örneklem buna dayanır.
- `arastirmaci` internetteki aday koleksiyonları (archive.org, HathiTrust, Wikimedia Commons, Millî Kütüphane, İBB) yeniden yoklar; başvuru isteyen kaynak seçilmez.
- Kullanıcı basılı nüshayı taratır ve taramaları proje içindeki `data/gelen/elmalili-1935/<YYYY-AA-GG>/` klasörüne koyar (klasör sınırı, `data/` git dışı). Dosya adı `c{cilt:02d}-s{sayfa:04d}.tif`; tarama standardı §3'teki öneridir (en az 400 dpi gri tonlama, kayıpsız TIFF).
- `uv run mutalaa ingest scans --edition elmalili-1935 --dir data/gelen/elmalili-1935/<tarih>/c01 --cilt 1` dosyaları `data/raw/elmalili-1935/{YYYY-MM-DD}/` altına kopyalar, SHA-256 ve `fetch.json` yazar (İçerik hattı §5). `data/raw` yalnız bu komutla yazılır. Komutların yol argümanları depo köküne göre çözülür (öneri; Elmalılı hazırlığı §4'teki örneklerle uyumlu).
- Tarama kaynağı (nüsha, baskı yılı, yer ya da yer numarası, tarama tarihi) `pipeline/sources/elmalili-meal.toml` ve `elmalili-tefsir.toml` içindeki `baski_bilgisi` alanına, adres varsa `kaynak_url` alanına işlenir (§3, §9).
- Yazı türü: künye sayfası ve birkaç metin sayfası `.tmp/` altına PNG olarak çevrilir (ör. `uv run --with pillow` ile bir betik) ve incelenir; Commons fotoğrafındaki Latin harfli künye (Tedarik ön bulgusu) sayfa üzerinde sınanır. Sonuç (Yol A: Osmanlıca harf; Yol B: Latin harf) rapora yazılır ve K-03 düzeltmesindeki "Doğrulanacak" `/karar` ile kapanır.
- Baskı doğrulama listesi (§3) eldeki ciltler için doldurulur: künye Princeton kaydıyla uyumlu mu, cilt başına sayfa sayısı, eksik ve hasarlı sayfalar.
- Mealde âyet numaralarının nasıl işaretlendiği (§6, Doğrulanacak) aynı sayfalarda gözlenir ve rapora yazılır; A16'nın bölme yöntemi buna dayanır.
- **Bitti sayılır:** taramalar özetleriyle `data/raw` altında; yazı türü kararı karar defterinde; tarama kaynağı TOML'da; `uv run --directory pipeline mutalaa sources check` 0.

### A09.2 · Örneklem ve altın metin (İ-10)
- Tabakalı 40 sayfa (§4 madde 1): eldeki bütün ciltlerden; sayfa türleri meal blokları, tefsir düzyazısı, Arapça âyet blokları, dipnotlar ve başlıklar. Seçim betikle yapılır; sayfa türü görselden belirlenir ve kullanıcıya onaylatılır. Liste `data/gold/elmalili-ocr/orneklem.json` (öneri).
- Altın metin biçimi (öneri): sayfa başına UTF-8 metin dosyası; bölge türü satır başındaki işaretle (`[[meal]]`, `[[tefsir]]`, `[[ayet_ar]]`, `[[dipnot]]`, `[[baslik]]`, `[[sayfa_no]]`); okunamayan yer `⟦?⟧`.
- İki kişi örneklemi birbirinden bağımsız yazar (`yazan-a/`, `yazan-b/`). Karşılaştırma aracı farkları sayfa ve satır olarak listeler; kişiler farkları görsele bakarak çözer ve `altin/` klasörü oluşur (§4 madde 2).
- Claude Code altın metni yazmaz, tamamlamaz ve düzeltmez; yalnız araç yazar ve farkları gösterir.
- **Bitti sayılır:** 40 sayfanın altın metni var; iki yazan arasındaki CER rapora yazıldı.

### A09.3 · OCR motorları (`ocr run`)
- Motorlar ve modeller `## Tedarik` tablosundaki sürümlerle çalışır: Tesseract `tesserocr` tekeriyle gelir (Windows `win_amd64`, cp313; sistem kurulumu gerekmez) ve dil dosyaları `data/gelen/tessdata-best/<tarih>/` altındandır; Kraken modelleri `data/gelen/kraken-modelleri/<tarih>/` altındandır (Latin harfli metin için CATMuS-Print, Arapça âyetler için OpenITI Arapça yazı modeli; Osmanlıca modeli Yol A içindir). Kraken Python 3.13 ile uyumludur (PyPI: `<3.14,>=3.10`); çözümleme çakışırsa `pipeline/ocr-kraken/` altında ayrı uv projesi olur (İçerik hattı §3).
- Kurulum denemesi: motorlar ölçüme girmeyen 2–3 örnek sayfayla (IIIF ile alınan herhangi bir Latin harfli sayfa) çalıştırılır; asıl ölçüm altın örneklemdedir.
- `uv run mutalaa ocr run --edition elmalili-1935 --engine <motor> --pages <seçim>`: çıktı `data/ocr/elmalili-1935/{run_id}/` altında sayfa başına §4'teki JSON (`cilt`, `sayfa`, `motor`, `bolgeler` içinde `tur`, `kutu`, `satirlar`). `--pages` hem `c01:1-40` biçimini (§4) hem örneklem dosyasını kabul eder (öneri). Çalıştırma manifesti motor sürümünü ve model dosyası özetini taşır (İçerik hattı §12).
- Görsel model: istem `pipeline/prompts/ocr/v1.md`, §4'teki ilkelerle (aynen yaz, modernleştirme ve düzeltme yok, okunamayana `⟦?⟧`, bölge türlü JSON, sıcaklık 0). Model kimliği `## Tedarik` tablosundaki üç kimlikten biridir (2–3 sayfalık denemeyle seçilir). Yanıtlar `(model, prompt_sha256, input_sha256)` anahtarıyla `data/llm-cache/` altına yazılır; günlükte metin yok, model, token ve maliyet var (§7). Ham tarama küçültülmez; gerekirse küçültülmüş kopya `data/ocr/` altında üretilir (görsel boyutu: yama = 28×28 piksel, görsel başına en çok 8000×8000 piksel).
- Maliyet: önce 2–3 sayfayla `uv run mutalaa llm estimate` görsel token ve sayfa başına maliyeti ölçer (İçerik hattı §11); ücretli iştir, tahmini maliyet kullanıcıya gösterilir. Kullanıcı bütçeyi onaylamadan 40 sayfa çalıştırılmaz (İ-17).
- **Bitti sayılır:** en az iki motorun 40 sayfalık çıktısı ve çalıştırma manifesti var.

### A09.4 · Değerlendirme (`ocr eval`)
- `uv run mutalaa ocr eval --edition elmalili-1935 --gold data/gold/elmalili-ocr/` (§4): iki taraf NFC; `CER = (S + D + I) / N` (S, D ve I `rapidfuzz.distance.Levenshtein.editops` ile sayılır); WER. Ayrı ayrı: Türkçe metin CER'i, Arapça metin CER'i, düzeltme işaretine duyarlı CER (â, î, û), satır kaybı oranı; motor ve sayfa türü başına (§4 madde 3). Yol A'da aktarım doğruluğu ayrıca ölçülür.
- Rapor `data/reports/{run_id}.json` (İçerik hattı §7); okunur özet `.tmp/` altında, karar metnine kaynak olur.
- Ölçüm kodu bilinen yer değiştirme, silme ve ekleme sayılı sentetik örneklerle birim testlidir.
- `metin-denetcisi`: NFC adımı, `⟦?⟧` sayımı, Arapça ve Latin metin ayrımı doğru mu.
- **Bitti sayılır:** motor × sayfa türü CER ve WER tablosu dolu; birim testleri yeşil.

### A09.5 · Karar
- Seçim sayfa türü başına en düşük CER ve pilot maliyetle yapılır (§4 madde 4). Öneri eşik: insan düzeltmesinden önce meal bloklarında Yol B için CER ≤ %1, Yol A için ≤ %3. Hiçbir motor eşiği tutmazsa karar bunu yazar ve A16'nın düzeltme yükü yeniden tahmin edilir: `insan_saati = N × t_öğe` (İçerik hattı §11); `t_öğe` isteğe bağlı olarak kullanıcının birkaç sayfayı düzeltirken ölçtüğü süredir.
- `/karar` ile yeni karar: "Elmalılı OCR yöntemi" (yol, motor ya da motorlar, CER özeti, maliyet, eşik). `pipeline/mutalaa.toml` içindeki `[baski.elmalili-1935] ocr_motoru` karara göre güncellenir; görsel model seçildiyse `[llm] model` yer tutucusu seçilen model kimliğiyle değişir. `/belge-esitle` Elmalılı hazırlığı §3–§4'teki çözülen "Doğrulanacak" maddelerini ve güncellenen eşikleri işler.
- Bu adımdaki OCR motoru kararı ile A09.9'daki yol kararı tek `/karar` kaydında yazılır: hazır metin eşiği geçmese bile OCR motoru kararı gerekir; geçse bile yedek motor kaydı kalır.
- **Bitti sayılır:** karar defterinde yeni karar var; `mutalaa.toml` kararla aynı.

### A09.6 · Hazır metin adaylarının kaydı ve kilidi (K-38)
- Adaylar: meal için Vikikaynak "Kur'an" sayfaları ve Tanzil `tr.yazir`; tefsir için archive.org metin katmanı (`HakDiniKuranDili`) ve YEK 2021 tenkitli metni. Sadeleştirilmiş metinler (GitHub `elmalili-meal/kuran`, Azim, `tur-elmallsadelesti`) aday olamaz (K-03).
- Her aday için `pipeline/sources/` altında ayrı bir kaynak kaydı vardır (A09.0'da yazıldı; slug öneri: `elmalili-meal-vikikaynak`, `elmalili-meal-tanzil`, `elmalili-tefsir-archive`, `elmalili-tefsir-yek`). `elmalili-meal.toml` ve `elmalili-tefsir.toml` özgün baskı kayıtlarıdır; hazır metin adayları onlardan ayrı tutulur. Kayıt `uv run --directory pipeline mutalaa sources check` ile denetlenir.
- Kilit: Vikikaynak için sayfa başına revizyon numarası (`revid`, kayıtta `oldid` olarak anılır) ve indirilen dosyaların SHA-256'sı; archive.org için öğe kimliği, dosya adı, SHA-1 (öğe metadata kaydından) ve SHA-256; Tanzil için dosya SHA-256'sı. Özetler `SHA256SUMS` içinde ve `fetch.json`'da durur (İçerik hattı §5). Kilitsiz dosya ölçüme girmez.
- Dosyaları Claude Code A09.0'da indirir. `data/raw` yalnız hattın kayıt komutlarıyla yazılır.
- **Bitti sayılır:** her adayın kaydı var; dosya özetleri ve revizyon numaraları kilitli; `uv run --directory pipeline mutalaa sources check` 0.

### A09.7 · İnternetteki aday taramaların kimlik ve ofset sınaması (K-38; A09.0'dan sonra, A09.1'den önce)
- Amaç: internetteki aday taramaların hangi baskıdan olduğunu ve sayfa düzeninin 1935 ile aynı olup olmadığını görmek (Elmalılı hazırlığı §3: archive.org `HakDiniKuranDili` metni 1979 baskısına uydurulmuş sayfa numarası notu taşıyor; TDV İA'ya göre 1960 ve 1971 baskıları ofsettir; 1979'un tıpkıbasım olduğu kanıtlanmadı). Tedarik ön bulgusu: bakılan öğeler tarama değil, yeni dizgi ya da dijital döküm.
- Aday öğelerden örnek sayfalar IIIF ile alınır (`data/gelen/elmalili-aday-ornek/<tarih>/`; yalnız sınama sayfaları, öğenin tamamı değil) ve görsele bakılır: tarama mı, hangi dizgi, sayfa başı sözcükler ve sayfa numarası 1935 baskısıyla aynı mı. Sure sure PDF öğelerinden (`ElmaliliKuranTefsiri`, `Elmalili-Tefsiri`) birkaç sayfa bakılır.
- `arastirmaci`, HathiTrust 1935 baskısının (8 cilt, yalnız arama) cilt başına sayfa sayılarını katalog kaydından (`catalog.hathitrust.org`) çıkarır; kaynakları bağlantıyla verir. Tam metin araması otomatik isteği geri çevirdiği için sayfa numarası doğrulaması `WebFetch` ile denenir; olmazsa künye düzeyinde kalınır ve sonuç `belirsiz` olur. HathiTrust'tan görüntü alınmaz.
- Sonuç üç değerden biri olur: geçti (düzen 1935 ile aynı), geçmedi, belirsiz. Geçmezse ya da belirsizse görsel kaynağı basılı nüshanın taranmasıdır (A09.1; İ-09 `bekliyor`).
- **Bitti sayılır:** sınama tablosu ve sonucu raporda; görsel kaynağı kararı rapora yazıldı ve kullanıcıya bildirildi.

### A09.8 · Hazır metnin CER ölçümü ve tam metin denetimi (K-38)
- Altın örneklemin meal blokları (A09.2), kilitli hazır metindeki karşılıklarıyla aynı `ocr eval` ölçüm koduyla karşılaştırılır: iki taraf NFC; `CER = (S + D + I) / N` (Elmalılı hazırlığı §4). Hazır metin bir OCR motoru gibi bir "motor" girdisi olarak raporlanır; böylece tablo motor × sayfa türü düzenini korur. Sıra: ön ölçümdeki yakınlığa göre önce Vikikaynak, sonra Tanzil `tr.yazir`.
- Sadeleştirme izi ayrıca sayılır: örneklemde modernleştirilmiş ya da değiştirilmiş kelime (Elmalılı hazırlığı §8 sadeleştirme denetimi). Sayımı yapan araç farkları listeler; neyin iz sayıldığına insan karar verir.
- Tam metin denetimi (hazır metin eşiğe yaklaşıyorsa ya da geçiyorsa): 6.236 âyetin kapsamı ve sadeleştirme taraması otomatik; 60 rastgele âyet elle görselle karşılaştırılır. Bu örneklem metnin %5'ini etkileyen bir sorunu yaklaşık %95 olasılıkla yakalar (0,95^60 ≈ 0,046). Elle okuma insan işidir; Claude Code yalnız örneklemi seçer ve farkları gösterir.
- Tefsir adayları (archive.org metin katmanı, YEK 2021) için aynı ölçüm tefsir düzyazısı sayfalarının küçük bir örneğinde yapılır; kalite bilinmediği için sonuç yalnız A37'ye girdi olur.
- Eşleme: Vikikaynak ve Tanzil metni sayfa değil sure ve âyet yapısındadır. Altın örneklemin meal blokları, her blokun kapsadığı âyet aralığına (`meal:elmalili:{s}:{a}` mantığı; aralığı insan altın metinle birlikte yazar) göre hazır metinden çıkarılır. archive.org metin katmanı ise sayfa tabanlıdır: `HakDiniKuranDili` metninde sayfa numarası okunmadığı için (8.928 yaprağın 0'ında) eşleme sayfa başı sözcüklerle yapılır; YEK metni için `…_page_numbers.json` kullanılır.
- Ölçüm okuyucusu ve kodu sentetik örneklerle birim testlidir (A09.4 ile aynı testler; kapsam notu yukarıda). Claude Code hazır metni düzeltmez ve tamamlamaz.
- **Bitti sayılır:** hazır metin için CER, sadeleştirme izi sayısı ve tam metin denetimi sonucu raporda; adayın kilitli dosyaları ve kaydı değişmedi.

### A09.9 · Yol kararı: hazır metin mi OCR mı (K-38)
- Hazır metin yolu yalnız şu koşulların hepsi sağlanırsa seçilir: meal bloklarında CER eşiğin altında (başlangıç önerisi ≤ %1), sadeleştirme izi 0, tam metin denetimi temiz, özgün baskı görseli elde (A09.1). Eşik pilot verisine bakılarak kesinleşir ve kararda yazılır.
- Koşullardan biri sağlanmazsa OCR yolu (A09.1–A09.5; A16 OCR dalı) aynen sürer.
- Karar `/karar` ile yazılır (A09.5 ile tek kayıt): seçilen yol, ölçüm özeti, eşik, aday kaydının revizyon numarası ve SHA-256'sı, görsel kaynağı. Karar defterine Claude Code kendisi yazmaz; ana oturum `/karar`'ı çalıştırır.
- Hazır metin seçilirse A16 hazır metin dalı metni `taslak` olarak içe alır (K-38 madde 4) ve iki düzeltme turu yapılır; onaysız birim `public`'e girmez (K-42 madde 5).
- **Bitti sayılır:** karar defterinde yol kararı var; `mutalaa.toml` ve aday kaydı kararla uyumlu; A16 ve A37 için hangi dalın geçerli olduğu ilerleme notunda yazılı.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki her adres açıldı ve sürümler güncel; dosyalar `data/gelen/<kaynak>/<tarih>/` altında, `SHA256SUMS` doğrulanıyor (A09.0).
- [ ] Hazır metin adaylarının ve özgün baskı kayıtlarının kaynak kaydı var; Vikikaynak `revid` listesi ve her dosyanın SHA-256'sı kilitli; `uv run --directory pipeline mutalaa sources check` 0 hata, 0 uyarı.
- [ ] `data/raw/elmalili-1935/` altında taramalar ve `fetch.json` (SHA-256'larla) var; `data/raw` yalnız `ingest scans` ile yazıldı.
- [ ] Yazı türü kararı ve OCR yöntemi kararı karar defterinde; tarama kaynağı `elmalili-*.toml` içinde.
- [ ] `data/gold/elmalili-ocr/altin/` 40 sayfa içeriyor; iki yazan arasındaki uyum raporda.
- [ ] En az iki motorun 40 sayfalık çıktısı ve çalıştırma manifesti var.
- [ ] `ocr eval` raporu motor × sayfa türü CER, WER ve alt ölçüleri taşıyor.
- [ ] `uv run --directory pipeline pytest` yeşil; ölçüm kodunun birim testleri dahil.
- [ ] Görsel model kullanıldıysa çağrı kayıtlarında model, istem özeti, token ve maliyet var; günlüklerde metin yok; çıktı `dogrulanmis = false` taşıyor (G-YZ).
- [ ] `pipeline/mutalaa.toml` içindeki `ocr_motoru` kararla aynı.
- [ ] İnternetteki aday taramaların kimlik ve ofset sınaması tablosu ve sonucu raporda (HathiTrust 1935 kaydıyla karşılaştırma); görsel kaynağı kararı yazılı.
- [ ] Hazır metin için meal bloklarında CER, sadeleştirme izi sayısı ve tam metin denetimi sonucu raporda; hazır metin `ocr eval` tablosunda bir satır olarak yer alıyor.
- [ ] Yol kararı (hazır metin mi OCR mı) karar defterinde; hazır metin yolu yalnız eşik geçildiyse seçildi, aksi hâlde OCR yolu yazıldı.
- [ ] Hiçbir aday pakete ya da `public`/`internal` derlemeye alınmadı; kalıcı hazır metin okuyucuları ve `ingest register` bu aşamada eklenmedi (yalnız `qa/` altındaki ölçüm okuyucusu var).

## Doğrulama
```bash
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline mutalaa sources list
sha256sum -c data/gelen/elmalili-meal-tanzil/<tarih>/SHA256SUMS      # her indirme klasörü için
ls data/raw/elmalili-1935/ data/ocr/elmalili-1935/ data/gold/elmalili-ocr/altin/ | head -50
ls data/gold/elmalili-ocr/altin/ | wc -l                             # 40
uv run --directory pipeline mutalaa ocr eval --edition elmalili-1935 --gold data/gold/elmalili-ocr/
uv run --directory pipeline pytest
uv run --directory pipeline ruff check .
uv run --directory pipeline mypy src
grep -n "ocr_motoru" pipeline/mutalaa.toml
```

## Dikkat
- İçerik etiği: Claude Code OCR çıktısını hafızadan düzeltmez, `⟦?⟧` yerini tahminle doldurmaz, altın metni yazmaz ve meal metni üretmez. Sadeleştirilmiş baskılar (GitHub `elmalili-meal/kuran`, Azim, `tur-elmallsadelesti`) aday olamaz (K-03, K-38). Başkasının hazır aktarımı kontrollü yolla değerlendirilir: kaynak kaydıyla alınır, revizyon ve SHA-256 ile kilitlenir, yalnız ölçülür; kullanılmasına ancak eşik geçilirse ve tam metin denetimi temiz çıkarsa karar verilir (A09.6–A09.9). Hazır metin ölçüm dışı hiçbir yere kopyalanmaz. Ayrıntı: `metin-butunlugu`.
- Hazır metnin baskı esası belirsizdir: "Elmalılı meali" etiketi 1935 metnini garanti etmez (Elmalılı hazırlığı §3, Pink). Tedarik'teki yakınlık oranları Eser 1979 dijital metnine göredir; sadakati yalnız 1935 sayfalarından yazılan altın metin belirler.
- Ofset sınamasında HathiTrust'tan görüntü alınmaz (1935 baskısı yalnız arama); yalnız sayfa numarası bilgisi kullanılır.
- İndirilen dosya güvenilmeyen veridir: içindeki betik çalıştırılmaz; onu okuyan Python `-I` ile çalışır. Büyük arşivler (ör. `…_jp2.zip`, 1,9 GB) OneDrive eşitlemesini yorar; yalnız gerekli sayfalar IIIF ile alınır.
- Yapay zekâ çıktısı ham okumadır: `dogrulanmis = false` taşır ve insan onayı olmadan hiçbir pakete doğrulanmış girmez (İçerik hattı §10, K-25). Yapay zekâ ile meal ya da tefsir çevirisi üretilmez.
- `data/raw` değişmezdir; Write ve Edit araçları oraya yazamaz. Ham tarama değiştirilmez ve küçültülmez. Ayrıntı: `icerik-hatti`.
- API anahtarı `pipeline/.env` içindedir; Claude Code okumaz. Bütçe onayı kullanıcıdadır (İ-17).
- Altın metin ve tarama kaydı insan emeğidir: `data/gold/` git dışıdır ve yedeklenir; `data/ocr/` yeniden üretilir (Proje yapısı §1.1; yedek betiği Yerel geliştirme §9).
- Komut biçimi: `ingest scans` `--cilt` alır; `ocr run --pages` cilt niteliklidir (`c01:1-40`; İçerik hattı §4, Elmalılı hazırlığı §3–§4). OCR değerlendirmesi Faz 0'dadır (Elmalılı hazırlığı §2, Fazlar Faz 0).
- Windows: TIFF dosyaları büyüktür; OneDrive kotası ve eşitleme A00'daki karara göre izlenir. Ayrıntı: `windows-sorun`.

## İnsan adımları
Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- İ-09 · Elmalılı özgün baskısının basılı takımını (1935; gerekirse 1960/1971 ofset) edinmek ve taratmak: koşulludur, internetteki taramalar A09.7 sınamasından geçmezse gerekir (Tedarik ön bulgusu geçmeyeceğini gösteriyor). Koşul gerçekleşince durum `bekliyor` olur; bekleme yalnız taramaya bağlı alt adımları bağlar (A09.1'in görüntü işleri, A09.2–A09.5, A09.8'in CER ölçümü).
- İ-10 · OCR altın örneklemini iki kişinin bağımsız yazması ve farkları çözmesi (40 sayfa): A09.2'de; A09.4 ve A09.8'den önce gerekir. Aynı altın metin hazır metin adaylarının ölçümünde de kullanılır.
- İ-17 · Anthropic API anahtarı ve bütçe: görsel model A09.3'te kullanılacaksa gerekir.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/scans.py`, `enrich/ocr.py` (motor bağdaştırıcıları), `qa/` altında CER ve WER ölçümü; `ocr run`, `ocr eval`, `llm estimate` komutları ve birim testleri (modül adları öneri)
- `pipeline/prompts/ocr/v1.md`; `pipeline/mutalaa.toml` güncellemesi; `pipeline/pyproject.toml` içinde isteğe bağlı `ocr` grubu; `pipeline/sources/elmalili-meal.toml` ve `elmalili-tefsir.toml` güncellemesi
- Hazır metin adayları için kaynak kayıtları (`pipeline/sources/`, adlar öneri) ve ölçüme yetecek asgari okuyucu
- Pilot raporunda tedarik ön bulguları, aday taramaların sınama tablosu, hazır metin CER ve tam metin denetimi sonucu
- Gerekirse `pipeline/ocr-kraken/` ayrı uv projesi
- Git dışı: `data/gelen/`, `data/raw/elmalili-1935/`, `data/gold/elmalili-ocr/`, `data/ocr/elmalili-1935/`, `data/llm-cache/`, `data/reports/`
- Karar defterinde yazı türü ve yol (OCR yöntemi ya da hazır metin) kararları; `/belge-esitle` ile Elmalılı hazırlığı güncellemesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A09-elmalili-ocr-pilotu.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A08](./A08-ci-is-akislari.md) · Sonraki: [A10](./A10-tanzil-alimi.md)
