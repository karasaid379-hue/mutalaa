# A21 · Mobil iskelet

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-32](../../00-ozet/02-karar-defteri.md#k-32--pnpm-kurulumu-sürüm-sabitleme-ve-düzen)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · [A04](./A04-capa-ve-test-vektorleri.md) · **İnsan adımı:** [İ-15](../06-insan-adimlari.md) (Expo hesabı, `eas login`)
> **Ajanlar:** `mobil-gelistirici` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A21`

## Amaç
Bu aşama `apps/mobile` altında Expo uygulamasının iskeletini kurar: rota ağacı, kök sağlayıcılar, NativeWind ve tema altyapısı, i18n'e hazır Türkçe metinler, üç derleme türü (`dev`, `internal`, `public`), EAS profilleri ve hata izleme. Sonraki mobil aşamalar (A22–A33) bu iskelete ekleme yapar. Aşama tedarikle başlar: çatı, kitaplıklar ve yazı tipleri hazır yapılardan, sabitlenmiş sürümlerle alınır (A21.0). Aşama, EAS bulutunda üretilen Android geliştirme derlemesinin emülatörde açılıp ekran görüntüleriyle denetlenmesiyle biter.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §1–§5, §10, §12 (Sentry), §14
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §1 Alt sekmeler, §2 Rota ağacı, §6 hizalama notları
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.1 Mobil, §4 Sürüm sabitleme ve yükseltme
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/mobile`), §2 bağımlılık kuralları, §5 lint, §7 `eas-build.yml`, §8
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §1 (EAS CLI, hesaplar), §5 `apps/mobile/.env.example`, §6 adım 8–9, §10.4
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §3.1 yazı tipleri, §10 (`vars()` ile tema yöntemi)
- [Gizlilik](../../07-yayin/02-gizlilik.md): §2.2 (kişisel veri içermeyen hata raporu)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 (kaynak kaydı ve atıf), §3.1 (yazı tipi kartları), §5 (yeni kaynak ekleme)

## Kapsam
**Yapılır**
- Tedarik: çatı, kitaplık ve yazı tipi sürümlerinin sabitlenmesi, yazı tiplerinin indirilmesi ve kaynak kayıtları (A21.0).
- Güncel kararlı Expo SDK'nın doğrulanması ve `apps/mobile` uygulamasının kurulması.
- Rota ağacı, kök sağlayıcılar, beş sekme, hata sınırı ve mini oynatıcı yuvası.
- NativeWind v4, React Native Reusables, Reanimated 4, Gesture Handler, @gorhom/bottom-sheet, MMKV ve v1'in öteki yerel modüllerinin kurulumu.
- Tema altyapısı (`sistem`, `kagit`, `ahar`, `gece`) ve fontların derlemeye gömülmesi.
- `app.config.ts`, `eas.json`, `src/lib/env.ts`, `src/lib/flags.ts`, i18n, telemetri.
- ESLint içe aktarma sınırları, Jest kurulumu, ilk EAS geliştirme derlemesi ve görsel denetim.

**Yapılmaz**
- `packages/ui-tokens`, tam jeton seti, simge takımı ve Tasarım vitrini: [A22](./A22-tasarim-vitrini.md).
- Veritabanları, manifest, `fetch-core.mjs`, `.db` Metro ayarı, `AppError` türleri: [A23](./A23-cihaz-veri-katmani.md).
- Okuyucu ve `SheetHost` (A24); alt sayfa içerikleri ve `[...capa].tsx` derin bağlantı rotası (A25); ses ve mini oynatıcının kendisi (A27).
- Mod C Kur'an yazı tipi adayı KFGQPC Hafs'ın indirilmesi ve yazı tipi seçimi (görsel kaliteye göre): [A24](./A24-okuyucu-mushaf-c.md) A24.0.
- Ayar ekranlarının içeriği, "Hata raporları" anahtarı ve öz test (A32); Maestro ve iç dağıtım derlemesi (A33); mağaza derlemesi (A34).
- Tanıtım ekranının içeriği ([Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §5): [A32](./A32-ayarlar-erisilebilirlik-oz-test.md) A32.7. Bu aşama yalnız rotayı açar.

## Tedarik
Yapılar internetten, GitHub'dan ve paket kayıtlarından alınır; sürümler sabitlenir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)). Ölçümler 2 Kasım 2026'dadır; ölçülmeyen hücre A21.0'da ölçülür.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Expo SDK 58 çatısı ve şablonu | `expo` 58.0.22 ve `expo-template-default` 58.0.31 ([npm](https://www.npmjs.com/package/expo), 31 Ekim 2026; React Native 0.88.1, React 19.3.0; git `expo/expo` etiketi `expo@58.0.22` = `004bfc41cfd82784da23450101015717c5da74e6`); duyuru: [SDK 58](https://expo.dev/changelog/sdk-58); biçim: npm paketi | `pnpm create expo-app apps/mobile --template default@sdk-58 --no-install --yes` ([belge](https://docs.expo.dev/more/create-expo/): SDK 58 geçiş döneminde `--template` verilmezse SDK 57 şablonu kurulur) | npm `latest` = 58.0.22; şablon etiketi `sdk-58` = 58.0.31 (1.407.796 bayt, 51 dosya: TypeScript, Expo Router, `src/app/` ve `scripts/reset-project.js` dahil); `create-expo` 5.1.6 Node ^22.13, ^24.3 ya da ≥ 26 ister | `expo` 57.0.31 ve `expo-template-default` 57.0.33 (npm `sdk-57` etiketi) |
| Expo'ya bağlı modüller | `bundledNativeModules.json` @ `expo@58.0.22` (SHA-256 `3b2c9d80113acb8ff74b6203c884196f70299bce4da7bb4b46a7faa41d41300d`; [jsDelivr](https://cdn.jsdelivr.net/npm/expo@58.0.22/bundledNativeModules.json)): `expo-router` ~58.0.29, `expo-dev-client` ~58.0.18, `expo-updates` ~58.0.20, `expo-sqlite` ~58.0.15, `expo-audio` ~58.0.11, `expo-file-system` ~58.0.13, `expo-font` ~58.0.11, `expo-image` ~58.0.18, `react-native-screens` ~4.30.1, `react-native-safe-area-context` ~5.10.1, `react-native-svg` 15.16.0 | `pnpm --filter @mutalaa/mobile exec expo install <paket>`; sürüm yazılmaz, `expo install` tablodan seçer | Expo paketlerinin hepsi npm kaydında var (28–31 Ekim 2026 yayımları); `expo install --check` A21.2'de hatasız olmalı | `bundledNativeModules.json` @ `expo@57.0.31` |
| Animasyon ve jestler | `react-native-reanimated` 4.7.1 (git etiketi `4.7.1` = `5fd93c32624c64c4020fb089171afde88a511d92`), `react-native-worklets` 0.13.0 (SDK 58 sürümü; npm `latest` 0.13.1), `react-native-gesture-handler` ~3.3.0 (git etiketi `v3.3.0` = `b9dbaec32902582d7c4c124123ffbf51f29c5daf`; npm `latest` 3.4.0) | `pnpm --filter @mutalaa/mobile exec expo install react-native-reanimated react-native-worklets react-native-gesture-handler` | Reanimated 4.7.1 eş bağımlılıkları `react-native 0.86 - 0.88` ve `react-native-worklets 0.13.x`; SDK 58 şablonu bu sürümleri taşır; `babel-preset-expo` 58.0.23 `react-native-worklets/plugin`'i kendisi ekler (`build/configs/expo.js`) | SDK 57 tablosundaki sürümler |
| Alt sayfa | `@gorhom/bottom-sheet` 5.2.14 (npm, 9 Mayıs 2026; git etiketi `v5.2.14` = `13c0890c844f11f842b29b0a9279792ea2517c6f`) | `pnpm --filter @mutalaa/mobile add @gorhom/bottom-sheet@5.2.14` | Eş bağımlılıkları Gesture Handler ≥ 2.16.1 ve Reanimated ≥ 3.16.0 ya da ≥ 4.0.0-; tek satırlı içe aktarımları (`Gesture`, `GestureDetector`, `State` ve tipler) Gesture Handler 3.3.0 kaynağında bulunur; kök paketten çözümlenmeleri ve çalışma zamanı uyumu A21.1'de sınanır | SDK 57 yolu (o tablodaki Gesture Handler ve Reanimated sürümleriyle) |
| Stil | `nativewind` 4.2.7 (npm, 14 Eylül 2026, `latest`; [kurulum belgesi](https://www.nativewind.dev/docs/getting-started/installation)), `tailwindcss` ^3.4.17 (3.4.19), `react-native-css-interop` 0.2.7 | `pnpm --filter @mutalaa/mobile add nativewind@4.2.7`; `tailwindcss` ve `babel-preset-expo` geliştirme bağımlılığı | Belge: Tailwind 3 yapılandırması, `nativewind/babel` ön ayarı, `withNativeWind(config, { input })`; `vars()` API bölümünde | NativeWind 5.0.0-rc.1 (2 Kasım 2026; Tailwind 4 ister) kullanılmaz (K-29); Unistyles 3 |
| Arayüz bileşenleri | React Native Reusables: `@react-native-reusables/cli` 0.7.1 (npm, 14 Mart 2026); git `founded-labs/react-native-reusables` HEAD `385834c2196f8a303cbc9057d1ac768f3bde0a3b` ([CLI README](https://github.com/founded-labs/react-native-reusables/blob/385834c2196f8a303cbc9057d1ac768f3bde0a3b/apps/cli/README.md)); biçim: bileşen kaynak kodu projeye kopyalanır | `pnpm dlx @react-native-reusables/cli@0.7.1 init` ve `add <bileşen>` (komutlar README'de; NativeWind v4 ile uyumu A21.1'de doğrulanır) | CLI `init`, `add [bileşenler]` ve `--all` sunar; bileşen listesi ve eş bağımlılıklar A21.0'da ölçülür | Bileşenleri elle yazmak (yalnız CLI çalışmazsa) |
| Durum ve yerel depolama | `zustand` 5.0.16, `@tanstack/react-query` 5.105.1, `react-native-mmkv` 4.3.2 (git etiketi `v4.3.2` = `e98276c438529731638c62be16013f3ca55804e7`) ve eş bağımlılığı `react-native-nitro-modules` 0.37.1 | `pnpm --filter @mutalaa/mobile add zustand @tanstack/react-query react-native-mmkv react-native-nitro-modules` | MMKV 4.3.2 `createMMKV()` ve `useMMKV()` dışa aktarır (paket kaynağı) ve `react-native-nitro-modules` ister | `@react-native-async-storage/async-storage` 2.2.0 (SDK 58 tablosunda) |
| Hata izleme | `@sentry/react-native` 8.33.0 (npm, 29 Ekim 2026; git etiketi `8.33.0` = `87468d75b86f58613fefb554926d0fc72b34f7cc`; [Expo kılavuzu](https://docs.sentry.io/platforms/react-native/guides/expo/)); hesap: altyapı (İ-27) | `pnpm --filter @mutalaa/mobile exec expo install @sentry/react-native`; `app.json` eklentisi `@sentry/react-native/expo`, `metro.config.js` için `@sentry/react-native/metro` | Eş bağımlılık `expo >=49`; Expo SDK 58 ile uyum A21.1'de sınanır | 8.x içinde bir önceki yama |
| Test ve lint | `jest-expo` ~58.0.13, `jest` 30.5.2, `@testing-library/react-native` 14.1.0, `eslint-config-expo` ~58.0.4 | `pnpm --filter @mutalaa/mobile exec expo install jest-expo eslint-config-expo`; `pnpm --filter @mutalaa/mobile add -D jest @testing-library/react-native` ve eş bağımlılıkları | `jest-expo` eş bağımlılığı `jest` ^29 ya da ^30 ve `@react-native/jest-preset ^0.88.1`; RNTL 14 `test-renderer ^1.0.0` ister | Jest 29 |
| Latin yazı tipleri: Literata (Türkçe gövde), IBM Plex Sans (arayüz) | `github.com/google/fonts` commit `6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec` (HEAD, 2 Kasım 2026): `ofl/literata/Literata[opsz,wght].ttf` (955.132 bayt, sürüm 3.103) ve `ofl/ibmplexsans/IBMPlexSans[wdth,wght].ttf` (537.244 bayt, sürüm 3.201); biçim: TrueType, değişken eksenli | `curl -L` ile `https://raw.githubusercontent.com/google/fonts/<commit>/ofl/<aile>/<dosya>` (`[`, `]`, `,` URL kodlu: `%5B`, `%5D`, `%2C`) → `data/gelen/literata-font/<YYYY-AA-GG>/` ve `data/gelen/ibm-plex-sans-font/<YYYY-AA-GG>/` | HTTP 200, bayt sayıları yukarıdaki gibi; Literata 1.789 glif, eksenler opsz 7–72 ve wght 200–900, TRK dil sistemi; IBM Plex Sans 1.025 glif, wght 100–700 ve wdth 75–100; Türkçe harfler (â î û ç ğ ı İ ö ş ü ve büyükleri) ikisinde de tam. İtalik kesimler aynı commit'te: `Literata-Italic[opsz,wght].ttf` (902.728), `IBMPlexSans-Italic[wdth,wght].ttf` (599.624); jeton gerektirirse A22'de alınır | `@expo-google-fonts/literata` 0.4.3 ve `@expo-google-fonts/ibm-plex-sans` 0.4.1 (npm; ağırlık başına statik dosya) |
| Arapça yazı tipleri: Amiri Quran (Kur'an metni), Amiri ve Noto Naskh Arabic (metin içi Arapça) | Aynı commit: `ofl/amiriquran/AmiriQuran-Regular.ttf` (136.920 bayt, sürüm 1.003, SHA-256 `e2a47644762d16bdfb6d33e0d8db8c6ff30beae84150ef5a705316bbd829455c`), `ofl/amiri/Amiri-Regular.ttf` (431.116 bayt, sürüm 1.002), `ofl/notonaskharabic/NotoNaskhArabic[wght].ttf` (307.592 bayt, sürüm 2.021); Amiri'nin `-Bold` (413.480), `-Italic` (428.532) ve `-BoldItalic` (409.692) kesimleri de var | Aynı yol; Amiri Quran için A15.0'ın `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` klasörü ve commit'i yeniden kullanılır (yoksa A21.0 indirir); öteki ikisi `data/gelen/amiri-font/<YYYY-AA-GG>/` ve `data/gelen/noto-naskh-arabic-font/<YYYY-AA-GG>/` | HTTP 200; glif sayıları: Amiri 6.710, Amiri Quran 1.446, Noto Naskh Arabic 1.719 (wght 400–700); Tanzil Uthmani metnindeki 69 ayırt edici kod noktasının 69'u ve Tanzil basit metnindeki 45'in 45'i üçünde de var (yalnız sayım); Türkçe harfler Amiri Quran'da yok, öteki ikisinde tam | `@expo-google-fonts/amiri` 0.4.1, `@expo-google-fonts/amiri-quran` 0.4.1, `@expo-google-fonts/noto-naskh-arabic` 0.4.5 (npm) |
| EAS derleme hizmeti ve CLI | `eas-cli` 27.2.0 (npm, 29 Ekim 2026); [EAS Build](https://docs.expo.dev/build/introduction/), [çalışma zamanı sürümü](https://docs.expo.dev/eas-update/runtime-versions/); hesap: altyapı (İ-15) | `npm install -g eas-cli` (İ-01; [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §1); sürüm A21.0'da npm kaydıyla karşılaştırılır | Belgeler HTTP 200; ücretsiz plan ayda 15 Android ve 15 iOS derleme, düşük öncelikli kuyruk ([fiyatlar](https://expo.dev/pricing)) | Yerel `expo run:android` (A00 yol kararına bağlı) |

Mod C'nin ikinci Kur'an yazı tipi adayı KFGQPC Hafs 3.0 (`https://fonts.qurancomplex.gov.sa/fonts/KFGQPC-Hafs-V30.zip`, doğrudan indirilir) [A24](./A24-okuyucu-mushaf-c.md) A24.0'da alınır; bu aşama yalnız Amiri Quran'ı gömer.

Kendimiz yapacağımız işler: rota ağacı ve kök sağlayıcılar, tema altyapısı, `src/lib` modülleri (`env`, `flags`, `kv`, `query`, `telemetry`, `i18n` ve açık eşlemeli `trLower`/`trUpper`), `app.config.ts` ve `eas.json`, ESLint içe aktarma sınırları, yapılandırma ve EAS testleri. Hesaplar (Expo, Sentry) altyapıdır.

## Adımlar
### A21.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: npm `latest` ve `sdk-58` etiketleri, `bundledNativeModules.json`, GitHub etiketleri (`git ls-remote`), belge sayfaları. Açılmayan adresin ya da uyumsuz sürümün yerine "Yedek aday" sütunundaki kaynağı kullan ve tabloyu güncelle.
- Kitaplıkların sürümünü paket kaydından doğrula (`npm view <paket> version`, `dist-tags` ve eş bağımlılık aralıkları); değerler tablodakiyle aynı olmalı. Kitaplıkları bu adım kurmaz; kurulum A21.2'dedir.
- Yazı tipi dosyalarını Claude Code indirir. İndirme formu çıkarsa Claude Code doldurur. Her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasöre iner ve klasörde `SHA256SUMS` (sha256sum biçimi) yazılır. Amiri Quran için A15.0 klasörü varsa dosya özeti karşılaştırılır, yoksa burada indirilir.
  ```bash
  C=6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec
  D=data/gelen/literata-font/$(date +%F); mkdir -p "$D"
  curl -fL --max-time 120 -o "$D/Literata[opsz,wght].ttf" "https://raw.githubusercontent.com/google/fonts/$C/ofl/literata/Literata%5Bopsz%2Cwght%5D.ttf"
  sha256sum "$D"/*.ttf | sed "s#$D/##" > "$D/SHA256SUMS"
  ```
  Aynı kalıp `ibm-plex-sans-font`, `amiri-font`, `amiri-quran-font` ve `noto-naskh-arabic-font` için tekrarlanır. Her dosyanın bayt sayısı tablodakiyle aynı olmalı.
- Kaynak kayıtları (`pipeline/sources/<kimlik>.toml`): `amiri-quran-font` kaydı var (A15.0 güncellediyse dokunulmaz; güncellemediyse sürüm 1.003 ve sabit commit adresi yazılır) ve dört yeni kayıt açılır: `literata-font`, `ibm-plex-sans-font`, `amiri-font`, `noto-naskh-arabic-font` (`tur = "font"`; ad, adres, sürüm ya da commit, atıf satırı). Kayıt sayısını sınayan test varsa güncellenir. `uv --directory pipeline run mutalaa sources check` hatasız.
- **Bitti sayılır:** tablodaki her adres açılıyor ya da yedeğe geçildiği tabloda yazılı; beş yazı tipi ailesinin dosyaları ve `SHA256SUMS` `data/gelen/` altında, boyutlar tablodaki gibi; beş font kaydı `sources check`ten geçiyor; kitaplık sürümleri tabloyla aynı.

### A21.1 · Sürüm ve belge doğrulaması (`arastirmaci`)
- SDK 58 kararlıdır (npm `latest` 58.0.22; [SDK 58 duyurusu](https://expo.dev/changelog/sdk-58)). K-09 SDK 57 ile başlayıp SDK 58 kararlı çıkınca geçmeyi söyler. NativeWind v4 (4.2.7), @gorhom/bottom-sheet 5.2.14 (Gesture Handler ~3.3.0 ile), Reanimated 4.7.1, Sentry 8.33.0 ve Drizzle SDK 58 ile uyumluysa SDK 58 seçilir; değilse SDK 57 ve en az `expo@57.0.17` ([Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §4.2). Seçim `/karar` ile K-09 güncellemesi olarak yazılır.
- Aynı turda resmî belgeden doğrulanır. Ön bulgular A21.0 araştırmasındandır (2 Kasım 2026):
  - `create-expo-app` komutu, TypeScript ve Expo Router içeren şablon adı, pnpm çalışma alanında kurulum yolu. Ön bulgu: `pnpm create expo-app --template default@sdk-58`; `--no-install` ve `--yes` bayrakları belgede; şablon rotaları `src/app/` altında üretir. Doğrulanacak: `apps/mobile` yolu ve Expo Router'ın rota klasörünü seçişi (`src/app/` ya da kökteki `app/`; belgeler `apps/mobile/app/` yazar, `src/app/` seçilirse bu aşamadaki yollar ve [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §2 eşitlenir).
  - NativeWind v4'ün istediği Tailwind sürümü, Babel ve Metro ayarı; `vars()` imzası (Tasarım sistemi TS-8). Ön bulgu: `nativewind@4.2.7`, `tailwindcss@^3.4.17`; Babel'de `["babel-preset-expo", { jsxImportSource: "nativewind" }]` ve `"nativewind/babel"`; Metro'da `withNativeWind(config, { input })`.
  - React Native Reusables'ın NativeWind v4 ile kurulumu ve istediği yerel bağımlılıklar (ör. SVG). Ön bulgu: CLI `init`, `add [bileşenler]` komutlarını sunar.
  - Reanimated 4'ün worklets Babel eklentisi; Gesture Handler ≥ 2.16.1 (bottom-sheet şartı). Ön bulgu: `babel-preset-expo` eklentiyi kendisi bulup ekler; SDK 58'in Gesture Handler sürümü ~3.3.0'dır ve bottom-sheet 5.2.14'ün tek satırlı içe aktarımları o sürümün kaynağında var; çalışma zamanı uyumu cihazda sınanır.
  - Expo Router'da `Tabs` için özel sekme çubuğu yöntemi (MM-9), `ErrorBoundary` dışa aktarımı ve rota testi yardımcısı.
  - `react-native-mmkv` örnek oluşturma API'si; Literata değişken fontunun React Native'de kullanımı. Ön bulgu: MMKV 4.3.2 `createMMKV()` ve `useMMKV()` dışa aktarır; [Expo Font](https://docs.expo.dev/versions/v58.0.0/sdk/font/) belgesine göre değişken yazı tipi `useFonts` ile çalışır ve `fontWeight` örneği seçer, Android API 29 altında yalnız varsayılan yüz yüklenir (MM-12 ile birlikte düşünülür; gerekirse ağırlık başına statik dosya). `expo-font` eklentisiyle gömülen yazı tipi adlarının iki platformda aynı çözümlendiği de doğrulanır.
  - Sentry Expo eklentisi ve Metro ayarı; kaynak eşlemesi yüklemesi olmadan derleme; `sendDefaultPii` ve kırıntı alan adları. Ön bulgu: `@sentry/react-native/expo` eklentisi ve `@sentry/react-native/metro` Metro ayarı.
  - `app.config.ts`'nin `.env.local` dosyasını okuması; dinamik yapılandırmada EAS proje kimliğinin yeri; `expo-updates` kanal ayarı.
  - pnpm izole kurulumunun (K-32'ye göre varsayılan düzen) seçilen SDK'da yeniden sınanması; Expo SDK 58'e özel uyumluluk tablosu yoktur. Sorun çıkarsa yedek `pnpm-workspace.yaml` içinde `nodeLinker: hoisted`'dır ve `/karar` ister. EAS'in pnpm çalışma alanını derlemesi.
  - Asgari Android sürümü (MM-12); EAS ücretsiz planının aylık derleme sınırı ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §8). Ön bulgu: ayda 15 Android ve 15 iOS derleme.
- **Bitti sayılır:** her maddenin sonucu kaynak bağlantısıyla `/belge-esitle` üzerinden ilgili dokümanda; SDK seçimi karar defterinde.

### A21.2 · Uygulamanın kurulması
- `apps/mobile` A21.1'de doğrulanan komut ve şablonla (`default@sdk-58`) kurulur. Şablonun örnek içeriği silinir: `src/app/`, `src/components/`, `src/constants/`, `src/hooks/`, `src/global.css`, `scripts/reset-project.js` ve örnek görseller; rotalar `apps/mobile/app/` altında kurulur (A21.1'deki rota klasörü sonucuna göre). A02'nin bıraktığı yer tutucu varsa onun yerine geçer. Paket adı `@mutalaa/mobile`; bağımlılıkları kökte `pnpm install` kurar.
- Expo'ya bağlı paketler `pnpm --filter @mutalaa/mobile exec expo install` ile kurulur; sürüm yazılmaz, kilit dosyasına girer: `expo-router`, `expo-dev-client`, `expo-updates`, `expo-sqlite`, `expo-audio`, `expo-file-system`, `expo-font`, `expo-image`, `react-native-reanimated`, `react-native-worklets`, `react-native-gesture-handler`, `react-native-safe-area-context`, `react-native-svg`, `@sentry/react-native` ve A21.1'in çıkardığı eş bağımlılıklar. `react-native-mmkv` (ve `react-native-nitro-modules`) `pnpm add` ile kurulur. v1'in yerel modülleri burada bir kez kurulur ki sonraki aşamalar yeni geliştirme derlemesi istemesin (öneri).
- JS paketleri: `zustand`, `@tanstack/react-query`, `@gorhom/bottom-sheet` (5.2.14), `nativewind` (4.2.7; `tailwindcss` ^3.4.17 geliştirme bağımlılığı), React Native Reusables (A21.1'deki yolla). NativeWind v5 ve eski plandaki kitaplıklar eklenmez. Sürümler A21.0 tablosuyla aynıdır.
- `package.json` betikleri: `start` (`expo start`), `typecheck` (`tsc --noEmit`), `lint` (`expo lint`), `test` (`jest`). `tsconfig.json` kökteki `tsconfig.base.json`'u genişletir; `@/*` → `src/*`.
- **Bitti sayılır:** `pnpm --filter @mutalaa/mobile exec expo install --check` ve `typecheck` hatasız.

### A21.3 · Rota ağacı, sağlayıcılar ve sekmeler
- Rotalar [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §2'deki ağaçla kurulur. Rota dosyası yalnız `src/features/<özellik>/index.ts`'den bir bileşen çağırır; bileşen şimdilik `t('genel.hazirlaniyor')` metnini gösterir.
- Bu aşamada kurulmayan rotalar: `ayarlar/gelistirici/vitrin.tsx` (A22), `[...capa].tsx` (A25; öteki çapa türleri MM-14 kapanınca aynı rotaya eklenir), `ayarlar/gelistirici/arama-olcumu.tsx` (A28), `ayarlar/gelistirici/oz-test.tsx` (A32), `sayfa/[no].tsx` (MM-14 kapanınca).
- Kök sağlayıcı sırası Mobil mimari §4'teki gibidir: `GestureHandlerRootView` → `SafeAreaProvider` → tema → `QueryClientProvider` → `DbGate` (A23 doldurur; şimdilik geçirgen) → `BottomSheetModalProvider` → `Stack`. `not/[id]` ve `hatim/yeni` kök düzeyinde modaldır.
- `(tabs)/_layout.tsx`: Oku, Kütüphane, Ara, Defterim, Ayarlar; etiketler `tab.*` anahtarlarından. Sekme çubuğunun üstünde boş `MiniPlayerSlot` durur (A27 doldurur); yöntem A21.1'deki MM-9 sonucudur. Simgeler A22'de seçilir; o zamana kadar yalnız yazılı etiket.
- Her sekme grubu `ErrorBoundary` dışa aktarır ("Yeniden dene", "Okumaya dön"). `+not-found`: açıklama, "Ara'da dene", "Okumaya dön".
- `ayarlar/gelistirici/index.tsx` yalnız `gelistiriciMenusu` bayrağı açıkken görünür; `public`'te Ayarlar'a yönlenir. Rotanın `public` pakete hiç girmemesi açık sorudur (ME-3).
- **Bitti sayılır:** rota testi bütün rotaların çizildiğini ve `public` bayrağıyla geliştirici rotasının yönlendiğini gösterir.

### A21.4 · Durum, tema ve fontlar
- `src/lib/kv.ts`: MMKV yalnız buradan kullanılır (`getItem`, `setItem`, `removeItem` sarmalayıcısı).
- `src/features/settings/store.ts`: `useSettings` Mobil mimari §5'teki gibi; `theme` `sistem` değerini de alır; varsayılanlar `sistem`, `C`, `mushaf_meal`, `rtl`, ölçekler 1.
- `src/lib/query.ts`: `QueryClient` ve `focusManager` (AppState); `onlineManager` ağ modülü seçilince A23'te bağlanır.
- Tema sağlayıcısı: `sistem` açıkta Kâğıt, koyuda Gece olur; etkin tema adı kökten bağlamla yayılır ve işletim sisteminin görünüm değişikliği dinlenir. Renk değerleri A22'de `@mutalaa/ui-tokens`'tan NativeWind `vars()` ile bağlanır; bu aşamada uygulama koduna renk kodu yazılmaz (mobil kuralları). React Native Reusables'ın tema değişkenleri de A22'de jetonlara eşlenir.
- Fontlar A21.0'da `data/gelen/` altına inen dosyalardan `apps/mobile/assets/fonts/` altına kopyalanır: Literata, IBM Plex Sans, Amiri Quran, Amiri, Noto Naskh Arabic. Köşeli parantezli dosya adları (`Literata[opsz,wght].ttf` gibi) kopyalanırken sadeleştirilir (`Literata.ttf`); kopyanın SHA-256 değeri `SHA256SUMS` içindeki değerle aynıdır. Fontlar `expo-font` yapılandırma eklentisiyle derlemeye gömülür.
- **Bitti sayılır:** tema testi `sistem` değerinin açık ve koyu görünümde doğru temaya çözüldüğünü ve seçimin MMKV'de kaldığını gösterir; `assets/fonts/` beş aileyi içerir ve her dosyanın özeti A21.0 kaydıyla aynıdır.

### A21.5 · Derleme türleri, bayraklar ve EAS
- `app.config.ts` Mobil mimari §10'daki örnekle yazılır: `APP_FLAVOR` (varsayılan `dev`), ad, kimlikler `app.mutalaa.dev` / `app.mutalaa.internal` / `app.mutalaa`, şemalar `mutalaa-dev` / `mutalaa-internal` / `mutalaa`, `runtimeVersion: { policy: 'fingerprint' }`, eklentiler (`expo-router`, mikrofonu kapalı `expo-audio`, `enableFTS: true` ile `expo-sqlite`, `expo-font`, Sentry), `extra: { flavor, manifestUrl, sentryDsn }`. Kimlikler yer tutucudur.
- `apps/mobile/.env.example` [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §5 ile aynıdır. Gerçek `.env.local` kullanıcıdadır; Claude Code onu okumaz.
- `src/lib/env.ts` (`flavor`, `manifestUrl`, `sentryDsn`) ve `src/lib/flags.ts` (MATRIX aynen). `'paket'` kuralı paket görünürlüğünü bir işleve sorar; işlev A23'e kadar `false` döner.
- `eas.json` Mobil mimari §10'daki üç profille: `development` (`developmentClient`, `distribution: internal`, kanal `development`, `APP_FLAVOR=dev`), `internal` (kanal `internal`), `production` (kanal `production`, `autoIncrement`, `APP_FLAVOR=public`). Ek alanlar yalnız A21.1'de doğrulananlardır.
- İ-15 tamamlanınca proje `eas init` ile bağlanır; komut etkileşim isterse kullanıcı PowerShell'de çalıştırır. `internal` ve `production` bu aşamada derlenmez.
- **Bitti sayılır:** yapılandırma testi üç `APP_FLAVOR` değerinde ad, kimlik ve şemayı; `eas.json` testi profil, kanal ve `APP_FLAVOR` eşlemesini doğrular.

### A21.6 · Metinler, telemetri, lint ve testler
- `src/lib/i18n/tr.ts` ve `t()` Mobil mimari §14'teki gibi; ekranlarda düz Türkçe dizgi yazılmaz. `trLower` ve `trUpper` açık eşlemeyle yazılır. Hermes'teki davranış (MM-11) öz test ekranında sınanır (A32). A04'ten devreden: `snapSpan` Hermes'te `\p{Mn}`, adlı grup ve ileri bakış desteğine dayanır; destek A32 öz testinde sınanır, burada yalnız kullanılan düzenli ifade özellikleri listelenir ve `snapSpan` cihazda hesaplanacaksa Unicode sürüm farkı (A04 aşama kaydı) dikkate alınır.
- `src/lib/telemetry.ts` Mobil mimari §12'deki gibi: `dev`'de `Sentry.init` çağrılmaz; `internal` ve `public`'te `sendDefaultPii: false`, ekran görüntüsü ve görünüm hiyerarşisi kapalı, kırıntı ve olay ayıklaması açık; oturum tekrarı yok.
- ESLint: kök yapılandırmaya Expo yapılandırması ve React Hooks kuralları eklenir. Yön `app → features → (db, packs, lib) → packages/*` `import/no-restricted-paths` ile; özellik içine derin içe aktarma `no-restricted-imports` deseniyle (öneri) engellenir.
- Jest ve jest-expo kurulur. Testler: yapılandırma ve EAS (A21.5), bayrak matrisi, `t()` anahtarları, `trLower('IŞIK') === 'ışık'`, `beforeSend` sonrası olayda not metni kalmaması ([Gizlilik](../../07-yayin/02-gizlilik.md) §2.2), ESLint sınır testi (yasak içe aktarma içeren örnek kod hata verir).
- **Bitti sayılır:** `lint`, `typecheck` ve `test` yeşil.

### A21.7 · Geliştirme derlemesi ve görsel denetim
- Android geliştirme derlemesi kullanıcının açık onayıyla EAS bulutunda başlatılır ve beklenmez: `(cd apps/mobile && eas build --profile development --platform android --non-interactive --no-wait)`. Komut derlemeyi kuyruğa koyup döner ve Bash aracının süre sınırına takılmaz. Komut yeniden çalıştırılırsa ikinci derleme başlar; bu yüzden tekrarlanmaz, durum `eas build:list` ile izlenir. İlk derlemede anahtar deposu gibi bir soru gerekiyorsa `--non-interactive` hata verir; o zaman komutu kullanıcı kendi terminalinde etkileşimli çalıştırır. Yerel `expo run:android` isteğe bağlıdır ve A00'daki yol kararına bağlıdır.
- Durum birkaç dakika arayla sorulur: `(cd apps/mobile && eas build:list --platform android --build-profile development --limit 1 --json --non-interactive)` (izinli komut). Durum `FINISHED` olunca APK indirilir: `mkdir -p .tmp/a21 && curl -L -o .tmp/a21/mutalaa-dev.apk "<artifacts.buildUrl>"` (`curl` onay ister). `ERRORED` ise derleme sayfasının bağlantısı kullanıcıya verilir; yeni derleme yalnız kullanıcının onayıyla başlar.
- APK emülatöre kurulur (`adb install -r .tmp/a21/mutalaa-dev.apk`). Metro arka planda başlatılır (`pnpm dev:mobile`) ve `adb reverse tcp:8081 tcp:8081` ile bağlanır.
- `mobil-ekran` becerisiyle beş sekmenin ve `+not-found` ekranının görüntüsü alınır (renkler A22'de gelir). `arayuz-denetcisi` görüntüleri okur: yazılı sekme etiketleri, Türkçe karakterler ve fontlar, 44×44 pt hedefler, metin taşması.
- iOS geliştirme derlemesi isteğe bağlıdır; Apple Developer hesabı (İ-15) ve `eas device:create` gerekir.
- **Bitti sayılır:** uygulama emülatörde açılır; 6 görüntü `.tmp/a21/` altında; `arayuz-denetcisi` raporunda engelleyici bulgu yok.

## Kabul ölçütleri
- [ ] A21.0: `## Tedarik` tablosundaki adresler açıldı (ya da yedeğe geçildi ve tablo güncellendi); beş yazı tipi ailesinin dosyaları `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında `SHA256SUMS` ile duruyor; beş font kaydı `uv --directory pipeline run mutalaa sources check`ten hatasız geçiyor; kitaplık sürümleri tabloyla aynı.
- [ ] SDK seçimi karar defterinde (K-09 güncellemesi); `apps/mobile/package.json` bu sürümü taşır; SDK 57 seçildiyse `expo` ≥ 57.0.17.
- [ ] `pnpm --filter @mutalaa/mobile exec expo install --check` hatasız.
- [ ] `pnpm --filter @mutalaa/mobile lint`, `typecheck` ve `test` yeşil.
- [ ] `APP_FLAVOR=internal` ile `expo config` çıktısında `app.mutalaa.internal` ve `mutalaa-internal`; `APP_FLAVOR=public` ile soneksiz `app.mutalaa` kimliği ve `mutalaa` şeması geçer.
- [ ] `eas.json` üç profili, kanalları ve `APP_FLAVOR` değerlerini Mobil mimari §10 ile aynı taşır (test).
- [ ] `dev` derlemede Sentry başlatılmaz; `beforeSend` ayıklama testi yeşil.
- [ ] ESLint sınır testi: `src/lib` içinden `@/features/...` içe aktarımı ve özellik içine derin içe aktarım hata verir.
- [ ] Rota ağacı Mobil ekranlar §2 ile aynıdır (A22, A25, A28, A32 ve MM-14 rotaları hariç); `public` bayrağıyla geliştirici rotası yönlenir (test).
- [ ] `apps/mobile/src` ve `apps/mobile/app` içinde onaltılık renk kodu yok.
- [ ] `apps/mobile/assets/fonts/` beş yazı tipi ailesini içerir; her dosyanın SHA-256 değeri A21.0 kaydıyla aynıdır.
- [ ] EAS Android geliştirme derlemesi başarılı; emülatör görüntüleri `.tmp/a21/` altında; `arayuz-denetcisi` raporu temiz.

## Doğrulama
```bash
# A21.0: tedarik
npm view expo dist-tags --json                    # latest tablodaki 58.0.22 ile aynı ya da daha yeni 58.x
uv --directory pipeline run mutalaa sources check
# A21.2 sonrası
pnpm install --frozen-lockfile
pnpm --filter @mutalaa/mobile exec expo install --check
pnpm --filter @mutalaa/mobile lint
pnpm --filter @mutalaa/mobile typecheck
pnpm --filter @mutalaa/mobile test
APP_FLAVOR=internal pnpm --filter @mutalaa/mobile exec expo config | grep -E "app\.mutalaa\.internal|mutalaa-internal"
APP_FLAVOR=public pnpm --filter @mutalaa/mobile exec expo config | grep -E "app\.mutalaa['\"]|scheme.*['\"]mutalaa['\"]"
grep -rlE "['\"]#[0-9A-Fa-f]{3,8}['\"]" apps/mobile/src apps/mobile/app || echo "onaltılık renk yok"
sha256sum apps/mobile/assets/fonts/*.ttf          # data/gelen/<kaynak>/<YYYY-AA-GG>/SHA256SUMS içindeki değerlerle aynı
grep '"expo"' apps/mobile/package.json
# Derleme A21.7'de kullanıcı onayıyla başlatıldı; burada yalnız durumu okunur, yeni derleme başlatılmaz:
(cd apps/mobile && eas build:list --platform android --build-profile development --limit 1 --json --non-interactive)
test -f .tmp/a21/mutalaa-dev.apk && adb install -r .tmp/a21/mutalaa-dev.apk
adb reverse tcp:8081 tcp:8081
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://bilinmeyen-yol"
adb exec-out screencap -p > .tmp/a21/not-found.png
```
PowerShell'de ortam değişkeni `$env:APP_FLAVOR = "internal"` ile verilir; ekran görüntüsü komutu Git Bash'te çalıştırılır.

## Dikkat
- Expo Go kullanılmaz; yalnız geliştirme derlemesi (K-09). Eski plandaki expo-av, WatermelonDB, react-native-track-player, react-native-fs ve Tamagui eklenmez (K-30).
- Proje yolu boşluk, Türkçe karakter ve OneDrive içerir; Android derlemesi bu yüzden varsayılan olarak EAS bulutundadır. Yol, Metro ve `adb` sorunlarında `windows-sorun`.
- `adb exec-out screencap -p > dosya` Git Bash'te çalışır; PowerShell 5.1'in ikili yönlendirmesi dosyayı bozabilir ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §9).
- EAS derlemesi geri dönüşü zor işlemdir; kullanıcının açık onayı olmadan başlatılmaz. `eas submit` hiç çalıştırılmaz.
- Yeni yerel modül yeni geliştirme derlemesi ister (`fingerprint`). Toplu kurulum EAS kotasını korur.
- `packages/*` içine `react-native` ve `expo-*` girmez (Proje yapısı §2). Yerel ayarlı büyük-küçük harf çağrıları kök ESLint kuralıyla yasaktır.
- `MANIFEST_URL` ve `SENTRY_DSN` gizli değildir ama `.env.local` git dışıdır; örnek değer yalnız `.env.example`'da.
- `data/gelen/` git dışıdır; `apps/mobile/assets/fonts/` altındaki kopyalar commit'e girer.
- Commit kapsamı `mobile` (ör. `feat(mobile): add router skeleton and build flavors`).
- A08'den devir (CI): `apps/mobile` eklendiği PR'da (1) `.github/dependabot.yml` içindeki `npm` girdisine Expo'ya bağlı paketler için `ignore` kuralı yazılır; bu paketler yalnız SDK yükseltmesiyle güncellenir ([Teknoloji yığını §4.2](../../02-mimari/02-teknoloji-yigini.md)). (2) `EXPO_TOKEN` sırrı tanımlanır: Expo robot kullanıcısı, en dar rol; Expo hesabı İ-15'e bağlıdır ([İnsan adımları](../06-insan-adimlari.md)). `eas-build.yml` `apps/mobile` yokken zaten durur. (3) EAS ücretsiz planı ayda 15 Android ve 15 iOS derleme verir; kota aşılınca ücret çıkmaz, derleme durur ([Proje yapısı §8](../../02-mimari/03-proje-yapisi.md#8-açık-sorular) madde 3). `mobile-v*` etiketi itmek ücretli bir üretim derlemesi başlatır (`eas-build.yml`). Ayrıca `ci-ts.yml` içindeki `expo install --check` adımı `apps/mobile/package.json` oluşunca kendiliğinden çalışmaya başlar.

## İnsan adımları
- İ-15 · Expo hesabı ve `eas login`: A21.5'teki `eas init` ve A21.7'deki ilk derlemeden önce gerekir. Apple Developer hesabı yalnız iOS derlemesi için.
- İ-01 · Android Studio (isteğe bağlı araç): emülatör ve `adb` için A21.7'den önce gerekir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/mobile/`: `package.json`, `app.config.ts`, `eas.json`, `metro.config.js`, `babel.config.js`, NativeWind v4 yapılandırması, `tsconfig.json`, Jest yapılandırması, `.env.example`
- `apps/mobile/app/**` rota dosyaları; `apps/mobile/src/features/*/index.ts` yer tutucuları
- `apps/mobile/src/lib/`: `env.ts`, `flags.ts`, `kv.ts`, `query.ts`, `telemetry.ts`, `i18n/`, `theme/`
- `apps/mobile/assets/fonts/` (beş yazı tipi ailesi); `apps/mobile/test/` altında testler
- `data/gelen/<kaynak>/<YYYY-AA-GG>/` (git dışı): yazı tipi dosyaları ve `SHA256SUMS`; `pipeline/sources/` altında dört yeni yazı tipi kaydı (`literata-font`, `ibm-plex-sans-font`, `amiri-font`, `noto-naskh-arabic-font`)
- Karar defterinde K-09 güncellemesi; `/belge-esitle` ile işlenen "Doğrulanacak" maddeleri; `.tmp/a21/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A21-mobil-iskelet.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [Kaynaklar](../../04-icerik/01-kaynaklar.md) · Önceki: [A20](./A20-risale-altyapisi.md) · Sonraki: [A22](./A22-tasarim-vitrini.md)
