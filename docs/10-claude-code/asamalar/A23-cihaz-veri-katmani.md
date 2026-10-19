# A23 · Cihaz veri katmanı: paketler, ATTACH, `user.db`, `device.db`, gömülü `core`

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A13](./A13-yayinlayici-ve-yayin-kapisi.md) · [A21](./A21-mobil-iskelet.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `lisans-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `paket-yayini` · `lisans-kapisi` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A23`

## Amaç
Cihazdaki üç veri katmanı kurulur: gömülü `core` ve ATTACH edilen metin paketlerinden oluşan salt okunur içerik bağlantısı, senkrona hazır `user.db` ve cihaza özgü `device.db`. Manifest istemcisi imzayı doğrular ve lisans kapısını ikinci kez uygular. `scripts/fetch-core.mjs` gömülü `core`'u imzalı manifestten alır ve özetini doğrular. Okuyucu, Defterim, Depolama ve ses bu katmanın üstüne kurulur.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §6 Veri erişimi, §10 (`isPackVisible`, manifest imzası), §11 Hata ve çevrimdışı davranış
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.1, §5 `manifest.json`, §6 Sürümleme, §7, §8 Cihazda yaşam döngüsü
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §1–§3
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §2 `device.db`, §3 dosya düzeni, §5 bütünlük
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/mobile`), §7 son paragraf (`fetch-core.mjs`)
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §6 adım 6–7, §10.3
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 · [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §4.3

## Kapsam
**Yapılır**
- `packages/content-schema`: `user.db` Drizzle şeması ve ortak senkron sütunları. `packages/reader-core` iskeleti: SQL yürütücü arayüzü ve HLC.
- `apps/mobile/src/db`: yollar, `user.db`, `device.db`, göçler, `ContentDb` (ATTACH, en çok 8 şema), mushaf ve ses paketleri için ayrı salt okunur bağlantılar, `DbGate`, açılış sırası, gömülü `core` içe aktarımı, `validatePack`.
- `apps/mobile/src/packs`: manifest istemcisi, imza doğrulama, açık anahtarlar, `isPackVisible`, `pack_source` denetimi.
- `src/lib/errors.ts` (`AppError`), `src/lib/network.ts`; `scripts/fetch-core.mjs` ve `eas-build-post-install`; göç fikstürü testleri.

**Yapılmaz**
- İndirme kuyruğu, uzlaştırmanın kuyruk ve sesle ilgili maddeleri, Depolama ekranı ve manifest güncelleme akışı: [A29](./A29-kutuphane-ve-depolama.md).
- Okuyucu sorguları ve sayfa modeli (A24); arama sorguları (A28); Defterim ekranları ve yedek (A30); senkron ve giden kutusu yazımı (A36).
- Yayınlayıcının imza ve paket kodu (A13'te). Değişiklik gerekirse `sunucu-gelistirici` ile ayrı iş açılır.

## Adımlar
### A23.1 · Doğrulamalar ve ölçümler
- `arastirmaci` seçilen SDK için resmî belgeden doğrular, sonuç `/belge-esitle` ile işlenir:
  - expo-sqlite: `openDatabaseAsync(ad, seçenekler, klasör)`, `enableChangeListener`, URI dosya adı (`mode=ro`, `immutable=1`) desteği; gömülü `core` için `SQLiteProvider` `assetSource` ile `expo-asset` kopyalaması arasındaki seçim (Mobil mimari §6.2).
  - Drizzle: `drizzle-orm/expo-sqlite`, `useMigrations`, `useLiveQuery`; `.sql` göçleri için Babel ve Metro ayarı; drizzle-kit ayarı.
  - expo-file-system: `Paths`, `File`, `Directory` adları ve `File.digest('SHA-256')` (DY-9).
  - Ağ durumu için `expo-network` ya da `@react-native-community/netinfo` (Mobil mimari §11); UUIDv7 üretimi ve güvenli rastgele sayı kaynağı (KV-4).
  - EAS derlemesinde profil adını veren ortam değişkeni; git dışı dosyaların EAS'e yüklenip yüklenmediği (A23.5 için).
  - Metro'nun sürümlü varlık adını sabit `require()` olmadan paketleyip paketleyemediği (`require.context`; BÇ-25'teki seçenek).
- İmza: A13'te Yayınlayıcının kullandığı algoritma, kanonik JSON yöntemi ve `kid` biçimi koddan ve karar defterinden okunur. Uygulama tarafı kitaplık (öneri `@noble/ed25519`, IP-7) buna göre seçilir. Node'da göç testi için SQLite sürücüsü seçilir (öneri: Windows'ta derleme istemeyen). İki seçim `/karar` ile yazılır.
- Cihazda ölçülecekler (`mobil-gelistirici`, geliştirme derlemesinde): `SQLITE_MAX_ATTACHED` değeri (MM-5, AR-6, IP-8), `PRAGMA query_only = ON` iken `ATTACH` (MM-6), şema nitelemeli FTS5 `MATCH`.
- **Bitti sayılır:** doğrulama ve ölçüm sonuçları dokümanda; imza kitaplığı ve Node sürücüsü karar defterinde.

### A23.2 · Şemalar, göçler ve HLC
- `packages/content-schema/src/user/`: `columns.ts` (`syncColumns`: `id`, `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id`) ve [Kullanıcı verisi](../../03-veri/04-kullanici-verisi-ve-senkron.md) §2'deki tablolar: `bookmark`, `highlight`, `note`, `reading_position`, `hatim`, `hatim_page`, `collection`, `setting`, `vocab` (v1.x tablosu, şema şimdiden), yalnız yerel `outbox` ve `sync_state`. Dizinler ve `CHECK` kısıtları DDL'deki gibidir.
- `apps/mobile/src/db/device/schema.ts`: Depolama yöneticisi §2'deki `installed_pack`, `download_job`, `audio_file`.
- Göçler drizzle-kit ile `apps/mobile/src/db/migrations/user/` ve `.../device/` altına üretilir; uygulanmış göç değiştirilmez.
- `packages/reader-core` açılır: içerik sorguları için SQL yürütücü arayüzü (platform kodu içeri verilir) ve `src/sync/hlc.ts` (`tick`, `recv`; biçim `{12 hane}-{4 hane}-{16 hane}` küçük harf onaltılık; son değer `sync_state.hlc_last`).
- Yazma yardımcısı: her kullanıcı yazımı tek işlemdir; satır UUIDv7 `id`, yeni `hlc`, `updated_at` ve `device_id` alır; `base_version` 0 kalır; v1'de `outbox` yazılmaz. `device_id` ilk açılışta UUIDv4 olarak üretilir ve `sync_state`'te durur (öneri).
- **Bitti sayılır:** `content-schema` testi her senkron tablosunda altı ortak sütunu bulur; HLC testleri (tekdüzelik, saat geri alınınca küçülmeme, dizgi sırası = zaman sırası, düğüm kısmı `device_id`'den) yeşil.

### A23.3 · Bağlantılar, açılış sırası ve paket doğrulaması
- `src/db/paths.ts`: `Paths.document/mutalaa/db/`, `.../packs/`, `.../tmp/`. `src/db/user.ts` ve `src/db/device.ts`: WAL ve `foreign_keys`; `user.db` `enableChangeListener: true` ile.
- `src/db/content.ts`: `ContentDb` Mobil mimari §6.3'teki gibi: tek bağlantı, `PRAGMA query_only`, `MAX_ATTACHED = 8`, takma ad `p_` + `[a-z0-9_]`, dosya yolu her zaman parametre, `Mutex`, LRU ile ayırma, süren sorgu bitmeden `DETACH` yok. Şema yerleşimi İçerik paketleri §2 tablosuyla aynıdır.
- `src/db/packs.ts`: mushaf ve ses paketleri ATTACH edilmez; ayrı salt okunur bağlantılar, LRU (A26 ve A27 kullanır).
- `DbGate` (A21'deki yer tutucu) Mobil mimari §6.2 sırasını uygular: MMKV'den eşzamanlı tema, mod ve son konum; gömülü `core` içe aktarımı (ilk açılışta ya da yeni gömülü sürümde); `user.db` ve `device.db` göçleri; içerik bağlantısı. Göçler bitmeden ekran çizilmez.
- Gömülü `core` dosyasının adı BÇ-25 kararıdır. Metro `require()` yalnız sabit yol kabul eder; belgelerdeki `assets/db/core-<sürüm>.db` adı her yeni sürümde kaynak kod değişikliği ister. Öneri: sabit ad `assets/db/core.db` ve yanında `assets/db/core.json` (`version`, `sha256`); ikisini `fetch-core.mjs` yazar ve ikisi de git dışıdır. `app.config.ts` `core.json`'u okuyup `extra.embeddedCore` alanına yazar. `core.db` paketleme anında çözüldüğü için dosya yokken Metro paketleyemez: `pnpm dev:mobile` ve yerel derlemeden önce `fetch-core.mjs` çalışır (EAS'te kanca çalıştırır). `.db` Metro varlık listesine eklenir. İçe aktarım `Paths.document/mutalaa/packs/` altına yapılır ve cihazdaki kopya sürümlü adı alır (`core-<sürüm>.db`, sürüm `extra.embeddedCore`'dan); böylece Mobil mimari §6.2'deki gerekçe (yeni sürüm yeni ad, eski kopyanın üzerine yazılmaz) korunur. `installed_pack` satırı `source = embedded` ile yazılır; indirilmiş `core` daha yeniyse o kalır.
- Açılış uzlaştırmasının kuyruktan bağımsız maddeleri burada yazılır (Depolama yöneticisi §3, madde 1, 2 ve 6): dosyası olmayan `installed_pack` satırı `broken` (`missing_file`) olur, kaydı olmayan sürüm klasörü silinir, gömülü `core` sürümü değiştiyse içe aktarılır. Kuyruk ve sesle ilgili 3, 4, 5 ve 7. maddeler A29'dadır.
- `validatePack()` İçerik paketleri §8 adım 5'i uygular: `PRAGMA user_version` `[PACK_SCHEMA_MIN, PACK_SCHEMA_MAX]` içinde; `pack_meta` içindeki `pack_id`, `version` ve `normalizer_version` (`major.minor`) beklenen değerde; `pack_source` derleme türüne uygun; `PRAGMA quick_check`; `unit` sayısı `unit_count` ile aynı; bir FTS sorgusu hatasız; `min_app_version` uygulamadan büyükse paket açılmaz.
- `src/lib/errors.ts`: `AppError` birleşim tipi (Mobil mimari §11). `src/lib/network.ts` A23.1 seçimiyle yazılır; TanStack Query `onlineManager` buna bağlanır.
- **Bitti sayılır:** `ContentDb` testleri (dokuzuncu pakette en eski ayrılır, yol değişince yeniden bağlanır, takma ad temizlenir) ve her başarısızlık nedeni için birer `validatePack` testi yeşil.

### A23.4 · Manifest istemcisi, imza ve görünürlük
- `src/packs/manifest.ts`: `{flavor}/manifest.json` `ETag` ile istenir; biçim `packages/content-schema/manifest.schema.json` ile doğrulanır (öneri `zod`); son geçerli kopya MMKV'de; sorgu anahtarı `qk.manifest(flavor)`.
- İmza: `signature` alanı çıkarılmış manifestin kanonik JSON'u, derleme türünün gömülü açık anahtarıyla doğrulanır; anahtar `kid` ile seçilir. Açık anahtarlar `src/packs/keys.ts`'tedir; değerler bir JSON dosyasından okunur ki `fetch-core.mjs` de kullanabilsin (öneri). İmzasız ya da tutmayan manifest `manifest_invalid` hatasıdır; uygulama son geçerli manifestle ve kurulu paketlerle sürer (K-06, İçerik paketleri §5).
- `src/packs/visibility.ts`: `isPackVisible` Mobil mimari §10'daki gibidir; `kurul_onay` nesne tipindedir. Kurulu paketin `pack_source` tablosu izin dışı durum gösterirse paket açılmaz (Yayın kapısı §4.3).
- A21'deki bayrak işlevinin `'paket'` kuralı artık `isPackVisible` ve manifestle çalışır.
- **Bitti sayılır:** görünürlük matrisi testi (4 durum × 3 derleme × `kurul_gerekli` × `kurul_onay`) Mobil mimari §10 ile aynı; imza testleri (geçerli, imzasız, değiştirilmiş, bilinmeyen `kid`) yeşil; A13'ün `packages/content-schema/test/fixtures/` altına bıraktığı imzalı örnek manifest ve yerel `dev` manifesti uygulama doğrulayıcısından geçer.

### A23.5 · `scripts/fetch-core.mjs` ve EAS kancası
- Betik `MANIFEST_URL`'den manifesti okur, imzayı derleme türünün açık anahtarıyla doğrular, `core` girişini bulur, BÇ-25'teki adın `.part` ekli biçimine indirir (öneri `assets/db/core.db.part`), boyut ve sha256'yı doğrular, dosyayı yeniden adlandırarak öncekinin yerine koyar ve `core.json`'u yazar. `production` profilinde `core` için `kurul_onay` boşsa durur (Kapsam ve fazlar B-05, B-06). Her hatada sıfırdan farklı kodla çıkar.
- Sınama için manifest yerel dosyadan da okunabilir: `MANIFEST_FILE` ortam değişkeni (öneri). Betik göreli yolları depo köküne göre çözer (kök: `pnpm-workspace.yaml` dosyasının olduğu klasör; öneri), çünkü `pnpm --filter … exec` çalışma dizinini `apps/mobile` yapar; komutlara mutlak yol verilmez. İmza, biçim denetiminden önce doğrulanır (öneri); böylece değiştirilmiş kopya imza hatasıyla durur.
- `apps/mobile/package.json` içindeki `eas-build-post-install` betiği bunu çağırır (Proje yapısı §7). `development` profilinde EAS bulutu yerel ağdaki SeaweedFS'e ulaşamaz; betik bu profilde indirmeyi atlar ve geliştirme derlemesinde `core` Metro üzerinden yerel `assets/db/` klasöründen gelir. Bu yol A23.1'deki doğrulamaya bağlıdır ve `/karar` ile yazılır.
- `apps/mobile/assets/db/*.db` ve `apps/mobile/assets/db/core.json` kökteki `.gitignore`'a eklenir (A02 kuralı: yalnız ekleme; BÇ-25 başka ad seçerse o ad).
- **Bitti sayılır:** yerel `dev` manifestiyle betik 0 koduyla biter ve dosyanın sha256'sı manifesttekine eşittir; imzası bozulmuş kopyada sıfırdan farklı kodla durur.

### A23.6 · Göç fikstürü testleri ve cihaz denetimi
- `user.db` ve `device.db` için ilk şema sürümünden fikstür veritabanı üretilir (`apps/mobile/test/fixtures/`); satırlar sentetiktir ("Deneme notu 1"). Test bütün göçleri Node'da bu fikstüre uygular, satır sayısının ve değerlerin korunduğunu doğrular (Test stratejisi §6). Her yeni şema sürümü bir fikstür ekler.
- `test-yazari` testleri gözden geçirir. `lisans-denetcisi` `isPackVisible`, `pack_source` denetimi ve `fetch-core.mjs`'nin `production` kuralını `lisans-kapisi` becerisiyle karşılaştırır.
- Geliştirici menüsüne "Veri katmanı" satırı eklenir (öneri): `core` sürümü, uygulanan göçler, bağlı şema sayısı, son manifestin imza durumu. Geliştirme derlemesinde `mobil-ekran` ile görüntüsü alınır; yeni yerel modül eklendiyse önce kullanıcı onayıyla yeni EAS derlemesi.
- **Bitti sayılır:** göç testleri yeşil; cihaz görüntüsünde `core` sürümü `dev` manifestindekiyle aynı ve imza "geçerli".

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/content-schema test` ve `pnpm --filter @mutalaa/reader-core test` yeşil (ortak sütunlar, HLC).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: `ContentDb`, `validatePack`, görünürlük matrisi, imza, göç fikstürü.
- [ ] `ContentDb` en çok 8 şema bağlar; dokuzuncu pakette LRU'daki en eski ayrılır (test).
- [ ] `isPackVisible`: `kapali` hiçbir derlemede; `bekliyor` ve `ic_kullanim` yalnız `dev`; `public`'te (ve karar aksini söylemedikçe `internal`'da) `kurul_gerekli` olup `kurul_onay` boş olan gizli (test).
- [ ] Uzlaştırma testleri (dosyası olmayan kayıt `broken`, kayıtsız sürüm klasörü silinir, yeni gömülü `core` içe aktarılır) yeşil.
- [ ] İmzasız ya da değiştirilmiş manifest reddedilir ve son geçerli manifest kalır (test).
- [ ] `fetch-core.mjs` yerel manifestle 0, bozuk imzalı kopyayla sıfırdan farklı kodla çıkar; indirilen dosyanın sha256'sı manifesttekiyle aynı (gözle karşılaştırma).
- [ ] `git check-ignore` `apps/mobile/assets/db/` altındaki `.db` dosyalarını git dışı gösterir.
- [ ] A23.1'deki ölçümler (ATTACH sınırı, `query_only` ile ATTACH) dokümana; imza kitaplığı, `development` profilindeki `core` yolu ve gömülü `core` dosyasının adı (BÇ-25) karar defterine işlendi.
- [ ] Geliştirici › Veri katmanı görüntüsü `.tmp/a23/` altında; `lisans-denetcisi` raporunda engelleyici bulgu yok.

## Doğrulama
```bash
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
git check-ignore -v apps/mobile/assets/db/core.db apps/mobile/assets/db/core.json
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/gelistirici"
adb exec-out screencap -p > .tmp/a23/veri-katmani.png
```
PowerShell karşılığı: `$env:MANIFEST_URL = "http://localhost:8333/mutalaa/dev/manifest.json"; pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs`. Önce yerel yığın çalışır olmalıdır: `docker compose up -d` ve `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev`.

## Dikkat
- İçerik bağlantısı salt okunurdur. Kanonik metin cihazda dönüştürülmez; `content_hash` yeniden hesaplanmaz, paketten okunur (Çapa şeması §7). Ayrıntı: `metin-butunlugu`.
- Kalıcı başvuru yalnız çapayla yapılır; `rowid` paket sürümü değişince değişebilir (İçerik paketleri §3.2).
- ATTACH takma adı SQL'e bağlanamaz; yalnız temizlenmiş paket kimliğinden üretilir. Dosya yolu her zaman parametredir.
- İmza kuralı gevşetilmez: imzasız manifest `dev` dahil hiçbir derlemede okunmaz (K-06; İçerik paketleri §5, Yayın kapısı §4.2).
- `bekliyor` ve `ic_kullanim` paketler yalnız `dev`'de görünür; `test-` kaynaklar `public`'e girmez. Ayrıntı: `lisans-kapisi`.
- `internal` derlemede `kurul_gerekli` olup `kurul_onay` taşımayan paket, Kurul'un kapalı test cevabı (İ-02) gelene kadar gizlenir (Mobil mimari §10, İçerik paketleri §8 madde 3, Yayın kapısı §3 ve §4.3); Yayınlayıcı kapısında P-04 yalnız `public`'tedir. Cevap gelene kadar dış test kullanıcısı zaten alınmaz (K-06).
- Gizli değer yoktur: depoya yalnız açık anahtarlar girer; özel anahtar kullanıcı sırlarındadır (A13). `.env.local` okunmaz.
- Fikstürlerde yalnız sentetik metin ("Deneme notu 1") kullanılır.
- Windows: `sha256sum` Git Bash'tedir, PowerShell'de `Get-FileHash`. Yayınlayıcı dosyayı taşımadan önce bağlantıyı kapatır; uygulama tarafında da açık dosya taşınmaz (`windows-sorun`).
- Commit kapsamları `mobile`, `content-schema`, `reader-core`.

## İnsan adımları
- Yok. Yerel yığının (`docker compose up -d`) ve A13'ün `dev` anahtarıyla imzalanmış manifestin hazır olması önkoşuldur. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/content-schema/src/user/` (Drizzle şeması, `columns.ts`), testler
- `packages/reader-core/` iskeleti: SQL yürütücü arayüzü, `src/sync/hlc.ts`, testler
- `apps/mobile/src/db/`: `paths.ts`, `user.ts`, `device.ts`, `device/schema.ts`, `content.ts`, `packs.ts`, `migrations/`, `DbGate`
- `apps/mobile/src/packs/`: `manifest.ts`, `keys.ts` ve anahtar JSON'u, `visibility.ts`, `validate.ts`
- `apps/mobile/src/lib/errors.ts`, `network.ts`; `apps/mobile/scripts/fetch-core.mjs`; `package.json` kancası; `metro.config.js` eki; `.gitignore` eki
- `apps/mobile/test/fixtures/` göç fikstürleri; karar defterinde imza kitaplığı, Node sürücüsü ve `development` `core` yolu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A23-cihaz-veri-katmani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A22](./A22-tasarim-vitrini.md) · Sonraki: [A24](./A24-okuyucu-mushaf-c.md)
