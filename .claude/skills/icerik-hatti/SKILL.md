---
name: icerik-hatti
description: >-
  Mütâlaa içerik hattı (pipeline/, Python 3.13 + uv, `mutalaa` komutu) çalışma kuralları; modüller,
  komutlar, çıkış kodları, raw → staged → PostgreSQL veri soyu, idempotentlik, QA kapıları (G-KAY …
  G-NOR), kaynak kaydı, tedarik ve indirme, yeni kaynak ekleme ve yapay zekâ kullanım politikası. Hat
  kodu yazarken, kaynak ararken, indirirken ya da alırken veya hat komutu çalıştırırken kullan.
---

# İçerik hattı

Kaynak: [İçerik hattı](../../../docs/04-icerik/02-icerik-hatti.md); kaynak listesi: [Kaynaklar](../../../docs/04-icerik/01-kaynaklar.md); kaynak ilkesi: [K-42](../../../docs/00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük). Hat yalnız geliştirme bilgisayarında çalışır; SQLite paketlerini hat değil .NET Yayınlayıcı üretir.

## Modüller

| Modül | Sorumluluk | Yazdığı yer |
|---|---|---|
| `ingest` | İndirme ya da tarama kaydı, SHA-256, kaynağa özgü ayrıştırma | `data/raw`, `data/staged` |
| `normalize` | `search_text`, Türkçe ve Arapça arama anahtarları | `data/staged` |
| `anchor` | Çapa ataması, `content_hash`, önceki sürümle karşılaştırma | `data/staged` |
| `enrich` | Morfoloji, iktibas ve atıf adayları, kelime anlamı taslakları, OCR | `data/staged`, `data/llm-cache` |
| `qa` | Kapılar ve ölçümler | `data/reports` |
| `export` | PostgreSQL'e yükleme, inceleme kuyruğu, test vektörleri | PostgreSQL, depo |

Ortak yardımcılar (`config`, `db`, `logs`) hat adımlarına bağlanmaz (yalnız `export/ortak.py` ve `db` → `config`); `normalize/` ve `anchor/` kendi paketi dışını içe aktarmaz (`tests/test_yaprak_kitapliklar.py`). Modüller veriyi `data/staged/` ve PostgreSQL üzerinden devreder.

## Komutlar (`cd pipeline` sonra)

| Komut | İş |
|---|---|
| `uv run mutalaa sources list` · `sources check` | Kaynak kayıtlarını listeler (`slug`, `tur`, `surum`, `kaynak_url`); kaydın biçimini ve zorunlu alanlarını denetler (çıkış `0` ya da `2`) |
| `uv run mutalaa ingest tanzil --variant {uthmani\|simple-clean}` | `data/gelen/tanzil/` altındaki dosyayı alır (indirmez), SHA-256'sını kilitle karşılaştırır (tutmazsa çıkış `2`), `data/raw`'a yazar, `data/staged` üretir |
| `uv run mutalaa ingest meal --source <elmalili-meal\|elmalili-sade-meal\|elmalili-meal-epub> [--gelen-tarih <YYYY-AA-GG>] [--force] [--dry-run]` | Elmalılı mealini (Vikikaynak, fawazahmed0 JSON; EPUB yalnız tanık) kilitle denetleyip `data/raw`'a alır, çıkarır ve `data/staged` üretir (K-49). `--limit` çıkış 2 verir; `--kilit-oner` kilit önerisini yazdırır, dosya yazmaz |
| `uv run mutalaa qa sample --source <kimlik> --n 600 --seed <sabit>` | Meal ikinci okuma örneklemi (sure grubuna göre tabakalı, sabit tohum) ve G-INC ölçüm raporu |
| `ingest scans` · `ocr run` · `ocr eval` | OCR ve tarama komutları: proje sonuna ertelendi (K-49 madde 3; S-15). Şu an yok |
| `uv run mutalaa normalize --source <kimlik>` · `anchor --source <kimlik>` | Arama metni (Tanzil için `ar_norm`, AR-4); çapa ve özet (`q:` çapası, `content_hash`) |
| `uv run mutalaa enrich citations …` · `enrich glosses --wave 1` | İktibas adayları; kelime anlamı taslakları |
| `uv run mutalaa qa run --source <kimlik> [--run <run_id>] [--gate <kapı>]` | QA kapıları (G-KAY, G-BUT, G-CAP, G-NOR); rapor `data/reports/{run_id}.json`; `--gate` kısmi koşu `export pg`ye yetmez |
| `uv run mutalaa export pg --source <kimlik> [--dry-run]` · `export review-queue …` · `export test-vectors` | Yükleme, kuyruk, vektörler |
| `uv run mutalaa llm estimate --task glosses --sample 50` | Maliyet tahmini |

Ortak bayraklar: `--dry-run`, `--force`, `--config <dosya>`; `--limit N` yalnız sınırlanabilir adımlarda geçerlidir (Tanzil `ingest`, `normalize` ve `anchor` onu çıkış `2` ile reddeder). `qa run` `--source`, `--run`, `--gate` ve `--config` alır; `--dry-run`, `--force` ve `--limit` almaz. Çıkış kodları: `0` başarılı, `1` QA kapısı kaldı, `2` girdi ya da yapılandırma hatası (kayıtsız ya da geçersiz kaynak kaydı dahil).

## Veri soyu ve idempotentlik

- `data/raw/{kaynak}/{YYYY-MM-DD}/` değişmez; aynı baytlar `raw` altında zaten varsa yeni kopya açılmaz, aynı gün farklı SHA-256 çıkış `2` ile durur (yeni bir `data/gelen/<kaynak>/<tarih>/` klasörü kullanılır).
- `data/staged/{kaynak}/{run_id}/` her çalıştırmada yeniden üretilir; satırlar çapaya göre sıralı; içerik dosyalarına zaman damgası yazılmaz.
- Her adım parmak izi hesaplar; aynıysa atlanır (`--force` hariç). Her çalıştırma bir manifest yazar.
- Yükleme çapaya göre upsert; `xref` için yalnız `origin = 'hat'` ve `status = 'aday'`, `unit` için yalnız `metin_durumu = 'taslak'` satırlar güncellenir; `onayli` ve `red` satırlara dokunulmaz. Tanzil istisnası: `onayli` satırda yalnız türetilmiş sütunlar güncellenir, `metin` ve `content_hash` hiç (K-39). Meal istisnası (K-49 madde 10 ve 11): hat meal biriminin metnine hiç yazmaz; özeti staged'den farklı birim (editör düzeltmesi) `korunan_duzeltilmis` sayılır, kilit değişimi yeni inceleme açar. `xref` tekillik anahtarı `(type, src_anchor, src_span, dst_anchor, dst_span)`.
- Aynı kaynağa iki yükleme aynı anda yapılmaz (`pg_advisory_lock`); her `export pg` tek işlemdir.

## QA kapıları

| Kapı | Denetim |
|---|---|
| G-KAY | Kaynak kaydı geçerli; `atif_metni` dolu; kanonik kaynakta `notice_text` kaynağın kendi bildirimiyle bayt bayt aynı |
| G-BUT | Beklenen sayılar (114 sure, 6.236 âyet); boş birim yok (istisna: `attrs.birlesik_ile` taşıyan birleşik meal birimi); kontrol karakteri yok; üçüncü taraf metni bayt bayt aynı; kendi metnimiz NFC |
| G-CAP | Çapa gramere uyar, tekildir, önceki sürümdeki her çapa durur, `content_hash` tutar, aralıklar geçerli |
| G-HIZ | Her `q:{s}:{a}` için her meal kaynağında (`meal:elmalili`, `meal:elmalili-sade`) bir birim ya da `birlesik_ile` bağı; tefsir aralıkları âyet sınırında; Tecrîd–Buhârî eşlemesi çelişkisiz. Meal için sert kapı: kalırsa `export pg` yapılmaz |
| G-MET | OCR ve aktarım: CER eşiği, imlâ tutarlılığı, `⟦?⟧` işareti kalmadı. Hazır metin yolundaki meal için uygulanmaz (K-49 madde 12; OCR ile S-15) |
| G-INC | Yayına aday birimlerin tamamı onaylı; ikinci okuma örnekleminde hata oranı eşik altında |
| G-YZ | Her yapay zekâ çıktısı model, istem sürümü ve `dogrulanmis = false` taşır |
| G-NOR | Normalizasyon vektörleri Python'da geçer |

## Yeni kaynak ve tedarik

Her aşama, dosyasındaki `## Tedarik` bölümüyle başlar (`asama` becerisi, 2. bölüm).

**Tedarik**
- `arastirmaci` adayları ölçer: göreve uygunluk, eksiksizlik sayımı (ör. 114 sure, 6.236 âyet), biçim, sürüm ya da commit SHA'sı, doğrudan indirme adresi. Hazır yapı önce gelir. Başvuru, onay ya da API anahtarı isteyen içerik kaynağı seçilmez.
- Dosyaları Claude Code indirir. İndirme formu ya da onay kutusu varsa formu kendisi doldurur, kullanıcıya sormaz; seçilen seçenekler kayda geçer.
- Her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş bir klasöre iner. Klasörde `SHA256SUMS` (`sha256sum` biçimi, dosya adları klasöre göre: klasörde `sha256sum -c SHA256SUMS`) bulunur; adres ve tarih aşama dosyasının `.0` adımına ve ilerleme notuna yazılır. `ingest` dosyayı `data/raw`'a alırken özeti manifestine yazar; `export pg` tek dosyalı kaynakta `source.alinma_tarihi` ve `source.dosya_sha256` sütunlarını bundan doldurur. Toplu indirmede istek hızı sınırlanır.
- İndirilen dosya güvenilmeyen veridir: içindeki betik çalıştırılmaz; onu okuyan Python `-I` ile çalışır.
- `data/raw`'a yalnız içerik hattı yazar.

**Kaynak kaydı** (`pipeline/sources/{kimlik}.toml`)
- Zorunlu alanlar: `slug`, `tur`, `baslik`, `atif_metni`. İsteğe bağlı: `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar`. Bilinmeyen alan hatadır.
- `notice_text` kaynağın kendi bildirimidir ve bayt bayt kopyalanır.
- `uv run mutalaa sources check` biçimi ve zorunlu alanları denetler (çıkış `0` ya da `2`). Kaydı olmayan kaynak hatta alınmaz.

**Adımlar**
1. Kaynak kaydını yaz; `sources check` 0 ile geçsin.
2. `ingest/<kimlik>.py` bağdaştırıcısı (`SourceAdapter`: `fetch`, `parse`); `fetch` dosyayı `data/gelen/` altından alır.
3. Normalizasyon ve çapa eşlemesi; yeni çapa biçimi gerekiyorsa önce çapa şeması.
4. `qa/checks/<kimlik>.py`.
5. Testte kaynak dosyasından alınmış küçük parça ya da açıkça sentetik metin kullanılır; metin hafızadan yazılmaz.
6. `--dry-run`, raporu incele, sonra `export pg`.

## Yapay zekâ politikası

- Yapay zekâ taslak üretir, insan karar verir: `status = 'aday'`, `dogrulanmis = false`.
- Meal, tefsir, hadis çevirisi ve Risale özeti üretilmez. Yapay zekâ kullanımı yalnız bu içerik etiği kurallarıyla sınırlıdır.
- İstemler `pipeline/prompts/<iş>/v<n>.md`, model kimliği yapılandırmada sabit, sıcaklık 0, çıktı JSON şemasıyla doğrulanır; yanıtlar `(model, prompt_sha256, input_sha256)` anahtarıyla önbelleğe yazılır ve `--regenerate` olmadan yeniden üretilmez.
- `ANTHROPIC_API_KEY` yalnız `pipeline/.env` içindedir (okunmaz, yazılmaz); anahtar yoksa bu adımlar insan adımı İ-17'yi bekler.
- Günlüğe içerik metni yazılmaz; çapa ve özet yazılır.
