# A24 · Okuyucu: Mushaf C, okuma biçimleri, sayfalayıcı

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) (A11.2, A11.4–A11.6) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A24`

## Amaç
Kur'an okuyucusunun temeli kurulur: indirme gerektirmeyen Mod C (akan Unicode metin), üç okuma biçimi (Mushaf, Mushaf + Meal, Âyet âyet), sağdan sola sayfalayıcı, Fihrist ve tefsir görünümünün iskeleti. Okuyucu her konumu çapayla tutar; biçim, tema, yön ya da ekran yönü değişince aynı âyet görünür kalır. Okuyucu yalnız kanonik metni gösterir. Mod C'nin yazı tipi iki hazır adaydan (Amiri Quran, KFGQPC Hafs) görsel kaliteye göre seçilir.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §1–§6
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (`SheetHost`, çip yuvası), §5 (`useReader`, `reading_position`), §7 ortak sözleşme, §7.3, §7.4, §8, §9
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 (Oku yığını), §3 (Kur'an okuyucu, Fihrist, Tefsir satırları), §4 (Okuma ayarları)
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §6 (`PageView`, `AyahMarker`, `SurahHeader`, `AyahItem`, `MealPane`, `TefsirPane`), §9
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 ofsetler, §10 sayfa eşlemeleri
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.2 (`unit`, `quran_word`, `page_map`, `sure`)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 5 ve 7, §9 `testID`
- [Kaynaklar](../../04-icerik/01-kaynaklar.md#31-kuran-metni-fontlar-ve-mushaf-düzeni): §3.1 (`amiri-quran-font`, `kfgqpc-hafs-font`)
- [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) çıktısı: `quran_word` Tanzil satırları, cüz ve secde tablosu kararı, `page_map` kaynağı; ilerleme notunda biten adımlar
- [A21](./A21-mobil-iskelet.md) çıktısı: kilitlenen Expo SDK ve gömülü yazı tipleri; [A23](./A23-cihaz-veri-katmani.md) çıktısı: SQL yürütücü arayüzü

## Kapsam
**Yapılır**
- `packages/reader-core`: sayfa, satır ve kelime modelleri; sayfa ↔ âyet eşlemesi; içerik sorguları.
- Mod C çizimi (`AyahFlow`), `SurahHeader`, `Besmele`, `AyahMarker`, `SecdeMarker`, `JuzMarker`, `PageView`.
- Mod C yazı tipi seçimi (Amiri Quran ya da KFGQPC Hafs) ve sayfalayıcı kitaplığı kararı (`FlatList`, `react-native-pager-view`, FlashList).
- Üç okuma biçimi; telefonda "Sayfa | Meal" sekmesi ve etkin âyet altyazısı; tablet yatayda açık kitap.
- İki Elmalılı meali arasında gösterim: orijinal (`meal:elmalili`) ve "sadeleştirilmiş" etiketli güncel meal (`meal:elmalili-sade`); iki meal arasında seçim ve gösterim A16'dan bu aşamaya devredildi ([K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)). Seçim ayarı A32'dedir; mealin kendisi `core`'dan okunur, etiket metni arayüz dosyalarındadır.
- Sağdan sola sayfalayıcı, yön ayarı, etiketli düğmeler, odak modu, konum koruma, okuma konumu yazımı.
- Tek `SheetHost` ve "Aa" Okuma ayarları alt sayfası.
- Fihrist (`oku/fihrist`), tefsir görünümünün iskeleti (`oku/tefsir/...`), okuyucu parçalarının Tasarım vitrinine eklenmesi.

**Yapılmaz**
- Seçim, kelime kartı, Bağlantılar paneli, geri dönüş yığını, derin bağlantılar: [A25](./A25-secim-kelime-karti-baglantilar.md). Bu aşama yalnız `openWordCard(anchor)` çağrısını ve `useReader.returnStack` alanını bırakır.
- Mod A (A26), Mod B (A40), ses ve takip (A27), adla adres ayrıştırma ("Bakara 255") ve Ara (A28), yer imi, vurgu ve not işaretleri (A30).
- Ayar ekranları ve ekran okuyucu önerisi (A32); tablet yatayda çift mushaf sayfası [s2][s1] (v1.x); tefsir içeriği (A37).

## Tedarik
Araştırma tarihi 2 Kasım 2026; adresler, sürümler ve özetler 3 Kasım 2026'da yeniden doğrulandı. Hazır yapı önce gelir: sayfalayıcı, liste, ekranı açık tutma ve yazı tipleri hazırdır. Okuyucunun modeli, sorguları, sayfa eşlemesi ve çizim kodu bizimdir. Durum ve yerel depolama kitaplıkları (`zustand`, `@tanstack/react-query`, `react-native-mmkv`) ile test araçları (`jest-expo`, `@testing-library/react-native`) A21'de, Node SQLite sürücüsü A23'te gelir; bu aşama yeni durum kitaplığı ya da test aracı almaz. Sürüm değerleri Expo SDK 58 hattındandır (`expo` 58.0.22; sürüm tablosu `https://cdn.jsdelivr.net/npm/expo@58.0.22/bundledNativeModules.json`, 4.291 bayt; [A21](./A21-mobil-iskelet.md) başka SDK kilitlerse `expo install` o SDK'nın tablosundan seçer). Yerel kod taşıyan kitaplık (`react-native-pager-view`) yeni geliştirme derlemesi ister; JS kitaplığı (`@shopify/flash-list`) ve çalışma anında yüklenen yazı tipi istemez. Ölçülmeyen hücre A24.0'da ölçülür.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Sağdan sola sayfalayıcı (MM-10), başlangıç seçimi | `FlatList` (React Native 0.88.1 çekirdeği, Expo SDK 58 şablonu) | Yok (çekirdek bileşen) | Kitaplık eklenmez; 50 sayfa çevirme ölçümü A24.1'de (cihaz ölçümü kullanıcıya bırakılır) | `react-native-pager-view` (sonraki satır) |
| Yerel sayfalayıcı, aday (MM-10) | `react-native-pager-view` 9.0.7 (Expo SDK 58 `bundledNativeModules.json` sürümü; npm `latest` 9.0.11, 27 Ekim 2026); git `callstack/react-native-pager-view` etiketi `v9.0.7` = `229cad5785193a5c0b1ce8fa8415d92cfb65ebce`, `v9.0.11` = `ffec5eb8c0daa1fd545ae5d4ac60303b88396c68`; biçim: npm paketi, yerel modül | `pnpm --filter @mutalaa/mobile exec expo install react-native-pager-view` (sürümü SDK tablosundan seçer); yalnız A24.1 `FlatList`'i yetersiz bulursa; yerel modüldür, eklenince yeni geliştirme derlemesi gerekir (EAS derlemesi ücretlidir: kural 11 gereği tahmini maliyet söylenir) | README (`v9.0.7`, HTTP 200): `layoutDirection` (`ltr` / `rtl` / `locale`, varsayılan `locale`), `offscreenPageLimit`, `setPageWithoutAnimation(index)`, `orientation`, `overdrag`; 7.x'ten beri yalnız yeni mimari; GitHub sürüm notları 9.0.4–9.0.11 (3 Kasım 2026): dokunma, güvenli alan ve sayfa durumu düzeltmeleri, `layoutDirection` kaydı yok; `bundledNativeModules.json` SHA-256 `3b2c9d80113acb8ff74b6203c884196f70299bce4da7bb4b46a7faa41d41300d` | `FlatList`; SDK 57 hattında `react-native-pager-view` 8.0.2 |
| Dikey liste (Âyet âyet), aday | `@shopify/flash-list` 2.3.2 (Expo SDK 58 sürümü; npm `latest` 2.3.3, 1 Ekim 2026); git `Shopify/flash-list` etiketi `v2.3.2` = `8c1375e95a795fcc7e7fbdeaf3059ccfb6cad50c`, `v2.3.3` = `527d7678190f4f0137f14383ff560efa7fccc9fb`; biçim: npm paketi, yalnız JS | `pnpm --filter @mutalaa/mobile exec expo install @shopify/flash-list`; yalnız `FlatList` yetmezse | README (`v2.3.2`): v2 yalnız yeni mimari ve yalnız JS, boyut tahmini gerekmez; kullanım belgesinde `horizontal` ve `inverted` var, sağdan sola düzen anlatılmıyor (yatay sayfalayıcı için aday değil); sürüm notları (3 Kasım 2026): 2.3.0 `inverted` ekledi, 2.3.1 `maintainVisibleContentPosition`'ı yatay listelere açtı, 2.3.3 hızlı kaydırmada boş satır düzeltmesi getirdi (SDK 58 sürümü 2.3.2'dir) | `FlatList`; SDK 57 hattında `@shopify/flash-list` 2.0.2 |
| Mod C Arapça yazı tipi, aday 1 | Amiri Quran, `AmiriQuran-Regular.ttf`; `github.com/google/fonts` commit `6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec`, yol `ofl/amiriquran/`; kaynak kaydı `amiri-quran-font` | `curl -L` ile `https://raw.githubusercontent.com/google/fonts/6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec/ofl/amiriquran/AmiriQuran-Regular.ttf` → `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` (A15.0 ve A21.0 aynı klasörü açtıysa özet karşılaştırılıp yeniden kullanılır); `assets/fonts/` kopyası `expo-font` yapılandırma eklentisiyle gömülür (A21) | HTTP 200 (3 Kasım 2026; yeniden indirilen kopyanın SHA-256'sı aynı); TrueType, 136.920 bayt, SHA-256 `e2a47644762d16bdfb6d33e0d8db8c6ff30beae84150ef5a705316bbd829455c`; ad "Amiri Quran Regular", sürüm 1.003, 1.446 glif; Tanzil Uthmani'nin (`quran-uthmani.txt`, 6.236 satır) boşluk dışı 68 ayırt edici kod noktasının 68'i fontta; işaret kümesinin (U+06DD, U+06DE, süsleme parantezleri U+FD3E ve U+FD3F, Arapça-Hint rakamları vb.) 15 kod noktasının 15'i fontta; OpenType: GSUB (`ccmp`, `init`, `medi`, `fina`, `rlig` …) ve GPOS (`mark`, `mkmk`, `curs`, `kern`) var; ölçüm iki ayrı araçla (kendi betiğimiz ve fontTools 4.68.0) aynı çıktıyı verdi; Türkçe Latin harfleri yok | `@expo-google-fonts/amiri-quran` 0.4.1 (npm, 27 Ağustos 2025; `AmiriQuran_400Regular.ttf`, 136.256 bayt) |
| Mod C Arapça yazı tipi, aday 2 | KFGQPC Hafs 3.0, `KFGQPC-Hafs-V30.zip`; sayfa `https://fonts.qurancomplex.gov.sa/hafs-reading/`; kaynak kaydı `kfgqpc-hafs-font` | `curl -L` ile `https://fonts.qurancomplex.gov.sa/fonts/KFGQPC-Hafs-V30.zip` (form yoktur) → `data/gelen/kfgqpc-hafs-font/<YYYY-AA-GG>/`, zip aynı klasörde açılır; karşılaştırma için `assets/fonts/` kopyası `expo-font`'un `useFonts` işleviyle çalışma anında yüklenir (yeni yerel derleme gerekmez); seçilirse `expo-font` eklentisinin `fonts` listesine eklenir ve bir sonraki derlemede gömülür (Expo belgesi eklentiyi Android ve iOS için önerir) | HTTP 200 (3 Kasım 2026; sayfa 68.924 bayt ve güncel sürüm olarak 3.0'ı yazar); zip 844.410 bayt (`Content-Length`; `Last-Modified` 13 Eylül 2026), SHA-256 `ddf52d0f6919b0a9cfb1e9cc048d41d88e695f973455fea3c9973837295a324c` (yeniden indirilen kopyada aynı); içindeki `KFGQPC Hafs V30.ttf` 301.356 bayt, SHA-256 `c9dd7e71a454565b13d89e5e6f2663a918acb0a20a23eea31eccb32a3aeec47a`, ad "KFGQPC HAFS Uthmanic Script Regular", sürüm 3.0, 1.572 glif, Arapça bloğunda 255 kod noktası; Tanzil Uthmani'nin 68 kod noktasının 68'i fontta; işaret kümesinin 13'ü fontta (U+FD3E ve U+FD3F yok); OpenType: GSUB (`init`, `medi`, `fina`, `calt`, `liga`, `rlig`) ve GPOS (`mark`, `mkmk`, `curs`, `kern`) var; ölçüm iki ayrı araçla (kendi betiğimiz ve fontTools 4.68.0) aynı çıktıyı verdi; Türkçe Latin harfleri yok | GitHub aynası `mustafa0x/qpc-fonts` commit `8a4f39d563ea69c994416a1692827e38156c548d`, `mushaf-v4-hafs/uthmanic_hafs_v22.ttf` (sürüm 2.2, 297.688 bayt, SHA-256 `a6e59510dcaf3ec99db49427321a035ed94af555ffc7d27e7f430b5fd5e179f8`; aynı kapsama sonuçları); Amiri Quran |
| Ekranı açık tutma | `expo-keep-awake` 58.0.3 (npm, 1 Ekim 2026; Expo SDK 58 `bundledNativeModules.json` değeri `~58.0.3`; `expo` paketinin de bağımlılığıdır) | `pnpm --filter @mutalaa/mobile exec expo install expo-keep-awake` | Expo belgesi (HTTP 200) `useKeepAwake`, `activateKeepAwakeAsync` ve `deactivateKeepAwake` işlevlerini anlatıyor | SDK 57 hattında `expo-keep-awake` ~57.0.2; "Ekranı açık tut" ayarı olmadan yalnız sistem ekran zamanaşımı |
| Alt sayfa (`SheetHost`) | `@gorhom/bottom-sheet` 5.2.14 (npm, 9 Mayıs 2026; [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları)); [A21](./A21-mobil-iskelet.md) kurar | A21'de `@gorhom/bottom-sheet@5.2.14`; A24 yalnız `SheetHost` kabuğunu yazar | Eş bağımlılıklar `react-native-gesture-handler >=2.16.1` ve `react-native-reanimated >=3.16.0 \|\| >=4.0.0-`; SDK 58 sürümleri (Gesture Handler ~3.3.0, Reanimated 4.7.1) karşılar | 5.2.x içinde bir önceki yama (A21) |
| Metin, Hareketi Azalt ve duyuru API'leri | React Native çekirdeği: `Text` (`selectable`, `onPress`, `textBreakStrategy`, `android_hyphenationFrequency`), `AccessibilityInfo.isReduceMotionEnabled()`, `AccessibilityInfo.announceForAccessibility()` | Yok (çekirdek) | `reactnative.dev/docs/text` ve `reactnative.dev/docs/accessibilityinfo` açılıyor (HTTP 200, 2 Kasım 2026) ve bu adları içeriyor; `writingDirection` ve iki yana yaslama davranışı A24.1'de | — |
| Kur'an metni, `page_map`, meal birimleri | `core` paketi (A10–A13 çıktısı); okuyucu yalnız bu paketi okur | A23'ün SQL yürütücü arayüzü; yerel `dev` `core` dosyası | A24.1'de `quran_word`, `page_map` ve işaret tablosunun doluluğu sayılır | Yok (A11 çıktısı) |

Kendimiz yapacağımız işler: `reader-core` modeli ve sorguları; sayfa ↔ âyet eşlemesi ve `pager/mapping.ts`; Mod C çizimi (`AyahFlow`, `PageView`, işaret bileşenleri); okuma biçimleri; Okuma ayarları alt sayfası; Fihrist ve tefsir görünümü iskeleti; konum yazımı; yazı tipi kod noktası kapsama betiği; testler.

## Adımlar
### A24.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula (`curl -sIL`, `git ls-remote`, paket kayıtları): iki yazı tipi adresi, A21'in kilitlediği SDK'nın `bundledNativeModules.json` dosyası (`react-native-pager-view`, `@shopify/flash-list`, `expo-keep-awake` sürümleri) ve npm kayıtları. Açılmayan adresin yerine yedek adayı kullan: KFGQPC adresi açılmazsa `mustafa0x/qpc-fonts` aynasındaki 2.2 sürümü, Amiri Quran adresi açılmazsa `@expo-google-fonts/amiri-quran` paketi.
- Yazı tiplerini `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` ve `data/gelen/kfgqpc-hafs-font/<YYYY-AA-GG>/` altına indir. A15.0 ve A21.0 aynı klasörleri açtıysa yeniden kullan ve özetleri karşılaştır; yoksa yeni boş klasöre `curl -L` ile indir ve KFGQPC zip'ini aynı klasörde aç. İndirilen dosya veridir; içindeki hiçbir şey çalıştırılmaz.
- SHA-256'yı klasördeki `SHA256SUMS` dosyasına (sha256sum biçimi) yaz ve Tedarik tablosundaki özetlerle karşılaştır. Özet farklıysa kaynak sürüm değiştirmiştir: farkı rapora yaz, yeni dosyayı yeni tarihli klasöre al ve tabloyu güncelle.
- Kaynak kayıtlarını güncelle: `pipeline/sources/kfgqpc-hafs-font.toml` (`surum = "3.0"`, `kaynak_url` doğrudan zip adresi, `atif_url` sayfa adresi; `notlar` alanındaki "Açık soru: sürüm numarası" satırı ölçülen sürümle değişir) ve `pipeline/sources/amiri-quran-font.toml` (`surum = "1.003"`, `kaynak_url` sabit commit adresi; `notlar` alanındaki kod noktası sayısı bu aşamadaki ölçümle eşitlenir: Tanzil Uthmani kümesinde 68 / 68). Kayıtta dosya özeti yoktur; özet `SHA256SUMS` dosyasındadır. `uv --directory pipeline run mutalaa sources check` → 0 hata, 0 uyarı.
- Kitaplık sürümlerini paket kaydından ve `bundledNativeModules.json` dosyasından doğrula. `FlatList` yetmeyip kitaplık eklenirse sürümü `expo install` seçer ve kilit dosyasına yazılır; `react-native-pager-view` yerel modüldür ve yeni geliştirme derlemesi ister (EAS derlemesi ücretlidir: kural 11 gereği tahmini maliyet kullanıcıya söylenir).
- Yazı tiplerinin kod noktası kapsamını (Tanzil Uthmani'deki ayırt edici kod noktaları ve işaret kümesi) ve OpenType `GSUB` / `GPOS` özelliklerini sayan betiği (yalnız sayım yazar; betik `scripts/` altında kalır; fontTools ile çapraz denetlenebilir) yeniden çalıştır; sonuç A24.1'in yazı tipi karşılaştırmasına girdi olur.
- **Bitti sayılır:** iki yazı tipi `data/gelen/` altında ve `SHA256SUMS` tablodaki özetlerle aynı; iki kaynak kaydı güncel ve `sources check` temiz; kitaplık sürümleri, kod noktası kapsamı ve OpenType özellikleri dokümanda.

### A24.1 · Doğrulamalar ve ön ölçümler
- `arastirmaci` (seçilen SDK için): iç içe `Text` parçalarında `selectable` ile `onPress`'in birlikte çalışması (Mobil mimari §7.3); `writingDirection` ve iki yana yaslama; `expo-keep-awake` (`useKeepAwake`); Hareketi Azalt ve `announceForAccessibility` API'leri; `react-native-pager-view` (`layoutDirection="rtl"`, `offscreenPageLimit`, `setPageWithoutAnimation`) ve FlashList'in A24.0'da doğrulanan sürümleriyle davranışı (MM-10).
- Yerel `dev` `core` dosyasında `quran_word`, `page_map` ve işaret tablosu dolu mu (A11 çıktısı). Boşsa A13'ün yayını A11'den önce yapılmıştır: `publish --flavor dev` yeniden çalışır ve `fetch-core.mjs` yeni `core`'u alır.
- Veriden okunur (metin elle yazılmaz): besmelenin Tanzil metninde ayrı satır mı yoksa ilk âyetin parçası mı olduğu (A10 çıktısı); `core`'da `page_map` düzeninin varlığı ve kaynağı (A11); Medine düzeninde iki sayfaya bölünen âyet olup olmadığı (OD-3); cüz ve secde tablosunun adı (A11 kararı).
- Yazı tipi seçimi görsel kaliteye göredir. Kapsama ve yazı özellikleri ölçüldü (A24.0): Tanzil Uthmani'nin boşluk dışı 68 kod noktasının 68'i iki yazı tipinde de var; ikisi de `GSUB` ve `GPOS` (`mark`, `mkmk`) tablolarını taşır; Amiri Quran süsleme parantezlerini (U+FD3E, U+FD3F) taşır, KFGQPC Hafs taşımaz. Karşılaştırma için vitrindeki Mod C Fâtiha sayfası iki yazı tipiyle çizilir (A24.6); KFGQPC Hafs karşılaştırmada çalışma anında yüklenir.
- Cihaz ölçümleri kullanıcıya bırakılır ve aşamayı bekletmez (CLAUDE.md, çalışma düzeni 3): U+06DD âyet sonu işaretinin rakamla birleşik çizimi; `FlatList` ile 50 sayfa çevirmede belirgin takılma olup olmadığı; iki yazı tipinin görsel karşılaştırması. Varsayılanlar: sayfalayıcı `FlatList`, Mod C yazı tipi Amiri Quran; kullanıcının cihaz ölçümü başka sonuç verirse `/karar` ile değişir. Asıl ölçüm sürüm derlemesinde A33'tedir.
- **Bitti sayılır:** sonuçlar dokümanda; sayfalayıcı kitaplığı ve Mod C yazı tipi kararı `/karar` ile ("FlatList yeterli" de bir karardır).

### A24.2 · `packages/reader-core`: model ve sorgular
- Sorgular parametreli SQL'dir ve A23'ün SQL yürütücü arayüzüyle çalışır: sayfanın âyetleri ve kelime sınırları (`page_map`, düzen `medine-604`), âyetin kelimeleri (`quran_word`), sure bilgisi (`sure`), sayfanın meal birimleri (`meal:elmalili:{s}:{a}`), âyet ↔ sayfa eşlemesi, cüz ve secde işaretleri (A11 tablosu).
- Okuyucu yalnız kanonik metni okur (`unit.text`, `quran_word.text_uthmani`). `search_text` ve arama tabloları okuyucu sorgularına girmez (Test stratejisi §5 test 5; A10 bu testi A24'e bıraktı).
- Bölünmüş âyet: meal başladığı sayfada tam verilir; sonraki sayfa "(önceki sayfadan)" satırıyla başlar (Okuma deneyimi §5).
- Sorgu anahtarları paket sürümünü içerir (`qk.page(page, coreVersion)`); içerik sorguları `contentQuery` ayarıyla çalışır.
- `core`'da `page_map` yoksa sayfalı Mod C çizilemez. Okuyucu Âyet âyet biçimine düşer ve Geliştirici menüsü uyarır (öneri; `/karar` ile kesinleşir).
- **Bitti sayılır:** `reader-core` testleri yeşil: okuyucu sorgularında `search_text` geçmez; yerel `dev` `core` dosyasıyla 1. sayfa `q:1:1`–`q:1:7`, 604. sayfa `q:114:6` ile biter, 0 ve 605 geçersiz (test 7; Node SQLite sürücüsü A23 kararıdır; dosya yoksa test atlanır).

### A24.3 · Mod C ve sayfa bileşenleri
- `src/features/reader/mushaf-c/AyahFlow.tsx` Mobil mimari §7.3'teki gibi: seçilen Mod C yazı tipi (A24.1; varsayılan Amiri Quran), `writingDirection: 'rtl'`, iki yana yaslı, satır yüksekliği 2,0–2,3 aralığında, boyut `arabicScale` ile. Yazı tipi adı tek yerde tanımlanır; seçim değişirse tek satır değişir. Kelimeler ayrı `Text` parçasıdır; paragraf `selectable`. Kısa dokunuş `openWordCard(anchor)` çağırır (A25 bağlar); uzun basışa uygulama seçimi bağlanmaz.
- Etkin âyet zemin tonu (`ses-ayet`), etkin kelime zemin ve alt çizgidir; renk tek başına anlam taşımaz.
- `SurahHeader` (tezhip çerçevesi, Türkçe ad `sure` tablosundan, erişilebilirlik başlığı "Bakara Sûresi, 286 âyet" biçiminde; `sure` tablosu boşsa, yani sure adları (A11.3) henüz gelmediyse, başlık, Fihrist ve sayfa duyurusu sure numarasını gösterir: "2. sûre"; ad elle yazılmaz), `Besmele` (A24.1 sonucuna göre; metin yalnız `core`'dan), `AyahMarker` (normal, etkin, seçili, secde), `SecdeMarker`, `JuzMarker`.
- `PageView` `React.memo` ile sarılır; veri çizimden önce sorgudan gelir; ses ilerlemesi sayfa özelliklerine girmez. Durumlar: hazır, yazı tipi yükleniyor, hata ("Yeniden dene").
- `testID`'ler çapa gramerini kullanır: `ayet-q:2:255`, `kelime-q:2:255:3`, `etkin-ayet-q:2:255` (Test stratejisi §9).
- **Bitti sayılır:** RNTL testleri yeşil: âyet ve kelime `testID`'leri, kelime dokunuşunun çapayı iletmesi, etkin âyet ve kelime stili.

### A24.4 · Okuma biçimleri ve Okuma ayarları
- `useSettings.readingLayout`: `mushaf`, `mushaf_meal` (varsayılan), `ayet_ayet`. Çizim yolu varsayılanı C (MM-13 kapandı).
- Mushaf + Meal: telefonda "Sayfa | Meal" `SegmentedControl` (varsayılan) ya da etkin âyet altyazı şeridi. `MealPane` sayfadaki âyetleri "2:255" etiketiyle listeler; âyete dokunmak meal paragrafını işaretler, meal paragrafına dokunmak âyeti tonlar. "Panelleri bağla" varsayılan açıktır.
- Âyet âyet: dikey liste; her zaman Mod C yazı tipi; öğede âyet numarası, Arapça, meal. Âyet öğeleri âyet sırasıyla dizilir.
- Düzenler Okuma deneyimi §4'teki gibidir: < 600 dp tek bölme; 600–899 dp ortalı sütun; ≥ 900 dp yatay açık kitap (sağda sayfa, solda meal).
- Meal birimi `core`'da yoksa (A16 meal yayını bitmeden ya da meal `public` derlemede onaysız olduğu için dışarıda kaldığında) meal bölmesi boş durum kartı gösterir; yer tutucu ya da sentetik meal metni yazılmaz.
- Tek `SheetHost` (Mobil mimari §4) kurulur: aynı anda tek alt sayfa, görünür "Kapat", Android geri tuşu önce alt sayfayı kapatır. "Aa" düğmesi Okuma ayarlarını açar (%60): biçim, çizim yolu, tema, Arapça ve Türkçe boyut. Değişiklik arkada anında görünür; ekrandaki ilk âyetin çapası korunur. Mod A ve B yalnız paketleri derlemede görünürse listelenir (Mobil mimari §7.4).
- **Bitti sayılır:** RNTL testleri yeşil: biçim değişiminde ilk görünen âyetin çapası aynı kalır; meal yokken boş durum kartı; görünür paket yokken Mod A ve B seçeneği listede yok.

### A24.5 · Sağdan sola sayfalayıcı ve konum
- `pager/mapping.ts` Mobil mimari §8'deki gibidir: `rtl`'de 1. sayfa indeks 603, indeks 602 sayfa 2; `ltr`'de sayfa − 1. `MushafPager` A24.1 kararıyla: `FlatList` ise `getItemLayout`, `windowSize={3}`, `initialNumToRender={1}`; `react-native-pager-view` ise yön yerel `layoutDirection` ile açıkça verilir (varsayılanı `locale`'dir ve arayüz soldan sağadır), beklenen indeks sayfa − 1'dir (sağdan sola düzende ilk çocuğun sağda durduğu A24.1'de doğrulanır) ve yalnız açık sayfa ile komşuları dolu çizilir. Eşleme işlevi her iki durumda tek yerde durur.
- Etiketli "Önceki sayfa" ve "Sonraki sayfa" düğmeleri her zaman görünür; sağdan sola düzende "Sonraki sayfa" soldadır. Yön ayarı değişince liste yeni başlangıç indeksiyle kurulur, açık sayfa korunur. Hareketi Azalt açıkken düğmeyle çevirme animasyonsuzdur (`scrollToIndex({ animated: false })`; pager-view'da `setPageWithoutAnimation`).
- Sürükleme başlayınca oynatıcıya `USER_SCROLLED` gönderecek bağlantı noktası bırakılır (A27 bağlar).
- Odak modu: kaydırınca ya da sayfanın ortasına dokununca çubuklar gizlenir, tek dokunuş geri getirir; "Ekranı açık tut" (`expo-keep-awake`) varsayılan açıktır ve cihaza özgüdür.
- Konum: ekran dönünce ya da alt sayfa kapanınca âyet ve ofset geri yüklenir. `reading_position` sayfa durduktan 1 saniye sonra MMKV kopyasıyla yazılır; `useReader.returnStack` boş değilken yazılmaz.
- Sayfa değişince `announceForAccessibility` ("Sayfa 42, Bakara Sûresi" biçiminde), en çok saniyede bir.
- **Bitti sayılır:** eşleme testleri ve konum yazımı testi (1 saniye gecikme, zincir açıkken yazmama) yeşil.

### A24.6 · Fihrist, tefsir iskeleti, vitrin ve görsel denetim
- `oku/fihrist`: sure listesi, cüz ızgarası, sayfa numarası ve "2:255" biçimli giriş (`packages/anchors` ile doğrulanır). Geçersiz giriş "Bu adres bulunamadı" der; adla arama A28'dedir.
- `oku/tefsir/[sure]/[ayet]` ve `TefsirPane`: "Elmalılı · Bakara 255–257" biçimli başlık, kapsanan âyet çipleri, "Takip et" (varsayılan açık). Paket yoksa "Elmalılı tefsiri indirilmedi · İndir (boyut)"; derlemede yoksa "Tefsir hazırlanıyor". Takip mantığı A13'ün sentetik `tefsir-test-ornek` paketiyle (yalnız `dev`'de bulunan fikstür) denenir; gerçek içerik `tefsir-elmalili` ile gelir (A37).
- `PageView`, `AyahMarker` durumları ve Mod C Fâtiha sayfası (iki aday yazı tipiyle) Tasarım vitrinine eklenir; vitrinin Arapça ve meal örnek alanı `core`'a bağlanır (A22).
- Görsel denetim kullanıcıya bırakılır ve aşamayı bekletmez (CLAUDE.md, çalışma düzeni 3). Bakılacaklar (`mobil-ekran` listesi): 1. sayfa ve Bakara 255'in bulunduğu sayfa (Fihrist'ten), üç tema; Mushaf + Meal "Meal" sekmesi; Âyet âyet; sağdan sola çevirme sırası; iki yazı tipinin karşılaştırması. `arayuz-denetcisi` 44×44 pt hedeflerini, etiketleri, Türkçe ve Arapça yönünü ve Tasarım sistemi §9'dan bu aşamaya düşen maddeleri kod ve test çıktısı üzerinden denetler.
- **Bitti sayılır:** `arayuz-denetcisi` raporu temiz; görsel denetim "kullanıcıya bırakıldı" diye ilerleme notunda yazılı.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/reader-core test` yeşil: test 5 (okuyucu sorgularında `search_text` yok) ve test 7 (yerel `core` ile sayfa sınırları).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: Mod C `testID`'leri, kelime dokunuşu, biçim değişiminde çapa korunması, meal yok durumu, eşleme ve konum testleri.
- [ ] `rtl`'de "Sonraki sayfa" düğmesi solda ve sonraki sayfa soldan gelir (eşleme testi; görüntü sırası kullanıcıya bırakılır).
- [ ] Mod C yalnız `core`'dan gelen metni çizer; okuyucu kodunda Kur'an ya da meal metni dizgisi yok (`metin-denetcisi` gözden geçirmesi).
- [ ] `reading_position` zincir açıkken yazılmaz; sayfa durduktan 1 saniye sonra yazılır (test).
- [ ] Yazı tipleri `data/gelen/amiri-quran-font/` ve `data/gelen/kfgqpc-hafs-font/` altında, `SHA256SUMS` Tedarik tablosuyla aynı; `kfgqpc-hafs-font` ve `amiri-quran-font` kayıtları güncel; `mutalaa sources check` temiz.
- [ ] Sayfalayıcı kitaplığı, Mod C yazı tipi, besmele ve bölünen âyet sonuçları dokümanda ya da karar defterinde.
- [ ] `arayuz-denetcisi` raporunda engelleyici bulgu yok; görsel denetim ve cihaz ölçümleri "kullanıcıya bırakıldı" diye ilerleme notunda yazılı.

## Doğrulama
```bash
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
grep -rn "search_text\|unit_search" packages/reader-core/src apps/mobile/src/features/reader || echo "okuyucuda search_text yok"
uv --directory pipeline run mutalaa sources check
sha256sum data/gelen/amiri-quran-font/*/AmiriQuran-Regular.ttf data/gelen/kfgqpc-hafs-font/*/KFGQPC-Hafs-V30.zip
```
`sources check` 0 hata ve 0 uyarı ile biter; özetler Tedarik tablosundakilerle aynıdır.

Cihaz komutları ve görüntüler kullanıcıya bırakılır (aşamayı bekletmez; kapanış raporunda "kullanıcıya bırakıldı" yazılır):
```bash
mkdir -p .tmp/a24
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://oku/fihrist"
adb shell input text "2:255"
adb shell input keyevent 66
adb exec-out screencap -p > .tmp/a24/bakara-255-kagit.png
```
Fihrist'teki giriş alanına odak gerekirse `mobil-ekran` becerisindeki dokunma yöntemi kullanılır. Görüntüler üç tema ve üç biçim için tekrarlanır.

## Dikkat
- İçerik etiği: Kur'an metni, besmele, sure adı ve meal elle yazılmaz; yalnız `core`'dan okunur. Testlerde sentetik metin "Deneme" diye başlar. Ayrıntı: `metin-butunlugu`.
- Okuma konumu çapayla tutulur; sayfa numarası `page_map`'ten türetilir (Çapa şeması §10). Ofsetler kod noktasıdır; dönüşüm yalnız `packages/anchors` ile (`capa-gramer`).
- Uygulama arayüzü soldan sağadır; `I18nManager` çevrilmez. Yalnız sayfalayıcı okları yöne göre yer değiştirir.
- Renk ve boyut `ui-tokens`'tan; Arapça ve Türkçe ölçek ayrıdır; okuma metni %200'e kadar kesilmeden büyür.
- Momentum kaydırması sırasında JS işi başlatılmaz; font ve veri ısıtması boşta yapılır (Mobil mimari §9).
- `adb shell input text` ASCII dışı karakter gönderemeyebilir; bu yüzden giriş "2:255" biçimindedir (Test stratejisi §9).
- Yazı tipi dosyaları ve zip veridir: her biri `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasördedir, içindeki hiçbir şey çalıştırılmaz. Dosyaları `metin-butunlugu` kurallarıyla değiştirmeden kullan (yazı tipi alt kümesi çıkarma ya da dönüştürme bu aşamanın işi değildir).
- Commit kapsamları `mobile` ve `reader-core`.

## İnsan adımları
- Yok. Cihaz denetimleri kullanıcıya bırakılır ve aşamayı bekletmez. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/`: sayfa ve kelime modelleri, sorgular, testler
- `apps/mobile/src/features/reader/`: `mushaf-c/`, `pager/`, `components/` (`PageView`, `AyahMarker`, `SurahHeader`, `Besmele`, `MealPane`, `AyahItem`, `TefsirPane`), `store.ts` (`useReader`), `queries.ts`, `hooks/`
- `apps/mobile/src/features/reader/sheets/` ya da ortak `SheetHost`; Okuma ayarları alt sayfası
- `apps/mobile/app/(tabs)/oku/` rotalarının içerikleri; Tasarım vitrini eki
- `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` ve `data/gelen/kfgqpc-hafs-font/<YYYY-AA-GG>/` (git dışı, `SHA256SUMS` ile); güncellenen `pipeline/sources/amiri-quran-font.toml` ve `kfgqpc-hafs-font.toml`
- Karar defterinde sayfalayıcı, Mod C yazı tipi ve `page_map` yokluğu kararları; `.tmp/a24/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A24-okuyucu-mushaf-c.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A23](./A23-cihaz-veri-katmani.md) · Sonraki: [A25](./A25-secim-kelime-karti-baglantilar.md)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md) · [A21](./A21-mobil-iskelet.md)
