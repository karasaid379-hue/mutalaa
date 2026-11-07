# A28 · Arama ekranı

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A12](./A12-arama-indeksi-ve-paket-semasi.md) · [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `hat-gelistirici` (ölçüm kümesi) · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `test-vektoru` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A28`

## Amaç
Ara sekmesini kurar. Arama cihazda, ATTACH edilmiş bütün metin paketlerinin FTS5 indekslerinde tek deyimle yapılır; sonuçlar esere göre gruplanır ve âyet sonuçlarında Arapça metinle meal birlikte görünür. Kapsam süzgeci, tırnaklı ifade, "Bakara 255" ve "2:255" ile adrese gitme ve son aramalar eklenir. Geliştirici menüsündeki "Arama ölçümü" ekranı ve sorgu kümesi K-17'deki 50 ms hedefini (p95) ölçmeye hazırlanır; referans cihazdaki resmî ölçüm A33'tedir.

## Okunacak belgeler
- [Arama (FTS5)](../../03-veri/05-arama-fts5.md): tamamı; özellikle §3 sorgu ayrıştırma, §4 sıralama ve sonuç parçası, §5 ATTACH, §6 ölçüm, §7 açık sorular
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §1 Ara sekmesi, §3.1 ortak durumlar, §3.2 Ara satırı, §6 Geliştirici, §7 `mutalaa://ara?q=…`, §8 kural 1 ve 11
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §6.3 ATTACH yöneticisi, §9 bütçeler, §10 bayraklar, §12 telemetri, §14 `trLower`
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §12 sure adları ve insan yazımları
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.7 arama özellikleri, §8 B-02
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 madde 5, §9 Arama akışı, §10 performans
- [Gizlilik](../../07-yayin/02-gizlilik.md): §2.1 son aramalar satırı, §2.7, §5 madde 3

## Kapsam
**Yapılır**
- `src/features/search`: sorgu yürütücü, esere göre gruplama, "Tümü" listesi (ağırlıklı RRF), "Daha fazla", sonuç satırı; `app/(tabs)/ara/index.tsx` (A21'in yer tutucusu) doldurulur.
- `ara` derin bağlantısının `q` ve `kapsam` parametreleri (A25 bu türü A28'e bırakır).
- Adla adres çözümü ("Bakara 255", "Âl-i İmrân 7") ve "2:255" için en üstte "Git: …" satırı.
- Kapsam süzgeci, tırnaklı ifade, "Tam yazımla ara" anahtarı, Arapça trigram yedeği, `kök:` süzgecinin arayüzü.
- Son aramalar: v1 özelliği, yalnız cihazda (01-urun/01 §4.7; Gizlilik §2.1); ayrıntıları A28.1'de karara bağlanır.
- "Arama ölçümü" ekranı ve ölçüm sorgu kümesi (A12 bunu A28'e bırakır); sonuç parçasının `packages/reader-core` içinde üretimi.

**Yapılmaz**
- Normalleştirme kuralları (A05), FTS tabloları ve MATCH sorgu kurucusu (A12). Bir vektör kırılırsa düzeltme oraya, `test-vektoru` kuralıyla gider.
- Fihrist'teki "2:255" girişi (A24); `q` derin bağlantısı ve geri dönüş yığını (A25); öz test ekranı (A32); Maestro akışları ve referans cihazda B-02 ölçümü (A33).
- Kök verisi (`kelime-kok`): A17. Tefsir kapsamının gerçek pakete bağlanması: A37. Web araması: A38. Anlamsal arama: faz atanmadı.

## Tedarik
Bu aşama yeni içerik kaynağı (metin, veri, yazı tipi, ses, görsel) almaz: `pipeline/sources/*.toml` kaydı ve `data/gelen/` klasörü gerekmez. Aldığı yapılar kitaplık ve araçtır; sürümler npm kaydına ve Expo SDK 58 paket listesine sabitlenir (ölçüm tarihi 2 Kasım 2026). Ücretli kitaplık ya da API yoktur; ücretli tek iş EAS derlemesidir (A28.1 Karar 2).

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Cihazda FTS5 ve ATTACH (A28.2, AR-6) | `expo-sqlite` ~58.0.15 ([npm](https://www.npmjs.com/package/expo-sqlite), 31 Ekim 2026; Expo SDK 58, `expo` 58.0.22; [Expo SQLite belgesi](https://docs.expo.dev/versions/v58.0.0/sdk/sqlite/)); biçim npm paketi (A12 Tedarik satırıyla aynı) | A21 kurar (`npx expo install`, sürüm kilit dosyasına girer); A28 yeni kurulum yapmaz | A12.0: SQLite 3.53.3, `-DSQLITE_ENABLE_FTS5=1` varsayılan açık. Tedarik ölçümü: arşivdeki iki `sqlite3.c` dosyasında (`vendor/sqlite3`, `vendor/sqlcipher`) `SQLITE_MAX_ATTACHED` varsayılanı 10; `android/build.gradle` ve `ios/ExpoSQLite.podspec` değeri değiştirmiyor; Node SQLite 3.53.4'te 11. ATTACH "too many attached databases - max 10" verir. `MATCH` sözdizimi Node'da ölçüldü: `FROM p_x.unit_fts … WHERE unit_fts MATCH ?1` (takma adsız tablo adı) `JOIN`, `bm25(unit_fts)`, `ORDER BY rank`, `LIMIT`/`OFFSET` ve iki şemalı `UNION ALL` ile çalışır; `WHERE p_x.unit_fts MATCH` ve takma ad (`AS f`) ile `bm25(f)` "no such column" verir. Android derlemesinde doğrulama A23.1'dedir | `@op-engineering/op-sqlite` 19.0.3 ([npm](https://www.npmjs.com/package/@op-engineering/op-sqlite), 29 Ekim 2026; yalnız gerçek veriyle ölçüm sorun gösterirse; [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §2) |
| Sonuç listesi (A28.3) | React Native yerleşik `SectionList` ve `FlatList` (`react-native` 0.88.1, [npm](https://www.npmjs.com/package/react-native), 27 Ekim 2026; Expo SDK 58 ile gelir); ek kitaplık yok | Yerleşik; indirme yok | `react-native` 0.88.1 npm kaydında ve Expo SDK 58 paket listesinde. Kaydırma bütçesi A33'te ölçülür | `@shopify/flash-list` 2.3.2 ([npm](https://www.npmjs.com/package/@shopify/flash-list), 10 Haziran 2026; Expo SDK 58 paket listesinde; GitHub `Shopify/flash-list` etiket v2.3.2 @e7c0df19ff08daceae786a7b2b6f6ff0997f390a; [belge](https://shopify.github.io/flash-list/)); npm'in en son sürümü 2.3.3'tür (1 Ekim 2026), SDK 58 listesi 2.3.2'yi sabitler |
| Son aramalar deposu (A28.4) | `react-native-mmkv` 4.3.2 ([npm](https://www.npmjs.com/package/react-native-mmkv), 22 Haziran 2026; GitHub `mrousavy/react-native-mmkv` etiket v4.3.2 @e98276c438529731638c62be16013f3ca55804e7) ve eş bağımlılığı `react-native-nitro-modules` 0.37.1 ([npm](https://www.npmjs.com/package/react-native-nitro-modules), 27 Ağustos 2026); yalnız `src/lib/kv.ts` üzerinden | A21 kurar (`pnpm --filter @mutalaa/mobile add react-native-mmkv react-native-nitro-modules`); A28 yeni kurulum yapmaz | A21 Tedarik satırıyla aynı sürüm; npm kaydı ve git etiketi eşleşti. README Expo için `npx expo prebuild` ister (yerel modül; proje `expo-dev-client` derlemesi kullanır) | `expo-sqlite/kv-store` (`expo-sqlite` 58.0.15 ile gelir; `getItemSync`, `setItemSync`, `removeItemSync`, `getAllKeysSync` ve `clearSync` yöntemleri doğrulandı) |
| Derin bağlantı (`ara?q=…&kapsam=…`) ve rota | `expo-router` ~58.0.29 ([npm](https://www.npmjs.com/package/expo-router), 31 Ekim 2026; [URL parametreleri](https://docs.expo.dev/router/reference/url-parameters/)) ve `expo-linking` ~58.0.15 ([npm](https://www.npmjs.com/package/expo-linking), 28 Ekim 2026; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/linking/)) | A21 kurar | Expo SDK 58 paket listesinde (`expo` 58.0.22). `expo-router` 58.0.29 eş bağımlılığı `@testing-library/react-native >= 14.0.0` ister; A21'in 14.1.0'ı karşılar | — |
| Ölçüm JSON'unu yazma, paylaşma ve cihaz bilgisi (A28.5) | `expo-file-system` ~58.0.13 ([npm](https://www.npmjs.com/package/expo-file-system), 28 Ekim 2026; `new File(Paths.document, …)` ve `file.write`; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/filesystem/)), `expo-sharing` ~58.0.21 ([npm](https://www.npmjs.com/package/expo-sharing), 28 Ekim 2026; `Sharing.isAvailableAsync` ve `Sharing.shareAsync`; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/sharing/)), `expo-device` ~58.0.5 ([npm](https://www.npmjs.com/package/expo-device), 1 Ekim 2026; `Device.modelName`, `Device.osVersion`, `Device.totalMemory`; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/device/)) | `expo-file-system` A21'de kuruludur; `expo-sharing` ve `expo-device` A28.5'te `npx expo install` ile eklenir (A30'daki yedek aynı paylaşım modülünü kullanır). Yeni yerel modül geliştirme derlemesini yeniler: EAS derlemesi ücretlidir, tahmini maliyet kullanıcıya gösterilir (CLAUDE.md kural 11) | Üç paket Expo SDK 58 paket listesinde; belge sayfaları açılıyor ve yöntem adları belgede var | JSON `Paths.document` altına yazılır ve `adb` ile okunur (paylaşım menüsü olmadan) |
| Türkçe gövdeleyici, cihaz yarısı (A12.1 kararına bağlı) | `snowball-stemmers-js` 3.1.2 ([npm](https://www.npmjs.com/package/snowball-stemmers-js), 13 Ağustos 2026; GitHub `QQSHI13/snowball-stemmers-js` etiket v3.1.2 @9a2044b462680f1a7df9b77b6cc087d7ad77fc1e); A12 Tedarik satırıyla aynı; yalnız A12.1 gövdeleyiciyi cihazda kullanmayı seçerse | `pnpm add` (A12.1 kararı); `index.js` değil, `lib/turkish-stemmer.js` doğrudan içe aktarılır | A12.0: 18.505 sözcükte Python `snowballstemmer` 3.1.1 çıktısıyla fark 0. Hermes'te yükleme denemesi A28.0'dadır | `tr_stem_lex` tablosu (Yayınlayıcı doldurur; cihazda gövdeleyici gerekmez) |
| Ekran testleri (A28.3, A28.4) | `@testing-library/react-native` 14.1.0 ([npm](https://www.npmjs.com/package/@testing-library/react-native), 8 Ekim 2026; GitHub `callstack/react-native-testing-library` etiket v14.1.0 @5ce6da4aaa78282d8a5b9429f6c2312cab2e8865; [belge](https://oss.callstack.com/react-native-testing-library/)) ve `jest-expo` ~58.0.13 ([npm](https://www.npmjs.com/package/jest-expo), 28 Ekim 2026) | A21 kurar (`pnpm --filter @mutalaa/mobile add -D`) | A21 Tedarik satırıyla aynı sürümler. RNTL 14.1.0 `react >=19`, `react-native >=0.78` ve `jest >=29` ister; `jest-expo` 58.0.13 `jest` 29 ya da 30 ile çalışır | — |
| Sure adları ve yazım biçimleri (ad tabanlı "Git" satırı) | A11 çıktısı `shared/data/sure-adlari.json` (tek üreteçten üç dilde; adaylar A11 Tedarik'indeki internet listesinden gelir, editör denetimi İ-23); A28 dışarıdan almaz | A11.3 üretir; A13 ve A24 `core` `sure` tablosuna yükler | A11.3 "Bitti sayılır": 114 kayıt, her sure için bir kanonik ad | — |
| Ölçüm derlemesi (sürüm kipi, A28.1 Karar 2) | EAS Build, `eas.json` `internal` profili (A21.5); hesap: altyapı (Expo hesabı); `eas-cli` sürümü A21'de sabitlenir | `eas build --platform android --profile internal` (ücretli iş: tahmini maliyet kullanıcıya gösterilir, CLAUDE.md kural 11) | Profil yapılandırması A21.5 testinde; ölçüm profili kararı A28.1'de | Yerel Gradle sürüm derlemesi (yalnız A00'daki yol kararı yerel derlemeyi seçtiyse) |

Kendimiz yapacağımız işler: çok paketli sorgu yürütücüsü (parametreli SQL), RRF ve ek puanlar, sonuç parçası ve vurgulama (kanonik metnin kod noktası ofsetleriyle; npm araması "react native highlight text", 2 Kasım 2026: bakımı süren uygun bir paket çıkmadı, en yakınları `@sanar/react-native-highlight-text` 1.0.2 (2021) ve metin girişi için `react-native-highlight-text-view`), sure adı çözücüsü, Ara ekranı bileşenleri, son aramalar sarmalayıcısı, ölçüm ekranı ve ölçüm sorgu kümesi üreteci.

## Adımlar
### A28.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: npm kaydı (`expo-sqlite`, `react-native-mmkv`, `react-native-nitro-modules`, `expo-router`, `expo-linking`, `expo-file-system`, `expo-sharing`, `expo-device`, `@testing-library/react-native`, `jest-expo`) ve Expo SDK 58 belge sayfaları. Açılmayan adresin yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Kitaplık sürümlerini paket kaydından doğrula: `pnpm --filter @mutalaa/mobile list` çıktısı tablodaki sürümlerle aynıdır (Expo paketleri SDK 58 paket listesiyle). `expo-sharing` ve `expo-device` kurulu değilse `npx expo install` ile eklenir; yenilenen geliştirme derlemesinin tahmini maliyeti önce kullanıcıya gösterilir.
- İndirilecek içerik dosyası yoktur: `data/gelen/` klasörü ve `pipeline/sources/*.toml` kaydı gerekmez.
- A12.1 gövdeleyiciyi cihazda kullanmayı seçtiyse `snowball-stemmers-js` 3.1.2 `lib/turkish-stemmer.js` dosyasının Hermes'te yüklendiği denenir (cihaz denemesi kullanıcıya bırakılır, CLAUDE.md çalışma düzeni 3); yüklenmezse `tr_stem_lex` tablosu kullanılır.
- **Bitti sayılır:** tablodaki her sürüm npm kaydı ve kilit dosyasıyla eşleşiyor; açılmayan adres yok ya da yedek adayla değiştirilip tablo güncellendi; gövdeleyicinin cihazdaki durumu (yüklendi ya da `tr_stem_lex`) ilerleme notunda yazılı.

### A28.1 · Önkoşul, doğrulamalar ve iki karar
- A12 çıktısını denetle: `packages/search` sorgu kurucusu ve `shared/test-vectors/fts-query/query.jsonl` yeşil; metin paketlerinin `unit_fts`, `unit_tri` ve `tr_stem_lex` taşıdığı Yayınlayıcı testlerinde görülüyor; `dev` manifesti `core` ve `test-kucuk` paketlerini listeliyor (A13).
- AR-6 ve MM-5 (expo-sqlite derlemesindeki `SQLITE_MAX_ATTACHED`, şema nitelemeli FTS5 `MATCH`) A23.1'de cihazda ölçüldüyse sonuç okunur. Tedarik ölçümü kaynaktan şunu verdi: `expo-sqlite` 58.0.15 derlemesinde `SQLITE_MAX_ATTACHED` 10'dur (mobil mimari yöneticisinin `MAX_ATTACHED = 8` sınırı bunun altındadır); `MATCH` sol işleneni takma adsız FTS tablosunun adıdır (`FROM p_x.unit_fts … WHERE unit_fts MATCH ?1`), şema nitelemeli ad ve takma ad hata verir. Cihaz sonucu yoksa burada ölçülür (Android derlemesi; cihaz denemesi kullanıcıya bırakılır) ve `/belge-esitle` ile işlenir.
- Karar 1 · Son aramaların ayrıntısı. Tutulması v1 kapsamındadır ve yalnız cihazdadır (01-urun/01 §4.7; Gizlilik §5 madde 3, 19 Ekim 2026'da çözüldü). Kayıt sayısı, Ara ekranındaki silme düğmesi ve Gizli mod kuralı kullanıcıya sorulur, `/karar` ile yazılır. Öneri: MMKV, en çok 10 kayıt, "Temizle" düğmesi, Gizli mod açıkken kayıt yok. "Verilerimi sil" son aramaları da siler (Gizlilik §2.7).
- Karar 2 · Ölçüm derlemesi. Ölçüm yalnız sürüm (release) kipinde geçerlidir (06-mobil/01 §9). `eas.json` `development` profili geliştirme istemcisidir (`developmentClient: true`), sürüm kipinde değildir; `internal` profili sürüm kipindedir ve `core` ile isteğe bağlı paketleri gösterir (06-mobil/01 §10; K-42). Seçenekleri kullanıcıya sun, `/karar` ile yaz. Öneri: ölçüm `internal` profil derlemesiyle yapılır; `dev` verisiyle ölçmek gerekirse `developmentClient: false` ve `APP_FLAVOR=dev` taşıyan ayrı bir EAS ölçüm profili eklenir. EAS derlemesi ücretli iştir: tahmini maliyet kullanıcıya gösterilir (CLAUDE.md kural 11). A33 bu kararı kullanır; karar [BÇ-14](../07-belge-celiskileri.md)'ü kapatır.
- **Bitti sayılır:** AR-6 sonucu ve iki karar yazılı; A12 testleri yeşil.

### A28.2 · Sorgu yürütücü ve adla adres çözümü
- MATCH ifadesi A12'nin sorgu kurucusundan gelir (03-veri/05 §3 tablosu). Çok paketli `UNION ALL` deyimi, gruplama, RRF (`Σ w / (60 + sıra)`; Âyet 1,2 · Meal 1,0 · Tefsir 0,9 · Risale 0,9 · Hadis 0,8), ek puanlar (başlık ×1,5, tam ifade ×1,3, dar anahtar ×1,2) ve sonuç parçası `packages/reader-core` içinde parametreli SQL olarak yazılır; SQL yürütücüsü arayüzle verilir (02-mimari/03 §2 kural 2). Her dal ayrı alt sorgudur ve `MATCH` sol işleneni takma adsız FTS tablosunun adıdır (`FROM p_x.unit_fts JOIN p_x.unit u ON u.rowid = unit_fts.rowid WHERE unit_fts MATCH ?1 ORDER BY bm25(unit_fts) LIMIT 20`; A28.0 ölçümü).
- Şema adları A23'ün `ContentDb.ensure` yöneticisinden gelir; ATTACH açılışta bir kez yapılır. Her dal `LIMIT 20`, "Daha fazla" `OFFSET n`; hazırlanmış deyimler yeniden kullanılır; `tr_stem_lex` sorguları toplu yapılır. 2 karakterlik önekte bm25 hesaplanmaz, sıra `ord`'dur.
- Türkçe terim `â`, `î` ya da `û` içeriyorsa dar süzgeç uygulanır; sonuç kalmazsa geniş sonuçlar "Düzeltme işaretsiz yazımlar da gösteriliyor" notuyla döner. Arapça terim az sonuç verir ve en az 3 karakterse `unit_tri` sonuçları "otomatik eşleşme" çipiyle katlı gelir. `kök:` süzgeci yalnız `p_kelime_kok` bağlıyken çalışır; değilse "Kelime kökleri paketi gerekli" der.
- Adla adres: A12'nin kurucusu adres biçimini algılar ve sure adı çözücüsünü dışarıdan alır. Çözücü burada `core` `sure` tablosundan kurulur: girdi geniş anahtarla normalize edilir, `variants` ile eşlenir, sonuç `packages/anchors` ile çapaya çevrilip doğrulanır. Aralık dışı adres (`2:300`) "Git" satırı üretmez ve en yakın âyete yuvarlanmaz. Fihrist de adla girişe açılırsa aynı çözücüyü kullanır (öneri); ikinci kopya yazılmaz. `sure` tablosu boşsa (A11.3'ün editör denetimi ve dışa aktarması, İ-23, henüz yapılmadıysa; A13, A24) çözücü yalnız `2:255` biçimini tanır; ad tabanlı "Git" satırı A11.3'ten sonra açılır; İ-23 yalnız bu alt adıma bağlıdır. Testlerin ad içeren girdileri belgedeki örneklerdir (Arama §3 madde 1), beklenen çapa `shared/data/sure-adlari.json` ile çözülür; dosya yoksa bu testler atlanır ve ilerleme notuna yazılır. Sure adı elle yazılmaz.
- **Bitti sayılır:** RRF, gruplama, sonuç parçası ve sure çözücüsü testleri Vitest'te yeşil; testler `LANG=tr_TR.UTF-8` altında da geçiyor.

### A28.3 · Ara ekranı
- Bileşenler: `SearchField`, `ScopeChips` (Tümü · Kur'an · Meal · Tefsir · Hadis · Risale; `kaynak:` süzgecinin arayüzü), `SearchResultRow`, son aramalar, `EmptyState`, `Skeleton` (150 ms kuralı). Rota dosyası yalnız özellik bileşenini çağırır.
- Ekran `q` ve `kapsam` parametrelerini okur (`mutalaa://ara?q=sabır&kapsam=kuran`; 01-urun/03 §7).
- Kapsam çipi yalnız derlemede görünen (`isPackVisible`) paketler için çıkar. Görünür ama kurulu olmayan kapsamda "Bu kapsamın paketi yok · İndir" (Depolama, A29).
- Âyet ve Meal satırları âyetin Arapçasını (kanonik Tanzil metni) ve `meal:elmalili:{sure}:{ayet}` mealini birlikte gösterir; 900 dp ve üstünde iki sütun (öneri). Meal `core`'da henüz yoksa yalnız Arapça görünür; yer tutucu meal yazılmaz.
- Sonuç parçası kanonik metinden ±12 sözcüktür; `search_text`, `snippet()` ve `highlight()` çıktısı ekrana girmez. Arapça sözcükler ayrı `Text` parçası olarak sağdan sola ve Arapça yazı tipiyle çizilir. Risale sonucunun kitabı kurulu değilse yalnız etiket ve indirme önerisi görünür.
- Okurken açılan aramada okunan eserin grubu önce gelir. Sonuca dokunuş hedefi 01-urun/03 §8 kural 1'e göre açar (Kur'an hedefi Oku'da, diğerleri Kütüphane'de); paketi olmayan hedefe atlanmaz, satırda "paket gerekli" yazar.
- Durumlar: boş sorgu → son aramalar; sonuç yok → "Tam ifade için tırnak kullan"; hata → satır içi kart ve "Yeniden dene".
- `testID` önerisi: `arama-alani`, `arama-sonuc-{çapa}`; A33 akışları bunları kullanır. Emülatördeki `isik` sınaması A13'ün "Işık" sözcüğünü taşıyan `test-kucuk` fikstürüyle yapılır.
- **Bitti sayılır:** RNTL testleri gruplama, kapsam, paket eksik ve sonuç yok durumlarını geçiyor; emülatör görüntüleri `arayuz-denetcisi` onayından geçti.

### A28.4 · Son aramalar
- A28.1 kararına göre yazılır. Kayıt yalnız `src/lib/kv.ts` (MMKV) üzerinden tutulur; `user.db`'ye, yedeğe ve Sentry'ye girmez (06-mobil/01 §12).
- **Bitti sayılır:** Birim testi kayıt sınırını, temizlemeyi ve kararın Gizli mod kuralını sınıyor.

### A28.5 · Arama ölçümü ekranı ve sorgu kümesi
- Rota (öneri ad) `app/(tabs)/ayarlar/gelistirici/arama-olcumu.tsx`; geliştirici menüsüne satır eklenir. `gelistiriciMenusu` bayrağıyla yalnız `dev` ve `internal` derlemede görünür; `public`'te Ayarlar'a yönlendirilir (03-veri/05 §6; 06-mobil/01 §10).
- Sorgu kümesi `shared/test-vectors/arama/olcum.jsonl` (03-veri/05 §6'daki konum, JSONL biçimi): yaklaşık 200 sorgu; sık ve seyrek sözcük, 2–4 karakterlik önek, ifade, düzeltme işaretli terim, ekli biçim, harekeli ve harekesiz Arapça, trigram, kök, adres ve birden çok paketi arayan sorgular. Satır alanları: `id`, `kategori`, `sorgu`, `beklenen` (ilk sonuç çapaları). Python ve C# vektör koşucuları bu klasörü de atlar (A12'deki `fts-query/` kuralı).
- Terimler ve beklenen sonuçlar hafızadan yazılmaz. `hat-gelistirici` terimleri paketteki normalize sözcüklerden sıklık bandına göre örnekleyen bir üreteci `uv run mutalaa export test-vectors` komutuna ekler; beklenen sonuçlar ilk koşudan alınır ve kullanıcı onayıyla dondurulur.
- Ekran kümeyi üç kez koşar, her sorguyu `performance.now()` ile ölçer, kategori başına p50, p95 ve en yüksek değeri gösterir; açılıştan sonraki ilk sorguyu ayrı yazar; beklenen ilk sonucu tutmayan sorguları listeler. Sonucu cihaz modeli (`expo-device`: `Device.modelName`, `Device.osVersion`, `Device.totalMemory`) ve paket sürümleriyle JSON olarak paylaşım menüsünden verir (`expo-sharing`: `Sharing.shareAsync`; A30'daki yedekle aynı modül). `dev` derlemede aynı JSON uygulama belge klasörüne de yazılır (`expo-file-system`: `new File(Paths.document, …)`; öneri).
- Emülatörde bir ön ölçüm yapılır ve `.tmp/a28/olcum.json` olarak saklanır. Geliştirme kipindeki değerler bütçeye tabi değildir.
- **Bitti sayılır:** Ekran kümenin tamamını koşuyor ve JSON üretiyor; dondurulmuş beklenen sonuçlarla uyuşmayan sorgu sayısı 0.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/search test`, `pnpm --filter @mutalaa/reader-core test` ve `pnpm --filter @mutalaa/mobile test` yeşil; yeni testler RRF, gruplama, sonuç parçası, sure çözücüsü ve ekran durumlarını kapsıyor.
- [ ] "2:255" en üstte "Git" satırı veriyor, "2:300" vermiyor (Vitest). "Bakara 255" ve "Âl-i İmrân 7" A11.3'ten sonra `shared/data/sure-adlari.json` ile sınanıyor; o zamana kadar bu testlerin atlandığı ilerleme notunda yazılı.
- [ ] Emülatörde `isik` araması "Işık" içeren sonucu ilk sırada gösteriyor ve dokunuş okuyucuyu açıyor (`.tmp/a28/`, `arayuz-denetcisi` raporu).
- [ ] Âyet sonucunda Arapça metin ve meal birlikte görünüyor; `search_text` hiçbir ekranda yok (`reader-core` testi, 07-yayin/03 §5 madde 5).
- [ ] `public` bayrağında `test-` önekli kaynaklı paketin, `internal` bayrağında `test-kucuk` ve `test-ses` dışındaki `test-` önekli kaynaklı paketin kapsam çipi görünmüyor (RNTL; `isPackVisible`).
- [ ] Arama sorgusu Sentry olayına ve kırıntısına girmiyor (telemetri birim testi).
- [ ] Arama ölçümü ekranı `public` bayrağında açılmıyor; `dev`'de kümeyi koşup JSON üretiyor; dondurulmuş beklenen sonuçlarla uyuşmazlık 0.
- [ ] `pnpm test` (JSONL biçim denetimi dahil), `dotnet test` ve `uv run pytest` yeşil; Python ve C# koşucuları `arama/` klasörünü atlıyor.
- [ ] AR-6 sonucu ve A28.1'deki iki karar karar defterinde ya da ilgili dokümanda yazılı.
- [ ] `## Tedarik` tablosundaki her sürüm npm kaydı ve kilit dosyasıyla eşleşiyor (A28.0).

## Doğrulama
```bash
pnpm --filter @mutalaa/mobile list expo-sqlite react-native-mmkv expo-router expo-sharing expo-device @testing-library/react-native   # A28.0: sürümler Tedarik tablosuyla aynı
pnpm --filter @mutalaa/search test
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm test                                                    # Turborepo; shared/test-vectors JSONL denetimi dahil
pnpm lint && pnpm typecheck
dotnet test --solution server/Mutalaa.slnx && uv --directory pipeline run pytest
curl -s http://localhost:8333/mutalaa/dev/manifest.json
# Aşağıdaki adb adımları emülatör ve cihaz testidir: kullanıcıya bırakılır (CLAUDE.md, çalışma düzeni 3).
mkdir -p .tmp/a28
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ara?q=isik'"
adb exec-out screencap -p > .tmp/a28/ara-isik.png            # mobil-ekran: PNG'yi Read ile oku
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ara?q=2:255'"
adb exec-out screencap -p > .tmp/a28/ara-adres.png
# Ölçüm JSON'u (yalnız dev derleme; dosya yolu A28.5'te belirlenir, Doğrulanacak):
# adb exec-out run-as app.mutalaa.dev cat files/<yol>/olcum.json > .tmp/a28/olcum.json
```

## Dikkat
- Kanonik metin değişmez; sonuç parçası ve işaretleme yalnız kanonik metinden üretilir (K-26; `metin-butunlugu`). Kur'an'da eşleşme Simple Clean normalize metniyle, gösterim Uthmani metinle yapılır; işaretlenemeyen eşleşmede satır yine gösterilir (AR-4).
- Türkçe küçük harf açık eşlemeyle yapılır (`packages/search`); `toLocaleLowerCase()` argümansız kullanılmaz. Hermes davranışı A32'deki öz testte ölçülür.
- Kullanıcı girdisindeki her sözcük FTS5 dizgisi olarak çift tırnağa alınır (tırnaksız `2:255` ya da `alfa-beta` FTS5'te "no such column" hatası verir; Node SQLite 3.53.4 ölçümü); SQL metnine yalnız ATTACH takma adı girer, değerler parametredir.
- ATTACH sınırı 10'dur (`expo-sqlite` 58.0.15 kaynak ölçümü); mobil mimari yöneticisi 8'le sınırlar ve Risale kitapları istek anında en çok 3 bağlanır (Arama §5).
- Arama sorgusu telemetriye, günlüğe ve yedeğe girmez (06-mobil/01 §12; Gizlilik §2.2).
- Ölçüm kümesinde ve testlerde Kur'an metni hafızadan yazılmaz; Arapça terimler paketten örneklenir (CLAUDE.md kural 2).
- Arama ölçümü ekranı `dev` ve `internal` derlemededir; küme `shared/test-vectors/arama/olcum.jsonl`'dır (03-veri/05 §6, 01-urun/03 §6, 07-yayin/03 §10, 02-mimari/03 §1.2).
- URL'de `?` ya da `&` varsa `adb shell` komutu tek parça tırnaklanır; cihaz yolu içeren argümanlarda Git Bash yol dönüşümü için `windows-sorun`.
- Commit kapsamları: `mobile`, `reader-core`, `test-vectors`, `pipeline`.

## İnsan adımları
- Yok. A28.1'deki iki karar kullanıcıya sorulur ve `/karar` ile yazılır.

## Çıktılar
- `apps/mobile/src/features/search/` (ekran, sorgu kancaları, son aramalar); `apps/mobile/app/(tabs)/ara/index.tsx`
- `apps/mobile/app/(tabs)/ayarlar/gelistirici/arama-olcumu.tsx` ve geliştirici menüsü satırı
- `packages/reader-core` içinde çok paketli sorgu, RRF, sonuç parçası ve sure çözücüsü; testleri
- `shared/test-vectors/arama/olcum.jsonl`, hattaki üreteci ve koşuculardaki atlama
- `apps/mobile/package.json` ve kilit dosyası (`expo-sharing`, `expo-device`)
- `apps/mobile/src/lib/i18n/tr.ts` anahtarları; `.tmp/a28/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A28-arama-ekrani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A27](./A27-ses-sistemi.md) · Sonraki: [A29](./A29-kutuphane-ve-depolama.md)
