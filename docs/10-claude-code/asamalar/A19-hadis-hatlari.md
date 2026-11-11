# A19 · Hadis hatları

> **Sürüm:** 1.2 · **Tarih:** 11 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-04](../../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-11 · İ-14
> **Ajanlar:** `hat-gelistirici` · `arastirmaci` · `metin-denetcisi` · `test-yazari` · `sunucu-gelistirici` (şema eki gerekirse) · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · `paket-yayini` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan işleri ayrıca
> **Başlat:** `/asama A19`

## Amaç
K-04 gereği Tecrîd-i Sarîh'in Arapça metni ve Türkçesi (Babanzâde Ahmed Naim ve Kâmil Miras ciltleri; tam takım) ile Kütüb-i Sitte'nin Arapça metni için hat kurulur: tedarik ve indirme (A19.0), kaynak kayıtları ve cilt eşlemesi, hazır dijital metin ile tarama ve OCR, hadis birimleri (`h:{koleksiyon}:{no}`, `ht:{ceviri}:tecrid:{no}`), numara eşleme ve konum tabloları, Tecrîd → Buhârî eşlemesi ve hadis atıf ayrıştırıcısı. Kaynakları internetten ve GitHub'dan Claude Code indirir. İnsan işi yalnız cilt künyelerinin ve mütercim bilgisinin doğrulanması (İ-14) ile Türkçe aktarımın düzeltme turlarıdır (İ-11).

## Okunacak belgeler
- [Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md): tamamı
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §13 hadis atıfları; motor için §3–§6
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §2 (`tecrid-*`, `hadis-*`), §3.4, §4, §5
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2–§5 (`h`, `ht`, slug kuralları), §13 ÇŞ-3
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source`, §4 `unit`, §9.1 `page_map`, §11 `hadith_number_map` ve `hadith_location`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1 hadis paketleri, §7 derleme türüne göre süzme
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §4 OCR değerlendirme yöntemi; §5 aktarım kılavuzu yalnız Osmanlıca harfli bir cilt kullanılırsa
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §8 yeni kaynak ekleme, §10 yapay zekâ politikası

## Kapsam
**Yapılır**
- Tedarik ve indirme (A19.0): Tecrîd'in harekeli Arapça metni, özgün baskı görüntüleri, 13 ciltlik Türkçe takım; Kütüb-i Sitte Arapçası için iki JSON veri seti.
- Kaynak kayıtları ve cilt eşlemesi: `tecrid-ar`, `tecrid-naim`, `tecrid-miras`, `hadis-fawaz-ar` güncellenir; `hadis-ahmedbaset` açılır.
- Numaralandırma kararı; `hadith_number_map`, `hadith_location`.
- Tecrîd metninin birimlere bölünmesi (cilt 1–12), OCR değerlendirmesi, Naim ve Miras aktarımı için inceleme kuyruğu.
- Kütüb-i Sitte Arapçası: altı kitap (Buhârî, Müslim, Ebû Dâvûd, Tirmizî, Nesâî, İbn Mâce).
- Tecrîd → Buhârî eşlemesi, hadis atıf ayrıştırıcısı; `hadis-tecrid` ve `hadis-kutub-i-sitte` paketlerinin `dev` yayını.

**Yapılmaz**
- Sıhhat derecesi etiketleri (sonra; yapay zekâ derece atamaz). Hadis okuyucusu (A31).
- Yapay zekâ ile hadis çevirisi. Kütüb-i Sitte'nin Türkçesi (K-04 yalnız Tecrîd'in Türkçesini kapsar).
- Atıf koşuları: ayrıştırıcıyı bu aşama kurar; Elmalılı tefsiri üzerindeki koşu A37'de, Risale metni üzerindeki koşu Risale aşamalarında yapılır.
- Cilt 13 (Kılavuz) ve ciltlerdeki şerh, dipnot ve fihrist metni birim olmaz.

## Tedarik
Araştırma tarihi 2 Kasım 2026; A19.0'da yenilenir. Sayımlar yalnız sayım ve yapı ölçümüdür (hadis metni yazdırılmadı). Kütüb-i Sitte için iki veri seti birlikte alınır: AhmedBaset'te boş Arapça kayıt yoktur (0/34.178) ve kitap adları Arapçadır; fawazahmed0'da Sunnah.com numarası (`hadithnumber`) ve harekesiz sürüm vardır, ama 379 kaydın Arapça metni boştur. Normalleştirilmiş metinleri %99,7–99,9 örtüştüğü için numara eşlemesi metinle kurulur.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Tecrîd-i Sarîh Arapça metni, harekeli hazır dijital metin (`tecrid-ar`, birincil) | Shamela dışa aktarımı "التجريد الصريح لأحاديث الجامع الصحيح" (Zebîdî; tahkik Hasan Abdülmünim Şelebî ve Kisrâ Sâlih el-Alî; Müessesetü'r-Risâle, Dımaşk, 1. baskı 1430/2009, 1 cilt). archive.org `0001Htm48_201901` öğesinde `1145Htm.zip` (içinde tek `.htm`, windows-1256, 1.315.950 bayt; öğe 6.538 kitaplık Shamela HTM dökümü, 2.918.024.813 bayt, eklenme 10 Ocak 2019) | `https://archive.org/download/0001Htm48_201901/1145Htm.zip` doğrudan dosya (200; 328.078 bayt; SHA-1 `4ebe9bf7…92e9` ve MD5 `8485e001…b087` metadata kaydıyla aynı; SHA-256 `1240e88b…a22e`) | Arapça harf 509.250; hareke kod noktası 343.607 (harf başına 0,675); satır başı numara kalıbı 2.263, farklı numara 2.253 (en küçük 1, en büyük 2.254); kod çözümünden sonra NFC. Kitap kartı: numaralar basılı baskının numaralarıdır, her hadisten sonra Sahîh-i Buhârî numarası verilir, bâb başlığı yoktur (yalnız kitap adları). Basılı Tecrîd numarasıyla örtüşme A19.2'de ölçülür | OpenITI sürümü (sonraki satır; harekesiz); özgün baskı görüntüleri ve OCR |
| Tecrîd Arapça, yapı ve karşılaştırma metni (`tecrid-ar` ikinci kaynak) | OpenITI `0893IbnAhmadZaynDinSharji.TajridSarih.Shamela0096283-ara1` (mARkdown; `OpenITI/0900AH` deposu): `master` HEAD `271ff65bd8364d3a46b5806ca529617d1ffc3393` (temizlenmiş sürüm, 1.418.201 bayt) ve `pre-clean` etiketi (commit `9a854cb097581344c51ebccf117a518595065121`; ön yazı ve dipnotlu sürüm, 1.418.639 bayt) | `https://raw.githubusercontent.com/OpenITI/0900AH/<sha>/data/0893IbnAhmadZaynDinSharji/0893IbnAhmadZaynDinSharji.TajridSarih/0893IbnAhmadZaynDinSharji.TajridSarih.Shamela0096283-ara1` doğrudan dosya (iki sürümde 200) ve `.yml` yan dosyası | `pre-clean`: 91 kitap başlığı, numaralı hadis başlığı 2.253 (1…2.254, eksik yalnız 1202), 88 zevâid notu, 2.554 sayfa işareti; `master`: 2.242 numaralı başlık (12 eksik). Harekesiz (hareke kod noktası 0), NFC; numara aralığı Shamela dosyasıyla aynı | Önceki satır (Shamela HTM) |
| Tecrîd Arapça, özgün baskı görüntüleri (sayfa eşlemesi, OCR girdisi, doğrulama) | archive.org `AAlexandrina-103522` (Kahire, 1322 [1904–1905]; eklenme 14 Ocak 2025; iki PDF 58.599.822 ve 12.315.962 bayt, JP2 zip 93.497.599 bayt, `_djvu.txt` 1.085.830 bayt SHA-1 `555ff006…`, `_page_numbers.json` 51.808 bayt, `_scandata.xml` 100.151 bayt; öğe 204.625.045 bayt) | `https://archive.org/download/AAlexandrina-103522/<dosya>` doğrudan dosya (`_djvu.txt`, `_page_numbers.json`, `_scandata.xml` için 200); MD5, SHA-1 ve boyut `https://archive.org/metadata/AAlexandrina-103522` kaydından | `_page_numbers.json` 305 kayıt. Hazır OCR metni zayıf (Tesseract 5.3): 621.455 karakter, Arapça harf 448.520, hareke 988 (harf başına 0,002), yalnız Arapça belirteç oranı 0,867; bu yüzden metin değil görüntü kaynağıdır | `at-tajrid-as-sarih-imam-az-zoubeydi_202408` (archive.org; 13 `_djvu.txt` ve 13 `_page_numbers.json`, öğe 4.921.289.098 bayt; künyesi A19.0'da okunur) |
| Tecrîd-i Sarîh Türkçesi: Ahmed Naim (cilt 1–3) ve Kâmil Miras (cilt 4–12) çevirileri; tam takım (`tecrid-naim`, `tecrid-miras`) | Diyanet İşleri Başkanlığı Yayınları, 13 ciltlik takım ("Sahîh-i Buhârî Muhtasarı Tecrîd-i Sarîh Tercemesi ve Şerhi"; Başbakanlık Basımevi, Ankara 1976–1980; 4.–6. baskılar; Latin harfli). Metin katmanı: archive.org tek ciltlik öğeler `BuhariTecridiSarih1…5` ve `BuxariTecridiSarih6…13` (ABBYY FineReader 8.0–11.0, 2013; 13 `_djvu.txt`, toplam 12.552.425 bayt). Görüntü: `buharitecridisarih` öğesinde 13 Text PDF (toplam 622.842.078 bayt; öğe 5.196.333.350 bayt, 2021) | `https://archive.org/download/<öğe>/<dosya>` doğrudan dosya: `BuhariTecridiSarih1/BuhariTecridiSarih1_djvu.txt`, `BuhariTecridiSarih2…5/buhari  tecridi sarih N_djvu.txt`, `BuxariTecridiSarih6…13/buxari  tecridi sarih N_djvu.txt` (çift boşluklu ad `%20` ile; 13 dosyada 200), `buharitecridisarih/buhari  tecridi sarih N.pdf` (cilt 1 ve 13 için 200); boyut ve SHA-1 `metadata` kaydından | 13/13 cilt metin katmanı (507.353–1.604.062 bayt). Cilt 1 için 768 yaprak (`_page_numbers.json`, 766 numaralı); öteki ciltlerin sayfa sayısı PDF'ten A19.0'da ölçülür. Künye (OCR satırlarından; İ-14 doğrular): cilt 1–3 Ahmed Naim, cilt 4–12 Kâmil Miras, cilt 13 "Kılavuz" (Mücteba Uğur ve M. Cemal Sofuoğlu). Metin katmanında Arapça harf yok (Arapça bloklar görselden okunur) ve Türkçe harf bozuklukları var; hadis numaraları güvenilir tek satır değil. Bu yüzden katman ilk geçiştir, CER A19.3'te ölçülür | Aynı baskının başka kopyaları: `Sahih-iBuhari-TecridiSarih` (ABBYY 11.0, aynı 13 PDF), `BuhariTecridiSarih11` (cilt 11 ikinci kopya). 8 ciltlik sonraki baskı kopyaları (`buhari_tecrid-i_sarih`, `sahihi-buhari-muhtasari-tecridi-sarih-tercumesiveserhi-03`) künyesi okunup sadeleştirme taraması yapılmadan kullanılmaz |
| Kütüb-i Sitte Arapça metni ve Arapça kitap adları (`hadis-ahmedbaset`; metin kaynağı) | AhmedBaset/hadith-json, `v1.2.0` etiketi (commit `ca32fd72aa16eeeb9a819c80bb65c9e78766532d`; `main` HEAD `70b83d6d21995bb32f8d7271cd75501be5a922a7` etiketin ilerisindedir), `db/by_book/the_9_books/<kitap>.json`; JSON; alanlar `arabic`, `english`, `id`, `idInBook`, `bookId`, `chapterId` | `https://raw.githubusercontent.com/AhmedBaset/hadith-json/ca32fd72aa16eeeb9a819c80bb65c9e78766532d/db/by_book/the_9_books/<kitap>.json` (6 dosyada 200): `bukhari` 12.750.789, `muslim` 11.453.533, `abudawud` 7.876.724, `tirmidhi` 7.657.978, `nasai` 7.886.749, `ibnmajah` 5.723.671 bayt (`main`'de boyutlar farklıdır, ör. Tirmizî 7.660.980) | Hadis kaydı ve kitap sayısı: Buhârî 7.277 ve 97; Müslim 7.459 ve 57; Ebû Dâvûd 5.276 ve 43; Tirmizî 4.053 ve 49; Nesâî 5.768 ve 52; İbn Mâce 4.345 ve 38. Toplam 34.178 kayıt; boş Arapça kayıt 0; kitap adları Arapça ve İngilizce dolu; `idInBook` 1…N sürekli, tekrar yok; harekeli; kayıtların çoğu NFC değil (ör. Buhârî 7.008/7.277) | fawazahmed0 (sonraki satır); OpenITI Shamela sürümleri |
| Kütüb-i Sitte numara sistemi (`sunnah-com` numaraları) ve harekesiz sürüm (`hadis-fawaz-ar`) | fawazahmed0/hadith-api, `1` dalı, commit `df57907be35291c91ad6a6691180e22ca9920784` (etiket yok); `editions/ara-<kitap>.json` (harekeli) ve `editions/ara-<kitap>1.json` (harekesiz); JSON; alanlar `hadithnumber`, `arabicnumber`, `text`, `reference` | `https://raw.githubusercontent.com/fawazahmed0/hadith-api/df57907be35291c91ad6a6691180e22ca9920784/editions/ara-<kitap>.json` (6 dosyada 200): `ara-bukhari` 9.770.083, `ara-muslim` 8.685.140, `ara-abudawud` 7.345.422, `ara-tirmidhi` 7.120.806, `ara-nasai` 7.152.291, `ara-ibnmajah` 5.583.102 bayt; `ara-<kitap>1` dosyaları 3.963.089–6.162.554 bayt; `editions.json` aynı depoda | Hadis kaydı, en büyük `hadithnumber`, boş Arapça kayıt: Buhârî 7.589, 7.563, 9; Müslim 7.563, 7.563, 203; Ebû Dâvûd 5.274, 5.274, 2; Tirmizî 3.998, 3.956, 74; Nesâî 5.765, 5.758, 86; İbn Mâce 4.343, 4.341, 5. Toplam 34.532 kayıt, 379 boş. Kesirli alt numara 26, 0, 0, 42, 7, 2. Bölüm adları yalnız Latin harfli. `ara-<kitap>1` harekesiz (hareke 0), kayıt ve boş sayıları aynı. AhmedBaset ile normalleştirilmiş metin örtüşmesi benzersiz metinlerin %99,7–99,9'u; AhmedBaset'te olup burada bulunmayan benzersiz metin Müslim 181, Tirmizî 144, Nesâî 99. Aynı numarada aynı metin oranı düşük (Buhârî 272/7.268, Müslim 0/7.269, Ebû Dâvûd 905/5.272, Tirmizî 744/3.889, Nesâî 156/5.672, İbn Mâce 0/4.336): iki numara sistemi farklıdır | AhmedBaset (önceki satır); OpenITI Shamela sürümleri |
| Kütüb-i Sitte Arapça, baskı künyeli yedek (harekesiz) | OpenITI Shamela sürümleri: `0275AH` commit `44e1c36738a2bf5c14dafa232a6ae1891e6171cd` (`0256Bukhari.Sahih.Shamela0001681-ara1` 6.039.255 bayt, `0261Muslim.Sahih.Shamela0001727-ara1.mARkdown` 4.933.663, `0275AbuDawudSijistani.Sunan.Shamela0001726-ara1` 3.398.133, `0273IbnMaja.Sunan.Shamela0001198-ara1` 2.535.073); `0300AH` commit `01a1544130e0236850ef2698923ad01575c5bd7c` (`0279Tirmidhi.Sunan.Shamela0001435-ara1` 3.702.921); `0325AH` commit `089e665b4958e0f145a46941987fb81cf3dda1b8` (`0303Nasai.SunanSughra.Shamela0000829-ara1` 3.460.338); mARkdown | `https://raw.githubusercontent.com/OpenITI/<depo>/<sha>/data/<yazar>/<eser>/<dosya>` doğrudan dosya (altısı da 200) | Sayfa işareti 12.531, 8.752, 7.207, 5.911, 3.004, 2.578 (Buhârî, Müslim, Ebû Dâvûd, İbn Mâce, Tirmizî, Nesâî); hareke kod noktası 0, NFC. Hadis sayısı ve numaralama A19.0'da yalnız yedek kullanılırsa ölçülür | Yok |
| Arapça ve Türkçe sayfa OCR'ı | A09'un seçtiği motor (`pipeline/mutalaa.toml` içinde `[baski.<ad>] ocr_motoru`); adaylar A09 Tedarik'indedir (Tesseract 5 `tur` ve `ara`, Kraken). Arapça için temel harf ve hareke CER'i ayrı ölçülür | A09 çıktısı; ücretli motor ya da görsel model kullanılırsa tam koşudan önce tahmini maliyet kullanıcıya gösterilir | A19.3 örneklem CER raporu | A09'un ikinci motoru |
| PDF ve JP2'den sayfa görseli | `pypdfium2` 5.14.0 ve `pillow` 13.0.0 (A16 Tedarik'iyle aynı sürümler) | `uv add --directory pipeline pypdfium2 pillow` (A16.0'da eklenmediyse); sürümler `uv.lock` içinde | PyPI kayıtları A16 Tedarik'inde 1 Kasım 2026'da okundu | `pikepdf` 10.17.0 |
| Normalizasyon ve hizalama (Tecrîd → Buhârî eşlemesi) | A05 Arapça normalleştirici ve A18 iktibas motoru (3–4 gram dizini, Smith-Waterman hizalaması) | Depo içi; yeni kitaplık yok | A05 ve A18 kabul ölçütleri | Yok |

Kendimiz yapacağımız işler: hadis numarası işaretlerini bulma ve Arapça ile Türkçe bloğu eşleme; `h:` ve `ht:` birimleri, çapa üretimi, kendi aktarımımızda ilk kayıtta NFC; zevâid hadislerinin ayıklanması; `hadith_location`, `hadith_number_map` ve `page_map` doldurma; iki JSON veri setinin metinle eşlenmesi; Tecrîd → Buhârî eşlemesi; hadis atıf ayrıştırıcısı ve kitap adı eşleme tablosu; G-CAP, G-BUT, G-KAY kapıları.

Seçilmeyenler (erişim ve kalite): Sunnah.com API (API anahtarı ister); fawazahmed0 ve AhmedBaset'in Türkçe ve İngilizce sürümleri (çevirmeni belgelenmemiş; Türkçe hadis metni K-04 gereği Naim ve Miras çevirileridir); künyesi okunmamış 8 ciltlik sonraki baskı kopyaları.

## Adımlar
### A19.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: GitHub depolarında commit SHA'sı ve etiket `git ls-remote https://github.com/<sahip>/<depo>.git HEAD` ve `'refs/tags/*'` ile (OpenITI için `refs/tags/pre-clean`; AhmedBaset için `v1.2.0` etiketinin hâlâ son etiket olduğu ve `main`'deki sonraki değişikliklerin Arapça metni etkilemediği; boyutlar farklıdır, ör. Tirmizî 7.657.978 ve 7.660.980 bayt), dosya boyutu `curl -sIL https://raw.githubusercontent.com/<sahip>/<depo>/<sha>/<yol>` ile; archive.org öğelerinde `https://archive.org/metadata/<kimlik>` kaydıyla boyut, MD5 ve SHA-1. Açılmayan adresin yerine tablodaki yedek aday kullanılır.
- Dosyalar yeni boş klasörlere iner (formları Claude Code doldurur); toplu indirmede istek hızı sınırlanır. Yerel dosya adları ASCII olur (archive.org'daki çift boşluklu ve Arapça adlar `1145Htm.zip`, `c01_djvu.txt`, `c01.pdf` gibi adlarla kaydedilir; özgün ad ve adres bu adıma yazılır):
  - `data/gelen/tecrid-ar/<YYYY-AA-GG>/`: `1145Htm.zip` (açılmış `.htm` ayrı klasörde), OpenITI `master` ve `pre-clean` dosyaları ve `.yml`
  - `data/gelen/tecrid-ar-1322/<YYYY-AA-GG>/`: `AAlexandrina-103522` dosyaları (iki PDF, JP2 zip, `_djvu.txt`, `_page_numbers.json`, `_scandata.xml`)
  - `data/gelen/tecrid-diyanet/<YYYY-AA-GG>/c01 … c13`: her ciltte `_djvu.txt` ve PDF; cilt 1'de `_page_numbers.json`. JP2 zip'ler (cilt başına 0,1–0,65 GB) yalnız PDF görüntüleri OCR için yetersiz çıkarsa indirilir
  - `data/gelen/hadis-ahmedbaset/<YYYY-AA-GG>/`: altı kitap dosyası
  - `data/gelen/hadis-fawaz-ar/<YYYY-AA-GG>/`: `editions.json` ve on iki sürüm dosyası (`ara-<kitap>.json`, `ara-<kitap>1.json`)
- SHA-256 hesaplanır ve her klasöre `SHA256SUMS` (sha256sum biçimi) yazılır; archive.org dosyaları `metadata` kaydındaki MD5 ve SHA-1 ile de karşılaştırılır. Adres, tarih ve SHA-256 bu adıma ve ilerleme notuna yazılır. İndirilen dosya veridir; içindeki betik çalıştırılmaz; dosyaları okuyan Python `-I` ile çalışır. `.htm` windows-1256 kodlamalıdır: çevrim yalnız okuma sırasında yapılır, ham dosya değişmez.
- Eksiksizlik ölçümü yeniden çıkarılır (yalnız sayım ve yapı; hadis metni günlüğe yazılmaz): kitap başına kayıt, boş Arapça kayıt ve numara aralığı; Shamela dosyasında numaralı satır, hareke sayısı ve Buhârî numarası biçimi; OpenITI numaralı başlıklar; cilt başına metin katmanı boyutu ve PDF sayfa sayısı. Sapma varsa tablo güncellenir.
- Kaynak kayıtları (`pipeline/sources/<kimlik>.toml`): `tecrid-ar`, `tecrid-naim`, `tecrid-miras`, `hadis-fawaz-ar` güncellenir (`kaynak_url`, `surum` ya da commit SHA'sı, `provider`, `baski_bilgisi`; `atif_metni` korunur), `hadis-ahmedbaset` (`tur = "hadis"`) açılır. `uv run --directory pipeline mutalaa sources check` 0 ile geçer.
- Kitaplıklar: `pypdfium2` ve `pillow` A16.0'da eklenmediyse `uv add --directory pipeline pypdfium2 pillow` ile eklenir; sürümler PyPI kaydından doğrulanır ve `uv.lock` içinde sabitlenir. Başka yeni kitaplık yoktur: JSON için standart kitaplık, normalleştirme için A05, hizalama için A18 iktibas motoru.
- Hazır yapı önce gelir: Arapça birimler hazır dijital metinlerden üretilir (Shamela HTM, iki JSON veri seti); kendi Arapça OCR'ımız yazılmaz. OCR yalnız Türkçe cilt metni ve doğrulama örneklemi içindir (A19.3).
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; beş indirme klasöründe dosyalar ve `SHA256SUMS` var; ölçümler tabloyla uyumlu ya da tablo güncellendi; beş kaynak kaydı güncel ve `sources check` 0 hata; kitaplık sürümleri `uv.lock` içinde.

### A19.1 · Kaynak kayıtları ve cilt eşlemesi
- Kayıtlar A06'da açıldı; A19.0 alanlarını doldurdu. `arastirmaci` her kaynak için [Kaynaklar](../../04-icerik/01-kaynaklar.md) §5 kontrol listesini yeniden yürütür ve eksikleri tamamlar (alma adresi ve tarihi, baskı künyesi).
- Cilt → kaynak eşlemesi `pipeline/mutalaa.toml` içinde `[baski.tecrid-diyanet]` altında durur: cilt 1–3 `tecrid-naim`, cilt 4–12 `tecrid-miras` (ön eşleme; künye okumasından, İ-14 doğrular). Cilt 13 (Kılavuz) metin kaynağı değildir; yalnız numara ve sayfa denetiminde başvuru olarak okunur. Türkçe birimlerin `ceviri` alanı (`naim` ya da `miras`) bu eşlemeden gelir.
- OpenITI Kütüb-i Sitte sürümleri ve `at-tajrid-as-sarih-imam-az-zoubeydi_202408` yedek adaydır; kullanılırsa kaydı o gün açılır. Türkçe ve İngilizce sürümler alınmaz.
- **Bitti sayılır:** `sources check` 0; cilt eşlemesi yapılandırmada ve testte; `tecrid-naim` ve `tecrid-miras` kayıtları `kaynak_url` ve `baski_bilgisi` taşıyor.

### A19.2 · Doğrulamalar ve numaralandırma kararı
- `arastirmaci` doğrular: Shamela ve OpenITI metinlerinin dayandığı baskı (kitap kartı Müessesetü'r-Risâle 2009'u gösteriyor; kartta editörün el yazması nüshadan eklediği hadisler anılıyor, OpenITI'de 88 zevâid notu var) ve bu eklerin ayıklanması; Tecrîd numarasının Diyanet ciltleri boyunca sürekliliği; atıflardaki numaranın bâb mı hadis mi olduğu; Tecrîd'in Buhârî kitap sırasını izleyip izlemediği; Shamela metnindeki Buhârî numaralarının biçimi ve hangi numaralamaya dayandığı; AhmedBaset `idInBook` ile fawaz `hadithnumber` numaralarının hangi baskıya karşılık geldiği.
- Naim'in çevirdiği ciltler ([Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md) §3 doğrulama listesi): cilt künyesinden mütercim adı ve baskı yılı (ön okuma: cilt 1–3 Ahmed Naim, cilt 4–12 Kâmil Miras) ve Naim'in çevirisinin bittiği hadis numarası. Editör basılı ya da taranmış künye sayfalarıyla doğrular (İ-14); Claude Code listeyi tutar ve bulguları Kaynaklar §3.4'e işler.
- Numaralandırma (§5: A, B, C, D) proje sahibinin kararıdır; ilk hadis çapası `internal` derlemeye girmeden `/karar` ile yazılır. Ölçüm girdileri: Shamela dosyasının 1–2.254 numaraları, AhmedBaset `idInBook`, fawaz `hadithnumber` (kesirli alt numaralar: Buhârî 26, Tirmizî 42, Nesâî 7, İbn Mâce 2). Alt numaralar (`2564a`, ÇŞ-3) gramerde yoktur; gerekiyorsa aynı kararda ele alınır. Koleksiyon kısa adları Çapa şemasına `/belge-esitle` ile işlenir.
- **Bitti sayılır:** karar defterinde numaralandırma ve koleksiyon adları kararı var; `hadith_number_map` sistem listesi (`kaynak-baski`, `sunnah-com`, `tecrid` ve gerekirse yeni adlar) yazılı.

### A19.3 · Tecrîd metni, OCR ve birimler
- Arapça: Shamela HTM okunur (çıkarılmış metin türü; Çapa şeması §7), numaralı hadis başlıkları birimlere bölünür, kitap başlıkları `hadith_location` için alınır; OpenITI metniyle normalleştirilmiş karşılaştırma raporu üretilir (A05 normalleştiricisi), farklar `review` kuyruğuna düşer.
- Türkçe: `uv run --directory pipeline mutalaa ingest scans --edition tecrid-diyanet --dir data/gelen/tecrid-diyanet/<YYYY-AA-GG>/c01 --cilt 1` (13 cilt için). Hazır `_djvu.txt` katmanları ilk geçiştir (K-38: dijital öncelikli); OCR motoru yalnız katmanın CER'i eşiği geçmezse devreye girer.
- OCR değerlendirmesi Elmalılı yöntemiyle yapılır: tabakalı örneklem, iki kişinin yazdığı altın metin (`data/gold/tecrid-ocr/`), CER. Hazır katman ve A09 motorları aynı örneklemde ölçülür; Türkçe için CER ve WER, Diyanet ciltlerindeki Arapça bloklar için temel harf CER'i ile hareke CER'i ayrı ölçülür ve Shamela metniyle karşılaştırılır. Ciltler Latin harflidir; Osmanlıca harfli bir cilt kullanılırsa Elmalılı hazırlığı §5 aktarım kılavuzu uygulanır. Motor seçimi `/karar` ile.
- Hadis numarası işaretlerinin bulunması, Arapça blok ile Türkçe bloğun eşlenmesi. Birimler: `h:tecrid:{no}`, `ht:naim:tecrid:{no}` (cilt 1–3) ve `ht:miras:tecrid:{no}` (cilt 4–12); `ceviri` cilt eşlemesinden gelir. Kendi taramamızdan aktarılan metin bizim ürettiğimiz metindir ve ilk kayıtta NFC'ye çevrilir; üçüncü taraf Arapça metin dağıtıldığı hâliyle saklanır.
- `hadith_location` (kitap › bâb › hadis, `ord`), `hadith_number_map` (sistemler) ve baskı sayfa eşlemesi (`page_map`; `source_id` birimin kaynağıdır, baskı künyesi kaynağın `baski_bilgisi` alanındadır; Hadis hazırlığı §7, Editoryal veritabanı §9.1).
- Naim ve Miras aktarımı `review` (`hedef_tablo = 'unit'`, `alan = 'metin'`) kuyruğuna düşer; düzeltme ve onay insan işidir (İ-11); onaylanana kadar birimler `metin_durumu = 'taslak'` kalır. Kalan iş yalnız bu turları bekliyorsa `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır ve Not sütununa bekleyen işi yazar; kuyruk kurulduğu için A19.4–A19.6 sürer.
- **Panelde Arapça hadis birimi (A15 notu).** A15 paneli Arapça metni yalnız `ArabicText` bileşeniyle çizer (`lang="ar"`, `dir="rtl"`, Amiri Quran; kırpma ve normalizasyon yok) ve Kur'an birimi için yazılmıştır. Arapça hadis birimleri (`h:tecrid:{no}`, `h:…`) panelde `kuyruk/ocr` ve `birimler` ekranlarına geldiğinde `ArabicText` ve sağdan sola düzen bu birimler için genişletilir (harekeli metnin satır aralığı ve yazı tipi yedeği, karma Türkçe/Arapça satırlar); değişmez metin kuralı hazır Arapça hadis için de [BÇ-52](../07-belge-celiskileri.md#1-karar-bekleyenler) ile karara bağlanır.
- **Bitti sayılır:** örneklem CER raporu var; birimler G-CAP, G-BUT ve G-KAY'dan geçiyor; cilt 1–12 birimleri yüklü; cilt 13 kaynaklı birim 0.

### A19.4 · Kütüb-i Sitte Arapça alımı
- `ingest/hadith_ar.py` bağdaştırıcısı iki biçimi okur (AhmedBaset ve fawaz JSON). Birim metni AhmedBaset'ten alınır (eksiksiz); fawaz kaydı normalleştirilmiş metinle eşleşirse `hadith_number_map` satırı (`sunnah-com`) yazılır; eşleşmeyen kayıtlar ve fawaz'daki 379 boş kayıt rapora girer. Kitap adları (Arapça) `hadith_location` için alınır.
- Üçüncü taraf Arapça metin dağıtıldığı hâliyle saklanır, NFC uygulanmaz; arama metni (`ar_norm`) ayrı sütundadır. Metin yapay zekâya gönderilmez ve gömülmez.
- Hazır yapı önce gelir: iki veri seti hazırdır, kendi sayısallaştırmamız yazılmaz. Bir kitapta iki veri setinin örtüşmesi düşük çıkarsa OpenITI Shamela sürümü yedek olarak devreye girer (alma yolu Tedarik'te).
- **Bitti sayılır:** altı kitabın birimleri yüklü; kitap başına sayılar Tedarik ölçümüyle uyumlu ya da sapma açıklanmış; boş Arapça birim 0; `hadith_number_map` doldu; birimler `metin_durumu = 'taslak'`.

### A19.5 · Tecrîd → Buhârî eşlemesi ve atıf ayrıştırıcısı
- `uv run --directory pipeline mutalaa enrich hadith-map --from tecrid --to buhari`: Hadis hazırlığı §6 adımları (basılı gösterge: Shamela metnindeki Buhârî numaraları; normalize edilmiş 3–4 gram ve Smith-Waterman hizalaması; kapsama; sıra kısıtı; tekrarlarda birincil ve ikincil aday). Buhârî tarafı A19.4'te yüklenen Arapça metindir. Sonuç `xref`: `type = 'atif'`, `origin = 'hat'`, `status = 'aday'`, `evidence = {"iliski": "muhtasar-asli", "kapsama": …, "yontem": "hizalama"}`. Ayrı bir `xref.type` (ör. `paralel`) Açık sorudur.
- Altın set: ciltlere göre tabakalı 200 Tecrîd hadisi elle eşlenir (İ-13 kapsamında atıf etiketlemesi). Öneri eşiği: birincil eşlemede kesinlik ≥ 0,98; altına düşerse bütün eşlemeler tek tek onaylanır.
- Hadis atıf ayrıştırıcısı ([İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md) §13 ve Hadis hazırlığı §9): "Buhârî, Îmân 12" biçimleri, kitap adı eşleme tablosu (Arapça kitap adları A19.4'ten, Türkçe adlar Diyanet ciltlerinin başlıklarından), numaranın iki yorumu, çözülemeyen atıf `evidence.unresolved = true`. Koleksiyon adı tablosu (`collection_alias`) editoryal DDL'de yoktur; yeri `/karar` ile belirlenir (gerekirse `sunucu-gelistirici` EF göçü). Ayrıştırıcı sentetik örneklerle sınanır; Elmalılı tefsiri üzerinde koşu A37'dedir (`uv run mutalaa enrich hadith-refs --target elmalili-tefsir`).
- **Bitti sayılır:** eşleme ve ayrıştırıcı testleri yeşil; altın set etiketlendiyse kesinlik raporu var.

### A19.6 · Paketler ve yayın
- `hadis-tecrid` (`h:tecrid`, `ht:naim` ve `ht:miras`) ve `hadis-kutub-i-sitte` paketleri `publish --flavor dev` ile yayımlanır (`paket-yayini` becerisi). Genel metin paketi tanımı A13'tedir; eksik varsa `sunucu-gelistirici` ekler.
- Görünürlük kalite temellidir ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §3): onaylı olmayan hadis birimleri `dev` ve `internal`'da "doğrulanmamış" rozetiyle görünür, `public`'e girmez (P-10); Tecrîd → Buhârî `aday` eşleme satırları (`atif`) `public`'e girmez (P-07). Derece etiketi gösterilmez; Sünen koleksiyonlarının gösterimi Açık sorudur (Hadis hazırlığı §8).
- **Bitti sayılır:** `dev` manifestinde hadis paketleri var; `public` kuru çalıştırması 0 ile biter ve kapı raporunda onaysız hadis birimleri ile `aday` eşleme satırları "girmedi" diye görünür.

## Kabul ölçütleri
- [ ] `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında `tecrid-ar`, `tecrid-ar-1322`, `tecrid-diyanet`, `hadis-ahmedbaset` ve `hadis-fawaz-ar` dosyaları ile `SHA256SUMS` var; adres, sürüm ve SHA-256 değerleri A19.0 notunda.
- [ ] `uv run --directory pipeline mutalaa sources check` 0 hata ile bitiyor; `tecrid-ar`, `tecrid-naim`, `tecrid-miras`, `hadis-fawaz-ar` güncel, `hadis-ahmedbaset` açık.
- [ ] Cilt → kaynak eşlemesi yapılandırmada ve testlerde; cilt 13 kaynaklı birim 0.
- [ ] Numaralandırma, koleksiyon adları, OCR motoru ve `collection_alias` kararları karar defterinde.
- [ ] Tecrîd örnekleminde Türkçe CER ve WER, Arapçada temel harf ve hareke CER'leri ayrı raporlanmış.
- [ ] `h:tecrid`, `ht:naim:tecrid` ve `ht:miras:tecrid` birimleri G-CAP, G-BUT ve G-KAY'dan geçiyor; kendi aktarımımız NFC, üçüncü taraf metni NFC uygulanmamış (`metin-denetcisi`).
- [ ] Altı kitabın Arapça birimleri yüklü; kitap başına sayılar Tedarik ölçümüyle uyumlu ya da sapma açıklanmış; boş Arapça birim yok.
- [ ] Tecrîd → Buhârî eşlemesi ve atıf ayrıştırıcısı testleri yeşil; eşleme satırları `aday`.
- [ ] `dev` manifestinde hadis paketleri; `public` kuru çalıştırma raporunda onaysız hadis birimi ve `aday` eşleme yok.

## Doğrulama
```bash
uv run --directory pipeline mutalaa sources list
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline pytest
uv run --directory pipeline ruff check .
sha256sum data/gelen/hadis-ahmedbaset/<YYYY-AA-GG>/*.json   # SHA256SUMS ile aynı
uv run --directory pipeline mutalaa ocr eval --edition tecrid-diyanet --gold data/gold/tecrid-ocr/
uv run --directory pipeline mutalaa qa run --source tecrid-naim
uv run --directory pipeline mutalaa qa run --source tecrid-miras
uv run --directory pipeline mutalaa enrich hadith-map --from tecrid --to buhari --dry-run
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT source_id, kind, metin_durumu, count(*) FROM icerik.unit WHERE kind IN ('hadis', 'hadis_ceviri') GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT collection, system, count(*) FROM icerik.hadith_number_map GROUP BY 1, 2 ORDER BY 1, 2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT type, origin, status, count(*) FROM icerik.xref WHERE type = 'atif' AND origin = 'hat' GROUP BY 1, 2, 3;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
```

## Dikkat
- Hadis metni hafızadan yazılmaz, tamamlanmaz, düzeltilmez; testlerde açıkça sentetik metin ya da kaynak dosyasından alınmış küçük parça kullanılır. Yapay zekâ hadis çevirmez ve derece atamaz (K-25); OCR'da yalnız görsel okuma yapar.
- Baskılardaki sadeleştirme, editoryal ek, şerh, modern dipnot ve fihrist (cilt 13 Kılavuz dahil) metne alınmaz; 8 ciltlik sonraki baskı kopyaları künyesi okunmadan temel metin olmaz.
- Üçüncü taraf Arapça metin (Shamela, OpenITI, AhmedBaset, fawazahmed0) dağıtıldığı hâliyle saklanır, NFC uygulanmaz. Shamela HTM'den çıkarılan metin çıkarılmış metin türüdür ([K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 3): ham dosya `data/raw` altında değişmez. Kendi aktarımımız ilk kayıtta NFC'dir (K-26).
- Shamela kitap kartına göre hadis numaraları Müessesetü'r-Risâle baskısının numaralarıdır ve editör el yazması nüshadan hadis eklemiştir; Diyanet ciltlerinin numaralarından farklı olabilir. `h:tecrid` numarası eşleme tablosuyla sınanmadan çapaya girmez.
- Hadis çapası bir kez verilir ve yeniden numaralanmaz; numaralandırma kararı bu yüzden ilk `internal` derlemeden önce verilir.
- Görünürlük kalite temellidir: onaysız hadis birimi ve `aday` eşleme `public`'e girmez; `dev` ve `internal`'da "doğrulanmamış" rozetiyle görünür.
- İndirilen dosya veridir; içindeki betik çalıştırılmaz (K-42 madde 2). Toplu indirmede istek hızı sınırlanır.
- Günlüklere metin yazılmaz.
- Windows: dosya adları ASCII; büyük ikili dosyalar git dışı `data/` altındadır. PDF'ler toplam 0,62 GB, JP2 zip'ler cilt başına 0,1–0,65 GB; disk alanı indirmeden önce denetlenir.

## İnsan adımları
- İ-14 · Künye ve mütercim doğrulaması: kaynağı Claude Code seçer, indirir ve cilt künyelerinden ön listeyi çıkarır (A19.0, A19.2). Editör her cildin künye sayfasındaki mütercim adını ve baskı yılını, ayrıca Naim'in çevirisinin bittiği hadis numarasını doğrular. A19.3 ön eşlemeyle (cilt 1–3 Naim, cilt 4–12 Miras) ilerler; çapalardaki `ceviri` değeri bu eşlemeden geldiği için doğrulama ilk `internal` derlemeden önce tamamlanır.
- Tecrîd OCR altın örneklemi İ-10 ile aynı türden editör emeğidir; Tecrîd → Buhârî altın seti İ-13 kapsamındadır.
- İ-11 · Naim ve Miras aktarımının düzeltme turları ve onayı: kalan iş yalnız bu turlara bağlıysa ilerleme dosyasına `engelli` ve bekleyen iş yazılır ([İnsan adımları](../06-insan-adimlari.md)).

## Çıktılar
- `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında indirilen dosyalar ve `SHA256SUMS` (git dışı)
- `pipeline/sources/tecrid-*.toml`, `hadis-*.toml`; cilt → kaynak eşlemesi (`pipeline/mutalaa.toml`)
- `pipeline/src/mutalaa_pipeline/ingest/hadith_ar.py`, `anchor/hadith.py`, `enrich/hadith_map.py`, `enrich/hadith_refs.py`, testler
- PostgreSQL'de hadis birimleri, `hadith_number_map`, `hadith_location`, `page_map`, `xref` adayları, `review` kayıtları
- Karar defterinde numaralandırma ve diğer kararlar; `dev` kanalında hadis paketleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A19-hadis-hatlari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A18](./A18-baglantilar-ve-altin-setler.md) · Sonraki: [A20](./A20-risale-altyapisi.md)
