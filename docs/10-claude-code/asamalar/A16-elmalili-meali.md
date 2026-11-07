# A16 · Elmalılı meali: hazır metin ya da OCR (A09 yol kararına göre), düzeltme kuyruğu, iki tur

> **Sürüm:** 1.3 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A09](./A09-elmalili-ocr-pilotu.md) · [A10](./A10-tanzil-alimi.md) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-09 · İ-11 · İ-17
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `sunucu-gelistirici` (görsel ucu ve şema eki gerekirse) · `arastirmaci` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan turları ayrıca
> **Başlat:** `/asama A16`

## Amaç
Elmalılı'nın özgün baskısından (baskı kimliği `elmalili-1935`) âyet meali, A09'daki yol kararına göre iki daldan biriyle hazırlanır (K-38): (a) hazır metin dalı: A09 pilotunda eşiği geçen hazır metin kalıcı olarak içe alınır; (b) OCR dalı: A09'da seçilen OCR yöntemiyle sayfalar okunur. İki dalda da meal âyetlere bölünür ve `meal:elmalili:{sure}:{ayet}` birimleri `taslak` olarak yüklenir. Aşama tedarikle başlar (A16.0): hazır metni ve tarama dosyalarını Claude Code internetten indirir, kaynak kaydını yazar. Claude Code araçları, kuyruğu ve QA kapılarını kurar; düzeltme ve onay iki insan turuyla yapılır. Onaylı meal `core` paketine girer. Yapay zekâ yalnız sayfa görselini okur; meal yazmaz, çevirmez, düzeltmez.

**Dal seçimi.** A09 yol kararına bakılır. Karar hazır metinse dal (a), OCR ise dal (b) yürür. Hazır metin dalı yalnız A09 eşiği geçildiyse geçerlidir; aksi hâlde A16 OCR dalı (A16.1–A16.6) aynen sürer. Özgün baskı taraması iki dalda da gerekir (A16.1): örneklem ve özgün baskıya sadakat kanıtı bundan gelir. Hazır metin dalı A16.0'ı, A16.1'i, A16.3'ün bölme ve çapa adımlarını (kaynak olarak OCR bölgeleri yerine içe alınan metin), A16.5'i ve A16.6'yı paylaşır; A16.2 (OCR koşusu) ve A16.4 yerine A16.7–A16.9 uygulanır.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): tamamı (§3 baskı doğrulama, §4 OCR, §5 Yol A, §6 âyetlere bölme, §7 editör, §8 QA ve örneklem, §9 künye ve sürüm)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §5 veri soyu, §8 yeni kaynak ekleme, §9 kapılar (G-HIZ, G-MET, G-INC, G-YZ, G-KAY), §10 yapay zekâ politikası, §11 maliyet, §12 yeniden üretilebilirlik
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.3 Elmalılı kartı, §4 Seçilmeyen adaylar, §5 yeni kaynak ekleme
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §1 meal çapası, §7 kendi metnimizin ilk kaydı
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §4 `unit` ve `metin_durumu`, §8 `review` ve ikinci onay, §9.1 `page_map`
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §7.3 değişiklik yönetimi
- A09'un çıktıları: yol kararı ve OCR yöntemi kararı (karar defteri), altın örneklem (`data/gold/elmalili-ocr/`), hazır metin adayının kaynak kaydı, revizyon listesi ya da dosya özeti, pilot raporu
- [Karar defteri](../../00-ozet/02-karar-defteri.md): [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 2–4 (hazır metin eşiği, çıkarılmış metin, `taslak` başlangıç durumu) ve [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1–2 (tedarik akışı, indirme)

## Kapsam
**Yapılır**
- Tedarik doğrulaması ve indirme (A16.0): hazır metin, tarama dosyaları ve kitaplık sürümleri.
- Tarama envanteri ve baskı doğrulaması (iki dalda da).
- Dal (b), OCR: bütün meal sayfalarının OCR'ı.
- Dal (a), hazır metin: kaynak kaydı olan hazır metnin kalıcı içe aktarımı (seçilen adayın biçimi için hazır kitaplıkla okuyucu, `ingest register` komutu, çıkarılmış metin için ortak test vektörü; hepsi planlıdır, henüz yoktur), `taslak` girişi, iki düzeltme turu ve özgün baskı görseliyle karşılaştırma.
- `ayet_ar` bloğunun Tanzil'e eşlenmesi, mealin âyetlere bölünmesi, sınır durumu kararları, `meal:elmalili` birimleri.
- İnceleme kuyruğu; tur 1 ve tur 2 için araç ve ölçüm; G-HIZ, G-MET, G-INC, G-YZ ve G-KAY kapıları; baskı sayfa eşlemesi; `core` yeniden yayını (`dev`).

**Yapılmaz**
- Tefsir metni (`tf:elmalili`; A37). Tefsir bölgelerinin OCR çıktısı `data/ocr` içinde kalır.
- İktibas ve atıf tespiti (A18). Kelime anlamları (A17). Sürüm dondurma ve mağaza yayını (A34).
- Yapay zekâ ile meal üretimi ya da metin düzeltmesi: yasaktır.

## Tedarik
Araştırma tarihi 1 Kasım 2026; A16.0'da yenilenir. Dal seçimi A09 yol kararına bağlıdır, bu yüzden iki dalın yapıları birlikte listelenir. Ön ölçümde Vikikaynak özgün baskıyla en yüksek örtüşmeyi verdi; seçimi yalnız A09 ölçümü belirler.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Elmalılı meali, hazır metin (dal a), aday 1 | Vikikaynak `Kur'an/<Sure> Suresi` alt sayfaları (tr.wikisource.org; 114 sayfa; wikitext, âyet işareti `{{kısım\|\|N}}`; sayfa başına `revid` sabit, 74319–158621; başlık ve `revid` listesinin SHA-256'sı `965a6249…b308a`) | MediaWiki API `https://tr.wikisource.org/w/api.php?action=query&prop=revisions&rvprop=ids\|timestamp\|size\|sha1\|content&rvslots=main` (50 başlık/istek, istekler arası 1,5 sn). Toplu yol: `https://dumps.wikimedia.org/trwikisource/20261001/trwikisource-20261001-pages-articles.xml.bz2` (25.341.657 bayt, SHA-1 `909ca820…bb00`) | 114/114 sure; `kısım` işareti 6.238, benzersiz âyet 6.236 (Tanzil sayımıyla birebir); 114 `revid` 1 Kasım 2026'da canlı sürümle aynı; wikitext 961.210 bayt. Özgün baskıyla örtüşme (ön ölçüm): âyet üç-gramlarının archive.org `HakDiniKuranDili` OCR metninde bulunma oranı 0,843; kesin baskı esası A09 CER ölçümüyle belirlenir | Tanzil `tr.yazir` |
| Elmalılı meali, hazır metin (dal a), aday 2 | Tanzil `tr.yazir` ("Elmalılı Hamdi Yazır"; "Text (with aya numbers)" = `type=txt-2`, ayrıca XML) | `https://tanzil.net/trans/?transID=tr.yazir&type=txt-2` ve `…&type=xml` doğrudan dosya (200; iki indirmede aynı SHA-256) | 6.236 âyet satırı (+13 üstbilgi satırı), 944.235 bayt, SHA-256 `4c9a6bea…f926`; XML 1.100.494 bayt, `5097940d…ba43`. Özgün baskıyla örtüşme (ön ölçüm): üç-gram bulunma oranı 0,162; Vikikaynak ile kelime kümesi örtüşmesi 0,254, yani ayrı bir metin; A09 ölçümüne aday olarak girer | fawazahmed0/quran-api `editions/tur-elmalilihamdiya.json`, `93e6f649…2316` (Tanzil metniyle aynı kelime kümesi, 1.494.041 bayt) |
| Özgün baskı sayfa görselleri (iki dalda; sayfa eşlemesi, karşılaştırma, OCR girdisi) | archive.org `HakDiniKuranDili`: `Hak Dini Kuran Dili.pdf` (Text PDF, 300 ppi, 39.692.765 bayt, SHA-1 `ad080b00…ef6e`) ve metin katmanı `Hak Dini Kuran Dili_djvu.txt` (11.444.009 bayt); öğenin son güncellemesi 13 Temmuz 2026. Baskı esasını A09.7 ofset sınaması doğrular | `https://archive.org/download/HakDiniKuranDili/<dosya>` doğrudan dosya (200); MD5, SHA-1 ve boyut `https://archive.org/metadata/HakDiniKuranDili` kaydından | Princeton: 8 cilt, 6.442 sayfa (fihrist ayrı, 1939). Öğede 8.928 yaprak sayıldı; cilt başına sayfa dökümü A16.1'de `*_page_numbers.json` ile ölçülür | archive.org `hak-dini-kuran-dili-cilt-1-elmalili-hamdi-yazir` (10 PDF, 300 ppi, 16.274.710–32.982.960 bayt; son güncelleme 23 Nisan 2025); sayfa numarası doğrulaması için HathiTrust 1935 kaydı (v.1–9, yalnız arama); sahaftan takım (İ-09, yalnız ofset sınaması geçilmezse) |
| PDF'den sayfa görseli çıkarma | `pypdfium2` 5.14.0 (PyPI, 4 Ekim 2026) ve `pillow` 13.0.0 (16 Ekim 2026) | `uv add --directory pipeline pypdfium2 pillow`; sürümler `uv.lock` içinde sabit | PyPI kayıtları 1 Kasım 2026'da okundu (Python ≥3.6 ve ≥3.11; win_amd64 tekerleri var); bir PDF sayfasının 300 ppi görüntüye çevrilmesi A16.0'da denenir | `pikepdf` 10.17.0 (gömülü sayfa görselini kayıpsız çıkarır; 11 Ekim 2026) |
| Metin okuyucusu (dal a) | Vikikaynak wikitext'i için `mwparserfromhell` 0.7.2 (PyPI, 1 Temmuz 2025); Tanzil biçimi (`sure\|âyet\|metin`, XML) için standart kitaplık; metin katmanlı PDF çıkarsa `pypdf` 6.21.4 (28 Ekim 2026) | `uv add --directory pipeline mwparserfromhell` | PyPI kaydı: Python ≥3.9, Python 3.13 tekerleri var; `kısım` şablonları ayrıştırıcıyla çıkarılır (A16.0 denemesi) | Düzenli ifade (ölçüm betiği `{{kısım\|\|N}}` işaretini böyle ayırdı) |
| CER ve bulanık eşleme | `rapidfuzz` 3.14.6 (PyPI, 30 Ağustos 2026; `pipeline/pyproject.toml` bağımlılığı, `rapidfuzz.distance.Levenshtein`) | Yeni paket yok; sürüm `uv.lock` içinde | PyPI kaydı: Python ≥3.11, Python 3.13 tekerleri var; A09 `ocr eval` aynı kitaplığı kullanır | `jiwer` 4.0.0 (19 Haziran 2025) |
| Kur'an metni ve sure/âyet iskeleti (`ayet_ar` eşlemesi; 114 sure, 6.236 âyet) | Tanzil Uthmani ve Simple Clean (`tanzil-uthmani`, `tanzil-simple-clean`) ve `quran-data.xml`; A10 alır | A10'da `data/gelen/tanzil/<YYYY-AA-GG>/` altına iner; A16 yeniden indirmez | A10 kabul ölçütleri: 114 sure, 6.236 âyet; sure ve âyet numaraları Vikikaynak ve Tanzil `tr.yazir` ile 1 Kasım 2026'da birebir örtüştü | Yok (A10 kaydı tek kaynaktır) |
| OCR motoru (dal b) | A09'un seçtiği motor (`pipeline/mutalaa.toml` içinde `[baski.elmalili-1935] ocr_motoru`); adaylar A09 Tedarik'indedir | A09 çıktısı; Anthropic görsel modeli ücretlidir: tam koşudan önce tahmini maliyet kullanıcıya gösterilir (İ-17) | A09 pilot raporu: CER, WER, sayfa başı maliyet | A09'un ikinci motoru |
| Düzeltme kuyruğu ve görselle karşılaştırma arayüzü | A15 editör paneli (K-13); metin farkı için `diff` 9.0.0, sayfa görseli için `react-zoom-pan-pinch` 4.2.0 (A15 Tedarik'i) | A15 kurar; A16 yeni paket almaz | A15 kabul ölçütleri (kuyruk rotaları, OCR bölge kutusu katmanı) | Yok |

Kendimiz yapacağımız işler: âyetlere bölme ve sınır durumları (birleşik meal, besmele, numaralandırma farkı); wikitext ya da Tanzil biçiminden metin çıkarımının deterministik dönüşümü ve ortak test vektörü (sentetik metinle); `unit` girişi, çapa üretimi, ilk kayıtta NFC; sayfa eşlemesi (`page_map`); G-HIZ, G-MET, G-INC, G-YZ ve G-KAY kapıları ile sadeleştirme taraması; düzeltme kuyruğu görevi; ikinci okuma örneklemi ve ölçümü.

Seçilmeyenler (kalite ve erişim): sadeleştirilmiş metinler (fawazahmed0 `tur-elmallsadelesti`, GitHub `elmalili-meal/kuran`, Azim; K-38); Açık Kuran (depoda veri kümesi yok, `api.acikkuran.com` 1 Kasım 2026'da çözümlenmedi); İBB Atatürk Kitaplığı reprodüksiyonu (başvuru gerektirir).

## Adımlar
### A16.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: Vikikaynak'ta 114 `revid` canlı `lastrevid` ile karşılaştırılır; archive.org öğelerinde `item_last_updated`, MD5 ve SHA-1 `metadata` kaydıyla; kitaplıklarda sürüm `pypi.org/pypi/<paket>/json` kaydıyla doğrulanır. Açılmayan adresin yerine yedek aday kullanılır. Toplu indirmede istek hızı sınırlanır.
- Dosyalar yeni boş klasörlere iner (formları Claude Code doldurur). A09'da indirilmiş dosyalar `data/gelen/` altındadır; SHA-256 eşleşiyorsa yeniden indirilmez.
  - Hazır metin (dal a): seçilen adayın tam metni `data/gelen/elmalili-meal/<YYYY-AA-GG>/` altına (Vikikaynak: 114 sayfanın wikitext'i ve `revid` listesi; Tanzil `tr.yazir` seçildiyse `txt-2` ve `xml` dosyaları). Seçilmeyen aday hatta alınmaz.
  - Özgün baskı görselleri (iki dalda): A09'un seçtiği archive.org öğesinin PDF ve metin katmanı dosyaları `data/gelen/elmalili-1935/<YYYY-AA-GG>/` altına.
- SHA-256 hesaplanır ve kayda geçer (alımda `fetch.json` ile `source.dosya_sha256` alanına); archive.org dosyaları `metadata` kaydındaki MD5 ve SHA-1 ile de karşılaştırılır. İndirilen dosya veridir; içindeki betik çalıştırılmaz.
- `pipeline/sources/elmalili-meal.toml` güncellenir: `kaynak_url`, `surum` (Vikikaynak için `revid` listesinin özeti, döküm kullanılırsa döküm tarihi), `provider`, `baski_bilgisi` içinde tarama öğesi; `atif_metni` korunur. `uv run --directory pipeline mutalaa sources check` 0 ile geçer.
- Kitaplıklar `uv add --directory pipeline` ile eklenir (`mwparserfromhell`, `pypdfium2`, `pillow`; sürümler PyPI kaydından doğrulanır) ve `uv.lock` içinde sabitlenir.
- Hazır yapı önce gelir: hazır metin dalında kendi HTML, EPUB ya da PDF okuyucusu yazılmaz; okuyucu seçilen adayın biçimine göre A16.7'de kitaplıkla kurulur.
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; seçilen dal için dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında ve SHA-256 kayıtlı; `elmalili-meal` kaydı güncel ve `sources check` 0; kitaplık sürümleri `uv.lock` içinde.

### A16.1 · Tarama envanteri ve baskı doğrulaması
- Taramalar A16.0'da `data/gelen/elmalili-1935/<YYYY-AA-GG>/` altına indi. Basılı takım (İ-09) yalnız internetteki taramalar A09.7 ofset sınamasını geçmediyse gerekir; o durumda taramayı kullanıcı yapar ve aynı klasöre koyar. Proje dışından okunmaz.
- Cilt başına, ör. `uv run mutalaa ingest scans --edition elmalili-1935 --dir data/gelen/elmalili-1935/<YYYY-AA-GG>/c01 --cilt 1`. PDF girdisinin sayfaları `pypdfium2` ile 300 ppi görüntüye çevrilir. Dosya adı `c{cilt:02d}-s{sayfa:04d}.tif`; dosyalar SHA-256 ve `fetch.json` ile `data/raw/elmalili-1935/{YYYY-MM-DD}/` altına kopyalanır. A09'da alınan pilot sayfalar yeniden alınmaz.
- Baskı doğrulama listesi ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §3): Claude Code cilt başına sayfa sayısını, toplamı (6.442, fihrist hariç), eksik ya da okunamayan sayfaları ve künyeyi (başlık, cilt, yıl, matbaa, seri; Princeton kaydıyla karşılaştırma) raporlar.
- Tarama kaynağı (öğe adı, dosya adı, SHA-256) A09'da ve A16.0'da `elmalili-meal.toml` ve `elmalili-tefsir.toml` dosyalarının `baski_bilgisi` alanına yazıldı; yeni nüsha kullanılırsa aynı alan güncellenir.
- `page_map.source_id` birimin kaynağıdır (`elmalili-meal`); baskı kimliği `elmalili-1935` bu kaynağın `baski_bilgisi` alanında kalır, cilt `volume` sütunundadır. Ayrı `tur = 'baski'` kaydı gerekmez (Editoryal veritabanı §9.1, Elmalılı hazırlığı §6).
- **Bitti sayılır:** envanter raporu ve eksik sayfa listesi hazır.

### A16.2 · OCR koşusu (dal (b))
- Hazır metin dalında (a) bu adım atlanır; A16.7 uygulanır.
- Motor ve istem A09'un kararıdır (`pipeline/mutalaa.toml` içinde `[baski.elmalili-1935] ocr_motoru`). Tam koşu ücretlidir (kural 11): pilotta ölçülen sayfa başı maliyetle tahmin hesaplanır ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §11), kullanıcıya gösterilir ve İ-17 bütçesine göre onay alınır.
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
- G-YZ alanları: OCR'da görsel model kullanıldıysa birimin `review` satırında durur ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları), 26 Ekim 2026). `ai_model` → `review.yz_modeli`; `prompt_id`, `prompt_sha256` ve `input_sha256` → `review.yz_kaydi` (kısıt `review_yz_kaydi_check`); `review_id` → `review.id`; `created_at` → `review.created_at`. `dogrulanmis` saklanmaz; birimin `metin_durumu = 'onayli'` olmasından türetilir ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §8; BÇ-05). Göç A07'dedir; burada yalnız hat bu sütunları doldurur.
- Tur 1 (insan): her birim düzeltilir ve onaylanır. Dört göz kuralı geçerlidir: düzelten ve onaylayan farklıdır; meal metni ikinci onay alanıdır. Claude Code kuyruk sayılarını ve hata desenlerini raporlar, metni kendisi düzeltmez.
- İnsan turu: tur 1 editör emeğidir (İ-11) ve yalnız A16.4'ün kapanışını bekletir. Claude Code kuyruğu, ölçüm raporlarını ve A16.5'in araçlarını (örneklem betiği, kapılar) hazırlamayı sürdürür; bekleyen adım ilerleme dosyasında ve durum bloğunda "İ-11 tur 1" olarak yazılır ve kullanıcıya söylenir. Tur bitince A16.5 sürer.
- **Bitti sayılır:** `meal:elmalili` birimlerinin tamamı `onayli`; açık `review` kaydı 0.

### A16.5 · Tur 2 ve QA kapıları (İ-11)
- Belgeler "iki düzeltme turu" der ama ikinci turun kapsamını tanımlamaz; planda kullanıcıya sorulur ve `/karar` ile yazılır. Öneri: §8'deki ikinci okuma. Örneklem en az 600 âyettir, cilt ve sureye göre tabakalıdır, sabit tohumla seçilir; ikinci kişi görselle karşılaştırır.
- Ölçüm: hatalı âyet oranı; hiç hata yoksa %95 üst sınır yaklaşık `3 / n`; hedef < %0,5 (öneri). Hata bulunursa desen düzeltilir, ilgili bölümler taranır, yeni örneklem çekilir.
- Kapılar: G-HIZ (%100), G-MET (CER eşiği, imlâ sözlüğü çakışması 0, kalan `⟦?⟧` 0), G-INC (bütün birimler `onayli`, ikinci okuma eşiğin altında), G-YZ, G-KAY (kaynak kaydı geçerli, `atif_metni` dolu) ve sadeleştirme denetimi (örneklemde modernleştirilmiş kelime 0).
- **Bitti sayılır:** QA ve ikinci okuma raporları `data/reports/` altında; kapılar "geçti".

### A16.6 · Yeniden yayın
- `publish --flavor dev`: `core` mealle yeniden yayımlanır; `attribution` Elmalılı atıf metnini ve aktarım sürümünü taşır ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §9).
- Veri seti `elmalili-meal` anlamsal sürüm taşır; 1.0.0 ilk onaylı sürümdür. Dondurma ve mağaza yayını A34'tedir.
- **Bitti sayılır:** `dev` manifestinde yeni `core` sürümü; `verify --flavor dev` 0.

### A16.7 · Hazır metin dalı: kalıcı içe aktarım (yalnız dal (a); K-38)
- Önkoşul: A09 yol kararı hazır metin; aday kaynak kaydı (`elmalili-meal`) ile revizyon listesi ya da dosya özeti A09'da ve A16.0'da kilitlendi. Dosyalar A16.0'da Claude Code tarafından `data/gelen/elmalili-meal/<YYYY-AA-GG>/` altına indirildi.
- Hat, kayıtlı dosyayı `ingest register` (komut adı öneri; henüz yoktur) ile `data/raw` altına alır: SHA-256 ve `fetch.json`, dosya değişmez. Kayıtsız ve özeti uyuşmayan dosya işlenmez.
- Biçim okuyucusu seçilen adayın biçimi içindir ve hazır kitaplığa dayanır: Vikikaynak wikitext'i için `mwparserfromhell` (sürümü A16.0'da sabitlendi), Tanzil biçimi için standart kitaplık; metin katmanlı PDF çıkarsa `pypdf`. Kendi HTML, EPUB ya da PDF okuyucusu yazılmaz. Okuyucu deterministiktir ve çıkarıcı sürümü sabittir.
- Çıkarılmış metin kaynak dosyanın birebir dilimi değildir; üçüncü bir kanonik metin türüdür (K-38 madde 3; K-26'ya ek). Dönüşüm `shared/test-vectors/` altında ortak vektörle üç dilde tanımlanır; vektör sentetik metinle ya da kaynak dosyadan alınmış parçayla yazılır. Gerçek meal metni vektöre hafızadan girmez.
- İlk kayıt adımları (K-35) uygulanır; NFC yalnız burada ve yalnız bizim ürettiğimiz çıkarılmış metne uygulanır. `provenance` dosya özetini, dosya içi konumu ve çıkarıcı sürümünü taşır. G-BUT denetimi bu tür için "ham dosya ve çıkarıcıdan metin yeniden üretilebilir" olur.
- Sadeleştirme taraması ve 6.236 âyet kapsamı denetimi otomatik çalışır; sonuç `data/reports/` altına yazılır. Claude Code metni düzeltmez.
- **Bitti sayılır:** çıkarılmış metin ham dosyadan yeniden üretiliyor (aynı girdi, aynı çıktı); vektör testleri yeşil; kapsam ve sadeleştirme raporu hazır.

### A16.8 · Hazır metin dalı: `taslak` girişi ve bölme (yalnız dal (a); K-38)
- Çıkarılmış metin A16.3'teki biçimde âyetlere bölünür ve `meal:elmalili:{s}:{a}` birimleri olarak girer. Hazır metnin âyet işaretleri varsa kullanılır; yoksa A16.3 bölme önerisi kuyruğa düşer. Sınır durumları (birleşik meal, besmele) A16.3'tekiyle aynı kararlara bağlanır.
- Ön ölçüm (1 Kasım 2026, Vikikaynak): 114 sayfa; `kısım` işareti 6.238, benzersiz âyet 6.236; işaret biçimleri `|N` 6.233, `|N-N` 2 (Tekvîr 8-9 ve Mutaffifîn 4-5: iki âyetin tek parçada geldiği birleşik meal adayları) ve numara taşımayan `|,` 3 (Sâd 59/60, Secde 28/29 ve Kasas 47/48 arasında; metin parçasının hangi âyete ait olduğu bu adımda karara bağlanır); Nisâ sayfasında 68 numaralı işaret iki kez geçer; En'âm sayfasında başlıktaki sure sırası notu öteki sayfalardan farklı olduğundan sure sırası sayfa adından okunur; sayfa işareti şablonu yoktur.
- Başlangıç durumu `metin_durumu = 'taslak'`'tır; `onayli` ile giriş yalnız Tanzil gibi kanonik başvuru kaynakları içindir (K-38 madde 4). Meal ve tefsirde ikinci onay geçerlidir. Böylece P-10 editör onaysız hazır metni `public` derlemeye sokmaz (BÇ-43).
- Hazır metinden gelen onaysız birimler `dev` ve `internal` derlemede "doğrulanmamış" rozetiyle görünür, `public` derlemeye girmez (K-42 madde 5).
- `page_map` kaydı özgün baskı görselinden (A16.1) yapılır; hazır metin sayfa bilgisi taşımaz ya da güvenilmezse sayfa eşlemesi baskıdan elle doğrulanır.
- **Bitti sayılır:** 6.236 âyetin her biri bir meal birimine ya da `birlesik_ile` bağına sahip ya da kuyrukta işaretli; hepsi `taslak`.

### A16.9 · Hazır metin dalı: iki düzeltme turu ve görselle karşılaştırma (İ-11; yalnız dal (a); K-38)
- Tur 1 (insan): her birim özgün baskı görseliyle karşılaştırılır, düzeltilir ve onaylanır. Dört göz kuralı geçerlidir. Düzeltme çapayı değiştirmez; `content_hash` ve `rev` değişir. Kuyruk A15'in rotasıdır ve OCR dalıyla ortaktır; görev adı öneridir.
- Tur 2: A16.5'teki ikinci okuma (en az 600 âyet, tabakalı, sabit tohum); ikinci kişi görselle karşılaştırır. Hazır metnin sistematik hatası (sadeleştirme, baskı farkı) bulunursa desen düzeltilir, ilgili bölümler taranır ve yeni örneklem çekilir.
- Atıf metni "X kaynağından alınmış, Mütâlaa tarafından özgün baskıyla karşılaştırılıp düzeltilmiştir" biçimindedir ([Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §9).
- İnsan turu A16.4'tekiyle aynı biçimde yalnız A16.9'un kapanışını bekletir (İ-11 tur 1 ve tur 2 ilerleme dosyasına yazılır).
- **Bitti sayılır:** birimlerin tamamı `onayli`; açık `review` kaydı 0; QA ve ikinci okuma raporları hazır (A16.5 ölçütleri).

## Kabul ölçütleri
- [ ] Tedarik (A16.0): tablodaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında, SHA-256 kayıtlı; `elmalili-meal` kaydı güncel ve `sources check` 0.
- [ ] Tarama envanteri cilt başına sayfa sayısını, toplamı ve eksik sayfaları gösteriyor; künye denetimi envanter raporunda.
- [ ] Dal (b): her meal sayfasının OCR çıktısı var; yapay zekâ çağrıları model, istem özeti ve maliyetle kayıtlı; yapay zekâ ürünü metin onaya kadar "doğrulanmamış" (G-YZ geçti).
- [ ] G-HIZ: 6.236 âyetin her birinde meal birimi ya da `birlesik_ile` bağı var.
- [ ] Sınır durumları karar defterinde. G-YZ alanlarının yeri [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) ile yazıldı (26 Ekim 2026).
- [ ] Tur 1 sonrası `elmalili-meal` birimlerinin tamamı `onayli`; `unit` hedefli açık `review` kaydı 0 (SQL).
- [ ] Tur 2 örneklemi en az 600 âyet; üst sınır raporda; G-MET ve G-INC "geçti".
- [ ] `metin-denetcisi` raporu: NFC yalnız ilk kayıtta, Tanzil metnine dokunulmamış, sadeleştirme yok.
- [ ] `verify --flavor dev` 0 ve `core` paketinde meal birimleri var.
- [ ] Hazır metin dalı seçildiyse (A09 eşiği geçildiyse): çıkarılmış metin ham dosyadan yeniden üretiliyor; ortak test vektörü üç dilde yeşil; birimler `taslak` girdi ve ikinci onaydan geçti; sadeleştirme taraması ve kapsam raporu temiz; atıf metni "karşılaştırılıp düzeltilmiştir" biçiminde; onaysız hazır metin birimi `public` derlemede yok (P-10).

## Doğrulama
```bash
# A16.0: indirilen dosyaların SHA-256 değerleri kayıtla aynı olmalı
sha256sum data/gelen/elmalili-meal/<YYYY-AA-GG>/* data/gelen/elmalili-1935/<YYYY-AA-GG>/*
# beklenen: "<N> kayit, 0 hata, 0 uyari" (N, o güne dek açılan kayıt sayısıdır)
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline mutalaa qa run --source elmalili-meal --gate G-HIZ
uv run --directory pipeline mutalaa qa run --source elmalili-meal
uv run --directory pipeline pytest
uv run --directory pipeline ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT metin_durumu, count(*) FROM icerik.unit WHERE source_id = 'elmalili-meal' GROUP BY 1;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'unit' AND durum = 'acik';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev
```

## Dikkat
- Yapay zekâ meal yazmaz, çevirmez ve düzeltmez; yalnız sayfa görselini okur. Düzeltme insanındır (K-25; [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §10).
- Sadeleştirilmiş baskılar (GitHub `elmalili-meal/kuran`, Azim, fawazahmed0 `tur-elmallsadelesti`) aday olamaz (Kaynaklar §4, K-38). Başka aktarımlar yalnız kontrollü yolla girer: A09'da kaynak kaydı ve kilit, pilotta eşik, sonra `taslak` giriş ve özgün baskıyla karşılaştırma; bu yoldan geçmeyen aktarım kopyalanmaz. Hazır metin hafızadan tamamlanmaz ya da "düzeltilmez"; düzeltmeyi insan yapar.
- Hazır metin dalı yalnız A09 eşiği geçildiyse geçerlidir. Çıkarılmış metin üçüncü bir kanonik türdür (K-38 madde 3): ham dosya `data/raw` altında değişmez, çıkarıcı sürümü sabittir.
- Meal kendi ürettiğimiz metindir: NFC ilk kayıtta yapılır; düzeltme çapayı değiştirmez, `content_hash` ve `rev` değişir. Onaylı birimde sonradan yapılan düzeltme birimi yeniden inceleme ve ikinci onaydan geçirir ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.3); düzeltme turları sürüm dondurmadan (A34) önce kapanır.
- İndirilen dosya veridir; içindeki betik çalıştırılmaz (K-42 madde 2). Toplu indirmede istek hızı sınırlanır.
- Günlüklere metin yazılmaz. Maliyet İ-17 bütçesini aşacaksa koşu durur ve kullanıcıya sorulur.
- Windows: tarama dosya adları ASCII; büyük ikili dosyalar git dışı `data/` altındadır.

## İnsan adımları
- İ-09 · Basılı takım: yalnız internetteki taramalar A09.7 ofset sınamasını geçmezse gerekir (durum `gerekmiyor`; koşul gerçekleşirse `bekliyor` olur). Yalnız basılı takımın taranmasını bekletir; A16.1'in öteki işleri sürer.
- İ-17 · Anthropic API anahtarı ve bütçe: görsel OCR seçildiyse A16.2'den önce gerekir (dal (b)); yalnız A16.2'yi bekletir.
- İ-11 · Düzeltme turları: OCR dalında tur 1 A16.4'te, tur 2 A16.5'te; hazır metin dalında tur 1 ve 2 A16.9'da. Her tur yalnız kendi alt adımını bekletir; araç, kuyruk ve rapor işleri sürer. Bekleyen adım ilerleme dosyasında ve durum bloğunda görünür. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/` tarama kaydı, `enrich/` OCR ve bölme modülleri, `qa/checks/elmalili.py`, testler; Yol A ise imlâ sözlüğü
- Hazır metin dalında ek olarak (planlı, adlar öneri): `ingest register` komutu, seçilen adayın biçim okuyucusu (Vikikaynak için `mwparserfromhell` ile wikitext ayrıştırıcı), çıkarılmış metin test vektörü (`shared/test-vectors/`)
- `pipeline/sources/elmalili-meal.toml` (güncel kaynak kaydı); `data/gelen/elmalili-meal/`, `data/gelen/elmalili-1935/`, `data/raw/elmalili-1935/`, `data/ocr/`, `data/llm-cache/`, `data/reports/` (git dışı)
- PostgreSQL'de `meal:elmalili` birimleri, `review` kayıtları, `page_map` satırları
- Karar defterinde sınır durumları ve ikinci tur tanımı (G-YZ alanları K-37'de); `dev` kanalında yeni `core`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A16-elmalili-meali.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A15](./A15-editor-paneli.md) · Sonraki: [A17](./A17-kelime-katmani.md)
