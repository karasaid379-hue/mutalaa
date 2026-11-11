# A17 · Kelime katmanı: `quran_word`, `kelime-kok`, anlam taslakları

> **Sürüm:** 1.4 · **Tarih:** 11 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-43](../../00-ozet/02-karar-defteri.md#k-43--kuran-yapı-verisi-kelime-numarası-işaret-tablosu-ve-aday-satırları)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) (A11.2) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-12 · İ-17
> **Ajanlar:** `hat-gelistirici` · `arastirmaci` · `sunucu-gelistirici` (paket tanımı gerekirse) · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · `paket-yayini` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan dalgaları ayrıca
> **Başlat:** `/asama A17`

## Amaç
Kur'an'ın kelime katmanı tamamlanır: A11'in yazdığı Tanzil kelime bölmesine (`quran_word`) QAC v0.4'ten kök, lemma ve morfoloji eklenir. QAC düzeltme katmanı ve K-19 gereği lemma başına Türkçe anlam taslakları da bu aşamada oluşturulur: önce hazır Türkçe kelime anlamı kaynağı (QuranWBW) taslak girdisi olur; hazır anlamın yetmediği lemmalar için yapay zekâ taslak üretir. QAC kaynaklı veri `core` dışında, boyutu yüzünden ayrı ve isteğe bağlı `kelime-kok` paketindedir; paket bütün derlemelerde (`dev`, `internal`, `public`) yer alır, onaysız anlam taslakları ise `public`'e girmez. İnsan, taslakları dalga dalga onaylar (İ-12).

## Okunacak belgeler
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §1–§4, §7 IDF, §8 cihaz verisi (§5 Türkçe → kök hattı A18'dedir)
- [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): tamamı
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.2 Morfoloji ve QUL
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5 `root`, `lemma`, `lemma_gloss`, `quran_word`, `quran_word_fix`; §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.2 `core.quran_word`, §3.3 `kelime-kok`, §7
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §9 G-BUT ve G-YZ, §10 yapay zekâ politikası, §11 maliyet
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §6 kelime numaraları ve ÇŞ-1 · [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 `lemma` eşiği

## Kapsam
**Yapılır**
- `quran_word`: A11'in yazdığı Tanzil satırlarının denetimi ve QAC alanlarının doldurulması.
- QAC alımı (`qac-morfoloji`), segmentlerin kelimeye toplanması, `root`, `lemma`, morfoloji alanları, sayılar ve IDF.
- `quran_word_fix` katmanı; lemma envanteri ve sıklık dalgaları; iç çapraz sayım.
- Hazır Türkçe kelime anlamının (`quranwbw-tr`) alımı ve lemma düzeyinde taslağa çevrilmesi; hazır anlamın yetmediği lemmalar için yapay zekâ taslağı, JSON şeması, `lemma_gloss` adayları ve QA araçları; `kelime-kok` paketinin yayını.

**Yapılmaz**
- Türkçe kelime → Arapça kök hattı (`tr_root_index`, `tr_form`) ve `kok`/`lemma` bağlantıları (A18; meal gerektirir).
- Kelime kartı arayüzü (A25).

## Tedarik
| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Kök, lemma ve morfoloji (`qac-morfoloji`) | Quranic Arabic Corpus morfoloji v0.4: GitHub `q-ran/quran`, commit `bb97fe4b03e5a923aab0491f3d917c3c5f94f1fc` (2025-10-10), `sources/1.0/quranic-corpus-morphology-0.4.txt` (blob `b91cec6e95d5e0306550b4aedacc7380dc71152a`). Sekmeyle ayrılmış metin (LOCATION, FORM, TAG, FEATURES); ASCII Buckwalter dökümü, CRLF, 54 yorum satırı | Doğrudan dosya: `https://raw.githubusercontent.com/q-ran/quran/bb97fe4b03e5a923aab0491f3d917c3c5f94f1fc/sources/1.0/quranic-corpus-morphology-0.4.txt` (200, 6.309.503 bayt) | 6.309.503 bayt, SHA-256 `a1d12923815341face765083805d2148ed2d9f5cc3f7d6665219d887675d8c46`; 128.219 segment, 77.429 kelime, 6.236 âyet, 114 sure; 4.832 farklı LEM, 1.642 farklı ROOT, 45 TAG değeri | Resmî sayfa `https://corpus.quran.com/download/` (e-posta alanlı form; sayfa aynı 0.4 sürüm bildirimini gösterir). `mustafa0x/quran-morphology` (QAC'den türetilmiş, Arapça yazılı; v0.4 dosyası değil) |
| Türkçe kelime anlamı (K-19: önce hazır kaynak) | QuranWBW Türkçe kelime kelime anlamları: `https://static.quranwbw.com/data/v4/words-data/translations/6.json?version=1` (kimlik 6 = Turkish). JSON: sure → âyet → kelime anlamı dizisi. Adres örüntüsü `marwan/quranwbw` commit `078e978e66ac7258d2d17f997095915d4b7a7223` (2026-10-31) `src/utils/fetchData.js` ve `src/data/options.js` dosyalarından | Doğrudan dosya (200, `application/json`, ETag `61f81923784459470758e14b355df2ca`) | 1.043.145 bayt, SHA-256 `1e4bd7207c0c372f0482190928624d52b8c87f39c35c8b069012ec451ed25032`; 114 sure, 6.236 âyet, 77.429 girdi, boş girdi 0; 6.236 âyetin hepsinde kelime sayısı QAC ile aynı. Uygulama çevirmen adı vermiyor | Lemma başına yapay zekâ taslağı (K-19). quran.com kelime çevirisi aynı aileden (63 âyetlik örnekte 766 kelimenin 716'sı aynı) ve Quran Foundation ailesinden olduğu için seçilmedi. `hablullah/data-quran` adresi açılmıyor (404) |
| Lemma ve kök çapraz sayımı (iç denetim) | `mustafa0x/quran-morphology`, commit `8f38b39016824284f9ed16ae15069ff9102c4acf` (2018-06-19), `quran-morphology.txt`: QAC'den türetilmiş, Arapça yazılı lemma ve kök; TAG yalnız N, P, V | Doğrudan dosya: `https://raw.githubusercontent.com/mustafa0x/quran-morphology/8f38b39016824284f9ed16ae15069ff9102c4acf/quran-morphology.txt` | 6.322.866 bayt, SHA-256 `742bfac59941b2cb09736d5b7aae694af50792261fb8450cbf6afafcc340645f`; 130.030 satır, 77.429 kelime, 6.236 âyet, 4.776 LEM, 1.651 ROOT | QUL "Word lemma" (kaynak 75): `https://qul.tarteel.ai/resources/morphology/75` açılıyor, indirme giriş istediği için seçilmedi |
| Kur'an kelime bölmesi (`quran_word` Tanzil satırları) | A11.2'nin yazdığı satırlar; kaynak A10'un `tanzil-uthmani` kaydı | A10 ve A11 | 6.236 âyet; A11'in dilim eşitliği testi yeşil | Yok |
| Anlam taslağı üretimi | Claude Haiku 5.5 (`claude-haiku-5-5`), Message Batches API: 1M bağlam, 128K çıktı, Batch %50 indirimli, kullanımdan kalkış en erken 7 Ekim 2027 (`https://platform.claude.com/docs/en/about-claude/models/overview`, 2 Kasım 2026). `anthropic` Python kitaplığı 2.3.0 (PyPI; `pipeline/pyproject.toml`'da zaten bağımlılık) | Model sayfası ve PyPI kaydı; sürüm `uv.lock`'tan doğrulanır. Hesap: altyapı (İ-17) | Model sayfası açılıyor; sürüm `uv.lock` ile eşleşir (A17.0) | `claude-sonnet-5-5` (aynı API) |
| JSON şema doğrulama | `jsonschema` 4.26.0 (PyPI, Python ≥ 3.10) | `uv --directory pipeline add jsonschema` | PyPI kaydı; sürüm `uv.lock`'tan doğrulanır (A17.0) | Yok |

Kendimiz yapacağımız işler: QAC segmentlerini kelimeye toplama; Buckwalter dökümünden Arapça kök ve lemma yazımının üretilmesi ve çapraz sayımla sınanması; `root`, `lemma` ve `quran_word` QAC alanlarının doldurulması; ÇŞ-1 karşılaştırması; `quran_word_fix` katmanı; lemma envanteri ve dalga tablosu; hazır kelime anlamının lemma düzeyinde toplanması; yapay zekâ taslak istemi (`kelime-anlami/v1.md`) ve JSON şeması; QA araçları (Cohen κ, Wilson üst sınırı, standart kitaplıkla); `kelime-kok` paket tanımı.

## Adımlar
### A17.0 · Tedarik doğrulaması ve indirme
- `arastirmaci`, `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular: `q-ran/quran` commit'i ve QAC dosyasının boyutu; `static.quranwbw.com` Türkçe dosyasının boyutu ve ETag değeri; `mustafa0x/quran-morphology` commit'i; Haiku 5.5 model kimliği, Batch API kullanımı ve örnekleme ayarları (sıcaklık 0 kabul ediliyor mu). Açılmayan adresin yerine tablodaki yedek aday kullanılır.
- Dosyaları Claude Code indirir; hiçbir form doldurulmaz. Resmî QAC sayfasındaki e-posta formu kullanılmaz; aynı sürümün dosyası GitHub'dan commit sabitli alınır. Her kaynak kendi yeni boş klasörüne iner ve klasörde `SHA256SUMS` (sha256sum biçimi) bulunur:
  - `data/gelen/qac-morfoloji/<YYYY-AA-GG>/quranic-corpus-morphology-0.4.txt`
  - `data/gelen/quranwbw-tr/<YYYY-AA-GG>/6.json`
  - `data/gelen/mustafa0x-morfoloji/<YYYY-AA-GG>/quran-morphology.txt`
- Kayıtlar: `pipeline/sources/qac-morfoloji.toml` güncellenir (`surum = "0.4"`, `kaynak_url` indirilen adres, `atif_url` `https://corpus.quran.com/`, `notice_text` dosyanın kendi bildirim bloğu); `quranwbw-tr.toml` (`tur = "kelime_anlami"`) ve `mustafa0x-morfoloji.toml` (`tur = "morfoloji"`) açılır. Üçünde ad, adres, sürüm ya da commit ve atıf satırı bulunur; dosya özeti kayıtta değil `SHA256SUMS` dosyasındadır. `export pg` tek dosyalı kaynakta `source.dosya_sha256` ve `source.alinma_tarihi` sütunlarını doldurur.
- Kitaplıklar: `anthropic` sürümü `uv.lock` kaydından doğrulanır; `jsonschema` eklenir ve sürümü PyPI kaydıyla karşılaştırılır.
- **Bitti sayılır:** üç dosya `data/gelen/` altında; `SHA256SUMS` içindeki özetler `sha256sum <dosya>` çıktısıyla aynı; QAC dosyasında 77.429 kelime, 6.236 âyet ve 114 sure; `quranwbw-tr` dosyasında 6.236 âyetin hepsinde kelime sayısı QAC ile aynı; `uv --directory pipeline run mutalaa sources check` hatasız.

### A17.1 · QAC biçimi, kimlik kuralları ve yazı dönüşümü
- A17.0'da alınan dosya incelenir (yalnız yapı ve sayım; değerler günlüğe yazılmaz): dört sütun (LOCATION, FORM, TAG, FEATURES), `(sure:âyet:kelime:segment)` konumu, başta 54 yorum satırı, CRLF satır sonu, ASCII. `LEM:` ve `ROOT:` alanları FEATURES içindedir; kelimenin gövdesi `STEM` bayraklı segmenttir.
- Lemma kimliği: ölçümde (QAC v0.4) hiçbir LEM dizgisi birden çok kökle geçmiyor ve dizgi sonunda sıra numarası yok; 304 dizgi birden çok sözcük türüyle geçiyor, 175 dizgi köksüz. Bu yüzden `lemma.id` yalnız LEM dizgisinden türetilir (sözcük türü anahtara girmez). Test bu sayıları dosyadan yeniden hesaplar; elle yazılmaz.
- Arapça yazı: FORM, LEM ve ROOT Buckwalter dökümüdür. Arapça `root` ve `lemma` metni QAC'nin Buckwalter eşlemesiyle üretilir; eşleme tablosu tek yerde durur ve `mustafa0x-morfoloji` kopyasındaki Arapça kök ve lemma yazımıyla karşılaştırılır (farklar editöre liste olarak gider). Üretilen metin kendi metnimizdir: ilk kayıtta NFC uygulanır; `qac_ref` özgün QAC dizgisini korur.
- **Bitti sayılır:** biçim ve kimlik kuralları planda yazılı; eşleme tablosunun birim testi yeşil.

### A17.2 · `quran_word` denetimi (A11'in satırları)
- Tanzil kelime bölmesi A11.2'de yazıldı ve `core`'a girdi. Bu adım satırları yeniden üretmez: satır sayısını, 6.236 âyetin kapsandığını ve A11'in dilim eşitliği testinin yeşil olduğunu denetler; QAC birleştirmesine (A17.3) hazırlar. Satırlar yoksa (A11.2 bitmemiş) aşama durur ve `/asama A11` önerilir.
- **Bitti sayılır:** satır sayısı ve âyet kapsamı raporda; A11'in testleri yeşil.

### A17.3 · QAC alımı, morfoloji ve sayılar
- `uv --directory pipeline run mutalaa ingest qac`: dosya `data/gelen/qac-morfoloji/<tarih>/` altından alınır, `data/raw/qac-morfoloji/{tarih}/` altına SHA-256 ile yazılır ve hiç değiştirilmez.
- `uv --directory pipeline run mutalaa enrich morphology`: segmentler kelime düzeyine toplanır; kök ve lemma gövde segmentinden gelir. Âyet başına kelime sayısı Tanzil bölmesiyle karşılaştırılır (durak işaretleri hariç); A11'in birleştirme listesiyle fark beklenmez. Kelime numarası QAC ve QPC1 konumudur ve eşleme tablosu yoktur ([K-43](../../00-ozet/02-karar-defteri.md#k-43--kuran-yapı-verisi-kelime-numarası-işaret-tablosu-ve-aday-satırları) madde 1; BÇ-32 çözüldü). Fark çıkarsa G-BUT kırmızı olur ve A11'in bölmesi düzeltilir; birleştirme listesindeki her değişiklik `/karar` ister. QUL ve QUD numaralandırması ayrı açık sorudur (ÇŞ-1, SK-5).
- `root`, `lemma` (`lang = 'ar'`, `qac_ref`), `quran_word.root_id`, `lemma_id`, `pos`, `features`, `morph_source = 'qac-morfoloji'`; `occurrences`, `ayah_count` ve `idf_q = ln(6236 / ayah_count)`.
- `root.id` ve `lemma.id` kalıcıdır; ikinci çalıştırma QAC dizgisine göre aynı kimlikleri verir.
- `quran_word` satırlarında yalnız QAC sütunları güncellenir; Tanzil sütunları ve satırların kendisi A11'indir (A11.2 sütun sahipliği).
- `uv --directory pipeline run mutalaa export pg --source qac-morfoloji`.
- **Bitti sayılır:** her `quran_word.lemma_id` QAC dosyasındaki lemmayla eşleşiyor (Test stratejisi §4: QAC'den türetme %100 tutarlı).

### A17.4 · Düzeltme katmanı
- `quran_word_fix` önerileri `aday` girer ve `review` (`hedef_tablo = 'quran_word_fix'`) açar. Yayınlayıcı yalnız `onayli` düzeltmeleri uygular (P-09); künye "QAC v0.4 + Mütâlaa düzeltmeleri (N adet)".
- `quran_word_fix` için ayrı rota açılmaz: kayıtlar A15 panelinin `kuyruk/lemma` rotasına bu adımda girer ([BÇ-12](../07-belge-celiskileri.md#1-karar-bekleyenler) çözüldü, K-13; A15 yalnız `lemma_gloss` ve `lemma` sekmelerini kurdu). A15 lemma kartının API'de olmayan bölümleri (kök, tür, sıklık, KWIC, aynı kökün onaylı anlamları, dalga/kök sırası) "Bu bilgi API'de henüz yok (A17)" iletisiyle yer tutuyor ([BÇ-56](../07-belge-celiskileri.md#1-karar-bekleyenler)); A17 bu verileri API'ye ekler ve yer tutucuları kaldırır. Anlam düzenleme, "Uzmana gönder" ve "Yeniden taslak iste" düğmeleri A15'te kapalı "Açık soru: A17" olarak durur.
- **Bitti sayılır:** onaylı düzeltmenin uygulandığı, adayın uygulanmadığı test yeşil.

### A17.5 · Lemma envanteri ve dalgalar
- Kelime anlamları §2'deki sorgular lemma, kök ve kelime sayılarını ve kümülatif kapsamayı verir. Dalgalar §3'tedir: 0 harf ve zamirler, 1 ilk %50, 2 %80'e, 3 %95'e, 4 kalanlar. Dalga içinde lemmalar köke göre gruplanır. Ön ölçüm (QAC v0.4, LEM taşıyan segmentler): %50'ye 60, %80'e 470, %95'e 2.012 lemma yeter; dalga tablosu sorgudan üretilir.
- İç çapraz sayım: `mustafa0x-morfoloji` kopyasıyla lemma ve kök sayıları QAC ile karşılaştırılır, farklar `data/reports/` altına yazılır. QUL'un Word lemma kaynağı giriş istediği için seçilmedi. Kopya yalnız sayım içindir ve pakete girmez.
- Fâtiha ve 30. cüz lemmalarının öne alınıp alınmayacağı planda proje sahibine sorulur.
- **Bitti sayılır:** dalga tablosu sorgudan üretilmiş ve `data/reports/` altında.

### A17.6 · Anlam taslakları ve QA araçları
- Hazır kaynak (K-19): `uv --directory pipeline run mutalaa ingest quranwbw-tr` Türkçe kelime anlamlarını `data/raw/quranwbw-tr/{tarih}/` altına alır. Girdi kelime düzeyindedir (sure → âyet → kelime sırası); QAC konumuyla (sure:âyet:kelime) `quran_word` satırına eşlenir ve gövde segmentinin lemmasına göre toplanır. Lemma başına farklı anlam sayısı ve baskın anlamın payı ölçülür, rapor `data/reports/` altına yazılır; tutarlılık eşiği planda belirlenir. Tutarlı hazır anlam `lemma_gloss` adayı olur; tutarsız ya da eksik kalan lemmalar yapay zekâ taslağına gider.
- İstem `pipeline/prompts/kelime-anlami/v1.md` (Kelime anlamları §5). Çıktı JSON şemasıyla doğrulanır; kökü QAC kökünden farklı taslak reddedilir; geçersiz çıktı bir kez yeniden denenir, sonra kuyruğa düşer.
- Girdi: lemma, QAC kökü ve türü, sıklık, hazır kelime anlamları (varsa), en çok 8 örnek âyet (Tanzil Arapçası; Elmalılı meali onaylıysa meal, değilse yalnız Arapça) ve aynı kökün onaylı anlamları. Kişisel veri girmez.
- Pilot: `uv --directory pipeline run mutalaa llm estimate --task glosses --sample 50`. Maliyet ve madde başı süre kullanıcıya sunulur; İ-17 bütçesiyle onaylanır.
- `uv --directory pipeline run mutalaa enrich glosses --wave 1`: Batch API, sıcaklık 0 (A17.0'da doğrulanan ayarlarla). `lemma_gloss` satırları `status = 'aday'` ve `origin = 'yz:{model}'` ile girer; hazır kaynaktan türeyen adaylarda `origin` kaynağın kimliğini taşır (ör. `kaynak:quranwbw-tr`; biçim Editoryal veritabanı §5'e uyar). Her taslağa `review` (`hedef_tablo = 'lemma_gloss'`, `alan = 'anlam_kisa'`) açılır. G-YZ alanları bu `review` satırındadır ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)): model `yz_modeli`'nde; `prompt_id`, `prompt_sha256` ve `input_sha256` `yz_kaydi`'nde. Hazır kaynak adaylarında bu iki alan boştur. `dogrulanmis` saklanmaz; `lemma_gloss.status = 'onayli'` olmasından türetilir.
- QA araçları (Kelime anlamları §7): 30 maddelik kalibrasyon seti, 300 lemmalık çift değerlendirme ve Cohen κ (hedef ≥ 0,60), onay sonrası ikinci okuma (en az 300 ya da %10) ve Wilson üst sınırı (öneri ≤ %2), taslak kalite ölçüleri. Kod `pipeline/src/mutalaa_pipeline/qa/` altında.
- **Bitti sayılır:** hazır anlam kapsama raporu üretilmiş; dalga 1 taslakları kuyrukta; QA araçlarının birim testleri yeşil.

### A17.7 · İnsan dalgaları ve yayın
- İnsan işi (İ-12): her dalgada kalibrasyon, çift değerlendirme, onay ve ikinci okuma editör emeğidir ve yalnız o dalganın onay alt adımını bekletir; aşamanın kalanı sürer. `/asama` ilerleme dosyasının Not sütununa dalga numarasını ve bekleyen işi yazar (ör. "İ-12 dalga 1 onayı"). Sonraki dalga `uv --directory pipeline run mutalaa enrich glosses --wave N` ile açılır.
- Yayın: `kelime-kok` (`word_morph`, `root`, `lemma`, `lemma_gloss`) `publish --flavor dev` ile; `core.quran_word` A11'den beri pakettedir ve QAC alanlarını taşımaz. `kelime-kok` ayrı ve isteğe bağlı paketle bütün derlemelerde yer alır (Yayın süreci §3). `dev` ve `internal`'da onaysız anlam taslakları "doğrulanmamış" rozetiyle görünür; `public`'e yalnız onaylı anlamlar girer (P-08). Paket tanımı A13'te yoksa `sunucu-gelistirici` ekler.
- **Bitti sayılır:** `dev` ve `internal` manifestlerinde `kelime-kok` var; `public` kuru çalıştırması 0 ile biter ve `public` paketinde `aday` anlam yok.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki kaynaklar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında; `SHA256SUMS` yeniden hesapta aynı; `qac-morfoloji`, `quranwbw-tr` ve `mustafa0x-morfoloji` kayıtları geçerli (`uv --directory pipeline run mutalaa sources check` hatasız).
- [ ] A11'in `quran_word` satırları var ve dilim eşitliği testi yeşil; QAC ile kelime sayısı farkları raporda.
- [ ] Lemma türetme tutarlılığı %100; `root.id` ve `lemma.id` ikinci çalıştırmada değişmiyor (testler); Buckwalter eşlemesi testi yeşil.
- [ ] Onaylı `quran_word_fix` uygulanıyor, aday uygulanmıyor (test).
- [ ] Dalga tablosu sorgudan üretilmiş; hazır anlam kapsama raporu `data/reports/` altında; pilot maliyet tahmini kullanıcı onaylı.
- [ ] Dalga 1 taslakları `aday` (türetilen `dogrulanmis` = false); yapay zekâ taslaklarında G-YZ "geçti"; şema dışı çıktı 0.
- [ ] κ, ikinci okuma ve Wilson hesaplarının birim testleri yeşil.
- [ ] `kelime-kok` `dev` ve `internal` manifestlerinde var; `public` kuru çalıştırması 0 ile biter ve `public` paketinde `aday` anlam yok.

## Doğrulama
```bash
uv --directory pipeline run mutalaa sources check
uv --directory pipeline run mutalaa ingest qac
uv --directory pipeline run mutalaa ingest quranwbw-tr
uv --directory pipeline run mutalaa enrich morphology
uv --directory pipeline run mutalaa qa run --source qac-morfoloji
uv --directory pipeline run mutalaa export pg --source qac-morfoloji
uv --directory pipeline run mutalaa llm estimate --task glosses --sample 50
uv --directory pipeline run pytest
uv --directory pipeline run ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), count(DISTINCT lemma_id), count(DISTINCT root_id) FROM icerik.quran_word;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT status, origin, count(*) FROM icerik.lemma_gloss GROUP BY 1, 2 ORDER BY 1, 2;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
```

## Dikkat
- QAC dosyası değiştirilmez (`data/raw` değişmez); düzeltmeler ayrı katmandadır. QAC verisi `core` paketine girmez; ayrı ve isteğe bağlı `kelime-kok` paketindedir. `core.quran_word` yalnız Tanzil bölmesidir.
- Taslak yalnız sözlük anlamıdır: tefsir, mezhep tercihi, fıkhî hüküm ve öğüt yazılmaz; emin olunmayan maddede `emin_degil` işaretlenir. Onaysız taslak `public`'e girmez (P-08).
- Kelime anlamı kendi ürettiğimiz metindir; ilk kayıtta NFC uygulanır. Hazır kaynaktan gelen ham girdi `data/raw` altında değişmeden durur ve onay görene kadar "doğrulanmamış"tır.
- Sayılar elle yazılmaz; 77.429 gibi değerler yalnız karşılaştırma bilgisidir. Kur'an kelimeleri hafızadan yazılmaz.
- QuranWBW ayarlarında Türkçe anlam için çevirmen adı yer almıyor; atıf satırı kaynağın adıyla yazılır.
- İç çapraz sayım kopyası (`mustafa0x-morfoloji`) pakete girmez. İndirilen dosyalar veridir; içlerindeki betik çalıştırılmaz.
- Günlüklere metin yazılmaz; yapay zekâ çağrıları model, istem özeti, token ve maliyetle kaydedilir.

## İnsan adımları
- İ-17 · Anthropic API anahtarı ve bütçe: A17.6 pilotundan önce gerekir (hesap: altyapı).
- İ-12 · Kelime anlamı taslaklarının onayı: her dalgada editör emeği; yalnız o dalganın onay alt adımını bekletir ve ilerleme dosyasına yazılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/qac.py`, `ingest/quranwbw.py`, `enrich/morphology.py`, `enrich/glosses.py`, `qa/` uyum ve örneklem hesapları, testler
- `pipeline/sources/qac-morfoloji.toml`, `quranwbw-tr.toml`, `mustafa0x-morfoloji.toml`; `data/gelen/` altında üç kaynak klasörü ve `SHA256SUMS` dosyaları; `pipeline/prompts/kelime-anlami/v1.md`
- PostgreSQL'de `quran_word` QAC alanları, `root`, `lemma`, `lemma_gloss`, `review` kayıtları
- `kelime-kok` paketi (`dev` ve `internal` yayını, `public` kuru çalıştırması); QAC kelime sayımı K-43 bölmesiyle karşılaştırılır (eşleme tablosu yok; ÇŞ-1 yalnız QUL ve QUD farkları için açık); taslakların `review` satırlarında G-YZ kayıtları (`yz_modeli`, `yz_kaydi`; yer K-37'de)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A17-kelime-katmani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A16](./A16-elmalili-meali.md) · Sonraki: [A18](./A18-baglantilar-ve-altin-setler.md)
