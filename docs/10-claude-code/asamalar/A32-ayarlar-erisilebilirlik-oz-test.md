# A32 · Ayarlar, ilk açılış, erişilebilirlik, kaynaklar, öz test

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A29](./A29-kutuphane-ve-depolama.md) · **İnsan adımı:** İ-27
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `test-vektoru` · `metin-butunlugu` · **Tahmini oturum:** 4–5
> **Başlat:** `/asama A32`

## Amaç
Ayarlar ağacını 01-urun/03 §6'ya göre tamamlar ve erişilebilirlik kurallarını bütün uygulamada uygular: ayrı Arapça ve Türkçe yazı boyutu, %200 büyütme, Hareketi Azalt, 44×44 pt dokunma hedefi ve ekran okuyucu için Unicode katmanı. Kaynaklar ekranını (B-07) paketlerdeki atıf verisinden ve açık kaynak bağımlılık listesinden kurar. Ortak test vektörlerini Hermes'te koşan, yalnız `dev` derlemedeki öz test ekranını ve kişisel veri içermeyen hata raporunun anahtarını ve denetimini (B-12) ekler. İlk açılış tanıtımını (01-urun/03 §5) da yazar; A21 yalnız rotasını açmıştı. Aşama tedarikle başlar (A32.0): kitaplık sürümleri doğrulanır, tanıtım ve boş durumlar için ebru görseli indirilir.

## Okunacak belgeler
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 `ayarlar/*` ve `onboarding/index.tsx`, §3.2 Kaynaklar satırı, §5 ilk açılış, §6 ayarlar ağacı ve hizalama notları, §9 ME-3, ME-4 ve ME-5
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 Kaynaklar ekranı notu, §5 `useSettings`, §10 bayraklar, §11 hata türleri, §12 Sentry, §13 erişilebilirlik, §14 Türkçe harf ve `Intl`
- [Gizlilik](../../07-yayin/02-gizlilik.md): tamamı; özellikle §2.2, §2.3, §2.5, §2.7, §4
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §6 Kaynaklar ekranı
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 kaynak kaydı ve atıf, §2 özet tablo, §3 kaynak kartları (atıf satırları)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.1 `attribution` tablosu
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §3 bağımlılık listesi
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §3.2 kademeler, §4 dokunma hedefi, §5 hareket, §9 kontrol listesi
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §13 erişilebilirlik
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 öz test, §11 erişilebilirlik
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §7 hangi ayar nerede durur

## Kapsam
**Yapılır**
- A21'in yer tutucu ayar rotaları doldurulur: `ayarlar/index`, `gorunum`, `okuma`, `mushaf`, `erisilebilirlik`, `kaynaklar`, `hakkinda`; geliştirici menüsüne öz test satırı ve yeni rota `ayarlar/gelistirici/oz-test.tsx` (öneri ad). Başka aşamada dolmuş ekran yeniden yazılmaz, ağaca bağlanır.
- Meal seçimi ayarı (`ayarlar/okuma`): orijinal ya da "sadeleştirilmiş" Elmalılı meali; iki meal arasında seçim A16'dan bu aşamaya devredildi ([K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)); gösterim A24'tedir.
- Ayar deposu: `theme` içinde `sistem`, `arabicScale` ve `turkishScale` için kademe eşlemesi, Hareketi Azalt ve dokunsal geri bildirim tercihleri, ayar göç testleri.
- 06-mobil/01 §13'teki erişilebilirlik uygulaması, bütün ekranlarda.
- Kaynaklar (atıf satırları ve açık kaynak bağımlılık listesi), Hakkında (gizlilik metni dahil), "Verilerimi sil".
- "Hata raporları" anahtarı ve A21'in `src/lib/telemetry.ts` kurulumunun denetimi; öz test ekranı.
- İlk açılış tanıtımı (`onboarding/index.tsx`): dört adım, her adımda "Atla", derin bağlantıyla ilk açılışta kısa yol; tamamlandı bilgisi MMKV'de; Hakkında'daki "Tanıtımı yeniden göster" onu açar.

**Yapılmaz**
- Depolama: A29. Okuyucu ve dinleme: A27. İlerleme satırlarının işlevi ve yedek: A30. Tasarım vitrini: A22. Arama ölçümü: A28. Sentry'nin ilk kurulumu: A21.
- Maestro akışları, referans cihazda elle erişilebilirlik ve performans ölçümü: A33. Mağaza beyanları, gizlilik metninin son hâli ve kaynak eşlemesi yüklemesi: A34.
- Tecvid renkleri, artırılmış kontrast, ek yazı tipleri: v1.x. Başka arayüz dilleri: faz atanmadı. Hesap ve hesaplı sürümün gizlilik metni: A35.

## Tedarik
A32 içerik metni almaz; kitaplık, araç, bir görsel ve bir hizmet hesabı alır. Sürümler 3 Kasım 2026'da npm kaydından ve Expo SDK 58 paket listesinden okundu (`expo/expo` `sdk-58` dalı HEAD `ea4641ff248845e582cba1afdc5d7bf714f5b9ad`; `packages/expo/bundledNativeModules.json` 4.291 bayt, SHA-256 `3b2c9d80113acb8ff74b6203c884196f70299bce4da7bb4b46a7faa41d41300d`). Ölçülmeyen hücreler A32.0'da doldurulur.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Hata izleme SDK'sı (A21 kurar, A32 denetler) | `@sentry/react-native` (npm; `getsentry/sentry-react-native`); Expo SDK 58 paketi `~8.28.0` (npm'de 24 Eylül 2026; etiket `8.28.0` = commit `e6f7b497f23cf35d85fda696066ba2cd9ae72206`; bağımlı `@sentry/core` 10.75.2); npm `latest` 8.33.0 (29 Ekim 2026; etiket `87468d75b86f58613fefb554926d0fc72b34f7cc`); Expo eklentisi `@sentry/react-native/expo` | `npx expo install @sentry/react-native` (SDK'ya uygun sürümü seçer) | SDK 58 `bundledNativeModules.json` kaydı `~8.28.0`; 8.28.0 paketinin `options.d.ts` dosyasında `sendDefaultPii` (satır 119), `attachScreenshot` (331), `attachViewHierarchy` (367); `@sentry/core` 10.75.2'de `tracesSampleRate`, `beforeSend`, `beforeBreadcrumb` tanımlı | Bugsink (Sentry SDK'larıyla uyumlu, kendi sunucumuzda; `bugsink/bugsink` HEAD `bdd593fe3e1a50a4ffe0d469e0d87bf4e4847ba7`) |
| Hata izleme hizmeti ve projesi | Sentry barındırılan hizmeti (hesap: altyapı, İ-27); belge `https://docs.sentry.io/platforms/react-native/` | Kullanıcı hesabı ve projeyi açar, DSN'yi `apps/mobile/.env.local` ve EAS ortamına yazar | Belge sayfaları açılıyor (HTTP 200). Sentry belgesine göre IP adreslerinin saklanması engellenebilir (Security & Privacy › Data Scrubbing; ayarın adı belgede geçmez, A32.1'de arayüzden doğrulanır); IP kapalıyken coğrafi bilgi yine IP'den çıkarılır, kaldırmak için ileri veri temizleme kuralı gerekir. Veri konumu ABD (Iowa) ya da AB (Frankfurt); organizasyon açılırken seçilir ve sonradan değişmez (`https://docs.sentry.io/organization/data-storage-location/`) | Bugsink (hesap gerekmez) |
| Dokunsal geri bildirim | `expo-haptics` `~58.0.7` (npm, 16 Ekim 2026; SDK 58 paketi; eş bağımlılık `expo`) | `npx expo install expo-haptics` | SDK 58 `bundledNativeModules.json` kaydı `~58.0.7`; Expo belgesi (`https://docs.expo.dev/versions/v58.0.0/sdk/haptics/`, HTTP 200) örneklerinde `impactAsync`, `notificationAsync`, `selectionAsync` | React Native `Vibration` (yerleşik) |
| Cihaza özgü ayar deposu (A21 kurar) | `react-native-mmkv` 4.3.2 (npm, 22 Haziran 2026; etiket `v4.3.2` = commit `d18f177336a803ce1fa6c24dca13bcc824c743e7`; eş bağımlılık `react-native-nitro-modules`, npm `latest` 0.37.1, 27 Ağustos 2026) | A21'de kurulu; A32.0 sürümü paket kaydından doğrular | npm kaydı; Expo SDK 58 listesinde yok, sürümü `pnpm-lock.yaml` sabitler | `@react-native-async-storage/async-storage` 2.2.0 (SDK 58 paketi; npm `latest` 3.1.1) |
| Ekran okuyucu ve Hareketi Azalt okuması | React Native `AccessibilityInfo` (`react-native` 0.88.1 ve `react` 19.3.0, Expo SDK 58 listesi; ek paket yok) | Yerleşik | Belge `https://reactnative.dev/docs/accessibilityinfo` (HTTP 200) örneğinde `isReduceMotionEnabled`, `isScreenReaderEnabled`, `addEventListener('reduceMotionChanged' \| 'screenReaderChanged')` ve `announceForAccessibility` geçiyor; Android okuyuşu `AccessibilityInfoModule.kt` kaynağından A32.1'de doğrulanır | `react-native-reanimated` `useReducedMotion` (4.7.1, SDK 58 paketi; eş bağımlılık `react-native-worklets` 0.13.0) |
| Bileşen testi ve erişilebilirlik sorguları | `@testing-library/react-native` 14.1.0 (npm, 8 Ekim 2026; etiket `v14.1.0` = commit `5519b249c14f278a30bf3e0a55217523cab36734`) ile `jest-expo` `~58.0.13` (npm, 28 Ekim 2026) | A21'de kurulu; A32.0 sürümü paket kaydından doğrular | npm kaydı: RNTL eş bağımlılıkları `test-renderer` ^1.0.0, `jest` ≥ 29, `react` ≥ 19, `react-native` ≥ 0.78; `jest-expo` `@react-native/jest-preset` ^0.88.1 ve `jest` ^29 \|\| ^30 ister (RN 0.88.1 ile uyumlu); `getByRole`, `getByLabelText` ve erişilebilirlik eşleştiricileri A32.0'da RNTL belgesinden (`https://callstack.github.io/react-native-testing-library/`, HTTP 200) doğrulanır | Yok |
| Erişilebilirlik lint kuralları | `eslint-plugin-react-native-a11y` 3.5.1 (npm, 4 Kasım 2024; etiket `v3.5.1` = commit `e09227abfc739919c93ed8897c7844037fef2b98`) | `pnpm add -D`; uyum A32.0'da ölçülür | npm kaydında eş bağımlılık `eslint` ^3 … ^8; depoda ESLint `^10.13.0`. Paketin `lib/` kodunda kaldırılan `context.getScope`, `getAncestors` ya da `getDeclaredVariables` çağrısı yok (yalnız `sourceCode` yoksa devreye giren `getSourceCode` yedek yolu var). Fiili uyum bir fikstür dosyasında ESLint 10 ile A32.0'da ölçülür | `@react-native-ama/core` 2.0.0 (npm, 20 Ekim 2026); kendi RNTL taramamız |
| Cihazda erişilebilirlik denetimi | TalkBack (`com.google.android.marvin.talkback`) ve Accessibility Scanner (`com.google.android.apps.accessibility.auditor`), Google Play | Emülatörde ve cihazda kullanıcı çalıştırır (kullanıcıya bırakıldı) | İki Play sayfası açılıyor (HTTP 200) | Android erişilebilirlik testi kılavuzu (`https://developer.android.com/guide/topics/ui/accessibility/testing`, HTTP 200) ve `google/Accessibility-Test-Framework-for-Android` (HEAD `c65cab02b2a845c29c3da100d6adefd345a144e3`) |
| Açık kaynak bağımlılık listesi | Depodaki `scripts/ci/list-licenses.mjs` (A08); `pnpm licenses list -r --json --prod` çıktısını okur, `--json <dosya>` ile `[{name, version, license}]` yazar | Depoda hazır; `apps/mobile` için çalıştırma A32.0'da | Betik depoda; bugün `apps/mobile` yok ve pnpm `--prod` kümesi boş, paket sayısı A32.0'da ölçülür | `react-native-legal` 1.9.0 (npm, 22 Ekim 2026; `callstackincubator/react-native-legal` HEAD `9dcd9882803088e4d26e5ebf60b8227d0b53eea5`; eş bağımlılık `expo` ≥ 52) |
| İçerik, ses ve yazı tipi atıf satırları | Kaynak kayıtları (`pipeline/sources/*.toml`, A06) ve paketlerin `attribution` tablosu (A13) | Koda yazılmaz; paketten okunur | `uv --directory pipeline run mutalaa sources check` çıktısı 3 Kasım 2026'da "25 kayit, 0 hata, 0 uyari"; arayüz yazı tipi kayıtlarını A21, ses kaynağı kayıtlarını A27 açar | Yok |
| Tanıtım ve boş durum ebru görseli | Wikimedia Commons ebru dosyaları, öncelik sırasıyla: `File:Taraklı Gel Git Ebru.jpg` (1193×1783 px, 726.279 bayt), `File:Battal Ebru.jpg` (1509×1835 px, 515.627 bayt), `File:Hatip Yürek Ebru.jpg` (2496×1699 px, 523.776 bayt); üçü JPEG | Doğrudan dosya, `curl` ile: `https://upload.wikimedia.org/wikipedia/commons/d/d4/Tarakl%C4%B1_Gel_Git_Ebru.jpg`, `.../c/c2/Battal_Ebru.jpg`, `.../f/f1/Hatip_Y%C3%BCrek_Ebru.jpg`; seçilen tek dosya `data/gelen/ebru-motifi/<YYYY-AA-GG>/` altına iner | Commons API'sinde üç dosyanın boyutu ve SHA-1 değeri örnek kopyalarla aynı (`e260bc6ff1…`, `1cbcf86c47…`, `ef9b367b6d…`); üç dosya sayfası açılıyor; Battal ve Hatip dosyaları HTTP 200, Taraklı dosyası istek sınırı nedeniyle (429) başlık vermedi, yol dosya adının MD5 kuralıyla türetildi ve A32.0'da indirilirken doğrulanır | Kendi SVG ebru desenimiz |
| Hermes `Intl` ve düzenli ifade desteği (öz test) | Hermes belgeleri `doc/IntlAPIs.md` (11.053 bayt) ve `doc/Features.md` (2.768 bayt); `facebook/hermes` HEAD `2f82501597d8659df644b547ffa89931f4d80092` | `https://raw.githubusercontent.com/facebook/hermes/main/doc/IntlAPIs.md` ve `.../Features.md` okunur | İki adres HTTP 200; `IntlAPIs.md` `Intl.NumberFormat` ile `toLocaleLowerCase` ve `toLocaleUpperCase` listeler; `Features.md` adlı yakalama gruplarını "planlanan" sayar. Belge eski olabilir; gerçek destek öz test ekranında cihazda ölçülür (A32.5) | Yok |
| Dışa aktarılan JS paketinde vektör denetimi | `expo export` (Expo CLI; `expo` 58.0.22, npm `latest`) | Yerleşik (`npx expo export`) | Expo CLI belgesi (`https://docs.expo.dev/more/expo-cli/`, HTTP 200): `--platform <ios\|android\|all>` (varsayılan all), `--output-dir <dir>` (varsayılan dist), `-c, --clear`, `--no-minify` | Yok |

Kendimiz yapacağımız işler: ayar deposunun göçü ve ekranları, `FontSizeSlider`, erişilebilirlik uygulaması (etiket, rol, 44×44 pt hedef, ekran okuyucu Unicode katmanı), Kaynaklar ekranının kodu (veri paketlerden ve bağımlılık listesinden gelir), öz test koşucusu, hata raporu süzgeçleri ve testleri, ilk açılış tanıtımı ekranları, ebru görselinin kırpılıp sıkıştırılması.

## Adımlar
### A32.0 · Tedarik doğrulaması ve indirme
- `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu `arastirmaci` ile doğrula (npm kaydı, Expo SDK 58 paket listesi, GitHub etiketleri, belge sayfaları). Açılmayan adresin yerine yedek adayı kullan.
- Kitaplıklarda sürümü paket kaydından doğrula: `npx expo install` ile gelen sürüm SDK 58 listesindeki aralıkta kalır (`@sentry/react-native` `~8.28.0`, `expo-haptics` `~58.0.7`); `react-native-mmkv` SDK listesinde olmadığından npm kaydındaki 4.3.2 ve `react-native-nitro-modules` eş bağımlılığıyla kurulur; RNTL 14.1.0 `test-renderer` ^1.0.0 eş bağımlılığını ister. `eslint-plugin-react-native-a11y` 3.5.1'in ESLint 10 ile çalışıp çalışmadığı bir fikstür dosyasında ölçülür; çalışmazsa yedek aday (kendi RNTL taramamız ya da `@react-native-ama/core`) kullanılır. Sürümler `pnpm-lock.yaml`'a ve Teknoloji yığını tablosuna işlenir.
- Ebru görselini indir: tablodaki öncelik sırasıyla ilk dosya (Taraklı Gel Git Ebru); görsel kalite ya da kırpma yetmezse sıradaki. Dosya `data/gelen/ebru-motifi/<YYYY-AA-GG>/` altında yeni boş klasöre iner (tek dosya, istek hızı sınırlı; Wikimedia 429 verirse istek aralığı artırılıp yeniden denenir). Klasörde `SHA256SUMS` dosyasına (sha256sum biçimi) SHA-256 yazılır ve değer Tedarik notundaki örnek kopyanın özetiyle karşılaştırılır. İndirilen görsel veridir; dosyayla gelen hiçbir şey çalıştırılmaz.
- Kaynak kaydını yaz: `pipeline/sources/ebru-motifi.toml` (zorunlu `slug`, `tur`, `baslik`, `atif_metni`; `kaynak_url` ve `atif_url` Commons dosya sayfası; `surum` seçilen dosyanın Commons sürümü). `tur` listesinde süs görseli türü olmadığından en yakın değer `mushaf_gorseli` kullanılır; ayrı tür gerekirse A06 şeması `/karar` ile genişler.
- `uv --directory pipeline run mutalaa sources check` hatasız bitmelidir.
- **Bitti sayılır:** Tablodaki her satırın adresi açıldı, sürümler pakete yazıldı, indirilen görselin SHA-256'sı `SHA256SUMS` dosyasında kayıtlı ve kaynak kaydı `sources check` ile geçerli.

### A32.1 · Önkoşul, doğrulamalar ve kararlar
- Dolu ve yer tutucu ayar ekranlarını, `useSettings` deposunu ve A21'in `telemetry.ts` dosyasını listele; 01-urun/03 §6 ağacıyla karşılaştır.
- `arastirmaci` resmî belgeden doğrular (Tedarik tablosundaki kanıtlar başlangıç noktasıdır; dokunsal geri bildirim modülü ve `expo export` bayrakları tabloda doğrulandı): Sentry projesinde IP saklamayı kapatan ayarın adı ve konumu ile IP kapalıyken coğrafi bilginin ileri veri temizleme kuralıyla kaldırılması (Gizlilik §2.2; A34'te yeniden bakılır), Android'de Hareketi Azalt ayarının `isReduceMotionEnabled` ile okunuşu, açık kaynak bağımlılık listesinin kapsamı (yalnız mobil uygulamanın üretim bağımlılıkları; `pnpm licenses` ve `--filter` kullanımı, 02-mimari/02 §3), vektörleri yalnız `dev` JS paketine koyma yöntemi (ME-3 ile aynı soru), `maxFontSizeMultiplier` için önerilecek değer.
- Kullanıcıya sorulur ve `/karar` ile yazılır:
  1. "Hata raporları" varsayılanı (ME-4; Gizlilik §5 madde 1). Öneri: açık; gizlilik metninde yazılı ve tek dokunuşla kapanır.
  2. "Verilerimi sil" için onay penceresi. Satırın yeri belgelerde eşitlendi (19 Ekim 2026): 01-urun/03 §6'da İlerleme ve gizlilik altında (Gizlilik §2.5, §2.7). Öneri: onay penceresiyle.
  3. **Çözüldü (19 Ekim 2026):** ekran adı 01-urun/03 §6'daki "İlerleme ve gizlilik"tir; Gizlilik §2.2 ve §2.5 bu ada uyduruldu.
- Sentry hesabı ve projesi İ-27'dir. Kullanıcı açar; organizasyonu açarken veri konumunu (ABD ya da AB) seçer, bu seçim sonradan değişmez (öneri: AB, Frankfurt). DSN değerini `apps/mobile/.env.local` ve EAS ortamına kendisi yazar (Claude Code `.env` okumaz).
- **Bitti sayılır:** Doğrulama sonuçları ve iki karar (madde 1–2) yazılı.

### A32.2 · Ayarlar ağacı ve depo
- Ağaç 01-urun/03 §6: Görünüm (tema Sistem* · Kâğıt · Âhar · Gece; Arapça ve Türkçe boyut 10 kademe, varsayılan 5, cihaza özgü; Türkçe yazı tipi Literata), Okuma, Mushaf (görünmeyen çizim yolu listelenmez), Okuyucu ve dinleme, Depolama, İlerleme ve gizlilik, Erişilebilirlik, Kaynaklar, Hakkında, Geliştirici (`gelistiriciMenusu`: yalnız `dev` ve `internal`).
- Kademe değerleri 01-urun/04 §3.2'den gelir (Türkçe 14…36 pt, Arapça 22…60 pt); depo çarpan tutar. Cihaza özgü ayarlar yalnız MMKV'dedir; diğerleri 03-veri/04 §7'ye göre `setting` tablosuna da yazılır.
- `FontSizeSlider` artı ve eksi düğmelidir ve canlı önizleme taşır; değişiklik önizleme bölgesinde anında görünür.
- Hakkında: sürüm, derleme türü, içerik paket sürümleri, ilkeler (K-25), gizlilik metni (Gizlilik §2.5 taslağı; yayıncı adı ve iletişim satırı yer tutucudur, mağaza hesabı açılırken belli olur: İ-15) ve "Tanıtımı yeniden göster".
- "Verilerimi sil" (01-urun/03 §6, İlerleme ve gizlilik; onay penceresi A32.1 kararıyla): `user.db`'yi, ayarları ve son aramaları siler (Gizlilik §2.7), paketlere dokunmaz.
- Ayar göçü: kalıcı depo sürümü artınca eski kayıt kaybolmadan taşınır (01-urun/01 §4.10).
- **Bitti sayılır:** Ayar göç testi ve "Verilerimi sil" testi yeşil; ağaçtaki her satır bir ekrana ya da işleve bağlı.

### A32.3 · Erişilebilirlik uygulaması
- Yazı: okuma metni kademe × sistem ölçeğiyle en az %200'e çıkar; Arapça ve Türkçe ayrı ayarlanır. Arayüz metni sistem ölçeğini `maxFontSizeMultiplier` sınırına kadar izler. Erişilebilirlik boyutlarında çok sütunlu düzen tek sütuna iner. Glif sayfası `allowFontScaling={false}` ile çizilir ve yakınlaştırmayla büyür; yakınlaştırma hiçbir ekranda kapatılmaz.
- Hareketi Azalt (Sistem* · Açık · Kapalı): sistem değeri `AccessibilityInfo.isReduceMotionEnabled()`'dan okunur. Açıkken sayfa çevirme ve takip kaydırması animasyonsuzdur (`scrollToIndex({ animated: false })`), alt sayfa geçişleri solmaya döner, hareket jetonları `anlik` olur.
- Hedefler: her dokunulabilir öğe en az 44×44 pt (küçük simgede `hitSlop`) ve Türkçe erişilebilirlik etiketi taşır; her kaydırma jestinin görünür düğmesi vardır; "Büyük dokunma alanları (Mod A)" ayarı Mod A isabet alanını büyütür.
- Ekran okuyucu: `screenReaderChanged` dinlenir; açılınca "Erişilebilir metin modu" (Âyet âyet + Unicode) bir kez önerilir. Her âyet "Bakara Sûresi, 255. âyet" etiketli ve Arapça Unicode metinli tek öğedir, âyet sırasıyla dizilir; öğe eylemleri Dinle, Meali oku, Tefsir (yalnız tefsir paketi kuruluyken), Vurgula, Bağlantılar; sayfa değişince en çok saniyede bir duyuru yapılır ("Sayfa 42, Bakara Sûresi"). Mod A katmanı A26'dadır ve burada denetlenir; Mod C ve Âyet âyet için eksik kalan burada tamamlanır.
- Renk tek başına anlam taşımaz; Türkçe paragraftaki her Arapça dizi ayrı `Text` olarak sağdan sola yazılır.
- **Bitti sayılır:** RNTL testleri etiket, rol ve eylemleri doğruluyor; %200 ve Gece görüntüleri `arayuz-denetcisi` onaylı.

### A32.4 · Kaynaklar ekranı
- Kaynaklar çevrimdışı açılır ve verisi koddan gelmez (Yayın süreci §6, Mobil mimari §4): `core` ile kurulu paketlerin `attribution` tabloları birleştirilir (`title`, `version`, `required_credit`, `source_url`, `notice_text`; yani ad, sürüm, atıf satırı, kaynak bağlantısı ve varsa kaynağın kendi bildirimi, bayt bayt). Ekran ayrıca fontları (yazı tipi adı, sürüm, kaynak bağlantısı), okuyucuları (MP3Quran, Tarteel) ve QUD zamanlama atfını, K-19 notunu (yapay zekâ taslağıyla hazırlanıp insan onayından geçen içerik) ve derlemede üretilen açık kaynak bağımlılık listesini gösterir.
- Açık kaynak bölümü: `pnpm licenses list -r --json --prod` çıktısı (kapsam A32.1'de doğrulanır) `node scripts/ci/list-licenses.mjs pnpm <dosya> --json <çıktı>` ile `[{name, version, license}]` biçimine çevrilir ve derlemeye girer; ekran paket adı, sürüm ve paketin bildirdiği lisansı listeler. Liste yalnız gösterilir; hiçbir lisans derlemeyi durdurmaz (K-42 madde 6).
- Uygulama varlıkları (arayüz yazı tipleri, ebru görseli) paket içeriği değildir; atıf satırlarının ekrana hangi yoldan geldiği (`core` paketinin `attribution` tablosuna varlık kaynağı olarak yazılması) A13 ve A21 ile birlikte kesinleştirilir; sonuç burada ve Yayın süreci §6'da yazılır.
- `dev` verisiyle ekran sınanır: bütün kaynak kayıtlarının atıf satırı görünür.
- **Bitti sayılır:** B-07 kontrol listesi (`.tmp/a32/b07.md`; `inceleyici` işaretler) `pipeline/sources/` kayıtlarındaki her atıf satırının ve `notice_text` değerinin ekranda değiştirilmeden göründüğünü gösteriyor; açık kaynak bölümü `list-licenses.mjs --json` çıktısıyla aynı sayıda paket listeliyor.

### A32.5 · Öz test ekranı
- Rota `ayarlar/gelistirici/oz-test.tsx` (öneri ad), yalnız `dev` derlemede; vektör dosyaları yalnız `dev` JS paketine girer (07-yayin/03 §2).
- Koşulan vektörler: `normalize/tr.jsonl`, `normalize/ar.jsonl`, `anchors/{valid,invalid,compare,contains,route}.jsonl`, `offsets/offsets.jsonl`, `fts-query/query.jsonl`. `content-hash/hash.jsonl` koşulmaz, çünkü cihaz özet hesaplamaz (03-veri/01 §7).
- Ayrıca Arapça sorgu sınaması koşulur (A28 ölçüm kümesindeki Arapça satırların beklenen ilk sonuçları; 07-yayin/03 §9). Bilgi satırları Hermes'teki `'İ'.toLocaleLowerCase('tr')`, `'I'.toLocaleLowerCase('tr')`, `normalize('NFC')` ve `Intl.NumberFormat('tr')` çıktılarını gösterir (MM-11). A04'ten devreden: ekran Hermes'te `\p{Mn}`, adlı grup (`(?<ad>…)`) ve olumsuz ileri bakış desteğini de sınar (`snapSpan` ve çapa desenleri bunlara dayanır; [A04 aşama kaydı](./A04-capa-ve-test-vektorleri.md#aşama-kaydı-kapanış-2026-10-25)); anchors vektörlerinin Hermes'te koşumu bu aşamadadır.
- Ekran dosya başına geçen ve kalan sayısını, sonda tek satırda "Geçti" ya da "Kaldı" gösterir (`testID` önerisi: `oz-test-sonuc`).
- **Bitti sayılır:** Emülatörde "Geçti"; MM-11 gözlemleri `/belge-esitle` ile işlendi.

### A32.6 · Hata raporu anahtarı ve denetimi
- A21'in `telemetry.ts` dosyası 06-mobil/01 §12 ile karşılaştırılır: `dev`'de başlatılmaz; `sendDefaultPii: false`; ekran görüntüsü, görünüm hiyerarşisi ve oturum tekrarı yok; `tracesSampleRate` `public`'te 0, `internal`'da 0,2; kırıntılardan `console`, `ui.input` ve `touch` düşer, gezinmede yalnız rota şablonu, ağda sorgusuz adres kalır; `beforeSend` kullanıcıyı, sunucu adını ve cihaz adını siler, `extra` yalnız `errorKind`, `packId`, `packVersion` taşır. Eksik madde tamamlanır.
- "Hata raporları" anahtarı (A32.1 kararıyla, cihaz ayarı): kapalıysa Sentry başlatılmaz.
- Ayıklama testi genişletilir: not metni, arama sorgusu, okunan çapa, kullanıcı ve cihaz adı içeren fikstür olay `beforeSend` sonrasında bunları taşımıyor (07-yayin/02 §2.2).
- Sentry'de IP saklama kapalıyken coğrafi bilgi IP adresinden yine çıkarılır (Sentry belgesi); `beforeSend` `event.user` alanını siler. Coğrafi bilginin de kaldırılması için ileri veri temizleme kuralı gerekip gerekmediği A32.1'de doğrulanır; gerekiyorsa kural proje ayarına İ-27 ile eklenir.
- `inceleyici` bağımlılık listesini denetler: analitik, reklam ya da izleme SDK'sı yok (Gizlilik §2.3; B-12).
- **Bitti sayılır:** Ayıklama ve anahtar testleri yeşil; `dev` bayrağında `Sentry.init` çağrılmıyor.

### A32.7 · İlk açılış tanıtımı
- Rota `onboarding/index.tsx` (A21 açtı), dört adım tek ekranda (01-urun/03 §5): Hoş geldin (uygulama adı, tek cümlelik tanım ve üç söz: "Reklam yok. Hesap gerekmez. Notların cihazında kalır."); Tema ve yazı boyutu (Kâğıt, Âhar, Gece, Sistem kartları canlı örnekle; Arapça ve Türkçe boyut kaydırıcıları); Mushaf ve okuma biçimi (yalnız bu derlemede görünen çizim yolları; C ve Mushaf + Meal önceden seçili; ekran okuyucu açıksa "Erişilebilir metin modu" önerisi); İsteğe bağlı paketler (görünen paketler boyutlarıyla, "Yalnız Wi-Fi ile indir" varsayılan açık, "Şimdi değil" geçerli).
- Canlı örnek metin koddan gelmez: Fâtiha'nın ilk âyeti ve meali gömülü `core`'dan okunur (CLAUDE.md kural 2). Paket listesi ve indirme kuyruğu A29'un manifest ve kuyruk işlevlerini kullanır; çevrimdışıyken paket adımı "Sonra indir" der ve tanıtım yine biter (01-urun/03 §3).
- Her adımda "Atla"; "Atla, varsayılanlarla aç" bütün adımları geçer. Tanıtım bitince Oku sekmesi Fâtiha'da açılır. Uygulama ilk kez bir derin bağlantıyla açıldıysa yalnız 1. adım gösterilir ve hedef açılır (öneri; ME-5 okur testiyle kesinleşir).
- Tamamlandı bilgisi MMKV'de (cihaza özgü); "Tanıtımı yeniden göster" bu bilgiyi siler ve rotayı açar. Seçimler (tema, boyut, mushaf, okuma biçimi) A32.2'deki ayar deposuna yazılır; ayrı kopya tutulmaz.
- Ebru motifi yalnız burada ve boş durumlarda kullanılır (01-urun/03 §3); görsel A32.0'da indirilen dosyadan hazırlanır; erişilebilirlik kuralları A32.3 ile aynıdır.
- **Bitti sayılır:** RNTL testleri dört adımı, "Atla" yolunu, derin bağlantı kısa yolunu ve "Tanıtımı yeniden göster"i doğruluyor; dört adımın Kâğıt ve Gece görüntüleri `arayuz-denetcisi` onaylı.

## Kabul ölçütleri
- [ ] Tedarik tablosundaki her adres açıldı, sürümler `pnpm-lock.yaml`'da; ebru görselinin SHA-256'sı `data/gelen/ebru-motifi/<YYYY-AA-GG>/SHA256SUMS` dosyasında ve kaynak kaydı `uv --directory pipeline run mutalaa sources check` ile geçerli.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; ayar göçü, "Verilerimi sil", erişilebilirlik etiketleri, Kaynaklar ekranı, hata raporu anahtarı ve genişletilmiş ayıklama testleri bu aşamada eklendi.
- [ ] Ağaçtaki her satır çalışıyor; görünmeyen çizim yolu listelenmiyor; Geliştirici menüsü `public` bayrağında yok (RNTL).
- [ ] Türkçe ve Arapça 10. kademede okuma metni varsayılanın iki katı; sistem yazı ölçeği 2,0 iken kesilen metin yok (`.tmp/a32/`, `arayuz-denetcisi`).
- [ ] Hareketi Azalt açıkken sayfa çevirme animasyonsuz (bileşen testi ve emülatörde gözlem).
- [ ] Dokunma hedefleri en az 44×44 pt (Tasarım vitrinindeki dokunma alanı katmanıyla görüntü).
- [ ] Kaynaklar ekranı uçak modunda açılıyor; B-07 kontrol listesi eksiksiz (her atıf satırı ve `notice_text` değiştirilmeden ekranda); açık kaynak bölümü `list-licenses.mjs --json` çıktısıyla aynı sayıda paket gösteriyor.
- [ ] Öz test emülatörde "Geçti"; `internal` için dışa aktarılan JS paketinde vektör kimliği (ör. `tr-0001`) yok.
- [ ] `dev` derlemede Sentry başlatılmıyor; olaylarda kişisel veri yok (birim testi); bağımlılıklarda analitik SDK'sı yok.
- [ ] İlk açılış tanıtımı: dört adım, "Atla" ve derin bağlantı kısa yolu testleri yeşil; seçimler ayar deposuna yazılıyor; "Tanıtımı yeniden göster" tanıtımı açıyor; örnek metin `core`'dan geliyor (kodda Kur'an ya da meal metni yok).

## Doğrulama
```bash
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/ui-tokens test                 # kontrast eşiği (07-yayin/03 §11)
pnpm lint && pnpm typecheck
uv --directory pipeline run mutalaa sources check     # kaynak kayıtları geçerli (ebru-motifi dahil)
mkdir -p .tmp/a32
pnpm licenses list -r --json --prod > .tmp/a32/pnpm-licenses.json   # kapsam (yalnız mobil uygulama) A32.1'de doğrulanır
node scripts/ci/list-licenses.mjs pnpm .tmp/a32/pnpm-licenses.json --json .tmp/a32/bagimlilik.json   # Kaynaklar ekranının açık kaynak bölümünün girdisi
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/gelistirici/oz-test"
adb exec-out screencap -p > .tmp/a32/oz-test.png
adb shell settings put system font_scale 2.0          # mobil-ekran: büyük yazı
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar"
adb exec-out screencap -p > .tmp/a32/ayarlar-200.png
adb shell settings put system font_scale 1.0
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://onboarding"
adb exec-out screencap -p > .tmp/a32/tanitim.png
# İç paket denetimi (`--platform` ve `--output-dir` bayrakları Expo CLI belgesinde doğrulandı):
# APP_FLAVOR=internal pnpm --filter @mutalaa/mobile exec expo export --platform android --output-dir .tmp/export-internal
# grep -rl "tr-0001" apps/mobile/.tmp/export-internal   # beklenen: çıktı yok
```

## Dikkat
- Ayar ekranları yalnız ayarı değiştirir; davranış A24–A31'deki koddan gelir. Var olan ekran yeniden yazılmaz, eksik olan eklenir.
- Sentry'ye ve günlüğe kullanıcı kimliği, cihaz adı, IP, okunan âyet, arama sorgusu, not metni ve ekran görüntüsü girmez (CLAUDE.md kural 10).
- Atıf metni koda yazılmaz. Pakette atıf eksikse sorun Yayınlayıcı çıktısıdır (A13); `inceleyici` raporuna yazılır.
- Öz testte kırılan vektör için kural kodu yerinde değiştirilmez; `test-vektoru` becerisiyle üç dilde ele alınır.
- Türkçe harf dönüşümü `trLower` ve `trUpper` ile yapılır; Türkçe metinde `textTransform: 'uppercase'` kullanılmaz (01-urun/04 §3.3).
- VoiceOver denetimi iOS cihaz ister; Windows'ta burada yalnız emülatör ve TalkBack yapılır, iOS denetimi A33'te İ-21 cihazında.
- Commit kapsamları: `mobile`, `ui-tokens` (yalnız jeton değişirse), `pipeline` (ebru kaynak kaydı).

## İnsan adımları
- İ-27 · Sentry hesabı, projesi ve DSN değeri: `internal` derlemeden önce kullanıcı açar (A32.1); organizasyonu açarken veri konumunu (ABD ya da AB) seçer, proje ayarında IP saklamayı kapatır ve DSN'i `apps/mobile/.env.local` ile EAS ortamına kendisi yazar ([İnsan adımları](../06-insan-adimlari.md)). Bu adım yalnız Sentry'nin canlı gönderimine bağlı `internal` ölçümünü bekletir; ayar ekranları, erişilebilirlik, Kaynaklar, öz test, tanıtım ve `telemetry.ts` birim testleri sürer.

## Çıktılar
- `apps/mobile/app/(tabs)/ayarlar/` altında doldurulan ekranlar (`index`, `gorunum`, `okuma`, `mushaf`, `erisilebilirlik`, `kaynaklar`, `hakkinda`) ve yeni `gelistirici/oz-test.tsx`; `apps/mobile/app/onboarding/index.tsx` (tanıtım)
- `apps/mobile/src/features/settings/` (depo, göç, ekranlar), `apps/mobile/src/lib/telemetry.ts` eklemeleri, erişilebilirlik yardımcıları
- Öz test koşucusu ve yalnız `dev` pakete giren vektör modülü; açık kaynak bağımlılık listesi üretimi; `.tmp/a32/` (git dışı)
- `data/gelen/ebru-motifi/<YYYY-AA-GG>/` (görsel ve `SHA256SUMS`, git dışı) ve `pipeline/sources/ebru-motifi.toml`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A32-ayarlar-erisilebilirlik-oz-test.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A31](./A31-hadis-ve-risale-okuyuculari.md) · Sonraki: [A33](./A33-uctan-uca-test-ve-ic-dagitim.md)
