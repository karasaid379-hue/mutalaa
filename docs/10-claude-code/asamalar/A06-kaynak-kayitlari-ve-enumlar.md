# A06 · Kaynak kayıtları ve ortak enum şeması

> **Sürüm:** 1.2 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · **İnsan adımı:** —
> **Ajanlar:** `hat-gelistirici` · `arastirmaci` · `web-gelistirici` · `sunucu-gelistirici` · `inceleyici` · **Beceriler:** `icerik-hatti` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A06`

## Amaç
Her somut kaynak, `pipeline/sources/{kimlik}.toml` kaydıyla depoya girer. Kayıt kaynağın adını, adresini, sürümünü, atıf satırını ve varsa kaynağın kendi bildirimini (bayt bayt) taşır ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 4). `uv run mutalaa sources list` ve `sources check` çalışır. Bundan sonra kaydı olmayan ya da geçersiz kaydı olan kaynak içerik hattına alınamaz (G-KAY; komut çıkış kodu 2). Paylaşılan enum değerleri `packages/content-schema` içindeki tek bir JSON dosyasında durur; Python, TypeScript ve C# karşılıkları bu dosyaya karşı test edilir, PostgreSQL tarafı A07'dedir. Faz 0 çıkış ölçütü "Kaynak kayıtları geçerli" bu aşamayla sağlanır.

## Okunacak belgeler
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): tamamı (§1 kaynak kaydı ve atıf, §2 özet tablo, §3 kaynak kartları, §5 yeni kaynak ekleme: tedarik kontrol listesi ve TOML örneği)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar ve çıkış kodları, §8 yeni kaynak ekleme, §9 G-KAY
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §2 türler, §3 `source` sütunları (TOML alanları aynı adları taşır)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 enum tutarlılığı
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük
- [Backend API](../../02-mimari/05-backend-api.md): §2 (`Content/`, `Links/`, `Releases/`), §7 (enum etiket testi), §10.3 (kapı kontrolleri)

## Kapsam
**Yapılır**
- `pipeline/sources/{kimlik}.toml` kayıtları (25 kayıt).
- `uv run mutalaa sources list` ve `sources check`, `tmp_path` içinde kodla üretilen sentetik fikstürlü testleriyle ve gerçek depoyu sabitleyen testlerle.
- `packages/content-schema/enums.json` ve TypeScript, Python, C# karşılıkları ile testleri.

**Yapılmaz**
- `source` tablosu ve PostgreSQL enum türleri (A07); `source` satırlarının veritabanına yüklenmesi (`export pg`, A10).
- Kaynak dosyalarının indirilmesi ve özetlerinin kaydı: ilgili aşamanın tedarik adımında, `data/gelen/<kaynak>/<YYYY-AA-GG>/` altına, `SHA256SUMS` ile (A10 ve sonrası).
- `test-` önekli sentetik kaynak kayıtları (`test-kucuk`, `test-ses`; A13).
- Henüz seçilmemiş kaynakların kayıtları: somut kaynak seçilince ilgili aşamanın tedarik adımında açılır.
- Yayınlayıcı kalite kapısı mantığı (A13).

## Tedarik
| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Kaynak üst verisi: ad, adres, sürüm, atıf satırı, kaynağın kendi bildirimi | [Kaynaklar](../../04-icerik/01-kaynaklar.md) §2 tablosu ve §3 kartları (25 kimlik); her kaydın `kaynak_url` ve `atif_url` alanı kaynağın kendi adresidir | Kartlardan TOML'a aktarım; kaynak sayfalarını `arastirmaci` okur, dosya indirilmez | `sources check`: `25 kayit, 0 hata, 0 uyari` | — |
| TOML okuyucu | Python 3.13 standart kitaplığı `tomllib` | Ek bağımlılık yok | `pipeline/tests/test_sources.py` yeşil | — |

## Adımlar
### A06.1 · Kayıt şeması ve `sources` komutları (`hat-gelistirici`)
- TOML alanları `source` sütunlarıyla aynı adı taşır (Editoryal veritabanı §3; Kaynaklar §5 örneği). Zorunlu: `slug`, `tur`, `baslik`, `atif_metni`. İsteğe bağlı: `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar`. Başka her alan hatadır.
- Kayıt dosya özeti taşımaz: indirilen dosyanın özeti `data/gelen/<kaynak>/<YYYY-AA-GG>/SHA256SUMS` dosyasındadır. `source` tablosunun 16 sütunundan 12'si kayıt alanıdır; `export pg` tek dosyalı kaynakta `alinma_tarihi` ve `dosya_sha256` sütunlarını ingest manifestinden doldurur, `created_at` ve `updated_at` veritabanında oluşur (Editoryal veritabanı §3).
- `slug` dosya adıyla aynıdır (ASCII, küçük harf, `^[a-z0-9]+(-[a-z0-9]+)*$`); `baslik` ve `atif_metni` boş olamaz. `notice_text` kaynağın kendi bildirimidir ve bayt bayt kopyalanır; kanonik kaynakta bildirimin dosyadakiyle aynılığı G-KAY'ın parçasıdır (A10'da testle kilitlenir).
- `surum` veritabanında zorunludur; TOML'da boşsa alım sırasında doldurulur (A10 ve sonrası; öneri).
- `uv run mutalaa sources list [--format json|tablo] [--kok <dizin>]`: sütunlar `slug`, `tur`, `surum`, `kaynak_url` (ASCII; olmayan değer `-`), `slug` sırasıyla (Ordinal). Yalnız kayıt şemasını denetler; şema hatasında çıkış `2`.
- `uv run mutalaa sources check [--kok <dizin>]`: her TOML ayrıştırılır (UTF-8, BOM'suz, LF); dosya adı `slug` ile aynı ve ASCII; `tur` `enums.json` değerlerinden (`source_kind`); zorunlu alanlar dolu; bilinmeyen alan ve yanlış alan tipi hatadır. Hatalar toplanır, ilki durdurmaz; mesajlar içerik metni taşımaz (alan adı, `slug` ve geçersiz enum etiketi yazılır). Çıkış kodları [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §4: komut yalnız `0` (geçti) ya da `2` (kayıt ya da dosya hatası) ile çıkar. Son satır `sources check: 25 kayit, 0 hata, 0 uyari` biçimindedir.
- Testler (`pipeline/tests/test_sources.py`) `tmp_path` altında kodla üretilen `test-` önekli sentetik kayıtlarla çalışır (`pipeline/tests/fixtures/sources/` klasörü yoktur): geçerli kayıt, bozuk TOML, BOM ve CRLF, UTF-8 olmayan dosya, bilinmeyen tür, bilinmeyen alan, eksik zorunlu alan, boş `atif_metni`, yanlış alan tipi, dosya adı ile `slug` farkı, ASCII olmayan dosya adı, hataların toplanması, çıktının içerik metni taşımaması ve `list` biçimleri.
- Gerçek depoyu sabitleyen testler (aynı dosya): tam 25 kimlik; gerçek depoda `sources check` çıkışı `0` ve `25 kayit, 0 hata, 0 uyari`; `sources list` gerçek depoda çalışır; `notice_text` yalnız iki Tanzil kaydında bulunur ve ikisinde aynıdır.
- **Bitti sayılır:** komut testleri yeşil; `0` ve `2` çıkış kodları sınandı.

### A06.2 · Enum JSON'u ve dil karşılıkları
- `packages/content-schema/enums.json`: A06 beş türü kurar: `xref_type` (8), `xref_status` (3), `xref_origin` (3) (Editoryal veritabanı §2'deki sırayla), `source_kind` (17 değer, TOML `tur` denetimi için) ve `derleme_turu` (`dev`, `internal`, `public`). JSON'daki sıra PostgreSQL etiket sırasıdır ve anlamlıdır. A07 kalan beş türü ekler ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)); dosya 10 tür taşır.
- TypeScript (`web-gelistirici`): `packages/content-schema/src/enums.ts` içinde `as const` dizileri ve birleşim tipleri; Vitest dizileri JSON'la sırasıyla karşılaştırır.
- Python (`hat-gelistirici`): `pipeline/src/mutalaa_pipeline/enums.py` `StrEnum` sınıfları; `pipeline/tests/test_enums.py` JSON'la karşılaştırır; `sources check` bu sınıfları kullanır.
- C# (`sunucu-gelistirici`): `Mutalaa.Domain/Releases` (`BuildFlavor`), `Mutalaa.Domain/Content` (`SourceKind`) ve `Mutalaa.Domain/Links` (`XrefType`, `XrefStatus`, `XrefOrigin`) (Backend API §2). C# adı ile veritabanı etiketi arasındaki eşleme Domain'de saf bir işlevdir: her enum için `...Labels.ToLabel` ve `TryParseLabel` (`BenzerAyet` → `benzer_ayet`); `EnumLabelTests` her değerin etiketini ve sırasını JSON'la sınar (Backend API §7). Domain Npgsql'e bağlanmaz.
- **Bitti sayılır:** üç dilin testi yeşil; JSON'dan bir değer geçici olarak silinince üçü de kırmızı.

### A06.4 · Kayıtlar (`hat-gelistirici`, `inceleyici`)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md) §2'deki her somut kimlik için bir TOML. Değerler tablodan ve §3 kartlarından aynen alınır: `baslik`, `yazar`, `surum`, `provider`, `kaynak_url`, `atif_metni`, `atif_url`.
- `tur` `source_kind` değerlerinden seçilir; belirsiz eşleşme (ör. `risale-kelime-frekans`) kullanıcıya sorulur.
- `notice_text` yalnız kaynağın kendi bildirimi varsa yazılır (ör. Tanzil) ve kaynak dosyasındaki bloktan bayt bayt kopyalanır; dosyadaki bildirimle karşılaştırması kaynak dosyası alındığında yapılır (Tanzil için A10).
- Kaynak kartlarındaki "Doğrulanacak" ve "Açık soru" notları TOML'un `notlar` alanına taşınır; çözümü sahibi olan aşamadadır (ör. Tanzil sürüm numarası A10, Naim'in çevirdiği ciltler A19).
- `inceleyici` `sources list --format json` çıktısını Kaynaklar §2 tablosuyla satır satır karşılaştırır; kimlik ve `tur` farkı sıfır olmalı.
- **Bitti sayılır:** `sources check` 0 ile çıkıyor (`25 kayit, 0 hata, 0 uyari`); karşılaştırma farkı sıfır.

## Kabul ölçütleri
- [ ] Kaynaklar §2'deki her somut kimlik için `pipeline/sources/{kimlik}.toml` var (25 kayıt); henüz seçilmemiş kaynaklar için dosya yok.
- [ ] `uv run mutalaa sources check` 0 ile çıkıyor ve `25 kayit, 0 hata, 0 uyari` yazıyor; bozuk fikstürlerde 2 ile çıktığı pytest'te sınanıyor.
- [ ] Her kayıt zorunlu alanları (`slug`, `tur`, `baslik`, `atif_metni`) taşıyor; kayıtlarda bilinmeyen alan yok.
- [ ] `enums.json` bu aşamada beş türü taşıyor (`source_kind`, `xref_type`, `xref_status`, `xref_origin`, `derleme_turu`); TypeScript, Python ve C# testleri yeşil.
- [ ] `inceleyici` karşılaştırma raporu: kimlik ve `tur` farkı sıfır.
- [ ] Hiçbir kayıt Kur'an, meal, hadis ya da Risale metni içermiyor (gözle); `notice_text` yalnız kaynağın kendi bildirimidir.

## Doğrulama
```bash
uv --directory pipeline run mutalaa sources check; echo "sources check çıkış: $?"
uv --directory pipeline run mutalaa sources list
uv --directory pipeline run mutalaa sources list --format json > .tmp/kaynaklar.json
uv --directory pipeline run pytest && uv --directory pipeline run ruff check . && uv --directory pipeline run mypy src
ls pipeline/sources/*.toml | wc -l                       # 25
pnpm --filter @mutalaa/content-schema test
dotnet test --solution server/Mutalaa.slnx
```

## Dikkat
- Kayıtlarda kaynak metni yoktur: yalnız üst veri, atıf satırı ve kaynağın kendi bildirimi. Kur'an, meal, hadis ya da Risale metni hafızadan yazılmaz.
- Kaynaklar belgesi (`04-icerik/01`) ile TOML kayıtları aynı değişiklikte güncellenir; biri değişip öteki kalmaz (§5).
- Enum sırası anlamlıdır; değer eklemek ya da sırayı değiştirmek `/karar` ister. Yeni değer önce JSON'a, sonra dört dile (TypeScript, Python, C#, PostgreSQL) aynı değişiklikte girer.
- Dosya adları ASCII; TOML UTF-8, BOM'suz, LF.

## İnsan adımları
- Yok. Belirsiz `tur` eşleşmeleri A06.4'te kullanıcıya sorulur.

## Çıktılar
- `pipeline/sources/*.toml` (25 kayıt)
- `pipeline/src/mutalaa_pipeline/` altında `sources/` (`kayit.py`, `liste.py`) ve `enums.py`; `cli.py` içinde `sources list` ve `sources check`; `pipeline/tests/` altında `test_sources.py`, `test_enums.py` (fikstürler testlerde `tmp_path` ile kodla üretilir)
- `packages/content-schema/enums.json`, `packages/content-schema/src/enums.ts` ve testi
- `server/Mutalaa.Domain/Releases/` (`BuildFlavor`), `Content/` ve `Links/` altındaki enum'lar ve etiket eşlemesi; `Mutalaa.Domain.Tests` içindeki enum testi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A06-kaynak-kayitlari-ve-enumlar.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A05](./A05-arama-normalizasyonu.md) · Sonraki: [A07](./A07-editoryal-veritabani.md)
