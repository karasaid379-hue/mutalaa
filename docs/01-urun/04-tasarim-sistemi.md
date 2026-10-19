# Tasarım Sistemi: Sade Osmanlı

> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-13](../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-14](../00-ozet/02-karar-defteri.md#k-14--web) · [K-24](../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-29](../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları)

Bu dosya "Sade Osmanlı" tasarım dilinin jetonlarını, tipografisini, ölçeklerini, hareket kurallarını, bileşenlerini, motif ve simge kurallarını, erişilebilirlik kontrol listesini ve jetonların koda nasıl aktığını tanımlar. Brifteki ve rapordaki değerler aynen kullanılır; bu dosyanın eklediği değerler "öneri" diye işaretlidir. Kontrast oranları WCAG formülüyle hesaplandı; rapordaki değerler yeniden hesaplanınca aynı çıktı.

## 1. Tasarım dili

Kâğıt yüzeyler, İznik çinisi paletinden çini mavisi, turkuaz ve lâl; altın yalnız süs çizgilerinde ([K-24](../00-ozet/02-karar-defteri.md#k-24--tasarım-dili)). İznik paleti 15. yüzyıl sonunda kobalt mavisiyle başladı; turkuaz 1520 civarında, adaçayı yeşili ve soluk mor 1540–1555 arasında, "bole" kırmızısı 1560 civarında, zümrüt yeşili 1567'de eklendi ([Wikipedia: İznik](https://en.wikipedia.org/wiki/Iznik_pottery)). Palet bu tarihe dayanır; klişe yeşil-altın "İslami" paletten kaçınılır.

İlkeler: arayüz geri çekilir ve metin öndedir; renk rolüyle adlandırılır; süs yalnız anlam taşıdığı yerde bulunur; erişilebilirlik ölçülebilir hedeflerle denetlenir.

## 2. Renk jetonları

Jeton adları role göredir. Bu sayede Âhar temasında "etkin" rolünün kahverengi olması (#6E5426) kodda sorun çıkarmaz.

### 2.1 Temel jetonlar

Değerler brifte ve raporda tanımlıdır. Parantez içi oran temanın yüzeyine karşı kontrasttır.

| Jeton | Rol | Kâğıt | Âhar | Gece |
|---|---|---|---|---|
| `yuzey` | Yüzey | #FBF8F1 | #F3E9D2 | #14181D |
| `metin` | Metin | #1F1A14 (16,3:1) | #2A2017 (13,2:1) | #E8E2D4 (13,8:1) |
| `baglanti` | Çini mavisi: bağlantı, seçim, odak | #1E4F8F (7,7:1) | #1E4F8F (6,77:1)¹ | #8FB4E8 (8,4:1) |
| `etkin` | Turkuaz: ses, etkin öğe | #0B6E72 (5,7:1) | #6E5426 (5,9:1) | #5CC4C0 (8,6:1) |
| `isaret` | Lâl: dipnot, secde, vakıf | #A2302A (6,6:1) | #9A2C26 (6,3:1) | #E07A6E (6,1:1) |
| `sus` | Altın: yalnız süs | #B38B3F (2,96:1) | #9A7A3A (3,33:1)¹ | #D6B46A (9,0:1) |
| `altin-metin` | Altın: metinde | #8A6A2B (4,7:1) | #7A5D24 (5,09:1)² | #D6B46A (9,0:1) |

¹ Raporda boş; bu dosyada hesaplandı. ² Öneri; brifte Âhar için metin altını yok.

### 2.2 Ek rol jetonları (öneri)

| Jeton | Rol | Kâğıt | Âhar | Gece |
|---|---|---|---|---|
| `metin-ikincil` | Açıklama, adres | #5C5245 (7,2:1)³ | #5B4B37 (6,94:1) | #A9A397 (7,1:1)³ |
| `metin-soluk` | Yer tutucu, küçük not | #6B6152 (5,73:1) | #685843 (5,68:1) | #918B80 (5,27:1; `yuzey-ust` üstünde 4,84:1) |
| `yuzey-ust` | Alt sayfa, kart | #FFFDF8 (metin 17,0:1) | #F9F2E2 (14,3:1) | #1B2027 (12,7:1) |
| `yuzey-cukur` | Giriş alanı | #F3EEE3 (14,9:1) | #EADFC5 (12,0:1) | #0F1216 (14,5:1) |
| `cizgi` | İnce ayraç (süs) | #E6DED0 | #DDCFB1 | #2A3139 |
| `cizgi-guclu` | Giriş alanı kenarı (≥ 3:1) | #8C8170 (3,61:1) | #857560 (3,69:1) | #6B737D (3,71:1) |
| `secim` | Seçim zemini | #D3DFF0 (metin 12,8:1) | #D2D9DE (11,2:1) | #24395A (9,0:1) |
| `ses-ayet` | Çalan âyet zemini | #D7EEEC (14,3:1)³ | #DCE3CC (12,1:1) | #1F3B3C (9,3:1)³ |
| `baglanti-ustu` | Dolu çini düğme üstündeki metin | #FFFFFF (8,17:1) | #FFFFFF (8,17:1) | #14181D (8,37:1) |
| `perde` | Pencere arkası örtü | `metin` %32 | `metin` %32 | #000000 %50 |

³ Araştırma notundaki değer. Diğerleri bu dosyada hesaplandı.

### 2.3 Vurgu renkleri

Beş renkli vurgu eski planın korunan çekirdeğidir ([K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)). Renkler İznik paletinden türetildi (öneri). Varsayılan adlar okurun değiştirebileceği adlardır; eski planın konu adları (Akide, İbadet, Ahlak, Tarih, Dil) hazır takım olarak sunulur (`quran-app-docs/06-icerik/03-highlighter.md`). Her vurgu zemin tonu, işaret renginde 1,5 pt alt çizgi ve kenar boşluğunda simgeyle gösterilir; renk tek başına anlam taşımaz.

| Varsayılan ad | İznik kaynağı | Kâğıt zemin / işaret | Âhar zemin / işaret | Gece zemin / işaret |
|---|---|---|---|---|
| Önemli | Tezhip altını | #F3E4B5 / #8A6A2B | #EDD9A2 / #7A5D24 | #45391B / #D6B46A |
| Ezber | Adaçayı yeşili | #DCE8CE / #4D6B38 | #D7DFC0 / #4A6335 | #2B3A27 / #9CC089 |
| Ders | Kobalt (çini mavisi) | #D6E2F1 / #1E4F8F | #CFD9E2 / #1E4F8F | #21334D / #8FB4E8 |
| Soru | Soluk mor | #E7DDEC / #6A4A7C | #E0D2DC / #634574 | #372C42 / #C4A7D8 |
| Tefekkür | Bole kırmızısı | #F4DAD3 / #A2302A | #EDCEC0 / #9A2C26 | #462826 / #E07A6E |

Hesaplanan değerler: metnin zemine karşı kontrastı Kâğıt'ta en az 13,0:1, Âhar'da 10,8:1, Gece'de 8,8:1. İşaret renginin yüzeye karşı kontrastı Kâğıt'ta en az 4,74:1, Âhar'da 5,09:1, Gece'de 6,09:1; kendi zeminine karşı en az 3,97:1. "Ders" zemini `secim` zeminine yakındır; seçim tutamaçları ve eylem çubuğuyla ayrılır. Metin içi bağlantılar (CitationLink) noktalı alt çizgi kullanır; vurgunun düz çizgisiyle karışmaz.

### 2.4 Bölüm vurgusu

İki külliyat ince bir farkla ayrılır: Kur'an bölümünde çini mavisi ve tezhip çerçeveleri, Risale bölümünde turkuaz-zümrüt tonları ve daha yalın bir çizgi süsü ([araştırma raporu](../09-kaynakca.md)). Tip sistemi ve yüzeyler ortaktır.

| Jeton | Kâğıt | Âhar | Gece |
|---|---|---|---|
| `bolum-kuran` | = `baglanti` | = `baglanti` | = `baglanti` |
| `bolum-risale` (zümrüt, öneri) | #1E6B4E (6,06:1) | #1F5E44 (6,34:1) | #6CC59A (8,56:1) |

### 2.5 Kontrast kuralları

- 17 pt'ye kadar metin en az 4,5:1, 18 pt ve üstü ya da kalın metin en az 3:1 ([Apple HIG Erişilebilirlik](https://developer.apple.com/design/human-interface-guidelines/accessibility)). Giriş kenarı ve odak halkası gibi bileşen sınırları en az 3:1.
- Quran.com'un turkuaz vurgusu (#2ca4ab) beyazda yalnız 3,00:1 verir; küçük metne uygun değildir ([Quran.com _light.scss](https://github.com/quran/quran.com-frontend-next/blob/production/src/styles/themes/_light.scss)). Bu yüzden `etkin` koyulaştırıldı.
- `sus` açık temalarda metin için kullanılmaz (2,96:1 ve 3,33:1).
- Tecvid renkleri (QPC V4) yazı tipine gömülüdür; her tema yüzeyine karşı ayrıca ölçülür (v1.x).
- Mod B'nin boyanan ya da ters çevrilen sayfa görselleri Gece temasında okunurluk için elle denetlenir.
- Her jeton çifti `packages/ui-tokens` derlemesinde test edilir (bölüm 10).

## 3. Tipografi

### 3.1 Yazı tipleri

| Rol | Yazı tipi | Lisans | Not |
|---|---|---|---|
| Türkçe gövde (meal, tefsir, Risale, hadis çevirisi) | Literata, optik boyut eksenli değişken | OFL ([googlefonts/literata](https://github.com/googlefonts/literata)) | Türkçe harfler ve â î û tam; TRK dil sistemi var ([google/fonts](https://github.com/google/fonts/tree/main/ofl/literata)) |
| Arayüz | IBM Plex Sans | OFL olduğu biliniyor; lisans dosyası Doğrulanacak | Brifin seçimi. Rapor Inter önermişti (Açık soru). Türkçe kapsamı Doğrulanacak. |
| Kur'an Unicode metni | Amiri Quran; yazılı izinle KFGQPC Hafs | OFL ([google/fonts](https://github.com/google/fonts/tree/main/ofl/amiriquran)) | 65 Kur'an kod noktasının 53'ü; Türkçe Latin harfi yok, yalnız Arapça dizide kullanılır |
| Metin içi Arapça | Amiri ya da Noto Naskh Arabic | OFL ([Amiri](https://github.com/google/fonts/tree/main/ofl/amiri), [Noto Naskh](https://github.com/google/fonts/tree/main/ofl/notonaskharabic)) | İkisi de 65 kod noktasının tamamını içerir |
| Mushaf A | QPC V2 sayfa yazı tipleri (tecvid V4) | QF şartları ([QF Developer Terms](https://api-docs.quran.foundation/legal/developer-terms/)) | Sayfa başına, cüz paketiyle |
| Sure adı hattı | Açık soru | | Quran.com ayrı bir sure adları yazı tipi taşır; lisansı doğrulanmadı |

Scheherazade New ve IBM Plex Sans Arabic Türkçe metinde kullanılmaz; ikisinde de ğ, ş ve İ eksik ([google/fonts](https://github.com/google/fonts/tree/main/ofl/scheherazadenew)). Latin IBM Plex Sans ayrı bir ailedir ve ayrıca ölçülür.

### 3.2 Roller ve boyutlar

Okuma rolleri uygulama içi kaydırıcıyla, arayüz rolleri işletim sisteminin yazı ölçeğiyle büyür. Brif değerleri: Türkçe gövde 17–19 pt, satır 1,6–1,7; Arapça Türkçenin 1,5–1,8 katı, satır 2,0–2,3. iOS varsayılan gövde 17/22 pt, en küçük metin 11 pt; ince ağırlıklardan kaçınılır ([Apple HIG Tipografi](https://developer.apple.com/design/human-interface-guidelines/typography)). Diğer arayüz boyutları Apple'ın varsayılan Dynamic Type tablosunu izler (Doğrulanacak).

| Jeton | Yazı tipi | Boyut / satır | Ağırlık | Ölçek |
|---|---|---|---|---|
| `okuma-tr` | Literata | 18 / 1,65 | 400 | Türkçe |
| `okuma-tr-dipnot` | Literata | 15 / 1,5 | 400 | Türkçe |
| `okuma-ar-kuran` | Amiri Quran | 30 / 2,2 | 400 | Arapça |
| `okuma-ar-metin-ici` | Amiri | Türkçe × 1,15; paragraf satırı ≥ 1,8 | 400 | Türkçe |
| `okuma-lugat` | IBM Plex Sans | Türkçe × 0,65, en az 11 | 400 | Türkçe |
| `baslik-buyuk` | IBM Plex Sans | 28 / 34 | 600 | Sistem |
| `baslik` | IBM Plex Sans | 22 / 28 | 600 | Sistem |
| `alt-baslik` | IBM Plex Sans | 17 / 22 | 600 | Sistem |
| `govde` | IBM Plex Sans | 17 / 22 | 400 | Sistem |
| `aciklama` | IBM Plex Sans | 15 / 20 | 400 | Sistem |
| `dipnot` | IBM Plex Sans | 13 / 18 | 400 | Sistem |
| `etiket` | IBM Plex Sans | 12 / 16 | 500 | Sistem |

`okuma-ar-kuran` Türkçe varsayılanın 1,67 katıdır. Metin içi Arapçanın %15 büyütülmesi, Apple'ın "sağdan sola metni yaklaşık 2 punto büyütme" notundan çıkarımdır ([Apple HIG RTL](https://developer.apple.com/design/human-interface-guidelines/right-to-left)).

**Kademeler (öneri).** Kaydırıcı on kademelidir; depo çarpan tutar (`arabicScale`, `turkishScale`; [Mobil mimari §5](../06-mobil/01-mobil-mimari.md#5-durum-yönetimi)). Son kademe varsayılanın iki katıdır.

| Kademe | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Türkçe (pt) | 14 | 15 | 16 | 17 | **18** | 20 | 22 | 26 | 30 | 36 |
| Arapça (pt) | 22 | 24 | 26 | 28 | **30** | 34 | 38 | 44 | 52 | 60 |

Okuma metni kademe × sistem ölçeğiyle çizilir. Arayüz metni sistem ölçeğini `maxFontSizeMultiplier` sınırına kadar izler.

### 3.3 Karışık yön ve Türkçe kuralları

- Türkçe paragraftaki her Arapça dizi kendi yazı tipi ve `writingDirection: 'rtl'` ile ayrı bir `Text` parçasıdır ([W3C](https://www.w3.org/International/articles/inline-bidi-markup/)). Üç satırdan uzun paragraf kendi dilinin yönüne hizalanır; sayıların sırası çevrilmez ([Apple HIG RTL](https://developer.apple.com/design/human-interface-guidelines/right-to-left)).
- Arayüz soldan sağadır. Arapça metindeki âyet numaraları yazı tipinin çizdiği rakamlarla, arayüzdeki sayılar Batı rakamlarıyla yazılır.
- Türkçe büyük ve küçük harf dönüşümü `trUpper` ve `trLower` ile yapılır ([Mobil mimari §14](../06-mobil/01-mobil-mimari.md#14-dil-türkçe-arayüz-i18ne-hazır-metinler)). Türkçe metinde `textTransform: 'uppercase'` kullanılmaz (öneri). "fi" bitişik harfi iki platformda denetlenir.

## 4. Boşluk, köşe ve yükselti

| Ölçek | Değerler |
|---|---|
| Boşluk (pt) | `0.5`=2 · `1`=4 · `2`=8 · `3`=12 · `4`=16 · `5`=20 · `6`=24 · `8`=32 · `10`=40 · `12`=48 · `16`=64 |
| Kenar boşluğu | Telefon 16, tablet 24; okuma sütunu satır başına 60–75 karakter (tablette en çok 640 pt, öneri) |
| Köşe | `yok` 0 · `xs` 2 · `sm` 4 · `md` 8 (kart, düğme) · `lg` 12 · `xl` 16 (alt sayfanın üst köşeleri) · `tam` 999 (çip) |
| Dokunma hedefi | 44×44 pt; en az 28×28 ([Apple HIG Erişilebilirlik](https://developer.apple.com/design/human-interface-guidelines/accessibility)); küçük simgelerde `hitSlop` |

| Yükselti | Kullanım | Görünüm |
|---|---|---|
| 0 | Okuma yüzeyi | `yuzey`, gölge yok |
| 1 | Liste ayracı, sayfa kenarı | `cizgi`, gölge yok |
| 2 | Kart, alt sayfa, mini oynatıcı | `yuzey-ust` ve `cizgi`. Kâğıt ve Âhar'da hafif gölge (metin rengi %8, bulanıklık 12, y 2; öneri). Gece'de gölge yok; yüzey açılarak ayrılır. |
| 3 | İletişim kutusu | `yuzey-ust` ve `perde` |

## 5. Hareket

| Jeton | Süre (öneri) | Kullanım |
|---|---|---|
| `anlik` | 0 ms | Hareketi Azalt açıkken bütün geçişler |
| `hizli` | 120 ms | Basma geri bildirimi, çip |
| `orta` | 200 ms | Solma, panel içeriği değişimi |
| `sayfa` | 250 ms | Sayfa çevirme kayması |
| `yavas` | 300 ms | Alt sayfanın açılması |

Eğri standart olarak `cubic-bezier(0.2, 0, 0, 1)` (öneri).

Kurallar:
- Hareket yalnız yapıyı anlatır: nereden gelindi, nereye gidildi. Süs amaçlı döngüsel animasyon yoktur.
- Sayfa kıvrılma efekti, yaylı aşma ve paralaks yoktur.
- Hareketi Azalt açıkken yatay ve dikey geçişler solmaya döner ya da anlık olur; takip kaydırması doğrudan atlar ([Apple HIG Erişilebilirlik](https://developer.apple.com/design/human-interface-guidelines/accessibility)).
- Ebru durağandır; animasyonluysa Hareketi Azalt altında durur ve metnin arkasına hiç girmez.
- Dokunsal geri bildirim seçim başında ve sonunda hafiftir; sistem ayarını izler.

## 6. Bileşen envanteri

Genel bileşenler React Native Reusables'tan gelir (düğme, iletişim kutusu, sekmeler, geçiş grubu, seçim kutusu, anahtar, ilerleme, açılır pencere). Kitaplıkta alt sayfa olmadığı için alt sayfalar @gorhom/bottom-sheet ile yapılır ([RN Reusables](https://github.com/founded-labs/react-native-reusables)). Aşağıdakiler alana özgü bileşenlerdir.

| Bileşen | Amaç | Durumlar | Erişilebilirlik ve not |
|---|---|---|---|
| `SurahHeader`, `Besmele` | Sure başı: tezhip çerçevesi, hat ad, Türkçe ad, âyet sayısı; besmele Fâtiha'da 1. âyet, Tevbe'de yok | tam · kompakt · etkin (ses bu surede) | Başlık rolü: "Bakara Sûresi, 286 âyet" |
| `PageView` | Mushaf sayfası kabı (A, B, C) | hazır · yazı tipi yükleniyor · cüz yok (C ve şerit) · lisans kapısı · hata | "Sayfa 42, Bakara 253–256" |
| `AyahMarker` | Âyet sonu işareti ve numarası | normal · etkin · seçili · yer imli · notlu · vurgulu · secde | "255. âyet sonu"; dokunuş eylem çubuğunu açar |
| `JuzMarker`, `SecdeMarker` | Cüz başı tezhibi; secde için lâl kenar işareti ve "Secde âyeti" yazısı | | Renk tek başına kullanılmaz |
| `AyahItem`, `MealPane`, `TefsirPane` | Âyet âyet öğesi; hizalı meal; etkin âyeti izleyen tefsir | etkin · seçili · bağlı · ayrık | Âyet öğesi özel eylemler taşır |
| `WordCard` | Kelime kartı | yükleniyor · anlam yok · kök paketi yok (kök satırı gizli) · ses yok | Görünür "Kapat" |
| `SelectionToolbar`, `HighlightSwatch` | Seçim eylemleri; vurgu rengi seçici | kelime · aralık · âyet (B) | Yazılı etiketler; renk adı ve simgesi |
| `LinkPanel`, `LinkResult` | Bağlantılar paneli; sonuç satırı | boş · paket eksik · lisans kapısı · önizleme açık | Adres, gerekçe ve etiket birlikte okunur |
| `ReasonChip`, `ConfidenceBadge` | Gerekçe; güven etiketi | kesin (dolu) · yüksek (çerçeveli) · orta (ince çerçeve) · düşük (kesik çizgi) | Etiket yazıyla |
| `Breadcrumb` | Kırıntı izi | tek satır; taşarsa baştan "…" | Her öğe düğme |
| `ChipSlot` | Okuyucunun altındaki tek çip yuvası | geri dönüş · okunan âyet · etkin âyet · boş | Zincir açıkken `BackChip`, yoksa `FollowChip`; iki çip birlikte görünmez ([Okuma deneyimi §9](./02-okuma-deneyimi.md#9-atla-ve-dön)) |
| `BackChip`, `FollowChip` | "↩ Okuduğun yere dön" ve "Burada kal"; "Okunan âyete dön", "Etkin âyete git" | `ChipSlot` içinde | `BackChip` iki ayrı 44 pt hedef taşır |
| `MiniPlayer`, `PlayerSheet`, `ReciterRow` | Sekme üstü oynatıcı; Dinleme sayfası (ana, hafız listesi, aralık seçici iç görünümleri); hafız satırı ve ön dinleme | çalıyor · duraklatıldı · yükleniyor · hata · indirilmiş | İlerleme yazıyla da okunur |
| `SegmentedControl`, `FontSizeSlider` | "Sayfa · Meal", "Meal · Tefsir", biçim seçimleri; kademeli boyut ve canlı önizleme | seçili · devre dışı | Radyo grubu rolü; kaydırıcının artı ve eksi düğmeleri de var |
| `StorageRow` | Paket satırı: ad, boyut, sürüm, lisans | indirilmedi · kuyrukta · iniyor % · duraklatıldı · indirildi · güncelleme var · hata | Yüzde yazıyla |
| `LicenseBadge`, `LicenseGate` | Lisans durumu rozeti; lisans paneli | Durum adları yalnız `dev` derlemesinde | |
| `UnverifiedBadge` | "doğrulanmamış" rozeti | | [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) |
| `LugatGloss`, `LugatCard`, `IbareCard`, `CitationLink`, `FootnoteMarker` | Risale katmanları | | Kısa anlam metne eklenmez |
| `HadithPair` | İki sütunlu hadis | Arapça · Türkçe · ikisi | |
| `HatimGrid`, `HatimBar` | 30 cüz ızgarası, 604 sayfa çubuğu | | Değerler yazıyla da verilir |
| `NoteLinkChip` | `[[q:2:255]]` bağlantısı | çözüldü · çözülmedi | |
| `TezhipFrame`, `SectionDivider` | İnce SVG çerçeve; çizgi süsü | | `currentColor` ile temaya uyar |

Ortak yardımcılar: `EmptyState`, `Skeleton`, `Snackbar` ("Geri al"), `SettingsRow`, `SearchField`, `ScopeChips`, `ReaderTopBar`, `PageNavButtons`, `TabBar`.

## 7. Motif kuralları

| Yapılır | Yapılmaz |
|---|---|
| Tezhip yalnız sure başlıklarında, cüz işaretlerinde, kitap kapaklarında ve hatim tamamlama ekranında; tek renkli ince SVG çerçeve, `currentColor` ile temaya uyar | Tezhibi metnin arkasına koymak |
| Hat yalnız anlam taşıdığı yerde: sure adları, besmele, uygulama işareti | Süs amaçlı sahte Arapça |
| Çini paleti ve ara sıra saz yaprağı ya da dört çiçek üslubunda çizgi süsleri, bölüm ayracı olarak | Laleyi her yerde kullanmak; aşırı kullanılmış bir "Türk" işaretidir |
| Ebru yalnız açılış, tanıtım, boş durum ve kitap kapaklarında | Ebruyu metnin altında ya da animasyonlu arka plan olarak kullanmak |
| Kur'an bölümünde tezhip, Risale bölümünde yalın çizgi süsü | Cami silueti, ay-yıldız, yeşil-altın gradyan, parlak arabesk duvar kâğıdı |

Kaynak: araştırma raporu ve tasarım notu ([Kaynakça](../09-kaynakca.md)).

## 8. İkonografi

- Tek bir çizgi simge takımı kullanılır: 24 pt ızgara, 1,5 pt çizgi, yuvarlak uçlar; IBM Plex Sans'ın ağırlığına uyar. Takım seçimi Doğrulanacak: Expo SDK 56'dan beri `@expo/vector-icons` yerini `@react-native-vector-icons/*` paketlerine bırakıyor ([Expo SDK 56](https://expo.dev/changelog/sdk-56)); React Native Reusables'ın kullandığı takım ve lisansı ayrıca okunmalı.
- Alana özgü simgeler ayrıca çizilir: mushaf, meal, tefsir, hadis, Risale, kök, iktibas, âyet sonu, secde, cüz, hafız, hatim, lügat, bağlantı, geri dönüş.
- Sekme simgeleri her zaman yazılı etiketle görünür. Yalnız simgeden oluşan düğme erişilebilirlik etiketi taşır.
- Anlamlı simgeler yazı boyutuyla büyür ([Apple HIG Tipografi](https://developer.apple.com/design/human-interface-guidelines/typography)).
- Sağdan sola düzende yalnız gezinme okları (sayfalayıcıdaki ‹ ›) çevrilir. Diğer simgeler çevrilmez ([Apple HIG RTL](https://developer.apple.com/design/human-interface-guidelines/right-to-left)).
- Hilal, cami ve benzeri klişe simgeler kullanılmaz.
- Uygulama işareti hat içerebilir; tasarımı Açık soru.

## 9. Erişilebilirlik kontrol listesi

Her ekran yayından önce bu listeden geçer. Kaynaklar: [Apple HIG Erişilebilirlik](https://developer.apple.com/design/human-interface-guidelines/accessibility), [NN/g yaşlı kullanıcılar](https://www.nngroup.com/articles/usability-for-senior-citizens/), [W3C](https://www.w3.org/International/articles/inline-bidi-markup/).

**Görsel**
- [ ] Bütün metin jetonları üç temada en az 4,5:1; büyük ve kalın metin en az 3:1.
- [ ] Bileşen sınırları ve odak halkası en az 3:1.
- [ ] Hiçbir bilgi yalnız renkle verilmez: vurgu adı ve simgesi, yazılı güven etiketi, ses vurgusunda zemin ve çizgi.

**Metin**
- [ ] Arapça ve Türkçe boyut ayrı ayarlanır; okuma metni %200'de kesilmeden okunur.
- [ ] Arayüz metni sistem yazı ölçeğini izler; sistem erişilebilirlik boyutlarında çok sütunlu düzen tek sütuna iner.
- [ ] Yakınlaştırma hiçbir ekranda kapatılmaz.
- [ ] Türkçe paragraftaki Arapça diziler ayrı yönle işaretlidir.

**Etkileşim**
- [ ] Dokunma hedefleri en az 44×44 pt.
- [ ] Her kaydırma jestinin görünür bir düğmesi var: sayfa çevirme, alt sayfa kapatma, silme.
- [ ] Mod A'da kelime seçiminin "Seç" düğmeli yolu çalışır.
- [ ] Alt sayfalar üst üste binmez; "Kapat" görünür; Android geri tuşu alt sayfayı kapatır.
- [ ] Zamanlayıcıyla kendiliğinden kaybolan kontrol yok.

**Ekran okuyucu**
- [ ] Mod A ve B'de glif ve görsel katmanı gizli; her âyet Türkçe etiketli ve Arapça Unicode metinli tek öğe.
- [ ] Âyet öğelerinde Dinle, Meali oku, Tefsir (tefsir paketi kuruluyken), Vurgula, Bağlantılar eylemleri var.
- [ ] Ekran okuyucu açılınca Erişilebilir metin modu önerilir.
- [ ] VoiceOver ve TalkBack ile Fâtiha ve Bakara 255 üç çizim yolunda okunur.

**Hareket ve ses**
- [ ] Hareketi Azalt açıkken kayan geçişler yerine solma ya da anlık geçiş var.
- [ ] Ses kendiliğinden başlamaz; her çalmanın görünür bir durdurma düğmesi var.

## 10. `packages/ui-tokens`

Renkler, tip ölçeği, boşluk, köşe ve hareket tek JSON kaynaktan hem mobil temaya hem web ve editör CSS değişkenlerine derlenir ([araştırma raporu](../09-kaynakca.md)). Bu yol üç temanın web ve mobilde aynı kalmasını sağlar.

```
packages/ui-tokens/
├─ src/tokens.json            tek kaynak
├─ src/schema.json            JSON Şeması; derlemede doğrulanır
├─ src/build.ts               üreteç
├─ test/contrast.test.ts      eşik altındaki çift derlemeyi durdurur
└─ dist/                      üretilir
   ├─ tokens.ts               tipli nesne: SVG, Reanimated, alt sayfa gibi ham renk isteyen yerler
   ├─ nativewind-preset.js    NativeWind v4 ön ayarı (mobil)
   ├─ tailwind.css            Tailwind v4 @theme ve tema değişkenleri (web, editör)
   └─ kontrast.md             derlemede hesaplanan kontrast tablosu
```

```json
{
  "meta": { "ad": "sade-osmanli", "surum": "1.0.0" },
  "temalar": ["kagit", "ahar", "gece"],
  "renk": {
    "yuzey":    { "kagit": "#FBF8F1", "ahar": "#F3E9D2", "gece": "#14181D" },
    "metin":    { "kagit": "#1F1A14", "ahar": "#2A2017", "gece": "#E8E2D4" },
    "baglanti": { "kagit": "#1E4F8F", "ahar": "#1E4F8F", "gece": "#8FB4E8" },
    "etkin":    { "kagit": "#0B6E72", "ahar": "#6E5426", "gece": "#5CC4C0" },
    "sus":      { "kagit": "#B38B3F", "ahar": "#9A7A3A", "gece": "#D6B46A", "yalnizSus": true },
    "vurgu": {
      "onemli": { "zemin": { "kagit": "#F3E4B5", "ahar": "#EDD9A2", "gece": "#45391B" },
                  "isaret": { "kagit": "#8A6A2B", "ahar": "#7A5D24", "gece": "#D6B46A" } }
    }
  },
  "kontrast": [
    { "on": "metin", "arka": "yuzey", "enAz": 4.5 },
    { "on": "cizgi-guclu", "arka": "yuzey", "enAz": 3.0 },
    { "on": "metin", "arka": "vurgu.*.zemin", "enAz": 4.5 }
  ],
  "yazi": {
    "okuma-tr":       { "aile": "Literata",   "boyut": 18, "satir": 1.65, "agirlik": 400, "olcek": "turkce" },
    "okuma-ar-kuran": { "aile": "AmiriQuran", "boyut": 30, "satir": 2.2,  "agirlik": 400, "olcek": "arapca" }
  },
  "kademe": { "turkce": [14,15,16,17,18,20,22,26,30,36], "arapca": [22,24,26,28,30,34,38,44,52,60], "varsayilan": 5 },
  "bosluk": { "0.5": 2, "1": 4, "2": 8, "3": 12, "4": 16, "5": 20, "6": 24, "8": 32, "10": 40, "12": 48, "16": 64 },
  "kose":   { "yok": 0, "xs": 2, "sm": 4, "md": 8, "lg": 12, "xl": 16, "tam": 999 },
  "hareket": { "anlik": 0, "hizli": 120, "orta": 200, "sayfa": 250, "yavas": 300 }
}
```

**Mobil (NativeWind v4).** NativeWind v4 kararlı sürümdür; v5 ön sürüm ve "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)). Ön ayar renkleri CSS değişkeni olarak tanımlar (`yuzey: 'rgb(var(--yuzey) / <alpha-value>)'`). Kökteki tema sağlayıcısı etkin temanın değişkenlerini NativeWind'in `vars()` yardımcısıyla uygular; sınıflar `bg-yuzey text-metin` biçimindedir. NativeWind v4'ün Tailwind v3 yapılandırma biçimini kullandığı ve `vars()` imzası Doğrulanacak.

**Web ve editör (Tailwind v4).** `tailwind.css` jetonları `@theme` içinde değişkene bağlar ve her tema için `[data-theme="gece"]` gibi bir değişken bloğu üretir. Editör paneli (K-13) ve web (K-14) aynı dosyayı içe aktarır.

**Kurallar**
- Uygulama kodunda onaltılık renk yazılmaz. ESLint kuralı `#` ile başlayan renk dizgesini `packages/ui-tokens` dışında yakalar (öneri).
- `kontrast` listesindeki her çift üç temada hesaplanır. Eşik altı bir çift derlemeyi durdurur; sonuç `kontrast.md` dosyasına yazılır.
- Jeton değişikliği bir sürüm artışıdır; Tasarım vitrini ekran görüntüleri yeniden alınır.

## 11. Tasarım vitrini

Ekranlardan önce kurulan, yalnız geliştirici derlemelerinde görünen bir ekrandır; rapor görsel kararların ekranlar yazılmadan gözden geçirilmesi için önerir ([araştırma raporu](../09-kaynakca.md)).

- **Rota:** `app/(tabs)/ayarlar/gelistirici/vitrin.tsx`. `tasarimVitrini` bayrağı `dev` ve `internal` derlemede açık, `public` derlemede kapalıdır; orada rota Ayarlar'a yönlendirilir ([Mobil mimari §10](../06-mobil/01-mobil-mimari.md#10-derleme-türleri-ve-özellik-bayrakları)).
- **Denetimler:** tema, yazı boyutu (varsayılan, kademe 8, %200), Hareketi Azalt, sayfa çevirme yönü, dokunma alanlarını gösteren katman.
- **Bölümler:** renkler (değer ve çalışma anında hesaplanan kontrast; eşik altı çift `isaret` çerçevesiyle işaretlenir) · tipografi (bütün roller, â î û içeren Türkçe örnek, Fâtiha'nın ilk âyeti, karışık yönlü meal paragrafı) · okuyucu parçaları (Fâtiha sayfası C ile, `AyahMarker` durumları, `WordCard`, bütün güven etiketleriyle `LinkResult`, `ChipSlot`, `MiniPlayer`, `PlayerSheet`) · genel bileşenler · motifler.
- **Örnek metin:** yalnız Tanzil metni ve Elmalılı meali; Risale metni vitrinde yer almaz.
- **Kullanım:** her jeton ya da bileşen değişikliğinden sonra üç tema ve üç boyutta ekran görüntüsü alınıp karşılaştırılır ([Test stratejisi](../07-yayin/03-test-stratejisi.md)).

## 12. Açık sorular

| No | Soru | Sahibi |
|---|---|---|
| TS-1 | Arayüz yazı tipi: brif IBM Plex Sans der, rapor Inter önerir. Seçim karar defterine işlenmeli; IBM Plex Sans'ın Türkçe ve â î û kapsamı ölçülmeli. | Proje sahibi |
| TS-2 | Sure adı hattı için yazı tipi ve lisansı | [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) |
| TS-3 | Simge takımı ve lisansı | Bu dosya, sonraki sürüm |
| TS-4 | Ek rol jetonlarının, vurgu renklerinin ve `bolum-risale` zümrüdünün onayı | Proje sahibi |
| TS-5 | Tecvid renklerinin (V4) üç temada kontrastı | v1.x |
| TS-6 | Mod B görsellerinin Gece temasında boyanması ya da ters çevrilmesi | [Mobil mimari](../06-mobil/01-mobil-mimari.md) (MM-7) |
| TS-7 | Uygulama işareti tasarımı | Proje sahibi |
| TS-8 | NativeWind v4 tema değişkeni yöntemi (`vars()`) ve Tailwind sürüm uyumu | Prototip |

## İlgili dosyalar

- [Kapsam ve fazlar](./01-kapsam-ve-fazlar.md) · [Okuma deneyimi](./02-okuma-deneyimi.md) · [Mobil ekranlar](./03-mobil-ekranlar.md)
- [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Proje yapısı](../02-mimari/03-proje-yapisi.md) · [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md)
- [Test stratejisi](../07-yayin/03-test-stratejisi.md)
- [Karar defteri](../00-ozet/02-karar-defteri.md) · [Sözlük](../00-ozet/03-sozluk.md) · [Kaynakça](../09-kaynakca.md)
