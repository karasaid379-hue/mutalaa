# A12 · Arama indeksi ve paket şeması

> **Sürüm:** 1.3 · **Tarih:** 9 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-44](../../00-ozet/02-karar-defteri.md#k-44--arama-indeksi-ve-paket-şeması-cihaz-gövdeleyicisi-simple-clean-paket-tabloları) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A10](./A10-tanzil-alimi.md) · **İnsan adımı:** —
> **Ajanlar:** `web-gelistirici` (TS paketleri) · `sunucu-gelistirici` · `hat-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `test-vektoru` · `paket-yayini` · `metin-butunlugu` · **Tahmini oturum:** 3
> **Başlat:** `/asama A12`

## Amaç
Cihazdaki SQLite paketlerinin tek şeması (`packages/content-schema/sql/`), FTS5 arama tabloları, manifest şeması ve `packages/search` içindeki FTS5 sorgu kurucusu yazılır. Sorgu kurucusu ortak vektörlerle (`fts-query/query.jsonl`) ve Node'da çalışan bir SQLite deneme düzeneğinde gerçek FTS5 tablolarına karşı sınanır. A13 bu DDL ile paket yazar; A23 ve A28 aynı şemayla okur.

## Okunacak belgeler
- [Arama](../../03-veri/05-arama-fts5.md): §1.4 Kur'an birimleri, §2 FTS5 tabloları, §3 sorgu ayrıştırma, §4 sıralama, §5 ATTACH, §6 performans (ölçüm kümesi A28'de)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3 paket içi şema, §4 bağlantıların dağılımı, §5 manifest, §6 sürümleme
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`content-schema`, `search`, `shared/test-vectors`), §1.2 vektör biçimi, §2 bağımlılık kuralları
- [Backend API](../../02-mimari/05-backend-api.md): §10.4 paket yazımı, §10.5 özet, imza ve depo düzeni
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 ortak vektörler, §6 enum tutarlılığı
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.3 Yayınlayıcı kitaplıkları

## Kapsam
**Yapılır**
- Bütün paket türlerinin DDL'i: ortak tablolar, metin paketleri, arama tabloları (içerikli ve içeriksiz), `core` ekleri, `kelime-kok`, `risale-dizin`, `risale-{kitap}`, `mushaf-a-cuz-*`, `mushaf-b`, `ses-*`; paket yazımından sonra çalışan FTS komutları.
- `packages/content-schema/manifest.schema.json` ve şema testleri.
- `packages/search` FTS5 sorgu kurucusu ve `shared/test-vectors/fts-query/query.jsonl`.
- Node tarafında SQLite FTS5 deneme düzeneği; C# tarafında DDL duman testi.
- Tedarik doğrulaması (A12.0): kitaplık sürümlerinin ve SQLite özelliklerinin (FTS5, `trigram`) ölçümü; Türkçe gövdeleyicinin TypeScript yarısı için hazır adayın sınanması.
- `packages/search` içinde cihaz gövdeleyicisi `stemTr` (`snowball-stemmers-js` 3.1.2) ve `normalize/tr-govde.jsonl` vektörleri ([K-44](../../00-ozet/02-karar-defteri.md#k-44--arama-indeksi-ve-paket-şeması-cihaz-gövdeleyicisi-simple-clean-paket-tabloları) madde 1).
- A10.3'ten devreden Simple Clean sorusu K-44 madde 2 ile kapandı: pakette tutulmaz; `core` paketinin `pack_source` ve `attribution` satırlarına kaynak olarak yazılması A13'tedir.

**Yapılmaz**
- Paket yazıcısı, imza ve yükleme (A13). Drizzle şemaları (`user.db`, `device.db`) ve cihazda ATTACH yönetimi (A23).
- Arama ekranı, kıyas ekranı ve ölçüm sorgu kümesi (A28). Normalleştirici (A05) ve Python gövdeleyicisi (A05). Sonuç parçası üretimi (`reader-core`, A28). Gövdeleyicinin Hermes'te yüklenmesi (A28).

## Tedarik
Bu aşama dışarıdan metin ya da veri almaz; kitaplık ve araç alır. Sürümler npm ve NuGet kayıtlarından, SQLite özellikleri yerel ölçümden ve paket arşivlerinin incelenmesinden okundu (2 Kasım 2026). A12.0, tablodaki ölçümleri CI'daki sürümlerle yineler.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Node'da FTS5 ve `trigram` ile deneme düzeneği (A12.5) | `node:sqlite`, Node.js yerleşik modülü ([API belgesi](https://nodejs.org/docs/latest-v24.x/api/sqlite.html), kararlılık 1.2 "sürüm adayı"); ölçülen sürüm Node 24.21.0 ve SQLite 3.53.4; biçim `DatabaseSync` | Yerleşik; indirme yok. Node sürümü `.nvmrc` (24) ile CI'da `setup-node` tarafından sabitlenir | `PRAGMA compile_options` içinde `ENABLE_FTS5`; `tokenize='trigram'`, `unicode61 remove_diacritics 0`, `content=''`, `contentless_delete=1`, `detail=none`, `detail=column` ve `prefix='2 3 4'` hatasız kuruldu; trigram alt dize araması (`cde` → 1 satır), önek araması ve bm25 sıralaması çalıştı. A12.0'da (9 Kasım 2026) yinelendi: Node 24.21.0 ve SQLite 3.53.4'te `ENABLE_FTS5` var, `contentless_delete=1`, `detail=none` ve `prefix='2 3 4'` kuruldu; Vitest 5.0.5 altında `node:sqlite` yüklendi. CI'daki Node sürümünde yinelenir | `better-sqlite3` 13.0.3 ([npm](https://www.npmjs.com/package/better-sqlite3), 5 Ağustos 2026; Node >=22; yerel eklenti, derleme bayrakları arasında `SQLITE_ENABLE_FTS5`; GitHub `WiseLibs/better-sqlite3` etiket v13.0.3, etiket nesnesi 0747dc94fb468715974716c6c54106ad6469d31b, etiketin gösterdiği commit dbc2ea1165fef1f599b9be12faea33fa5e9d7ffb (npm `gitHead` ile aynı); arşiv 11.402.131 bayt) |
| Paket yazımı ve DDL duman testi (A12.6) | `Microsoft.Data.Sqlite` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.Data.Sqlite/10.0.14), 25 Ekim 2026); bağımlılıkları `Microsoft.Data.Sqlite.Core` 10.0.14 ve `SQLitePCLRaw.bundle_e_sqlite3` 2.1.13 (yerel SQLite: [`SQLitePCLRaw.lib.e_sqlite3`](https://www.nuget.org/packages/SQLitePCLRaw.lib.e_sqlite3/2.1.13) 2.1.13, 18.762.900 bayt); biçim NuGet paketi | `dotnet add package` (sürüm `server/Directory.Packages.props` içinde) | Ölçüldü (`net10.0` deneme projesi): `sqlite_version()` 3.53.3; `compile_options` içinde `ENABLE_FTS5`; `trigram`, `contentless_delete=1`, `detail=none`, `detail=column` ve `prefix` tabloları hatasız kuruldu, trigram alt dize araması 1 satır döndü, `PRAGMA user_version = 1` okundu. `lib.e_sqlite3` arşivindeki 25 yerel dosyanın hepsinde `ENABLE_FTS5` ve `trigram` dizgisi var (`win-x64` `e_sqlite3.dll` 1.978.880 bayt). A12.6'da test projesinde yinelenir | `SQLitePCLRaw.bundle_e_sqlite3` 3.0.5 ([NuGet](https://www.nuget.org/packages/SQLitePCLRaw.bundle_e_sqlite3/3.0.5), 27 Temmuz 2026; SQLite 3.53.4 paketine bağlı) |
| Manifest şeması doğrulaması (C# testi, A12.3) | `JsonSchema.Net` 9.6.0 ([NuGet](https://www.nuget.org/packages/JsonSchema.Net/9.6.0), 31 Ekim 2026; GitHub `gregsdennis/json-everything`; [belge](https://docs.json-everything.net/schema/basics/)); bağımlılığı `JsonPointer.Net` 7.0.4; biçim NuGet paketi, `Evaluate(JsonElement)` | `dotnet add package` (yalnız test projesi) | Ölçüldü: `$schema` değeri draft-07, 2019-09 ve 2020-12 olan üç şema yüklendi; `pattern` ile küçük harfli 64 onaltılık karakter geçti, büyük harfli reddedildi. Taslak seçimi A12.1'dedir; beş şema testi (A12.3) geçince kanıtlanır | `LateApexEarlySpeed.Json.Schema` 4.2.2 ([NuGet](https://www.nuget.org/packages/LateApexEarlySpeed.Json.Schema/4.2.2), 16 Ekim 2026) |
| Cihazdaki SQLite özellikleri (yalnız doğrulama; kitaplık A21'de kurulur) | `expo-sqlite` 58.0.15 ([npm](https://www.npmjs.com/package/expo-sqlite), 31 Ekim 2026; Expo SDK 58, `expo` 58.0.22); [Expo SQLite belgesi](https://docs.expo.dev/versions/v58.0.0/sdk/sqlite/); biçim npm arşivi (10.769.785 bayt) | npm paket arşivi (`registry.npmjs.org/expo-sqlite/-/expo-sqlite-58.0.15.tgz`) `.tmp/` altında yeni bir klasöre indirilip incelenir; kurulum yok | Ölçüldü: arşivdeki `vendor/sqlite3/sqlite3.h` SQLite 3.53.3 (SQLCipher kolu da 3.53.3); `android/build.gradle` ve `ios/ExpoSQLite.podspec`, `expo.sqlite.enableFTS` değeri `false` olmadıkça `-DSQLITE_ENABLE_FTS5=1` ekler (varsayılan açık); `trigram` için SQLite 3.34 ve FTS5 yeter. Cihaz ölçümleri (`SQLITE_MAX_ATTACHED`, şema nitelemeli `MATCH`) A23.1'dedir | `@op-engineering/op-sqlite` 19.0.3 ([npm](https://www.npmjs.com/package/@op-engineering/op-sqlite), 29 Ekim 2026; yalnız gerçek veriyle ölçüm sorun gösterirse; [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §2) |
| Türkçe gövdeleyici, TypeScript yarısı (AR-2) | `snowball-stemmers-js` 3.1.2 ([npm](https://www.npmjs.com/package/snowball-stemmers-js), 13 Ağustos 2026; GitHub `QQSHI13/snowball-stemmers-js` etiket v3.1.2 @9a2044b462680f1a7df9b77b6cc087d7ad77fc1e); Snowball 3.1.1 derleyicisinin ürettiği saf JavaScript, bağımlılık yok; biçim ES modülü `lib/turkish-stemmer.js` (57.589 bayt; `new Stemmer().stemWord(kelime)`; arşiv 83.031 bayt, sha256 bf9f1b1b94f491ba42b4d021edce3bf705d348a6d4a7c9bd2fa4c58425d73951). Paketin `package.json` dosyasında `type` yok; `exports` alanı yok. Python yarısı `snowballstemmer` 3.1.1 (A05) | K-44 ile seçildi: `pnpm add` (tam sürüm sabit); `index.js` algoritma listesini `fs` ile okuduğu için cihaz kodu `lib/turkish-stemmer.js` dosyasını doğrudan içe aktarır | Ölçüldü: 161 kök ve 115 ekten üretilen 18.505 benzersiz sözcükte (`â î û` dar katlamasından sonra) Python `snowballstemmer` 3.1.1 çıktısıyla fark 0; A12.0'da (9 Kasım 2026) 13.044 sentetik sözcükte (60 kök × ek kombinasyonları) yine fark 0. `kuran` → `kura`, `mümin` → `müm`, `iman` → `ima`, `sabır` → `sabır`, `kitaplar` → `kitap` iki tarafta aynı. Dosya `fs`, ağ, süreç ve `eval` çağrısı taşımaz (tek `import` `base-stemmer.js`). ESM sözdizimi (`import`/`export default`, özel `#` alanları) olduğu için Node 24'te `MODULE_TYPELESS_PACKAGE_JSON` uyarısıyla ES modül olarak yeniden ayrıştırılır; Vitest 5.0.5 altında yüklenir. Metro/Hermes (özel alanlar için Babel dönüşümü) denemesi A28'dedir | `tr_stem_lex` tablosu (yalnız yedek; Yayınlayıcı doldurur, dönüş için yeni `/karar` gerekir) |

Kendimiz yapacağımız işler: paket DDL dosyaları, `manifest.schema.json`, FTS5 sorgu kurucusu ve `fts-query/query.jsonl` vektörleri (projeye özgü gramer; npm kaydında `fts5 query builder` araması bu grameri karşılayan paket vermedi, 2 Kasım 2026), Node düzeneği testleri ve C# duman testi.

## Adımlar
### A12.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: Node API belgesi, npm kaydı (`better-sqlite3`, `expo-sqlite`, `snowball-stemmers-js`), NuGet kaydı (`Microsoft.Data.Sqlite`, `SQLitePCLRaw.bundle_e_sqlite3`, `JsonSchema.Net`). Açılmayan adresin yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Kitaplıklarda sürüm paket kaydından doğrulanır: NuGet sürümleri `server/Directory.Packages.props` içinde, npm sürümleri `package.json` ve `pnpm-lock.yaml` içinde tam sürümle durur; kayıttaki sürüm tablodakiyle karşılaştırılır (`dotnet list server/Mutalaa.slnx package`, `pnpm list`).
- İncelenen arşivler (`expo-sqlite` npm paketi, `SQLitePCLRaw.lib.e_sqlite3` NuGet paketi, `snowball-stemmers-js`) yalnız okunur: `.tmp/` altında yeni ve boş bir klasöre iner, kurulum betikleri çalıştırılmaz, ölçüm betikleri ayrı klasörde durur. Gövdeleyici modülü, kaynağında `fs`, ağ ve süreç çağrısı olmadığı görüldükten sonra yalnız karşılaştırma betiğiyle yüklenir.
- Tablodaki ölçümler CI'daki sürümlerle yinelenir ve sayılarıyla rapora yazılır: Node'da `PRAGMA compile_options` (`ENABLE_FTS5`) ve `trigram` tablosu; `Microsoft.Data.Sqlite` ile aynı iki ölçüm ve `sqlite_version()`; `expo-sqlite` arşivindeki SQLite sürümü ve FTS5 bayrağı; gövdeleyici adayının Python çıktısıyla aynı sözcük listesindeki karşılaştırması.
- Bu aşama içerik kaynağı almaz: `data/gelen/` altına dosya inmez, `pipeline/sources/` altına kayıt yazılmaz. Test verisi kodla üretilen sentetik satırlardır.
- **Bitti sayılır:** tablodaki her adres açıldı; sürümler paket kaydıyla eşleşiyor; ölçülecek hücrelerin hepsi sayıyla dolu; sonuçlar A12.1 kararlarına girdi olarak raporlu.

### A12.1 · Doğrulamalar
- `arastirmaci`, A12.0 ölçümlerini resmî kaynaktan doğrular ve bağlantısıyla raporlar:
  - Node'da FTS5 ve `trigram` belirteçleyicisini destekleyen SQLite kitaplığı. Adaylar: Node'un yerleşik `node:sqlite` modülü (seçilen) ve `better-sqlite3` (yedek). Ölçütler: FTS5 ve `trigram` derlemede açık mı, Windows'ta yerel derleme ister mi, Node 24 uyumu, modülün kararlılık düzeyi.
  - expo-sqlite derlemesindeki SQLite sürümü ve `trigram` desteği; paket yalnız cihazdaki SQLite'ın desteklediği özellikleri kullanır ([Backend API](../../02-mimari/05-backend-api.md) §10.4).
  - `Microsoft.Data.Sqlite` (e_sqlite3) derlemesinde FTS5 ve `trigram`.
  - `JsonSchema.Net` sürüm durumu ve desteklediği JSON Schema taslağı.
- Gövdeleyici kararı (AR-2): A05'te Python gövdeleyicisi seçildi ve uygulandı (`snowballstemmer` 3.1.1, [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 6). TypeScript yarısı için `snowball-stemmers-js` 3.1.2 seçildi: 13.044 sentetik ve 18.505 sözcükte Python çıktısıyla fark 0. **Çözüldü (9 Kasım 2026, K-44 madde 1):** gövdeyi cihazda `stemTr` üretir, paketde `tr_stem_lex` tablosu yoktur ve Yayınlayıcı onu doldurmaz. Snowball'un agresif gövdelerinin (`kuran` → `kura`, `mümin` → `müm`, `iman` → `ima`) arama ölçümüyle gözden geçirilmesi kalır.
- Seçimler `/karar` ile yazılır. expo-sqlite `trigram` desteklemiyorsa durum kullanıcıya gösterilir; Arapça alt dize araması için seçenek karar olmadan uygulanmaz.
- **Bitti sayılır:** dört konu kaynak bağlantısıyla raporlu; kitaplık, JSON Schema taslağı, gövdeleyici ve Simple Clean kararları karar defterinde K-44 olarak yazılı (9 Kasım 2026).

### A12.2 · Paket DDL'i
- `packages/content-schema/sql/` altında paket türü başına dosyalar (K-44 sonrası liste): `00-ortak.sql` (`PRAGMA user_version = 1`, `pack_meta`, `pack_source`, `attribution`), `10-metin.sql` (`unit`), `11-xref.sql` (`xref_idx`), `12-tr-root.sql` (`tr_root_index`), `20-arama.sql` (`unit_search`, `unit_fts`, `unit_tri`; `tr_stem_lex` yok), `21-arama-iceriksiz.sql`, `29-arama-sonrasi.sql` (içerikli tablolarda `rebuild`, `rank`, `optimize`), `29-arama-sonrasi-iceriksiz.sql` (içeriksiz tablolarda yalnız `rank` ve `optimize`; `rebuild` yok), `30-core.sql` (`quran_word`, `quran_marker`, `sure`), `31-page-map.sql` (`page_map`), `40-kelime-kok.sql`, `50-risale-dizin.sql` (`unit_ref`), `60-mushaf-a.sql`, `61-mushaf-b.sql`, `70-ses-katalog.sql`, `71-ses-zaman.sql`. Paket türü → dosya listesi tek bir JSON'da durur: `sql/paketler.json`.
- Tablo ve sütun adları [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §3 ve [Arama](../../03-veri/05-arama-fts5.md) §2 ile birebir aynıdır; yeni ad uydurulmaz. K-44 madde 3: `tr_root_index` `core`'da yoktur, `kelime-kok`, `tefsir-elmalili`, `hadis-*` ve `risale-dizin` paketlerindedir; `risale-{kitap}` arama tabloları, `xref_idx` ve `tr_root_index` taşımaz, üçü `risale-dizin` içindedir.
- `kind`, `status` gibi değerler A06'nın `packages/content-schema/enums.json` dosyasıyla karşılaştırılır (Test stratejisi §6).
- A11 `quran_marker` tablosunu kurdu ([K-43](../../00-ozet/02-karar-defteri.md#k-43--kuran-yapı-verisi-kelime-numarası-işaret-tablosu-ve-aday-satırları) madde 2: `quran_marker(kind TEXT, no INTEGER, anchor TEXT, secde_turu TEXT, PRIMARY KEY (kind, no)) WITHOUT ROWID`, [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §3.2); tablo `30-core.sql` dosyasına eklenir.
- Simple Clean kararı (A10.3 devri) K-44 madde 2 ile verildi: pakette tutulmaz; yalnız normalize hâli `unit_search.ar_norm` içindedir. `21-arama-iceriksiz.sql`, `risale-dizin` için ve boyuta göre içeriksiz kurulabilecek metin paketleri için uygulanabilir yazılır ([Arama](../../03-veri/05-arama-fts5.md) §2: içeriksiz tablo arama metnini ikinci kez saklamaz; K-44 madde 4: içeriksiz tabloda `rebuild` çalışmaz).
- **Bitti sayılır:** her paket türünün dosya listesi Node düzeneğinde ve C# duman testinde hatasız kuruluyor; `PRAGMA user_version` 1 dönüyor.

### A12.3 · Manifest şeması
- `packages/content-schema/manifest.schema.json`, [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §5'i izler: üst düzeyde `manifest_version`, `flavor` (`dev`, `internal`, `public`), `release`, `generated_at`, `packs`, zorunlu `signature {alg, kid, value}`; paket başına zorunlu `pack_id`, `version`, `sha256`, `size_bytes`, `min_app_version`, `depends_on`, `url`; isteğe bağlı `schema_version`, `title`, `bundled`.
- Kurallar: `flavor` A06'nın `derleme_turu` enum değerleriyle (`dev`, `internal`, `public`) aynıdır; `signature` her derleme türünde zorunludur; `version` CalVer `YYYY.M.N`; `sha256` 64 küçük onaltılık karakter.
- Testler `JsonSchema.Net` ile Publisher test projesindedir: §5'teki örnek manifest geçer; imzasız manifest, bilinmeyen `flavor`, büyük harfli `sha256` ve CalVer'e uymayan `version` reddedilir. Uygulama tarafındaki doğrulayıcı (Teknoloji yığını §2.1'de `zod` önerisi) A23'te bu şemayla uyumlanır.
- **Bitti sayılır:** beş şema testi yeşil.

### A12.4 · FTS5 sorgu kurucusu ve vektörler
- `packages/search/src/` altında sorgu kurucusu (dosya adı öneri: `fts-query.ts`), [Arama](../../03-veri/05-arama-fts5.md) §3'ün gramerini ve dokuz kuralını uygular: adres algılama (sure adı çözücüsü dışarıdan verilir), yazı sistemi ayrımı, Türkçe terimde `tr_wide` ve `tr_stem` `OR`, düzeltme işaretli terimde dar süzgeç, en az 2 karakterlik önek (tek karakterli terim yok sayılır, önekte gövde yok), ifade (gövde yok), Arapça terim ve en az 3 karakterde `unit_tri` yedeği, `kök:` ve `kaynak:` süzgeçleri, her sözcüğün çift tırnakla kaçışı.
- Normalleştirme yalnız A05'in `packages/search` işlevleriyle yapılır. Gövde, terimin dar sözcüğünden `stemTr` ile üretilir (K-44 madde 1; `tr_stem_lex` araması yoktur; kurucu gövdeleyiciyi `stem` işlevi olarak alır); sure adı çözümü dışarıdan verilen işlevdir. Paket SQLite'a bağlanmaz ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §2 kural 2–3).
- Sorgu kurucusu 1.024 kod noktasından uzun girdiyi işlemez ve `tooLong` döner; sınır testle kilitlenir (K-44 madde 6, A05 devri).
- `shared/test-vectors/fts-query/query.jsonl` (`fq-` öneki): §3 tablosundaki yedi örnek (`sabır`, `ışığın nuru`, `kur*`, `"rahmet-i ilâhiye"`, `âlem`, `الصابرين`, `kök:صبر`) ve kenar durumları (FTS5 sözdizimi karakteri içeren girdi, tek karakter, 2 karakterlik önek, "Bakara 255", "2:255", 1.024 kod noktası sınırı). Vektörlerde gövde gerçek gövdeleyici çıktısı değildir: girdideki `stems` eşlemesinden gelen sabit yer tutucudur (`G1`, `G2`; eşleme anahtarı dar sözcük, ör. `"stems":{"sabır":"G1"}`). `{G}`, `{G1}`, `{G2}` gösterimi Arama §3 tablosunda `stemTr(dar sözcük)` anlamına gelir; gerçek `stemTr` çıktısı yalnız `normalize/tr-govde.jsonl` ve `packages/search/test/fts-query.test.ts` içindeki entegrasyon testlerindedir (ör. `ağaçları` → `agac`). Arapça örnek sorgular belgeden programla, bayt bayt alınır; elle yazılmaz (`test-vektoru`): `uv run mutalaa export test-vectors --fts-ornekleri`.
- `shared/test-vectors/normalize/tr-govde.jsonl` (`tg-` öneki): Türkçe gövde vektörleri. TypeScript ve Python koşar, C# atlar (gövdeleme yapmaz). İki gövdeleyici bu dosyayla kilitlenir; gövdeleyici sürümü değişirse normalleştirici küçük sürümü artar (K-36 madde 7).
- Biçim JSONL, UTF-8, BOM yok, LF, her satırda benzersiz `id` (`test-vektoru`). `fts-query/query.jsonl` dosyasını yalnız TypeScript koşar; Python ve C# vektör koşucuları `fts-query/` klasörünü açıkça atlar (`hat-gelistirici`, `sunucu-gelistirici`).
- **Bitti sayılır:** `pnpm --filter @mutalaa/search test` vektörlerle yeşil; `shared/test-vectors` `build` görevi biçimi doğruluyor; pytest ve xUnit vektör koşucuları yeşil (`tr-govde.jsonl` Python ve TypeScript'te koşar).

### A12.5 · Node SQLite deneme düzeneği
- Düzenek `packages/content-schema/test/` altındadır (öneri); `search` yaprak paket kaldığı için `content-schema` `@mutalaa/search` paketine geliştirme bağımlılığıyla bağlanır. SQLite kitaplığı A12.1'deki karardır. Geçici veritabanı dosyaları `.tmp/` altına yazılır.
- Veritabanı DDL dosyalarından kurulur. Sentetik Türkçe satırlar ("Deneme paragrafı 1 … ışık …") A05 normalleştiricisiyle `unit_search` tablosuna yazılır. Arapça satırlar `\u` kaçışıyla kurulan sentetik harf dizileridir (ör. bir dizi ve başına bitişik ek harfi U+0648 eklenmiş biçimi; bitişik ek ve trigram denemesi için); Kur'an kelimesi yazılmaz (`test-vektoru`).
- Sınananlar: her vektörün MATCH ifadesi FTS5'te hatasız çalışır; düzeneğin sentetik satırları için yazılmış vektörler beklenen çapaları döndürür (§3 tablosundaki Arapça örnek sorgular düzenekte yalnız hatasız çalışır, sonuç beklenmez); `ORDER BY rank` bm25 ağırlıklarıyla sıralar; 2–4 karakterlik önek; `trigram` alt dize araması; içeriksiz tablo ile `unit_ref` birleşimi; ayrı dosyadan `ATTACH` edilen pakette şema nitelemeli `MATCH` ve §5'teki `UNION ALL` deyimi (AR-6'nın Node tarafı; ölçüm sonuçları Arama §5'te: SQLite 3.53.4, 9 Kasım 2026; expo-sqlite tarafı A23.1 ve A28'de).
- **Bitti sayılır:** `pnpm --filter @mutalaa/content-schema test` yeşil.

### A12.6 · C# DDL duman testi ve hat uyumu
- `sunucu-gelistirici`: Publisher test projesinde her paket türünün DDL'i `Microsoft.Data.Sqlite` ile boş dosyaya uygulanır; `PRAGMA compile_options` `ENABLE_FTS5` içerir; `trigram` tablosu kurulur; `PRAGMA user_version` 1 döner.
- `hat-gelistirici`: hattın ürettiği `tr_wide`, `tr_stem`, `ar_norm` sütunlarının `unit_search` sütunlarıyla aynı adda olduğu doğrulanır. "`tr_wide` ile `tr_stem` aynı sayıda sözcük taşır" değişmez kuralı ([Arama](../../03-veri/05-arama-fts5.md) §1.2 madde 7) A05'te test edildi; bu aşamada hattın QA adımına da bağlanır, çünkü `unit_search.tr_stem` sütunu bu hizayı taşır (`tr_stem_lex` tablosu K-44 ile kalktı).
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` ve `uv --directory pipeline run pytest` yeşil.

## Kabul ölçütleri
- [ ] A12.0 tedarik raporu hazır: `## Tedarik` tablosundaki adresler açıldı, sürümler paket kaydıyla eşleşiyor, ölçümler CI sürümlerinde yinelendi.
- [ ] `packages/content-schema/sql/` İçerik paketleri §3 ve Arama §2'deki bütün tabloları taşıyor; `inceleyici` tablo ve sütun adlarının dokümanla birebir olduğunu karşılaştırma tablosuyla raporluyor.
- [ ] Her paket türünün DDL'i Node düzeneğinde ve C# duman testinde hatasız kuruluyor; `PRAGMA user_version` 1.
- [ ] `manifest.schema.json` §5 örneğini kabul ediyor, dört olumsuz örneği reddediyor (C# testi).
- [ ] `fts-query/query.jsonl` §3'teki yedi örneği ve en az beş kenar durumunu taşıyor; vektör testleri yeşil.
- [ ] Node düzeneğinde bm25 sırası, önek, `trigram`, içeriksiz tablo ve `ATTACH` ile şema nitelemeli `MATCH` testleri yeşil.
- [ ] Node SQLite kitaplığı, JSON Schema taslağı, gövdeleyici (`tr_stem_lex` yok) ve Simple Clean kararları karar defterinde (K-44); expo-sqlite `trigram` sonucu ilerleme notunda.
- [ ] `tr-govde.jsonl` vektörleri TypeScript ve Python'da yeşil; sorgu kurucusu 1.024 kod noktası sınırında `tooLong` dönüyor.
- [ ] `pnpm lint`, `pnpm typecheck`, `pnpm test`, `dotnet test --solution server/Mutalaa.slnx` ve `uv --directory pipeline run pytest` yeşil.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build
pnpm --filter @mutalaa/search test
pnpm --filter @mutalaa/content-schema test
pnpm lint && pnpm typecheck && pnpm test
dotnet test --solution server/Mutalaa.slnx
uv --directory pipeline run pytest
```

## Dikkat
- `snippet()` ve `highlight()` kullanılmaz; katlanmış metin döndürürler. Sonuç parçası kanonik metinden `reader-core` içinde üretilir.
- `tokenize='unicode61 remove_diacritics 0'`; normalleştirme belirteçleyiciye bırakılmaz. `detail` varsayılandır; boyut gerekçesiyle değiştirmek Açık sorudur.
- Paket DDL'i diller arası sözleşmedir; değişiklik A13, A23 ve A28'i etkiler. Şema değişince `schema_version` ve `normalizer_version` kuralları uygulanır ([İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §6).
- Testlerde Arapça metin uydurulmaz: `\u` kaçışıyla kurulan sentetik harf dizileri (A12.5), belgeden programla alınan örnek sorgular (A12.4) ya da kaynak dosyadan betikle kesilmiş parça kullanılır.
- Kültürden bağımsızlık: sorgu kurucusunda `toLocaleLowerCase` argümansız kullanılmaz; testler CI'da `LANG=tr_TR.UTF-8` ile de koşar.
- Gövdeleyici için yalnız `lib/turkish-stemmer.js` içe aktarılır; `index.js` `fs` ve `path` yükler, algoritma dosyasını dinamik `require` ile açar ve cihaz paketlemesine uygun değildir. Dosya ESM sözdizimindedir ve paketin `package.json` dosyasında `type` yoktur: Node `MODULE_TYPELESS_PACKAGE_JSON` uyarısı verir, Vitest altında yüklenir.
- İçeriksiz FTS5 tablosunda `'rebuild'` çalışmaz (SQLite 3.53.4); satırlar doğrudan yazılır, ardından yalnız `rank` ve `optimize` çalışır (K-44 madde 4).
- `.sql` ve `.jsonl` dosyaları LF ve BOM'suzdur; `metin-kurali` hook'u denetler.

## İnsan adımları
- Yok.

## Çıktılar
- `packages/content-schema/sql/*.sql` (00-ortak, 10-metin, 11-xref, 12-tr-root, 20-arama, 21-arama-iceriksiz, 29-arama-sonrasi, 29-arama-sonrasi-iceriksiz, 30-core, 31-page-map, 40-kelime-kok, 50-risale-dizin, 60-mushaf-a, 61-mushaf-b, 70-ses-katalog, 71-ses-zaman) ve `sql/paketler.json`; `packages/content-schema/manifest.schema.json`; `packages/content-schema/test/` (şema testleri ve SQLite düzeneği)
- `packages/search/src/` sorgu kurucusu (`tooLong` sınırı), `stemTr` ve testleri; `shared/test-vectors/fts-query/query.jsonl` (`fq-`) ve `shared/test-vectors/normalize/tr-govde.jsonl` (`tg-`); `uv run mutalaa export test-vectors --fts-ornekleri`
- Publisher test projesinde DDL duman testi ve manifest şeması testi; Python ve C# vektör koşucularında `fts-query/` atlaması; C# koşucusunda `tr-govde.jsonl` atlaması
- A12.0 tedarik raporu: sürümler, ölçüm sayıları ve gövdeleyici karşılaştırması (ilerleme notuna da yazılır)
- Karar defterinde K-44 (Node SQLite kitaplığı, JSON Schema taslağı, cihaz gövdeleyicisi, Simple Clean ve paket tabloları)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A12-arama-indeksi-ve-paket-semasi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) · Sonraki: [A13](./A13-yayinlayici-ve-kalite-kapisi.md)
