# A22 · Tasarım vitrini ve `ui-tokens`

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-14](../../00-ozet/02-karar-defteri.md#k-14--web) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A21](./A21-mobil-iskelet.md) · **İnsan adımı:** İ-22 (durdurmaz)
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A22`

## Amaç
"Sade Osmanlı" tasarım dilinin jetonları tek JSON kaynakta toplanır ve hem mobil (NativeWind v4) hem web ve editör (Tailwind v4) için derlenir. Kontrast eşiğinin altında kalan her jeton çifti derlemeyi durdurur. Ekranlar yazılmadan önce, yalnız geliştirici derlemelerinde görünen Tasarım vitrini kurulur; görsel kararlar üç tema ve üç yazı boyutunda gözden geçirilir.

## Okunacak belgeler
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): tamamı
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §11 Erişilebilirlik kontrolleri, §12 CI düzeni
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10 (`tasarimVitrini`), §13 Erişilebilirlik uygulaması
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §3.2 (Tasarım vitrini satırı), §6 yazı boyutu kademeleri
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): "Geri al" çubuğunun davranışı (`Snackbar`)
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §2 bağımlılık kuralları, §4.1 Turborepo görevleri
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): mobil arayüz kitaplıkları; paylaşılan paketlerin bağımlılık kuralı
- [A21](./A21-mobil-iskelet.md): `## Tedarik` (NativeWind, Reusables, alt sayfa, yazı tipleri) ve A21.4 (tema sağlayıcısı)

## Kapsam
**Yapılır**
- `packages/ui-tokens`: `tokens.json`, `schema.json`, `build.ts`, kontrast testi ve `dist/` çıktıları.
- A21'deki tema sağlayıcısının ve React Native Reusables tema değişkenlerinin bu jetonlara bağlanması.
- Yazı rolleri ve kademeleri, hareket jetonları ve Hareketi Azalt bağı.
- Simge takımı kararı (TS-3; öneri `lucide-react-native`) ve onaltılık renk ESLint kuralı (öneri).
- Tasarım vitrini rotası, ilk bölümleri ve üç tema × üç boyut ekran görüntüsü komutları (görüntüleri kullanıcı alır).

**Yapılmaz**
- Okuyucu parçalarının kendisi: `PageView` ve `AyahMarker` (A24), `WordCard`, `LinkResult`, `ChipSlot` (A25), `MiniPlayer` ve `PlayerSheet` (A27). Her aşama kendi bileşenini vitrine ekler.
- Ayarlar › Görünüm ekranı (A32). Editörün ve webin `tailwind.css`'e geçişi `web-gelistirici`nin ayrı işidir. Tecvid renkleri (v1.x).
- Yazı tipi dosyalarının alınması (A21.4) ve Arapça yazı tipi ile Arapça örnek metin (A24).

## Tedarik
Araştırma tarihi: 3 Kasım 2026 (ilk geçiş 2 Kasım; adresler, sürümler ve ölçümler 3 Kasım'da yeniden okundu). Sürümler npm kaydından (`dist-tags.latest`), yayım tarihleri deps.dev'den, etiketler ve commit'ler `git ls-remote` ile okundu (`api.github.com` kullanılmadı); Expo'ya bağlı modüllerin sabitleri `bundledNativeModules.json` dosyalarından (`expo@58.0.22` ve `sdk-57` dalı) alındı. Stil katmanı, Reusables kurulumu, alt sayfa ve yazı tipleri A21'in `## Tedarik` tablosunda alınır; A22 onları kullanır, yeni olarak simge takımını, kontrast doğrulamasını, şema doğrulayıcısını ve tip bildirimlerini ekler. Aşama içerik metni, hesap ya da anahtar gerektirmez; eklenen her şey paket kaydından ya da GitHub'dan doğrudan alınır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Stil katmanı (mobil) | `nativewind` 4.2.7 (14 Eylül 2026; npm `latest`) ve `tailwindcss` 3.4.19 (10 Aralık 2025; npm `v3-lts`); npm. `nativewind@5.0.0-rc.1` (`rc` etiketi) kullanılmaz (K-29). Belgeler: [kurulum](https://www.nativewind.dev/docs/getting-started/installation), [`vars()`](https://www.nativewind.dev/docs/api/vars), [Theme](https://www.nativewind.dev/docs/customization/theme) | A21.2 kurar; A22 yalnız `dist/nativewind-preset.js` ön ayarını ve `vars()` bağını ekler, sürüm değiştirmez | Üç belge sayfası açılıyor (3 Kasım 2026); `vars()` belgesi `import { vars } from "nativewind"`, `style={vars({ '--brand-color': … })}` ve `text-[--brand-color]` örneğini veriyor (sayfa 24 Mart 2026 güncel); kurulum belgesi `tailwindcss@^3.4.17` ister; `nativewind` 4.2.7 eş bağımlılığı `tailwindcss >3.3.0`; `react-native-css-interop` 0.2.7 eş bağımlılıkları `tailwindcss@~3` ve `react-native-reanimated >=3.6.2` | Unistyles 3 (Teknoloji yığını) |
| Stil katmanı (web ve editör) | `tailwindcss` 4.3.4 (2 Kasım 2026; npm `latest`; git etiketi `v4.3.4` = `2626ae6ceddf36069ab6d55c53a5857c1e2e360a`); Teknoloji yığını 4.3.3 yazıyor (git etiketi `v4.3.3` = `c2b24dd15fed1c59dd521bd86082f520c9f5ad0d`); npm. Belgeler: [`@theme`](https://tailwindcss.com/docs/theme), [koyu kip](https://tailwindcss.com/docs/dark-mode) | A15 kurar; A22 yalnız `dist/tailwind.css` üretir. A22.1 sınaması için `pnpm dlx @tailwindcss/cli@4.3.4` (4.3.4, 2 Kasım 2026; depoya eklenmez) | İki belge sayfası açılıyor (3 Kasım 2026); belgede `@theme { --color-mint-500: oklch(...) }`, `@theme inline { --font-sans: var(--font-inter); }` ve `@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *))` örnekleri var | `tailwindcss` 4.3.3 (Teknoloji yığını) |
| Bileşen kitaplığı | React Native Reusables: `github.com/founded-labs/react-native-reusables` commit `385834c2196f8a303cbc9057d1ac768f3bde0a3b` (`HEAD`; 2 ve 3 Kasım 2026'da aynı); CLI `@react-native-reusables/cli` 0.7.1 (14 Mart 2026); ilkeller `@rn-primitives/*` 1.5.2 (2 Temmuz 2026; `portal` 1.5.3); yardımcılar `class-variance-authority` 0.7.1, `clsx` 2.1.1, `tailwind-merge` 3.7.0, `tailwindcss-animate` 1.0.7; npm. Biçem `nativewind` (depoda `uniwind` biçemi de var; kullanılmaz, K-29) | A21.1–A21.2 kurulumu yapar; A22.0 bileşenleri ekler: `pnpm dlx @react-native-reusables/cli@0.7.1 add --cwd apps/mobile --styling-library nativewind -y <bileşenler>`; bileşen kaynakları `https://reactnativereusables.com/r/nativewind/<bileşen>.json` kayıt adresinden gelir ve depoya kopyalanır; `add`, `apps/mobile/components.json` ister (yoksa yazmayı önerir; `init` A21.2'de yazar) | `packages/registry/src/nativewind/components/ui/` altında 32 dosya (30 bileşen, `icon`, `native-only-animated-view`); düğme, iletişim kutusu, sekmeler, geçiş grubu, seçim kutusu, anahtar, ilerleme, açılır pencere ve iskelet kayıtta var; alt sayfa, bildirim çubuğu (`Snackbar`) ve boş durum bileşeni yok. Kayıt adresinden 14 öğe okundu (button, dialog, tabs, toggle-group, toggle, select, switch, progress, popover, skeleton, text, icon, separator, native-only-animated-view; hepsi HTTP 200): `dialog` → `@rn-primitives/dialog` ile `text`, `native-only-animated-view`, `icon`; `button` → `text`; `text` → `@rn-primitives/slot`; `icon` npm paketi eklemez (`lucide-react-native` ayrıca kurulur). `add` seçenekleri `--cwd`, `--styling-library`, `-y`, `-o`, `-a`, `-p` (CLI belgesi ve kaynağı); `reactnativereusables.com/docs/installation` açılıyor | Yalnız `@rn-primitives/*` ilkelleri üzerine kendi bileşenlerimiz |
| Simge takımı (TS-3) | `lucide-react-native` 1.66.0 (31 Ekim 2026; npm `latest` 3 Kasım 2026'da da bu; git etiketi `1.66.0` = `a630cec77eac6568b989e87e4947a8bfe45caacd`); npm; [belge](https://lucide.dev/guide/react-native). `react-native-svg` A21'de kurulur (SDK 58 sabiti 15.16.0; SDK 57 sabiti 15.15.4) | `pnpm --filter @mutalaa/mobile add lucide-react-native` | Tarball 2.444.673 bayt (SHA-256 `2948e11a21216e2d38a8d27512aa08789ddc72f9e6493d41f77b350d982b2c9d`; kayıtlı kopyadan 3 Kasım 2026'da yeniden hesaplandı), 2.016 simge; tip bildirimi pakette; sekme ve eylem simgeleri için denenen 26 addan 25'i var (`book-open`, `search`, `library`, `bookmark`, `settings`, `play`, `pause`, `x`, `check`, `download`, `share-2`, `copy`, `link`, `highlighter`, `notebook-pen`, `undo-2`, `headphones`, `languages` ve öteki; `trash-2` yok, `trash` var); `strokeWidth` ve `absoluteStrokeWidth` özellikleri var (varsayılan 2; Tasarım sistemi §8 için 1,5 verilir); Reusables'ın `Icon` bileşeni `LucideIcon` ve `LucideProps` tiplerine bağlı; eş bağımlılıklar `react-native-svg ^12 – ^15`, `react` 16.5 – 19 | `@react-native-vector-icons/lucide` 14.0.0 (19 Ekim 2026; yazı tipi tabanlı, `expo` eş bağımlılığı) |
| Alt sayfa ve jestler | `@gorhom/bottom-sheet` 5.2.14 (9 Mayıs 2026; git etiketi `v5.2.14` → commit `9bfbeb521b90d525791a3400a68eec523ad7e444`); SDK 58 sabitleri: `react-native-reanimated` 4.7.1, `react-native-worklets` 0.13.0, `react-native-gesture-handler` ~3.3.0 (SDK 57: 4.5.1, 0.10.1, ~2.32.0) | A21.2 kurar; A22 yalnız arka plan ve tutamaç renklerini `useThemeTokens()` ile verir | 5.2.14 eş bağımlılıkları `react-native-gesture-handler` ≥ 2.16.1 ve `react-native-reanimated` ≥ 3.16.0 ya da ≥ 4.0.0 (önsürümler dahil); iki SDK'nın sabitleri bunları karşılıyor (npm kaydı, 3 Kasım 2026); A21 tablosundaki `13c0890c…` etiket nesnesidir, commit `9bfbeb52…`; Reusables kaydında alt sayfa yok | `@gorhom/bottom-sheet` 5.2.13 (git etiketi `v5.2.13` → commit `bc94d544d37395eab056d27a2a4b38c56c355cc7`) |
| Kontrast doğrulaması | `culori` 4.0.2 (27 Haziran 2025; git etiketi `v4.0.2` → commit `5e5bddb37b1dafeb88e4531bd19afeb1cc24ad29`); bağımlılığı yok; `wcagContrast`. Tip bildirimi pakette yok: `@types/culori` 4.0.1 (2 Eylül 2025). `ui-tokens` çalışma zamanı bağımlılığı taşımaz (Teknoloji yığını): ikisi de paketin yalnız `devDependencies` alanında durur; vitrin `culori`'yi `apps/mobile` bağımlılığı olarak alır | `pnpm --filter @mutalaa/ui-tokens add -D culori @types/culori`; `pnpm --filter @mutalaa/mobile add culori`; `pnpm --filter @mutalaa/mobile add -D @types/culori` | `src/index.js` `contrast as wcagContrast` dışa aktarıyor; `src/wcag.js` doğrusal RGB ağırlıklarıyla (0,2126 / 0,7152 / 0,0722) göreli parlaklığı ve (L1 + 0,05) / (L2 + 0,05) oranını uyguluyor; `package.json`'da `types` alanı ve `exports.types` yok (3 Kasım 2026); Tasarım sistemi §2.1–2.4'teki 46 oran WCAG formülüyle yeniden hesaplandı (2 ve 3 Kasım 2026) ve hepsi belgedeki değerle bir ondalık içinde aynı çıktı; vurgu çiftlerinin en küçük değerleri (metin ↔ zemin 13,0 / 10,8 / 8,8; işaret ↔ yüzey 4,74 / 5,09 / 6,09; işaret ↔ zemin en az 3,97) de aynı | `colorjs.io` 0.7.1 (24 Temmuz 2026; git etiketi `v0.7.1` = `1251997f0dda2f95c41724e4981c071f1defb180`; tip bildirimi pakette) |
| Şema doğrulayıcı | `ajv` 8.20.0 (24 Nisan 2026); npm; yalnız `devDependencies` | `pnpm --filter @mutalaa/ui-tokens add -D ajv` | Kayıt doğrulandı (tip bildirimi pakette; bağımlılıkları `fast-deep-equal`, `fast-uri`, `json-schema-traverse`, `require-from-string`); `schema.json` ile `tokens.json` doğrulaması A22.2'de sınanır | `@cfworker/json-schema` 4.1.4 (30 Ekim 2026; bağımlılığı yok) |
| Jeton derleyicisi | Kendi `src/build.ts` (yaklaşık 150 satır): `tokens.json` → dört çıktı. Hazır araçlar değerlendirildi, seçilmedi: Terrazzo 2.10.0 (21 Ekim 2026; DTCG jetonları, kip desteği, `a11y/min-contrast` kuralı, CSS, JS ve Tailwind eklentileri; Tailwind eklentisi `tailwindcss ^4.0.0` ister) ve Style Dictionary 5.7.1 (24 Ekim 2026; git etiketi `v5.7.1` = `6e43a74285817ef07a6f3932e604c6824966a2a0`; Node ≥ 22). Gerekçe: NativeWind v4 Tailwind 3 ön ayarı ister; bu ön ayar ve `kontrast.md` için iki araçta da özel eklenti ya da biçimleyici yazılır; Tasarım sistemi §10'daki `tokens.json` biçimi DTCG değildir ve DTCG'ye geçiş bir biçim kararıdır; kontrast hesabı zaten `culori` ile yapılır | Yok (depoda yazılır); çalıştırıcı A22.2'de seçilir | Node 24.21.0 yerelde; `tsx` 4.23.15 (20 Eylül 2026) kayıtta; yerel TypeScript çalıştırma A22.2'de sınanır. Terrazzo belgeleri açılıyor: `terrazzo.app/docs/linting` (`a11y/min-contrast` kuralı karşılaştırılacak ön plan ve arka plan çiftlerini bildirmeyi ister) ve `terrazzo.app/docs/integrations/tailwind` (Tailwind 4 teması üretir) | Terrazzo 2.10.0 (jeton dosyası DTCG'ye çevrilirse); Style Dictionary 5.7.1 |
| Yazı tipleri (A21 alır) | `github.com/google/fonts` commit `6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec` (A21'in sabiti; `HEAD` 3 Kasım 2026'da `2fe1e8c6b137fb13041a7cfca6fdcd8a910ea4dc`'ye ilerledi, sabit commit'teki dosyalar değişmedi): `ofl/ibmplexsans/IBMPlexSans[wdth,wght].ttf` (537.244 bayt, sürüm 3.201, SHA-256 `3b031aa4216174205bd8471f88a49b91f093169e9e87bd5262242bc5967fe2e3`) ve `ofl/literata/Literata[opsz,wght].ttf` (955.132 bayt, sürüm 3.103, SHA-256 `b41138c9373112f32abb589cc22e8674b06ed4048b0c513be922bdd26f274440`); biçim: TrueType, değişken eksenli | A21.4 `assets/fonts/` altına alır; A22 `tokens.json` `yazi` rollerindeki `aile` adlarını bu dosyalara bağlar | İki dosyanın `cmap` tablosunda â î û Â Î Û ğ Ğ ş Ş ı İ ç Ç ö Ö ü Ü ile tipografik tırnak, çizgi ve üç nokta işaretleri var (IBM Plex Sans 891, Literata 1.163 kod noktası; 2 ve 3 Kasım 2026 ölçümü, kayıtlı kopyaların SHA-256 değerleri yukarıdakiyle aynı); aynı ölçüm `@expo-google-fonts/ibm-plex-sans` 0.4.1'in statik 400 / 500 / 600 / 700 dosyalarında da eksiksiz | Inter (TS-1): aynı commit'te `ofl/inter/Inter[opsz,wght].ttf` (876.576 bayt); `@expo-google-fonts/ibm-plex-sans` 0.4.1 (9 Eylül 2025; statik ağırlıklar) |
| Erişilebilirlik ve kod denetimi | ESLint çekirdek kuralı `no-restricted-syntax` (renk kuralı; ek paket yok; kökte ESLint ^10.13.0); `@testing-library/react-native` 14.1.0 (8 Ekim 2026; A21 Jest kurulumu): rol sorguları ve yerleşik eşleştiriciler (`toHaveAccessibleName`, `toBeOnTheScreen`, `toBeVisible`, `toHaveAccessibilityValue`; [belge](https://callstack.github.io/react-native-testing-library/docs/api/jest-matchers)); Vitest ^5.0.5 (kök; `ui-tokens` testi) | Ek kurulum yok; A21 ve kök sürümleri okunur | `eslint.org/docs/latest/rules/no-restricted-syntax` ve eşleştirici belgesi açılıyor (3 Kasım 2026). Kullanılmaz: `eslint-plugin-react-native-a11y` 3.5.1 (4 Kasım 2024; eş bağımlılık ESLint 8 ve altı), `eslint-plugin-react-native` 5.0.0 (30 Aralık 2024; ESLint 9 ve altı), çünkü kökte ESLint 10 var; `react-native-accessibility-engine` 3.2.0 (15 Kasım 2022; eş bağımlılık `react-test-renderer`, RNTL 14 `test-renderer` ister). Android Erişilebilirlik Tarayıcısı ve Xcode Accessibility Inspector taraması (Test stratejisi §11) kullanıcıya bırakılır | Yerleşik kural yetmezse kendi ESLint kuralı |
| Vitrin çatısı | Kendi rota ve bölümleri (`app/(tabs)/ayarlar/gelistirici/vitrin.tsx`; Tasarım sistemi §11). Hazır araç değerlendirildi, seçilmedi: Storybook for React Native `@storybook/react-native` 10.7.1 (30 Ekim 2026; npm) | Yok (depoda yazılır) | Eş bağımlılıkları `storybook ^10.5.4`, `@gorhom/bottom-sheet >=4`, `react-native-reanimated >=3`, `react-native-gesture-handler >=2` ve `react-native-safe-area-context` (npm kaydı, 3 Kasım 2026); vitrin ürünün içinde, `tasarimVitrini` bayrağıyla `dev` ve `internal` derlemede açılan bir rotadır (Mobil mimari §10); Storybook ayrı bir giriş noktası ve `storybook` paketi ekler | `@storybook/react-native` 10.7.1 |
| Ekran görüntüsü araçları (kullanıcı çalıştırır) | `adb` (Android SDK Platform-Tools; A00 "Android araçları"): `adb exec-out screencap` | Yok; Claude Code çalıştırmaz (CLAUDE.md, Çalışma düzeni 3) | Komutlar Doğrulama bölümünde; `adb shell am start` biçimi [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) belgesinde de kullanılıyor | Yok (emülatör ve ekran görüntüsü işleri kullanıcıya bırakılır) |
| Geliştirme derlemesi (hesap: altyapı) | EAS Build geliştirme derlemesi; Expo hesabı altyapıdır (A21) | A21.7'deki derleme kullanılır; A22'nin eklediği paketler yalnız JS'tir (`lucide-react-native`, `culori`, `ajv` ve tip bildirimleri); yerel modül gerekirse `eas build` ücretli iştir, tahmini maliyet söylenip kullanıcıya sorulur | A21.2 v1'in yerel modüllerini (Reusables'ın istediği `react-native-svg` dahil) bir kez kurmayı hedefler | Yerel derleme (A00 yol kararı) |

Kendimiz yapacağımız işler: `tokens.json` ve `schema.json` (değerler Tasarım sistemi'nden), jeton üreteci `build.ts`, kontrast testi ve `kontrast.md`, `ui-tokens` jetonlarının Reusables renk adlarına eşlenmesi, tema sağlayıcısının jetonlara bağlanması ve `useThemeTokens`, onaltılık renk kuralının ESLint ayarı, `IconButton`, `EmptyState`, `Snackbar` (Reusables'ta yok), `TezhipFrame`, `SectionDivider`, `UnverifiedBadge`, vitrin ekranı ve bölümleri. Alana özgü simgeler (mushaf, meal, tefsir, âyet sonu …) ve Arapça yazı tipleri ilk gereken aşamada alınır (A24 ve sonrası).

## Adımlar
### A22.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: npm kaydı (`dist-tags.latest`), belge sayfaları (`nativewind.dev`, `reactnativereusables.com`, `tailwindcss.com`, `lucide.dev`, `callstack.github.io`, `terrazzo.app`), Reusables kayıt adresleri (`https://reactnativereusables.com/r/nativewind/<bileşen>.json`), GitHub etiketleri ve commit'ler (`git ls-remote`; `api.github.com` kullanılmaz). Açılmayan adresin yerine yedek adayı kullan; değişen sürümü tabloya yaz. A21'in `## Tedarik` tablosuyla (NativeWind, Reusables, alt sayfa, yazı tipleri) fark varsa A21'in değeri geçerlidir; fark tabloya yazılır.
- Kitaplıkları ekle: `pnpm --filter @mutalaa/ui-tokens add -D ajv culori @types/culori`; `pnpm --filter @mutalaa/mobile add lucide-react-native culori`; `pnpm --filter @mutalaa/mobile add -D @types/culori`. Reusables bileşenlerini ekle: `pnpm dlx @react-native-reusables/cli@0.7.1 add --cwd apps/mobile --styling-library nativewind -y button dialog tabs toggle-group select switch progress popover skeleton`. `add`, `apps/mobile/components.json` ister (A21.2'deki `init` yazar); seçenekler ve bağımlı bileşenler `add --help` çıktısıyla doğrulanır. Kayıt adreslerine göre `text`, `icon`, `toggle` ve `native-only-animated-view` bileşenleri ile `@rn-primitives/dialog`, `tabs`, `toggle-group`, `toggle`, `select`, `switch`, `progress`, `popover` ve `slot` ilkelleri birlikte gelmelidir; CLI'nin eklediği ilkelleri ve yardımcı paketleri `package.json` içinden okuyup tabloya yaz.
- Yüklü sürümleri `pnpm-lock.yaml` içinden oku ve tabloyla karşılaştır; Expo'ya bağlı kitaplıklar için `pnpm --filter @mutalaa/mobile exec expo install --check` temiz olmalı. Fark varsa tabloya yaz. `lucide-react-native` tarball'ı (`npm view lucide-react-native@<sürüm> dist.tarball` adresi) `.tmp/` altında yeni bir klasöre indirilir ve SHA-256'sı tablodakiyle karşılaştırılır.
- Yazı tipi dosyalarının (A21.4'ün `assets/fonts/` kopyaları) Türkçe harf kapsamını `cmap` tablosundan yeniden ölç; sonuç tablodakiyle aynı olmalı.
- Kitaplıklar paket kaydından, yazı tipleri A21'in alımından gelir; bu aşamada `data/gelen/` indirmesi ve yeni kaynak kaydı gerekmez.
- **Bitti sayılır:** tablodaki her adres açılıyor; kilit dosyasındaki sürümler tabloyla aynı (fark tabloda yazılı); `expo install --check` temiz; Reusables bileşenleri eklenmiş; yazı tipi kapsamı tabloyla aynı.

### A22.1 · Doğrulamalar ve kararlar (`arastirmaci`)
- A21'de seçilen SDK `apps/mobile/package.json`'dan okunur. Şunlar resmî belgeden doğrulanır ve sonuç `/belge-esitle` ile işlenir (ön araştırma sonuçları 2 Kasım 2026'da alındı, 3 Kasım'da yeniden okundu ve maddelerin yanında yazılıdır):
  - NativeWind v4 ön ayarında CSS değişkenli renk tanımı ve `vars()` ile tema geçişi (TS-8; A21.1'de doğrulandıysa sonucu okunur). Ön araştırma: belge `import { vars } from "nativewind"` ve `style={vars({ '--brand-color': … })}` biçimini veriyor; kurulum belgesi `tailwindcss@^3.4.17` ister; `react-native-css-interop` 0.2.7 `tailwindcss@~3` eş bağımlılığı taşır.
  - React Native Reusables'ın beklediği tema değişkeni adları. Ön araştırma (`apps/showcase/global.css`, commit `385834c2196f8a303cbc9057d1ac768f3bde0a3b`): `--background`, `--foreground`, `--card`, `--card-foreground`, `--popover`, `--popover-foreground`, `--primary`, `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--muted`, `--muted-foreground`, `--accent`, `--accent-foreground`, `--destructive`, `--border`, `--input`, `--ring`, `--radius`, `--chart-1` … `--chart-5`. Değerler `H S% L%` üçlüsüdür; `tailwind.config.js` bunları `hsl(var(--background))` biçiminde kullanır ve ayrıca `destructive-foreground` rengini tanımlar. Eşleme A22.4'tedir.
  - Tailwind v4 `@theme` sözdizimi ve `[data-theme="gece"]` değişken blokları (editör Tailwind v4 kullanır: Teknoloji yığını 4.3.3, npm `latest` 4.3.4). Ön araştırma: belgede `@theme inline { --font-sans: var(--font-inter); }` biçimi var (yardımcı sınıf değişkene değil değere bağlanır); koyu mod belgesi `@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *))` örneğini veriyor. Çalışma anında tema değiştiren değişkenler için `inline` seçeneğinin gerekip gerekmediği burada, `pnpm dlx @tailwindcss/cli@4.3.4` ile üretilen CSS incelenerek sınanır.
  - Simge takımı (TS-3): Expo SDK 56'dan beri `@react-native-vector-icons/*` paketleri var; React Native Reusables'ın `Icon` bileşeni `lucide-react-native` tiplerine (`LucideIcon`, `LucideProps`) bağlı (ön araştırma, aynı commit). Öneri `lucide-react-native` 1.66.0; seçim `/karar` ile yazılır.
  - IBM Plex Sans'ın Türkçe kapsamı (â, î, û, ğ, ş, İ, ı): ön araştırmada `cmap` tablosunda hepsi var (TS-1'in ölçüm kısmı). Apple'ın varsayılan Dynamic Type tablosu: ön araştırmada HIG "Large (default)" tablosu Tasarım sistemi §3.2'deki arayüz boyutlarıyla aynı çıktı (Title 1 28/34, Title 2 22/28, Headline ve Body 17/22, Subhead 15/20, Footnote 13/18, Caption 1 12/16).
- TS-1 (IBM Plex Sans ya da Inter) ve TS-4 (öneri jetonların onayı) öneri değerlerdir; proje sahibine İ-22 ile sunulur. Aşama bunu beklemez, belgedeki değerlerle ilerler; karar değişirse jeton sürümü artar.
- **Bitti sayılır:** maddelerin sonucu dokümanda; simge takımı kararı karar defterinde.

### A22.2 · `packages/ui-tokens`
- Klasör düzeni Tasarım sistemi §10'daki gibidir; paket A02 iskeletinin üstüne kurulur (`src/index.ts`, `tsc -p tsconfig.build.json`). `build.ts` Node API'si kullandığından `tsconfig.build.json` kapsamı ve `types` ayarı buna göre güncellenir. `tokens.json` değerleri dokümandan aynen taşır:
  - §2.1 temel jetonlar; §2.2 ek rol jetonları (öneri, TS-4); §2.3 beş vurgu rengi (zemin ve işaret); §2.4 bölüm vurgusu; `sus` için `yalnizSus: true`.
  - §3.2 yazı rolleri ve kademe dizileri (`turkce`, `arapca`, varsayılan 5); §4 boşluk ve köşe; §5 hareket.
  - `kontrast` listesi: metin ↔ yüzey 4,5; `cizgi-guclu` ↔ yüzey 3,0; metin ↔ `vurgu.*.zemin` 4,5. Bütün metin jetonları sınandığı için (§2.5, §9) öteki metin rolleri de listeye girer.
- `schema.json` biçimi derlemede `ajv` ile doğrular. `build.ts` dört dosya üretir: `dist/tokens.ts`, `dist/nativewind-preset.js`, `dist/tailwind.css`, `dist/kontrast.md`.
- Paket `react-native`, `expo-*` ve DOM API'si kullanmaz ve çalışma zamanı bağımlılığı taşımaz (`ajv`, `culori` ve `@types/culori` yalnız `devDependencies`; Teknoloji yığını). Betikler: `build`, `test` (Vitest), `typecheck`. Turborepo `build` çıktısı `dist/**`.
- **Bitti sayılır:** `pnpm --filter @mutalaa/ui-tokens build` dört dosyayı üretir.

### A22.3 · Kontrast testi
- `test/contrast.test.ts` `culori`'nin `wcagContrast` işleviyle (WCAG göreli parlaklık formülü) hesaplar. `kontrast` listesindeki her çift üç temada sınanır; joker (`vurgu.*.zemin`) bütün vurgulara açılır.
- Hesaplanan oranlar Test stratejisi §11 tablosuyla ve Tasarım sistemi §2'deki değerlerle bir ondalık hassasiyetle aynıdır (ör. metin Kâğıt 16,3, çini mavisi Âhar 6,8, altın süs Kâğıt 2,96).
- `yalnizSus` jetonu hiçbir metin rolünde kullanılamaz; kullanılırsa test kırılır.
- Eşik altı çift derlemeyi durdurur: bozuk bir bellek içi jeton kümesiyle `build` işlevinin hata verdiği ayrıca sınanır. Sonuç tablosu `kontrast.md`'ye yazılır.
- **Bitti sayılır:** `pnpm --filter @mutalaa/ui-tokens test` yeşil; kırılma testi geçer.

### A22.4 · Mobil bağlama
- `apps/mobile` pakete `workspace:*` ile bağlanır. NativeWind yapılandırması `nativewind/preset` ile birlikte `ui-tokens` ön ayarını kullanır; A21'in tema sağlayıcısı etkin temanın değişkenlerini `vars()` ile uygular. Sınıflar `bg-yuzey text-metin` biçimindedir.
- React Native Reusables'ın tema değişkenleri aynı jetonlara eşlenir; kitaplığın kendi renk değerleri (`global.css` içindeki HSL üçlüleri) kullanılmaz. Ön ayar Reusables'ın renk adlarını jeton değişkenlerine bağlar (öneri): `background` → `yuzey`; `foreground`, `card-foreground`, `popover-foreground`, `secondary-foreground`, `accent-foreground` → `metin`; `card` ve `popover` → `yuzey-ust`; `primary` ve `ring` → `baglanti`; `primary-foreground` ve `destructive-foreground` → `baglanti-ustu`; `secondary` ve `muted` → `yuzey-cukur`; `muted-foreground` → `metin-ikincil`; `accent` → `secim`; `destructive` → `isaret`; `border` → `cizgi`; `input` → `cizgi-guclu`; `--radius` köşe jetonlarına (`md`, `lg`) bağlanır.
- `useThemeTokens()` ham renk isteyen yerler (SVG, Reanimated, alt sayfa) için `dist/tokens.ts`'den okur.
- Yazı: okuma rolleri kademe × sistem ölçeğiyle, arayüz rolleri sistem ölçeğiyle `maxFontSizeMultiplier` sınırına kadar büyür (sınır değeri öneri olarak yazılır). Okuma metni en az %200'e çıkar; Arapça ve Türkçe ölçek ayrıdır (`arabicScale`, `turkishScale`).
- Hareket: Hareketi Azalt açıkken süreler `anlik` olur (`AccessibilityInfo.isReduceMotionEnabled`).
- ESLint kuralı `#` ile başlayan renk dizgesini `packages/ui-tokens` dışında yakalar (öneri, Tasarım sistemi §10): çekirdek kural `no-restricted-syntax` ve `Literal[value=/^#[0-9A-Fa-f]{3,8}$/]` seçicisiyle yazılır (ek paket yok); `ui-tokens` içinde kapalıdır.
- Simge takımı A22.1 kararıyla kurulur (`lucide-react-native`, çizgi kalınlığı `strokeWidth` 1,5; Tasarım sistemi §8); sekme simgeleri yazılı etiketle birlikte görünür. Yalnız simgeden oluşan düğme tek bir `IconButton` bileşeninden çıkar ve erişilebilirlik etiketi zorunlu alandır (tip düzeyinde); vitrin render testi her `button` rolünün bir adı olduğunu doğrular.
- **Bitti sayılır:** tema testi üç temada `yuzey` ve `metin` değişkenlerinin jetonlardaki değerleri aldığını gösterir; `apps/mobile` içinde onaltılık renk yok; mobil `lint`, `typecheck` ve `test` yeşil.

### A22.5 · Tasarım vitrini
- Rota `app/(tabs)/ayarlar/gelistirici/vitrin.tsx`; içerik `src/features/settings/vitrin/`. `tasarimVitrini` `dev` ve `internal`'da açık, `public`'te kapalıdır; orada rota Ayarlar'a yönlenir.
- Denetimler: tema, yazı boyutu (varsayılan, kademe 8, %200), Hareketi Azalt, sayfa çevirme yönü, dokunma alanlarını gösteren katman. Ekran görüntüsünü betikle almak için aynı değerler sorgu parametresiyle de verilir: `?tema=gece&boyut=8` (öneri).
- Bölümler (Tasarım sistemi §11):
  - Renkler: değer ve çalışma anında hesaplanan kontrast; eşik altı çift `isaret` çerçevesiyle. Hesap, kontrast testinin kullandığı `culori` `wcagContrast` işleviyle yapılır.
  - Tipografi: bütün roller. Türkçe örnek açıkça sentetiktir ("Deneme paragrafı 1 · âlem, îman, ûlâ, İı, ğş"). Arapça rollerin örneği (Fâtiha'nın ilk âyeti) ve meal örneği yalnız `core` paketinden okunur; o bağlantı A24'te kurulur, o zamana kadar alan "Örnek metin `core` bağlanınca görünür" der.
  - Okuyucu parçaları: yer tutucu liste; A24, A25 ve A27 kendi bileşenlerini buraya ekler.
  - Genel bileşenler: React Native Reusables'tan düğme, iletişim kutusu, sekmeler, geçiş grubu, seçim kutusu, anahtar, ilerleme, açılır pencere; `EmptyState`, `Skeleton`, `Snackbar` ("Geri al" ekrandan çıkılana kadar durur, zamanlayıcıyla kaybolmaz: Tasarım sistemi §9, Depolama yöneticisi).
  - Motifler ve rozetler: `TezhipFrame`, `SectionDivider` (`currentColor`), `UnverifiedBadge` ("doğrulanmamış").
- **Bitti sayılır:** vitrinin render testi (üç tema, her bölüm hatasız çizilir) ve `public` yönlendirme testi yeşil; `dev` derlemede açılması kullanıcıya bırakılır.

### A22.6 · Görsel denetim (kullanıcıya bırakılır)
- Emülatörde ya da cihazda açma, ekran görüntüsü alma ve görüntüleri okuma kullanıcıya bırakılır (CLAUDE.md, Çalışma düzeni 3). Aşama bunu beklemez; ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" yazılır.
- Claude Code vitrinin kaynağını ve komutları hazırlar: 9 görüntünün komutları (Kâğıt, Âhar, Gece × varsayılan, kademe 8, %200 → `.tmp/vitrin/<tema>-<boyut>.png`) Doğrulama bölümündedir.
- `arayuz-denetcisi` vitrin kaynağını Tasarım sistemi §9 kontrol listesiyle kod düzeyinde inceler: renkler `ui-tokens`'tan, simgeli düğmelerde erişilebilirlik adı, hedef boyutu (en az 44×44 pt) ve `hitSlop`, `maxFontSizeMultiplier` sınırı, `textTransform` kullanılmaması, renk tek başına anlam taşımaması. Kullanıcı görüntüleri aldığında aynı liste görüntülere de uygulanır: kontrast listesinde eşik altı çift yok, %200'de kesilen metin yok, dokunma katmanında 44×44 pt altında hedef yok, Türkçe harfler doğru.
- Yeni yerel modül eklenirse yeni EAS geliştirme derlemesi gerekir; `eas build` ücretli iştir: tahmini maliyet söylenip kullanıcıya sorulur (CLAUDE.md, kural 11).
- Referans görüntülerin saklanacağı yer öneridir (`apps/mobile/test/vitrin-referans/`); her jeton ya da bileşen değişikliğinde yeniden alınır.
- **Bitti sayılır:** kod düzeyindeki `arayuz-denetcisi` incelemesinde engelleyici bulgu yok; 9 görüntü ve görüntü incelemesi ilerleme notunda "kullanıcıya bırakıldı" ya da kullanıcının sonuçlarıyla.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki her adres açılıyor; kilit dosyasındaki sürümler tabloyla aynı; `expo install --check` temiz; Reusables bileşenleri eklenmiş (A22.0).
- [ ] `pnpm --filter @mutalaa/ui-tokens build` `dist/tokens.ts`, `dist/nativewind-preset.js`, `dist/tailwind.css` ve `dist/kontrast.md` üretir.
- [ ] `pnpm --filter @mutalaa/ui-tokens test` yeşil: her çift eşikte; oranlar Test stratejisi §11 ile aynı; bozuk küme derlemeyi durdurur; `sus` metin rolünde yok.
- [ ] `kontrast.md` üç temanın bütün çiftlerini oranlarıyla listeler (gözle kontrol).
- [ ] `apps/mobile/src` ve `apps/mobile/app` içinde onaltılık renk dizgesi yok; ESLint renk kuralı örnek ihlali yakalar (test).
- [ ] `pnpm --filter @mutalaa/mobile lint`, `typecheck` ve `test` yeşil; vitrin `public` bayrağıyla Ayarlar'a yönlenir (test).
- [ ] Kontrast testi CI'daki `turbo run test` içinde koşar (`ci-ts.yml`; Test stratejisi §12).
- [ ] Simge takımı kararı ve TS-8 sonucu karar defterinde ya da dokümanda.
- [ ] Kod düzeyindeki `arayuz-denetcisi` raporunda engelleyici bulgu yok; 9 ekran görüntüsü ve görüntü incelemesi ilerleme notunda "kullanıcıya bırakıldı" ya da kullanıcının sonuçlarıyla.

## Doğrulama
```bash
pnpm --filter @mutalaa/ui-tokens build
ls packages/ui-tokens/dist
pnpm --filter @mutalaa/ui-tokens test
pnpm --filter @mutalaa/ui-tokens typecheck
grep -rnE "['\"]#[0-9A-Fa-f]{3,8}['\"]" apps/mobile/src apps/mobile/app || echo "onaltılık renk yok"
pnpm --filter @mutalaa/mobile exec expo install --check
pnpm --filter @mutalaa/mobile lint && pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile test
```
Aşağıdaki komutlar emülatör ve ekran görüntüsü işidir; kullanıcıya bırakılır (CLAUDE.md, Çalışma düzeni 3):
```bash
mkdir -p .tmp/vitrin
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ayarlar/gelistirici/vitrin?tema=gece&boyut=8'"
adb exec-out screencap -p > .tmp/vitrin/gece-8.png
```
Son iki komut dokuz tema ve boyut birleşimi için tekrarlanır. `adb shell` içinde `&` tırnak içinde kalmalıdır.

## Dikkat
- Değerler dokümandan aynen alınır; yeni değer "öneri" diye işaretlenir. Jeton değişikliği paket sürümünü artırır ve vitrin görüntüleri yeniden alınır (kullanıcı).
- `sus` açık temalarda metin olarak kullanılmaz (2,96:1 ve 3,33:1). Altın yalnız süs çizgisidir.
- Renk tek başına anlam taşımaz: vurgu zemin, alt çizgi ve simgeyle; güven etiketi yazıyla.
- İçerik etiği: Kur'an ve meal örneği elle yazılmaz, yalnız `core` paketinden (kaynak dosyalarından alınmış parça) okunur. Risale katmanları vitrinde açıkça sentetik metinle gösterilir ("Deneme paragrafı 1 …"); sentetik Türkçe örnek "Deneme" diye başlar.
- Türkçe metinde `textTransform: 'uppercase'` kullanılmaz (öneri); büyük harf `trUpper` ile.
- Klişe motif yok: cami silueti, hilal, ay-yıldız, yeşil-altın gradyan, süs amaçlı sahte Arapça (Tasarım sistemi §7, §8).
- `packages/ui-tokens` platformdan bağımsızdır ve çalışma zamanı bağımlılığı taşımaz (Teknoloji yığını); NativeWind ve Tailwind çıktıları üretilir, paket onları içe aktarmaz.
- Reusables bileşenleri depoya kopyalanır; kitaplığın kendi renk değerleri kullanılmaz, sınıflar jeton değişkenlerine eşlenir (A22.4).
- Git Bash'te `adb` yol dönüşümü ve tırnak sorunlarında `windows-sorun`.
- Commit kapsamları `ui-tokens` ve `mobile`.

## İnsan adımları
- İ-22 · Öneri işaretli değerlerin onayı: TS-4 (ek rol jetonları, vurgu renkleri, `bolum-risale`) ve TS-1 (arayüz yazı tipi) proje sahibine sunulur. Aşamayı durdurmaz; belgedeki değerler kullanılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- Emülatör ve ekran görüntüsü işleri (A22.6) kullanıcıya bırakılır; aşamayı bekletmez.

## Çıktılar
- `packages/ui-tokens/`: `package.json`, `src/tokens.json`, `src/schema.json`, `src/build.ts`, `test/contrast.test.ts`; üretilen `dist/`
- `apps/mobile/`: tema sağlayıcısı, `useThemeTokens`, NativeWind ön ayar bağlantısı, Reusables bileşenleri, `IconButton`, ESLint renk kuralı, simge takımı (`lucide-react-native`)
- `apps/mobile/app/(tabs)/ayarlar/gelistirici/vitrin.tsx`, `apps/mobile/src/features/settings/vitrin/`
- Karar defterinde simge takımı; `/belge-esitle` ile işlenen TS-8 ve yazı tipi doğrulamaları; `.tmp/vitrin/` (git dışı; görüntüleri kullanıcı alır)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A22-tasarim-vitrini.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A21](./A21-mobil-iskelet.md) · Sonraki: [A23](./A23-cihaz-veri-katmani.md)
