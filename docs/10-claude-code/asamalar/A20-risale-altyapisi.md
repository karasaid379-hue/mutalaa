# A20 · Risale altyapısı (metinsiz: çapa, yapı, sayfa eşleme şeması, sentetik fikstür)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A07](./A07-editoryal-veritabani.md) · [A13](./A13-yayinlayici-ve-yayin-kapisi.md) · **İnsan adımı:** İ-03 · İ-24 (içindekiler ve baskı sayfa verisi) · İ-28 (lügat maddeleri)
> **Ajanlar:** `hat-gelistirici` · `lisans-denetcisi` · `sunucu-gelistirici` (Yayınlayıcı paket tanımları) · `metin-denetcisi` · `test-yazari` · `inceleyici` · **Beceriler:** `lisans-kapisi` · `capa-gramer` · `paket-yayini` · `metin-butunlugu` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A20`

## Amaç
K-05 gereği Risale-i Nur'un altyapısı metne dokunmadan kurulur: kaynak kayıtları ve `kapali` korumaları, kitap slug listesi ve bölüm adlandırma kuralları, baskı kayıtları ve baskı sayfa eşlemesinin şeması, `risale-dizin` ve `risale-{kitap}` paketlerinin Yayınlayıcı tanımları. Risale lügatinin metinsiz altyapısı (kaynak kayıtları, madde şeması, başlık söz listesi, editör kuyruğu) da burada kurulur. Hepsi açıkça sentetik `test-` fikstürüyle (`ic_kullanim`, yalnız `dev`) uçtan uca sınanır. Bu aşamada hiçbir Risale metni indirilmez, saklanmaz ya da işlenmez; metin avukat görüşüne (İ-03) kadar `kapali`dır.

## Okunacak belgeler
- [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md): tamamı; özellikle §1 iç kullanım uyarısı, §2 tarafsızlık, §3 şimdi kurulanlar, §4 yayın kuralları
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.2, §3.4 `risale-dizin`, §4 bağlantıların dağılımı, §7 süzme
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2–§6 (`rn` grameri, slug kuralları, haşiye önerisi, kararlılık), §10 sayfa eşlemeleri
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 (`tur = 'baski'`, `baski_bilgisi`), §4 (`parent_path`, `sentences`, `marks`), §9.1 `page_map`
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §2.3 ayrı dizin kaydı, §2.4 açık sorular
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §1 iç kullanım kuralı, §3.5, §4
- [Arama](../../03-veri/05-arama-fts5.md): §2 içeriksiz tablolar · [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §8 sentetik kaynak

## Kapsam
**Yapılır**
- `risale-1956-1960`, `risale-asil-nusha` ve atıf dizini (`risale-atif-dizini`) kayıtlarının denetimi ve hat korumaları.
- Kitap slug listesi, bölüm kalıpları ve içindekiler girişi için biçim ve doğrulayıcı.
- Baskı kaydı biçimi ve baskı sayfa eşlemesi şeması (karar).
- Yayınlayıcıda `risale-dizin` ve `risale-{kitap}` paket tanımları.
- Sentetik fikstür kaynağı `test-risale-ornek`, üreteci, `dev` yayını ve kapı testleri.
- Lügat altyapısı: kaynak kayıtları, `lugat_madde` şeması, Kelime-Frekans'tan başlık söz listesi (yalnız kelime ve sıklık), editör kuyruğu, fikstür için sentetik maddeler (A20.6).

**Yapılmaz**
- Risale metninin indirilmesi, OCR'ı, saklanması, indekslenmesi, yapay zekâya gönderilmesi; paragraf çapası üretimi (temel metin ve İ-03 sonrası, ayrı iş).
- Âyet atıf dizininin otomatik üretimi (A18'in motoru; İ-03 sonrası). Risale altın seti (İ-03 sonrası).
- Lügat maddelerinin tanımlarını yazmak (insan işi, İ-28) ve Redhouse 1890'ın taranıp içe aktarılması (yolu Doğrulanacak; ayrı iş). Lügat kartı ve yoğunluk ayarı (A31). Konu listesi (v1.x).
- Risale okuyucusu ve cihazda ATTACH yönetimi (A31, A23).

## Adımlar
### A20.1 · Kaynak kayıtları ve korumalar
- `lisans-denetcisi`: A06'da açılan `pipeline/sources/risale-1956-1960.toml` ve `risale-asil-nusha.toml` denetlenir; ikisi de `kapali` ve `embed_ok = false`. `risale-1956-1960` için `kamu_mali_tarihi = 2031-01-01` (lisans defteri §2 ve §6).
- Hat korumaları: `risale-*` kaynakta `ingest`, `ocr run`, `normalize`, `anchor` ve `enrich` 3 ile çıkar; `require_embed_ok` Risale kaynağı için 3 ile durur.
- Lisans defteri §4'teki kaynaklar (`alitekdemir/Risale-i-Nur-Diyanet`, eRisale ve yayınevi lügatleri) hiçbir kaynak kaydına giremez; `sources check` bu adresleri reddeder (öneri).
- Atıf dizini: Yayın kapısı §2.3'ün istediği ayrı kayıt lisans defteri §2'deki `risale-atif-dizini`'dir; metinle birlikte hukukçu görüşüne kadar `kapali` (K-05). A06'nın açtığı TOML'da `kapali` ve `embed_ok = false` olduğu denetlenir. Bu aşamada dizin verisi üretilmez.
- **Bitti sayılır:** `sources check` 0; koruma testleri yeşil.

### A20.2 · Kitap ve bölüm adresleri
- Slug listesi (yol öneri: `shared/data/risale-kitaplar.json`): Risale hazırlığı §3.1 tablosundaki slug'lar, her biri `dogrulandi: false`. Kullanıcı temel baskının içindekileriyle doğruladıkça `true` olur. Küçük kitapların slug'ları ve Lâhika parçalarının numaralandırması Açık sorudur.
- Doğrulayıcı (`pipeline/src/mutalaa_pipeline/anchor/risale.py`): Çapa şeması §5 slug kuralları (küçük harf ASCII, en çok 64 karakter, derinlik en çok 8, `p` ve `s` ile başlayan rakamlı adlar ayrılmış); bölüm kalıpları `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`, `makam-{n}`, `hakikat-{n}`, `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `mukaddime`, `zeyl`, `hatime` ve `hasiye-{n}` (öneri, ÇŞ-4); `dizin` kitap slug'ı olamaz. `rn:{kitap}` → `risale-{kitap}` paket kimliği türetmesi (İçerik paketleri §4).
- İçindekiler girişi: bölüm ağacı (`parent_path` listesi) ve başlıklar için dosya biçimi ve doğrulayıcı. Değerleri Claude Code yazmaz; kullanıcı basılı içindekilerden girer. Yazılmamış bölümler için çapa üretilmez.
- **Bitti sayılır:** doğrulayıcı testleri yeşil; slug dosyası §3.1 tablosuyla birebir.

### A20.3 · Baskılar ve baskı sayfa eşlemesi şeması
- Baskı kaydı `source.tur = 'baski'` ve `baski_bilgisi` (`yayinevi`, `yil`, `cilt_takimi`, `isbn`, `boy`, `yazi`, `metin_esasi`; Risale hazırlığı §3.3). Biçim ve doğrulama hazırlanır; değerleri kullanıcı girer.
- Şema sorunu: `page_map.start_anchor` bir çapa ister. Paragraf çapası temel metinden önce üretilemez; bölüm yolu (`parent_path`) ise çapa değildir. Bölüm başı sayfa eşlemesinin nasıl tutulacağı planda önerilir ve `/karar` ile yazılır (öneri: ayrı bölüm-sayfa tablosu ya da `page_map`'e bölüm yolu sütunu). `risale-dizin` paketindeki `page_map` aynı karara uyar. Göç gerekiyorsa `sunucu-gelistirici` `ef-goc` ile ekler.
- **Bitti sayılır:** karar defterinde şema kararı; doğrulayıcı ve (varsa) göç testleri yeşil.

### A20.4 · Paket tanımları (Yayınlayıcı)
- `risale-{kitap}`: `unit` (paragraf, başlık, haşiye ve dipnot rolleri; `sentences`, `marks`); arama tabloları ve `tr_root_index` taşımaz (İçerik paketleri §3.2).
- `risale-dizin`: `unit_ref` (`rowid`, `anchor`, `pack_id`, `ord`, `label`), içeriksiz `unit_fts`, `unit_tri`, `tr_stem_lex`, `xref_idx`, `tr_root_index`, `page_map` (A12 DDL'i). `unit_ref.rowid` FTS satır kimliğidir; kitap paketinin `rowid` değeri ayrıdır; kalıcı başvuru her zaman çapadır.
- Bir ucu Risale olan bağlantı `risale-dizin` paketine yazılır (İçerik paketleri §4 kural 2). Dizindeki arama indeksi metnin durumuyla, bağlantılar ve sayfa eşlemeleri ayrı dizin kaynağının durumuyla süzülür (§7).
- `label` birim başlıklarından üretilir ("Sözler › 10. Söz › 3. Hakikat ¶4" biçimi); slug'dan türetilmez.
- **Bitti sayılır:** yazıcı testleri yeşil; içeriksiz FTS sorgusu `unit_ref` üzerinden kitap paketindeki birime ulaşıyor.

### A20.5 · Sentetik fikstür ve `dev` yayını
- `pipeline/sources/test-risale-ornek.toml`: `tur = 'risale'`, `license_status = 'ic_kullanim'`, `embed_ok = false`; lisans defterine kayıt.
- Belirlenimci üreteç (komut öneri: `uv run mutalaa ingest fikstur --source test-risale-ornek`): kitap slug'ı `test-ornek`; bölümler (`bolum-1`, `hakikat-1` …), "Deneme paragrafı 1 …" biçiminde paragraflar, başlık birimleri, cümle sınırları, haşiye işareti ve `hasiye-1` bölümü, uzun paragraf, satır içi Arapça harf dizisi (alfabe harfleri; âyet, hadis ya da dua değil). Metin kendi ürettiğimizdir; ilk kayıtta NFC.
- `rn:test-ornek:…` çapaları gerçek slug listesine, kullanıcı verisine ya da kalıcı çapa kaydına yazılmaz (Risale hazırlığı §3.2).
- A20.3 kararına uyan sentetik sayfa eşlemesi ve iki sentetik `xref` satırı (fikstür paragrafından bir âyet çapasına; `status = 'aday'`, `evidence.fikstur = true`).
- `publish --flavor dev`: `risale-dizin` ve `risale-test-ornek` yalnız `dev` manifestine girer. `internal` ve `public` kuru çalıştırmasında P-03 ve P-12 ile dışarıda kalırlar; `risale-*` gerçek kaynaklardan içerik hiçbir derlemede yoktur (P-01).
- **Bitti sayılır:** `dev` manifestinde iki paket var; kuru çalıştırma raporları beklenen kodları gösteriyor.

### A20.6 · Lügat altyapısı (metinsiz)
- Kaynak kayıtları defterle aynı: `lugat-redhouse-1890` (`serbest`), `risale-kelime-frekans` (`serbest`; yalnız kelime ve sıklık sütunları), `lugat-kamus-i-turki` ve `lugat-naci` (`bekliyor`, Doğrulanacak) ([Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §2, §3.6). eRisale ve yayınevi lügatleri ile Kelime-Frekans deposunun `anlam` sütunu hiçbir kayda ve dosyaya girmez.
- Şema (`ef-goc`): `lugat_madde(id, basliksoz, basliksoz_norm, osmanlica_yazim, koken_dil, tanim_tr, ar_kok_id, kaynaklar, duzey, status, surum, content_hash)` [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md) §3.5 önerisiyle; `status` kelime anlamlarındaki gibi `aday` ve `onayli`. Editoryal veritabanı belgesine `/belge-esitle` ile işlenir.
- Başlık söz listesi: Kelime-Frekans deposundan yalnız kelime ve sıklık alınır (komut öneri: `uv run mutalaa ingest kelime-frekans`); `basliksoz_norm` A05 normalleştiricisiyle üretilir; `anlam` sütununun okunmadığı testle kanıtlanır.
- Tanımları editör yazar (İ-28). Yapay zekâ taslağı yalnız `embed_ok = true` serbest sözlüklerden ve "doğrulanmamış" rozetiyle üretilebilir; korumalı lügatler isteme girmez ([Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md)). Editör panelinde lügat kuyruğu A15'in kuyruk bileşeniyle açılır (öneri).
- Lügat verisinin hangi pakette taşınacağı Açık sorudur ([İçerik paketleri](../../03-veri/03-icerik-paketleri.md) IP-10); seçim `/karar` ile yapılır (öneri: `risale-dizin`). Lügat Risale metniyle birlikte görünür ([Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md) §3); metin `kapali` olduğu sürece yalnız fikstürle sınanır.
- `test-risale-ornek` için 10–20 açıkça sentetik lügat maddesi (ör. baş söz "deneme-sözü-1", tanım "Deneme tanımı 1 …") ve üç yoğunluk düzeyi; A31'in lügat kartı bunlarla geliştirilir.
- **Bitti sayılır:** göç ve içe aktarma testleri yeşil; paket yeri kararı karar defterinde; sentetik maddeler `dev` yayınında görünüyor.

## Kabul ölçütleri
- [ ] Risale kaynakları `kapali`; hat komutları bu kaynaklarda 3 ile çıkıyor (testler); veritabanında `risale-1956-1960` ve `risale-asil-nusha` kaynaklı birim 0.
- [ ] Depoda ve `data/` altında Risale metni yok; `metin-denetcisi` ve `lisans-denetcisi` raporları fikstürün yalnız sentetik metin taşıdığını doğruluyor.
- [ ] Slug dosyası §3.1 tablosundaki kayıtları `dogrulandi: false` ile taşıyor; doğrulayıcı testleri (ayrılmış adlar, `dizin`, bölüm kalıpları, uzunluk ve derinlik) yeşil.
- [ ] Baskı sayfa eşlemesi şeması kararı karar defterinde; `risale-atif-dizini` TOML'u defterle aynı (`kapali`).
- [ ] `risale-dizin` ve `risale-{kitap}` yazıcı testleri yeşil; içeriksiz FTS araması `unit_ref` üzerinden kitap paketine ulaşıyor.
- [ ] `dev` manifestinde `risale-dizin` ve `risale-test-ornek`; `internal` ve `public` kuru çalıştırma raporlarında P-03 ve P-12 ile dışarıdalar.
- [ ] Lügat kaynak kayıtları defterle aynı; başlık söz listesi içe aktarımı yalnız kelime ve sıklık alıyor (test); `lugat_madde` göçü uygulanıyor; IP-10 kararı karar defterinde; fikstürün sentetik lügat maddeleri `dev` yayınında.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
(cd pipeline && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT source_id, count(*) FROM icerik.unit WHERE kind = 'risale' GROUP BY 1;"
dotnet test server/Mutalaa.slnx
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
```
SQL sonucu yalnız `test-risale-ornek` satırını göstermelidir.

## Dikkat
- Risale metni hiçbir biçimde projeye girmez: indirme, kopyala-yapıştır, OCR, test örneği yok. Claude Code Risale metnini, bölüm başlıklarını ya da içindekileri hafızadan yazmaz; kitap slug'ları yalnız Risale hazırlığı §3.1 tablosundan alınır.
- Risale için yapay zekâ özeti yoktur (K-25, K-30); Risale kaynakları `embed_ok = false` taşır.
- `ic_kullanim` yalnız `dev`'de görünür; `test-` kaynak hiçbir durumda `public`'e girmez (P-12).
- Tarafsızlık: yayınevi markası öne çıkarılmaz, baskılar eşit gösterilir, topluluklara özgü adlar kullanılmaz (Risale hazırlığı §2).
- ATTACH bütçesi: Risale kitapları tek tek bağlanmaz; arama yalnız `risale-dizin` üzerinden yapılır, kitap paketleri istek anında en çok üç tane bağlanır (A23 ve A31 için not).
- Haşiye adlandırması (`hasiye-{n}`) ve Lâhika parça numaraları öneridir; temel metin gelmeden kesinleştirilmez.

## İnsan adımları
- İ-03 · Avukat görüşü: bu aşamayı engellemez. Görüş gelince `license_status` değişikliği ikinci onaylı inceleme ve `/karar` ile yapılır; metin işleri ayrı bir aşamada planlanır. A20 o işi yapmaz.
- İ-24 · İçindekiler ve baskı sayfa verisinin basılı kitaptan girilmesi kullanıcı işidir; ilerleme dosyasına bekleyen veri olarak yazılır ([İnsan adımları](../06-insan-adimlari.md)).
- İ-28 · Lügat maddelerinin yazımı ve onayı: aşamayı durdurmaz; altyapı ve kuyruk hazır olunca editör işi başlar.

## Çıktılar
- `pipeline/sources/risale-1956-1960.toml`, `risale-asil-nusha.toml`, `test-risale-ornek.toml`; hat korumaları ve testleri
- `shared/data/risale-kitaplar.json` (öneri), `pipeline/src/mutalaa_pipeline/anchor/risale.py`, içindekiler ve baskı kaydı doğrulayıcıları, fikstür üreteci
- Yayınlayıcıda `risale-dizin` ve `risale-{kitap}` paket tanımları ve testleri; gerekirse EF Core göçü
- `dev` kanalında `risale-dizin` ve `risale-test-ornek`; karar defterinde sayfa eşlemesi şeması
- Lügat: kaynak TOML'ları, `lugat_madde` göçü, başlık söz listesi içe aktarımı ve testi, editör kuyruğu, sentetik lügat maddeleri; IP-10 kararı

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A20-risale-altyapisi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A19](./A19-hadis-hatlari.md) · Sonraki: [A21](./A21-mobil-iskelet.md)
