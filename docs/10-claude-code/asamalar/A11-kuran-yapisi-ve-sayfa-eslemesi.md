# A11 · Kur'an yapısı: sure adları, cüz, secde, Medine sayfa eşlemesi

> **Sürüm:** 1.1 · **Tarih:** 25 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · **İnsan adımı:** İ-23 (sure adlarının girişi ve onayı) · AS-10 kaynak kararı (proje sahibi)
> **Ajanlar:** `hat-gelistirici` · `lisans-denetcisi` · `arastirmaci` · `sunucu-gelistirici` (şema eki gerekirse) · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `lisans-kapisi` · `capa-gramer` · `ef-goc` · **Tahmini oturum:** 2–3 (insan beklemesi hariç)
> **Başlat:** `/asama A11`

## Amaç
Okuyucunun, aramanın ve atıf ayrıştırıcısının ihtiyaç duyduğu Kur'an yapı verisi kaynak dosyadan üretilir: Tanzil kelime bölmesi (`quran_word`), cüz, hizb ve secde işaretleri, Medine 604 sayfa eşlemesi, onaylı sure adları ve yazım varyantları (`shared/data/sure-adlari.json`). Okuyucu (A24) ve kelime kartı (A25) yapı adımlarına (A11.2, A11.4–A11.6) dayanır, kelime katmanı (A17) yalnız A11.2'ye; sure adları insan onayıyla sonra gelebilir. Hiçbir değer hafızadan yazılmaz. Sayfa sınırlarının kaynağı ve lisansı (AS-10) önce doğrulanır ve karara bağlanır.

## Okunacak belgeler
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §10 sayfa eşlemeleri, §12 sure adları ve insan yazımları
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5 `quran_word`, §6 `surah_alias`, §8 `review`, §9.1 `page_map`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.2 `core` tabloları (`page_map`, `sure`), §7 sayfa eşlemesinin kaynağı, §10 IP-3
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §2 varyant tablosu planı ve riskli adlar
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §2 `medine-604-duzen`, §3.1 QF ve QUL düzen verisi, §7 kontrol listesi
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.1 (hizb kaynağı Doğrulanacak), §9 AS-10
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 7 · [Arama](../../03-veri/05-arama-fts5.md): §1.2 geniş anahtar, §1.3 Kur'an işaretleri

## Kapsam
**Yapılır**
- Tanzil üst veri dosyasının alımı; âyet sayılarının üç yönlü karşılaştırması.
- Tanzil metninden kelime bölme işlevi ve `quran_word` tablosunun Tanzil satırları (QAC alanları boş; A17 doldurur).
- `surah_alias` adayları, kurala göre varyant üretimi, onay sonrası `shared/data/sure-adlari.json` ve üretilen kopyalar.
- Cüz, hizb ve secde verisinin şeması (karar) ve yüklenmesi.
- Medine 604 sayfa eşlemesi (`page_map`), sayfa sorgu işlevi ve test 7.

**Yapılmaz**
- `quran_word`'ün QAC alanları (kök, lemma, morfoloji) ve QAC karşılaştırması (A17). Açık atıf ayrıştırıcısı (A18).
- Mod A satır düzeni ve glif verisi, `mushaf-a-cuz-*` paketleri (A26). Mod B (A40).
- `core` paketine yazma: A13 bu aşamanın çıktısını okur; A12 ve A13 önceden bittiyse küçük ek A11.4'te yapılır ve `publish --flavor dev` yeniden çalışır.

## Adımlar
### A11.1 · Kaynak ve lisans doğrulaması (AS-10)
- Tanzil üst veri dosyasının adresi A04'te doğrulandı (`shared/data/ayet-sayilari.json` içindeki `kaynak_url`); kullanım şartı belirsiz ([lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1, [İ-08](../06-insan-adimlari.md)). Bu aşama dosyayı kalıcı olarak alır ve kaynak kaydını açar.
- `arastirmaci` resmî kaynaktan doğrular ve bağlantısıyla raporlar:
  - Üst veri dosyasının içerdiği alanlar (Arapça sure adı, âyet sayısı, cüz, hizb, secde, sayfa başlangıcı) ve lisans metninin tarihli kopyası için kaynak.
  - AS-10: Medine 604 sayfa sınırlarının kaynağı ve lisansı; adaylar Tanzil üst verisi ve `medine-604-duzen` (QUL ya da QF). QF içeriği hazır veritabanı olarak dağıtılamaz (`kisitlar.hazir_vt_yasak`; lisans defteri §3.1).
  - Sınırların çözünürlüğü (âyet ya da kelime) ve Medine sayfalarının hep âyet başında başlayıp başlamadığı ([Çapa şeması](../../03-veri/01-capa-semasi.md) §10, "veriyle Doğrulanacak").
  - Hizb verisinin kaynağı ([Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md) §4.1).
- Proje sahibi kaynağı seçer; seçim `/karar` ile yazılır. `lisans-denetcisi` lisans defteri §7 kontrol listesini yürütür. Tanzil üst verisi için `pipeline/sources/{kimlik}.toml` ve tarihli lisans kopyası açılır; `medine-604-duzen` seçilirse A06'daki kaydı güncellenir. Defter aynı değişiklikte `/belge-esitle` ile güncellenir.
- Seçilen kaynak `serbest` değilse `page_map` yalnız `dev` derlemeye girer; Yayınlayıcı kaynak düzeyinde süzer ve `public` `core` sayfa eşlemesiz çıkar ([İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §7).
- **Bitti sayılır:** karar defterinde AS-10 kaydı var; yeni TOML'lar `uv run mutalaa sources check` denetiminden geçiyor.

### A11.2 · Üst veri alımı ve kelime bölme
- Tanzil üst veri bağdaştırıcısı A10'daki kalıpla yazılır (`ingest/tanzil.py` genişletilir; varyant adı öneri: `ust-veri`). Dosya `data/raw/` altına alınır; A04 dosyayı yalnız `.tmp/` altına indirmişti. Ham dosyanın SHA-256'sı `tanzil.lock.json` dosyasına eklenir ve `shared/data/ayet-sayilari.json` içindeki `sha256` ile karşılaştırılır; farklıysa dizi A04 üretecinden yeniden üretilir. Çıktı `data/staged/` altında sure listesi, cüz, hizb, secde ve sayfa başlangıçları JSONL'idir.
- Âyet sayıları üç yerde aynı olmalıdır: üst veri, A10'daki Tanzil metni ve A04'ün `shared/data/ayet-sayilari.json` dizisi.
- `pipeline/src/mutalaa_pipeline/anchor/quran.py`: âyet metnini kelimelere bölen ve kod noktası aralıklarını döndüren işlev. Kural (öneri): boşlukla ayrılan belirteç; yalnız U+06D6–U+06ED karakterlerinden oluşan belirteç kelime sayılmaz ([Arama](../../03-veri/05-arama-fts5.md) §1.3 aralığı). A17 bu bölmeyi QAC sayımıyla doğrular (ÇŞ-1).
- Bölme sonucu `quran_word` satırlarına yazılır ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §5): `anchor` `q:{s}:{a}:{k}`, `surah`, `ayah`, `word`, `ayah_index`, `text_uthmani` (âyet metninin `[char_start, char_end)` dilimi, bayt bayt), `norm` (A05 Arapça normalleştiricisi), `char_start`, `char_end`, `source_id = 'tanzil-uthmani'`, `data_version`. QAC alanları (`root_id`, `lemma_id`, `pos`, `features`, `morph_source`) boştur; A17 doldurur.
- Testler: her kelimede `ayet_metni[char_start:char_end] == text_uthmani`; `char_start < char_end`; aralıklar örtüşmüyor; kelime numaraları her âyette 1'den kesintisiz; toplam kelime sayısı rapora yazılır (sayı ezberlenmez).
- Yükleme: `quran_word` satırları A10 kalıbıyla PostgreSQL'e yazılır (`uv run mutalaa export pg --source tanzil-uthmani`; komutun kelime tablosunu da yazması öneri) ve `uv run mutalaa qa run --source tanzil-uthmani` G-BUT ve G-CAP'ten geçer. Sütun sahipliği: A11 yalnız Tanzil sütunlarını yazar, QAC sütunlarına dokunmaz ve satır silmez (upsert); A17 yalnız QAC sütunlarını günceller. Böylece A11'in yeniden çalışması A17'nin verisini silmez.
- **Bitti sayılır:** üç yönlü sayı testi, kelime bölme birim testleri ve `quran_word` dilim eşitliği testi yeşil; `icerik.quran_word` 6.236 âyetin hepsini kapsıyor.

### A11.3 · Sure adları: adaylar, onay, dışa aktarma
- `ad_ar` ve `ayet_sayisi` yalnız üst veri dosyasından gelir. Türkçe kanonik adları Claude Code yazmaz. `.tmp/sure-adlari-girdi.tsv` şablonu üretilir: `no`, `ad_ar`, `ayet_sayisi` dolu; `kanonik_ad`, `diger_adlar`, `kaynak` boş. Proje sahibi doldurur.
- İçe aktarma komutu (öneri: `uv run mutalaa ingest sure-adlari --dosya .tmp/sure-adlari-girdi.tsv`) şunları `surah_alias` tablosuna `status = 'aday'` ve her satır için `review` kaydıyla yazar:
  - `kanonik` ve `diger_ad` satırları (girdiden),
  - `yazim` satırları: şapkalı ve şapkasız, noktalı ve noktasız I, "Sûre-i X", "X Sûresi", "Sûretü'l-X" (kurala göre üretilir),
  - `arapca` satırları: üst verideki ad ve `سورة` önekli biçimi.
- `alias_key` A05'teki geniş anahtardır. İktibas tespiti §2'deki riskli adlar `risky = true` önerisiyle gelir; editör onaylar.
- Onay A14'teki karar uçlarıyla verilir (`POST /api/v1/reviews/decisions`, en çok 100 kayıt, `If-Match`): editör Scalar arayüzünü (`/scalar/v1`, yalnız `Development`) kullanır ya da Claude Code çağrıyı kullanıcının açık talimatıyla yapar; karar her durumda editöründür. Panelde `surah_alias` için ayrı rota yoktur (Açık soru). Hat onaylı alana yazmaz. A14 bitmediyse onay A14 sonrasına kalır.
- Dışa aktarma onaydan sonra (öneri: `uv run mutalaa export sure-adlari`): `shared/data/sure-adlari.json` (114 kayıt; [Çapa şeması](../../03-veri/01-capa-semasi.md) §12 biçimi), `packages/anchors/src/generated/sure-adlari.ts`, hattın Python modülü (öneri: `anchor/sure_adlari.py`) ve C# gömülü kaynağı tek üreteçten çıkar.
- **Bitti sayılır:** JSON 114 kayıt taşıyor; her sure için bir kanonik ad var; `ayet_sayisi` A04 dizisiyle aynı; üç kopya JSON ile aynı (dil başına birer test).

### A11.4 · Cüz, hizb ve secde
- Editoryal şemada ve `core` paket şemasında bu işaretler için tablo yoktur (Açık soru). Öneri, planda onaylanıp `/karar` ile yazılır: editoryal `quran_marker(kind, no, anchor, source_id, data_version)` tablosu (`kind`: `cuz`, `hizb`, `secde`) ve aynı adlı `core` tablosu.
- Göç `sunucu-gelistirici` tarafından `ef-goc` becerisiyle eklenir. A12 bittiyse tablo `packages/content-schema/sql/` DDL'ine, A13 bittiyse Yayınlayıcı'nın `core` sorgusuna bu aşamada eklenir; bitmediyse o aşamalar bu kararı uygular.
- Değerler yalnız kaynak dosyadan yüklenir. Testler değer ezberlemez: cüz sayısı 30, numaralar 1..30 kesintisiz, başlangıçlar okuma sırasında artıyor, ilk cüz `q:1:1` ile başlıyor; her çapa geçerli âyet çapası; hizb ve secde kayıt sayıları kaynak dosyadaki sayıya eşit.
- **Bitti sayılır:** tablo dolu, testler yeşil, karar ve `/belge-esitle` işlenmiş.

### A11.5 · Medine 604 sayfa eşlemesi
- `page_map` satırları seçilen kaynaktan yazılır: `source_id` seçilen kaynak, `page` 1..604, `line` boş (Mod C sayfa düzeyi; Mod A satırları A26'da). `start_anchor` ve `end_anchor` kelime çapasıdır. Kaynak âyet düzeyindeyse başlangıç `q:{s}:{a}:1`, bitiş âyetin son kelimesidir (A11.2 işlevi). Biçim örneği: `medine-604 · sayfa 1 → q:1:1:1 … q:1:7:{son}`. Paketteki `page_map.layout` değeri `medine-604`'tür; Yayınlayıcı kaynak kimliğini bu düzen adına eşler (A13, A24).
- Sayfa sorgu işlevi (öneri: `anchor/sayfa.py`): sayfa → çapa aralığı, çapa → sayfa; 0 ve 605 için hata.
- Testler ([Test stratejisi](../../07-yayin/03-test-stratejisi.md) §5 test 7): 1. sayfanın birimleri `q:1:1`–`q:1:7`; 604. sayfa son surenin son âyetinde (`q:114:6`) biter; 0 ve 605 geçersiz; sayfalar 1..604 kesintisiz; boşluk ve örtüşme yok; her âyet en az bir sayfada.
- **Bitti sayılır:** `page_map` 604 sayfa satırı taşıyor; test 7 yeşil.

### A11.6 · Yükleme ve QA
- `export pg` A10 kalıbıyla çalışır: işaret tablosu ve `page_map` tek işlemde yüklenir (`quran_word` A11.2'de yüklendi); `surah_alias` satırları İ-23'ten sonra aynı komutun ikinci çalışmasıyla gelir.
- QA: G-LIS (yeni kaynak), G-BUT (sayılar), G-CAP (bütün çapalar gramere uyar). Sonuç `data/reports/` altında.
- **Bitti sayılır:** `uv run mutalaa qa run --source {seçilen-kaynak}` 0 ile çıkıyor.

## Kabul ölçütleri
- [ ] Karar defterinde AS-10 ve işaret şeması kararları var; lisans defteri yeni kaynağı ve durumunu gösteriyor.
- [ ] `uv run mutalaa sources check` 0; üst veri dosyasının SHA-256'sı `tanzil.lock.json` içinde.
- [ ] Âyet sayıları üst veri, Tanzil metni ve A04 dizisinde aynı (pytest).
- [ ] `page_map` sorgusu 604 satır, en küçük sayfa 1, en büyük 604 döndürüyor; test 7 yeşil.
- [ ] Cüz, hizb ve secde testleri yeşil; değerler yalnız kaynak dosyadan.
- [ ] `quran_word` Tanzil satırları yüklü: dilim eşitliği testi yeşil, 6.236 âyetin hepsi kapsanıyor, QAC alanları A17'ye kadar boş; toplam kelime sayısı raporda.
- [ ] Onay sonrası: `shared/data/sure-adlari.json` 114 kayıt; `pnpm --filter @mutalaa/anchors test`, `uv run pytest` ve `dotnet test` kopyaların JSON ile aynı olduğunu doğruluyor.
- [ ] Onay öncesi: `.tmp/sure-adlari-girdi.tsv` şablonu üretilmiş; ilerleme dosyasında insan bekleme noktası yazılı.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check && uv run mutalaa qa run --source tanzil-uthmani && uv run mutalaa qa run --source "{seçilen-kaynak}")
(cd pipeline && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), min(page), max(page) FROM icerik.page_map WHERE source_id = '{seçilen-kaynak}' AND line IS NULL;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), count(DISTINCT ayah_index), count(root_id) FROM icerik.quran_word;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT kind, status, count(*) FROM icerik.surah_alias GROUP BY kind, status ORDER BY 1, 2;"
pnpm --filter @mutalaa/anchors test
dotnet test --solution server/Mutalaa.slnx
```
`{seçilen-kaynak}` A11.1'deki karardaki kaynak kimliğidir. `quran_word` sorgusunda ikinci sütun 6236, üçüncü sütun A17'ye kadar 0 olmalıdır. İşaret tablosu karara göre adlandırılır; sorgusu planda yazılır.

## Dikkat
- Sure adları, âyet sayıları, cüz, hizb, secde ve sayfa sınırları hafızadan yazılmaz; testler de sabit değer ezberlemez, kaynak dosyadan ve yapısal kurallardan türetir.
- Kur'an metni değişmez: kelime bölme yalnız aralık hesaplar, metni kopyalamaz ya da normalize etmez (`metin-butunlugu`).
- QF kaynaklı düzen verisi pakete konmaz ve gömülmez (`hazir_vt_yasak`, `embed_ok = false`). Düzen kaynağı `bekliyor` ise `public` derleme sayfa eşlemesiz çıkar.
- `alias_key` için yalnız A05 normalleştiricisi kullanılır; yerel ayarlı küçük harf dönüşümü yasaktır.
- Riskli adlar (Nûr, Fecr …) yalnız güçlü ipucuyla atıf sayılır; bu kural A18'in ayrıştırıcısında uygulanır, burada yalnız işaretlenir.

## İnsan adımları
- AS-10 kaynak seçimi: proje sahibi, A11.1 sonunda. Seçilen kaynak QF ise İ-06 (QF Developer Console hesabı) gerekir.
- İ-23 · Sure adlarının girişi (`.tmp/sure-adlari-girdi.tsv`) ve editör onayı: A11.3'te ([İnsan adımları](../06-insan-adimlari.md)). `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır, Not sütununa biten adımları ve bekleyen işi yazar (ör. "A11.1, A11.2, A11.4–A11.6 tamam; İ-23 bekleniyor"); A17 ve A24 önkoşul denetiminde bu nota bakar. Onaydan sonra aşama `/asama A11` ile sürer.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/tanzil.py` eki, `anchor/quran.py`, `anchor/sayfa.py`, sure adı içe ve dışa aktarma komutları, testler
- `pipeline/sources/{yeni-kaynak}.toml`, lisans kopyası; `tanzil.lock.json` eki
- `shared/data/sure-adlari.json`, `packages/anchors/src/generated/sure-adlari.ts`, Python ve C# kopyaları
- EF Core göçü (işaret tablosu kararı gerektirirse); PostgreSQL'de `quran_word` Tanzil satırları, `surah_alias`, `review`, `page_map` ve işaret satırları
- Karar defterinde AS-10 ve işaret şeması kayıtları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A11-kuran-yapisi-ve-sayfa-eslemesi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A10](./A10-tanzil-alimi.md) · Sonraki: [A12](./A12-arama-indeksi-ve-paket-semasi.md)
