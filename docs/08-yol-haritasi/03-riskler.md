# Riskler

> **Sürüm:** 1.2 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-15](../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses) · [K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)

Bu dosya risk kaydıdır. Olasılık ve etki 1–5 arası puanlanır; skor ikisinin çarpımıdır. Puanlar değerlendirmedir (tahmin) ve gözden geçirmede değişebilir. Hukuki riskler için **hukuki görüş değildir**.

| Skor | Seviye | Eylem |
|---|---|---|
| 1–4 | Düşük | İzle |
| 5–9 | Orta | Önlemi hazır tut, tetiği izle |
| 10–14 | Yüksek | Önlemi şimdi uygula |
| 15–25 | Kritik | Faz planında öncelik, haftalık bak |

| Rol | Sorumluluk |
|---|---|
| Proje sahibi | Karar, dış görüşmeler (Kurul, hak sahipleri, hafızlar), faz geçişleri |
| Geliştirici | Mobil, arka uç, içerik hattı, Publisher, testler |
| İçerik editörü | OCR düzeltme, bağlantı onayı, lisans defteri |
| Hukuk danışmanı (dış) | Telif, KVKK ve Kurul konularında görüş |

Tek geliştiricili dönemde bir kişi birden çok rolü taşır.

## 1. Özet

| ID | Risk | O | E | Skor | Seviye | Sahip |
|---|---|---|---|---|---|---|
| R-01 | Kurul onayının gecikmesi ya da reddi | 3 | 5 | 15 | Kritik | Proje sahibi |
| R-02 | Risale hakları | 3 | 4 | 12 | Yüksek | Proje sahibi, hukuk |
| R-03 | Ses lisansı | 4 | 3 | 12 | Yüksek | Proje sahibi |
| R-04 | Quran Foundation şartlarının değişmesi | 2 | 3 | 6 | Orta | Geliştirici |
| R-05 | QAC lisans belirsizliği | 3 | 3 | 9 | Orta | Proje sahibi |
| R-06 | Hadis veri setlerinin kökeni | 4 | 2 | 8 | Orta | İçerik editörü |
| R-07 | Elmalılı metin kalitesi (OCR ya da hazır metin) | 4 | 4 | 16 | Kritik | İçerik editörü |
| R-08 | Yanlış pozitif bağlantıların güveni aşındırması | 3 | 4 | 12 | Yüksek | İçerik editörü, geliştirici |
| R-09 | Türkçe yerel ayar hataları | 4 | 3 | 12 | Yüksek | Geliştirici |
| R-10 | Uygulama boyutu | 3 | 3 | 9 | Orta | Geliştirici |
| R-11 | iOS 16.4 asgari sürümünün eski iPhone'ları dışarıda bırakması | 5 | 2 | 10 | Yüksek | Proje sahibi |
| R-12 | Dini içeriğin mağaza incelemesi | 2 | 3 | 6 | Orta | Proje sahibi |
| R-13 | Hesaplar gelince KVKK | 3 | 4 | 12 | Yüksek | Proje sahibi, hukuk |
| R-14 | Tek geliştiricinin tükenmesi | 4 | 5 | 20 | Kritik | Proje sahibi |
| R-15 | Tanzil metninin istemeden değişmesi (ek) | 2 | 4 | 8 | Orta | Geliştirici |
| R-16 | Font lisansları (ek) | 3 | 2 | 6 | Orta | Proje sahibi |
| R-17 | Tarafsızlık algısı (ek) | 2 | 4 | 8 | Orta | Proje sahibi |
| R-18 | SDK geçişi ve kitaplık ön sürümleri (ek) | 3 | 2 | 6 | Orta | Geliştirici |
| R-19 | v1'de cihazdaki kullanıcı verisinin kaybı (ek) | 3 | 2 | 6 | Orta | Geliştirici |
| R-20 | SDK 57'de arka planda sesin kesilmesi (ek) | 4 | 3 | 12 | Yüksek | Geliştirici |
| R-21 | Hazır metinden sadeleştirme ya da belirsiz baskı sızması (ek) | 3 | 4 | 12 | Yüksek | İçerik editörü, hukuk |

| Olasılık \ Etki | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| 5 | R-11 | | | |
| 4 | R-06 | R-03, R-09, R-20 | R-07 | R-14 |
| 3 | R-16, R-18, R-19 | R-05, R-10 | R-02, R-08, R-13, R-21 | R-01 |
| 2 | | R-04, R-12 | R-15, R-17 | |

## 2. Kayıt

### R-01 · Kurul onayının gecikmesi ya da reddi
- **Açıklama.** 633 sayılı Kanun m. 6 elektronik ve sesli Kur'an ile mealli mushafı Kurul onayına bağlıyor ([Lexpera, 633](https://www.lexpera.com.tr/mevzuat/kanunlar/diyanet-isleri-baskanligi-kurulus-ve-gorevleri-hakkinda-kanun-633)). Başvuru usulü, ücret ve süre bilinmiyor. Medine düzenli fontların kabulü belirsiz. Onay sürüme bağlı ([Memurlar.net, 2022](https://www.memurlar.net/haber/1045766/kur-an-i-kerim-basim-ve-yayim-kriterleri-hakkinda-yonetmelik-resmi-gazete-de-yayimlandi.html)). `core` onaysız public derlemeye giremez. Onayın Kur'an metninin yanında gösterilen bağlantı ve dizin verisini de kapsayıp kapsamadığı Açık soru.
- **Önlem.** Ön görüşme Faz 0'ın ilk işi; içerik dondurma; başvuru dosyası Faz 2 ile paralel; meal düzeltme turları başvurudan önce kapanır; Mushaf C yedek; düzeltmeler onay treniyle ([Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md)).
- **Tetik.** Ön görüşme talebine proje sahibinin belirlediği sürede cevap gelmemesi; düzeltme ya da ret yazısı; font sorusuna olumsuz cevap.

### R-02 · Risale hakları
- **Açıklama.** Risale-i Nur 31 Aralık 2030'a kadar korunuyor ve hakları bugün kimin kullandığı belirsiz ([TDV İslâm Ansiklopedisi](https://islamansiklopedisi.org.tr/risale-i-nur-kulliyati); [T24](https://t24.com.tr/haber/aym-risale-i-nur-yasagini-iptal-etti,299364)). Metnin iç test grubuna dahi dağıtılması ihlal sayılabilir. Tek bir topluluğun yayınevinden lisans almak tarafsızlığı zedeler. Telifli metnin dizin, gömme ve altın set için içeride işlenmesi, harici bir dil modeli API'sine gönderilmesi ve metinsiz dizinin mağaza derlemesinde yer alması Açık soru (hukuki görüş değildir; [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md), §2.4).
- **Önlem.** Metin hukukçu görüşü gelene kadar `kapali`: hiçbir derlemeye girmez ve işlenmez. Görüş olumluysa yalnız ekip içi `dev` derlemede `ic_kullanim` olur ([K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik), [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)). Kapı testleri; harici API ve gömme adımları yalnız serbest metinlerde çalışır; metinsiz atıf dizini için avukat görüşü; 2031 hazırlığı ([Sonra yapılacaklar](./02-sonra-yapilacaklar.md), S-06).
- **Tetik.** Avukat görüşünün gelmesi; hak sahibinden ihtar; Risale içeriğinin `dev` dışındaki bir derlemede görünmesi (kapı testi kırılır).

### R-03 · Ses lisansı
- **Açıklama.** Popüler kıraat kaynaklarının hiçbiri açık lisans vermiyor; telif okuyucuda ve okuyucu kaldırma isteyebilir ([AlQuran Cloud](https://alquran.cloud/terms-and-conditions)). Ses ayrıca Kurul onayına tabi. quran-align zamanlamaları yalnız hizalandığı EveryAyah dosyaları için geçerli ([quran-align](https://raw.githubusercontent.com/cpfair/quran-align/master/README.md)).
- **Önlem.** Yazılı izin şablonu ve 3–5 okuyucu (S-07); QF akışı şartlarıyla yedek; ses ücretli katmana konmaz; kaldırma talebinde kaynak `kapali` olur ve manifestten çıkar. Sesin gecikmesi hâlinde mağaza v1'in sessiz çıkıp çıkmayacağı Açık soru.
- **Tetik.** İzin reddi; kaldırma talebi; Kurul'un sesi ayrıca incelemesi.

### R-04 · Quran Foundation şartlarının değişmesi
- **Açıklama.** QF şartları (son güncelleme 11 Ekim 2026) 30 gün bildirimle feshedilebiliyor. Önbellek en fazla bir hafta, çevrimdışı kopya yalnız Content Sync ile, hazır veritabanı dağıtımı yok; gömmeler aynı kısıtlara tabi ([QF Developer Terms](https://api-docs.quran.foundation/legal/developer-terms/)). Mushaf A'nın QPC fontları bu şartlarla gömülüyor.
- **Önlem.** QF değiştirilebilir bir adaptörün arkasında durur; `core` QF içeriğine dayanmaz; Mushaf C yedek; KFGQPC'den doğrudan izin seçeneği; şart sayfasının tarihi ayda bir kontrol edilir.
- **Tetik.** QF bildirimi; şart sayfasında yeni tarih.

### R-05 · QAC lisans belirsizliği
- **Açıklama.** İndirme sayfası GPL ve "herhangi bir web sitesinde veya uygulamada" kullanım izni veriyor; SSS "ticari amaçla kullanmamak" şartı koyuyor; dosya değiştirilemez ([QAC indirme](https://corpus.quran.com/download/); [QAC SSS](https://corpus.quran.com/faq.jsp)).
- **Önlem.** Faz 0'da QAC'ye yazılır (S-15). Cevap gelene dek QAC'den türeyen kök ve lemma `core` dışında, `kelime-kok` paketinde `bekliyor` kalır (K-06); mağaza derlemesinde kelime kartının kök, lemma ve anlam satırları kapalıdır ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)). Düzeltmeler ayrı bir katmanda tutulur; atıf ve bağlantı verilir; gelir modeli kararında yeniden değerlendirilir (S-01). Hukuki görüş değildir. Yedek olarak QUL lemma dışa aktarımı yalnız kaynak bazında şart teyidiyle kullanılır ([QUL SSS](https://qul.tarteel.ai/faq)).
- **Tetik.** Olumsuz ya da gelmeyen cevap; gelir modeli kararı.

### R-06 · Hadis veri setlerinin kökeni
- **Açıklama.** fawazahmed0/hadith-api Unlicense ile dağıtılıyor, ama Türkçe metinlerin kaynağı belgelenmemiş ([editions.json](https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions.json)). hadith-json Sunnah.com'dan kazınmış ve lisans dosyası yok ([README](https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/README.md)). Sunnah.com API'si anahtar istiyor ve verinin bir kısmını açıyor ([Sunnah.com](https://sunnah.com/developers)).
- **Önlem.** Türkçe metin yalnız Tecrîd'in Naim kısmından ve kendi transkripsiyonumuzdan gelir. Kökeni belgelenmemiş set `serbest` olmaz. `hadis-kutub-i-sitte` kaynak seçimi netleşene dek `bekliyor` başlar; `hadis-tecrid` serbest ciltlerden yaptığımız aktarımdır (`tecrid-ar`, `tecrid-naim` `serbest`); Tecrîd'in Kâmil Miras ciltleri 1 Ocak 2028'e kadar `kapali` (K-06). Lisansı açık bir Arapça kaynak adayı Açık soru ([Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md)).
- **Tetik.** Bir hadis paketinin `serbest` durumuna alınma isteği.

### R-07 · Elmalılı metin kalitesi (OCR ya da hazır metin)
- **Açıklama.** 6.442 sayfalık özgün baskıda (İstanbul 1935–1938) Türkçe metin büyük olasılıkla Latin harfli, âyetler Arapça harfli; iş 1930'ların dizgisine ve imlasına uygun OCR ve düzeltmedir ([K-03](../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) düzeltmesi; tarama nüshasında Doğrulanacak). Hazır dijital metin adayları bulundu (meal için Vikikaynak "Kur'an", tefsir için archive.org metin katmanı), ama baskı esasları belirsiz ya da kalitesi bilinmiyor; temiz bir hazır özgün baskı metni yok ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)). Sadeleştirilmiş baskılar ve ticari kullanımı kapatan kaynaklar kullanılamaz. Hazır metin pilotta ölçülür; eşik geçilmezse OCR yolu sürer ve 6.442 sayfalık OCR ve düzeltme yükü aynen kalır. Meal `core`'un parçası; onaydan sonraki düzeltme yeniden onay demek.
- **Önlem.** Faz 0'da pilot: OCR motorları ve hazır metin adayları aynı altın örneklemde ölçülür (CER), Latin harf doğrulaması yapılır; yol ölçümle seçilir (A09). Türkçe ve Arapça kısımlar için ayrı OCR ayarı (öneri); iki tur insan düzeltmesi; editör panelinde düzeltme kuyruğu; her düzeltme hattan geçer ve `content_hash` değişimini kaydeder; düzeltme turları Kurul başvurusundan önce kapanır; tefsir metni meal yolundan ayrı yürür ([Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md)).
- **Tetik.** Tarama nüshasında baskının Latin harfli çıkmaması; pilotta hiçbir yolun eşiği geçememesi (eşikler yola göre belirlenir; hazır metin yolu için başlangıç önerisi CER ≤ %1, Elmalılı hazırlığı §4); düzeltme hızının planın gerisinde kalması.

### R-08 · Yanlış pozitif bağlantıların güveni aşındırması
- **Açıklama.** En büyük yanlış pozitif kaynağı kısa ve kalıplaşmış ifadeler. QUL 5.641 tekrarlanan ifade listeliyor; "تَجْرِي مِن تَحْتِهَا الْأَنْهَارُ خَالِدِينَ" 18 âyette geçiyor ([QUL](https://qul.tarteel.ai/morphology_phrases?page=61)). Basılı fihristte Kur'an'da karşılığı bulunmayan bir kayıt da not edilmiş ([RİNAP](https://rinap.uskudar.edu.tr/uploads/site/6/content/files/risale-i-nurun-tefsirdeki-yeri-compressed.pdf)).
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
- **Açıklama.** Araştırma App Store ve Google Play'in dini içerik incelemesine dair bir kaynak bulmadı (Doğrulanacak). Eski plan Apple reddini orta risk sayıyordu (`quran-app-docs/14-riskler/01-risk-matrisi.md`).
- **Önlem.** TestFlight ve Google Play kapalı testi erken açılır; mağaza metni resmî kurum çağrışımı taşımaz ve kurum logosu kullanılmaz; Kurul onay bilgisi, lisans belgeleri ve gizlilik beyanları itiraz dosyasında hazır durur; reklam yoktur.
- **Tetik.** Ret ya da ek bilgi talebi.

### R-13 · Hesaplar gelince KVKK
- **Açıklama.** Yurt dışına düzenli aktarımda her veri işleyenle standart sözleşme ve 5 iş günü içinde Kurum'a bildirim gerekiyor; bildirim yapmamanın 2026 cezası 90.308–1.806.377 TL ([Cottgroup](https://cottgroup.com/tr/blog/kvkk-gdpr/item/standart-sozlesme-bildirim-yukumlulugu-ve-yaptirimlari)). Rapordaki bütün aday sağlayıcılar veriyi yurt dışında tutuyor. Notların ve okuma ilerlemesinin özel nitelikli veri sayılıp sayılmadığı Açık soru.
- **Önlem.** Hesap isteğe bağlı ([K-15](../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte)); veri en aza indirilir; veri işleyenler listesi, sözleşme ve bildirim akışı, aydınlatma metni, silme ve dışa aktarma; avukat incelemesi ([KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md)).
- **Tetik.** Faz 4'ün başlaması; yeni bir veri işleyen eklenmesi.

### R-14 · Tek geliştiricinin tükenmesi
- **Açıklama.** Eski plan bu riski en üst sıraya koyuyordu; rapor çok servisli bir mimarinin tek geliştiricinin en büyük riskini büyüttüğünü söylüyor. Hukuk ve lisans süreçleri uzun bekleme içeriyor.
- **Önlem.** İnce mimari ([K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)); faz çıkış ölçütleri; Sonra yapılacaklar park alanı; CI ve Publisher otomasyonu; yapay zekâ destekli geliştirme; süreçlerin yazılı olması; haftalık dinlenme ritmi (eski plandaki yarım gün ve tam gün izin önerisi); bekleme dönemlerinin teknik işle doldurulması.
- **Tetik.** İki faz çıkışının üst üste kayması; uzun süre yüksek çalışma saati; öz değerlendirmede motivasyon düşüşü.

### R-15 · Tanzil metninin istemeden değişmesi (ek)
- **Açıklama.** Tanzil metni değiştirilemez ([Tanzil metni, OpenITI kopyası](https://raw.githubusercontent.com/OpenITI/0025AH/master/data/0001Quran/0001Quran.Mushaf/0001Quran.Mushaf.Tanzil001-ara1.mARkdown)). NFC dönüşümü Arapça hareke sırasını değiştirebilir; bu, onaylı içerik özetini de bozar.
- **Önlem.** Değişmezlik testleri; görüntüleme yalnız kanonik metinden; Tanzil metnine NFC bile uygulanmaz (K-26) ([Test stratejisi](../07-yayin/03-test-stratejisi.md)).
- **Tetik.** Değişmezlik testinin kırılması.

### R-16 · Font lisansları (ek)
- **Açıklama.** KFGQPC Hafs lisansı çelişkili ve alt kümeleme değişiklik sayılabilir ([font dosyası](https://raw.githubusercontent.com/mustafa0x/qpc-fonts/f93bf5f3/various-woff2/UthmanicHafs1%20Ver09.woff2)). QPC sayfa fontları "All rights reserved" diyor; GitHub aynalarından toplu kopyalamak riskli ([QCF_P001](https://raw.githubusercontent.com/mustafa0x/qpc-fonts/f93bf5f3/mushaf-woff2/QCF_P001.woff2)).
- **Önlem.** Hafs için yazılı izin ya da Amiri Quran; QPC fontları yalnız QF şartlarıyla; font dosyaları değiştirilmez.
- **Tetik.** İzin reddi; şart değişikliği.

### R-17 · Tarafsızlık algısı (ek)
- **Açıklama.** Türkiye'deki güçlü rakiplerin hepsi bir kuruma bağlı; rapor tarafsızlığı pazarda boş duran bir konum olarak görüyor. Tek bir yayınevine bağlanan lisans ya da eski plandaki topluluk adı içeren ifadeler bu konumu zedeler.
- **Önlem.** [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler); çok yayınevli lisans yaklaşımı; baskılar arası sayfa eşlemesi; metinlerde topluluk adı kullanılmaz.
- **Tetik.** Tekel şartı taşıyan bir lisans teklifi; kamuoyunda bağlılık iddiası.

### R-18 · SDK geçişi ve kitaplık ön sürümleri (ek)
- **Açıklama.** Expo SDK 58 beta React Native 0.88 RC üzerinde ([SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)); NativeWind v5 "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)); react-native-track-player v5 ticari lisanslı ([RNTP](https://github.com/doublesymmetry/react-native-track-player)).
- **Önlem.** SDK 57 ile başlanır, 58 kararlı olunca geçilir ([K-09](../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji)); NativeWind v4 ([K-29](../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları)); expo-audio ([K-28](../00-ozet/02-karar-defteri.md#k-28--ses)); bağımlılık lisans denetimi.
- **Tetik.** SDK 58 kararlı sürümü; bir bağımlılığın lisans değişikliği.

### R-19 · v1'de cihazdaki kullanıcı verisinin kaybı (ek)
- **Açıklama.** v1 hesapsızdır; telefon kaybı ya da uygulamanın silinmesi notları götürür.
- **Önlem.** İşletim sistemi yedeği açık (öneri); Verilerimi dışa aktar (öneri); v1.x senkron.
- **Tetik.** Veri kaybı şikâyetleri.

### R-20 · SDK 57'de arka planda sesin kesilmesi (ek)
- **Açıklama.** Android'de kilit ekranı kontrolü etkin değilse arka plandaki ses yaklaşık 3 dakika sonra kesiliyor ([expo-audio](https://docs.expo.dev/versions/latest/sdk/audio/)). Kilit ekranında oynatma listesi desteği SDK 58 ile geliyor ([SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)); SDK 57'de oynatma listesi kilit ekranı kontrolüyle çalışmaz.
- **Önlem.** v1'de tek âyetlik oynatıcı: tek `AudioPlayer` her âyette kaynağını değiştirir ve kilit ekranı aynı oynatıcıda açık kalır. Kesintisiz oynatma listeleri SDK 58'den sonra gelir ([Ses sistemi](../06-mobil/02-ses-sistemi.md)).
- **Tetik.** İç testte arka planda sesin kesilmesi; SDK 58'in kararlı sürümü.

### R-21 · Hazır metinden sadeleştirme ya da belirsiz baskı sızması (ek)
- **Açıklama.** Kontrollü hazır metin yolunda ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)) hazır metnin sadeleştirilmiş ya da baskı esası belirsiz bir metne dayanması ve bunun fark edilmeden temel metin olması mümkün. Sadeleştirme FSEK m. 6 anlamında işlenme eseri olabilir; veri tabanı hakkı (ek m. 8) ve CC BY-SA şartı da açık sorudur (hukuki görüş değildir; [avukat soruları](../yazismalar/avukat-sorulari.md)). Metin Kurul kapsamında olduğu için sızan bir hata ya da hak sorunu onay sürecini de etkiler (R-01).
- **Önlem.** Pilotta CER ve sadeleştirme izi ölçümü (eşik geçilmezse hazır metin girmez); 6.236 âyet kapsam ve sadeleştirme taraması, 60 rastgele âyet elle; hazır metin `bekliyor` kaydı ve `taslak` girişi, ikinci onay; revizyon numarası ve SHA-256 ile kilit dosyası (planlı; henüz yok); özgün baskı görseliyle iki tur karşılaştırma; hazır metin `serbest` olmadan `public` ve `internal` derlemeye girmez (K-06).
- **Tetik.** Pilotta sadeleştirme izi bulunması; kilitli revizyonla indirilen dosyanın özetinin uyuşmaması; avukattan olumsuz cevap; ikinci okumada sistematik fark.

## 3. Gözden geçirme

- Kritik riskler (R-01, R-07, R-14) haftada bir; bütün kayıt ayda bir ve her faz geçişinde gözden geçirilir.
- Tetik gerçekleşince risk hemen ele alınır ve önlem kaydı tarihle yazılır.
- Kapanan risk silinmez; "Kapandı" olarak işaretlenir. Yeni risk sıradaki numarayı alır.

## İlgili dosyalar

- [Fazlar](./01-fazlar.md) · [Sonra yapılacaklar](./02-sonra-yapilacaklar.md)
- [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) · [KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md) · [Test stratejisi](../07-yayin/03-test-stratejisi.md)
- [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) · [Arama](../03-veri/05-arama-fts5.md)
- [Kaynakça](../09-kaynakca.md) · [Karar defteri](../00-ozet/02-karar-defteri.md)
