# A32 · Ayarlar, ilk açılış tanıtımı, erişilebilirlik, Kaynaklar ve lisanslar, Kurul bilgisi, öz test, hata raporu

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A29](./A29-kutuphane-ve-depolama.md) · **İnsan adımı:** İ-27 (Sentry hesabı ve DSN)
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `lisans-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `test-vektoru` · `lisans-kapisi` · `metin-butunlugu` · **Tahmini oturum:** 4–5
> **Başlat:** `/asama A32`

## Amaç
Ayarlar ağacını 01-urun/03 §6'ya göre tamamlar ve erişilebilirlik kurallarını bütün uygulamada uygular: ayrı Arapça ve Türkçe yazı boyutu, %200 büyütme, Hareketi Azalt, 44×44 pt dokunma hedefi ve ekran okuyucu için Unicode katmanı. Kaynaklar ve lisanslar (B-07) ile Kurul onay bilgisi (B-06) ekranlarını paketlerdeki veriden kurar. Ortak test vektörlerini Hermes'te koşan, yalnız `dev` derlemedeki öz test ekranını ve kişisel veri içermeyen hata raporunun anahtarını ve denetimini (B-12) ekler. İlk açılış tanıtımını (01-urun/03 §5) da yazar; A21 yalnız rotasını açmıştı.

## Okunacak belgeler
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 `ayarlar/*` ve `onboarding/index.tsx`, §5 ilk açılış, §6 ayarlar ağacı ve hizalama notları, §9 ME-3, ME-4 ve ME-5
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §5 `useSettings`, §10 bayraklar, §11 hata türleri, §12 Sentry, §13 erişilebilirlik, §14 Türkçe harf ve `Intl`
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): tamamı; özellikle §2.2, §2.3, §2.5, §2.7, §4
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §6 Kaynaklar ve lisanslar, Kurul onay bilgisi
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §2 özet tablo, §3 atıf satırları
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §3.2 kademeler, §4 dokunma hedefi, §5 hareket, §9 kontrol listesi
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §13 erişilebilirlik
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 öz test, §11 erişilebilirlik
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §7 hangi ayar nerede durur

## Kapsam
**Yapılır**
- A21'in yer tutucu ayar rotaları doldurulur: `ayarlar/index`, `gorunum`, `okuma`, `mushaf`, `erisilebilirlik`, `kaynaklar`, `kurul`, `hakkinda`; geliştirici menüsüne öz test satırı ve yeni rota `ayarlar/gelistirici/oz-test.tsx` (öneri ad). Başka aşamada dolmuş ekran yeniden yazılmaz, ağaca bağlanır.
- Ayar deposu: `theme` içinde `sistem`, `arabicScale` ve `turkishScale` için kademe eşlemesi, Hareketi Azalt ve dokunsal geri bildirim tercihleri, ayar göç testleri.
- 06-mobil/01 §13'teki erişilebilirlik uygulaması, bütün ekranlarda.
- Kaynaklar ve lisanslar, Kurul onay bilgisi, Hakkında (gizlilik metni dahil), "Verilerimi sil".
- "Hata raporları" anahtarı ve A21'in `src/lib/telemetry.ts` kurulumunun denetimi; öz test ekranı.
- İlk açılış tanıtımı (`onboarding/index.tsx`): dört adım, her adımda "Atla", derin bağlantıyla ilk açılışta kısa yol; tamamlandı bilgisi MMKV'de; Hakkında'daki "Tanıtımı yeniden göster" onu açar.

**Yapılmaz**
- Depolama: A29. Hafız ve dinleme: A27. İlerleme satırlarının işlevi ve yedek: A30. Tasarım vitrini: A22. Arama ölçümü: A28. Sentry'nin ilk kurulumu: A21.
- Maestro akışları, referans cihazda elle erişilebilirlik ve performans ölçümü: A33. Mağaza beyanları, gizlilik metninin son hâli ve kaynak eşlemesi yüklemesi: A34.
- Tecvid renkleri, artırılmış kontrast, ek yazı tipleri: v1.x. Başka arayüz dilleri: faz atanmadı. Hesap ve aydınlatma metni: A35.

## Adımlar
### A32.1 · Önkoşul, doğrulamalar ve kararlar
- Dolu ve yer tutucu ayar ekranlarını, `useSettings` deposunu ve A21'in `telemetry.ts` dosyasını listele; 01-urun/03 §6 ağacıyla karşılaştır.
- `arastirmaci` resmî belgeden doğrular: Sentry projesinde IP saklamayı kapatan ayar ve veri bölgesi (07-yayin/02 §2.2; A34'te yeniden bakılır), Android'de Hareketi Azalt ayarının `isReduceMotionEnabled` ile okunuşu, dokunsal geri bildirim modülü, açık kaynak lisans listesi üretim aracı (02-mimari/02 §3), vektörleri yalnız `dev` JS paketine koyma yöntemi (ME-3 ile aynı soru), `expo export` bayrakları, `maxFontSizeMultiplier` için önerilecek değer.
- Kullanıcıya sorulur ve `/karar` ile yazılır:
  1. "Hata raporları" varsayılanı (ME-4; KVKK §5 madde 2). Öneri: açık; gizlilik metninde yazılı ve tek dokunuşla kapanır.
  2. "Verilerimi sil" için onay penceresi. Satırın yeri belgelerde eşitlendi (19 Ekim 2026): 01-urun/03 §6'da İlerleme ve gizlilik altında (KVKK §2.5, §2.7). Öneri: onay penceresiyle.
  3. **Çözüldü (19 Ekim 2026):** ekran adı 01-urun/03 §6'daki "İlerleme ve gizlilik"tir; KVKK §2.2 ve §2.5 bu ada uyduruldu.
- Sentry hesabı ve projesi İ-27'dir. Kullanıcı açar; DSN değerini `apps/mobile/.env.local` ve EAS ortamına kendisi yazar (Claude Code `.env` okumaz).
- **Bitti sayılır:** Doğrulama sonuçları ve iki karar (madde 1–2) yazılı.

### A32.2 · Ayarlar ağacı ve depo
- Ağaç 01-urun/03 §6: Görünüm (tema Sistem* · Kâğıt · Âhar · Gece; Arapça ve Türkçe boyut 10 kademe, varsayılan 5, cihaza özgü; Türkçe yazı tipi Literata), Okuma, Mushaf (görünmeyen çizim yolu listelenmez), Hafız ve dinleme, Depolama, İlerleme ve gizlilik, Erişilebilirlik, Kaynaklar ve lisanslar, Kurul onay bilgisi, Hakkında, Geliştirici (`gelistiriciMenusu`: yalnız `dev` ve `internal`).
- Kademe değerleri 01-urun/04 §3.2'den gelir (Türkçe 14…36 pt, Arapça 22…60 pt); depo çarpan tutar. Cihaza özgü ayarlar yalnız MMKV'dedir; diğerleri 03-veri/04 §7'ye göre `setting` tablosuna da yazılır.
- `FontSizeSlider` artı ve eksi düğmelidir ve canlı önizleme taşır; değişiklik önizleme bölgesinde anında görünür.
- Hakkında: sürüm, derleme türü, içerik paket sürümleri, ilkeler (K-25), gizlilik metni (KVKK §2.5 taslağı; veri sorumlusu satırı Açık soru diye işaretli) ve "Tanıtımı yeniden göster".
- "Verilerimi sil" (01-urun/03 §6, İlerleme ve gizlilik; onay penceresi A32.1 kararıyla): `user.db`'yi, ayarları ve son aramaları siler (KVKK §2.7), paketlere dokunmaz.
- Ayar göçü: kalıcı depo sürümü artınca eski kayıt kaybolmadan taşınır (01-urun/01 §4.10).
- **Bitti sayılır:** Ayar göç testi ve "Verilerimi sil" testi yeşil; ağaçtaki her satır bir ekrana ya da işleve bağlı.

### A32.3 · Erişilebilirlik uygulaması
- Yazı: okuma metni kademe × sistem ölçeğiyle en az %200'e çıkar; Arapça ve Türkçe ayrı ayarlanır. Arayüz metni sistem ölçeğini `maxFontSizeMultiplier` sınırına kadar izler. Erişilebilirlik boyutlarında çok sütunlu düzen tek sütuna iner. Glif sayfası `allowFontScaling={false}` ile çizilir ve yakınlaştırmayla büyür; yakınlaştırma hiçbir ekranda kapatılmaz.
- Hareketi Azalt (Sistem* · Açık · Kapalı): sistem değeri `AccessibilityInfo.isReduceMotionEnabled()`'dan okunur. Açıkken sayfa çevirme ve takip kaydırması animasyonsuzdur (`scrollToIndex({ animated: false })`), alt sayfa geçişleri solmaya döner, hareket jetonları `anlik` olur.
- Hedefler: her dokunulabilir öğe en az 44×44 pt (küçük simgede `hitSlop`) ve Türkçe erişilebilirlik etiketi taşır; her kaydırma jestinin görünür düğmesi vardır; "Büyük dokunma alanları (Mod A)" ayarı Mod A isabet alanını büyütür.
- Ekran okuyucu: `screenReaderChanged` dinlenir; açılınca "Erişilebilir metin modu" (Âyet âyet + Unicode) bir kez önerilir. Her âyet "Bakara Sûresi, 255. âyet" etiketli ve Arapça Unicode metinli tek öğedir, âyet sırasıyla dizilir; öğe eylemleri Dinle, Meali oku, Tefsir (yalnız tefsir paketi kuruluyken), Vurgula, Bağlantılar; sayfa değişince en çok saniyede bir duyuru yapılır ("Sayfa 42, Bakara Sûresi"). Mod A katmanı A26'dadır ve burada denetlenir; Mod C ve Âyet âyet için eksik kalan burada tamamlanır.
- Renk tek başına anlam taşımaz; Türkçe paragraftaki her Arapça dizi ayrı `Text` olarak sağdan sola yazılır.
- **Bitti sayılır:** RNTL testleri etiket, rol ve eylemleri doğruluyor; %200 ve Gece görüntüleri `arayuz-denetcisi` onaylı.

### A32.4 · Kaynaklar ve lisanslar, Kurul onay bilgisi
- Kaynaklar ve lisanslar çevrimdışı açılır ve verisi koddan gelmez: `core` ile kurulu paketlerin `attribution` tabloları birleştirilir (ad, sürüm, lisans, zorunlu atıf, kaynak bağlantısı, tam bildirim metni). Ekran ayrıca fontları (lisans metni font dağıtımından; IBM Plex Sans ve Amiri Doğrulanacak), hafızları ve quran-align atfını, derlemede üretilen açık kaynak lisans listesini ve K-19 notunu (yapay zekâ taslağıyla hazırlanıp insan onayından geçen içerik) gösterir.
- Kurul onay bilgisi: her onayın numarası, tarihi, onaylı sürümü, kapsadığı paketler ve `pack_meta` içindeki içerik özetinin ilk 12 karakteri (`installed_pack.kurul_onay`). Onay bekleyen paket hiçbir derlemede listelenmez (01-urun/03 §3.2, 07-yayin/01 §6); "Kurul onayı bekleniyor" etiketi yoktur. Onayın gösterim biçimi (numara, QR, mühür) Açık soru; numara ve metin gösterilir.
- B-06'nın `public` derlemedeki ölçümü A34'tedir; burada `dev` verisiyle ekran sınanır.
- **Bitti sayılır:** `lisans-denetcisi` B-07 kontrol listesi (`.tmp/a32/b07.md`) lisans defterinin §3 atıf satırlarına karşı eksiksiz; Kurul ekranı `dev`'de onaysız `core`'u listelemiyor.

### A32.5 · Öz test ekranı
- Rota `ayarlar/gelistirici/oz-test.tsx` (öneri ad), yalnız `dev` derlemede; vektör dosyaları yalnız `dev` JS paketine girer (07-yayin/03 §2).
- Koşulan vektörler: `normalize/tr.jsonl`, `normalize/ar.jsonl`, `anchors/{valid,invalid,compare,contains,route}.jsonl`, `offsets/offsets.jsonl`, `fts-query/query.jsonl`. `content-hash/hash.jsonl` koşulmaz, çünkü cihaz özet hesaplamaz (03-veri/01 §7).
- Ayrıca Arapça sorgu sınaması koşulur (A28 ölçüm kümesindeki Arapça satırların beklenen ilk sonuçları; 07-yayin/03 §9). Bilgi satırları Hermes'teki `'İ'.toLocaleLowerCase('tr')`, `'I'.toLocaleLowerCase('tr')`, `normalize('NFC')` ve `Intl.NumberFormat('tr')` çıktılarını gösterir (MM-11).
- Ekran dosya başına geçen ve kalan sayısını, sonda tek satırda "Geçti" ya da "Kaldı" gösterir (`testID` önerisi: `oz-test-sonuc`).
- **Bitti sayılır:** Emülatörde "Geçti"; MM-11 gözlemleri `/belge-esitle` ile işlendi.

### A32.6 · Hata raporu anahtarı ve denetimi
- A21'in `telemetry.ts` dosyası 06-mobil/01 §12 ile karşılaştırılır: `dev`'de başlatılmaz; `sendDefaultPii: false`; ekran görüntüsü, görünüm hiyerarşisi ve oturum tekrarı yok; `tracesSampleRate` `public`'te 0, `internal`'da 0,2; kırıntılardan `console`, `ui.input` ve `touch` düşer, gezinmede yalnız rota şablonu, ağda sorgusuz adres kalır; `beforeSend` kullanıcıyı, sunucu adını ve cihaz adını siler, `extra` yalnız `errorKind`, `packId`, `packVersion` taşır. Eksik madde tamamlanır.
- "Hata raporları" anahtarı (A32.1 kararıyla, cihaz ayarı): kapalıysa Sentry başlatılmaz.
- Ayıklama testi genişletilir: not metni, arama sorgusu, okunan çapa, kullanıcı ve cihaz adı içeren fikstür olay `beforeSend` sonrasında bunları taşımıyor (07-yayin/02 §2.2).
- `inceleyici` bağımlılık listesini denetler: analitik, reklam ya da izleme SDK'sı yok (KVKK §2.3; B-12).
- **Bitti sayılır:** Ayıklama ve anahtar testleri yeşil; `dev` bayrağında `Sentry.init` çağrılmıyor.

### A32.7 · İlk açılış tanıtımı
- Rota `onboarding/index.tsx` (A21 açtı), dört adım tek ekranda (01-urun/03 §5): Hoş geldin (uygulama adı, tek cümlelik tanım ve üç söz: "Reklam yok. Hesap gerekmez. Notların cihazında kalır."); Tema ve yazı boyutu (Kâğıt, Âhar, Gece, Sistem kartları canlı örnekle; Arapça ve Türkçe boyut kaydırıcıları); Mushaf ve okuma biçimi (yalnız bu derlemede görünen çizim yolları; C ve Mushaf + Meal önceden seçili; ekran okuyucu açıksa "Erişilebilir metin modu" önerisi); İsteğe bağlı paketler (görünen paketler boyut ve lisans rozetiyle, "Yalnız Wi-Fi ile indir" varsayılan açık, "Şimdi değil" geçerli).
- Canlı örnek metin koddan gelmez: Fâtiha'nın ilk âyeti ve meali gömülü `core`'dan okunur (CLAUDE.md kural 2). Paket listesi ve indirme kuyruğu A29'un manifest ve kuyruk işlevlerini kullanır; çevrimdışıyken paket adımı "Sonra indir" der ve tanıtım yine biter (01-urun/03 §3).
- Her adımda "Atla"; "Atla, varsayılanlarla aç" bütün adımları geçer. Tanıtım bitince Oku sekmesi Fâtiha'da açılır. Uygulama ilk kez bir derin bağlantıyla açıldıysa yalnız 1. adım gösterilir ve hedef açılır (öneri; ME-5 okur testiyle kesinleşir).
- Tamamlandı bilgisi MMKV'de (cihaza özgü); "Tanıtımı yeniden göster" bu bilgiyi siler ve rotayı açar. Seçimler (tema, boyut, mushaf, okuma biçimi) A32.2'deki ayar deposuna yazılır; ayrı kopya tutulmaz.
- Ebru motifi yalnız burada ve boş durumlarda kullanılır (01-urun/03 §3); erişilebilirlik kuralları A32.3 ile aynıdır.
- **Bitti sayılır:** RNTL testleri dört adımı, "Atla" yolunu, derin bağlantı kısa yolunu ve "Tanıtımı yeniden göster"i doğruluyor; dört adımın Kâğıt ve Gece görüntüleri `arayuz-denetcisi` onaylı.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; ayar göçü, "Verilerimi sil", erişilebilirlik etiketleri, Kurul ekranı, hata raporu anahtarı ve genişletilmiş ayıklama testleri bu aşamada eklendi.
- [ ] Ağaçtaki her satır çalışıyor; görünmeyen çizim yolu listelenmiyor; Geliştirici menüsü `public` bayrağında yok (RNTL).
- [ ] Türkçe ve Arapça 10. kademede okuma metni varsayılanın iki katı; sistem yazı ölçeği 2,0 iken kesilen metin yok (`.tmp/a32/`, `arayuz-denetcisi`).
- [ ] Hareketi Azalt açıkken sayfa çevirme animasyonsuz (bileşen testi ve emülatörde gözlem).
- [ ] Dokunma hedefleri en az 44×44 pt (Tasarım vitrinindeki dokunma alanı katmanıyla görüntü).
- [ ] Kaynaklar ve lisanslar ekranı uçak modunda açılıyor; B-07 kontrol listesi eksiksiz.
- [ ] Kurul onay bilgisi ekranı onay bekleyen paketi listelemiyor (`dev`'de onaysız `core` satırı yok; test).
- [ ] Öz test emülatörde "Geçti"; `internal` için dışa aktarılan JS paketinde vektör kimliği (ör. `tr-0001`) yok.
- [ ] `dev` derlemede Sentry başlatılmıyor; olaylarda kişisel veri yok (birim testi); bağımlılıklarda analitik SDK'sı yok.
- [ ] İlk açılış tanıtımı: dört adım, "Atla" ve derin bağlantı kısa yolu testleri yeşil; seçimler ayar deposuna yazılıyor; "Tanıtımı yeniden göster" tanıtımı açıyor; örnek metin `core`'dan geliyor (kodda Kur'an ya da meal metni yok).

## Doğrulama
```bash
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/ui-tokens test                 # kontrast eşiği (07-yayin/03 §11)
pnpm lint && pnpm typecheck
mkdir -p .tmp/a32
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar/gelistirici/oz-test"
adb exec-out screencap -p > .tmp/a32/oz-test.png
adb shell settings put system font_scale 2.0          # mobil-ekran: büyük yazı
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://ayarlar"
adb exec-out screencap -p > .tmp/a32/ayarlar-200.png
adb shell settings put system font_scale 1.0
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://onboarding"
adb exec-out screencap -p > .tmp/a32/tanitim.png
# İç paket denetimi; komut ve bayraklar A32.1'de arastirmaci ile doğrulanır:
# APP_FLAVOR=internal pnpm --filter @mutalaa/mobile exec expo export --platform android --output-dir .tmp/export-internal
# grep -rl "tr-0001" apps/mobile/.tmp/export-internal   # beklenen: çıktı yok
```

## Dikkat
- Ayar ekranları yalnız ayarı değiştirir; davranış A24–A31'deki koddan gelir. Var olan ekran yeniden yazılmaz, eksik olan eklenir.
- Sentry'ye ve günlüğe kullanıcı kimliği, cihaz adı, IP, okunan âyet, arama sorgusu, not metni ve ekran görüntüsü girmez (CLAUDE.md kural 10).
- Atıf metni koda yazılmaz. Pakette atıf eksikse sorun Yayınlayıcı çıktısıdır (A13); `lisans-denetcisi` raporuna yazılır.
- Öz testte kırılan vektör için kural kodu yerinde değiştirilmez; `test-vektoru` becerisiyle üç dilde ele alınır.
- Türkçe harf dönüşümü `trLower` ve `trUpper` ile yapılır; Türkçe metinde `textTransform: 'uppercase'` kullanılmaz (01-urun/04 §3.3).
- VoiceOver denetimi iOS cihaz ister; Windows'ta burada yalnız emülatör ve TalkBack yapılır, iOS denetimi A33'te İ-21 cihazında.
- Commit kapsamları: `mobile`, `ui-tokens` (yalnız jeton değişirse).

## İnsan adımları
- İ-27 · Sentry hesabı, projesi ve DSN değeri: `internal` derlemeden önce kullanıcı açar (A32.1) ve DSN'i `apps/mobile/.env.local` ile EAS ortamına kendisi yazar ([İnsan adımları](../06-insan-adimlari.md)).

## Çıktılar
- `apps/mobile/app/(tabs)/ayarlar/` altında doldurulan ekranlar (`index`, `gorunum`, `okuma`, `mushaf`, `erisilebilirlik`, `kaynaklar`, `kurul`, `hakkinda`) ve yeni `gelistirici/oz-test.tsx`; `apps/mobile/app/onboarding/index.tsx` (tanıtım)
- `apps/mobile/src/features/settings/` (depo, göç, ekranlar), `apps/mobile/src/lib/telemetry.ts` eklemeleri, erişilebilirlik yardımcıları
- Öz test koşucusu ve yalnız `dev` pakete giren vektör modülü; açık kaynak lisans listesi üretimi; `.tmp/a32/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A32-ayarlar-erisilebilirlik-oz-test.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A31](./A31-hadis-ve-risale-okuyuculari.md) · Sonraki: [A33](./A33-uctan-uca-test-ve-ic-dagitim.md)
