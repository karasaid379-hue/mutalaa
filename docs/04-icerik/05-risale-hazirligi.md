# Risale-i Nur Hazırlığı
> **Sürüm:** 1.5 · **Tarih:** 12 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) · [K-02](../00-ozet/02-karar-defteri.md#k-02--i̇lk-içerik-seti) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)

K-02 gereği Risale-i Nur'un metni, adresleri, âyet atıf dizini, lügatı ve baskı sayfa eşlemesi içerik hattıyla gelir (A20). Bu dosya kaynağın nasıl seçildiğini, hangi parçaların nasıl hazırlanacağını ve yayın kurallarını anlatır. Metin kelimesi kelimesine, kısaltmasız ve sadeleştirmesiz yayımlanır (K-25); birimler editör onayından geçtikçe mağaza paketine girer (K-42 madde 5).

## 1. Kaynak ve kapsam

Kaynak; göreve uygunluk, eksiksizlik, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirlik ölçütleriyle seçilir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1). Başvuru, onay ya da API anahtarı isteyen kaynak seçilmez. Dosyaları Claude Code indirir: her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni bir klasöre iner ve klasörde `SHA256SUMS` bulunur. Adresler, commit'ler ve sayımlar A20 `## Tedarik` bölümündedir.

- **Kitap kapsamı ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 1).** Projede RNK Neşriyat'ın Türkçe (`tr`, `tr_k`), Osmanlıca (`osm`) ve Arapça (`ar`, `ar_k`) raflarındaki bütün Risale-i Nur kitapları yer alır: yaklaşık 87 kitap. Bunlar Diyanet'in 25 kitabı (14 büyük, 11 küçük), RNK'nın Diyanet'te olmayan 36 Türkçe kitabı (İman ve Küfür Muvazeneleri, Asâr-ı Bedîiyye, İlk Eserler ve 33 küçük kitap), 12 Osmanlıca ve 14 Arapça kitaptır. Kur'an metni (`evr` rafı) yalnız Tanzil'den gelir (K-26); öteki dillere çeviri rafları (`fi`, `fr`, `uz`, `uzk`, `pt`, `id`, `ny`, `ja`, `zh`, `sw`, `el`) alınmaz. Aynı ada sahip RNK ve Diyanet kitabı tek kitaptır (ör. `gencreh` = `genclik-rehberi`); Diyanet'te birden çok kitabı aynı sırayla bir cilde toplayan RNK kitabı yeni kitap sayılmaz (`sunuhat` = `sunuhat` + `tuluat` + `isarat`).
- **Metin (K-51 madde 2).** Metin önce Diyanet'in "asıl nüsha" metninin GitHub kopyasından gelir: `alitekdemir/Risale-i-Nur-Diyanet` (kayıt `risale-asil-nusha`; 15 kitap klasörü; `txt`, `obsidian-markdown` ve `html` biçimleri; markdown'da başlık, dipnot ve Arapça işareti). Diyanet'in tahkik heyeti müellifin tashih ettiği 1956–1960 baskılarını esas almıştır ([README](https://raw.githubusercontent.com/alitekdemir/Risale-i-Nur-Diyanet/master/README.md)); `risale-1956-1960` kaydı bu baskıların künyesidir ve metin taşımaz. Diyanet'te bulunmayan metin RNK Neşriyat'ın uygulama içeriğinden gelir (kayıt `risale-rnk-metin`, `tur = "risale"`): Asâr-ı Bedîiyye'nin yarıdan fazlası (Diyanet'te bulunma oranı %44,4) ve Latif Nükteler'in %85'i (%15,3), derlemelerin Diyanet'te olmayan parçaları, Osmanlıca ve Arapça kitapların tamamı. RNK'nın işaretlemesi yapıya çevrilir; anlamı veriden çıkmayan işaret yorumlanmaz, dur ve karar açılır (A20.1b). Büyük Diyanet kitaplarında RNK'da fazladan görünen %0,4–2,1'lik kısım (fihrist, sürüm farkı) metne eklenmez, rapora yazılır.
- **Derleme kitaplar (K-51 madde 3).** Büyük kitaplardan bölüm derleyen her RNK kitabı (Haşir Risalesi gibi küçük kitaplar, İman ve Küfür Muvazeneleri, İlk Eserler …) kendi slug'ı, kendi `rn:` çapaları ve kendi metniyle girer. Kitabın yapısı ve paragraf sırası RNK'dan gelir; Diyanet'te bulunan paragrafın baytları Diyanet'ten kopyalanır (kısmi paragraf kod noktası aralığıyla), kaynak çapa `provenance`'ta tutulur; bulunmayan paragraf RNK'dan gelir. Aynı paragrafın birden çok çapası olur ve aramada tekrar görünür; sonuç gruplaması arama ve okuyucu aşamasına bırakılır ([BÇ-62](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Diyanet'in 11 küçük kitabı zaten kendi metniyle girer.
- **Osmanlıca ve Arapça kitaplar (K-51 madde 4).** Osmanlıca kitabın slug'ı `{slug}-osmanlica`, Arapça kitabınki `{slug}-arapca` olur (Çapa şeması §5). Kitap düzeyinde `dil` (`tr`, `ota`, `ar`) ve `yon` (`rtl`) bilgisi `risale-kitaplar.json` dosyasında ve paket bilgisinde taşınır. Bu kitaplarda yalnız `ar_norm` dolar ve `ar_norm` 1.0 kalır; Farsça harf katlaması (گ, پ, چ, ژ) ayrı bir karar işidir ([BÇ-64](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Sağdan sola okuyucu ve arama katmanı A31'in işidir ([BÇ-63](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Arapça kitapların mütercimi ve Osmanlıca baskıların künyesi RNK verisinde yoktur; hafızadan yazılmaz, editör doldurur (İ-24).
- **Taslak girer.** Hazır dijital metin `taslak` girer ve editör onayından geçer ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 4–5). Onay yolu (K-51 madde 11): kitap bazında toplu onay; tur 1 kaynakla bayt eşitliği (G-BUT), tur 2 örneklem okuması, İ-24 slug doğrulamasından sonra. Uç `POST /api/v1/risale/books/{kitap}/approve` ve editör panelindeki "kitabı onayla" düğmesi A20.8'dedir. Risale metni onayda yeniden hesaplanmaz: metni değiştiren onay 422 verir (K-51 madde 8; `marks` ve `sentences` kararlı kalır).
- **Karşılaştırma ve yedek.** Metin kaynağı dışındaki dijital kopyalar (Hizmet Vakfı sitesinin Diyanet ve Külliyat sayfaları, eRisale, risale.online) yalnız karşılaştırma, doğrulama ve yedek içindir: içindekiler, kelime dizisi eşliği, sayfa eşlemesi. Farklar sürüm farkı olarak raporlanır; temel metin "düzeltilmez".
- **Sadakat (K-25, K-26).** Metin kelimesi kelimesine, kısaltılmadan ve sadeleştirilmeden saklanır ve yayımlanır; yapay zekâ özeti yazılmaz (K-30). Hazır dijital metin kaynağın dağıttığı hâliyle saklanır (NFC uygulanmaz); kendi OCR aktarımımız ilk kayıtta NFC'ye çevrilir. Arama için normalize metin ayrı sütundadır.
- **Fikstür.** Birim ve arayüz testleri için sentetik bir kaynak vardır (bölüm 3.6); gerçek metin testleri kaynak dosyasından alınmış kısa parçalarla yazılır.

## 2. Tarafsızlık

**Tarafsızlık kuralları (K-25).**
- Hiçbir cemaate ve yayınevine bağlı olunmaz. Uygulamada yayınevi markası öne çıkarılmaz; baskılar eşit gösterilir ve okur baskıyı kendisi seçer.
- Birden fazla baskı için sayfa eşlemesi tutulur (bölüm 3.3).
- Topluluklara özgü adlandırmalar kullanılmaz.

## 3. Hazırlanacak parçalar

| İş | Girdi | Aşama |
|---|---|---|
| RNK metni ve derlemeler (Diyanet'te olmayan metin, Osmanlıca, Arapça) | RNK Neşriyat uygulama içeriği (`risale-rnk-metin`) | A20.1b |
| Kitap ve bölüm adresleri | Metnin başlıkları ve RNK içindekileri; eRisale ile karşılaştırma | A20.2a, A20.2b |
| Baskı kaydı, bölüm başı ve paragraf düzeyi sayfa eşlemesi | RNK Neşriyat'ın en son güncel baskısı (`risale-baski-rnk`) | A20.3 |
| Paragraf çapaları | Seçilen metin | A20.2b |
| Kitap bazında toplu onay | Kitap onayı ucu ve editör düğmesi | A20.8 |
| Âyet atıf dizini | Açık atıflar ve Arapça alıntılar; hazır araçlar önce ölçülür | A20.7 |
| Lügat | Kelime-Frekans verisi, kaynak sözlükler, editör tanımları | A20.6 |
| Âyet ve hadis atıf ayrıştırıcıları | Elmalılı, Risale metni ve sentetik örnekler | A18.4, A19.5, A20.7 |
| Okuyucu arayüzü ve paket hattı | Gerçek metin; arayüz ve paket testleri için sentetik fikstür | A20.4, A20.5, A31 |
| Risale'ye özgü konu listesi (`konu:{slug}`; ör. haşir delilleri, ene ve zerre) ve paragraflara bağlanması | Anlamsal katman | v1.x ([Anlamsal katman](../05-capraz-referans/04-anlamsal-katman.md)) |

### 3.1 Kitap ve bölüm adresleri

Çapa grameri `rn:{kitap}(:{bolum})*:p{n}(:s{cumle})?` biçimindedir; örnek `rn:sozler:soz-10:hakikat-3:p4` ([Çapa şeması](../03-veri/01-capa-semasi.md)). Kitap listesi yaklaşık 87 kitaptır (bölüm 1) ve `shared/data/risale-kitaplar.json` dosyasında tutulur; aşağıdaki tablo Diyanet deposunun 14 büyük kitabını gösterir. Kesin liste metnin başlıkları, RNK ve eRisale içindekileriyle doğrulanır (A20.2a, A20.2b). eRisale içindekilerinde kitap bölünmesi farklıdır (Emirdağ Lâhikası tek kitap; İman ve Küfür Muvazeneleri ve İlk Dönem Eserleri ayrı kitaplar); RNK'da da bölünme Diyanet'ten farklıdır (Sözler'in başında başka kitaptan bölüm, `sunuhat` birleşik kitap). Eşleştirme farkları rapora yazılır.

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| Sözler | `sozler` | Asâ-yı Mûsâ | `asa-yi-musa` |
| Mektûbât | `mektubat` | Barla Lâhikası | `barla-lahikasi` |
| Lem'alar | `lemalar` | Kastamonu Lâhikası | `kastamonu-lahikasi` |
| Şuâlar | `sualar` | Emirdağ Lâhikası I | `emirdag-lahikasi-1` |
| Mesnevî-i Nûriye | `mesnevi-i-nuriye` | Emirdağ Lâhikası II | `emirdag-lahikasi-2` |
| İşârâtü'l-İ'câz | `isaratul-icaz` | Tarihçe-i Hayat | `tarihce-i-hayat` |
| Muhâkemât | `muhakemat` | Sikke-i Tasdîk-i Gaybî | `sikke-i-tasdik-i-gaybi` |

- **Küçük kitaplar.** Diyanet deposundaki `Küçük Kitaplar` klasörü 11 eser içerir ve her eser ayrı kitap slug'ı alır. Slug'lar dosya adlarından Çapa şeması §5 kuralıyla türetilir: `divan-i-harb-i-orfi`, `genclik-rehberi`, `hanimlar-rehberi`, `hutbe-i-samiye`, `isarat`, `konferans`, `munazarat`, `nur-cesmesi`, `nurun-ilk-kapisi`, `sunuhat`, `tuluat`.
- **Derleme ve RNK'ya özgü kitaplar.** RNK'nın Diyanet'te olmayan 36 Türkçe kitabı (İman ve Küfür Muvazeneleri, Asâr-ı Bedîiyye, İlk Eserler ve 33 küçük kitap) kendi slug'larını eser adından alır. Derleme kitaplar kendi metin kopyasıyla girer (bölüm 1).
- **Osmanlıca ve Arapça kitaplar.** Slug `{türkçe-slug}-osmanlica` ve `{türkçe-slug}-arapca` olur (ör. `sozler-arapca`, `mesnevi-i-nuriye-arapca`); Türkçe karşılığı olmayan kitapta eser adı ve `-arapca` (ör. `saykalul-islam-arapca`). Paket kimliği `risale-{slug}` olarak türer (ör. `risale-sozler-osmanlica`).
- **Slug listesi ve doğrulama.** Liste küçük bir JSON dosyasında tutulur: `shared/data/risale-kitaplar.json` (slug, `dil`, `yon`, metin kaynağı, Diyanet dosya adları, RNK `raf` ve `uid`). Hepsi `dogrulandi: false` başlar; metnin başlıkları ve içindekilerle eşleşenler betikle `true` olur, eşleşmeyenler editör denetimine (İ-24) kalır.
- **Slug kuralı.** Küçük harf ASCII; ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u, â→a, î→i, û→u; kesme işareti düşer; boşluk tireye döner. `dizin` kitap slug'ı olamaz; slug en çok 64 karakterdir; kardeş çakışmasında `-2` eki eklenir ve rapora yazılır.
- **Bölüm kalıpları.** `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`; iç bölümler `makam-{n}`, `hakikat-{n}`, `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `mukaddime`, `zeyl`, `hatime`; haşiyeler için `hasiye-{n}` (`n` bölümdeki atıf sırasıdır; [Çapa şeması](../03-veri/01-capa-semasi.md)). Bu kurallar ilk `dev` yayınından önce kesinleşir (K-51 madde 12).
- **Lâhikalar.** Mektupların başlığı ya da numarası olmayabilir. Başlık ya da numara yoksa metindeki sıraya göre `parca-{n}`, varsa kaynaktaki numara kullanılır (K-51 madde 12; metinle doğrulanır).
- **Yazılmamış bölümler.** Bazı bölüm numaraları Külliyat'ta yazılmamış sayılır (ör. 14. ve 25. Mektup, 5. Lem'a; liste Doğrulanacak). Bu bölümler için çapa üretilmez; eksik numaralar rapora yazılır, doldurulmaz.

### 3.2 Paragraf çapaları ve temel baskı

Çapalar yeniden numaralanmaz (K-26). Paragraf numarası bu yüzden yalnız temel metinden üretilir: içe alınan metinde her satır bir paragraf ya da başlıktır ve `n` bölüm içinde belge sırasıyla 1'den başlar (A20.2b). Temel metin içe alınıp G-KAY ve G-BUT kapılarından geçmeden paragraf çapası üretilmez; kaynak güncellenirse yalnız [Çapa şeması](../03-veri/01-capa-semasi.md) §9'daki yeniden çapalama kuralı uygulanır. Sentetik fikstürle denenen `rn:` çapaları kalıcı bir dosyaya ya da kullanıcı verisine yazılmaz. Cümle (`:s{n}`) ve karakter aralığı (`@{başlangıç}-{bitiş}`; yarı açık, başlangıç dahil, bitiş hariç) adresleri de temel metinden üretilir.

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

Sayfa eşlemesi RNK Neşriyat'ın en son güncel baskısından yapılır ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 6 ve 7; [BÇ-07](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler) çözüldü).

- **Baskı kaydı.** Baskı ayrı bir kaynaktır: `risale-baski-rnk` (`source.tur = 'baski'`). Yıl bilinmediği için kimlikte yıl yoktur. Künye `baski_bilgisi` alanındadır: `yayinevi = "RNK Neşriyat"`, `yazi = "latin"`; yıl, ISBN ve boy boştur ve editör doldurur (İ-24). Kayıt kartı [Kaynaklar](./01-kaynaklar.md) §3.5'tedir.
- **Veri.** RNK'nın mobil ve web uygulamasının (`rnk.tr`) giriş istemeyen statik dosyalarıdır (`rnknesriyat.com/res/metinler/…`): kitap başına bir `txt` (basılı sayfa işaretli metin, `#n` satırları) ve bir `json` (içindekiler ağacı ve `pageNo`). Sürüm katalogdaki dosya özetidir (`hash_txt`, `hash_json`). Sözler'de sayfa işaretleri `#4`…`#862` arası kesintisizdir ve sayfa sınırlarının çoğu cümle ortasına düşer (basılı sayfa); RNK sitesindeki satış baskısı da Sözler için 862 sayfa verir. Web uygulamasında baskı düzeni seçimi yoktur. Veri belgelenmiş bir uç değil, uygulamanın kendi içeriğidir; dosyalar kilitlenir ve değişiklik raporlanır.
- **Bölüm başı sayfaları.** `page_map` tek tablo kalır; ayrı bölüm-sayfa tablosu ve göç açılmaz. Bölüm başı satırı bölümün ilk paragraf çapasıyla (`start_offset = 0`) bütün kitaplar için yazılır (`data_version` soneki `/bolum-basi`). `volume` baskının kitap kimliğidir (RNK kitap kimliği: `sozler`, `emirdag1` …); bizim slug'larımıza eşleme `risale-kitaplar.json` içindedir.
- **Paragraf düzeyi.** Hizalama bütün kitaplarda yapılır; pilotla sınırlı değildir (Sözler'de İkinci, Üçüncü ve Dördüncü Söz'de kelime eşleşmesi %100). Yapısı RNK'dan gelen kitaplarda (derleme, RNK'ya özgü, Osmanlıca ve Arapça) sayfa başı birimin kendi çapasıdır; Diyanet yapılı kitaplarda RNK metni Diyanet metniyle hizalanır. Hizalanan sayfanın gerçek başlangıcı bölüm başı satırının yerine geçer; hizalanamayan sayfa rapora ve İ-24'e gider. RNK metni burada yalnız hizalama girdisidir; veritabanına yalnız bölüm 1'deki kapsamdaki paragraflar metin olarak girer. Baskıların kendi dipnot, fihrist ve editoryal ekleri kopyalanmaz. `osm_asamusa`, `osm_mektubat` ve `osm_sualar` dosyalarında sayfa işareti yoktur; bu üç kitap için yalnız bölüm başı satırı yazılır ve eksiklik rapora gider.
- **Yedek.** Hizmet Vakfı (Envar) Külliyat görünümü ("Hizmet Vakfı ve Envar Neşriyat'ın Latin harfli Türkçe baskısı"; 2 Kasım 2026'da ulaşılamamıştı, 12 Kasım 2026'da açıldı) yalnız RNK'da olmayan ya da hizalanamayan kitap için yedektir ve varsayılan olarak indirilmez; sayfa başına istek gerektirir ve sayfa numaraları RNK baskısıyla uyuşmaz (Sözler 872 sayfa, RNK 862). risale.online ("Hayrat Neşriyat, Isparta 2016") yalnız noktasal doğrulama içindir. Yedek kaynak ayrı bir `baski` kaydıyla aynı şemaya yazılır; baskılar eşit gösterilir (bölüm 2).
- **Ölçek.** RNK `tr` rafı toplam 6.893 sayfadır. Kitapyurdu listesindeki 14 ciltlik büyük boy, 7.550 sayfalık takım RNK'nın değil Yeni Asya Neşriyat'ın takımıdır (ISBN 9755257525, 2017; [kitapyurdu](https://www.kitapyurdu.com/kitap/risalei-nur-kulliyati-buyuk-boy-14-cilt-takim/429602.html)); RNK baskısının sayfa sayısı olarak kullanılmaz. Dört ana mecmua 130 parçadan oluşur ([TDV İA](https://cdn2.islamansiklopedisi.org.tr/dosya/35/C35011446.pdf)).

### 3.4 Âyet atıf dizini

Dizin `xref` tablosunda `rn:` çapalarından `q:` çapalarına giden bağlantılardır: açık kaynak gösterimi `atif`, Arapça alıntı `iktibas`, metni verilmeyen anıştırma `ima` (yalnız küratörlü). Ardışık âyetler birlikte alıntılanmışsa hedef âyet aralığı çapasıdır: `q:{s}:{ilk}-{son}` (K-26). Yöntem [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) dosyasındadır; özet:
- "(Bakara Sûresi, 255)" ya da "Âl-i İmrân: 7" gibi açık atıflar küçük bir gramer ve sure adı varyant tablosuyla ayrıştırılır.
- Arapça diziler normalize edilir ve Kur'an'ın Uthmani ve imlâî biçimleriyle oluşturulmuş 3–4 kelimelik n-gram indeksinde aranır; adaylar Smith-Waterman hizalamasıyla genişletilir.
- Kısa ve kalıplaşmış ifadeler düşük ön güvenle başlar. QUL 5.641 tekrarlanan ifade listeliyor; "تَجْرِى مِن تَحْتِهَا ٱلْأَنْهَـٰرُ خَـٰلِدِينَ" 18 âyette geçiyor ([QUL](https://qul.tarteel.ai/morphology_phrases?page=61)).
- Hazır araçlar önce Risale örnekleri üzerinde ölçülür: `ijaza` 2.0.0 ([PyPI](https://pypi.org/project/ijaza/)), `quran-detector` 0.0.2 ve `quran-toolkit` 0.1.0. Kazanan sarılır; hiçbiri tutmazsa İktibas tespiti §5–§6 eşleştiricisi yazılır (A20.7).
- Sözler, Mektubat, Lem'alar, Şuâlar, Mesnevî-i Nuriye ve İşârâtü'l-İ'câz'dan tabakalı seçilen 300–500 paragraflık altın set elle etiketlenir; kesinlik ve duyarlılık uzun ve kısa iktibaslar için ayrı raporlanır.
- Basılı fihristler yalnız başlangıç noktasıdır. Bir çalışma âyetlerin çoğu zaman başlık olarak kullanıldığını, pek çok âyetin metni verilmeden açıklandığını ve bir fihrist kaydı için "Kur'an'da bu metinle herhangi bir âyet bulunamamıştır" notu düşüldüğünü gösteriyor ([RİNAP](https://rinap.uskudar.edu.tr/uploads/site/6/content/files/risale-i-nurun-tefsirdeki-yeri-compressed.pdf)).
- İşârâtü'l-İ'câz Fâtiha'dan Bakara 33'e kadar tefsir eder.

Otomatik yöntemler seçilen Risale metni üzerinde çalışır (A20.7). Dizin metinlidir: bağlantı yanındaki parça metin kopyalanmaz, `rn:` çapa aralığından okunur; böylece metin tek yerde durur. Dizin `risale-dizin` paketindeki `xref_idx` tablosuna yazılır; kaynak kaydı `risale-atif-dizini`dir. Hazır bir Risale âyet atıf dizini internette bulunamadı (yalnız basılı fihristler); dizin kendi hattımızla üretilir.

### 3.5 Lügat

- **Köken ve yazım başvuruları.** Internet Archive'daki taramalar: Redhouse, *A Turkish and English Lexicon* (1890; `aturkishandenglishlexicon1`, `_djvu.txt` 8.447.120 bayt), Kâmûs-ı Türkî'nin Latin harfli kopyası (Şemseddin Sâmi; `kamus-i-turki-semseddin-sami-bey`, `_djvu.txt` 5.969.007 bayt) ve Lugat-ı Nâci (Muallim Nâci ve Müstecâbîzâde İsmet Bey; 1891; `lugati-naci`, `_djvu.txt` 2.585.323 bayt). Yedekler: Kâmûs-ı Türkî 1899 taraması `kamusitrki00emse`, `ottomanlexicons.com` ve Redhouse için [HathiTrust](https://catalog.hathitrust.org/Record/001771732) kaydı. Osmanlıca başlıklar OCR'da bozuk okunur, Latin açıklamalar okunabilir; kalite 100 başlık söz örneklemiyle ölçülür ve Osmanlıca OCR'ı kullanılamayan kopyalar kullanılmaz (A20.6). Çağdaş Sözlük'e (`turki.cagdassozluk.com`) 2 Kasım 2026'da ulaşılamadı.
- **Başlık söz listesi ve sıklık.** Kelime-Frekans deposunun (`alitekdemir/Risale-i-Nur-Kelime-Frekans`, kayıt `risale-kelime-frekans`) `analysis/terkipsiz/<kitap>_frekans.txt` dosyaları (sütunlar `kelime,frekans`) 15 kitapta birleşik 20.045 benzersiz kelime verir. README'ye göre Sözler'de 56.384 lügatli kelime geçişi ve 12.692 farklı kelime var; ölçümde Sözler için 13.725 benzersiz kelime çıktı ([Kelime-Frekans](https://github.com/alitekdemir/Risale-i-Nur-Kelime-Frekans)).
- **Anlam başvurusu.** Aynı deponun `data/eRisale/raw/<kitap>.csv` dosyaları (sütunlar `"kelime","anlam"`; Külliyat sayfa altı kelime açıklamaları) 15 kitapta 398.772 satır ve 46.090 benzersiz kelime taşır. 26 Ekim 2026 kararı geçerlidir ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 10): `anlam` sütunu maddeye ve pakete yazılmaz, yalnız editör kartında başvuru olarak görünür. Madde başlık söz, sıklık ve sözlük isabetiyle `aday` ve "doğrulanmamış" rozetiyle açılır, `tanim_tr` boş kalır; tanımı editör yazar (A20.6, İ-28).
- **Madde yapısı (öneri).** `lugat_madde(id, source_id, basliksoz, basliksoz_norm, osmanlica_yazim, koken_dil, tanim_tr, ar_kok_id, kaynaklar, duzey, status, origin, version, content_hash, data_version)`; `tanim_tr` boş olabilir ve `UNIQUE (source_id, basliksoz)` (A20.6). `ar_kok_id` QAC kök envanterine bağlanır ve Kur'an'a köprü olur ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)). `duzey` okurun "Lügat: Kapalı / Az / Orta / Çok" yoğunluk ayarını besler.
- **İş akışı.** Önce hazır kaynak: başlık söz ve sıklık Kelime-Frekans'tan gelir; Kelime-Frekans anlamı yalnız editör başvurusudur. Tanımı olmayan madde için yapay zekâ taslağı S-16'ya ertelendi ([K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü) madde 1; [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-16): madde editörce yazılır ya da boş kalır. S-16'da taslak yalnız "doğrulanmamış" rozetiyle üretilebilir ([İçerik hattı](./02-icerik-hatti.md) §10). Her madde insan onayından geçer (İ-28; [Kelime anlamları](./06-kelime-anlamlari.md)).
- **Paket.** Lügat `risale-dizin` paketinde taşınır (ek ATTACH yok, kitaplar arası tekrar yok); görünürlük K-50 madde 8 gibidir: `aday` yalnız `dev` ve `internal` ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 9; [İçerik paketleri](../03-veri/03-icerik-paketleri.md) IP-10, [BÇ-23](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler) çözüldü). Lügat Risale metniyle birlikte görünür.

### 3.6 Sentetik fikstür

Sentetik `test-risale-ornek` kaynağı, Külliyat'ın yapısını taklit eden yapay Türkçe metin taşır: kitap, bölüm ve paragraf ağacı, satır içi Arapça diziler, dipnot işaretleri, uzun paragraflar. Metin bir betikle üretilir ve "örnek metin" diye işaretlenir. Kitap slug'ı `test-ornek`, kitap paketi `risale-test-ornek`'tir; paket kimliği çapadan türetilir ([İçerik paketleri](../03-veri/03-icerik-paketleri.md#4-bağlantıların-paketlere-dağılımı) §4). Kaynak yalnız `dev` derlemesinde görünür; Yayınlayıcı `test-` önekli kaynağı `public` derlemeye hiçbir durumda almaz ve `internal` derlemeye yalnız `test-kucuk` ile `test-ses` girer ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md#8-örnek-veri) §8, P-12). Okuyucu arayüzü, arama, lügat katmanı ve paket hattı bu kaynaktan üretilen paketlerle uçtan uca test edilir; gerçek metin testleri kaynak dosyasından alınmış kısa parçalarla yazılır (A20.5).

## 4. Yayın kuralları

Görünürlük editoryal kaliteye bağlıdır ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 5; [Yayın süreci](../07-yayin/01-yayin-sureci.md) §3).

- `risale-{kitap}` ve `risale-dizin` paketleri her derlemede bulunur. Onaysız Risale birimleri `dev` ve `internal` derlemelerinde "doğrulanmamış" rozetiyle görünür; `public` derlemeye yalnız onaylı birimler girer (P-10).
- Onaylı Risale birimi yoksa Risale paketleri `public` manifestinde yer almaz; `public` kuru çalıştırması yine 0 ile biter.
- Âyet atıf dizini (`risale-atif-dizini`) insan onayı isteyen türlerdendir: `aday` satırlar yalnız `dev` ve `internal`'da görünür, `public`'e yalnız onaylı satırlar girer (P-07). Dizin kitap ve bölüm adresini, âyet çapasını, bağlantı türünü, baskıyı ve sayfayı taşır; metin alıntısı bağlantıya kopyalanmaz.
- `test-risale-ornek` yalnız `dev`'de görünür (P-12).

## 5. Hazırlık listesi

- [ ] **Tedarik:** Metin, içindekiler, sayfa eşlemesi, lügat ve atıf aracı kaynakları `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında; her klasörde `SHA256SUMS` var; commit'ler ve paket sürümleri doğrulandı; kaynak kayıtları geçerli (`sources check` hatasız).
- [ ] **Metin:** Diyanet metni (`risale-asil-nusha`) ve RNK metni (`risale-rnk-metin`; derlemeler, Asâr-ı Bedîiyye, Latif Nükteler, Osmanlıca ve Arapça kitaplar) `unit` olarak yüklendi; G-KAY ve G-BUT yeşil (beklenen sayılar ölçümle aynı, metin kaynak dosyayla bayt bayt aynı); ikinci içe alma 0 değişiklik; derleme raporu yazıldı. Kelimesi kelimesine kuralı: kısaltma, sadeleştirme ve "düzeltme" yok.
- [ ] **Baskı esası:** Her kitabın dayandığı müellif tashihli 1956–1960 baskısının künyesi `risale-1956-1960` kaydına yazıldı (künye Doğrulanacak).
- [ ] **Karşılaştırma:** Metin kaynağı dışındaki dijital kopyalar yalnız karşılaştırma içindir. Farklar sürüm farkı olarak raporlanır; temel metin "düzeltilmez".
- [ ] **Künye ve mütercim (İ-24):** `risale-baski-rnk` künyesi (yıl, ISBN, boy), Osmanlıca baskı künyeleri ve Arapça kitapların mütercimi editörce dolduruldu; RNK verisinde yoktur ve hafızadan yazılmaz.
- [ ] **Yazar dökümü:** Lâhikalar ve Tarihçe-i Hayat gibi derlemelerde başka kişilerin kaleminden çıkan kısımlar olabilir (Doğrulanacak). İşârâtü'l-İ'câz ve Mesnevî-i Nûriye'nin Türkçe tercümelerinin mütercimi belirlenir (genel bilgiye göre müellifin kardeşi Abdülmecid Nursî; Doğrulanacak). Bu kısımlar atıf satırında ve kaynak kaydında ayrıca belirtilir.
- [ ] **Adresler:** Kitap ve bölüm slug'ları metnin başlıkları ve içindekilerle doğrulandı; paragraf çapaları üretildi ve donduruldu.
- [ ] **Sayfa eşlemesi:** RNK baskısının (`risale-baski-rnk`) bölüm başı satırları `page_map`'te; paragraf düzeyi hizalama bütün kitaplarda yapıldı; hizalanamayan sayfalar raporda. Başka baskılar aynı şemaya ayrı `baski` kaydıyla eklenir (bölüm 2).
- [ ] **Onay:** Kitaplar kitap bazında toplu onayla `onayli` olur (tur 1 G-BUT, tur 2 örneklem okuması, slug doğrulaması; A20.8).
- [ ] **Atıf dizini:** Araç karşılaştırma raporu ve karar kaydı var; `xref` aday satırları yüklendi; altın set görev dosyaları hazır. Etiketler geldikçe kesinlik ve duyarlılık raporlanır, onaylı bağlantılar yayına girer (İ-13).
- [ ] **Lügat:** Başlık söz listesi `aday` olarak yüklendi (`tanim_tr` boş; `anlam` yalnız editör kartında); sık başlık sözlerin tanımları editörce yazıldı ve onaylı (İ-28).
- [ ] **Paketler:** `risale-dizin` (lügat dahil) ve yaklaşık 87 `risale-{kitap}` paketi (`dil` ve `yon` bilgisiyle) gerçek metinle üretildi; `risale-test-ornek` fikstürüyle uçtan uca test edildi.
- [ ] **Yayın:** `public` kuru çalıştırması 0 ile biter; `public` manifestinde yalnız onaylı Risale birimleri bulunur.

Atıf metni (öneri): "Bediüzzaman Said Nursî, Risale-i Nur Külliyatı. Metin {kaynak adı ve adresi} kaynağından alınmış, {baskı künyesi} esas alınarak kelimesi kelimesine yayımlanmıştır."

## 6. Açık sorular

1. Metin kaynağının kitap kapsamı: Hizmet Vakfı ve eRisale kitap listelerinde olup RNK ve Diyanet'te ayrı metin olarak bulunmayan eserler (A20.1 listeleri karşılaştırır; eksik kitabı başka kaynaktan eklemek kapsam değişikliğidir).
2. *Çözüldü (12 Kasım 2026, [K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 11):* Risale birimlerinin `taslak` → `onayli` yolu kitap bazında toplu onaydır.
3. Küçük kitapların slug'ları ve Lâhika parçalarının numaralandırması (metinle doğrulanır).
4. Her kitap için dayandığı baskının künyesi.
5. Başka yazar ve mütercimlerin kısımları.
6. *Çözüldü (12 Kasım 2026, K-51 madde 6; [BÇ-07](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)):* Bölüm başı baskı sayfası bölümün ilk paragraf çapasıyla `page_map`'e girer.
7. *Çözüldü (12 Kasım 2026, K-51 madde 9; [BÇ-23](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)):* Lügat verisi `risale-dizin` paketinde taşınır.
8. Aramada derleme kopyalarının tekrarı ([BÇ-62](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)), Osmanlıca ve Arapça okuyucu ([BÇ-63](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)) ve Osmanlıca `ar_norm` Farsça harf katlaması ([BÇ-64](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)).

## İlgili dosyalar
- [Kaynaklar](./01-kaynaklar.md) · [İçerik hattı](./02-icerik-hatti.md) · [Hadis hazırlığı](./04-hadis-hazirligi.md) · [Kelime anlamları](./06-kelime-anlamlari.md)
- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md)
- [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) · [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)
- [Yayın süreci](../07-yayin/01-yayin-sureci.md) · [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) · [Riskler](../08-yol-haritasi/03-riskler.md)
