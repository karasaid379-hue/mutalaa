# A13 · Yayınlayıcı ve yayın kapısı (ilk `dev` `core` paketi)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A07](./A07-editoryal-veritabani.md) · [A12](./A12-arama-indeksi-ve-paket-semasi.md) · **İnsan adımı:** yok
> **Ajanlar:** `sunucu-gelistirici` · `lisans-denetcisi` · `test-yazari` · `hat-gelistirici` (fikstür kaynakları) · `arastirmaci` · `inceleyici` · **Beceriler:** `lisans-kapisi` · `paket-yayini` · `ef-goc` · `windows-sorun` · **Tahmini oturum:** 4–5
> **Başlat:** `/asama A13`

## Amaç
`Mutalaa.Publisher` konsolu, lisans kapısının P-01…P-14 kuralları, SQLite paket yazıcısı, imzalı manifest ve yerel SeaweedFS'e yükleme kurulur. Aşama, Tanzil metni ve `test-` önekli sentetik fikstürlerle ilk `dev` yayınını üretir; mobil aşamalar (A23) bu yayınla başlar. Meal, kelime ve bağlantılar hazır oldukça aynı komutla paketler yeniden yayımlanır.

## Okunacak belgeler
- [Backend API](../../02-mimari/05-backend-api.md): §2 çözüm yapısı, §10 Yayınlayıcı (tamamı), §11 test
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §2–§6
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3–§7
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source` (atıf ve Kurul alanları), §10 `release` ve içerik özeti
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §3 kullanıcı sırları, §4 `publisher` servisi ve `s3.json`, §6 adım 6, §8 örnek veri, §10.3–§10.4
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 testler 6 ve 8, §7, §9 fikstürler
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.3 Yayınlayıcı kitaplıkları

## Kapsam
**Yapılır**
- `Mutalaa.Domain/Licensing` kapı kuralları; `Mutalaa.Infrastructure/Packs` (`SqlitePackWriter`, `ManifestSigner`) ve `Storage` (S3).
- Komutlar: `keys generate`, `build`, `publish`, `upload`, `verify`, `promote`, `rollback`, `watch`.
- Paket tanımları: `core`, `kelime-kok`, genel metin paketi (`tefsir-*`, `hadis-*`); fikstür paketleri `test-kucuk` ve `tefsir-test-ornek`.
- İlk `dev` yayını; `internal` ve `public` için kuru çalıştırma kapı raporları.

**Yapılmaz**
- `apps/mobile/scripts/fetch-core.mjs`, `keys.ts` ve uygulamadaki imza doğrulaması (A23).
- `risale-dizin` ve `risale-{kitap}` paket tanımları (A20). `mushaf-a-cuz-*` (A26). `ses-*` paketleri ve `ses-test` fikstürü (A27).
- API'nin yayın uçları (A14); `watch` onların bıraktığı kayıtları işler. Canlı depo ve `internal` erişim yöntemi (İ-18, A34).

## Adımlar
### A13.1 · Doğrulamalar ve kararlar
- `arastirmaci` resmî kaynaktan doğrular: Ed25519 için .NET kitaplığı (NSec ya da BouncyCastle; lisans, bakım, .NET 10 uyumu); JSON kanonikleştirme yöntemi (öneri RFC 8785 JCS) ve .NET uygulaması; aynı baytları üretecek JS yolu A23 için not edilir (`@noble/ed25519` öneri); `System.CommandLine` kararlı sürüm durumu; `AWSSDK.S3` bütünlük sağlaması ayarının SeaweedFS ile davranışı (`RequestChecksumCalculation = WHEN_REQUIRED`), `x-amz-meta-sha256` meta verisi, anonim okuma ve Range isteği ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §11).
- Kararlar `/karar` ile yazılır: imza algoritması ve kitaplık, kanonikleştirme, anahtar saklama (İçerik paketleri IP-7).
- İmzanın yeri: imza ayrı dosyada değil, manifest içindeki `signature` alanındadır ve `dev` dahil her derlemede zorunludur (K-06 uygulama notu; İçerik paketleri §5, Backend API §10.5, [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md) §4.2).
- **Bitti sayılır:** kararlar karar defterinde, doğrulama raporu kaynak bağlantılı.

### A13.2 · Kapı kuralları (Domain)
- `Mutalaa.Domain/Licensing`: `LicenseStatus` sırası (`serbest < bekliyor < ic_kullanim < kapali`), `BuildFlavor`, `LicenseGate.Check` ([Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md) §4) ve P-01…P-14'ü saf işlev olarak değerlendiren kapı (ad öneri: `GateEvaluator`). Her karar kural koduyla kapı raporu satırı üretir: paket ya da kaynak, "girdi" ya da "girmedi", gerekçe.
- xUnit: durum × derleme matrisinin her hücresi (`[Theory]`; §5 madde 1); onaysız, onaylı ve onaydan sonra değişmiş Kurul kaynağı; kaynak kaydı olmayan paket; `kurul_gerekli` türetimi; her P kuralı için en az bir olumlu ve bir olumsuz test. Testler `tr-TR` kültüründe de koşar.
- **Bitti sayılır:** kapı testleri yeşil; kural başına test listesi raporda.

### A13.3 · Paket yazıcısı ve paket tanımları
- `Mutalaa.Infrastructure/Packs/SqlitePackWriter` [Backend API](../../02-mimari/05-backend-api.md) §10.4'ü adım adım izler: `.db.tmp`, PRAGMA'lar, `Publisher:SchemaDir` (`packages/content-schema/sql/`) DDL'i, çapa sırasıyla tek işlemde hazırlanmış komutlar, FTS5 doldurma ve `29-arama-sonrasi` komutları, `pack_meta` anahtarları (İçerik paketleri §3.1), `pack_source`, `attribution` (Editoryal veritabanı §3 eşlemesi), `ANALYZE`, `VACUUM`, `journal_mode=DELETE`, öz denetim, `Pooling=False`, taşıma, `SHA256.HashDataAsync` ve `Convert.ToHexStringLower`. Açılışta `ENABLE_FTS5` aranır.
- `content_digest` ve Kurul içerik özeti (Yayın kapısı §2.2) aynı sıralama kuralıyla hesaplanır; içerik değişmediyse yeni paket sürümü üretilmez. `content_digest` girdileri Backend API §10.5'te (şema sürümü, `normalizer_version`, kaynak özetleri, bağlantı alanları, lisans) ile İçerik paketleri §6'da (`anchor` + `content_hash` satırları) farklı tanımlıdır; fark planda gösterilir ve `/karar` ile tek tanıma bağlanır.
- Paket tanımları: `core` (Tanzil birimleri; A11 çıktıları: `quran_word` Tanzil satırları, `page_map` ve işaret tablosu; sure adları onaylıysa `shared/data/sure-adlari.json`'dan `sure` tablosu; meal hazır oldukça), `kelime-kok` ve genel metin paketi. A11 çıktısı henüz yoksa ilgili tablolar boş kalır; A11'den sonra `publish --flavor dev` yeniden çalışır. Süzme kaynak düzeyindedir; aynı paket derlemeye göre farklı içerik taşıyabilir (İçerik paketleri §7). `xref_idx` P-07 ile süzülür; `approved` ve `folded` önceden hesaplanır.
- `label` birim başlıklarından ve sure adlarından üretilir. Sure adları henüz onaylı değilse (İ-23) sayısal biçim yazılır ve `sure` tablosu boş kalır (öneri); ad uydurulmaz. Onaydan sonra yeniden yayınla düzelir.
- Tanzil bildiriminin tam metni `core` paketinde `attribution.notice_text` alanına yazılır (Test stratejisi §5 test 6).
- P-11 için Yayınlayıcı Tanzil birimlerinin `content_hash` değerini `data/raw/tanzil-*` altındaki ham dosyadan yeniden hesaplar (yapılandırma anahtarı öneri: `Publisher:RawDir`). `app` profilindeki konteyner yalnız `data/packs` klasörünü bağlar; ham dosya için birim eklenir ya da Yayınlayıcı ana makinede çalışır (öneri).
- **Bitti sayılır:** yazıcı testleri yeşil; aynı veritabanından iki `build` aynı `content_digest` değerlerini veriyor.

### A13.4 · Manifest, imza ve anahtarlar
- Manifest İçerik paketleri §5 alanlarıyla yazılır ve `manifest.schema.json`'a karşı doğrulanır. `url` = `{PublicBaseUrl}/packs/{flavor}/{pack_id}/{version}/{pack_id}-{version}.db`.
- İmza `signature {alg, kid, value}`; girdi, `signature` alanı çıkarılmış manifestin kanonik JSON biçimidir (A13.1 kararı). Her derleme türünde zorunludur.
- Yayınlayıcı yapılandırmayı .NET genel ana bilgisayarıyla okur (`Host.CreateApplicationBuilder`, öneri); kullanıcı sırları yalnız `Development` ortamında yüklenir. Kit ayarları Claude Code komutlarına `DOTNET_ENVIRONMENT=Development` verir; elle açılan terminalde değer komutun başına yazılır. Yayınlayıcının csproj dosyasında `UserSecretsId` yoksa `dotnet user-secrets init --project server/Mutalaa.Publisher` çalışır (onay ister; yalnız csproj'a kimlik yazar).
- `keys generate --flavor dev`: özel anahtar ve `kid` kullanıcı sırlarına (`Signing:dev:PrivateKey`, `Signing:dev:Kid`) yazılır, açık anahtar ekrana basılır (öneri). `dotnet user-secrets` kullanıcı onayı ister. Konteynerdeki Yayınlayıcı için `.env` içindeki `PUBLISHER_DEV_SIGNING_KEY` değerini kullanıcı yazar; Claude Code `.env` okumaz.
- A23'ün çapraz testi için açık anahtar ve imzalı örnek manifest `packages/content-schema/test/fixtures/` altına yazılır; yalnız açık malzeme (öneri).
- `verify --flavor <f> [--manifest <yol>] [--embedded-core <yol>]`: imza, şema, adres, boyut, sha256 ve kapı kuralları. İmzasız ya da bozuk imzalı manifest 3 ile reddedilir.
- **Bitti sayılır:** imza gidiş-dönüş, kurcalanmış manifest ve imzasız manifest testleri yeşil.

### A13.5 · Depo, komutlar ve yayın durumları
- `Storage`: `AWSSDK.S3` `ServiceURL` ve `ForcePathStyle = true`; anahtar düzeni ve `Cache-Control` değerleri §10.5 tablosundaki gibi; tür `application/vnd.sqlite3`; `x-amz-meta-sha256`. Sıra: paketler → HEAD doğrulaması → manifest geçmişi → `manifest.json`. Var olan anahtara farklı sha256 yazılmaz (çıkış 4); aynı sha256 atlanır.
- Komutlar §10.1'deki gibidir; `build` çıktısı `data/packs/{flavor}/{surum}/` altındadır. `watch` `pg_try_advisory_lock` ve `FOR UPDATE SKIP LOCKED` kullanır. Çıkış kodları: `0` başarı, `2` kapı reddi, `3` doğrulama, `4` depo, `1` diğer.
- BÇ-04 (terfi ve geri alma talebi) kabul edilirse `release` tablosuna eklenen alanlar yeni bir EF göçüdür: `sunucu-gelistirici` `ef-goc` becerisiyle ekler, `dotnet ef migrations has-pending-model-changes` temiz kalır, A07'nin şema dökümü anlık görüntüsü bilinçli olarak güncellenir ve fark commit'te gözden geçirilir.
- `release` durumları: `hazirlaniyor → dogrulandi → yayinlandi`; başarısız deneme `basarisiz` (Editoryal veritabanı §10, Backend API §10.6); geri almada `geri_cekildi`. Okuma tek `REPEATABLE READ` salt okunur anlık görüntüdedir. Sürüm CalVer `YYYY.M.N`; komutta verilmezse ayın sıradaki numarası (öneri).
- Bütünleşik test (Testcontainers, `postgres:18`): her durumdan birer kaynak ve bir `test-` kaynağı taşıyan fikstür veritabanından üç derleme üretilir; P-01…P-14, FTS sorgusu ve imza denetlenir (Backend API §11).
- **Bitti sayılır:** `dotnet test server/Mutalaa.slnx` yeşil.

### A13.6 · Fikstürler ve ilk `dev` yayını
- `hat-gelistirici`: `pipeline/sources/test-kucuk.toml` (`serbest`) ve `test-tefsir-ornek.toml` (`ic_kullanim`), ikisi de `embed_ok = false`; lisans defterine kayıt (`/belge-esitle`). `sources check` `kapali` dışındaki her kaynakta lisans kopyası ister; iki sentetik kaynağın lisans kopyası projenin kendi beyanıdır (`pipeline/sources/licenses/test-kucuk-{YYYY-AA-GG}.txt` ve `test-tefsir-ornek-{YYYY-AA-GG}.txt`: "Sentetik test verisi; Mütâlaa projesince üretildi; dinî ya da telifli metin içermez."), `lisans_sha256` bu dosyanın özetidir ve `atif_metni` "Sentetik test verisi (Mütâlaa)" olur (öneri). Belirlenimci üreteç (komut öneri: `uv run mutalaa ingest fikstur --source test-kucuk`) "Deneme paragrafı 1 …" biçiminde açıkça sentetik Türkçe metin üretir; `test-kucuk` Maestro arama akışı için "Işık" sözcüğünü içerir (Test stratejisi §9). Metin kendi ürettiğimizdir; ilk kayıtta NFC.
- Çapalar ve paket kimlikleri (öneri, `/karar` ile): `k:test-kucuk:bolum-1:p{n}` → paket `test-kucuk`; `tf:test-ornek:{s}-{ilk}-{son}:p{n}` → paket `tefsir-test-ornek`. Kur'an, meal, tefsir, hadis ya da Risale metnine benzeyen içerik yazılmaz.
- İlk yayın: `keys generate --flavor dev`, `publish --flavor dev`, manifest kontrolü, `verify --flavor dev`. Açık anahtar ve yayın sürümü ilerleme dosyasına not edilir (A23 için).
- Kuru çalıştırma: `internal` ve `public` için `--dry-run`. Beklenen: `public` raporu `core` için P-04 (Kurul onayı yok) ile durur; `tefsir-test-ornek` `internal` ve `public`'te P-03 ile, `test-kucuk` `public`'te P-12 ile girmez; `internal` raporunda `core` ve `test-kucuk` girer.
- **Bitti sayılır:** manifest imzalı ve üç paketi listeliyor; `verify --flavor dev` 0; kuru çalıştırma raporları beklenen kodları gösteriyor.

## Kabul ölçütleri
- [ ] P-01…P-14'ün her biri en az bir olumlu ve bir olumsuz testle kapsanıyor; durum × derleme matrisi `tr-TR` kültüründe de yeşil.
- [ ] Bütünleşik testte `internal` ve `public` çıktısında `serbest` dışı `pack_source` satırı 0, `public`'te `test-` kaynak 0, `dev`'de `kapali` kaynak 0.
- [ ] Aynı veritabanından iki `build` aynı `content_digest` değerlerini üretiyor.
- [ ] İmzasız ve bozuk imzalı manifest `verify` tarafından 3 çıkış koduyla reddediliyor.
- [ ] `publish --flavor dev` 0 ile bitiyor; `dev/manifest.json` `core`, `test-kucuk` ve `tefsir-test-ornek` paketlerini ve dolu `signature` alanını taşıyor; `verify --flavor dev` 0.
- [ ] `core` paketinin öz denetim raporunda `integrity_check` `ok`, `q:2:255` sorgusu bir satır, FTS sorgusu sonuç; `attribution.notice_text` Tanzil bildiriminin tam metni (gözle kontrol).
- [ ] Kuru çalıştırma raporları A13.6'daki P kodlarını gösteriyor.
- [ ] İmza, kanonikleştirme ve fikstür çapası kararları karar defterinde; `test-` kaynaklar lisans defterinde.

## Doğrulama
```bash
dotnet build server/Mutalaa.slnx
dotnet test server/Mutalaa.slnx
docker compose up -d && docker compose ps
(cd pipeline && uv run mutalaa sources check)
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run; echo "çıkış (2 beklenir): $?"
```
`public` kuru çalıştırmasının `2` ile bitmesi beklenen sonuçtur: `core` Kurul onayı taşımadığı için P-04 public derlemeyi durdurur (A13.6). Komutlar `DOTNET_ENVIRONMENT=Development` ile koşar (kit ayarı; A13.4).

## Dikkat
- Gizli değerler: özel anahtar dosyaya, koda, günlüğe ya da `appsettings*.json` içine yazılmaz; yalnız kullanıcı sırlarında ya da git dışı `.env`'de durur.
- Windows: SQLite bağlantısı kapanmadan dosya taşınmaz (`Pooling=False`). Proje yolu boşluk ve Türkçe karakter içerir; `Publisher:SchemaDir` göreli verilir.
- Kurul onayı paket dosyasının sha256'sına değil, içerik özetine bağlanır (Yayın kapısı §2.2).
- Kapı iki kez uygulanır (Yayınlayıcı ve uygulama). Yayınlayıcıdaki kural hiçbir derlemede gevşetilmez; `public` derleme imza kuralını da gevşetmez.
- Manifest biçiminin sahibi İçerik paketleri §5'tir: CalVer sürüm, `.db` anahtarı, `kurul_onay` nesne ya da `null` ([Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md) §4.1 örneği de bu biçimdedir).
- `Storage:PublicBaseUrl` LAN IP'sini taşır; IP değişince `publish` yeniden çalışır ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §10.3).
- Fikstür metni hiçbir dini metne benzetilmez; `test-` kaynaklar `public`'e hiçbir durumda girmez (P-12).

## İnsan adımları
- Yok. `dotnet user-secrets` komutu kullanıcı onayı ister; konteyner için `.env` değerini kullanıcı kendisi yazar. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `server/Mutalaa.Domain/Licensing/*`, `server/Mutalaa.Infrastructure/Packs/*`, `server/Mutalaa.Infrastructure/Storage/*`, `server/Mutalaa.Publisher/Program.cs` ve `Commands/*`
- Publisher test projesinde kapı, yazıcı, imza ve bütünleşik testler; `packages/content-schema/test/fixtures/` açık anahtar ve imzalı örnek manifest
- `pipeline/sources/test-kucuk.toml`, `test-tefsir-ornek.toml`, fikstür üreteci
- `data/packs/dev/{surum}/` (git dışı); SeaweedFS'te `dev/manifest.json`, `dev/manifests/{surum}.json`, `packs/dev/...`
- Karar defterinde imza, kanonikleştirme ve fikstür kayıtları; lisans defterinde `test-` kaynaklar

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A13-yayinlayici-ve-yayin-kapisi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A12](./A12-arama-indeksi-ve-paket-semasi.md) · Sonraki: [A14](./A14-api-editor-uclari.md)
