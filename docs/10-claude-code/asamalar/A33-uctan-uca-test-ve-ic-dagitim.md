# A33 · Uçtan uca testler, performans, iç dağıtım

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji)
> **Faz:** 2 · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A25](./A25-secim-kelime-karti-baglantilar.md) · [A26](./A26-mushaf-a.md) · [A27](./A27-ses-sistemi.md) · [A28](./A28-arama-ekrani.md) · [A29](./A29-kutuphane-ve-depolama.md) · [A30](./A30-defterim-ve-ilerleme.md) · [A31](./A31-hadis-ve-risale-okuyuculari.md) · [A32](./A32-ayarlar-erisilebilirlik-oz-test.md) · **İnsan adımı:** İ-21
> **Ajanlar:** `test-yazari` · `arayuz-denetcisi` · `arastirmaci` · `mobil-gelistirici` · `inceleyici` · `belge-bekcisi` · **Beceriler:** `mobil-ekran` · `paket-yayini` · `windows-sorun` · **Tahmini oturum:** 3–5
> **Başlat:** `/asama A33`

## Amaç
Faz 2'nin çıkış ölçütlerini kanıtlar: Test stratejisi §9'daki Maestro akışları yazılır, §10'daki performans ölçümleri ve §11'deki erişilebilirlik denetimleri hazırlanıp ölçülür; B-01…B-04 ve B-07…B-13 için durum tablosu çıkar. `internal` derleme EAS iç dağıtımıyla ekip cihazlarına ve davetli dış test kullanıcılarına gider. Sonuçlar A34'ün girdisidir.

## Okunacak belgeler
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 kullanıcı veritabanı göç testleri, §8–§11, §12 CI düzeni, §13 sürüm kontrol listesi, §14 açık sorular
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §2.1 derleme türleri, §8 başarı ölçütleri (B-01…B-04, B-07…B-13), §9 AS-08, AS-09
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 2 çıkış ölçütleri
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §9 bütçeler, §10 derleme türleri ve `isPackVisible`
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları, §5 yapıt taraması, §7 yayın adımları
- [Arama (FTS5)](../../03-veri/05-arama-fts5.md): §6 ölçüm ve bütçe aşılırsa
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §9 erişilebilirlik kontrol listesi
- [Gizlilik](../../07-yayin/02-gizlilik.md): §4 kontrol listeleri (verilerimi sil ve dışa aktar)
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §1 iOS notu, §6 madde 8 ve HTTPS kuralı
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §1 (Maestro ve EAS satırları)
- [Belge çelişkileri](../07-belge-celiskileri.md): BÇ-14 (ölçüm derlemesi), BÇ-15 (iOS'ta Maestro)

## Kapsam
**Yapılır**
- Maestro akışlarının yazımı ve sözdizimi denetimi. Klasör `apps/mobile/e2e/` (Proje yapısı §1; Test stratejisi §9); Maestro Teknoloji yığını §1'dedir. Akışları emülatörde ya da cihazda koşmayı kullanıcı yapar (CLAUDE.md çalışma düzeni 3).
- Performans ölçüm düzeni: Flashlight ve `adb` komutları, kıyas ekranına kelime kartı ve Bağlantılar ilk sonuç süresinin eklenmesi, rapor şablonu. Referans cihazda ölçümü kullanıcı koşar.
- Erişilebilirlik: kontrast testi, tarayıcılar, elle kontrol listesi (kullanıcıyla).
- B tablosu ve ölçüm raporu.
- `internal` EAS derlemesi, ekip içi dağıtım ve dış test kullanıcılarının daveti.

**Yapılmaz**
- `public` derleme ve mağaza hazırlığı: A34. `eas submit` hiç çalıştırılmaz.
- B-03 ve B-04 altın set ölçümleri: A18; raporları tabloya alınır.
- Bulunan büyük hatalar ilgili aşamanın işidir; küçük düzeltmeler burada `fix(mobile)` commitleriyle yapılır.

## Tedarik
Bu bölüm A33.0'da doğrulanır; ölçülmeyen hücreler "A33.0'da ölçülür" diye durur.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Uçtan uca test aracı | Maestro CLI: [mobile-dev-inc/maestro](https://github.com/mobile-dev-inc/maestro), [Windows kurulumu](https://docs.maestro.dev/getting-started/installing-maestro/windows); sürüm ve commit A33.0'da ölçülür; `maestro.zip` | GitHub sürüm dosyası, doğrudan indirme | Sürüm etiketi, dosya boyutu, SHA-256 ve `maestro --version`: A33.0'da ölçülür | Detox (wix/Detox); Appium |
| Maestro için Java çalışma ortamı | JDK 17 ya da üstü (sürüm A33.0'da ölçülür) | Paket yöneticisi ya da Android Studio ile gelen JBR | A33.0'da ölçülür | Eclipse Temurin |
| Android performans ölçümü | Flashlight: [bamlab/flashlight](https://github.com/bamlab/flashlight), [belgeler](https://docs.flashlight.dev); sürüm A33.0'da ölçülür | A33.0'da ölçülür | A33.0'da ölçülür | `adb shell dumpsys gfxinfo` ve `am start -W` (yerleşik) |
| EAS CLI ve iç dağıtım | `eas-cli` 27.2.0 (npm; A21 ile aynı), [iç dağıtım](https://docs.expo.dev/build/internal-distribution/); hesap: altyapı (İ-15) | `pnpm dlx eas-cli@27.2.0` ya da kurulu `eas` | A33.0'da ölçülür | Firebase App Distribution |
| iOS'ta Maestro koşusu | EAS Workflows Maestro işi; adres ve koşul A33.0'da ölçülür | Expo hesabı (altyapı) | A33.0'da ölçülür | Maestro Cloud; kullanıcının Mac'i |
| Dış test dağıtımı | EAS iç dağıtım bağlantısı (Android); iOS için kayıtlı cihaz ya da TestFlight; Google Play iç test. Hesaplar: altyapı | `eas device:create`; mağaza yükleme `eas submit` ile yapılmaz, kullanıcı elle yükler | A33.0'da ölçülür | Firebase App Distribution |
| Erişilebilirlik tarayıcıları | Google Erişilebilirlik Tarayıcısı (Android), Xcode Accessibility Inspector (Mac); TalkBack ve VoiceOver sistemde yerleşik | Mağaza uygulaması; sistem aracı | A33.0'da ölçülür | Elle kontrol listesi |
| Test fikstürleri | `test-kucuk` ve `test-ses` paketleri (A13 üretir) | Kendi ürettiğimiz | A13 testleri | Yok |

Kendimiz yapacağımız işler: dokuz Maestro akışı ve göç akışı, eksik `testID`'ler, kıyas ekranı ölçümleri, ölçüm komutları ve rapor şablonu, erişilebilirlik kontrol listesi, B tablosu ve ölçüm raporu.

## Adımlar
### A33.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula; açılmayan adresin yerine yedek adayı kullan, tabloyu bu adımla birlikte güncelle.
- Maestro sürüm dosyasını `data/gelen/maestro/<YYYY-AA-GG>/` altına yeni boş klasöre indir; `SHA256SUMS` dosyasını sha256sum biçiminde yaz. Araçlar içerik kaynağı değildir: kaynak kaydı (TOML) açılmaz.
- Sürümleri paket kaydından doğrula: `eas-cli` için `npm view eas-cli version`; Maestro ve Flashlight için sürüm etiketi. Maestro sürümünü Teknoloji yığını §1 satırına `/belge-esitle` ile yaz.
- **Bitti sayılır:** Tablodaki her adres açılıyor ya da yedek adaya geçiş yazılı; sürümler sabit; Maestro `SHA256SUMS` yazılı.

### A33.1 · Önkoşul, doğrulanacak maddeler ve kararlar
- `/durum` ile A24–A32'nin durumunu oku. Kısmi kalan aşamaya dayanan akışlar planda atlanır ve raporda gerekçesiyle yazılır.
- Planın ilk maddesi BÇ-15'in kararıdır (iOS'ta Maestro): Windows'ta iOS simülatörü yoktur (Yerel geliştirme §1). Seçenekler Tedarik tablosundadır; öneri bulut koşusudur (ücretli iştir, tahmini maliyet söylenir). Karar `/belge-esitle` ile Test stratejisi §14 madde 7'ye ve BÇ-15'e işlenir. iOS akışları yazılır; iOS koşumu ve Instruments ölçümü kullanıcıya bırakıldı ve aşamayı bekletmez.
- `arastirmaci` resmî kaynaktan doğrular: `maestro test` ortam değişkeni bayrağı, Android'de ASCII dışı karakter girişi (Test stratejisi §14 madde 4), uçak modu ve ekran döndürme komutları, B-01 için ağ isteği izleme yöntemi, bellek ve soğuk açılış ölçüm yöntemleri (B-13).
- BÇ-14 ve A28.1 kararı uygulanır: ölçüm `internal` profil derlemesiyle (sürüm kipi) yapılır; `dev` verisiyle ölçmek gerekirse `developmentClient: false` ve `APP_FLAVOR=dev` taşıyan ayrı bir EAS ölçüm profili eklenir.
- Derleme görünürlüğü Yayın süreci §3'tedir: `internal` derleme onaylı birimleri, onaysız birimleri "doğrulanmamış" rozetiyle, insan onayı isteyen türdeki aday bağlantıları ve yalnız `test-kucuk` ile `test-ses` fikstürlerini taşır. `dev`'e özgü akışlar (öz test) yalnız `dev` derlemede koşar.
- **Bitti sayılır:** Araç doğrulamaları, BÇ-14 ve BÇ-15 kararları yazılı.

### A33.2 · Maestro akışları
- Her akış `appId: ${APP_ID}` kullanır (`dev` için `app.mutalaa.dev`, `internal` için `app.mutalaa.internal`; kimlikler yer tutucudur, Mobil mimari §10). Şema da değişkendir: `${SCHEME}` (`mutalaa-dev`, `mutalaa-internal`; Test stratejisi §9). `testID` adları çapa gramerini izler; eksik kimlik ilgili ekrana eklenir.
  1. `sayfa-kelime-baglanti.yaml`: Test stratejisi §9'daki örnek akış.
  2. `ses-cal.yaml`: `q/1/1` açılır, mini oynatıcıda Oynat; Duraklat düğmesi görünür; `etkin-ayet-q:1:2` 20 saniye içinde görünür; Duraklat (`ses-test` fikstürü).
  3. `arama.yaml`: Ara sekmesi, `isik` yazılır; ilk sonuç "Işık" içerir; sonuca dokununca okuyucu açılır.
  4. `depolama-paket-sil.yaml`: Ayarlar › Depolama, `test-kucuk` satırında Sil. K-18 ve Depolama yöneticisi §1.1 gereği onay penceresi yoktur: satır "Silindi · Geri al" olur; ekrandan çıkınca Kütüphane'de "İndir" görünür (Test stratejisi §9).
  5. `oz-test.yaml`: öz test ekranında "Geçti" (yalnız `dev`).
  6. `verilerimi-sil.yaml` ve `disa-aktar.yaml`: Gizlilik §4'teki "Verilerimi sil ve dışa aktar" maddesi; paylaşım sayfası açılınca akış durur.
  7. `geri-don-zinciri.yaml`: 5 adımlı atlama zinciri, döndürme ve tema değişimi; "↩ Okuduğun yere dön" başlangıç çapasına ve ofsetine döner (B-09).
  8. `cevrimdisi.yaml`: temiz kurulumdan sonra uçak modunda okuma, arama, kelime kartı, `core` içi bağlantı, not, vurgu, yer imi ve hatim (B-01).
  9. `perf-sayfa-cevir.yaml`: 50 sayfa çevirme (Test stratejisi §10).
- Kullanıcı veritabanı göç akışı (Test stratejisi §6): ikinci `internal` derlemeden başlayarak eski derlemenin üstüne yenisi kurulur ve kayıtların korunduğu sınanır.
- Akışları Claude Code yazar ve sözdizimini denetler; koşumu kullanıcı yapar.
- **Bitti sayılır:** Dokuz akış ve göç akışı yazıldı; sözdizimi denetimi geçiyor; akışlardaki kimlikler uygulama kaynağındaki `testID`'lerle eşleşiyor. Emülatörde koşum kullanıcıya bırakıldı.

### A33.3 · Performans
- Referans cihazlar İ-21 ile seçilir; adları rapora ve `/belge-esitle` ile Test stratejisi §14 madde 2'ye yazılır (AS-08, AR-7, MM-12).
- Arama: A28 ekranı ve sorgu kümesi, sürüm kipinde, `core` ve üç isteğe bağlı paket bağlıyken (B-02; Arama §6); hedef 50 ms altı, p95 < 50 ms (K-17). B-02 üç paketi adıyla vermez; bağlanan paketler ve sürümleri raporda yazılır. Açılıştan sonraki ilk sorgu ayrı yazılır; JSON rapora eklenir.
- Kıyas ekranına kelime kartı açılışı ve Bağlantılar ilk sonuç süresi eklenir; hedef ≤ 100 ms (öneri).
- Sayfa çevirme: Flashlight ile `perf-sayfa-cevir.yaml` koşulur; `gfxinfo` sıfırlanır ve takılan kare oranı ≤ %5 (öneri) okunur. iOS Instruments Mac ister.
- Soğuk açılış ≤ 2,5 s (B-13, öneri), bellek < 200 MB (öneri), uygulama boyutu kaydı; yöntemler A33.1 doğrulamasıyla.
- Claude Code komutları, rapor şablonunu ve kıyas ekranı kodunu hazırlar; ölçümü kullanıcı referans cihazda yapar.
- **Bitti sayılır:** Ölçüm düzeni ve rapor şablonu hazır; ölçümler cihaz modeli, derleme ve paket sürümleriyle rapora işlendi ya da kullanıcıya bırakıldı olarak yazılı; bütçeyi aşan ölçü için Arama §6'daki sırayla iş kaydı yazılı.

### A33.4 · Erişilebilirlik ölçümü
- Otomatik: `ui-tokens` kontrast testi (4,5:1 eşiği; altın yalnız süs).
- Android Erişilebilirlik Tarayıcısı ve Xcode Accessibility Inspector taramalarını kullanıcı yapar; bulgular rapora girer.
- Elle kontrol listesi (Test stratejisi §11, Tasarım sistemi §9): TalkBack ve VoiceOver ile dört E2E akışı (1–4); Mod A'da glif katmanı gizli ve her âyet tek öğe; metin %200; 44×44 pt; Hareketi Azalt; her jestin düğmesi; renk tek başına anlam taşımaz; Fâtiha ve Bakara 255 üç çizim yolunda okunur (B-10). Claude Code listeyi `.tmp/a33/erisilebilirlik.md` olarak hazırlar, kullanıcı cihazda doldurur; `arayuz-denetcisi` kaynak kodda erişilebilirlik etiketlerini, rolleri ve dokunma hedeflerini denetler.
- **Bitti sayılır:** Liste hazır; dolu kısmı rapora bağlı; açık bulgular iş olarak yazılı.

### A33.5 · İç dağıtım ve dış test
- Yayınlayıcı kalite kapısı: `internal` manifesti Yayın süreci §3'teki görünürlüğe uyuyor; `test-` önekli kaynaklar `public`'e girmiyor, `internal`'a yalnız `test-kucuk` ve `test-ses` giriyor; `verify --flavor internal` temiz (Yayın süreci §5).
- `internal` derleme yalnız HTTPS kullanır (Yerel geliştirme §6). Profilin `MANIFEST_URL` değeri EAS bulutundan ve cihazdan erişilebilen HTTPS adres olmalıdır; canlı depo (İ-18) yoksa paket indiremeyen derlemenin yalnız gömülü `core` ile çıktığı rapora yazılır.
- `eas build` ücretli iştir: tahmini maliyet söylenir, kullanıcı onayıyla başlatılır ve beklenmez: `pnpm --dir apps/mobile exec eas build --profile internal --platform android --non-interactive --no-wait`; durum ve indirme A21.7'deki gibi `eas build:list … --json` ile izlenir. iOS için Apple hesabı ve kayıtlı cihaz gerekir (İ-15).
- Dış test: davetli kullanıcılar aynı `internal` derlemeyi kullanır. Android'de EAS iç dağıtım bağlantısı verilir; iOS'ta cihaz `eas device:create` ile kaydedilir ya da kullanıcı derlemeyi TestFlight'a elle yükler. Davet listesi ve geri bildirim kanalı kullanıcının işidir.
- **Bitti sayılır:** `internal` derleme ekip cihazında açılıyor; kalite kapısı temiz; dış test durumu ilerleme dosyasında yazılı.

### A33.6 · B tablosu ve rapor
- Rapor (öneri ad) `docs/07-yayin/04-faz-2-olcum-raporu.md`: cihazlar, derlemeler, paket sürümleri, akış sonuçları, ölçümler, erişilebilirlik listesi ve B tablosu.
- B tablosunda her ölçütün hedefi, yöntemi, sonucu ve durumu (Geçti · Kaldı · İzleniyor · Faz 3'te) yazılır. B-03 ve B-04: A18 raporları (`data/reports/{data_version}.json`); altın set etiketlenmediyse (İ-13) "Ölçülemedi". B-07: A32 kontrol listesi. B-11: Faz 2'nin son dört haftasındaki Sentry verisi, izleniyor. B-12: A32 testleri ve bağımlılık denetimi. "Öneri" hedefleri (B-03, B-04, B-11, B-13) İ-22 ile onaylanır.
- `belge-bekcisi` raporu Test stratejisi ve ilerleme dosyasından bağlar.
- **Bitti sayılır:** Rapor yazılı; Faz 2 çıkış ölçütlerinin her biri için durum ve kanıt var.

## Kabul ölçütleri
- [ ] Dokuz Maestro akışı ve göç akışı `apps/mobile/e2e/` altında yazıldı; sözdizimi denetimi geçiyor; kimlikler uygulamadaki `testID`'lerle eşleşiyor. Emülatörde koşum ve `maestro test` çıktısı kullanıcıya bırakıldı.
- [ ] Arama ölçümü için komutlar ve rapor şablonu hazır; referans Android cihazdaki p95 < 50 ms ölçümü kullanıcıya bırakıldı, sonucu JSON rapora eklenir ya da aşmanın nedeni ve iş kaydı yazılır.
- [ ] Takılan kare oranı, soğuk açılış, bellek ve uygulama boyutu için ölçüm düzeni raporda.
- [ ] `pnpm --filter @mutalaa/ui-tokens test` yeşil; elle erişilebilirlik listesi hazır.
- [ ] `verify --flavor internal` 0 ile bitiyor; `internal` derleme ekip cihazına kurulup açıldı.
- [ ] Dış test durumu ilerleme dosyasında yazılı.
- [ ] B-01…B-04 ve B-07…B-13 tablosunda her satır durum ve kanıt taşıyor.

## Doğrulama
Claude Code çalıştırır:
```bash
pnpm lint && pnpm typecheck && pnpm test
pnpm --filter @mutalaa/ui-tokens test
mkdir -p .tmp/a33
dotnet run --project server/Mutalaa.Publisher -- verify --flavor internal
pnpm --dir apps/mobile exec eas build:list --platform android --build-profile internal --limit 1 --json --non-interactive   # iç derlemenin durumu
```
Kullanıcı çalıştırır (emülatör ya da İ-21 cihazı; kullanıcıya bırakıldı):
```bash
adb devices
maestro test apps/mobile/e2e/                        # APP_ID ve SCHEME bayrağı A33.1'de doğrulanır
adb shell dumpsys gfxinfo <paket-adi> reset
maestro test apps/mobile/e2e/perf-sayfa-cevir.yaml
adb shell dumpsys gfxinfo <paket-adi> | grep -i "janky"
```

## Dikkat
- `eas build` ve `eas update` ücretli iştir ve kullanıcı onayı ister; `eas submit` hiç çalıştırılmaz (CLAUDE.md kural 11).
- Uygulama emülatörde ya da cihazda Claude Code tarafından çalıştırılmaz, ekran görüntüsü alınmaz (CLAUDE.md çalışma düzeni 3); ilgili adımlar "kullanıcıya bırakıldı" diye yazılır ve aşamayı bekletmez.
- Bütçeye yalnız sürüm (release) kipinde ve referans cihazda yapılan ölçüm tabidir (Mobil mimari §9); emülatör ve geliştirme kipi değerleri yalnız eğilim gösterir.
- Akışlarda ve raporlarda kişisel veri ya da gerçek not metni yoktur; fikstürler sentetiktir.
- Android'de ASCII dışı karakter girişi doğrulanana kadar arama akışı `isik` kullanır; Arapça sorgu öz testte sınanır (Test stratejisi §9).
- `dev`'e özgü akışlar (öz test) yalnız `dev` derlemede koşar.
- Git Bash'te `adb` ve `maestro` doğrudan çalışır; cihaz yolu içeren argümanlarda yol dönüşümü için `windows-sorun`.
- Commit kapsamları: `mobile` (akışlar ve düzeltmeler), `docs` (rapor).
- A08'den devir: EAS ücretsiz planı ayda 15 Android ve 15 iOS derleme verir (kota aşılınca ücret çıkmaz, derleme durur; [Proje yapısı §8](../../02-mimari/03-proje-yapisi.md#8-açık-sorular) madde 3). Faz 2'nin `internal`, ölçüm ve duman derlemeleri bu kotaya karşı planlanır; yeterli değilse sorun `/karar` ile ele alınır. Toplu derleme kotayı korur (`fingerprint`, A21).

## İnsan adımları
- İ-21 · Referans cihazların seçimi: A33.3'ten önce gerekir.
- İ-15 · Expo hesabı ve `eas login` (iOS için Apple Developer): A33.5'ten önce. İ-18 · Canlı içerik deposu: `internal` derlemenin paket indirmesi için. İ-22 · "Öneri" hedeflerin onayı: B tablosu kapanmadan önce.
- Maestro akışlarının emülatörde koşumu, referans cihazdaki ölçümler, elle erişilebilirlik denetimi (TalkBack, VoiceOver) ve tarayıcı taramaları kullanıcıyla yapılır.

## Çıktılar
- `apps/mobile/e2e/*.yaml` ve eksik `testID`'ler
- Kıyas ekranında kelime kartı ve Bağlantılar ölçümleri
- `docs/07-yayin/04-faz-2-olcum-raporu.md` (öneri ad); ham ölçümler ve listeler `.tmp/a33/` (git dışı)
- `internal` EAS derlemesi (yapıt EAS'te) ve ilerleme dosyasında Faz 2 durumu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A33-uctan-uca-test-ve-ic-dagitim.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A32](./A32-ayarlar-erisilebilirlik-oz-test.md) · Sonraki: [A34](./A34-magaza-yayini.md)
