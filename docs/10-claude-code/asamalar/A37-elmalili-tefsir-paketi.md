# A37 · Elmalılı tefsir paketi

> **Sürüm:** 1.3 · **Tarih:** 11 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)
> **Faz:** 4 · v1.x · **Önkoşul:** A16 (A16.4 yeterli: [A16](./A16-elmalili-meali.md) meal birimleri yüklenmiş olmalı; insan turları beklenmez) · [A18](./A18-baglantilar-ve-altin-setler.md) · **İnsan adımı:** İ-11
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `test-yazari` · `sunucu-gelistirici` · `mobil-gelistirici` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · `paket-yayini` · `mobil-ekran` · **Tahmini oturum:** 6+ (insan düzeltme süresine bağlı)
> **Başlat:** `/asama A37`

## Amaç
*Hak Dini Kur'an Dili*'nin tefsir paragrafları ve haşiyeleri, A16'nın hazır metin araçlarıyla (kaynak kaydı, kilit, çıkarılmış metin, `taslak` giriş, inceleme kuyruğu; K-49) uygun bir hazır metinden `tf:elmalili:…` çapalarına alınır, iki düzeltme turundan geçer ve `tefsir-elmalili` paketi olarak yayımlanır. Uygun hazır metin yoksa (eksiksiz kapsam, yapılandırılabilir biçim, sabitlenebilir sürüm) tefsirin OCR'ı ve özgün baskı taraması proje sonuna bırakılır (S-15; K-49 madde 3) ve A37 tedarik raporuyla kapanır. v1'de yazılan tefsir görünümü gerçek pakete bağlanır. Görünürlük kalite temellidir: onaysız tefsir birimleri `dev` ve `internal` derlemelerde "doğrulanmamış" rozetiyle görünür; `public`'e yalnız onaylı birimler girer (P-10).

## Okunacak belgeler
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.3 Meal ve tefsir (`elmalili-tefsir` kartı), §5 Yeni kaynak ekleme
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §3 kaynak baskı ve tarama, §4 OCR ve hazır metin ölçümü, §5 Yol B kuralı, §6 sınır durumları, §7 editör, §8 QA ve örneklem, §9 atıf, §10 tefsir metni
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §1, §2 kural 4, §3 `tf` deseni, §4, §5 haşiye adlandırması, §6 kararlılık, §7 kanonik metin, §10 baskı sayfaları, §13 ÇŞ-4
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §6 idempotentlik, §8 yeni kaynak ekleme, §9 QA kapıları, §10 yapay zekâ politikası, §11 maliyet
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.2, §4 · [Arama](../../03-veri/05-arama-fts5.md): §2 paket tabloları, §5
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §2, §3 yapısal bağlantılar, §8 yayın kuralı ve insan onayı · [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §1, §2, §11 hazır araçlar, §13 hadis atıfları
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §6 tefsir görünümü, §8 Bağlantılar paneli
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları · [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 altın setler

## Kapsam
**Yapılır**
- Tedarik doğrulaması ve indirme (A37.0); tefsir çapası, haşiye ve sure girişi kararları; yeni çapa vektörleri.
- Tefsir metninin alımı (hazır metin; A16'nın hazır metin araçları), `anchor/tefsir.py`, `export pg`. Sayfa eşlemesi (`page_map`) ve görsel eşleme S-15'tedir.
- Düzeltme turları ve QA kapıları; iktibas, atıf ve hadis atfı adayları; altın sete tefsir örneklemi.
- `tefsir-elmalili` paketinin `dev` yayını ve tefsir görünümünün, Kütüphane'nin, aramanın ve Bağlantılar panelinin bu pakete bağlanması.

**Yapılmaz**
- Meal (A16), kelime katmanı (A17), altın set araçları ve eşik altyapısı (A18; burada yalnız tefsir örneklemi eklenir).
- OCR, özgün baskı taraması ve `page_map` (S-15; K-49 madde 3).
- Tefsir görünümünün ilk kodu (A24'te sentetik `test-` fikstürüyle yazıldı, ör. `test-tefsir-ornek`).
- `public` yayın: tefsir birimleri onaylanınca A34 sürüm yordamıyla ve kullanıcı kararıyla (`promote`). Diğer tefsirler (S-09).

## Tedarik
Araştırma tarihi 2 Kasım 2026; A37.0'da yenilenir. Tefsir metni hazır metinle alınır (K-49); "uygun hazır metin" eksiksiz kapsam, yapılandırılabilir biçim ve sabitlenebilir sürümdür. Aday metin katmanları (archive.org `djvu.txt` makine OCR çıktısıdır) A37.0'da küçük bir örneklemle ve otomatik denetimlerle (kapsam, çapraz tanık, sadeleştirme taraması) değerlendirilir; uygun çıkmazsa OCR ve özgün baskı taraması S-15'e kalır. A16.0 yalnız iki meal ve meal tanıklarını indirdi; PDF, `pypdfium2` ve `pillow` A16'da alınmadı. Tabloda metin alıntısı yoktur; yalnız sayım, biçim ve yapı bilgisi vardır. Ölçülmeyen hücrelerde "A37.0'da ölçülür" yazar.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Tefsir metni, hazır metin (dal a) | archive.org `HakDiniKuranDili` (300 ppi, 18 dosya, son güncelleme 13 Temmuz 2026): `Hak Dini Kuran Dili_djvu.txt` (DjVuTXT, 11.444.009 bayt, SHA-1 `735617d9…5e1b`). Metin katmanında "Eser Neşriyat, 3. baskı, İstanbul 1979" künyesi geçer; baskı esası belgesizdir; makine OCR katmanıdır ve kapsam ile kalite A37.0 örneklemiyle ölçülür (K-49 madde 3) | `https://archive.org/download/HakDiniKuranDili/Hak%20Dini%20Kuran%20Dili_djvu.txt` doğrudan dosya (302 → 200, 2 Kasım 2026); boyut ve SHA-1 `https://archive.org/metadata/HakDiniKuranDili`; A37.0'da `data/gelen/elmalili-tefsir-archive/<YYYY-AA-GG>/` altına iner | 10.284.567 karakter, 342.838 satır; Arap yazısı 317.962 karakter (%3,1), Arapça ağırlıklı 6.530 satır; `…_djvu.txt` sayfa ayracı taşımaz; sayfa sınırı aynı öğedeki `…_hocr_searchtext.txt.gz` (4.540.861 bayt; açılınca 9.941.729 karakter) ve `…_hocr_pageindex.json.gz` (108.197 bayt; 8.928 sayfa, boş sayfa 0; son ofset metin uzunluğuna eşit) ile gelir (3 Kasım 2026 ölçümü); searchtext, `…_djvu.txt` ile aynı sözcük dizisidir (boşluklar normalleştirilince metin aynı; fark yalnız satır sonu ve boşluk: 9.941.729 ve 10.284.567 karakter), bu yüzden sayfa ofsetleri sözcük sırasıyla `…_djvu.txt`'ye taşınabilir; bölüm ve haşiye yapısı A37.0'da ölçülür | YEK 2021 tenkitli metin `hak-dini-kuran-dili-1-6-elmalili-muhammed-hamdi-yazir-yek-yay` (6 cilt; `…_djvu.txt` 13.692.391 bayt, SHA-1 `933d450d…27cc`; son güncelleme 23 Nisan 2025); `Elmalili0110OrjinalYenda` (`…_djvu.txt` 13.033.115 bayt, SHA-1 `99a572b8…`, 600 ppi) |
| Özgün baskı sayfa görselleri (karşılaştırma, `page_map`, OCR girdisi) | S-15'e taşındı (K-49 madde 3): A16.0 bu dosyaları indirmedi. Bilinen ölçüm (3 Kasım 2026): archive.org `HakDiniKuranDili` Text PDF 8.928 sayfa, dijital döküm; gömülü metin katmanı güvenilmez; 1935 baskısının sayfa görselleri yoktur | S-15'in tedarikinde | S-15'in tedarikinde | S-15'in tedarikinde |
| OCR motoru | S-15'e taşındı (K-49 madde 3); A09 ertelendi ve motor seçilmedi | — | — | — |
| Kur'an metni (`ayet_ar` bloğu ve Arapça alıntı hizalaması) | `tanzil-uthmani`, `tanzil-simple-clean`, `quran-data.xml` (A10) | A10'da `data/gelen/tanzil/<YYYY-AA-GG>/` altına iner; A37 yeniden indirmez | 114 sure, 6.236 âyet (A10 kabul ölçütleri) | Yok |
| CER ve bulanık eşleme | `rapidfuzz` 3.14.6 (A16'da `processor=None` ile kullanılır; `pipeline/uv.lock`) | Yeni paket yok | PyPI kaydı 2 Kasım 2026'da okundu | `jiwer` 4.0.0 |
| İktibas ve atıf adayı motoru (`enrich citations`) | A18'in motoru (n-gram indeksi, Smith-Waterman hizalaması); karşılaştırma araçları `ijaza` 2.0.0, `quran-search-in-text` 0.1.3, `passim` 2.0.1 (A18 Tedarik'i) | A18 kurar ve sürümleri sabitler; A37 yeniden almaz | A18 kabul ölçütleri ve altın set raporu | A18'in yedek adayları |
| Hadis atfı eşlemesi (`enrich hadith-refs`) | A19'un hadis kayıtları: `hadis-ahmedbaset` (AhmedBaset/hadith-json `v1.2.0` = `ca32fd72…`), `hadis-fawaz-ar` (fawazahmed0/hadith-api, `1` dalı `df57907b…`), `tecrid-ar`; atıf kısa adları `collection_alias` tablosunda | A19 alır; A37 yeniden almaz | A19 kabul ölçütleri | A19'un yedek adayları (OpenITI Shamela sürümleri) |
| Paket üretimi, imza ve arama dizini | `Mutalaa.Publisher` (A13) ve paket şeması (A12): `Microsoft.Data.Sqlite` (SQLitePCLRaw e_sqlite3), Ed25519 imza kitaplığı; Türkçe gövde cihazda üretilir, pakette gövde tablosu yoktur (K-44) | A12 ve A13 kurar; sürümler `server/Directory.Packages.props` ve `packages.lock.json` içinde | A12 ve A13 kabul ölçütleri | Yok |
| Düzeltme kuyruğu, tefsir görünümü, arama, Kütüphane | A15 editör paneli; A24, A25, A28 ve A29 mobil ekranları | Yeni kitaplık yok | Önceki aşamaların kabul ölçütleri | Yok |

Kendimiz yapacağımız işler: tefsir çapa, haşiye ve sure girişi kararları; `anchor/tefsir.py` (bölgeleri bölümlere ve paragraflara bölme, çapa, ilk kayıtta NFC, `content_hash`); hazır metnin çıkarılmış metin dönüşümü ve ortak test vektörü (sentetik metinle; A16'nın araçları yeniden kullanılır); tefsir QA kuralları ve sadeleştirme taraması; iktibas ve hadis atfı için tefsire özgü eşleştirme ayarı; düzeltme turları (İ-11); tefsir paketinin yayını ve mobil bağlama.

Seçilmeyenler (kalite ve erişim): sadeleştirilmiş baskılar (fawazahmed0 `tur-elmallsadelesti`, GitHub `elmalili-meal/kuran`, Azim; K-38) ve sure sure yeni meal öğeleri; Açık Kuran (depoda veri kümesi yok, `api.acikkuran.com` çözümlenmedi). Elmalılı tefsiri için GitHub, Hugging Face ve Kaggle'da makine okunur başka bir veri kümesi bulunamadı (web araması, 2 Kasım 2026).

## Adımlar
### A37.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: archive.org öğelerinde `https://archive.org/metadata/<öğe>` kaydındaki `item_last_updated`, boyut ve SHA-1; GitHub'da `git ls-remote` (etiket ve commit); kitaplıklarda `pypi.org/pypi/<paket>/json` (sürüm, `requires_python`, cp313 tekeri). Açılmayan ya da sürümü değişen adresin yerine yedek aday kullanılır; değişiklik tabloya yazılır.
- Tefsir için hazır metin adayı (`elmalili-tefsir-archive`) yeni boş klasöre iner: `data/gelen/elmalili-tefsir-archive/<YYYY-AA-GG>/` (`…_djvu.txt`, `…_page_numbers.json`); Claude Code formları kendisi doldurur ve `SHA256SUMS` (sha256sum biçimi, dosya adları klasöre göre: klasörde `sha256sum -c SHA256SUMS`) yazar. Adayın uygunluğu (eksiksiz kapsam, yapılandırılabilir biçim, sabitlenebilir sürüm) örneklem ve otomatik denetimlerle ölçülür (K-49 madde 3). Yedek aday seçildiyse aynı yol izlenir (`elmalili-tefsir-yek`; A16.0'daki YEK ölçümü başlangıç bilgisidir). Uygun hazır metin yoksa tefsir S-15'e bırakılır ve aşama tedarik raporuyla kapanır; OCR ve özgün baskı görselleri bu aşamada alınmaz.
- Sayfa sınırı verisi (aynı öğenin `…_hocr_searchtext.txt.gz` ve `…_hocr_pageindex.json.gz` dosyaları; `…_djvu.txt` sayfa ayracı taşımaz ve PDF'in gömülü metin katmanı güvenilmez) yalnız `page_map` için gerekir; `page_map` S-15'tedir ve bu dosyalar bu aşamada alınmaz (`## Tedarik` tablosundaki 3 Kasım 2026 ölçümü S-15 tedarikinde yenilenir).
- `pipeline/sources/elmalili-tefsir.toml` güncellenir: `surum`, `provider` (`archive.org`), `kaynak_url`, `baski_bilgisi` içinde tarama öğesi; `atif_metni` K-49 madde 14'ün düzenine göre yazılır (kaynağın adı, adresi ve sürümü; baskı esası belgesizse bu açıkça söylenir; G-INC geçince "Mütâlaa editörlerince denetlenmiştir." eklenir); `notlar` içindeki "Açık soru" satırı tedarik sonucuna göre yeniden yazılır. Kayıt dosya özeti taşımaz; özet `SHA256SUMS` dosyasındadır. `uv run --directory pipeline mutalaa sources check` 0 hata, 0 uyarı verir.
- Kitaplık eklenmez; A16'da sabitlenen sürümler `pipeline/uv.lock` içinde PyPI kaydıyla karşılaştırılır.
- Hazır yapı önce gelir: tefsir için kendi HTML, EPUB ya da PDF okuyucusu yazılmaz; iktibas ve hadis atfı için A18 ve A19'un hazır yapıları kullanılır.
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında ve `SHA256SUMS` doğrulanıyor; `elmalili-tefsir` kaydı güncel ve `sources check` 0 hata, 0 uyarı; kitaplık sürümleri `uv.lock` içinde.

### A37.1 · Çapa, kapsam ve kararlar
- Âyete bağlı bölüm `tf:elmalili:{sure}-{ilk}-{son}:p{n}`; aralık `ayet_ar` bloğundan gelir, iki uç her zaman yazılır, aralık sure sınırını geçmez (kaynak geçerse hat bölümü ikiye ayırır). Âyete bağlı olmayan bölüm `tf:elmalili:{bolum}:p{n}` (`mukaddime`; sure girişi önerisi `sure-{n}-giris`).
- Haşiye modeli (ÇŞ-4 açık). Öneri: haşiye aynı bölümde ayrı paragraf birimidir (`role = 'hasiye'`, bölümde kullanılmamış sıradaki `p{n}`); ana paragrafın `marks` alanı `{"t":"hasiye","a":"tf:…"}` ile ona bağlanır; gramer değişmez. Dipnotlar meal kuralıyla `attrs.dipnotlar` içinde, yarı açık `@{başlangıç}-{bitiş}` adresiyle.
- `p{n}` kimliktir, okuma sırası `unit.ord`'dadır; bölünme ve birleşme Çapa şeması §6'daki yönlendirmeyle yapılır. Çapalar ilk `internal` yayından önce donar.
- Öncelik sırası (ör. önce sık okunan sureler) ve kısmi yayın proje sahibince belirlenir. Kısmi yayın kalite temellidir: yalnız `onayli` birimler `public`'e girer (P-10); kapsamda olmayan âyet için tefsir görünümü "Tefsir hazırlanıyor" durumunu gösterir.
- Kararlar `/karar` ile deftere; yeni çapa örnekleri `test-vektoru` ile `shared/test-vectors/anchors/valid.jsonl` ve `invalid.jsonl` dosyalarına eklenir.
- **Bitti sayılır:** kararlar defterde; yeni vektörler TypeScript, C# ve Python'da yeşil.

### A37.2 · Hazır metinden aktarım
- Metin yolu (K-38, K-49): tefsir için hazır metin adayı archive.org metin katmanlarıdır (`## Tedarik`); makine OCR çıktısıdır ve kalitesi A37.0 ölçümüne bağlıdır. Aday uygunsa tefsir metni A16'nın hazır metin araçlarıyla (kaynak kaydı, kilit, çıkarılmış metin ve ortak vektör; A16.2) `taslak` olarak alınır; uygun değilse bu adım ve sonrası S-15'e kalır.
- OCR yolu yoktur: görsel model ya da OCR motoru bu aşamada çalıştırılmaz ve `llm estimate` gerekmez (S-15).
- Metin baskıdaki imlâsıyla aynen alınır (Latin harfli baskı; Elmalılı hazırlığı §3); açık dizgi hataları metinde değil ayrı "tashih" katmanında tutulur. Arapça alıntılar Arapça harfle ve baskıdaki harekeyle kalır, `lang="ar"` aralığı olarak işaretlenir. Aktarım kılavuzu (§5, imlâ sözlüğü) yalnız Osmanlıca harfli bir kaynak çıkarsa gerekir.
- `pipeline/src/mutalaa_pipeline/anchor/tefsir.py`: bölgeleri bölümlere ve paragraflara böler, çapa verir; kendi ürettiğimiz metin olduğu için ilk kayıtta NFC uygular ve `content_hash` hesaplar; `attrs` cilt, sayfa ve bölge kutusunu taşır. `page_map` yazılmaz (S-15).
- `uv run mutalaa anchor --source elmalili-tefsir`, `qa run --source elmalili-tefsir`, `export pg --source elmalili-tefsir --dry-run`, sonra `export pg`. Birimler `metin_durumu = 'taslak'` girer.
- **Bitti sayılır:** `qa run` G-KAY, G-BUT, G-CAP ve G-HIZ (tefsir aralıkları âyet sınırında) kapılarını geçiyor; kuru yükleme raporu incelendi.

### A37.3 · Düzeltme turları ve nitelik (İ-11 tefsir turları)
- Editör panelindeki inceleme kuyruğu (`kuyruk/ocr` rotası; A15, A16) tefsir birimleriyle çalışır: dört göz; tefsir metni ikinci onay gerektirir (`inceleyen` ve `ikinci_inceleyen` farklı editör).
- Claude Code tefsir metnini hafızadan yazmaz, tamamlamaz, "düzeltmez". Yalnız inceleme adayı üretir: imlâ sözlüğü çakışmaları, `⟦?⟧` işaretleri, Arapça alıntının Tanzil hizalamasında çıkan farkı. Karar görsele bakan insanındır; alıntı Tanzil metniyle değiştirilmez.
- G-MET bu yolda uygulanmaz (K-49 madde 12); G-INC (ikinci okuma örneklemi; hata yoksa %95 üst sınır ≈ 3/n, öneri en az 600 birim) ve sadeleştirme denetimi (0) uygulanır.
- **Bitti sayılır:** yayın kapsamındaki bütün birimler `onayli`; `⟦?⟧` sayısı 0; QA raporu `data/reports/` altında.

### A37.4 · Bağlantılar
- `uv run mutalaa enrich citations --target elmalili-tefsir` (açık atıf ve iktibas) ve `uv run mutalaa enrich hadith-refs --target elmalili-tefsir`. Satırlar `aday` girer ve editörde onaylanır; onay isteyen türdeki (`atif`, `iktibas`, `ima`) `aday` satırlar `dev` ve `internal`'da görünür, `public`'e yalnız onaylılar girer (P-07).
- Âyet ↔ tefsir aralığı ilişkisi çapadan türetilir; `xref`'e yazılmaz (K-27).
- Atıf ve iktibas altın setine Elmalılı tefsir örneklemi eklenir (Test stratejisi §4). Eşik tutmazsa o türün `aday` satırları pakete girmez. Rapor `data/reports/{data_version}.json`.
- **Bitti sayılır:** değerlendirme raporu "geçti"; onaylı bağlantılar veritabanında.

### A37.5 · Paket ve mobil bağlama
- `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev`: paket `unit`, `unit_search`, `unit_fts`, `unit_tri`, `xref_idx`, `tr_root_index`, `page_map` (boş; S-15), `pack_meta`, `pack_source`, `attribution` taşır; `depends_on: ["core"]`; öz denetimde kapsamdaki bir âyeti kapsayan paragraf sorgusu ve bir FTS sorgusu sonuç verir. `tr_root_index` satırlarından yalnız onaylılar uygulanır (P-09); `attribution` ve `pack_source` kaynak kaydının `atif_metni` ve `atif_url` değerini aynen taşır (P-11). Ardından `verify --flavor dev`.
- `mobil-gelistirici` + `mobil-ekran`: tefsir görünümü `p_tefsir_elmalili` şemasından okur (küresel âyet sırası `ayah_first`, `ayah_last`); "Takip et", başlık ve âyet çipleri; "Paket yok · İndir (boyut)" ve "Tefsir hazırlanıyor" durumları; Kütüphane içindekiler (sureler, mukaddime); Ara'da "Tefsir" kapsamı; Bağlantılar panelinde Tefsir grubu; tefsirdeki Arapça alıntıda iktibas kartı; `mutalaa-dev://tf/elmalili/2-255-257/p3` derin bağlantısı. Kısmi yayında kapsanmayan âyetin mesajı öneri olarak kayda yazılır.
- Görsel denetim ve cihaz ölçümleri kullanıcıya bırakılır (aşamayı bekletmez); `arayuz-denetcisi` kodu ve metinleri inceler.
- **Bitti sayılır:** `dev` manifestinde `tefsir-elmalili` var; mobil testler yeşil; `publish --flavor public --dry-run` 0 ile biter ve kapı raporunda `tefsir-elmalili` için yalnız `onayli` birimler "girdi" olur (P-10).

## Kabul ölçütleri
- [ ] Tedarik (A37.0): tablodaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında, SHA-256 kayıtlı; `elmalili-tefsir` kaydı güncel ve `sources check` 0 hata, 0 uyarı.
- [ ] Çapa vektörleri yeni tefsir örnekleriyle üç dilde yeşil.
- [ ] `uv run mutalaa qa run --source elmalili-tefsir` 0 ile çıkıyor.
- [ ] Kapsamdaki birimlerde `onayli` olmayan ya da `⟦?⟧` içeren satır sayısı 0 (SQL).
- [ ] Âyete bağlı tefsir birimlerinde `ayah_range` boş satır sayısı 0 (SQL).
- [ ] Onaylanmış tefsir metin incelemelerinde `ikinci_inceleyen` boş ya da `inceleyen` ile aynı satır sayısı 0 (SQL).
- [ ] Altın set raporunda tefsir örneklemi "geçti".
- [ ] `publish --flavor dev` ve `verify --flavor dev` 0 ile çıkıyor; `dev` manifestinde `tefsir-elmalili` `depends_on` olarak `core` taşıyor.
- [ ] `publish --flavor public --dry-run` 0 ile çıkıyor; kapı raporunda `core` ve `tefsir-elmalili` "girdi" (kapsamdaki birimlerin hepsi `onayli`, P-10).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; `arayuz-denetcisi` bulguları kapalı; emülatör ve ekran görüntüsü denetimi "kullanıcıya bırakıldı" diye ilerleme notunda yazılı.
- [ ] `metin-denetcisi` raporunda kanonik metne kural dışı dönüşüm yok.

## Doğrulama
```bash
pnpm --filter @mutalaa/anchors test && dotnet test --solution server/Mutalaa.slnx && uv run --directory pipeline pytest && uv run --directory pipeline ruff check .
sha256sum -c data/gelen/elmalili-tefsir-archive/<YYYY-AA-GG>/SHA256SUMS   # hazır metin yolunda
uv run --directory pipeline mutalaa sources check; echo "çıkış: $?"
uv run --directory pipeline mutalaa qa run --source elmalili-tefsir; echo "çıkış: $?"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-tefsir' AND (metin_durumu <> 'onayli' OR strpos(metin, chr(10214) || '?' || chr(10215)) > 0);"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-tefsir' AND anchor ~ '^tf:elmalili:[0-9]' AND ayah_range IS NULL;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'unit' AND alan = 'metin' AND hedef_anahtar LIKE 'tf:elmalili:%' AND durum = 'onaylandi' AND (ikinci_inceleyen IS NULL OR ikinci_inceleyen = inceleyen);"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run; echo "çıkış: $?"   # 0 beklenir; tefsir-elmalili için yalnız onaylı birimler girer (P-10)
curl -sS http://localhost:8333/mutalaa/dev/manifest.json -o .tmp/dev-manifest.json && grep -c '"tefsir-elmalili"' .tmp/dev-manifest.json
pnpm --filter @mutalaa/mobile test
```
`chr(10214)` ve `chr(10215)` `⟦` ve `⟧` işaretleridir; kabuk ve konsol kodlamasına takılmasın diye `chr()` kullanılır (`windows-sorun`). Kısmi yayında ilk sorgu kapsamdaki surelerle süzülür. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır.

Cihaz komutları ve görüntüler kullanıcıya bırakılır (aşamayı bekletmez; kapanış raporunda "kullanıcıya bırakıldı" yazılır):
```bash
adb exec-out screencap -p > .tmp/tefsir.png   # Kâğıt, Gece, %200
```

## Dikkat
- İçerik etiği: tefsir, âyet ve meal metni hafızadan yazılmaz, tamamlanmaz, düzeltilmez; testte açıkça sentetik `test-` metin ("Deneme paragrafı 1 …") ya da kaynak dosyadan betikle kesilmiş parça kullanılır.
- Sadeleştirilmiş baskılar kullanılmaz (K-03). Başkasının "orijinal metin" aktarımı (tefsir için archive.org metin katmanı) yalnız kontrollü yolla girer (K-38, K-49): kaynak kaydı ve kilit, otomatik denetimler (kapsam, çapraz tanık, sadeleştirme taraması), `taslak` giriş ve iki insan turu. Metin katmanı makine OCR çıktısıdır ve kalitesi bilinmiyor; A37.0 ölçümü uygun bulmazsa hiçbir parçası kopyalanmaz ve tefsir S-15'e kalır. Yapay zekâ tefsir üretmez, çevirmez ve OCR yapmaz.
- Kanonik metin: kendi aktarımımız ilk kayıtta bir kez NFC olur, sonra değişmez; ofsetler kod noktası, aralık yarı açık. Ayrıntı: `metin-butunlugu`, `capa-gramer`.
- Görünürlük kalite temellidir (K-42): onaysız tefsir birimi `public` derlemeye girmez (P-10); `dev` ve `internal` derlemelerde "doğrulanmamış" rozetiyle görünür.
- İş büyüktür: oturumlar sure grupları hâlinde planlanır; yarıda kalan adımın yeri ilerleme notuna yazılır. Windows'ta dosyalar `encoding="utf-8"` ile açılır.

## İnsan adımları
- İ-11 (tefsir turları) · Tefsir düzeltme turları ve ikinci okuma: A37.3 boyunca. Elmalılı meal turları (İ-11, K-49 madde 12) A37'yi bekletmez; `public` yayının (A34) ve Faz 1 çıkışının şartıdır.
- Proje sahibi: öncelik sırası ve kısmi yayın (A37.1); `public`'e geçiş kararı (`promote`).
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/anchor/tefsir.py`, `qa/checks/` tefsir kuralları, `pipeline/tests/` tefsir testleri
- `shared/test-vectors/anchors/valid.jsonl`, `invalid.jsonl` ekleri
- `pipeline/sources/elmalili-tefsir.toml` (güncel kaynak kaydı); hazır metin yolunda `data/gelen/elmalili-tefsir-archive/` (git dışı)
- Editoryal veritabanında `elmalili-tefsir` birimleri, `review` ve `xref` satırları; `data/reports/` (git dışı)
- `tefsir-elmalili` paketi (`dev`); `apps/mobile/src/features/library/` ve `src/features/reader/` bağlama değişiklikleri ve testleri
- Karar defteri girdileri (haşiye, sure girişi)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A37-elmalili-tefsir-paketi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A36](./A36-senkron.md) · Sonraki: [A38](./A38-web.md)
