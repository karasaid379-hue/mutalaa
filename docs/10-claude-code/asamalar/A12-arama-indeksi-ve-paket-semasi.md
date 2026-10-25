# A12 · Arama indeksi ve paket şeması

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A10](./A10-tanzil-alimi.md) · **İnsan adımı:** yok
> **Ajanlar:** `web-gelistirici` (TS paketleri) · `sunucu-gelistirici` · `hat-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `test-vektoru` · `paket-yayini` · `metin-butunlugu` · **Tahmini oturum:** 3
> **Başlat:** `/asama A12`

## Amaç
Cihazdaki SQLite paketlerinin tek şeması (`packages/content-schema/sql/`), FTS5 arama tabloları, manifest şeması ve `packages/search` içindeki FTS5 sorgu kurucusu yazılır. Sorgu kurucusu ortak vektörlerle (`fts-query/query.jsonl`) ve Node'da çalışan bir SQLite deneme düzeneğinde gerçek FTS5 tablolarına karşı sınanır. A13 bu DDL ile paket yazar; A23 ve A28 aynı şemayla okur.

## Okunacak belgeler
- [Arama](../../03-veri/05-arama-fts5.md): §1.4 Kur'an birimleri, §2 FTS5 tabloları, §3 sorgu ayrıştırma, §4 sıralama, §5 ATTACH, §6 performans (ölçüm kümesi A28'de)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3 paket içi şema, §4 bağlantıların dağılımı, §5 manifest, §6 sürümleme
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`content-schema`, `search`, `shared/test-vectors`), §1.2 vektör biçimi, §2 bağımlılık kuralları
- [Backend API](../../02-mimari/05-backend-api.md): §10.4 paket yazımı, §10.5 özet, imza ve depo düzeni
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 ortak vektörler, §6 enum tutarlılığı
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.3 Yayınlayıcı kitaplıkları

## Kapsam
**Yapılır**
- Bütün paket türlerinin DDL'i: ortak tablolar, metin paketleri, arama tabloları (içerikli ve içeriksiz), `core` ekleri, `kelime-kok`, `risale-dizin`, `risale-{kitap}`, `mushaf-a-cuz-*`, `mushaf-b`, `ses-*`; paket yazımından sonra çalışan FTS komutları.
- `packages/content-schema/manifest.schema.json` ve şema testleri.
- `packages/search` FTS5 sorgu kurucusu ve `shared/test-vectors/fts-query/query.jsonl`.
- Node tarafında SQLite FTS5 deneme düzeneği; C# tarafında DDL duman testi.
- A10.3'ten devreden karar: Simple Clean pakette tutulacak mı.

**Yapılmaz**
- Paket yazıcısı, imza ve yükleme (A13). Drizzle şemaları (`user.db`, `device.db`) ve cihazda ATTACH yönetimi (A23).
- Arama ekranı, kıyas ekranı ve ölçüm sorgu kümesi (A28). Normalleştirici (A05) ve gövdeleyici (A05; orada çözülmediyse A12.1'de). Sonuç parçası üretimi (`reader-core`, A28).

## Adımlar
### A12.1 · Doğrulamalar
- `arastirmaci` resmî kaynaktan doğrular:
  - Node'da FTS5 ve `trigram` belirteçleyicisini destekleyen SQLite kitaplığı. Adaylar (öneri): Node'un yerleşik `node:sqlite` modülü ya da `better-sqlite3`. Ölçütler: FTS5 ve `trigram` derlemede açık mı, Windows'ta yerel derleme ister mi, lisans, Node 24 uyumu.
  - expo-sqlite derlemesindeki SQLite sürümü ve `trigram` desteği; paket yalnız cihazdaki SQLite'ın desteklediği özellikleri kullanır ([Backend API](../../02-mimari/05-backend-api.md) §10.4).
  - `Microsoft.Data.Sqlite` (e_sqlite3) derlemesinde FTS5 ve `trigram`.
  - `JsonSchema.Net` sürüm durumu ve desteklediği JSON Schema taslağı.
- `tr_stem_lex` kararı (AR-2): A05'in raporuna göre TypeScript'te Türkçe Snowball uygulaması yoksa tablo kalır ve Yayınlayıcı doldurur ([Arama](../../03-veri/05-arama-fts5.md) §2). A05'te Python gövdeleyicisi seçildi ve uygulandı (`snowballstemmer` 3.1.1, [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 6; AR-2 Python yarısı çözüldü); bu aşamada yalnız TypeScript yarısı (cihazda gövdeleyici) ve Snowball'un agresif gövdelerinin (`kuran` → `kura`, `mümin` → `mum`, `iman` → `ima`) arama ölçümüyle gözden geçirilmesi kalır.
- Seçimler `/karar` ile yazılır. expo-sqlite `trigram` desteklemiyorsa durum kullanıcıya gösterilir; Arapça alt dize araması için seçenek karar olmadan uygulanmaz.
- **Bitti sayılır:** dört konu kaynak bağlantısıyla raporlu; kitaplık, JSON Schema taslağı ve `tr_stem_lex` kararları karar defterinde.

### A12.2 · Paket DDL'i
- `packages/content-schema/sql/` altında paket türü başına dosyalar (adlar öneri): `00-ortak.sql` (`PRAGMA user_version = 1`, `pack_meta`, `pack_source`, `attribution`), `10-metin.sql` (`unit`, `xref_idx`, `tr_root_index`), `20-arama.sql` (`unit_search`, `unit_fts`, `unit_tri`, `tr_stem_lex`), `21-arama-iceriksiz.sql`, `29-arama-sonrasi.sql` (`rebuild`, `rank`, `optimize`), `30-core.sql` (`quran_word`, `page_map`, `sure`), `40-kelime-kok.sql`, `50-risale-dizin.sql` (`unit_ref`), `60-mushaf-a.sql`, `61-mushaf-b.sql`, `70-ses.sql`. Paket türü → dosya listesi tek bir JSON'da durur (öneri: `sql/paketler.json`).
- Tablo ve sütun adları [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §3 ve [Arama](../../03-veri/05-arama-fts5.md) §2 ile birebir aynıdır; yeni ad uydurulmaz. `risale-{kitap}` arama tabloları ve `tr_root_index` taşımaz; bunlar `risale-dizin` içindedir.
- `kind`, `status`, `license_status` gibi değerler A06'nın `packages/content-schema/enums.json` dosyasıyla karşılaştırılır (Test stratejisi §6).
- A11 cüz, hizb ve secde için tablo kararı verdiyse tablo `30-core.sql` dosyasına eklenir.
- Simple Clean kararı (A10.3 devri): pakette tutulup tutulmayacağı planda önerilir ve `/karar` ile yazılır (öneri: tutulmaz; Kur'an `ar_norm` Simple Clean'den gelir). ÇŞ-2'nin cevabı olumsuz gelirse Kur'an için içeriksiz FTS biçimi kullanılır; `21-arama-iceriksiz.sql` bu yüzden iki paket ailesine de uygulanabilir yazılır ([Arama](../../03-veri/05-arama-fts5.md) §1.4).
- **Bitti sayılır:** her paket türünün dosya listesi Node düzeneğinde ve C# duman testinde hatasız kuruluyor; `PRAGMA user_version` 1 dönüyor.

### A12.3 · Manifest şeması
- `packages/content-schema/manifest.schema.json`, [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §5'i izler: üst düzeyde `manifest_version`, `flavor` (`dev`, `internal`, `public`), `release`, `generated_at`, `packs`, zorunlu `signature {alg, kid, value}`; paket başına zorunlu `pack_id`, `version`, `sha256`, `size_bytes`, `license_status`, `kurul_gerekli`, `kurul_onay`, `min_app_version`, `depends_on`, `url`; isteğe bağlı `schema_version`, `title`, `bundled`.
- Kurallar: `kurul_onay` ya `null` ya `{onay_no, onay_tarihi, onayli_surum, icerik_ozeti}` nesnesi; `license_status` dört değer; `version` CalVer `YYYY.M.N`; `sha256` 64 küçük onaltılık karakter.
- Testler `JsonSchema.Net` ile Publisher test projesindedir: §5'teki örnek manifest geçer; imzasız manifest, metin olarak `kurul_onay`, bilinmeyen `license_status` ve büyük harfli `sha256` reddedilir. Uygulama tarafındaki doğrulayıcı (Teknoloji yığını §2.1'de `zod` önerisi) A23'te bu şemayla uyumlanır.
- **Bitti sayılır:** beş şema testi yeşil.

### A12.4 · FTS5 sorgu kurucusu ve vektörler
- `packages/search/src/` altında sorgu kurucusu (dosya adı öneri: `fts-query.ts`), [Arama](../../03-veri/05-arama-fts5.md) §3'ün gramerini ve dokuz kuralını uygular: adres algılama (sure adı çözücüsü dışarıdan verilir), yazı sistemi ayrımı, Türkçe terimde `tr_wide` ve `tr_stem` `OR`, düzeltme işaretli terimde dar süzgeç, en az 2 karakterlik önek (tek karakterli terim yok sayılır, önekte gövde yok), ifade (gövde yok), Arapça terim ve en az 3 karakterde `unit_tri` yedeği, `kök:` ve `kaynak:` süzgeçleri, her sözcüğün çift tırnakla kaçışı.
- Normalleştirme yalnız A05'in `packages/search` işlevleriyle yapılır. `tr_stem_lex` araması ve sure adı çözümü dışarıdan verilen işlevlerdir; paket SQLite'a bağlanmaz ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §2 kural 2–3).
- `shared/test-vectors/fts-query/query.jsonl`: §3 tablosundaki yedi örnek (`sabır`, `ışığın nuru`, `kur*`, `"rahmet-i ilâhiye"`, `âlem`, `الصابرين`, `kök:صبر`) ve kenar durumları (FTS5 sözdizimi karakteri içeren girdi, tek karakter, 2 karakterlik önek, "Bakara 255", "2:255"). Gövdeler gerçek gövdeleyici çıktısı değildir; tablodaki `{G1}`, `{G2}` gibi satır içinde verilen sabit eşlemeyle yazılır. Arapça örnek sorgular belgeden programla, bayt bayt alınır; elle yazılmaz (`test-vektoru`).
- Biçim JSONL, UTF-8, BOM yok, LF, her satırda benzersiz `id` (`test-vektoru`). Bu dosyayı yalnız TypeScript koşar; Python ve C# vektör koşucuları `fts-query/` klasörünü açıkça atlar (`hat-gelistirici`, `sunucu-gelistirici`).
- **Bitti sayılır:** `pnpm --filter @mutalaa/search test` vektörlerle yeşil; `shared/test-vectors` `build` görevi biçimi doğruluyor; pytest ve xUnit vektör koşucuları yeşil.

### A12.5 · Node SQLite deneme düzeneği
- Düzenek `packages/content-schema/test/` altındadır (öneri); `search` yaprak paket kaldığı için `content-schema` `@mutalaa/search` paketine geliştirme bağımlılığıyla bağlanır. SQLite kitaplığı A12.1'deki karardır. Geçici veritabanı dosyaları `.tmp/` altına yazılır.
- Veritabanı DDL dosyalarından kurulur. Sentetik Türkçe satırlar ("Deneme paragrafı 1 … ışık …") A05 normalleştiricisiyle `unit_search` tablosuna yazılır. Arapça satırlar `\u` kaçışıyla kurulan sentetik harf dizileridir (ör. bir dizi ve başına bitişik ek harfi U+0648 eklenmiş biçimi; bitişik ek ve trigram denemesi için); Kur'an kelimesi yazılmaz (`test-vektoru`).
- Sınananlar: her vektörün MATCH ifadesi FTS5'te hatasız çalışır; düzeneğin sentetik satırları için yazılmış vektörler beklenen çapaları döndürür (§3 tablosundaki Arapça örnek sorgular düzenekte yalnız hatasız çalışır, sonuç beklenmez); `ORDER BY rank` bm25 ağırlıklarıyla sıralar; 2–4 karakterlik önek; `trigram` alt dize araması; içeriksiz tablo ile `unit_ref` birleşimi; ayrı dosyadan `ATTACH` edilen pakette şema nitelemeli `MATCH` ve §5'teki `UNION ALL` deyimi (AR-6'nın Node tarafı; expo-sqlite tarafı A28).
- **Bitti sayılır:** `pnpm --filter @mutalaa/content-schema test` yeşil.

### A12.6 · C# DDL duman testi ve hat uyumu
- `sunucu-gelistirici`: Publisher test projesinde her paket türünün DDL'i `Microsoft.Data.Sqlite` ile boş dosyaya uygulanır; `PRAGMA compile_options` `ENABLE_FTS5` içerir; `trigram` tablosu kurulur; `PRAGMA user_version` 1 döner.
- `hat-gelistirici`: hattın ürettiği `tr_wide`, `tr_stem`, `ar_norm` sütunlarının `unit_search` sütunlarıyla aynı adda olduğu doğrulanır. "`tr_wide` ile `tr_stem` aynı sayıda sözcük taşır" değişmez kuralı ([Arama](../../03-veri/05-arama-fts5.md) §1.2 madde 7) A05'te test edildi; bu aşamada hattın QA adımına da bağlanır, çünkü Yayınlayıcı `tr_stem_lex` tablosunu bu hizadan kurar.
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` ve `uv run pytest` yeşil.

## Kabul ölçütleri
- [ ] `packages/content-schema/sql/` İçerik paketleri §3 ve Arama §2'deki bütün tabloları taşıyor; `inceleyici` tablo ve sütun adlarının dokümanla birebir olduğunu karşılaştırma tablosuyla raporluyor.
- [ ] Her paket türünün DDL'i Node düzeneğinde ve C# duman testinde hatasız kuruluyor; `PRAGMA user_version` 1.
- [ ] `manifest.schema.json` §5 örneğini kabul ediyor, dört olumsuz örneği reddediyor (C# testi).
- [ ] `fts-query/query.jsonl` §3'teki yedi örneği ve en az beş kenar durumunu taşıyor; vektör testleri yeşil.
- [ ] Node düzeneğinde bm25 sırası, önek, `trigram`, içeriksiz tablo ve `ATTACH` ile şema nitelemeli `MATCH` testleri yeşil.
- [ ] Node SQLite kitaplığı, JSON Schema taslağı, `tr_stem_lex` ve Simple Clean kararları karar defterinde; expo-sqlite `trigram` sonucu ilerleme notunda.
- [ ] `pnpm lint`, `pnpm typecheck`, `pnpm test`, `dotnet test --solution server/Mutalaa.slnx` ve `uv run pytest` yeşil.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build
pnpm --filter @mutalaa/search test
pnpm --filter @mutalaa/content-schema test
pnpm lint && pnpm typecheck && pnpm test
dotnet test --solution server/Mutalaa.slnx
(cd pipeline && uv run pytest)
```

## Dikkat
- `snippet()` ve `highlight()` kullanılmaz; katlanmış metin döndürürler. Sonuç parçası kanonik metinden `reader-core` içinde üretilir.
- `tokenize='unicode61 remove_diacritics 0'`; normalleştirme belirteçleyiciye bırakılmaz. `detail` varsayılandır; boyut gerekçesiyle değiştirmek Açık sorudur.
- Paket DDL'i diller arası sözleşmedir; değişiklik A13, A23 ve A28'i etkiler. Şema değişince `schema_version` ve `normalizer_version` kuralları uygulanır ([İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §6).
- Testlerde Arapça metin uydurulmaz: `\u` kaçışıyla kurulan sentetik harf dizileri (A12.5), belgeden programla alınan örnek sorgular (A12.4) ya da kaynak dosyadan betikle kesilmiş parça kullanılır.
- Kültürden bağımsızlık: sorgu kurucusunda `toLocaleLowerCase` argümansız kullanılmaz; testler CI'da `LANG=tr_TR.UTF-8` ile de koşar.
- `.sql` ve `.jsonl` dosyaları LF ve BOM'suzdur; `metin-kurali` hook'u denetler.

## İnsan adımları
- Yok.

## Çıktılar
- `packages/content-schema/sql/*.sql` ve paket türü listesi; `packages/content-schema/manifest.schema.json`; `packages/content-schema/test/` (şema testleri ve SQLite düzeneği)
- `packages/search/src/` sorgu kurucusu ve testleri; `shared/test-vectors/fts-query/query.jsonl`
- Publisher test projesinde DDL duman testi ve manifest şeması testi; Python ve C# vektör koşucularında `fts-query/` atlaması
- Karar defterinde Node SQLite kitaplığı, JSON Schema taslağı, `tr_stem_lex` ve Simple Clean kayıtları; A05'ten devir olduysa hattın gövdeleyicisi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A12-arama-indeksi-ve-paket-semasi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) · Sonraki: [A13](./A13-yayinlayici-ve-yayin-kapisi.md)
