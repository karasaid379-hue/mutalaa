# A23 · Cihaz veri katmanı

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A13](./A13-yayinlayici-ve-kalite-kapisi.md) · [A21](./A21-mobil-iskelet.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `paket-yayini` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A23`

## Amaç
Cihazdaki üç veri katmanı kurulur: gömülü `core` ve ATTACH edilen metin paketlerinden oluşan salt okunur içerik bağlantısı, senkrona hazır `user.db` ve cihaza özgü `device.db`. Aşama tedarikle başlar: kitaplıkların sürümleri doğrulanır ve sabitlenir (A23.0). Manifest istemcisi imzayı doğrular ve `isPackVisible` ile kalite kapısının ikinci kontrolünü uygular (derleme türü ve `test-` önekli kaynak kuralı). `scripts/fetch-core.mjs` gömülü `core`'u imzalı manifestten alır ve özetini doğrular. Okuyucu, Defterim, Depolama ve ses bu katmanın üstüne kurulur.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §6 Veri erişimi, §10 (`isPackVisible`, manifest imzası), §11 Hata ve çevrimdışı davranış
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.1, §5 `manifest.json`, §6 Sürümleme, §7, §8 Cihazda yaşam döngüsü
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §1–§3
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §2 `device.db`, §3 dosya düzeni, §5 bütünlük
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/mobile`), §7 son paragraf (`fetch-core.mjs`)
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §6 adım 6–7, §10.3
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 · [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 Derleme türleri ve görünürlük, §4.2 Manifest imzası, §4.3 Uygulamadaki ikinci kontrol

## Kapsam
**Yapılır**
- `packages/content-schema`: `user.db` Drizzle şeması ve ortak senkron sütunları. `packages/reader-core` iskeleti: SQL yürütücü arayüzü ve HLC.
- `apps/mobile/src/db`: yollar, `user.db`, `device.db`, göçler, `ContentDb` (ATTACH, en çok 8 şema), mushaf ve ses paketleri için ayrı salt okunur bağlantılar, `DbGate`, açılış sırası, gömülü `core` içe aktarımı, `validatePack`.
- `apps/mobile/src/packs`: manifest istemcisi, imza doğrulama, açık anahtarlar, `isPackVisible`, `pack_source` denetimi.
- `src/lib/errors.ts` (`AppError`), `src/lib/network.ts`; `scripts/fetch-core.mjs` ve `eas-build-post-install`; göç fikstürü testleri.
- Kitaplıkların kurulumu ve sürümlerinin sabitlenmesi (A23.0): `expo-network`, `expo-crypto`, `drizzle-orm`, `drizzle-kit`, `zod`, `@noble/ed25519`, `@noble/hashes`, `canonicalize`, `uuid`.

**Yapılmaz**
- İndirme kuyruğu, uzlaştırmanın kuyruk ve sesle ilgili maddeleri, Depolama ekranı ve manifest güncelleme akışı: [A29](./A29-kutuphane-ve-depolama.md).
- Okuyucu sorguları ve sayfa modeli (A24); arama sorguları (A28); Defterim ekranları ve yedek (A30); senkron ve giden kutusu yazımı (A36).
- Yayınlayıcının imza ve paket kodu (A13'te). Değişiklik gerekirse `sunucu-gelistirici` ile ayrı iş açılır.

## Tedarik
Bu aşama dışarıdan metin ya da veri almaz; kitaplık ve araç alır. Sürümler npm kaydından, API adları Expo SDK 58 ve Drizzle belgelerinden, SQLite özellikleri paket arşivinin incelenmesinden ve Node ölçümünden okundu (2 Kasım 2026). Expo paketlerinin sürümleri `expo@58.0.22` içindeki `bundledNativeModules.json` ile aynıdır (`expo-sqlite` ~58.0.15, `expo-file-system` ~58.0.13, `expo-network` ~58.0.4, `expo-asset` ~58.0.19, `expo-crypto` ~58.0.7; dosyanın SHA-256 değeri `3b2c9d80113acb8ff74b6203c884196f70299bce4da7bb4b46a7faa41d41300d`, A21 ile aynı). A23.0 bu ölçümleri yineler.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Cihazda SQLite (ATTACH, FTS5, değişiklik dinleyici, gömülü varlık) | `expo-sqlite` 58.0.15 (npm, 31 Ekim 2026; Expo SDK 58 hattı, `expo` 58.0.22; npm arşivi, 10.769.785 bayt; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/sqlite/)) | A21'de `expo install` ile kurulur (sürümü `expo` belirler); A23.0 sürümü `pnpm-lock.yaml` ile doğrular | Ölçüldü (paket kaynağı, 2 Kasım 2026): paketlenen SQLite 3.53.3; `enableFTS` (varsayılan açık) FTS5 bayraklarını açar (`android/build.gradle`, `ios/ExpoSQLite.podspec`); `SQLITE_MAX_ATTACHED` bayrağı yok, derleme varsayılanı 10 (uygulama sınırı 8 kalır); yerel kodda `SQLITE_OPEN_URI` ve `SQLITE_USE_URI` yok (yalnız web'de), yani `mode=ro` URI dosya adı kullanılmaz, salt okunurluk `PRAGMA query_only` ile sağlanır; `customBuildFlags` eklenti seçeneği derleme bayrağı ekleyebilir (yeni geliştirme derlemesi ister); belgede `openDatabaseAsync`, `enableChangeListener`, `SQLiteProvider` `assetSource`, `defaultDatabaseDirectory` var. Cihaz ölçümü (ATTACH sayısı, `query_only` ile ATTACH, şema nitelemeli `MATCH`) kullanıcıya bırakılır | `@op-engineering/op-sqlite` 19.0.3 (npm, 29 Ekim 2026; Drizzle sürücüsü var; yalnız `expo-sqlite` sınırı aşılmazsa) |
| Cihaz veritabanları için ORM ve göç üretimi | `drizzle-orm` 0.45.4 (npm, 8 Ekim 2026; arşiv 1.234.631 bayt) ve `drizzle-kit` 0.31.11 (npm, 21 Eylül 2026); `.sql` göçleri için `babel-plugin-inline-import` 3.0.0 (npm, 5 Haziran 2018); [Drizzle Expo belgesi](https://orm.drizzle.team/docs/get-started/expo-new) | `pnpm add` (`drizzle-orm` `apps/mobile` ve `packages/content-schema`; `drizzle-kit` ve eklenti geliştirme bağımlılığı); `pnpm-lock.yaml` | Ölçüldü: arşivde `drizzle-orm/expo-sqlite` altında `driver`, `migrator` (`useMigrations`, `migrate`), `query` (`useLiveQuery`) ve `session` var; `peerDependencies` `expo-sqlite >=14.0.0`; belge `drizzle.config.ts` için `driver: 'expo'`, Metro için `sourceExts.push('sql')`, Babel için `inline-import` (`.sql`) ve canlı sorgu için `enableChangeListener: true` ister | Göç dosyalarını TypeScript modülüne çeviren küçük betik ve `PRAGMA user_version` ile ham SQL göçleri (kendimiz; eklenti çalışmazsa) |
| Manifest biçim doğrulaması | `zod` 4.6.7 (npm, 12 Ekim 2026; bağımlılığı yok) | `pnpm add` (`apps/mobile`; `packages/*` dış bağımlılık almaz); `pnpm-lock.yaml` | npm kaydı (2 Kasım 2026); A23.4 testi A13'ün imzalı fikstür manifestinin geçtiğini, `manifest.schema.json` kurallarını bozan manifestlerin reddedildiğini doğrular | Elle yazılmış tip denetleyici (kendimiz; manifest düz bir yapıdır) |
| Manifest imzası (Ed25519) ve kanonik JSON (RFC 8785), JS tarafı | `@noble/ed25519` 3.2.0 (npm, 27 Ağustos 2026; [paulmillr/noble-ed25519](https://github.com/paulmillr/noble-ed25519) etiket 3.2.0 @f3790a0), `@noble/hashes` 2.4.0 (npm, 27 Ağustos 2026; `sha512`) ve `canonicalize` 5.1.0 (npm, 18 Eylül 2026; [erdtman/canonicalize](https://github.com/erdtman/canonicalize) etiket v5.1.0 @31fb117; yalnız ESM, Node 22+) | `pnpm add` (`apps/mobile`; `fetch-core.mjs` aynı paketleri kullanır); A13 aynı seçimi not etti | Ölçüldü (Node 24.21.0, 2 Kasım 2026): Node `crypto` ile üretilen 64 baytlık imza `verifyAsync` ve `verify` ile geçerli; `globalThis.crypto` kaldırılmış ortamda (WebCrypto ve `getRandomValues` yok, Hermes benzeri) de geçerli; değiştirilmiş mesaj ve değiştirilmiş imza reddedildi; Türkçe harfli örnek manifest 127 bayt kanonik çıktı verdi. README, React Native için `ed.hashes.sha512` ve `sha512Async` atamasını ister. Altı RFC çifti ve A13 fikstürü A23.4'te sınanır (çiftleri A13.0 indirir) | `@noble/curves` 2.4.0 (npm, 27 Ağustos 2026; `ed25519`); betikte Node'un yerleşik `node:crypto` Ed25519 doğrulaması; JCS için RFC yazarının `cyberphone/json-canonicalization` deposundaki `node-es6` uygulaması (@32a4819) |
| Ağ durumu | `expo-network` 58.0.4 (npm, 21 Ekim 2026; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/network/)) | `expo install expo-network` (A21'in kurulum listesinde yok; yeni yerel modül, yeni geliştirme derlemesi ister) | Belgede `addNetworkStateListener`, `getNetworkStateAsync`, `useNetworkState` ve `isInternetReachable` var (2 Kasım 2026) | `@react-native-community/netinfo` 12.0.1 (npm, 14 Şubat 2026) |
| Dosya yolları, kopyalama ve SHA-256 özeti | `expo-file-system` 58.0.13 (npm, 28 Ekim 2026; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/filesystem/)) | A21'de `expo install` ile kurulur | Belgede `Paths.document`, `downloadFileAsync` ve `digest(algorithm)` (küçük harf onaltılık çıktı, `SHA-256` değeri) var; Depolama yöneticisi DY-9 aynı sonuca varır | `expo-crypto` 58.0.7 `digest` (bellekte çalışır; büyük dosyada kullanılmaz) |
| Gömülü `core` varlığının cihaza kopyalanması | `expo-asset` 58.0.19 (npm, 28 Ekim 2026; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/asset/)) | `expo` ile gelir; ayrı kurulum gerekmez | Belgede `Asset.fromModule`, `downloadAsync` ve `localUri` var; `.db` uzantısı Metro varlık listesine eklenir | `SQLiteProvider` `assetSource` (expo-sqlite kendi kopyasını yapar; sürümlü ad vermediği için ikinci tercih) |
| Satır kimliği UUIDv7 ve güvenli rastgele bayt (KV-4) | `uuid` 14.0.3 (npm, 10 Ekim 2026; `v7()` ve `rng` seçeneği; arşiv 14.991 bayt) ve `expo-crypto` 58.0.7 (npm, 16 Ekim 2026; `getRandomBytes`, `getRandomValues`, `randomUUID`) | `pnpm add uuid`; `expo install expo-crypto` (A21'in kurulum listesinde yok; yeni yerel modül) | Ölçüldü (Node 24.21.0, 2 Kasım 2026): `v7({ rng })` ile 2000 kimlik tekil, sürüm hanesi 7; `rng` verilince kitaplık aynı milisaniyedeki sırayı korumaz, satır sırası `hlc` ile belirlenir. README: React Native'de `crypto.getRandomValues` yoksa `react-native-get-random-values` içe aktarılır ya da `rng` verilir; `device_id` (UUIDv4) `randomUUID()` ile üretilir | `react-native-get-random-values` ile `uuid`'in varsayılan rastgele kaynağı |
| Son geçerli manifest önbelleği ve sorgu durumu (A21'den) | `react-native-mmkv` 4.3.2 (npm, 22 Haziran 2026) ve `@tanstack/react-query` 5.105.1 (npm, 1 Kasım 2026; `onlineManager`) | A21'de kurulur; bu aşama yeni kitaplık eklemez | npm kaydı (2 Kasım 2026) | `expo-sqlite/kv-store` (`expo-sqlite` ile gelir) |
| Node'da göç testi için SQLite sürücüsü | `node:sqlite` (Node 24.21.0'da yerleşik; SQLite 3.53.4, `DatabaseSync`) | Kurulum yok | Ölçüldü (2 Kasım 2026): FTS5 (`unicode61`, `trigram`) açık, `MAX_ATTACHED=10`, ondan sonraki ATTACH "too many attached databases" ile durur; `query_only=ON` iken ATTACH çalışır, `INSERT` reddedilir; şema nitelemeli `MATCH` çalışır. Jest içinde içe aktarım A23.1'de sınanır | `better-sqlite3` 13.0.3 (npm, 5 Ağustos 2026; Node 22+; yerel eklenti, hazır ikili yoksa derleme ister) |
| Derleme ortamı ve `eas-build-post-install` kancası | EAS Build (hesap: altyapı); [kanca belgesi](https://docs.expo.dev/build-reference/npm-hooks/); [yükleme kuralı](https://docs.expo.dev/build-reference/easignore/) | `eas build` (ücretli iş: tahmini maliyet söylenir, kullanıcı onayı alınır); yerel derleme A00 yol kararına bağlıdır | Belgede `eas-build-post-install` kancası var; yükleme `.gitignore`'u izler, git dışı `core.db` yüklenmez ve kanca onu indirir; profil ayrımı `eas.json` `env` içindeki `APP_FLAVOR` ile yapılır (Mobil mimari §10; `EAS_BUILD_PROFILE` ilgili belge sayfalarında bulunamadı); belgedeki güncel imajlar Node 22.x taşır ve `eas.json` `node` alanı sürümü sabitler (`canonicalize` Node 22+ ister) | Yerel derleme |

Kendimiz yapacağımız işler: `ContentDb` (ATTACH yönetimi, LRU) ve `Mutex` (`src/lib/mutex.ts`; Mobil mimari §6.3'teki `run` ve `shared`), `DbGate` açılış sırası, `validatePack`, HLC (`tick`, `recv`) ve yazma yardımcısı, `user.db` ve `device.db` şemaları, manifest istemcisi (ETag, son geçerli kopya), `isPackVisible`, `scripts/fetch-core.mjs`, `AppError`, göç fikstürleri. HLC biçimi (`{12 hane}-{4 hane}-{16 hane}`) sunucuyla ortak sözleşmedir; npm'deki hazır saatler uymaz (`@sozai/hlc` 0.1.0: `<ISO zaman>:<sayaç>:<düğüm>`; `liepoch` 1.0.3: 16 haneli onaltılık, düğüm kısmı yok; 2 Kasım 2026). Öteki işlerin hazır karşılığı yoktur; hepsi uygulamaya özgüdür. `core` paketi, `dev` manifesti ve imzalı fikstür manifesti A13'ün çıktısıdır.

## Adımlar
### A23.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: npm kaydı (`expo`, `expo-sqlite`, `expo-file-system`, `expo-network`, `expo-asset`, `expo-crypto`, `drizzle-orm`, `drizzle-kit`, `babel-plugin-inline-import`, `zod`, `@noble/ed25519`, `@noble/hashes`, `canonicalize`, `uuid`), Expo SDK 58 belge sayfaları, Drizzle Expo belgesi, GitHub için `git ls-remote` (GitHub API'si kullanılmaz). Açılmayan adresin ya da yayından kalkan sürümün yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Kitaplıklarda sürüm paket kaydından doğrulanır: Expo paketleri `expo install` ile SDK'ya uygun sürümde, öteki paketler `pnpm add` ile kurulur; tam sürümler `package.json` ve `pnpm-lock.yaml` içinde durur ve `pnpm list` çıktısı tablodakiyle karşılaştırılır. Ön sürüm alınmaz.
- Tablodaki ölçümler yinelenir ve sayılarıyla rapora yazılır: `node:sqlite` ile `PRAGMA compile_options` (`ENABLE_FTS5`, `MAX_ATTACHED`), `query_only` ile ATTACH ve şema nitelemeli `MATCH`; `@noble/ed25519` ile Node `crypto` imzasının gidiş-dönüşü (WebCrypto yokken de); `expo-sqlite` arşivinde SQLite sürümü, FTS5 bayrağı, `SQLITE_MAX_ATTACHED` ve URI bayrakları. İncelenen arşivler yalnız okunur: `.tmp/` altında yeni ve boş klasöre iner, kurulum betikleri çalıştırılmaz, ölçüm betikleri ayrı klasörde durur.
- Bu aşama içerik kaynağı almaz: `data/gelen/` altına dosya inmez, `pipeline/sources/` altına kayıt yazılmaz. Test verisi kodla üretilen sentetik satırlardır; `core` paketi ve imzalı manifest A13'ün çıktısıdır. `expo-network` ve `expo-crypto` yeni yerel modüldür: kurulum yeni geliştirme derlemesi ister (A23.6).
- **Bitti sayılır:** tablodaki her adres açıldı; kitaplık sürümleri `pnpm-lock.yaml` içinde sabit ve tablodakiyle aynı (ya da yeni sürüm gerekçesiyle tabloya yazıldı); ölçülecek hücrelerin hepsi sayıyla dolu ve sonuçlar A23.1'e girdi olarak raporlu.

### A23.1 · Doğrulamalar ve ölçümler
- Tedarik'in (A23.0) ölçtükleri ve `arastirmaci`nın seçilen SDK için resmî belgeden doğruladıkları `/belge-esitle` ile işlenir (MM-5, MM-6, AR-6, IP-7, IP-8, KV-4):
  - expo-sqlite: `openDatabaseAsync(ad, seçenekler, klasör)`, `enableChangeListener`; gömülü `core` için `SQLiteProvider` `assetSource` ile `expo-asset` kopyalaması arasındaki seçim (Mobil mimari §6.2). URI dosya adı (`mode=ro`, `immutable=1`): paket kaynağında yerel `SQLITE_OPEN_URI` ve `SQLITE_USE_URI` yoktur (Tedarik); salt okunurluk `PRAGMA query_only` ile sağlanır, URI gerekmez.
  - Drizzle: `drizzle-orm/expo-sqlite`, `useMigrations`, `useLiveQuery`; `.sql` göçleri için Babel (`inline-import`) ve Metro (`sourceExts`) ayarı; drizzle-kit ayarı (`driver: 'expo'`).
  - expo-file-system: `Paths`, `File`, `Directory` adları ve `File.digest('SHA-256')` (DY-9).
  - Ağ durumu için `expo-network` ya da `@react-native-community/netinfo` (Mobil mimari §11); UUIDv7 üretimi ve güvenli rastgele sayı kaynağı (KV-4): `uuid` `v7({ rng })` ve `expo-crypto`.
  - EAS derlemesinde `eas.json` `env` içindeki `APP_FLAVOR`'ın `eas-build-post-install` kancasında görünmesi; git dışı dosyaların EAS'e yüklenmediği (yükleme `.gitignore`'u izler; A23.5 için).
  - Metro'nun sürümlü varlık adını sabit `require()` olmadan paketleyip paketleyemediği (`require.context`; BÇ-25'teki seçenek).
- İmza: A13'te Yayınlayıcının kullandığı algoritma (Ed25519), kanonik JSON yöntemi (RFC 8785) ve `kid` biçimi koddan ve karar defterinden okunur. Uygulama tarafı kitaplık Tedarik'teki seçimdir: `@noble/ed25519`, `@noble/hashes` ve `canonicalize` (IP-7). Node'da göç testi için SQLite sürücüsü `node:sqlite`'tır (Tedarik); Jest içinde `node:sqlite` içe aktarımı sınanır, olmazsa göç testi kökteki Vitest ile ya da `node --test` ile ayrı dosyada çalışır. İki seçim `/karar` ile yazılır.
- Cihazda ölçülecekler kullanıcıya bırakılır (CLAUDE.md, çalışma düzeni 3) ve aşamayı bekletmez: `SQLITE_MAX_ATTACHED` değeri (MM-5, AR-6, IP-8; kaynakta bayrak yok, varsayılan 10), `PRAGMA query_only = ON` iken `ATTACH` (MM-6) ve şema nitelemeli FTS5 `MATCH`. Ölçüm kodu geliştirici menüsündeki "Veri katmanı" ekranına sınama eylemi olarak yazılır (öneri); çalıştırmak kullanıcıya aittir ve sonuç ilerleme notunda "kullanıcıya bırakıldı" diye durur.
- **Bitti sayılır:** doğrulama ve ölçüm sonuçları dokümanda (cihaz ölçümleri "kullanıcıya bırakıldı" notuyla); imza kitaplığı ve Node sürücüsü karar defterinde.

### A23.2 · Şemalar, göçler ve HLC
- `packages/content-schema/src/user/`: `columns.ts` (`syncColumns`: `id`, `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id`) ve [Kullanıcı verisi](../../03-veri/04-kullanici-verisi-ve-senkron.md) §2'deki tablolar: `bookmark`, `highlight`, `note`, `reading_position`, `hatim`, `hatim_page`, `collection`, `setting`, `vocab` (v1.x tablosu, şema şimdiden), yalnız yerel `outbox` ve `sync_state`. Dizinler ve `CHECK` kısıtları DDL'deki gibidir.
- `apps/mobile/src/db/device/schema.ts`: Depolama yöneticisi §2'deki `installed_pack`, `download_job`, `audio_file` (`audio_file` anahtarı `(kayit, sure, dosya_surumu)`, K-41).
- Göçler drizzle-kit ile `apps/mobile/src/db/migrations/user/` ve `.../device/` altına üretilir; uygulanmış göç değiştirilmez.
- `packages/reader-core` açılır: içerik sorguları için SQL yürütücü arayüzü (platform kodu içeri verilir) ve `src/sync/hlc.ts` (`tick`, `recv`; biçim `{12 hane}-{4 hane}-{16 hane}` küçük harf onaltılık; son değer `sync_state.hlc_last`).
- Yazma yardımcısı: her kullanıcı yazımı tek işlemdir; satır UUIDv7 `id` (`uuid` `v7({ rng })`, rastgele baytlar `expo-crypto` `getRandomBytes`; Tedarik), yeni `hlc`, `updated_at` ve `device_id` alır; `base_version` 0 kalır; v1'de `outbox` yazılmaz. `device_id` ilk açılışta UUIDv4 olarak (`expo-crypto` `randomUUID()`) üretilir ve `sync_state`'te durur (öneri).
- **Bitti sayılır:** `content-schema` testi her senkron tablosunda altı ortak sütunu bulur; HLC testleri (tekdüzelik, saat geri alınınca küçülmeme, dizgi sırası = zaman sırası, düğüm kısmı `device_id`'den) yeşil.

### A23.3 · Bağlantılar, açılış sırası ve paket doğrulaması
- `src/db/paths.ts`: `Paths.document/mutalaa/db/`, `.../packs/`, `.../tmp/`. `src/db/user.ts` ve `src/db/device.ts`: WAL ve `foreign_keys`; `user.db` `enableChangeListener: true` ile.
- `src/db/content.ts`: `ContentDb` Mobil mimari §6.3'teki gibi: tek bağlantı, `PRAGMA query_only`, `MAX_ATTACHED = 8`, takma ad `p_` + `[a-z0-9_]`, dosya yolu her zaman parametre, `Mutex`, LRU ile ayırma, süren sorgu bitmeden `DETACH` yok. Şema yerleşimi İçerik paketleri §2 tablosuyla aynıdır.
- `src/db/packs.ts`: mushaf ve ses paketleri ATTACH edilmez; ayrı salt okunur bağlantılar, LRU (A26 ve A27 kullanır).
- `DbGate` (A21'deki yer tutucu) Mobil mimari §6.2 sırasını uygular: MMKV'den eşzamanlı tema, mod ve son konum; gömülü `core` içe aktarımı (ilk açılışta ya da yeni gömülü sürümde); `user.db` ve `device.db` göçleri; içerik bağlantısı. Göçler bitmeden ekran çizilmez.
- Gömülü `core` dosyasının adı BÇ-25 kararıdır. Metro `require()` yalnız sabit yol kabul eder; belgelerdeki `assets/db/core-<sürüm>.db` adı her yeni sürümde kaynak kod değişikliği ister. Öneri: sabit ad `assets/db/core.db` ve yanında `assets/db/core.json` (`version`, `sha256`); ikisini `fetch-core.mjs` yazar ve ikisi de git dışıdır. `app.config.ts` `core.json`'u okuyup `extra.embeddedCore` alanına yazar. `core.db` paketleme anında çözüldüğü için dosya yokken Metro paketleyemez: `pnpm dev:mobile` ve yerel derlemeden önce `fetch-core.mjs` çalışır (EAS'te kanca çalıştırır). `.db` Metro varlık listesine eklenir. İçe aktarım `Paths.document/mutalaa/packs/` altına yapılır ve cihazdaki kopya sürümlü adı alır (`core-<sürüm>.db`, sürüm `extra.embeddedCore`'dan); böylece Mobil mimari §6.2'deki gerekçe (yeni sürüm yeni ad, eski kopyanın üzerine yazılmaz) korunur. `installed_pack` satırı `source = embedded` ile yazılır; indirilmiş `core` daha yeniyse o kalır.
- Açılış uzlaştırmasının kuyruktan bağımsız maddeleri burada yazılır (Depolama yöneticisi §3, madde 1, 2 ve 6): dosyası olmayan `installed_pack` satırı `broken` (`missing_file`) olur, kaydı olmayan sürüm klasörü silinir, gömülü `core` sürümü değiştiyse içe aktarılır. Kuyruk ve sesle ilgili 3, 4, 5 ve 7. maddeler A29'dadır.
- `validatePack()` İçerik paketleri §8 adım 5'i uygular: `PRAGMA user_version` `[PACK_SCHEMA_MIN, PACK_SCHEMA_MAX]` içinde; `pack_meta` içindeki `pack_id`, `version`, `flavor` ve `normalizer_version` (`major.minor`) beklenen değerde; `pack_source` derleme türüne uygun (`isPackVisible`, A23.4); `PRAGMA quick_check`; paket türüne göre koşullu: `unit` taşıyan türlerde (`core`, `tefsir-elmalili`, `hadis-*`, `risale-{kitap}`) `unit` sayısı `unit_count` ile aynı, `unit_fts` taşıyan türlerde (`core`, `tefsir-elmalili`, `hadis-*`, `risale-dizin`) bir FTS sorgusu hatasız (tür tabloları `sql/paketler.json`'dadır; öteki türlerde bu iki denetim atlanır); `min_app_version` uygulamadan büyükse paket açılmaz.
- `src/lib/errors.ts`: `AppError` birleşim tipi (Mobil mimari §11; görünmeyen paket için `not_visible`, imza ve biçim hatası için `manifest_invalid`). `src/lib/network.ts` A23.1 seçimiyle yazılır; TanStack Query `onlineManager` buna bağlanır.
- **Bitti sayılır:** `ContentDb` testleri (dokuzuncu pakette en eski ayrılır, yol değişince yeniden bağlanır, takma ad temizlenir) ve her başarısızlık nedeni için birer `validatePack` testi yeşil.

### A23.4 · Manifest istemcisi, imza ve görünürlük
- `src/packs/manifest.ts`: `{flavor}/manifest.json` `ETag` ile istenir; biçim `packages/content-schema/manifest.schema.json` ile doğrulanır (`zod`, Tedarik); son geçerli kopya MMKV'de; sorgu anahtarı `qk.manifest(flavor)`.
- İmza: `signature` alanı (`{alg, kid, value}`) çıkarılmış manifestin kanonik JSON'u (RFC 8785, `canonicalize`), derleme türünün gömülü açık anahtarıyla doğrulanır (`@noble/ed25519`; `ed.hashes.sha512` ve `sha512Async` `@noble/hashes` ile atanır); anahtar `kid` ile seçilir. Açık anahtarlar `src/packs/keys.ts`'tedir; değerler bir JSON dosyasından okunur ki `fetch-core.mjs` de kullanabilsin (öneri). İmzasız ya da tutmayan manifest `manifest_invalid` (`imzasiz`, `imza_gecersiz`, `bicim`) hatasıdır; uygulama son geçerli manifestle ve yüklü paketlerle sürer (K-21, İçerik paketleri §5).
- `src/packs/visibility.ts`: `isPackVisible({ flavor, source_ids }, flavor)` Mobil mimari §10'daki gibidir: paketin `pack_meta.flavor` değeri uygulamanın derleme türüyle aynı olmalıdır; `dev` hepsini açar; `internal` yalnız `test-kucuk` ve `test-ses` kaynaklarını açar, başka `test-` önekli kaynak taşıyan paketi açmaz; `public` hiçbir `test-` önekli kaynağı açmaz (P-12). Manifest paket satırı kaynak bilgisi taşımadığı için girdi, indirilen ya da cihazdaki paket dosyasının `pack_meta` ve `pack_source` tablolarından okunur (Yayın süreci §4.3). Birimin onay durumu paket üretilirken Yayınlayıcı'da uygulanır (P-08, P-10).
- A21'deki bayrak işlevinin `'paket'` kuralı artık `isPackVisible` ve manifestle çalışır.
- **Bitti sayılır:** görünürlük matrisi testi (derleme türü eşleşmesi × `test-` önekli kaynak: `dev` hepsi; `internal` yalnız `test-kucuk` ve `test-ses`; `public` hiçbiri) Mobil mimari §10 ile aynı; imza testleri (geçerli, imzasız, değiştirilmiş, bilinmeyen `kid`) yeşil; A13'ün `packages/content-schema/test/fixtures/` altına bıraktığı imzalı örnek manifest ve yerel `dev` manifesti uygulama doğrulayıcısından geçer; A13'ün `fixtures/jcs/` altına kopyaladığı altı RFC 8785 çifti `canonicalize` ile bayt bayt aynı çıkar.

### A23.5 · `scripts/fetch-core.mjs` ve EAS kancası
- Betik `MANIFEST_URL`'den manifesti okur, imzayı derleme türünün açık anahtarıyla doğrular, manifestin `flavor` alanını derleme türüyle (`APP_FLAVOR`) karşılaştırır, `core` girişini bulur, BÇ-25'teki adın `.part` ekli biçimine indirir (öneri `assets/db/core.db.part`), boyut ve sha256'yı doğrular, dosyayı yeniden adlandırarak öncekinin yerine koyar ve `core.json`'u yazar. `flavor` derleme türüne uymuyorsa (ör. `production` derlemesinde `internal` manifesti) indirmeden durur. Her hatada sıfırdan farklı kodla çıkar.
- Sınama için manifest yerel dosyadan da okunabilir: `MANIFEST_FILE` ortam değişkeni (öneri). Betik göreli yolları depo köküne göre çözer (kök: `pnpm-workspace.yaml` dosyasının olduğu klasör; öneri), çünkü `pnpm --filter … exec` çalışma dizinini `apps/mobile` yapar; komutlara mutlak yol verilmez. İmza, biçim denetiminden önce doğrulanır (öneri); böylece değiştirilmiş kopya imza hatasıyla durur.
- `apps/mobile/package.json` içindeki `eas-build-post-install` betiği bunu çağırır (Proje yapısı §7). `development` profilinde EAS bulutu yerel ağdaki SeaweedFS'e ulaşamaz; betik bu profilde (`eas.json` `env` içindeki `APP_FLAVOR=dev`) indirmeyi atlar ve geliştirme derlemesinde `core` Metro üzerinden yerel `assets/db/` klasöründen gelir (BÇ-11). Bu yol A23.1'deki doğrulamaya bağlıdır ve `/karar` ile yazılır.
- `apps/mobile/assets/db/*.db` ve `apps/mobile/assets/db/core.json` kökteki `.gitignore`'a eklenir (A02 kuralı: yalnız ekleme; BÇ-25 başka ad seçerse o ad).
- **Bitti sayılır:** yerel `dev` manifestiyle betik 0 koduyla biter ve dosyanın sha256'sı manifesttekine eşittir; imzası bozulmuş kopyada ve `flavor` değeri derleme türüne uymayan manifestte (`APP_FLAVOR=public` ile `dev` manifesti) sıfırdan farklı kodla durur.

### A23.6 · Göç fikstürü testleri ve cihaz denetimi
- `user.db` ve `device.db` için ilk şema sürümünden fikstür veritabanı üretilir (`apps/mobile/test/fixtures/`); satırlar sentetiktir ("Deneme notu 1"). Test bütün göçleri Node'da bu fikstüre uygular, satır sayısının ve değerlerin korunduğunu doğrular (Test stratejisi §6). Her yeni şema sürümü bir fikstür ekler.
- `test-yazari` testleri gözden geçirir. `inceleyici` `isPackVisible`, `pack_source` denetimi ve `fetch-core.mjs`'nin `flavor` kuralını Mobil mimari §10 ve Yayın süreci §4.3 ile karşılaştırır.
- Geliştirici menüsüne "Veri katmanı" satırı eklenir (öneri): `core` sürümü, uygulanan göçler, bağlı şema sayısı, son manifestin imza durumu. Cihaz denemesi ve ekran görüntüsü kullanıcıya bırakılır (CLAUDE.md, çalışma düzeni 3); `expo-network` ve `expo-crypto` yeni yerel modül olduğundan önce kullanıcı onayıyla yeni EAS geliştirme derlemesi alınır (ücretli iş: tahmini maliyet söylenir).
- **Bitti sayılır:** göç testleri yeşil; Veri katmanı satırı kodda ve birim testinde hazır; cihazdaki `core` sürümü ve imza durumunun gözle denetimi ilerleme notunda "kullanıcıya bırakıldı".

## Kabul ölçütleri
- [ ] A23.0: Tedarik tablosundaki adresler açılıyor; kitaplık sürümleri `pnpm-lock.yaml` içinde sabit ve tablodakiyle aynı.
- [ ] `pnpm --filter @mutalaa/content-schema test` ve `pnpm --filter @mutalaa/reader-core test` yeşil (ortak sütunlar, HLC).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: `ContentDb`, `validatePack`, görünürlük matrisi, imza, göç fikstürü.
- [ ] `ContentDb` en çok 8 şema bağlar; dokuzuncu pakette LRU'daki en eski ayrılır (test).
- [ ] `isPackVisible`: derleme türü uymayan paket hiçbir derlemede açılmaz; `dev` hepsini açar; `internal` yalnız `test-kucuk` ve `test-ses` kaynaklarını açar; `public` hiçbir `test-` önekli kaynağı açmaz (test).
- [ ] Uzlaştırma testleri (dosyası olmayan kayıt `broken`, kayıtsız sürüm klasörü silinir, yeni gömülü `core` içe aktarılır) yeşil.
- [ ] İmzasız ya da değiştirilmiş manifest reddedilir ve son geçerli manifest kalır (test).
- [ ] `fetch-core.mjs` yerel manifestle 0, bozuk imzalı kopyayla ve derleme türüne uymayan `flavor` ile sıfırdan farklı kodla çıkar; indirilen dosyanın sha256'sı manifesttekiyle aynı (gözle karşılaştırma).
- [ ] `git check-ignore` `apps/mobile/assets/db/` altındaki `.db` dosyalarını git dışı gösterir.
- [ ] A23.1'deki ölçümler (ATTACH sınırı, `query_only` ile ATTACH) dokümana; imza kitaplığı, `development` profilindeki `core` yolu ve gömülü `core` dosyasının adı (BÇ-25) karar defterine işlendi.
- [ ] `inceleyici` raporunda engelleyici bulgu yok; Geliştirici › Veri katmanı satırı kodda ve birim testinde hazır; cihaz denemeleri (ATTACH sayısı, `query_only` ile ATTACH, şema nitelemeli `MATCH`, ekran görüntüsü) ilerleme notunda "kullanıcıya bırakıldı".

## Doğrulama
```bash
curl -sIL --max-time 30 https://docs.expo.dev/versions/v58.0.0/sdk/sqlite/ | head -1
git ls-remote https://github.com/paulmillr/noble-ed25519.git 'refs/tags/3.2.0'
git ls-remote https://github.com/erdtman/canonicalize.git 'refs/tags/v5.1.0'
pnpm --filter @mutalaa/mobile list expo-sqlite expo-file-system expo-network expo-crypto drizzle-orm zod @noble/ed25519 @noble/hashes canonicalize uuid
pnpm --filter @mutalaa/content-schema test
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
mkdir -p .tmp/a23
curl -s http://localhost:8333/mutalaa/dev/manifest.json > .tmp/a23/dev-manifest.json
MANIFEST_URL=http://localhost:8333/mutalaa/dev/manifest.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs; echo "çıkış: $?"
sha256sum apps/mobile/assets/db/core*.db
grep -oE '"sha256": *"[0-9a-f]{64}"' .tmp/a23/dev-manifest.json
sed -E 's/("release": *")/\1x/' .tmp/a23/dev-manifest.json > .tmp/a23/manifest-bozuk.json
MANIFEST_FILE=.tmp/a23/manifest-bozuk.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs; echo "çıkış (sıfırdan farklı olmalı): $?"
APP_FLAVOR=public MANIFEST_FILE=.tmp/a23/dev-manifest.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs; echo "çıkış (sıfırdan farklı olmalı): $?"
git check-ignore -v apps/mobile/assets/db/core.db apps/mobile/assets/db/core.json
```
Cihaz denemesi kullanıcıya bırakılır; geliştirme derlemesi açıkken kullanıcı şunları çalıştırabilir:
```bash
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/gelistirici"
adb exec-out screencap -p > .tmp/a23/veri-katmani.png
```
PowerShell karşılığı: `$env:MANIFEST_URL = "http://localhost:8333/mutalaa/dev/manifest.json"; pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs`. Önce yerel yığın çalışır olmalıdır: `docker compose up -d` ve `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev`.

## Dikkat
- İçerik bağlantısı salt okunurdur. Kanonik metin cihazda dönüştürülmez; `content_hash` yeniden hesaplanmaz, paketten okunur (Çapa şeması §7). Ayrıntı: `metin-butunlugu`.
- Kalıcı başvuru yalnız çapayla yapılır; `rowid` paket sürümü değişince değişebilir (İçerik paketleri §3.2).
- ATTACH takma adı SQL'e bağlanamaz; yalnız temizlenmiş paket kimliğinden üretilir. Dosya yolu her zaman parametredir.
- İmza kuralı gevşetilmez: imzasız manifest `dev` dahil hiçbir derlemede okunmaz (K-21; İçerik paketleri §5, Yayın süreci §4.2).
- Görünürlük kuralı: `test-` önekli kaynak taşıyan paket `public`'te açılmaz; `internal`'da yalnız `test-kucuk` ve `test-ses` açılır (P-12). Onaysız birim süzmesi paket üretilirken Yayınlayıcı'da yapılır (P-08, P-10). Ayrıntı: `paket-yayini`.
- Kitaplık sürümleri tam sürümle sabittir; Expo paketleri yalnız `expo install` ile eklenir (SDK uyumu). Yeni yerel modül (`expo-network`, `expo-crypto`) yeni geliştirme derlemesi ister; EAS derlemesi ücretli iştir (tahmini maliyet söylenir, kullanıcı onayı alınır).
- Gizli değer yoktur: depoya yalnız açık anahtarlar girer; özel anahtar kullanıcı sırlarındadır (A13). `.env.local` okunmaz.
- Fikstürlerde yalnız sentetik metin ("Deneme notu 1") kullanılır.
- Windows: `sha256sum` Git Bash'tedir, PowerShell'de `Get-FileHash`. Yayınlayıcı dosyayı taşımadan önce bağlantıyı kapatır; uygulama tarafında da açık dosya taşınmaz (`windows-sorun`).
- Commit kapsamları `mobile`, `content-schema`, `reader-core`.

## İnsan adımları
- Yok. Yerel yığının (`docker compose up -d`) ve A13'ün `dev` anahtarıyla imzalanmış manifestin hazır olması önkoşuldur. Cihaz denemeleri kullanıcıya bırakılır ve aşamayı bekletmez. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/content-schema/src/user/` (Drizzle şeması, `columns.ts`), testler
- `packages/reader-core/` iskeleti: SQL yürütücü arayüzü, `src/sync/hlc.ts`, testler
- `apps/mobile/src/db/`: `paths.ts`, `user.ts`, `device.ts`, `device/schema.ts`, `content.ts`, `packs.ts`, `migrations/`, `DbGate`
- `apps/mobile/src/packs/`: `manifest.ts`, `keys.ts` ve anahtar JSON'u, `visibility.ts`, `validate.ts`
- `apps/mobile/src/lib/errors.ts`, `network.ts`; `apps/mobile/scripts/fetch-core.mjs`; `package.json` kancası; `metro.config.js` eki; `.gitignore` eki
- `apps/mobile/test/fixtures/` göç fikstürleri; karar defterinde imza kitaplığı, Node sürücüsü ve `development` `core` yolu
- `pnpm-lock.yaml` içinde sabitlenen kitaplık sürümleri; Tedarik tablosunda ölçüm sonuçları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A23-cihaz-veri-katmani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A22](./A22-tasarim-vitrini.md) · Sonraki: [A24](./A24-okuyucu-mushaf-c.md)
