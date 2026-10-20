# A10 · Tanzil alımı ve değişmezlik testleri

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A06](./A06-lisans-defteri-ve-enumlar.md) · [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** yok
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `arastirmaci` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · `windows-sorun` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A10`

## Amaç
İçerik hattının ilk gerçek kaynağı olan Tanzil Uthmani ve Simple Clean dosyaları alınır. `q:{sure}:{ayet}` birimleri bayt bayt değiştirilmeden editoryal veritabanına yüklenir. Kilit dosyası, QA kapıları ve değişmezlik testleri Kur'an metninin hiçbir adımda değişmediğini kanıtlar. Bu aşamadan sonra `core` paketinin Kur'an metni hazırdır; paketleme A13'tedir.

## Okunacak belgeler
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): tamamı; özellikle §4 komutlar ve çıkış kodları, §5 veri soyu, §6 idempotentlik, §8 bağdaştırıcı, §9 QA kapıları, §12 çalıştırma manifesti
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 değişmezlik testleri, §14 madde 1
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2 anlam kuralları, §7 kanonik metin ve `content_hash`, §8 ofsetler
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.1 Tanzil kartı, §6 şart takibi, §8 yazışma 1
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source`, §4 `unit`, §10 `pipeline_run` ve yükleme
- [Arama](../../03-veri/05-arama-fts5.md): §1.3 Arapça kurallar, §1.4 Kur'an birimleri, §1.5 Arapça tablo (A10.7)
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §6 adım 4, §10.1–§10.2

## Kapsam
**Yapılır**
- `tanzil-uthmani` ve `tanzil-simple-clean` için indirme, `tanzil.lock.json`, ham kayıt ve ayrıştırma; `tanzil-uthmani` için normalize, çapa, `content_hash`, QA ve `export pg`. Simple Clean `q:` birimi olarak yüklenmez (`unit.anchor` tekildir); yeri A10.3'ün kararıdır.
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §5'teki sekiz testin envanteri: 1–4 bu aşamada yazılır, 5–8'in sahibi olan aşama kayda geçer.
- A04'te üretilen gömülü âyet sayısı dizisinin Tanzil metniyle çapraz doğrulanması.
- A05'ten devir: Arama §1.5 Arapça tablosunun Tanzil baytlarıyla vektör satırları (A10.7).

**Yapılmaz**
- Sure adları, cüz, secde ve Medine sayfa eşlemesi (A11). Kelime bölmesi ve `quran_word` (A11 ve A17).
- Paket DDL'i ve FTS5 tabloları (A12). `core` paketinin üretimi ve Tanzil bildiriminin pakete yazılması (A13).
- Okuyucunun metin seçicisi testi (test 5; `reader-core` ile A24). CI gece işi (A08'de kurulur).

## Adımlar
### A10.1 · Adres, sürüm ve lisans doğrulaması
- `arastirmaci` resmî kaynaktan doğrular ve bağlantısıyla raporlar: Uthmani ve Simple Clean dosyalarının indirme adresi ve biçimi (satır düzeni, varsa indirme seçenekleri), Uthmani dosyasının sürüm numarası, dosyadaki bildirim satırlarının biçimi, canlı tanzil.net lisans metni ve güncellemeler sayfası. Bunlar lisans defteri §3.1'de "Doğrulanacak" ya da "okunmadı" diye işaretlidir.
- Sonuçlar A06'da açılan `pipeline/sources/tanzil-uthmani.toml` ve `tanzil-simple-clean.toml` dosyalarına işlenir (`kaynak_url`, `lisans_kopyasi`, `lisans_sha256`, `yeniden_kontrol`). Tarihli lisans kopyası `pipeline/sources/licenses/tanzil-{varyant}-{YYYY-MM-DD}.txt` olur. Alan adları değişmez.
- Şartlar otomatik indirmeye izin vermiyorsa dosyayı kullanıcı indirir ve A09'daki kalıpla `data/gelen/tanzil/` altına koyar (öneri); `data/raw` yalnız `ingest` ile yazılır ve kilit denetimi aynı kalır.
- Çözülen "Doğrulanacak" maddeleri `/belge-esitle` ile lisans defterine işlenir.
- **Bitti sayılır:** iki TOML doğrulanmış adres, tarihli lisans kopyası ve SHA-256 taşıyor; `uv run mutalaa sources check` 0 ile çıkıyor.

### A10.2 · Kilit dosyası ve bağdaştırıcı
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py`: [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §8'deki `SourceAdapter` (`fetch`, `parse`) ve `run_ingest` içindeki `require_status` denetimi.
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.lock.json`: varyant başına `url`, `sha256`, `boyut`, `surum`, indirme seçenekleri ve alınma tarihi (Test stratejisi §5 madde 1).
- `fetch` dosyayı `data/raw/tanzil-{varyant}/{YYYY-MM-DD}/` altına yazar ve `fetch.json` üretir. SHA-256 kilitle tutmazsa komut `2` ile çıkar ve "yeni Tanzil sürümü yalnız onay treniyle alınır" uyarısını basar ([Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md) §7.3). Kilit yalnız `/karar` ile güncellenir.
- `parse` dosyayı bayt olarak okur, yalnız `b"\n"` ile böler, satırı katı UTF-8 ile çözer. NFC, `strip()`, `str.splitlines()` ve satır sonu çevirisi yoktur; `\r` görülürse raporlanır. Bildirim satırları birimlere girmez; tam metni `source.notice_text` alanına aynen yazılır.
- Her birimin kaynak dosyadaki yeri (`file`, `line`) `provenance` içinde tutulur; `kaynak[başlangıç:bitiş] == text` eşitliği QA'da denetlenir ([Çapa şeması](../../03-veri/01-capa-semasi.md) §7).
- Bağdaştırıcı birim testleri depodaki küçük bir Tanzil parçasıyla yazılır. Parça dosyadan betikle kesilir, elle yazılmaz; atıf satırı korunur.
- **Bitti sayılır:** `uv run mutalaa ingest tanzil --variant uthmani` ve `--variant simple-clean` (ikinci varyant adı öneri) 0 ile çıkıyor; `data/staged/` altında 6.236'şar satırlık `units.jsonl` ve çalıştırma manifesti var.

### A10.3 · Simple Clean'in yeri (karar)
- Dokümanlarda `q:` çapası yalnız Uthmani metni gösterir ve `unit.anchor` tekildir. `core` paketinde Simple Clean ayrı birim ya da sütun değildir; normalize hâli `unit_search.ar_norm` sütunundadır (İçerik paketleri §3.2, Arama §1.4). Ham Simple Clean metninin editoryal veritabanında duracağı yer tanımlı değildir.
- Plan aşamasında öneri sunulur, kullanıcı onaylar, `/karar` ile yazılır. Öneri: Simple Clean `data/raw` ve `data/staged` içinde kalır ve yalnız Kur'an birimlerinin `ar_norm` sütununu besler; pakette tutulup tutulmayacağı A12'de karara bağlanır.
- **Bitti sayılır:** karar defterinde Simple Clean'in yeri yazılı.

### A10.4 · Normalize, çapa ve yükleme
- Önce `test -f pipeline/.env && echo var`. Dosya yoksa durulur ve kullanıcıdan A03'teki kopyalama istenir; Claude Code `.env` dosyası oluşturamaz ve okuyamaz. Hat yapılandırması `pipeline/src/mutalaa_pipeline/config.py` (pydantic-settings; yoksa bu aşamada eklenir) `MUTALAA_DB_URL` değerini ortamdan ya da `env_file` olarak `pipeline/.env` dosyasından okur (İçerik hattı §3 öncelik sırası). pydantic-settings `.env` değerlerini `os.environ`'a yazmaz; bu yüzden testler ve komutlar bağlantı dizesini yalnız `config.py`'den alır. Dosya yolu paketin konumundan çözülür, çalışma dizinine bağlı değildir (öneri). Değer koda, günlüğe ve rapora yazılmaz.
- `data/staged` satırlarında `content_hash` 64 küçük harfli onaltılık karakterdir; `sha256:` öneki yazılmaz (Editoryal veritabanı §4'teki CHECK kısıtı).
- `uv run mutalaa normalize --source tanzil-uthmani`: `ar_norm`, A05'teki Python normalleştiricisiyle Simple Clean âyet metninden üretilir ([Arama](../../03-veri/05-arama-fts5.md) §1.4). Uthmani biçimlerinin sona eklenmesi (AR-4) öneridir; planda kullanıcıya sorulur. Kur'an birimlerinde `tr_*` sütunları boştur.
- `uv run mutalaa anchor --source tanzil-uthmani`: `q:{s}:{a}` çapası, `kind = 'ayet'`, `ord` ve `ayah_range` küresel âyet sırası (1..6236), `content_hash` UTF-8 baytların SHA-256'sı, `metin_durumu = 'onayli'`, `data_version = 'tanzil-uthmani@{surum}'`.
- `uv run mutalaa export pg --source tanzil-uthmani [--dry-run]`: geçici `staging_unit` tablosuna `COPY` (hat şema değiştirmez; şema A07'nin göçlerindedir), tek işlem, `pg_advisory_lock`, `pipeline_run` satırı ve `source` satırının TOML'dan güncellenmesi ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §6).
- **Bitti sayılır:** `icerik.unit` içinde 6.236 `tanzil-uthmani` satırı; ikinci `export pg` hiçbir satırı değiştirmiyor.

### A10.5 · QA kapıları ve âyet sayısı çapraz denetimi
- `pipeline/src/mutalaa_pipeline/qa/checks/tanzil.py`: G-LIS (kaynak kaydı, lisans kopyası, atıf, durum), G-BUT (114 sure, 6.236 âyet, boş birim ve kontrol karakteri yok, bayt eşitliği, NFC uygulanmamış), G-CAP (gramer, teklik, `content_hash` yeniden hesabı, önceki çapaların varlığı), G-NOR (`shared/test-vectors/normalize/` Python'da geçer).
- Metnin NFC olup olmadığı yalnız rapora bilgi olarak yazılır; kapı değildir ([Test stratejisi](../../07-yayin/03-test-stratejisi.md) §14).
- AR-8 (A05'ten devir): iki dosyada Farsça `ی` (U+06CC), `ک` (U+06A9) ve Arapça-Hint rakamları sayılır; görülürse [Arama](../../03-veri/05-arama-fts5.md) §1.3 madde 4 önerisi `/karar` ile karara bağlanır ve önce vektörü eklenir. Normalizasyondan sonra Arapça bloklarında kalan birleşen işaretler (Mn) rapora yazılır.
- Âyet sayısı dizisi: A04'ün ürettiği `shared/data/ayet-sayilari.json` Uthmani ve Simple Clean'den sayılan değerlerle karşılaştırılır; üç kopyanın (`packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`) JSON ile aynı olduğu denetlenir. Fark varsa aşama durur. Dizi elle düzeltilmez; A04'ün üretecinden (`export ayet-sayilari`) yeniden üretilir.
- Besmelenin Tanzil dosyasında ayrı satır mı yoksa ilk âyetin parçası mı olduğu dosyadan ölçülür ve rapora yazılır; A24 bu sonucu okur.
- **Bitti sayılır:** `uv run mutalaa qa run --source tanzil-uthmani` 0 ile çıkıyor; rapor `data/reports/{run_id}.json` altında.

### A10.6 · Değişmezlik testleri
- `pipeline/tests/test_degismezlik.py`; testler `degismezlik` işaretini taşır (işaret `pyproject.toml` içinde tanımlanır) ve yerel veri yoksa atlanır:
  1. İki dosyanın SHA-256'sı `tanzil.lock.json` ile aynı.
  2. 114 sure ve 6.236 âyet var.
  3. Birimlerden Tanzil dosyası yeniden üretilir ve bildirim satırları hariç kaynakla bayt bayt aynıdır. Denetim hem `data/staged` hem PostgreSQL'den okunan birimlerle yapılır (`config.py` bağlantı dizesi vermiyorsa ikincisi atlanır).
  4. Her birimin `content_hash` değeri metninin SHA-256'sı.
- Testler 5–8'in sahibi ilerleme dosyasına yazılır: 5 `reader-core` (A24), 6 `core` paketinde Tanzil bildiriminin tam metni (A13), 7 sayfa eşlemesi (A11), 8 Kurul içerik özeti (A13, P-04).
- **Bitti sayılır:** dört test yerelde yeşil; veri olmayan ortamda atlanıyor, kırılmıyor.

### A10.7 · Arapça vektörlere Tanzil satırları (A05'ten devir)
- Arama §1.5 Arapça tablosunun girdileri Kur'an metnidir; A05 bu kuralları sentetik dizilerle sınadı. Bu adımda aynı girdilerin Tanzil Uthmani baytlarıyla satırları `shared/test-vectors/normalize/ar.jsonl` dosyasına betikle eklenir (komut öneri: `uv run mutalaa export test-vectors --tanzil-ornekleri`).
- Betik tabloyu belgeden okur. Her girdinin iskeletini (NFD'den sonra birleşen işaretler, U+0640 ve U+06D6–U+06ED atılmış hâli; sınanan normalleştiriciden bağımsızdır) Tanzil Uthmani âyetlerinin ve boşlukla ayrılan kelimelerinin iskeletiyle karşılaştırır, okuma sırasındaki ilk eşleşmeyi alır. Tablo girdisi yalnız arama anahtarıdır; vektöre yazılmaz.
- Satırın girdisi Tanzil'in baytlarıdır ve değiştirilmez (birleşen işaretler dosyada `\u` kaçışıyla yazılır); beklenen değer tablodaki `ar` sütunudur; `note` kaynağı ve çapayı taşır (ör. `tanzil-uthmani q:1:1`; atıf şartı).
- Eşleşme bulunamazsa ya da normalleştirici tablodaki değeri vermezse durulur: fark kullanıcıya gösterilir ve `/belge-esitle` ya da `/karar` ile çözülür. Beklenen değer uydurulmaz, Tanzil girdisi düzeltilmez.
- Betik yalnız kendi satırlarını yazar (`id` öneki `ar-tz-`) ve onları her çalışmada baştan üretir; A05'in sentetik satırlarına dokunmaz, ikinci çalıştırma dosyayı değiştirmez.
- Yeni satırlar üç dilde koşar (`test-vektoru`); G-NOR yeniden çalışır.
- **Bitti sayılır:** tablonun yedi girdisinin Tanzil karşılığı `ar.jsonl`'da ve üç koşucu yeşil; ya da farklar aşama kaydında ve karar bekliyor.

## Kabul ölçütleri
- [ ] `uv run mutalaa sources check` 0 ile çıkıyor; iki Tanzil TOML'u doğrulanmış adres, tarihli lisans kopyası ve SHA-256 taşıyor.
- [ ] `tanzil.lock.json` iki varyantın adresini, sürümünü ve SHA-256'sını taşıyor; tek baytı değiştirilmiş bir ham dosyanın kopyasıyla çalışan bağdaştırıcı testi `2` çıkış kodunu doğruluyor.
- [ ] `icerik.unit` içinde 6.236 `tanzil-uthmani` satırı var; ikinci `export pg` 0 satır değiştiriyor (rapor sayıları).
- [ ] SQL denetiminde `content_hash` yeniden hesabıyla uyuşmayan satır sayısı 0.
- [ ] `uv run pytest -m degismezlik` dört testte yeşil; `uv run pytest` ve `uv run ruff check .` yeşil.
- [ ] QA raporunda G-LIS, G-BUT, G-CAP ve G-NOR "geçti"; NFC durumu bilgi olarak yazılı.
- [ ] `shared/data/ayet-sayilari.json` ve üç kopyası Tanzil sayımıyla aynı (114 eleman, toplam 6.236); besmele gözlemi raporda.
- [ ] `source.notice_text` Tanzil bildiriminin tam metnini taşıyor (gözle kontrol: dosyadaki bildirim satırlarıyla karşılaştırma).
- [ ] Simple Clean kararı karar defterinde; `metin-denetcisi` raporunda kanonik metne dokunan dönüşüm yok.
- [ ] `pipeline/.env` var (kullanıcı oluşturdu); bağlantı dizesi koda, günlüğe ve rapora yazılmamış; değişmezlik testi 3'ün PostgreSQL yarısı atlanmadan koştu.
- [ ] `normalize/ar.jsonl` Arama §1.5 Arapça tablosunun Tanzil satırlarını taşıyor (girdi Tanzil baytları, `note` kaynak ve çapa) ve üç koşucu yeşil; ya da farklar aşama kaydında.

## Doğrulama
```bash
test -f pipeline/.env && echo "pipeline/.env var" || echo "pipeline/.env yok: A03'teki kullanıcı adımı"
(cd pipeline && uv run mutalaa sources check)
(cd pipeline && uv run mutalaa ingest tanzil --variant uthmani && uv run mutalaa ingest tanzil --variant simple-clean)
(cd pipeline && uv run mutalaa normalize --source tanzil-uthmani && uv run mutalaa anchor --source tanzil-uthmani)
(cd pipeline && uv run mutalaa qa run --source tanzil-uthmani)
(cd pipeline && uv run mutalaa export pg --source tanzil-uthmani --dry-run && uv run mutalaa export pg --source tanzil-uthmani)
(cd pipeline && uv run pytest -m degismezlik && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'tanzil-uthmani';"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'tanzil-uthmani' AND content_hash <> encode(sha256(convert_to(metin, 'UTF8')), 'hex');"
grep -c 'tanzil-uthmani q:' shared/test-vectors/normalize/ar.jsonl          # 7 (A10.7)
pnpm --filter @mutalaa/search test && dotnet test server/Mutalaa.slnx
```
`-U` ve `-d` değerleri `.env.example` varsayılanlarıdır; kullanıcı değiştirdiyse ona göre yazılır.

## Dikkat
- Tanzil metni hiçbir adımda değişmez: NFC, kırpma, satır sonu çevirisi ve dosyayı editörde açıp kaydetmek yasaktır. Ayrıntı: `metin-butunlugu`.
- Windows: dosya bayt kipinde okunur; metin kipi satır sonlarını çevirebilir. `.gitattributes` içindeki `* text=auto eol=lf` kuralı depoya giren Tanzil parçasını dönüştürebilir; parça dosyası için `.gitattributes` dosyasına `-text` satırı eklenir (yalnız ekleme).
- `ar_norm` ayrı sütundur, kanonik metnin yerine geçmez. Ayrı sütundaki normalize metnin Tanzil şartlarında "değiştirme" sayılıp sayılmadığı açıktır (ÇŞ-2, İ-08). Bu aşama yalnız editoryal veritabanına yazar.
- **A01.1 bulgusu (2026-10-20): indirme ve kilit.** Tanzil dosya başlığındaki telif yılı satırı indirme yılına göre değişebilir ("Copyright (C) 2007-2021" / "2007-2026" görüldü; değişimin nedeni çıkarımdır) ve indirme formundaki seçenekler baytları değiştirir. `tanzil.lock.json` tasarlanırken bu dikkate alınır: kilit seçenekleri ve alınma tarihini de taşır (A10.2); yalnız dosya SHA-256'sına dayanan bir uyarının başlık satırı farkını ayıramaması olasıdır (öneri: bildirim satırları ve metin satırları ayrı karşılaştırılabilir; plan aşamasında sorulur). İndirme formundaki şart onayını kullanıcı kendisi verir: A01.1 sırasında bir araştırma ajanı `agree=true` ile formu çağırdı, bu kural ihlaliydi ve o dosyalar kullanılmaz. Tanzil'in cevabı için [Tanzil arama metni yazısı](../../yazismalar/tanzil-arama-metni.md).
- Günlüklere âyet metni yazılmaz; çapa ve özet yazılır.
- Kur'an metni ve üst verisi hafızadan yazılmaz. Testler yalnız indirilen dosyadan ya da dosyadan betikle kesilmiş parçadan okur.

## İnsan adımları
- Numaralı insan adımı yok. Şartlar otomatik indirmeye izin vermezse kullanıcı dosyayı indirir (A10.1). Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- `pipeline/.env` A03'te kullanıcı tarafından oluşturulmuş olmalıdır (`MUTALAA_DB_URL`, kök `.env` ile aynı parola); A10.4'ten önce denetlenir.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py`, `ingest/tanzil.lock.json`, `qa/checks/tanzil.py`, `config.py`
- `shared/test-vectors/normalize/ar.jsonl` eki (Tanzil satırları) ve `export test-vectors` seçeneği
- `pipeline/sources/tanzil-uthmani.toml`, `tanzil-simple-clean.toml` güncellemesi; `pipeline/sources/licenses/tanzil-*-{tarih}.txt`
- `pipeline/tests/test_degismezlik.py`, bağdaştırıcı testleri ve küçük Tanzil parçası fikstürü; `.gitattributes` eki
- `data/raw/tanzil-*/`, `data/staged/tanzil-*/`, `data/reports/` (git dışı); PostgreSQL'de `source`, `unit`, `pipeline_run` satırları
- Karar defterinde Simple Clean kaydı; lisans defterinde çözülen "Doğrulanacak" maddeleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A10-tanzil-alimi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A09](./A09-elmalili-ocr-pilotu.md) · Sonraki: [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md)
