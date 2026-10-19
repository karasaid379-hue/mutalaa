# Kaynaklar ve Lisans Defteri
> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-03](../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-04](../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-07](../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-19](../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses)

Bu defter, Mütâlaa'ya giren ya da girmesi düşünülen her içerik kaynağının lisans durumunu tutar. Editoryal veritabanındaki her `source` satırı buradaki bir kayıtla aynı kimliği taşır. Yayınlayıcının lisans kapısı yalnız `license_status` ve `kurul_onay` alanlarına bakar ([Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md)). Defterde kaydı olmayan kaynak içerik hattına alınmaz.

> **Hukuki görüş değildir.** Değerlendirmeler Ekim 2026 araştırma raporuna ve bağlantısı verilen birincil sayfalara dayanır. "Açık soru" işaretli hukuki konular yayından önce bir fikri haklar avukatına sorulur. FSEK alıntıları WIPO Lex metnindendir; bu metin 2008'e kadarki değişiklikleri içerir ([FSEK, WIPO Lex](https://www.wipo.int/wipolex/en/text/499171)).

## 1. Durum kodları ve derleme görünürlüğü

| `license_status` | Anlamı | `dev` (yalnız ekip) | `internal` (davetli test) | `public` (mağaza) |
|---|---|---|---|---|
| `serbest` | Koruma süresi dolmuş ya da lisans ücretsiz uygulama dağıtımına izin veriyor; şartlar uygulanıyor | Görünür | Görünür; Kurul kapsamındaki içerik Açık soru | Görünür; Kurul kapsamındaysa yalnız onaylı sürüm |
| `bekliyor` | Serbest bir eserin kaynağı belirsiz dijital kopyası ya da şartları netleşmemiş bir lisans | Görünür | Görünmez | Görünmez |
| `ic_kullanim` | Hak sahibinin izni ya da avukat görüşü ekip içi kullanıma izin veriyor, dağıtıma vermiyor | Görünür | Görünmez | Görünmez |
| `kapali` | Hiçbir derlemeye girmez; ham verisi hatta alınmaz | Görünmez | Görünmez | Görünmez |

K-06 güncellemesine (18 Ekim 2026) göre `internal` derlemeler davetli test kullanıcılarına gittiği için yalnız `serbest` içerik görür; dış test kullanıcılarına dağıtım çoğaltma ve yayma sayılabilir. Kurul onayı bekleyen Kur'an metni, meal ve sesin kapalı testte gösterilip gösterilemeyeceği Kurul'a sorulur; cevap gelene kadar dış test kullanıcısı alınmaz.

**İç kullanım kuralı.** Koruma süresi dolmamış bir eserin metni, sesi ya da görseli (Risale-i Nur, Kâmil Miras ciltleri, modern mealler, hafız kayıtları) hak sahibinin yazılı izni ya da avukat görüşü olmadan indirilmez, hatta işlenmez, yapay zekâ servisine gönderilmez ve geliştirme derlemesine konmaz. Bu kaynaklar o güne kadar `kapali` kalır ve `embed_ok = false` taşır. Olumlu görüş gelirse en fazla `ic_kullanim` olurlar ve yalnız ekip içi `dev` derlemelerinde görünürler. Ekip içi işlemenin (dizin üretimi dahil) hukuki uygunluğu da hukukçuya danışılır (K-05).

**Çözüldü (19 Ekim 2026): Editoryal veritabanı ile fark.** [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md#3-source) §3 ve §11 artık bu defterle aynı değerleri verir: `risale-asil-nusha` ve `tecrid-miras` iç kullanım kuralı gereği avukat görüşüne ya da serbest kalma tarihine kadar `kapali`dır.

**Kurul alanı.** Kur'an metni, meal ve ses kaynakları `kurul_onay` alanında onay numarasını ve onaylı içerik sürümünü taşır. 633 sayılı Kanun m. 6'ya göre Kurul onayı olmayan "sesli, görüntülü ve elektronik ortamda hazırlanan Kur'an-ı Kerimler basılamaz ve yayımlanamaz" ([Lexpera, 633](https://www.lexpera.com.tr/mevzuat/kanunlar/diyanet-isleri-baskanligi-kurulus-ve-gorevleri-hakkinda-kanun-633)). 2022 yönetmeliğine göre onaylanmış eserin içeriği değiştirilemez ([Memurlar.net](https://www.memurlar.net/haber/1045766/kur-an-i-kerim-basim-ve-yayim-kriterleri-hakkinda-yonetmelik-resmi-gazete-de-yayimlandi.html)). Başvuru usulü, ücret ve süre bilinmiyor (Açık soru). Paket manifesti paket başına `kurul_gerekli` bilgisi taşır (K-06 uygulama notu); bu değer paketteki kaynakların Kurul kapsamından türetilir.

**`embed_ok` alanı.** Kaynağın metninin gömme (embedding) vektörüne çevrilip çevrilemeyeceğini ve harici bir yapay zekâ API'sine gönderilip gönderilemeyeceğini söyler. Varsayılan `false`'tur; kaynak kartındaki dayanakla `true` yapılır. Korumalı metinler (Risale-i Nur, Kâmil Miras ciltleri) hukuki onay olmadan `false` kalır. Quran Foundation içeriği `false`'tur, çünkü QF şartları içerikten türetilen gömmeleri de aynı kısıtlara bağlıyor ([QF Developer Terms](https://api-docs.quran.foundation/legal/developer-terms/)). İçerik hattı bu alana uyar ([İçerik hattı](./02-icerik-hatti.md)). Tablodaki "Uygulanmaz" değeri metin taşımayan kaynaklar (fontlar) içindir.

**Veri setleri de kapıdan geçer.** K-06 uygulama notuna göre QAC kaynaklı kök ve lemma verisi `core` paketinden ayrı bir pakette, kendi lisans durumuyla tutulur. Bu dosyada önerilen paket adı `kelime-kok`'tur; QAC'den yazılı açıklık gelene kadar `bekliyor` durumundadır ve bu sürede yalnız ekip içi `dev` derlemelerinde görünür.

## 2. Özet tablo

| Kimlik | Kaynak | `license_status` | `embed_ok` | Kurul | Hüküm |
|---|---|---|---|---|---|
| `tanzil-uthmani` | Tanzil Kur'an metni, Uthmani | `serbest` | Evet (çıkarım) | Evet | Kullan |
| `tanzil-simple-clean` | Tanzil Kur'an metni, Simple Clean | `serbest` | Evet (çıkarım) | Evet | Kullan (arama tabanı) |
| `kfgqpc-hafs-font` | KFGQPC Uthmanic Hafs fontu | `bekliyor` | Uygulanmaz | Dolaylı | Yazılı izin; yedek Amiri Quran |
| `qpc-v1-font`, `qpc-v2-font`, `qpc-v4-font` | QPC sayfa fontları | `bekliyor` | Uygulanmaz | Evet | QF şartlarıyla |
| `medine-604-duzen` | Mushaf A sayfa düzeni ve kelime-glif eşlemesi | `bekliyor` | Hayır (QF şartı) | Evet | Kaynak seçimi Açık soru |
| `amiri-quran-font` | Amiri Quran | `serbest` | Uygulanmaz | Dolaylı | Kullan (Mushaf C) |
| `qac-morfoloji` | Quranic Arabic Corpus v0.4 | `bekliyor` | Evet, yalnız etiket alanları (çıkarım) | Gerekmez (çıkarım) | Ayrı paket (`kelime-kok`); QAC'den yazılı açıklama |
| `qul-*` | QUL veri setleri | `bekliyor` (kaynak başına) | Kaynağa göre; varsayılan Hayır | Kaynağa göre | Kaynak başına teyit |
| `elmalili-meal`, `elmalili-tefsir` | Hak Dini Kur'an Dili, özgün baskı (baskı kimliği `elmalili-1935`) | `serbest` | Evet | Meal evet; tefsir Açık soru | Kendi aktarımımız |
| `tefsir-quranpedia` | Quranpedia klasik Arapça tefsirler | `serbest` | Evet (çıkarım) | Açık soru | Sonra (K-03) |
| `tecrid-ar` | Tecrîd-i Sarîh Arapça metni | `serbest` | Evet | Gerekmez (çıkarım) | Serbest ciltlerden |
| `tecrid-naim` | Tecrîd-i Sarîh, Ahmed Naim Türkçesi | `serbest` | Evet | Gerekmez (çıkarım) | Kullan |
| `tecrid-miras` | Tecrîd-i Sarîh, Kâmil Miras ciltleri | `kapali` (1 Ocak 2028'de `serbest`) | Hayır (2028'e kadar) | Gerekmez (çıkarım) | 2028'i bekle |
| `hadis-fawaz-ar` | fawazahmed0/hadith-api, Arapça | `bekliyor` | Hayır | Gerekmez | Yalnız prototip |
| `hadis-sunnah-api` | Sunnah.com API | `bekliyor` | Hayır | Gerekmez | Yazılı izin iste |
| `risale-1956-1960` | Risale-i Nur, müellif tashihli 1956–1960 baskıları | `kapali` (1 Ocak 2031) | Hayır (hukuki onay olmadan) | Gerekmez (çıkarım) | 2031 temel metni |
| `risale-asil-nusha` | Diyanet "asıl nüsha" | `kapali` | Hayır | Gerekmez | 2031'den sonra yalnız karşılaştırma |
| `risale-atif-dizini` | Risale âyet atıf dizini (metinsiz: âyet ↔ Risale yeri, baskı sayfası) | `kapali` (metinle birlikte, hukukçu görüşüne kadar; K-05) | Hayır (hukuki onay olmadan) | Gerekmez (çıkarım) | Hukukçu görüşü; üretimi metnin işlenmesini gerektirir |
| `risale-kelime-frekans` | Kelime-Frekans deposu, sıklık sütunları | `serbest` | Evet (kelime ve sıklık) | Gerekmez | Sıklık kullan, anlam kullanma |
| `lugat-redhouse-1890` | Redhouse, A Turkish and English Lexicon | `serbest` | Evet | Gerekmez | Kullan |
| `lugat-kamus-i-turki`, `lugat-naci` | Kâmûs-ı Türkî, Lugat-ı Nâci | `bekliyor` | Hayır (Doğrulanacak) | Gerekmez | Doğrulanacak |
| `ses-everyayah`, `ses-quranicaudio` | Âyet ses dosyaları | `kapali` | Hayır | Evet | Hafız başına yazılı izin |
| `ses-qf-api` | Quran Foundation ses API'si | `bekliyor` | Hayır (QF şartı) | Evet | Akış için QF şartlarıyla |
| `ses-turk-hafiz-*` | Türk hafızlar | `kapali` | Hayır | Evet | Doğrudan görüşme |
| `ses-kfgqpc-meal` | KFGQPC sesli meal çevirileri | `bekliyor` | Hayır (Doğrulanacak) | Evet (çıkarım) | Türkçe sürüm Doğrulanacak |
| `quran-align` | quran-align kelime zamanlamaları | `serbest` | Evet | Ses paketiyle | Eşleştiği dosyalarla |
| `kaikki-tr` | Wiktionary / kaikki dökümleri | `bekliyor` | Evet (çıkarım) | Gerekmez | Lisans teyidi |
| `mushaf-b-*` | Türk hattı sayfa görselleri | `kapali` | Hayır | Evet | Lisans gelince |

## 3. Kaynak kartları

Kartlar özet tablodaki hükmün dayanağını, zorunlu atfı ve açık soruları verir.

### 3.1 Kur'an metni, fontlar ve mushaf düzeni

**`tanzil-uthmani`, `tanzil-simple-clean` · Tanzil.** Başlık "License: Creative Commons Attribution 3.0". Şartlar: "Permission is granted to copy and distribute verbatim copies of this text, but CHANGING IT IS NOT ALLOWED."; kaynak "clearly indicated" olmalı ve "a link is made to tanzil.net" şartı var; bildirim türetilmiş dosyalarda da korunur ([OpenITI kopyası](https://raw.githubusercontent.com/OpenITI/0025AH/master/data/0001Quran/0001Quran.Mushaf/0001Quran.Mushaf.Tanzil001-ara1.mARkdown)). Metin kadimdir, süre hesabı uygulanmaz (çıkarım). Kurul: evet.
- **Atıf:** "Kur'an metni: Tanzil Project, tanzil.net. Metin değiştirilmeden kullanılmıştır." Pakete Tanzil'in İngilizce bildirimi aynen konur.
- **Not:** Metin düzeltilmez. Tanzil'den türetilip değiştirilmiş metinler (ör. quranacademy/quran-text) kullanılmaz ([README](https://raw.githubusercontent.com/quranacademy/quran-text/master/README.md)). Simple Clean sürümünü arama tabanı almak değişiklik sorusunu küçültür (rapor çıkarımı).
- **Saklama:** Metin dağıtıldığı hâliyle, bayt bayt saklanır; NFC bile uygulanmaz, çünkü NFC şedde ile harekenin sırasını değiştirir (K-26). Arama için normalize metin ayrı sütunda tutulur ([İçerik hattı](./02-icerik-hatti.md)).
- **Açık soru:** Şartlar canlı tanzil.net sayfasından okunmadı. Ayrı sütundaki normalize `search_text` "değiştirme" sayılır mı? Tanzil'e bilgi için sorulur. Uthmani dosyasının sürüm numarası Doğrulanacak.

**`kfgqpc-hafs-font`.** v0.09 EULA: "Permission is hereby granted, Free of Cost, ... the rights to Use, Copy, Distribute"; koşul: "The Font Software cannot be Sold, Modified, Altered, Translated ...". Telif alanı: "may not be reproduced, modified without the express written approval of King Fahd Glorious Quran Printing Complex" ([font dosyası](https://raw.githubusercontent.com/mustafa0x/qpc-fonts/f93bf5f3/various-woff2/UthmanicHafs1%20Ver09.woff2)). Kurul: dolaylı; basılı mushafta "Kurul'un uygun gördüğü yazı tipleri" şartı var ([Cumhuriyet](https://www.cumhuriyet.com.tr/turkiye/resmi-gazetede-yayimlandi-diyanetten-kuran-karari-1998786)), dijitaldeki karşılığı Açık soru.
- **Atıf:** "KFGQPC Uthmanic Script HAFS © King Fahd Glorious Qur'an Printing Complex." EULA metni Ayarlar › Kaynaklar ve lisanslar ekranında.
- **Not:** Alt kümeleme (subsetting) değişiklik sayılabileceği için yapılmaz. Resmî lisans sayfası (dm.qurancomplex.gov.sa/copyright-2/) ve yeni sürümlerin lisansı okunmadı.

**`qpc-v1-font`, `qpc-v2-font`, `qpc-v4-font`, `medine-604-duzen` · QPC fontları ve düzen verisi.** Font meta verisi "King Fahad Complex, All rights reserved." diyor, kullanım hakkı tanımıyor ([QCF_P001](https://raw.githubusercontent.com/mustafa0x/qpc-fonts/f93bf5f3/mushaf-woff2/QCF_P001.woff2)). Woff2 boyutları V2 93,2 MB, V1 45,7 MB, V4 48,5 MB ([Quran.com font klasörü](https://github.com/quran/quran.com-frontend-next/tree/production/public/fonts/quran/hafs)). QF geliştirici şartlarına (son güncelleme 11 Ekim 2026) göre geliştirici "maintains an active account in the Developer Console" ve QF'ye "in a reasonably accessible place" atıf yaparsa fontlar uygulamaya gömülebilir; uygulama dışında dağıtılamaz. Düzen verisi QF API'den gelirse "QF Content" sayılır: "longer than 1 week" önbellek yasak, çevrimdışı kopya yalnız Content Sync ile ve bu istisna "does not itself authorize distributing a prepackaged database or build-time bundle of QF Content". Şartlar New York hukukuna bağlıdır ve "30 days' notice" ile feshedilebilir ([QF Developer Terms](https://api-docs.quran.foundation/legal/developer-terms/)). QUL 31 düzen listeliyor, hiçbiri Türk düzeni değil ve lisans alanı yok ([QUL düzenleri](https://qul.tarteel.ai/mushaf_layouts)). Kurul: evet; Medine düzenli fontların kabulü Açık soru.
- **Atıf:** "Mushaf sayfa fontları: King Fahd Glorious Qur'an Printing Complex; Quran Foundation aracılığıyla." QF'nin istediği kesin ifade Doğrulanacak.
- **Açık soru:** Fontların kendi depomuzdan cüz paketi (`mushaf-a-cuz-{01..30}`) olarak indirilmesi "gömme" sayılır mı? Düzen verisi QF Content Sync, QUL ya da KFGQPC izninden hangisiyle alınacak? Bunlar çözülmeden Mushaf A çevrimdışı paketi yayına çıkmaz.

**`amiri-quran-font`.** SIL Open Font License; test edilen 65 Kur'an kod noktasının 53'ünü içeriyor, Türkçe Latin harfi yok ([google/fonts](https://github.com/google/fonts/tree/main/ofl/amiriquran)).
- **Atıf:** "Amiri Quran, SIL Open Font License." OFL metni uygulamada yer alır.
- **Not:** Eksik kod noktalarında yedek font davranışı test edilir. Alt kümelemede OFL'nin ayrılmış font adı koşulu Doğrulanacak.

### 3.2 Morfoloji ve QUL

**`qac-morfoloji`.** 77.429 kelime, yaklaşık %99 doğruluk ([QAC SSS](https://corpus.quran.com/faq.jsp)). İndirme sayfası GNU GPL diyor: "Permission is granted to copy and distribute verbatim copies of this file, but CHANGING IT IS NOT ALLOWED."; veri "in any website or application" kaynak gösterilip corpus.quran.com'a bağlantı verilerek kullanılabilir ([QAC indirme](https://corpus.quran.com/download/)). SSS ise "You do not use the data for commercial purposes" şartını koyuyor. İki metin çelişiyor.
- **Atıf:** "Morfoloji: Quranic Arabic Corpus (corpus.quran.com), GNU GPL." Bağlantıyla.
- **Not:** Dosya değiştirilmez; düzeltmeler ayrı katmanda tutulur ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)).
- **Paket:** `kelime-kok` (bölüm 1); `bekliyor` kaldıkça yalnız `dev` derlemelerinde görünür. Kendi Türkçe anlamlarımız bizimdir ama kelimeye QAC lemma eşlemesiyle bağlandığı için aynı pakete girer; yedek yol [Kelime anlamları](./06-kelime-anlamlari.md) dosyasında.
- **`embed_ok`:** İstemlere yalnız lemma, kök ve sözcük türü etiketleri girer (çıkarım). QAC'nin cevabı bunu kısıtlarsa istemler etiketsiz çalışır.
- **Açık soru:** GPL verinin uygulama paketinde dağıtılmasının uygulama koduna etkisi avukata sorulur.

**`qul-*`.** Kod MIT. SSS: "Yes, you can use QUL data in commercial projects. However, please review the licensing terms for each resource." İncelenen kaynak sayfalarında lisans alanı yok ([QUL SSS](https://qul.tarteel.ai/faq); [QUL lemma](https://qul.tarteel.ai/resources/morphology/75)). Tematik konu başlıkları "Clear Quran" çevirisinden geliyor ve telifli olabilir ([QUL konular](https://qul.tarteel.ai/resources/ayah-topics/45)). Her kaynak ayrı kimlik alır (ör. `qul-lemma-75`, `qul-benzer-ayet`). Atıf QUL'a ve özgün yazara yapılır ([QUL krediler](https://qul.tarteel.ai/credits)).

### 3.3 Meal ve tefsir

**`elmalili-meal`, `elmalili-tefsir` · Hak Dini Kur'an Dili, özgün baskı.** Taramalar ve sayfa eşlemesi baskı kimliği `elmalili-1935` ile tutulur. "1935-1939 yıllarında İstanbul'da dokuz cilt ve 10.000 takım olarak basılmış" ([Küre](https://kureansiklopedi.com/tr/detay/hak-dini-kuran-dili-2)). Princeton kaydı: 8 cilt, 6.442 sayfa, [1935–1938], Matbaai Ebüzziya, "T. C. Diyanet işleri reisliği neşriyatından, no. 5" ([kayıt](https://catalog.princeton.edu/catalog/SCSB-3946972)); fihrist cildi 1939 ([kayıt](https://catalog.princeton.edu/catalog/SCSB-4322432)). Müellif 1942'de vefat etti; eser 1 Ocak 2013'ten beri serbest ([MKÜ kaydı](https://openaccess.mku.edu.tr/items/1b02bae2-408d-43ea-920d-6c26605c442a)). Sadeleştirilmiş baskılar FSEK m. 6 anlamında işlenme eseridir. Kanun "alelade transkripsiyonları" işlenme saymıyor (m. 6/8); düz bir aktarımın yeni hak doğurmadığı bu yüzden savunulabilir (çıkarım). Kurul: meal için evet; meal Arapça metinle gösterildiğinde "mealli mushaf" sayılır (633 m. 6) ve meal yayınları Din İşleri Yüksek Kurulu incelemesine açıktır (m. 5/ı). Tefsir için Kurul kapsamı Açık soru.
- **Atıf:** "Elmalılı Muhammed Hamdi Yazır, Hak Dini Kur'an Dili, İstanbul 1935–1939. Metin özgün baskıdan Mütâlaa tarafından aktarılmıştır. Aktarım sürümü {sürüm}."
- **Açık soru:** Tarama kaynağı Doğrulanacak. Yazı türü: K-03 düzeltmesine göre büyük olasılıkla Latin harfli (Princeton kaydı dili Türkçe olarak ve künyeyi Latin imlâsıyla veriyor; baskı 1928 harf devriminden sonra); bir tarama üzerinde Doğrulanacak. Eserin Diyanet sözleşmesiyle yazılmasının hak durumuna etkisi avukata teyit ettirilir. Aktarımımızın lisansı ([Elmalılı hazırlığı](./03-elmalili-hazirligi.md)).

**`tefsir-quranpedia` (sonra).** Veri lisansı (sürüm 2026-10-14) uygulamalarda kullanımı serbest bırakır ve bu kullanım için atıf istemez; indirilebilir veri tabanı olarak yeniden yayımlamada bağlantılı atıf ve döküm sürümü ister. Kur'an metni ve klasik tefsirler için "no one claims ownership of them" der; çeviriler ve çağdaş eserler sahiplerinde kalır ([Quranpedia LICENSE](https://quranpedia.net/dumps/LICENSE.md)). İndirilebilir paketlerimizde atıf zorunlu kabul edilir: "Arapça tefsir metni: Quranpedia.net, döküm sürümü {sürüm}." Modern tahkiklerin dipnot, giriş ve fihristleri ayıklanır.

### 3.4 Hadis

**`tecrid-ar`, `tecrid-naim`, `tecrid-miras`.** Babanzâde Ahmed Naim 13 Ağustos 1934'te vefat etti; çevirdiği kısım 1 Ocak 2005'ten beri serbest. Kâmil Miras III. cildin müsveddesini hazırladı, IV–XII. ciltleri (İstanbul 1938–1948) tamamladı ve 30 Nisan 1957'de vefat etti; ciltleri 1 Ocak 2028'de serbest kalır ([Küre: Miras](https://kureansiklopedi.com/tr/detay/miras-kamil)). Arapça metin yaşı itibarıyla serbesttir. Naim'in çevirdiği ciltler Doğrulanacak; o zamana kadar III. cilt Miras kısmı sayılır ve 2028'e kadar hatta alınmaz. Sonraki baskılardaki sadeleştirme ve editoryal ekler kullanılmaz.
- **Atıf:** "Tecrîd-i Sarîh Tercümesi, mütercim Babanzâde Ahmed Naim. Özgün baskıdan Mütâlaa tarafından aktarılmıştır."

**`hadis-fawaz-ar`, `hadis-sunnah-api`.** fawazahmed0/hadith-api Unlicense ile 20 Arapça ve 8 Türkçe koleksiyon dağıtıyor; README metinlerin kaynağını belgelemiyor ([editions.json](https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions.json); [LICENSE](https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/LICENSE)). Unlicense yalnız yükleyicinin sahip olduğu şeyi kapsar. Sunnah.com: "You will need an API key to access this data"; "Our API offers access to a portion of our data"; kullanım şartları okunmadı ([Sunnah.com](https://sunnah.com/developers)). Seçim yolu [Hadis hazırlığı](./04-hadis-hazirligi.md) dosyasında.

### 3.5 Risale-i Nur

**`risale-1956-1960`, `risale-asil-nusha`, `risale-kelime-frekans`.** Said Nursî 1960'ta vefat etti; Külliyat 1 Ocak 2031'de serbest kalır ([TDV İA](https://islamansiklopedisi.org.tr/risale-i-nur-kulliyati)). Hakları bugün kimin kullandığı belirsiz: 2014 Bakanlar Kurulu kararının dayandığı hükmü Anayasa Mahkemesi 11 Haziran 2015'te iptal etti ve 2016–2026 için hak sahibini gösteren kaynak bulunamadı ([T24](https://t24.com.tr/haber/aym-risale-i-nur-yasagini-iptal-etti,299364); [AYM K.2015/45](https://normkararlarbilgibankasi.anayasa.gov.tr/Dosyalar/Kararlar/KararPDF/2015-45-nrm.pdf)). Asıl nüsha 1956–1960 baskılarını esas alıyor ve 2015 başından beri basılıyor ([README](https://raw.githubusercontent.com/alitekdemir/Risale-i-Nur-Diyanet/master/README.md)); 2031'den sonra yalnız karşılaştırma metnidir, Diyanet'in eklediği notlar ayrıca korunabilir. Kelime-Frekans deposunun LICENSE dosyası CC0 1.0'dır; README "Çünkü sayfa altındaki kelime listesine erisale.com gibi sitelerden derledik." diyor ([depo](https://github.com/alitekdemir/Risale-i-Nur-Kelime-Frekans)). Bu depodan yalnız kelime ve sıklık sütunları alınır.
- **Açık soru:** Derlemelerde başka yazarların ya da mütercimlerin kısımları varsa süreleri kendi ölüm yıllarına göre işler (Doğrulanacak; [Risale hazırlığı](./05-risale-hazirligi.md)).

### 3.6 Lügat

**`lugat-redhouse-1890`.** Redhouse (1811–1892), *A Turkish and English Lexicon*, 1890; HathiTrust'ta iki parça hâlinde tam görünüm ([HathiTrust](https://catalog.hathitrust.org/Record/001771732); [Online Books](https://onlinebooks.library.upenn.edu/webbin/who/Redhouse%2c%20James%20W%2e%20%28James%20William%29%2c%20Sir%2c%201811%2d1892)). Türkçe tanımları biz yazarız. Tarama sağlayıcısının kullanım bildirimi okunur (Doğrulanacak). Kâmûs-ı Türkî ve Lugat-ı Nâci'nin durumu ve dijital erişimi Doğrulanacak.

### 3.7 Ses ve zamanlama

**`ses-everyayah`, `ses-quranicaudio`, `ses-turk-hafiz-*`.** Açık lisans yok. AlQuran Cloud: "All audio files used on this website and third party libraries own and retain their respective copyrights."; okuyucular "may ask you to remove the conent [sic]" ([AlQuran Cloud](https://alquran.cloud/terms-and-conditions)). Moderatör: "the copyright still remains with the reciter" ([Islamic Network](https://community.islamic.network/d/231-clarification-on-licensing-and-usage-rights-for-quran-recitation-api)). Türk hafızlar için açık kaynak yok; Osman Şahin ve İshak Danış gibi hafızlarla doğrudan görüşülür (rapor).

**`ses-qf-api`.** Âyet zaman damgaları ve isteğe bağlı kelime segmentleri verir; kimlik bilgileri arka uçta kalır ([QF ses](https://api-docs.quran.foundation/docs/sdk/audio/)). Akış serbest, çevrimdışı kopya yalnız Content Sync ile. Geliştirmedeki ses denemeleri bu yoldan yapılır; `ses-{hafiz}` paketleri bu kaynaktan üretilmez.

**`ses-kfgqpc-meal`.** "free general use in computer apps, broadcasting channels, internet websites" ([KFGQPC](https://qurancomplex.gov.sa/en/?p=4973)). Sayfa dil listesi vermiyor; Türkçe sürüm Doğrulanacak.

**`quran-align`.** "These data files are licensed under a Creative Commons Attribution 4.0 International License"; kod MIT. Kelimeler Tanzil `quran-uthmani.txt` üzerinden bölünmüş; ortalama sapma 73 ms altında, kelimelerin %98,5–99,9'u hizalı; yalnız hizalandığı EveryAyah dosyaları için geçerli ([README](https://raw.githubusercontent.com/cpfair/quran-align/master/README.md)).
- **Atıf:** "Kelime zamanlamaları: Collin Fair, quran-align, CC BY 4.0." Bağlantı ve değişiklik notuyla.

### 3.8 Diğer

**`kaikki-tr`.** kaikki lisans belirtmiyor; Ylonen (LREC 2022) atfı ve kaikki.org bağlantısı istiyor ([kaikki](https://kaikki.org/dictionary/rawdata.html)). Wiktionary metninin CC BY-SA olduğu düşünülüyor, birincil kaynaktan doğrulanmadı.

**`mushaf-b-*`.** Modern mushafların hattı ve tezhibi FSEK m. 4 ile korunur. Telifsiz Osmanlı mushaflarında (Kayışzâde ö. 1894, Hasan Rıza ö. 1920) tutan kütüphanenin kullanım şartı okunur ([Küre: âyet berkenar](https://kureansiklopedi.com/tr/detay/ayet-berkenar-a2f19)).

## 4. Kullanılmayacak kaynaklar (`kapali`)

| Kaynak | Gerekçe |
|---|---|
| alitekdemir/Risale-i-Nur-Diyanet | Metin "risaleinur.hizmetvakfi.org adresinden indirilmiştir"; CC BY-ND 4.0 ifadesi yalnız README'de ve yükleyici hak sahibi değil ([README](https://raw.githubusercontent.com/alitekdemir/Risale-i-Nur-Diyanet/master/README.md); [Risale hazırlığı](./05-risale-hazirligi.md)) |
| Tanzil çeviri dosyaları, Elmalılı dahil | "for non-commercial purposes only"; Elmalılı metninin baskı esası doğrulanmadı ([OPUS](https://opus.nlpl.eu/Tanzil/corpus/version/Tanzil)) |
| "Elmalılı sadeleştirilmiş" | Sadeleştirme işlenme eseridir ([editions.json](https://raw.githubusercontent.com/fawazahmed0/quran-api/1/editions.json)) |
| Diyanet ve Diyanet Vakfı mealleri (QUL #148 dahil), modern mealler, QuranEnc | Korunuyor; Diyanet için kamuya açık lisans yolu bulunamadı; QuranEnc "All Copyrights Reserved" ([QuranEnc](https://quran.islamcontent.com/en/turkish_shaban/112)) |
| Çantay meali; Bilmen meal-tefsiri | 1 Ocak 2035; 1 Ocak 2042 ([Küre: Çantay](https://kureansiklopedi.com/tr/detay/cantay-hasan-basri); [Küre: Bilmen](https://kureansiklopedi.com/tr/detay/bilmen-omer-nasuhi)) |
| QuranWBW; hablullah/data-quran | "copying them is not allowed"; CC BY-NC-ND 4.0 ([QuranWBW](https://legacy.quranwbw.com/2); [GitHub](https://github.com/hablullah/data-quran)) |
| OpenITI | CC BY-NC-SA 4.0; bağış ya da ileride ücretli katman olan üründe kullanılmaz ([Zenodo](https://zenodo.org/records/3082463)) |
| AhmedBaset/hadith-json; fawazahmed0 Türkçe hadisleri | Sunnah.com'dan kazınmış, lisans dosyası yok ([README](https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/README.md)); Türkçe metinlerin kaynağı belgelenmemiş |
| erisale.com ve yayınevi lügatleri; Kelime-Frekans `anlam` sütunu | Korunan derlemeler |
| Modern Diyanet ya da özel mushaf taramaları | Hat ve tezhip FSEK m. 4 ile korunuyor |

Bu kaynakların hepsinde `embed_ok = false` geçerlidir.

## 5. Eski plandaki lisans iddialarının düzeltmesi

Kaynak: `quran-app-docs/11-icerik-edinim/01-veri-kaynaklari.md`, `02-telif-analizi.md`, `quran-app-docs/04-okuma/03-risale-i-nur-okuyucu.md`.

| Eski iddia | Düzeltme |
|---|---|
| Tanzil "CC BY-ND 3.0" | Başlık CC BY 3.0; ayrıca "değiştirmek yasak" şartı ve tanzil.net bağlantısı |
| Risale deposu "lisans açık, hukuken güvenli" | Geçersiz; okuyucu dokümanındaki "üretimden önce yazılı izin alın" uyarısı doğru |
| Kelime-Frekans "CC BY-ND 4.0" | LICENSE dosyası CC0 1.0; anlam sütunu lügatlerden derlenmiş |
| Manevi haklar "süresiz" (m. 16) | m. 19 mirasçılara 70 yıl veriyor; Bakanlık yetkisinin süresi belirtilmemiş. Pratik sonuç aynı: metin kelimesi kelimesine korunur |
| hadith-json "açık"; everyayah "Free distribution" | Lisans dosyası yok; açık lisans yok, telif okuyucuda |
| Tecrîd: Naim 1942, Miras 22 Eylül 1957, "PD olabilir" | Naim ö. 13 Ağustos 1934 (serbest); Miras ö. 30 Nisan 1957 (Küre). Serbest kalma tarihi iki tarihte de 1 Ocak 2028 |
| Hadis Türkçesi için yapay zekâ çevirisi | K-04 ile Naim ve Miras çevirileri seçildi |
| "Lane's Lexicon (Hans Wehr)" | İki ayrı sözlük karıştırılmış; Lane'in durumu Doğrulanacak |

## 6. Telif takvimi

FSEK m. 27: "Koruma süresi eser sahibinin yaşadığı müddetçe ve ölümünden itibaren 70 yıl devam eder." m. 26: süre "eser sahibinin öldüğü seneyi takip eden yılın ilk günü" başlar. Eser ölüm yılı + 71'inci yılın 1 Ocak'ında serbest kalır. Kural mütercim ve sadeleştiren için ayrıca işler.

| Tarih | Olay | Kaynak | Hazırlık |
|---|---|---|---|
| 1 Ocak 2005 | Ahmed Naim (ö. 1934) | `tecrid-naim` | Şimdi işlenir |
| 1 Ocak 2013 | Elmalılı (ö. 1942) | `elmalili-meal`, `elmalili-tefsir` | Şimdi işlenir |
| 1 Ocak 2028 | Kâmil Miras (ö. 30 Nisan 1957) | `tecrid-miras` | 2027'nin son çeyreğinde tarama planı ve araçlar hazır |
| 1 Ocak 2031 | Said Nursî (ö. 1960) | `risale-1956-1960` | 2030'un son çeyreğinde son hukuki kontrol |
| 1 Ocak 2035 | Hasan Basri Çantay (ö. 3 Aralık 1964) | Çantay meali | Sonra yapılacaklar |
| 1 Ocak 2042 | Ömer Nasuhi Bilmen (ö. 12 Ekim 1971) | Meal-tefsir, Hikmet Goncaları | Sonra yapılacaklar |

Zaten serbest olup sonraki fazda düşünülenler: Kısas-ı Enbiyâ özgün metni (Ahmed Cevdet Paşa ö. 1895; Mahir İz'in 1973 sadeleştirmesi korunuyor) ve Süleyman Çelebi'nin Mevlid'i (ö. 1422; tenkitli neşirlerin kurduğu metin işlenme sayılabilir) ([KTB](https://www.ktb.gov.tr/EN-118064/ahmed-cevdet-pasa.html); [TDV İA](https://islamansiklopedisi.org.tr/mevlid--suleyman-celebi)).

**Şart takibi.** QF şartları çeyrekte bir ve her `public` sürümden önce okunur (11 Ekim 2026'da güncellendi, 30 gün bildirimle feshedilebilir). Quranpedia lisansı sürümlüdür, her döküm indirmesinde okunur. Tanzil güncellemeleri her indirmede tanzil.net/updates sayfasından kontrol edilir. QAC'nin çelişkili metinleri yazılı cevap gelene kadar her sürümde yeniden okunur.

## 7. Yeni kaynak kontrol listesi (lisans hijyeni)

```mermaid
flowchart TD
  A[Kaynak önerisi] --> B[pipeline/sources/kimlik.toml açılır]
  B --> C{Eserin koruma süresi doldu mu?}
  C -- Hayır --> D{Hak sahibinin yazılı izni var mı?}
  D -- Hayır --> K[kapali]
  D -- Evet --> E[İznin kapsamı okunur] --> P[ic_kullanim ya da serbest]
  C -- Evet --> F{Dijital kopyanın kaynağı ve lisansı belli mi?}
  F -- Hayır --> G[bekliyor: kaynağı araştır ya da kendi kopyanı üret]
  F -- Evet --> H{NC, ND, değiştirme, önbellek ya da gömme kısıtı var mı?}
  H -- Evet --> I[Kısıtı uygula ya da kapali]
  H -- Hayır --> J{Arapça Kur'an metni, meal ya da ses var mı?}
  J -- Evet --> L[serbest + kurul_onay bekleniyor]
  J -- Hayır --> M[serbest]
```

- [ ] Kaynak kimliği seçildi; `pipeline/sources/{kimlik}.toml` açıldı. Başlangıç durumu `bekliyor`, korumalı eserde `kapali`.
- [ ] Yazar, mütercim, sadeleştiren ve derleyicinin ölüm tarihleri kaynak bağlantısıyla yazıldı; FSEK m. 26–27 hesabı yapıldı.
- [ ] Kullanılacak baskı belirlendi; sadeleştirme, çeviri, tahkik dipnotu ve editoryal ek ayıklandı.
- [ ] Lisans metni canlı sayfadan ve dosya içinden okundu; tarihli kopyası `pipeline/sources/licenses/{kimlik}-{YYYY-MM-DD}.txt` olarak saklandı, SHA-256'sı kaydedildi.
- [ ] Yükleyicinin hak sahibi olup olmadığı kontrol edildi.
- [ ] NC, ND, "değiştirmek yasak", önbellek, çevrimdışı, gömme (embedding) ve alt kümeleme kısıtları listelendi.
- [ ] Kurul kapsamı belirlendi.
- [ ] `embed_ok` belirlendi: metin gömülebilir ya da harici yapay zekâ API'sine gönderilebilir mi? Korumalı metinde hukuki onay olmadan `false`.
- [ ] Türkçe atıf metni yazıldı ve Ayarlar › Kaynaklar ve lisanslar ekranına eklendi.
- [ ] Gerekiyorsa avukat görüşü alındı ve dosyaya bağlandı.
- [ ] Proje sahibi durumu onayladı; bu defter ve `source` satırı aynı değişiklikte güncellendi; yeniden kontrol tarihi girildi.

```toml
# pipeline/sources/quran-align.toml (örnek; alan adları source tablosuyla aynı)
slug = "quran-align"
tur = "zamanlama"
baslik = "quran-align kelime zamanlamaları"
yazar = "Collin Fair"
surum = "<sürüm>"                  # source.surum zorunlu; veri setinin sürümü
kaynak_url = "https://github.com/cpfair/quran-align"
license_name = "CC BY 4.0 (veri), MIT (kod)"
license_url = "https://raw.githubusercontent.com/cpfair/quran-align/master/LICENSE"
license_status = "serbest"
kisitlar = { yalniz_eslesen_ses = true }
atif_metni = "Kelime zamanlamaları: Collin Fair, quran-align, CC BY 4.0."
kurul_gerekli = true               # ses paketiyle birlikte
embed_ok = true
# hatta özgü alanlar
lisans_kopyasi = "licenses/quran-align-2026-10-18.txt"
lisans_sha256 = "<sha256>"
yeniden_kontrol = 2027-04-01
```

## 8. Açık sorular ve yazışma listesi

| # | Muhatap | Soru | Engellediği iş |
|---|---|---|---|
| 1 | Tanzil | Ayrı sütundaki normalize arama metni "değiştirme" sayılır mı? (Metin bayt bayt saklanır; K-26) | `core` arama |
| 2 | KFGQPC | Hafs fontu için yazılı izin; alt kümeleme | Mushaf C fontu |
| 3 | Quran Foundation | Fontların cüz paketiyle indirilmesi; düzen verisinin çevrimdışı paketlenmesi; atıf ifadesi | Mushaf A |
| 4 | QAC | "commercial purposes" şartı bağışla yürüyen ücretsiz uygulamayı kapsar mı? | `kelime-kok` paketi |
| 5 | Tarteel (QUL) | Kullanılacak her kaynağın lisansı | QUL verileri |
| 6 | Sunnah.com | Arapça metin ve numaralandırma izni | `hadis-kutub-i-sitte` |
| 7 | Hafızlar | Yazılı izin | `ses-{hafiz}` |
| 8 | Avukat | Risale iç kullanımı ve dizin yolu; GPL verinin dağıtımı; sipariş eserlerin (Elmalılı, Tecrîd) hak durumu; aktarımlarımızın ve kelime anlamlarının lisansı | Risale, `kelime-kok`, Elmalılı |
| 9 | Kurul | Başvuru usulü, ücret ve süre; Medine fontlarının kabulü; kelime anlamlarının meal sayılıp sayılmadığı | Mağaza yayını |

## İlgili dosyalar
- [Karar defteri](../00-ozet/02-karar-defteri.md) · [Sözlük](../00-ozet/03-sozluk.md)
- [İçerik hattı](./02-icerik-hatti.md) · [Elmalılı hazırlığı](./03-elmalili-hazirligi.md) · [Hadis hazırlığı](./04-hadis-hazirligi.md) · [Risale hazırlığı](./05-risale-hazirligi.md) · [Kelime anlamları](./06-kelime-anlamlari.md)
- [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md)
- [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) · [Riskler](../08-yol-haritasi/03-riskler.md)
- [Kaynakça](../09-kaynakca.md)
