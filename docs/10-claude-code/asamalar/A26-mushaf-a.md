# A26 · Mushaf A (Medine düzeni)

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `arastirmaci` · `hat-gelistirici` ve `sunucu-gelistirici` (A26.0 ve A26.4) · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `icerik-hatti` · `paket-yayini` · `capa-gramer` · **Tahmini oturum:** 4
> **Başlat:** `/asama A26`

## Amaç
Mod A, basılı Medine mushafıyla (QPC V1, 1405 H baskısı) satır satır aynı sayfayı QPC sayfa fontlarıyla çizer; kelime seçimi ve ekran okuyucu için paralel Unicode katmanı sunar. Fontlar ve satır düzeni verisi GitHub'daki hazır bir veri setinden alınır ([Tedarik](#tedarik)). Aşama tedarik doğrulamasıyla başlar (A26.0); sonra Mod A kodu ve testleri, cüz paketleri ve cihaz ölçümleri gelir. Mod A `mushafA` bayrağının arkasındadır; paket görünmüyorsa okuma Mod C ile sürer.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7 ortak sözleşme, §7.1, §7.4, §9, §10 (`mushafA`, `tecvidRenkleri`), §15 (MM-3, MM-4)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.5, §7, §9
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §2 (`qpc-*-font`, `medine-604-duzen`), §3.1
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §5 (veri soyu), §8 (yeni kaynak ekleme)
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 (derleme türleri ve görünürlük), §4 (kalite kapısı kuralları)
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 (Mod A kelime aralığı), §13
- [Backend API](../../02-mimari/05-backend-api.md): §10.3 (P-01, P-11, P-13)
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §9.1 (`page_map.glyphs`)
- [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md): `## Tedarik` ve A11.0 (aynı depo ve commit; `medine-604-duzen` kaydı)

## Kapsam
**Yapılır**
- Tedarik (A26.0): QPC V1 sayfa fontlarının ve Medine 604 satır düzeni verisinin `data/gelen/` altına indirilmesi, SHA-256 ve kaynak kayıtları.
- Mod A kodu: font önbelleği, satır düzeni, isabet testi, jestler, "Seç" yolu, paralel Unicode katmanı (`src/features/reader/mushaf-a/`); sayfa → cüz paketi çözümü; eksik paket şeridi; `mushafA` bayrağı ve mod listesi.
- Cüz paketleri: `mushaf-a-cuz-NN` paket şeması, hat ve Yayınlayıcı desteği, `dev` yayını; cihaz ölçümleri.

**Yapılmaz**
- Mod B ([A40](./A40-mushaf-b.md)); tecvid renkleri V4 (v1.x; `tecvidRenkleri` kapalı kalır).
- Depolama'daki 30 cüzlük ızgara ve indirme kuyruğu (A29); tanıtımdaki "Mod A'yı Wi-Fi ile indir" önerisi (tanıtım ekranının işi; A21'deki nota bakılır).

## Tedarik
Adresler 2 ve 3 Kasım 2026'da açıldı (HTTP 200); sayılar aynı günlerin yerel ölçümüdür. Seçim ölçütü göreve uygunluk, eksiksizlik, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirliktir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)).

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| QPC sayfa fontları (V1, 604 sayfa), besmele ve sure başlığı yazı tipleri | `qpc-v1-font`: GitHub `zonetecde/mushaf-layout` (https://github.com/zonetecde/mushaf-layout), varsayılan dal `v2`, commit `421e9eaa991897ecd50d7abb79160651a45976d3` (2026-10-14); `fonts/QPC1/p001.woff2` … `p604.woff2` (woff2), `fonts/QPC1/QPC1BSML.ttf` (besmele), `fonts/Surahs.ttf` (sure başlığı); basım: Medine mushafı 1405 H (QUL düzen listesinde "Quran Complex V1") | `git clone --depth 1 --filter=blob:none --sparse --branch v2`, ardından `git sparse-checkout set --no-cone fonts/QPC1/ fonts/Surahs.ttf` → `data/gelen/qpc-v1-font/<YYYY-AA-GG>/`; tek dosya: `https://raw.githubusercontent.com/zonetecde/mushaf-layout/421e9eaa991897ecd50d7abb79160651a45976d3/fonts/QPC1/p001.woff2` | 604 `pNNN.woff2`, toplam 48.013.376 bayt (sayfa başına 15.328–119.784); cüz başına 1.428.148–1.687.800 bayt; `QPC1BSML.ttf` 303.644 bayt (574 glif), `Surahs.ttf` 382.580 bayt (317 glif; Arapça harf cmap'i, 462 ligatür); 604 sayfanın 603'ünde düzen dosyasındaki bütün glif kodları sayfa fontunun cmap'indedir (565. sayfada yalnız U+0020 boşluk yoktur); 112 besmele satırının hepsi `QPC1BSML` cmap'indedir | `quran/quran.com-frontend-next` dal `production` commit `aff1a035b09b66f28047b3216edcae4c5c949a49` (2026-03-03): `public/fonts/quran/hafs/v1/woff2/p1.woff2` … (604 dosya; 595'i aynı blob) ve `v1/ttf` (604 dosya, 94.881.448 bayt); `nuqayah/qpc-fonts` (`mustafa0x/qpc-fonts` ile aynı depo) commit `8a4f39d563ea69c994416a1692827e38156c548d`: `mushaf-woff2/QCF_P001.woff2` … (604 dosya ve `QCF_BSML.woff2`, 605 dosya 48.174.208 bayt; 596'sı aynı blob) |
| Medine 604 satır düzeni ve kelime-glif eşlemesi (QPC V1 düzeni) | `medine-604-duzen`: aynı depo ve commit, `mushaf/QPC1/page-001.json` … `page-604.json` (JSON); sayfada `lines[]`: `line`, `type` (`text`, `surah-header`, `basmala`), `verseRange`, `words[]` (`location` = `sure:âyet:kelime`, `word`, `qpcV1`) | Aynı klon; `git sparse-checkout set --no-cone mushaf/QPC1/`; A11.0 aynı klasörü `data/gelen/medine-604-duzen/<YYYY-AA-GG>/` altına aldıysa A26 o kaydı kullanır (commit aynı olmalı) | 604 sayfa; 9.046 satır (602 sayfa × 15, 2 sayfa × 8); 114 sure başlığı, 112 besmele, 8.820 metin satırı; 77.995 kelime girdisi (77.429 kelime ve 566 ayrı âyet sonu girdisi; hepsinde glif); 6.236 âyet, 114 sure; her sayfanın ilk âyeti Tanzil `pages` ile aynı (A11 ölçümü, 604/604); Tanzil Uthmani ile âyet başına kelime sayısı 6.120 âyette aynı, 112 âyette +4 (besmele öneki), 4 âyette +1 (2:181, 8:6, 13:37, 37:130) | Aynı commit'te QPC V2 düzeni (`mushaf/QPC2`, 78.003 girdi; 25 sayfada ilk âyet `core` ile farklı); QUL mushaf düzenleri (https://qul.tarteel.ai/mushaf_layouts; indirme bağlantıları oturum açma ister, bu yüzden birincil değil) |
| İkinci baskı (QPC V2) ve tecvid renkli sayfa fontları (V4) | `qpc-v2-font`: aynı depo ve commit, `fonts/QPC2/p001.woff2` … (604 dosya, 97.748.500 bayt); `qpc-v4-font`: `quran/quran.com-frontend-next` `aff1a035b09b66f28047b3216edcae4c5c949a49`, `public/fonts/quran/hafs/v4/colrv1/woff2/` (604 dosya, 50.877.636 bayt) | Bu aşamada alınmaz; kayıtlar adres ve sürümle güncellenir | QPC V2: ayet kümesi 36 sayfada, ilk âyet 25 sayfada ve satır imzası 354 sayfada QPC V1'den farklıdır; cüz başına woff2 2.552.972–3.934.360 bayt | `MohamadHajjRabee/quran-qcf4` commit `5130511027e769f0a8f4eeb7f00f46bde3788d60` (V4 sayfa JSON'u ve yazı tipleri; içeriği v1.x'te doğrulanır) |
| Mobil kitaplıklar | Expo SDK 58 (`expo` npm `latest` 58.0.22): `expo/expo` dal `sdk-58` `packages/expo/bundledNativeModules.json`: `expo-font ~58.0.11`, `expo-file-system ~58.0.13`, `expo-sqlite ~58.0.15`, `react-native-reanimated 4.7.1`, `react-native-gesture-handler ~3.3.0`, `react-native 0.88.1`; `@shopify/react-native-skia 2.14.0` yalnız bellek bütçesi aşılırsa | A21'de `apps/mobile/package.json`'a yazılır; A26.0'da `npm view <paket> version` ile doğrulanır | `bundledNativeModules.json` adresi HTTP 200 (4.291 bayt); `expo-font` 58.0.11 ve `expo-file-system` 58.0.13 npm `latest` etiketleriyle aynı | Expo `next` etiketi (58.0.11); çizim yolu için yedek `@shopify/react-native-skia` |
| Python yazı tipi araçları (cmap denetimi, gerekirse woff2 → TTF dönüşümü) | PyPI `fonttools` 4.68.0 ve `brotli` 1.2.1 (2 Kasım 2026) | `uv --directory pipeline add fonttools brotli` (A26.4) | Bu tedarik ölçümünde `fontTools.ttLib.TTFont` 604 woff2 dosyasını okudu (cmap, ilerleme genişliği) | — |
| Kur'an Unicode metni, cüz ve sayfa tabloları | A10 (`tanzil-uthmani`) ve A11 (`page_map`, cüz tablosu) çıktıları | `core` paketinden; bu aşamada yeniden alınmaz | A10: 114 sure, 6.236 âyet; A11: 604 sayfa | — |

Kendimiz yapacağımız işler: düzen JSON'unun editoryal `page_map` (`glyphs`) satırlarına ve `glyph_word` tablosuna yüklenmesi (`location` → `q:{sure}:{ayet}:{kelime}` çapası; düzen JSON'undaki `word` ve `text` alanları Kur'an metni olarak alınmaz, kanonik metin Tanzil'dir); `centered` bayrağının üretimi (düzen verisinde bayrak yoktur: besmele ve sure başlığı satırları ortalanır, âyet satırlarında sayfa fontundaki glif ilerleme genişliklerinin toplamı modal tam satır genişliğinin %95'inin altındaysa satır ortalanır; 8.820 âyet satırından 26'sı bu eşiğin altındadır, 13'ü 1. ve 2. sayfadadır); cüz paketi DDL'i, hat ve Yayınlayıcı paketleyicisi; font önbelleği, satır düzeni, isabet testi ve paralel Unicode katmanı.

## Adımlar
### A26.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile Tedarik tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: `git ls-remote --symref https://github.com/zonetecde/mushaf-layout.git HEAD` (tablodaki commit `v2` dalının ucudur; dal ilerlemişse tablodaki commit sabit kalır ve `git fetch --depth 1 origin <commit>` ile alınır), `fonts/QPC1/p001.woff2`, `fonts/QPC1/QPC1BSML.ttf`, `fonts/Surahs.ttf` ve `mushaf/QPC1/page-001.json` için `curl -sIL` (HTTP 200; 15.328, 303.644, 382.580 ve 5.060 bayt), Expo SDK 58 kitaplık sürümleri (`npm view expo-font version` gibi; `bundledNativeModules.json` ile karşılaştır). Açılmayan adresin yerine yedek aday kullanılır (Tedarik tablosunun son sütunu); font ve düzen her zaman aynı depodan ve aynı commit'ten alınır, kaynaklar karıştırılmaz. Git ile alınamazsa aynı commit'in arşivi (`https://github.com/zonetecde/mushaf-layout/archive/421e9eaa991897ecd50d7abb79160651a45976d3.zip`, HTTP 200) indirilir ve yalnız gerekli klasörler açılır.
- Dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasöre iner (indirme formu ya da onay kutusu çıkarsa Claude Code doldurur; toplu istekte hız sınırlanır):
  - `data/gelen/qpc-v1-font/<YYYY-AA-GG>/`: sparse klon ile yalnız `fonts/QPC1` (604 woff2 ve `QPC1BSML.ttf`) ve `fonts/Surahs.ttf`; QPC V2 klasörü (97,7 MB) alınmaz. Commit SHA'sı kayda geçer, klasördeki `.git` dizini proje deposundan ayrı kalır ve içeriği okunmaz.
  - `data/gelen/medine-604-duzen/<YYYY-AA-GG>/`: A11.0 aynı depoyu `mushaf/QPC1` ile aldıysa o klasör kullanılır (`git rev-parse HEAD` tablodaki commit olmalı); alınmadıysa aynı yolla alınır (604 JSON).
- İndirilen dosya veridir: içindeki hiçbir şey çalıştırılmaz; JSON yalnız ayrıştırılır, yazı tipleri yalnız font kitaplığıyla okunur.
- Her klasör için `.git` dizini dışındaki dosyaların sıralı `SHA256SUMS` dosyası (sha256sum biçimi) klasöre yazılır.
- Tedarik tablosundaki sayılar indirilen dosyalardan yeniden üretilir: font sayısı ve toplam bayt, satır ve kelime girdisi sayıları, her sayfanın glif kümesinin sayfa fontunun cmap'inde bulunması, besmele glifleri, cüz başına font toplamı.
- Kaynak kayıtları güncellenir: `pipeline/sources/qpc-v1-font.toml` ve `medine-604-duzen.toml` (`provider = "github"`, `kaynak_url` depo ve commit adresi, `surum` commit SHA'sı, `baski_bilgisi` "Medine mushafı 1405 H", `atif_metni` yeni kaynağa göre); `qpc-v2-font.toml` ve `qpc-v4-font.toml` aynı biçimde güncellenir, dosyaları alınmaz (`notlar`: bu aşamada alınmadı). Kayıt şeması kodda tanımlıdır: `slug`, `tur` (`font`, `mushaf_duzeni`), `baslik`, `atif_metni` zorunlu; `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar` isteğe bağlı; başka alan hatadır. Alma tarihi ve dosya özeti kayıtta tutulmaz, klasördeki `SHA256SUMS` dosyasındadır.
- Kitaplıklar: sürümler `apps/mobile/package.json` ve `npm view` çıktısıyla doğrulanır; A21'de sabitlenen sürüm Tedarik tablosundakinden ayrılırsa fark raporlanır.
- **Bitti sayılır:** `data/gelen/qpc-v1-font/<YYYY-AA-GG>/` (604 `pNNN.woff2`, toplam 48.013.376 bayt; `QPC1BSML.ttf`; `Surahs.ttf`) ve `data/gelen/medine-604-duzen/<YYYY-AA-GG>/` (604 JSON) dolu, ikisinde de `SHA256SUMS` yazılı ve klonların commit'i `421e9eaa991897ecd50d7abb79160651a45976d3`; Tedarik tablosundaki sayılar (9.046 satır, 77.995 kelime girdisi, 6.236 âyet, 114 sure; 603 sayfada tam cmap, 565. sayfada yalnız U+0020; 112 besmele) yeniden üretildi; dört QPC kaydı güncel ve `uv --directory pipeline run mutalaa sources check` 0 hata ve 0 uyarıyla bitiyor.

### A26.1 · Teknik doğrulamalar
- `arastirmaci` (SDK 58 için): expo-font'un yerelde woff2 kabulü (MM-3; Expo font belgesi biçim listesi vermiyor, örneklerde `.ttf` ve `.otf` var); `loadAsync`'te `file://` kaynağı (belge `FontSource` olarak string, modül kimliği, Asset ve `{ uri }` nesnesini sayıyor, `file://` anılmıyor); boşaltma yöntemi ve `ERR_UNLOAD` (MM-4; belge hata kodunu listeliyor, boşaltma API'sini belgelemiyor); Reanimated 4'te JS'e geri çağırma API'si; Android'de `accessibilityLanguage` karşılığı; expo-sqlite'ın `ArrayBuffer` değişikliğinin BLOB okumaya etkisi.
- woff2 yerelde kabul edilmezse hat woff2'yi TTF'ye çevirir (A26.4, `fonttools`); beklenen boyut cüz başına yaklaşık 3,0–3,4 MB (V1 TTF, quran.com listesi) ve ölçümle doğrulanır.
- **Bitti sayılır:** doğrulama sonuçları dokümanda (Mobil mimari §7.1 ve §15, MM-3 ve MM-4).

### A26.2 · Mod A kodu ve birim testleri
- `fontCache.ts` Mobil mimari §7.1'deki gibidir: aile adı `QPC_P{sayfa:3 hane}_{sürüm}`; font BLOB'u ayrı salt okunur bağlantıdan (A23 `src/db/packs.ts`) okunup `Paths.cache/mutalaa/qpc/` altına yazılır; `Font.loadAsync`; etkin küme `MAX_ACTIVE = 12` (ölçümle ayarlanır); okuma yönünde iki ileri, bir geri ısıtma; sayfa sınırı 1–604.
- Sayfa → paket: sayfa, ilk âyetinin bulunduğu cüzün paketine girer (İçerik paketleri §3.5); cüz verisi `core`'dan (A11 tablosu).
- Satır düzeni: satır başına bir `View`, kelimeler mantıksal sırayla ayrı `Text`, `flexDirection: 'row-reverse'`; `I18nManager` çevrilmez; glif metni `allowFontScaling={false}`; büyütme sayfa yakınlaştırmasıyla. Tam satırların toplam glif genişliği modal değerden ±%5 sapar (8.820 âyet satırının 8.671'i bu bantta, 123'ü daha geniş, 26'sı daha dar); satır kutusuna ölçeklenerek ya da `space-between` ile sığdırılır, `centered` satırlar ortalanır (A26.5'te ölçülür).
- Besmele ve sure başlığı satırları: besmele, satırdaki `qpcV1` kodlarıyla `QPC1BSML` fontunda; sure başlığı `Surahs.ttf` ile çizilir. `Surahs.ttf` Arapça harf cmap'i ve bağlamsal biçim kuralları (462 ligatür) taşır, yani sure adı Unicode metin olarak verilir; ad `core` sure tablosundan gelir (A11), düzen dosyasındaki `text` alanından alınmaz. İki yazı tipi küçüktür (303.644 ve 382.580 bayt) ve uygulamaya expo-font eklentisiyle gömülür (öneri).
- İsabet testi (`hitTest.ts`): isabet alanı satır yüksekliğine ve en az 44 pt genişliğe büyür. Kısa dokunuş kelime kartını (A25), 350 ms uzun basış ve sürükleme seçimi başlatır; jest gerektirmeyen "Seç" yolu A25'teki akışla aynıdır.
- Paralel Unicode katmanı: glif katmanı ekran okuyucudan gizlidir. Her âyet için görünmez bir erişilebilir öğe Türkçe adres etiketi ve `core`'daki Arapça Unicode metni taşır; iOS'ta `accessibilityLanguage="ar"`. Kopyalama seçilen çapaların Tanzil Unicode metnini kopyalar; glif kodu asla kopyalanmaz.
- Etkin âyet ve kelime glifler üzerinden vurgulanır; kullanıcı vurguları kelime çapasıyla glife eşlenir (veri A30'da gelir).
- **Bitti sayılır:** birim testleri yeşil: `familyName`, `hitTest` (dar kelimede 44 pt genişleme, en yakın merkez), sayfa → cüz eşlemesi, ısıtma sınırları, kopyalamanın Unicode metin döndürmesi.

### A26.3 · Bayrak, mod listesi ve eksik paket
- `mushafA` `'paket'` kuralıyla açılır: derleme türünde görünür bir `mushaf-a-cuz-*` paketi yoksa kapalıdır (`isPackVisible`, A23). Paketler kaynak kaydı taşıdığı için (P-01) `dev`, `internal` ve `public` derlemelerinde görünür (Mobil mimari §7.4 ve §10; Yayın süreci §3).
- Mod A seçiliyken cüz paketi kurulu değilse sayfa Mod C ile çizilir ve üstte `reader.cuzMissing` şeridi görünür: "Bu cüzün Medine düzeni indirilmedi · İndir". "İndir" A29'un kuyruğuna devreder; A29'a kadar Depolama rotasını açar. Okuma hiçbir zaman beklemez.
- **Bitti sayılır:** RNTL testleri yeşil: görünür paket yokken (her derleme türünde) seçenek listede yok; paket görünür ama cüz kurulu değilken Mod C ve şerit.

### A26.4 · Cüz paketleri
- Paket DDL'i `packages/content-schema/sql/` altına İçerik paketleri §3.5'e göre yazılır: `page_font`, `page_line`, `glyph_word`.
- `hat-gelistirici`: A26.0'da alınan düzeni ve fontları içerik hattıyla `data/raw` → `staged` → editoryal `page_map` satırlarına işler (`source_id = 'medine-604-duzen'`; `line`, `line_type`, `centered`, `glyphs`); `location` çapaya `mutalaa_pipeline.anchor` ile çevrilir, ayrı âyet sonu girdisi `end` işaretlenir; kelime sayısı `quran_word` ile âyet âyet aynı olmalıdır (A11'deki dört birleştirme: 2:181, 8:6, 13:37, 37:130); `centered` Tedarik bölümündeki kuralla üretilir. `fonttools` ve `brotli` hat bağımlılığı olarak eklenir; sayım ve cmap denetimi pytest olarak yazılır.
- `sunucu-gelistirici`: Yayınlayıcı `mushaf-a-cuz-{01..30}` paketlerini üretir; P-01, P-11 ve P-13 uygulanır; atıf, kaynak kaydından `attribution` tablosuna aynen yazılır.
- `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev` ile paketler `dev` manifestine girer.
- **Bitti sayılır:** `dev` manifestinde 30 `mushaf-a-cuz-*` girişi var; `publish --flavor public --dry-run` 0 ile biter ve kapı raporu 30 paketi "girdi" gösterir.

### A26.5 · Cihaz ölçümleri ve görsel denetim
- Cüz paketleri geliştirici menüsündeki basit indirme düğmesiyle kurulur (öneri; asıl kuyruk A29'dadır).
- `mobil-gelistirici` ölçer ve dokümana işler: woff2 ya da TTF ile paket boyutu (MM-3; V1 woff2 için cüz başına 1,4–1,7 MB beklenir); 604 sayfa baştan sona çevrilirken bellek (MM-4; bütçe ortalama < 200 MB, Mobil mimari §9); tam satırların iki yana yaslanması ve ortalanmış satırlar. Bütçe aşılırsa `@shopify/react-native-skia` değerlendirmesi Açık soru olarak `/karar`'a götürülür.
- Görsel denetim: 1. sayfa ve Bakara 255'in sayfası Mod A'da, üç temada; kelimeye dokununca kelime kartı; "Seç" yolu. `arayuz-denetcisi` TalkBack ile âyet öğesinin Türkçe etiket ve Arapça metinle okunduğunu denetler.
- Emülatör ve cihaz adımlarını kullanıcı yürütür; ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" yazılır, aşama bekletilmez.
- **Bitti sayılır:** ölçümler dokümanda; görüntüler ve rapor `.tmp/a26/` altında.

## Kabul ölçütleri
- [ ] A26.0: `qpc-v1-font` ve `medine-604-duzen` klasörleri `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında dolu, `SHA256SUMS` yazılı, commit `421e9eaa991897ecd50d7abb79160651a45976d3`; dört QPC kaydı güncel; `uv --directory pipeline run mutalaa sources check` 0 hata, 0 uyarı.
- [ ] Tedarik tablosundaki sayılar (604 font, 9.046 satır, 77.995 kelime girdisi, 6.236 âyet; cmap denetimi) indirilen dosyalardan yeniden üretildi.
- [ ] A26.1 doğrulamaları dokümanda (MM-3, MM-4).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: `familyName`, `hitTest`, sayfa → cüz, ısıtma sınırları, Unicode kopyalama, mod listesi, eksik paket şeridi.
- [ ] Görünür `mushaf-a-cuz-*` paketi yokken Mod A seçeneği yok (test); paket görünürse seçenek listelenir.
- [ ] `dev` manifestinde 30 `mushaf-a-cuz-*` girişi; `public` kuru çalıştırması 0 ile biter ve kapı raporu 30 paketi "girdi" gösterir.
- [ ] MM-3 ve MM-4 ölçümleri dokümanda; Mod A görüntüleri ve `arayuz-denetcisi` raporu temiz (cihaz adımları kullanıcıya bırakıldı).

## Doğrulama
```bash
uv --directory pipeline run mutalaa sources check
git -C data/gelen/qpc-v1-font/<YYYY-AA-GG> rev-parse HEAD
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
# Paketler üretildikten sonra:
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -oE '"mushaf-a-cuz-[0-9]{2}"' | sort -u | wc -l
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
# Görsel denetim (kullanıcı yürütür):
mkdir -p .tmp/a26
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://oku/fihrist"
adb shell input text "1:1"
adb shell input keyevent 66
adb exec-out screencap -p > .tmp/a26/mod-a-sayfa-1-kagit.png
```
Yayınlayıcının `--dry-run` kapı raporu ayrıca okunur. Görüntüden önce "Aa" › Çizim yolu'ndan Mod A seçilir; görüntü üç tema için tekrarlanır.

## Dikkat
- Font ve düzen verisi aynı depodan ve aynı commit'ten alınır; kaynaklar karıştırılmaz: QPC V1 woff2 dosyalarının 9 sayfası quran.com kopyasından, 8 sayfası `nuqayah/qpc-fonts` kopyasından bayt olarak farklıdır.
- QPC V1 düzeni core `page_map` ile (Tanzil `pages`) aynı sayfa sınırlarını verir; QPC V2 25 sayfada ayrılır. V2 seçilirse ayrı düzen kimliği gerekir.
- Düzen JSON'undaki `word` ve `text` alanları Kur'an metni olarak alınmaz; kanonik metin Tanzil'dir (K-26). Bu alanlar yalnız Tanzil ile harf iskeleti karşılaştırmasında kullanılır.
- Glif kodu kelimeyle ilgisiz bir sunum kod noktasıdır; kopyalama, arama ve ekran okuyucu her zaman Tanzil Unicode metnini kullanır.
- Kur'an metni elle yazılmaz; paralel katmandaki metin `core`'dan okunur.
- Tecvid renkleri (COLRv1, V4) bu aşamada açılmaz; `tecvidRenkleri` bayrağı kapalı kalır.
- Git Bash `/` ile başlayan bağımsız değişkeni Windows yoluna çevirir (`/fonts/QPC1/` olur `C:/Program Files/Git/fonts/QPC1/`); sparse-checkout desenleri başında `/` olmadan yazılır (Git, tek dosya deseni `fonts/Surahs.ttf` için uyarı verir; desen yine de çalışır, denendi).
- Commit kapsamları `mobile`, `content-schema`, `pipeline`, `publisher`.

## Çıktılar
- `data/gelen/qpc-v1-font/<YYYY-AA-GG>/` ve `data/gelen/medine-604-duzen/<YYYY-AA-GG>/` (git dışı) ile `SHA256SUMS` dosyaları; güncellenen `pipeline/sources/qpc-v1-font.toml`, `qpc-v2-font.toml`, `qpc-v4-font.toml` ve `medine-604-duzen.toml`
- `apps/mobile/src/features/reader/mushaf-a/`: `fontCache.ts`, `hitTest.ts`, `useWordGestures.ts`, satır düzeni ve Unicode katmanı bileşenleri, testler
- Mod listesi ve `reader.cuzMissing` şeridi; geliştirici menüsünde indirme düğmesi (öneri)
- `packages/content-schema/sql/` Mod A DDL'i, hat ve Yayınlayıcı ekleri
- Doğrulama sonuçları ve ölçüm sonuçları; `.tmp/a26/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A26-mushaf-a.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A25](./A25-secim-kelime-karti-baglantilar.md) · Sonraki: [A27](./A27-ses-sistemi.md)
