# Riskler

> **Sürüm:** 1.5 · **Tarih:** 11 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-49](../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses) · [K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme)

Bu dosya risk kaydıdır. Olasılık ve etki 1–5 arası puanlanır; skor ikisinin çarpımıdır. Puanlar değerlendirmedir (tahmin) ve gözden geçirmede değişebilir.

| Skor | Seviye | Eylem |
|---|---|---|
| 1–4 | Düşük | İzle |
| 5–9 | Orta | Önlemi hazır tut, tetiği izle |
| 10–14 | Yüksek | Önlemi şimdi uygula |
| 15–25 | Kritik | Faz planında öncelik, haftalık bak |

| Rol | Sorumluluk |
|---|---|
| Proje sahibi | Karar, faz geçişleri, hesaplar ve ödemeler |
| Geliştirici | Mobil, arka uç, içerik hattı, Publisher, testler |
| İçerik editörü | OCR düzeltme, bağlantı onayı, kelime anlamı onayı |

Tek geliştiricili dönemde bir kişi birden çok rolü taşır.

## 1. Özet

| ID | Risk | O | E | Skor | Seviye | Sahip |
|---|---|---|---|---|---|---|
| R-03 | Ses kaynağı ve ayna: erişilebilirlik, depolama maliyeti | 3 | 3 | 9 | Orta | Geliştirici |
| R-07 | Elmalılı metin kalitesi (hazır metin; baskı esası belgesiz) | 4 | 4 | 16 | Kritik | İçerik editörü |
| R-08 | Yanlış pozitif bağlantıların güveni aşındırması | 3 | 4 | 12 | Yüksek | İçerik editörü, geliştirici |
| R-09 | Türkçe yerel ayar hataları | 4 | 3 | 12 | Yüksek | Geliştirici |
| R-10 | Uygulama boyutu | 3 | 3 | 9 | Orta | Geliştirici |
| R-11 | iOS 16.4 asgari sürümünün eski iPhone'ları dışarıda bırakması | 5 | 2 | 10 | Yüksek | Proje sahibi |
| R-12 | Dini içeriğin mağaza incelemesi | 2 | 3 | 6 | Orta | Proje sahibi |
| R-14 | Tek geliştiricinin tükenmesi | 4 | 5 | 20 | Kritik | Proje sahibi |
| R-15 | Tanzil metninin istemeden değişmesi (ek) | 2 | 4 | 8 | Orta | Geliştirici |
| R-17 | Tarafsızlık algısı (ek) | 2 | 4 | 8 | Orta | Proje sahibi |
| R-18 | SDK geçişi ve kitaplık ön sürümleri (ek) | 3 | 2 | 6 | Orta | Geliştirici |
| R-19 | v1'de cihazdaki kullanıcı verisinin kaybı (ek) | 3 | 2 | 6 | Orta | Geliştirici |
| R-20 | Arka planda ses ve kilit ekranı (ek) | 4 | 3 | 12 | Yüksek | Geliştirici |
| R-21 | Hazır metinden sadeleştirme ya da belirsiz baskı sızması (ek) | 3 | 4 | 12 | Yüksek | İçerik editörü |

| Olasılık \ Etki | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| 5 | R-11 | | | |
| 4 | | R-09, R-20 | R-07 | R-14 |
| 3 | R-18, R-19 | R-03, R-10 | R-08, R-21 | |
| 2 | | R-12 | R-15, R-17 | |

## 2. Kayıt

### R-03 · Ses kaynağı ve ayna: erişilebilirlik, depolama maliyeti
- **Açıklama.** Ses dosyaları üçüncü taraf kaynaklardan (MP3Quran CDN, Tarteel CDN) gelir. Kaynakta dosyanın değişmesi ya da adresin taşınması zamanlamayı kaydırır; kaynak sunucusunun erişilemez olması indirmeyi durdurur. Kaynaklar boyut ve sha256 vermez ([Ses kaynağı araştırması](../06-mobil/04-ses-kaynak-arastirmasi.md) §5.2). Ayna bunları çözer ama maliyet getirir: dokuz kayıt için yaklaşık 19,74 GB depolama ve çıkış trafiği (1.026 dosya, 3 Kasım 2026 ön ölçümü). Depo ücretliyse tahmini maliyet kullanıcıya gösterilir (S-03, İ-18).
- **Önlem.** Claude Code dosyaları kaynaktan bir kez indirir (`data/gelen/<kaynak>/<YYYY-AA-GG>/`); içerik hattı sha256 ile kilitler ve Yayınlayıcı kendi depomuzdan değişmez sürümlü adresle sunar (ayna). Kaynak değişirse yeni `dosya_surumu` açılır. Uygulama üçüncü taraf ses sunucusuna bağlanmaz ([K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) madde 4); bu yüzden kaynağın erişilemez olması dinlemeyi etkilemez. Dosya bozulur ya da zamanlaması tutmazsa kayıt katalogdan çıkarılır, çalma durur, dosyalar silinmek üzere işaretlenir ([Ses sistemi](../06-mobil/02-ses-sistemi.md) §12). Depolama maliyeti için çıkış ücretsiz depo (R2) önerilir; boyut her sürümde kaydedilir.
- **Tetik.** Kaynakta sha256 ya da boyut farkı; kaynak adresinin erişilemez olması; ayna depolama maliyetinin bütçeyi aşması.

### R-07 · Elmalılı metin kalitesi (hazır metin; baskı esası belgesiz)
- **Açıklama.** Elmalılı mealleri hazır dijital metinle alınır ([K-49](../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)): orijinal meal Vikikaynak "Kur'an" sayfalarından (2007'de kaynaksız girilmiş; baskı esası belgesiz), güncel meal fawazahmed0 `tur-elmallsadelesti` dosyasından (sadeleştirilmiş; sadeleştireni belirtilmemiş). İnternette "Elmalılı" adıyla dolaşan metinler üç ailedir (özgün, sadeleştirilmiş, "yeni Elmalılı"); yanlış aileden alınan metin yanlış kişiye atfedilebilir. 6.442 sayfalık özgün baskının (İstanbul 1935–1939) indirilebilir taraması internette bulunamadı; OCR ve özgün baskıyla karşılaştırma proje sonuna ertelendi ([S-15](./02-sonra-yapilacaklar.md)). Meal `core`'un parçasıdır; ikinci editör onayı tamamlanmayan âyet `public`'e girmez (P-10) ve bir meal kaynağı G-INC geçmeden `public`'e çıkmaz.
- **Önlem.** Otomatik denetimler (6.236 âyet kapsamı, orijinal mealde çapraz tanık raporu ve sadeleştirme taraması); kaynak kilidi (revizyon ve SHA-256); `taslak` giriş; iki insan turu (tur 1 her âyetin iki kişiyle onayı, tur 2 en az 600 âyetlik ikinci okuma); her düzeltme hattan geçer ve `content_hash` değişimini kaydeder; dürüst atıf (baskı esası belgesiz denir); tefsir metni meal yolundan ayrı yürür ([Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md)). Özgün baskıyla karşılaştırma S-15'tedir.
- **Tetik.** Çapraz tanık raporunda düşük uyum ya da sistematik fark; ikinci okumada hatalı âyet oranının hedefi (< %0,5) aşması; düzeltme hızının planın gerisinde kalması; S-15 başlarsa özgün baskıyla karşılaştırmada sapma.

### R-08 · Yanlış pozitif bağlantıların güveni aşındırması
- **Açıklama.** En büyük yanlış pozitif kaynağı kısa ve kalıplaşmış ifadeler. QUL 5.641 tekrarlanan ifade listeliyor; "تَجْرِى مِن تَحْتِهَا ٱلْأَنْهَـٰرُ خَـٰلِدِينَ" 18 âyette geçiyor ([QUL](https://qul.tarteel.ai/morphology_phrases?page=61)). Basılı fihristte Kur'an'da karşılığı bulunmayan bir kayıt da not edilmiş ([RİNAP](https://rinap.uskudar.edu.tr/uploads/site/6/content/files/risale-i-nurun-tefsirdeki-yeri-compressed.pdf)).
- **Önlem.** Dört kelimeden kısa ifadeler ve kalıplar düşük ön güvenle başlar; bağlam sinyalleri güveni yükseltir; altın set kapıları ve gerileme kuralı ([Test stratejisi](../07-yayin/03-test-stratejisi.md)); düşük güvenli bağlantılar "Daha fazla (otomatik)" altında katlanır; her bağlantı gerekçe etiketi ve güven düzeyi taşır; olumlu ve olumsuz oylar inceleme kuyruğunu besler; yapay zekâ metni "doğrulanmamış" rozeti taşır ([K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)).
- **Tetik.** Bir türde olumsuz oy oranının eşiği aşması (eşik Açık soru); gece değerlendirmesinde kesinlik düşüşü.

### R-09 · Türkçe yerel ayar hataları
- **Açıklama.** FTS5'in varsayılan tokenizer'ı "Işık" kelimesini `ışık`, `IŞIK` ve `isik` sorgularıyla bulamadı ([SQLite FTS5](https://sqlite.org/fts5.html), rapordaki yerel deneme). Python'da `"İ".lower()` iki kod noktası üretir; .NET küçük harf dönüşümü kültüre bağlıdır; JS ve C# ofseti UTF-16 birimiyle sayar.
- **Önlem.** Ortak test vektörleri üç dilde; açık harf eşlemesi; cihazda öz test; indeks normalize `search_text` üzerinde; kültüre bağlı çağrıları yakalayan lint kuralı (öneri).
- **Tetik.** Bir vektörün herhangi bir dilde kırılması; "bulunamadı" geri bildirimi.

### R-10 · Uygulama boyutu
- **Açıklama.** QPC V2 sayfa fontlarının tam seti woff2 biçiminde 93,2 MB, tek Unicode font 87.760 bayt ([Quran.com font klasörü](https://github.com/quran/quran.com-frontend-next/tree/production/public/fonts/quran/hafs)). Araştırma notu bütün metinlerin FTS indeksleriyle cihazda 60–120 MB tutabileceğini, bir hafızın tam kaydının 0,5–1,5 GB olabileceğini tahmin ediyor.
- **Önlem.** `core` küçük tutulur; fontlar cüz başına iner (cüz başına ~3 MB, tahmin); ses ve paketler isteğe bağlıdır; Depolama yöneticisi ([K-18](../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de)); yalnız Wi-Fi ile indirme; her sürümde boyut kaydı. Boyut bütçesi Açık soru.
- **Tetik.** İndirme boyutunun bütçeyi aşması; mağaza yorumlarında boyut şikâyeti.

### R-11 · iOS 16.4 asgari sürümü
- **Açıklama.** Expo SDK 56'dan itibaren asgari iOS sürümü 16.4; iPhone 7, 6s ve ilk SE desteklenmiyor ([Expo SDK 56](https://expo.dev/changelog/sdk-56)). Rapor yaşlı kullanıcı kitlesi için bunun not edilmesini istiyor. Hedef kitlenin cihaz dağılımı araştırılmadı; Android asgari sürümü bulunamadı.
- **Önlem.** Mağaza sayfasında asgari sürüm açıkça yazılır; mağaza konsollarının cihaz istatistikleri izlenir; Faz 5 web sürümü eski cihazlar için bir yol olabilir (tarayıcı desteği Doğrulanacak).
- **Tetik.** "Yüklenemiyor" geri bildirimlerinde artış.

### R-12 · Dini içeriğin mağaza incelemesi
- **Açıklama.** Araştırma App Store ve Google Play'in dini içerik incelemesine dair bir kaynak bulmadı (Doğrulanacak). Eski plan Apple reddini orta risk sayıyordu (`quran-app-docs/14-riskler/01-risk-matrisi.md`). Ret ya da ek bilgi talebi teknik ve kalite gerekçelerinden gelebilir: çökme, eksik ya da yanıltıcı mağaza metni, gizlilik beyanıyla davranışın uyuşmaması.
- **Önlem.** TestFlight ve Google Play kapalı testi erken açılır; mağaza metni resmî kurum çağrışımı taşımaz ve kurum logosu kullanılmaz; Kaynaklar ekranı (atıflar) ve gizlilik beyanları itiraz dosyasında hazır durur; reklam yoktur.
- **Tetik.** Ret ya da ek bilgi talebi.

### R-14 · Tek geliştiricinin tükenmesi
- **Açıklama.** Eski plan bu riski en üst sıraya koyuyordu; rapor çok servisli bir mimarinin tek geliştiricinin en büyük riskini büyüttüğünü söylüyor. Aşama sayısı yüksektir (A00–A40) ve editör emeği isteyen işler (OCR düzeltme turları, bağlantı ve kelime anlamı onayı) uzun sürer.
- **Önlem.** İnce mimari ([K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)); faz çıkış ölçütleri; Sonra yapılacaklar park alanı; CI ve Publisher otomasyonu; yapay zekâ destekli geliştirme; süreçlerin yazılı olması; haftalık dinlenme ritmi (eski plandaki yarım gün ve tam gün dinlenme önerisi); bekleyen insan adımının yalnız kendisine bağlı alt adımı bekletmesi, aşamanın kalanının sürmesi ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 3).
- **Tetik.** İki faz çıkışının üst üste kayması; uzun süre yüksek çalışma saati; öz değerlendirmede motivasyon düşüşü.

### R-15 · Tanzil metninin istemeden değişmesi (ek)
- **Açıklama.** Tanzil metni bayt bayt saklanır ([K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)). NFC dönüşümü Arapça hareke sırasını değiştirebilir; bu, kanonik metni kaynaktan ayırır ve `content_hash` ile içerik özetini bozar.
- **Önlem.** Değişmezlik testleri; görüntüleme yalnız kanonik metinden; Tanzil metnine NFC bile uygulanmaz (K-26) ([Test stratejisi](../07-yayin/03-test-stratejisi.md)).
- **Tetik.** Değişmezlik testinin kırılması.

### R-17 · Tarafsızlık algısı (ek)
- **Açıklama.** Türkiye'deki güçlü rakiplerin hepsi bir kuruma bağlı; rapor tarafsızlığı pazarda boş duran bir konum olarak görüyor. Tek bir yayınevine ya da topluluğa bağlı görünmek (kaynak seçimi, atıf ve ifade biçimiyle) bu konumu zedeler.
- **Önlem.** [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler); kaynaklar kalite ölçütüyle seçilir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1); baskılar arası sayfa eşlemesi; metinlerde topluluk adı kullanılmaz.
- **Tetik.** Kamuoyunda bağlılık iddiası.

### R-18 · SDK geçişi ve kitaplık ön sürümleri (ek)
- **Açıklama.** Expo SDK 58 beta React Native 0.88 RC üzerinde ([SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)); NativeWind v5 "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)); react-native-track-player v5 ticari kullanımda ücretli ([RNTP](https://github.com/doublesymmetry/react-native-track-player)).
- **Önlem.** SDK 57 ile başlanır, 58 kararlı olunca geçilir ([K-09](../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji)); NativeWind v4 ([K-29](../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları)); expo-audio ([K-28](../00-ozet/02-karar-defteri.md#k-28--ses)); bağımlılıklar CI'da listelenir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 6) ve ücretli kitaplıkta tahmini maliyet kullanıcıya gösterilir.
- **Tetik.** SDK 58 kararlı sürümü; bir bağımlılığın ücretli hâle gelmesi ya da bakımının durması.

### R-19 · v1'de cihazdaki kullanıcı verisinin kaybı (ek)
- **Açıklama.** v1 hesapsızdır; telefon kaybı ya da uygulamanın silinmesi notları götürür.
- **Önlem.** İşletim sistemi yedeği açık (öneri); Verilerimi dışa aktar (öneri); v1.x senkron.
- **Tetik.** Veri kaybı şikâyetleri.

### R-20 · Arka planda ses ve kilit ekranı (ek)
- **Açıklama.** Android'de kilit ekranı denetimi etkin değilse arka plandaki ses yaklaşık 3 dakika sonra kesilir. SDK 58'de kilit ekranı oynatma listesiyle çalışır (expo-audio 58.0.0); tek oynatıcıda sonraki/önceki düğmesi yoktur ([#43538](https://github.com/expo/expo/issues/43538)). Listede kilit ekranı açıldıktan sonra öğe eklemek Android'de çöküyor ([#52192](https://github.com/expo/expo/issues/52192)).
- **Önlem.** Varsayılan motor `PlaylistEngine` (sure dosyaları parça, kilit ekranında sonraki/önceki sure); liste kilit ekranından önce tam kurulur; oynatıcı modül düzeyindedir. Yedek `SingleEngine` kilit ekranını yine açar ([Ses sistemi](../06-mobil/02-ses-sistemi.md) §4).
- **Tetik.** İç testte arka planda sesin kesilmesi; listede çökme ya da perde bozulması (cihaz ölçümü, kullanıcı).

### R-21 · Hazır metinden sadeleştirme ya da belirsiz baskı sızması (ek)
- **Açıklama.** Kontrollü hazır metin yolunda ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme), [K-49](../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)) orijinal mealin sadeleştirilmiş ya da baskı esası belirsiz bir metne dayanması ve bunun fark edilmeden temel metin olması mümkün. Sadeleştirilmiş metin yalnız ayrı adlı güncel meal (`meal:elmalili-sade`) olarak girer ve "sadeleştirilmiş" etiketi taşır; orijinal meale ya da tefsire sızması engellenir. Özgün metne sadakat bozulur; sızan hata `core`'daki mealin tamamını etkiler (R-07).
- **Önlem.** Aile işareti ölçümü (16:43 âyetindeki çeviri farkı; A16.0); 6.236 âyet kapsam ve orijinal mealde sadeleştirme taraması (veriye dayanır); kaynak kilidi (revizyon numarası ve SHA-256); hazır metin `taslak` girer ve iki tur insan onayı alır; onaysız hazır metin `public` derlemeye girmez (P-10, [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 5). Özgün baskı görseliyle karşılaştırma S-15'tedir.
- **Tetik.** Orijinal mealde sadeleştirme izi bulunması; kilitli revizyonla indirilen dosyanın özetinin uyuşmaması; ikinci okumada sistematik fark.

## 3. Gözden geçirme

- Kritik riskler (R-07, R-14) haftada bir; bütün kayıt ayda bir ve her faz geçişinde gözden geçirilir.
- Tetik gerçekleşince risk hemen ele alınır ve önlem kaydı tarihle yazılır.
- Kapanan risk silinmez; "Kapandı" olarak işaretlenir. Yeni risk sıradaki numarayı alır. Numaralar yeniden kullanılmaz ve yeniden numaralandırılmaz.

## İlgili dosyalar

- [Fazlar](./01-fazlar.md) · [Sonra yapılacaklar](./02-sonra-yapilacaklar.md)
- [Yayın süreci](../07-yayin/01-yayin-sureci.md) · [Gizlilik](../07-yayin/02-gizlilik.md) · [Test stratejisi](../07-yayin/03-test-stratejisi.md)
- [Kaynaklar](../04-icerik/01-kaynaklar.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) · [Arama](../03-veri/05-arama-fts5.md)
- [Kaynakça](../09-kaynakca.md) · [Karar defteri](../00-ozet/02-karar-defteri.md)
