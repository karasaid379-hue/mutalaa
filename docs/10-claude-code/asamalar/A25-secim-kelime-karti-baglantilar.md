# A25 · Seçim, kelime kartı, Bağlantılar paneli, geri dönüş yığını, derin bağlantılar

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `arayuz-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · `lisans-kapisi` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A25`

## Amaç
Okur bir kelimeye ya da aralığa dokunup anlamını, kökünü ve bağlantılarını görür, bir bağlantıya atlar ve tek dokunuşla okuduğu yere döner. Seçim her zaman çapaya çevrilir. Bağlantılar cihazda hesaplanmaz; paketteki `xref_idx` satırlarından ve çapadan türetilen yapısal bağlardan okunur. `q` derin bağlantıları aynı atlama kuralıyla açılır.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 Seçim, §7 Kelime kartı, §8 Bağlantılar paneli, §9 Atla ve dön
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §6 güven etiketleri, §9–§13
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

## Adımlar
### A25.1 · Doğrulamalar ve kararlar
- `arastirmaci`: React Native `Text` seçiminin ofsetini bildirip bildirmediği, seçim köprüsü ya da salt okunur metin alanı seçenekleri (MM-15, OD-2); @gorhom/bottom-sheet 5.2.x'in seçilen SDK ve Reanimated 4 ile uyumu ve Android geri tuşu davranışı; panoya kopyalama için Expo modülü; React Native `Share`.
- Belgeler arasında ayrışan değerler eşitlendi (19 Ekim 2026): grup sırası ve "Önerilen"in v1.x'te olması Okuma deneyimi §8 ve Bağlantı modeli §7, §10; güven etiketlerinin koşulları ve eşikleri Bağlantı modeli §6, ekranda yazılan adları Okuma deneyimi §8 (OD-4 çözüldü); yükseklik %40 → %90 Mobil ekranlar §4; derinlik sınırı 12 Okuma deneyimi §9; yığın `useReader`'da, bellekte (Mobil mimari §5; Bağlantı modeli §11).
- İki âyete yayılan seçimde öneri uygulanır: âyet başına bir parça (OD-1).
- **Bitti sayılır:** doğrulama sonuçları dokümanda.

### A25.2 · Seçim modeli ve eylem çubuğu
- `packages/reader-core/src/selection.ts`: kelime aralığı `q:S:A:i-j` olur; tek kelime `q:S:A:i` yazılır, `i-i` yazılmaz. Türkçe metinde karakter aralığı kelime sınırına genişletilir ve `meal:elmalili:S:A@a-b` olur. Ofsetler kod noktasıdır; dönüşüm yalnız `packages/anchors` (`cpToUtf16`, `utf16ToCp`, `snapSpan`) ile yapılır.
- Mod C ve meal: uzun basış işletim sisteminin seçimini açar ve sistemin "Kopyala"sı her durumda çalışır. Uygulama aralığı köprü hazır olana kadar üst çubuktaki "Seç" düğmesiyle kurar: "Başlangıç kelimesine dokun" → "Bitiş kelimesine dokun"; her adımda "Vazgeç".
- `SelectionToolbar` yüzen araç çubuğudur, alt sayfa sayılmaz. Bu aşamadaki eylemler: Bağlantılar, Kopyala (Unicode metin ve okunur adres), Paylaş (metin ve derleme türünün şemasıyla `…://q/2/255`), Tefsir. Âyet sonu işaretine dokunmak âyeti seçer ve çubuğu açar. Mushaf biçiminde âyete dokununca çubuğun üstünde mealin ilk satırları görünür.
- **Bitti sayılır:** seçim testleri (kanonik biçim, kelime sınırına genişletme, BMP dışı karakterli ofset, iki âyete yayılan seçim) ve "Seç" akışı testi yeşil.

### A25.3 · Kelime kartı
- `WordCard` tek `SheetHost` içinde %40'ta açılır; okuyucu, kelime kartın üstünde kalacak biçimde kayar. Satırlar Okuma deneyimi §7'deki gibidir: Arapça kelime (`quran_word.text_uthmani`) ve "Bakara 255 · 3. kelime" biçiminde konum; Türkçe anlam; kök harfleri ve "Bu kök Kur'an'da N yerde geçer"; lemma ve kısa morfoloji. Kelime sesi satırı gizlidir (Açık soru).
- Sure adı gösteren her etiket (kelime kartındaki konum, kırıntı izi, `BackChip`) adı `core`'daki `sure` tablosundan alır. Tablo boşsa (sure adları İ-23 onayını bekliyor; A24) sayısal biçim kullanılır: "2:255 · 3. kelime", "↩ Okuduğun yere dön (2:255)". Ad elle yazılmaz.
- Anlam, kök ve lemma `kelime-kok` paketinden okunur (İçerik paketleri §3.3). Paket bağlı değilse bu satırlar ve "Kökü incele" boşluk bırakmadan gizlenir, uyarı gösterilmez. Paket var ama anlam onaysızsa "Anlam henüz onaylanmadı"; `dev`'de taslak `UnverifiedBadge` ("doğrulanmamış") ile görünür (K-25).
- Eylemler: Kökü incele (paket varsa), Bu kelime nerede geçiyor?, Âyetin tefsiri, Kopyala. Not ve Vurgu A30'da eklenir.
- Kart yukarı çekilince ya da "Bu kelime nerede geçiyor?" seçilince aynı alt sayfa Bağlantılar paneline büyür (%90); ikinci sayfa açılmaz. "Kapat" ve Android geri tuşu kartı kapatır. Açılış bütçesi 100 ms'dir (öneri); süre geliştirme günlüğüne yazılır.
- `testID`: `kelime-karti`.
- **Bitti sayılır:** RNTL testleri yeşil: `kelime-kok` varken ve yokken satırlar; `internal` ve `public` bayrağıyla `bekliyor` `kelime-kok` görünmez ve kök, lemma, anlam satırları kapalıdır (Test stratejisi §8).

### A25.4 · Bağlantılar paneli
- Çözümleyici `packages/reader-core/src/links/` altında Bağlantı modeli §9 tablosunu uygular. Bu aşamadaki girişler: Kur'an kelimesi, Kur'an ifadesi, meal içindeki Türkçe kelime ve ifade. Risale ve tefsirdeki Arapça ibare A31'dedir.
- Sorgular paketteki `xref_idx` tablosunu kullanır (İçerik paketleri §3.2; Bağlantı modeli §13). `xref` adı yalnız editoryal veritabanındaki tablodur. Kur'an seçimi `toUnitSpan` ile uç birime ve kelime konumu aralığına çevrilir (`q:2:255:3-7` → `q:2:255`, `[3,8)`). Âyet ↔ meal ve âyet ↔ tefsir bağları çapadan türetilir, `xref_idx`'te aranmaz. Türkçe ifade sorgusu `packages/search` normalizasyonuyla kurulur.
- Gruplar sabit sırayla gelir: Kur'an, Meal, Tefsir, Hadis, Risale-i Nur; boş grup gizlenir. Grup içinde sıra güven etiketi, puan, metin sırasıdır; "Metin sırası" düğmesi mushaf ya da kitap sırasına geçirir.
- Satır: okunur adres (paketteki `unit.label`), eşleşen aralığı vurgulu kısa parça, en çok iki gerekçe çipi ve "+N", yazılı güven etiketi. `folded = 1` satırlar "Daha fazla (otomatik) · N" altında katlıdır; `red` satır pakete zaten girmez. `dev` ve `internal`'da `approved = 0` satır "Aday" rozetiyle görünür.
- Hedef paketi cihazda yoksa satır "paket gerekli" etiketi taşır ve atlamaz; derlemede yoksa görünmez. Boş sonuç: "Bu seçim için bağlantı bulunamadı · Tam ifadeyi ara" (Ara rotasına gider).
- Panelin iç geri yığını (kelime → kök → lemma) atlama yığınından ayrıdır; panel kapanınca silinir.
- `testID`: `baglanti-0`, `baglanti-1` …
- **Bitti sayılır:** çözümleyici ve panel testleri sentetik `xref_idx` fikstürüyle yeşil: grup sırası, katlama, etiket eşlemesi, eksik paket satırı, yapısal meal bağı.

### A25.5 · Geri dönüş yığını ve çip yuvası
- Saf işlevler `packages/reader-core/src/backstack.ts` içindedir: it, geri, başlangıca dön, burada kal. Kayıt `{ rota, çapa, ofset, seçim, biçim, gerekçe }`; derinlik 12, aşılınca başlangıç korunur ve en eski ara kayıt düşer. Durum `useReader` deposundadır (bellek).
- Her atlamadan önce bulunulan konum yığına yazılır; sayfa çevirme, kaydırma ve biçim değişimi atlama sayılmaz. Kur'an hedefi Oku sekmesinde açılır (`router.navigate('/oku')`).
- Kırıntı izi panelin başında ve zincir açıkken okuyucunun üst çubuğu altında görünür. `ChipSlot` zincir açıkken `BackChip` gösterir: "↩ Okuduğun yere dön (Bakara 255)" ve "Burada kal", iki ayrı 44 pt hedef. Ses çipi A27'de aynı yuvaya girer; iki çip birlikte görünmez.
- Zincir açıkken `reading_position` yazılmaz; "Burada kal" bulunulan yeri yazar.
- Android geri tuşu sırası Mobil ekranlar §8 kural 3'teki gibidir: alt sayfa → seçim → yığında bir adım → yönlendirici → Oku kökünde arka plan.
- `testID`: `geri-don-cipi`.
- **Bitti sayılır:** yığın testleri yeşil: 5 adımlı zincir, kırıntı izi, dön, burada kal, derinlik sınırı, geri tuşu sırası.

### A25.6 · Derin bağlantılar ve cihaz denetimi
- `app/[...capa].tsx`: yol `fromRoute` ile çapaya çevrilir (`q/2/255/3-7` → `q:2:255:3-7`) ve `packages/anchors` ile doğrulanır (Çapa şeması §11; karakter aralığı `?aralik=` sorgusundadır). Geçerli hedef bir atlamadır: bulunulan konum başlangıç olarak yığına yazılır, hedef okuyucu deposuna yazılır, `router.replace('/oku')` çağrılır. `q/2/255/3` kelimeyi seçip kartı açar; `?panel=baglantilar` paneli açar.
- Geçersiz ya da aralık dışı adres (`q/2/300`) en yakın âyete yuvarlanmaz; Oku açılır ve "Bağlantı geçersiz" uyarısı görünür.
- `WordCard`, `LinkResult` (bütün güven etiketleriyle) ve `ChipSlot` Tasarım vitrinine eklenir.
- Cihazda üç bağlantı açılır ve görüntülenir: `q/2/255`, `q/2/255/3-7`, `q/2/300`; ayrıca kelime kartı, panel ve geri dönüş çipi. Görüntüler `arayuz-denetcisi`ne verilir.
- Gerçek `xref_idx` satırları A18 ile gelir. O zamana kadar cihazdaki panel yapısal bağlarla denetlenir: meal `core`'daysa (A16) Meal grubu, A13'ün sentetik `tefsir-test-ornek` paketi (yalnız `dev`) Tefsir grubu; hiçbiri yoksa boş durum kartı.
- **Bitti sayılır:** derin bağlantı testleri yeşil; cihaz görüntüleri `.tmp/a25/` altında; rapor temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/reader-core test` yeşil: seçim, çözümleyici, geri dönüş yığını.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: kelime kartı (paketli ve paketsiz), Bağlantılar paneli (gruplama, gerekçe, güven, katlama), geri dönüş çipi, lisans görünürlüğü (Test stratejisi §8).
- [ ] Seçim çapaları gramere uyar: tek kelime `q:S:A:i`, aralık `q:S:A:i-j`, meal `meal:elmalili:S:A@a-b`; ofsetler kod noktası (test).
- [ ] `mutalaa-dev://q/2/255` Bakara 255'i ve geri dönüş çipini gösterir; `q/2/300` "Bağlantı geçersiz" uyarısı verir ve yuvarlama yapmaz (görüntü).
- [ ] Zincir açıkken `reading_position` yazılmaz; "↩ Okuduğun yere dön" başlangıç çapasına ve ofsetine döner (test).
- [ ] Grup sırası, güven eşikleri, yükseklik, derinlik ve kalıcılık belgelerdeki değerlerle uygulandı (A25.1 maddesi; test).
- [ ] `arayuz-denetcisi` raporunda engelleyici bulgu yok; `lisans-denetcisi` `kelime-kok` görünürlüğünü onayladı.

## Doğrulama
```bash
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
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
- `kelime-kok` `bekliyor` durumundadır: `internal` ve `public`'te kök, lemma ve anlam satırları görünmez; eksiklik uyarısı da gösterilmez (`lisans-kapisi`).
- Yapay zekâ taslağı anlamlar "doğrulanmamış" rozetiyle görünür (K-25); onaysız taslak `public`'e girmez (P-08).
- Panel sonuç parçaları paketteki kanonik metinden gelir; testlerde sentetik metin "Deneme" diye başlar. Kur'an, meal ya da Risale metni test için elle yazılmaz.
- Alt sayfalar üst üste açılmaz; her sayfada görünür "Kapat" vardır; her jestin düğme karşılığı vardır (Tasarım sistemi §9).
- Derin bağlantı şeması derleme türüne göre değişir (`mutalaa-dev`, `mutalaa-internal`, `mutalaa`); şema elle yazılmaz, `src/lib/env.ts`'den okunur.
- Commit kapsamları `mobile` ve `reader-core`.

## İnsan adımları
- Yok. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/`: `selection.ts`, `links/`, `backstack.ts`, güven etiketi eşlemesi, testler
- `apps/mobile/src/features/reader/`: `SelectionToolbar`, "Seç" akışı; `src/features/crossref/`: `WordCard`, `LinkPanel`, `LinkResult`, `ReasonChip`, `ConfidenceBadge`, `Breadcrumb`, `ChipSlot`, `BackChip`
- `apps/mobile/app/[...capa].tsx`; Tasarım vitrini ekleri
- Karar defterinde OD-1 önerisi; `.tmp/a25/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A25-secim-kelime-karti-baglantilar.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A24](./A24-okuyucu-mushaf-c.md) · Sonraki: [A26](./A26-mushaf-a.md)
