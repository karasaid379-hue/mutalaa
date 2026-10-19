# A09 · Elmalılı OCR pilotu ve yöntem seçimi

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · [A06](./A06-lisans-defteri-ve-enumlar.md) · **İnsan adımı:** [İ-09, İ-10, İ-17](../06-insan-adimlari.md)
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `lisans-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `lisans-kapisi` · **Tahmini oturum:** 2–4 (insan beklemesi hariç)
> **Başlat:** `/asama A09`

## Amaç
Elmalılı'nın özgün baskısı (baskı kimliği `elmalili-1935`) için iki belirsizlik ölçümle kapanır: baskının yazı türü (K-03 düzeltmesi: Türkçe metin büyük olasılıkla Latin harfli, âyetler Arapça harfli; Doğrulanacak) ve OCR yöntemi. En az iki OCR motoru 40 sayfalık tabakalı örneklemde çalışır; insan yazımı altın metne karşı CER ve WER ölçülür, maliyet tahmin edilir ve seçim `/karar` ile yazılır. Faz 0 çıkış ölçütü "OCR yöntemi ölçümle seçildi ve yazıldı" bu aşamayla sağlanır. Meal aktarımı ve düzeltme turları A16'dadır.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §1 hukuki çerçeve, §3 kaynak baskı ve tarama standardı, §4 OCR ve değerlendirme, §5 (yalnız Yol A çıkarsa), §8 QA ölçütleri, §11 açık sorular
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §3 `mutalaa.toml` ve Kraken notu, §4 komutlar, §5 veri soyu, §7 günlük, §10 yapay zekâ politikası, §11 maliyet, §12 çalıştırma manifesti
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.3 (`elmalili-meal`, `elmalili-tefsir`), §7 kontrol listesi
- [Karar defteri](../../00-ozet/02-karar-defteri.md): K-03 ve 18 Ekim 2026 düzeltmesi
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.4 (OCR adayları)

## Kapsam
**Yapılır**
- `uv run mutalaa ingest scans` komutu ve taramaların `data/raw` altına kaydı; tarama kaynağının kullanım şartının kaynak kaydına işlenmesi.
- Yazı türünün tarama üzerinde doğrulanması; baskı doğrulama listesinin eldeki nüsha için doldurulması.
- 40 sayfalık örneklem ve altın metin için karşılaştırma aracı (altın metni insanlar yazar, İ-10).
- `ocr run` (en az iki motor), `ocr eval` (CER, WER ve alt ölçüler), görsel model için `llm estimate`.
- Pilot raporu, yöntem kararı ve `pipeline/mutalaa.toml` güncellemesi.

**Yapılmaz**
- Meal bloklarının âyetlere bölünmesi, Tanzil eşleştirmesi, inceleme kuyruğu, G-MET ve G-HIZ kapıları, 6.442 sayfanın tamamının OCR'ı (A16).
- Tefsir metni (A37). Latin harfine aktarım kılavuzunun uygulanması (A16; Yol A çıkarsa bu aşamada yalnız aktarım doğruluğu ölçülür).
- Editör panelindeki OCR kuyruğu (A15).

## Adımlar
### A09.1 · Taramalar, kaynak şartı ve yazı türü (İ-09)
- İ-09 henüz yoksa `arastirmaci` §3'teki aday koleksiyonlarda (Millî Kütüphane, İSAM, Diyanet ve ilahiyat kütüphaneleri, Internet Archive, HathiTrust, Vikikaynak) tarama arar ve kullanım şartıyla listeler (hepsi Doğrulanacak); seçim kullanıcınındır.
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
- **Bitti sayılır:** karar defterinde yeni karar var; `mutalaa.toml` kararla aynı.

## Kabul ölçütleri
- [ ] `data/raw/elmalili-1935/` altında taramalar ve `fetch.json` (SHA-256'larla) var; `data/raw` yalnız `ingest scans` ile yazıldı.
- [ ] Yazı türü kararı ve OCR yöntemi kararı karar defterinde; tarama kaynağı ve şartı `elmalili-*.toml` içinde; `sources check` 0.
- [ ] `data/gold/elmalili-ocr/altin/` 40 sayfa içeriyor; iki yazan arasındaki uyum raporda.
- [ ] En az iki motorun 40 sayfalık çıktısı ve çalıştırma manifesti var.
- [ ] `ocr eval` raporu motor × sayfa türü CER, WER ve alt ölçüleri taşıyor.
- [ ] `uv run pytest` yeşil; ölçüm kodunun birim testleri dahil.
- [ ] Görsel model kullanıldıysa çağrı kayıtlarında model, istem özeti, token ve maliyet var; günlüklerde metin yok; `embed_ok = false` bir kaynak için çağrı yok (G-YZ).
- [ ] `pipeline/mutalaa.toml` içindeki `ocr_motoru` kararla aynı.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
ls data/raw/elmalili-1935/ data/ocr/elmalili-1935/ data/gold/elmalili-ocr/altin/ | head -50
ls data/gold/elmalili-ocr/altin/ | wc -l                      # 40
(cd pipeline && uv run mutalaa ocr eval --edition elmalili-1935 --gold data/gold/elmalili-ocr/)
(cd pipeline && uv run pytest && uv run ruff check . && uv run mypy src)
grep -n "ocr_motoru" pipeline/mutalaa.toml
grep -rn "embed_ok" pipeline/sources/elmalili-meal.toml pipeline/sources/elmalili-tefsir.toml
```

## Dikkat
- İçerik etiği: Claude Code OCR çıktısını hafızadan düzeltmez, `⟦?⟧` yerini tahminle doldurmaz, altın metni yazmaz ve meal metni üretmez. Sadeleştirilmiş baskılar ve başkalarının aktarımları kullanılmaz (§1, K-03). Ayrıntı: `metin-butunlugu`.
- Yapay zekâ çıktısı ham okumadır: `dogrulanmis = false` taşır ve insan onayı olmadan hiçbir pakete doğrulanmış girmez (İçerik hattı §10, K-25). Yapay zekâ ile meal ya da tefsir çevirisi üretilmez.
- `data/raw` değişmezdir; Write ve Edit araçları oraya yazamaz. Ham tarama değiştirilmez ve küçültülmez. Ayrıntı: `icerik-hatti`.
- API anahtarı `pipeline/.env` içindedir; Claude Code okumaz. Bütçe onayı kullanıcıdadır (İ-17).
- Altın metin ve tarama kaydı insan emeğidir: `data/gold/` git dışıdır ve yedeklenir; `data/ocr/` yeniden üretilir (Proje yapısı §1.1; yedek betiği Yerel geliştirme §9).
- Komut biçimi: `ingest scans` `--cilt` alır; `ocr run --pages` cilt niteliklidir (`c01:1-40`; İçerik hattı §4, Elmalılı hazırlığı §3–§4). OCR değerlendirmesi Faz 0'dadır (Elmalılı hazırlığı §2, Fazlar Faz 0).
- Windows: TIFF dosyaları büyüktür; OneDrive kotası ve eşitleme A00'daki karara göre izlenir. Ayrıntı: `windows-sorun`.

## İnsan adımları
Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- İ-09 · Elmalılı özgün baskısının tarama nüshası: A09.1'den önce gerekir.
- İ-10 · OCR altın örneklemini iki kişinin bağımsız yazması ve farkları çözmesi: A09.2'de; A09.4'ten önce gerekir.
- İ-17 · Anthropic API anahtarı ve bütçe: görsel model A09.3'te kullanılacaksa gerekir.
- İ-01'e ek: Tesseract gibi proje dışına kurulan OCR aracı gerekirse kullanıcı kurar.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/scans.py`, `enrich/ocr.py` (motor bağdaştırıcıları), `qa/` altında CER ve WER ölçümü; `ocr run`, `ocr eval`, `llm estimate` komutları ve birim testleri (modül adları öneri)
- `pipeline/prompts/ocr/v1.md`; `pipeline/mutalaa.toml` güncellemesi; `pipeline/sources/elmalili-meal.toml` ve `elmalili-tefsir.toml` güncellemesi
- Gerekirse `pipeline/ocr-kraken/` ayrı uv projesi
- Git dışı: `data/gelen/`, `data/raw/elmalili-1935/`, `data/gold/elmalili-ocr/`, `data/ocr/elmalili-1935/`, `data/llm-cache/`, `data/reports/`
- Karar defterinde yazı türü ve OCR yöntemi kararları; `/belge-esitle` ile Elmalılı hazırlığı güncellemesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A09-elmalili-ocr-pilotu.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A08](./A08-ci-is-akislari.md) · Sonraki: [A10](./A10-tanzil-alimi.md)
