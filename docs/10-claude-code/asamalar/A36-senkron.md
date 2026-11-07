# A36 · Senkron ve bağlantı oyları

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç)
> **Faz:** 4 · v1.x · **Önkoşul:** [A35](./A35-hesap-ve-gizlilik.md) · **İnsan adımı:** İ-20 (canlıya açılış)
> **Ajanlar:** `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` (A36.0 tedarik) · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `ef-goc` · `test-vektoru` · `mobil-ekran` · **Tahmini oturum:** 5–7
> **Başlat:** `/asama A36`

## Amaç
Hesabı bağlı cihazlar arasında kullanıcı verisi eşitlenir: UUIDv7 kimlikler, HLC zaman damgası, giden kutusu, `op_id` ile idempotent yükleme, `server_seq` imleçli çekme, 410 `imlec-eskidi` ile tam eşitleme ve K-16'nın veri türüne göre birleştirme kuralları. İki cihazda değişen not iki sürüm olarak korunur ve kullanıcı seçer. Kurallar sunucuda (C#) ve istemcide (TypeScript) aynı sonucu verir; bu ortak vektörlerle ve özellik tabanlı testlerle kilitlenir. Hesapla gelen bağlantı oyları ("Yararlı", "Yararsız", "Hata bildir") da bu aşamada açılır. Aşama, A35'in hazırladığı listeyle hesap, senkron ve oyların canlıya açılmasıyla biter.

## Okunacak belgeler
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): tamamı
- [Backend API](../../02-mimari/05-backend-api.md): §5 senkron uçları, §6 hata modeli, §7 EF Core, §9 kültür
- [Gizlilik](../../07-yayin/02-gizlilik.md): §3.2 veri envanteri, §3.5 hassas kullanıcı kayıtları, §3.6 silme ve dışa aktarma
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 depolama biçimi, §9 yeniden çapalama (senkronlanan kayıt kendiliğinden değişmez)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 kullanıcı veritabanı göç testleri · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §6 ayarlar ağacı
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §12 oylar ve inceleme kuyruğu · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §7 `xref_vote`

## Kapsam
**Yapılır**
- HLC'nin C# karşılığı (TypeScript uygulaması A23'te yazıldı) ve birleştirme kurallarının iki dilde saf işlevler olarak yazılması; ortak vektörler.
- Sunucuda `kullanici` şeması, `POST /api/v1/sync/push`, `GET /api/v1/sync/pull`, silinmiş satır temizliği ve `gc_seq`.
- İstemcide giden kutusu, yükleme ve çekme döngüsü, birleştirme, tam eşitleme; not çakışması arayüzü.
- v1 "Geri yükle" akışının aynı birleştirme işlevlerine bağlanması; özellik tabanlı testler; canlıya açılış.
- Bağlantı oyları: `xref_vote`, `PUT` ve `DELETE /api/v1/xrefs/{id}/vote`, gece işi ve Bağlantılar panelindeki oy menüsü.

**Yapılmaz**
- Hesap, kimlik ve silme akışı (A35); silme ve döküm akışları oyları da kapsar (A35).
- Uçtan uca şifreli notlar (ertelenmiş seçenek, [Gizlilik](../../07-yayin/02-gizlilik.md) §3.5). Metin CRDT'si (yalnız ortak düzenleme gelirse). PowerSync ve expo-sqlite oturum değişiklik kümeleri (gereksinim büyürse değerlendirilir; §8 "Seçenekler" ve Tedarik notları).

## Tedarik
Araştırma tarihi 2 Kasım 2026; A36.0'da yenilenir. Bu aşama içerik dosyası almaz: yalnız kitaplık ve yerleşik .NET ile PostgreSQL özelliklerini kullanır. Protokol (HLC, giden kutusu, birleştirme) K-16 ve [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md) §3–§8 ile belirlidir. İstemci kimlik üretimi (`uuid`, `expo-crypto`) ve HLC'nin TypeScript uygulaması A23'te kurulur; bu aşama onları yeniden almaz.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Satır kimliği UUIDv7 (istemci) ve güvenli rastgele bayt (KV-4) | `uuid` 14.0.3 (npm, 10 Ekim 2026; GitHub `uuidjs/uuid`, etiket `v14.0.3`, commit `993ff7b64a289ef7f921ccafc8bb98ef9461d214`; ESM, bağımlılık yok, tür tanımları pakette) ve `expo-crypto` 58.0.7 (npm; `getRandomBytes`). A23'te kurulur | Yeni paket yok (A23: `pnpm add uuid`, `expo install expo-crypto`) | `src/v7.ts` (v14.0.3): `options` (`random`, `rng`, `msecs`, `seq`) verilince üretim iç durumdan bağımsızdır; verilmezse `crypto.getRandomValues` ister ve README React Native ile Expo'da `react-native-get-random-values` önerir. Bu yüzden `v7({ rng })` ile `expo-crypto` baytları kullanılır (KV-4); Hermes'e polyfill eklenmez | `uuidv7` 1.2.1 (npm, 22 Mart 2026; GitHub `LiosK/uuidv7`, etiket `v1.2.1`, commit `98bfc947a22720dceb03622c846c9156f1333e07`; `V7Generator` özel rastgele kaynak alır); `react-native-get-random-values` 2.1.0 |
| UUIDv7 üretimi (sunucu ve .NET testleri) | `System.Guid.CreateVersion7()` ve `CreateVersion7(DateTimeOffset)` (.NET 9, 10 ve 11; temel kitaplıkta) | Yok (yerleşik) | Learn "Guid.CreateVersion7" (güncelleme 3 Ağustos 2026): RFC 9562 sürüm 7; zaman `DateTimeOffset.UtcNow`'dan gelir, `rand_a` ve `rand_b` rastgele doldurulur; aynı milisaniyede sıra vaadi yok | PostgreSQL 18 `uuidv7([shift interval])` (belge: milisaniye ve alt milisaniye zaman damgası ile rastgele bölüm; `uuid_extract_timestamp` ve `uuid_extract_version` ile doğrulanır) |
| Özellik tabanlı test, TypeScript | `fast-check` 4.10.2 (npm, 19 Eylül 2026; GitHub `dubzzz/fast-check`, etiket `v4.10.2`, commit `c77afa8277a67250d798c52e61343b8ed5fd268b`; ESM ve CJS; tek bağımlılık `pure-rand`; tür tanımları pakette) | `pnpm --filter @mutalaa/reader-core add -D fast-check` | `Parameters` arayüzü (v4.10.2): `seed`, `numRuns`, `path`, `verbose`, `reporter`; kökteki `vitest` ^5.0.5 ile çalışır | `@fast-check/vitest` 0.5.0 (npm, 11 Eylül 2026; etiket `vitest/v0.5.0`; `vitest` 4.1 ya da 5 ister; `test.prop` sarmalayıcısı, isteğe bağlı) |
| Özellik tabanlı test, .NET | `FsCheck.Xunit.v3` 3.6.0 (NuGet, 21 Ekim 2026; `FsCheck` 3.6.0 ve `FSharp.Core` 5.0.2'yi getirir; `xunit.v3.extensibility.core` [4.0.0, 5.0.0) ister, projede `xunit.v3` 4.0.2; GitHub `fscheck/FsCheck`, etiket `3.6.0`, commit `1ef52cfc65d5c318f5ee4da467df9087ad03e34c`) | `dotnet add server/tests/Mutalaa.Domain.Tests package FsCheck.Xunit.v3`; sürüm `server/Directory.Packages.props` içinde | FsCheck belgesi "Running tests": `[Property(MaxTest = 500)]` ve `[Property(Replay = "123,456")]` örnekleri; paket adı `FsCheck.Xunit.v3` belgede; nuspec bağımlılığı projedeki `xunit.v3` aralığına uyuyor | `CsCheck` 5.0.0 (NuGet, 24 Ekim 2026; GitHub `AnthonyLloyd/CsCheck`; F# bağımlılığı yok) |
| Not sürümlerinin kelime düzeyinde farkı (KV-6) | `diff` 9.0.0 (npm, 13 Nisan 2026; GitHub `kpdecker/jsdiff`, etiket `v9.0.0`, commit `ed13aca03aa25735fafc0645d1185e7a1c68fd8c`; ESM ve CJS; bağımlılık yok; tür tanımları pakette) | `pnpm --filter @mutalaa/mobile add diff` | `src/index.ts` (v9.0.0): `diffWords`, `diffWordsWithSpace`, `diffChars`, `diffLines`, `diffSentences` dışa aktarılır. Sürüm notu: 9.0.0'da ES5 desteği düştü ve `parsePatch` `TextDecoder` kullanır; bu aşama yama ayrıştırmaz | `fast-diff` 1.3.0 (npm, 19 Mayıs 2023; GitHub `jhchen/fast-diff`; karakter düzeyi; bağımlılık yok; tür tanımları pakette) |
| Saati denetlenen sunucu testleri (`saat_ileri`, 180 günlük temizlik) | `Microsoft.Extensions.TimeProvider.Testing` 10.11.0 (NuGet; `FakeTimeProvider`) | `dotnet add server/tests/Mutalaa.Api.Tests package Microsoft.Extensions.TimeProvider.Testing`; sürüm `server/Directory.Packages.props` içinde | NuGet düz kapsayıcı dizininde son kararlı sürüm 10.11.0; sunucu kodu zamanı `TimeProvider` ile okur (`UpdatedAtInterceptor`) | Elle yazılmış `TimeProvider` türevi |
| Bütünleşik test ortamı ve iki sanal istemci | `xunit.v3` 4.0.2 ve `Testcontainers.PostgreSql` 4.16.0 (`postgres:18.6-trixie`; A07'de kurulu); `Microsoft.AspNetCore.Mvc.Testing` (`WebApplicationFactory`; A14'te eklenir); kökte `vitest` ^5.0.5 | Yeni paket yok | [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) sürüm tablosu; `server/Directory.Packages.props` (`xunit.v3`, `Testcontainers.PostgreSql`); A14 Tedarik tablosu | Yok |
| Oy kimliği, hız sınırı ve idempotent yazma | Yerleşik: `System.Security.Cryptography.HMACSHA256` (`account_hash`); `AddRateLimiter` (A35'te kurulur); PostgreSQL 18 `INSERT … ON CONFLICT` ve `UPDATE … RETURNING` | Yok | [Backend API](../../02-mimari/05-backend-api.md) §5 (`account_hash = HMAC-SHA256(sunucu sırrı, hesap kimliği)`); A35 Tedarik tablosunda "Hız sınırı" satırı | Yok (yerleşik) |

Kendimiz yapacağımız işler: HLC'nin C# karşılığı (`Mutalaa.Domain/Sync`; TypeScript uygulaması A23'te) ve birleştirme kuralları, iki dilde saf işlev ve ortak vektörler (hazır HLC paketleri bu biçimi vermez, aşağıdaki not); `kullanici` şeması ve `push`/`pull` uçları; giden kutusu ve eşitleme döngüsü; not çakışması arayüzü; oy uçları, gece işi ve Wilson eşiği (birkaç satırlık formül).

Notlar:
- HLC için hazır paketler değerlendirildi: `@sozai/hlc` 0.1.0 (npm, 23 Ekim 2026; dizgi `<ISO zaman>:<8 haneli ondalık sayaç>:<düğüm>`), `@consento/hlc` 2.1.0 (npm; `Uint8Array` kodlaması), `Clockworks` 1.4.1 (NuGet; yalnız .NET, benzetimli `TimeProvider`, UUIDv7 ve HLC birlikte). Hiçbiri [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md) §3'teki `{12}-{4}-{16}` onaltılık biçimini iki dilde aynı çıktıyla vermez; bu yüzden HLC kendi saf işlevimizdir.
- Hazır eşitleme motoru seçilmedi: `@powersync/react-native` 2.3.3 (npm) `@op-engineering/op-sqlite` ister ve expo-sqlite ile Drizzle tasarımına girmez; protokol K-16 olarak kalır.
- expo-sqlite oturum değişiklik kümeleri kullanılmaz. Expo SDK 58 belgesinde `createSessionAsync`, `attachAsync`, `createChangesetAsync` ve `applyChangesetAsync` vardır; SQLite oturum eklentisi yalnız bildirilmiş birincil anahtarlı tablolarla çalışır, değişiklik kümesi eski ve yeni satır değerlerini taşır, çakışmayı uygulama sırasında bir geri çağrı çözer; zaman damgası kavramı yoktur ve silme yalnız satır silme kaydıdır. HLC, `op_id` ve PostgreSQL sunucusuyla bağdaşmaz; `outbox` korunur.
- Hypothesis (PyPI 6.170.14, 30 Ekim 2026; Python 3.11 ve üstü) bu aşamada kullanılmaz: A36'da Python kodu yoktur, ortak vektörler TypeScript ve C# içindir.
- `expo-crypto` belgesi: `getRandomBytes` 0 ile 1024 bayt alır; geliştirmede (React Native Debugger) `Math.random`'a düşer, yayın derlemesinde yerel güvenli kaynaktır.

## Adımlar
### A36.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosunu yenile: sürümleri npm kaydından (`https://registry.npmjs.org/<paket>/latest`), NuGet düz kapsayıcı dizininden (`https://api.nuget.org/v3-flatcontainer/<kimlik>/index.json`) ve GitHub etiketlerinden (`git ls-remote https://github.com/<sahip>/<depo>.git "refs/tags/<etiket>"`) oku; adreslerin açıldığını `curl -sIL --max-time 30 <adres>` ile doğrula. Açılmayan adresin yerine tablodaki yedek aday kullanılır. Çıkan sürüm tablodakinden farklıysa aynı ana sürümdeki en yeni kararlı sürüm alınır; ana sürüm değişmişse sürüm notu okunur ve tablo güncellenir.
- Bu aşama içerik dosyası almaz: `data/gelen/` altına indirme, `SHA256SUMS` ve `pipeline/sources/` kaydı gerekmez. Kitaplıklar paket yöneticisiyle gelir; sürümleri kilit dosyalarında sabitlenir (`pnpm-lock.yaml`, `server/Directory.Packages.props`).
- Kitaplıklarda sürümü paket kaydından doğrula: `uuid` ve `expo-crypto` A23'te kuruludur, `pnpm-lock.yaml` içindeki sürümler tabloyla karşılaştırılır; `fast-check`, `diff`, `FsCheck.Xunit.v3` ve `Microsoft.Extensions.TimeProvider.Testing` bu aşamada eklenir. Expo paketleri `expo install` ile SDK uyumlu sürümle gelir.
- Hazır yapı önce gelir: UUIDv7, fark gösterimi ve özellik tabanlı test için hazır kitaplık kullanılır; kendimiz yalnız HLC ve birleştirme kurallarını yazarız (Tedarik notları).
- **Bitti sayılır:** tablodaki sürümler paket kayıtlarıyla doğrulandı ve aşama notuna yazıldı; yeni kitaplıklar kilit dosyalarında sabit; `pnpm install --frozen-lockfile` ve `dotnet restore server/Mutalaa.slnx` hatasız.

### A36.1 · Doğrulamalar ve ortak çekirdek
- Tedarik sonuçları kayda geçer (`arastirmaci` A36.0'da doğruladı): KV-4 için A23'te kurulan `uuid` 14.0.3 `v7({ rng })` ve `expo-crypto` baytları; KV-6 için `diff` 9.0.0 (`diffWordsWithSpace`); expo-sqlite oturum değişiklik kümeleri kullanılmaz (gerekçe Tedarik notlarında). Karar verilince `/belge-esitle` ile [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md) §8 "Seçenekler" ve §9 (KV-4, KV-6) işlenir.
- `packages/reader-core/src/sync/hlc.ts` (A23.2'de yazıldı): §3'teki sabit genişlikli biçim (`{12}-{4}-{16}` küçük harf onaltılık; düğüm `device_id`'nin tiresiz ilk 16 hanesi), `tick`, `recv`, sayaç taşması, `sync_state.hlc_last` kalıcılığı. Bu adım sayaç taşmasını ve `recv` kenar durumlarını ortak vektörlerle sınar, eksik varsa tamamlar. C# karşılığı Domain'de (öneri `Mutalaa.Domain/Sync`; altyapı bağımlılığı yok).
- Birleştirme kuralları iki dilde saf işlev: §4 tablosu (kayıt bazında son yazan kazanır; `setting` anahtar başına; `hatim_page` küme birleşimi; `reading_position` cihaz başına; `note` iki sürüm) ve ek kurallar (silinen koleksiyonda `collection_id = NULL`; aynı çapa ve koleksiyonda başlıksız iki canlı yer iminden küçük `id` kalır, karşılaştırma ordinal dizgi karşılaştırmasıdır ve `Guid` türünün kendi sıralaması kullanılmaz; `vocab` `(lang, key)` için tek satır, büyük `seen_count`).
- Ortak vektörler (öneri, yeni aile; `/karar` ile kayda geçer): `shared/test-vectors/sync/hlc.jsonl` ve `shared/test-vectors/sync/merge.jsonl`; §4'teki beş örnek ilk satırlardır. Biçim `test-vektoru` becerisine uyar (JSONL, UTF-8, BOM yok, LF).
- **Bitti sayılır:** HLC ve birleştirme vektörleri TypeScript ve C#'ta yeşil.

### A36.2 · Sunucu: `kullanici` şeması ve senkron uçları
- `ef-goc`: `sync_user`, `device`, `op_log` ve §2'deki her kullanıcı tablosu §8'deki `kullanici.note` kalıbıyla (`user_id`, `server_seq`, birincil anahtar `(user_id, id)`, `(user_id, server_seq)` dizini; `reading_position` için `(user_id, device_id, context)` tekil). Tablolar A35'te seçilen kullanıcı veritabanındadır.
- `push`: işlemler sırayla uygulanır: `op_log`'da aynı `op_id` varsa kayıtlı sonuç döner; çapa `AnchorRef` ile ve boyutlar doğrulanır; tablo kuralı uygulanır; `server_seq` kullanıcının sayacından alınır (`UPDATE kullanici.sync_user SET last_seq = last_seq + $2 … RETURNING`; genel dizi kullanılmaz); sonuç `op_log`'a yazılır. İstek en çok 500 işlem taşır. Sonuç kodları `uygulandi`, `eskimis`, `reddedildi`; not çakışması `cakisma_kopyasi` (`id = op_id`, `conflict_of`). Yanıt `server_seq` ve `server_hlc` taşır.
- `pull`: her tablodan `server_seq > cursor` ilk `limit` satır okunur, birleştirilir, sıralanır; `next_cursor`, `has_more`, `server_hlc`.
- Silinmiş satırlar 180 gün tutulur (öneri, KV-1); temizlik işi `gc_seq` yazar; imleci gerideki istek 410 ve `imlec-eskidi` alır. Saati 10 dakikadan fazla ileride olan işlem `saat_ileri` ile reddedilir (öneri, KV-2). İki kod da Backend API §6 hata tablosundadır; `saat_ileri`'nin HTTP kodu ve istek düzeyinde mi işlem sonucu olarak mı döndüğü Doğrulanacak; karar verilince `/belge-esitle` ile işlenir.
- Testler (Testcontainers `postgres:18`): aynı `op_id` ile yeniden gönderim aynı sonucu verir ve `last_seq` artmaz; aynı kullanıcının eşzamanlı iki yüklemesinde `server_seq` tekrarsız ve artan; sayfalı çekme atlamasız; 501 işlem 400; 410 yolu; A35 silme testi yeni tabloları da kapsıyor.
- **Bitti sayılır:** `dotnet test` yeşil; OpenAPI farkı temiz.

### A36.3 · İstemci: giden kutusu, döngü ve birleştirme
- Hesap bağlıyken her kullanıcı yazması ile `outbox` satırı aynı işlemde yazılır (§2 "Yazma"). İlk bağlamada bütün yerel satırlar bir kez kuyruğa alınır ve hesaptaki verilerle §4 kurallarıyla birleşir; ikinci cihaz da aynı yolla katılır.
- Giden kutusunda aynı satırın gönderilmemiş işlemleri teke iner; yanıtı gelmemiş işlem aynı `op_id` ile yeniden gönderilir; o arada gelen değişiklik yeni `op_id` alır. Yanıttaki `accepted` ve `conflicts` listelerindeki işlemler giden kutusundan silinir ve satırın `base_version` değeri dönen `server_seq` olur.
- Tetikler: uygulama öne gelince, yerel yazmadan 5 saniye sonra (toplanarak), "Şimdi eşitle". Önce yükleme, sonra `has_more` bitene kadar çekme; imleç `sync_state`'e yazılır; `recv(server_hlc)` çağrılır.
- 410'da tam eşitleme: giden kutusu yüklenir, canlı satırların tamamı indirilir, giden kutusunda olmayan ve sunucuda bulunmayan yerel satırlar silinir. Cihaz kendi silinmiş satırlarını 365 gün tutar (öneri).
- v1 "Geri yükle" (A30) aynı birleştirme işlevlerini çağırır; ayrı kural kopyası kalmaz.
- Gizlilik: senkron kullanıcı açınca başlar; okuma ilerlemesi ve hatim için ayrı anahtar (öneri, [Gizlilik](../../07-yayin/02-gizlilik.md) §3.5); Gizli modda okuma geçmişi, otomatik hatim işareti ve seri kaydı yazılmaz (01-urun/02 §14, 03-veri/04 §7). Eşitlenen ayarlar §7 tablosundadır.
- Yeniden çapalama sonucu yalnız `device.db` `anchor_resolution` önbelleğine yazılır; senkronlanan kayıt kullanıcı eylemi olmadan değişmez.
- **Bitti sayılır:** istemci birim testleri ve vektörler yeşil; `user.db` göç testleri yayımlanmış her şema sürümünün fikstüründe veri kaybı göstermiyor.

### A36.4 · Not çakışması arayüzü ve bildirimler
- §5: asıl notta şerit ("Bu not iki cihazda değiştirildi · Sürümleri karşılaştır"), Defterim'de metinli "Çakışma" rozeti, karşılaştırma ekranı (telefonda alt alta, tablette yan yana; cihaz adı ve zaman), dört eylem; çözüm tek işlemdir. Farklar `diff` kitaplığının `diffWordsWithSpace` işleviyle kelime düzeyinde çıkarılır.
- Örnek 5 bildirimi ("Bu not başka bir cihazda düzenlendiği için geri getirildi") ve Örnek 4 önerisi ("Diğer cihazda: Bakara 255 · 2 saat önce").
- Ekran okuyucu etiketi, 44×44 pt hedefler; renk tek başına anlam taşımaz. Ekran görüntüsüyle denetim (`mobil-ekran`, `arayuz-denetcisi`).
- **Bitti sayılır:** bileşen testleri yeşil; Kâğıt ve Gece temasında ekran görüntüleri incelendi.

### A36.5 · Özellik tabanlı testler ve iki cihaz senaryoları
- `test-yazari`: sabit tohumlu üreteçle, özellik başına en az 1.000 rastgele işlem dizisi (öneri), iki dilde (TypeScript: `fast-check`, `fc.assert(özellik, { seed, numRuns: 1000 })`; .NET: `FsCheck.Xunit.v3`, `[Property(MaxTest = 1000)]` ve sabit tohum için `Replay`):
  1. Yakınsama: aynı işlem kümesi farklı sıralarla uygulanınca bütün kopyalar aynı duruma varır.
  2. İdempotentlik: aynı `op_id` iki kez uygulanınca durum ve `server_seq` değişmez.
  3. HLC tekdüzeliği: `tick` ve `recv` sonrası değer görülen her değerden büyüktür; cihaz saati geri alınsa da küçülmez.
  4. Not kaybı yok: iki tarafta değişen notta iki metin de korunur (asıl ve tek kopya, `conflict_of`); silme ile düzenleme yarışında düzenleme kazanır.
  5. Hatim işareti kaybolmaz: eşzamanlı işaretler korunur; silme yalnız gördüğü satırları kaldırır.
  6. `reading_position` çakışmaz: `(device_id, context)` başına tek satır.
  7. İmleç: sayfalı çekme her değişikliği tam bir kez verir.
- İki cihaz: C# bütünleşik testinde iki sanal istemci (HTTP) §4'teki beş örneği adıyla koşar. Gerçek iki cihazla (emülatör ve telefon, yerel API) bir elle tur yapılır ve sonucu kayda yazılır.
- **Bitti sayılır:** özellik ve senaryo testleri yeşil; tohumlar test çıktısında.

### A36.6 · Bağlantı oyları
- Sunucu (`sunucu-gelistirici`, `ef-goc`): `xref_vote(xref_id, account_hash, vote, reason, data_version, created_at)` A35'te seçilen kullanıcı veritabanındadır; `account_hash = HMAC-SHA256(sunucu sırrı, hesap kimliği)`, sır kullanıcı sırlarında durur ([Backend API](../../02-mimari/05-backend-api.md) §5; [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §7).
- `PUT /api/v1/xrefs/{id}/vote` (`{vote: up|down, reason?}`; nedenler `yanlis_ayet`, `iktibas_degil`, `kok_yanlis`, `alakasiz`) ve `DELETE`; hesap başına tek oy; hız sınırı hesap ve IP başına. Hesap silinince oylar silinir (A35 silme işi).
- Gece işi oyları editoryal veritabanındaki `xref.votes_up` ve `votes_down` sayaçlarına işler ve [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md) §12'deki Wilson eşikleriyle `review` satırı açar. Oy bağlantının durumunu kendiliğinden değiştirmez; karar editöründür. Etki sonraki paket sürümüyle cihaza ulaşır.
- Mobil (`mobil-gelistirici`): Bağlantılar panelinde satır menüsüne "Yararlı", "Yararsız" ve nedenli "Hata bildir"; yalnız hesap bağlıyken ve `hesapVeSenkron` açıkken görünür. Oy sayısı ve katkı sıralaması gösterilmez (K-25). Çevrimdışıyken menü devre dışıdır (öneri; başka bir yol `/karar` ister).
- **Bitti sayılır:** oy uçlarının bütünleşik testleri (tek oy, oyu geri alma, hesap silinince oyların silinmesi) ve gece işinin eşik testleri yeşil; menü ekran görüntüsüyle incelendi.

### A36.7 · Canlıya açılış (A35 listesiyle)
- Önkoşul: İ-20 (barındırma seçimi) tamam; A35.5'in canlıya açılış listesi ve [Gizlilik](../../07-yayin/02-gizlilik.md) §4 "Faz 4 öncesi" kontrol listesi kapalı. İ-20 tamam değilse yalnız bu adım bekler; A36.0–A36.6 sürer ve beklenen insan adımı ilerleme dosyasına yazılır.
- A35.5 listesi uygulanır. `hesapVeSenkron` önce `internal`, sonra yeni uygulama sürümüyle `public` için açılır (A34 yordamı).
- **Bitti sayılır:** canlı `/health/ready` HTTPS üzerinden 200; canlıda editör uçları 404; gerçek iki cihazla canlı senkron turu başarılı.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki sürümler paket kayıtlarıyla doğrulandı (A36.0); `fast-check`, `diff`, `FsCheck.Xunit.v3` ve `Microsoft.Extensions.TimeProvider.Testing` kilit dosyalarında sabit.
- [ ] `shared/test-vectors/sync/*.jsonl` TypeScript ve C#'ta yeşil; JSONL biçim denetimi geçiyor.
- [ ] Yedi özellik testi sabit tohumla yeşil; tohumlar raporda.
- [ ] §4'teki beş örnek sunucu ve istemci tarafında adlandırılmış senaryo testi olarak yeşil.
- [ ] Aynı `op_id` ile yeniden gönderimde sonuç aynı, `last_seq` değişmiyor; eşzamanlı yüklemelerde `server_seq` tekrarsız ve artan.
- [ ] `gc_seq` gerisindeki imleç 410 ve `imlec-eskidi` alıyor; tam eşitlemeden sonra istemcinin canlı satır kümesi sunucuyla aynı.
- [ ] 501 işlemli istek 400 alıyor.
- [ ] Altı ortak sütun testi ve `user.db` göç testleri yeşil; `outbox` ve `sync_state` yedek dosyasına girmiyor.
- [ ] A35 silme testi yeni `kullanici` tablolarını kapsayarak yeşil.
- [ ] Backend API §6 hata tablosunda `imlec-eskidi` var (`grep`).
- [ ] Oy uçları hesap başına tek oy yazıyor; `DELETE` oyu kaldırıyor; hesap silinince oylar siliniyor; gece işi bağlantı durumunu değiştirmeden `review` satırı açıyor (bütünleşik testler).
- [ ] Canlıya açılış yapıldıysa canlı sağlık ucu 200, editör ucu 404.

## Doğrulama
```bash
pnpm install --frozen-lockfile
grep -n -E '"(fast-check|diff)"' packages/reader-core/package.json apps/mobile/package.json   # A36.0 kitaplıkları
grep -n -E "FsCheck|TimeProvider.Testing" server/Directory.Packages.props
pnpm --filter @mutalaa/test-vectors build          # JSONL biçim denetimi
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test                 # user.db göç ve ortak sütun testleri dahil
dotnet test --solution server/Mutalaa.slnx
git diff --exit-code server/Mutalaa.Api/openapi
grep -n "imlec-eskidi" docs/02-mimari/05-backend-api.md
# Canlıya açılıştan sonra (A36.7)
curl -sSf "https://<api-alanı>/health/ready"
curl -s -o /dev/null -w "%{http_code}\n" "https://<api-alanı>/api/v1/sources"   # 404
```
PowerShell'de `curl` yerine `curl.exe` yazılır.

## Dikkat
- Birleştirmede `updated_at` kullanılmaz; sıra yalnız HLC'dir. HLC biçimi sabit genişliklidir ve değişmez; dizgi karşılaştırması ordinaldir.
- `uuid` `v7({ rng })` aynı milisaniyede üretilen kimlikleri sıralı vermez (üretim iç durumdan bağımsızdır); sıra yalnız HLC'dedir, kimlik benzersizliği sağlar.
- Kayıt bazında son yazan kazanır; alan bazında birleştirme yapılmaz (Örnek 1'in bilinen bedeli, K-16).
- Notta kullanıcının yazdığı metin hiçbir yolda kaybolmaz.
- Sunucu kayıt içeriğini işlemez, analiz etmez, günlüğe yazmaz; yalnız saklar ve eşler ([Gizlilik](../../07-yayin/02-gizlilik.md) §3.5). Günlükte not metni yok.
- Çapalar kalıcıdır; sunucu çapayı doğrular ama yeniden çapalamaz.
- Kültürden bağımsızlık: Domain testleri `tr-TR` kültüründe de geçer; zaman `timestamptz` ve UTC.

## İnsan adımları
- İ-20 · Barındırma seçimi: canlıya açılış (A36.7) bu adımın tamamlanmasına bağlıdır; yalnız A36.7 bekler. Gerçek iki cihazla elle senkron turu kullanıcıyla yapılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/sync/` (HLC, birleştirme, giden kutusu, döngü) ve testleri
- `apps/mobile/src/features/notebook/` ve `src/features/settings/` (çakışma ekranı, senkron ayarları); `src/db/` yazma yolu
- `server/Mutalaa.Domain/Sync/` (öneri), `server/Mutalaa.Infrastructure/` göçleri, `server/Mutalaa.Api/Endpoints/` senkron uçları, `openapi/v1.json`, `server/tests/`
- `shared/test-vectors/sync/hlc.jsonl`, `merge.jsonl` (öneri)
- Kitaplık kayıtları: `packages/reader-core/package.json` ve `apps/mobile/package.json` (`fast-check`, `diff`), `pnpm-lock.yaml`, `server/Directory.Packages.props` (`FsCheck.Xunit.v3`, `Microsoft.Extensions.TimeProvider.Testing`)
- Belge güncellemeleri: Backend API §6, Kullanıcı verisi ve senkron §8 ve §9 (KV maddeleri), karar defteri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A36-senkron.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A35](./A35-hesap-ve-gizlilik.md) · Sonraki: [A37](./A37-elmalili-tefsir-paketi.md)
