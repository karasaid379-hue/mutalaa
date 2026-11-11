# Hadis Hazırlığı
> **Sürüm:** 1.4 · **Tarih:** 11 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-04](../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-49](../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)

K-04 gereği Tecrîd-i Sarîh (Arapça metin ve Türkçesi: Babanzâde Ahmed Naim ile Kâmil Miras ciltleri, tam takım) ile Kütüb-i Sitte'nin Arapça metni birlikte işlenir. Paketler `hadis-tecrid` ve `hadis-kutub-i-sitte` adını taşır. Çapalar `h:{koleksiyon}:{no}` (Arapça) ve `ht:{ceviri}:{koleksiyon}:{no}` (çeviri) biçimindedir; örnek `h:tecrid:15`, `ht:naim:tecrid:15`, `h:buhari:52`.

## 1. Kaynak ilkesi

Kaynak; göreve uygunluk, eksiksizlik, baskı esasının belgelenmesi, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirlik ölçütleriyle seçilir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1). Başvuru, onay ya da API anahtarı isteyen kaynak seçilmez. Önce hazır dijital metin aranır; tarama ve OCR yedek yoldur (K-38). Dosyaları Claude Code indirir: her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni bir klasöre iner ve klasörde `SHA256SUMS` bulunur. Adresler, sürümler ve sayımlar A19 `## Tedarik` bölümündedir.

- **Arapça metin.** Tecrîd'in Arapçası hazır dijital kaynaktan gelir (harekeli Shamela dışa aktarımı birincil, OpenITI sürümü karşılaştırma); özgün baskı görüntüleri sayfa eşlemesi ve doğrulama içindir. Kütüb-i Sitte'nin Arapçası iki JSON veri setinden alınır (bölüm 4).
- **Türkçe metin.** Tecrîd'in Türkçesi Diyanet'in 13 ciltlik takımından gelir; cilt 1–3 Ahmed Naim, cilt 4–12 Kâmil Miras çevirisidir (bölüm 3). Yapay zekâ hadis çevirmez (K-25).
- **Baskı esası.** Hazır veri setlerinin baskı esası çoğu zaman belirsizdir; asıl sorun kaynak belgelerinin zayıflığıdır (rapor). Baskı esası belgelenmemiş set temel metin olmaz (K-38): metin `taslak` girer ve editör onayından geçer; numaralandırma ve baskı esası ölçümle belirlenir (bölüm 4 ve 5).
- **Metne alınmayanlar.** Baskılardaki sadeleştirme, editoryal ek, şerh, modern dipnot ve fihrist birim olmaz; cilt 13 "Kılavuz" metin kaynağı değildir.
- **Görünürlük.** Onaylı hadis birimi her derlemeye girer. Onaysız birim `dev` ve `internal` derlemelerinde "doğrulanmamış" rozetiyle görünür, `public`'e girmez (K-42 madde 5; [Yayın süreci](../07-yayin/01-yayin-sureci.md) §3).

## 2. Kapsam ve kaynaklar

| Parça | Kayıt | Kaynak ve işleniş |
|---|---|---|
| Tecrîd Arapça metni | `tecrid-ar` | Harekeli Shamela dışa aktarımı (archive.org `0001Htm48_201901`, `1145Htm.zip`) birincil; OpenITI `TajridSarih` sürümü (harekesiz) yapı ve karşılaştırma için; özgün baskı görüntüleri (archive.org `AAlexandrina-103522`, Kahire 1322) sayfa eşlemesi ve doğrulama için |
| Ahmed Naim Türkçesi (cilt 1–3) | `tecrid-naim` | Diyanet 13 ciltlik takım (Ankara 1976–1980, Latin harfli): archive.org metin katmanı ilk geçiş, PDF görüntüleri OCR ve doğrulama için |
| Kâmil Miras Türkçesi (cilt 4–12) | `tecrid-miras` | Aynı takım; cilt 13 "Kılavuz"dur ve metin kaynağı değildir |
| Kütüb-i Sitte Arapça metni (altı kitap) | `hadis-ahmedbaset` (A19.0'da açılır), `hadis-fawaz-ar` | AhmedBaset/hadith-json `v1.2.0` metin kaynağı; fawazahmed0/hadith-api numara sistemi ve harekesiz sürüm; yedek OpenITI Shamela sürümleri |
| Sıhhat derecesi etiketleri | — | Yok; sonra (bölüm 8) |

Ölçümler (A19, 2 Kasım 2026; yalnız sayım ve yapı): Shamela dosyasında 2.253 numaralı hadis (numaralar 1…2.254); AhmedBaset altı kitapta 34.178 kayıt (boş Arapça kayıt 0); fawazahmed0 altı kitapta 34.532 kayıt (379'unun Arapça metni boş).

## 3. Naim ve Miras ciltleri (Doğrulanacak)

Kaynaklar cilt paylarını farklı anlatır. Küre'deki Miras maddesine göre Kâmil Miras III. cildin müsveddesini hazırladı ve IV–XII. ciltleri (İstanbul 1938–1948) tamamladı ([Küre: Miras](https://kureansiklopedi.com/tr/detay/miras-kamil)); buna göre Naim'in payı I–II. ciltler ve belki III. cildin bir kısmıdır. Diyanet takımının künye satırlarından okunan ön eşleme cilt 1–3 Ahmed Naim, cilt 4–12 Kâmil Miras, cilt 13 "Kılavuz"dur.

Doğrulama listesi:
- [ ] Her cildin künye sayfasında mütercim adı ve baskı yılı.
- [ ] Önsöz ve sonsözlerde çevirinin kimden kime geçtiğine dair ifade.
- [ ] Kütüphane kayıtlarında cilt başına mütercim.
- [ ] Naim'in çevirisinin bittiği hadis numarası.
- [ ] Ciltlerde Arapça blokların basılı olduğunun görüntüden teyidi ve cilt başına sayfa sayısı (yalnız cilt 1 için ölçüldü: 768 yaprak).
- [ ] Ciltlerdeki çeviri dışı açıklama, giriş ve fihrist bölümlerinin sınırları (bunlar birim olmaz).

Kural: Her Türkçe birim `ceviri` alanı taşır: `naim` ya da `miras`. Çapalar buna göre `ht:naim:tecrid:{no}` ya da `ht:miras:tecrid:{no}` olur. Cilt → çeviri eşlemesi `pipeline/mutalaa.toml` içinde `[baski.tecrid-diyanet]` altında durur ve ön eşlemeyle başlar. Çapalardaki `ceviri` değeri bu eşlemeden geldiği için editör doğrulaması (İ-14) ilk `internal` derlemeden önce tamamlanır.

**Kaynak bulguları (okuma 27 Ekim 2026 ve A19 tedarik ölçümü, 2 Kasım 2026).** Ayrıntı: [Kaynaklar](./01-kaynaklar.md) §3.4.
- **Naim ve Miras payı.** Hansu'ya göre ([Küre: et-Tecrîdü's-sarîh](https://kureansiklopedi.com/tr/detay/et-tecridus-sarih), 20.11.2024) Naim mukaddimeyle 477 hadisi iki cilt hâlinde yayımladı (İstanbul 1346/1928), III. cildi hazırladı ama yayımlanmadan 1934'te öldü; Kâmil Miras III. cildi gözden geçirip yayımladı. Aynı maddede Naim'in çevirdiği hadis sayısı 589, baskıda görünen 574 olarak geçiyor; fark ve 477 ile ilişki açık. [TDV İA Babanzâde maddesi](https://islamansiklopedisi.org.tr/babanzade-ahmed-naim) "ilk üç cilt"i Naim'e verir. Fark, Miras'ın payının anılıp anılmamasından gelebilir (çıkarım). Yukarıdaki "Miras III. cildin müsveddesini hazırladı" bilgisiyle ([Küre: Miras](https://kureansiklopedi.com/tr/detay/miras-kamil)) Hansu'nun anlatımı uyuşmuyor; ciltlerin künye ve önsözleriyle sınanır (doğrulama listesinin ilk iki maddesi).
- **Türkçe metin.** Seçilen kaynak Diyanet'in 13 ciltlik takımıdır ("Sahîh-i Buhârî Muhtasarı Tecrîd-i Sarîh Tercemesi ve Şerhi", Başbakanlık Basımevi, Ankara 1976–1980, 4.–6. baskılar, Latin harfli). Metin katmanı archive.org'da 13 tek ciltlik öğededir (ABBYY FineReader, toplam 12.552.425 bayt); görüntüler `buharitecridisarih` öğesinde 13 PDF'tir (toplam 622.842.078 bayt). Metin katmanında Arapça harf yoktur ve Türkçe harf bozuklukları vardır; katman ilk geçiştir, CER bölüm 7'deki yöntemle ölçülür. 8 ciltlik sonraki baskıların kopyaları künyesi okunmadan ve sadeleştirme taraması yapılmadan kullanılmaz. İTÜ Dijital Koleksiyonlar kaydı (1926–1928, cilt 1–3, "Osmanlıca") yalnız üst veri gösterir; Diyanet ePUB'ı (yayin.diyanet.gov.tr, 1. cilt ISBN 9789751970602) arama özetine göre modern bir baskıdır ve Miras ciltlerini de içerir, birincil sayfa açılmadı. İkisi de seçilmedi.
- **Arapça hazır metinler.** Birincil kaynak Shamela dışa aktarımıdır (archive.org `0001Htm48_201901`, `1145Htm.zip`; windows-1256 kodlu tek `.htm`; Arapça harf 509.250, hareke kod noktası 343.607; 2.253 numaralı hadis, numaralar 1…2.254). OpenITI `TajridSarih` sürümü (`master` ve `pre-clean` etiketi; harekesiz; `pre-clean`'de 91 kitap başlığı ve 88 zevâid notu) yapı ve karşılaştırma içindir. İki kopya da Risâle 2009 baskısına dayanıyor; zevâid hadisleri ve Buhârî numaraları eklenmiş. Kahire 1322 baskısının taraması (archive.org `AAlexandrina-103522`) görüntü kaynağıdır; hazır OCR metni zayıf olduğu için (hareke harf başına 0,002) metin kaynağı sayılmaz.
- **Arapça metnin yazarı.** Tecrîd'in müellifi Zebîdî'dir ([TDV İA](https://islamansiklopedisi.org.tr/zebidi-ahmed-b-ahmed)).

## 4. Kütüb-i Sitte Arapça veri seti seçenekleri

Kütüb-i Sitte için iki veri seti birlikte alınır: AhmedBaset'te boş Arapça kayıt yoktur ve kitap adları Arapçadır; fawazahmed0'da Sunnah.com numarası (`hadithnumber`) ve harekesiz sürüm vardır, ama 379 kaydın Arapça metni boştur. fawazahmed0'daki normalleştirilmiş benzersiz metinlerin %99,7–99,9'u AhmedBaset'te de bulunduğu için numara eşlemesi metinle yapılır.

| Seçenek | Ne veriyor | Sorun | Hüküm |
|---|---|---|---|
| fawazahmed0/hadith-api | 20 Arapça ve 8 Türkçe koleksiyon ([editions.json](https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions.json)); altı kitapta 34.532 kayıt; Sunnah.com numarası (`hadithnumber`); harekeli ve harekesiz sürüm | README metinlerin kaynağını belgelemiyor; numaralandırmanın dayandığı baskı belirsiz; 379 kaydın Arapça metni boş | Numara sistemi (`sunnah-com`) ve harekesiz sürüm için `hadis-fawaz-ar`; Türkçe ve İngilizce sürümler alınmaz (çevirmen belgelenmemiş) |
| AhmedBaset/hadith-json | `v1.2.0` etiketi; `the_9_books` altında altı kitapta 34.178 hadis (boş Arapça kayıt 0), harekeli Arapça ve İngilizce, Arapça kitap adları; depo genelinde 50.884 hadis ve 17 kitap ([README](https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/README.md)) | Numaraların hangi baskıya karşılık geldiği doğrulanmadı (A19.2); `idInBook` numarası fawazahmed0 `hadithnumber` değerinden farklı bir sıradır; kayıtların çoğu NFC değil | Metin kaynağı `hadis-ahmedbaset`; İngilizce sürüm alınmaz |
| Sunnah.com API | "You will need an API key"; "a portion of our data"; çevrimdışı döküm henüz yok ([Sunnah.com](https://sunnah.com/developers)) | API anahtarı ister; verinin yalnız bir bölümünü sunar | Seçilmedi |
| OpenITI Shamela sürümleri | Altı kitap, mARkdown, harekesiz, sayfa işaretli, baskı künyeli | Harekesiz; hadis sayısı ve numaralama ölçülmedi | Yedek: iki veri setinin örtüşmesi bir kitapta düşük çıkarsa devreye girer |
| Kendi sayısallaştırmamız | Basılı nüshalardan OCR | Harekeli Arapça OCR emek ister; baskı seçimi numaralandırma kararına bağlı | Son yol: hazır metinler baskı esasını belgeleyemezse |

**Önerilen yol.**
1. Tecrîd'in Arapça metni harekeli Shamela dışa aktarımından alınır. OpenITI sürümüyle normalleştirilmiş karşılaştırma raporu üretilir (A05 normalleştiricisi); farklar `review` kuyruğuna düşer. Özgün baskı görüntüleri (Kahire 1322) sayfa eşlemesi ve doğrulama içindir.
2. Kütüb-i Sitte'nin metni AhmedBaset'ten alınır (eksiksiz, Arapça kitap adlarıyla). fawazahmed0 kayıtları normalleştirilmiş metinle eşleştirilir; eşleşenler için `sunnah-com` numara sistemi eşleme tablosuna yazılır. Eşleşmeyen kayıtlar ve fawazahmed0'daki 379 boş kayıt rapora girer.
3. Bir kitapta iki veri setinin örtüşmesi düşük çıkarsa o kitap için baskı künyeli OpenITI Shamela sürümü devreye girer.
4. Hazır kaynakların hiçbiri baskı esasını belgeleyemezse numaralandırma kararında seçilen baskının nüshasından kendi sayısallaştırmamız yapılır (K-38).
5. Seçilen kaynak `source` kaydıyla izlenir; her birim ve bağlantı kaynak kimliğini taşıdığı için kalite sorunu çıkan bir veri seti yayından önce tek hamlede dışarıda bırakılabilir (K-27).
6. Üçüncü taraf veri setinden gelen Arapça metin dağıtıldığı hâliyle, NFC uygulanmadan saklanır. Kendi taramamızdan aktarılan metin bizim ürettiğimiz metindir ve ilk kayıtta NFC'ye çevrilir (K-26). HTML, EPUB ya da PDF'ten çıkarılan metin için çıkarılmış metin türü geçerlidir ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme), madde 3; [Çapa şeması](../03-veri/01-capa-semasi.md#7-kanonik-metin-ve-content_hash) §7).

## 5. Numaralandırma kararı: `h:{koleksiyon}:{no}` (Açık soru)

Çapalar hiçbir sürümde yeniden numaralanmaz (K-26). Notlar, yer imleri ve `xref` satırları hadis çapasına bağlanacağı için bu karar ilk hadis çapası bir `internal` derlemeye girmeden verilmelidir.

Kaynak edinimi yolu (bölüm 4; K-38) bütün kitaplara uygulanır: baskı esası belgelenmemiş set temel metin olmaz ve numaralandırma baskı esasına göre seçilir.

**Koleksiyon kısa adları (öneri).** `tecrid`, `buhari`, `muslim`, `ebu-davud`, `tirmizi`, `nesai`, `ibn-mace`. Kesin liste [Çapa şeması](../03-veri/01-capa-semasi.md) dosyasında tutulur.

| Seçenek | Açıklama | Artı | Eksi |
|---|---|---|---|
| A. Kaynak baskı numarası | Her koleksiyonda adı belli bir baskının sürekli numarası (baskı seçimi Doğrulanacak) | Basılı atıflarla uyumlu; bir platforma bağlı değil | Dijital metnin bu baskıyla hizalı olması gerekir |
| B. Sunnah.com numarası | Platformun numaralandırması; fawazahmed0 `hadithnumber` değerleri bu sistemdedir | Çevrimiçi paralel bağlantı kolay; veri bu kaynaktan gelirse doğal uyum | Platform bağımlılığı; numaralandırma değişebilir |
| C. Kendi sıra numaramız | 1'den başlayan iç numara | Tam denetim | Dışarıda anlamı yok; eşleme tablosu yine gerekir |
| D. Kitap-bâb-hadis bileşik numarası | ör. 2.12.3 | Okunur konum | Gramerdeki tek `{no}` alanına uymaz; gramer değişikliği ister |

**Öneri.** Kütüb-i Sitte için A seçeneği; Tecrîd için basılı Tecrîd numarası (`h:tecrid:{no}`; numaranın ciltler boyunca sürekli olup olmadığı Doğrulanacak). Diğer numara sistemleri eşleme tablosunda tutulur.

> **Uyarı (okuma 27 Ekim 2026).** Shamela ve OpenITI'deki Tecrîd Arapçası Risâle 2009 baskısına dayanıyor; editör Buhârî numaralarını ve 105 zevâid hadisini eklemiş (Doğrulanacak). Bu yüzden o kopyaların numaralandırması basılı Tecrîd numarasından farklı olabilir. `h:tecrid` numaralarıyla örtüşmesi sınanmadan bu numaralar eşleme tablosuna ya da çapaya girmez. Sınama Diyanet ciltlerinin ve özgün baskı görüntülerinin numaralarıyla yapılır; zevâid hadisleri ayıklanır (A19.2).

**Ölçüm (A19, 2 Kasım 2026).** fawazahmed0'daki normalleştirilmiş benzersiz metinlerin %99,7–99,9'u AhmedBaset'te de bulunur (AhmedBaset'te olup fawazahmed0'da bulunmayan benzersiz metin: Müslim 181, Tirmizî 144, Nesâî 99), ama aynı numarada aynı metin oranı düşüktür (fawazahmed0 `hadithnumber` ve AhmedBaset `idInBook` karşılaştırması: Buhârî 272/7.268, Müslim 0/7.269, Ebû Dâvûd 905/5.272, Tirmizî 744/3.889, Nesâî 156/5.672, İbn Mâce 0/4.336). İki numara sistemi farklıdır; eşleme metinle yapılır. fawazahmed0'da kesirli alt numara sayısı Buhârî 26, Tirmizî 42, Nesâî 7, İbn Mâce 2'dir; alt numaralar (`2564a`) gramerde yoktur ([Çapa şeması](../03-veri/01-capa-semasi.md) ÇŞ-3) ve gerekiyorsa bu kararda ele alınır.

Eşleme tablosu (editoryal adı `hadith_number_map`, [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) §11):

```sql
-- Öneri; kesin şema Editoryal veritabanı dosyasında
CREATE TABLE hadis_numara_esleme (
  koleksiyon text NOT NULL,          -- 'buhari'
  sistem     text NOT NULL,          -- 'kaynak-baski', 'sunnah-com' (numaralandırma etiketi), 'tecrid'
  numara     text NOT NULL,          -- sistemdeki numara
  capa       text NOT NULL,          -- 'h:buhari:52'
  PRIMARY KEY (koleksiyon, sistem, numara)
);

CREATE TABLE hadis_konum (            -- akademik mod gezinmesi: kitap › bâb › hadis
  capa     text PRIMARY KEY,
  kitap_no int, kitap_ad text,
  bab_no   int, bab_ad   text,
  sira     int NOT NULL
);
```

Kitap › bâb › hadis gezinmesi hadis okuyucusunun akademik modunda kullanılır. Karar proje sahibince verilip karar defterine yeni madde olarak eklenir. Pakette ayrı bir `hadis_konum` tablosu yoktur (editoryal adı `hadith_location`, [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) §11); kitap › bâb konumu paketteki `unit` tablosunun genel alanlarıyla taşınır: `parent_path` (içindekiler yolu), `label`, `ord` ve kitap ile bâb numarası ve adı için `attrs` ([İçerik paketleri](../03-veri/03-icerik-paketleri.md) §3.2; öneri).

## 6. Tecrîd numaralarını Buhârî numaralarına eşleme

Amaç: Tecrîd hadisinden Buhârî'deki tam rivayete geçiş, Naim çevirisini Kütüb-i Sitte Arapçasına bağlama ve bağlantı panelinde "aynı hadis" gösterimi.

1. **Basılı gösterge.** Shamela metni her hadisten sonra Sahîh-i Buhârî numarasını verir; bu numaraların biçimi ve dayandığı numaralama A19.2'de ölçülür. Tecrîd ciltleri Buhârî'deki kitap ya da bâb bilgisini veriyorsa o da ayrıştırılır (Doğrulanacak).
2. **Metin hizalaması.** İki taraf (Tecrîd ve bölüm 4'te alınan Buhârî metni) iktibas tespitindeki normalizasyondan geçer: harekeler ve tatvil silinir; أ إ آ ٱ → ا, ى → ي, ة → ه ([İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md)). Buhârî metninden 3–4 kelimelik n-gram ters indeksi oluşturulur; aday eşleşmeler Smith-Waterman hizalamasıyla genişletilir ve kapsama oranı kaydedilir.
3. **Sıra kısıtı.** Tecrîd'in Buhârî'nin kitap sırasını izlediği doğrulanırsa eşleme dinamik programlamayla sıralı tutulur; sıradan sapan eşleşmeler incelemeye düşer.
4. **Tekrarlar.** Buhârî bir hadisi birden fazla yerde verebilir. Birden fazla aday varsa Tecrîd başlığıyla aynı kitaptaki aday birincil, diğerleri ikincil bağlantı olur.
5. **İnsan onayı.** Her eşleme editör panelinde Arapça metinler yan yana gösterilerek onaylanır.

**Saklama.** Ara çözüm olarak `xref` satırı: `type = 'atif'`, `origin = 'hat'`, `status = 'aday'`, `evidence = {"iliski": "muhtasar-asli", "kapsama": 0.92, "yontem": "hizalama"}`. Bu ilişki için ayrı bir `xref.type` değeri (ör. `paralel`) eklenip eklenmeyeceği Açık soru ([Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md)). `atif` insan onayı isteyen bir türdür: `aday` eşleme satırları yalnız `dev` ve `internal` derlemelerinde görünür, `public`'e yalnız onaylı satırlar girer (P-07).

**QA.** Ciltlere göre tabakalı 200 Tecrîd hadisi elle eşlenir ve altın set olur. Birincil eşleme için kesinlik ve duyarlılık raporlanır. Öneri eşiği: otomatik önerilen birincil eşlemelerde kesinlik ≥ 0,98; altına düşerse bütün eşlemeler tek tek onaylanır.

## 7. OCR ihtiyacı (S-15'e ertelendi)

- **Tecrîd.** Türkçe metin ve harekeli Arapça metin aynı sayfadadır. Diyanet takımı Latin harflidir; archive.org metin katmanı (`_djvu.txt`) hazır metin yoluyla alınır (K-38, [K-49](../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi) madde 3); katman uygun değilse (eksiksiz kapsam, yapılandırılabilir biçim, sabitlenebilir sürüm) ilgili cildin OCR'ı proje sonuna bırakılır (S-15). Metin katmanında Arapça harf yoktur: Arapça bloklar görüntüden okunur ve Shamela metniyle karşılaştırılır; kendi Arapça OCR'ımız yazılmaz, Arapça birimler Shamela metninden gelir. Osmanlıca harfli bir cilt kullanılırsa Elmalılı aktarım kılavuzu uygulanır ([Elmalılı hazırlığı](./03-elmalili-hazirligi.md)). OCR değerlendirmesi (tabakalı örneklem, altın metin, CER) S-15'tedir; A19'da katman otomatik denetimlerle ve Shamela karşılaştırmasıyla ölçülür. Arapçada temel harf farkı ile hareke farkı ayrı raporlanır.
- **Motor ve maliyet.** OCR yapılırsa (S-15) motor o aşamada seçilir; A09 ertelendi ve motor seçilmedi. Ücretli motor ya da görsel model kullanılırsa tam koşudan önce tahmini maliyet kullanıcıya gösterilir ([İçerik hattı](./02-icerik-hatti.md) §11). Yapay zekâ OCR'da yalnız görsel okuma yapar; hadis çevirmez.
- **Hadis birimlerine bölme.** Hadis numarası işaretleri bulunur; her numara için Arapça blok ile Türkçe blok eşlenir; `h:tecrid:{no}`, `ht:naim:tecrid:{no}` ve `ht:miras:tecrid:{no}` birimleri üretilir (`ceviri` cilt eşlemesinden gelir). Sayfa eşlemesi Elmalılı'daki gibi `page_map` tablosuna birimin kaynağıyla (`source_id`), cilt ve sayfayla yazılır; baskı künyesi kaynağın `baski_bilgisi` alanındadır ([Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md#91-page_map-ayah_box-audio_timing) §9.1).
- **Kütüb-i Sitte.** OCR yalnız kendi sayısallaştırma yolu seçilirse gerekir. Harekeli Arapça için ayrı CER eşiği konur.
- **Editör turları.** Naim ve Miras aktarımı `review` kuyruğuna düşer (`hedef_tablo = 'unit'`, `alan = 'metin'`); düzeltme turları ve onay editör emeğidir (İ-11). Onaylanana kadar birimler `metin_durumu = 'taslak'` kalır.

```bash
# S-15 (ertelendi; komutlar henüz yok)
uv run mutalaa ingest scans --edition tecrid-diyanet --dir data/gelen/tecrid-diyanet/<YYYY-AA-GG>/c01 --cilt 1   # 13 cilt için
uv run mutalaa ocr run   --edition tecrid-diyanet --engine vision --pages c01:1-30
uv run mutalaa ocr eval  --edition tecrid-diyanet --gold data/gold/tecrid-ocr/
uv run mutalaa anchor    --source tecrid-naim
uv run mutalaa anchor    --source tecrid-miras
uv run mutalaa enrich hadith-map  --from tecrid --to buhari
uv run mutalaa enrich hadith-refs --target elmalili-tefsir
uv run mutalaa qa run    --source tecrid-naim
uv run mutalaa qa run    --source tecrid-miras
```

## 8. Sıhhat derecesi etiketleri (sonra)

- v1'de derece etiketi gösterilmez.
- Etiket eklendiğinde her derece adı belli bir kaynağa dayanır: âlim ya da eser, baskı ve sayfa. Farklı görüşler yan yana gösterilir. Uygulama kendi derecesini üretmez; yapay zekâ derece atamaz. Bu kural fetva vermeme ve tarafsızlık ilkelerinden gelir (K-25).
- Derecelendirme sonraya bırakılır. Sünen koleksiyonlarının v1'de nasıl gösterileceği Açık soru: (a) "Derece bilgisi bu sürümde yok" notuyla göstermek, (b) önce yalnız Tecrîd, Buhârî ve Müslim'i açmak, (c) derece politikası belirlenene kadar Sünen koleksiyonlarını açmamak.

## 9. Risale ve tefsirde hadis atıflarının tespiti

İki tür atıf vardır: açık kaynak gösterimi ("Buhârî, Îmân 12") ve Arapça hadis metninin alıntılanması.

**Açık atıf ayrıştırıcısı.** Aşağıdaki sürüm Unicode ve Türkçe harf katlamasıyla çalışır ve konum ofsetlerini korur.

```python
import regex as re

def katla(s: str) -> str:
    """Türkçe küçük harf ve düzeltme işaretsiz biçim; NFC metinde uzunluğu korur."""
    s = s.replace("I", "ı").replace("İ", "i").lower()
    return s.translate(str.maketrans("âîû", "aiu"))

KOLEKSIYON = {
    "buhari": ["buhari"], "muslim": ["müslim"], "ebu-davud": ["ebu davud"],
    "tirmizi": ["tirmizi"], "nesai": ["nesai"], "ibn-mace": ["ibn mace", "ibni mace"],
}
ALIAS = {a: k for k, v in KOLEKSIYON.items() for a in v}
KOL = "|".join(sorted(map(re.escape, ALIAS), key=len, reverse=True))
ATIF = re.compile(rf"\b(?P<kol>{KOL})\s*,\s*(?P<kitap>\p{{L}}[\p{{L}}'’ -]{{1,40}}?)\s*,?\s*(?P<no>\d+)\b")

def adaylar(metin: str):
    for m in ATIF.finditer(katla(metin)):
        yield {
            "koleksiyon": ALIAS[m["kol"]],
            "kitap": m["kitap"].strip(),     # kitap adı eşleme tablosuyla çözülür
            "no": int(m["no"]),
            "yorumlar": ["bab", "hadis"],    # numaranın anlamı koleksiyona göre değişir
            "span": (m.start(), m.end()),    # özgün metinde aynı ofset
        }
```

- **Kitap adı.** Her koleksiyon için kitap adı eşleme tablosu tutulur (ör. "îmân", "iman", "kitâbü'l-îmân" → aynı kitap).
- **Numaranın anlamı.** Numaranın bâb mı hadis mi olduğu koleksiyona ve atıf geleneğine göre değişir (Doğrulanacak). Ayrıştırıcı iki yorumu da aday üretir; çözümleme `hadis_konum` tablosuyla yapılır; belirsiz kalanı insan seçer.
- **Arapça alıntılar.** İktibas tespitindeki n-gram ve hizalama yöntemi, indeks olarak hadis metinleriyle çalıştırılır.
- **Bağlantı türleri.** Açık atıf `atif`, metin alıntısı `iktibas`, metni verilmeyen anıştırma `ima` (yalnız küratörlü) olarak `xref` tablosuna girer. Bu türler insan onayı isteyen türlerdir: `aday` satırlar `dev` ve `internal` derlemelerinde görünür, `public`'e yalnız onaylı satırlar girer (P-07).
- **Kapsam.** Ayrıştırıcıyı A19 kurar ve sentetik örneklerle sınar; Elmalılı tefsiri üzerindeki koşu A37'de, Risale metni ([Risale hazırlığı](./05-risale-hazirligi.md)) üzerindeki koşu A20 sonrasında yapılır. Dipnotlardaki kaynak göstermeleri rol alanında ayrı tutulur (A20.2); yayıncı notları müellif metni sayılmaz.

## 10. Açık sorular

1. Numaralandırma sistemi (bölüm 5) ve her koleksiyon için kaynak baskı; AhmedBaset `idInBook` ile fawazahmed0 `hadithnumber` numaralarının hangi baskıya karşılık geldiği.
2. Naim'in çevirdiği ciltler ve Naim'in son hadis numarası (İ-14).
3. Tecrîd ↔ Buhârî ilişkisi için ayrı `xref.type` değeri.
4. Sünen koleksiyonlarının derecesiz gösterimi.
5. Shamela metnindeki Buhârî numaralarının biçimi ve zevâid hadislerinin ayıklanması (A19.2).

## İlgili dosyalar
- [Kaynaklar](./01-kaynaklar.md) · [İçerik hattı](./02-icerik-hatti.md) · [Elmalılı hazırlığı](./03-elmalili-hazirligi.md) · [Risale hazırlığı](./05-risale-hazirligi.md)
- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md)
- [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)
