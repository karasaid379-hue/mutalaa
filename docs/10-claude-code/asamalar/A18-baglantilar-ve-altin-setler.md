# A18 · Bağlantılar (`xref`) ve altın setler

> **Sürüm:** 1.5 · **Tarih:** 12 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi) · [K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** A16 (A16.4 yeterli: [A16](./A16-elmalili-meali.md) meal birimleri yüklenmiş olmalı; insan turları beklenmez) · [A17](./A17-kelime-katmani.md) · **İnsan adımı:** İ-12 · İ-13
> **Ajanlar:** `arastirmaci` (A18.0 tedarik) · `hat-gelistirici` · `test-yazari` · `sunucu-gelistirici` (yayın süzgeci) · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `metin-butunlugu` · `paket-yayini` · **Tahmini oturum:** 4–5 Claude Code oturumu; etiketleme ayrıca
> **Başlat:** `/asama A18`

## Amaç
Aşama tedarikle başlar (A18.0): Türkçe çözümleme kitaplığı, etimoloji dökümü, hazır benzer âyet verisi, iktibas araçları ve etiketleme arayüzü internetten alınır. Sonra v1 bağlantı türleri içerik hattında üretilir ve `xref` tablosuna aday olarak yazılır: Kur'an içi `kok` ve `lemma`, Tanzil üzerinde kendi n-gram indeksimizle `benzer_ayet`, meal için (taslak birimler dahil) Türkçe kelime → Arapça kök indeksi. Açık atıf ve iktibas motoru yazılır ve sentetik örneklerle sınanır. Altın set araçları ve tür başına kapılar hazırlanır; etiketleme insan işidir (İ-13). Kapıyı geçemeyen türün aday bağlantıları pakete girmez.

## Okunacak belgeler
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §2 katmanlar, §4 `xref` ve upsert, §5 türler, §6 puanlama, §8 yayın kuralı, §13 paketleme
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): tamamı
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §5 Türkçe kelime → Arapça kök hattı, §6 "yalnızca etimolojik", §7 kalite ve IDF
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 altın set değerlendirmesi ve eşikler
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5–§7 (`lemma` Türkçe satırı, `tr_root_index`, `tr_form`, `xref`), §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §4 bağlantıların dağılımı, §7 süzme · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §6 madde 4, §8 yeni kaynak ekleme, §9, §10
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.2 Morfoloji ve QUL (`qac-morfoloji`), §3.8 Diğer (`kaikki-tr`), §5 Yeni kaynak ekleme · [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §4 kalite kapısı kuralları (P-07)

## Kapsam
**Yapılır**
- Tedarik ve indirme (A18.0): kaikki dökümleri, QurSim, NLTK `punkt_tab`, kitaplıklar, kaynak kayıtları.
- Türkçe kelime → Arapça kök hattı meal üzerinde; `lemma` (`lang = 'tr'`), `tr_root_index`, `tr_form`. Bağlantılar taslak meal birimlerinde de üretilir (K-49 madde 15; İ-11 turları A18'i bekletmez): satırlar `aday` kalır ve `public`'e girmez (P-07); birim sonradan onaylanınca bağlantılar yeniden üretilir ve onay yolundan geçer. Hangi mealin (orijinal ya da sadeleştirilmiş) hedef olduğu A18.1'de yazılır; editördeki bağlantı hedefi bugün orijinal mealdir.
- Kur'an içi `kok` ve `lemma` bağlantıları; `benzer_ayet` (sözlüksel, kendi indeksimiz; QurSim çiftleri ek aday kaynak).
- Açık atıf grameri ve iktibas motoru (n-gram, Smith-Waterman, kalıp ve bağlam kuralları); hazır araç karşılaştırması. Gri bölgede dil modeli doğrulaması yoktur: S-16'ya ertelendi ([K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)).
- Altın set biçimi, etiketleme görevleri (hazır arayüz), ölçüm ve kapı raporları; tür bazında yayın süzgeci kararı.

**Yapılmaz**
- Dil modeli (yapay zekâ) işleri: çözülmeyen Türkçe lemma (A18.2) ve gri bölge doğrulaması (A18.4) [S-16](../../08-yol-haritasi/02-sonra-yapilacaklar.md#s-16--yapay-zekâ-ile-taslak-üretimi-kelime-anlamı-türkçe-lemma--kök-gri-bölge-doğrulaması-lügat-kök-anlamı)'ya ertelendi ([K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)). Hat Anthropic çağrısı yapmaz.
- Risale metni üzerinde çalıştırma ve Risale altın seti (Risale metni A20'de gelir). Elmalılı tefsir paragrafları (A37).
- Hadis atıfları ve Tecrîd–Buhârî eşlemesi (A19). `anlamsal` ve `konu` (v1.x). Bağlantılar paneli ve "Önerilen" sırası (cihazda; A25).

## Tedarik
Metin girdileri önceki aşamalardan gelir: Tanzil Uthmani ve Simple Clean (A10), QAC kök ve lemma envanteri (A17), Elmalılı mealleri (A16; birimler `taslak` olabilir, A16.4 yeterli). Bu aşama aşağıdaki yapıları dışarıdan alır. Araştırma ve ölçüm tarihi 2 Kasım 2026; A18.0'da yenilenir.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Türkçe lemmatizasyon | zeyrek 0.1.3 · https://pypi.org/project/zeyrek/ · 29 Aralık 2022 · `zeyrek-0.1.3-py2.py3-none-any.whl` (930.996 bayt) · GitHub `obulat/zeyrek`, etiket `v0.1.3` = `5adc7c7d…` · bağımlılık `nltk`. Daha yeni bir ön sürüm var (`0.1.4a0`, 14 Temmuz 2024); kararlı sürüm seçilir | `pipeline/pyproject.toml` `turkce` grubu; `zeyrek` 0.1.3 ve `nltk` 3.10.3 `pipeline/uv.lock` içinde sabit | Python 3.13.16 ve Windows'ta çalışır (2 Kasım 2026 ölçümü, `punkt_tab` verisiyle). kaikki'deki tek sözcüklü Arapça kökenli Türkçe başlıkların (isim, sıfat, fiil, zarf) 1.303/1.350'si (%96,5) çözümlendi; "Arabic" geçen 3.403 başlıktan 3.000'lik örneklemin %97,1'i; Osmanlıca romanizasyonların (8.613) 3.000'lik örneklemde %68,1'i. Hız yaklaşık 1.000 sözcük/sn. Meal sözcükleriyle kapsama A18.1'de ölçülür | ZemberekDotNet (https://github.com/JnRMnT/ZemberekDotNet, HEAD `8f4785e1…`; etiketli sürümü ve NuGet'te `zemberekdotnet` kimliği yok, kaynaktan derlenir) · zemberek-python 0.2.3 (PyPI, 2 Ocak 2023; 95 MB) · simplemma 2.0.0 (`tr` desteği; yalnız sözlük tabanlı lemma) |
| zeyrek'in Türkçe tokenizer verisi | NLTK `punkt_tab` · https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.zip · 4.319.076 bayt · SHA-256 `e57f6418…0106` · zip (97 giriş, `punkt_tab/turkish/` var) | `data/gelen/nltk-punkt/<YYYY-AA-GG>/` altına iner; `NLTK_DATA` açılmış `nltk_data` dizinini gösterir (ev klasörüne yazılmaz) | zeyrek `lemmatize` tek sözcükte bile Türkçe `word_tokenize` çağırır; veri yoksa `LookupError`. Veriyle ölçüm çalıştı (üstteki satır) | Yok (4,3 MB, tek dosya) |
| Türkçe kelime → Arapça etimon ve kök | kaikki.org (Wiktextract), İngilizce Vikisözlük'ün Türkçe ve Osmanlıca maddeleri, JSONL: https://kaikki.org/dictionary/Turkish/kaikki.org-dictionary-Turkish.jsonl.gz (38.129.580 bayt; açılmış 462.889.173 bayt) ve https://kaikki.org/dictionary/Ottoman%20Turkish/kaikki.org-dictionary-OttomanTurkish.jsonl (34.356.167 bayt); ikisi de 30 Ekim 2026 çıktısı. Yapısal `ety` ve `root` şablonları vardır | `data/gelen/kaikki-tr/<YYYY-AA-GG>/` altına iner; kayıt `kaikki-tr` | Türkçe: 46.254 madde, 42.452 farklı sözcük, 25.365 maddede etimoloji metni; `root` şablonu 1.249 (1.166'sı `tr` → `ar`, 1.073 farklı sözcük); `bor`/`der`/`inh` şablonunda kaynak dil `ar` olan 1.471 sözcük; etimoloji metninde "Arabic" geçen 3.929 sözcük. Osmanlıca: 10.016 madde, 8.848 sözcük, "Arabic" geçen 2.581, `root` 464 | Türkçe Vikisözlük çıkarımı https://kaikki.org/dictionary/downloads/tr/tr-extract.jsonl.gz (45.899.849 bayt; 323.798 Türkçe madde, 23.003'ünde etimoloji metni, 3.601'inde "Arap" geçer; yapısal şablon yok) · ham döküm https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz (3.082.476.978 bayt; `lang_code` `tr` ve `ota` süzülür) · wiktextract'ı İngilizce Vikisözlük dökümünden çalıştırmak (https://github.com/tatuylonen/wiktextract, HEAD `19f9a300…`; döküm https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2, 1.677.020.378 bayt) |
| Hazır benzer âyet verisi | QurSim, filtrelenmiş sürüm · https://github.com/AlsalehAbdullah/QurSim · HEAD `210fbef9…` · `QurSim_filtered.csv` (2.254.930 bayt; sütunlar `ID, SS, SV, Verse1, TS, TV, Verse2, Label`) | `https://raw.githubusercontent.com/AlsalehAbdullah/QurSim/<commit>/QurSim_filtered.csv` → `data/gelen/qursim/<YYYY-AA-GG>/`; kayıt `qursim` (`tur = "baglanti_verisi"`) | 6.915 tekil çift, 114 sure; `Label` 0: 857, 1: 3.510, 2: 2.548; 456 çift aynı sure içinde; kaynak âyet 2.293, hedef âyet 3.111, birleşik 4.114 âyet | QUL "Similar Ayah" (kaynak 74) indirmesi giriş ister, seçilmedi; GitHub'daki kısmi kopya `arriqaaq/ilm` `qul/matching-ayah.json` (373.367 bayt; 3.552 çift, 1.162 kaynak âyet, 107 sure; commit A18.0'da sabitlenir). QurSim'in özgün sitesi textminingthequran.com yanıt vermedi |
| Açık atıf ve iktibas araçları (karşılaştırma, olası sarmalama) | ijaza 2.0.0 (PyPI, 8 Mart 2026; GitHub `memoelsamadony/ijaza`, HEAD `85336e26…`; `ijaza-2.0.0-py3-none-any.whl` 2.813.903 bayt; Python ≥3.9; bağımlılık `rapidfuzz`) · quran-search-in-text 0.1.3 (PyPI, 18 Kasım 2024; 306.587 bayt; bağımlılık `bs4`) · passim 2.0.1 (https://github.com/dasmiq/passim, etiket `v2.0.1` = `ce8f6837…`; yöntem sayfası https://kitab-project.org/methods/text-reuse) | ijaza ve quran-search-in-text geliştirme grubuna (`uv add --directory pipeline --dev`); passim yalnız karşılaştırma gerekirse ayrı ortamda: `pip install git+https://github.com/dasmiq/passim.git` (Java ve Apache Spark gerekir) | PyPI kayıtları 2 Kasım 2026'da okundu; ijaza paketi Kur'an metnini ve normalleştirilmiş dizini içerir (`ijaza/data/quran-verses.json`, `normalized-index.json`); âyet kapsamı (6.236) A18.4 karşılaştırmasında sayılır | QDetect (depo bulunamadı) · quran-verse-detection (https://github.com/fawazahmed0/quran-verse-detection, HEAD `408b5962…`; İngilizce TensorFlow.js modeli, Arapça ve Türkçe metin için uygun değil, seçilmedi) |
| Hizalama (Smith-Waterman) | Önce biopython 1.88 `PairwiseAligner` yerel kipi (PyPI, 6 Ağustos 2026; Python ≥3.10) denenir; kelime düzeyi bulanık eşleşmeyi taşımazsa `rapidfuzz` 3.14.6 ile İktibas tespiti §6'daki uygulama yazılır | `rapidfuzz` `pipeline/uv.lock` içinde sabit; biopython gerekirse `uv add --directory pipeline` | PyPI kaydı: biopython Python ≥3.10, rapidfuzz Python ≥3.11; karar A18.4'te ölçümle | parasail 1.3.4 (PyPI, 17 Şubat 2023) |
| Ölçüm kitaplığı (Cohen κ, kesinlik, duyarlılık, F1) | scikit-learn 1.9.1 (PyPI, 10 Eylül 2026; Python ≥3.11) · `cohen_kappa_score`, `precision_recall_fscore_support` | `uv add --directory pipeline scikit-learn`; sürüm `pipeline/uv.lock` içinde 1.9.1 olarak zaten sabit (`camel-tools` isteğe bağlı grubu çeker) | PyPI kaydı: Windows `win_amd64` tekeri var | statsmodels (`stats.inter_rater`) |
| Etiketleme arayüzü (altın set) | Label Studio 1.23.2 (PyPI, 29 Eylül 2026; Python ≥3.10 ve <4; https://github.com/HumanSignal/label-studio; Docker imajı `heartexlabs/label-studio`, Docker Hub kaydı 30 Ekim 2026'da güncel) | Docker (ayrı hizmet) ya da `uv tool install label-studio==1.23.2`; etiketleyici hesapları yerel kurulumda açılır | İki etiketleyicinin aynı görevi ayrı etiketlemesi ve dışa aktarımda etiketleyen kimliğinin bulunması A18.0'da denenir | doccano 1.8.5 (PyPI ve GitHub, 11 Ocak 2026) · INCEpTION (https://github.com/inception-project/inception) · A15 editör paneline altın set kartı |
| Dil modeli (çözülmeyen lemma, gri bölge doğrulaması) | S-16'ya ertelendi ([K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)); bu aşamada Anthropic çağrısı ve İ-17 yok | — | — | Dil modelsiz yol ana yoldur: çözülmeyen lemmalar doğrudan editör kuyruğuna gider |

Kendimiz yapacağımız işler: izafet, harf-i tarif ve kesme ön bölmesi (zeyrek bunları ayırmaz); Türkçe İ/ı eşlemesi ve iki anahtar (A05 kuralları); QAC kök envanterine eşleme; açık atıf grameri ve iktibas motoru (n-gram indeksi, kalıp ve bağlam kuralları; hazır araçlar Osmanlıca-Türkçe ana metin için tasarlanmadı); sözlüksel `benzer_ayet` indeksi; açıklık örtüşmesi (IoU ≥ 0,5) ölçümü; Label Studio görev dosyalarının üretimi ve etiketlerin içe alınması; yayın süzgeci (Yayınlayıcı).

## Adımlar
### A18.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`) ve sürümlerin güncel olduğunu doğrula: kitaplık sürümleri `pypi.org/pypi/<paket>/json` kaydıyla, kaikki dosyaları `Last-Modified` ve `Content-Length` başlıklarıyla, GitHub depoları `git ls-remote` ile (`api.github.com` kullanılmaz). Açılmayan adresin yerine yedek aday kullanılır; kaikki'nin Türkçe dökümü kaldırılmışsa yedek sırası uygulanır (`tr-extract`, ham döküm, wiktextract).
- Dosyalar yeni boş klasörlere iner (formları Claude Code doldurur):
  - `data/gelen/kaikki-tr/<YYYY-AA-GG>/`: Türkçe (`.jsonl.gz`) ve Osmanlıca (`.jsonl`) dökümleri;
  - `data/gelen/qursim/<YYYY-AA-GG>/`: `QurSim_filtered.csv` (commit sabitlenerek);
  - `data/gelen/nltk-punkt/<YYYY-AA-GG>/`: `punkt_tab.zip`; açmadan önce girişlerde `..` ve mutlak yol olmadığı denetlenir, arşiv aynı klasörde `nltk_data/tokenizers/` altına açılır.
- Her klasörde `SHA256SUMS` (sha256sum biçimi) yazılır. İndirilen dosya veridir; içindeki betik çalıştırılmaz.
- Kaynak kayıtları: `pipeline/sources/kaikki-tr.toml` güncellenir (`tur = "sozluk"`, `surum` döküm tarihi, `kaynak_url` seçilen dosyanın adresi; atıf satırı korunur); yeni `pipeline/sources/qursim.toml` yazılır (`tur = "baglanti_verisi"`, `atif_metni`, `atif_url`). `uv run --directory pipeline mutalaa sources check` 0 hata, 0 uyarı verir.
- Kitaplıklar `uv add --directory pipeline` ile eklenir ya da doğrulanır ve `uv.lock` içinde sabitlenir: `zeyrek==0.1.3` (`turkce` grubu), `scikit-learn`, geliştirme grubunda `ijaza==2.0.0` ve `quran-search-in-text==0.1.3`; sürümler PyPI kaydından doğrulanır.
- Ölçümler yenilenir: zeyrek `NLTK_DATA` ile Python 3.13'te çalışıyor mu; kaikki sayıları tablodakiyle aynı mı (fark varsa tablo güncellenir). `Label` değerlerinin anlamı (0, 1, 2) QurSim makalesinden doğrulanır (https://aclanthology.org/2021.wanlp-1.19/). Label Studio'da iki etiketleyici hesabı aynı görevi ayrı etiketleyebiliyor ve dışa aktarma etiketleyen kimliğini taşıyor mu denenir; olmuyorsa yedek aday seçilir.
- Hazır yapı önce gelir: etiketleme arayüzü ve κ ile kesinlik/duyarlılık hesabı için kendi kodumuz yazılmaz; hizalama için hazır yerel hizalama önce denenir (A18.4).
- **Bitti sayılır:** tablodaki adresler açıldı ya da yedeği kullanıldı; dosyalar `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında ve `SHA256SUMS` yazılı; `kaikki-tr` kaydı güncel, `qursim` kaydı yeni ve `sources check` hatasız; kitaplık sürümleri `uv.lock` içinde.

### A18.1 · Doğrulamalar ve kararlar
- **İlk madde: [BÇ-58](../07-belge-celiskileri.md#1-karar-bekleyenler) kararı.** Ofsetli tabloların (`tr_root_index`, `tr_form`, `xref` ofsetleri) meal metni düzeltmesinde ve kaynak sürümü değişiminde korunması bu aşamanın başında `/karar` ile yazılır. Karar yazılmadan ofsetli tablo üretilmez.
- **Açık iş: [BÇ-61](../07-belge-celiskileri.md#1-karar-bekleyenler).** "Uzmana gönder" düğmesi için durum değeri ve rol yok; `quran_word_fix` adaylarının kaynağı ve `quran_word_fix` incelemesinde `new_value` düzenlemesi tanımlı değil ([K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü) madde 6). Bu aşamanın başında `/karar` ile seçilir; o zamana kadar panelde düğme devre dışı ve "Açık soru" etiketlidir.
- `arastirmaci` doğrular: zeyrek'in `punkt_tab` verisiyle meal sözcükleri üzerindeki çözümleme kapsamı (Python 3.13 ve Windows'ta çalıştığı tedarik ölçümünde görüldü; Kök ve lemma §10 madde 3); kaikki `ety`, `root` ve `etymology_text` alanlarının meal sözcüklerini ne kadar kapsadığı; Tanzil Uthmani ve Simple Clean âyet başı kelime sayısı eşitliği ve imlâî → Uthmani konum eşlemesi (İktibas tespiti §5, §14 madde 3); ijaza, quran-search-in-text ve passim sürümleri (§11).
- Meal kapsaması planlanan eşiği tutmazsa yedek yol (ZemberekDotNet, zemberek-python ya da simplemma) `/karar` ile seçilir. Birim başına bağlantı sayısı N ve `idf_n < 0,2` eşiği (öneri) planda sorulur.
- Eşikler: hedefler Kapsam ve fazlar §8 B-03 ve B-04'tür (İ-22 onayına kadar öneri); tür başına kapı eşikleri Test stratejisi §4 tablosundadır ve B-03 ile uyumludur. İktibas tespiti §10 bu ikisine bağlanır.
- **Bitti sayılır:** kararlar karar defterinde; doğrulama raporu kaynak bağlantılı.

### A18.2 · Türkçe kelime → Arapça kök (meal)
- Kök ve lemma §5 adımları `pipeline/src/mutalaa_pipeline/enrich/` altında (komut öneri: `uv run --directory pipeline mutalaa enrich tr-roots --source elmalili-meal`): belirteç ve iki anahtar (A05), izafet, harf-i tarif ve kesme ön bölmesi, zeyrek lemmatizasyonu (`NLTK_DATA` `data/gelen/nltk-punkt/` altını gösterir; çözümsüz sözcük `analyze` çıktısındaki `Unk` ile ayrılır), kaikki etimolojisi (`data/gelen/kaikki-tr/` dökümlerinden; yalnız eşleme ve madde bağlantısı saklanır), QAC kök envanterine eşleme, çözülmeyenler doğrudan editör kuyruğuna gider (ana yol; dil modeli toplu işi S-16'ya ertelendi, [K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)).
- Türkçe lemmalar `lemma` tablosunda `lang = 'tr'` satırıdır (`ar_lemma_id`, `etymological_only`, `origin`, `status = 'aday'`, `freq`). Her eşleme `review` açar; kart A15'in `kuyruk/lemma` rotasındadır. Onaylı eşlemelerden `tr_root_index` (ofset kanonik metinde kod noktası) ve `tr_form` üretilir.
- "Yalnızca etimolojik" işareti `(tr_lemma, kök)` çiftindedir (§6); örnekleri editör doğrular.
- **Bitti sayılır:** onaylı eşlemelerden `tr_root_index` ve `tr_form` dolu; her `span` meal metni uzunluğu içinde (G-CAP).

### A18.3 · Kur'an içi `kok`, `lemma` ve `benzer_ayet`
- `kok` ve `lemma`: âyetten âyete, Bağlantı modeli §6 formülüyle (`idf_n`, birim-birim skor); birim başına ilk N satır. Girdi QAC envanteri A17'den gelir (`qac-morfoloji`). `lemma` bağlantıları QAC lemmalarıyla %100 tutarlı olmalıdır (Test stratejisi §4).
- `benzer_ayet`: Tanzil üzerinde kendi n-gram indeksimiz; skor `min(1, ortak/7)·(0,5 + 0,5·kapsama)`, `evidence.subtype = 'sozluksel'`. QurSim çiftleri (`data/gelen/qursim/`) ek aday kaynaktır ve `evidence.source_id = 'qursim'` taşır; `Label` ölçeğinin 0–1 eşlemesi A18.0'da makaleden doğrulanır ve Bağlantı modeli §6'daki satır `/belge-esitle` ile eşitlenir. Sözlüksel satırlar kendi indeksimizden gelir.
- Yükleme doğal anahtarla upsert yapar (Bağlantı modeli §4 madde 3); yeni çalışmada üretilmeyen `aday` satır silinir, `onayli` satır "yeniden doğrula" kaydıyla kuyruğa düşer. Her satır `evidence.src_hash`, `dst_hash`, `source_id` taşır.
- **Bitti sayılır:** üç tür `xref` içinde `aday`; lemma tutarlılık testi yeşil; ikinci çalıştırma `onayli` satırlara dokunmuyor (test).

### A18.4 · Açık atıf ve iktibas motoru
- Açık atıf grameri İktibas tespiti §2'yi izler; `SURE_ADI` alternatifleri A11'in onaylı `surah_alias` satırlarından uzunluk sırasıyla derlenir; riskli adlar yalnız güçlü ipucuyla kabul edilir; sure ve âyet sınırı A04 dizisiyle denetlenir. A11'in onayı henüz yoksa gramer yalnız sayısal biçimleri (`(2:255)`, `[2/255]`) tanır; ad tabanlı biçimler onaydan sonra açılır.
- İktibas: Arapça dizilerin çıkarılması (§3), eşleştirme normalizasyonu (§4; A05 kuralları ve iki ek adım), 3–4 gram indeksi Uthmani ve Simple Clean üzerinde (§5), Smith-Waterman genişletme ve âyet sınırında bölme (§6; hizalama için önce hazır yerel hizalama denenir, kelime düzeyi bulanık eşleşmeyi taşımazsa §6'daki uygulama yazılır), kısa ve kalıp ifade kuralları (§7; kalıp listesi editör onaylı dosya), bağlam sinyalleri (§8). `0,40 ≤ confidence < 0,80` aralığındaki gri bölge adayları dil modeliyle doğrulanmaz (§9; S-16'ya ertelendi, [K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)); durum `aday` kalır ve aday editör kuyruğuna gider.
- Hazır araçlar (§11): ijaza ve quran-search-in-text geliştirme bölümünde aynı dizilerle koşulur; passim yöntem karşılaştırması için gerekirse ayrı ortamda denenir. Karar kuralı §11'dedir ve `/karar` ile yazılır.
- Testler sentetik Türkçe paragraflarla yazılır; Arapça diziler dokümandaki örneklerden ya da Tanzil dosyasından betikle alınır, hafızadan yazılmaz. Motor bugün meal üzerinde (taslak birimler dahil; satırlar `aday` kalır, onayda yeniden üretilir) koşar (komut: `uv run --directory pipeline mutalaa enrich citations --target elmalili-meal`; hedef adı öneri); tefsir A37'de, Risale metni A20'de geldikten sonra eklenir.
- **Bağlantı kuyruğu (A15 `kuyruk/baglanti`; [BÇ-56](../07-belge-celiskileri.md#1-karar-bekleyenler)).** A15 paneli aday kartını API'nin verdiği alanlarla çizer; API'de olmayan bölümleri ("Bu bilgi API'de henüz yok (A18)" iletisiyle yer tutan vurgulu dizi, kanıt özeti, alternatifler ve tutarsız → toplu → gri bölge sırası) bu adım API'ye ekler ve yer tutucuları kaldırır. Toplu seçim A15'te kapalıdır (K-13 politika 1; "Açık soru: A18"): toplu karar ve %10 örneklem bileşeni kurulu ve testlidir, `apps/editor/src/screens/baglanti/config.ts` içindeki `BULK_ENABLED` bayrağı kapalıdır, çünkü API aday sınıfını (tutarsız, toplu, gri bölge) vermiyor. A18 sınıf bilgisini API'ye (`GET /reviews` öğesi ya da `hedef` anlık görüntüsü; OpenAPI belgesi güncellenir ve `gen:api` yenilenir) ekleyince bayrak açılır. Toplu karar ucunda `If-Match` yoktur (her öğe `xmin` taşır). Hedefi değiştir, Aralığı düzelt, Tür değiştir, İma ve Kalıp listesi düğmeleri A15'te kapalı "Açık soru: A18" olarak durur; API'deki karşılıkları (K-48 madde 2, bugün 422 `inceleme-desteklenmiyor`) burada kurulur.
- **Bitti sayılır:** motorun birim testleri yeşil; meal koşusu rapor üretiyor.

### A18.5 · Altın setler ve kapılar
- Setler `data/gold/` altında tutulur (git dışı, yedeklenir). Biçim, etiket sınıfları ve iki kişilik bağımsız etiketleme İktibas tespiti §10'u izler; ayrışmayı üçüncü kişi çözer; Cohen κ iki insan etiketleyici arasında raporlanır (scikit-learn `cohen_kappa_score`; yapay zekâ ile etiketleme ve B-04'ün buna bağlı κ ölçümü S-16'dadır); %40 geliştirme, %60 dondurulmuş test.
- Etiketleme arayüzü hazırdır: Label Studio (Tedarik). Claude Code örneklemi seçer, görev dosyalarını `data/gold/` altında üretir ve dışa aktarılan etiketleri içe alır; iki etiketleyici ayrı hesaplarla aynı görevleri bağımsız etiketler. Label Studio A18.0 denemesinde yetersiz kalırsa yedek aday seçilir.
- Bu aşamada hazırlanan setler: kök (300–500 Türkçe lemma → kök çifti; şimdilik meal bandı, sıklık bandına göre tabakalı) ve `benzer_ayet` örneklemi. Atıf ve iktibas setinin biçimi ve görev dosyaları hazırlanır; içerik A37 (Elmalılı tefsir) ve Risale metni (A20) geldikten sonra dolar.
- Ölçüm (komut öneri: `uv run --directory pipeline mutalaa qa gold --type kok`): `prf` (scikit-learn `precision_recall_fscore_support`), açıklık eşleşmesi (aynı hedef ve örtüşme ≥ 0,5; kendi kodumuz), κ. Eşikler Test stratejisi §4 tablosundadır; önceki kabul edilmiş koşuya göre 0,02'den fazla düşüş koşuyu kırar (öneri). Rapor `data/reports/{data_version}.json`.
- Yayın süzgeci: eşik tutmazsa o türün `aday` satırları pakete girmez. Raporun Yayınlayıcı'ya nasıl ulaşacağı dokümanda yoktur; öneri `/karar` ile yazılır ve `sunucu-gelistirici` Yayınlayıcı'ya ekler.
- İnsan adımı (İ-13): kök ve `benzer_ayet` setlerinin etiketlenmesi. Etiketleme bekleyen alt adımdır: ilerleme dosyasının Not sütununa "İ-13 etiketleme bekleniyor" yazılır ve kullanıcıya bildirilir; yalnız ölçüm ve kapı raporu etiketlere bağlıdır, aşamanın kalanı (A18.2–A18.4, A18.6) sürer. Etiketleme bitince ölçüm koşar.
- **Bitti sayılır:** ölçüm araçlarının testleri yeşil; setler etiketlendiyse kapı raporu üretilmiş.

### A18.6 · Yayın
- `publish --flavor dev`: `xref_idx` satırları İçerik paketleri §4 kurallarıyla pakete dağılır; `approved` ve `folded` Bağlantı modeli §6 etiket tablosundan. Yayın kuralı Bağlantı modeli §8 ve P-07'dir: `red` hiç girmez; insan onayı isteyen türdeki (`atif`, `iktibas`, `ima`, `konu`) `aday` satır yalnız `dev` ve `internal`'a girer; `kok`, `lemma` ve `benzer_ayet` `confidence ≥ 0,50` ile `public`'e de girer (`kok` ve `lemma` için Türkçe taraftaki sözlük girdisi onaylı olmalıdır); altın set kapısını geçemeyen türün `aday` satırları pakete girmez. `tr_root_index` ve `tr_form` `kelime-kok` paketine girer.
- **Bitti sayılır:** `dev` manifestinde yeni sürümler; `internal` ve `public` kuru çalıştırmaları 0 ile biter ve kapı raporu insan onayı isteyen türdeki `aday` satırlar için `public`'te "girmedi" yazar.

## Kabul ölçütleri
- [ ] A18.0: `## Tedarik` tablosundaki adresler açıldı ya da yedeği kullanıldı; `data/gelen/kaikki-tr/`, `qursim/` ve `nltk-punkt/` altında dosyalar ve `SHA256SUMS` var; `kaikki-tr` kaydı güncel, `qursim` kaydı yeni; `sources check` 0 hata, 0 uyarı.
- [ ] zeyrek, kaikki dökümü, N, araç seçimi ve yayın süzgeci kararları karar defterinde.
- [ ] `tr_root_index` satırlarının tamamı onaylı eşlemeden; her açıklık metin uzunluğu içinde ve yarı açık (test).
- [ ] `kok`, `lemma`, `benzer_ayet` satırları `xref` içinde; `lemma` tutarlılığı %100; ikinci çalıştırma `onayli` satırları değiştirmiyor, üretilmeyen `aday` satırları siliyor (testler).
- [ ] Her `xref` satırının `evidence.source_id` değeri `pipeline/sources/` altında kayıtlı bir kaynaktır (G-KAY; SQL); `public` kuru çalıştırmasında insan onayı isteyen türde `aday` satır yok (P-07).
- [ ] Atıf ve iktibas motorunun birim testleri yeşil; hat hiçbir yerde dil modeli çağırmıyor (dil modeli toplu işleri ve gri bölge doğrulaması S-16'ya ertelendi, [K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)).
- [ ] Ölçüm araçları (`prf`, açıklık örtüşmesi, κ, gerileme kuralı) testli; etiketleme bittiyse kök ve `benzer_ayet` kapı raporları `data/reports/` altında.
- [ ] `dev` yayını `xref_idx` taşıyor; `internal` ve `public` kuru çalıştırmaları 0 ile bitiyor.

## Doğrulama
```bash
# A18.0: indirilen dosyaların SHA-256 değerleri SHA256SUMS ile aynı olmalı
sha256sum data/gelen/kaikki-tr/<YYYY-AA-GG>/* data/gelen/qursim/<YYYY-AA-GG>/* data/gelen/nltk-punkt/<YYYY-AA-GG>/punkt_tab.zip
# beklenen: "N kayit, 0 hata, 0 uyari"
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline mutalaa enrich citations --target elmalili-meal --dry-run
uv run --directory pipeline mutalaa qa run --source elmalili-meal --gate G-CAP
uv run --directory pipeline mutalaa qa gold --type kok
uv run --directory pipeline pytest
uv run --directory pipeline ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT type, status, count(*) FROM icerik.xref GROUP BY 1, 2 ORDER BY 1, 2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.xref x WHERE NOT EXISTS (SELECT 1 FROM icerik.source s WHERE s.slug = x.evidence->>'source_id');"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.tr_root_index;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
```
`enrich` ve `qa gold` komutları bu aşamada eklenir (öneri); ikinci SQL sorgusu 0 satır beklenir.

## Dikkat
- Âyet ↔ meal ve âyet ↔ tefsir ilişkisi çapadan türetilir; `xref`'e yazılmaz (K-27). Âyet aralığı çapası `xref` ucu olmaz; âyet başına satır ve `evidence.group` kullanılır.
- Uçlar birim düzeyindedir; Kur'an ucunda aralık kelime konumu, metin biriminde kod noktasıdır (`toUnitSpan`).
- Bu aşama Risale metnine dokunmaz (metin A20'de gelir). Testlerde Kur'an, meal ya da Risale metni hafızadan yazılmaz: sentetik paragraflar "Deneme paragrafı" biçimindedir, Arapça diziler Tanzil dosyasından betikle alınır.
- Dil modeli S-16'da gelince yalnız aday puanlar; kararı editör verir (v1'de dil modeli yok). `ima` ve `konu` otomatik yayımlanmaz.
- Reddedilen bağlantı başka yoldan yeniden önerilmez: doğal anahtar `origin` içermez.
- Günlüklere metin yazılmaz.
- zeyrek: `NLTK_DATA` olmadan çalışmaz ve NLTK'nin varsayılan arama yolu ev klasörünü içerir, bu yüzden `NLTK_DATA` proje klasörüne ayarlanır; `lemmatize` çözümsüz sözcüğü kendisi olarak döndürür, çözümsüzlük `analyze` çıktısındaki `Unk` ile anlaşılır; bazı yollarda stdout'a hata ayıklama satırı yazar, çıktı yakalanır; büyük-küçük harf dönüşümü Türkçe İ/ı eşlemesiyle elle yapılır (CLAUDE.md kural 6).
- Paket adları: PyPI'deki `passim` paketi KITAB'ın metin yeniden kullanım aracı değildir, araç GitHub'dan alınır. `quran-search-in-text` proje bağlantıları örnek projeye işaret eder; sürüm PyPI kaydından sabitlenir.
- kaikki'nin Türkçe döküm sayfası "DEPRECATED" notu taşır: dosya kaldırılırsa Tedarik tablosundaki yedek sırası uygulanır.

## İnsan adımları
- İ-13 · Altın set etiketleme: A18.5'te kök ve `benzer_ayet` setleri; atıf ve iktibas seti A37 ve A20'den sonra. Claude Code örneklemi, görev dosyalarını ve ölçümü hazırlar; etiketlemeyi iki kişi yapar. Bekleyen adım yalnız ölçümü ve kapı raporunu bekletir; ilerleme dosyasına yazılır.
- İ-12 · Türkçe kelime → kök eşlemelerinin editör onayı: A18.2'de; kelime anlamı onayıyla aynı editör işidir ([İnsan adımları](../06-insan-adimlari.md)).
- İ-17 (API anahtarı) gerekmez: dil modeli işleri S-16'ya ertelendi ([K-50](../../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)); bağlı aşama S-16'dır.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/enrich/` kök hattı, bağlantı üreteçleri, atıf ve iktibas motoru, kalıp listesi; `qa/` altın set ölçümleri; testler
- `data/gelen/kaikki-tr/`, `qursim/` ve `nltk-punkt/` altında dosyalar ve `SHA256SUMS`; `pipeline/sources/kaikki-tr.toml` (güncel) ve `qursim.toml` kayıtları
- PostgreSQL'de `lemma` (`tr`), `tr_root_index`, `tr_form`, `xref` ve `review` kayıtları
- `data/gold/` setleri (git dışı); `data/reports/{data_version}.json`
- Yayınlayıcıda tür bazında süzgeç (karara göre); `dev` kanalında yeni paket sürümleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A18-baglantilar-ve-altin-setler.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A17](./A17-kelime-katmani.md) · Sonraki: [A19](./A19-hadis-hatlari.md)
