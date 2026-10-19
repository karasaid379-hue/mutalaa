# Risale-i Nur Hazırlığı
> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-02](../00-ozet/02-karar-defteri.md#k-02--i̇lk-içerik-seti) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)

K-05 gereği Risale-i Nur'un altyapısı şimdi hazırlanır, metin sonra yayımlanır. Bu dosya bugün neyin, hangi hukuki sınırla kurulacağını ve 1 Ocak 2031'e hazırlığın nasıl izleneceğini anlatır. Risale metni mağaza paketine girmez.

## 1. Hukuki durum

> **Hukuki görüş değildir.** Aşağıdakiler araştırma raporunun ve bağlantısı verilen kaynakların özetidir. Her uygulama adımı öncesinde bir fikri haklar avukatına danışılır.

- **Koruma süresi.** Said Nursî 1960'ta vefat etti. Ekonomik haklar 31 Aralık 2030'a kadar sürer; Külliyat 1 Ocak 2031'de serbest kalır ([TDV İslâm Ansiklopedisi](https://islamansiklopedisi.org.tr/risale-i-nur-kulliyati); [FSEK m. 26–27](https://www.wipo.int/wipolex/en/text/499171)).
- **Hak sahibi belirsiz.** Kültür ve Turizm Bakanlığı 2014'te bandrol başvurularını reddetti; gerekçe, yasal mirasçıların hakları birlikte kullanması gerektiği ve "sözleşme/muvafakatname" sunulamamasıydı ([AA/Sondakika](https://www.sondakika.com/guncel/haber-risale-i-nur-kulliyati-nin-basimi-6272228/)). Topluluk, Nursî'nin yayını "mutlak vekilim" dediği talebelerine emanet ettiğini savundu ([Timeturk](https://www.timeturk.com/tr/2014/07/08/risale-i-nurlar-yasaklaniyor-mu.html)). Kasım 2014'te bir Bakanlar Kurulu kararı, 6552 sayılı Kanunla değişen FSEK m. 47'ye dayanarak kullanım haklarını Diyanet'e verdi ([Hürriyet](https://www.hurriyet.com.tr/yazarlar/yalcin-bayer/nereden-nereye-27679980); [AYM K.2015/45](https://normkararlarbilgibankasi.anayasa.gov.tr/Dosyalar/Kararlar/KararPDF/2015-45-nrm.pdf)). Anayasa Mahkemesi bu hükmü 11 Haziran 2015'te iptal etti ([T24](https://t24.com.tr/haber/aym-risale-i-nur-yasagini-iptal-etti,299364); [Lexpera, 2023](https://www.lexpera.com.tr/literatur/armagan-makaleler/fikri-haklarin-anayasal-himayesi-uzerine-notlar-2-soyut-norm-denetimi-iptal-davasi-934-937/1)). 2016–2026 arasında hakları kimin kullandığını gösteren bir kaynak bulunamadı.
- **Asıl nüsha.** Diyanet'in tahkik heyeti müellifin tashih ettiği 1956–1960 baskılarını esas aldı; metin 2015 başından beri yayınevlerince basılıyor ve risaleinur.hizmetvakfi.org'da yayımlanıyor ([README](https://raw.githubusercontent.com/alitekdemir/Risale-i-Nur-Diyanet/master/README.md)).
- **alitekdemir/Risale-i-Nur-Diyanet deposu.** README metnin "www.risaleinur.hizmetvakfi.org adresinden indirilmiştir" diyor ve "Creative Commons Atıf-Türetilemez 4.0" iddiasını yalnız README'de taşıyor ([GitHub](https://github.com/alitekdemir/Risale-i-Nur-Diyanet)). Hak sahibi olmayan bir yükleyici sahip olmadığı hakkı lisanslayamaz; bu iddia geçersizdir ve depo kullanılmaz. Eski planın "lisans açık, hukuken güvenli" değerlendirmesi bu yüzden geçersizdir (`quran-app-docs/11-icerik-edinim/02-telif-analizi.md`).
- **Manevi haklar.** FSEK m. 16 eserde "kısaltmalar, ekleme ve başka değiştirmeler" yapılmasını izne bağlar. m. 19 mirasçılara bu hakları 70 yıl kullanma imkânı verir ve kültür açısından önemli eserlerde Bakanlığa tanınan yetkinin süresini belirtmez. Pratik kural değişmez: metin 2031'den sonra da kelimesi kelimesine, kısaltılmadan ve sadeleştirilmeden yayımlanır (K-25).

> **İç kullanım uyarısı.** Telif süresi dolmamış bir metin kaynağının iç kullanımı da (indirme, depoya ya da veritabanına koyma, OCR, indeksleme, yapay zekâ servisine gönderme, geliştirme derlemesine koyma) önce bir avukatla netleştirilir. Avukat görüşü gelene kadar Risale metni içerik hattına girmez ve Risale kaynakları `embed_ok = false` taşır: metin gömülmez ve harici yapay zekâ API'lerine gönderilmez. Geliştirme yer tutucu metinle yapılır (bölüm 3.6). K-05'e göre Risale metni yalnız ekip içi `dev` derlemelerinde görünür; davetli test kullanıcılarına giden `internal` derlemelere ve mağaza paketine girmez. Ekip içi işlemenin (dizin üretimi dahil) hukuki uygunluğu da hukukçuya danışılır; bu dosya ekip içi kullanımın bu görüşten sonra başlamasını öngörür. Bu not hukuki görüş değildir.

## 2. Üç yol ve tarafsızlık

| Yol | Ne yapılır | Risk ve koşul |
|---|---|---|
| 1. Lisans | Mirasçılardan ya da vasiyetnamede adı geçen talebe ve vakıflardan belgelenmiş muvafakati olan bir yayınevinden veya yayınevleri konsorsiyumundan yazılı izin | Tek bir topluluğun yayınevine bağlanmak tarafsızlığı zedeler |
| 2. Metin yerine dizin (hukuki inceleme bekliyor) | Hangi âyetin hangi risalede, hangi bölümde ve hangi baskının kaçıncı sayfasında geçtiği yayımlanır; metin yayımlanmaz | Olgusal bilgi olduğu için risk düşük görünüyor (çıkarım). Dizini kurmak için metni işlemenin hukuki durumu avukatla doğrulanır |
| 3. 1 Ocak 2031'i beklemek | Altyapı hazır bekler; metin 2031'de müellif tashihli 1956–1960 baskılarından açılır; asıl nüsha karşılaştırma metni olur | Takvim riski yok; hazırlık eksik kalırsa açılış gecikir |

Rapor 2. ve 3. yolu birleştirmeyi, 1. yolu paralel müzakere etmeyi öneriyor. Görüşmeler [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) listesindedir.

**Tarafsızlık kuralları (K-25).**
- Münhasır anlaşma yapılmaz; bir yayınevine verilen hak diğerlerine de aynı şartlarla açık kalır.
- Uygulamada yayınevi markası öne çıkarılmaz; baskılar eşit gösterilir ve okur baskıyı kendisi seçer.
- Birden fazla baskı için sayfa eşlemesi tutulur.
- Topluluklara özgü adlandırmalar kullanılmaz. Rapor eski plandaki "Hizmet hareketi" ifadesinin ve sesli Risale lisansı için cemaat kuruluşlarının aday gösterilmesinin çıkarılmasını istiyor.

## 3. Şimdi kurulanlar

| İş | Risale metni gerekir mi? | Durum |
|---|---|---|
| Kitap ve bölüm adresleri | Hayır (içindekiler bilgisi) | Şimdi |
| Baskı kayıtları, bölüm başı sayfa eşlemesi | Hayır (basılı kitaptan sayfa numarası) | Şimdi |
| Paragraf çapaları | Evet | Temel metinden; 2031 ya da avukat onayı |
| Âyet atıf dizini | Otomatik yöntem evet, elle dizin hayır | Yol 2 hukuki görüşüne bağlı |
| Lügat | Hayır (serbest sözlükler ve kendi tanımlarımız) | Şimdi |
| Âyet ve hadis atıf ayrıştırıcıları | Hayır (Elmalılı ve yapay örnekler) | Şimdi |
| Okuyucu arayüzü ve paket hattı | Hayır (yer tutucu metin) | Şimdi |
| Risale'ye özgü konu listesi (`konu:{slug}`; ör. haşir delilleri, ene ve zerre) ve paragraflara bağlanması | Liste için hayır, bağlama için evet | Liste şimdi, bağlama sonra ([Anlamsal katman](../05-capraz-referans/04-anlamsal-katman.md)) |

### 3.1 Kitap ve bölüm adresleri

Çapa grameri `rn:{kitap}(:{bolum})*:p{n}(:s{cumle})?` biçimindedir; örnek `rn:sozler:soz-10:hakikat-3:p4` ([Çapa şeması](../03-veri/01-capa-semasi.md)). Kitap listesi alitekdemir deposunun 15 klasörlük yapısından ve eski plandan çıkarıldı; kesin liste temel baskının içindekileriyle doğrulanır.

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| Sözler | `sozler` | Asâ-yı Mûsâ | `asa-yi-musa` |
| Mektûbât | `mektubat` | Barla Lâhikası | `barla-lahikasi` |
| Lem'alar | `lemalar` | Kastamonu Lâhikası | `kastamonu-lahikasi` |
| Şuâlar | `sualar` | Emirdağ Lâhikası I | `emirdag-lahikasi-1` |
| Mesnevî-i Nûriye | `mesnevi-i-nuriye` | Emirdağ Lâhikası II | `emirdag-lahikasi-2` |
| İşârâtü'l-İ'câz | `isaratul-icaz` | Tarihçe-i Hayat | `tarihce-i-hayat` |
| Muhâkemât | `muhakemat` | Küçük kitaplar | Risale başına ayrı slug (Açık soru) |
| Sikke-i Tasdîk-i Gaybî | `sikke-i-tasdik-i-gaybi` | | |

- **Slug kuralı.** Küçük harf ASCII; ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u, â→a, î→i, û→u; kesme işareti düşer; boşluk tireye döner.
- **Bölüm kalıpları.** `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`; iç bölümler `makam-{n}`, `hakikat-{n}`, `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `mukaddime`, `zeyl`, `hatime`; haşiyeler için `hasiye-{n}` ([Çapa şeması](../03-veri/01-capa-semasi.md)).
- **Lâhikalar.** Mektupların başlığı ya da numarası olmayabilir. Öneri: temel baskıdaki sıraya göre `parca-{n}` (Açık soru).
- **Yazılmamış bölümler.** Eski plan bazı bölümleri "yazılmamış" diye listeliyor (ör. 14. ve 25. Mektup, 5. Lem'a; `quran-app-docs/04-okuma/03-risale-i-nur-okuyucu.md`). Bu bölümler için çapa üretilmez; liste Doğrulanacak.

### 3.2 Paragraf çapaları ve temel baskı

Çapalar yeniden numaralanmaz (K-26). Paragraf numarası bu yüzden yalnız temel metinden, yani müellif tashihli 1956–1960 baskılarından üretilir. Temel metin sayısallaştırılmadan paragraf çapası üretilmez. Geliştirmede yer tutucu metinle `rn:` çapaları denenebilir; bunlar kalıcı bir dosyaya ya da kullanıcı verisine yazılmaz. Yol 2 dizini yayımlanırsa bölüme ve baskı sayfasına bağlanır; böylece temel metin geldiğinde yeniden numaralama gerekmez. Cümle (`:s{n}`) ve karakter aralığı (`@{başlangıç}-{bitiş}`; yarı açık, başlangıç dahil, bitiş hariç) adresleri de temel metinden üretilir.

### 3.3 Baskılar ve sayfa eşlemesi

Ders halkalarında farklı baskıların sayfa numaraları kullanılır; araştırma hiçbir üründe baskılar arası eşleme bulamadı (rapor). Eşleme `page_map(baskı, çapa, sayfa)` tablosunda tutulur ([Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md)).

```sql
-- Baskı kaydı önerisi; kesin şema Editoryal veritabanı dosyasında
CREATE TABLE baski (
  id           text PRIMARY KEY,   -- 'rn-takim-buyuk-boy-14'
  yayinevi     text,
  yil          int,
  cilt_takimi  text,
  isbn         text,
  boy          text,               -- 'büyük boy', 'orta boy'
  yazi         text,               -- 'latin', 'osmanlica'
  metin_esasi  text                -- '1956-1960', 'asil-nusha', 'diger'
);
```

- **Şimdi.** Bölüm başlarının sayfa numaraları basılı kitapların içindekiler sayfalarından ve kitabın kendisinden elle girilir. Ölçek fikri için kitapyurdu listesindeki 14 ciltlik büyük boy takım 7.550 sayfadır ([kitapyurdu](https://www.kitapyurdu.com/kitap/risalei-nur-kulliyati-buyuk-boy-14-cilt-takim/429602.html)); dört ana mecmua 130 parçadan oluşur ([TDV İA](https://cdn2.islamansiklopedisi.org.tr/dosya/35/C35011446.pdf)).
- **2031'den sonra.** Her baskının metni temel metinle hizalanarak paragraf düzeyinde sayfa eşlemesi üretilir. Baskıların kendi dipnot, fihrist ve editoryal ekleri kopyalanmaz.

### 3.4 Âyet atıf dizini

Dizin `xref` tablosunda `rn:` çapalarından `q:` çapalarına giden bağlantılardır: açık kaynak gösterimi `atif`, Arapça alıntı `iktibas`, metni verilmeyen anıştırma `ima` (yalnız küratörlü). Ardışık âyetler birlikte alıntılanmışsa hedef âyet aralığı çapasıdır: `q:{s}:{ilk}-{son}` (K-26). Yöntem [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) dosyasındadır; özet:
- "(Bakara Sûresi, 255)" ya da "Âl-i İmrân: 7" gibi açık atıflar küçük bir gramer ve sure adı varyant tablosuyla ayrıştırılır.
- Arapça diziler normalize edilir ve Kur'an'ın Uthmani ve imlâî biçimleriyle kurulmuş 3–4 kelimelik n-gram indeksinde aranır; adaylar Smith-Waterman hizalamasıyla genişletilir.
- Kısa ve kalıplaşmış ifadeler düşük ön güvenle başlar. QUL 5.641 tekrarlanan ifade listeliyor; "تَجْرِي مِن تَحْتِهَا الْأَنْهَارُ خَالِدِينَ" 18 âyette geçiyor ([QUL](https://qul.tarteel.ai/morphology_phrases?page=61)).
- MIT lisanslı ijaza önce Risale örnekleri üzerinde ölçülür ([PyPI](https://pypi.org/project/ijaza/)).
- Sözler, Mektubat, Lem'alar, Şuâlar, Mesnevî-i Nuriye ve İşârâtü'l-İ'câz'dan tabakalı seçilen 300–500 paragraflık altın set elle etiketlenir; kesinlik ve duyarlılık uzun ve kısa iktibaslar için ayrı raporlanır.
- Basılı fihristler yalnız başlangıç noktasıdır. Bir çalışma âyetlerin çoğu zaman başlık olarak kullanıldığını, pek çok âyetin metni verilmeden açıklandığını ve bir fihrist kaydı için "Kur'an'da bu metinle herhangi bir âyet bulunamamıştır" notu düşüldüğünü gösteriyor ([RİNAP](https://rinap.uskudar.edu.tr/uploads/site/6/content/files/risale-i-nurun-tefsirdeki-yeri-compressed.pdf)).
- İşârâtü'l-İ'câz Fâtiha'dan Bakara 33'e kadar tefsir eder; eski planın "Fâtiha + Bakara 1–31" kapsamı buna göre düzeltilir.

Otomatik yöntemler Risale metnini işlediği için avukat görüşü gelmeden çalıştırılmaz. Basılı kitaptan elle dizin çıkarmak ayrı bir hukuki sorudur ve aynı görüşte sorulur.

### 3.5 Lügat

- **Kaynaklar.** Redhouse'un 1890 tarihli *A Turkish and English Lexicon*'u serbesttir ve HathiTrust'ta tam görünümdedir ([HathiTrust](https://catalog.hathitrust.org/Record/001771732)). Kâmûs-ı Türkî ve Lugat-ı Nâci Doğrulanacak. Türkçe tanımları biz yazarız.
- **Kopyalanmayanlar.** eRisale'nin ve yayınevlerinin Risale'ye özgü modern lügatleri korunan derlemelerdir. Kelime-Frekans deposunun `anlam` sütunu bu tür lügatlerden derlendiği için kullanılmaz. Tanımı yazan editör bu lügatlere bakmaz.
- **Başlık söz listesi.** Kelime-Frekans deposunun CC0 lisanslı kelime ve sıklık sütunları olgu niteliğindedir ve kullanılabilir. Ölçek: README'ye göre Sözler'de 56.384 lügatli kelime geçişi ve 12.692 farklı kelime var ([Kelime-Frekans](https://github.com/alitekdemir/Risale-i-Nur-Kelime-Frekans)).
- **Madde yapısı (öneri).** `lugat_madde(id, basliksoz, basliksoz_norm, osmanlica_yazim, koken_dil, tanim_tr, ar_kok_id, kaynaklar, duzey, status, surum, content_hash)`. `ar_kok_id` QAC kök envanterine bağlanır ve Kur'an'a köprü olur ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)). `duzey` okurun "Lügat: Kapalı / Az / Orta / Çok" yoğunluk ayarını besler.
- **İş akışı.** Yapay zekâ serbest sözlüklerden taslak çıkarabilir; isteme yalnız `embed_ok = true` kaynaklardan metin girer, korumalı metin girmez. Her madde insan onayından geçer ([Kelime anlamları](./06-kelime-anlamlari.md)).

### 3.6 Geliştirme için yer tutucu metin

Sentetik `test-risale-ornek` kaynağı, Külliyat'ın yapısını taklit eden yapay Türkçe metin taşır: kitap, bölüm ve paragraf ağacı, satır içi Arapça diziler, dipnot işaretleri, uzun paragraflar. Metin bir betikle üretilir ve "örnek metin" diye işaretlenir. Kitap slug'ı `test-ornek`, kitap paketi `risale-test-ornek`'tir; paket kimliği çapadan türetilir ([İçerik paketleri](../03-veri/03-icerik-paketleri.md#4-bağlantıların-paketlere-dağılımı) §4). Kaynak `ic_kullanim` durumundadır ve yalnız `dev` derlemesinde görünür; Yayınlayıcı `test-` önekli kaynağı `public` derlemeye hiçbir durumda almaz ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md#8-örnek-veri) §8, P-12). Okuyucu arayüzü, arama, lügat katmanı ve paket hattı bu kaynaktan üretilen paketlerle uçtan uca test edilir. Bu yol Risale metnine dokunmadan işin büyük kısmını bitirir.

## 4. Yayın kuralları

- `risale-*` kaynakları avukat görüşüne kadar `kapali` kalır. Olumlu görüş gelirse en fazla `ic_kullanim` olur.
- K-06'ya göre `ic_kullanim` içerik yalnız ekip içi `dev` derlemelerinde görünür; `internal` ve `public` derlemelere girmez ([Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md)).
- 1. yolla lisans alınmadıkça mağaza paketlerine 2031'den önce Risale metni girmez.
- 2. yol dizini yalnız avukat görüşünden sonra yayımlanır ve şunları içerir: kitap ve bölüm adresi, âyet çapası, bağlantı türü, baskı ve sayfa. Metin alıntısı içermez.

## 5. 2031 hazırlık listesi

- [ ] **2027:** Avukat görüşü alındı (iç kullanım; dizin yöntemi; yer tutucu dışındaki her geliştirme kullanımı).
- [ ] **Temel metin:** Her kitap için müellif tashihli 1956–1960 baskısı belirlendi (künye ve yer numarası Doğrulanacak); fiziksel nüsha ya da tarama kaynağı ayarlandı. Tarama 2031'den önce yapılacaksa avukat onayı var.
- [ ] **Karşılaştırma:** Asıl nüsha yalnız karşılaştırma metni. Farklar sürüm farkı olarak raporlanır; temel metin "düzeltilmez".
- [ ] **Yazar dökümü:** Lâhikalar ve Tarihçe-i Hayat gibi derlemelerde başka kişilerin kaleminden çıkan kısımlar olabilir (Doğrulanacak). İşârâtü'l-İ'câz ve Mesnevî-i Nûriye'nin Türkçe tercümelerinin mütercimi belirlenir (genel bilgiye göre müellifin kardeşi Abdülmecid Nursî; Doğrulanacak). Bu kısımlar kendi yazar ya da mütercimlerinin ölüm yılına göre serbest kalır; tarihleri ayrı hesaplanır.
- [ ] **Sayısallaştırma:** Temel baskıların yazı türüne göre OCR yolu seçildi; CER örneklemi yapıldı; dört göz incelemesi planlandı. Kelimesi kelimesine kuralı: kısaltma, sadeleştirme ve "düzeltme" yok. Aktarılan metin bizim ürettiğimiz metindir ve ilk kayıtta NFC'ye çevrilir (K-26).
- [ ] **Adresler:** Kitap ve bölüm slug'ları temel baskının içindekileriyle doğrulandı; paragraf çapaları üretildi ve donduruldu.
- [ ] **Sayfa eşlemesi:** En az üç baskının bölüm başları hazır; paragraf düzeyi temel metinle hizalanarak üretilecek.
- [ ] **Atıf dizini:** Altın sette kesinlik ve duyarlılık raporlandı; onaylı bağlantılar hazır.
- [ ] **Lügat:** Sık başlık sözlerin tanımları onaylı.
- [ ] **Paketler:** `risale-{kitap}` paketleri yer tutucu metinle uçtan uca test edildi.
- [ ] **Ekim–Aralık 2030:** Son hukuki kontrol (süre, manevi haklar, atıf metni) yapıldı; mağaza sürüm notları hazır.
- [ ] **1 Ocak 2031:** `risale-1956-1960` kaynağı `serbest` oldu; paketler yayımlandı.

Atıf metni (2031, öneri): "Bediüzzaman Said Nursî, Risale-i Nur Külliyatı. Metin {baskı künyesi} esas alınarak kelimesi kelimesine aktarılmıştır."

## 6. Açık sorular

1. Avukat görüşü: iç kullanım, otomatik ve elle dizin yöntemleri.
2. 1. yol için hangi hak sahipleriyle, hangi tarafsızlık şartlarıyla görüşülecek?
3. Küçük kitapların slug'ları ve Lâhika parçalarının numaralandırması.
4. Her kitap için temel baskının künyesi.
5. Başka yazar ve mütercimlerin kısımları ve serbest kalma tarihleri.
6. Risale içinde geçen âyetler için Kurul onayı gerekmez (çıkarım); teyit edilecek.

## İlgili dosyalar
- [Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md) · [İçerik hattı](./02-icerik-hatti.md) · [Hadis hazırlığı](./04-hadis-hazirligi.md) · [Kelime anlamları](./06-kelime-anlamlari.md)
- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md)
- [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) · [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)
- [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) · [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) · [Riskler](../08-yol-haritasi/03-riskler.md)
