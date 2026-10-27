# A33 · Uçtan uca testler (Maestro), performans, erişilebilirlik ölçümü, iç dağıtım

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A25](./A25-secim-kelime-karti-baglantilar.md) · [A26](./A26-mushaf-a.md) · [A27](./A27-ses-sistemi.md) · [A28](./A28-arama-ekrani.md) · [A29](./A29-kutuphane-ve-depolama.md) · [A30](./A30-defterim-ve-ilerleme.md) · [A31](./A31-hadis-ve-risale-okuyuculari.md) · [A32](./A32-ayarlar-erisilebilirlik-oz-test.md) · **İnsan adımı:** İ-02 (dış test için Kurul ön cevabı) · İ-21 (referans cihazlar)
> **Ajanlar:** `test-yazari` · `arayuz-denetcisi` · `lisans-denetcisi` · `arastirmaci` · `mobil-gelistirici` · `inceleyici` · `belge-bekcisi` · **Beceriler:** `mobil-ekran` · `lisans-kapisi` · `windows-sorun` · **Tahmini oturum:** 3–5 (insan beklemesi hariç)
> **Başlat:** `/asama A33`

## Amaç
Faz 2'nin çıkış ölçütlerini kanıtlar: 07-yayin/03 §9'daki Maestro akışları, §10'daki performans ölçümleri ve §11'deki erişilebilirlik denetimleri koşulur; B-01…B-13 için durum tablosu çıkar. `internal` derleme EAS iç dağıtımla ekip cihazlarına gider. Dış test kullanıcısı yalnız Kurul ön görüşmesinin cevabından sonra alınır (K-06, İ-02). Sonuçlar A34'ün girdisidir.

## Okunacak belgeler
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 kullanıcı veritabanı göçü, §8–§11, §12 CI düzeni, §13 sürüm kontrol listesi, §14 açık sorular
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §2.1 derleme türleri, §8 B-01…B-13, §9 AS-08, AS-09, AS-11
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 2 çıkış ölçütleri
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §9 bütçeler, §10 derleme türleri ve `isPackVisible`
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §3 iç test sorusu, §5 yapıt taraması
- [Arama (FTS5)](../../03-veri/05-arama-fts5.md): §6 ölçüm ve bütçe aşılırsa
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §9 erişilebilirlik kontrol listesi
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §4 Faz 3 öncesi kontrol listesi
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §1 iOS notu, §6 madde 8 ve HTTPS kuralı

## Kapsam
**Yapılır**
- Maestro akışları ve emülatörde koşumları. Klasör `apps/mobile/e2e/` (02-mimari/03 §1; 07-yayin/03 §10); Maestro 02-mimari/02 §1'dedir.
- Referans cihazda performans ölçümü; kıyas ekranına kelime kartı ve Bağlantılar ilk sonuç süresinin eklenmesi.
- Erişilebilirlik: kontrast testi, tarayıcılar, elle kontrol listesi (kullanıcıyla).
- B-01…B-13 durum tablosu ve ölçüm raporu.
- `internal` EAS derlemesi, ekip içi dağıtım ve dış test kapısı.

**Yapılmaz**
- `public` derleme ve mağaza hazırlığı: A34. `eas submit` hiç çalıştırılmaz.
- B-03 ve B-04 altın set ölçümleri: A18; raporları tabloya alınır. Kurul başvurusu: İ-19.
- Bulunan büyük hatalar ilgili aşamanın işidir; küçük düzeltmeler burada `fix(mobile)` commitleriyle yapılır.

## Adımlar
### A33.1 · Önkoşul, araçlar ve kararlar
- `/durum` ile A24–A32'nin durumunu oku. Kısmi kalan aşamaya (ör. lisans nedeniyle A26) dayanan akışlar planda atlanır ve raporda gerekçesiyle yazılır.
- `arastirmaci` resmî kaynaktan doğrular: Maestro CLI'nin Windows kurulumu ve sürümü (İ-01; kurulumu kullanıcı yapar ya da onaylar), `maestro test` ortam değişkeni bayrağı, Android'de ASCII dışı karakter girişi (07-yayin/03 §14 madde 4), uçak modu ve ekran döndürme komutları, B-01 için ağ isteği izleme yöntemi, bellek ve soğuk açılış ölçüm yöntemleri (B-13).
- A28.1'de verilen ölçüm derlemesi kararı uygulanır (sürüm kipinde `dev` profili ya da seçilen yol).
- Görünürlük kuralı: Kurul onayı bekleyen `core`, Kurul'un kapalı test cevabı (İ-02) gelene kadar `internal` derlemede gizlidir (06-mobil/01 §10, 03-veri/03 §8 madde 3, 07-yayin/01 §3 ve §4.3); Yayınlayıcı onu `internal` manifestine koyar, P-04 yalnız `public`'tedir. Cevap gelene kadar `core` gerektiren akışlar yalnız `dev` derlemede koşar; `internal`'da `core`'un gizlendiği sınanır (öneri).
- iOS: Windows'ta iOS simülatörü yok (02-mimari/04 §1). Maestro'nun iOS'ta koşacağı yer (Mac ya da bulut) Açık soru (07-yayin/03 §14 madde 7); kullanıcıya sorulur. Faz 2 ölçütü "Maestro akışları iOS ve Android'de yeşil" bu cevaba bağlıdır.
- **Bitti sayılır:** Araç doğrulamaları ve iOS yolu kararı yazılı.

### A33.2 · Maestro akışları
- Her akış `appId: ${APP_ID}` kullanır (`dev` için `app.mutalaa.dev`, `internal` için `app.mutalaa.internal`; kimlikler yer tutucudur, 06-mobil/01 §10). Şema da değişkendir: `${SCHEME}` (`mutalaa-dev`, `mutalaa-internal`; 07-yayin/03 §9). `testID` adları çapa gramerini izler; eksik kimlik ilgili ekrana eklenir.
  1. `sayfa-kelime-baglanti.yaml`: 07-yayin/03 §9'daki örnek akış.
  2. `ses-cal.yaml`: `q/1/1` açılır, mini oynatıcıda Oynat; Duraklat düğmesi görünür; `etkin-ayet-q:1:2` 20 saniye içinde görünür; Duraklat (`ses-test` fikstürü).
  3. `arama.yaml`: Ara sekmesi, `isik` yazılır; ilk sonuç "Işık" içerir; sonuca dokununca okuyucu açılır.
  4. `depolama-paket-sil.yaml`: Ayarlar › Depolama, `test-kucuk` satırında Sil. K-18 ve 06-mobil/03 §1.1 gereği onay penceresi yoktur: satır "Silindi · Geri al" olur; ekrandan çıkınca Kütüphane'de "İndir" görünür (07-yayin/03 §9).
  5. `oz-test.yaml`: öz test ekranında "Geçti" (yalnız `dev`).
  6. `verilerimi-sil.yaml` ve `disa-aktar.yaml`: KVKK §4 maddesi; paylaşım sayfası açılınca akış durur.
  7. `geri-don-zinciri.yaml`: 5 adımlı atlama zinciri, döndürme ve tema değişimi; "↩ Okuduğun yere dön" başlangıç çapasına ve ofsetine döner (B-09).
  8. `cevrimdisi.yaml`: temiz kurulumdan sonra uçak modunda okuma, arama, kelime kartı, `core` içi bağlantı, not, vurgu, yer imi ve hatim (B-01).
  9. `perf-sayfa-cevir.yaml`: 50 sayfa çevirme (07-yayin/03 §10).
- Kullanıcı veritabanı göç akışı (§6): ikinci `internal` derlemeden başlayarak eski derlemenin üstüne yenisi kurulur ve kayıtların korunduğu sınanır.
- **Bitti sayılır:** Akışlar emülatördeki `dev` derlemede yeşil; `internal` derlemede `dev`'e özgü olmayan ve (İ-02 cevabına kadar) `core` gerektirmeyen akışlar yeşil (A33.1).

### A33.3 · Performans
- Referans cihazlar İ-21 ile seçilir; adları rapora ve `/belge-esitle` ile 07-yayin/03 §14 madde 2'ye yazılır (AS-08, AR-7, MM-12).
- Arama: A28 ekranı ve sorgu kümesi, sürüm kipinde, `core` ve üç isteğe bağlı paket bağlıyken (B-02; 03-veri/05 §6); hedef 50 ms altı, p95 < 50 ms (K-17). B-02 üç paketi adıyla vermez; bağlanan paketler ve sürümleri raporda yazılır. Açılıştan sonraki ilk sorgu ayrı yazılır; JSON rapora eklenir.
- Kıyas ekranına kelime kartı açılışı ve Bağlantılar ilk sonuç süresi eklenir; hedef ≤ 100 ms (öneri).
- Sayfa çevirme: `gfxinfo` sıfırlanır, `perf-sayfa-cevir.yaml` koşar, takılan kare oranı ≤ %5 (öneri). iOS Instruments Mac ister; Açık soru.
- Soğuk açılış ≤ 2,5 s (B-13, öneri), bellek < 200 MB (öneri), uygulama boyutu kaydı; yöntemler A33.1 doğrulamasıyla.
- **Bitti sayılır:** Ölçümler cihaz modeli, derleme ve paket sürümleriyle raporda; bütçeyi aşan ölçü için 03-veri/05 §6'daki sırayla iş kaydı yazılı.

### A33.4 · Erişilebilirlik ölçümü
- Otomatik: `ui-tokens` kontrast testi (4,5:1 eşiği; altın yalnız süs).
- Android Erişilebilirlik Tarayıcısı ve Xcode Accessibility Inspector taramalarını kullanıcı yapar; bulgular rapora girer.
- Elle kontrol listesi (07-yayin/03 §11, 01-urun/04 §9): TalkBack ve VoiceOver ile dört E2E akışı (1–4); Mod A'da glif katmanı gizli ve her âyet tek öğe; metin %200; 44×44 pt; Hareketi Azalt; her jestin düğmesi; renk tek başına anlam taşımaz; Fâtiha ve Bakara 255 üç çizim yolunda okunur (B-10). Claude Code listeyi `.tmp/a33/erisilebilirlik.md` olarak hazırlar, kullanıcı cihazda doldurur, `arayuz-denetcisi` ekran görüntüleriyle karşılaştırır.
- **Bitti sayılır:** Liste dolu ve rapora bağlı; açık bulgular iş olarak yazılı.

### A33.5 · İç dağıtım
- `lisans-denetcisi`: `internal` manifesti yalnız `serbest` paket taşıyor; `test-` önekli kaynaklar `public`'e girmiyor; A13'teki `verify --flavor internal` temiz (07-yayin/01 §5).
- `internal` derleme yalnız HTTPS kullanır (02-mimari/04 §6). Profilin `MANIFEST_URL` değeri EAS bulutundan ve cihazdan erişilebilen HTTPS adres olmalıdır; canlı depo (İ-18) yoksa paket indiremeyen derlemenin yalnız gömülü `core` ile çıktığı rapora yazılır.
- Derleme kullanıcı onayıyla başlatılır ve beklenmez: `(cd apps/mobile && eas build --profile internal --platform android --non-interactive --no-wait)`; durum ve indirme A21.7'deki gibi `eas build:list … --json` ile izlenir; iOS için Apple hesabı ve kayıtlı cihaz gerekir (İ-15). Kurulum bağlantısı yalnız ekip cihazlarına verilir.
- Dış test: İ-02 cevabı gelmeden davetli test kullanıcısı alınmaz. Cevap olumluysa kapsam ve görünürlük `/karar` ile yazılır, sonra davet gönderilir; olumsuzsa `internal` ekip içinde kalır.
- **Bitti sayılır:** `internal` derleme ekip cihazında açılıyor; lisans raporu temiz; dış test durumu ilerleme dosyasında yazılı.

### A33.6 · B tablosu ve rapor
- Rapor (öneri ad) `docs/07-yayin/04-faz-2-olcum-raporu.md`: cihazlar, derlemeler, paket sürümleri, akış sonuçları, ölçümler, erişilebilirlik listesi ve B tablosu.
- B tablosunda her ölçütün hedefi, yöntemi, sonucu ve durumu (Geçti · Kaldı · İzleniyor · Faz 3'te) yazılır. B-03 ve B-04: A18 raporları (`data/reports/{data_version}.json`); altın set etiketlenmediyse (İ-13) "Ölçülemedi". B-05 ve B-06: `internal` için burada, `public` için A34. B-07: A32 kontrol listesi. B-11: Faz 2'nin son dört haftasındaki Sentry verisi, izleniyor. B-12: A32 testleri ve bağımlılık denetimi. "Öneri" hedefleri (B-03, B-04, B-11, B-13) İ-22 ile onaylanır.
- `belge-bekcisi` raporu 07-yayin/03 ve ilerleme dosyasından bağlar.
- **Bitti sayılır:** Rapor yazılı; Faz 2 çıkış ölçütlerinin her biri için durum ve kanıt var.

## Kabul ölçütleri
- [ ] Dokuz Maestro akışı `dev` derlemede emülatörde yeşil; `maestro test` çıktısı rapora eklendi.
- [ ] Referans Android cihazda arama p95 < 50 ms ölçüldü ve JSON rapora eklendi ya da aşmanın nedeni ve iş kaydı yazılı.
- [ ] Takılan kare oranı, soğuk açılış, bellek ve uygulama boyutu raporda.
- [ ] `pnpm --filter @mutalaa/ui-tokens test` yeşil; elle erişilebilirlik listesi dolu.
- [ ] `verify --flavor internal` 0 ile bitiyor; `internal` derleme ekip cihazına kurulup açıldı.
- [ ] İ-02 cevabı gelmeden dış test kullanıcısı yok (ilerleme dosyasında durum).
- [ ] B-01…B-13 tablosunda her satır durum ve kanıt taşıyor.

## Doğrulama
```bash
pnpm lint && pnpm typecheck && pnpm test
pnpm --filter @mutalaa/ui-tokens test
mkdir -p .tmp/a33
adb devices                                          # emülatör ya da İ-21 cihazı
maestro test apps/mobile/e2e/                        # APP_ID ve SCHEME bayrağı A33.1'de doğrulanır
adb shell dumpsys gfxinfo <paket-adi> reset
maestro test apps/mobile/e2e/perf-sayfa-cevir.yaml
adb shell dumpsys gfxinfo <paket-adi> | grep -i "janky"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor internal
(cd apps/mobile && eas build:list --platform android --build-profile internal --limit 1 --json --non-interactive)   # iç derlemenin durumu
```

## Dikkat
- `eas build` ve `eas update` kullanıcı onayı ister; `eas submit` hiç çalıştırılmaz (CLAUDE.md kural 11).
- Bütçeye yalnız sürüm (release) kipinde ve referans cihazda yapılan ölçüm tabidir (06-mobil/01 §9); emülatör ve geliştirme kipi değerleri yalnız eğilim gösterir.
- Akışlarda ve rapor görüntülerinde kişisel veri ya da gerçek not metni yoktur; fikstürler sentetiktir.
- Android'de ASCII dışı karakter girişi doğrulanana kadar arama akışı `isik` kullanır; Arapça sorgu öz testte sınanır (07-yayin/03 §9).
- `internal` derleme `bekliyor` ve `ic_kullanim` paketleri göstermez; bu paketlere dayanan akışlar yalnız `dev`'de koşar.
- Git Bash'te `adb` ve `maestro` doğrudan çalışır; cihaz yolu içeren argümanlarda yol dönüşümü için `windows-sorun`.
- Commit kapsamları: `mobile` (akışlar ve düzeltmeler), `docs` (rapor).
- A08'den devir: EAS ücretsiz planı ayda 15 Android ve 15 iOS derleme verir (kota aşılınca ücret çıkmaz, derleme durur; [Proje yapısı §8](../../02-mimari/03-proje-yapisi.md#8-açık-sorular) madde 3). Faz 2'nin `internal`, ölçüm ve duman derlemeleri bu kotaya karşı planlanır; yeterli değilse sorun `/karar` ile ele alınır. Toplu derleme kotayı korur (`fingerprint`, A21).

## İnsan adımları
- İ-21 · Referans cihazların seçimi: A33.3'ten önce gerekir.
- İ-02 · Kurul ön görüşmesi cevabı: dış test kullanıcısı davetinden önce gerekir; ekip içi dağıtım beklemez.
- İ-15 · Expo hesabı ve `eas login` (iOS için Apple Developer): A33.5'ten önce. İ-18 · Canlı içerik deposu: `internal` derlemenin paket indirmesi için. İ-22 · "Öneri" hedeflerin onayı: B tablosu kapanmadan önce.
- Elle erişilebilirlik denetimi (TalkBack, VoiceOver) ve tarayıcı taramaları kullanıcıyla yapılır.

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
