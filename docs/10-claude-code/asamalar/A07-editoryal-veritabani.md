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
- Domain varlıkları; A06'daki enum'lar kullanılır. Kalan beş tür (`unit_kind`, `unit_status`, `metin_durumu`, `inceleme_durumu`, `surum_durumu`) aynı etiket kuralıyla C#'a ve `packages/content-schema/enums.json` dosyasına eklenir ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)); böylece 11 türün hepsi tek dosyayla karşılaştırılır.
- `IcerikDbContext` (`Mutalaa.Infrastructure/Persistence`) ve 19 tablo: `source`, `unit`, `root`, `lemma`, `lemma_gloss`, `quran_word`, `quran_word_fix`, `tr_root_index`, `tr_form`, `surah_alias`, `xref`, `review`, `page_map`, `ayah_box`, `audio_timing`, `release`, `pipeline_run`, `hadith_number_map`, `hadith_location`; §2'deki 11 enum türü.
- Identity: `EditorUser`, roller `editor` ve `admin`; tablolar `kimlik` şemasında ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları), Backend API §7).
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
- Varlıklar `Mutalaa.Domain` altında (`Content/`, `Links/`, `Releases/`, `Reviews/`; Backend API §2). Domain EF Core'a bağlanmaz.
- Bağlam: varsayılan şema `icerik`; tablo adları tekil ve `ToTable("source")` gibi açıkça; sütunlar snake_case; zaman `timestamptz` ve UTC; eşzamanlılık `xmin`.
- Enum'lar §2'deki 11 PostgreSQL türüne eşlenir; etiketler ve sıra `packages/content-schema/enums.json` ve §2 ile aynı.
- Çapa sütunları (`anchor` ve `_anchor` ile bitenler) `UseCollation("C")` ve `AnchorRef` değer dönüştürücüsüyle bağlanır; geçersiz çapa yazılamaz. `parent_path` ve `review.hedef_anahtar` çapa değildir, düz metindir. `unit.anchor` `@` taşımaz.
- Tür eşlemeleri §12'deki gibi: `int4range` → `NpgsqlRange<int>`, `jsonb`, `tsvector`. `tsv_tr` ve `tsv_ar` `HasComputedColumnSql(…, stored: true)`; GiST ve GIN dizinleri `HasMethod(…)`; kısmi dizinler (`review_queue`, `xref_queue`, `review_xref`) ve CHECK kısıtları belgedeki ifadelerle.
- Ham SQL yalnız `xref_natural_key`'dir (gerçek `UNIQUE NULLS NOT DISTINCT` kısıtı; hat `ON CONFLICT ON CONSTRAINT` ile hedefler). `page_map` `AreNullsDistinct(false)` ile adlı tekil dizin olarak EF'de kurulur (§12).
- **Bitti sayılır:** `dotnet build` uyarısız; her tablo, sütun, kısıt ve dizin belgedeki adla eşlenmiş.

### A07.3 · Identity ve `seed` (`sunucu-gelistirici`)
- `EditorUser`, roller `editor` ve `admin`; Identity tabloları `kimlik` şemasında. Parola en az 12 karakter (başka şart yok), 5 hatalı denemede 15 dakika kilit, e-posta tekil ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları), Backend API §6).
- `Mutalaa.Api/Program.cs`'e `AddIcerikDb` ve `AddEditorIdentity` çağrıları ile `seed` dalı eklenir (Backend API §3: `if (args is ["seed"])`). Uçlar A14'tedir.
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
- Şema dökümü: konteyner içinde `pg_dump --schema-only`; A07.1'deki değişken satırlar ayıklanır; sonuç `server/tests/Mutalaa.Api.Tests/Snapshots/editoryal-sema.sql` ile karşılaştırılır. Bilinçli değişiklikte anlık görüntü `MUTALAA_UPDATE_SNAPSHOTS=1` ortam değişkeniyle yeniden yazılır (test bilerek kırmızı biter; `CI` doluysa reddedilir) ve farkı commit'te gözden geçirilir.
- Kısıt testleri: biçimsiz `content_hash` reddedilir; `kurul_onay` dolu ama tarih ya da özet boşsa reddedilir; `status = 'kullanim_disi'` ve boş `successors` reddedilir; `xref_natural_key` NULL aralıklı kopyayı reddeder; `char_start >= char_end` reddedilir; `tsv_tr` ve `tsv_ar` saklı üretilen sütundur (`pg_attribute.attgenerated = 's'`).
- Değer dönüştürücü: geçersiz çapa yazma girişimi hata verir. `seed` idempotentliği.
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil (Docker Desktop açık).

## Kabul ölçütleri
- [x] `dotnet build server/Mutalaa.slnx` uyarısız ve hatasız.
- [x] `dotnet test --solution server/Mutalaa.slnx` yeşil; `MigrationTests` boş veritabanına bütün göçleri uyguluyor ve bekleyen göç yok.
- [x] PostgreSQL'deki 11 enum türünün etiketleri ve sırası `enums.json` ve Editoryal veritabanı §2 ile aynı (test).
- [x] Şema dökümü testi yeşil; anlık görüntü dosyası depoda.
- [x] `dotnet ef migrations has-pending-model-changes` fark bildirmiyor.
- [x] Yerel veritabanında `icerik` şemasında 19 tablo var (göç geçmişi tablosu hariç); Identity tabloları `kimlik` şemasında.
- [x] `seed` iki kez çalıştırıldıktan sonra `editor` ve `admin` rolleri ve tek yönetici var.
- [x] İdempotent SQL betiği belgedeki DDL ile karşılaştırıldı; fark yok ya da `/belge-esitle` ile işlendi.
- [x] `appsettings*.json` dosyalarında parola ya da anahtar değeri yok.

Kanıtlar aşağıdaki "Aşama kaydı"ndadır.

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
- `server/Mutalaa.Api/Program.cs` (`AddIcerikDb`, `AddEditorIdentity`, `seed` dalı)
- `server/tests/Mutalaa.Api.Tests/` göç, enum, şema dökümü, kısıt ve `seed` testleri; `Snapshots/editoryal-sema.sql`
- `server/Directory.Packages.props` ve `packages.lock.json` güncellemeleri
- Git dışı: `.tmp/editoryal-goc.sql`, `.tmp/efbundle.exe`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A07-editoryal-veritabani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A06](./A06-lisans-defteri-ve-enumlar.md) · Sonraki: [A08](./A08-ci-is-akislari.md)

## Aşama kaydı (kapanış 2026-10-27)

Plan kararları (2026-10-26): BÇ-05 `review.yz_kaydi jsonb` olarak çözüldü; `enums.json` 11 türe çıktı; parola yalnız uzunluk >= 12. Üçü, ad politikası ve dizin kuralıyla birlikte [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) olarak kaydedildi.

### A07.1 doğrulamaları (iki `arastirmaci`, 26 Ekim 2026)

| Madde | Sonuç ve kaynak |
|---|---|
| EF Core 10 sürümü | 10.0.14 (25 Ekim, plan dışı güvenlik sürümü), `dotnet-ef` 10.0.14; araç eskiyse yalnız uyarı çıkar ([OperationExecutor.cs](https://raw.githubusercontent.com/dotnet/efcore/release/10.0/src/EFCore.Design/Design/OperationExecutor.cs)). Kodda 10.0.14 sabitlendi |
| Npgsql EF 10.0.3 `MapEnum` | Etiketleri alfabetik dizer, tasarım gereği ([efcore.pg #3390](https://github.com/npgsql/efcore.pg/issues/3390), [#3667](https://github.com/npgsql/efcore.pg/issues/3667)); açık `HasPostgresEnum` ile sıra korunur. `SetPostgresVersion(18, 0)` gerekir ([NpgsqlDbContextOptionsBuilder.cs](https://raw.githubusercontent.com/npgsql/efcore.pg/v10.0.3/src/EFCore.PG/Infrastructure/NpgsqlDbContextOptionsBuilder.cs)) |
| `EFCore.NamingConventions` | 10.0.1 EF Core 10 destekler (Apache-2.0); kültür verilmezse Invariant; açık adları ezmez ([nuspec](https://api.nuget.org/v3-flatcontainer/efcore.namingconventions/10.0.1/efcore.namingconventions.nuspec)) |
| `xmin` | `uint` + `IsRowVersion()` -> `xid`, sütun adı `xmin`; göçte sütun üretilmez, gölge özellik çalışır ([Npgsql eşzamanlılık](https://www.npgsql.org/efcore/modeling/concurrency.html)); `DbUpdateConcurrencyException` testle doğrulandı |
| PostgreSQL 18 `uuidv7()` | 18.0'da eklendi ([functions-uuid](https://www.postgresql.org/docs/18/functions-uuid.html)); yerel kapta 18.6'da çalıştı (`uuid_extract_version` = 7) |
| Üretilen sütun varsayılanı | VIRTUAL; sanal sütun dizinlenemez, bu yüzden `STORED` açık yazılır ([sql-createtable](https://www.postgresql.org/docs/18/sql-createtable.html), [ddl-generated-columns](https://www.postgresql.org/docs/18/ddl-generated-columns.html)) |
| `pg_dump` değişken satırlar | `\restrict` ve `\unrestrict` rastgele anahtar taşır; sürüm yorumları ara sürümle değişir ([app-pgdump](https://www.postgresql.org/docs/18/app-pgdump.html), [CVE-2025-8714](https://www.postgresql.org/support/security/CVE-2025-8714/)); dört satır ayıklanır |
| Testcontainers | `Testcontainers.PostgreSql` 4.16.0 (MIT); parametresiz `PostgreSqlBuilder()` `[Obsolete]` ([NuGet](https://www.nuget.org/packages/Testcontainers.PostgreSql)); imaj `postgres:18.6-trixie` |
| Identity EF | 10.0.14; çerçeve başvurusu istemez; şema sürümü varsayılanı V1 (passkey tablosu yok, `kimlik` 7 tablo); model `IdentityOptions`'ı DI'dan okur ([IdentityUserContext.cs](https://raw.githubusercontent.com/dotnet/aspnetcore/release/10.0/src/Identity/EntityFrameworkCore/src/IdentityUserContext.cs)) |

### Kabul ölçütleri ve kanıt

| Ölçüt | Kanıt |
|---|---|
| Derleme | `dotnet build server/Mutalaa.slnx --no-incremental`: 0 uyarı, 0 hata |
| Testler | `dotnet test --solution server/Mutalaa.slnx` 1755/1755 (Domain 1544, Publisher 2, Api 209); Debug iki koşu ve Release bir koşu; `dotnet format ... --verify-no-changes` çıkış 0 |
| Enum sırası | `PostgresEnumTests`: 11 türün `pg_enum` etiketleri `enumsortorder` sırasıyla `enums.json` ile aynı; `EnumDocumentTests`: `enums.json` = belge §2; TypeScript 15, Python `test_enums.py` 33 |
| Anlık görüntü | `Snapshots/editoryal-sema.sql` (1393 satır) depoda; `SchemaSnapshotTests` ardışık iki koşuda yeşil |
| Bekleyen değişiklik | `dotnet ef migrations has-pending-model-changes`: "No changes have been made" |
| Yerel veritabanı | `icerik` 19 tablo (+ göç geçmişi), `kimlik` 7 tablo, 11 enum; göç geçmişinde yalnız `20261026222825_CreateEditorialSchema` |
| `seed` | İki çalıştırma çıkış 0; `kimlik.roles` 2, `kimlik.users` 1, yönetici `admin` rolünde; günlükte parola, e-posta ve bağlantı dizesi yok |
| İdempotent betik | `.tmp/editoryal-goc.sql` geçici veritabanında art arda iki kez hatasız uygulandı; Up -> Down -> Up döngüsü çalıştı; belge DDL'i ile `ModelDdlTests` (sütun, tip, NOT NULL, DEFAULT, 18 CHECK, 18 FK) ve DDL sadakati denetçisi karşılaştırdı; kabul edilmiş farklar Editoryal veritabanı §12'de |
| Gizli değer | `appsettings*.json` taraması boş; diff taramaları boş |
| Göç paketi | `.tmp/efbundle.exe` üretildi (git dışı) |

### İnceleme

Çok ajanlı denetim (7 bakış açısı: kod doğruluğu, metin bütünlüğü, lisans, DDL sadakati, test yeterliği, güvenlik, belge sapması; 49 ajan, her bulgu çürütülmeye çalışıldı): 50 bulgu, engelleyici yok; 37 onaylı, 6 kısmi, 7 çürütülen. Düzeltilenler: `Down()` 11 enum türünü ve `kimlik` şemasını düşürüyor; `kimlik.users` e-posta dizini tekil; bağlantı dizesi bağlam kurulurken okunuyor; `Api.csproj` biçimi; `AnchorSpan` üç anlamının belgelenmesi; K-26 için `unit.metin` bayt-bayt saklama testi (`TextIntegrityTests`); `unit.anchor`, FK, `page_map` ve kalan 13 CHECK testleri; Down döngüsü testi; test kabının rastgele parolası ve yalnız 127.0.0.1; belge sapmalarının tamamı (Backend API §2/§3/§6/§7, Editoryal veritabanı §1/§4/§5/§8/§11/§12/§13, A13/A14, Test stratejisi §6, Yerel geliştirme, Teknoloji yığını).

Devreden öneriler: `content_hash` ile `metin` tutarlılığı veritabanında denetlenmiyor (A10 yükleme kapısı); `source` özet sütunlarında biçim CHECK'i yok ([BÇ-41](../07-belge-celiskileri.md), A13/A14); kilit yalnız `AccessFailedAsync` / `CheckPasswordSignInAsync(lockoutOnFailure: true)` ile işler (A14 uç testi); `NoAction` FK'de EF izlenen çocuğu NULL'a çektiği için silme 23503 yerine 23502 verebilir (A14 hata eşlemesi); `unit` okumaları `tsv_*` sütunlarını da seçer (A13/A14 projeksiyon); `Program.cs` seed dalı için süreç düzeyi çıkış kodu testi yazılmadı; `THIRD_PARTY_NOTICES` A34'e eklendi; `halfvec` .NET türü v1.x'te doğrulanacak.

### Kullanıcıya bırakıldı

Yok (emülatör işi yok). Kullanıcı üç `dotnet user-secrets` değerini girdi ve veritabanı parolasını `.env` ile eşitledi.

### Sürprizler

Npgsql `MapEnum` etiketleri alfabetik diziyor (lisans kapısı sırasını bozardı); EF göç dosyaları, `dotnet user-secrets init` çıktısı ve kilit dosyaları BOM ve CRLF yazıyor; `migrations bundle` kilit dosyasına `win-x64` ekliyor; `.env` parolası kurulumdan sonra değişince kapsayıcı ve veritabanı eski parolada kalıyor. Hepsi `ef-goc` ve `windows-sorun` becerilerine işlendi.
