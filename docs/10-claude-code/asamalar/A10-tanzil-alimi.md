# A10 · Tanzil alımı ve değişmezlik testleri

> **Sürüm:** 1.4 · **Tarih:** 9 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-39](../../00-ozet/02-karar-defteri.md#k-39--tanzil-alımı-simple-cleanin-yeri-kanonik-kaynakta-hat-yazma-kuralı-kilit)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A06](./A06-kaynak-kayitlari-ve-enumlar.md) · [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** —
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `arastirmaci` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · `windows-sorun` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A10`

## Amaç
İçerik hattının ilk gerçek kaynağı olan Tanzil Uthmani ve Simple Clean dosyalarını Claude Code tanzil.net'ten indirir ve hat alır. `q:{sure}:{ayet}` birimleri bayt bayt değiştirilmeden editoryal veritabanına yüklenir. Kilit dosyası, QA kapıları ve değişmezlik testleri Kur'an metninin hiçbir adımda değişmediğini kanıtlar. Bu aşamadan sonra `core` paketinin Kur'an metni hazırdır; paketleme A13'tedir.

## Okunacak belgeler
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): tamamı; özellikle §4 komutlar ve çıkış kodları, §5 veri soyu, §6 idempotentlik, §8 bağdaştırıcı, §9 QA kapıları, §12 çalıştırma manifesti
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 değişmezlik testleri, §14 madde 1
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2 anlam kuralları, §7 kanonik metin ve `content_hash`, §8 ofsetler
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.1 Tanzil kartı, §5 yeni kaynak ekleme
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source`, §4 `unit`, §10 `pipeline_run` ve yükleme
- [Arama](../../03-veri/05-arama-fts5.md): §1.3 Arapça kurallar, §1.4 Kur'an birimleri, §1.5 Arapça tablo (A10.7)
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §6 adım 4, §10.1–§10.2

## Kapsam
**Yapılır**
- `tanzil-uthmani` ve `tanzil-simple-clean` için indirme (A10.0), `tanzil.lock.json`, ham kayıt ve ayrıştırma; `tanzil-uthmani` için normalize, çapa, `content_hash`, QA ve `export pg`. Simple Clean `q:` birimi olarak yüklenmez (`unit.anchor` tekildir); yeri K-39'da yazılıdır (A10.3).
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §5'teki sekiz testin envanteri: 1–4 bu aşamada yazılır, 5–8'in sahibi olan aşama kayda geçer.
- A04'te üretilen gömülü âyet sayısı dizisinin Tanzil metniyle çapraz doğrulanması.
- A05'ten devir: Arama §1.5 Arapça tablosunun Tanzil baytlarıyla vektör satırları (A10.7).
- Gece iş akışı: `.github/workflows/nightly.yml` iskeleti kuruldu (`99526cc`; `sources check` ve `pytest -m degismezlik -rs` koşar, gerçek veri testleri CI'da atlanır, tanzil.net'ten hiçbir şey indirilmez). A10 fikstür testlerini ona ekler; gerçek veriyle koşu yerelde `scripts/nightly.ps1` ile yapılır.

**Yapılmaz**
- Sure adları, cüz, secde ve Medine sayfa eşlemesi (A11). Kelime bölmesi ve `quran_word` (A11 ve A17).
- Paket DDL'i ve FTS5 tabloları (A12). `core` paketinin üretimi ve Tanzil bildiriminin pakete yazılması (A13).
- Okuyucunun metin seçicisi testi (test 5; `reader-core` ile A24).
- Tanzil `quran-data.xml` üst veri dosyasının kalıcı alımı (A11.0). A10 yalnız A04'ün ondan ürettiği `shared/data/ayet-sayilari.json` ile çapraz denetim yapar.

## Tedarik
Adresler 2 Kasım 2026'da açıldı (HTTP 200); sayılar aynı günkü ölçümdür ve 1 Kasım 2026 ölçümüyle bayt bayt aynı çıktı. Seçim ölçütü eksiksizlik, biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirliktir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)).

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Kur'an metni, Uthmani (`tanzil-uthmani`, kanonik) | Tanzil Project, "Uthmani", "Text (with aya numbers)". Form sayfası `https://tanzil.net/download/` (7.115 bayt; 31 Ekim ve 2 Kasım 2026'da bayt bayt aynı), işlem adresi `https://tanzil.net/pub/download/index.php`. Dosya başlığı "Tanzil Quran Text (Uthmani, Version 1.1)"; güncellemeler sayfasında (`https://tanzil.net/updates/`) 1.1, 12 Şubat 2021. UTF-8, LF, BOM yok; âyet satırı dik çizgiyle ayrılmış sure, âyet ve metindir. | GET isteği, form alanlarıyla: `marks=true&sajdah=true&tatweel=true&quranType=uthmani&outType=txt-2&agree=true`. Bu, formun açılıştaki hâlidir: `marks`, `sajdah`, `tatweel` işaretli; `rub` ve `stanween` işaretsiz (`stanween` yalnız `me_quran` yazı tipi içindir). `agree` onay kutusudur ve Claude Code işaretler. `alef` ve `laa` formda yoktur; adrese eklenseler de dosya değişmez. Dosya adı yanıt başlığından gelir (`quran-uthmani.txt`). Hedef: `data/gelen/tanzil/<YYYY-AA-GG>/quran-uthmani.txt` | 1.396.087 bayt; SHA-256 `6933e133dd56db778c801bf738848454e43648105a151e8d84d86a7cae39ec5f` (1 ve 2 Kasım 2026'da üç ayrı istekte aynı). 6.266 satır: 6.236 âyet satırı (114 sure, her surede âyetler 1'den kesintisiz; sure sure sayım `shared/data/ayet-sayilari.json` ile aynı), 2 boş satır, 28 `#` bildirim satırı (6.237–6.266. satırlar); `\r` ve BOM yok; katı UTF-8; NFC olmayan âyet 5.782 (NFC uygulanmaz). 82.260 boşlukla ayrılan belirteç; `rub` işareti yok, secde işareti 15. `data/backups/gelen/tanzil/quran-uthmani.txt` (1.409.970 bayt, SHA-256 `aa0bf9278a177a12e6d9bef621ce37a1d24fa35168b5ae9c13ebcbe01e3686cf`) başka dosyadır: `rub=true&stanween=true` ile alınan çıktıyla aynıdır. | GitHub `dotquran/corpus`, commit `c23f5cec2e95e253dc450bd0f34d09e37ba40fac`, `src/resources/uthmani.txt` (1.396.087 bayt; SHA-256 form çıktısıyla aynı). GitHub `jatoi94912/Quran-data`, commit `ee21120024dcb6b9903f9ff05e77c32ca5ee8e92`, `quran-uthmani.txt` (SHA-256 aynı). Internet Archive `quran-uthmani_20250625` (`https://archive.org/download/quran-uthmani_20250625/quran-uthmani-aya.txt`, 1.396.087 bayt, SHA-256 `edd7c64865216d0d94b7426338275dc226af7d5f58bc0cd8435d683e9fa8d38f`): âyet satırları aynı, bildirimdeki yıl satırı farklı (2007-2025) |
| Kur'an metni, Simple Clean (`tanzil-simple-clean`, arama tabanı) | Tanzil Project, "Simple (Clean)", "Text (with aya numbers)"; aynı form ve işlem adresi. Dosya başlığı "Tanzil Quran Text (Simple Clean, Version 1.1)"; güncellemeler sayfasında ayrı Simple Clean girdisi yok, sürüm dosya başlığından alınır. | GET isteği: `marks=true&sajdah=true&tatweel=true&quranType=simple-clean&outType=txt-2&agree=true` (tarayıcı formu da bu alanları gönderir; `tatweel` kutusu bu türde gizlidir ama işaretli kalır). `rub=true` dosyayı değiştirir; `stanween` bu türde etkisizdir. Dosya adı `quran-simple-clean.txt`. Hedef: `data/gelen/tanzil/<YYYY-AA-GG>/quran-simple-clean.txt` | 794.313 bayt; SHA-256 `054b3d9f79c0c2e44df7f9ddf42561797b3b5cb4fbdafbf2e99c805ccf1a6b49` (1 ve 2 Kasım 2026'da aynı). 6.266 satır: 6.236 âyet satırı (114 sure, kesintisiz; sayım Uthmani ve `ayet-sayilari.json` ile aynı), 2 boş satır, 28 `#` bildirim satırı; `\r` ve BOM yok; katı UTF-8; NFC olmayan âyet 0; 82.627 belirteç. `data/backups/gelen/tanzil/quran-simple-clean.txt` (794.910 bayt, SHA-256 `1862ee63c70fbfc6285e0bb0b9587b89beb5b7891109a4d543d9d2cf8283e8c8`) başka dosyadır: `rub=true` ile alınan çıktıyla aynıdır. | GitHub `dotquran/corpus`, commit `c23f5cec2e95e253dc450bd0f34d09e37ba40fac`, `src/resources/simple-clean.txt` (794.313 bayt; SHA-256 form çıktısıyla aynı). `jatoi94912/Quran-data` yalnız Uthmani taşır; ikinci bir Simple Clean aynası bulunmadı |
| Âyet sayısı dizisi (çapraz denetim) | `shared/data/ayet-sayilari.json`: A04'te Tanzil `quran-data.xml` (sürüm 1.0, `https://tanzil.net/res/text/metadata/quran-data.xml`) dosyasından üretildi; `sha256` alanı `8867c1d88191472adec9db694b3cd9f135b1a2ef580574d32cf888dcb22c5c7a` | Depoda hazır, yeni indirme yok. XML'in kalıcı alımı A11.0'dadır | 114 eleman, toplam 6.236; iki Tanzil dosyasının sure sure sayımıyla aynı (2 Kasım 2026). XML aynı gün yeniden indirildi: 77.234 bayt, SHA-256 aynı | Tanzil `quran-data.js` (A11.0 yedeği) |
| Hat bağımlılıkları ve araçlar | Yeni kitaplık eklenmez: `typer`, `pydantic-settings`, `psycopg[binary]`, `httpx` (çalışma), `pytest`, `ruff`, `mypy` (geliştirme); sürümler `pipeline/pyproject.toml` ve `pipeline/uv.lock` içinde. İndirme ve özet: `curl`, `sha256sum` (Git Bash ile gelir) | `uv sync` (A02, A07); `curl` ve `sha256sum` Git Bash'te hazır | `uv --directory pipeline run pytest` ve `ruff check .` yeşil; `curl` ve `sha256sum` Git Bash'te çalışıyor (2 Kasım 2026 örnek indirmeleri) | `httpx` (hat içinden indirme gerekirse) |

**Kendimiz yapacağımız işler:** bağdaştırıcı ve kilit dosyası, QA kapıları, değişmezlik testleri, `ar.jsonl` Tanzil satırları betiği, gece iş akışına fikstür testleri ve `scripts/nightly.ps1`. Ayrıştırma bayt düzeyinde on satırlık işlemdir ve K-26 gereği (NFC, kırpma ve satır sonu çevirisi yok) kitaplığa bırakılmaz (`ingest/tanzil_bicim.py`).

## Adımlar
### A10.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` Tedarik tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular: form sayfası (`https://tanzil.net/download/`; alanlar `marks`, `sajdah`, `rub`, `tatweel`, `stanween`, `quranType`, `outType`, `agree`), güncellemeler sayfası (`https://tanzil.net/updates/`; Uthmani için 1.1, 12 Şubat 2021), GitHub aynaları (`git ls-remote https://github.com/<sahip>/<depo>.git HEAD`; commit tablodakinden farklıysa dosyanın boyutu ve SHA-256'sı yeniden ölçülür) ve Internet Archive kaydı. Açılmayan ya da değişen adresin yerine tablodaki yedek aday kullanılır; ayna kullanılırsa SHA-256 yine ölçülür ve kayda "ayna" diye yazılır.
- Claude Code formu kendisi doldurur ve iki dosyayı yeni boş `data/gelen/tanzil/<YYYY-AA-GG>/` klasörüne indirir; istekler arasında en az 3 saniye bekler:
  ```bash
  D=data/gelen/tanzil/$(date +%F); mkdir -p data/gelen/tanzil && mkdir "$D"
  curl -sS --max-time 90 -o "$D/quran-uthmani.txt" 'https://tanzil.net/pub/download/index.php?marks=true&sajdah=true&tatweel=true&quranType=uthmani&outType=txt-2&agree=true'
  sleep 3
  curl -sS --max-time 90 -o "$D/quran-simple-clean.txt" 'https://tanzil.net/pub/download/index.php?marks=true&sajdah=true&tatweel=true&quranType=simple-clean&outType=txt-2&agree=true'
  sha256sum "$D"/quran-*.txt | sed "s#$D/##" > "$D/SHA256SUMS"
  ```
- Tam adresler, indirme tarihi ve form seçenekleri bu adımın sonuna ve ilerleme notuna yazılır; seçenekler `tanzil.lock.json` içinde de durur (A10.2).
- Ölçüm: 6.236 âyet satırı, 114 sure, her surede âyetler kesintisiz, sure sure sayım `shared/data/ayet-sayilari.json` ile aynı, `\r` ve BOM yok, katı UTF-8, bildirim bloğu 6.237–6.266. satırlar. Sonuç aşağıdaki ön ölçümle aynıysa devam edilir; farklıysa fark bildirimde mi metinde mi olduğu ölçülür ve ilk kilit değerleri buna göre `/karar` ile yazılır.
- SHA-256 `data/backups/gelen/tanzil/` kopyalarıyla karşılaştırılır. Kopyalar form açılışıyla alınmamıştır (`rub` ve `stanween` işaretli); bu yüzden özetleri farklıdır: Uthmani için `aa0bf927…` ↔ `6933e133…`, Simple Clean için `1862ee63…` ↔ `054b3d9f…`. Karşılaştırma sonucu ilerleme notuna yazılır; kopyalar silinmez.
- **Ön ölçüm (2 Kasım 2026, ayrı örnek indirme; `outType=txt-2`, `agree=true` ve `marks`, `sajdah`, `tatweel` hepsinde işaretli):**

  | `rub` / `stanween` | Uthmani (bayt) | Simple Clean (bayt) |
  |---|---|---|
  | ikisi de işaretsiz (seçilen) | 1.396.087 | 794.313 |
  | yalnız `rub` | 1.396.684 | 794.910 |
  | yalnız `stanween` | 1.409.373 | 794.313 |
  | ikisi de işaretli | 1.409.970 | 794.910 |

  `rub` 199 işaret ekler; `stanween` yalnız Uthmani'de bayt ekler ve belirteç sayısını değiştirmez.
- Kaynak kayıtları: `pipeline/sources/tanzil-uthmani.toml` ve `tanzil-simple-clean.toml` güncellenir. `kaynak_url` form sayfasıdır (`https://tanzil.net/download/`); `surum` dosya başlığındaki sürümdür (iki dosyada da "Version 1.1"); `notlar` form seçeneklerini ve indirme tarihini taşır. `notice_text`, dosyadaki bildirim bloğunun (6.237–6.266. satırlar) baytlarının katı UTF-8 çözümüdür (K-39 madde 6): `ingest/tanzil_bicim.py` içindeki `ayristir(...).bildirim` ile çıkarılır ve betikle TOML'a kopyalanır, elle yazılmaz; baştaki iki boş satır ve satır sonu boşlukları korunur. TOML çok satırlı değişmez dizgede açılıştan hemen sonraki ilk LF atıldığı için bayt eşitliği G-KAY ile sınanır (A10.5).
- Kitaplık sürümleri `pipeline/uv.lock` kaydındadır; bu aşama yeni bağımlılık eklemez.
- **Bitti sayılır:** iki dosya ve `SHA256SUMS` `data/gelen/tanzil/<YYYY-AA-GG>/` altında; SHA-256 ve ölçümler ilerleme notunda; yedek kopyalarla karşılaştırma yazılı; iki kayıt güncel ve `uv --directory pipeline run mutalaa sources check` 0 hata, 0 uyarıyla bitiyor.

### A10.1 · Biçim ölçümü, sürüm ve belge eşitleme
- `ingest/tanzil_bicim.py` içindeki `VARSAYIM (olculecek: A10)` işaretleri ölçülen düzenle değiştirilir: 6.236 âyet satırı, ardından 2 boş satır ve 28 `#` satırı (bildirim bloğu `konum = "son"`); dosya LF ile biter. Biçim testleri dosyadan betikle kesilmiş parçayla yazılır.
- Simple Clean sürümü: dosya başlığı "Version 1.1" der, güncellemeler sayfasında ayrı girdi yoktur. Kayıttaki `surum = "1.1"` dosya başlığından alınmıştır; [BÇ-37](../07-belge-celiskileri.md#1-karar-bekleyenler) ve Kaynaklar §3.1'in ilgili "Doğrulanacak" maddesi `/belge-esitle` ile kapatılır.
- Çözülen öteki "Doğrulanacak" maddeleri (indirme adresi ve form seçenekleri, bildirim satırlarının biçimi, güncellemeler sayfası) `/belge-esitle` ile Kaynaklar §3.1'e işlenir.
- A11'in kullandığı Tanzil örneği beş kutulu kopyadır (1.409.970 bayt, 82.459 belirteç). Seçilen dosyanın değerleri (1.396.087 bayt, 82.260 belirteç, `rub` işareti yok) ilerleme notuna yazılır; A11 sayılarını bu dosyayla yeniden doğrular.
- **Bitti sayılır:** `tanzil_bicim.py` içinde `VARSAYIM` işareti kalmadı ve biçim testleri yeşil; BÇ-37 `çözüldü`; Kaynaklar §3.1 güncel.

### A10.2 · Kilit dosyası ve bağdaştırıcı
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py`: [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §8'deki `SourceAdapter` (`fetch`, `parse`) ve `run_ingest` içindeki kaynak kaydı denetimi (`require_sources`, G-KAY; kayıtsız ya da geçersiz kayıtta çıkış `2`). `ingest/base.py` (`SourceAdapter`, `run_ingest`, `staged_yaz`) ve `ingest/tanzil_bicim.py` (K-39 madde 7 biçimi) kodda hazırdır (`fca0c57`, `9a4e8a5`).
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.lock.json`: varyant başına `url`, `sha256`, `metin_sha256`, `bildirim_sha256`, `boyut`, `surum`, indirme seçenekleri ve alınma tarihi (K-39 madde 4; Test stratejisi §5 madde 1). `--kilit-oner` ilk değerleri yazdırır; kilit yalnız `/karar` ile yazılır ve değişir, ilk değerler K-39'a tarihli notla eklenir.
- `fetch` dosyayı `data/gelen/tanzil/<YYYY-AA-GG>/` altından alır, kilitle karşılaştırır ve ancak ondan sonra `data/raw/tanzil-{varyant}/{YYYY-MM-DD}/` altına kopyalar; `fetch.json` üretir. Dosya özeti kilitle tutmazsa komut her durumda `2` ile çıkar; ileti farkın bildirimde mi metinde mi olduğunu söyler ve "yeni Tanzil sürümü kilit güncellenerek (`/karar`) alınır" uyarısını basar.
- `parse` dosyayı bayt olarak okur, yalnız `b"\n"` ile böler, satırı katı UTF-8 ile çözer. NFC, `strip()`, `str.splitlines()` ve satır sonu çevirisi yoktur; `\r`, BOM ya da tanımsız satır görülürse komut `2` ile çıkar (K-39 madde 7). Bildirim satırları birimlere girmez; tam metni `notice.txt` olarak staged klasörüne yazılır ve `source.notice_text` alanına aynen aktarılır.
- Her birimin kaynak dosyadaki yeri (`file`, `line`) `provenance` içinde tutulur; `kaynak[başlangıç:bitiş] == text` eşitliği QA'da denetlenir ([Çapa şeması](../../03-veri/01-capa-semasi.md) §7).
- Kilit yazılınca `pipeline/tests/test_degismezlik.py` içine `sha256(notice_text) == bildirim_sha256` denetimi eklenir (`notice_text` TOML kaydından ve `notice.txt` dosyasından okunur; A10.6 madde 1).
- Bağdaştırıcı birim testleri depodaki küçük bir Tanzil parçasıyla yazılır. Parça dosyadan betikle kesilir, elle yazılmaz; bildirim satırları korunur.
- **Bitti sayılır:** `uv run mutalaa ingest tanzil --variant uthmani` ve `--variant simple-clean` 0 ile çıkıyor; `data/staged/` altında 6.236'şar satırlık `units.jsonl` ve çalıştırma manifesti var.

### A10.3 · Simple Clean'in yeri (karar)
- **Karar: K-39 (28 Ekim 2026).** Simple Clean `q:` birimi olmaz, yalnız `ar_norm` kaynağıdır; `icerik.source` tablosuna birimsiz bir satır olarak yüklenir. Kanonik kaynakta hat yazma kuralı, `source` satırı güncelleme kuralı, sıkı kilit, AR-4 ve bildirim metni de aynı kararda.
- `q:` çapası yalnız Uthmani metni gösterir ve `unit.anchor` tekildir. `core` paketinde Simple Clean ayrı birim ya da sütun değildir; normalize hâli `unit_search.ar_norm` sütunundadır (İçerik paketleri §3.2, Arama §1.4). Simple Clean `data/raw` ve `data/staged` içinde kalır ve yalnız Kur'an birimlerinin `ar_norm` sütununu besler; `ar_norm` taşıyan paket Simple Clean'i de kaynak sayar (kaynak kaydı ve atıf satırı). Pakette tutulup tutulmayacağı A12'de karara bağlanır.
- **Bitti sayılır:** karar defterinde Simple Clean'in yeri yazılı (K-39).

### A10.4 · Normalize, çapa ve yükleme
- Önce `test -f pipeline/.env && echo var`. Dosya yoksa PostgreSQL'e bağlı işler (`export pg`, değişmezlik testi 3'ün PostgreSQL yarısı) atlanır ve kullanıcıdan A03'teki kopyalama istenir; dosya adımları sürer. Claude Code `.env` dosyası oluşturamaz ve okuyamaz. Hat yapılandırması `pipeline/src/mutalaa_pipeline/config.py` (pydantic-settings, `fca0c57`) `MUTALAA_DB_URL` değerini ortamdan ya da `env_file` olarak `pipeline/.env` dosyasından okur (İçerik hattı §3 öncelik sırası). pydantic-settings `.env` değerlerini `os.environ`'a yazmaz; bu yüzden testler ve komutlar bağlantı dizesini yalnız `config.py`'den alır. Dosya yolu paketin konumundan çözülür, çalışma dizinine bağlı değildir (öneri). Değer koda, günlüğe ve rapora yazılmaz.
- `data/staged` satırlarında `content_hash` 64 küçük harfli onaltılık karakterdir; `sha256:` öneki yazılmaz (Editoryal veritabanı §4'teki CHECK kısıtı).
- `uv run mutalaa normalize --source tanzil-uthmani`: `ar_norm`, A05'teki Python normalleştiricisiyle Simple Clean âyet metninden üretilir ([Arama](../../03-veri/05-arama-fts5.md) §1.4). Uthmani biçimlerinin sona eklenmesi (AR-4) bu aşamada uygulanır ([K-39](../../00-ozet/02-karar-defteri.md#k-39--tanzil-alımı-simple-cleanin-yeri-kanonik-kaynakta-hat-yazma-kuralı-kilit) madde 5). Kur'an birimlerinde `tr_*` sütunları boştur.
- `uv run mutalaa anchor --source tanzil-uthmani`: `q:{s}:{a}` çapası, `kind = 'ayet'`, `ord` ve `ayah_range` küresel âyet sırası (1..6236), `content_hash` UTF-8 baytların SHA-256'sı, `metin_durumu = 'onayli'`, `data_version = 'tanzil-uthmani@{surum}'`.
- `uv run mutalaa export pg --source tanzil-uthmani [--dry-run]`: geçici `staging_unit` tablosuna `COPY` (hat şema değiştirmez; şema A07'nin göçlerindedir), tek işlem, `pg_advisory_xact_lock`, `pipeline_run` satırı ve `source` satırının K-39 madde 3 kuralıyla yazılması: satır yoksa TOML'daki bütün alanlarla eklenir, varsa yalnız betimleyici alanlar güncellenir. Tek dosyalı kaynakta `source.dosya_sha256` ve `source.alinma_tarihi` ham kayıttan doldurulur. Kod hazırdır (`9a4e8a5`; kanonik metinde `notice.txt` zorunluluğu `224dad3`); bu adım onu gerçek veriyle çalıştırır ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §6).
- **Bitti sayılır:** `icerik.unit` içinde 6.236 `tanzil-uthmani` satırı; ikinci `export pg` hiçbir satırı değiştirmiyor.

### A10.5 · QA kapıları ve âyet sayısı çapraz denetimi
- `pipeline/src/mutalaa_pipeline/qa/checks/tanzil.py`: G-KAY (kaynak kaydı geçerli, `atif_metni` dolu, `notice_text` dosyadaki bildirim bloğuyla bayt bayt aynı ve `sha256(notice_text) == bildirim_sha256`), G-BUT (114 sure, 6.236 âyet, boş birim ve kontrol karakteri yok, bayt eşitliği, NFC uygulanmamış), G-CAP (gramer, teklik, `content_hash` yeniden hesabı, önceki çapaların varlığı), G-NOR (`shared/test-vectors/normalize/` Python'da geçer).
- Metnin NFC olup olmadığı yalnız rapora bilgi olarak yazılır; kapı değildir ([Test stratejisi](../../07-yayin/03-test-stratejisi.md) §14).
- AR-8 (A05'ten devir): iki dosyada Farsça `ی` (U+06CC), `ک` (U+06A9) ve Arapça-Hint rakamları sayılır; görülürse [Arama](../../03-veri/05-arama-fts5.md) §1.3 madde 4 önerisi `/karar` ile karara bağlanır ve önce vektörü eklenir. Normalizasyondan sonra Arapça bloklarında kalan birleşen işaretler (Mn) rapora yazılır.
- Âyet sayısı dizisi: A04'ün ürettiği `shared/data/ayet-sayilari.json` Uthmani ve Simple Clean'den sayılan değerlerle karşılaştırılır (ön ölçümde iki dosya da aynı çıktı); üç kopyanın (`packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`) JSON ile aynı olduğu denetlenir. Fark varsa aşama durur. Dizi elle düzeltilmez; A04'ün üretecinden (`export ayet-sayilari`) yeniden üretilir.
- Besmelenin Tanzil dosyasında ayrı satır mı yoksa ilk âyetin parçası mı olduğu dosyadan ölçülür ve rapora yazılır; A24 bu sonucu okur. Ön ölçüm (2 Kasım 2026): ayrı satır yoktur; Fâtiha'da birinci âyettir (4 belirteç), 2–114. surelerde (9 hariç) birinci âyetin ilk dört belirtecidir. Bu dört belirteç 1:1 ile Simple Clean'de 112 surenin hepsinde, Uthmani'de 110'unda bayt bayt aynıdır; 95. ve 97. surelerde Uthmani'nin ilk dört belirteci 1:1'dekinden farklı yazılmıştır (A11 inceler); 9. surede önek yoktur.
- **Bitti sayılır:** `uv run mutalaa qa run --source tanzil-uthmani` 0 ile çıkıyor; rapor `data/reports/{run_id}.json` altında.

### A10.6 · Değişmezlik testleri
- `pipeline/tests/test_degismezlik.py`; testler `degismezlik` işaretini taşır (işaret `pyproject.toml` içinde tanımlanır) ve yerel veri yoksa atlanır:
  1. İki dosyanın SHA-256'sı `tanzil.lock.json` ile aynı; kilitteki `bildirim_sha256`, `notice_text` özetine eşit (A10.2'de eklenen denetim).
  2. 114 sure ve 6.236 âyet var.
  3. Birimlerden Tanzil dosyası yeniden üretilir ve bildirim satırları hariç kaynakla bayt bayt aynıdır. Denetim hem `data/staged` hem PostgreSQL'den okunan birimlerle yapılır (`config.py` bağlantı dizesi vermiyorsa ikincisi atlanır).
  4. Her birimin `content_hash` değeri metninin SHA-256'sı.
- Testler 5–8'in sahibi ilerleme dosyasına yazılır: 5 `reader-core` (A24), 6 `core` paketinde Tanzil bildiriminin tam metni ve `bildirim_sha256` eşitliği (A13), 7 sayfa eşlemesi (A11), 8 terfide içerik özeti eşitliği (A13, P-14).
- **Bitti sayılır:** dört test yerelde yeşil; veri olmayan ortamda atlanıyor, kırılmıyor.

### A10.7 · Arapça vektörlere Tanzil satırları (A05'ten devir)
- Arama §1.5 Arapça tablosunun girdileri Kur'an metnidir; A05 bu kuralları sentetik dizilerle sınadı. Bu adımda aynı girdilerin Tanzil Uthmani baytlarıyla satırları `shared/test-vectors/normalize/ar.jsonl` dosyasına betikle eklenir (komut öneri: `uv run mutalaa export test-vectors --tanzil-ornekleri`).
- Betik tabloyu belgeden okur. Her girdinin iskeletini (NFD'den sonra birleşen işaretler, U+0640 ve U+06D6–U+06ED atılmış hâli; sınanan normalleştiriciden bağımsızdır) Tanzil Uthmani âyetlerinin ve boşlukla ayrılan kelimelerinin iskeletiyle karşılaştırır, okuma sırasındaki ilk eşleşmeyi alır. Tablo girdisi yalnız arama anahtarıdır; vektöre yazılmaz.
- Satırın girdisi Tanzil'in baytlarıdır ve değiştirilmez (birleşen işaretler dosyada `\u` kaçışıyla yazılır); beklenen değer tablodaki `ar` sütunudur; `note` kaynağı ve çapayı taşır (ör. `tanzil-uthmani q:1:1`).
- Eşleşme bulunamazsa ya da normalleştirici tablodaki değeri vermezse durulur: fark kullanıcıya gösterilir ve `/belge-esitle` ya da `/karar` ile çözülür. Beklenen değer uydurulmaz, Tanzil girdisi düzeltilmez.
- Betik yalnız kendi satırlarını yazar (`id` öneki `ar-tz-`) ve onları her çalışmada baştan üretir; A05'in sentetik satırlarına dokunmaz, ikinci çalıştırma dosyayı değiştirmez.
- Yeni satırlar üç dilde koşar (`test-vektoru`); G-NOR yeniden çalışır.
- **Bitti sayılır:** tablonun yedi girdisinin Tanzil karşılığı `ar.jsonl`'da ve üç koşucu yeşil; ya da farklar aşama kaydında ve `/karar` ile çözülecek.

## Kabul ölçütleri
- [x] `uv --directory pipeline run mutalaa sources check` 0 ile çıkıyor; iki Tanzil kaydı `kaynak_url` (`https://tanzil.net/download/`), `surum` ve dosyadaki bildirim bloğuyla bayt bayt aynı `notice_text` taşıyor. Kanıt: `sources check` 25 kayıt, 0 hata, 0 uyarı; iki Tanzil kaydının `notice_text` değeri dosyadaki bildirim bloğuyla bayt bayt aynı (G-KAY ve `test_degismezlik.py`); `kaynak_url` `https://tanzil.net/download/`, `surum` 1.1.
- [x] `data/gelen/tanzil/<YYYY-AA-GG>/` altında iki dosya ve `SHA256SUMS` var; SHA-256 değerleri A10.0 ölçümüyle aynı; `data/backups/gelen/tanzil/` kopyalarıyla karşılaştırma ilerleme notunda. Kanıt: `sha256sum -c SHA256SUMS` iki dosyada OK (`6933e133…`, `054b3d9f…`). `data/backups/gelen/tanzil/` kopyaları başka dosyadır (`rub` ve `stanween` işaretli; 1.409.970 ve 794.910 bayt, `aa0bf927…` ve `1862ee63…`), silinmedi.
- [x] `tanzil.lock.json` iki varyantın adresini, sürümünü, indirme seçeneklerini ve üç özetini (`sha256`, `metin_sha256`, `bildirim_sha256`) taşıyor; tek baytı değiştirilmiş bir ham dosyanın kopyasıyla çalışan bağdaştırıcı testi `2` çıkış kodunu doğruluyor; `sha256(notice_text) == bildirim_sha256` testi yeşil. Kanıt: `tanzil.lock.json` adres, sürüm, seçenekler, alınma tarihi, boyut ve üç özeti taşır. `test_komut_tek_bayt_degisince_cikis_2` ve `test_kilit_uyusmazliginda_ileti_farki_ayirir_ve_hicbir_sey_yazmaz` kilit uyuşmazlığında çıkış `2` ve boş `raw` doğrular; `test_kayit_bildirimi_kilitteki_ozetle_ayni` yeşil.
- [x] `icerik.unit` içinde 6.236 `tanzil-uthmani` satırı var; ikinci `export pg` 0 satır değiştiriyor (rapor sayıları). Kanıt: geçici `postgres:18` konteynerinde (yerel konteynerin parolası `pipeline/.env` ile uyuşmuyor, aşama kaydına bakın) 6.236 `tanzil-uthmani` satırı, hepsi `onayli`; `export pg --dry-run` yazmadı, ilk `export pg` 6.236 birim ve 2 kaynak ekledi, ikincisi 6.236 değişmeyen, 0 eklenen, 0 güncellenen (rapor sayıları).
- [x] SQL denetiminde `content_hash` yeniden hesabıyla uyuşmayan satır sayısı 0. Kanıt: aynı veritabanında `content_hash` ile `sha256(metin)` uyuşmayan satır sayısı 0.
- [x] `uv --directory pipeline run pytest -m degismezlik` dört testte yeşil; `uv --directory pipeline run pytest` ve `uv --directory pipeline run ruff check .` yeşil. Kanıt: `MUTALAA_DEGISMEZLIK_ZORUNLU=1` ile `pytest -m degismezlik` 29 geçti, 0 atlandı (`scripts/nightly.ps1 -ExportPg`, geçici veritabanı); yerelde veritabanısız 27 geçti, 2 atlandı. `pytest` 2.178 geçti, 19 atlandı; `ruff check`, `ruff format --check` ve `mypy` temiz.
- [x] QA raporunda G-KAY, G-BUT, G-CAP ve G-NOR "geçti"; NFC durumu bilgi olarak yazılı. Kanıt: `qa run` dört kapıda `gecti` (G-BUT: 114 sure, 6.236 birim, bayt farkı 0; G-CAP: 6.236 çapa; G-NOR: 155 vektör, 0 kalan). NFC bilgisi: Uthmani'de 5.782 NFC olmayan âyet, Simple Clean'de 0; AR-8 sayıları 0; normalizasyondan sonra kalan Mn 0.
- [x] `shared/data/ayet-sayilari.json` ve üç kopyası Tanzil sayımıyla aynı (114 eleman, toplam 6.236); besmele gözlemi raporda. Kanıt: QA ölçümü `ayet_sayilari_json`: 114 eleman, toplam 6.236, iki Tanzil dosyası ve üç kopya aynı. Besmele: ayrı satır yok; Fâtiha'da 1. âyet (4 belirteç); 2–114. surelerde (9 hariç) ilk dört belirteç 1:1 ile Simple Clean'de 112, Uthmani'de 110 surede bayt bayt aynı (95. ve 97. surede yazım farkı, A11 inceler); A24 bu sonucu okur.
- [x] `source.notice_text` Tanzil bildiriminin tam metnini taşıyor (dosyadaki bildirim bloğuyla bayt bayt karşılaştırma). Kanıt: `source.notice_text` 1.108 (Uthmani) ve 1.113 bayt (Simple Clean); `unit.metin` ile `notice_text`ten yeniden kurulan Uthmani dosyası kaynakla bayt bayt aynı (SHA-256 `6933e133…`; `test_degismezlik.py` ve `metin-denetcisi` bağımsız doğrulaması).
- [x] Simple Clean kararı karar defterinde (K-39); `metin-denetcisi` raporunda kanonik metne dokunan dönüşüm yok. Kanıt: K-39 ve 7 Kasım 2026 notu; `metin-denetcisi` kanonik metne dokunan dönüşüm bulmadı (26 mutantın 25'i yakalandı, kalan eşdeğerdi ve doğrudan testle sınandı).
- [x] `pipeline/.env` var (A03); bağlantı dizesi koda, günlüğe ve rapora yazılmamış; değişmezlik testi 3'ün PostgreSQL yarısı atlanmadan koştu. Kanıt: `pipeline/.env` var, bağlantı dizesi koda, günlüğe ve rapora yazılmadı. Testin PostgreSQL yarısı geçici konteynerde atlanmadan koştu; yerel veritabanında koşmadı, çünkü `pipeline/.env` parolası yerel konteynerinkiyle uyuşmuyor (`28P01`). **Kullanıcıya bırakıldı:** parolayı hizalamak (`windows-sorun` becerisi, `ALTER USER`).
- [x] `normalize/ar.jsonl` Arama §1.5 Arapça tablosunun Tanzil satırlarını taşıyor (girdi Tanzil baytları, `note` kaynak ve çapa) ve üç koşucu yeşil; ya da farklar aşama kaydında. Kanıt: `ar-tz-0001` … `ar-tz-0007` (`q:1:1`, `q:2:11`, `q:2:51`, `q:3:8`, `q:5:88`, `q:2:20`, `q:2:189`) `ar.jsonl` içinde; `export test-vectors --tanzil-ornekleri --check` "fark yok"; pytest, vitest (`@mutalaa/search`, 181) ve `dotnet test` (1.761) yeşil.

## Doğrulama
```bash
test -f pipeline/.env && echo "pipeline/.env var" || echo "pipeline/.env yok: A03'teki kopyalama (cp -n pipeline/.env.example pipeline/.env)"
sha256sum data/gelen/tanzil/<YYYY-AA-GG>/quran-uthmani.txt data/gelen/tanzil/<YYYY-AA-GG>/quran-simple-clean.txt   # SHA256SUMS ile aynı
uv --directory pipeline run mutalaa sources check
uv --directory pipeline run mutalaa ingest tanzil --variant uthmani && uv --directory pipeline run mutalaa ingest tanzil --variant simple-clean
uv --directory pipeline run mutalaa normalize --source tanzil-uthmani && uv --directory pipeline run mutalaa anchor --source tanzil-uthmani
uv --directory pipeline run mutalaa qa run --source tanzil-uthmani
uv --directory pipeline run mutalaa export pg --source tanzil-uthmani --dry-run && uv --directory pipeline run mutalaa export pg --source tanzil-uthmani
uv --directory pipeline run pytest -m degismezlik && uv --directory pipeline run pytest && uv --directory pipeline run ruff check .
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'tanzil-uthmani';"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'tanzil-uthmani' AND content_hash <> encode(sha256(convert_to(metin, 'UTF8')), 'hex');"
grep -c 'tanzil-uthmani q:' shared/test-vectors/normalize/ar.jsonl          # 7 (A10.7)
pnpm --filter @mutalaa/search test && dotnet test --solution server/Mutalaa.slnx
```
`-U` ve `-d` değerleri `.env.example` varsayılanlarıdır; kullanıcı değiştirdiyse ona göre yazılır.

## Dikkat
- Tanzil metni hiçbir adımda değişmez: NFC, kırpma, satır sonu çevirisi ve dosyayı editörde açıp kaydetmek yasaktır. Ayrıntı: `metin-butunlugu`.
- Windows: dosya bayt kipinde okunur; metin kipi satır sonlarını çevirebilir. `.gitattributes` içindeki `* text=auto eol=lf` kuralı depoya giren Tanzil parçasını dönüştürebilir; parça dosyası için `.gitattributes` dosyasına `-text` satırı eklenir (yalnız ekleme).
- `ar_norm` ayrı sütundur, kanonik metnin yerine geçmez; Kur'an metni bayt bayt kalır (K-26). Bu aşama yalnız editoryal veritabanına yazar.
- **İndirme ve kilit (ölçüm, 2 Kasım 2026).** Bildirimdeki yıl satırı indirme yılını izler: 2026 indirmesinde 2007-2026, Internet Archive kopyasında (`quran-uthmani_20250625`) 2007-2025; âyet satırları aynıdır. İndirme formundaki seçenekler baytları değiştirir (`rub` +597 bayt, yalnız Uthmani'de `stanween` +13.286 bayt). Bu yüzden kilit seçenekleri ve alınma tarihini taşır (A10.2) ve dosya özetinin yanında âyet satırlarının (`metin_sha256`) ve bildirim bloğunun (`bildirim_sha256`) özetini ayrı tutar (K-39 madde 4): yıl satırı değiştiğinde fark bildirimde görünür, metinde görünmez.
- Dosyalar `data/gelen/` altında yeni boş klasöre iner ve sonradan değiştirilmez; `data/raw`'a yalnız `ingest` yazar. İndirilen dosya veridir: içindeki hiçbir şey çalıştırılmaz.
- Günlüklere âyet metni yazılmaz; çapa ve özet yazılır.
- Kur'an metni ve üst verisi hafızadan yazılmaz. Testler yalnız indirilen dosyadan ya da dosyadan betikle kesilmiş parçadan okur.

## İnsan adımları
Bu aşamanın insan adımı yoktur: Tanzil dosyalarını Claude Code indirir (A10.0). `pipeline/.env` A03'ün çıktısıdır (kullanıcı `cp -n pipeline/.env.example pipeline/.env` ile oluşturur; `MUTALAA_DB_URL`, kök `.env` ile aynı parola); A10.4'ten önce denetlenir.

## Çıktılar
- `data/gelen/tanzil/<YYYY-AA-GG>/` (git dışı): `quran-uthmani.txt`, `quran-simple-clean.txt`, `SHA256SUMS`
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py`, `ingest/tanzil.lock.json`, `ingest/tanzil_bicim.py` (ölçüm güncellemesi), `adimlar/normalize_tanzil.py`, `adimlar/anchor_tanzil.py`, `staged.py`, `zincir.py`, `qa/run.py`, `qa/rapor.py`, `qa/vektorler.py`, `qa/checks/tanzil.py`, `export/tanzil_ornekleri.py`
- `shared/test-vectors/normalize/ar.jsonl` eki (Tanzil satırları) ve `export test-vectors` seçeneği
- `pipeline/sources/tanzil-uthmani.toml`, `tanzil-simple-clean.toml` güncellemesi
- `pipeline/tests/test_degismezlik.py`, `test_bosluk_korunumu.py`, bağdaştırıcı, adım, QA ve zincir testleri, katman testleri (`test_tekil_tanimlar.py`, `test_yaprak_kitapliklar.py`) ve küçük Tanzil parçası fikstürü (`tests/fixtures/tanzil/`); `.gitattributes` eki
- `.github/workflows/nightly.yml` (kuruldu; fikstür testleri eklenir) ve `scripts/nightly.ps1` (yerelde gerçek veriyle koşu; CRLF)
- `data/raw/tanzil-*/`, `data/staged/tanzil-*/`, `data/reports/` (git dışı); PostgreSQL'de `source`, `unit`, `pipeline_run` satırları
- Karar defterinde ilk kilit değerleri (K-39'a tarihli not); Kaynaklar §3.1'de çözülen "Doğrulanacak" maddeleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A10-tanzil-alimi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## Aşama kaydı (2026-11-07)

Durum: tamam (7 Kasım 2026); PR bekliyor. A10.0 2 Kasım 2026'da yapıldı (indirme ve kaynak kayıtları: `a3d338d`); kod ve testler 3–7 Kasım 2026. Commit'ler: `f5a135c` hat adımları, `5909c10` vektörler, `99be379` değişmezlik testleri, `5dd947e` gece iş akışı, `f440f7c` K-39 notu, `d57bb45` belgeler, `64fb569` kit becerisi, `cdf5756` belge örnekleri.

### Kararlar ve gerekçeleri

- **Adım kodu `adimlar/` altında.** `normalize --source` ve `anchor --source` kodu `normalize/` ve `anchor/` paketlerine konmadı: A05'in mimari testi (`test_normalize_unit.py`) normalize paketinin `export` ve `cli` içe aktarmamasını şart koşar ve iki paket TypeScript ve C# karşılıklarıyla aynı yaprak kitaplık rolündedir. Adım kodu (staged okuma ve yazma, parmak izi, manifest, komut gövdesi) `adimlar/normalize_tanzil.py` ve `adimlar/anchor_tanzil.py` içindedir; kural `tests/test_yaprak_kitapliklar.py` ile sınanır.
- **Kilit sıkı ve tanılı** (K-39 madde 4). Üç özet (`sha256`, `metin_sha256`, `bildirim_sha256`); uyuşmazlık her durumda çıkış `2` verir ve `data/raw`'a kopyalamadan önce durur. İleti farkın bildirimde mi metinde mi olduğunu söyler; "yeni Tanzil sürümü kilit güncellenerek (`/karar`) alınır" uyarısı 300 karakter sınırında kesilmez.
- **Ham kopya.** Aynı baytlar `raw` altında zaten varsa yeni kopya açılmaz (gece koşusu `raw`'u şişirmez). Aynı tarihli klasörde başka bayt varsa çıkış `2` verilir ve yeni bir `data/gelen` tarih klasörü kullanılır; İçerik hattı §5'in ilk taslağındaki "yeni klasör ve uyarı" yerine bu seçildi, çünkü `raw` değişmezliği için daha güvenlidir. Dosyalar diske eşitlenmeden klasör görünür olmaz.
- **QA kabulü tek yerde (`qa/rapor.py`).** Bir anchor çalıştırmasının kabulü, o çalıştırmaya ait raporların en yenisinden okunur. Kapısı kalan ya da tamamlanamayan sonraki koşu eski `gecti` raporunu geçersiz kılar; başarılı kısmi (`--gate`) koşu kararı değiştirmez. `export pg` ve G-CAP tabanı aynı işlevi kullanır.
- **G-CAP tabanı** hemen önceki anchor çalıştırması değil, dört kapıyı geçmiş en yeni önceki çalıştırmadır; böyle biri yoksa taban yoktur ve rapora uyarı yazılır.
- **Ortak sabitler** (`units.jsonl` ve `notice.txt` adları, SHA-256 ve `run_id` desenleri) yalnız `lineage.py` içinde tanımlıdır; `test_tekil_tanimlar.py` bunu AST ile korur.
- **Gece iş akışı** yalnız atlayan ya da hiç test seçmeyen (pytest çıkış `5`) koşuda düşer: en az bir "passed" şartı vardır. Gerçek veriyle koşu yerelde `scripts/nightly.ps1 [-ExportPg]` ile yapılır.

### Kanıtlar (7 Kasım 2026, temiz çalışma ağacı)

- **Gerçek veriyle uçtan uca** (`scripts/nightly.ps1 -ExportPg`, geçici `postgres:18`): `sources check` 25 kayıt, 0 hata, 0 uyarı; `ingest` iki varyantta 6.236'şar birim; `normalize` ve `anchor` 6.236; `qa run` dört kapıda `gecti` (rapor `01a1b640-bd03-7416-8469-480e1486fd8a`, `onceki_anchor_run_id` dolu); `export pg --dry-run` hiçbir satır yazmadı; `export pg` 6.236 birim ve 2 kaynak satırı ekledi; ikinci `export pg` 6.236 değişmeyen, 0 eklenen, 0 güncellenen; vektör denetimi "fark yok"; `degismezlik` 29 geçti, 0 atlandı. Parmak izi aynıyken `ingest`, `normalize` ve `anchor` ikinci koşuda "atlandi" der.
- **SQL:** `icerik.unit` içinde 6.236 `tanzil-uthmani` satırı (114 sure, `ord` 1–6236, hepsi `onayli`), `content_hash` uyuşmazlığı 0, Simple Clean için `q:` birimi yok; `source.notice_text` 1.108 (Uthmani) ve 1.113 bayt (Simple Clean), `dosya_sha256` kilitle aynı.
- **Kapılar:** `pytest` 2.178 geçti, 19 atlandı (atlananlar yerel PostgreSQL testleri; geçici konteynerde 17 geçti); `ruff check`, `ruff format --check`, `mypy` temiz; `pnpm --filter @mutalaa/search test` 181; `dotnet test --solution server/Mutalaa.slnx` 1.761/1.761; kit testleri 68/68; actionlint ve `check-jsonschema` temiz; belge bağlantı denetimi temiz.
- **QA ölçümleri:** NFC olmayan âyet Uthmani'de 5.782, Simple Clean'de 0; AR-8 sayıları 0 (Farsça `ی`, `ک`, Arapça-Hint rakam); normalizasyondan sonra kalan Mn 0; AR-4 ek sözcük 7.592 (3.982 âyette); `ayet-sayilari.json` ve üç kopyası iki dosyayla aynı (114 sure, 6.236 âyet); besmele ayrı satır değil (Fâtiha'da 1. âyet, 4 belirteç).

### İnceleme (3–7 Kasım 2026)

İlk inceleme üç bağımsız bakışla yapıldı (doğruluk, metin bütünlüğü, saldırgan ve mutasyon): 20 bulgu, 14'ü iki bağımsız çürütme denemesine alındı, 13'ü doğrulandı, 1'i çürütüldü. 10'u kodda ve testlerde düzeltildi: QA kabulü ve G-CAP tabanı, boşluk korunumu testi, yanlış nedenle geçen çıkış-2 testleri, kirli ağaç kuralı testi, kesilen uyarı iletisi, ham kopya `fsync`, yinelenen sabitler ve ölü koşul, K-39 `metin` farkı testi. İkisi ana oturumda kapandı (K-39 ilk kilit notu, belge ve kit kayması); biri kullanıcı adımıdır (`pipeline/.env` parolası).

Son tur `inceleyici` ve `metin-denetcisi` ile yapıldı; kritik bulgu yok.

- `inceleyici` bir önemli bulgu verdi ve düzeltildi: zincir ya da kilit hatasıyla biten `qa run` rapora `anchor_run_id` yazmadan çıktığı için eski `gecti` raporunu geçersiz kılmıyordu (test önce kırmızı, sonra yeşil). Rapor `fsync` ve `cikis_kodu` tipi sertleştirildi; `nightly.yml` geçici dosyasız hâle getirildi.
- `metin-denetcisi` kanonik metne dokunan dönüşüm bulmadı. Gerçek veride staged çıktıdan ve PostgreSQL'den dosya bayt bayt yeniden kuruldu, 26 mutantın 25'i yakalandı, kalan eşdeğer mutant `parse` içindeki yinelenen özet denetimiydi (doğrudan testle sınandı). Belgelerde Tanzil baytı olmayan, elle yazılmış üç Kur'an örneği buldu; `cdf5756` ile Tanzil diliminden alındı.

### Sapmalar

- `normalize/tanzil.py` ve `anchor/tanzil.py` yerine `adimlar/` paketi (yukarıda).
- Aynı gün farklı SHA-256: yeni klasör ve uyarı yerine çıkış `2`.
- `ingest tanzil` ek bayrakları `--gelen-tarih` ve `--kok`; `qa run` bayrakları `--run`, `--gate`.
- Manifest `Duzen` alanında satır aralığı kapalı ve 1 tabanlı, bayt aralığı yarı açıktır (İçerik hattı §5'e yazıldı).

### Devredilenler

- **Kullanıcı:** `pipeline/.env` içindeki `MUTALAA_DB_URL` parolası yerel konteynerinkiyle uyuşmuyor (psycopg `28P01`). Düzeltme `windows-sorun` becerisindeki `ALTER USER` adımıdır; ardından `scripts/nightly.ps1 -ExportPg` yerel veritabanına yükler. Ölçütler 4, 5 ve 11 o zamana dek geçici konteynerde kanıtlıdır.
- **A11:** Tanzil örneği beş kutulu kopyaydı (1.409.970 bayt, 82.459 belirteç); seçilen dosya 1.396.087 bayt, 82.260 belirteç ve `rub` işaretsizdir, A11 sayılarını bu dosyayla yeniden doğrular. 95. ve 97. surede Uthmani'nin ilk dört belirteci 1:1'dekinden farklı yazılmıştır, A11 inceler.
- **A12:** Simple Clean'in pakette tutulup tutulmayacağı (K-39 madde 1).
- **A13:** `core` paketinde Tanzil bildirimi ve `bildirim_sha256` eşitliği (test 6), terfide içerik özeti eşitliği (test 8, P-14). Çözüldü (2026-11-09, A13): QA günlüğünde kapı adı (`qa_kapi` olayı artık `kapi` alanını taşır: `Gunluk.yaz(..., kapi=...)`; [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §7); rapor ve manifest yazımında `os.replace` için yeniden deneme (OneDrive `EPERM`: `lineage.atomik_degistir`, en çok 3 deneme; İçerik hattı §7). Test 6 ve test 8 A13'te kalır.
- **A24:** okuyucunun metin seçicisi testi (test 5) ve QA raporundaki besmele gözlemi.
- **Bilinçli Tanzil sürüm geçişi:** kilit `/karar` ile güncellenip `content_hash` değişirse yalnız `anchor`'ı yeniden koşmak G-CAP'i geçirmez ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §13 madde 6); gerektiğinde `/karar` ile tasarlanır.

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A09](./A09-elmalili-ocr-pilotu.md) · Sonraki: [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md)
