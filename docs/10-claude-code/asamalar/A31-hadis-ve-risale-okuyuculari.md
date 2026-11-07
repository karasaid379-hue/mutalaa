# A31 · Hadis ve Risale okuyucuları

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-04](../../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A25](./A25-secim-kelime-karti-baglantilar.md) · [A19](./A19-hadis-hatlari.md) · [A20](./A20-risale-altyapisi.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `metin-denetcisi` · `hat-gelistirici` (fikstür gerekirse) · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A31`

## Amaç
Tecrîd-i Sarîh ve Kütüb-i Sitte için Arapça ile Türkçesini (Babanzâde Ahmed Naim ve Kâmil Miras) yan yana gösteren hadis okuyucusunu ve Risale-i Nur okuyucusunu yazar. Okuyucular A19 ve A20'nin `dev` paketlerindeki gerçek metinle çalışır: Tecrîd'in tamamı, Kütüb-i Sitte'nin Arapçası ve Risale-i Nur Külliyatı. Onaysız birim "doğrulanmamış" rozetiyle görünür; `public` derlemede yalnız onaylı birim bulunur. Lügat yoğunluğu, ibare kartı ve baskı sayfa işaretleri A20'nin lügat, âyet atıf dizini ve `page_map` verisini kullanır.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 seçim, §11 hadis okuyucu, §12 Risale-i Nur okuyucu, §13 erişilebilirlik
- [Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md): tamamı; özellikle Naim ve Miras ciltleri, numaralandırma, Tecrîd ↔ Buhârî eşlemesi, derece etiketi
- [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md): tamamı; özellikle kitap ve bölüm adresleri, paragraf çapaları, baskılar ve sayfa eşlemesi, âyet atıf dizini, lügat
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.4 Hadis, §3.5 Risale-i Nur, §3.6 Lügat
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 `kutuphane/hadis/*`, `kutuphane/risale/*`, `h/`, `ht/`, `rn/`; §3 hadis ve Risale satırları; §6 Okuma › Risale ayarları; §7 derin bağlantılar
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.4 bölüm vurgusu, §3.1–§3.3 yazı tipleri ve karışık yön, §6 `HadithPair`, `LugatGloss`, `LugatCard`, `IbareCard`, `CitationLink`, `FootnoteMarker`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.4 `risale-dizin`, §7 süzme
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §9 seçim çözümleme (Arapça ibare satırı), §10 okunur adres
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7.3 yerel seçim kuralı, §8 sayfa çevirme yönü, §13 sağdan sola parçalar

## Kapsam
**Yapılır**
- A21'in yer tutucu rotaları doldurulur: `kutuphane/hadis/[koleksiyon]/index.tsx` (kitap ve bâb listesi), `kutuphane/hadis/[koleksiyon]/[no].tsx` (hadis okuyucu), `kutuphane/risale/[kitap]/index.tsx` (bölüm ağacı, kitap ilerlemesi), `kutuphane/risale/[kitap]/[...bolum].tsx` (Risale okuyucu).
- `h`, `ht` ve `rn` derin bağlantıları: A25'in tek yakalayıcı rotası `app/[...capa].tsx` bu türleri de çözecek biçimde genişler (A25 bu türleri A31'e bırakır).
- Lügat katmanı ve kartı, ibare (iktibas) kartı, haşiye alt sayfası, açık atıf bağlantıları, baskı sayfa işaretleri.
- Onaysız birim için "doğrulanmamış" rozeti; derlemede görünür birim yoksa "Bu içerik bu sürümde yok" durumu.
- Bu okuyucularda seçim, vurgu ve not (A30 kayıtları) ve `reading_position` bağlamları (`hadis:tecrid`, `risale:{kitap}`).

**Yapılmaz**
- Hadis ve Risale hatları, paketleri ve gerçek veri: A19, A20. Kütüphane giriş listeleri (`hadis/index`, `risale/index`): A29.
- Hadis numaralandırma kararı (Hadis hazırlığı; proje sahibi), derece etiketi (sonra), konkordans (v1.x), sesli Risale (Faz atanmadı; Kapsam ve fazlar §4.4).
- Yapay zekâ ile özet ya da çeviri: bilerek yok (K-25, K-30).

## Tedarik
Araştırma tarihi 3 Kasım 2026; tablodaki adresler, commit'ler ve paket sürümleri aynı gün yeniden açıldı ve okundu (A31.0'da yenilenir). Bu aşama içerik dosyası indirmez: gerçek hadis ve Risale metni A19 ve A20'nin `dev` paketlerinden gelir; kaynakların adresleri, sürümleri ve sayımları o aşamaların Tedarik bölümlerindedir ve burada yinelenir. Yazı tipleri ve kitaplıklar A21–A25'te eklenir; bu aşama yeni kitaplık eklemez. Ölçümler yalnız sayım ve yapı bilgisidir (metin yazdırılmadı) ve ham kaynak dosyalarındaki ön ölçümlerdir; paket ölçümü A31.0'da yapılır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Tecrîd-i Sarîh Arapçası; kitap, bâb ve hadis yapısı | A19 çıktısı: `hadis-tecrid` paketi. Kaynak kaydı `tecrid-ar`: Shamela dışa aktarımı, archive.org `0001Htm48_201901`, `1145Htm.zip` (tek `.htm`, windows-1256, 1.315.950 bayt) | A19.0 `https://archive.org/download/0001Htm48_201901/1145Htm.zip` adresinden `data/gelen/tecrid-ar/<YYYY-AA-GG>/` altına indirir (3 Kasım 2026'da 200, 328.078 bayt); A31 yerel S3 `dev` manifestinden (`http://localhost:8333/mutalaa/dev/manifest.json`) okur | A19: 2.253 numaralı hadis (1…2.254). Ham dosyada 5.465 satır; satır uzunluğu (kod noktası) medyan 57, p99 1.577, en uzun 2.920; 48 farklı Arapça kod noktası (toplam 861.561), iki Arapça yazı tipinde de eksik 0. Paketteki `unit` sayısı ve `parent_path` derinliği A31.0'da ölçülür | OpenITI `TajridSarih` sürümü (commit `271ff65bd8364d3a46b5806ca529617d1ffc3393`; 3 Kasım 2026'da 200, 1.418.201 bayt) |
| Tecrîd-i Sarîh Türkçesi: Ahmed Naim (cilt 1–3) ve Kâmil Miras (cilt 4–12) | A19 çıktısı: `hadis-tecrid` paketinin Türkçe katmanı. Kaynak kayıtları `tecrid-naim` ve `tecrid-miras`: Diyanet İşleri Başkanlığı 13 ciltlik takım (1976–1980), archive.org `BuhariTecridiSarih1…5` ve `BuxariTecridiSarih6…13` metin katmanları | A19.0 `https://archive.org/download/<öğe>/<dosya>` adreslerinden indirir (3 Kasım 2026'da cilt 1 ve cilt 6 metin dosyaları 200: 1.604.062 ve 1.028.963 bayt); A31 `dev` manifestinden okur | A19: 13/13 cilt metin katmanı; düzeltme kuyruğu İ-11. Mütercim (Naim ya da Miras) `ht:naim` ve `ht:miras` çapalarından ve kaynak kayıtlarından gelir; paketteki alan adları A31.0'da doğrulanır | Aynı baskının başka kopyaları (A19 Tedarik) |
| Kütüb-i Sitte Arapçası (Buhârî, Müslim, Ebû Dâvûd, Tirmizî, Nesâî, İbn Mâce) | A19 çıktısı: `hadis-kutub-i-sitte` paketi. Kaynak kayıtları `hadis-ahmedbaset` (GitHub `AhmedBaset/hadith-json`, `v1.2.0`, commit `ca32fd72aa16eeeb9a819c80bb65c9e78766532d`) ve `hadis-fawaz-ar` (GitHub `fawazahmed0/hadith-api`, commit `df57907be35291c91ad6a6691180e22ca9920784`) | A19.0 `https://raw.githubusercontent.com/<sahip>/<depo>/<commit>/…` adreslerinden indirir (3 Kasım 2026'da `v1.2.0` etiketi ve `HEAD` sabit, `bukhari.json` 12.750.789 ve `ara-bukhari.json` 9.770.083 bayt, 200); A31 `dev` manifestinden okur | A19: 34.178 kayıt (Buhârî 7.277, Müslim 7.459, Ebû Dâvûd 5.276, Tirmizî 4.053, Nesâî 5.768, İbn Mâce 4.345). Hadis uzunluğu (karakter) medyan 441, p90 928, p99 2.075, en uzun 14.785 (Müslim); 1.000 üstü 2.825, 5.000 üstü 45 hadis. 48 farklı Arapça kod noktası (toplam 15.986.713), iki Arapça yazı tipinde de eksik 0 | OpenITI Shamela sürümleri (A19 Tedarik; Buhârî `0275AH` commit `44e1c36738a2bf5c14dafa232a6ae1891e6171cd`, 3 Kasım 2026'da 200, 6.039.255 bayt) |
| Risale-i Nur metni; kitap, bölüm, paragraf, haşiye ve dipnot sınırları | A20 çıktısı: `risale-{kitap}` paketleri. Kaynak kaydı `risale-asil-nusha`: GitHub `alitekdemir/Risale-i-Nur-Diyanet`, commit `1dad9ea73618772d5daecad19e8ccb27c0923d27` (`txt/`, `obsidian-markdown/`, `html/`) | A20.0 `https://github.com/alitekdemir/Risale-i-Nur-Diyanet/archive/1dad9ea73618772d5daecad19e8ccb27c0923d27.zip` adresinden indirir (3 Kasım 2026'da `HEAD` aynı commit, zip 200); A31 `dev` manifestinden okur | A20: 15 kitap, 298 `txt` dosyası, 47.558 paragraf ya da başlık satırı, 2.000.362 kelime. Satır uzunluğu (kod noktası) medyan 192, p90 590, p99 1.019, en uzun 3.665; 1.000 üstü 522, 3.000 üstü 1 satır. Arapça içeren satır 7.106; Arapça dizi 9.846 (uzunluk medyan 36, p99 501, en uzun 3.665; 300 üstü 211; satır başına en çok 30 dizi); 3.110 satırın Arapça oranı 0,9 ve üstü (neredeyse tümü Arapça paragraf). 62 farklı Arapça kod noktası (toplam 513.405), iki Arapça yazı tipinde de eksik 0 | `risale.online` ve Hizmet Vakfı Diyanet sayfaları (`https://risaleinur.hizmetvakfi.org/diyanet`; 3 Kasım 2026'da 200) |
| Âyet atıf dizini ve basılı baskı sayfa eşlemesi | A20 çıktısı: `risale-dizin` paketi (`xref`) ve `page_map`. Kaynak kayıtları `risale-atif-dizini` (âyet atıf dizini) ve `risale-baski-envar` (Hizmet Vakfı Külliyat görünümü, Hizmet Vakfı ve Envar Neşriyat Latin harfli baskısı, `https://risaleinur.hizmetvakfi.org/kulliyat`) | A20.3 ve A20.7 üretir (Külliyat sayfaları 3 Kasım 2026'da 200); A31 `dev` manifestinden okur | A20.3 ve A20.7 kabul ölçütleri; A20 ön ölçümünde Sözler için 271 içindekiler düğümü, `start_page` 5–856. Paketteki `xref` ve `page_map` satır sayıları A31.0'da ölçülür | `risale.online` (24 eser, 7.811 sayfa; paragraf başına `sayfa`; 3 Kasım 2026'da 200) |
| Lügat maddeleri, kelime sıklığı ve anlam taslağı | A20.6 çıktısı. Kaynak kayıtları `risale-kelime-frekans` (GitHub `alitekdemir/Risale-i-Nur-Kelime-Frekans`, commit `23f3c5caec91739f5c18d5280399d82bb47dcc02`; sıklık `data/eRisale/analysis/terkipsiz/<kitap>_frekans.txt`, anlam taslağı `data/eRisale/raw/<kitap>.csv`) ve köken başvuruları `lugat-redhouse-1890`, `lugat-kamus-i-turki`, `lugat-naci` (archive.org taramaları) | A20.0 indirir (3 Kasım 2026'da `HEAD` aynı commit, zip 200), A20.6 işler; A31 `dev` manifestinden okur | A20: sıklıkta 15 kitapta birleşik 20.045 benzersiz kelime (toplam frekans 491.225); anlam taslağında 398.772 satır, 46.090 benzersiz kelime. Anlam taslağı editör onayına (İ-28) kadar "doğrulanmamış". Paketteki madde sayısı A31.0'da ölçülür | Metnimizden kendi sıklık sayımımız (A05 normalleştiricisi) |
| Sağdan sola çizim ve uzun metin: Arapça dizi yönü, paragraf yerleşimi, kelime sonrası kısa anlam | React Native çekirdeği `Text` (0.88.1): iç içe `Text` parçası, `writingDirection` (belgede yalnız iOS), `textBreakStrategy` (belgede yalnız Android). Hazır ruby ya da çift yönlü metin bileşeni yok; npm araması (3 Kasım 2026) React Native için ruby bileşeni göstermedi | Yok (çekirdek bileşen) | `react-native-website` `main` belgeleri (`text-style-props`, `text`, `accessibility`) 3 Kasım 2026'da okundu: `writingDirection` ve `accessibilityLanguage` iOS etiketli. Birim uzunlukları yukarıdaki satırlarda (en uzun hadis 14.785 karakter, en uzun Risale satırı 3.665 kod noktası) | Yok |
| Yazı tipleri: Literata (Türkçe metin), Amiri ve Noto Naskh Arabic (Arapça) | `github.com/google/fonts` commit `6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec`: `ofl/literata/Literata[opsz,wght].ttf` (955.132 bayt, sürüm 3.103), `ofl/amiri/Amiri-Regular.ttf` (431.116 bayt, sürüm 1.002), `ofl/notonaskharabic/NotoNaskhArabic[wght].ttf` (307.592 bayt, sürüm 2.021) | A21 ve A22'de uygulamaya eklenir; A31 yeni yazı tipi eklemez (üç dosya 3 Kasım 2026'da bu commit'ten 200 ve aynı boyutta geldi; depo `HEAD` ilerledi, sabitlenen commit geçerli) | `cmap` ölçümü: Amiri-Regular 1.699, Noto Naskh Arabic 1.551, Literata 1.163 kod noktası. Risale, Kütüb-i Sitte ve Tecrîd Arapçasındaki bütün Arapça kod noktaları iki Arapça yazı tipinde var; Literata'da Risale Türkçe metninin tek eksiği U+200C (321 kez, biçim denetim karakteri) | `@expo-google-fonts/literata` 0.4.3, `@expo-google-fonts/amiri` 0.4.1, `@expo-google-fonts/noto-naskh-arabic` 0.4.5 (A21 Tedarik) |
| Liste, alt sayfa, test araçları | `FlatList` (React Native 0.88.1 çekirdeği), `@gorhom/bottom-sheet` 5.2.14, `jest-expo` ~58.0.13, `@testing-library/react-native` 14.1.0 (A21–A25'te eklenir) | Eklenir; sürüm `pnpm-lock.yaml` içinde | npm kayıtları 3 Kasım 2026'da okundu: `latest` etiketleri 5.2.14, 58.0.13 ve 14.1.0; `@gorhom/bottom-sheet` eş bağımlılığı Reanimated ≥3.16 ya da ≥4 ve Gesture Handler ≥2.16.1; `jest-expo` `@react-native/jest-preset` ^0.88.1; RNTL react ≥19, react-native ≥0.78 ve `test-renderer` ^1.0.0 ister. Paket kaydı A31.0'da yeniden doğrulanır | `@shopify/flash-list` 2.3.2 (Expo SDK 58 sürümü; npm `latest` 2.3.3) |

Kendimiz yapacağımız işler: hadis ve Risale ekranları, `HadithPair`, lügat katmanı ve kartı, ibare kartı, haşiye alt sayfası, kelime sonrası kısa anlam gösterimi (`LugatGloss`), `h`, `ht` ve `rn` derin bağlantı çözümü, uzun birim ve Arapça dizi çizim ayarları, gerekirse `test-hadis-ornek` sentetik fikstürü.

## Adımlar
### A31.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula (A19 ve A20 kaynakları, `google/fonts` yazı tipi dosyaları, kitaplık sürümleri); açılmayan adresin yerine yedek adayı kullan.
- İçerik dosyalarını A19.0 ve A20.0 `data/gelen/<kaynak>/<YYYY-AA-GG>/` altına indirir ve SHA-256 değerlerini `SHA256SUMS` dosyasına yazar; kaynak kayıtlarını `pipeline/sources/<kimlik>.toml` olarak açar. Bu adım o klasörlerin ve kayıtların varlığını denetler (`tecrid-ar`, `tecrid-naim`, `tecrid-miras`, `hadis-ahmedbaset`, `hadis-fawaz-ar`, `risale-asil-nusha`, `risale-atif-dizini`, `risale-baski-envar`, `risale-kelime-frekans`, `lugat-*`); eksik olanın aşama dosyasındaki `.0` adımı yürütülür.
- Ölçülmeyen hücreleri `dev` paketlerinden ölç (betik `.tmp/` altında, `python -I` ile; yalnız sayım): `unit` sayısı ve `parent_path` derinliği, birim uzunluğu dağılımı (medyan, p99, en uzun), Arapça kod noktalarının yazı tipi `cmap` kapsamı, `xref`, `page_map` ve lügat madde sayıları.
- Kitaplık sürümlerini `pnpm-lock.yaml` ve paket kaydından, yazı tipi dosyalarını `apps/mobile/assets/fonts/` içindeki kopyaların SHA-256 değerinden doğrula.
- **Bitti sayılır:** Tablodaki her satırın durumu (var, yok, sürüm) yazılı; ölçülmeyen hücreler dolu; ilgili kaynak kayıtları geçerli (`uv --directory pipeline run mutalaa sources check` hatasız).

### A31.1 · Önkoşul ve paket denetimi
- `dev` manifestini oku: `hadis-tecrid`, `hadis-kutub-i-sitte`, `risale-dizin`, `risale-*` ve `test-` önekli fikstür paketlerinin varlığı.
- Risale paketleri A20'den gelir. Fikstür gerekirse kaynak `test-risale-ornek` (yalnız `dev`), kitap slug'ı `test-ornek`, paketler `risale-dizin` ve `risale-test-ornek`; fikstürdeki iki sentetik `xref` satırı ibare kartını sınamaya yeter. Adlar Risale hazırlığı ile aynıdır.
- Hadis fikstürü gerekirse `hat-gelistirici` A13'teki `test-tefsir-ornek` kalıbıyla ekler (öneri: kaynak `test-hadis-ornek`; Türkçe "Deneme hadis metni 1 …", Arapça yerine açıkça sentetik harf dizisi).
- Derin bağlantı biçimi MM-14 ve ME-1'e bağlıdır (öneri 03-veri/01 §11 `toRoute`; 01-urun/03 §7 ona uyar: `mutalaa://h/tecrid/15`, `mutalaa://ht/naim/tecrid/15`, `mutalaa://rn/sozler/soz-10/hakikat-3/p4?aralik=120-184`). Kapanmadıysa öneri kullanıcıya sunulur ve `/karar` ile yazılır.
- `arastirmaci` doğrular: OD-5 (lügat kısa anlamının kelime üstünde, ruby biçiminde gösterimi; ön bulgu: React Native çekirdeğinde ruby yok ve npm araması hazır bileşen göstermedi, kelime sonrası iç içe `Text` yolu `LugatGloss` ile sürer, prototip ölçümü kalır); Android'de `accessibilityLanguage` karşılığı (ön bulgu: React Native belgesinde `accessibilityLanguage` ve `writingDirection` yalnız iOS etiketli, Android karşılığı belgelenmemiş; A26'da doğrulandıysa sonuç okunur).
- `metin-denetcisi` planı okur: hiçbir adım hadis ya da Risale metnini koda, teste ya da belgeye yazmıyor.
- **Bitti sayılır:** Paket durumu tablosu planda; fikstür adları ve bağlantı biçimi belli; doğrulama sonuçları yazılı.

### A31.2 · Hadis okuyucu
- Kitap › bâb › hadis gezinmesi paketteki `unit.parent_path` ve `label` alanlarından oluşturulur. `hadis_konum`'un pakette ayrı tablosu yoktur; konum `unit.parent_path`, `label`, `ord` ve `attrs` ile taşınır (Hadis hazırlığı numaralandırma bölümü, 03-veri/03 §3.2); A19 çıktısı esas alınır. Liste üstündeki arama alanı A28'in yürütücüsünü `kaynak:hadis` kapsamıyla kullanır (öneri).
- `HadithPair`: telefonda dikeyde Arapça üstte (sağdan sola, Amiri ya da Noto Naskh Arabic), Türkçe altta (Literata); üst çubukta "Arapça | Türkçe | İkisi". Yatay ve tablette iki sütun: Arapça sağda, Türkçe solda, satırlar hadis başında hizalı.
- Başlık: "Tecrîd-i Sarîh · 15", "Buhârî · 52" çipi, "Tercüme: Babanzâde Ahmed Naim" (cilt 4–12 için "Tercüme: Kâmil Miras"); değerler paketten gelir.
- Türkçe sütunda Naim ve Miras çevirisi aynı biçimde gösterilir. Onaysız Türkçe birim "doğrulanmamış" rozetiyle görünür.
- Kütüb-i Sitte yalnız Arapçadır; Tecrîd karşılığı olan hadiste "Tecrîd'deki tercümesine git" (A19'un `atif` bağlantısı, `xref_idx`).
- Arapça metindeki âyet iktibasları çini mavisi alt çizgiyle işaretlenir ve ibare kartını açar. Derece etiketi gösterilmez; yapay zekâ çevirisi yoktur.
- Seçim çapaları `h:tecrid:15@30-58` ve `ht:naim:tecrid:15@…` biçimindedir; kısa dokunuş, uzun basış ve "Seç" yolu 06-mobil/01 §7.3 kuralıdır.
- Uzun hadis (ölçüm: Kütüb-i Sitte'de 5.000 karakteri aşan 45 hadis, en uzunu 14.785) önce tek `FlatList` öğesi ve tek `Text` olarak çizilir. Cihaz ölçümü sorun gösterirse birim görsel parçalara bölünür; parçalar tek `unit` çapasını ve kod noktası ofset tabanını korur (ölçüm kullanıcıya bırakıldı).
- **Bitti sayılır:** RNTL testleri üç görünümü, mütercim başlığını, "doğrulanmamış" rozetini ve "Tecrîd'deki tercümesine git" bağlantısını sınıyor; dikey ve yatay görüntü denetimi kullanıcıya bırakıldı.

### A31.3 · Risale okuyucu
- Paragraflar soldan sağa akar (Literata). Her Arapça dizi ayrı `Text` parçasıdır: Amiri ya da Noto Naskh Arabic, Türkçe boyutun 1,15 katı (`okuma-ar-metin-ici`). iOS'ta parçaya `writingDirection: 'rtl'` verilir (stil yalnız iOS'ta vardır); Android'de yönü platformun Unicode çift yönlü algoritması belirler. Yalnız Arapça olan paragraf (ölçüm: Arapça oranı 0,9 ve üstü olan 3.110 satır) tek Arapça dizi olarak sağdan sola ve sağa hizalı çizilir. Sayfa çevirme yönü soldan sağadır (06-mobil/01 §8).
- Metin kelimesi kelimesine gösterilir; kısaltma, sadeleştirme ve yapay zekâ özeti yoktur; kanonik metne hiçbir şey eklenmez.
- Haşiye işaretleri lâl renktedir ve kısa bir alt sayfa açar (`FootnoteMarker`). "(Bakara Sûresi, 255)" gibi açık atıflar `CitationLink` (noktalı alt çizgi) olur ve A25'in atlama yoluyla açılır.
- Ayarlar › Okuma'da baskı seçilmişse kenarda "s. 61" işaretleri görünür (`page_map`); "Sayfaya git" o baskının sayfa numarasını kabul eder.
- Lügat yoğunluğu Kapalı · Az* · Orta · Çok: kısa anlam kelimeden hemen sonra küçük punto ve ikincil renkle yazılır; metne eklenmez, kopyalanmaz, ofseti değiştirmez. Kelimeye dokunuş `LugatCard` açar (baş kelime, anlam, köken, varsa kök ve "Kur'an'da bu kök", Külliyat'tan örnek). Onaysız anlam "doğrulanmamış" rozetiyle görünür.
- İbare kartı (Arapça diziye dokunuş): `xref_idx`'te seçimle örtüşen `iktibas` ya da `atif` varsa âyet adresi, `core`'dan Unicode metin, Elmalılı meali, "Âyete git" ve "Karşılaştır". Yoksa cihazdaki Kur'an trigram tablosu ("otomatik eşleşme" çipi), sonra yüklü hadis paketleri, sonra "Kaynak bulunamadı" ve Bağlantılar paneline geçiş (01-urun/02 §12; zincir 05-capraz-referans/01 §9).
- Bölüm ağacı, kitap başına yüzde ve kaldığın yer (`reading_position`, `risale:{kitap}`). Kitap paketleri istek anında bağlanır, en çok 3 (LRU); `risale-dizin` bir Risale kitabı yüklüyken bağlıdır (03-veri/03 §2).
- Uzun paragraf (ölçüm: Risale'de 1.000 kod noktasını aşan 522, 3.000'i aşan 1 satır) bir `unit` olarak tek öğe çizilir. Android'de yerleşim süresi `textBreakStrategy` (`simple`, `highQuality`, `balanced`) ile ayarlanabilir; seçim cihaz ölçümüyle yapılır (kullanıcıya bırakıldı).
- **Bitti sayılır:** Gerçek `dev` paketleriyle ve sentetik fikstürle bütün katmanların testleri yeşil; emülatörde görüntü denetimi üç temada kullanıcıya bırakıldı.

### A31.4 · Görünürlük durumları ve derin bağlantılar
- Okuyucu üç durumu ayırır: görünür birim var → okuyucu (onaysız birim "doğrulanmamış" rozetiyle); paket cihazda yok → indirme önerisi (A29 akışı); derlemede görünür birim yok → "Bu içerik bu sürümde yok" durumu ve içeriğin hiçbir parçası.
- Görünürlüğü yalnız `isPackVisible` belirler; ekran derleme türüne bakarak kendi kuralını yazmaz. Lügat yoğunluğu ve baskı sayfa ayarları yalnız Risale metni görünürken etkilidir.
- Derin bağlantılar 01-urun/03 §7 kurallarını izler: yol `packages/anchors` (`fromRoute`) ile çapaya çevrilip doğrulanır; geçerli hedef A25'in atlama kuralıyla açılır; geçersiz adres yuvarlanmaz ve "Bağlantı geçersiz" uyarısı görünür.
- `dev` derlemede fikstür hep görünür; görünürlük durumları RNTL'de sahte görünürlük değerleriyle sınanır. `public` derlemede onaysız birimin ve `test-` önekli fikstürün görünmediği A33'te denetlenir.
- **Bitti sayılır:** Üç durumun ve derin bağlantıların testleri yeşil; `metin-denetcisi` raporu temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; hadis üç görünümü, mütercim başlığı, "doğrulanmamış" rozeti, Risale üç görünürlük durumu, ibare kartının dört sonucu ve `h`, `ht`, `rn` bağlantılarının geçerli ve geçersiz örnekleri test ediliyor.
- [ ] Lügat açıkken kopyalanan seçim ve kaydedilen vurgu aralığı lügat kapalıyken alınanla aynı (birim testi).
- [ ] Türkçe paragraftaki her Arapça dizi ayrı `Text`, Arapça yazı tipiyle ve iOS'ta `writingDirection: 'rtl'` ile çiziliyor (bileşen testi).
- [ ] Hadis ve Risale ekranlarında dokunma hedefleri en az 44×44 pt; "Arapça | Türkçe | İkisi" erişilebilirlik etiketli (`arayuz-denetcisi` raporu).
- [ ] Uygulama kodunda hadis ya da Risale metni yok; testler sentetik metin ya da kaynak dosyasından alınmış parça kullanıyor (`metin-denetcisi` raporu, `git grep` denetimi).
- [ ] `public` bayrağında onaysız birim ve `test-` önekli fikstür listelenmiyor; `internal` bayrağında `test-` önekli kaynaklardan yalnız `test-kucuk` ve `test-ses` var (RNTL).
- [ ] Tedarik: `## Tedarik` tablosundaki her yapının durumu yazılı; A19 ve A20 kaynak kayıtları geçerli (`uv --directory pipeline run mutalaa sources check` hatasız).
- [ ] Emülatörde hadis okuyucusu ve Risale okuyucusu görüntüleri (`.tmp/a31/`) üç temada kullanıcıya bırakıldı.

## Doğrulama
```bash
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -o '"risale-[a-z0-9-]*"' | sort -u   # beklenen: risale-dizin, risale-test-ornek ve A20'nin risale-{kitap} paketleri
uv --directory pipeline run mutalaa sources check   # beklenen: 0 hata
pnpm --filter @mutalaa/mobile test
pnpm lint && pnpm typecheck
git grep -n -i "risaleinur\|Risale-i-Nur-Diyanet" -- apps packages   # beklenen: sonuç yok (kaynak adresleri yalnız pipeline/sources kayıtlarındadır)
```
Emülatör denetimi kullanıcıya bırakıldı (Çalışma düzeni 3); kullanıcı çalıştırırsa:
```bash
mkdir -p .tmp/a31
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://h/tecrid/15"   # pakette ya da fikstürde var olan bir numara
adb exec-out screencap -p > .tmp/a31/hadis.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://kutuphane/risale/test-ornek"   # A20 fikstür kitabı
adb exec-out screencap -p > .tmp/a31/risale-fikstur.png
```

## Dikkat
- Hadis ve Risale metni hafızadan yazılmaz; uygulamaya yalnız A19 ve A20 paketlerinden gelir. Testte sentetik metin ("Deneme paragrafı 1 …") ya da kaynak dosyasından alınmış parça kullanılır.
- Lügat anlamı (Kelime-Frekans deposunun anlam sütunu ve sözlük taramaları) editör onayına kadar "doğrulanmamış"tır (Risale hazırlığı, lügat).
- Geliştirmede kullanılan sentetik `rn:` çapaları kalıcı bir dosyaya ya da kullanıcı verisine yazılmaz (Risale hazırlığı, paragraf çapaları); cihaz denemesinden sonra uygulama verisi temizlenir.
- Hadis Arapçası dağıtıldığı hâliyle gösterilir; okuyucu metni normalize etmez (K-26; `metin-butunlugu`).
- Görünürlük kararı yalnız `isPackVisible`'dadır; ekran derleme türüne bakarak kendi kuralını yazmaz.
- Tarafsızlık: yayınevi markası öne çıkarılmaz; baskılar eşit listelenir, okur seçer (K-25).
- ATTACH sınırı 8 şemadır; Risale kitapları için aynı anda en çok 3 bağ (03-veri/03 §2). Derin bağlantı şeması `src/lib/env.ts`'den okunur, elle yazılmaz (A25).
- Commit kapsamları: `mobile`, `anchors` (yalnız rota yardımcısı değişirse), `pipeline` (fikstür).

## İnsan adımları
- Yok. Cihaz denetimleri kullanıcıya bırakılır ve aşamayı bekletmez. A19'un editör adımları (İ-11, İ-14) ve A20'nin editör adımları (İ-24, İ-28) da bu aşamayı bekletmez: okuyucu onaysız birimi "doğrulanmamış" rozetiyle, onaylı birimi rozetsiz gösterir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/mobile/app/(tabs)/kutuphane/hadis/[koleksiyon]/index.tsx`, `[koleksiyon]/[no].tsx`; `apps/mobile/app/(tabs)/kutuphane/risale/[kitap]/index.tsx`, `[kitap]/[...bolum].tsx`
- `apps/mobile/app/[...capa].tsx` içinde `h`, `ht`, `rn` çözümü
- `apps/mobile/src/features/library/` altında hadis ve Risale modülleri (okuyucu, lügat, ibare kartı)
- Gerekirse `test-` önekli sentetik hadis fikstürü (hat tarafı), i18n anahtarları, testler; `.tmp/a31/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A31-hadis-ve-risale-okuyuculari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A30](./A30-defterim-ve-ilerleme.md) · Sonraki: [A32](./A32-ayarlar-erisilebilirlik-oz-test.md)
