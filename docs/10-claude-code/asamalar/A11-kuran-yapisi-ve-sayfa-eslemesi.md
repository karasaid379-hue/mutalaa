# A11 · Kur'an yapısı: sure adları, cüz, secde, sayfa eşlemesi

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · **İnsan adımı:** İ-23
> **Ajanlar:** `hat-gelistirici` · `arastirmaci` · `sunucu-gelistirici` (şema eki gerekirse) · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · `ef-goc` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A11`

## Amaç
Okuyucunun, aramanın ve atıf ayrıştırıcısının ihtiyaç duyduğu Kur'an yapı verisi kaynak dosyadan üretilir: Tanzil kelime bölmesi (`quran_word`), cüz, hizb ve secde işaretleri, Medine 604 sayfa eşlemesi, onaylı sure adları ve yazım varyantları (`shared/data/sure-adlari.json`). Yapı verisi Tanzil üst veri dosyasından, Türkçe sure adı adayları internetteki yayımlanmış listeden gelir; hiçbir değer hafızadan yazılmaz. Okuyucu (A24) ve kelime kartı (A25) yapı adımlarına (A11.2, A11.4–A11.6) dayanır, kelime katmanı (A17) yalnız A11.2'ye; sure adları editör onayıyla sonra gelebilir. Medine 604 sayfa sınırlarının kaynağı (AS-10) Tedarik bölümünde seçilmiştir; A11.0 ve A11.1 doğrular.

## Okunacak belgeler
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §10 sayfa eşlemeleri, §12 sure adları ve insan yazımları
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5 `quran_word`, §6 `surah_alias`, §8 `review`, §9.1 `page_map`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.2 `core` tabloları (`page_map`, `sure`), §7 sayfa eşlemesinin kaynağı
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §2 varyant tablosu planı ve riskli adlar
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §2 `medine-604-duzen`, §3.1 Kur'an metni, fontlar ve mushaf düzeni, §5 yeni kaynak ekleme
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.1 (hizb kaynağı Doğrulanacak), §9 AS-10
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 7 · [Arama](../../03-veri/05-arama-fts5.md): §1.2 geniş anahtar, §1.3 Kur'an işaretleri

## Kapsam
**Yapılır**
- Tanzil üst veri dosyasının alımı (`tanzil-ust-veri`); âyet sayılarının üç yönlü karşılaştırması.
- Tanzil metninden kelime bölme işlevi ve `quran_word` tablosunun Tanzil satırları (QAC alanları boş; A17 doldurur).
- `surah_alias` adayları (internetteki sure listesinden), kurala göre varyant üretimi, onay sonrası `shared/data/sure-adlari.json` ve üretilen kopyalar.
- Cüz, hizb ve secde verisinin şeması (karar) ve yüklenmesi.
- Medine 604 sayfa eşlemesi (`page_map`), sayfa sorgu işlevi ve test 7.

**Yapılmaz**
- `quran_word`'ün QAC alanları (kök, lemma, morfoloji) ve QAC karşılaştırması (A17). Açık atıf ayrıştırıcısı (A18).
- Mod A satır düzeni ve glif verisi, `mushaf-a-cuz-*` paketleri (A26). Mod B (A40). Bu aşama QPC1 düzen dosyalarından yalnız her sayfanın ilk ve son kelimesini okur.
- `core` paketine yazma: A13 bu aşamanın çıktısını okur; A12 ve A13 önceden bittiyse küçük ek A11.4'te yapılır ve `publish --flavor dev` yeniden çalışır.

## Tedarik
Adresler 1 Kasım 2026'da açıldı; sayılar aynı günkü yerel ölçümdür. Seçim ölçütü eksiksizlik, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirliktir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)).

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Sure listesi (Arapça ad, âyet sayısı, iniş yeri, iniş sırası), cüz, hizb çeyreği, menzil, rükû, secde ve sayfa başlangıçları | Tanzil Project `quran-data.xml`: https://tanzil.net/res/text/metadata/quran-data.xml · kök `type="metadata" version="1.0"` · 77.234 bayt · SHA-256 `8867c1d88191472adec9db694b3cd9f135b1a2ef580574d32cf888dcb22c5c7a` (A04'te 2026-10-24'te alınan dosyayla aynı) · XML · alan belgesi https://tanzil.net/docs/quran_metadata | Doğrudan dosya (`curl -fL`; form, anahtar ya da başvuru yok) → `data/gelen/tanzil-ust-veri/<YYYY-AA-GG>/` | 114 sure, âyet toplamı 6.236 (86 Mekkî, 28 Medenî), 30 cüz, 240 hizb çeyreği (60 hizb), 7 menzil, 556 rükû, 604 sayfa, 15 secde (11 `recommended`, 4 `obligatory`); her grupta `index` 1'den kesintisiz ve (sure, âyet) sırası artan; sure `start` değerleri birikimli; 604 sayfa başlangıcının hepsi geçerli âyet. `quran-meta` 7.0.0 `HafsLists` ile cüz, hizb çeyreği, menzil, rükû, sayfa ve secde listelerinde 0 fark | `quran-data.js` (aynı dizin, 25.096 bayt); `quran-meta` 7.0.0 (npm; `quran-center/quran-meta` @`3b7afc7f8c905da3d8fb3e8725f86805bd76b2bd`; mutlak âyet numaralı listeler) |
| Medine 604 sayfa eşlemesi (sayfa → başlangıç ve bitiş âyeti; AS-10) | Birincil: yukarıdaki dosyanın `pages` grubu (604 giriş, âyet düzeyi). Doğrulayıcı: GitHub `zonetecde/mushaf-layout`, dal `v2`, commit `421e9eaa991897ecd50d7abb79160651a45976d3`, klasör `mushaf/QPC1` (604 `page-NNN.json`; her kelimede `location` = `sure:âyet:kelime`) | İkincisi `git clone --depth 1 --filter=blob:none --sparse` ve `git sparse-checkout set mushaf/QPC1` → `data/gelen/medine-604-duzen/<YYYY-AA-GG>/` | QPC1: 604 sayfa, 6.236 âyet, 77.429 kelime; 604 sayfanın hepsi bir âyetin 1. kelimesiyle başlar ve bir âyetin son kelimesiyle biter; her sayfanın ilk âyeti Tanzil `pages` ile 604/604 aynı. Aynı depodaki QPC2 düzeni 25 sayfada ayrılır (121–123, 145, 532–534, 565, 568, 570, 576, 584, 586, 588–590, 592–600) | `quran-meta` `PageList` (604 giriş, 0 fark); QUL mushaf düzenleri (qul.tarteel.ai; indirme oturum açma ister, seçilmedi) |
| Kelime bölmesi (`quran_word` numaralaması) | Kendi bölme işlevimiz, A10'da alınan Tanzil Uthmani metni (`tanzil-uthmani`) üzerinde; numaralama doğrulayıcısı aynı QPC1 klasörü (kelime sayısı âyet âyet QAC ile aynıdır) | Metin A10'dan; QPC1 `data/gelen/medine-604-duzen/` altından | Kural (boşlukla ayrılan belirteç; yalnız U+06D6–U+06ED işaretlerinden oluşan belirteç hariç; sure 2–114'ün (9 hariç) 1. âyetinde ilk dört besmele belirteci hariç) 77.433 kelime verir. QAC 0.4: 77.429; QPC1: 77.429, QAC ile âyet âyet 0 fark; QUL biçimli QPC Hafs kelime JSON'u: 77.432. Tanzil fazlası dört âyettedir (2:181, 8:6, 13:37, 37:130): bitişik iki Tanzil belirteci QAC ve QPC1'de tek kelimedir (QPC1 harf iskeletiyle doğrulandı; birleşme konumu sırasıyla 3., 4., 8. ve 3. belirteç) | QAC morfolojisi (`qac-morfoloji`, A17'de alınır); QUL kelime kelime JSON'u (3 âyette QAC'den +1) |
| Türkçe sure adları, adın anlamı ve yazım varyantı adayları | Vikipedi (Türkçe) "Sureler listesi": https://tr.wikipedia.org/wiki/Sureler_listesi · revizyon 37447386 (9 Temmuz 2026) · vikimetin tablosu (no, sure ve madde bağlantısı, âyet, cüz, adın anlamı, iniş yeri, iniş sırası, mukattaa harfleri) · 15.110 bayt. Varyant adayları: aynı sayfadan bağlanan 114 sure maddesinin yönlendirmeleri (MediaWiki Action API, `generator=links` ve `prop=redirects`) | `curl -sL` ile `index.php?title=Sureler_listesi&action=raw` (`oldid` ile sabitlenir) ve Action API (anahtarsız, herkese açık) → `data/gelen/sure-adlari-vikipedi/<YYYY-AA-GG>/` | 114 satır, 114 benzersiz görünen ad (30'unda şapka ya da kesme işareti var, 7'sinde görünen ad madde başlığından farklı); âyet toplamı 6.236; her sure için âyet sayısı, iniş yeri ve iniş sırası Tanzil `quran-data.xml` ile 0 fark. Yönlendirme: ilk istekte 73 sure için 180 yönlendirme (`continue` ile tamamlanır) | `quran-meta` 7.0.0 `surah.tr` (114 ad ve Türkçe anlam, şapkasız); Tanzil `tname` (114 Latin harfli yazım); A16'da alınan Elmalılı metninin sure başlıkları |

Kendimiz yapacağımız işler: kelime bölme işlevi ve dört âyetlik birleştirme listesi (`anchor/quran.py`); `quran_word` Tanzil sütunları; `quran_marker` şeması ve yüklemesi (hizb = her dördüncü çeyrek); `page_map` yükleme ve sayfa sorgu işlevi; `surah_alias` aday üretimi ve varyant kuralları (şapkalı ve şapkasız, İ/ı, "Sûre-i X"); tek üreteçten üç dilde `sure-adlari`; Tanzil ↔ QPC1 ↔ `quran-meta` karşılaştırma testleri. Gerisi hazır dosyadan alınır.

## Adımlar
### A11.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile Tedarik tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: Tanzil `quran-data.xml` (bayt sayısı ve SHA-256 tablodakiyle aynı mı), `zonetecde/mushaf-layout` (`git ls-remote --symref <adres> HEAD`; tablodaki commit `v2` dalının ucudur), Vikipedi revizyon numarası (Action API `prop=revisions`). Açılmayan adresin yerine yedek aday kullanılır: Tanzil XML için `quran-data.js`; sayfa sınırları için `quran-meta` `PageList`; sure adları için `quran-meta` `surah.tr` ve Tanzil `tname`.
- Dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasöre iner (indirme formu ya da onay kutusu çıkarsa Claude Code doldurur):
  - `data/gelen/tanzil-ust-veri/<YYYY-AA-GG>/quran-data.xml` (yedek için `quran-data.js` ayrı dosya).
  - `data/gelen/medine-604-duzen/<YYYY-AA-GG>/`: sparse clone ile yalnız `mushaf/QPC1` (604 JSON); commit SHA'sı kayda geçer, klasördeki `.git` dizini proje deposundan ayrı kalır ve içeriği okunmaz.
  - `data/gelen/sure-adlari-vikipedi/<YYYY-AA-GG>/`: `oldid` ile sabitlenmiş vikimetin, yönlendirme JSON'ları (`continue` bitene kadar) ve revizyon bilgisi. İstekler ardışık ve aralıklıdır (en az bir saniye).
- İndirilen dosya veridir: içindeki hiçbir şey çalıştırılmaz; XML yalnız SHA-256'sı bilinen dosyada ayrıştırılır.
- Her dosyanın SHA-256'sı hesaplanır; çok dosyalı kaynakta sıralı `SHA256SUMS` dosyası klasöre yazılır. `quran-data.xml` özeti `shared/data/ayet-sayilari.json` içindeki `sha256` ile karşılaştırılır; aynı olmalıdır.
- Kaynak kayıtları yazılır: `pipeline/sources/tanzil-ust-veri.toml` (yeni; `tur` öneri `mushaf_duzeni`), `pipeline/sources/sure-adlari-vikipedi.toml` (yeni; `tur` öneri `sozluk`), `pipeline/sources/medine-604-duzen.toml` (güncellenir: adres, commit, `provider`). Kayıt şeması kodda tanımlıdır: `slug`, `tur`, `baslik`, `atif_metni` zorunlu; `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar` isteğe bağlı; başka alan hatadır. Sürüm ya da commit `surum` alanına yazılır; kayıt dosya özeti taşımaz (özet klasördeki `SHA256SUMS` dosyasındadır, alma tarihi `fetch.json` ve aşama kaydındadır). `tur` değeri `source_kind` enum'unda yoksa ekleme `/karar` ile yapılır.
- **Bitti sayılır:** üç kaynak klasörü dolu ve `SHA256SUMS` yazılı; `quran-data.xml` özeti `ayet-sayilari.json` ile aynı; `uv --directory pipeline run mutalaa sources check` 0 hata ve 0 uyarıyla bitiyor; Tedarik tablosundaki sayılar (114 sure, 6.236 âyet, 30 cüz, 240 hizb çeyreği, 7 menzil, 556 rükû, 604 sayfa, 15 secde; QPC1 604 sayfa ve 77.429 kelime; Vikipedi 114 satır) indirilen dosyalardan yeniden üretildi.

### A11.1 · Alan ve sayfa sınırı doğrulaması (AS-10)
- Tanzil üst veri dosyasının adresi A04'te doğrulandı (`shared/data/ayet-sayilari.json` içindeki `kaynak_url`); bu aşama dosyayı kalıcı olarak alır (A11.0) ve kaynak kaydını açar.
- `arastirmaci` Tanzil alan belgesinden (https://tanzil.net/docs/quran_metadata) ve indirilen dosyadan şunları raporlar: dosyanın içerdiği alanlar (sure: Arapça ad, Latin yazım, İngilizce ad, âyet sayısı, başlangıç sırası, iniş yeri, iniş sırası, rükû sayısı; ayrıca cüz, hizb çeyreği, menzil, rükû, secde ve türü, sayfa başlangıcı); sayfa ve hizb çeyreği girişlerinin çözünürlüğü (âyet düzeyi: yalnız `sura` ve `aya`).
- Sayfa sınırı sınaması (AS-10): Tanzil `pages` ile QPC1 düzeni 604 sayfanın hepsinde aynı başlangıç âyetini verir; QPC1 düzeninde hiçbir sayfa âyet ortasında başlamaz ya da bitmez ([Çapa şeması](../../03-veri/01-capa-semasi.md) §10'daki "veriyle Doğrulanacak" bu ölçümle kapanır). Aynı depodaki QPC2 düzeni 25 sayfada ayrılır; `page_map.layout = medine-604` QPC1 ve Tanzil düzenidir (Dikkat).
- Hizb: Tanzil 240 hizb çeyreği verir, hizb her dördüncü çeyrektir; `quran-meta` `HizbQuarterList` ile 0 fark ([Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md) §4.1'deki "hizb kaynağı Doğrulanacak" kapanır).
- Üç ölçüm (sayfa sınırı kelime düzeyinde, hizb çeyreği sayısı, Tanzil ↔ QPC1 ↔ `quran-meta` karşılaştırması) bir pytest ya da betik raporu olarak `data/reports/` altına yazılır.
- **Bitti sayılır:** ölçüm raporu `data/reports/` altında; Çapa şeması §10 ve Kapsam ve fazlar §9 AS-10 maddeleri `/belge-esitle` ile işlendi.

### A11.2 · Üst veri alımı ve kelime bölme
- Tanzil üst veri bağdaştırıcısı A10'daki kalıpla yazılır (`ingest/tanzil.py` genişletilir; varyant adı öneri: `ust-veri`). Hat dosyayı `data/gelen/tanzil-ust-veri/` altından `data/raw/` altına alır (A04 dosyayı yalnız `.tmp/` altına indirmişti). Ham dosyanın SHA-256'sı `tanzil.lock.json` dosyasına eklenir ve `shared/data/ayet-sayilari.json` içindeki `sha256` ile karşılaştırılır; farklıysa dizi A04 üretecinden yeniden üretilir. Çıktı `data/staged/` altında sure listesi, cüz, hizb çeyreği, secde ve sayfa başlangıçları JSONL'idir.
- Âyet sayıları üç yerde aynı olmalıdır: üst veri, A10'daki Tanzil metni ve A04'ün `shared/data/ayet-sayilari.json` dizisi.
- `pipeline/src/mutalaa_pipeline/anchor/quran.py`: âyet metnini kelimelere bölen ve kod noktası aralıklarını döndüren işlev. Kural: boşlukla ayrılan belirteç; yalnız U+06D6–U+06ED karakterlerinden oluşan belirteç kelime sayılmaz ([Arama](../../03-veri/05-arama-fts5.md) §1.3 aralığı); sure 2–114'ün (9 hariç) 1. âyetindeki besmele öneki (ilk dört belirteç) kelime numarası almaz, çünkü QAC ve QPC1 düzeni de saymaz (sure 1'in 1. âyeti besmeledir ve kelimeleri sayılır; A10'un besmele gözlemi kuralın girdisidir); Tanzil'de bitişik iki belirtecin QAC ve QPC1'de tek kelime olduğu dört âyet (2:181, 8:6, 13:37, 37:130) bir birleştirme listesinden okunur (sure, âyet, birleşecek belirteç sırası; birleşen kelimenin aralığı iki belirteci ve aradaki boşluğu kapsar). Sonuç QPC1 düzeniyle aynı kelime sayısıdır; liste QPC1 harf iskeleti karşılaştırmasıyla sınanır. A17 bu bölmeyi QAC sayımıyla doğrular (ÇŞ-1).
- Bölme sonucu `quran_word` satırlarına yazılır ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §5): `anchor` `q:{s}:{a}:{k}`, `surah`, `ayah`, `word`, `ayah_index`, `text_uthmani` (âyet metninin `[char_start, char_end)` dilimi, bayt bayt), `norm` (A05 Arapça normalleştiricisi), `char_start`, `char_end`, `source_id = 'tanzil-uthmani'`, `data_version`. QAC alanları (`root_id`, `lemma_id`, `pos`, `features`, `morph_source`) boştur; A17 doldurur.
- Testler: her kelimede `ayet_metni[char_start:char_end] == text_uthmani`; `char_start < char_end`; aralıklar örtüşmüyor; kelime numaraları her âyette 1'den kesintisiz; her âyetin kelime sayısı `data/gelen/medine-604-duzen/` altındaki QPC1 düzeniyle aynı (sayı ezberlenmez, dosyadan okunur); birleştirme listesi tam olarak QPC1 ile farklı çıkan âyetleri kapsıyor; toplam kelime sayısı rapora yazılır.
- Yükleme: `quran_word` satırları A10 kalıbıyla PostgreSQL'e yazılır (`uv --directory pipeline run mutalaa export pg --source tanzil-uthmani`; komutun kelime tablosunu da yazması öneri) ve `uv --directory pipeline run mutalaa qa run --source tanzil-uthmani` G-BUT ve G-CAP'ten geçer. Sütun sahipliği: A11 yalnız Tanzil sütunlarını yazar, QAC sütunlarına dokunmaz ve satır silmez (upsert); A17 yalnız QAC sütunlarını günceller. Böylece A11'in yeniden çalışması A17'nin verisini silmez.
- **Bitti sayılır:** üç yönlü sayı testi, kelime bölme birim testleri ve `quran_word` dilim eşitliği testi yeşil; `icerik.quran_word` 6.236 âyetin hepsini kapsıyor ve kelime sayısı QPC1 düzeniyle aynı.

### A11.3 · Sure adları: adaylar, onay, dışa aktarma
- `ad_ar` ve `ayet_sayisi` yalnız üst veri dosyasından gelir. Türkçe kanonik ad, anlam ve yazım varyantı adayları A11.0'da inen listelerden gelir (Tedarik); Claude Code adı elle yazmaz.
- İçe aktarma komutu (öneri: `uv --directory pipeline run mutalaa ingest sure-adlari`) `data/gelen/sure-adlari-vikipedi/` altındaki dosyaları, `quran-meta` `surah.tr` yedeğini ve Tanzil `tname` değerlerini okur; şunları `surah_alias` tablosuna `status = 'aday'` ve her satır için `review` kaydıyla yazar (`kaynak` sütunu satırın geldiği dosyayı gösterir):
  - `kanonik` ve `diger_ad` satırları: Vikipedi tablosundaki sure adı ve madde başlığı, Vikipedi yönlendirmeleri, `quran-meta` adı ve Tanzil Latin yazımı; adın anlamı ilgili satırın notuna gider,
  - `yazim` satırları: şapkalı ve şapkasız, noktalı ve noktasız I, "Sûre-i X", "X Sûresi", "Sûretü'l-X" (kurala göre üretilir),
  - `arapca` satırları: üst verideki ad ve `سورة` önekli biçimi.
- Vikipedi listesinin âyet sayısı, iniş yeri ve iniş sırası Tanzil ile karşılaştırılır (Tedarik ölçümünde 0 fark); fark çıkarsa satır editör kuyruğuna işaretli girer.
- `alias_key` A05'teki geniş anahtardır. İktibas tespiti §2'deki riskli adlar `risky = true` önerisiyle gelir; editör onaylar.
- Onay A14'teki karar uçlarıyla verilir (`POST /api/v1/reviews/decisions`, en çok 100 kayıt, `If-Match`): editör Scalar arayüzünü (`/scalar/v1`, yalnız `Development`) kullanır ya da Claude Code çağrıyı kullanıcının açık talimatıyla yapar; karar her durumda editöründür. Panelde `surah_alias` için ayrı rota yoktur (Açık soru). Hat onaylı alana yazmaz. A14 bitmediyse onay A14 sonrasına kalır.
- Dışa aktarma onaydan sonra (öneri: `uv --directory pipeline run mutalaa export sure-adlari`): `shared/data/sure-adlari.json` (114 kayıt; [Çapa şeması](../../03-veri/01-capa-semasi.md) §12 biçimi), `packages/anchors/src/generated/sure-adlari.ts`, hattın Python modülü (öneri: `anchor/sure_adlari.py`) ve C# gömülü kaynağı tek üreteçten çıkar.
- **Bitti sayılır:** adaylar yazıldı (114 sure için kanonik aday satırı ve `review` kaydı; İ-23'ü beklemez). Onay sonrası: JSON 114 kayıt taşıyor; her sure için bir kanonik ad var; `ayet_sayisi` A04 dizisiyle aynı; üç kopya JSON ile aynı (dil başına birer test).

### A11.4 · Cüz, hizb ve secde
- Editoryal şemada ve `core` paket şemasında bu işaretler için tablo yoktur (Açık soru). Öneri, planda onaylanıp `/karar` ile yazılır: editoryal `quran_marker(kind, no, anchor, source_id, data_version)` tablosu (`kind`: `cuz`, `hizb`, `secde`) ve aynı adlı `core` tablosu. Kaynak dosya ayrıca 240 hizb çeyreği, 7 menzil ve 556 rükû verir; şema kararı bunlardan hangilerinin yükleneceğini de seçer (öneri: `hizb` türü 60 hizbı, `rub` türü 240 çeyreği taşır; menzil ve rükû v1'de kullanılmıyorsa yüklenmez). Secde türü (`recommended`, `obligatory`) tabloda taşınır.
- Göç `sunucu-gelistirici` tarafından `ef-goc` becerisiyle eklenir. A12 bittiyse tablo `packages/content-schema/sql/` DDL'ine, A13 bittiyse Yayınlayıcı'nın `core` sorgusuna bu aşamada eklenir; bitmediyse o aşamalar bu kararı uygular.
- Değerler yalnız kaynak dosyadan yüklenir. Testler değer ezberlemez: cüz sayısı 30, numaralar 1..30 kesintisiz, başlangıçlar okuma sırasında artıyor, ilk cüz `q:1:1` ile başlıyor; her çapa geçerli âyet çapası; hizb, çeyrek ve secde kayıt sayıları kaynak dosyadaki sayıya eşit.
- **Bitti sayılır:** tablo dolu, testler yeşil, karar ve `/belge-esitle` işlenmiş.

### A11.5 · Medine 604 sayfa eşlemesi
- `page_map` satırları Tanzil `pages` grubundan yazılır: `source_id = 'tanzil-ust-veri'`, `page` 1..604, `line` boş (Mod C sayfa düzeyi; Mod A satırları A26'da). `start_anchor` ve `end_anchor` kelime çapasıdır. Başlangıç `q:{s}:{a}:1`; bitiş, sonraki sayfanın başlangıç âyetinden önceki âyetin son kelimesidir (A11.2 işlevi), son sayfada `q:114:6`'nın son kelimesidir. Sayfalar âyet ortasında başlamadığı ve bitmediği için âyet düzeyi yeterlidir (A11.1 ölçümü). Biçim örneği: `medine-604 · sayfa 1 → q:1:1:1 … q:1:7:{son}`. Paketteki `page_map.layout` değeri `medine-604`'tür; Yayınlayıcı `tanzil-ust-veri` kaynak kimliğini bu düzen adına eşler (A13, A24).
- Sayfa sorgu işlevi (öneri: `anchor/sayfa.py`): sayfa → çapa aralığı, çapa → sayfa; 0 ve 605 için hata.
- Testler ([Test stratejisi](../../07-yayin/03-test-stratejisi.md) §5 test 7): 1. sayfanın birimleri `q:1:1`–`q:1:7`; 604. sayfa son surenin son âyetinde (`q:114:6`) biter; 0 ve 605 geçersiz; sayfalar 1..604 kesintisiz; boşluk ve örtüşme yok; her âyet en az bir sayfada; 604 sayfanın başlangıç âyeti `data/gelen/medine-604-duzen/` altındaki QPC1 düzeniyle aynı.
- **Bitti sayılır:** `page_map` 604 sayfa satırı taşıyor; test 7 yeşil.

### A11.6 · Yükleme ve QA
- `export pg` A10 kalıbıyla çalışır: işaret tablosu ve `page_map` tek işlemde yüklenir (`quran_word` A11.2'de yüklendi); `surah_alias` satırları aynı komutun ilk çalışmasıyla aday olarak, onaydan sonra ikinci çalışmasıyla onaylı olarak gelir.
- QA: G-KAY (yeni kaynak kayıtları), G-BUT (sayılar), G-CAP (bütün çapalar gramere uyar). Sonuç `data/reports/` altında.
- **Bitti sayılır:** `uv --directory pipeline run mutalaa qa run --source tanzil-ust-veri` 0 ile çıkıyor.

## Kabul ölçütleri
- [ ] `tanzil-ust-veri` ve `sure-adlari-vikipedi` kayıtları yazıldı, `medine-604-duzen` kaydı güncellendi; `uv --directory pipeline run mutalaa sources check` 0 hata ve 0 uyarı; `data/gelen/` klasörlerinde `SHA256SUMS` var; `quran-data.xml` özeti `tanzil.lock.json` içinde ve `shared/data/ayet-sayilari.json` ile aynı.
- [ ] Âyet sayıları üst veri, Tanzil metni ve A04 dizisinde aynı (pytest).
- [ ] `page_map` sorgusu 604 satır, en küçük sayfa 1, en büyük 604 döndürüyor; test 7 yeşil; 604 sayfanın başlangıç âyeti QPC1 düzeniyle aynı.
- [ ] Cüz, hizb ve secde testleri yeşil; değerler yalnız kaynak dosyadan.
- [ ] `quran_word` Tanzil satırları yüklü: dilim eşitliği testi yeşil, 6.236 âyetin hepsi kapsanıyor, her âyetin kelime sayısı QPC1 düzeniyle aynı, QAC alanları A17'ye kadar boş; toplam kelime sayısı raporda.
- [ ] Karar defterinde işaret şeması kararı var; Kaynaklar belgesi üç kaydı gösteriyor; Çapa şeması §10 ve Kapsam ve fazlar AS-10 `/belge-esitle` ile işlendi.
- [ ] Adaylar: 114 sure için `surah_alias` kanonik aday satırı ve `review` kaydı yazılı.
- [ ] Onay sonrası: `shared/data/sure-adlari.json` 114 kayıt; `pnpm --filter @mutalaa/anchors test`, `uv --directory pipeline run pytest` ve `dotnet test` kopyaların JSON ile aynı olduğunu doğruluyor.

## Doğrulama
```bash
sha256sum data/gelen/tanzil-ust-veri/<YYYY-AA-GG>/quran-data.xml
grep '"sha256"' shared/data/ayet-sayilari.json
uv --directory pipeline run mutalaa sources check
uv --directory pipeline run mutalaa qa run --source tanzil-uthmani
uv --directory pipeline run mutalaa qa run --source tanzil-ust-veri
uv --directory pipeline run pytest
uv --directory pipeline run ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), min(page), max(page) FROM icerik.page_map WHERE source_id = 'tanzil-ust-veri' AND line IS NULL;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), count(DISTINCT ayah_index), count(root_id) FROM icerik.quran_word;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT kind, status, count(*) FROM icerik.surah_alias GROUP BY kind, status ORDER BY 1, 2;"
pnpm --filter @mutalaa/anchors test
dotnet test --solution server/Mutalaa.slnx
```
İki özet aynı olmalıdır. `quran_word` sorgusunda birinci sütun QPC1 düzenindeki kelime sayısına (ölçüm: 77.429), ikinci sütun 6236'ya eşit, üçüncü sütun A17'ye kadar 0 olmalıdır. İşaret tablosu karara göre adlandırılır; sorgusu planda yazılır.

## Dikkat
- Sure adları, âyet sayıları, cüz, hizb, secde ve sayfa sınırları hafızadan yazılmaz; testler de sabit değer ezberlemez, kaynak dosyadan ve yapısal kurallardan türetir.
- Kur'an metni değişmez: kelime bölme yalnız aralık hesaplar, metni kopyalamaz ya da normalize etmez (`metin-butunlugu`).
- Sayfa düzeni sürümü: QPC2 düzeni QPC1'den 25 sayfada ayrılır. `medine-604` yalnız QPC1 ve Tanzil düzenidir; Mod A (A26) QPC2 ya da başka bir basımın glifleriyle çalışacaksa ayrı düzen kimliği ve ayrı `page_map` satırları gerekir.
- Vikipedi listesi ve yönlendirmeleri aday kaynağıdır, kanonik değildir: adlar editör onayına kadar `aday` kalır; liste kendi yazımını (ör. şapkasız "Nisa") taşıyabilir, yazımı editör seçer.
- `alias_key` için yalnız A05 normalleştiricisi kullanılır; yerel ayarlı küçük harf dönüşümü yasaktır.
- Riskli adlar (Nûr, Fecr …) yalnız güçlü ipucuyla atıf sayılır; bu kural A18'in ayrıştırıcısında uygulanır, burada yalnız işaretlenir.

## İnsan adımları
- İ-23 · Sure adlarının ve varyantlarının editör denetimi ve onayı: A11.3'te ([İnsan adımları](../06-insan-adimlari.md)). Adaylar internetteki listelerden gelir; editör yazmaz, denetler ve onaylar. Yalnız A11.3'ün onay ve dışa aktarma alt adımı buna bağlıdır; A11.0–A11.2 ve A11.4–A11.6 sürer. `/asama` ilerleme dosyasının Not sütununa biten adımları ve bekleyen işi yazar (ör. "A11.0–A11.2, A11.4–A11.6 tamam; İ-23 sürüyor"); A17 ve A24 önkoşul denetiminde bu nota bakar ve yalnız A11.2 ile A11.4–A11.6'ya dayandıkları için ilerler. Onaydan sonra aşama `/asama A11` ile kapanır.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py` eki, `anchor/quran.py`, `anchor/sayfa.py`, sure adı içe ve dışa aktarma komutları, testler
- `pipeline/sources/tanzil-ust-veri.toml`, `pipeline/sources/sure-adlari-vikipedi.toml`, güncellenmiş `pipeline/sources/medine-604-duzen.toml`; `tanzil.lock.json` eki
- `data/gelen/tanzil-ust-veri/`, `data/gelen/medine-604-duzen/`, `data/gelen/sure-adlari-vikipedi/` (git dışı)
- `shared/data/sure-adlari.json`, `packages/anchors/src/generated/sure-adlari.ts`, Python ve C# kopyaları
- EF Core göçü (işaret tablosu kararı gerektirirse); PostgreSQL'de `quran_word` Tanzil satırları, `surah_alias`, `review`, `page_map` ve işaret satırları
- Karar defterinde işaret şeması kaydı; Çapa şeması §10 ve Kapsam ve fazlar AS-10 için `/belge-esitle` güncellemesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A11-kuran-yapisi-ve-sayfa-eslemesi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A10](./A10-tanzil-alimi.md) · Sonraki: [A12](./A12-arama-indeksi-ve-paket-semasi.md)
