# A24 · Okuyucu: Mushaf C, okuma biçimleri, sağdan sola sayfalayıcı

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) (A11.2 ve A11.4–A11.6 yeterli; sure adları A11.3 sonra gelebilir) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A24`

## Amaç
Kur'an okuyucusunun temeli kurulur: indirme gerektirmeyen Mod C (akan Unicode metin), üç okuma biçimi (Mushaf, Mushaf + Meal, Âyet âyet), sağdan sola sayfalayıcı, Fihrist ve tefsir görünümünün iskeleti. Okuyucu her konumu çapayla tutar; biçim, tema, yön ya da ekran yönü değişince aynı âyet görünür kalır. Okuyucu yalnız kanonik metni gösterir.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §1–§6
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (`SheetHost`, çip yuvası), §5 (`useReader`, `reading_position`), §7 ortak sözleşme, §7.3, §7.4, §8, §9
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 (Oku yığını), §3 (Kur'an okuyucu, Fihrist, Tefsir satırları), §4 (Okuma ayarları)
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §6 (`PageView`, `AyahMarker`, `SurahHeader`, `AyahItem`, `MealPane`, `TefsirPane`), §9
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 ofsetler, §10 sayfa eşlemeleri
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.2 (`unit`, `quran_word`, `page_map`, `sure`)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 5 ve 7, §9 `testID`
- [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) çıktısı: `quran_word` Tanzil satırları, cüz ve secde tablosu kararı, `page_map` kaynağı; ilerleme notunda biten adımlar

## Kapsam
**Yapılır**
- `packages/reader-core`: sayfa, satır ve kelime modelleri; sayfa ↔ âyet eşlemesi; içerik sorguları.
- Mod C çizimi (`AyahFlow`), `SurahHeader`, `Besmele`, `AyahMarker`, `SecdeMarker`, `JuzMarker`, `PageView`.
- Üç okuma biçimi; telefonda "Sayfa | Meal" sekmesi ve etkin âyet altyazısı; tablet yatayda açık kitap.
- Sağdan sola sayfalayıcı, yön ayarı, etiketli düğmeler, odak modu, konum koruma, okuma konumu yazımı.
- Tek `SheetHost` ve "Aa" Okuma ayarları alt sayfası.
- Fihrist (`oku/fihrist`), tefsir görünümünün iskeleti (`oku/tefsir/...`), okuyucu parçalarının Tasarım vitrinine eklenmesi.

**Yapılmaz**
- Seçim, kelime kartı, Bağlantılar paneli, geri dönüş yığını, derin bağlantılar: [A25](./A25-secim-kelime-karti-baglantilar.md). Bu aşama yalnız `openWordCard(anchor)` çağrısını ve `useReader.returnStack` alanını bırakır.
- Mod A (A26), Mod B (A40), ses ve takip (A27), adla adres ayrıştırma ("Bakara 255") ve Ara (A28), yer imi, vurgu ve not işaretleri (A30).
- Ayar ekranları ve ekran okuyucu önerisi (A32); tablet yatayda çift mushaf sayfası [s2][s1] (v1.x); tefsir içeriği (A37).

## Adımlar
### A24.1 · Doğrulamalar ve ön ölçümler
- `arastirmaci` (seçilen SDK için): iç içe `Text` parçalarında `selectable` ile `onPress`'in birlikte çalışması (Mobil mimari §7.3); `writingDirection` ve iki yana yaslama; ekranı açık tutan Expo modülü; Hareketi Azalt ve `announceForAccessibility` API'leri; `react-native-pager-view` ve FlashList'in güncel sürümleri (MM-10).
- Yerel `dev` `core` dosyasında `quran_word`, `page_map` ve işaret tablosu dolu mu (A11 çıktısı). Boşsa A13'ün yayını A11'den önce yapılmıştır: `publish --flavor dev` yeniden çalışır ve `fetch-core.mjs` yeni `core`'u alır.
- Veriden okunur (metin elle yazılmaz): besmelenin Tanzil metninde ayrı satır mı yoksa ilk âyetin parçası mı olduğu (A10 çıktısı); `core`'da `page_map` düzeninin varlığı ve kaynağı (A11, IP-3); Medine düzeninde iki sayfaya bölünen âyet olup olmadığı (OD-3); cüz ve secde tablosunun adı (A11 kararı).
- Cihazda (`mobil-gelistirici`): U+06DD âyet sonu işaretinin rakamla birleşik çizimi; `FlatList` ile 50 sayfa çevirmede belirgin takılma olup olmadığı. Asıl ölçüm sürüm derlemesinde A33'tedir.
- **Bitti sayılır:** sonuçlar dokümanda; sayfalayıcı kitaplığı kararı `/karar` ile ("FlatList yeterli" de bir karardır).

### A24.2 · `packages/reader-core`: model ve sorgular
- Sorgular parametreli SQL'dir ve A23'ün SQL yürütücü arayüzüyle çalışır: sayfanın âyetleri ve kelime sınırları (`page_map`, düzen `medine-604`), âyetin kelimeleri (`quran_word`), sure bilgisi (`sure`), sayfanın meal birimleri (`meal:elmalili:{s}:{a}`), âyet ↔ sayfa eşlemesi, cüz ve secde işaretleri (A11 tablosu).
- Okuyucu yalnız kanonik metni okur (`unit.text`, `quran_word.text_uthmani`). `search_text` ve arama tabloları okuyucu sorgularına girmez (Test stratejisi §5 test 5; A10 bu testi A24'e bıraktı).
- Bölünmüş âyet: meal başladığı sayfada tam verilir; sonraki sayfa "(önceki sayfadan)" satırıyla başlar (Okuma deneyimi §5).
- Sorgu anahtarları paket sürümünü içerir (`qk.page(page, coreVersion)`); içerik sorguları `contentQuery` ayarıyla çalışır.
- `core`'da `page_map` yoksa (IP-3) sayfalı Mod C çizilemez. Okuyucu Âyet âyet biçimine düşer ve Geliştirici menüsü uyarır (öneri; `/karar` ile kesinleşir).
- **Bitti sayılır:** `reader-core` testleri yeşil: okuyucu sorgularında `search_text` geçmez; yerel `dev` `core` dosyasıyla 1. sayfa `q:1:1`–`q:1:7`, 604. sayfa `q:114:6` ile biter, 0 ve 605 geçersiz (test 7; Node SQLite sürücüsü A23 kararıdır; dosya yoksa test atlanır).

### A24.3 · Mod C ve sayfa bileşenleri
- `src/features/reader/mushaf-c/AyahFlow.tsx` Mobil mimari §7.3'teki gibi: Amiri Quran, `writingDirection: 'rtl'`, iki yana yaslı, satır yüksekliği 2,0–2,3 aralığında, boyut `arabicScale` ile. Kelimeler ayrı `Text` parçasıdır; paragraf `selectable`. Kısa dokunuş `openWordCard(anchor)` çağırır (A25 bağlar); uzun basışa uygulama seçimi bağlanmaz.
- Etkin âyet zemin tonu (`ses-ayet`), etkin kelime zemin ve alt çizgidir; renk tek başına anlam taşımaz.
- `SurahHeader` (tezhip çerçevesi, Türkçe ad `sure` tablosundan, erişilebilirlik başlığı "Bakara Sûresi, 286 âyet" biçiminde; `sure` tablosu boşsa, yani sure adları İ-23 onayını bekliyorsa, başlık, Fihrist ve sayfa duyurusu sure numarasını gösterir: "2. sûre"; ad elle yazılmaz), `Besmele` (A24.1 sonucuna göre; metin yalnız `core`'dan), `AyahMarker` (normal, etkin, seçili, secde), `SecdeMarker`, `JuzMarker`.
- `PageView` `React.memo` ile sarılır; veri çizimden önce sorgudan gelir; ses ilerlemesi sayfa özelliklerine girmez. Durumlar: hazır, hata ("Yeniden dene"), lisans kapısı.
- `testID`'ler çapa gramerini kullanır: `ayet-q:2:255`, `kelime-q:2:255:3`, `etkin-ayet-q:2:255` (Test stratejisi §9).
- **Bitti sayılır:** RNTL testleri yeşil: âyet ve kelime `testID`'leri, kelime dokunuşunun çapayı iletmesi, etkin âyet ve kelime stili.

### A24.4 · Okuma biçimleri ve Okuma ayarları
- `useSettings.readingLayout`: `mushaf`, `mushaf_meal` (varsayılan), `ayet_ayet`. Çizim yolu varsayılanı C (MM-13 kapandı).
- Mushaf + Meal: telefonda "Sayfa | Meal" `SegmentedControl` (varsayılan) ya da etkin âyet altyazı şeridi. `MealPane` sayfadaki âyetleri "2:255" etiketiyle listeler; âyete dokunmak meal paragrafını işaretler, meal paragrafına dokunmak âyeti tonlar. "Panelleri bağla" varsayılan açıktır.
- Âyet âyet: dikey liste; her zaman Mod C yazı tipi; öğede âyet numarası, Arapça, meal. Âyet öğeleri âyet sırasıyla dizilir.
- Düzenler Okuma deneyimi §4'teki gibidir: < 600 dp tek bölme; 600–899 dp ortalı sütun; ≥ 900 dp yatay açık kitap (sağda sayfa, solda meal).
- Meal birimi `core`'da yoksa (A16 bitmeden) meal bölmesi boş durum kartı gösterir; yer tutucu ya da sentetik meal metni yazılmaz.
- Tek `SheetHost` (Mobil mimari §4) kurulur: aynı anda tek alt sayfa, görünür "Kapat", Android geri tuşu önce alt sayfayı kapatır. "Aa" düğmesi Okuma ayarlarını açar (%60): biçim, çizim yolu, tema, Arapça ve Türkçe boyut. Değişiklik arkada anında görünür; ekrandaki ilk âyetin çapası korunur. Mod A ve B yalnız paketleri derlemede görünürse listelenir (Mobil mimari §7.4).
- **Bitti sayılır:** RNTL testleri yeşil: biçim değişiminde ilk görünen âyetin çapası aynı kalır; meal yokken boş durum kartı; görünür paket yokken Mod A ve B seçeneği listede yok.

### A24.5 · Sağdan sola sayfalayıcı ve konum
- `pager/mapping.ts` Mobil mimari §8'deki gibidir: `rtl`'de 1. sayfa indeks 603, indeks 602 sayfa 2; `ltr`'de sayfa − 1. `MushafPager` A24.1 kararıyla (`FlatList` ise `getItemLayout`, `windowSize={3}`, `initialNumToRender={1}`).
- Etiketli "Önceki sayfa" ve "Sonraki sayfa" düğmeleri her zaman görünür; sağdan sola düzende "Sonraki sayfa" soldadır. Yön ayarı değişince liste yeni başlangıç indeksiyle kurulur, açık sayfa korunur. Hareketi Azalt açıkken düğmeyle çevirme animasyonsuzdur (`scrollToIndex({ animated: false })`).
- Sürükleme başlayınca oynatıcıya `USER_SCROLLED` gönderecek bağlantı noktası bırakılır (A27 bağlar).
- Odak modu: kaydırınca ya da sayfanın ortasına dokununca çubuklar gizlenir, tek dokunuş geri getirir; "Ekranı açık tut" varsayılan açıktır ve cihaza özgüdür.
- Konum: ekran dönünce ya da alt sayfa kapanınca âyet ve ofset geri yüklenir. `reading_position` sayfa durduktan 1 saniye sonra MMKV kopyasıyla yazılır; `useReader.returnStack` boş değilken yazılmaz.
- Sayfa değişince `announceForAccessibility` ("Sayfa 42, Bakara Sûresi" biçiminde), en çok saniyede bir.
- **Bitti sayılır:** eşleme testleri ve konum yazımı testi (1 saniye gecikme, zincir açıkken yazmama) yeşil.

### A24.6 · Fihrist, tefsir iskeleti, vitrin ve görsel denetim
- `oku/fihrist`: sure listesi, cüz ızgarası, sayfa numarası ve "2:255" biçimli giriş (`packages/anchors` ile doğrulanır). Geçersiz giriş "Bu adres bulunamadı" der; adla arama A28'dedir.
- `oku/tefsir/[sure]/[ayet]` ve `TefsirPane`: "Elmalılı · Bakara 255–257" biçimli başlık, kapsanan âyet çipleri, "Takip et" (varsayılan açık). Paket yoksa "Elmalılı tefsiri indirilmedi · İndir (boyut)"; derlemede yoksa "Tefsir hazırlanıyor". Takip mantığı A13'ün sentetik `tefsir-test-ornek` paketiyle (`ic_kullanim`, yalnız `dev`) denenir; gerçek içerik `tefsir-elmalili` ile gelir (A37).
- `PageView`, `AyahMarker` durumları ve Mod C Fâtiha sayfası Tasarım vitrinine eklenir; vitrinin Arapça ve meal örnek alanı `core`'a bağlanır (A22).
- Görsel denetim (`mobil-ekran`): 1. sayfa ve Bakara 255'in bulunduğu sayfa (Fihrist'ten), üç tema; Mushaf + Meal "Meal" sekmesi; Âyet âyet; sağdan sola çevirme sırası. `arayuz-denetcisi` 44×44 pt hedefleri, etiketleri, Türkçe ve Arapça yönü ve Tasarım sistemi §9'dan bu aşamaya düşen maddeleri denetler.
- **Bitti sayılır:** görüntüler `.tmp/a24/` altında; rapor temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/reader-core test` yeşil: test 5 (okuyucu sorgularında `search_text` yok) ve test 7 (yerel `core` ile sayfa sınırları).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: Mod C `testID`'leri, kelime dokunuşu, biçim değişiminde çapa korunması, meal yok durumu, eşleme ve konum testleri.
- [ ] `rtl`'de "Sonraki sayfa" düğmesi solda ve sonraki sayfa soldan gelir (görüntü sırası ve test).
- [ ] Mod C yalnız `core`'dan gelen metni çizer; okuyucu kodunda Kur'an ya da meal metni dizgisi yok (`metin-denetcisi` gözden geçirmesi).
- [ ] `reading_position` zincir açıkken yazılmaz; sayfa durduktan 1 saniye sonra yazılır (test).
- [ ] Sayfalayıcı kararı, besmele ve bölünen âyet sonuçları dokümanda ya da karar defterinde.
- [ ] Görüntüler `.tmp/a24/` altında; `arayuz-denetcisi` raporunda engelleyici bulgu yok.

## Doğrulama
```bash
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
grep -rn "search_text\|unit_search" packages/reader-core/src apps/mobile/src/features/reader || echo "okuyucuda search_text yok"
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
- Commit kapsamları `mobile` ve `reader-core`.

## İnsan adımları
- Yok. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/`: sayfa ve kelime modelleri, sorgular, testler
- `apps/mobile/src/features/reader/`: `mushaf-c/`, `pager/`, `components/` (`PageView`, `AyahMarker`, `SurahHeader`, `Besmele`, `MealPane`, `AyahItem`, `TefsirPane`), `store.ts` (`useReader`), `queries.ts`, `hooks/`
- `apps/mobile/src/features/reader/sheets/` ya da ortak `SheetHost`; Okuma ayarları alt sayfası
- `apps/mobile/app/(tabs)/oku/` rotalarının içerikleri; Tasarım vitrini eki
- Karar defterinde sayfalayıcı ve `page_map` yokluğu kararları; `.tmp/a24/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A24-okuyucu-mushaf-c.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A23](./A23-cihaz-veri-katmani.md) · Sonraki: [A25](./A25-secim-kelime-karti-baglantilar.md)
