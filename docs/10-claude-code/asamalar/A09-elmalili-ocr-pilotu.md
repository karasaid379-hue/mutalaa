# A09 · Elmalılı OCR pilotu ve yöntem seçimi (OCR motorları ve hazır metin adayları)

> **Sürüm:** 1.1 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · [A06](./A06-lisans-defteri-ve-enumlar.md) · **İnsan adımı:** [İ-09, İ-10, İ-17, İ-29](../06-insan-adimlari.md)
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `lisans-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `lisans-kapisi` · **Tahmini oturum:** 2–4 (insan beklemesi hariç)
> **Başlat:** `/asama A09`

## Amaç
Elmalılı'nın özgün baskısı (baskı kimliği `elmalili-1935`) için iki belirsizlik ölçümle kapanır: baskının yazı türü (K-03 düzeltmesi: Türkçe metin büyük olasılıkla Latin harfli, âyetler Arapça harfli; Doğrulanacak) ve metin yolu. Yol, OCR motorlarıyla hazır metin adaylarının (K-38; meal için Vikikaynak "Kur'an", tefsir için archive.org metin katmanı) aynı altın örneklemde yarıştırılmasıyla seçilir. En az iki OCR motoru ve kayıtlı hazır metin adayları 40 sayfalık tabakalı örneklemde ölçülür; insan yazımı altın metne karşı CER ve WER hesaplanır, hazır metin için ayrıca sadeleştirme izi sayılır ve tam metin denetimi yapılır. Maliyet tahmin edilir ve yol kararı `/karar` ile yazılır. Hazır metin yolu yalnız eşik geçilirse geçerlidir (başlangıç önerisi: meal bloklarında CER ≤ %1, sadeleştirme izi 0; eşik pilottan sonra kesinleşir); geçilmezse OCR yolu aynen sürer. Faz 0 çıkış ölçütü "OCR yöntemi ya da hazır metin yolu ölçümle seçildi ve yazıldı" bu aşamayla sağlanır. Meal aktarımı ve düzeltme turları A16'dadır.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §1 hukuki çerçeve, §3 kaynak baskı ve tarama standardı, §4 OCR ve değerlendirme, §5 (yalnız Yol A çıkarsa), §8 QA ölçütleri, §11 açık sorular
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §3 `mutalaa.toml` ve Kraken notu, §4 komutlar, §5 veri soyu, §7 günlük, §10 yapay zekâ politikası, §11 maliyet, §12 çalıştırma manifesti
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.3 (`elmalili-meal`, `elmalili-tefsir`), §4 (hazır metin adaylarının bulguları), §7 kontrol listesi
- [Karar defteri](../../00-ozet/02-karar-defteri.md): K-03 ve 18 Ekim 2026 düzeltmesi; [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 1–4 (kontrollü hazır metin, çıkarılmış metin, `taslak` başlangıç durumu)
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.4 (OCR adayları)

## Kapsam
**Yapılır**
- `uv run mutalaa ingest scans` komutu ve taramaların `data/raw` altına kaydı; tarama kaynağının kullanım şartının kaynak kaydına işlenmesi.
- Yazı türünün tarama üzerinde doğrulanması; baskı doğrulama listesinin eldeki nüsha için doldurulması.
- 40 sayfalık örneklem ve altın metin için karşılaştırma aracı (altın metni insanlar yazar, İ-10).
- `ocr run` (en az iki motor), `ocr eval` (CER, WER ve alt ölçüler), görsel model için `llm estimate`.
- Hazır metin adaylarının `bekliyor` kaydı ve kilidi, archive.org ofset sınaması, hazır metnin aynı altın örneklemde CER ve sadeleştirme izi ölçümü, tam metin denetimi (A09.6–A09.9). Bunun için yalnız ölçüme yetecek asgari okuyucu yazılır: kilitli dosyadan (Vikikaynak HTML ya da wikitext, metin katmanlı PDF) altın örneklemin karşılığı çıkarılır. Bu okuyucu ölçüm içindir; kalıcı değildir: `ingest/` altına konmaz, `data/staged` ya da PostgreSQL'e yazmaz, ölçüm dışında kullanılmaz. `pipeline/src/mutalaa_pipeline/qa/` altında ölçüm aracının yanında durur ve yalnız sentetik girdiyle (açıkça uydurma metin içeren küçük HTML ve PDF örnekleri) birim testlidir; gerçek aday metin teste girmez. Kalıcı okuyucular, `ingest register` ve çıkarılmış metin test vektörü A16'ya kalır.
- Pilot raporu, yol kararı (hazır metin mi OCR mı) ve `pipeline/mutalaa.toml` güncellemesi.

**Yapılmaz**
- Meal bloklarının âyetlere bölünmesi, Tanzil eşleştirmesi, inceleme kuyruğu, G-MET ve G-HIZ kapıları, 6.442 sayfanın tamamının OCR'ı (A16).
- Kalıcı hazır metin içe aktarımı: HTML, EPUB ve PDF okuyucuları, `ingest register` komutu ve çıkarılmış metin test vektörü (K-38 madde 3). Bunlar planlıdır, henüz yoktur; A16'nın hazır metin dalına bırakılır.
- Hazır metnin `serbest` yapılması, pakete ya da `public`/`internal` derlemeye alınması. Aday `bekliyor` kalır ve yalnız `dev` görür.
- Otomatik toplu indirme: aday dosyaları kullanıcı elle indirir (İ-29).
- Tefsir metni (A37). Latin harfine aktarım kılavuzunun uygulanması (A16; Yol A çıkarsa bu aşamada yalnız aktarım doğruluğu ölçülür). Tefsir için hazır metin adayı (archive.org metin katmanı) yalnız aynı ölçümün küçük bir örneğiyle denenir; kalıcı karar A37'dedir.
- Editör panelindeki OCR kuyruğu (A15).

## Adımlar
### A09.1 · Taramalar, kaynak şartı ve yazı türü (İ-09)
- İ-09 henüz yoksa `arastirmaci` §3'teki aday koleksiyonlarda (Millî Kütüphane, İSAM, Diyanet ve ilahiyat kütüphaneleri, Internet Archive, HathiTrust, Vikikaynak) tarama arar ve kullanım şartıyla listeler (hepsi Doğrulanacak); seçim kullanıcınındır.
- Görsel kaynağı sırası (K-38): önce archive.org taraması, A09.7'deki ofset sınamasından geçerse; geçmezse ya da kullanım şartı elverişsizse yedek, sahaftan alınan takım (1935 ya da 1960/1971 ofset). Özgün baskı taraması hazır metin yolunda da gerekir: altın örneklem ve Kurul'a sadakat kanıtı buna dayanır.
- Kullanıcı taramaları proje içindeki `data/gelen/elmalili-1935/` klasörüne koyar (öneri; klasör sınırı, `data/` git dışı). Dosya adı `c{cilt:02d}-s{sayfa:04d}.tif`; tarama standardı §3'teki öneridir (en az 400 dpi gri tonlama, kayıpsız TIFF).
- `uv run mutalaa ingest scans --edition elmalili-1935 --dir data/gelen/elmalili-1935/c01 --cilt 1` dosyaları `data/raw/elmalili-1935/{YYYY-MM-DD}/` altına kopyalar, SHA-256 ve `fetch.json` yazar (İçerik hattı §5). `data/raw` yalnız bu komutla yazılır. Komutların yol argümanları depo köküne göre çözülür (öneri; Elmalılı hazırlığı §4'teki örneklerle uyumlu).
- `lisans-denetcisi`: tarama kaynağı (kütüphane ya da kendi nüshamız, yer numarası, tarama tarihi, kullanım şartı) `pipeline/sources/elmalili-meal.toml` ve `elmalili-tefsir.toml` içindeki `baski_bilgisi` alanına işlenir (§3, §9). Şart görsellerin yapay zekâ servisine gönderilmesine izin vermiyorsa `embed_ok` buna göre ayarlanır ve görsel model pilottan çıkar (§4).
- Yazı türü: künye sayfası ve birkaç metin sayfası `.tmp/` altına PNG olarak çevrilir (ör. `uv run --with pillow` ile bir betik) ve incelenir. Sonuç (Yol A: Osmanlıca harf; Yol B: Latin harf) kullanıcıyla teyit edilir; K-03 düzeltmesindeki "Doğrulanacak" `/karar` ile kapanır.
- Baskı doğrulama listesi (§3) eldeki ciltler için doldurulur: künye Princeton kaydıyla uyumlu mu, cilt başına sayfa sayısı, eksik ve hasarlı sayfalar.
- Mealde âyet numaralarının nasıl işaretlendiği (§6, Doğrulanacak) aynı sayfalarda gözlenir ve rapora yazılır; A16'nın bölme yöntemi buna dayanır.
- **Bitti sayılır:** taramalar özetleriyle `data/raw` altında; yazı türü kararı karar defterinde; tarama kaynağı ve şartı TOML'da; `uv run mutalaa sources check` 0.

### A09.2 · Örneklem ve altın metin (İ-10)
- Tabakalı 40 sayfa (§4 madde 1): eldeki bütün ciltlerden; sayfa türleri meal blokları, tefsir düzyazısı, Arapça âyet blokları, dipnotlar ve başlıklar. Seçim betikle yapılır; sayfa türü görselden belirlenir ve kullanıcıya onaylatılır. Liste `data/gold/elmalili-ocr/orneklem.json` (öneri).
- Altın metin biçimi (öneri): sayfa başına UTF-8 metin dosyası; bölge türü satır başındaki işaretle (`[[meal]]`, `[[tefsir]]`, `[[ayet_ar]]`, `[[dipnot]]`, `[[baslik]]`, `[[sayfa_no]]`); okunamayan yer `⟦?⟧`.
- İki kişi örneklemi birbirinden bağımsız yazar (`yazan-a/`, `yazan-b/`). Karşılaştırma aracı farkları sayfa ve satır olarak listeler; kişiler farkları görsele bakarak çözer ve `altin/` klasörü oluşur (§4 madde 2).
- Claude Code altın metni yazmaz, tamamlamaz ve düzeltmez; yalnız araç yazar ve farkları gösterir.
- **Bitti sayılır:** 40 sayfanın altın metni var; iki yazan arasındaki CER rapora yazıldı.

### A09.3 · OCR motorları (`ocr run`)
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar: Tesseract'ın Windows kurulumu ya da Docker'da çalıştırılması, Türkçe ve Arapça dil verileri; Kraken ya da eScriptorium için hazır model, lisansı, Windows ve Python 3.13 uyumu (§4; İçerik hattı §3); görsel yapay zekâ modelinin kimliği, fiyatı ve görsel boyut sınırları (İçerik hattı §3 ve §11, "Doğrulanacak").
- Proje dışına kurulması gereken araç (ör. Tesseract) kullanıcı tarafından kurulur (İ-01'e ek). Kraken Python 3.13 ile uyumsuzsa `pipeline/ocr-kraken/` altında ayrı uv projesi olur ya da gerekçesi yazılarak pilot dışında kalır (İçerik hattı §3).
- `uv run mutalaa ocr run --edition elmalili-1935 --engine <motor> --pages <seçim>`: çıktı `data/ocr/elmalili-1935/{run_id}/` altında sayfa başına §4'teki JSON (`cilt`, `sayfa`, `motor`, `bolgeler` içinde `tur`, `kutu`, `satirlar`). `--pages` hem `c01:1-40` biçimini (§4) hem örneklem dosyasını kabul eder (öneri). Çalıştırma manifesti motor sürümünü ve model dosyası özetini taşır (İçerik hattı §12).
- Görsel model: istem `pipeline/prompts/ocr/v1.md`, §4'teki ilkelerle (aynen yaz, modernleştirme ve düzeltme yok, okunamayana `⟦?⟧`, bölge türlü JSON, sıcaklık 0). Çağrıdan önce `require_embed_ok` (İçerik hattı §10). Yanıtlar `(model, prompt_sha256, input_sha256)` anahtarıyla `data/llm-cache/` altına yazılır; günlükte metin yok, model, token ve maliyet var (§7). Ham tarama küçültülmez; gerekirse küçültülmüş kopya `data/ocr/` altında üretilir.
- Maliyet: önce 2–3 sayfayla `uv run mutalaa llm estimate` görsel token ve sayfa başına maliyeti ölçer (İçerik hattı §11). Kullanıcı bütçeyi onaylamadan 40 sayfa çalıştırılmaz (İ-17).
- **Bitti sayılır:** en az iki motorun 40 sayfalık çıktısı ve çalıştırma manifesti var.

### A09.4 · Değerlendirme (`ocr eval`)
- `uv run mutalaa ocr eval --edition elmalili-1935 --gold data/gold/elmalili-ocr/` (§4): iki taraf NFC; `CER = (S + D + I) / N`; WER. Ayrı ayrı: Türkçe metin CER'i, Arapça metin CER'i, düzeltme işaretine duyarlı CER (â, î, û), satır kaybı oranı; motor ve sayfa türü başına (§4 madde 3). Yol A'da aktarım doğruluğu ayrıca ölçülür.
- Rapor `data/reports/{run_id}.json` (İçerik hattı §7); okunur özet `.tmp/` altında, karar metnine kaynak olur.
- Ölçüm kodu bilinen yer değiştirme, silme ve ekleme sayılı sentetik örneklerle birim testlidir.
- `metin-denetcisi`: NFC adımı, `⟦?⟧` sayımı, Arapça ve Latin metin ayrımı doğru mu.
- **Bitti sayılır:** motor × sayfa türü CER ve WER tablosu dolu; birim testleri yeşil.

### A09.5 · Karar
- Seçim sayfa türü başına en düşük CER ve pilot maliyetle yapılır (§4 madde 4). Öneri eşik: insan düzeltmesinden önce meal bloklarında Yol B için CER ≤ %1, Yol A için ≤ %3. Hiçbir motor eşiği tutmazsa karar bunu yazar ve A16'nın düzeltme yükü yeniden tahmin edilir: `insan_saati = N × t_öğe` (İçerik hattı §11); `t_öğe` isteğe bağlı olarak kullanıcının birkaç sayfayı düzeltirken ölçtüğü süredir.
- `/karar` ile yeni karar: "Elmalılı OCR yöntemi" (yol, motor ya da motorlar, CER özeti, maliyet, eşik). `pipeline/mutalaa.toml` içindeki `[baski.elmalili-1935] ocr_motoru` karara göre güncellenir. `/belge-esitle` Elmalılı hazırlığı §3–§4'teki çözülen "Doğrulanacak" maddelerini ve güncellenen eşikleri işler.
- Bu adımdaki OCR motoru kararı ile A09.9'daki yol kararı tek `/karar` kaydında yazılır: hazır metin eşiği geçmese bile OCR motoru kararı gerekir; geçse bile yedek motor kaydı kalır.
- **Bitti sayılır:** karar defterinde yeni karar var; `mutalaa.toml` kararla aynı.

### A09.6 · Hazır metin adaylarının kaydı ve kilidi (K-38)
- Adaylar: meal için Vikikaynak "Kur'an" sayfası ve tefsir için archive.org metin katmanı. Sadeleştirilmiş metinler (GitHub `elmalili-meal/kuran`, Azim) ve ticari kullanımı kapatanlar (Tanzil, Açık Kuran) aday olamaz (Elmalılı hazırlığı §1).
- Her aday için `pipeline/sources/` altında ayrı bir kaynak kaydı açılır (slug öneri: `elmalili-meal-hazir-vikikaynak`, `elmalili-tefsir-hazir-archive`), `license_status = "bekliyor"`. Mevcut `elmalili-meal.toml` ve `elmalili-tefsir.toml` özgün baskı kayıtlarıdır ve bu adımda değişmez. `lisans-denetcisi` kaydı denetler; lisans kopyası ve özeti `licenses/` altına konur.
- Kilit: Vikikaynak için revizyon numarası (`oldid`) ve indirilen dosyanın SHA-256'sı; archive.org için öğe kimliği, dosya adı ve SHA-256. Özetler kayıtta ve `fetch.json`'da durur (İçerik hattı §5). Kilitsiz dosya ölçüme girmez.
- Dosyaları kullanıcı elle indirir ve `data/gelen/` altında ayrı klasöre koyar (İ-29). Claude Code toplu indirme yapmaz. `data/raw` yalnız hattın kayıt komutlarıyla yazılır.
- **Bitti sayılır:** her adayın `bekliyor` kaydı var; dosya özetleri ve revizyon numaraları kayıtta; `uv run mutalaa sources check` 0.

### A09.7 · archive.org ofset sınaması (K-38)
- Amaç: archive.org taramasının hangi baskıdan olduğunu ve sayfa düzeninin 1935 ile aynı olup olmadığını görmek (Elmalılı hazırlığı §3: archive.org `HakDiniKuranDili` 1979 baskısı satırı taşıyor; TDV İA'ya göre 1960 ve 1971 baskıları ofsettir; 1979'un tıpkıbasım olduğu kanıtlanmadı).
- `arastirmaci`, HathiTrust 1935 baskısının (8 cilt, yalnız arama) arama özelliğiyle seçilmiş sayfa numaralarını ve cilt başına sayfa sayılarını çıkarır; kaynakları bağlantıyla verir.
- Örnek sayfalar archive.org taramasındaki karşılıklarıyla yan yana konur: cilt, sayfa numarası ve sayfa başı kelimeler aynı mı. HathiTrust'tan görüntü alınmaz; yalnız arama sonucu olan sayfa numarası ve parça kullanılır.
- Sonuç üç değerden biri olur: geçti (düzen 1935 ile aynı), geçmedi, belirsiz. Geçmezse ya da belirsizse görsel kaynağı sahaftan alınan takımdır (A09.1; İ-09).
- **Bitti sayılır:** sınama tablosu ve sonucu raporda; görsel kaynağı kararı kullanıcıyla teyit edildi.

### A09.8 · Hazır metnin CER ölçümü ve tam metin denetimi (K-38)
- Altın örneklemin meal blokları (A09.2), kilitli hazır metindeki karşılıklarıyla aynı `ocr eval` ölçüm koduyla karşılaştırılır: iki taraf NFC; `CER = (S + D + I) / N` (Elmalılı hazırlığı §4). Hazır metin bir OCR motoru gibi bir "motor" girdisi olarak raporlanır; böylece tablo motor × sayfa türü düzenini korur.
- Sadeleştirme izi ayrıca sayılır: örneklemde modernleştirilmiş ya da değiştirilmiş kelime (Elmalılı hazırlığı §8 sadeleştirme denetimi). Sayımı yapan araç farkları listeler; neyin iz sayıldığına insan karar verir.
- Tam metin denetimi (hazır metin eşiğe yaklaşıyorsa ya da geçiyorsa): 6.236 âyetin kapsamı ve sadeleştirme taraması otomatik; 60 rastgele âyet elle görselle karşılaştırılır. Bu örneklem metnin %5'ini etkileyen bir sorunu yaklaşık %95 olasılıkla yakalar (0,95^60 ≈ 0,046). Elle okuma insan işidir; Claude Code yalnız örneklemi seçer ve farkları gösterir.
- Tefsir adayı (archive.org metin katmanı) için aynı ölçüm tefsir düzyazısı sayfalarının küçük bir örneğinde yapılır; kalite bilinmediği için sonuç yalnız A37'ye girdi olur.
- Eşleme: Vikikaynak metni sayfa değil sure ve âyet yapısındadır. Altın örneklemin meal blokları, her blokun kapsadığı âyet aralığına (`meal:elmalili:{s}:{a}` mantığı; aralığı insan altın metinle birlikte yazar) göre hazır metinden çıkarılır. archive.org metin katmanı ise sayfa tabanlıdır; sayfa numarası ofset sınamasından (A09.7) gelir.
- Ölçüm okuyucusu ve kodu sentetik örneklerle birim testlidir (A09.4 ile aynı testler; kapsam notu yukarıda). Claude Code hazır metni düzeltmez ve tamamlamaz.
- **Bitti sayılır:** hazır metin için CER, sadeleştirme izi sayısı ve tam metin denetimi sonucu raporda; adayın `bekliyor` kaydı değişmedi.

### A09.9 · Yol kararı: hazır metin mi OCR mı (K-38)
- Hazır metin yolu yalnız şu koşulların hepsi sağlanırsa seçilir: meal bloklarında CER eşiğin altında (başlangıç önerisi ≤ %1), sadeleştirme izi 0, tam metin denetimi temiz, ofset sınaması ya da sahaf takımıyla özgün baskı görseli elde. Eşik pilot verisine bakılarak kesinleşir ve kararda yazılır.
- Koşullardan biri sağlanmazsa OCR yolu (A09.1–A09.5; A16 OCR dalı) aynen sürer.
- Karar `/karar` ile yazılır (A09.5 ile tek kayıt): seçilen yol, ölçüm özeti, eşik, aday kaydının revizyon numarası ve SHA-256'sı, görsel kaynağı. Karar defterine Claude Code kendisi yazmaz; ana oturum `/karar`'ı çalıştırır.
- Hazır metin seçilse bile aday `bekliyor` kalır; `serbest` ve Kurul başvurusu avukat görüşüne ve Kurul onayına bağlıdır (K-38 madde 2; hukuki görüş değildir). A16 hazır metin dalı metni `taslak` olarak içe alır.
- **Bitti sayılır:** karar defterinde yol kararı var; `mutalaa.toml` ve aday kaydı kararla uyumlu; A16 ve A37 için hangi dalın geçerli olduğu ilerleme notunda yazılı.

## Kabul ölçütleri
- [ ] `data/raw/elmalili-1935/` altında taramalar ve `fetch.json` (SHA-256'larla) var; `data/raw` yalnız `ingest scans` ile yazıldı.
- [ ] Yazı türü kararı ve OCR yöntemi kararı karar defterinde; tarama kaynağı ve şartı `elmalili-*.toml` içinde; `sources check` 0.
- [ ] `data/gold/elmalili-ocr/altin/` 40 sayfa içeriyor; iki yazan arasındaki uyum raporda.
- [ ] En az iki motorun 40 sayfalık çıktısı ve çalıştırma manifesti var.
- [ ] `ocr eval` raporu motor × sayfa türü CER, WER ve alt ölçüleri taşıyor.
- [ ] `uv run pytest` yeşil; ölçüm kodunun birim testleri dahil.
- [ ] Görsel model kullanıldıysa çağrı kayıtlarında model, istem özeti, token ve maliyet var; günlüklerde metin yok; `embed_ok = false` bir kaynak için çağrı yok (G-YZ).
- [ ] `pipeline/mutalaa.toml` içindeki `ocr_motoru` kararla aynı.
- [ ] Hazır metin adaylarının `bekliyor` kaydı var; Vikikaynak revizyon numarası (`oldid`) ve her dosyanın SHA-256'sı kayıtta; `sources check` 0.
- [ ] archive.org ofset sınaması tablosu ve sonucu raporda (HathiTrust 1935 sayfa numaralarıyla karşılaştırma).
- [ ] Hazır metin için meal bloklarında CER, sadeleştirme izi sayısı ve tam metin denetimi sonucu raporda; hazır metin `ocr eval` tablosunda bir satır olarak yer alıyor.
- [ ] Yol kararı (hazır metin mi OCR mı) karar defterinde; hazır metin yolu yalnız eşik geçildiyse seçildi, aksi hâlde OCR yolu yazıldı.
- [ ] Hiçbir aday `serbest` yapılmadı, pakete ya da `public`/`internal` derlemeye alınmadı; kalıcı hazır metin okuyucuları ve `ingest register` bu aşamada eklenmedi (yalnız `qa/` altındaki ölçüm okuyucusu var).

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
ls data/raw/elmalili-1935/ data/ocr/elmalili-1935/ data/gold/elmalili-ocr/altin/ | head -50
ls data/gold/elmalili-ocr/altin/ | wc -l                      # 40
(cd pipeline && uv run mutalaa ocr eval --edition elmalili-1935 --gold data/gold/elmalili-ocr/)
(cd pipeline && uv run pytest && uv run ruff check . && uv run mypy src)
grep -n "ocr_motoru" pipeline/mutalaa.toml
grep -rn "embed_ok" pipeline/sources/elmalili-meal.toml pipeline/sources/elmalili-tefsir.toml
grep -n "license_status" pipeline/sources/elmalili-*hazir*.toml   # hepsi "bekliyor" (dosya adları öneri)
```

## Dikkat
- İçerik etiği: Claude Code OCR çıktısını hafızadan düzeltmez, `⟦?⟧` yerini tahminle doldurmaz, altın metni yazmaz ve meal metni üretmez. Sadeleştirilmiş baskılar (GitHub `elmalili-meal/kuran`, Azim) ve ticari kullanımı kapatan kaynaklar (Tanzil, Açık Kuran) aday olamaz (§1, K-03, K-38). Başkasının hazır aktarımı ise kontrollü yolla değerlendirilir: `bekliyor` olarak kaydedilir, revizyon ve SHA-256 ile kilitlenir, yalnız ölçülür; kullanılmasına ancak eşik geçilirse ve tam metin denetimi temiz çıkarsa karar verilir (A09.6–A09.9). Hazır metin `serbest` sayılmaz ve ölçüm dışı hiçbir yere kopyalanmaz. Ayrıntı: `metin-butunlugu`, `lisans-kapisi`.
- Ofset sınamasında HathiTrust'tan görüntü alınmaz (1935 baskısı yalnız arama); yalnız sayfa numarası bilgisi kullanılır. Aday dosyalar elle indirilir (İ-29); Claude Code toplu indirme yapmaz.
- Yapay zekâ çıktısı ham okumadır: `dogrulanmis = false` taşır ve insan onayı olmadan hiçbir pakete doğrulanmış girmez (İçerik hattı §10, K-25). Yapay zekâ ile meal ya da tefsir çevirisi üretilmez.
- `data/raw` değişmezdir; Write ve Edit araçları oraya yazamaz. Ham tarama değiştirilmez ve küçültülmez. Ayrıntı: `icerik-hatti`.
- API anahtarı `pipeline/.env` içindedir; Claude Code okumaz. Bütçe onayı kullanıcıdadır (İ-17).
- Altın metin ve tarama kaydı insan emeğidir: `data/gold/` git dışıdır ve yedeklenir; `data/ocr/` yeniden üretilir (Proje yapısı §1.1; yedek betiği Yerel geliştirme §9).
- Komut biçimi: `ingest scans` `--cilt` alır; `ocr run --pages` cilt niteliklidir (`c01:1-40`; İçerik hattı §4, Elmalılı hazırlığı §3–§4). OCR değerlendirmesi Faz 0'dadır (Elmalılı hazırlığı §2, Fazlar Faz 0).
- Windows: TIFF dosyaları büyüktür; OneDrive kotası ve eşitleme A00'daki karara göre izlenir. Ayrıntı: `windows-sorun`.

## İnsan adımları
Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- İ-09 · Elmalılı özgün baskısının tarama nüshası: A09.1'den önce gerekir. Görsel kaynağı önce archive.org taraması (A09.7 ofset sınamasından geçerse); geçmezse yedek, sahaf takımı.
- İ-10 · OCR altın örneklemini iki kişinin bağımsız yazması ve farkları çözmesi (40 sayfa): A09.2'de; A09.4 ve A09.8'den önce gerekir. Aynı altın metin hazır metin adaylarının ölçümünde de kullanılır.
- İ-29 · Hazır metin adaylarını (Vikikaynak sayfası, archive.org dosyaları) elle indirip `data/gelen/` altına koymak: A09.6'dan önce gerekir.
- İ-17 · Anthropic API anahtarı ve bütçe: görsel model A09.3'te kullanılacaksa gerekir.
- İ-01'e ek: Tesseract gibi proje dışına kurulan OCR aracı gerekirse kullanıcı kurar.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/scans.py`, `enrich/ocr.py` (motor bağdaştırıcıları), `qa/` altında CER ve WER ölçümü; `ocr run`, `ocr eval`, `llm estimate` komutları ve birim testleri (modül adları öneri)
- `pipeline/prompts/ocr/v1.md`; `pipeline/mutalaa.toml` güncellemesi; `pipeline/sources/elmalili-meal.toml` ve `elmalili-tefsir.toml` güncellemesi
- Hazır metin adayları için `bekliyor` kaynak kayıtları (`pipeline/sources/`, adlar öneri) ve ölçüme yetecek asgari okuyucu
- Pilot raporunda ofset sınaması tablosu, hazır metin CER ve tam metin denetimi sonucu
- Gerekirse `pipeline/ocr-kraken/` ayrı uv projesi
- Git dışı: `data/gelen/`, `data/raw/elmalili-1935/`, `data/gold/elmalili-ocr/`, `data/ocr/elmalili-1935/`, `data/llm-cache/`, `data/reports/`
- Karar defterinde yazı türü ve yol (OCR yöntemi ya da hazır metin) kararları; `/belge-esitle` ile Elmalılı hazırlığı güncellemesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A09-elmalili-ocr-pilotu.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A08](./A08-ci-is-akislari.md) · Sonraki: [A10](./A10-tanzil-alimi.md)
