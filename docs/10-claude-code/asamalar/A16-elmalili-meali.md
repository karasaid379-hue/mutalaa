# A16 · Elmalılı meali: OCR ya da hazır metin, düzeltme kuyruğu, iki düzeltme turu

> **Sürüm:** 1.2 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A09](./A09-elmalili-ocr-pilotu.md) · [A10](./A10-tanzil-alimi.md) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-09 · İ-11 · İ-17
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `sunucu-gelistirici` (görsel ucu ve şema eki gerekirse) · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan turları ayrıca
> **Başlat:** `/asama A16`

## Amaç
Elmalılı'nın özgün baskısından (baskı kimliği `elmalili-1935`) âyet meali, A09'daki yol kararına göre iki daldan biriyle hazırlanır (K-38): (a) hazır metin dalı: A09 pilotunda eşiği geçen kayıtlı hazır metin kalıcı olarak içe alınır; (b) OCR dalı: A09'da seçilen OCR yöntemiyle sayfalar okunur. İki dalda da meal âyetlere bölünür ve `meal:elmalili:{sure}:{ayet}` birimleri `taslak` olarak yüklenir. Claude Code araçları, kuyruğu ve QA kapılarını kurar; düzeltme ve onay iki insan turuyla yapılır. Onaylı meal `core` paketine girer. Yapay zekâ yalnız sayfa görselini okur; meal yazmaz, çevirmez, düzeltmez.

**Dal seçimi.** A09 yol kararına bakılır. Karar hazır metinse dal (a), OCR ya da karar yoksa dal (b) yürür. Hazır metin dalı yalnız A09 eşiği geçildiyse geçerlidir; aksi hâlde A16 OCR dalı (A16.1–A16.6) aynen sürer. Özgün baskı taraması iki dalda da gerekir (A16.1): örneklem ve Kurul'a sadakat kanıtı bundan gelir. Hazır metin dalı A16.1'i, A16.3'ün bölme ve çapa adımlarını (kaynak olarak OCR bölgeleri yerine içe alınan metin), A16.5 ve A16.6'yı paylaşır; A16.2 (OCR koşusu) ve A16.4 yerine A16.7–A16.9 uygulanır.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): tamamı (§3 baskı doğrulama, §4 OCR, §5 Yol A, §6 âyetlere bölme, §7 editör, §8 QA ve örneklem, §9 künye ve sürüm)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §5 veri soyu, §9 kapılar (G-HIZ, G-MET, G-INC, G-YZ, G-KUR), §10 yapay zekâ politikası, §11 maliyet, §12 yeniden üretilebilirlik
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.3 Elmalılı kartı, §4 kullanılmayacak kaynaklar
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §1 meal çapası, §7 kendi metnimizin ilk kaydı
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §4 `unit` ve `metin_durumu`, §8 `review` ve ikinci onay, §9.1 `page_map`
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §7.3 değişiklik yönetimi
- A09'un çıktıları: yol kararı ve OCR yöntemi kararı (karar defteri), altın örneklem (`data/gold/elmalili-ocr/`), hazır metin adayının `bekliyor` kaydı, revizyon numarası ve SHA-256'sı, pilot raporu
- [Karar defteri](../../00-ozet/02-karar-defteri.md): [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 2–4 (hazır metin eşiği, çıkarılmış metin, `taslak` başlangıç durumu)

## Kapsam
**Yapılır**
- Tarama envanteri ve baskı doğrulaması (iki dalda da).
- Dal (b), OCR: bütün meal sayfalarının OCR'ı.
- Dal (a), hazır metin: kayıtlı hazır metnin kalıcı içe aktarımı (HTML, EPUB ve PDF okuyucuları, `ingest register` komutu, çıkarılmış metin için ortak test vektörü; hepsi planlıdır, henüz yoktur), `taslak` girişi, iki düzeltme turu ve özgün baskı görseliyle karşılaştırma.
- `ayet_ar` bloğunun Tanzil'e eşlenmesi, mealin âyetlere bölünmesi, sınır durumu kararları, `meal:elmalili` birimleri.
- İnceleme kuyruğu; tur 1 ve tur 2 için araç ve ölçüm; G-HIZ, G-MET, G-INC, G-YZ ve G-KUR kapıları; baskı sayfa eşlemesi; `core` yeniden yayını (`dev`).

**Yapılmaz**
- Tefsir metni (`tf:elmalili`; A37). Tefsir bölgelerinin OCR çıktısı `data/ocr` içinde bekler.
- İktibas ve atıf tespiti (A18). Kelime anlamları (A17). Sürüm dondurma ve Kurul başvurusu (A34).
- Yapay zekâ ile meal üretimi ya da metin düzeltmesi: yasaktır.

## Adımlar
### A16.1 · Tarama envanteri ve baskı doğrulaması
- İ-09 tamamlanmadan başlamaz. Kullanıcı taramaları A09'daki gibi proje içindeki `data/gelen/elmalili-1935/` klasörüne koyar; proje dışından okunmaz.
- Cilt başına, ör. `uv run mutalaa ingest scans --edition elmalili-1935 --dir data/gelen/elmalili-1935/c01 --cilt 1`. Dosya adı `c{cilt:02d}-s{sayfa:04d}.tif`; dosyalar SHA-256 ve `fetch.json` ile `data/raw/elmalili-1935/{YYYY-MM-DD}/` altına kopyalanır. A09'da alınan pilot sayfalar yeniden alınmaz.
- Baskı doğrulama listesi ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §3): Claude Code cilt başına sayfa sayısını, toplamı (6.442, fihrist hariç) ve eksik ya da okunamayan sayfaları raporlar; künye ve baskı denetimini kullanıcı yapar.
- Tarama kaynağı ve kullanım şartı A09'da `elmalili-meal.toml` ve `elmalili-tefsir.toml` dosyalarının `baski_bilgisi` alanına yazıldı; yeni nüsha kullanılırsa aynı alan güncellenir. Görsellerin yapay zekâ servisine gönderilmesi bu şarta ve `embed_ok` değerine bağlıdır.
- `page_map.source_id` birimin kaynağıdır (`elmalili-meal`); baskı kimliği `elmalili-1935` bu kaynağın `baski_bilgisi` alanında kalır, cilt `volume` sütunundadır. Ayrı `tur = 'baski'` kaydı gerekmez (Editoryal veritabanı §9.1, Elmalılı hazırlığı §6).
- **Bitti sayılır:** envanter raporu ve eksik sayfa listesi hazır.

### A16.2 · OCR koşusu (dal (b))
- Hazır metin dalında (a) bu adım atlanır; A16.7 uygulanır.
- Motor ve istem A09'un kararıdır (`pipeline/mutalaa.toml` içinde `[baski.elmalili-1935] ocr_motoru`). Tam koşudan önce pilotta ölçülen sayfa başı maliyetle tahmin hesaplanır ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §11) ve kullanıcı İ-17 bütçesine göre onaylar.
- `uv run mutalaa ocr run --edition elmalili-1935 --engine <A09 seçimi> --pages <cilt:aralık>` cilt cilt koşar. Çıktı `data/ocr/elmalili-1935/{run_id}/` altında sayfa başına bölge JSON'udur (`ayet_ar`, `meal`, `tefsir`, `dipnot`, `baslik`, `sayfa_no`). Yanıtlar `data/llm-cache/` altında `(model, prompt_sha256, input_sha256)` anahtarıyla saklanır; yeniden üretim yalnız `--regenerate` ile.
- İstem ilkeleri §4'tekilerdir: metin aynen, modernleştirme ve düzeltme yok, okunamayan karakter `⟦?⟧`, sıcaklık 0.
- Yol A seçildiyse §5 aktarım kılavuzu ve imlâ sözlüğü uygulanır (sözlük yolu modül düzenine göre: `pipeline/src/mutalaa_pipeline/normalize/elmalili_imla.tsv`). Yol B'de metin baskıdaki imlâsıyla kalır; açık dizgi hataları ayrı tashih katmanında tutulur.
- **Bitti sayılır:** bütün meal sayfalarının OCR çıktısı var; her çağrı model, istem özeti, girdi özeti, token ve maliyetle günlükte.

### A16.3 · Âyetlere bölme ve birimler
- §6 akışı: `ayet_ar` bloğu Arapça normalize edilip Tanzil'e eşlenir ve kapsanan aralık bulunur; meal bloğu âyet işaretlerine göre bölünür. İşaret yoksa cümle sınırı ve âyet sayısıyla bölme önerisi üretilir ve kuyruğa düşer.
- Sınır durumları (§6, Açık soru): birleşik meal (`kapsam`, `birlesik_ile`), besmele meali, numaralandırma farkı (`versification_map`), parantez ve dipnot. Veri modeli planda önerilir ve `/karar` ile yazılır. Öznitelikler editoryal `unit.attrs` sütununda tutulur (Editoryal veritabanı §4).
- Birim: `meal:elmalili:{s}:{a}`, `kind = 'meal'`, metin ilk kayıtta NFC ve [Çapa şeması](../../03-veri/01-capa-semasi.md) §7 adımları, `content_hash`, `metin_durumu = 'taslak'`, `ayah_range`, `attrs` (cilt, sayfa, bölge kutusu; §6), `provenance` (OCR çalıştırması). Her birime `review` satırı (`hedef_tablo = 'unit'`, `alan = 'metin'`).
- Türkçe arama anahtarları A05 normalleştiricisiyle üretilir. Baskı sayfa eşlemesi `page_map` tablosuna `source_id = 'elmalili-meal'` ve cilt (`volume`) ile yazılır (Elmalılı hazırlığı §6).
- Komutlar: `normalize`, `anchor`, `qa run`, `export pg` (`--source elmalili-meal`).
- **Bitti sayılır:** 6.236 âyetin her biri bir meal birimine ya da `birlesik_ile` bağına sahip ya da kuyrukta işaretli.

### A16.4 · Kuyruk ve tur 1 (İ-11; dal (b))
- Hazır metin dalında (a) tur 1 A16.9'dadır.
- Kuyruk A15'in `kuyruk/ocr` rotasıdır (görev adı öneri: `uv run mutalaa export review-queue --task ocr`). Görsel ucu A14.4'te karara bağlanmadıysa bu adımda `sunucu-gelistirici` ile kapanır.
- ~~G-YZ alanları (`ai_model`, `prompt_id`, `prompt_sha256`, `input_sha256`, `dogrulanmis`, `review_id`) editoryal DDL'de sütun olarak yoktur (Açık soru). A16 ve A17'den önce çalışanı yerlerini `/karar` ile belirler (öneri: `unit.provenance` ve `review.onerilen` içinde ya da EF göçüyle ek sütun).~~ Çözüldü (26 Ekim 2026, [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)): OCR'da görsel model kullanıldıysa alanlar birimin `review` satırındadır. `ai_model` → `review.yz_modeli`; `prompt_id`, `prompt_sha256` ve `input_sha256` → `review.yz_kaydi` (kısıt `review_yz_kaydi_check`); `review_id` → `review.id`; `created_at` → `review.created_at`. `dogrulanmis` saklanmaz; birimin `metin_durumu = 'onayli'` olmasından türetilir ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §8; BÇ-05). Göç A07'dedir; burada yalnız hat bu sütunları doldurur.
- Tur 1 (insan): her birim düzeltilir ve onaylanır. Dört göz kuralı geçerlidir: düzelten ve onaylayan farklıdır; meal metni ikinci onay alanıdır. Claude Code kuyruk sayılarını ve hata desenlerini raporlar, metni kendisi düzeltmez.
- Bekleme noktası: `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır, Not sütununa "İ-11 tur 1 bekleniyor" yazar ve durum bloğundaki bekleyen insan adımlarını günceller. Tur bitince aşama `/asama A16` ile sürer.
- **Bitti sayılır:** `meal:elmalili` birimlerinin tamamı `onayli`; açık `review` kaydı 0.

### A16.5 · Tur 2 ve QA kapıları (İ-11)
- Dokümanlar "iki düzeltme turu" der ama ikinci turun kapsamını tanımlamaz; planda proje sahibine sorulur. Öneri: §8'deki ikinci okuma. Örneklem en az 600 âyettir, cilt ve sureye göre tabakalıdır, sabit tohumla seçilir; ikinci kişi görselle karşılaştırır.
- Ölçüm: hatalı âyet oranı; hiç hata yoksa %95 üst sınır yaklaşık `3 / n`; hedef < %0,5 (öneri). Hata bulunursa desen düzeltilir, ilgili bölümler taranır, yeni örneklem çekilir.
- Kapılar: G-HIZ (%100), G-MET (CER eşiği, imlâ sözlüğü çakışması 0, kalan `⟦?⟧` 0), G-INC (bütün birimler `onayli`, ikinci okuma eşiğin altında), G-YZ, G-KUR (Kurul kapsamındaki metin değiştiyse işaret) ve sadeleştirme denetimi (örneklemde modernleştirilmiş kelime 0).
- **Bitti sayılır:** QA ve ikinci okuma raporları `data/reports/` altında; kapılar "geçti".

### A16.6 · Yeniden yayın
- `publish --flavor dev`: `core` mealle yeniden yayımlanır; `attribution` Elmalılı atıf metnini ve aktarım sürümünü taşır ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §9).
- Veri seti `elmalili-meal` anlamsal sürüm taşır; 1.0.0 ilk onaylı sürümdür. Dondurma ve Kurul başvurusu A34'tedir.
- **Bitti sayılır:** `dev` manifestinde yeni `core` sürümü; `verify --flavor dev` 0.

### A16.7 · Hazır metin dalı: kalıcı içe aktarım (yalnız dal (a); K-38)
- Önkoşul: A09 yol kararı hazır metin; aday kaydı `bekliyor`, revizyon numarası ve SHA-256 kilitli. Dosya `data/gelen/` altına kullanıcı tarafından konmuştur (İ-29); Claude Code toplu indirme yapmaz.
- Hat, kayıtlı dosyayı `ingest register` (komut adı öneri; henüz yoktur) ile `data/raw` altına alır: SHA-256 ve `fetch.json`, dosya değişmez. Kayıtsız ve özeti uyuşmayan dosya işlenmez.
- Biçim okuyucuları (HTML, EPUB, metin katmanlı PDF; yalnız kayıtlı adayın biçimi için gerekenler) deterministiktir ve çıkarıcı sürümü sabittir. Çıkarılmış metin kaynak dosyanın birebir dilimi değildir; üçüncü bir kanonik metin türüdür (K-38 madde 3; K-26'ya ek). Dönüşüm `shared/test-vectors/` altında ortak vektörle üç dilde tanımlanır; vektör sentetik ya da lisansı izin veren parçalarla yazılır. Gerçek meal metni vektöre hafızadan girmez.
- İlk kayıt adımları (K-35) uygulanır; NFC yalnız burada ve yalnız bizim ürettiğimiz çıkarılmış metne uygulanır. `provenance` dosya özetini, dosya içi konumu ve çıkarıcı sürümünü taşır. G-BUT denetimi bu tür için "ham dosya ve çıkarıcıdan metin yeniden üretilebilir" olur.
- Sadeleştirme taraması ve 6.236 âyet kapsamı denetimi otomatik çalışır; sonuç `data/reports/` altına yazılır. Claude Code metni düzeltmez.
- **Bitti sayılır:** çıkarılmış metin ham dosyadan yeniden üretiliyor (aynı girdi, aynı çıktı); vektör testleri yeşil; kapsam ve sadeleştirme raporu hazır.

### A16.8 · Hazır metin dalı: `taslak` girişi ve bölme (yalnız dal (a); K-38)
- Çıkarılmış metin A16.3'teki biçimde âyetlere bölünür ve `meal:elmalili:{s}:{a}` birimleri olarak girer. Hazır metnin âyet işaretleri varsa kullanılır; yoksa A16.3 bölme önerisi kuyruğa düşer. Sınır durumları (birleşik meal, besmele) A16.3'tekiyle aynı kararlara bağlanır.
- Başlangıç durumu `metin_durumu = 'taslak'`'tır; `onayli` ile giriş yalnız Tanzil gibi kanonik başvuru kaynakları içindir (K-38 madde 4). Meal ve tefsirde ikinci onay geçerlidir. Böylece P-10 editör onaysız hazır metni `public` derlemeye sokmaz (BÇ-43).
- Kaynak kaydı `bekliyor` kalır; hazır metinden gelen birimler `serbest` olmadan `public` ve `internal` derlemeye girmez (K-06).
- `page_map` kaydı özgün baskı görselinden (A16.1) yapılır; hazır metin sayfa bilgisi taşımaz ya da güvenilmezse sayfa eşlemesi baskıdan elle doğrulanır.
- **Bitti sayılır:** 6.236 âyetin her biri bir meal birimine ya da `birlesik_ile` bağına sahip ya da kuyrukta işaretli; hepsi `taslak`.

### A16.9 · Hazır metin dalı: iki düzeltme turu ve görselle karşılaştırma (İ-11; yalnız dal (a); K-38)
- Tur 1 (insan): her birim özgün baskı görseliyle karşılaştırılır, düzeltilir ve onaylanır. Dört göz kuralı geçerlidir. Düzeltme çapayı değiştirmez; `content_hash` ve `rev` değişir. Kuyruk A15'in rotasıdır ve OCR dalıyla ortaktır; görev adı öneridir.
- Tur 2: A16.5'teki ikinci okuma (en az 600 âyet, tabakalı, sabit tohum); ikinci kişi görselle karşılaştırır. Hazır metnin sistematik hatası (sadeleştirme, baskı farkı) bulunursa desen düzeltilir, ilgili bölümler taranır ve yeni örneklem çekilir.
- Atıf metni "X kaynağından alınmış, Mütâlaa tarafından özgün baskıyla karşılaştırılıp düzeltilmiştir" biçimindedir ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §9). `serbest` ve Kurul başvurusu avukat görüşüne ve Kurul onayına bağlıdır (hukuki görüş değildir).
- Bekleme noktası A16.4'tekiyle aynıdır (İ-11 tur 1, tur 2 ilerleme dosyasına yazılır).
- **Bitti sayılır:** birimlerin tamamı `onayli`; açık `review` kaydı 0; QA ve ikinci okuma raporları hazır (A16.5 ölçütleri).

## Kabul ölçütleri
- [ ] Tarama envanteri cilt başına sayfa sayısını, toplamı ve eksik sayfaları gösteriyor; künye denetimi kullanıcı tarafından işaretli.
- [ ] Her meal sayfasının OCR çıktısı var; yapay zekâ çağrıları model, istem özeti ve maliyetle kayıtlı; `embed_ok = false` kaynağa gönderim yok (G-YZ geçti).
- [ ] G-HIZ: 6.236 âyetin her birinde meal birimi ya da `birlesik_ile` bağı var.
- [ ] Sınır durumları karar defterinde. G-YZ alanlarının yeri [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) ile yazıldı (26 Ekim 2026).
- [ ] Tur 1 sonrası `elmalili-meal` birimlerinin tamamı `onayli`; `unit` hedefli açık `review` kaydı 0 (SQL).
- [ ] Tur 2 örneklemi en az 600 âyet; üst sınır raporda; G-MET ve G-INC "geçti".
- [ ] `metin-denetcisi` raporu: NFC yalnız ilk kayıtta, Tanzil metnine dokunulmamış, sadeleştirme yok.
- [ ] `verify --flavor dev` 0 ve `core` paketinde meal birimleri var.
- [ ] Hazır metin dalı seçildiyse (A09 eşiği geçildiyse): çıkarılmış metin ham dosyadan yeniden üretiliyor; ortak test vektörü üç dilde yeşil; birimler `taslak` girdi ve ikinci onaydan geçti; sadeleştirme taraması ve kapsam raporu temiz; atıf metni "karşılaştırılıp düzeltilmiştir" biçiminde; kaynak kaydı `serbest` olmadan `public`/`internal` derlemede hazır metin birimi yok.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
(cd pipeline && uv run mutalaa qa run --source elmalili-meal --gate G-HIZ)
(cd pipeline && uv run mutalaa qa run --source elmalili-meal)
(cd pipeline && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT metin_durumu, count(*) FROM icerik.unit WHERE source_id = 'elmalili-meal' GROUP BY 1;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'unit' AND durum = 'acik';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev
```

## Dikkat
- Yapay zekâ meal yazmaz, çevirmez ve düzeltmez; yalnız sayfa görselini okur. Düzeltme insanındır (K-25; [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §10).
- Sadeleştirilmiş baskılar (GitHub `elmalili-meal/kuran`, Azim) ve ticari kullanımı kapatan kaynaklar (Tanzil, Açık Kuran) kullanılmaz (lisans defteri §4, K-38). Başka aktarımlar yalnız kontrollü yolla girer: A09'da `bekliyor` kaydı ve kilit, pilotta eşik, sonra `taslak` giriş ve özgün baskıyla karşılaştırma; bu yoldan geçmeyen aktarım kopyalanmaz. Hazır metin hafızadan tamamlanmaz ya da "düzeltilmez"; düzeltmeyi insan yapar.
- Hazır metin dalı yalnız A09 eşiği geçildiyse geçerlidir. Çıkarılmış metin üçüncü bir kanonik türdür (K-38 madde 3): ham dosya `data/raw` altında değişmez, çıkarıcı sürümü sabittir.
- Meal kendi ürettiğimiz metindir: NFC ilk kayıtta yapılır; düzeltme çapayı değiştirmez, `content_hash` ve `rev` değişir.
- Meal Kurul kapsamındadır; onaydan sonraki her düzeltme yeniden onay gerektirebilir (G-KUR). Düzeltme turları başvurudan önce kapanır.
- Günlüklere metin yazılmaz. Maliyet İ-17 bütçesini aşacaksa koşu durur ve kullanıcıya sorulur.
- Windows: tarama dosya adları ASCII; büyük ikili dosyalar git dışı `data/` altındadır.

## İnsan adımları
- İ-09 · Tarama nüshası: A16.1'den önce gerekir (iki dalda da).
- İ-17 · Anthropic API anahtarı ve bütçe: görsel OCR seçildiyse A16.2'den önce gerekir (dal (b)).
- İ-11 · Düzeltme turları: OCR dalında tur 1 A16.4'te, tur 2 A16.5'te; hazır metin dalında tur 1 ve 2 A16.9'da. Her bekleme noktası ilerleme dosyasına yazılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/` tarama kaydı, `enrich/` OCR ve bölme modülleri, `qa/checks/elmalili.py`, testler; Yol A ise imlâ sözlüğü
- Hazır metin dalında ek olarak (planlı, adlar öneri): `ingest register` komutu, HTML/EPUB/PDF okuyucuları, çıkarılmış metin test vektörü (`shared/test-vectors/`)
- `data/raw/elmalili-1935/`, `data/ocr/`, `data/llm-cache/`, `data/reports/` (git dışı)
- PostgreSQL'de `meal:elmalili` birimleri, `review` kayıtları, `page_map` satırları
- Karar defterinde sınır durumları ve ikinci tur tanımı (G-YZ alanları K-37'de); `dev` kanalında yeni `core`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A16-elmalili-meali.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A15](./A15-editor-paneli.md) · Sonraki: [A17](./A17-kelime-katmani.md)
