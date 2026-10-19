---
name: icerik-hatti
description: >-
  Mütâlaa içerik hattı (pipeline/, Python 3.13 + uv, `mutalaa` komutu) çalışma kuralları; modüller,
  komutlar, çıkış kodları, raw → staged → PostgreSQL veri soyu, idempotentlik, QA kapıları (G-LIS …
  G-KUR), yeni kaynak ekleme ve yapay zekâ kullanım politikası. Hat kodu yazarken, kaynak alırken ya
  da hat komutu çalıştırırken kullan.
---

# İçerik hattı

Kaynak: [İçerik hattı](../../../docs/04-icerik/02-icerik-hatti.md). Hat yalnız geliştirme bilgisayarında çalışır; SQLite paketlerini hat değil .NET Yayınlayıcı üretir.

## Modüller

| Modül | Sorumluluk | Yazdığı yer |
|---|---|---|
| `ingest` | İndirme ya da tarama kaydı, SHA-256, kaynağa özgü ayrıştırma | `data/raw`, `data/staged` |
| `normalize` | `search_text`, Türkçe ve Arapça arama anahtarları | `data/staged` |
| `anchor` | Çapa ataması, `content_hash`, önceki sürümle karşılaştırma | `data/staged` |
| `enrich` | Morfoloji, iktibas ve atıf adayları, kelime anlamı taslakları, OCR | `data/staged`, `data/llm-cache` |
| `qa` | Kapılar ve ölçümler | `data/reports` |
| `export` | PostgreSQL'e yükleme, inceleme kuyruğu, test vektörleri | PostgreSQL, depo |

Ortak yardımcılar (`config`, `db`, `logs`) başka modüle bağlanmaz. Modüller veriyi `data/staged/` ve PostgreSQL üzerinden devreder.

## Komutlar (`cd pipeline` sonra)

| Komut | İş |
|---|---|
| `uv run mutalaa sources list` · `sources check` | Kaynaklar ve lisans durumları; kayıt, lisans kopyası, SHA-256, atıf metni denetimi (G-LIS) |
| `uv run mutalaa ingest tanzil --variant uthmani` | İndirir, hash'ler, `data/raw`'a yazar, `data/staged` üretir |
| `uv run mutalaa ingest scans --edition elmalili-1935 --dir data/gelen/elmalili-1935/c01 --cilt 1` | Bir cildin tarama görsellerini `data/raw` altına kaydeder (taramalar önce proje içindeki `data/gelen/` klasörüne konur) |
| `uv run mutalaa ocr run --edition elmalili-1935 --engine <motor> --pages c01:1-40` · `ocr eval --edition elmalili-1935 --gold <klasör>` | OCR (sayfa seçimi cilt niteliklidir) ve CER/WER ölçümü |
| `uv run mutalaa normalize --source <kimlik>` · `anchor --source <kimlik>` | Arama metni; çapa ve özet |
| `uv run mutalaa enrich citations …` · `enrich glosses --wave 1` | İktibas adayları; kelime anlamı taslakları |
| `uv run mutalaa qa run --source <kimlik> [--gate G-CAP]` | QA kapıları |
| `uv run mutalaa export pg --source <kimlik> [--dry-run]` · `export review-queue …` · `export test-vectors` | Yükleme, kuyruk, vektörler |
| `uv run mutalaa llm estimate --task glosses --sample 50` | Maliyet tahmini |

Ortak bayraklar: `--dry-run`, `--force`, `--limit N`, `--config <dosya>`. Çıkış kodları: `0` başarılı, `1` QA kapısı kaldı, `2` girdi ya da yapılandırma hatası, `3` lisans kapısı (`kapali` kaynak ya da `embed_ok = false`).

## Veri soyu ve idempotentlik

- `data/raw/{kaynak}/{YYYY-MM-DD}/` değişmez; aynı gün farklı SHA-256 yeni klasör ve uyarı demektir.
- `data/staged/{kaynak}/{run_id}/` her çalıştırmada yeniden üretilir; satırlar çapaya göre sıralı; içerik dosyalarına zaman damgası yazılmaz.
- Her adım parmak izi hesaplar; aynıysa atlanır (`--force` hariç). Her çalıştırma bir manifest yazar.
- Yükleme çapaya göre upsert; yalnız `origin = 'hat'` ve `status = 'aday'` satırlar güncellenir; `onayli` ve `red` satırlara dokunulmaz. `xref` tekillik anahtarı `(type, src_anchor, src_span, dst_anchor, dst_span)`.
- Aynı kaynağa iki yükleme aynı anda yapılmaz (`pg_advisory_lock`); her `export pg` tek işlemdir.

## QA kapıları

| Kapı | Denetim |
|---|---|
| G-LIS | Kaynak kaydı, tarihli lisans kopyası, atıf metni; durum `kapali` değil |
| G-BUT | Beklenen sayılar (114 sure, 6.236 âyet); boş birim yok (istisna: `attrs.birlesik_ile` taşıyan birleşik meal birimi); kontrol karakteri yok; üçüncü taraf metni bayt bayt aynı; kendi metnimiz NFC |
| G-CAP | Çapa gramere uyar, tekildir, önceki sürümdeki her çapa durur, `content_hash` tutar, aralıklar geçerli |
| G-HIZ | Her `q:{s}:{a}` için bir `meal:elmalili:{s}:{a}`; tefsir aralıkları âyet sınırında; Tecrîd–Buhârî eşlemesi çelişkisiz |
| G-MET | OCR ve aktarım: CER eşiği, imlâ tutarlılığı, `⟦?⟧` işareti kalmadı |
| G-INC | Yayına aday birimlerin tamamı onaylı; ikinci okuma örnekleminde hata oranı eşik altında |
| G-YZ | Her yapay zekâ çıktısı model, istem sürümü ve `dogrulanmis = false` taşır; `embed_ok = false` kaynak çağrıya girmemiş |
| G-NOR | Normalizasyon vektörleri Python'da geçer |
| G-KUR | Kurul kapsamındaki birimin metni değiştiyse "yeniden onay gerekebilir" işareti üretildi |

## Yeni kaynak

1. Lisans defteri kontrol listesi; `pipeline/sources/<kimlik>.toml` (bkz. `lisans-kapisi`).
2. `ingest/<kimlik>.py` bağdaştırıcısı (`SourceAdapter`: `fetch`, `parse`).
3. Normalizasyon ve çapa eşlemesi; yeni çapa biçimi gerekiyorsa önce çapa şeması.
4. `qa/checks/<kimlik>.py`.
5. Serbest kaynakta küçük örnek dosyayla test; korumalı kaynakta yapay yer tutucu metin.
6. `--dry-run`, raporu incele, sonra `export pg`.

## Yapay zekâ politikası

- Yapay zekâ taslak üretir, insan karar verir: `status = 'aday'`, `dogrulanmis = false`.
- Meal, tefsir, hadis çevirisi ve Risale özeti üretilmez.
- `embed_ok = false` kaynağın metni harici API'ye gönderilmez ve gömülmez.
- İstemler `pipeline/prompts/<iş>/v<n>.md`, model kimliği yapılandırmada sabit, sıcaklık 0, çıktı JSON şemasıyla doğrulanır; yanıtlar `(model, prompt_sha256, input_sha256)` anahtarıyla önbelleğe yazılır ve `--regenerate` olmadan yeniden üretilmez.
- `ANTHROPIC_API_KEY` yalnız `pipeline/.env` içindedir (okunmaz, yazılmaz); anahtar yoksa bu adımlar insan adımı İ-17'yi bekler.
- Günlüğe içerik metni yazılmaz; çapa ve özet yazılır.
