# A25 · Seçim, kelime kartı, Bağlantılar paneli, geri dönüş

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `arayuz-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A25`

## Amaç
Okur bir kelimeye ya da aralığa dokunup anlamını, kökünü ve bağlantılarını görür, bir bağlantıya atlar ve tek dokunuşla okuduğu yere döner. Seçim her zaman çapaya çevrilir. Bağlantılar cihazda hesaplanmaz; paketteki `xref_idx` satırlarından ve çapadan türetilen yapısal bağlardan okunur. `q` derin bağlantıları aynı atlama kuralıyla açılır.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 Seçim, §7 Kelime kartı, §8 Bağlantılar paneli, §9 Atla ve dön
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §6 puanlama ve güven etiketleri, §8 yayın kuralı, §9–§13
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları (P-07, P-08)
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §4 Alt sayfalar, §7 Derin bağlantılar, §8 Gezinme kuralları
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (`SheetHost`, `ChipSlot`, derin bağlantı), §5, §7 (kelime kartı ve `kelime-kok`)
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2–§4, §8, §11 (`fromRoute`, `toUnitSpan`, `snapSpan`)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.2 (`xref_idx`, `tr_root_index`), §3.3 `kelime-kok`, §4
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §8 Mobil bileşen testleri, §9 `testID`

## Kapsam
**Yapılır**
- Seçim modeli (`packages/reader-core`), Mod C ve meal için "Seç" düğmeli yol, `SelectionToolbar`.
- `WordCard` ve `kelime-kok` paketine bağlı satırlar.
- Bağlantılar paneli: çözümleyici, gruplar, gerekçe çipleri, güven etiketleri, katlama, panelin iç geri yığını.
- Geri dönüş yığını, kırıntı izi, `ChipSlot` içinde `BackChip`, Android geri tuşu sırası.
- `app/[...capa].tsx` derin bağlantı rotası (tek yakalayıcı rota; bu aşamada `q` türü); "Paylaş"ta derin bağlantı.

**Yapılmaz**
- Vurgula ve Not eylemleri ([A30](./A30-defterim-ve-ilerleme.md)); "Kaynak kopyala" (OD-8, sonraki sürüm); Dinle (A27 ekler); Mod A seçimi (A26); Mod B (A40).
- Öteki çapa türlerinin `[...capa].tsx` içindeki çözümü (`tf`, `rn`, `h`, `ht`, `meal`) ve `sayfa/[no].tsx`: MM-14 kapanınca hedef ekranın aşamasında (ör. A31). `ara?q=…&kapsam=…` bir çapa değildir; Expo Router rota parametreleriyle açılır ve ekran onları A28'de okur.
- Risale lügat, ibare ve haşiye kartları (A31); Ara ekranı (A28); bağlantı oyu ve "Önerilen" listesi (v1.x).

## Tedarik
Araştırma tarihi 2 Kasım 2026. Bu aşama içerik metni (Kur'an, meal, tefsir, hadis, Risale) almaz: `data/gelen/` altına dosya, `pipeline/sources/` altına kayıt yoktur. Panel ve kelime kartı paketlerdeki satırları okur (`xref_idx` A18'den, `kelime-kok` A17'den, meal A16'dan gelir); testler "Deneme" diye başlayan sentetik fikstürle çalışır. Dışarıdan yalnız kitaplık alınır. Sürümler Expo SDK 58 paket listesinden (`expo` 58.0.22 içindeki `bundledNativeModules.json`) ve npm kayıtlarından alındı. Cihaz davranışı (sürükleme, Android geri tuşu, seçim) paket kaydı ve testlerle doğrulanır; cihaz denemesi kullanıcıya bırakılır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Alt sayfa (`SheetHost`: kelime kartı ve Bağlantılar paneli) | `@gorhom/bottom-sheet` 5.2.14 (npm, 9 Mayıs 2026; [npm](https://www.npmjs.com/package/@gorhom/bottom-sheet), [GitHub](https://github.com/gorhom/react-native-bottom-sheet) etiketi `v5.2.14`, commit `9bfbeb521b90d525791a3400a68eec523ad7e444`; TypeScript, npm arşivi); [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) | A24.0'da (ya da öncesinde) kurulur; A25.0 sürümü paket kaydından doğrular: `pnpm --filter @mutalaa/mobile add @gorhom/bottom-sheet` | npm kaydı: 808 dosya, 1.328.755 bayt açık boyut; bağımlılıkları `@gorhom/portal` 1.0.14 ve `invariant`; eş bağımlılıkları `react-native-gesture-handler` `>=2.16.1` ve `react-native-reanimated` `>=3.16.0` ya da `>=4.0.0-`. SDK 58 listesi Reanimated 4.7.1 ve Gesture Handler ~3.3.0 verir. Kitaplık `Gesture.Pan()` ve `GestureDetector` kullanır (`BottomSheetDraggableView`, `BottomSheetHandleContainer`, `BottomSheetBackdrop`); Gesture Handler 3.4.0'ın `GestureDetector`'ı eski `Gesture` nesnelerini eski dedektöre devreder (`src/v3/detectors/GestureDetector.tsx`) ve paket `Gesture`, `PanGestureHandler`, `State`, `TextInput`'u dışa aktarır. Kitaplığın `src/` klasöründe `BackHandler` yoktur ve sorun #2781 donanım geri tuşunun işlenmediğini bildirir: geri tuşu sırasını uygulama kurar (A25.5). Sorun listesinde #2734 (5.2.14'te `Dimensions` değişiminde `window` hatası; Reanimated v3 ve Gesture Handler v2 ile bildirilmiş) ve Reanimated 4.6 ve üstünde "Dependencies should only be used on the web" uyarıları vardır; Gesture Handler 3'te `GestureDetector` yerel görünümdür (yükseltme rehberi), bu yüzden sürükleme cihaz denemesinde izlenir | Expo Router `formSheet` sunumu (`react-native-screens` 4.30.1, `sheetAllowedDetents`; rota tabanlıdır, tek `SheetHost` modeline uymaz) ve `@lodev09/react-native-true-sheet` 4.0.1 (npm, 30 Ekim 2026; etiket `v4.0.1`, commit `cc074e1c94762e9c3280bf1b631d630054fa6072`; yerel alt sayfa, Fabric, `react-native` `>=0.82.0`, `react-native-reanimated` `>=4.1.0`). Değişiklik yalnız `/karar` ile (K-29) |
| Pano (Kopyala eylemi) | `expo-clipboard` 58.0.4 (npm, 21 Ekim 2026; SDK 58 listesi `~58.0.4`; `expo/expo` deposunda `packages/expo-clipboard`; TypeScript, npm arşivi); API `Clipboard.setStringAsync(text, options)` ([belge](https://docs.expo.dev/versions/latest/sdk/clipboard/)) | `pnpm --filter @mutalaa/mobile exec expo install expo-clipboard` (sürümü SDK listesinden seçer) | npm kaydı: 84 dosya, 268.393 bayt açık boyut, bağımlılık yok; eş bağımlılıkları `expo`, `react`, `react-native`; etiketler `latest` 58.0.4, `sdk-57` 57.0.2. Belge Android 13 ve üstünde pano önizlemesini gizleme seçeneğini (`android.isSensitive`) anlatır; Kur'an metni için seçenek gerekmez | `@react-native-clipboard/clipboard` 1.16.3 (npm, 28 Haziran 2025; topluluk paketi) |
| Paylaş eylemi (metin ve derin bağlantı) | React Native `Share.share({ message })` (çekirdek, `react-native` 0.88.1, npm 27 Ekim 2026; [belge](https://reactnative.dev/docs/share)); `message`, Android'de `title`, iOS'ta `url` | Yok (çekirdek) | Belge: Android'de söz her zaman `sharedAction` ile çözülür, iOS'ta kullanıcı kapatırsa `dismissedAction` döner. `expo-sharing` 58.0.21 (npm, 28 Ekim 2026) dosya paylaşır ve gelen paylaşımı alır ([belge](https://docs.expo.dev/versions/latest/sdk/sharing/)); metin paylaşımı için değildir, bu yüzden kurulmaz | `expo-sharing` 58.0.21 (yalnız dosya kartı gerekirse) |
| Seçim aralığı ofseti (MM-15, OD-2) | Hazır kitaplık seçilmedi; v1 yolu kendi kodumuzdur: "Seç" düğmesi (A25.2). React Native `Text` seçim aralığı bildirmez (`reactnative.dev/docs/text` sayfasında `onSelectionChange` yok); `TextInput` bildirir ([belge](https://reactnative.dev/docs/textinput)) | Yok (çekirdek ve kendi kodumuz) | `Text` sayfasında 334 satırda `onSelectionChange` eşleşmesi 0; `TextInput` belgesinde `onSelectionChange` var ve `multiline={true}` ile `editable={false}` birlikte anılır. İncelenen hazır kitaplıklar: `@rob117/react-native-selectable-text` 2.1.0 (18 Eylül 2025) ve `@wekor/react-native-selectable-text` 1.0.0 (11 Mayıs 2026) Fabric bileşenidir ama yalnız özel bağlam menüsü ve `highlightedText` verir, ofset vermez; `@majornutcracker/react-native-selectable-text` 1.2.1 `react-native-webview` üstünde HTML içindir; `react-native-enriched-markdown` 1.1.1 markdown içindir; `react-native-advanced-selectable-text` 0.1.3 Skia ile çizer; `react-native-wiser-selectable-text` 0.1.1 (1 Mart 2026) `onSelectionChange` ile `start`, `end` verir, ama ViewManager tabanlıdır (Fabric bileşeni değil), git deposu bulunamadı ve sürümü 0.1.x'tir | Salt okunur `TextInput` (yalnız meal ve Türkçe paragraf; iç içe `onPress` taşımaz); `react-native-wiser-selectable-text` 0.1.1 (prototip) |
| Animasyon ve jest altyapısı | SDK 58 paket listesi: `react-native-reanimated` 4.7.1, `react-native-worklets` 0.13.0, `react-native-gesture-handler` ~3.3.0, `react-native-screens` ~4.30.1; `react-native` 0.88.1 | A21'de kurulur (`expo install`); A25.0 sürümleri doğrular | npm kaydı: Reanimated 4.7.1 (2 Ekim 2026) `react-native` `0.86 - 0.88` ve `react-native-worklets` `0.13.x` ister. npm'de `react-native-worklets` 0.13.1 (26 Ekim 2026) ve `react-native-gesture-handler` 3.4.0 (16 Ekim 2026) daha yenidir; SDK listesi 0.13.0 ve ~3.3.0 verdiği için `expo install` bunları seçer | — |
| Derin bağlantı rotası | `expo-router` 58.0.29 (npm, 31 Ekim 2026) ve `expo-linking` 58.0.15 (28 Ekim 2026); SDK listesi `~58.0.29` ve `~58.0.15`. Dinamik rota notasyonu ([belge](https://docs.expo.dev/router/basics/notation/)); özel şema `scheme` ([belge](https://docs.expo.dev/linking/into-your-app/)) | A21'de kurulu | Belge sayfaları 2 Kasım 2026'da açıldı; `expo-router` eş bağımlılığı `@testing-library/react-native` `>= 14.0.0` ister | — |
| Bileşen testleri | `jest-expo` 58.0.13 (npm, 28 Ekim 2026; SDK listesi `~58.0.13`) ve `@testing-library/react-native` 14.1.0 (npm, 8 Ekim 2026) | A21'de kurulu | `@testing-library/react-native` 14.1.0: `jest` `>=29`, `react` `>=19`, `react-native` `>=0.78` ve `test-renderer` `^1.0.0` (1.3.1) ister; Node.js `^22.13.0` ya da `>=24` (seçim Node.js 24 LTS). `jest-expo` `@react-native/jest-preset` `^0.88.1` ister (0.88.1 yayımlandı) | — |

Kendimiz yapacağımız işler: seçim modeli ve çapaya çeviri (`packages/reader-core/src/selection.ts`), Bağlantılar çözümleyicisi (`links/`), geri dönüş yığını (`backstack.ts`), `SelectionToolbar` ve "Seç" akışı, `WordCard`, `LinkPanel`, `ChipSlot` ve `BackChip`, derin bağlantı rotası `app/[...capa].tsx`. Hazır karşılıkları yoktur: hepsi çapa gramerine ve paket şemasına bağlıdır.

## Adımlar
### A25.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin (npm kayıtları, GitHub etiketleri, belge sayfaları) açıldığını ve sürümlerin güncel olduğunu doğrula; açılmayan adresin yerine yedek adayı kullan.
- Bu aşama içerik dosyası indirmez: `data/gelen/` altına dosya ve `pipeline/sources/` altına kayıt yoktur. Kitaplıklar `expo install` ya da `pnpm add` ile kurulur; sürüm Expo SDK'nın `bundledNativeModules` listesinden ve paket kaydından (`pnpm-lock.yaml`, `apps/mobile/package.json`) doğrulanır.
- `@gorhom/bottom-sheet` için: kurulu sürüm ile eş bağımlılıkların (Reanimated, Gesture Handler) SDK listesindeki sürümlerle uyuştuğunu doğrula; `GestureDetector`'ın eski `Gesture.Pan()` nesnelerini kabul ettiğini Gesture Handler kaynağında (`src/v3/detectors/GestureDetector.tsx`) denetle (3.4.0'da kabul eder); kitaplığın sorun listesindeki #2734 ve #2781'in durumunu yeniden oku.
- **Bitti sayılır:** Tedarik tablosundaki her kitaplığın sürümü `pnpm-lock.yaml`'da sabit ve tabloyla aynı (fark varsa gerekçesiyle tabloya işlenmiş); `pnpm --filter @mutalaa/mobile typecheck` yeşil; doğrulama sonuçları dokümanda.

### A25.1 · Doğrulamalar ve kararlar
- `arastirmaci` (seçilen SDK için): Tedarik bulgularını yeniden sına. React Native `Text` seçilen aralığın ofsetini bildirmez; v1 yolu "Seç" düğmesidir, salt okunur `TextInput` ve `react-native-wiser-selectable-text` prototip adayıdır (MM-15, OD-2). @gorhom/bottom-sheet 5.2.x seçilen SDK, Reanimated 4 ve Gesture Handler 3 ile çalışır ve Android geri tuşunu işlemez (A25.5'te uygulama işler). Panoya kopyalama `expo-clipboard`, metin paylaşımı React Native `Share` ile yapılır.
- Sonucu `/belge-esitle` ile Mobil mimari §7.3 ve §15 (MM-15) ile Okuma deneyimi §3 ve §15 (OD-2) maddelerine işle.
- Belgeler arasında ayrışan değerler eşitlendi (19 Ekim 2026): grup sırası ve "Önerilen"in v1.x'te olması Okuma deneyimi §8 ve Bağlantı modeli §7, §10; güven etiketlerinin koşulları ve eşikleri Bağlantı modeli §6, ekranda yazılan adları Okuma deneyimi §8 (OD-4 çözüldü); yükseklik %40 → %90 Mobil ekranlar §4; derinlik sınırı 12 Okuma deneyimi §9; yığın `useReader`'da, bellekte (Mobil mimari §5; Bağlantı modeli §11).
- İki âyete yayılan seçimde öneri uygulanır: âyet başına bir parça (OD-1).
- **Bitti sayılır:** doğrulama sonuçları dokümanda.

### A25.2 · Seçim modeli ve eylem çubuğu
- `packages/reader-core/src/selection.ts`: kelime aralığı `q:S:A:i-j` olur; tek kelime `q:S:A:i` yazılır, `i-i` yazılmaz. Türkçe metinde karakter aralığı kelime sınırına genişletilir ve `meal:elmalili:S:A@a-b` olur. Ofsetler kod noktasıdır; dönüşüm yalnız `packages/anchors` (`cpToUtf16`, `utf16ToCp`, `snapSpan`) ile yapılır.
- Mod C ve meal: uzun basış işletim sisteminin seçimini açar ve sistemin "Kopyala"sı her durumda çalışır. Uygulama aralığı, ofset veren olgun bir hazır kitaplık olmadığından (Tedarik) köprü hazır olana kadar üst çubuktaki "Seç" düğmesiyle kurar: "Başlangıç kelimesine dokun" → "Bitiş kelimesine dokun"; her adımda "Vazgeç".
- `SelectionToolbar` yüzen araç çubuğudur, alt sayfa sayılmaz. Bu aşamadaki eylemler: Bağlantılar, Kopyala (`expo-clipboard` ile Unicode metin ve okunur adres), Paylaş (React Native `Share` ile metin ve derleme türünün şemasıyla `…://q/2/255`), Tefsir. Âyet sonu işaretine dokunmak âyeti seçer ve çubuğu açar. Mushaf biçiminde âyete dokununca çubuğun üstünde mealin ilk satırları görünür.
- **Bitti sayılır:** seçim testleri (kanonik biçim, kelime sınırına genişletme, BMP dışı karakterli ofset, iki âyete yayılan seçim) ve "Seç" akışı testi yeşil.

### A25.3 · Kelime kartı
- `WordCard` tek `SheetHost` içinde %40'ta açılır; okuyucu, kelime kartın üstünde kalacak biçimde kayar. Satırlar Okuma deneyimi §7'deki gibidir: Arapça kelime (`quran_word.text_uthmani`) ve "Bakara 255 · 3. kelime" biçiminde konum; Türkçe anlam; kök harfleri ve "Bu kök Kur'an'da N yerde geçer"; lemma ve kısa morfoloji. Kelime sesi satırı gizlidir (Açık soru).
- Sure adı gösteren her etiket (kelime kartındaki konum, kırıntı izi, `BackChip`) adı `core`'daki `sure` tablosundan alır. Tablo boşsa (sure adları A11.3'te `core`'a girer; A24 onları beklemeden ilerler) sayısal biçim kullanılır: "2:255 · 3. kelime", "↩ Okuduğun yere dön (2:255)". Ad elle yazılmaz.
- Anlam, kök ve lemma `kelime-kok` paketinden okunur (İçerik paketleri §3.3). Paket bağlı değilse bu satırlar ve "Kökü incele" boşluk bırakmadan gizlenir, uyarı gösterilmez. Paket var ama anlam onaysızsa "Anlam henüz onaylanmadı"; `dev` ve `internal`'da taslak `UnverifiedBadge` ("doğrulanmamış") ile görünür (K-25, K-42).
- Eylemler: Kökü incele (paket varsa), Bu kelime nerede geçiyor?, Âyetin tefsiri, Kopyala. Not ve Vurgu A30'da eklenir.
- Kart yukarı çekilince ya da "Bu kelime nerede geçiyor?" seçilince aynı alt sayfa Bağlantılar paneline büyür (%90); ikinci sayfa açılmaz. "Kapat" ve Android geri tuşu kartı kapatır. Açılış bütçesi 100 ms'dir (öneri); süre geliştirme günlüğüne yazılır.
- `testID`: `kelime-karti`.
- **Bitti sayılır:** RNTL testleri yeşil: `kelime-kok` varken ve yokken satırlar; paket var ama anlam onaysızken `dev` ve `internal` bayraklarında taslak "doğrulanmamış" rozetiyle görünür, `public` bayrağında "Anlam henüz onaylanmadı" yazar (Test stratejisi §8).

### A25.4 · Bağlantılar paneli
- Çözümleyici `packages/reader-core/src/links/` altında Bağlantı modeli §9 tablosunu uygular. Bu aşamadaki girişler: Kur'an kelimesi, Kur'an ifadesi, meal içindeki Türkçe kelime ve ifade. Risale ve tefsirdeki Arapça ibare A31'dedir.
- Sorgular paketteki `xref_idx` tablosunu kullanır (İçerik paketleri §3.2; Bağlantı modeli §13). `xref` adı yalnız editoryal veritabanındaki tablodur. Kur'an seçimi `toUnitSpan` ile uç birime ve kelime konumu aralığına çevrilir (`q:2:255:3-7` → `q:2:255`, `[3,8)`). Âyet ↔ meal ve âyet ↔ tefsir bağları çapadan türetilir, `xref_idx`'te aranmaz. Türkçe ifade sorgusu `packages/search` normalizasyonuyla kurulur.
- Gruplar sabit sırayla gelir: Kur'an, Meal, Tefsir, Hadis, Risale-i Nur; boş grup gizlenir. Grup içinde sıra güven etiketi, puan, metin sırasıdır; "Metin sırası" düğmesi mushaf ya da kitap sırasına geçirir.
- Satır: okunur adres (paketteki `unit.label`), eşleşen aralığı vurgulu kısa parça, en çok iki gerekçe çipi ve "+N", yazılı güven etiketi. `folded = 1` satırlar "Daha fazla (otomatik) · N" altında katlıdır; `red` satır pakete zaten girmez (P-07). İnsan onayı isteyen türde (`atif`, `iktibas`, `ima`, `konu`) `approved = 0` satır yalnız `dev` ve `internal` paketlerindedir ve "Aday" rozetiyle görünür; otomatik türler (`kok`, `lemma`, `benzer_ayet`, `anlamsal`) `confidence ≥ 0,50` ile her derlemede gelir (Bağlantı modeli §8).
- Hedef paketi cihazda yoksa satır "paket gerekli" etiketi taşır ve atlamaz; derlemede yoksa görünmez. Boş sonuç: "Bu seçim için bağlantı bulunamadı · Tam ifadeyi ara" (Ara rotasına gider).
- Panelin iç geri yığını (kelime → kök → lemma) atlama yığınından ayrıdır; panel kapanınca silinir.
- `testID`: `baglanti-0`, `baglanti-1` …
- **Bitti sayılır:** çözümleyici ve panel testleri sentetik `xref_idx` fikstürüyle yeşil: grup sırası, katlama, etiket eşlemesi, eksik paket satırı, yapısal meal bağı.

### A25.5 · Geri dönüş yığını ve çip yuvası
- Saf işlevler `packages/reader-core/src/backstack.ts` içindedir: it, geri, başlangıca dön, burada kal. Kayıt `{ rota, çapa, ofset, seçim, biçim, gerekçe }`; derinlik 12, aşılınca başlangıç korunur ve en eski ara kayıt düşer. Durum `useReader` deposundadır (bellek).
- Her atlamadan önce bulunulan konum yığına yazılır; sayfa çevirme, kaydırma ve biçim değişimi atlama sayılmaz. Kur'an hedefi Oku sekmesinde açılır (`router.navigate('/oku')`).
- Kırıntı izi panelin başında ve zincir açıkken okuyucunun üst çubuğu altında görünür. `ChipSlot` zincir açıkken `BackChip` gösterir: "↩ Okuduğun yere dön (Bakara 255)" ve "Burada kal", iki ayrı 44 pt hedef. Ses çipi A27'de aynı yuvaya girer; iki çip birlikte görünmez.
- Zincir açıkken `reading_position` yazılmaz; "Burada kal" bulunulan yeri yazar.
- Android geri tuşu sırası Mobil ekranlar §8 kural 3'teki gibidir: alt sayfa → seçim → yığında bir adım → yönlendirici → Oku kökünde arka plan. `@gorhom/bottom-sheet` donanım geri tuşunu işlemez (Tedarik); sırayı uygulamada kayıtlı tek `BackHandler` dinleyicisi uygular.
- `testID`: `geri-don-cipi`.
- **Bitti sayılır:** yığın testleri yeşil: 5 adımlı zincir, kırıntı izi, dön, burada kal, derinlik sınırı, geri tuşu sırası.

### A25.6 · Derin bağlantılar ve cihaz denetimi
- `app/[...capa].tsx`: yol `fromRoute` ile çapaya çevrilir (`q/2/255/3-7` → `q:2:255:3-7`) ve `packages/anchors` ile doğrulanır (Çapa şeması §11; karakter aralığı `?aralik=` sorgusundadır). Geçerli hedef bir atlamadır: bulunulan konum başlangıç olarak yığına yazılır, hedef okuyucu deposuna yazılır, `router.replace('/oku')` çağrılır. `q/2/255/3` kelimeyi seçip kartı açar; `?panel=baglantilar` paneli açar.
- Geçersiz ya da aralık dışı adres (`q/2/300`) en yakın âyete yuvarlanmaz; Oku açılır ve "Bağlantı geçersiz" uyarısı görünür.
- `WordCard`, `LinkResult` (bütün güven etiketleriyle) ve `ChipSlot` Tasarım vitrinine eklenir.
- Cihaz denemesi kullanıcıya bırakılır (CLAUDE.md, çalışma düzeni 3): `q/2/255`, `q/2/255/3-7`, `q/2/300` bağlantıları ile kelime kartı, panel ve geri dönüş çipi cihazda açılıp görüntülenir; komutlar Doğrulama bölümündedir. Claude Code uygulamayı çalıştırmaz, görüntü almaz ve incelemez; aşamayı bekletmez, ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" diye yazılır.
- Gerçek `xref_idx` satırları A18 ile gelir. O zamana kadar panel yapısal bağlarla denetlenir: meal `core`'daysa (A16) Meal grubu, A13'ün sentetik `tefsir-test-ornek` paketi (yalnız `dev`) Tefsir grubu; hiçbiri yoksa boş durum kartı.
- **Bitti sayılır:** derin bağlantı testleri yeşil; geçersiz adres testi yuvarlama yapmadığını gösterir; rapor temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/reader-core test` yeşil: seçim, çözümleyici, geri dönüş yığını.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: kelime kartı (paketli ve paketsiz), Bağlantılar paneli (gruplama, gerekçe, güven, katlama), geri dönüş çipi, onay görünürlüğü (Test stratejisi §8).
- [ ] Seçim çapaları gramere uyar: tek kelime `q:S:A:i`, aralık `q:S:A:i-j`, meal `meal:elmalili:S:A@a-b`; ofsetler kod noktası (test).
- [ ] `mutalaa-dev://q/2/255` Bakara 255'i ve geri dönüş çipini gösterir; `q/2/300` "Bağlantı geçersiz" uyarısı verir ve yuvarlama yapmaz (derin bağlantı testi; cihaz görüntüsü kullanıcıya bırakıldı).
- [ ] Zincir açıkken `reading_position` yazılmaz; "↩ Okuduğun yere dön" başlangıç çapasına ve ofsetine döner (test).
- [ ] Grup sırası, güven eşikleri, yükseklik, derinlik ve kalıcılık belgelerdeki değerlerle uygulandı (A25.1 maddesi; test).
- [ ] Onaysız anlam `dev` ve `internal` bayraklarında "doğrulanmamış" rozetiyle görünür, `public` bayrağında "Anlam henüz onaylanmadı" yazar; `approved = 0` aday bağlantı "Aday" rozetiyle `dev` ve `internal`'da görünür (test).
- [ ] Tedarik tablosundaki kitaplık sürümleri `pnpm-lock.yaml`'da sabittir; A25.0 doğrulama sonuçları dokümandadır.
- [ ] `arayuz-denetcisi` raporunda engelleyici bulgu yok (kod ve test incelemesi; cihaz görüntüleri kullanıcıya bırakıldı).

## Doğrulama
```bash
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
pnpm --filter @mutalaa/mobile list @gorhom/bottom-sheet expo-clipboard react-native-reanimated react-native-gesture-handler
```

### Kullanıcıya bırakıldı
Cihaz denemesi (CLAUDE.md, çalışma düzeni 3) kullanıcının işidir ve aşamayı bekletmez. Görüntüler `.tmp/a25/` altına gider (git dışı).
```bash
mkdir -p .tmp/a25
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"
adb exec-out screencap -p > .tmp/a25/q-2-255.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255/3-7"
adb exec-out screencap -p > .tmp/a25/q-2-255-3-7.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/300"
adb exec-out screencap -p > .tmp/a25/q-2-300.png
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://q/2/255?panel=baglantilar'"
adb exec-out screencap -p > .tmp/a25/panel.png
```

## Dikkat
- Çapa ayrıştırma ve biçimleme yalnız `packages/anchors` ile yapılır; elle dizgi birleştirilmez (`capa-gramer`).
- Kopyalama yalnız Tanzil Unicode metnini ve okunur adresi kopyalar; `search_text` ve glif kodu asla kopyalanmaz.
- `kelime-kok` her derlemede yer alır ama ayrı ve isteğe bağlı pakettir: cihazda yoksa kök, lemma ve anlam satırları ile "Kökü incele" görünmez ve eksiklik uyarısı gösterilmez.
- Yapay zekâ taslağı anlamlar "doğrulanmamış" rozetiyle görünür (K-25); onaysız taslak `public`'e girmez (P-08).
- Panel sonuç parçaları paketteki kanonik metinden gelir; testlerde sentetik metin "Deneme" diye başlar. Kur'an, meal ya da Risale metni test için elle yazılmaz.
- Alt sayfalar üst üste açılmaz; her sayfada görünür "Kapat" vardır; her jestin düğme karşılığı vardır (Tasarım sistemi §9).
- `@gorhom/bottom-sheet` Android donanım geri tuşunu işlemez; geri tuşu sırası A25.5'teki gibi uygulamada kayıtlı tek `BackHandler` dinleyicisindedir.
- Derin bağlantı şeması derleme türüne göre değişir (`mutalaa-dev`, `mutalaa-internal`, `mutalaa`); şema elle yazılmaz, `src/lib/env.ts`'den okunur.
- Commit kapsamları `mobile` ve `reader-core`.

## İnsan adımları
- Yok. Cihaz denemesi kullanıcıya bırakılır ve aşamayı bekletmez. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/`: `selection.ts`, `links/`, `backstack.ts`, güven etiketi eşlemesi, testler
- `apps/mobile/src/features/reader/`: `SelectionToolbar`, "Seç" akışı; `src/features/crossref/`: `WordCard`, `LinkPanel`, `LinkResult`, `ReasonChip`, `ConfidenceBadge`, `Breadcrumb`, `ChipSlot`, `BackChip`
- `apps/mobile/app/[...capa].tsx`; Tasarım vitrini ekleri
- Karar defterinde OD-1 önerisi; Tedarik doğrulama sonuçları bu dosyada; `.tmp/a25/` (git dışı, kullanıcının cihaz görüntüleri)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A25-secim-kelime-karti-baglantilar.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A24](./A24-okuyucu-mushaf-c.md) · Sonraki: [A26](./A26-mushaf-a.md)
