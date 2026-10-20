# A07 · Editoryal veritabanı (EF Core 10 + PostgreSQL 18)

> **Sürüm:** 1.1 · **Tarih:** 21 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-11](../../00-ozet/02-karar-defteri.md#k-11--veritabanı-postgresql-18) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-33](../../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A03](./A03-yerel-altyapi.md) · [A04](./A04-capa-ve-test-vektorleri.md) · [A06](./A06-lisans-defteri-ve-enumlar.md) · **İnsan adımı:** yok
> **Ajanlar:** `sunucu-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `ef-goc` · `lisans-kapisi` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A07`

## Amaç
İçeriğin tek doğruluk kaynağı olan editoryal veritabanı, [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) belgesindeki v1 şemasıyla EF Core 10 göçleri üzerinden `icerik` şemasında kurulur. Identity tabloları ayrı şemada durur; `seed` komutu rolleri ve ilk yöneticiyi açar. Göç, enum ve şema dökümü testleri Testcontainers ile `postgres:18` üzerinde koşar. İçerik hattı (A10), Yayınlayıcı (A13) ve API (A14) bu şemaya yazar ve okur.

## Okunacak belgeler
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): tamamı
- [Backend API](../../02-mimari/05-backend-api.md): §2 çözüm yapısı, §3 `Program.cs` ve `seed` dalı, §6 editör kimliği, §7 EF Core 10 ve Npgsql, §9 kültür
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 göç ve enum testleri
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §3 kullanıcı sırları, §6 adım 2–3, §10.4 EF Core ve saat
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §11 (`AnchorRef`, değer dönüştürücü)

## Kapsam
**Yapılır**
- Domain varlıkları; A06'daki enum'lar kullanılır. Kalan beş tür (`unit_kind`, `unit_status`, `metin_durumu`, `inceleme_durumu`, `surum_durumu`) aynı etiket kuralıyla C#'a ve `packages/content-schema/enums.json` dosyasına eklenir (öneri); böylece 11 türün hepsi tek dosyayla karşılaştırılır.
- `IcerikDbContext` (`Mutalaa.Infrastructure/Persistence`) ve 19 tablo: `source`, `unit`, `root`, `lemma`, `lemma_gloss`, `quran_word`, `quran_word_fix`, `tr_root_index`, `tr_form`, `surah_alias`, `xref`, `review`, `page_map`, `ayah_box`, `audio_timing`, `release`, `pipeline_run`, `hadith_number_map`, `hadith_location`; §2'deki 11 enum türü.
- Identity: `EditorUser`, roller `editor` ve `admin`; tablolar `kimlik` şemasında (Backend API §7, öneri).
- İlk göç, idempotent SQL betiği, göç paketi denemesi, `seed` komutu ve testler.

**Yapılmaz**
- `xref_vote` ve `embedding` tabloları: ikisi de v1.x'tir (§7, §9.2); `embedding` ayrıca pgvector ister. Faz 4'te (A35–A36 ya da anlamsal katman işi) eklenir.
- API uçları, çerezli oturum ve yetki politikaları (A14). Hat yüklemesi ve `staging_unit` (A10). Yayınlayıcı okumaları (A13).
- `quran_marker` gibi belgede olmayan tablolar (A11'in kararıyla, kendi göçünde).

## Adımlar
### A07.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar:
  - `EFCore.NamingConventions`'ın EF Core 10 desteği (Editoryal veritabanı §12).
  - Npgsql EF Core 10 sağlayıcısında enum eşleme API'sinin adı ve kullanımı (Backend API §7; Editoryal veritabanı §12).
  - `xmin` eşzamanlılık belirteci (`IsRowVersion()`; Backend API §7).
  - PostgreSQL 18'de `uuidv7()` işlevi ve üretilen sütunların varsayılan türü (ED-3). A03'teki konteynerde `SELECT uuidv7();` ile de sınanır.
  - ~~`xunit.v3` ile `IAsyncLifetime` imzası; Test stratejisi §6'daki örnek `ValueTask` döndürür, sonuç oraya işlenir.~~ Çözüldü (21 Ekim 2026, [K-33](../../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)): `InitializeAsync()` ve `DisposeAsync()` `ValueTask` döndürür ([IAsyncLifetime.cs](https://raw.githubusercontent.com/xunit/xunit/main/src/xunit.v3.core/IAsyncLifetime.cs), [göç kılavuzu](https://xunit.net/docs/getting-started/v3/migration)); sonuç Test stratejisi §6'ya işlendi. Burada yalnız örnek `MigrationTests` ile derlenip koştuğu görülür. Test komutu `dotnet test --solution server/Mutalaa.slnx` (MTP).
  - `pg_dump --schema-only` çıktısındaki sürüme ya da oturuma bağlı satırlar (sürüm yorumları; varsa rastgele anahtar taşıyan satırlar).
- `uuidv7()` yoksa kimlik değerini hat ve uygulama üretir; varsayılan değer göçe yazılmaz (Editoryal veritabanı §5).
- **Bitti sayılır:** altı madde kaynaklı aşama kaydında (xunit maddesi K-33 ile çözüldü; burada yalnız derleme ile teyit edilir).

### A07.2 · Domain ve `IcerikDbContext` (`sunucu-gelistirici`)
- Varlıklar `Mutalaa.Domain` altında (`Content/`, `Links/`, `Releases/`, `Review/`; Backend API §2). Domain EF Core'a bağlanmaz.
- Bağlam: varsayılan şema `icerik`; tablo adları tekil ve `ToTable("source")` gibi açıkça; sütunlar snake_case; zaman `timestamptz` ve UTC; eşzamanlılık `xmin`.
- Enum'lar §2'deki 11 PostgreSQL türüne eşlenir; etiketler ve sıra `packages/content-schema/enums.json` ve §2 ile aynı.
- Çapa sütunları (`anchor` ve `_anchor` ile bitenler) `UseCollation("C")` ve `AnchorRef` değer dönüştürücüsüyle bağlanır; geçersiz çapa yazılamaz. `parent_path` ve `review.hedef_anahtar` çapa değildir, düz metindir. `unit.anchor` `@` taşımaz.
- Tür eşlemeleri §12'deki gibi: `int4range` → `NpgsqlRange<int>`, `jsonb`, `tsvector`. `tsv_tr` ve `tsv_ar` `HasComputedColumnSql(…, stored: true)`; GiST ve GIN dizinleri `HasMethod(…)`; kısmi dizinler (`review_queue`, `xref_queue`, `review_xref`) ve CHECK kısıtları belgedeki ifadelerle.
- EF'nin ifade edemediği yapılar göçte ham SQL'dir: `xref_natural_key` ve `page_map` üzerindeki `UNIQUE NULLS NOT DISTINCT` (§12).
- **Bitti sayılır:** `dotnet build` uyarısız; her tablo, sütun, kısıt ve dizin belgedeki adla eşlenmiş.

### A07.3 · Identity ve `seed` (`sunucu-gelistirici`)
- `EditorUser`, roller `editor` ve `admin`; Identity tabloları `kimlik` şemasında (öneri). Parola en az 12 karakter, 5 hatalı denemede 15 dakika kilit (Backend API §6, öneri).
- `Mutalaa.Api/Program.cs`'e `AddInfrastructure` ve `seed` dalı eklenir (Backend API §3: `if (args is ["seed"])`). Uçlar A14'tedir.
- `seed` idempotenttir: roller yoksa açılır; yönetici `Mutalaa:Seed:AdminEmail` ve `Mutalaa:Seed:AdminPassword` ayarlarından okunur (kullanıcı sırları; Yerel geliştirme §6 adım 3).
- **Bitti sayılır:** `seed` art arda iki kez çalışınca iki rol ve tek yönetici var (test).

### A07.4 · İlk göç ve yerel uygulama
- `dotnet ef migrations add <ad>` ile `server/Mutalaa.Infrastructure/Migrations` altında tek göç. SQL `dotnet ef migrations script --idempotent` ile `.tmp/` altına yazılır; `inceleyici` belgedeki DDL ile tablo tablo karşılaştırır.
- Bağlantı dizesi kullanıcı sırlarındadır (Yerel geliştirme §3). Api projesinin csproj dosyasında `UserSecretsId` yoksa önce `dotnet user-secrets init --project server/Mutalaa.Api` çalışır (onay ister; yalnız csproj'a kimlik yazar, sır yazmaz). `.env`'deki parola değiştirildiyse `dotnet user-secrets … set` komutunu kullanıcı çalıştırır; Claude Code parolayı görmez.
- Komutlar `Development` ortamında çalışır: kit ayarları Claude Code komutlarına `ASPNETCORE_ENVIRONMENT=Development` ve `DOTNET_ENVIRONMENT=Development` verir (`.claude/settings.json` › `env`); kullanıcı sırları yalnız bu ortamda yüklenir. Elle açılan terminalde değer komutun başına yazılır (`ef-goc`).
- Yerel veritabanına `dotnet ef database update …` ile uygulanır. Göç paketi `dotnet ef migrations bundle` ile `.tmp/` altına üretilerek denenir (CI ve canlı için; Backend API §7).
- **Bitti sayılır:** yerelde `icerik` ve `kimlik` şemaları ve bütün tablolar var; model ile göç arasında fark yok.

### A07.5 · Testler (`test-yazari`, `sunucu-gelistirici`)
- Konum `server/tests/Mutalaa.Api.Tests/` (öneri; Api testleri zaten Testcontainers `postgres:18` kullanır, Backend API §11).
- `MigrationTests`: boş kaba bütün göçler uygulanır, bekleyen göç kalmaz (Test stratejisi §6).
- Enum testi: 11 türün `pg_enum` etiketleri `enumsortorder` sırasıyla `enums.json` ile aynı; JSON'daki değerler de §2 ile aynı.
- Şema dökümü: konteyner içinde `pg_dump --schema-only`; A07.1'deki değişken satırlar ayıklanır; sonuç `server/tests/Mutalaa.Api.Tests/Snapshots/editoryal-sema.sql` (öneri yol) ile karşılaştırılır. Bilinçli değişiklikte anlık görüntü bir ortam değişkeniyle yeniden yazılır (öneri) ve farkı commit'te gözden geçirilir.
- Kısıt testleri: biçimsiz `content_hash` reddedilir; `kurul_onay` dolu ama tarih ya da özet boşsa reddedilir; `status = 'kullanim_disi'` ve boş `successors` reddedilir; `xref_natural_key` NULL aralıklı kopyayı reddeder; `char_start >= char_end` reddedilir; `tsv_tr` ve `tsv_ar` saklı üretilen sütundur (`pg_attribute.attgenerated = 's'`).
- Değer dönüştürücü: geçersiz çapa yazma girişimi hata verir. `seed` idempotentliği.
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil (Docker Desktop açık).

## Kabul ölçütleri
- [ ] `dotnet build server/Mutalaa.slnx` uyarısız ve hatasız.
- [ ] `dotnet test --solution server/Mutalaa.slnx` yeşil; `MigrationTests` boş veritabanına bütün göçleri uyguluyor ve bekleyen göç yok.
- [ ] PostgreSQL'deki 11 enum türünün etiketleri ve sırası `enums.json` ve Editoryal veritabanı §2 ile aynı (test).
- [ ] Şema dökümü testi yeşil; anlık görüntü dosyası depoda.
- [ ] `dotnet ef migrations has-pending-model-changes` fark bildirmiyor.
- [ ] Yerel veritabanında `icerik` şemasında 19 tablo var (göç geçmişi tablosu hariç); Identity tabloları `kimlik` şemasında.
- [ ] `seed` iki kez çalıştırıldıktan sonra `editor` ve `admin` rolleri ve tek yönetici var.
- [ ] İdempotent SQL betiği belgedeki DDL ile karşılaştırıldı; fark yok ya da `/belge-esitle` ile işlendi.
- [ ] `appsettings*.json` dosyalarında parola ya da anahtar değeri yok.

## Doğrulama
```bash
docker compose up -d && docker compose ps
dotnet build server/Mutalaa.slnx
dotnet test --solution server/Mutalaa.slnx
dotnet ef migrations has-pending-model-changes --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
dotnet ef migrations script --idempotent --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api -o .tmp/editoryal-goc.sql
dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt icerik.*" -c "\dt kimlik.*" -c "\dT icerik.*"'
dotnet run --project server/Mutalaa.Api -- seed && dotnet run --project server/Mutalaa.Api -- seed
dotnet ef migrations bundle --force --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api -o .tmp/efbundle.exe
grep -rniE '"(Password|AdminPassword|SecretKey|PrivateKey)"[[:space:]]*:[[:space:]]*"[^"]+"|Password=[^;"]+' server --include='appsettings*.json'   # çıktı boş
```
Komutlar `Development` ortamında koşar (kit ayarı; A07.4). Son satır JSON anahtarı olarak yazılmış gizli değerleri ve bağlantı dizesinin içindeki `Password=` değerini arar.

## Dikkat
- Şemanın tek sahibi EF Core göçleridir; Python hattı şema değiştirmez. Uygulanmış göç değiştirilmez; API açılışında otomatik göç yoktur. Ayrıntı: `ef-goc`.
- Enum'a eklenen değer geri alınamaz; yıkıcı değişiklik genişlet, taşı, daralt adımlarıyla yapılır (§12).
- Çapa sütunları `COLLATE "C"`; aralıklar `int4range` ve yarı açık `[)`. `metin` sütunu kanonik metindir: hazır kaynak metni (Tanzil) değiştirilemez, NFC yalnız kendi metnimize ilk kayıtta uygulanır (K-26).
- `license_status` sırası kapının davranışını belirler; etiketler A06'daki JSON'dan sapmaz. Ayrıntı: `lisans-kapisi`.
- Saat: `timestamptz` sütununa yalnız `DateTimeKind.Utc` değer yazılır (Yerel geliştirme §10.4). Uygulama açılışta `InvariantCulture` kullanır.
- Gizli değerler `dotnet user-secrets` ile verilir; bu komut kullanıcı onayı ister. Bağlantı dizesi ve yönetici parolası dosyaya ya da commit'e yazılmaz.
- Testcontainers Docker Desktop ister; Docker kapalıysa testler kırmızı görünür, bu bir kod hatası sayılmaz.
- Belge farkları: ED-7 çözüldü (19 Ekim 2026); Backend API Editoryal veritabanının tür adlarını (`license_status`, `xref_status`) ve `basarisiz` değerini kullanır. Backend API §4.1 ve §12 madde 1–2'deki açık sorular da çözüldü (19 Ekim 2026): `hedef_tablo` listesi Editoryal veritabanı §8'de, `basarisiz` değeri §2'dedir. Şema bu belgeyi izler.
- Commit kapsamı: `Mutalaa.Domain` ve `Mutalaa.Infrastructure` değişiklikleri için `server` ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §6); ör. `feat(server): add editorial schema and first migration`.

## İnsan adımları
- Yok. Kullanıcı `.env` parolasını değiştirdiyse bağlantı dizesini `dotnet user-secrets` ile kendisi girer.

## Çıktılar
- `server/Mutalaa.Domain/` varlıkları ve enum'ları
- `server/Mutalaa.Infrastructure/Persistence/IcerikDbContext` ve yapılandırmalar; `Identity/`; `Migrations/` (ilk göç ve model anlık görüntüsü)
- `server/Mutalaa.Api/Program.cs` (`AddInfrastructure`, `seed` dalı)
- `server/tests/Mutalaa.Api.Tests/` göç, enum, şema dökümü, kısıt ve `seed` testleri; `Snapshots/editoryal-sema.sql`
- `server/Directory.Packages.props` ve `packages.lock.json` güncellemeleri
- Git dışı: `.tmp/editoryal-goc.sql`, `.tmp/efbundle.exe`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A07-editoryal-veritabani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A06](./A06-lisans-defteri-ve-enumlar.md) · Sonraki: [A08](./A08-ci-is-akislari.md)
