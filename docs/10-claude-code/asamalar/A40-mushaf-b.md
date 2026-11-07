# A40 · Mushaf B (Türk hattı)

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 6 · Ek içerik · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** —
> **Ajanlar:** `arastirmaci` · `hat-gelistirici` · `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `icerik-hatti` · `paket-yayini` · `mobil-ekran` · `capa-gramer` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A40`

## Amaç
Türk hattı sayfa görselleri ve sayfa başına âyet koordinatlarıyla (`ayah_box`) Mushaf B açılır: âyet vurgusu ve âyet seçimi vardır, kelime seçimi yoktur (K-07). Sayfa görselleri internetteki hazır taramadan alınır (Merve Yayınları Hâfız Osman hattı, 606 basılı sayfa; Internet Archive). Türk düzeni için hazır `ayah_box` verisi bulunamadı; koordinatları içerik hattımız görüntü işlemeyle üretir. Aşama tedarikle başlar (A40.0), hattan pakete, paketten mobil Mod B'ye ilerler. Görünürlük editoryal kaliteye bağlıdır: `public` derlemeye yalnız editörce onaylı kutular girer (K-42 madde 5).

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7 tablo ve ortak sözleşme, §7.2 Mod B, §7.4 eksik paket, §9 bellek, §10 bayraklar, §13, §15 MM-7
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1 `mushaf-b`, §3.5, §6 içerik özeti · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source` (16 sütun), §8 `review`, §9.1 `page_map` ve `ayah_box`
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 Kaynak kaydı ve atıf, §3.8 Diğer (`mushaf-b-*`), §5 Yeni kaynak ekleme
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları, §7 yayın adımları
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §2, §3 Mod B seçimi, §5, §10 vurgu, §13 · [Çapa şeması](../../03-veri/01-capa-semasi.md): §10 Mod B eşleme birimi
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.5 Mod B Gece denetimi, §12 TS-6 · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §8 yeni kaynak, §9 QA kapıları

## Kapsam
**Yapılır**
- Tedarik: taramanın indirilmesi, SHA-256 ve kaynak kaydı (A40.0); girdi denetimi ve tarama ölçümü (A40.1).
- Görsel biçimi, paket bölünmesi ve `ayah_box` yöntemi kararları.
- Görsel bağdaştırıcısı, Türk düzeni `page_map` (606 sayfa), `ayah_box` üretimi ve QA kuralları.
- `mushaf-b` paketinin yazımı ve `dev` yayını; mobil Mod B; `internal` ve `public` görünürlüğü.

**Yapılmaz**
- Görselden metin okumak: Mod B'nin metin katmanı Tanzil'den çapayla gelir; görsel OCR edilmez, işaretler yalnız renk ve şekille bulunur.
- Kelime seçimi ve kelime kartı (Mod B'de yok; "Kelimeler" düğmesi âyeti Âyet âyet biçiminde açar). Mağaza sürümü ([A34](./A34-magaza-yayini.md) yordamı).

## Tedarik
Araştırma tarihi 2 Kasım 2026; A40.0'da yenilenir. Sayfa görselleri hazır taramadan alınır. Türk düzeni için hazır `ayah_box` verisi bulunamadı: koordinatlar ve `page_map` taramanın kendisinden üretilir. Ölçümler yerel betiklerle yapıldı.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Türk hattı sayfa görselleri (Mushaf B; 606 basılı sayfa) | Internet Archive öğesi `kuran-i-kerim-merve-yay.-hafiz-osman-hatti-net-sure-yer-imli`, "Kur'an-ı Kerim Merve Yayınları Hafız Osman Hattı Net Sure Yer İmli" (<https://archive.org/details/kuran-i-kerim-merve-yay.-hafiz-osman-hatti-net-sure-yer-imli>; öğe 13 Ekim 2026'da eklendi, 17 dosya, 760.952.130 bayt). Alınacak dosya `Kur'an-ı Kerim Merve Yay. Hafız Osman Hattı Net Sure Yer İmli_jp2.zip`: 281.838.331 bayt, 624 JP2, ETag `6ace568b-10cc82fb`, MD5 `39f1f482a49b96de7abfac9a5a913802`, SHA-1 `34e9d6bfe26cad88d3cb81fba51c783d0fceb04b`. Yanına `…_scandata.xml`: 199.880 bayt, SHA-1 `6302ce7a13b7cd7b950352e13e28680dca05ef63` | Doğrudan dosya: `https://archive.org/download/<kimlik>/<dosya adı>` (302 ile `ia600507.us.archive.org`; hesap, form ve anahtar yok); `data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/`. Ek yollar: BitTorrent (`…_archive.torrent`, 32.400 bayt); tek yaprak JPEG (`https://archive.org/download/<kimlik>/page/n<yaprak>.jpg`); ZIP'ten tek yaprak HTTP Range ile (2 yaprak için 9 istek, 1,1 MB). 412 MB'lık PDF alınmaz | `scandata.xml`: 624 yaprak, hepsi "Normal". Yaprak 4–609 = 606 basılı Kur'an sayfası; basılı numara yaprak − 3 (yaprak 20 → 17, 330 → 327, 609 → 606; 609 son sayfadır). Yaprak 5–609 (605 yaprak) 1800×2856 px (604'ü tam), yaprak 4 (tezhipli ilk sayfa) 2213×3511 px; yaprak 0–3 ve 610–623 Kur'an dışıdır. Sayfada 15 satır; üç örnek sayfada (17, 327, 606) sayfa tam âyetle başlar ve biter (âyet berkenar). ZIP: 624 JP2 (224.125–1.243.224 bayt, ortanca 437.084; toplam 281.563.978 bayt); yaprak 330 ve 609 Pillow ile çözüldü | Internet Archive `Kuran-Kerim-ArapaMushaf-erif-Diyanet-` (28 Haziran 2018; 612 yaprak, hepsi 2245×3249 px, 300 ppi; JP2 ZIP 270.560.993 bayt) ve `kuranikerimdiyanetyayinlari_202001` (15 Ocak 2020; 616 yaprak, hepsi 2315×3319 px, 300 ppi; JP2 ZIP 259.473.984 bayt); hat, sayfa sayısı ve düzen A40.0'da ilk, orta ve son sayfaya bakılarak ölçülür. `kuran-husrev-mushaf` (604 JPEG, `0.jpg`–`603.jpg`, 634.156.176 bayt) son sayfa (İhlâs, Felak, Nâs; `604.jpg` yok) eksik olduğu için seçilmedi. Kayışzâde ve Hasan Rıza taramaları Internet Archive'da ve web aramasında bulunamadı; bulunursa listeye eklenir |
| Âyet koordinatları (`ayah_box`; sayfa başına âyet satır kutuları) | Hazır veri yok: Türk düzeni için herkese açık `ayah_box` ya da sayfa koordinatı verisi bulunamadı (GitHub, PyPI ve web aramaları, 2 Kasım 2026). Bilinen hazır veriler Medine sayfalarına aittir: GitHub `bodoorzahera/Quran-coordinate` (HEAD `ed24b7fbf60a052ac58e694d5728ab4c4d59f96d`; PyPI `qurancoor` 1.2.3; kelime kutuları) ve `mushafdatabase/MushafDatabase-Ligature-Based-SVG` (HEAD `ae5786ab08597f8123575dec4e774f1eca195e0f`; SVG sayfalar). Bu taramanın 606 sayfasına uymazlar | Kendimiz üretiriz (A40.3): JP2 yaprakları Pillow ile çözülür; âyet sonu işaretleri (turuncu noktalı halka) renk ve şekille, satırlar yatay izdüşümle bulunur; kutular işaretler arasındaki satır parçalarıdır | Prototip (2 Kasım 2026; uzaktan okunan iki yaprak): yaprak 330'da 13 işaretin 13'ü bulundu (sayfada 13 âyet); yaprak 609'da 15 işaretin 11'i (eşik ince ayarı A40.3'te). Ürün ölçütü: 6.236 âyetin her biri en az bir kutuda; sayfa başına işaret sayısı sayfadaki âyet sayısına eşit | Aykırı sayfalar için editör paneli `ayah_box` kuyruğunda elle işaretleme (A15); gerekirse `opencv-python-headless` 5.0.0.93 (şablon eşleme, Hough çemberi) |
| Türk düzeni `page_map` (sayfa → âyet aralığı; 606 sayfa) | Taramanın kendisi ve Tanzil (A10): her sayfadaki âyet sonu işaretleri Tanzil'in 6.236 âyetlik dizisine sırayla atanır; sayfa başı ve sonu `q:{sure}:{ayet}` çapasıdır. Medine 604 sayfa düzeni (`medine-604-duzen`, A11) bu düzen değildir | İçerik hattı (A40.3); girdi A10 `unit` satırları ve A11 sure başlangıçları | İşaret sayılarının toplamı 6.236; her sayfanın ilk âyeti bir önceki sayfanın son âyetinden sonraki âyettir. Karşılaştırma verisi GitHub `Mythpwr/Quran-Data` (HEAD `80d5378fb42511c731248178b32a73bdd47b5d4c`; `sayfa_duzenli_kuran.json` 4.342.789 bayt; Diyanet uygulamasının sayfa düzeni): 605 sayfa ve 5.984 âyet; 6.236'ya ulaşmadığı için kaynak seçilmedi | Yok; yedek tarama (Diyanet) seçilirse `page_map` o taramadan çıkarılır |
| Görüntü işleme kitaplıkları (pipeline) | PyPI: `pillow` 13.0.0 (Python ≥3.11), `numpy` 2.5.4 (≥3.12), `scipy` 1.18.1 (≥3.12) | `uv add --directory pipeline pillow numpy scipy`; sürümler `uv.lock` içinde sabitlenir | PyPI kayıtları 2 Kasım 2026'da okundu; üçü Python 3.13 ile uyumlu. `uv run --python 3.13 --with pillow --with numpy --with scipy python -I` ile JP2 çözüldü (1800×2856 RGB), WebP ve AVIF yazıldı | `opencv-python-headless` 5.0.0.93; `scikit-image` 0.26.0 |
| Mobil görüntü ve yakınlaştırma kitaplıkları | `expo-image` (Expo SDK ile birlikte sürümlenir; npm: `sdk-57` etiketi 57.0.5, `latest` 58.0.18); `react-native-gesture-handler` ve `react-native-reanimated` A24–A25'te Expo SDK uyumlu sürümle eklenir | `npx expo install expo-image` (SDK uyumlu sürümü seçer) | npm kayıtları 2 Kasım 2026'da okundu; yeni kitaplık yok | Yok |

Kendimiz yapacağımız işler: sayfa görsellerinin kırpılması ve paket biçimine (WebP) çevrilmesi; Türk düzeni `page_map`'in işaret sayımıyla üretilmesi ve doğrulanması; `ayah_box` üretimi (işaret bulma, satır ayırma, kutu hesabı) ve aykırı sayfaların elle işaretlenmesi için editör kuyruğu; `ingest/mushaf_b.py` bağdaştırıcısı ve QA kuralları; `mushaf-b` paket yazıcısı.

Ölçümler (2 Kasım 2026):
- Sayfa görseli: Kur'an sayfaları 1800×2856 px (kayıtlı ppi 96), 15 satır; tezhipli ilk sayfa 2213×3511 px.
- Paket görseli boyutu (yaprak 330): JP2 445.309 bayt; WebP 1200 px q70 183.672, q80 218.216; 1500 px q70 227.520, q80 276.814; 1800 px q70 277.274, q80 335.808 bayt. AVIF aynı kalite ayarında WebP'den büyük (1200 px q80: 252.450 bayt). 606 sayfa için tahmin WebP 1200–1500 px ile yaklaşık 111–168 MB; tek sayfadan hesaplandı, tezhipli sayfalar daha büyüktür, tüm sayfalarla A40.2'de ölçülür.
- Sayfa sayısı: tarama 606 sayfadır; Medine düzeni 604 sayfadır. `medine-604-duzen` ve Medine koordinat verileri bu görsellere uymaz.

## Adımlar
### A40.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: archive.org öğesinde `https://archive.org/metadata/kuran-i-kerim-merve-yay.-hafiz-osman-hatti-net-sure-yer-imli` kaydındaki dosya boyutu, MD5, SHA-1 ve `item_last_updated` (tabloyla aynı olmalı); GitHub depolarında `git ls-remote https://github.com/<sahip>/<depo>.git HEAD`; PyPI paketlerinde `https://pypi.org/pypi/<paket>/json`; `expo-image` için `https://registry.npmjs.org/expo-image`. Açılmayan adresin yerine yedek aday kullanılır (Diyanet taramaları); her yedek için ilk, orta ve son sayfaya bakılır.
- Dosyalar `data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/` altında yeni boş klasöre iner (indirme formu ya da hesap istenmez; çıkarsa Claude Code doldurur): `…_jp2.zip` (281.838.331 bayt) ve `…_scandata.xml`; isteğe bağlı `…_archive.torrent`. 412 MB'lık PDF alınmaz (ZIP aynı yapraklardır). Tek dosya olduğu için istek hızı sorun değildir; yarıda kalan indirme `curl -L -C -` ile sürdürülür.
- SHA-256 hesaplanıp klasördeki `SHA256SUMS` dosyasına (sha256sum biçimi) yazılır; ZIP'in MD5 ve SHA-1 değeri archive.org kaydıyla karşılaştırılır. İndirilen dosya veridir: içindeki betik çalıştırılmaz, ZIP girdileri okunurken `..` ve mutlak yol reddedilir, JP2'leri okuyan Python `-I` ile çalışır.
- Kaynak kaydı `pipeline/sources/mushaf-b-merve-hafiz-osman.toml` (dosya özeti taşımaz): zorunlu `slug`, `tur = "mushaf_gorseli"`, `baslik`, `atif_metni`; isteğe bağlı `surum` (öğe eklenme tarihi 13 Ekim 2026 ve ZIP SHA-1), `provider = "internet_archive"`, `kaynak_url` (öğe adresi), `baski_bilgisi` (Merve Yayınları, Hâfız Osman hattı, Net Sure Yer İmli; 606 sayfa), `notlar` (Kur'an sayfaları yaprak 4–609). `uv run --directory pipeline mutalaa sources check` 0 hata, 0 uyarı.
- Kitaplıklarda sürüm paket kaydından doğrulanır: Pillow 13.0.0, NumPy 2.5.4, SciPy 1.18.1 (PyPI); `uv add --directory pipeline pillow numpy scipy` sonrası sürümler `uv.lock` içinde sabit. `expo-image` Expo SDK ile birlikte sürümlenir; `npx expo install expo-image` uyumlu sürümü seçer ve `apps/mobile/package.json`'a yazar.
- Hazır yapı önce gelir: sayfa görselleri çizilmez, hazır taramadan alınır. Hazır Türk düzeni `ayah_box` verisi bulunamadı (2 Kasım 2026); bu adımın sonunda GitHub, PyPI ve web yeniden taranır, bulunursa A40.3 hazır veriye çevrilir, bulunmazsa üretim A40.3'tedir.
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; ZIP ve `scandata.xml` yeni boş klasörde, `SHA256SUMS` var; ZIP'in MD5 ve SHA-1 değeri archive.org kaydıyla aynı; ZIP'te 624 JP2; kaynak kaydı yazıldı ve `sources check` 0 hata; kitaplık sürümleri doğrulandı; adres, tarih ve sürümler aşama notuna yazıldı.

### A40.1 · Girdi denetimi ve tarama ölçümü
Her oturumun ilk işidir. Eksik madde varsa o madde tamamlanır, sonra ilerlenir.
1. Önkoşullar: [A24](./A24-okuyucu-mushaf-c.md) bitti (Mod C okuyucu ve sayfalayıcı); A10 Tanzil birimleri veritabanında (114 sure, 6.236 âyet); A07 şemasında `page_map`, `ayah_box` ve `review` var.
2. Kaynak kaydı: `uv run --directory pipeline mutalaa sources check` 0 hata ve 0 uyarı; `data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/` altında `SHA256SUMS` var ve ZIP'in özeti onunla aynı.
3. Tarama ölçümü: `scandata.xml` 624 yaprak; Kur'an sayfaları yaprak 4–609 (606 sayfa); yaprak–sayfa eşlemesi (sayfa = yaprak − 3) ilk, orta ve son sayfada basılı numara okunarak doğrulandı ve kayda yazıldı.
4. `ayah_box` kaynağı belli: kendi üretimimiz (A40.3); koordinatlar ölçümden ya da işaretleme aracından gelir.
- **Bitti sayılır:** dört madde kayıtlı kanıtla sağlanıyor; sayfa sayısı (606) ve yaprak–sayfa eşlemesi aşama notunda.

### A40.2 · Kararlar
- `arastirmaci`: React Native'de görsel renk ters çevirme (`filter`) desteği ve expo-image `tintColor` davranışı (Mobil mimari §7.2 "Doğrulanacak"). Tarama renklidir (siyah mürekkep, turuncu çerçeve ve işaretler, beyaz zemin); mürekkep maskesi ile süsün ayrı katman olarak tutulması da denenir.
- `/karar`: görsel biçimi (saydam zeminli mürekkep maskesi ve `tintColor`, ters çevirme ya da mürekkep ve süs iki katman; MM-7, TS-6) ve paket görsel boyutu (WebP 1200 ya da 1500 px; Tedarik ölçümü); paket bölünmesi (tek `mushaf-b` ya da cüzlere bölünme; İçerik paketleri §3.5 Açık soru); `ayah_box` üretim yöntemi ve düzeltme aracı; `public` derlemede `ayah_box` ve `page_map` onay kuralı (A40.6).
- **Bitti sayılır:** kararlar defterde; İçerik paketleri §3.5 ve Mobil mimari MM-7 `/belge-esitle` ile güncel.

### A40.3 · Hat: kaynak, `page_map`, `ayah_box`
- Kaynak kaydı A40.0'da yazıldı (`tur = "mushaf_gorseli"`). Görseller için yeni bağdaştırıcı `ingest/mushaf_b.py` ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §8; `SourceAdapter`): `fetch` ZIP'i `data/gelen/` altından alır, `parse` yaprak 4–609'u sayfa 1–606'ya eşler; ZIP içeriği `data/raw`'a yalnız içerik hattıyla girer. Her sayfa görseli kırpılır, A40.2'de seçilen boyut ve biçime çevrilir ve sha256'sı kaydedilir.
- `page_map` (Türk düzeni; Mod B'de sayfa başına bir satır): sayfa başına âyet aralığı. Aralıklar, sayfadaki âyet sonu işareti sayılarıyla Tanzil dizisine atanarak üretilir. Âyet berkenar düzeninde her sayfanın tam âyetle başlayıp tam âyetle bittiği veriyle denetlenir ([Çapa şeması](../../03-veri/01-capa-semasi.md) §10). Medine düzeni (`medine-604-duzen`) kullanılmaz: tarama 606 sayfadır.
- `ayah_box`: âyetin satır başına kutuları (`seq`), paketlenen görselin piksel uzayında (ham yaprakta ölçülür, paket görselinin oranıyla ölçeklenir). Yöntem: âyet sonu işaretleri renk ve şekille, satırlar yatay izdüşümle bulunur; sure başlığı bantları ve besmele satırı kutu üretmez; bir âyet, önceki işaretten kendi işaretine kadar olan satır parçalarıdır (sağdan sola). Koordinatlar ölçümden ya da işaretleme aracından gelir; Claude Code koordinat uydurmaz. Kutular editörde `hedef_tablo = 'ayah_box'` kuyruğuyla onaylanır.
- QA (`pipeline/src/mutalaa_pipeline/qa/checks/mushaf_b.py`, öneri): 6.236 âyetin her biri en az bir kutuda; sayfa başına işaret sayısı `page_map` aralığındaki âyet sayısına eşit; kutular görsel sınırları içinde; `seq` kesintisiz; bir sayfanın kutuları o sayfanın `page_map` aralığındaki âyetleri kapsıyor; her görselin sha256'sı kayıtlı.
- **Bitti sayılır:** `qa run` 0 ile çıkıyor; `export pg` sonrası satır sayıları raporda (`page_map` 606 satır; `ayah_box` içinde farklı âyet 6.236).

### A40.4 · `mushaf-b` paketi
- `sunucu-gelistirici`: Yayınlayıcı paketi İçerik paketleri §3.5'e göre yazar: `page_image(page, format, width, height, data, sha256)`, `ayah_box(page, anchor, seq, x, y, w, h)`, `page_map` (Türk düzeni); her pakette olduğu gibi `pack_meta`, `pack_source`, `attribution` (`atif_metni` ve `atif_url` pakete aynen yazılır, P-11). İçerik özeti görsel dosyalarının yol ve sha256 satırlarıyla hesaplanır (§6). Boyut tahmini 111–168 MB'dır (WebP 1200–1500 px); paket bölünmesini A40.2 kararı belirler.
- `publish --flavor dev` ve `verify --flavor dev`. Paket ATTACH edilmez; kendi salt okunur bağlantısıyla açılır. Manifest her derlemede imzalıdır.
- **Bitti sayılır:** `dev` manifestinde `mushaf-b` var; `verify` 0.

### A40.5 · Mobil Mod B
- `mobil-gelistirici` + `mobil-ekran`: `src/features/reader/mushaf-b/` içinde `MushafImagePage` (Mobil mimari §7.2): expo-image ve A40.2'deki tema yolu; etkin âyetin kutuları zemin tonu ve alt kenar çizgisiyle; dokunuş âyeti seçer, "Seç" âyet aralığı kurar; kelime aralığına yapılmış vurgular kutu kenarında işaretle görünür; sesli takipte kutu vurgusu; meal dokunuşunda kutu tonu; kıstırma yakınlaştırması kutu katmanını aynı dönüşümle büyütür; aynı anda en çok üç çözülmüş sayfa.
- Erişilebilirlik: görsel ekran okuyucudan gizli; her âyet Türkçe etiket ve Arapça Unicode metinli tek öğe.
- `src/lib/flags.ts` `mushafB: 'paket'`: paket derlemede görünmüyorsa Mod B ayarlarda ve tanıtımda listelenmez (§7.4).
- Üç temada (Kâğıt, Âhar, Gece) görsel denetim ve ekran okuyucu denetimi emülatörde ya da cihazda yapılır: kullanıcıya bırakılır (CLAUDE.md, Çalışma düzeni 3), aşamayı bekletmez; ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" yazılır. `arayuz-denetcisi` kodu inceler.
- **Bitti sayılır:** isabet, ölçek ve görünürlük birim testleri yeşil; `arayuz-denetcisi` kod incelemesinde engelleyici bulgu yok; görsel ve ekran okuyucu denetimi "kullanıcıya bırakıldı" notuyla.

### A40.6 · Görünürlük ve yayın hazırlığı
- Görünürlük editoryal kaliteye bağlıdır (K-42 madde 5; [Yayın süreci](../../07-yayin/01-yayin-sureci.md) §3): `dev` ve `internal` derlemelerde `mushaf-b` paketi görünür; `public` derlemeye yalnız editörce onaylı `ayah_box` ve `page_map` satırlarını taşıyan paket girer. `ayah_box` tablosunda onay sütunu yoktur; paket yazıcısı onayı `review` kaydından (`hedef_tablo = 'ayah_box'`) okur, kuralın kapı karşılığı A40.2'de karara bağlanır.
- Mod B kodunu taşıyan uygulama sürümü mağazaya A34 yordamıyla çıkar.
- **Bitti sayılır:** `public` kuru çalıştırması (`publish --flavor public --dry-run`) 0 ile biter; kapı raporunda `mushaf-b` için "girdi" ya da onay eksikliğiyle "girmedi" kararı kural koduyla yazılı.

## Kabul ölçütleri
- [ ] A40.0: tarama `data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/` altında, `SHA256SUMS` var; ZIP'in MD5 ve SHA-1 değeri archive.org kaydıyla aynı; kaynak kaydı yazıldı.
- [ ] `uv run --directory pipeline mutalaa sources check` ve `qa run --source mushaf-b-merve-hafiz-osman` 0 ile çıkıyor.
- [ ] `page_map` 606 satır; `ayah_box` içinde farklı âyet sayısı 6.236 (SQL).
- [ ] `publish --flavor dev` ve `verify --flavor dev` 0; `dev` manifestinde `mushaf-b` imzalı pakettir.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: isabet testi, ölçek dönüşümü, `isPackVisible` ile derleme türüne uymayan paketin gizlenmesi.
- [ ] `arayuz-denetcisi` kod incelemesinde engelleyici bulgu yok; Kâğıt, Âhar ve Gece görsel denetimi ile VoiceOver ve TalkBack okuması (Fâtiha ve Bakara 255; B-10) kullanıcıya bırakıldı ve ilerleme notunda yazılı.
- [ ] `public` kuru çalıştırması 0 ile biter; `mushaf-b` için kapı kararı raporda.

## Doğrulama
```bash
uv run --directory pipeline mutalaa sources check; echo "çıkış: $?"
uv run --directory pipeline mutalaa qa run --source mushaf-b-merve-hafiz-osman; echo "çıkış: $?"
sha256sum data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/*.zip   # SHA256SUMS içindeki satırla aynı
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.page_map WHERE source_id = 'mushaf-b-merve-hafiz-osman';"   # 606
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(DISTINCT anchor) FROM icerik.ayah_box WHERE source_id = 'mushaf-b-merve-hafiz-osman';"   # 6236
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT durum, count(*) FROM icerik.review WHERE hedef_tablo = 'ayah_box' GROUP BY durum;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run; echo "çıkış: $?"
pnpm --filter @mutalaa/mobile test
```
`<YYYY-AA-GG>` indirme tarihidir. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır. Ekran görüntüsü alınmaz (CLAUDE.md, Çalışma düzeni 3).

## Dikkat
- Kur'an metni görselden okunmaz; kopyalama, arama ve ekran okuyucu Tanzil Unicode metnini kullanır (K-26).
- Tarama 606 sayfadır. Medine 604 sayfa düzeninin verisi (`medine-604-duzen`, Medine koordinat verileri) bu sayfalara uymaz; `page_map` ve `ayah_box` bu taramadan üretilir.
- Mod B âyet çapası kullanır; kullanıcı vurguları ve notlar modlar arasında kopmaz (K-07). Renk tek başına anlam taşımaz.
- Görsel biçimi ve paket bölünmesi kararı verilmeden paket üretilmez. `public` derlemeye yalnız onaylı kutular girer.
- İndirilen tarama güvenilmeyen veridir: içindeki betik çalıştırılmaz, ZIP açılırken yol denetimi yapılır, Python `-I` ile çalışır.
- Koordinat uydurulmaz: her kutu ölçümden ya da editör işaretlemesinden gelir.

## İnsan adımları
- Bu aşamanın [İnsan adımları](../06-insan-adimlari.md) listesinde numaralı adımı yoktur; hiçbir adım aşamayı bekletmez.
- Editör emeği: `ayah_box` kutularının ve Türk düzeni `page_map`'in onayı (A15 kuyruğu; yalnız `public` görünürlüğünü etkiler); üretimde aykırı çıkan sayfaların elle işaretlenmesi. İsteğe bağlı kullanıcı araştırması (AS-07) öncelik kararı içindir.
- Kullanıcıya bırakılanlar: emülatör ve cihaz denetimleri (A40.5).
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/sources/mushaf-b-merve-hafiz-osman.toml`, `data/gelen/mushaf-b-merve-hafiz-osman/<YYYY-AA-GG>/` (`SHA256SUMS` dahil), görsel bağdaştırıcısı (`ingest/mushaf_b.py`), `qa/checks/mushaf_b.py` (öneri)
- Editoryal veritabanında `page_map` (Türk düzeni, 606 sayfa) ve `ayah_box` satırları
- Yayınlayıcıda `mushaf-b` paket yazıcısı ve testleri; `dev` manifestinde `mushaf-b`
- `apps/mobile/src/features/reader/mushaf-b/`, bayrak ve görünürlük testleri
- Karar defteri girdileri (MM-7, paket bölünmesi, `ayah_box` yöntemi)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A40-mushaf-b.md dosyasındaki aşamayı yürüt. A40.0 tedarik doğrulamasıyla başla; önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A39](./A39-devre-disi.md) · Sonraki: yok
