# Hadis Hazırlığı
> **Sürüm:** 1.2 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-04](../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)

K-04 gereği Tecrîd-i Sarîh (Arapça metin ve Babanzâde Ahmed Naim'in Türkçesi) ile Kütüb-i Sitte'nin Arapça metni birlikte işlenir. Paketler `hadis-tecrid` ve `hadis-kutub-i-sitte` adını taşır. Çapalar `h:{koleksiyon}:{no}` (Arapça) ve `ht:{ceviri}:{koleksiyon}:{no}` (çeviri) biçimindedir; örnek `h:tecrid:15`, `ht:naim:tecrid:15`, `h:buhari:52`.

## 1. Hukuki durum

> **Hukuki görüş değildir.** Kaynak: araştırma raporu ve bağlantısı verilen sayfalar.

- Tecrîd-i Sarîh çevirisi 1925'te sipariş edildi ve Babanzâde Ahmed Naim'e verildi. Naim 13 Ağustos 1934'te vefat etti; çevirdiği kısım 1 Ocak 2005'ten beri serbest. Kâmil Miras III. cildin müsveddesini hazırladı, IV–XII. ciltleri (İstanbul 1938–1948) tamamladı ve 30 Nisan 1957'de vefat etti; ciltleri 1 Ocak 2028'de serbest kalır ([Küre: Miras](https://kureansiklopedi.com/tr/detay/miras-kamil)).
- Klasik koleksiyonların Arapça metni yaşı itibarıyla serbesttir. Asıl sorun dijital veri setlerinin kaynak belgelerinin zayıflığıdır (rapor).
- Modern Türkçe hadis çevirileri korumalı kabul edilir. Sunnah.com'daki İngilizce çeviriler modern ve korumalıdır. Bilmen'in *Hikmet Goncaları* 1 Ocak 2042'de serbest kalır.
- Miras ciltlerinin metni 1 Ocak 2028'e kadar indirilmez, taranmaz ve hatta işlenmez ([lisans defterindeki iç kullanım kuralı](./01-kaynaklar-ve-lisans-defteri.md)). Araçlar Naim ciltleri üzerinde hazırlanır.
- Hadis metinleri 633 m. 6 kapsamında Kur'an yayını sayılmaz; Kurul onayı gerekmez (çıkarım). Metin içinde geçen âyet çevirilerinin durumu Açık soru.

## 2. Kapsam ve takvim

| Parça | Ekim 2026 | 1 Ocak 2028 |
|---|---|---|
| Tecrîd Arapça metni, Naim ciltleri | İşlenir (`tecrid-ar`) | |
| Ahmed Naim Türkçesi | İşlenir (`tecrid-naim`) | |
| Kâmil Miras ciltleri (Türkçe ve aynı ciltlerdeki Arapça) | Hatta alınmaz | Tarama ve OCR başlar (`tecrid-miras`) |
| Kütüb-i Sitte Arapça metni | İzin ya da kendi sayısallaştırmamız (bölüm 4) | |
| Sıhhat derecesi etiketleri | Yok | Sonra (bölüm 8) |

## 3. Naim'in çevirdiği ciltler (Doğrulanacak)

Bilinen: Miras III. cildin müsveddesini hazırladı ve IV–XII. ciltleri tamamladı (Küre). Buna göre Naim'in payı I–II. ciltler ve belki III. cildin bir kısmıdır. Eski plan ise "Cilt 2-12 Kâmil Mîrâs" yazıyor (`quran-app-docs/11-icerik-edinim/02-telif-analizi.md`); iki bilgi çelişiyor.

Doğrulama listesi:
- [ ] Her cildin künye sayfasında mütercim adı ve baskı yılı.
- [ ] Önsöz ve sonsözlerde çevirinin kimden kime geçtiğine dair ifade.
- [ ] Kütüphane kayıtlarında cilt başına mütercim.
- [ ] Naim'in çevirisinin bittiği hadis numarası.
- [ ] Her cildin yazı türü (Osmanlıca ya da Latin harf) ve ciltlerde Arapça metnin basılı olup olmadığı.
- [ ] Ciltlerde çeviri dışında açıklama ve giriş bölümleri varsa bunların yazarı ve kapsama alınıp alınmayacağı (Açık soru).

Kural: doğrulama bitene kadar III. cilt Miras kısmı sayılır ve `kapali` kalır. Her Türkçe birim `ceviri` alanı taşır: `naim` ya da `miras`. Çapalar buna göre `ht:naim:tecrid:{no}` ya da `ht:miras:tecrid:{no}` olur.

**Yeni bulgular (okuma 27 Ekim 2026; Zebîdî'nin vefat tarihi TDV İA ile doğrulandı, diğerleri Doğrulanacak; kural değişmez).** Hukuki sonuç taşımaz; hukuki görüş değildir. Ayrıntı: [lisans defteri §3.4](./01-kaynaklar-ve-lisans-defteri.md).
- **Naim ve Miras payı.** Hansu'ya göre ([Küre: et-Tecrîdü's-sarîh](https://kureansiklopedi.com/tr/detay/et-tecridus-sarih), 20.11.2024) Naim mukaddimeyle 477 hadisi iki cilt hâlinde yayımladı (İstanbul 1346/1928), III. cildi hazırladı ama yayımlanmadan 1934'te öldü; Kâmil Miras III. cildi gözden geçirip yayımladı. Aynı maddede Naim'in çevirdiği hadis sayısı 589, baskıda görünen 574 olarak geçiyor; fark ve 477 ile ilişki açık. [TDV İA Babanzâde maddesi](https://islamansiklopedisi.org.tr/babanzade-ahmed-naim) "ilk üç cilt"i Naim'e verir. Fark, Miras'ın payının anılıp anılmamasından gelebilir (çıkarım). Yukarıdaki "Miras III. cildin müsveddesini hazırladı" bilgisiyle ([Küre: Miras](https://kureansiklopedi.com/tr/detay/miras-kamil)) Hansu'nun anlatımı uyuşmuyor; ciltlerin künye ve önsözleriyle sınanır (doğrulama listesinin ilk iki maddesi).
- **Türkçe kopyalar.** İTÜ kaydı: 1926–1928, cilt 1–3, "Osmanlıca"; yalnız üst veri görülebiliyor, "Copyright hakları saklıdır". Diyanet ePUB'ı (yayin.diyanet.gov.tr, 1. cilt ISBN 9789751970602) arama özetine göre ücretli, modern bir baskıdır ve Miras ciltlerini de içerir; birincil sayfa açılmadı. Bu metin kullanılmaz; yalnız izinle karşılaştırma tanığı olabilir. Kendi aktarımımız için 1928 ciltlerinin taraması bir kütüphaneden istenir (İ-14).
- **Arapça hazır metinler.** OpenITI ([Zenodo](https://zenodo.org/records/3082463), CC BY-NC-SA 4.0) ve Shamela ("haklar sahiplerinde kalır") kopyaları Risâle 2009 baskısına dayanıyor; zevâid hadisleri ve Buhârî numaraları eklenmiş. OpenITI `kapali`dır; Shamela için kayıt açılmadı. Kendi OCR'ımız için aday: archive.org `AAlexandrina-103522` (Kahire, Hayriyye, 1322/1904); kaynağı Doğrulanacak.
- **Arapça metnin yazarı.** Zebîdî'nin vefatı 893/1488'dir ([TDV İA](https://islamansiklopedisi.org.tr/zebidi-ahmed-b-ahmed)).

## 4. Kütüb-i Sitte Arapça veri seti seçenekleri

| Seçenek | Ne veriyor | Sorun | Hüküm |
|---|---|---|---|
| fawazahmed0/hadith-api | Unlicense; 20 Arapça ve 8 Türkçe koleksiyon ([editions.json](https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions.json)) | README metinlerin kaynağını belgelemiyor; Unlicense yalnız yükleyicinin sahip olduğu şeyi kapsar; numaralandırmanın dayandığı baskı belirsiz | Arapça `bekliyor`, yalnız ekip içi `dev` prototipi; Türkçe `kapali` |
| AhmedBaset/hadith-json | 50.884 hadis, Arapça ve İngilizce, 17 kitap ([README](https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/README.md)) | Sunnah.com'dan kazınmış; lisans dosyası yok | `kapali` |
| Sunnah.com API | "You will need an API key"; "a portion of our data"; çevrimdışı döküm henüz yok ([Sunnah.com](https://sunnah.com/developers)) | Kullanım şartları okunmadı | `bekliyor`; yazılı izin istenir |
| OpenITI hadis metinleri | Geniş külliyat | CC BY-NC-SA 4.0 ([Zenodo](https://zenodo.org/records/3082463)) | `kapali` |
| Kendi sayısallaştırmamız | Serbest basılı nüshalardan OCR | Harekeli Arapça OCR emek ister; baskı seçimi numaralandırma kararına bağlı | Yedek yol |

**Önerilen yol.**
1. Tecrîd'in Arapça metni, ciltlerde basılıysa, serbest ciltlerin kendi taramamızdan alınır. Kaynağı en temiz parça budur.
2. Sunnah.com'a Arapça metin ve numaralandırma eşlemesi için yazılı izin talebi gönderilir.
3. Aynı anda fawazahmed0 bakımcısına Arapça metinlerin kaynağı sorulur ve bir koleksiyonun örneklemi serbest bir basılı nüshayla karşılaştırılır. Kaynak netleşirse lisans defterinde durum güncellenir.
4. İki yol da sonuç vermezse numaralandırma kararında seçilen baskının serbest nüshasından kendi sayısallaştırmamız yapılır.
5. Seçilen kaynak `source` kaydıyla ve `license` sütunuyla izlenir; sorun çıkarsa veri seti yayından önce tek hamlede kapatılabilir (K-27).
6. Üçüncü taraf veri setinden gelen Arapça metin dağıtıldığı hâliyle, NFC uygulanmadan saklanır. Kendi taramamızdan aktarılan metin bizim ürettiğimiz metindir ve ilk kayıtta NFC'ye çevrilir (K-26). HTML, EPUB ya da PDF'ten çıkarılan metin için çıkarılmış metin türü geçerlidir ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme), madde 3; [Çapa şeması](../03-veri/01-capa-semasi.md#7-kanonik-metin-ve-content_hash) §7).

## 5. Numaralandırma kararı: `h:{koleksiyon}:{no}` (Açık soru)

Çapalar hiçbir sürümde yeniden numaralanmaz (K-26). Notlar, yer imleri ve `xref` satırları hadis çapasına bağlanacağı için bu karar ilk hadis çapası bir `internal` derlemeye girmeden verilmelidir.

**Koleksiyon kısa adları (öneri).** `tecrid`, `buhari`, `muslim`, `ebu-davud`, `tirmizi`, `nesai`, `ibn-mace`. Kesin liste [Çapa şeması](../03-veri/01-capa-semasi.md) dosyasında tutulur.

| Seçenek | Açıklama | Artı | Eksi |
|---|---|---|---|
| A. Kaynak baskı numarası | Her koleksiyonda adı belli bir baskının sürekli numarası (baskı seçimi Doğrulanacak) | Basılı atıflarla uyumlu; bir platforma bağlı değil | Dijital metnin bu baskıyla hizalı olması gerekir |
| B. Sunnah.com numarası | Platformun numaralandırması | Çevrimiçi paralel bağlantı kolay; veri bu kaynaktan gelirse doğal uyum | Platform bağımlılığı; lisansı belirsiz; değişebilir |
| C. Kendi sıra numaramız | 1'den başlayan iç numara | Tam denetim | Dışarıda anlamı yok; eşleme tablosu yine gerekir |
| D. Kitap-bâb-hadis bileşik numarası | ör. 2.12.3 | Okunur konum | Gramerdeki tek `{no}` alanına uymaz; gramer değişikliği ister |

**Öneri.** Kütüb-i Sitte için A seçeneği; Tecrîd için basılı Tecrîd numarası (`h:tecrid:{no}`; numaranın ciltler boyunca sürekli olup olmadığı Doğrulanacak). Diğer numara sistemleri eşleme tablosunda tutulur.

> **Uyarı (okuma 27 Ekim 2026).** OpenITI ve Shamela'daki Tecrîd Arapçası Risâle 2009 baskısına dayanıyor; editör Buhârî numaralarını ve 105 zevâid hadisini eklemiş (Doğrulanacak). Bu yüzden o kopyaların numaralandırması basılı Tecrîd numarasından farklı olabilir. `h:tecrid` numaralarıyla örtüşmesi sınanmadan bu numaralar eşleme tablosuna ya da çapaya girmez. OpenITI `kapali` olduğu için ham dosyası alınmaz; sınama serbest bir basılı nüshadan (kendi taramamız) yapılır.

Eşleme tablosu:

```sql
-- Öneri; kesin şema Editoryal veritabanı dosyasında
CREATE TABLE hadis_numara_esleme (
  koleksiyon text NOT NULL,          -- 'buhari'
  sistem     text NOT NULL,          -- 'kaynak-baski', 'sunnah-com', 'tecrid'
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

Kitap › bâb › hadis gezinmesi eski planın hadis okuyucusundan gelir (`quran-app-docs/04-okuma/02-hadis-dual-mode.md`). Karar proje sahibince verilip karar defterine yeni madde olarak eklenir. Pakette ayrı bir `hadis_konum` tablosu yoktur (editoryal adı `hadith_location`, [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) §11); kitap › bâb konumu paketteki `unit` tablosunun genel alanlarıyla taşınır: `parent_path` (içindekiler yolu), `label`, `ord` ve kitap ile bâb numarası ve adı için `attrs` ([İçerik paketleri](../03-veri/03-icerik-paketleri.md) §3.2; öneri).

## 6. Tecrîd numaralarını Buhârî numaralarına eşleme

Amaç: Tecrîd hadisinden Buhârî'deki tam rivayete geçiş, Naim çevirisini Kütüb-i Sitte Arapçasına bağlama ve bağlantı panelinde "aynı hadis" gösterimi.

1. **Basılı gösterge.** Tecrîd ciltleri Buhârî'deki kitap ya da bâb bilgisini veriyorsa ayrıştırılır (Doğrulanacak).
2. **Metin hizalaması.** İki taraf iktibas tespitindeki normalizasyondan geçer: harekeler ve tatvil silinir; أ إ آ ٱ → ا, ى → ي, ة → ه ([İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md)). Buhârî metninden 3–4 kelimelik n-gram ters indeksi kurulur; aday eşleşmeler Smith-Waterman hizalamasıyla genişletilir ve kapsama oranı kaydedilir.
3. **Sıra kısıtı.** Tecrîd'in Buhârî'nin kitap sırasını izlediği doğrulanırsa eşleme dinamik programlamayla sıralı tutulur; sıradan sapan eşleşmeler incelemeye düşer.
4. **Tekrarlar.** Buhârî bir hadisi birden fazla yerde verebilir. Birden fazla aday varsa Tecrîd başlığıyla aynı kitaptaki aday birincil, diğerleri ikincil bağlantı olur.
5. **İnsan onayı.** Her eşleme editör panelinde Arapça metinler yan yana gösterilerek onaylanır.

**Saklama.** Ara çözüm olarak `xref` satırı: `type = 'atif'`, `origin = 'hat'`, `status = 'aday'`, `evidence = {"iliski": "muhtasar-asli", "kapsama": 0.92, "yontem": "hizalama"}`. Bu ilişki için ayrı bir `xref.type` değeri (ör. `paralel`) eklenip eklenmeyeceği Açık soru ([Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md)).

**QA.** Ciltlere göre tabakalı 200 Tecrîd hadisi elle eşlenir ve altın set olur. Birincil eşleme için kesinlik ve duyarlılık raporlanır. Öneri eşiği: otomatik önerilen birincil eşlemelerde kesinlik ≥ 0,98; altına düşerse bütün eşlemeler tek tek onaylanır.

## 7. OCR ihtiyacı

- **Tecrîd.** Türkçe metin ve harekeli Arapça metin aynı sayfadadır. Ciltlerin yazı türü Doğrulanacak; Osmanlıca harfli çıkarsa Elmalılı aktarım kılavuzu kullanılır ([Elmalılı hazırlığı](./03-elmalili-hazirligi.md)). Değerlendirme yöntemi aynıdır: tabakalı örneklem, altın metin, CER. Arapçada temel harf CER'i ile hareke CER'i ayrı ölçülür.
- **`embed_ok`.** Naim ciltlerinin görüntüleri ve metni `embed_ok = true` taşır ve görsel modele gönderilebilir. Miras ciltleri 1 Ocak 2028'e kadar `false`'tur. fawazahmed0 ve Sunnah.com verisi kaynak netleşene kadar `false` kalır; gömülmez ve yapay zekâ servisine gönderilmez ([Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md)).
- **Hadis birimlerine bölme.** Hadis numarası işaretleri bulunur; her numara için Arapça blok ile Türkçe blok eşlenir; `h:tecrid:{no}` ve `ht:naim:tecrid:{no}` birimleri üretilir. Sayfa eşlemesi Elmalılı'daki gibi `page_map` tablosuna birimin kaynağıyla (`source_id`), cilt ve sayfayla yazılır; baskı künyesi kaynağın `baski_bilgisi` alanındadır ([Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md#91-page_map-ayah_box-audio_timing) §9.1).
- **Kütüb-i Sitte.** OCR yalnız kendi sayısallaştırma yolu seçilirse gerekir. Harekeli Arapça için ayrı CER eşiği konur.

```bash
uv run mutalaa ingest scans --edition tecrid-ilk-baski --dir data/gelen/tecrid-ilk-baski/c01 --cilt 1   # baskı künyesi Doğrulanacak
uv run mutalaa ocr run   --edition tecrid-ilk-baski --engine vision --pages c01:1-30
uv run mutalaa ocr eval  --edition tecrid-ilk-baski --gold data/gold/tecrid-ocr/
uv run mutalaa anchor    --source tecrid-naim
uv run mutalaa enrich hadith-map  --from tecrid --to buhari
uv run mutalaa enrich hadith-refs --target elmalili-tefsir
uv run mutalaa qa run    --source tecrid-naim
```

## 8. Sıhhat derecesi etiketleri (sonra)

- v1'de derece etiketi gösterilmez.
- Etiket eklendiğinde her derece adı belli bir kaynağa dayanır: âlim ya da eser, baskı ve sayfa. Farklı görüşler yan yana gösterilir. Uygulama kendi derecesini üretmez; yapay zekâ derece atamaz. Bu kural fetva vermeme ve tarafsızlık ilkelerinden gelir (K-25).
- Eski plan derecesiz hadis yayımlamamayı kural sayıyordu. Bu dosya derecelendirmeyi sonraya bırakıyor. Sünen koleksiyonlarının v1'de nasıl gösterileceği Açık soru: (a) "Derece bilgisi bu sürümde yok" notuyla göstermek, (b) önce yalnız Tecrîd, Buhârî ve Müslim'i açmak, (c) derece politikası hazır olana kadar beklemek.

## 9. Risale ve tefsirde hadis atıflarının tespiti

İki tür atıf vardır: açık kaynak gösterimi ("Buhârî, Îmân 12") ve Arapça hadis metninin alıntılanması.

**Açık atıf ayrıştırıcısı.** Eski planın ayrıştırıcısı bu biçimi zaten tanıyordu (`quran-app-docs/04-okuma/03-risale-i-nur-okuyucu.md`); aşağıdaki sürüm Unicode ve Türkçe harf katlamasıyla çalışır ve konum ofsetlerini korur.

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
- **Bağlantı türleri.** Açık atıf `atif`, metin alıntısı `iktibas`, metinsiz anıştırma `ima` (yalnız küratörlü) olarak `xref` tablosuna girer.
- **Hukuki sınır.** Risale metni üzerinde çalışmak avukat onayı ister ([Risale hazırlığı](./05-risale-hazirligi.md)). Ayrıştırıcı Elmalılı metni (serbest) ve yapay örneklerle geliştirilir. Modern baskılardaki kaynak dipnotları yayınevinin ya da Diyanet'in editoryal eki olabilir ve kopyalanmaz; rapor modern tahkiklerin dipnot ve fihristlerinin ayrıca korunduğunu söylüyor.

## 10. Açık sorular

1. Numaralandırma sistemi (bölüm 5) ve her koleksiyon için kaynak baskı.
2. Naim'in çevirdiği ciltler, Naim'in son hadis numarası ve ciltlerin yazı türü.
3. Ciltlerdeki açıklama ve giriş bölümleri kapsama alınacak mı?
4. Tecrîd ↔ Buhârî ilişkisi için ayrı `xref.type` değeri.
5. Sunnah.com ve fawazahmed0'dan gelecek cevaplar; gelmezse kendi sayısallaştırma takvimi.
6. Sünen koleksiyonlarının derecesiz gösterimi.
7. Hadis metinlerindeki âyet çevirilerinin Kurul ve DİYK kapsamı.

## İlgili dosyalar
- [Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md) · [İçerik hattı](./02-icerik-hatti.md) · [Elmalılı hazırlığı](./03-elmalili-hazirligi.md) · [Risale hazırlığı](./05-risale-hazirligi.md)
- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md)
- [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)
