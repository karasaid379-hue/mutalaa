# A16 · Elmalılı mealleri: orijinal ve sadeleştirilmiş, hazır metin yolu, inceleme kuyruğu, iki tur

> **Sürüm:** 2.1 · **Tarih:** 12 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-48](../../00-ozet/02-karar-defteri.md#k-48--editör-api-kuralları-inceleme-kararı-ikinci-onay-eşzamanlılık-yayın-talebi-ve-sayfa-görseli) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-11
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `sunucu-gelistirici` · `web-gelistirici` · `arastirmaci` · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · `paket-yayini` · **Tahmini oturum:** 5–7 Claude Code oturumu; insan turları ayrıca
> **Başlat:** `/asama A16`

## Amaç
Elmalılı'nın iki mealini hazır dijital metinle içe almak (K-49): **orijinal meal** (`meal:elmalili`, kaynak `elmalili-meal`, Vikikaynak "Kur'an" sayfaları) ve **sadeleştirilmiş meal** (`meal:elmalili-sade`, kaynak `elmalili-sade-meal`, fawazahmed0/quran-api `tur-elmallsadelesti`). Arayüzde ikincisi "sadeleştirilmiş" etiketiyle görünür ve orijinal meali değiştirmez. İki meal de `taslak` girer, iki insan turundan geçer ve onaylanınca `core` paketine girer. A09 ölçümü beklenmez; OCR ve özgün baskı taraması proje sonuna ertelendi (S-15).

Aşama tedarikle başlar (A16.0): kaynak dosyalarını Claude Code internetten indirir, ölçer ve kilitler. Claude Code bağdaştırıcıları, kapıları, yüklemeyi, API süzgeçlerini ve editör ekranlarını kurar; düzeltme ve onay insan turlarıdır (İ-11). Yapay zekâ meal yazmaz, çevirmez, düzeltmez ve sadeleştirmez.

## Okunacak belgeler
- [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi): tamamı (iki meal, yol, sınır durumları, inceleme kuralları, kapılar, atıf); [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme) madde 2–4 (çıkarılmış metin, `taslak` başlangıç durumu) ve [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1–2 (tedarik akışı, indirme)
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): tamamı (§3 aile ayrımı ve tedarik, §6 âyetlere bölme, §7 editör, §8 QA ve örneklem, §9 künye ve atıf)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §5 veri soyu, §8 yeni kaynak ekleme, §9 kapılar (G-HIZ, G-CAP, G-INC, G-KAY), §10 yapay zekâ politikası, §12 yeniden üretilebilirlik
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.3 Elmalılı kartları, §4 Seçilmeyen adaylar
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §1 meal çapası, §7 kendi metnimizin ilk kaydı
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §4 `unit` ve `metin_durumu`, §8 `review`, ikinci onay ve hat yazma istisnası
- [Backend API](../../02-mimari/05-backend-api.md): §4 inceleme uçları ve liste süzgeçleri, §4.1 karar kuralları, §6
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1 `core` içeriği, §5 meal başlığı
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §7.3 değişiklik yönetimi
- [Belge çelişkileri](../07-belge-celiskileri.md): BÇ-08 (çözüldü), BÇ-53 (meal için çözüldü), BÇ-54, BÇ-58 ve BÇ-59 (bu aşamada değil; A18 ve A20)

## Kapsam
**Yapılır**
- Tedarik doğrulaması, indirme ve ölçüm (A16.0): iki meal ve EPUB tanığı; ölçüm raporu (`data/reports/a16-tedarik-olcum.json`).
- Belge ve kit eşitlemesi (A16.1).
- Kaynak kayıtları, kilit dosyası, Vikikaynak ve JSON bağdaştırıcıları, tanık bağdaştırıcıları, `extract/meal.jsonl` vektörü (A16.2).
- Normalize, anchor, meal kapıları (G-KAY, G-BUT, G-CAP, G-NOR, G-HIZ), tanık skoru, kapsam ve sadeleştirme taraması raporları (A16.3).
- `export pg` ile `taslak` yükleme ve inceleme kuyruğu (A16.4).
- `GET /api/v1/reviews` süzgeçleri (`kaynak`, `asama`), birleşik izleyen birimde 422, editörde iki meal sekmesi, rozet ve uyarı kutusu (A16.5).
- `core` kataloğuna iki meal ve `dev` yeniden yayını (A16.6).
- `qa sample` örneklem aracı, ikinci okuma ve G-INC ölçüm raporu; tur 1 ve tur 2 (A16.7; İ-11).

**Yapılmaz**
- OCR, tarama ve `page_map` (S-15). Özgün baskıyla karşılaştırma ve "temel metin" sayılma da S-15'tedir.
- Tefsir metni (`tf:elmalili`) ve A37 kaynak seçimi: tanıklar yalnız A16 raporu içindir.
- Mobilde meal seçimi ve gösterimi (A24, A32).
- Ofsetli tablolar ve iktibas bağlantısı (A18; [BÇ-58](../07-belge-celiskileri.md#1-karar-bekleyenler)). Birim `marks`/`sentences` yeniden hesabı (A20; [BÇ-59](../07-belge-celiskileri.md#1-karar-bekleyenler)).
- Kelime anlamları (A17). Sürüm dondurma ve mağaza yayını (A34).
- Yapay zekâ ile meal üretimi, çevirisi, düzeltmesi ya da sadeleştirmesi: yasaktır.
- T ailesinden ("yeni Elmalılı": Tanzil `tr.yazir` vb.) metin almak: Elmalılı adıyla alınmaz.

## Tedarik
Araştırma 11 Kasım 2026 (`arastirmaci`); A16.0'da kodla yenilenir. İnternetteki "Elmalılı meali" metinleri üç ailedir; ayırt edici işaret Johanna Pink'in 16:43 âyeti tespitidir ([GloQur](https://gloqur.de/?p=2195)):
- **O, özgün:** Vikikaynak, archive.org `meal-i-serif` EPUB'ı, kuranmeali.com "Orijinal", Açık Kuran.
- **S, sadeleştirilmiş:** fawazahmed0 `tur-elmallsadelesti`, Açık Kuran "sadeleştirilmiş".
- **T, "yeni Elmalılı" (1994–96):** Tanzil `tr.yazir`, fawazahmed0 `tur-elmalilihamdiya` ve `tur-elmallsadelesti1`, GitHub `elmalili-meal/kuran`, kuranmeali id=16. Bu aile Elmalılı adıyla alınmaz.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Orijinal meal (O); kaynak `elmalili-meal` | Vikikaynak `Kur'an/<Sure> Suresi`, 114 sayfa, wikitext, `{{kısım\|\|N}}`; `revid` 74319–158621 | MediaWiki API `action=query&prop=revisions&rvprop=ids\|timestamp\|size\|sha1\|content&rvslots=main&format=json`, 50 başlık/istek, istekler arası ≥ 1,5 sn, kişisel bilgi taşımayan genel `User-Agent` | 11 Kasım: 114/114 `lastrevid` 1 Kasım'la aynı; `length` toplamı 961.210; `kısım` 6.238, benzersiz âyet 6.236. Liste SHA-256 `965a6249…b308a` A16.0'da yeniden hesaplanır | Döküm `trwikisource-20261101-pages-articles.xml.bz2` (25.376.776 bayt, SHA-1 `c06eaf65…32bc`); revizyonlar kilitle karşılaştırılır |
| Orijinal mealin ikinci tanığı (O ailesi); kaynak `elmalili-meal-epub`, yalnız QA | archive.org `elmalili-hamdi-yazir-meal-i-serif` EPUB, 379.462 bayt, MD5 `ec786be4…6fcc`, SHA-1 `97477fdd…3bc6` | `https://archive.org/download/<öğe>/<dosya>`; dosya adı ve özetler `metadata` kaydından | 6.236 âyet A16.0'da sayılır | Kardeş öğe `…-tefsirindeki-meal-i-serif` PDF (1.376.405 bayt, SHA-1 `597cf819…f156`); PDF indirilmez, yalnız yedek olarak kayıtlıdır |
| Bağımsız tanık adayı (ayrı nüsha soyu); kaynak `elmalili-tefsir-yek` | KULLANILMADI. YEK tenkitli neşir (Köksal ve Kaya, 2021–2023; esas: 1935–38 matbu baskı ve üç yazma); archive.org `hak-dini-kuran-dili` (cilt başına `djvu.txt`) ve `…-1-6-…-yek-yay` (`djvu.txt` 13.692.391 bayt) | — | A16.0 ölçümünde (11 Kasım 2026) YEK metin katmanı meal bloklarına ayrılamadı; tanık yalnız EPUB'dır (`elmalili-meal-epub`). Kayıt açılmadı, dosya indirilmedi ya da kullanılmadı | A37 adayıdır (tefsir hazır metin adayı) |
| Sadeleştirilmiş meal (S); kaynak `elmalili-sade-meal` | fawazahmed0/quran-api `editions/tur-elmallsadelesti.json` @ `93e6f64925ae76273520d636fcaaf061129f2316`; 1.471.811 bayt, blob `f9421578…fada6`; edition `source` qurandatabase.org | `https://raw.githubusercontent.com/fawazahmed0/quran-api/<commit>/editions/tur-elmallsadelesti.json` | 6.236 kayıt ve S aile işareti A16.0'da kodla ölçülür | Açık Kuran "sadeleştirilmiş" âyet sayfaları (hız sınırlı) |
| Wikitext ayrıştırıcı | `mwparserfromhell` 0.7.2 (cp313 win_amd64 tekeri) | `uv add --directory pipeline mwparserfromhell==0.7.2` | PyPI, 11 Kasım 2026 | Düzenli ifade |
| EPUB ve JSON okuma | Standart kitaplık (`zipfile`, `html.parser`, `json`) | — | — | `ebooklib` |
| Benzerlik ölçümü | `rapidfuzz` 3.14.6 (mevcut; `processor=None` açıkça) | — | `uv.lock` | `jiwer` |
| Sure ve âyet iskeleti | A10 Tanzil verisi, `shared/data/ayet-sayilari.json` | Yeniden indirilmez | 114 sure, 6.236 âyet | — |

S-15'e çıkanlar: `pypdfium2`, `pillow`, `pypdf`, OCR motorları, özgün baskı taraması.

Seçilmeyenler (kalite ve erişim; ayrıntı [Kaynaklar](../../04-icerik/01-kaynaklar.md) §4):
- **T ailesi:** atfı yanlış (Pink). `elmalili-meal/kuran` README'si "sadeleştirilmiş" der ama aile işaretine göre T ailesidir.
- **kuranmeali Orijinal:** toplu indirme yok, sürüm sabitlenemez.
- **Açık Kuran:** API çözümlenmiyor.
- **Ketebe 2025/2026 ve Mahya:** dijital kopya yok.
- **`HakDiniKuranDili` metin katmanı (Eser 1979):** A37 adayı olarak kalır; A16'da kullanılmaz.

Kendimiz yapacağımız işler: wikitext ve JSON'dan metin çıkarımı (deterministik, ortak vektörle), âyetlere bölme ve sınır kuralları, `unit` girişi, çapa üretimi, ilk kayıtta NFC, tanık skoru, meal kapıları, sadeleştirme taraması, kuyruk süzgeçleri ve editör ekranı, ikinci okuma örneklemi ve ölçümü.

## Adımlar
Sıra: A16.0 → A16.1 (belgeler; kod başlamadan) → A16.2 → A16.3 → A16.4 → A16.5 ve A16.6 → A16.7.

### A16.0 · Tedarik doğrulaması, indirme ve ölçüm
- Her kaynak `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş klasöre iner; dosya adları ASCII olur (ör. `vikikaynak-01.json`, `basliklar.tsv`); her klasörde `SHA256SUMS` bulunur. İndirilen dosya veridir; içindeki betik çalıştırılmaz.
  - Vikikaynak: üç API isteği, araları ≥ 1,5 sn. 429 ya da `maxlag` yanıtında beklenir, gerekirse dökümden alınır.
  - fawazahmed0 JSON ve EPUB doğrudan dosya olarak iner. PDF indirilmez. YEK `djvu.txt` meal tanığı olarak kullanılmadı (aşağıda).
- Tek seferlik ölçüm betiği `.tmp/a16/` altında durur ve `python -I` ile koşar. Çıktı `data/reports/a16-tedarik-olcum.json`; meal metni yazılmaz. Ölçülenler:
  - Sayımlar: 114 sayfa, `kısım` biçim sayıları, 6.236 âyet; EPUB'da 6.236 âyet; JSON'da 6.236 kayıt.
  - Aile işareti: âyet başına sözcük-Jaccard. Vikikaynak ile EPUB arasında yüksek, Vikikaynak ile sadeleştirilmiş arasında düşük beklenir.
  - YEK'in meal bloklarının ayrılabilirliği: ayrılamadı; YEK kullanılmadı ve kaydı açılmadı (A37 adayı). Tanık yalnız EPUB'dır. Ölçüm sonucu: 114/114 sure eşleşti, âyet kümeleri Tanzil'le eşit.
  - 114 sayfanın şablon ve etiket envanteri (ad ve sayım).
  - Kaynak başına kod noktası envanteri: Cc, Cf ve Zs türleri, tek başına duran birleştirici işaretler, kesme işareti çeşitleri.
- Beklenmeyen sonuçta durulur ve kullanıcıya gösterilir.
- **Bitti sayılır:** `sha256sum -c` her klasörde geçer; ölçüm raporu var; tedarik tablosu ölçümle güncel.

### A16.1 · Belgeler ve kit eşitlemesi
- `belge-bekcisi` belgeleri K-49'a göre eşitler (bu dosya dahil); kit dosyalarını (`icerik-hatti` ve `metin-butunlugu` becerileri, `test-vektoru` becerisi, `paylasilan-paketler` ve `icerik-hatti` kuralları, `arayuz-denetcisi` ajanı) ana oturum günceller, ayrı commit atar.
- Arama ifadeleri (docs/ ve .claude/ altında): `A09`, `OCR`, `pilot`, `ingest register`, `ingest scans`, `Sadeleştiril`, `sadeleş`, `A16'da`, `Açık soru: A16`, `1935–1938`, `İ-09`, `İ-10`, `İ-17`, `G-HIZ`, `G-MET`, `tr.yazir`, `A16.1`…`A16.9`. Karara aykırı atıf kalmaz.
- **Bitti sayılır:** aynı aramalar yeniden koşar ve aykırı atıf kalmaz; `belge-esitle` bağlantı denetimi temiz; `node --test ".claude/hooks/test/*.test.mjs"` yeşil.

### A16.2 · Kaynak kayıtları, kilit ve içe aktarım (`hat-gelistirici`)
- **Kaynak kayıtları.** `elmalili-meal.toml` için `surum` yoktur ve `export pg` onsuz çıkış 2 verir; eklenen alanlar: `surum`, `kaynak_url`, `provider`, K-49 atfı; notlar yeniden yazılır. `surum` biçimi (ASCII, boşluksuz): `elmalili-meal` `revid-liste-965a6249f61c-2026-11-11`, `elmalili-sade-meal` `commit-93e6f64925ae76273520d636fcaaf061129f2316`, `elmalili-meal-epub` `sha1-97477fdddf3b-2026-11-11`; `data_version = '{slug}@{surum}'`. Yeni kayıtlar: `elmalili-sade-meal.toml`, `elmalili-meal-epub.toml`. `elmalili-tefsir-yek` kaydı açılmaz (YEK kullanılmadı; A37 adayı).
- **Tek kayıt modülü** `ingest/meal_kaynaklari.py`: kaynak kimliğine bağdaştırıcıyı, çapa eserini, kilit bölümünü, tanık bağını ve kapı kümesini eşler. `cli.py` (normalize, anchor, ingest), `qa/run.py`, `export/pg.py` ve `qa/__init__.py` `kaynak_kapilari` bu kümeden türer. Tutarlılık testi yazılır.
- **Kilit** `ingest/elmalili_meal.lock.json` kendi şemasını taşır:
  - Vikikaynak sayfa başına: `baslik`, `sure` (114 açık eşleme; başlık çalışma sırasında ayrıştırılmaz), `revid`, `sha1`, `wikitext_sha256`.
  - Sadeleştirilmiş meal: `url`, `commit`, `boyut`, `sha256`.
  - Tanık (EPUB): öğe, dosya, boyut, `sha1`, `sha256`.
  - `ingest meal --kilit-oner` öneriyi yazdırır, dosya yazmaz. Her sayfanın âyet sayısı Tanzil sayısıyla karşılaştırılır. Kilit yalnız `/karar` ile değişir (K-49 madde 11).
- **Yeniden kullanım.** Yardımcılar (`_yaz_esitle`, `_klasoru_tasi`, `tarih_gecerli`, `ham_kopyala` …) `ingest/tanzil_ust_veri.py` örneğindeki gibi `ingest/tanzil.py` ve `ingest/sure_adlari.py`'den içe aktarılır. Taşıma yapılmaz; A10 ve A11 koduna dokunulmaz.
- **Vikikaynak bağdaştırıcısı** (`ingest/elmalili_vikikaynak.py`, `SourceAdapter` ve `run_ingest` düzeni). `parse` adımında sırayla:
  1. `mwparserfromhell` ile ayrıştırma; çağrı parametreleri açıkça verilir.
  2. A16.0 envanterinden kurulan açık kural tablosu: her şablon ve etiket için "at", "N'inci parametreyi tut" ya da "boşluk yap". Bilinmeyen şablon ya da etiket çıkış 2 verir.
  3. Satır sonu kuralı yazılır. `str.split()`, `str.strip()` ve `\s` kullanılmaz (U+00A0); sayılar `[0-9]` ile okunur.
  4. Sayfa başı ve sonu bölgeleri ile K-49 madde 8 sınır kuralları; uyarılar.
  5. `anchor/metin.py` `kanonik_metin` (ilk kayıt; NFC yalnız burada).
  6. Konum ve `provenance`: ham dosya SHA-256, `CIKARICI_SURUMU`, `mwparserfromhell` sürümü, `unicodedata.unidata_version`. Konum kilitli revizyonun wikitext dizgisinde yarı açık kod noktası aralıklarının listesidir; `@` ofseti değildir.
  - Çıktı doğrudan `meal:elmalili:{s}:{a}` birimleridir.
- **Sadeleştirilmiş meal bağdaştırıcısı:** `json`, çapa `meal:elmalili-sade`; konum JSON yoludur.
- **Tanık bağdaştırıcıları.** EPUB (`zipfile` ve `html.parser`) `data/raw`'a alınır; YEK kullanılmadı. Çıktı birimsiz, (sure, âyet) anahtarlı staged `tanik.jsonl` dosyasıdır; adı `lineage.py`'de tanımlanır.
- **Komut:** `uv run mutalaa ingest meal --source <kimlik> [--gelen-tarih] [--force] [--dry-run]`. `--limit` çıkış 2 verir.
- **Vektör** `shared/test-vectors/extract/meal.jsonl`: yalnız sentetik girdi; her tuzak için bir satır (şablon, `<ref>`, `<br>`, nowiki, `&nbsp;`, `''` ve `'''`, satır sonu, numarasız, aralıklı, ardışık işaretler, ortak metin, yinelenen, besmele). Kayıt yerleri: `check-lib.mjs` `KINDS`, `check.test.mjs` `VECTOR_KINDS`, `pipeline/tests/vektor_dosyalari.py` `KOSULAN`, `server/tests/Mutalaa.Domain.Tests/VectorCoverageTests.cs` `SkippedFiles` (K-49 madde 13 gerekçesiyle). Gerçek meal metni teste ve vektöre girmez.
- `mwparserfromhell` tip bilgisi taşımıyorsa `pipeline/stubs/` altına taslak eklenir.
- **Testler.** Çıkış 2 beklenenler: kilit uyuşmazlığı, bozuk wikitext, bilinmeyen şablon, `--limit`. Yazım davranışı: `--dry-run` `data/raw`'a yazmaz; var olan raw yeniden kullanılır; `--force` ile iki koşu bayt bayt aynı staged üretir. Sınır kuralları (birleşik ve ardışık işaretler, `ortak_metin`, numarasız, yinelenen, besmele işareti, sayfa başı ve sonu) ayrı ayrı sınanır. Gerçek veride beklenen sayılar (11 Kasım 2026 ölçümü, orijinal meal): 19 baş ve 19 izleyen birleşik birim, 17 `ortak_metin` birimi, 3 numarasız parça, Nisâ 68 yinelenen numara; `{{kısım||besmele}}` gerçek veride yoktur.
- **Bitti sayılır:** iki meal ve tanıklar staged'de; testler ve vektör yeşil.

### A16.3 · Normalize, anchor, kapılar ve raporlar (`hat-gelistirici`, `metin-denetcisi`)
- **Ortak işlevler.** `adimlar/meal.py` kaynak parametreli çalışır (şablon: `adimlar/fikstur.py`). normalize: `search_keys` ile `tr_*`. anchor: `content_hash`, `ord`, `ayah_range` (baş birimde kapsam aralığı), `metin_durumu = 'taslak'`, `data_version = '{slug}@{surum}'`.
- **Tanık skoru.** `elmalili-meal` anchor adımında hesaplanır; tanık staged dosyası girdi olur. `rapidfuzz`, `processor=None`, `tr_narrow` üzerinde; ölçek 0–100; yöntem sürümüyle staged'e yazılır.
- **Kapılar** (`qa/checks/meal.py`, `MEAL_KAPILARI`): G-KAY; G-BUT (yeniden üretilebilirlik, birleşik birim için iki yönlü değişmez, NFC; U+200C ve U+200D serbest, öteki Cf ve Cc karakterleri red; sayfa başı ya da sonu bölgesi 100 karakterden uzunsa kalır: `bolge_sayisi`, `en_uzun_bolge`); G-CAP (meal tanımı: çapa durur, `content_hash` yalnız kilit değişiminde değişebilir ve rapora yazılır); G-NOR; G-HIZ (sert kapı: kalırsa `export pg` yapılmaz). G-MET bu yolda uygulanmaz (K-49 madde 12). `qa/rapor.py` sayı sözlüğüne `5: "bes"` eklenir; `cli.py` yardım metni güncellenir.
- **Raporlar** (`data/reports/`, meal metni yok): kapsam raporu; kod noktası envanteri; çapraz tanık raporu (başına tanığın baskı esası ve ortak köken ihtimali yazılır; skor "özgün baskıya sadakat" diye sunulmaz); sadeleştirme taraması (orijinal mealde; veriye dayanır, yapay zekâ kullanılmaz: aynı âyette sadeleştirilmiş mealle ortak olup tanıkta bulunmayan sözcükler, şapka ve kesme farkları; karşılaştırma `tr_narrow` ve ham sözcüklerle).
- **Testler:** G-HIZ kalınca çıkış 1; beş kapılı rapor kabul edilir; G-BUT değişmezi; U+200C korunur.
- **Bitti sayılır:** iki kaynakta da kapılar geçti; `metin-denetcisi` raporu temiz.

### A16.4 · Yükleme ve inceleme kuyruğu (`hat-gelistirici`)
- **Yönlendirme.** `export/pg.py` meal kaynaklarını kayıt modülünden `export/pg_meal.py`'ye gönderir. Tanıklar yüklenmez. Şablonlar: `export/pg_fikstur.py` (taslak `INSERT_UNIT`) ve `export/pg_sure_adlari.py` (`INSERT_REVIEW`); `pg_fikstur`'un fark denetimi kullanılmaz, meal için ayrı denetim yazılır. Var olan advisory lock ve tek işlem korunur. `page_map` yazılmaz (S-15).
- **Birim kuralları:** K-49 madde 10 ve 11. Hat meal biriminin metnine hiç yazmaz; özeti farklı birim (editör düzeltmesi) `korunan_duzeltilmis` sayacına girer (yeniden kuyruğa giren taslak birim sayılmaz); `tr_stem IS NULL` ise veritabanındaki güncel metinden hesaplanır (`export`'un `normalize`'ı içe aktarması `tests/test_yaprak_kitapliklar.py` ile sınanır; uygun değilse hesap ayrı bir adıma alınır).
- **İnceleme kuralları:** K-49 madde 9. Hat kaydı `eylem = 'oner'`, `koken = 'hat'`, `oneren = 'hat'`; `onerilen = {metin, content_hash, uyari?: [kod], tanik?: {skor 0..100, kapsam: [ilk, son] ya da null, yontem "rapidfuzz.fuzz.ratio/tr_narrow", yontem_surumu "1", kaynak "elmalili-meal-epub"}}`; uyarı kodları `birlesik_meal`, `ortak_metin`, `numarasiz_parca`, `yinelenen_numara`, `sira_disi`, `besmele_meali`; anahtar `(unit, 'metin', onerilen.content_hash)`; birleşik izleyen birimde `onerilen` NULL; kaynak sürümü değişiminde `onceki` = `{metin, content_hash}`. `pg_meal` açık inceleme açmadan önce sunucunun düzeltme ucuyla aynı `unit-correction:{çapa}` danışma kilidini alır. İlk yüklemede kayıtlar tanık skoruna göre artan sırada eklenir; bu sıra yalnız ilk yükleme için geçerlidir.
- İlk `export pg`'den önce önlem olarak `scripts/backup-db.ps1` çalıştırılır.
- **Testler** (`veritabani` işareti, `MUTALAA_DEGISMEZLIK_ZORUNLU=1`): ilk yükleme `taslak` girer ve ikinci koşu 0 değişiklik verir; ret, ilk onay, ikinci onay ve düzeltme UPDATE ile benzetilir, ardından koşu çıkış 0 verir, 0 yeni kayıt açar ve `korunan_duzeltilmis` sayacını gösterir; `tr_stem` dolar; ret sonrası birim yeniden kuyruğa girer; birleşik birimde `onerilen` NULL olur; kilit değişimi ve çıkış 1 ile 2 durumları sınanır.
- **Bitti sayılır:** yerel veritabanında 2×6.236 birim `taslak`; açık kayıt sayısı 2×6.236 (birleşik izleyenler dahil); ikinci `export pg` 0 değişiklik.

### A16.5 · API ve editör (`sunucu-gelistirici`, `web-gelistirici`)
- **API.** `GET /api/v1/reviews` iki isteğe bağlı süzgeç alır: `kaynak` (`unit.source_id`) ve `asama` (ilk ya da ikinci onay bekleyen). Release derlemesiyle `openapi/v1.json` yeniden üretilir, `gen:api` çalışır. `birlesik_ile` taşıyan birimde metin değiştiren karar ve düzeltme 422 verir. "A16'da kalkar" iletileri ve yorumu BÇ-59'a (A20) çekilir; iki ileti de "Ofsetli" ile başlar (editörde `OFFSET_MARKER` eşleşmesi). Dosyalar: `ReviewDecisions.cs`, `UnitEndpoints.Corrections.cs`.
- **API testleri.** Hat kökenli meal iki onayla `onayli` olur; `onerilen` NULL ile durum onayı çalışır; `onceki` dolu kaynak farkı kaydı onaylanır; hat kaydı açıkken düzeltme 409 verir; süzgeçler çalışır; ileti belirteci yerindedir.
- **Editör.** `kuyruk/ocr` rotasına kaynak sekmeleri (orijinal ve sadeleştirilmiş) ve "ikinci onay bekleyenler" görünümü eklenir; seçim URL'dedir (`?kaynak=orijinal|sade`, `?asama=ilk|ikinci`) ve liste yükleme sayısı canlı bölgeden duyurulur. Liste öğesinde ve ayrıntıda kaynak adı ve etiket görünür. Ayrıntıya eklenenler: `onerilen.uyari` kutusu (kodlara göre); "tanık uyumu" gösterimi (Güven etiketi kullanılmaz); `AyahSection` içinde `attrs.kapsam`; izleyen birimde baş birime bağlantı ve kapalı Düzelt; besmele notu. `OpenQuestionButton` aşamaları `'S-15'` ve `'A20'` olur; `tr-ocr.ts` `notMapped` metni güncellenir; `screens/baglanti/target.ts` yorumuna "bağlantı hedefi orijinal meal; A18'de gözden geçirilir" yazılır. Vitest ve axe testleri.
- **Bitti sayılır:** `dotnet test`, `dotnet format`, OpenAPI ve `gen:api` farkı temiz; editör `test`, `lint`, `typecheck` yeşil.

### A16.6 · Yayınlayıcı ve yeniden yayın (`sunucu-gelistirici`)
- **Katalog.** `PackCatalog.cs`'te `core`'a `elmalili-meal` ve `elmalili-sade-meal` eklenir (`Content`, `Required: false`). K-47 notu: ilk meal yayınından sonra meal çapa kümesi donar. Başlık "Kur'an ve Elmalılı mealleri".
- **Testler.** `PackCatalogTests` güncellenir; kapı girdisi meal satırıyla ve meal satırı olmadan sınanır; `PackAssembler`: `dev` ve `internal`'da `approved = 0`, atıf `atif_metni` ve `surum` alanlarını olduğu gibi taşır; `public`'te P-10 süzmesi; `capa-kayboldu` durumu; sentetik meal fikstürüyle uçtan uca test (yalnız test kodunda; depoya yeni `test-` kaydı eklenmez).
- **İlk `publish --flavor dev`.** Yalnız G-HIZ ve K-49 madde 8 kesinleştikten sonra yapılır. Önce LAN IP ve `Storage:PublicBaseUrl` denetlenir. Ardından `verify --flavor dev` koşar; `internal` ve `public` kuru çalıştırılır.
- **Bitti sayılır:** `verify` 0; `core` öz denetiminde iki meal için 6.236'şar `unit`; `public` kuru çalıştırmada meal birimleri dışarıda.

### A16.7 · Tur araçları ve editör turları (İ-11)
- `uv run mutalaa qa sample --source <kimlik> --n 600 --seed <sabit>`: sure grubuna göre tabakalı örneklem (cilt S-15'e kalır). İkinci okuma rapor şablonu ve G-INC ölçüm raporu (veritabanını okur).
- Tur 1 her âyetin iki ayrı kişiyle onayıdır (K-38'deki 60 âyetlik elle ön denetimi karşılar); tur 2 en az 600 âyetlik ikinci okumadır, hedef %95 güvenle hatalı âyet oranı < %0,5 (K-49 madde 12; hiç hata yoksa üst sınır yaklaşık `3 / n`). Hata bulunursa desen düzeltilir, ilgili bölümler taranır, yeni örneklem çekilir. Turlar iki meal için yapılır; Faz 1'i yalnız orijinal mealin turları bağlar (K-49 madde 6).
- Kod işi bitince A16 `engelli` olur. Not: "A16.0–A16.6 tamam; İ-11 tur 1 ve tur 2 bekleniyor".
- **Bitti sayılır:** örneklem ve ölçüm araçları hazır; kalan iş insan turlarıdır.

## Kabul ölçütleri
**Kod ve veri**
1. [ ] Tedarik: `SHA256SUMS` geçer, kilit yazılı, `sources check` 0 hata 0 uyarı, ölçüm raporu var.
2. [ ] G-HIZ: iki meal için 6.236 âyetin her biri bir birime ya da `birlesik_ile` bağına sahip.
3. [ ] `--force` ile iki `ingest` aynı staged'i üretir; Python vektör testi ve `check.mjs` yeşil.
4. [ ] G-KAY, G-BUT, G-CAP, G-NOR, G-HIZ geçti (G-BUT sayfa başı ve sonu bölgesi sınırı dahil); G-MET K-49 gereği uygulanmadı. Orijinal mealde 19 baş ve 19 izleyen birleşik birim ile 17 `ortak_metin` uyarısı raporda.
5. [ ] Veritabanı: 2×6.236 birim `taslak`; inceleme sayısı doğru; ikinci `export pg` 0 değişiklik; benzetilen kararlardan sonra yine 0.
6. [ ] API ve editör testleri yeşil; OpenAPI ve üretilmiş istemci güncel.
7. [ ] `dev` `core` iki meali `approved = 0` ile taşır; `verify` 0; `public` kuru çalıştırmada mealler P-10 ile dışarıda.
8. [ ] `metin-denetcisi`: NFC yalnız ilk kayıtta; Tanzil metnine dokunulmadı; raporlarda, testlerde ve commit'lerde meal metni yok.
9. [ ] Atıf metinleri K-49 madde 14'e uygun.
10. [ ] Belgeler: arama ifadeleri temiz, bağlantı denetimi temiz, kit testleri yeşil.

**İ-11'e bağlı**

11. [ ] Tur 1: iki mealde bütün birimler `onayli`; `unit` hedefli açık inceleme 0 (SQL).
12. [ ] Tur 2: her meal için en az 600 âyet; üst sınır raporda; G-INC geçti.

## Doğrulama
```bash
sha256sum -c SHA256SUMS                                              # her data/gelen/<kaynak>/<tarih>/ klasöründe
uv run --directory pipeline mutalaa sources check
uv run --directory pipeline mutalaa ingest meal --source elmalili-meal --force      # iki kez; staged özetleri karşılaştırılır
uv run --directory pipeline mutalaa ingest meal --source elmalili-sade-meal
uv run --directory pipeline mutalaa ingest meal --source elmalili-meal-epub
uv run --directory pipeline mutalaa normalize --source elmalili-meal   # ve elmalili-sade-meal
uv run --directory pipeline mutalaa anchor --source elmalili-meal      # ve elmalili-sade-meal
uv run --directory pipeline mutalaa qa run --source elmalili-meal      # ve elmalili-sade-meal
uv run --directory pipeline mutalaa export pg --source elmalili-meal   # ve elmalili-sade-meal; ikinci koşu 0 değişiklik
uv run --directory pipeline mutalaa qa sample --source elmalili-meal --n 600 --seed 20261111 --dry-run
uv run --directory pipeline pytest
MUTALAA_DEGISMEZLIK_ZORUNLU=1 uv run --directory pipeline pytest -m veritabani
uv run --directory pipeline ruff check . && uv run --directory pipeline ruff format --check . && uv run --directory pipeline mypy
uv run --directory pipeline mutalaa export test-vectors --check
node shared/test-vectors/scripts/check.mjs
pnpm lint && pnpm typecheck && pnpm test && pnpm exec prettier --check .
pnpm --filter @mutalaa/editor gen:api && git diff --exit-code apps/editor/src/api
dotnet build server/Mutalaa.slnx -c Release && git diff --exit-code server/Mutalaa.Api/openapi
dotnet test --solution server/Mutalaa.slnx
dotnet format server/Mutalaa.slnx --verify-no-changes
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT source_id, metin_durumu, count(*) FROM icerik.unit WHERE kind = 'meal' GROUP BY 1,2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'unit' AND durum = 'acik';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev
node --test ".claude/hooks/test/*.test.mjs"
node --test "scripts/ci/*.test.mjs"
```
Komut adları ve bayraklar uygulamada `package.json` ve `cli.py` ile karşılaştırılır. Belge bağlantı denetimi `belge-esitle` becerisiyle yapılır.

## Dikkat
- Yapay zekâ meal yazmaz, çevirmez, düzeltmez ve sadeleştirmez; düzeltme insanındır (K-25; [İçerik hattı](../../04-icerik/02-icerik-hatti.md) §10). Meal metni hafızadan tamamlanmaz ve örnek diye uydurulmaz; testte yalnız sentetik metin kullanılır.
- Sadeleştirilmiş metin yalnız `meal:elmalili-sade` adlı ayrı baskı olarak girer. Orijinal meal ve tefsir için sadeleştirilmiş metin yasağı sürer; iki baskı birbirinin yerine konmaz. T ailesi Elmalılı adıyla alınmaz (K-49 madde 1).
- Çapa adları başka bir metne verilmez (K-26). Aile ayrımı 16:43 âyetindeki çeviri farkına dayanır.
- Hazır metnin baskı esası belgesizdir: iki meal `taslak` girer ve `dev` ile `internal`'da "doğrulanmamış" rozetiyle görünür. Bir meal kaynağı bütün âyetleri onaylanıp G-INC geçmeden `public`'e çıkmaz; zorlayan kod A34'te yazılır (K-49 madde 5).
- Çıkarılmış metin kaynak dosyanın birebir dilimi değildir (K-38 madde 3). İlk kayıt adımları (NFC dahil) `ingest` ayrıştırmasında bir kez uygulanır; konum `provenance` içindedir ve `@` ofseti değildir. Vektörü yalnız Python tüketir (K-49 madde 13).
- Hat meal biriminin metnine hiç yazmaz (K-49 madde 10). Editör düzeltmesi çapayı değiştirmez; `content_hash` ve `rev` değişir. Onaylı birimde sonradan yapılan düzeltme yeniden inceleme ve ikinci onaydan geçer ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.3).
- Editörler çalışırken meal `export pg` yapılmaz: hat ve API farklı kilit anahtarı kullanır ve açık kayıt tekilliği yoktur. Kısmi tekil dizin önerisi yeni bir BÇ olarak açılır.
- Çapa kümesi donmuştur (K-47): ilk `dev` yayını (2026.11.2; `core` iki meali taşır, `verify` temiz) yapıldı, bu yüzden meal çapa kümesi ve sınır kararları (K-49 madde 8) artık değişirse yayın reddedilir. A34'e kadar kısmi meal `public`'e girebilir (yalnız onaylı birimler; P-10); G-INC kuralı A34'te yazılır.
- Toplu indirmede istek hızı sınırlanır; `User-Agent` kişisel bilgi taşımaz. Windows: dosya adları ASCII; indirilen dosyalar `python -I` ile okunur; BOM ve CRLF denetlenir.
- Günlüklere, raporlara ve commit'lere meal metni yazılmaz. Kuyruk ekranlarının tarayıcıda görülmesi kullanıcıya bırakılır.

## İnsan adımları
- İ-11 · Düzeltme turları: iki mealde tur 1 (her âyetin iki ayrı kişiyle onayı) ve tur 2 (en az 600 âyetlik ikinci okuma). Orijinal mealin turları Faz 1'i bağlar; sadeleştirilmiş mealin turları fazı bekletmez. İnsan turu yalnız A16.7'nin kapanışını bekletir; araç, kuyruk ve rapor işleri sürer, öteki aşamalar beklemez. Bekleyen adım ilerleme dosyasında ve durum bloğunda görünür. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/` altında `meal_kaynaklari.py`, `elmalili_vikikaynak.py`, sadeleştirilmiş meal ve tanık bağdaştırıcıları, `elmalili_meal.lock.json`; `adimlar/meal.py`, `qa/checks/meal.py`, `export/pg_meal.py`, `qa sample`; testler
- `shared/test-vectors/extract/meal.jsonl` (sentetik)
- `pipeline/sources/` altında `elmalili-meal.toml` (güncel) ve yeni `elmalili-sade-meal.toml`, `elmalili-meal-epub.toml`; `data/gelen/` altında iki meal ve EPUB tanığı klasörü, `data/reports/` altında ölçüm, kapsam, tanık, sadeleştirme taraması ve G-INC raporları (git dışı)
- PostgreSQL'de `meal:elmalili` ve `meal:elmalili-sade` birimleri ve `review` kayıtları
- API süzgeçleri ve 422 kuralı, editörde iki meal sekmesi; `core` kataloğunda iki meal ve `dev` kanalında yeni `core`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A16-elmalili-meali.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A15](./A15-editor-paneli.md) · Sonraki: [A17](./A17-kelime-katmani.md)
- [Karar defteri](../../00-ozet/02-karar-defteri.md) · [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) · [Kaynaklar](../../04-icerik/01-kaynaklar.md) · [Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md) (S-15) · [A09 (ertelendi)](./A09-elmalili-ocr-pilotu.md)
