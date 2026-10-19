---
paths:
  - "apps/mobile/**"
---

# Mobil uygulama kuralları (`apps/mobile`)

Kaynak: [Mobil mimari](../../docs/06-mobil/01-mobil-mimari.md), [Okuma deneyimi](../../docs/01-urun/02-okuma-deneyimi.md), [Tasarım sistemi](../../docs/01-urun/04-tasarim-sistemi.md).

- **Katmanlar.** `app/` yalnız rota ve ekran bağlar, iş mantığı tutmaz. Özellikler (`src/features/*`) birbirini yalnız `index.ts` üzerinden kullanır. Yön `app → features → (db, packs, lib) → packages/*`; ters yönü ESLint engeller.
- **Kitaplıklar.** Expo'ya bağlı paketler `npx expo install` ile kurulur. NativeWind v4, React Native Reusables, @gorhom/bottom-sheet, Reanimated 4, Zustand, TanStack Query, MMKV (K-29). expo-av, react-native-track-player ve WatermelonDB kullanılmaz (K-28, K-30).
- **Veri.** İçerik paketleri ATTACH ile bağlanır; aynı anda en çok 8 şema. `user.db` tablolarında `id` (UUIDv7), `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id` sütunları bulunur (K-15). Arama metni ekranda gösterilmez; okuyucu yalnız kanonik metni gösterir.
- **Derleme türleri.** `APP_FLAVOR` = `dev` | `internal` | `public`. Paket görünürlüğü yalnız `src/packs/visibility.ts` içindeki `isPackVisible` ile belirlenir. İmzasız ya da imzası tutmayan manifest okunmaz. EAS Update gömülü `core` paketini değiştirmez.
- **Arayüz.** Renk, boşluk ve yazı boyutu yalnız `packages/ui-tokens` jetonlarından gelir; sabit renk kodu yazılmaz. Türkçe metinler i18n dosyasındadır. Arapça metin `lang="ar"` ve sağdan sola yazılır; Arapça ve Türkçe yazı boyutu ayrı ayarlanır.
- **Erişilebilirlik.** Her dokunulabilir öğe en az 44×44 pt, Türkçe erişilebilirlik etiketi taşır; her kaydırma jestinin görünür düğme karşılığı vardır; Hareketi Azalt açıkken kayan geçiş yerine solma kullanılır; renk tek başına anlam taşımaz.
- **Test kimlikleri** çapa gramerini kullanır: `ayet-q:2:255`, `kelime-q:2:255:3` ([Test stratejisi](../../docs/07-yayin/03-test-stratejisi.md) §9).
- **Gizlilik.** Sentry `dev` derlemede kapalıdır; olaylara kullanıcı tanımlayıcısı, not metni ya da arama sorgusu girmez.
- **Derleme.** Geliştirme derlemesi varsayılan olarak EAS bulutunda üretilir (`eas build` kullanıcı onayı ister). Derleme `--non-interactive --no-wait` ile başlatılır ve beklenmez; durum `eas build:list … --json --non-interactive` ile izlenir, APK `.tmp/` altına indirilir ([A21](../../docs/10-claude-code/asamalar/A21-mobil-iskelet.md) A21.7). Durum sorgusu yeni derleme başlatmaz. Ekranı denetlemek için `mobil-ekran` becerisindeki emülatör ekran görüntüsü yolunu ve `arayuz-denetcisi` ajanını kullan.
