# A29 · Kütüphane ve Depolama yöneticisi

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-18](../../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `lisans-denetcisi` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `paket-yayini` · `lisans-kapisi` · `mobil-ekran` · **Tahmini oturum:** 4–5
> **Başlat:** `/asama A29`

## Amaç
K-18'deki Ayarlar › Depolama ekranını ve Kütüphane sekmesini kurar. Paketler duraklatılabilen ve varsayılan olarak yalnız Wi-Fi ile çalışan bir kuyrukla iner, sha256 ile doğrulanır, kendi sürüm klasörüne çökmeye dayanıklı biçimde kurulur ve tek dokunuşla silinir. Hafız sesleri hafız ve sure başına silinir; düşük depolama eşikleri, otomatik temizlik, açılış uzlaştırması ve manifest güncelleme bildirimi çalışır. Kütüphane yalnız derlemede görünen paketlerin bölümlerini gösterir.

## Okunacak belgeler
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): tamamı
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest alanları, §7 derleme türüne göre süzme, §8 cihazda yaşam döngüsü
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §5 durum tablosu, §6 veri erişimi, §10 görünürlük ve bayraklar, §11 hata türleri
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 rota ağacı (`kutuphane/*`, `ayarlar/depolama/*`), §3 Kütüphane ve Depolama satırları, §4 silme onayı
- [Ses sistemi](../../06-mobil/02-ses-sistemi.md): §5.2 `PACK_REMOVED`, §11 indirme ve önbellek, §12 hafız lisans kapısı
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §8 Depolama listesi ve lisans görünürlüğü, §9 "Depolama'da paket sil"

## Kapsam
**Yapılır**
- Kütüphane: A21'in yer tutucu rotaları doldurulur: `kutuphane/_layout.tsx`, `kutuphane/index.tsx`, `kutuphane/tefsir/index.tsx`, `kutuphane/hadis/index.tsx`, `kutuphane/risale/index.tsx`.
- Depolama: `ayarlar/depolama/index.tsx` ve paket ya da hafız ayrıntısı `ayarlar/depolama/[packId].tsx`.
- İndirme kuyruğu, bütünlük doğrulaması, atomik kurulum, açılıştaki tam uzlaştırma, silme, sabitleme, eşikler, otomatik temizlik ve manifest güncellemeleri (06-mobil/03 §1–§9; A23 kuyruğu ve tam uzlaştırmayı A29'a bırakır).
- Paket güncellendiğinde yeniden çapalama olayının yayımlanması.

**Yapılmaz**
- `device.db` şeması, `ContentDb`, `validatePack`, manifest istemcisi, imza doğrulaması, `isPackVisible` ve gömülü `core` içe aktarımı: A23.
- Hadis ve Risale içindeki gezinme ve okuyucular: A31. Tefsir okuyucusu: A24; tefsir içindekilerinin gerçek pakete bağlanması: A37. Ses çalma ve `PACK_REMOVED` işleyicisi: A27; burada yalnız olay gönderilir.
- Yeniden çapalama algoritması: A30. Arka planda indirme: v1.x (DY-4). iCloud yedeğinden dışlama: Açık soru (DY-5). Canlı içerik deposu: İ-18, A33 ve A34.

## Adımlar
### A29.1 · Önkoşul, doğrulamalar ve iki fark
- A23 çıktısını denetle: `src/db/device/schema.ts`, `src/db/content.ts` (`ContentDb`), `src/packs/validate.ts` (`validatePack`), `src/packs/manifest.ts`, `src/packs/visibility.ts`, `src/lib/network.ts`. A23.1'de doğrulanan `File.digest('SHA-256')` ve ağ modülü sonuçları okunur.
- `arastirmaci` kurulu SDK'nın resmî belgesinden doğrular: DY-9'un kalanı (`File.createDownloadTask`, `DownloadTask` üzerinde `pause`, `resumeAsync`, `savable`, `fromSavable`; aralık isteğiyle sürdürme), DY-8 (ölçülü Wi-Fi), DY-6 (`Paths.availableDiskSpace`). Yeni bağımlılık `npx expo install` ile kurulur; sonuçlar `/belge-esitle` ile işlenir.
- Manifest denetim aralığı belgelerde aynıdır: öne gelişte en çok 6 saatte bir (06-mobil/03 §8, 03-veri/03 §8). Paket silme de belgelerde eşitlendi (19 Ekim 2026): K-18, 06-mobil/03 §1.1, 01-urun/03 §4 ve 07-yayin/03 §9'a göre tek dokunuş, satırda "Silindi · Geri al"; onay yalnız toplu silmede ve başka paketi etkileyen silmede istenir.
- **Bitti sayılır:** Doğrulama sonuçları yazılı.

### A29.2 · Kütüphane sekmesi
- Katalog görünür paketlerden kurulur: Elmalılı tefsiri, Hadis (Tecrîd-i Sarîh, Kütüb-i Sitte), Risale-i Nur. Derlemede görünmeyen paketin bölümü listelenmez (01-urun/03 §3.1); ME-6 açık kalır.
- Eser kartı paket durum rozeti taşır (`StorageRow` durumları). `LicenseBadge` durum adını yalnız `dev`'de gösterir; `bekliyor` ve `ic_kullanim` içerikte "Yalnız ekip" şeridi (07-yayin/01 §3, öneri).
- Hiç isteğe bağlı paket yoksa: "Paketleri Depolama'dan indirebilirsin". Görünür ama kurulu olmayan pakette indirme kartı: boyut, ağ türü ve "Yalnız Wi-Fi" durumu.
- Giriş listeleri paketteki `unit.parent_path` ve `label` alanlarından kurulur; eser ve bölüm adı koda yazılmaz (öneri). Tefsir içindekiler A13'ün `tefsir-test-ornek` fikstürüyle sınanır. Risale metin paketi görünmüyorsa liste yalnız dizin kaynağının yapısal adlarıyla kurulur; ayrıntı A31'dedir.
- **Bitti sayılır:** `internal` bayrağıyla `bekliyor` paketin bölümü görünmüyor (RNTL; 07-yayin/03 §8); `dev` emülatör görüntüsü onaylı.

### A29.3 · Depolama ekranı
- Bölümler 06-mobil/03 §1 tablosundaki sırayla: kullanım çubuğu (Çekirdek, Metin, Mushaf, Ses, Önbellek; kategoriler yazıyla da), indirme ayarları (Yalnız Wi-Fi varsayılan açık, otomatik temizlik varsayılan kapalı; ikisi de MMKV'de), indirme kuyruğu (boşsa gizli), metin paketleri, Mushaf (30 cüz ızgarası; lisansla görünür), hafız sesleri, önbellek.
- Metinler §1.3 anahtar tablosundan i18n'e girer. Boyutlar 1000 tabanlı ve Türkçe biçimli ("12,4 MB"); son kullanım göreli ("dün", "3 gün önce", "hiç açılmadı").
- `core` satırı kilitli: "Uygulamayla gelir, silinemez." İndirilmiş bir `core` güncellemesi silinebilir; uygulama gömülü sürüme döner.
- Hafız ayrıntısında sure listesi, sure başına ve hafız başına silme.
- Erişilebilirlik: çubuk `accessibilityRole="progressbar"` ve yazılı değer taşır; her "Sil" etiketi paket adını ve boyutunu içerir; kuyruk ilerlemesi en çok %25'lik adımlarla duyurulur; bütün eylemler düğmedir.
- **Bitti sayılır:** Bileşen testleri yeşil; üç temada ekran görüntüleri `arayuz-denetcisi` onaylı.

### A29.4 · Kuyruk, doğrulama, kurulum ve uzlaştırma
- `download_job` durum makinesi 06-mobil/03 §4'teki durumları ve geçişleri birebir uygular. Sıra önce öncelik, sonra oluşturulma zamanı; aynı anda bir paket işi; ses işinde dosyalar üçerli paralel iner ve biten her dosya hemen `audio_file`'a yazılır.
- Yalnız Wi-Fi açıkken hücresel ağdaki iş `waiting_wifi` olur; "Hücresel veriyle indir" o işe `allow_cellular` verir ve boyutu gösterir. Wi-Fi'dan hücresele geçişte iş bekler, Wi-Fi gelince sürer.
- Duraklatmada ve arka plana geçişte `savable()` çıktısı `resume_data`'ya yazılır. Geri çekilme `nextRetryAt` ile (taban 5 s, tavan 10 dk, 6 deneme, ±%20 sapma); 404 ve 410 manifesti yeniler.
- Yer denetimi başlamadan önce ve her 10 MB'ta (§6): indirmeden sonra ≥ 1 GB sessiz; 300 MB–1 GB `storage.low.warn` onayı; < 300 MB engel ve temizlik önerisi; cihazda < 100 MB bütün işler `paused` (`storage`) ve "Notlarının kaydı için yer aç".
- Doğrulama (§5): `File.digest('SHA-256')` sonucu küçük harfli manifest değeriyle karşılaştırılır. Tutmazsa `.part` silinir ve iş sürdürmesiz baştan iner; ikinci kez tutmazsa manifest yenilenir, özet değiştiyse bir kez daha denenir, değişmediyse iş `failed` olur. Sentry'ye yalnız paket kimliği, sürüm ve bayt gider. Doğrulanmamış dosya ATTACH edilmez ve çalınmaz.
- Kurulum: A23'ün `validatePack()` denetimi → `packs/<paket>/<sürüm>/pack.db` → tek işlemde `installed_pack` ve iş `done` → eski şema DETACH, yenisi ATTACH → eski klasör silinir. Bir adım başarısızsa yeni dosya silinir, önceki sürüm etkin kalır (03-veri/03 §8 adım 6–7).
- Açılış uzlaştırması (06-mobil/03 §3) ilk kareden sonra boşta çalışır: dosyası olmayan paket `broken`; kaydı olmayan sürüm klasörü ve sahipsiz `.part` silinir; 7 günden uzun duraklatılmış işin yarım dosyası silinir; `running` işler `queued` olur; `pending_delete` paketler silinir; `audio_file` diskle eşlenir. Gömülü `core` maddesi A23'tedir.
- **Bitti sayılır:** Sahte dosya sistemi ve sahte indirme göreviyle birim testleri geri çekilmeyi, eşikleri, durum geçişlerini, iki kez tutmayan özeti, kurulum geri dönüşünü ve uzlaştırmanın her maddesini sınıyor.

### A29.5 · Silme, sabitleme ve otomatik temizlik
- "Sil"e tek dokunuş paketi `pending_delete` yapar; satır "Silindi · Geri al" olur ve "Geri al" ekrandan çıkılana kadar kalır (zamanlayıcı yok). Dosyalar ekrandan çıkınca ya da uygulama arka plana geçince silinir; önce ses `PACK_REMOVED` ile durur, metin paketi DETACH edilir; DETACH başarısızsa silme sonraki açılışa kalır.
- Onay yalnız toplu silmede ("Tüm indirmeleri sil", "Bu hafızın tüm sesleri") ve `depends_on` bağımlısı olan silmede istenir; pencere bağımlıları listeler.
- Sabitlenen paket ve hafız otomatik temizliğe ve yer önerilerine girmez; güncellemesi Wi-Fi'da kendiliğinden iner.
- Otomatik temizlik (§7): 30, 60 ya da 90 gün (varsayılan 90); günde en çok bir kez, ilk kareden sonra; sureyi bütün siler; sabitlenmiş hafızı, çalma kuyruğundaki âyetleri ve son 7 günde inenleri korur; sonucu ekrana yazar, bildirim göndermez.
- Not ya da vurgunun bağlı olduğu paket silinince kullanıcı kaydı silinmez (§9).
- **Bitti sayılır:** `test-kucuk` silinince satır "Silindi · Geri al" oluyor, ekrandan çıkınca Kütüphane "İndir" gösteriyor; otomatik temizlik seçim testi yeşil.

### A29.6 · Manifest güncellemeleri ve cihaz senaryoları
- A23'ün manifest istemcisi uygulama öne geldiğinde en çok 6 saatte bir (06-mobil/03 §8), ayrıca Depolama açılınca ve "Güncellemeleri denetle" ile çağrılır. Çevrimdışıyken "Son denetim: 3 gün önce" yazar.
- 06-mobil/03 §8 akışı: imza ve biçim → görünürlük (görünmez paket `disabled`, `license`; içerik gizlenir, ses durur, dosyalar silinmek üzere işaretlenir, `storage.licenseRemoved` bir kez) → yeni sürüm → `min_app_version` (`storage.needsApp`) → sabitli ve Wi-Fi ise kuyruk, değilse "Güncelle" ve rozet. `kurul_onay` değişince satır "Kurul onaylı yeni sürüm" der.
- Güncelleme kurulunca `onPackUpdated(packId, eskiSurum, yeniSurum)` olayı yayımlanır (öneri ad); A30'daki yeniden çapalama buna abone olur.
- Manifestten tamamen kalkan paket Açık soru (DY-3); öneri `public`'te devre dışı bırakmak, `/karar` ile netleşir. Yayınlayıcı `kapali` paketi manifeste hiç yazmadığı için lisans durumu değişimi sahte manifestle birim testinde sınanır.
- Cihaz senaryoları (§10): indirme ortasında uygulamayı öldürme, uçak modu, Wi-Fi'dan hücresele geçiş, küçük depolamalı emülatörde dolmak üzere disk, not bağlı paketi silip yeniden indirme. Emülatörde ağ, hız ve disk ayarı komutlarını `arastirmaci` doğrular. Bozuk dosya ve `min_app_version` senaryoları sahte manifest ve sahte indirmeyle Jest'te koşar. Duraklat ve sürdür en büyük `dev` paketiyle (ör. `core` güncellemesi ya da bir Mod A cüzü) denenir.
- `lisans-denetcisi` inceler: `kapali` ya da derlemede görünmeyen paket hiçbir ekranda listelenmiyor; `test-` önekli paketler `public` bayrağında görünmüyor.
- **Bitti sayılır:** Güncelleme bildirimi, `needsApp` ve lisans kaldırma testleri yeşil; cihaz senaryolarının sonuçları `.tmp/a29/cihaz.md` notunda.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; geri çekilme süreleri (yaklaşık 5, 10, 20, 40, 80, 160 s; altıncı denemeden sonra `failed`), dört eşik satırı, kuyruk geçişleri, otomatik temizlik seçimi, uzlaştırma ve görünürlük testleri bu aşamada eklendi.
- [ ] Özeti iki kez tutmayan iş `failed` oluyor ve dosya ATTACH edilmiyor; manifestteki özet değişince bir kez yeniden deneniyor (Jest).
- [ ] Emülatörde Depolama ekranı `dev` manifestindeki paketleri listeliyor (02-mimari/04 §6 madde 10); `core` satırı kilitli.
- [ ] Yalnız Wi-Fi açıkken hücresel ağda iş "Wi-Fi bekleniyor" oluyor; "Hücresel veriyle indir" işi başlatıyor (emülatör görüntüleri).
- [ ] Duraklatılıp sürdürülen işte inen bayt sıfırlanmıyor; uygulama öldürülüp açılınca iş `resume_data` ile sürüyor (DY-9 sonucuna göre; görüntü ve not).
- [ ] `test-kucuk` tek dokunuşla siliniyor, "Geri al" çalışıyor, ekrandan çıkınca Kütüphane "İndir" gösteriyor.
- [ ] Bir hafızın tek suresi ve bütün sesleri ayrı ayrı siliniyor; toplu silme onay istiyor; çalan ses `PACK_REMOVED` ile duruyor (`ses-test`).
- [ ] Yeni sürümlü manifest "Güncelleme var" rozetini ve `storage.update` metnini, yüksek `min_app_version` `storage.needsApp` metnini gösteriyor (Jest).
- [ ] `internal` ve `public` bayrağında `bekliyor` ve `ic_kullanim` paketler Kütüphane'de ve Depolama'da yok (RNTL); `lisans-denetcisi` raporu temiz.
- [ ] TalkBack ile Depolama ekranında çubuk değeri ve "Sil" etiketleri okunuyor (elle denetim, `.tmp/a29/cihaz.md`).

## Doğrulama
```bash
docker compose up -d && docker compose ps
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
pnpm --filter @mutalaa/mobile test
pnpm lint && pnpm typecheck
mkdir -p .tmp/a29
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/depolama"
adb exec-out screencap -p > .tmp/a29/depolama.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://kutuphane"
adb exec-out screencap -p > .tmp/a29/kutuphane.png
```

## Dikkat
- Paket görünürlüğü yalnız `isPackVisible` ile belirlenir; ekranlar kendi kuralını yazmaz (`lisans-kapisi`). `kapali` içerik hiçbir derlemede listelenmez.
- Kullanıcı verisi paket silinince silinmez; kayıtlar `label`, `excerpt` ve `content_hash` ile okunur kalır (03-veri/03 §8 madde 9).
- Silme kodu yalnız `packs/`, `audio/`, `tmp/` ve önbellek klasörlerini hedefler; önbellek temizliği kullanıcı verisine dokunmaz. Testte sahte dosya sistemi kullanılır.
- `dev` paket adresleri bilgisayarın LAN IP'sini taşır; emülatör de LAN IP kullanır. IP değişirse `Storage:PublicBaseUrl` güncellenir ve yeniden yayımlanır (02-mimari/04 §10.3; `windows-sorun`).
- Expo FileSystem API adları SDK'ya göre değişebilir; SDK 58'e geçildiyse A29.1 doğrulaması yinelenir.
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
