# A29 · Kütüphane ve Depolama yöneticisi

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-18](../../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `paket-yayini` · `mobil-ekran` · **Tahmini oturum:** 4–5
> **Başlat:** `/asama A29`

## Amaç
K-18'deki Ayarlar › Depolama ekranını ve Kütüphane sekmesini kurar. Paketler duraklatılabilen ve varsayılan olarak yalnız Wi-Fi ile çalışan bir kuyrukla iner, sha256 ile doğrulanır, kendi sürüm klasörüne çökmeye dayanıklı biçimde kurulur ve tek dokunuşla silinir. Okuyucu sesleri kayıt ve sure başına silinir; düşük depolama eşikleri, otomatik temizlik, açılış uzlaştırması ve manifest güncelleme bildirimi çalışır. Kütüphane yalnız derlemede görünen paketlerin bölümlerini gösterir.

## Okunacak belgeler
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): tamamı
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest alanları, §7 derleme türüne göre süzme, §8 cihazda yaşam döngüsü
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §5 durum tablosu, §6 veri erişimi, §10 derleme türleri ve özellik bayrakları, §11 hata türleri
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 rota ağacı (`kutuphane/*`, `ayarlar/depolama/*`), §3 Kütüphane ve Depolama satırları, §4 silme onayı
- [Ses sistemi](../../06-mobil/02-ses-sistemi.md): §5.2 `RECORDING_REMOVED`, §11 indirme ve önbellek, §12 kaynaklar, görünürlük ve atıf
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §8 Depolama listesi ve paket görünürlüğü, §9 "Depolama'da paket sil"
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): Mobil çatı, Ses ve Mobil durum satırları (SDK 58 sürümleri)

## Kapsam
**Yapılır**
- Kütüphane: A21'in yer tutucu rotaları doldurulur: `kutuphane/_layout.tsx`, `kutuphane/index.tsx`, `kutuphane/tefsir/index.tsx`, `kutuphane/hadis/index.tsx`, `kutuphane/risale/index.tsx`.
- Depolama: `ayarlar/depolama/index.tsx` ve paket ya da okuyucu kaydı ayrıntısı `ayarlar/depolama/[packId].tsx`.
- İndirme kuyruğu, bütünlük doğrulaması, atomik kurulum, açılıştaki tam uzlaştırma, silme, sabitleme, eşikler, otomatik temizlik ve manifest güncellemeleri (06-mobil/03 §1–§9; A23 kuyruğu ve tam uzlaştırmayı A29'a bırakır).
- Paket güncellendiğinde yeniden çapalama olayının yayımlanması.

**Yapılmaz**
- `device.db` şeması, `ContentDb`, `validatePack`, manifest istemcisi, imza doğrulaması, `isPackVisible` ve gömülü `core` içe aktarımı: A23.
- Hadis ve Risale içindeki gezinme ve okuyucular: A31. Tefsir okuyucusu: A24; tefsir içindekilerinin gerçek pakete bağlanması: A37. Ses çalma ve `RECORDING_REMOVED` işleyicisi: A27 (ses indirme işlerini de A27 üretir ve bu aşamanın kuyruğunu kullanır, ikinci kuyruk yazılmaz); burada yalnız olay gönderilir.
- Yeniden çapalama algoritması: A30. Arka planda indirme: v1.x (DY-4). iCloud yedeğinden dışlama: Açık soru (DY-5). Canlı içerik deposu: İ-18, A33 ve A34.

## Tedarik
Bu aşama içerik (metin, ses, görsel) almaz; yalnız kitaplık ve araç alır. Sürümler Expo SDK 58 hattındadır ve sabitlenir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)). Ölçümler 2 Kasım 2026'dadır: npm kaydı, `bundledNativeModules.json` (git `expo/expo` dalı `sdk-58`) ve npm arşivlerinin kaynağı (bütünlük özeti npm kaydıyla tuttu). Ölçülmeyen hücre A29.0'da ölçülür.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| İndirme görevi (duraklat, sürdür, kaydet), dosya yolları, taşıma ve silme, boş disk alanı, dosya SHA-256 özeti | `expo-file-system` 58.0.13 (npm `latest`; Expo SDK 58 `bundledNativeModules.json` `~58.0.13`; npm arşivi 8.613.075 bayt, SHA-256 `820d4af9889f3906b78d70d11533a4a4b2bb3099397d69cb1957273e220cb7d7`; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/filesystem/) HTTP 200; biçim: npm paketi, TypeScript tipleri, Kotlin ve Swift kaynağı, Jest maketi) | `npx expo install expo-file-system` (A23.1'de kurulduysa yeniden kurulmaz; sürümü `expo` belirler); `pnpm-lock.yaml` | Ölçüldü (paket kaynağı): `File.createDownloadTask(url, hedef, seçenekler)` görevi başlatmadan döndürür; `DownloadTask` durumları `idle`, `active`, `paused`, `completed`, `cancelled`, `error`; `pause()` ve `pauseAsync()` yalnız `active` durumunda, `resumeAsync()` ve `savable()` yalnız `paused` durumunda çalışır; `savable()` `{ url, fileUri, isDirectory, headers, resumeData }` verir, `DownloadTask.fromSavable(durum, seçenekler)` `resumeData` yoksa hata verir; `File.digest('SHA-256')` (58.0.0'dan; MD5, SHA-1, SHA-256, SHA-384, SHA-512); `Paths.document`, `Paths.cache`, `Paths.availableDiskSpace`, `Paths.totalDiskSpace`; `File.move`, `copy`, `delete`. Android sürdürmesi `Range: bytes=N-` gönderir, `If-Range` göndermez; sunucunun 206 yerine 200 dönmesi görevde ayrıca ele alınır (`isPartial`). iOS'ta `sessionType` varsayılanı `background`. iOS'ta `Paths.availableDiskSpace` `systemFreeSize` okur; Android'de 58.0.11'den beri uygulamanın kullanabileceği alanı verir | Eski API `expo-file-system/legacy` (pakette `./legacy` dışa aktarımı var; `DownloadResumable`); arka planda indirme için (v1.x, DY-4) `@kesha-antonov/react-native-background-downloader` 4.7.0 (npm, 31 Ekim 2026 güncellendi) |
| Ağ türü (Wi-Fi, hücresel) ve çevrimiçi durumu | `expo-network` 58.0.4 (A23.1 seçimi; npm `latest`; `bundledNativeModules.json` `~58.0.4`; npm arşivi 47.353 bayt, SHA-256 `a0e4c3bc6e0cb4b7ef9643b6ee33e979c6633d6ac67a2bf8eba3bf99ba505736`; [belge](https://docs.expo.dev/versions/v58.0.0/sdk/network/) HTTP 200) | A23.1'de kurulur; bu aşama yeniden eklemez | Ölçüldü (paket kaynağı): `getNetworkStateAsync`, `addNetworkStateListener`, `useNetworkState`; `NetworkState` alanları `type`, `isConnected`, `isInternetReachable`; `NetworkStateType` değerleri `NONE`, `UNKNOWN`, `CELLULAR`, `WIFI`, `BLUETOOTH`, `ETHERNET`, `WIMAX`, `VPN`, `OTHER`; ölçülü bağlantı alanı yok | `@react-native-community/netinfo` 12.0.1 (sonraki satır) |
| Ölçülü bağlantı bilgisi (telefonun erişim noktası gibi ölçülü Wi-Fi; DY-8) | `@react-native-community/netinfo` 12.0.1 (npm `latest`; `bundledNativeModules.json` `12.0.1`; npm arşivi 140.017 bayt, SHA-256 `2f7de0df879f66281b537a8b64b7ba2039fe9cd6d3da3e43b32f6ce44df58bed`; eş bağımlılık `react-native >=0.59`) | `npx expo install @react-native-community/netinfo` (A29.0); sargı `src/lib/network.ts` | Ölçüldü (paket kaynağı): `details.isConnectionExpensive` (`src/internal/types.ts`); Android'de `isActiveNetworkMetered` ile dolar (`ConnectivityReceiver.java`); iOS'ta `RNCConnectionState.m` içindeki `expensive` alanı (hesaplanışı A29.0'da ölçülür) | Ölçülü bilgisi olmadan yalnız `expo-network` `WIFI` türü (ölçülü Wi-Fi serbest sayılır) |
| "Yalnız Wi-Fi" ve otomatik temizlik ayarları, son geçerli manifest kopyası | `react-native-mmkv` 4.3.2 (npm `latest`; eş bağımlılık `react-native-nitro-modules`) | A21'de kurulur; bu aşama yeni kitaplık eklemez | Ölçüldü: npm `latest` = 4.3.2 (A21 satırıyla aynı) | `expo-sqlite/kv-store` (`expo-sqlite` ile gelir) |
| `installed_pack`, `download_job` ve `audio_file` tabloları (`device.db`) | `expo-sqlite` 58.0.15 (npm `latest`; `bundledNativeModules.json` `~58.0.15`) ve `drizzle-orm` 0.45.4 (A23 şeması) | A23'te kurulur; bu aşama yeni kitaplık eklemez | Ölçüldü: sürümler A23 satırıyla aynı | — |
| Hata izleme (yalnız paket kimliği, sürüm ve bayt) | `@sentry/react-native` 8.33.0 (A21 seçimi) | A21'de kurulur; bu aşama yeni kitaplık eklemez | A21 satırı | — |
| Birim ve bileşen testleri; sahte dosya sistemi | `jest-expo` 58.0.13 (npm `latest`; A21'de `~58.0.13`; arşiv 32.995 bayt, SHA-256 `36a61f8e1ef7b500e728935e966ef0aaedf3014c734ee4fd304eb1bcea437e84`), `jest` 30.5.2, `@testing-library/react-native` 14.1.0 (A21 seçimi) ve `expo-file-system` 58.0.13 ile gelen Jest maketi `mocks/FileSystem.ts` | A21'de kurulur; maket `expo-file-system` ile gelir | Ölçüldü (paket kaynağı): maket `File`, `Directory` ve `Paths` için bellekte dosya sistemi kurar (oluştur, yaz, oku, taşı, kopyala, sil); `documentDirectory` `file:///mock/document/`, `availableDiskSpace` 500.000.000, `totalDiskSpace` 1.000.000.000; `jest-expo` ön ayarı onu yerel modülün yerine koyar. Sınırı: `digest` gerçek SHA-256 değildir (`fakeDigest`, yol ve boyuttan üretilen sahte dizi); `FileSystemDownloadTask` taslaktır (bayt yazmaz, `start` sabit yol döndürür, `pause` sabit `resumeData` verir) | Kendi bellek içi dosya sistemimiz (Map); `memfs` 4.80.0 (Node `fs` için; `expo-file-system` sınıflarına uymaz, seçilmedi) |
| Emülatörde ağ ve disk koşulları (kullanıcı denemesi) | Android Emülatör konsolu ([belge](https://developer.android.com/studio/run/emulator-console) HTTP 200: `network speed`, `network delay`, `network status`) ve komut satırı seçenekleri ([belge](https://developer.android.com/studio/run/emulator-commandline) HTTP 200: `-netspeed`, `-netdelay`, `-partition-size`, `-no-snapshot`); `adb` (Android SDK Platform-Tools, A00) | A00 ortamı; kurulum yok | Ölçüldü: iki sayfa açıldı, komut adları sayfalarda geçiyor; uçak modu ve Wi-Fi kapatma komutları A29.0'da `arastirmaci` ile doğrulanır | Gerçek Android cihaz |
| İndirilecek paketler ve sesler (kuyruğun beslendiği veri) | Bu aşama dışarıdan içerik almaz: `dev` manifesti, `test-kucuk` paketi ve `ses-test` A13 ve A27 çıktısıdır; yerel S3 deposu A03'te kurulur (`http://localhost:8333/mutalaa/dev/manifest.json`) | A13 Yayınlayıcı (`dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev`) | A13 ve A27 kabul ölçütleri | — |

Kendimiz yapacağımız işler: `download_job` durum makinesi, sıra, geri çekilme ve eşikler; bütünlük doğrulaması ve atomik kurulum; açılış uzlaştırması; silme, sabitleme ve otomatik temizlik; manifest güncelleme akışı ve `onPackUpdated` olayı; Kütüphane ve Depolama ekranları; sahte indirme görevi ve gerçek SHA-256 hesaplayan test yardımcısı. Hazır karşılıkları yoktur: işler `device.db` şemasına ve paket sözleşmesine özeldir. Bellek içi kuyruk kitaplıkları (`p-queue` 10.0.0, `p-limit` 7.3.3, `p-retry` 8.0.1) kalıcı iş tablosunu, Wi-Fi beklemeyi ve özet doğrulamasını karşılamadığı için alınmaz.

## Adımlar
### A29.0 · Tedarik doğrulaması ve indirme
- `## Tedarik` tablosundaki sürümlerin güncel olduğunu `arastirmaci` ile doğrula: `expo-file-system`, `expo-network` ve `@react-native-community/netinfo` için npm kaydı ile `expo` 58.x `bundledNativeModules.json` eşleşmeli; üç belge adresi (Expo FileSystem ve Network v58.0.0, Android Emülatör konsolu) HTTP 200 vermeli. Açılmayan adresin yerine yedek adayı kullan.
- Kitaplıkları paket kaydından doğrula ve kur: `pnpm --filter @mutalaa/mobile exec expo install expo-file-system expo-network @react-native-community/netinfo` (A23.1'de kurulanlar yeniden kurulmaz). `pnpm-lock.yaml` sürümleri tablodakilerle aynı olmalı ve `expo install --check` hatasız bitmeli.
- Ölçülmeyen hücreleri doldur: netinfo'nun iOS `expensive` hesabı, uçak modu ve Wi-Fi kapatma komutları. `jest-expo` maketinin kapsamı kurulu sürümde yinelenir.
- Bu aşama içerik dosyası almaz: `data/gelen/` altına dosya inmez ve `pipeline/sources/` altına kayıt açılmaz.
- **Bitti sayılır:** Tablodaki her sürüm npm kaydı ve `pnpm-lock.yaml` ile eşleşiyor; ölçülmeyen hücre kalmadı; `expo install --check` hatasız.

### A29.1 · Önkoşul, doğrulamalar ve iki fark
- A23 çıktısını denetle: `src/db/device/schema.ts`, `src/db/content.ts` (`ContentDb`), `src/packs/validate.ts` (`validatePack`), `src/packs/manifest.ts`, `src/packs/visibility.ts`, `src/lib/network.ts`. A23.1'de doğrulanan `File.digest('SHA-256')` ve ağ modülü sonuçları okunur.
- `arastirmaci` kurulu SDK'nın resmî belgesinden ve paket kaynağından doğrular: DY-9'un kalanı (`File.createDownloadTask`, `DownloadTask` üzerinde `pause`, `pauseAsync`, `resumeAsync`, `savable`, `fromSavable`; aralık isteğiyle sürdürme), DY-8 (ölçülü Wi-Fi), DY-6 (`Paths.availableDiskSpace`). Ön ölçüm (2 Kasım 2026, `expo-file-system` 58.0.13): `savable()` yalnız `paused` durumunda çağrılır ve `resumeData` ister, bu yüzden `resume_data` yazmadan önce `pauseAsync()` beklenir; veri gelmeden duraklatılan işte `resumeData` yoktur ve iş baştan iner; Android `resumeData` olarak diskteki bayt sayısını verir ve sürdürmede `Range: bytes=N-` gönderir (`If-Range` yok); iOS'ta `Paths.availableDiskSpace` `systemFreeSize` okur ve Ayarlar uygulamasındaki değerden farklı olabilir. DY-8 için netinfo 12.0.1 `details.isConnectionExpensive` ile ölçülü bağlantı hücresel gibi sayılır (öneri). Yeni bağımlılık `npx expo install` ile kurulur (A29.0); sonuçlar `/belge-esitle` ile Depolama yöneticisi DY-6, DY-8 ve DY-9 satırlarına işlenir.
- Manifest denetim aralığı belgelerde aynıdır: öne gelişte en çok 6 saatte bir (06-mobil/03 §8, 03-veri/03 §8). Paket silme de belgelerde eşitlendi (19 Ekim 2026): K-18, 06-mobil/03 §1.1, 01-urun/03 §4 ve 07-yayin/03 §9'a göre tek dokunuş, satırda "Silindi · Geri al"; onay yalnız toplu silmede ve başka paketi etkileyen silmede istenir.
- **Bitti sayılır:** Doğrulama sonuçları yazılı.

### A29.2 · Kütüphane sekmesi
- Katalog görünür paketlerden kurulur: Elmalılı tefsiri, Hadis (Tecrîd-i Sarîh, Kütüb-i Sitte), Risale-i Nur. Derlemede görünmeyen paketin bölümü listelenmez (01-urun/03 §3.1).
- Eser kartı paket durum rozeti taşır (`StorageRow` durumları).
- Hiç isteğe bağlı paket yoksa: "Paketleri Depolama'dan indirebilirsin". Görünür ama kurulu olmayan pakette indirme kartı: boyut, ağ türü ve "Yalnız Wi-Fi" durumu.
- Giriş listeleri paketteki `unit.parent_path` ve `label` alanlarından kurulur; eser ve bölüm adı koda yazılmaz (öneri). Tefsir içindekiler A13'ün `tefsir-test-ornek` fikstürüyle sınanır. Risale-i Nur listesi `risale-dizin` ve `risale-{kitap}` paketlerinin yapısal alanlarından kurulur (A20 çıktısı); ayrıntı A31'dedir.
- **Bitti sayılır:** `public` bayrağıyla `test-` önekli kaynaklı paketin bölümü görünmüyor, `internal` bayrağıyla yalnız `test-kucuk` ve `test-ses` kaynaklı paketler görünüyor (RNTL; 07-yayin/03 §8); `dev` emülatör görüntüsü onaylı.

### A29.3 · Depolama ekranı
- Bölümler 06-mobil/03 §1 tablosundaki sırayla: kullanım çubuğu (Çekirdek, Metin, Mushaf, Ses, Önbellek; kategoriler yazıyla da), indirme ayarları (Yalnız Wi-Fi varsayılan açık, otomatik temizlik varsayılan kapalı; ikisi de MMKV'de), indirme kuyruğu (boşsa gizli), metin paketleri, Mushaf (30 cüz ızgarası; paket manifestte varsa görünür), hafız sesleri, önbellek.
- Metinler §1.3 anahtar tablosundan i18n'e girer. Boyutlar 1000 tabanlı ve Türkçe biçimli ("12,4 MB"); son kullanım göreli ("dün", "3 gün önce", "hiç açılmadı").
- `core` satırı kilitli: "Uygulamayla gelir, silinemez." İndirilmiş bir `core` güncellemesi silinebilir; uygulama gömülü sürüme döner.
- Okuyucu kaydı ayrıntısında sure listesi, sure başına ve kayıt başına silme ve "Bütün Kur'an'ı indir" (iş kapsamı `{"kayit": …, "sure": n}` ya da `{"kayit": …, "tum": true}`; `audio_file` anahtarı `(kayit, sure, dosya_surumu)`).
- Erişilebilirlik: çubuk `accessibilityRole="progressbar"` ve yazılı değer taşır; her "Sil" etiketi paket adını ve boyutunu içerir; kuyruk ilerlemesi en çok %25'lik adımlarla duyurulur; bütün eylemler düğmedir.
- **Bitti sayılır:** Bileşen testleri yeşil; üç temada ekran görüntüleri `arayuz-denetcisi` onaylı.

### A29.4 · Kuyruk, doğrulama, kurulum ve uzlaştırma
- `download_job` durum makinesi 06-mobil/03 §4'teki durumları ve geçişleri birebir uygular. Sıra önce öncelik, sonra oluşturulma zamanı; aynı anda bir paket işi; ses işinde dosyalar üçerli paralel iner ve biten her dosya hemen `audio_file`'a yazılır.
- Yalnız Wi-Fi açıkken hücresel ağdaki iş `waiting_wifi` olur; "Hücresel veriyle indir" o işe `allow_cellular` verir ve boyutu gösterir. Wi-Fi'dan hücresele geçişte iş bekler, Wi-Fi gelince sürer.
- Duraklatmada ve arka plana geçişte `pauseAsync()` beklenir, sonra `savable()` çıktısı `resume_data`'ya yazılır; `resumeData` yoksa iş sürdürmesiz baştan iner. Geri çekilme `nextRetryAt` ile (taban 5 s, tavan 10 dk, 6 deneme, ±%20 sapma); 404 ve 410 manifesti yeniler.
- Yer denetimi başlamadan önce ve her 10 MB'ta (§6): indirmeden sonra ≥ 1 GB sessiz; 300 MB–1 GB `storage.low.warn` onayı; < 300 MB engel ve temizlik önerisi; cihazda < 100 MB bütün işler `paused` (`storage`) ve "Notlarının kaydı için yer aç".
- Doğrulama (§5): `File.digest('SHA-256')` sonucu küçük harfli manifest değeriyle karşılaştırılır. Tutmazsa `.part` silinir ve iş sürdürmesiz baştan iner; ikinci kez tutmazsa manifest yenilenir, özet değiştiyse bir kez daha denenir, değişmediyse iş `failed` olur. Sentry'ye yalnız paket kimliği, sürüm ve bayt gider. Doğrulanmamış dosya ATTACH edilmez ve çalınmaz.
- Kurulum: A23'ün `validatePack()` denetimi → `packs/<paket>/<sürüm>/pack.db` → tek işlemde `installed_pack` ve iş `done` → eski şema DETACH, yenisi ATTACH → eski klasör silinir. Bir adım başarısızsa yeni dosya silinir, önceki sürüm etkin kalır (03-veri/03 §8 adım 6–7).
- Açılış uzlaştırması (06-mobil/03 §3) ilk kareden sonra boşta çalışır: dosyası olmayan paket `broken`; kaydı olmayan sürüm klasörü ve sahipsiz `.part` silinir; 7 günden uzun duraklatılmış işin yarım dosyası silinir; `running` işler `queued` olur; `pending_delete` paketler silinir; `audio_file` diskle eşlenir. Gömülü `core` maddesi A23'tedir.
- **Bitti sayılır:** `expo-file-system` Jest maketi (bellek içi dosya sistemi), gerçek SHA-256 hesaplayan test yardımcısı ve sahte indirme göreviyle birim testleri geri çekilmeyi, eşikleri, durum geçişlerini, iki kez tutmayan özeti, kurulum geri dönüşünü ve uzlaştırmanın her maddesini sınıyor.

### A29.5 · Silme, sabitleme ve otomatik temizlik
- "Sil"e tek dokunuş paketi `pending_delete` yapar; satır "Silindi · Geri al" olur ve "Geri al" ekrandan çıkılana kadar kalır (zamanlayıcı yok). Dosyalar ekrandan çıkınca ya da uygulama arka plana geçince silinir; önce ses `RECORDING_REMOVED` ile durur, metin paketi DETACH edilir; DETACH başarısızsa silme sonraki açılışa kalır.
- Onay yalnız toplu silmede ("Tüm indirmeleri sil", "Bu kaydın tüm sesleri") ve `depends_on` bağımlısı olan silmede istenir; pencere bağımlıları listeler.
- Sabitlenen paket ve kayıt otomatik temizliğe ve yer önerilerine girmez; güncellemesi Wi-Fi'da kendiliğinden iner.
- Otomatik temizlik (§7): 30, 60 ya da 90 gün (varsayılan 90); günde en çok bir kez, ilk kareden sonra; sureyi bütün siler; sabitlenmiş kaydı, çalınan sureyi ve son 7 günde inenleri korur; sonucu ekrana yazar, bildirim göndermez.
- Not ya da vurgunun bağlı olduğu paket silinince kullanıcı kaydı silinmez (§9).
- **Bitti sayılır:** `test-kucuk` silinince satır "Silindi · Geri al" oluyor, ekrandan çıkınca Kütüphane "İndir" gösteriyor; otomatik temizlik seçim testi yeşil.

### A29.6 · Manifest güncellemeleri ve cihaz senaryoları
- A23'ün manifest istemcisi uygulama öne geldiğinde en çok 6 saatte bir (06-mobil/03 §8), ayrıca Depolama açılınca ve "Güncellemeleri denetle" ile çağrılır. Çevrimdışıyken "Son denetim: 3 gün önce" yazar.
- 06-mobil/03 §8 akışı: imza ve biçim → manifestte var mı (kalkan paket `disabled`, `not_visible`; içerik gizlenir, ses durur, dosyalar silinmek üzere işaretlenir, `storage.notVisible` bir kez) → yeni sürüm → `min_app_version` (`storage.needsApp`) → sabitli ve Wi-Fi ise kuyruk, değilse "Güncelle" ve rozet.
- Güncelleme kurulunca `onPackUpdated(packId, eskiSurum, yeniSurum)` olayı yayımlanır (öneri ad); A30'daki yeniden çapalama buna abone olur.
- Manifestten tamamen kalkan paket Açık soru (DY-3); öneri `public`'te devre dışı bırakmak, `/karar` ile netleşir. Yayınlayıcı kaynak kaydı olmayan içeriği hiçbir pakete yazmadığı için (P-01) paketin manifestten kalkması sahte manifestle birim testinde sınanır. İndirilen paketin uygulamadaki ikinci kontrolü (`pack_meta.flavor` ve `test-` önekli kaynak, P-12) geçmezse paket kurulmaz ve iş `not_visible` ile biter (06-mobil/03 §5); bu da aynı testte sınanır.
- Cihaz senaryoları (§10): indirme ortasında uygulamayı öldürme, uçak modu, Wi-Fi'dan hücresele geçiş, küçük depolamalı emülatörde dolmak üzere disk, not bağlı paketi silip yeniden indirme. Emülatörde ağ, hız ve disk ayarı komutlarını `arastirmaci` doğrular. Bozuk dosya ve `min_app_version` senaryoları sahte manifest ve sahte indirmeyle Jest'te koşar. Duraklat ve sürdür en büyük `dev` paketiyle (ör. `core` güncellemesi ya da bir Mod A cüzü) denenir.
- `inceleyici` inceler: paket görünürlüğü yalnız `isPackVisible` ile belirleniyor; derlemede görünmeyen paket hiçbir ekranda listelenmiyor; `test-` önekli kaynaklı paketler `public` bayrağında, `test-kucuk` ve `test-ses` dışındakiler `internal` bayrağında görünmüyor (P-12).
- **Bitti sayılır:** Güncelleme bildirimi, `needsApp` ve `not_visible` (kalkan paket, geçmeyen ikinci kontrol) testleri yeşil; cihaz senaryolarının sonuçları `.tmp/a29/cihaz.md` notunda.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; geri çekilme süreleri (yaklaşık 5, 10, 20, 40, 80, 160 s; altıncı denemeden sonra `failed`), dört eşik satırı, kuyruk geçişleri, otomatik temizlik seçimi, uzlaştırma ve görünürlük testleri bu aşamada eklendi.
- [ ] Tedarik tablosundaki sürümler `pnpm-lock.yaml` ve npm kaydıyla eşleşiyor; `expo install --check` hatasız (A29.0).
- [ ] Özeti iki kez tutmayan iş `failed` oluyor ve dosya ATTACH edilmiyor; manifestteki özet değişince bir kez yeniden deneniyor (Jest).
- [ ] Emülatörde Depolama ekranı `dev` manifestindeki paketleri listeliyor (02-mimari/04 §6 madde 10); `core` satırı kilitli.
- [ ] Yalnız Wi-Fi açıkken hücresel ağda iş "Wi-Fi bekleniyor" oluyor; "Hücresel veriyle indir" işi başlatıyor (emülatör görüntüleri).
- [ ] Duraklatılıp sürdürülen işte inen bayt sıfırlanmıyor; uygulama öldürülüp açılınca iş `resume_data` ile sürüyor (DY-9 sonucuna göre; görüntü ve not).
- [ ] `test-kucuk` tek dokunuşla siliniyor, "Geri al" çalışıyor, ekrandan çıkınca Kütüphane "İndir" gösteriyor.
- [ ] Bir kaydın tek suresi ve bütün sesleri ayrı ayrı siliniyor; toplu silme onay istiyor; çalan ses `RECORDING_REMOVED` ile duruyor (`ses-test`).
- [ ] Yeni sürümlü manifest "Güncelleme var" rozetini ve `storage.update` metnini, yüksek `min_app_version` `storage.needsApp` metnini gösteriyor (Jest).
- [ ] `public` bayrağında `test-` önekli kaynaklı paket, `internal` bayrağında `test-kucuk` ve `test-ses` dışında `test-` önekli kaynaklı paket Kütüphane'de ve Depolama'da yok (RNTL); `inceleyici` raporu temiz.
- [ ] TalkBack ile Depolama ekranında çubuk değeri ve "Sil" etiketleri okunuyor (elle denetim, `.tmp/a29/cihaz.md`).

## Doğrulama
```bash
docker compose up -d && docker compose ps
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
pnpm --filter @mutalaa/mobile exec expo install --check
pnpm --filter @mutalaa/mobile test
pnpm lint && pnpm typecheck
mkdir -p .tmp/a29
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/depolama"
adb exec-out screencap -p > .tmp/a29/depolama.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://kutuphane"
adb exec-out screencap -p > .tmp/a29/kutuphane.png
```

## Dikkat
- Paket görünürlüğü yalnız `isPackVisible` ile belirlenir; ekranlar kendi kuralını yazmaz (`paket-yayini`, 06-mobil/01 §10). Derlemede görünmeyen paket hiçbir ekranda listelenmez.
- Kullanıcı verisi paket silinince silinmez; kayıtlar `label`, `excerpt` ve `content_hash` ile okunur kalır (03-veri/03 §8 madde 9).
- Silme kodu yalnız `packs/`, `audio/`, `tmp/` ve önbellek klasörlerini hedefler; önbellek temizliği kullanıcı verisine dokunmaz. Testte `expo-file-system` Jest maketi (bellek içi dosya sistemi) kullanılır.
- `dev` paket adresleri bilgisayarın LAN IP'sini taşır; emülatör de LAN IP kullanır. IP değişirse `Storage:PublicBaseUrl` güncellenir ve yeniden yayımlanır (02-mimari/04 §10.3; `windows-sorun`).
- Expo FileSystem API adları SDK'ya göre değişebilir; sürüm `~58.0.13` olarak sabittir, SDK değişirse A29.0 ve A29.1 doğrulaması yinelenir. Android'de `Paths.availableDiskSpace` 58.0.11'den önce sistemin ayırdığı alanı da sayıyordu; eşik testleri bu sürümle yazılır.
- Sentry olayına paket kimliği, sürüm ve bayt dışında alan girmez (06-mobil/01 §12).
- Commit kapsamı: `mobile`.

## İnsan adımları
- Yok. `internal` derlemenin paket indirebilmesi için gereken canlı depo (İ-18) A33 ve A34'te ele alınır.

## Çıktılar
- `apps/mobile/app/(tabs)/kutuphane/` (`_layout.tsx`, `index.tsx`, `tefsir/index.tsx`, `hadis/index.tsx`, `risale/index.tsx`)
- `apps/mobile/app/(tabs)/ayarlar/depolama/index.tsx`, `[packId].tsx`
- `apps/mobile/src/features/storage/` (ekran, kuyruk, eşikler, otomatik temizlik, uzlaştırma), `apps/mobile/src/features/library/`
- `apps/mobile/src/packs/` (indirme, kurulum, güncelleme, olay yayını), i18n anahtarları, testler; `.tmp/a29/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A29-kutuphane-ve-depolama.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A28](./A28-arama-ekrani.md) · Sonraki: [A30](./A30-defterim-ve-ilerleme.md)
