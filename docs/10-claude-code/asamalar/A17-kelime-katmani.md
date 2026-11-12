# A17 · Kelime katmanı: `quran_word`, `kelime-kok`, hazır anlam adayları

> **Sürüm:** 2.0 · **Tarih:** 12 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-39](../../00-ozet/02-karar-defteri.md#k-39--tanzil-alımı-simple-cleanin-yeri-kanonik-kaynakta-hat-yazma-kuralı-kilit) (madde 2, QAC istisnasının dayanağı) · [K-43](../../00-ozet/02-karar-defteri.md#k-43--kuran-yapı-verisi-kelime-numarası-işaret-tablosu-ve-aday-satırları) (madde 3 genişledi) · [K-46](../../00-ozet/02-karar-defteri.md#k-46--yayın-kaydı-içerik-özetleri-ve-fikstürler) (madde 1 ve 7 güncellendi) · [K-48](../../00-ozet/02-karar-defteri.md#k-48--editör-api-kuralları-inceleme-kararı-ikinci-onay-eşzamanlılık-yayın-talebi-ve-sayfa-görseli) (madde 2 güncellendi)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) (A11.2) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-12 (İ-17 gerekmez; S-16'ya bağlı)
> **Ajanlar:** `hat-gelistirici` · `arastirmaci` · `sunucu-gelistirici` · `web-gelistirici` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · `paket-yayini` · `ef-goc` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan dalgaları ayrıca
> **Başlat:** `/asama A17`

## Amaç
Kur'an'ın kelime katmanı tamamlanır: A11'in yazdığı Tanzil kelime bölmesine (`quran_word`) QAC v0.4'ten kök, lemma ve morfoloji eklenir. K-50 gereği bu aşamada yapay zekâ taslağı yoktur ve hat Anthropic çağrısı yapmaz. Hazır Türkçe kelime anlamı kaynağı (QuranWBW) her lemma için `lemma_gloss` adayı verir; anlamı tutarsız çıkan lemmanın anlamını editör "Düzenle ve onayla" ile yazar. QAC'nin kök ve lemma satırları kaynak verisidir: `onayli` girer, `review` açılmaz; yanlışlar `quran_word_fix` katmanıyla düzeltilir. QAC kaynaklı veri `core` dışında, boyutu yüzünden ayrı ve isteğe bağlı `kelime-kok` paketindedir; paket bütün derlemelerde (`dev`, `internal`, `public`) yer alır, onaysız anlam adayları ise `public`'e girmez. İnsan, adayları dalga dalga onaylar (İ-12).

## Okunacak belgeler
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §1–§4, §7 IDF, §8 cihaz verisi (§5 Türkçe → kök hattı A18'dedir)
- [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): tamamı (yapay zekâ istemi §5 S-16'ya ertelenmiştir)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.2 Morfoloji ve QUL
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5 `root`, `lemma`, `lemma_gloss`, `quran_word`, `quran_word_fix`; §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.2 `core.quran_word`, §3.3 `kelime-kok`, §7
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları (P-08, P-09)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §9 G-BUT (G-YZ ve §10 yapay zekâ politikası S-16'dadır)
- [Backend API](../../02-mimari/05-backend-api.md): §4 ve §10.3 (`lemma` ve `lemma_gloss` uçları)
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §6 kelime numaraları ve ÇŞ-1 · [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 `lemma` eşiği
- [Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md): S-16 (yapay zekâ işleri)

## Kapsam
**Yapılır**
- `quran_word`: A11'in yazdığı Tanzil satırlarının denetimi ve QAC alanlarının doldurulması.
- QAC alımı (`qac-morfoloji`), segmentlerin kelimeye toplanması, `root` ve `lemma` (onaylı, `origin = 'qac'`), morfoloji alanları, sayılar ve IDF.
- `quran_word_fix` katmanı (yalnız onay ve red); lemma envanteri, `lemma_dalga` tablosu ve dalgalar; iç çapraz sayım.
- Hazır Türkçe kelime anlamının (`quranwbw-tr`) alımı; her lemma için `lemma_gloss` adayı; "Düzenle ve onayla"; QA araçları (Cohen κ, Wilson üst sınırı, tabakalı seçim, `qa gloss-sample`).
- `kelime-kok` paketinin kurulumu ve `dev` yayını; `GET /api/v1/lemmas/{id}` ucu, `sira=dalga` ve panel işleri (BÇ-56'nın A17 yarısı).

**Yapılmaz**
- Yapay zekâ taslağı, istem, Batch, `llm estimate`, G-YZ, `kok_anlami_onerisi` ve panelde "Yeniden taslak iste": hepsi S-16'dadır ([Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md); K-50 madde 1). `jsonschema` eklenmez.
- "Uzmana gönder", `quran_word_fix` için `new_value` düzenlemesi ve `quran_word_fix` adaylarının kaynağı: BÇ-61 (A18).
- Türkçe kelime → Arapça kök hattı (`tr_root_index`, `tr_form`) ve `kok`/`lemma` bağlantıları (A18; meal gerektirir).
- Kelime kartı arayüzü (A25).

## Tedarik
Claude Haiku 5.5 ve `jsonschema` satırları kaldırıldı: yapay zekâ işleri S-16'ya taşındı (K-50 madde 1); model, fiyat ve örnekleme ayarları o zaman yeniden araştırılır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Kök, lemma ve morfoloji (`qac-morfoloji`) | Quranic Arabic Corpus morfoloji v0.4: GitHub `q-ran/quran`, commit `bb97fe4b03e5a923aab0491f3d917c3c5f94f1fc` (2025-10-10), `sources/1.0/quranic-corpus-morphology-0.4.txt` (blob `b91cec6e95d5e0306550b4aedacc7380dc71152a`). Sekmeyle ayrılmış metin (LOCATION, FORM, TAG, FEATURES); ASCII Buckwalter dökümü, CRLF, 54 yorum satırı | Doğrudan dosya: `https://raw.githubusercontent.com/q-ran/quran/bb97fe4b03e5a923aab0491f3d917c3c5f94f1fc/sources/1.0/quranic-corpus-morphology-0.4.txt` (200, 6.309.503 bayt) | 6.309.503 bayt, SHA-256 `a1d12923815341face765083805d2148ed2d9f5cc3f7d6665219d887675d8c46`; 128.219 segment, 77.429 kelime, 6.236 âyet, 114 sure; 4.832 farklı LEM, 1.642 farklı ROOT, 45 TAG değeri | Resmî sayfa `https://corpus.quran.com/download/` (e-posta alanlı form; sayfa aynı 0.4 sürüm bildirimini gösterir). `mustafa0x/quran-morphology` (QAC'den türetilmiş, Arapça yazılı; v0.4 dosyası değil) |
| QAC Buckwalter tablosu sayfası (`qac-belge`; eşleme tablosunun kaynağı) | Quranic Arabic Corpus, "Java API - Buckwalter Transliteration": `https://corpus.quran.com/java/buckwalter.jsp`. HTML tablo: Decimal, Hex, Glyph (görsel), ASCII, Orthography. ROOT ve LEM için "extended Buckwalter" kullanıldığını `https://corpus.quran.com/documentation/morphologicalfeatures.jsp` söyler | Doğrudan dosya (girişsiz, 200): `data/gelen/qac-belge/2026-11-12/buckwalter.html` | 24.018 bayt, SHA-256 `5de168205dad216f001c95e6f760541b7798aef60548f235229aa8c3e6c2c972`; 35 harf görseli. Arapça karakter görselden değil, Decimal ve Hex sütunundan üretilir | `en.wikipedia.org/wiki/Buckwalter_transliteration` (yalnız çapraz kontrol: 29 harf girdisi; hareke ve Kur'ânî işaretler eksik olabilir) |
| QAC etiket kümesi sayfası (`qac-belge`; dalga 0 listesinin kaynağı) | Quranic Arabic Corpus etiket kümesi: `https://corpus.quran.com/documentation/tagset.jsp` (Nominals, Verbs, Particles, Disconnected Letters; zamir etiketleri PRON, DEM, REL). Özellikler sayfası `morphologicalfeatures.jsp` | Doğrudan dosya (girişsiz, 200): `data/gelen/qac-belge/2026-11-12/tagset.html` | 22.874 bayt, SHA-256 `2e39d087e629c360ecba4c1799fe84aa42115134205e2e16e7c17c3970c59ef6`; sayfa 44 etiket listeler, v0.4 dosyasında 45 farklı TAG ölçüldü (fark `DET` olabilir; `morphologicalfeatures.html` 29.965 bayt, SHA-256 `b0153d43005f335368ca2d07b2f74c4070fe74b7952616c351292d34ab9cab29`). A17.1'de küme farkıyla doğrulanır | Yok |
| Türkçe kelime anlamı (K-19: önce hazır kaynak) | QuranWBW Türkçe kelime kelime anlamları: `https://static.quranwbw.com/data/v4/words-data/translations/6.json?version=1` (kimlik 6 = Turkish). JSON: sure → âyet → kelime anlamı dizisi. Adres örüntüsü `marwan/quranwbw` commit `078e978e66ac7258d2d17f997095915d4b7a7223` (2026-10-31) `src/utils/fetchData.js` ve `src/data/options.js` dosyalarından | Doğrudan dosya (200, `application/json`, ETag `61f81923784459470758e14b355df2ca`) | 1.043.145 bayt, SHA-256 `1e4bd7207c0c372f0482190928624d52b8c87f39c35c8b069012ec451ed25032`; 114 sure, 6.236 âyet, 77.429 girdi, boş girdi 0; 6.236 âyetin hepsinde kelime sayısı QAC ile aynı. Uygulama çevirmen adı vermiyor | Yok; hazır anlamı yetmeyen lemmanın anlamını editör yazar (K-50). quran.com kelime çevirisi aynı aileden (63 âyetlik örnekte 766 kelimenin 716'sı aynı) ve Quran Foundation ailesinden olduğu için seçilmedi. `hablullah/data-quran` adresi açılmıyor (404) |
| Lemma ve kök çapraz sayımı (iç denetim) | `mustafa0x/quran-morphology`, commit `8f38b39016824284f9ed16ae15069ff9102c4acf` (2018-06-19), `quran-morphology.txt`: QAC'den türetilmiş, Arapça yazılı lemma ve kök; TAG yalnız N, P, V | Doğrudan dosya: `https://raw.githubusercontent.com/mustafa0x/quran-morphology/8f38b39016824284f9ed16ae15069ff9102c4acf/quran-morphology.txt` | 6.322.866 bayt, SHA-256 `742bfac59941b2cb09736d5b7aae694af50792261fb8450cbf6afafcc340645f`; 130.030 satır, 77.429 kelime, 6.236 âyet, 4.776 LEM, 1.651 ROOT | QUL "Word lemma" (kaynak 75): `https://qul.tarteel.ai/resources/morphology/75` açılıyor, indirme giriş istediği için seçilmedi |
| Kur'an kelime bölmesi (`quran_word` Tanzil satırları) | A11.2'nin yazdığı satırlar; kaynak A10'un `tanzil-uthmani` kaydı | A10 ve A11 | 6.236 âyet; A11'in dilim eşitliği testi yeşil | Yok |
| Cüz sınırları (dalga 1 için Fâtiha ve 30. cüz) | A10'un `tanzil-ust-veri` kaydı; staged `markers.jsonl` (`quran_marker`, `kind = 'cuz'`) | A10 | A10'un G-BUT sonucu | Yok |

Sayılar (77.429 kelime, 6.236 âyet, 4.832 LEM vb.) karşılaştırma bilgisidir; kodda sabit olarak durmaz, testler dosyadan yeniden hesaplar.

Kendimiz yapacağımız işler: QAC segmentlerini kelimeye toplama; Buckwalter eşleme tablosunun kaydedilmiş kaynak sayfadan üretilmesi (Arapça hafızadan yazılmaz) ve `mustafa0x` kopyasındaki Arapça yazımla sınanması; `root`, `lemma` ve `quran_word` QAC alanlarının doldurulması; ÇŞ-1 karşılaştırması; `quran_word_fix` katmanı; lemma envanteri ve `lemma_dalga` (dalga ve sıra); hazır kelime anlamının lemma düzeyinde toplanıp `lemma_gloss` adayına çevrilmesi; QA araçları (Cohen κ, Wilson üst sınırı, standart kitaplıkla); `kelime-kok` paket tanımı. Yapay zekâ istemi ve JSON şeması bu listede yoktur (S-16).

## Adımlar
### A17.0 · Tedarik doğrulaması ve indirme
- Tedarik tablosu indirmeden önce güncellenir: Haiku ve `jsonschema` satırları çıkar (S-16); QAC Buckwalter tablosu ve QAC etiket kümesi sayfaları için adres `arastirmaci` ile doğrulanıp tabloya yazılır.
- `arastirmaci`, tablodaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular: `q-ran/quran` commit'i ve QAC dosyasının boyutu; `static.quranwbw.com` Türkçe dosyasının boyutu ve ETag değeri; `mustafa0x/quran-morphology` commit'i; iki QAC belge sayfası. Açılmayan adresin yerine tablodaki yedek aday kullanılır.
- Dosyaları Claude Code `curl` ile indirir; hiçbir form doldurulmaz (QAC resmî sayfasındaki e-posta formu kullanılmaz; aynı sürümün dosyası GitHub'dan commit sabitli alınır). Her kaynak kendi yeni boş klasörüne iner ve klasörde `SHA256SUMS` (sha256sum biçimi) bulunur:
  - `data/gelen/qac-morfoloji/2026-11-12/quranic-corpus-morphology-0.4.txt`
  - `data/gelen/quranwbw-tr/2026-11-12/6.json`
  - `data/gelen/mustafa0x-morfoloji/2026-11-12/quran-morphology.txt`
  - `data/gelen/qac-belge/2026-11-12/` (Buckwalter tablosu ve etiket kümesi sayfaları)
- Kayıtlar: `pipeline/sources/qac-morfoloji.toml` güncellenir (`surum = "0.4"`, `kaynak_url` indirilen adres, `atif_url` `https://corpus.quran.com/`, `notice_text` dosyanın kendi bildirim bloğundan bayt bayt kopyalanır; içeriği değerlendirilmez, K-42); `quranwbw-tr.toml` (`tur = "kelime_anlami"`) ve `mustafa0x-morfoloji.toml` (`tur = "morfoloji"`) açılır. Her kayıtta ad, adres, sürüm ya da commit ve atıf satırı bulunur; dosya özeti kayıtta değil `SHA256SUMS` dosyasındadır. `mustafa0x-morfoloji` ve `qac-belge` pakete girmez ve veritabanında `source` satırı açılmaz (quran-meta emsali). `export pg` tek dosyalı kaynakta `source.dosya_sha256` ve `source.alinma_tarihi` sütunlarını doldurur.
- Kilitler: `pipeline/src/mutalaa_pipeline/ingest/qac.lock.json` ve `ingest/quranwbw.lock.json` açılır; ilk değerler `ingest ... --kilit-oner` ile önerilir ve indirilen dosyanın özetiyle karşılaştırılır. Kilitlerin ilk değerleri A17.0'dan sonra K-50'ye tarihli not olarak girer (`/karar`).
- Dalga 0 listesi: QAC etiket sayfasından zamir ve harf/edat sınıflarının etiketleri türetilir ve K-50 notuna yazılır (`/karar`).
- Sayım kanıtı: ölçüm betiği `.tmp/a17/` altında durur ve `uv run python -I` ile koşar; dosya yolları argüman olarak verilir (indirilen dosyanın klasöründen yorumlayıcı başlatılmaz).
- **Bitti sayılır:**
  - `sha256sum -c` ve `uv --directory pipeline run mutalaa sources check` 0 ile biter.
  - Ölçüm çıktısı: 77.429 kelime, 6.236 âyet, 114 sure; QuranWBW'de her âyetin kelime sayısı QAC ile aynı.

### A17.G · Göç (`sunucu-gelistirici`, `ef-goc` becerisi; A17.3'ten önce)
- İçerik şeması: `lemma_dalga(lemma_id PK FK, dalga, sira, data_version)` tablosu; kısmi tekil dizinler `lemma(qac_ref) WHERE lang = 'ar'` ve `root(letters_bw)`.
- Sınama ve uygulama:
  - Şema görüntüsü `editoryal-sema.sql`, `MUTALAA_UPDATE_SNAPSHOTS=1` ile yenilenir; `SchemaSnapshotTests` ve `MigrationTests` koşar.
  - Veritabanı değişikliğinden önce yedek alınır (`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1`), sonra `dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api` ve `scripts/test-db.ps1`.
  - Göç ortak yerel veritabanında geri alınmaz; düzeltme yeni göçle yapılır.
- **Bitti sayılır:** `dotnet ef migrations has-pending-model-changes` temiz; iki veritabanında (yerel ve test) yeni tablo var.

### A17.1 · QAC biçimi, kimlik kuralları ve yazı dönüşümü (`hat-gelistirici`)
- QAC dosyası bayt olarak okunur: ASCII denetlenir, CRLF bellekte ayrılır; metin kipi ve yerel kod sayfası kullanılmaz. `data/raw` değişmez. Yapı ve sayım incelenir (değerler günlüğe yazılmaz): dört sütun (LOCATION, FORM, TAG, FEATURES), `(sure:âyet:kelime:segment)` konumu, başta 54 yorum satırı. `LEM:` ve `ROOT:` alanları FEATURES içindedir; kelimenin gövdesi `STEM` bayraklı segmenttir.
- Buckwalter eşlemesi:
  - Tek yaprak modüldür. Tablo, `data/gelen/qac-belge/` altındaki kaydedilmiş QAC sayfasından `-I` ile koşan bir betikle üretilir ve kod noktaları `\u` kaçışıyla yazılır; Arapça harf hafızadan yazılmaz.
  - Sayfanın bir parçası `pipeline/tests/fixtures/qac/` altına alınır; CI testi tabloyu bu parçadan yeniden türetir.
  - Gerçek veri testi, eşlemenin ürettiği kök ve lemma yazımını `mustafa0x-morfoloji` kopyasındaki Arapça yazımla karşılaştırır (farklar sayı olarak raporlanır). Test `Ayarlar().veri_kok` ve `_yok()` desenini kullanır; `-I` alt süreç deseni `test_meal_gercek`'tir.
- Arapça metin: `anchor.metin.kanonik_metin` bir kez uygulanır. `qac_ref` özgün QAC dizgisini korur; `text_clean` `normalize_ar` ile üretilir.
- Kimlik kuralı: `lemma.id` yalnız LEM dizgisinden türetilir (sözcük türü anahtara girmez; ölçümde hiçbir LEM dizgisi birden çok kökle geçmiyor, 175 dizgi köksüz). Var olan `(lang = 'ar', qac_ref)` satırının kimliği korunur; yoksa `max(id) + 1` QAC'deki ilk geçiş sırasıyla verilir. Kök için anahtar `letters_bw`'dir. Testler bu sayıları dosyadan yeniden hesaplar; elle yazılmaz.
- **Bitti sayılır:** eşleme ve kimlik testleri yeşil; kimlikler ikinci çalıştırmada ve boş veritabanında aynı.

### A17.2 · `quran_word` denetimi (A11'in satırları)
- Tanzil kelime bölmesi A11.2'de yazıldı ve `core`'a girdi; bu adım satırları yeniden üretmez. `test_kelime_gercek.py` ve `test_anchor_tanzil.py` (dilim eşitliği) yeşil olmalıdır; psql ile satır sayısı ve âyet kapsamı alınır. Satırlar yoksa (A11.2 bitmemiş) aşama durur ve `/asama A11` önerilir.
- **Bitti sayılır:** satır sayısı ve âyet kapsamı raporda; A11'in testleri yeşil.

### A17.3 · QAC alımı, morfoloji ve sayılar (`hat-gelistirici`)
- Komutlar: `ingest qac` (dosya `data/gelen/qac-morfoloji/<tarih>/` altından alınır, `data/raw/qac-morfoloji/{tarih}/` altına SHA-256 ile yazılır, değişmez), `enrich morphology`, `qa run --source qac-morfoloji`, `export pg --source qac-morfoloji`.
- Yeni dosyalar (`pipeline/src/mutalaa_pipeline/` altında):
  - `ingest/qac.py`: `meal_ortak` yardımcılarıyla.
  - `enrich/morphology.py`: saf işlevler (segment → kelime, gövde lemması, sayılar, `idf_q = ln(6236 / ayah_count)` ve sayı karşılaştırma bilgisidir, dalga ve sıra).
  - `adimlar/enrich_morphology.py`.
  - `qa/run_qac.py` ve `qa/checks/qac.py`: G-KAY; G-BUT (âyet başına kelime sayısı = Tanzil bölmesi, durak işaretleri hariç; LEM tutarlılığı %100; çapraz sayım farkı sayı olarak); G-CAP (`mutalaa_pipeline.anchor` ile `q:s:a:k`). Kelime numarası QAC ve QPC1 konumudur; eşleme tablosu yoktur ([K-43](../../00-ozet/02-karar-defteri.md#k-43--kuran-yapı-verisi-kelime-numarası-işaret-tablosu-ve-aday-satırları) madde 1). Fark çıkarsa G-BUT kırmızı olur ve A11'in bölmesi düzeltilir; birleştirme listesindeki her değişiklik `/karar` ister. QUL ve QUD numaralandırması ayrı açık sorudur (ÇŞ-1, SK-5).
  - `export/pg_qac.py`: tek işlemde sırasıyla `source`, `root`, `lemma`, `lemma_dalga`, ardından `quran_word` QAC sütunlarının (`root_id`, `lemma_id`, `pos`, `features`, `morph_source`) UPDATE'i. `export pg --source qac-morfoloji` yalnız bu QAC sütunlarını UPDATE eder; Tanzil sütunlarına, `source_id` ve `data_version` sütunlarına dokunulmaz (K-43 madde 3'ün genişlemesi).
- QAC lemma ve kökleri `status = 'onayli'`, `origin = 'qac'` girer; `review` açılmaz (K-50 madde 4, K-39 madde 2 benzeri istisna). Sonraki yüklemelerde hat yalnız `occurrences`, `ayah_count`, `idf_q` ve `data_version` sütunlarını günceller; `text`, `qac_ref`, `letters`, `letters_bw` ve `status` değişmişse işlem geri alınır (çıkış 1). Bu istisna Editoryal veritabanı §8 ve `icerik-hatti` becerisinde aynı değişiklikte yazılır.
- Zincir: `ENRICH_ADIMI` (`lineage`, `zincir`); `_anchor_calismasi` ve QA rapor anahtarı adım ve staged özetiyle genelleşir.
- Kancalar: `cli.py`, `qa/__init__.py`, `qa/run.py`, `export/pg.py`, `lineage.py` ve `TEKIL_DIZGELER`.
- **Bitti sayılır:**
  - Her `quran_word.lemma_id` gövde LEM'iyle eşleşir (%100; SQL ve test; Test stratejisi §4).
  - İkinci `export pg --source qac-morfoloji` 0 değişiklik verir.
  - `export pg --source tanzil-uthmani --dry-run` 0 fark verir; `test_qac_sutunlarina_dokunulmaz` yeşil.

### A17.4 · Düzeltme katmanı (`sunucu-gelistirici`; panel `web-gelistirici`)
- `quran_word_fix` önerileri `aday` girer ve `review` (`hedef_tablo = 'quran_word_fix'`) açar. Yayınlayıcı yalnız `onayli` düzeltmeleri uygular (P-09); künye "QAC v0.4 + Mütâlaa düzeltmeleri (N adet)".
- Snapshot okuyucu: QAC sütunları, `root`, `lemma`, anlam içeriği ve düzeltmenin `field` ve `new_value` alanları okunur.
- `PackAssembler`: `word_morph` = QAC tabanı + `IncludedLexicals` içindeki onaylı düzeltmeler (tür dönüşümü yapılır). Düzeltmenin gösterdiği kimlik yoksa kapı kalır.
- `ReviewDecider`: `review.alan` ile `field` eşleşmesi denetlenir. `quran_word_fix` incelemesinde yalnız onay ve red vardır; `new_value` düzenlemesi, "Uzmana gönder" ve adayların kaynağı BÇ-61'e (A18) bırakılır.
- Panel: `quran_word_fix` için ayrı rota açılmaz; kayıtlar A15 panelinin `kuyruk/lemma` rotasında `quran_word_fix` sekmesi olarak girer (süzgeçte `alan` isteğe bağlı) ve kart satırları eklenir ([BÇ-12](../07-belge-celiskileri.md#1-karar-bekleyenler) çözüldü, K-13).
- **Bitti sayılır:** onaylı düzeltme uygulanır, aday ve reddedilmiş uygulanmaz; eşleşmeyen alan reddedilir (test).

### A17.5 · Lemma envanteri, dalgalar ve çapraz sayım (`hat-gelistirici`)
- Sayım kelime düzeyindedir ve gövde lemmasını sayar ([Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md) §2 sorgusuyla aynı). Dalgalar (K-50 madde 7):
  - Dalga 0: lemmanın en sık gövde etiketi QAC etiket kümesinin zamir ya da harf/edat sınıfındadır (liste A17.0'da türetilir).
  - Yüzdeler dalga 0 dışarıda bırakılarak hesaplanır. Dalga 1: sıklıkla ilk %50 ile Fâtiha ve 30. cüz lemmalarının birleşimi; bunlardan dalga 0'a düşenler dalga 0'da kalır. Dalga 2: %80'e, dalga 3: %95'e kadar; dalga 4: kalanlar. Cüz sınırı `tanzil-ust-veri` staged `markers.jsonl` dosyasından alınır.
  - `sira`: dalga içinde kökün toplam geçişine göre azalan (eşitlikte `root.id`), köksüzler sonda; kök içinde lemma geçişine göre azalan (eşitlikte `lemma.id`). Hat yazar, API okur ve sıralar. Dalga 0, dalga 1 ile birlikte açılır.
  - Ön ölçüm (karşılaştırma bilgisi): önceki ölçümde ilk %50'ye 60, %80'e 470, %95'e 2.012 lemma yetiyordu; dalga tablosu sorgudan üretilir.
- İç çapraz sayım: `mustafa0x-morfoloji` kopyasıyla lemma ve kök sayıları QAC ile karşılaştırılır. Kopya yalnız sayım içindir ve pakete girmez.
- Dalga raporu ve çapraz sayım raporu `data/reports/` altına yazılır. Raporlarda yalnız `lemma_id`, `qac_ref`, çapa ve sayı bulunur; metin olmadığını bir test sınar.
- **Bitti sayılır:**
  - `lemma_dalga` dolu; Python sırası Kelime anlamları §2 SQL sorgusunun sırasıyla aynı (veritabanı testi).
  - Fâtiha ve 30. cüz lemmalarının hepsi dalga 0 ya da 1'de.

### A17.6 · Hazır anlam adayları ve QA araçları
- Hat (`hat-gelistirici`):
  - `ingest/quranwbw.py`: her girdiye `anchor.metin.kanonik_metin` bir kez uygulanır ve `provenance` yazılır; ham dosya `data/raw/quranwbw-tr/{tarih}/` altında değişmeden durur.
  - `enrich/glosses.py` ve `adimlar/enrich_glosses.py` (`enrich glosses --wave N`, yalnız hazır kaynaktan toplar): QuranWBW girdisi QAC konumuyla (sure:âyet:kelime) `quran_word` satırına, oradan gövde segmentinin lemmasına eşlenir. Gruplama `normalize_tr` geniş anahtarıyla yapılır (Türkçe İ/ı açık eşlemeyle); `anlam_kisa` kümenin baskın anlamının gerçek kanonik yazımıdır.
  - `qa/run_quranwbw.py`: G-KAY; G-BUT (6.236 âyet, kelime sayıları QAC ile aynı, boş girdi 0, metin yeniden üretilebilir).
  - `export/pg_glosses.py` (`export pg --source quranwbw-tr`): yalnız ekler (`pg_sure_adlari` ve `pg_meal` deseni); onaylı ve reddedilmiş satıra dokunmaz.
- Aday biçimi (K-50 madde 5): her lemma aday olur. `lemma_gloss.status = 'aday'`, `origin = 'kaynak:quranwbw-tr'`, `version = '1'`, `content_hash = sha256(anlam_kisa)` (kanonik metin üzerinden; K-46 madde 4 biçimi, yeni test vektörü gerekmez); `yz_modeli` ve `yz_kaydi` boştur. Her aday için `review` (`hedef_tablo = 'lemma_gloss'`, `alan = 'anlam_kisa'`) açılır: `onerilen = {anlam_kisa, dagilim: [{anlam, sayi}], baskin_pay}`, `guven = baskin_pay`; `dagilim` hedefe uygulanmaz. Baskın pay 0,8 ve üstündeyse lemma "tutarlı", altındaysa "tutarsız hazır anlam" işaretini ve kuyrukta öncelik sırasını alır; eşik aday kümesini değiştirmez. `dogrulanmis` saklanmaz; `status = 'onayli'` olmasından türetilir.
- Düzenle ve onayla (K-50 madde 6, K-48 madde 2 güncellemesi): editör `duzenlenen = {"anlam_kisa": …}` verir; onayda `anlam_kisa`, `content_hash` ve `version` (+1) yenilenir; değer öneriden farklıysa `origin = 'editor'` olur. Metin kendi ürettiğimiz metindir: ilk kayıtta NFC uygulanır.
- Kapsama raporu `data/reports/` altına yazılır: yalnız sayılar (lemma sayısı, tutarlı ve tutarsız aday sayısı, dalga başına dağılım).
- QA araçları (`test-yazari`; Kelime anlamları §7):
  - `qa/uyum.py`: Cohen κ (hedef ≥ 0,60) ve Wilson üst sınırı (öneri ≤ %2); tabakalı seçim A16'nın `qa/ornekleme.py` ortak işleviyle.
  - Komutlar: `qa gloss-sample` (30 maddelik kalibrasyon seti, 300 lemmalık çift değerlendirme, onay sonrası ikinci okuma için en az 300 ya da %10 şablonları) ve şablonları puanlayan komut. Kod `pipeline/src/mutalaa_pipeline/qa/` altındadır.
- **Bitti sayılır:** kapsama raporu üretildi; dalga 0 ve 1 adayları kuyrukta; QA birim testleri yeşil.

### A17.7 · Paket, API, panel ve yayın
- Paket (`sunucu-gelistirici`):
  - `PackCatalog`: `kelime-kok`, `DependsOn [core]`; `qac-morfoloji` sözlük rolüyle `Required`; `quranwbw-tr` atıf, `Required: false`. Satır ve içerik tipleri `PackRows` ve `PackContent`'tedir.
  - İçerik: `word_morph` (QAC sütunları + onaylı `quran_word_fix`), `root` ve `lemma` (`lang = 'ar'`, onaylı), `lemma_gloss` (yeni `origin` sütunuyla), `tr_form` ve `tr_root_index` (A18'e kadar boş).
  - Görünürlük (K-50 madde 8, P-09): `GateEvaluator.DecideLexical` derleme türünü alır (`FlavorPolicy`, `GateReasons`). `lemma_gloss` `onayli` her derlemeye girer; `aday` yalnız `dev` ve `internal`'a `status = 'aday'` ile girer; `red` hiçbirine girmez; `public` pakette `aday` anlam bulunmaz. `quran_word_fix` her derlemede yalnız `onayli` ile uygulanır. `GateInputBuilder.HasContent` ve `ReleaseDigests` sözlük verisini kapsar.
  - Künye: `pack_meta` yeni anahtarı onaylı düzeltme sayısını taşır (`SqlitePackWriter.ExpectedMeta`); `attribution` kaynağıyla bayt bayt aynı kalır (P-11).
  - DDL: `40-kelime-kok.sql` `origin` sütunu; `ddl.test.ts` ve `PackDdlSmokeTests` güncellenir. Sözlük satırlarında `test-` kaynak için P-12 testi.
- API (BÇ-56'nın A17 yarısı; `sunucu-gelistirici`):
  - `GET /api/v1/lemmas/{id:int}`: kök, tür dağılımı, sıklık, dalga ve sıra, aynı kökün onaylı anlamları, KWIC (Tanzil Arapçası ve `meal:elmalili`, `metin_durumu` ile; sık lemmada örneklem).
  - Anlık görünüm, hedef satırın kendi sütunlarıyla genişler (`origin` dahil).
  - Liste `sira=dalga`: yalnız `lemma` ve `lemma_gloss`; türü etiketli imleç; birleşim `lemma.id::text = hedef_anahtar`.
  - `lemma_gloss` için Düzenle ve onayla.
  - Sonra `dotnet build server/Mutalaa.Api -c Release` ve `pnpm --filter @mutalaa/editor gen:api`.
- Panel (`web-gelistirici`):
  - Lemma kartındaki "Bu bilgi API'de henüz yok (A17)" yer tutucuları kalkar ([BÇ-56](../07-belge-celiskileri.md#1-karar-bekleyenler)); güven alanı baskın payı gösterir; kökeni gösteren `origin` satırı eklenir. K-25 rozeti yalnız `yz_modeli` dolu taslağa çıkar.
  - Anlam düzenleme formu, `quran_word_fix` sekmesi ve dalga sırası.
  - "Yeniden taslak iste" `phase = 'S-16'` olur, "Uzmana gönder" BÇ-61'e bağlanır; `OpenQuestionButton` tipi ve testleri güncellenir. Panelin tarayıcıda denetimi kullanıcıya bırakılır.
- Yayın: `publish --flavor dev` gerçek yayın; `internal` ve `public` `--dry-run` ile koşar. Kanıt `gate-report.json`'dadır: `dev` ve `internal`'da `kelime-kok` girer ve aday sayısı görünür; `public`'te P-09 ile dışarıda kalan anlam sayısı aday sayısına eşittir. `ReleaseEndToEndTests` `public` `kelime-kok` paketini açıp `aday` anlam sayısının 0 olduğunu sınar. Paket tanımı A13'te yoksa `sunucu-gelistirici` ekler.
- İnsan işi (İ-12): her dalgada hazır adayların onayı, tutarsız anlamların editörce yazılması, kalibrasyon, çift değerlendirme ve ikinci okuma editör emeğidir ve yalnız o dalganın onay alt adımını bekletir; aşamanın kalanı sürer. `/asama` ilerleme dosyasının Not sütununa dalga numarasını ve bekleyen işi yazar (ör. "İ-12 dalga 1 onayı"). Sonraki dalga `enrich glosses --wave N` ile açılır.
- **Bitti sayılır:**
  - `kelime-kok` `dev` manifestinde; `internal` kuru çalıştırmasında giriyor; `public` kuru çalıştırması 0 ile biter ve `public` paketinde `aday` anlam yok.
  - `phase="A17"` sayısı kaynakta 0; OpenAPI ve `schema.d.ts` yeniden üretimde farksız.

Paralellik: K-50 ve tedarikten sonra hat (A17.1–A17.3) ile sunucu (göç, paket, kapı; sentetik veriyle) birlikte yürür; `qa/uyum.py` bağımsız yazılır. Sıra: göç → `export pg` → A17.5 ve A17.6 → API → panel.

## Kabul ölçütleri
- [ ] Tedarik: dört klasör (`qac-morfoloji`, `quranwbw-tr`, `mustafa0x-morfoloji`, `qac-belge`) `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında; `SHA256SUMS` yeniden hesapta aynı; iki kilit (`qac.lock.json`, `quranwbw.lock.json`) var; `uv --directory pipeline run mutalaa sources check` hatasız; sayımlar `-I` ölçümüyle ve G-BUT'la kanıtlı.
- [ ] A11'in `quran_word` satırları var ve dilim eşitliği testi yeşil; QAC ile âyet başına kelime farkı raporda (0 beklenir).
- [ ] Lemma türetme tutarlılığı %100; `root.id` ve `lemma.id` ikinci çalıştırmada ve boş veritabanında aynı; Buckwalter testi yeşil; Tanzil kuru çalıştırmasında 0 fark.
- [ ] Onaylı `quran_word_fix` uygulanıyor; aday ve reddedilmiş uygulanmıyor; `alan` ve `field` eşleşme testi yeşil.
- [ ] `lemma_dalga` ve dalga raporu sorgudan üretilmiş; Fâtiha ve 30. cüz lemmaları dalga 0 ya da 1'de; çapraz sayım ve kapsama raporları `data/reports/` altında ve metin içermiyor.
- [ ] Dalga 0 ve 1 adaylarında `status = 'aday'` (türetilen `dogrulanmis` = false), `origin = 'kaynak:quranwbw-tr'` ve G-YZ alanları (`yz_modeli`, `yz_kaydi`) boş (psql gruplu sayım).
- [ ] κ, ikinci okuma ve Wilson birim testleri yeşil.
- [ ] BÇ-56'nın A17 yarısı tamam: kaynakta `phase="A17"` sayısı 0; OpenAPI ve `schema.d.ts` yeniden üretimde farksız.
- [ ] `kelime-kok` `dev` manifestinde; `internal` kuru çalıştırmasında giriyor; `public` kuru çalıştırması 0 ile bitiyor ve uçtan uca testte `public` pakette `aday` anlam yok.
- S-16'ya devredilenler (bu aşamanın ölçütü değildir): pilot maliyet onayı, G-YZ "geçti", şema dışı çıktı 0, istem dosyası.

## Doğrulama
```bash
uv --directory pipeline run mutalaa sources check
uv --directory pipeline run mutalaa ingest qac
uv --directory pipeline run mutalaa enrich morphology
uv --directory pipeline run mutalaa qa run --source qac-morfoloji
uv --directory pipeline run mutalaa export pg --source qac-morfoloji      # 2 kez; ikincisi 0 değişiklik
uv --directory pipeline run mutalaa export pg --source tanzil-uthmani --dry-run
uv --directory pipeline run mutalaa ingest quranwbw-tr
uv --directory pipeline run mutalaa enrich glosses --wave 1
uv --directory pipeline run mutalaa qa run --source quranwbw-tr
uv --directory pipeline run mutalaa export pg --source quranwbw-tr        # 2 kez
MUTALAA_DEGISMEZLIK_ZORUNLU=1 uv --directory pipeline run pytest -rs -p no:cacheprovider
uv --directory pipeline run ruff check .
uv --directory pipeline run ruff format --check .
uv --directory pipeline run mypy
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), count(DISTINCT lemma_id), count(DISTINCT root_id) FROM icerik.quran_word;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT status, origin, count(*) FROM icerik.lemma_gloss GROUP BY 1, 2 ORDER BY 1, 2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT dalga, count(*) FROM icerik.lemma_dalga GROUP BY 1 ORDER BY 1;"
dotnet test --solution server/Mutalaa.slnx
dotnet format server/Mutalaa.slnx --verify-no-changes
dotnet build server/Mutalaa.Api -c Release && git diff --exit-code server/Mutalaa.Api/openapi
pnpm --filter @mutalaa/editor gen:api && git diff --exit-code apps/editor/src/api
pnpm lint
pnpm typecheck
pnpm test
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
node --test ".claude/hooks/test/*.test.mjs"
node --test "scripts/ci/*.test.mjs"
```
S-16'ya devredilenler (`llm estimate`, Batch, G-YZ ve şema denetimi) bu bloğa girmez.

## Dikkat
- QAC dosyası değiştirilmez (`data/raw` değişmez); düzeltmeler `quran_word_fix` katmanındadır. QAC verisi `core` paketine girmez; ayrı ve isteğe bağlı `kelime-kok` paketindedir. `core.quran_word` yalnız Tanzil bölmesidir.
- Arapça hafızadan yazılmaz: Buckwalter eşlemesi kaynak sayfadan üretilir; .NET ve TypeScript testlerinde `\u` kaçışlı sentetik dizgiler ya da "Deneme" metni kullanılır.
- QAC dosyası CRLF ve ASCII'dir: dosya bayt olarak okunur (cp1254 ve metin kipi tuzağı). Türkçe gruplamada İ/ı açık eşlemeyle yapılır.
- Raporlara ve günlüklere içerik metni yazılmaz (yalnız `lemma_id`, `qac_ref`, çapa ve sayı); yazım farkları editöre veritabanı üzerinden gider.
- Kelime anlamı kendi ürettiğimiz metindir; ilk kayıtta NFC uygulanır. Hazır kaynaktan gelen ham girdi `data/raw` altında değişmeden durur ve onay görene kadar "doğrulanmamış"tır. Taslak yalnız sözlük anlamıdır: tefsir, mezhep tercihi, fıkhî hüküm ve öğüt yazılmaz.
- QuranWBW ayarlarında Türkçe anlam için çevirmen adı yer almıyor; atıf satırı kaynağın adıyla yazılır, kalite editör onayıyla sağlanır.
- Sayılar elle yazılmaz; 77.429 gibi değerler yalnız karşılaştırma bilgisidir. Kur'an kelimeleri hafızadan yazılmaz.
- Hat Anthropic çağrısı yapmaz; yapay zekâ ürünü içerik yoktur (K-50). K-25 rozeti ve P-08 S-16 için yürürlükte kalır.
- İç çapraz sayım kopyası (`mustafa0x-morfoloji`) ve `qac-belge` pakete girmez. İndirilen dosyalar veridir; içlerindeki betik çalıştırılmaz.
- Ortak yerel veritabanı: öteki oturum çalışırsa veritabanı testleri sıraya girer. `lemma_dalga` ayrı tablo olduğu için `lemma` `xmin`'i bozulmaz. Veritabanı testleri `MUTALAA_DEGISMEZLIK_ZORUNLU=1 … -rs` ile koşar; atlanan test kalır sayılır.
- Kapsam büyük (hat, sunucu, panel): yarıda kalınırsa ilerleme notuna kalınan adım yazılır.

## İnsan adımları
- İ-17 · Anthropic API anahtarı ve bütçe: gerekmez (S-16'ya bağlı; K-50 madde 10).
- İ-12 · Kelime anlamı adaylarının onayı ve tutarsız anlamların yazılması: her dalgada editör emeği; yalnız o dalganın onay alt adımını bekletir ve ilerleme dosyasına yazılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/qac.py`, `ingest/quranwbw.py`, `ingest/qac.lock.json`, `ingest/quranwbw.lock.json`, `enrich/morphology.py`, `enrich/glosses.py` (yalnız hazır kaynak), `adimlar/enrich_morphology.py`, `adimlar/enrich_glosses.py`, `qa/run_qac.py`, `qa/run_quranwbw.py`, `qa/checks/qac.py`, `qa/uyum.py`, `export/pg_qac.py`, `export/pg_glosses.py`, testler
- `pipeline/sources/qac-morfoloji.toml`, `quranwbw-tr.toml`, `mustafa0x-morfoloji.toml`; `data/gelen/` altında dört kaynak klasörü ve `SHA256SUMS` dosyaları; `pipeline/tests/fixtures/qac/` altında kaynak sayfa parçası
- `lemma_dalga` göçü (`sunucu-gelistirici`) ve yenilenen şema görüntüsü
- PostgreSQL'de `quran_word` QAC alanları, `root`, `lemma`, `lemma_dalga`, `lemma_gloss` adayları ve `review` kayıtları
- `data/reports/` altında dalga, çapraz sayım ve kapsama raporları (yalnız sayı ve kimlik)
- `kelime-kok` paketi (`dev` yayını; `internal` ve `public` kuru çalıştırması); `GET /api/v1/lemmas/{id}` ucu, `sira=dalga`, panelde lemma kartı, düzenleme formu ve `quran_word_fix` sekmesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A17-kelime-katmani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A16](./A16-elmalili-meali.md) · Sonraki: [A18](./A18-baglantilar-ve-altin-setler.md)
