# Risale-i Nur Hazırlığı
> **Sürüm:** 1.7 · **Tarih:** 14 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) · [K-02](../00-ozet/02-karar-defteri.md#k-02--i̇lk-içerik-seti) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)

K-02 gereği Risale-i Nur'un metni, adresleri, âyet atıf dizini, lügatı ve baskı sayfa eşlemesi içerik hattıyla gelir (A20). Bu dosya kaynağın nasıl seçildiğini, hangi parçaların nasıl hazırlanacağını ve yayın kurallarını anlatır. Metin kelimesi kelimesine, kısaltmasız ve sadeleştirmesiz yayımlanır (K-25); birimler editör onayından geçtikçe mağaza paketine girer (K-42 madde 5).

## 1. Kaynak ve kapsam

Kaynak; göreve uygunluk, eksiksizlik, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirlik ölçütleriyle seçilir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1). Başvuru, onay ya da API anahtarı isteyen kaynak seçilmez. Dosyaları Claude Code indirir: her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni bir klasöre iner ve klasörde `SHA256SUMS` bulunur. Adresler, commit'ler ve sayımlar A20 `## Tedarik` bölümündedir.

- **Kitap kapsamı ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 1).** Projede RNK Neşriyat'ın Türkçe (`tr`, `tr_k`), Osmanlıca (`osm`) ve Arapça (`ar`, `ar_k`) raflarındaki bütün Risale-i Nur kitapları yer alır: 87 kitap (`tr` 61, `ota` 12, `ar` 14). Türkçe kitapların 25'i Diyanet'in kitabıdır (14 büyük, 11 küçük), 36'sı RNK'nın Diyanet'te karşılığı olmayan ya da kısmi olan kitabıdır (İman ve Küfür Muvazeneleri, Asâr-ı Bedîiyye, İlk Eserler ve 33 küçük kitap). Bu sınıflama `risale-kitaplar.json` içinde `diyanet_karsiligi` alanında (`diyanet` 25, `derleme` 34, `rnk` 28) yalnız bilgi olarak durur. Kur'an metni (`evr` rafı) yalnız Tanzil'den gelir (K-26); öteki dillere çeviri rafları (`fi`, `fr`, `uz`, `uzk`, `pt`, `id`, `ny`, `ja`, `zh`, `sw`, `el`) alınmaz. Aynı ada sahip RNK ve Diyanet kitabı tek kitaptır (ör. `gencreh` = `genclik-rehberi`); Diyanet'te birden çok kitabı bir cilde toplayan RNK kitabı Diyanet'in kitap ayrımıyla üç kitap olarak girer ve RNK içindekilerinden bölünür (`sunuhat` → `sunuhat`, `tuluat`, `isarat`).
- **Metin (K-51 madde 2).** Birincil metin kaynağı RNK Neşriyat'ın uygulama içeriğidir (kayıt `risale-rnk-metin`, `tur = "risale"`; 13 Kasım 2026 kararı: RNK yayınlarına öncelik). 87 kitabın bütün birimleri, çapaları ve metni buradan gelir: Türkçe, Osmanlıca ve Arapça kitaplar, derlemeler, Asâr-ı Bedîiyye ve Latif Nükteler dahil. RNK'nın işaretleme karakterleri birim metninden çıkarılır; ham karakter ve kod noktası aralığı `marks`'a yazılır (`t: "rnk"`), böylece kaynak bayt bayt yeniden kurulur. Anlamı veriden çıkmayan işaretler (`\`, `∫`, `§`, `÷`, `%`, `½` gibi) yorumlanmaz; anlamları ayrı bir belge çelişkisiyle karara bağlanır ([BÇ-67](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler); A20.1b). Yalnız sayfa işaretleri (`#n`) ve ayıraç satırları (`,* * *>`) birim üretmez.
- **Diyanet karşılaştırması.** Diyanet deposu (`alitekdemir/Risale-i-Nur-Diyanet`, kayıt `risale-asil-nusha`; 15 kitap klasörü; `txt`, `obsidian-markdown` ve `html` biçimleri) karşılaştırma, doğrulama ve eksik dipnot yedeğidir; birim olarak yüklenmez. Diyanet'in tahkik heyeti müellifin tashih ettiği 1956–1960 baskılarını esas almıştır ([README](https://raw.githubusercontent.com/alitekdemir/Risale-i-Nur-Diyanet/master/README.md)); `risale-1956-1960` kaydı bu baskıların künyesidir ve metin taşımaz. Karşılaştırma verisi `data/staged` altında durur (paragraf `txt`'den, yapı markdown'dan, dipnot `txt`'de varsa oradan yoksa markdown'dan; Mermaid blokları alınmaz). Diyanet ile RNK kelime dizisi örtüşmesi kitap başına rapora yazılır (A20.1): RNK'nın Diyanet'te bulunma oranı 15 büyük kitapta %97,9–99,6, Asâr-ı Bedîiyye'de %44,4, Latif Nükteler'de %15,3'tür. Diyanet'te olup RNK'da bulunmayan ya da farklı olan kısımlar ve RNK'da fazladan görünen %0,4–2,1'lik kısım (fihrist, sürüm farkı) raporlanır, metne eklenmez; RNK'daki yayıncı önsözü ve notları raporda işaretlenir (İ-24).
- **Derleme kitaplar (K-51 madde 3).** Büyük kitaplardan bölüm derleyen her RNK kitabı (Haşir Risalesi gibi küçük kitaplar, İman ve Küfür Muvazeneleri, İlk Eserler …) kendi slug'ı, kendi `rn:` çapaları ve kendi metniyle girer; metin RNK'dan gelir, Diyanet baytı kopyalanmaz ve Diyanet çapasına bağ kurulmaz. Aynı paragrafın birden çok çapası olur ve aramada tekrar görünür; sonuç gruplaması arama ve okuyucu aşamasına bırakılır ([BÇ-62](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Diyanet'in 11 küçük kitabı da RNK'dan girer.
- **Osmanlıca ve Arapça kitaplar (K-51 madde 4).** Osmanlıca kitabın slug'ı `{slug}-osmanlica`, Arapça kitabınki `{slug}-arapca` olur (Çapa şeması §5). Kitap düzeyinde `dil` (`tr`, `ota`, `ar`) ve `yon` (`ltr` ya da `rtl`) bilgisi `risale-kitaplar.json` dosyasında ve paket bilgisinde taşınır. Bu kitaplarda yalnız `ar_norm` dolar ve `ar_norm` 1.0 kalır; Farsça harf katlaması (گ, پ, چ, ژ) ayrı bir karar işidir ([BÇ-64](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Sağdan sola okuyucu ve arama katmanı A31'in işidir ([BÇ-63](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Arapça kitapların mütercimi ve Osmanlıca baskıların künyesi RNK verisinde yoktur; hafızadan yazılmaz, editör doldurur (İ-24).
- **Taslak girer.** Hazır dijital metin `taslak` girer ve editör onayından geçer ([K-38](../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 4–5). Onay yolu (K-51 madde 11): kitap bazında toplu onay; tur 1 kaynakla bayt eşitliği (G-BUT), tur 2 örneklem okuması, İ-24 slug doğrulamasından sonra. Uç `POST /api/v1/risale/books/{kitap}/approve` ve editör panelindeki "kitabı onayla" düğmesi A20.8'dedir. Risale metni onayda yeniden hesaplanmaz: metni değiştiren onay 422 verir (K-51 madde 8; `marks` ve `sentences` kararlı kalır).
- **Öteki karşılaştırma ve yedek kaynaklar.** Diyanet deposu dışındaki dijital kopyalar (Hizmet Vakfı sitesinin Diyanet ve Külliyat sayfaları, eRisale, risale.online) yalnız karşılaştırma, doğrulama ve yedek içindir: içindekiler, kelime dizisi eşliği, sayfa eşlemesi. Farklar sürüm farkı olarak raporlanır; temel metin "düzeltilmez".
- **Sadakat (K-25, K-26).** Metin kelimesi kelimesine, kısaltılmadan ve sadeleştirilmeden saklanır ve yayımlanır; yapay zekâ özeti yazılmaz (K-30). Hazır dijital metin kaynağın dağıttığı hâliyle saklanır (NFC uygulanmaz; Arapça hareke sırası NFC'ye uymayan satırlar kalır); kendi OCR aktarımımız ilk kayıtta NFC'ye çevrilir. Dosya başındaki BOM ve CR satır sonu (RNK'da 7 dosya) metne girmez ve dosya düzeyi bilgi olarak kilide yazılır. U+200C, U+200D, U+200F, U+00AD (yumuşak tire), boşluk türü karakterler (U+00A0, U+2005, U+2006, U+2009, U+200A, U+202F) ve U+06DD metinde olduğu gibi kalır; özel kullanım karakterleri (U+EEE3–U+EEE5; Arapça Mesnevî'de 3 yer) de korunur, kilitte tek tek işaretlenir ve editöre bırakılır (İ-24). G-BUT "yasak karakter yok" yerine bu karakterlerin kitap başına kilitli sayılarını denetler (K-51 madde 5). Arama için normalize metin ayrı sütundadır ve bu karakterleri siler ya da boşluğa çevirir; ham metne dokunmaz.
- **Fikstür.** Birim ve arayüz testleri için sentetik bir kaynak vardır (bölüm 3.6); gerçek metin testleri kaynak dosyasından alınmış kısa parçalarla yazılır.

## 2. Tarafsızlık

**Tarafsızlık kuralları (K-25).**
- Hiçbir cemaate ve yayınevine bağlı olunmaz. Uygulamada yayınevi markası öne çıkarılmaz; baskılar eşit gösterilir ve okur baskıyı kendisi seçer.
- Birden fazla baskı için sayfa eşlemesi tutulur (bölüm 3.3).
- Topluluklara özgü adlandırmalar kullanılmaz.

## 3. Hazırlanacak parçalar

| İş | Girdi | Aşama |
|---|---|---|
| RNK birincil metin (87 kitap: Türkçe, derlemeler, Osmanlıca, Arapça) | RNK Neşriyat uygulama içeriği (`risale-rnk-metin`) | A20.1b |
| Diyanet karşılaştırma verisi ve Diyanet ↔ RNK kelime dizisi karşılaştırma raporu | Diyanet deposu (`risale-asil-nusha`; birim olmaz) | A20.1 |
| Kitap ve bölüm adresleri | RNK içindekileri ve metnin başlık satırları; Diyanet başlıkları ve eRisale ile karşılaştırma | A20.2a, A20.2b |
| Baskı kaydı, bölüm başı ve paragraf düzeyi sayfa eşlemesi | RNK Neşriyat'ın en son güncel baskısı (`risale-baski-rnk`) | A20.3 |
| Paragraf çapaları | RNK metni | A20.2b |
| Kitap bazında toplu onay | Kitap onayı ucu ve editör düğmesi | A20.8 |
| Âyet atıf dizini | Açık atıflar ve Arapça alıntılar; hazır araçlar önce ölçülür | A20.7 |
| Lügat | Kelime-Frekans verisi, kaynak sözlükler, editör tanımları | A20.6 |
| Âyet ve hadis atıf ayrıştırıcıları | Elmalılı, Risale metni ve sentetik örnekler | A18.4, A19.5, A20.7 |
| Okuyucu arayüzü ve paket hattı | Gerçek metin; arayüz ve paket testleri için sentetik fikstür | A20.4, A20.5, A31 |
| Risale'ye özgü konu listesi (`konu:{slug}`; ör. haşir delilleri, ene ve zerre) ve paragraflara bağlanması | Anlamsal katman | v1.x ([Anlamsal katman](../05-capraz-referans/04-anlamsal-katman.md)) |

### 3.1 Kitap ve bölüm adresleri

Çapa grameri `rn:{kitap}(:{bolum})*:p{n}(:s{cumle})?` biçimindedir; örnek `rn:sozler:soz-10:hakikat-3:p4` ([Çapa şeması](../03-veri/01-capa-semasi.md)). Kitap listesi 87 kitaptır (bölüm 1) ve `shared/data/risale-kitaplar.json` dosyasında tutulur; aşağıdaki ilk tablo Diyanet deposunun 14 büyük kitabını gösterir, sonraki listeler öteki kitapları. Kesin liste RNK içindekileri, metnin başlıkları ve eRisale içindekileriyle doğrulanır (A20.2a, A20.2b). eRisale içindekilerinde kitap bölünmesi farklıdır (Emirdağ Lâhikası tek kitap; İman ve Küfür Muvazeneleri ve İlk Dönem Eserleri ayrı kitaplar); RNK'da da bölünme Diyanet'ten farklıdır (Sözler'in başında başka kitaptan bölüm, `sunuhat` birleşik kitap). Eşleştirme farkları rapora yazılır.

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| Sözler | `sozler` | Asâ-yı Mûsâ | `asa-yi-musa` |
| Mektûbât | `mektubat` | Barla Lâhikası | `barla-lahikasi` |
| Lem'alar | `lemalar` | Kastamonu Lâhikası | `kastamonu-lahikasi` |
| Şuâlar | `sualar` | Emirdağ Lâhikası I | `emirdag-lahikasi-1` |
| Mesnevî-i Nûriye | `mesnevi-i-nuriye` | Emirdağ Lâhikası II | `emirdag-lahikasi-2` |
| İşârâtü'l-İ'câz | `isaratul-icaz` | Tarihçe-i Hayat | `tarihce-i-hayat` |
| Muhâkemât | `muhakemat` | Sikke-i Tasdîk-i Gaybî | `sikke-i-tasdik-i-gaybi` |

- **Küçük kitaplar.** Diyanet deposundaki `Küçük Kitaplar` klasörü 11 eser içerir ve her eser ayrı kitap slug'ı alır. Slug'lar Diyanet dosya adlarından Çapa şeması §5 kuralıyla türetilir (metin RNK'dan gelir; eşleme `risale-kitaplar.json` kimlik tablosuyladır): `divan-i-harb-i-orfi`, `genclik-rehberi`, `hanimlar-rehberi`, `hutbe-i-samiye`, `isarat`, `konferans`, `munazarat`, `nur-cesmesi`, `nurun-ilk-kapisi`, `sunuhat`, `tuluat`.
- **Derleme ve RNK'ya özgü kitaplar.** RNK'nın Diyanet'te karşılığı olmayan ya da kısmi olan 36 Türkçe kitabı (İman ve Küfür Muvazeneleri, Asâr-ı Bedîiyye, İlk Eserler ve 33 küçük kitap) kendi slug'larını eser adından alır. Derleme kitaplar kendi metin kopyasıyla ve RNK'dan gelen metinle girer (bölüm 1). Kitap listesinin tamamı (87 kitap) `shared/data/risale-kitaplar.json` dosyasından okunur; `metin_kaynagi` bütün kitaplarda `rnk`'dır (K-51 madde 2), `diyanet_karsiligi` alanı Diyanet karşılığı bilgisini taşır: `diyanet` 25, `derleme` 34, `rnk` 28. Dil dağılımı: `tr` 61, `ota` 12, `ar` 14.

**Diyanet karşılığı olan kitaplar (`diyanet_karsiligi = diyanet`, 25):** yukarıdaki tablodaki 14 büyük kitap ve "Küçük kitaplar" maddesindeki 11 eser.

**Diyanet'in büyük kitaplarından bölüm derleyen RNK kitapları (`diyanet_karsiligi = derleme`, 34):**

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| İman ve Küfür Muvazeneleri | `iman-ve-kufur-muvazeneleri` | İlk Eserler | `ilk-eserler` |
| Âyetü'l-Kübra | `ayetul-kubra` | Bediüzzaman Cevap Veriyor | `bediuzzaman-cevap-veriyor` |
| Elhüccetüzzehra | `elhuccetuzzehra` | Ene ve Zerre | `ene-ve-zerre` |
| Hakikat Nurları | `hakikat-nurlari` | Haşir Risalesi | `hasir-risalesi` |
| Hastalar Risalesi | `hastalar-risalesi` | Hizmet Rehberi | `hizmet-rehberi` |
| İhlas Risaleleri | `ihlas-risaleleri` | İhtiyarlar Risalesi | `ihtiyarlar-risalesi` |
| İkinci Şua | `ikinci-sua` | İman Hakikatleri | `iman-hakikatleri` |
| Küçük Sözler | `kucuk-sozler` | Meyve Risalesi | `meyve-risalesi` |
| Miftahu'l-İman | `miftahul-iman` | Mirac ve Şakk-ı Kamer | `mirac-ve-sakk-i-kamer` |
| Mirkatü's-Sünnet | `mirkatus-sunnet` | Mu'cizât-ı Ahmediye | `mucizat-i-ahmediye` |
| Mu'cizat-ı Kur'âniye | `mucizat-i-kuraniye` | Münâcat | `munacat` |
| Nur Aleminin bir Anahtarı | `nur-aleminin-bir-anahtari` | On Üçüncü Şua | `on-ucuncu-sua` |
| Otuzuncu Lem'a | `otuzuncu-lema` | Otuz Üç Pencere | `otuz-uc-pencere` |
| Rahmet ve Şefkat İlaçları | `rahmet-ve-sefkat-ilaclari` | Ramazan İktisat Şükür | `ramazan-iktisat-sukur` |
| Tabiat Risalesi | `tabiat-risalesi` | Uhuvvet Risalesi | `uhuvvet-risalesi` |
| Vesvese ve Hikmetü'l-İstiâze | `vesvese-ve-hikmetul-istiaze` | Yirmi Dördüncü Mektup | `yirmi-dorduncu-mektup` |
| Yirmi Üçüncü Söz | `yirmi-ucuncu-soz` | Zühretü'n-Nur | `zuhretun-nur` |

**Diyanet karşılığı olmayan ya da kısmi olan Türkçe kitaplar (`diyanet_karsiligi = rnk`, 2):** Asâr-ı Bedîiyye (`asar-i-bediiyye`), Latif Nükteler (`latif-nukteler`).

**Osmanlıca kitaplar (`diyanet_karsiligi = rnk`, 12):**

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| Asâ-yı Musa | `asa-yi-musa-osmanlica` | Barla Lâhikası | `barla-lahikasi-osmanlica` |
| Emirdağ Lâhikası 1 | `emirdag-lahikasi-1-osmanlica` | Emirdağ Lâhikası 2 | `emirdag-lahikasi-2-osmanlica` |
| İşârâtü'l-İ'caz | `isaratul-icaz-osmanlica` | Kastamonu Lâhikası | `kastamonu-lahikasi-osmanlica` |
| Lem'alar | `lemalar-osmanlica` | Mektubat | `mektubat-osmanlica` |
| Mesnevi-i Nuriye | `mesnevi-i-nuriye-osmanlica` | Sözler | `sozler-osmanlica` |
| Şualar | `sualar-osmanlica` | Tarihçe-i Hayat | `tarihce-i-hayat-osmanlica` |

**Arapça kitaplar (`diyanet_karsiligi = rnk`, 14):**

| Kitap | Slug | Kitap | Slug |
|---|---|---|---|
| Asâ-yı Musa | `asa-yi-musa-arapca` | İman ve Küfür Muvazeneleri | `iman-ve-kufur-muvazeneleri-arapca` |
| İşârâtü'l-İ'caz | `isaratul-icaz-arapca` | Lem'alar | `lemalar-arapca` |
| Mektubat | `mektubat-arapca` | Melâhık | `melahik-arapca` |
| Mesnevi-i Nuriye | `mesnevi-i-nuriye-arapca` | Saykalü'l-İslâm | `saykalul-islam-arapca` |
| Sözler | `sozler-arapca` | Şualar | `sualar-arapca` |
| Haşir Risalesi | `hasir-risalesi-arapca` | Hastalar Risalesi | `hastalar-risalesi-arapca` |
| Küçük Sözler | `kucuk-sozler-arapca` | Yirmi Üçüncü Söz | `yirmi-ucuncu-soz-arapca` |

- **Editör onayı gerektiren slug'lar.** `yirmi-ucuncu-soz-arapca` (RNK `ar_yirmiuc`; Arapça başlık Türkçe "Yirmi Üçüncü Söz" ile aynı değildir, karşılık yalnız `uid` önekinden varsayıldı: BELİRSİZ), `melahik-arapca` ve `saykalul-islam-arapca` (Türkçe karşılığı olmayan Arapça kitaplar; ad Arapça başlığın Türkçe okunuşundan türetildi) için editör onayı gerekir (İ-24); slug'lar ilk `dev` yayınından önce doğrulanır, çünkü slug sonradan değişmez (K-26; [BÇ-70](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)).
- **Osmanlıca ve Arapça kitaplar.** Slug `{türkçe-slug}-osmanlica` ve `{türkçe-slug}-arapca` olur (ör. `sozler-arapca`, `mesnevi-i-nuriye-arapca`); Türkçe karşılığı olmayan kitapta eser adı ve `-arapca` (ör. `saykalul-islam-arapca`). Paket kimliği `risale-{slug}` olarak türer (ör. `risale-sozler-osmanlica`).
- **Slug listesi ve doğrulama.** Liste küçük bir JSON dosyasında tutulur: `shared/data/risale-kitaplar.json` (slug, `dil`, `yon`, `metin_kaynagi` (hepsi `rnk`), `diyanet_karsiligi`, Diyanet dosya adları, RNK `raf` ve `uid`). Hepsi `dogrulandi: false` başlar; metnin başlıkları ve içindekilerle eşleşenler betikle `true` olur, eşleşmeyenler editör denetimine (İ-24) kalır.
- **Slug kuralı.** Küçük harf ASCII; ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u, â→a, î→i, û→u; kesme işareti düşer; boşluk tireye döner; ayrık birleşen işaretler (U+0307, U+0302) atılır. `dizin` kitap slug'ı olamaz; slug en çok 64 karakterdir ve uzun ad 64 karakterde kesilir; kardeş çakışmasında `-2` eki eklenir ve rapora yazılır.
- **Bölüm kalıpları.** `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`; iç bölümler `makam-{n}`, `hakikat-{n}`, `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `mukaddime`, `zeyl`, `hatime`; Lâhika parçası için `parca-{n}` (kaynakta numara yoksa); haşiyeler için `hasiye-{n}` (`n` bölümdeki atıf sırasıdır; [Çapa şeması](../03-veri/01-capa-semasi.md)). Kalıp dışı başlıklar `slug_turet` ile başlıktan türetilir; bölüm adı kuralları (64 karakter, kardeşte `-2`, kalıp adıyla karışan ad için `bolum-` öneki, Latin harfi olmayan başlık için `bolum-{n}`, kitap slug'ıyla aynı ilk düzey düğümün daraltılması) [Çapa şeması](../03-veri/01-capa-semasi.md) §5'tedir. Bu kurallar ilk `dev` yayınından önce kesinleşir (K-51 madde 12). Arap harfli başlıktan slug türetilemediği için Osmanlıca ve Arapça kitaplarda bu başlıkların bölüm adı `bolum-{n}` olur ([BÇ-76](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)); aynı kitabın Osmanlıca ya da Arapça sürümü ile Türkçe sürümünün bölüm ağaçlarının birebir eşleşmesi güvence altında değildir ([BÇ-77](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)).
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

- **Baskı kaydı.** Baskı ayrı bir kaynaktır: `risale-baski-rnk` (`source.tur = 'baski'`). Yıl bilinmediği için kimlikte yıl yoktur. Künye `baski_bilgisi` alanındadır: `yayinevi = "RNK Neşriyat"`; yazı Latin, Osmanlıca ya da Arapça olabildiği için kayıtta `yazi` yazılmaz, kitap düzeyinde rafa göre `risale-kitaplar.json` taşır; yıl, ISBN ve boy boştur ve editör doldurur (İ-24). Kayıt kartı [Kaynaklar](./01-kaynaklar.md) §3.5'tedir.
- **Veri.** RNK'nın mobil ve web uygulamasının (`rnk.tr`) giriş istemeyen statik dosyalarıdır (`rnknesriyat.com/res/metinler/…`): kitap başına bir `txt` (basılı sayfa işaretli metin, `#n` satırları) ve bir `json` (içindekiler ağacı ve `pageNo`). Sürüm katalogdaki dosya özetidir (`hash_txt`, `hash_json`). Sözler'de sayfa işaretleri `#4`…`#862` arası kesintisizdir ve sayfa sınırlarının çoğu cümle ortasına düşer (basılı sayfa); RNK sitesindeki satış baskısı da Sözler için 862 sayfa verir. Web uygulamasında baskı düzeni seçimi yoktur. Veri belgelenmiş bir uç değil, uygulamanın kendi içeriğidir; dosyalar kilitlenir ve değişiklik raporlanır.
- **Sayfa satırı ve bölüm başı satırı.** `page_map` tek tablo kalır; ayrı bölüm-sayfa tablosu ve göç açılmaz. Her `#n` sayfa başı için gerçek satır yazılır (başlangıç çapası ve kod noktası ofseti; sayfa cümle ortasında başlıyorsa ofset 0'dan büyüktür). Anahtar `(source_id, volume, page, line)` sayfa başına tek satıra izin verdiği için bölüm başı satırı yalnız gerçek satırı olmayan sayfada yazılır: bölümün ilk paragraf çapasıyla, `start_offset = 0`, `data_version` soneki `/bolum-basi`. Sayfa ortasında ya da aynı sayfada ikinci başlayan bölümün sayfası gerçek sayfa satırından bulunur ve rapora sayılır. Bölümün sayfası JSON `pageNo` değil, gerçek `#n` sayfasıdır. Yüklemede 26.009 sayfa satırı vardır (85 RNK dosyası; `sunuhat` dosyası üç kitaba bölünür ve sayfa listesi dosya düzeyindedir).
- **`volume`.** `volume` (`smallint`) `risale-kitaplar.json` `rnk.cilt` değeridir: her RNK dosyası (`{raf}/{uid}`) için bir kez verilen kalıcı cilt numarasıdır (1'den başlar, değişmez, yeni dosya sona eklenir). Baskının kitap kimliği (`sozler`, `emirdag1` …) değildir; kitap kimliği bu tabloyla çözülür. Aynı dosyadan bölünen kitaplar (`sunuhat`, `tuluat`, `isarat`) aynı cildi paylaşır ve satır çapasının kendi kitap slug'ını gösterir ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 6).
- **Paragraf düzeyi.** Eşleme bütün kitaplarda yapılır; pilotla sınırlı değildir. Bütün kitaplar RNK'dan geldiği için sayfa başı (`#n`), kendisinden sonra gelen ilk metin biriminin çapasına ve o birimin kod noktası ofsetine bağlanır; Diyanet ile hizalama gerekmez. Sayfa sınırı çoğu zaman cümle ortasına düşer; ofset işaret çıkarılmış birim metnindeki konumdur. Eşlenen sayfanın gerçek başlangıcı bölüm başı satırının yerine geçer; eşlenemeyen sayfa rapora ve İ-24'e gider. `#n` sayfa işareti 85 kitabın 85'inde vardır (CR satır sonu taşıyan `osm_asamusa`, `osm_mektubat` ve `osm_sualar` dahil); `json` `pageNo` değeri bazı kitaplarda azalan adım içerir ve ayrışmalar rapora gider. Baskıların kendi dipnot, fihrist ve editoryal ekleri ayrıca kopyalanmaz.
- **Yedek.** Hizmet Vakfı (Envar) Külliyat görünümü ("Hizmet Vakfı ve Envar Neşriyat'ın Latin harfli Türkçe baskısı"; 2 Kasım 2026'da ulaşılamamıştı, 12 Kasım 2026'da açıldı) yalnız RNK'da olmayan ya da sayfa işareti eşlenemeyen kitap için yedektir ve varsayılan olarak indirilmez; sayfa başına istek gerektirir ve sayfa numaraları RNK baskısıyla uyuşmaz (Sözler 872 sayfa, RNK 862). risale.online ("Hayrat Neşriyat, Isparta 2016") yalnız noktasal doğrulama içindir. Yedek kaynak ayrı bir `baski` kaydıyla aynı şemaya yazılır; baskılar eşit gösterilir (bölüm 2).
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

**Uygulama durumu (A20.7a ve A20.7b, 13–14 Kasım 2026).** Araç `quran-toolkit` 0.1.0'dır ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 13); açık atıf grameri, Arapça dizi çıkarımı ve `score`/`confidence` hesabı bizdedir (`enrich/atif_gramer.py`, `arapca_dizi.py`, `atif_guven.py`). Veritabanına 8.907 `xref` adayı yüklendi (8 `atif`, 8.899 `iktibas`; hepsi `aday`, `origin = 'hat'`; etiketsiz ölçüm, kesinlik ve duyarlılık hesaplanmadı). Bu aşamada sure adı tablosu yoktur (`shared/data/sure-adlari.json` üretilmedi): adlı atıflar ("Bakara Sûresi, 255") bulunmaz, yalnız adsız parantezli sayısal biçimler ("(2:255)") bulunur ([BÇ-73](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Bu `xref` adayları için `review` satırı açılmaz; kuyruk A18'dedir ([BÇ-72](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Altın set etiketleri İ-13'tedir.

### 3.5 Lügat

- **Köken ve yazım başvuruları.** Internet Archive'daki taramalar: Redhouse, *A Turkish and English Lexicon* (1890; `aturkishandenglishlexicon1`, `_djvu.txt` 8.447.120 bayt), Kâmûs-ı Türkî'nin Latin harfli kopyası (Şemseddin Sâmi; `kamus-i-turki-semseddin-sami-bey`, `_djvu.txt` 5.969.007 bayt) ve Lugat-ı Nâci (Muallim Nâci ve Müstecâbîzâde İsmet Bey; 1891; `lugati-naci`, `_djvu.txt` 2.585.323 bayt). Yedekler: Kâmûs-ı Türkî 1899 taraması `kamusitrki00emse`, `ottomanlexicons.com` ve Redhouse için [HathiTrust](https://catalog.hathitrust.org/Record/001771732) kaydı. Osmanlıca başlıklar OCR'da bozuk okunur, Latin açıklamalar okunabilir; kalite 100 başlık söz örneklemiyle ölçülür ve Osmanlıca OCR'ı kullanılamayan kopyalar kullanılmaz (A20.6). Çağdaş Sözlük'e (`turki.cagdassozluk.com`) 2 Kasım 2026'da ulaşılamadı. **Ölçüm (13 Kasım 2026, A20.6; `ingest/sozluk_ocr.py`):** 100 başlık söz örneğinde madde başı isabeti Kâmûs-ı Türkî Latin kopyada %45 (kontrol %2), Redhouse'ta %2 (kontrol %1) ve Lugat-ı Nâci'de %0'dır (Nâci OCR'ı Arap harflidir, Latin başlık söz bulunamaz). Örnek isabeti %30'un altındaki sözlük "güvenilmez" bayrağı alır: Redhouse ve Lugat-ı Nâci OCR'ı güvenilmez sayıldı (OCR'ın düzgün okunması S-15'e kalır). Her maddenin `kaynaklar` alanında üç sözlüğün isabeti (`sozluk_isabet`; yalnız konum, OCR metni yazılmaz) ve güvenilmez bayrağı alan sözlüklerin adı (`sozluk_guvenilmez`) durur; bunlar editör başvurusudur ve pakete girmez ([BÇ-74](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)).
- **Başlık söz listesi ve sıklık.** Kelime-Frekans deposunun (`alitekdemir/Risale-i-Nur-Kelime-Frekans`, kayıt `risale-kelime-frekans`) `analysis/terkipsiz/<kitap>_frekans.txt` dosyaları (sütunlar `kelime,frekans`) 15 kitapta birleşik 20.045 benzersiz kelime verir. README'ye göre Sözler'de 56.384 lügatli kelime geçişi ve 12.692 farklı kelime var; ölçümde Sözler için 13.725 benzersiz kelime çıktı ([Kelime-Frekans](https://github.com/alitekdemir/Risale-i-Nur-Kelime-Frekans)).
- **Anlam başvurusu.** Aynı deponun `data/eRisale/raw/<kitap>.csv` dosyaları (sütunlar `"kelime","anlam"`; Külliyat sayfa altı kelime açıklamaları) 15 kitapta 398.772 satır ve 46.090 benzersiz kelime taşır. 26 Ekim 2026 kararı geçerlidir ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 10): `anlam` sütunu maddeye ve pakete yazılmaz, yalnız editör kartında başvuru olarak görünür. Madde başlık söz, sıklık ve sözlük isabetiyle `aday` ve "doğrulanmamış" rozetiyle açılır, `tanim_tr` boş kalır; tanımı editör yazar (A20.6, İ-28).
- **Madde yapısı (uygulandı, A20.6).** `lugat_madde(id, source_id, basliksoz, basliksoz_norm, osmanlica_yazim, koken_dil, tanim_tr, ar_kok_id, kaynaklar, duzey, status, origin, version, content_hash, data_version, created_at, updated_at)`; `tanim_tr` aday iken boş olabilir, onaylı maddede dolu olmak zorundadır (CHECK) ve `UNIQUE (source_id, basliksoz)`. Hat 21.486 aday madde ve aynı sayıda inceleme satırı yükledi (`status = 'aday'`, `origin = 'hat'`, `tanim_tr` boş); sıklık `kaynaklar` içinde, `anlam` başvurusu yalnız `review.onerilen` içinde durur. `duzey` toplam sıklık dilimidir (1 en sık): toplam sıklık 100 ve üstü 1, 20 ve üstü 2, altı 3; bu eşikler öneridir ve `ingest/lugat_madde.py` içinde tek yerde durur, karara bağlanmadı ([BÇ-74](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). `ar_kok_id` QAC kök envanterine bağlanır ve Kur'an'a köprü olur ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)). `duzey` okurun "Lügat: Kapalı / Az / Orta / Çok" yoğunluk ayarını besler.
- **İş akışı.** Önce hazır kaynak: başlık söz ve sıklık Kelime-Frekans'tan gelir; Kelime-Frekans anlamı yalnız editör başvurusudur. Tanımı olmayan madde için yapay zekâ taslağı S-16'ya ertelendi ([K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü) madde 1; [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-16): madde editörce yazılır ya da boş kalır. S-16'da taslak yalnız "doğrulanmamış" rozetiyle üretilebilir ([İçerik hattı](./02-icerik-hatti.md) §10). Her madde insan onayından geçer (İ-28; [Kelime anlamları](./06-kelime-anlamlari.md)).
- **Paket.** Lügat `risale-dizin` paketinde taşınır (ek ATTACH yok, kitaplar arası tekrar yok); görünürlük K-50 madde 8 gibidir: `aday` yalnız `dev` ve `internal` ([K-51](../00-ozet/02-karar-defteri.md#k-51--risale-altyapısı-kapsam-metin-baskı-sayfası-ve-onay-yolu) madde 9; [İçerik paketleri](../03-veri/03-icerik-paketleri.md) IP-10, [BÇ-23](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler) çözüldü). Lügat Risale metniyle birlikte görünür.

### 3.6 Sentetik fikstür

Sentetik `test-risale-ornek` kaynağı, Külliyat'ın yapısını taklit eden yapay Türkçe metin taşır: kitap, bölüm ve paragraf ağacı, satır içi Arapça diziler, dipnot işaretleri, uzun paragraflar. Metin bir betikle üretilir ve "örnek metin" diye işaretlenir. Kitap slug'ı `test-ornek`, kitap paketi `risale-test-ornek`'tir (veri: 13 birim, 4 sayfa eşlemesi satırı, 15 sentetik lügat maddesi ve 2 sentetik `xref` adayı); sayfa eşlemesi `risale-dizin` paketinde `rnk-baski-test` düzeniyle yazılır, çünkü fikstür cildi (1) Sözler cildiyle (1) çakışır ([İçerik paketleri](../03-veri/03-icerik-paketleri.md) §3.2, [BÇ-75](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)); paket kimliği çapadan türetilir ([İçerik paketleri](../03-veri/03-icerik-paketleri.md#4-bağlantıların-paketlere-dağılımı) §4). Kaynak yalnız `dev` derlemesinde görünür; Yayınlayıcı `test-` önekli kaynağı `public` derlemeye hiçbir durumda almaz ve `internal` derlemeye yalnız `test-kucuk` ile `test-ses` girer ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md#8-örnek-veri) §8, P-12). Okuyucu arayüzü, arama, lügat katmanı ve paket hattı bu kaynaktan üretilen paketlerle uçtan uca test edilir; gerçek metin testleri kaynak dosyasından alınmış kısa parçalarla yazılır (A20.5).

## 4. Yayın kuralları

Görünürlük editoryal kaliteye bağlıdır ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 5; [Yayın süreci](../07-yayin/01-yayin-sureci.md) §3).

- `risale-{kitap}` ve `risale-dizin` paketleri her derlemede bulunur. Onaysız Risale birimleri `dev` ve `internal` derlemelerinde "doğrulanmamış" rozetiyle görünür; `public` derlemeye yalnız onaylı birimler girer (P-10).
- Onaylı Risale birimi yoksa Risale paketleri `public` manifestinde yer almaz; `public` kuru çalıştırması yine 0 ile biter.
- Âyet atıf dizini (`risale-atif-dizini`) insan onayı isteyen türlerdendir: `aday` satırlar yalnız `dev` ve `internal`'da görünür, `public`'e yalnız onaylı satırlar girer (P-07). Dizin kitap ve bölüm adresini, âyet çapasını, bağlantı türünü, baskıyı ve sayfayı taşır; metin alıntısı bağlantıya kopyalanmaz.
- `test-risale-ornek` yalnız `dev`'de görünür (P-12).

## 5. Hazırlık listesi

- [ ] **Tedarik:** Metin, içindekiler, sayfa eşlemesi, lügat ve atıf aracı kaynakları `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında; her klasörde `SHA256SUMS` var; commit'ler ve paket sürümleri doğrulandı; kaynak kayıtları geçerli (`sources check` hatasız).
- [ ] **Metin:** 87 kitabın RNK metni (`risale-rnk-metin`) `unit` olarak yüklendi; G-KAY ve G-BUT yeşil (beklenen sayılar ölçümle aynı, metin kaynak dosyayla bayt bayt aynı, BOM ve CR dosya düzeyi bilgi, U+200C, U+200D, U+200F, U+00AD, boşluk türü karakterler ve U+06DD kitap başına kilitli sayılarla aynı); ikinci içe alma 0 değişiklik. Diyanet (`risale-asil-nusha`) birim olarak yüklenmedi; Diyanet ↔ RNK karşılaştırma raporu yazıldı. Kelimesi kelimesine kuralı: kısaltma, sadeleştirme ve "düzeltme" yok.
- [ ] **Baskı esası:** Her kitabın dayandığı müellif tashihli 1956–1960 baskısının künyesi `risale-1956-1960` kaydına yazıldı (künye Doğrulanacak).
- [ ] **Karşılaştırma:** Diyanet deposu ve öteki dijital kopyalar yalnız karşılaştırma, doğrulama ve eksik dipnot yedeği içindir. Farklar sürüm farkı olarak raporlanır; temel metin "düzeltilmez".
- [ ] **Künye ve mütercim (İ-24):** `risale-baski-rnk` künyesi (yıl, ISBN, boy), Osmanlıca baskı künyeleri ve Arapça kitapların mütercimi editörce dolduruldu; RNK verisinde yoktur ve hafızadan yazılmaz.
- [ ] **Yazar dökümü:** Lâhikalar ve Tarihçe-i Hayat gibi derlemelerde başka kişilerin kaleminden çıkan kısımlar olabilir (Doğrulanacak). İşârâtü'l-İ'câz ve Mesnevî-i Nûriye'nin Türkçe tercümelerinin mütercimi belirlenir (genel bilgiye göre müellifin kardeşi Abdülmecid Nursî; Doğrulanacak). Bu kısımlar atıf satırında ve kaynak kaydında ayrıca belirtilir.
- [ ] **Adresler:** Kitap ve bölüm slug'ları RNK içindekileri ve metnin başlıklarıyla, Diyanet başlıkları ve eRisale ile karşılaştırılarak doğrulandı (`ar_yirmiuc`, `melahik-arapca`, `saykalul-islam-arapca` editör onaylı; İ-24); paragraf çapaları üretildi ve donduruldu.
- [ ] **Sayfa eşlemesi:** RNK baskısının (`risale-baski-rnk`) bölüm başı satırları `page_map`'te; paragraf düzeyi sayfa başı eşlemesi bütün kitaplarda yapıldı; eşlenemeyen sayfalar raporda. Başka baskılar aynı şemaya ayrı `baski` kaydıyla eklenir (bölüm 2).
- [ ] **Onay:** Kitaplar kitap bazında toplu onayla `onayli` olur (tur 1 G-BUT, tur 2 örneklem okuması, slug doğrulaması; A20.8).
- [ ] **Atıf dizini:** Araç karşılaştırma raporu ve karar kaydı var; `xref` aday satırları yüklendi; altın set görev dosyaları hazır. Etiketler geldikçe kesinlik ve duyarlılık raporlanır, onaylı bağlantılar yayına girer (İ-13).
- [ ] **Lügat:** Başlık söz listesi `aday` olarak yüklendi (`tanim_tr` boş; `anlam` yalnız editör kartında); sık başlık sözlerin tanımları editörce yazıldı ve onaylı (İ-28).
- [ ] **Paketler:** `risale-dizin` (lügat dahil) ve 87 `risale-{kitap}` paketi (`dil` ve `yon` bilgisiyle) gerçek metinle üretildi; `risale-test-ornek` fikstürüyle uçtan uca test edildi.
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
