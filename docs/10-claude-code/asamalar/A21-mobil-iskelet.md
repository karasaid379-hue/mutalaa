# A21 · Mobil iskelet: Expo, Router, NativeWind, temalar, derleme türleri, EAS

> **Sürüm:** 1.1 · **Tarih:** 25 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-32](../../00-ozet/02-karar-defteri.md#k-32--pnpm-kurulumu-sürüm-sabitleme-ve-düzen)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · [A04](./A04-capa-ve-test-vektorleri.md) · **İnsan adımı:** [İ-15](../06-insan-adimlari.md) (Expo hesabı, `eas login`)
> **Ajanlar:** `mobil-gelistirici` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A21`

## Amaç
Bu aşama `apps/mobile` altında Expo uygulamasının iskeletini kurar: rota ağacı, kök sağlayıcılar, NativeWind ve tema altyapısı, i18n'e hazır Türkçe metinler, üç derleme türü (`dev`, `internal`, `public`), EAS profilleri ve hata izleme. Sonraki mobil aşamalar (A22–A33) bu iskelete ekleme yapar. Aşama, EAS bulutunda üretilen Android geliştirme derlemesinin emülatörde açılıp ekran görüntüleriyle denetlenmesiyle biter.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §1–§5, §10, §12 (Sentry), §14
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §1 Alt sekmeler, §2 Rota ağacı, §6 hizalama notları
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.1 Mobil, §4 Sürüm sabitleme ve yükseltme
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/mobile`), §2 bağımlılık kuralları, §5 lint, §7 `eas-build.yml`, §8
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §1 (EAS CLI, hesaplar), §5 `apps/mobile/.env.example`, §6 adım 8–9, §10.4
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §3.1 yazı tipleri, §10 (`vars()` ile tema yöntemi)
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §2.2

## Kapsam
**Yapılır**
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
- Ayar ekranlarının içeriği, "Hata raporları" anahtarı ve öz test (A32); Maestro ve iç dağıtım derlemesi (A33); mağaza derlemesi (A34).
- Tanıtım ekranının içeriği ([Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §5): [A32](./A32-ayarlar-erisilebilirlik-oz-test.md) A32.7. Bu aşama yalnız rotayı açar.

## Adımlar
### A21.1 · Sürüm ve belge doğrulaması (`arastirmaci`)
- Güncel kararlı Expo SDK doğrulanır. K-09 SDK 57 ile başlayıp SDK 58 kararlı çıkınca geçmeyi söyler. SDK 58 kararlıysa ve NativeWind v4, @gorhom/bottom-sheet 5.2.x, Reanimated 4, Sentry ve Drizzle onunla uyumluysa SDK 58 seçilir; değilse SDK 57 ve en az `expo@57.0.17` ([Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §4.2). Seçim `/karar` ile K-09 güncellemesi olarak yazılır.
- Aynı turda resmî belgeden doğrulanır:
  - `create-expo-app` komutu, TypeScript ve Expo Router içeren şablon adı, pnpm çalışma alanında kurulum yolu.
  - NativeWind v4'ün istediği Tailwind sürümü, Babel ve Metro ayarı; `vars()` imzası (Tasarım sistemi TS-8).
  - React Native Reusables'ın NativeWind v4 ile kurulumu ve istediği yerel bağımlılıklar (ör. SVG).
  - Reanimated 4'ün worklets Babel eklentisi; Gesture Handler ≥ 2.16.1 (bottom-sheet şartı).
  - Expo Router'da `Tabs` için özel sekme çubuğu yöntemi (MM-9), `ErrorBoundary` dışa aktarımı ve rota testi yardımcısı.
  - `react-native-mmkv` örnek oluşturma API'si; Literata değişken fontunun React Native'de kullanımı.
  - Sentry Expo eklentisi ve Metro ayarı; kaynak eşlemesi yüklemesi olmadan derleme; `sendDefaultPii` ve kırıntı alan adları.
  - `app.config.ts`'nin `.env.local` dosyasını okuması; dinamik yapılandırmada EAS proje kimliğinin yeri; `expo-updates` kanal ayarı.
  - pnpm izole kurulumunun (K-32'ye göre varsayılan düzen) seçilen SDK'da yeniden sınanması; Expo SDK 58'e özel uyumluluk tablosu yoktur. Sorun çıkarsa yedek `pnpm-workspace.yaml` içinde `nodeLinker: hoisted`'dır ve `/karar` ister. EAS'in pnpm çalışma alanını derlemesi.
  - Asgari Android sürümü (MM-12); EAS ücretsiz planının aylık derleme sınırı ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §8).
- **Bitti sayılır:** her maddenin sonucu kaynak bağlantısıyla `/belge-esitle` üzerinden ilgili dokümanda; SDK seçimi karar defterinde.

### A21.2 · Uygulamanın kurulması
- `apps/mobile` A21.1'de doğrulanan komut ve şablonla kurulur; örnek ekranlar silinir. A02'nin bıraktığı yer tutucu varsa onun yerine geçer. Paket adı `@mutalaa/mobile`; bağımlılıkları kökte `pnpm install` kurar.
- Expo'ya bağlı paketler `npx expo install` ile kurulur; sürüm yazılmaz, kilit dosyasına girer: `expo-router`, `expo-dev-client`, `expo-updates`, `expo-sqlite`, `expo-audio`, `expo-file-system`, `expo-font`, `expo-image`, `react-native-reanimated`, `react-native-gesture-handler`, `react-native-mmkv`, `@sentry/react-native` ve A21.1'in çıkardığı eş bağımlılıklar. v1'in yerel modülleri burada bir kez kurulur ki sonraki aşamalar yeni geliştirme derlemesi istemesin (öneri).
- JS paketleri: `zustand`, `@tanstack/react-query`, `@gorhom/bottom-sheet` (5.2.x), `nativewind` (v4), React Native Reusables (A21.1'deki yolla). NativeWind v5 ve eski plandaki kitaplıklar eklenmez.
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
- Fontlar resmî kaynaklarından `assets/fonts/` altına alınır: Literata, IBM Plex Sans, Amiri Quran, Amiri, Noto Naskh Arabic. Her ailenin lisans dosyası yanında durur; IBM Plex Sans ve Amiri lisansı font dosyasından okunur (Doğrulanacak, `arastirmaci`). Fontlar `expo-font` yapılandırma eklentisiyle derlemeye gömülür.
- **Bitti sayılır:** tema testi `sistem` değerinin açık ve koyu görünümde doğru temaya çözüldüğünü ve seçimin MMKV'de kaldığını gösterir; `assets/fonts/` beş aileyi ve lisanslarını içerir.

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
- Jest ve jest-expo kurulur. Testler: yapılandırma ve EAS (A21.5), bayrak matrisi, `t()` anahtarları, `trLower('IŞIK') === 'ışık'`, `beforeSend` sonrası olayda not metni kalmaması ([KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md) §2.2), ESLint sınır testi (yasak içe aktarma içeren örnek kod hata verir).
- **Bitti sayılır:** `lint`, `typecheck` ve `test` yeşil.

### A21.7 · Geliştirme derlemesi ve görsel denetim
- Android geliştirme derlemesi kullanıcının açık onayıyla EAS bulutunda başlatılır ve beklenmez: `(cd apps/mobile && eas build --profile development --platform android --non-interactive --no-wait)`. Komut derlemeyi kuyruğa koyup döner ve Bash aracının süre sınırına takılmaz. Komut yeniden çalıştırılırsa ikinci derleme başlar; bu yüzden tekrarlanmaz, durum `eas build:list` ile izlenir. İlk derlemede anahtar deposu gibi bir soru gerekiyorsa `--non-interactive` hata verir; o zaman komutu kullanıcı kendi terminalinde etkileşimli çalıştırır. Yerel `expo run:android` isteğe bağlıdır ve A00'daki yol kararına bağlıdır.
- Durum birkaç dakika arayla sorulur: `(cd apps/mobile && eas build:list --platform android --build-profile development --limit 1 --json --non-interactive)` (izinli komut). Durum `FINISHED` olunca APK indirilir: `mkdir -p .tmp/a21 && curl -L -o .tmp/a21/mutalaa-dev.apk "<artifacts.buildUrl>"` (`curl` onay ister). `ERRORED` ise derleme sayfasının bağlantısı kullanıcıya verilir; yeni derleme yalnız kullanıcının onayıyla başlar.
- APK emülatöre kurulur (`adb install -r .tmp/a21/mutalaa-dev.apk`). Metro arka planda başlatılır (`pnpm dev:mobile`) ve `adb reverse tcp:8081 tcp:8081` ile bağlanır.
- `mobil-ekran` becerisiyle beş sekmenin ve `+not-found` ekranının görüntüsü alınır (renkler A22'de gelir). `arayuz-denetcisi` görüntüleri okur: yazılı sekme etiketleri, Türkçe karakterler ve fontlar, 44×44 pt hedefler, metin taşması.
- iOS geliştirme derlemesi isteğe bağlıdır; Apple Developer hesabı (İ-15) ve `eas device:create` gerekir.
- **Bitti sayılır:** uygulama emülatörde açılır; 6 görüntü `.tmp/a21/` altında; `arayuz-denetcisi` raporunda engelleyici bulgu yok.

## Kabul ölçütleri
- [ ] SDK seçimi karar defterinde (K-09 güncellemesi); `apps/mobile/package.json` bu sürümü taşır; SDK 57 seçildiyse `expo` ≥ 57.0.17.
- [ ] `pnpm --filter @mutalaa/mobile exec expo install --check` hatasız.
- [ ] `pnpm --filter @mutalaa/mobile lint`, `typecheck` ve `test` yeşil.
- [ ] `APP_FLAVOR=internal` ile `expo config` çıktısında `app.mutalaa.internal` ve `mutalaa-internal`; `APP_FLAVOR=public` ile soneksiz `app.mutalaa` kimliği ve `mutalaa` şeması geçer.
- [ ] `eas.json` üç profili, kanalları ve `APP_FLAVOR` değerlerini Mobil mimari §10 ile aynı taşır (test).
- [ ] `dev` derlemede Sentry başlatılmaz; `beforeSend` ayıklama testi yeşil.
- [ ] ESLint sınır testi: `src/lib` içinden `@/features/...` içe aktarımı ve özellik içine derin içe aktarım hata verir.
- [ ] Rota ağacı Mobil ekranlar §2 ile aynıdır (A22, A25, A28, A32 ve MM-14 rotaları hariç); `public` bayrağıyla geliştirici rotası yönlenir (test).
- [ ] `apps/mobile/src` ve `apps/mobile/app` içinde onaltılık renk kodu yok.
- [ ] EAS Android geliştirme derlemesi başarılı; emülatör görüntüleri `.tmp/a21/` altında; `arayuz-denetcisi` raporu temiz.

## Doğrulama
```bash
pnpm install --frozen-lockfile
pnpm --filter @mutalaa/mobile exec expo install --check
pnpm --filter @mutalaa/mobile lint
pnpm --filter @mutalaa/mobile typecheck
pnpm --filter @mutalaa/mobile test
APP_FLAVOR=internal pnpm --filter @mutalaa/mobile exec expo config | grep -E "app\.mutalaa\.internal|mutalaa-internal"
APP_FLAVOR=public pnpm --filter @mutalaa/mobile exec expo config | grep -E "app\.mutalaa['\"]|scheme.*['\"]mutalaa['\"]"
grep -rlE "['\"]#[0-9A-Fa-f]{3,8}['\"]" apps/mobile/src apps/mobile/app || echo "onaltılık renk yok"
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
- Commit kapsamı `mobile` (ör. `feat(mobile): add router skeleton and build flavors`).

## İnsan adımları
- İ-15 · Expo hesabı ve `eas login`: A21.5'teki `eas init` ve A21.7'deki ilk derlemeden önce gerekir. Apple Developer hesabı yalnız iOS derlemesi için.
- İ-01 · Android Studio (isteğe bağlı araç): emülatör ve `adb` için A21.7'den önce gerekir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/mobile/`: `package.json`, `app.config.ts`, `eas.json`, `metro.config.js`, `babel.config.js`, NativeWind v4 yapılandırması, `tsconfig.json`, Jest yapılandırması, `.env.example`
- `apps/mobile/app/**` rota dosyaları; `apps/mobile/src/features/*/index.ts` yer tutucuları
- `apps/mobile/src/lib/`: `env.ts`, `flags.ts`, `kv.ts`, `query.ts`, `telemetry.ts`, `i18n/`, `theme/`
- `apps/mobile/assets/fonts/` (fontlar ve lisans dosyaları); `apps/mobile/test/` altında testler
- Karar defterinde K-09 güncellemesi; `/belge-esitle` ile işlenen "Doğrulanacak" maddeleri; `.tmp/a21/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A21-mobil-iskelet.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A20](./A20-risale-altyapisi.md) · Sonraki: [A22](./A22-tasarim-vitrini.md)
