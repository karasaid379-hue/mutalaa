# A14 · API editör uçları

> **Sürüm:** 1.4 · **Tarih:** 9 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-46](../../00-ozet/02-karar-defteri.md#k-46--yayın-kaydı-içerik-özetleri-ve-fikstürler) · [K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** —
> **Ajanlar:** `sunucu-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `ef-goc` · `paket-yayini` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A14`

## Amaç
Editör kipindeki ASP.NET Core 10 Minimal API kurulur: ASP.NET Core Identity ile oturum ve roller, salt okunur kaynak kaydı uçları ve birim uçları, tek `review` tablosu üzerinden inceleme kuyrukları ve ikinci onay, yayın talebi uçları, RFC 9457 hata modeli ve depoya giren OpenAPI belgesi. Editör paneli (A15) bu belgeden üretilen istemciyle çalışır; içerik hattının adayları bu uçlarla onaylanır. Aşama tedarikle başlar: API'nin kullandığı hazır kitaplıklar (OpenAPI, Scalar, Serilog, sağlık denetimi, test araçları) sürümleri sabitlenerek alınır; yeniden yazılmaz.

## Okunacak belgeler
- [Backend API](../../02-mimari/05-backend-api.md): §1–§9 (tamamı) ve §10.6 (yayın durumları, terfi, geri alma)
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source`, §8 `review` ve inceleme akışı, §10 `release`, §12 EF Core notları
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 kaynak kaydı ve atıf (kaynak uçlarının döndürdüğü alanlar)
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.2 API ve altyapı paketleri
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §3 kullanıcı sırları, §6 adım 2–3 ve 5, §10.1 Türkçe yerel ayar
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §6.1 kaynaktan yayına akış
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 veritabanı göç testleri

## Kapsam
**Yapılır**
- `Program.cs` iskeletinin kalanı (Serilog, ProblemDetails, sağlık, OpenAPI), çerezli oturum, yetki politikaları (`Editor`, `Admin`) ve `DevAutoLogin`. Identity (`EditorUser`, `editor` ve `admin` rolleri, `kimlik` şeması, parola ve kilit ayarları), `seed` komutu ve `Program.cs` iskeletinin `AddIcerikDb`, `AddEditorIdentity` ve `seed` kısmı A07'de teslim edildi ([K-37](../../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)); A14 bunları yeniden kurmaz, yalnız uçları ve oturumu ekler.
- [Backend API](../../02-mimari/05-backend-api.md) §4 tablosundaki bütün v1 uçları, §4.1 kuyrukları ve ikinci onay, §4.2 uç kuralları, §6 hata kodları.
- Derlemede üretilip depoya giren `server/Mutalaa.Api/openapi/v1.json`; sağlık uçları; Serilog.
- Uç başına yetki matrisi testleri.
- A13'ten devredildi: `server/Mutalaa.Publisher/Dockerfile` ve `docker-compose.yml` içindeki `publisher` servisinin (`app` profili, `command: ["watch"]`) imaja bağlanması; `Signing__dev__PrivateKey` değerini kullanıcı `.env` içine yazar (Claude Code `.env` okumaz). API Dockerfile'ıyla aynı adımda yazılır ve `app` profili birlikte sınanır.

**Yapılmaz**
- v1.x genel kip uçları: hesap, senkron, bağlantı oyu (A35, A36).
- Paket üretimi ve yükleme (A13); API yalnız `release` kaydı açar.
- Editör arayüzü (A15). Kuyruklara aday yazan hat işleri (A11, A16–A19).

## Tedarik
| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| OpenAPI belgesi (çalışma zamanı) | `Microsoft.AspNetCore.OpenApi` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.AspNetCore.OpenApi/10.0.14), 25 Ekim 2026; `dotnet/dotnet` etiketi `v10.0.14`, commit `0427b9ab`; `Microsoft.OpenApi` `[2.12.2, 3.0.0)` aralığıyla gelir; nupkg) | `dotnet add package`; sürüm `server/Directory.Packages.props` içinde | Learn [Generate OpenAPI documents](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0) (güncelleme 29 Ekim 2026): .NET 10 varsayılanı OpenAPI 3.1, .NET 11 varsayılanı 3.2; bu yüzden `OpenApiVersion` açıkça `OpenApi3_1` yazılır; `MapOpenApi()` varsayılan yolu `/openapi/{documentName}.json`; NuGet kaydında 10.0.14 son kararlı sürümdür | `Swashbuckle.AspNetCore` 10.3.1 (19 Ekim 2026); `NSwag.AspNetCore` 14.7.1 (20 Nisan 2026) |
| Derlemede `openapi/v1.json` üretimi | `Microsoft.Extensions.ApiDescription.Server` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.Extensions.ApiDescription.Server/10.0.14), 25 Ekim 2026; aynı commit `0427b9ab`; bağımlılığı yok; nupkg) | `dotnet add package`; csproj'ta `OpenApiDocumentsDirectory` = `openapi`, `OpenApiGenerateDocumentsOptions` = `--file-name v1` | Aynı Learn sayfası, "Generate OpenAPI documents at build time": paket derlemede belgeyi üretir; dosya adı varsayılan olarak proje adıdır, `--file-name` ile değişir; sürüm `--openapi-version` ile seçilir; veritabanı kodunu atlatma kalıbı resmî örnekte vardır (`Assembly.GetEntryAssembly()?.GetName().Name != "GetDocument.Insider"`) | `Swashbuckle.AspNetCore.Cli` 10.3.1 (`swagger tofile`) |
| API arayüzü (yalnız Development) | `Scalar.AspNetCore` 2.18.7 ([NuGet](https://www.nuget.org/packages/Scalar.AspNetCore/2.18.7), 30 Ekim 2026; `scalar/scalar` commit `66ba1d76`; net8.0, net9.0 ve net10.0 hedefli; nupkg) | `dotnet add package Scalar.AspNetCore`; `app.MapScalarApiReference()` | Scalar belgesi ([integration.md](https://raw.githubusercontent.com/scalar/scalar/66ba1d7671c2f230af9be4ed7a94ee057683b8df/documentation/integrations/aspnetcore/integration.md), commit `66ba1d76`): varsayılan yol `/scalar`, varsayılan belge adı `v1`; varlıklar pakette yerel, yazı tipleri CDN'den gelir ve `DisableDefaultFonts()` ile kapanır | `Swashbuckle.AspNetCore.SwaggerUI` 10.3.1 (Learn örneği); Redoc |
| Yapılandırılmış günlük | `Serilog.AspNetCore` 10.0.0 ([NuGet](https://www.nuget.org/packages/Serilog.AspNetCore/10.0.0), 28 Kasım 2025; `serilog/serilog-aspnetcore` commit `0ddce6f8`; birlikte gelenler: `Serilog` 4.3.0, `Serilog.Sinks.Console` 6.1.1, `Serilog.Sinks.File` 7.0.0, `Serilog.Settings.Configuration` 10.0.0; nupkg) | `dotnet add package Serilog.AspNetCore` | nuspec hedefleri `net8.0`, `net9.0`, `net10.0`; NuGet kaydında 10.0.0 son kararlı sürümdür; `UseSerilogRequestLogging()` istek günlüğünü verir | Yerleşik `Microsoft.Extensions.Logging` JSON konsol biçimleyicisi |
| Çerezli oturum ve 401/403 | `Microsoft.AspNetCore.Identity.EntityFrameworkCore` 10.0.14 (A07'de kurulu; `dotnet list server/Mutalaa.slnx package` ile doğrulandı) ve yerleşik çerez kimlik doğrulaması | Yeni paket yok; giriş ucu `CheckPasswordSignInAsync(kullanici, parola, lockoutOnFailure: true)` çağırır | Learn [Cookie login redirects are disabled for known API endpoints](https://learn.microsoft.com/en-us/aspnet/core/breaking-changes/10/cookie-authentication-api-endpoints?view=aspnetcore-10.0) (.NET 10 Preview 7'den beri; güncelleme 29 Ekim 2026): JSON okuyan ya da yazan Minimal API uçları ve `TypedResults` kullanan uçlar yönlendirme yerine 401/403 döner; tanınmayan uçta `DisableCookieRedirect()` | `CookieAuthenticationEvents.OnRedirectToLogin` ve `OnRedirectToAccessDenied` olaylarını 401/403 yazacak biçimde ezmek |
| Minimal API girdi doğrulaması | `Microsoft.Extensions.Validation` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.Extensions.Validation/10.0.14), 25 Ekim 2026; commit `0427b9ab`) ve `builder.Services.AddValidation()` | Web SDK projesinde çatıyla gelir (paket başvurusu yok); düz sınıf kitaplığında paket başvurusu gerekir | Learn [Validation in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/validation?view=aspnetcore-10.0) (güncelleme 31 Ekim 2026): kaynak üretici yalnız `AddValidation` çağrılan derlemeyi kapsar; .NET 10'da `[ValidatableType]` deneyseldir (ASP0029); null olabilen değer türü parametreler doğrulanmaz ([dotnet/aspnetcore #67033](https://github.com/dotnet/aspnetcore/issues/67033)); bilinmeyen JSON alanı için `UnmappedMemberHandling = Disallow` | `FluentValidation` 12.2.0 (10 Ekim 2026); `MiniValidation` 0.10.0 (4 Mayıs 2026) |
| RFC 9457 hata modeli | Yerleşik `AddProblemDetails()`, `IProblemDetailsService`, `IExceptionHandler` | Yok (çatıyla gelir, ek paket yok) | Learn [Handle errors in ASP.NET Core APIs](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/error-handling-api?view=aspnetcore-10.0) (güncelleme 29 Ekim 2026): "Problem Details for HTTP APIs" ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)) `IProblemDetailsService` ile üretilir | Yok (yerleşik) |
| Sağlık uçları (`/health/live`, `/health/ready`) | Yerleşik `AddHealthChecks()` ve `Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore/10.0.14), 25 Ekim 2026; `AddDbContextCheck`; nupkg) | `dotnet add package` | nuspec bağımlılıkları `Microsoft.Extensions.Diagnostics.HealthChecks` 10.0.14 ve `Microsoft.EntityFrameworkCore.Relational` 10.0.14 (A07'deki sürümle aynı) | `AspNetCore.HealthChecks.NpgSql` 9.0.0 (19 Aralık 2024) |
| Uç, yetki matrisi ve akış testleri | `Microsoft.AspNetCore.Mvc.Testing` 10.0.14 ([NuGet](https://www.nuget.org/packages/Microsoft.AspNetCore.Mvc.Testing/10.0.14), 25 Ekim 2026; `WebApplicationFactory`); `Testcontainers.PostgreSql` 4.16.0 (8 Ekim 2026; commit `df0f931e`) ve `xunit.v3` 4.0.2 (9 Ekim 2026; commit `0c7aa499`), ikisi A07'de kayıtlı | `dotnet add package` (yalnız `Mutalaa.Api.Tests`) | `dotnet list server/Mutalaa.slnx package`: Testcontainers ve xunit.v3 `Mutalaa.Api.Tests` projesinde 4.16.0 ve 4.0.2 olarak çözümlenmiş; Mvc.Testing nuspec bağımlılıkları `Microsoft.AspNetCore.TestHost`, `Microsoft.Extensions.DependencyModel` ve `Microsoft.Extensions.Hosting` 10.0.14 | `Verify.XunitV3` 33.3.4 (16 Ekim 2026; OpenAPI JSON anlık görüntü testi, isteğe bağlı) |
| İz ve ölçü (isteğe bağlı; Teknoloji yığını §2.2 ve Backend API §8) | `OpenTelemetry.Extensions.Hosting` 1.20.1 (20 Ekim 2026), `OpenTelemetry.Instrumentation.AspNetCore` 1.20.1 (21 Ekim 2026), `OpenTelemetry.Instrumentation.Http` 1.20.1 (21 Ekim 2026), `OpenTelemetry.Exporter.OpenTelemetryProtocol` 1.20.1 (20 Ekim 2026), `Npgsql.OpenTelemetry` 10.0.3 (27 Mayıs 2026) | `dotnet add package` | NuGet kaydında hepsi son kararlı sürümdür; çekirdek `OpenTelemetry` 1.20.1; `Npgsql.OpenTelemetry` nuspec'i `Npgsql` 10.0.3 ister | Yerleşik `System.Diagnostics` etkinlikleri ve konsol günlüğü (dışa aktarım olmadan) |

Kendimiz yapacağımız işler: inceleme kuyrukları ve ikinci onay kuralları (`Mutalaa.Domain/Reviews`); imleçli sayfalama; `If-Match` ve `xmin` ETag eşlemesi; OCR sayfa görseli ucu (salt okunur, yalnız `data/raw/{baskı}/`, yol kaçışı denetimli); `urn:mutalaa:problem:<kod>` tablosu; uç başına yetki matrisi testlerinin üretimi.

## Adımlar
### A14.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular. Kitaplığın varlığı ve son kararlı sürümü NuGet kayıt dizininden okunur (`https://api.nuget.org/v3-flatcontainer/<kimlik küçük harfle>/index.json`); `www.nuget.org/packages/...` sayfaları GET isteğine 200, HEAD isteğine 404 verir. Learn ve Scalar adresleri açılır, güncelleme tarihleri tablodakilerle karşılaştırılır. Açılmayan adresin ya da kayıtta bulunmayan sürümün yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Bu aşama içerik kaynağı almaz: `data/gelen/` altına dosya inmez, `pipeline/sources/` altına kayıt açılmaz. Alınan yapılar NuGet kitaplıklarıdır; paket dosyalarını `dotnet restore` indirir. Sürümler `server/Directory.Packages.props` içinde sabitlenir (A14.2); `packages.lock.json` her paketin içerik özetini (`contentHash`) kaydeder.
- Sürümü paket kaydından doğrula: `dotnet list server/Mutalaa.slnx package` istenen ve çözümlenen sürümü, `--outdated` bayrağı kayıttaki son kararlı sürümü gösterir. Tablo, `Directory.Packages.props` ve komut çıktısı aynı sürümleri vermelidir.
- `Microsoft.AspNetCore.OpenApi` 10.0.14, `Microsoft.OpenApi` paketini `[2.12.2, 3.0.0)` aralığıyla getirir; kayıttaki son kararlı `Microsoft.OpenApi` 3.x'tir. Doğrudan `Microsoft.OpenApi` başvurusu eklenmez, çünkü sürüm aralığı çakışır.
- **Bitti sayılır:** tablodaki her kitaplığın sürümü NuGet kaydında doğrulanmış (ya da yedek adayla değiştirilip tablo güncellenmiş); Learn ve Scalar adresleri açılıyor; sürümler A14.2'de `Directory.Packages.props` içine bu değerlerle yazılmaya hazır.

### A14.1 · Doğrulamalar
- `arastirmaci` aşağıdaki maddeleri resmî kaynakla ve çalışan kodla doğrular. Bunlar Backend API §2, §3 ve §6'da "Doğrulanacak" diye işaretlidir. Tedarik araştırması (1 Kasım 2026) belgeleri okudu; kod düzeyindeki sınama bu adımdadır:
  - **Minimal API doğrulaması (`AddValidation()`).** Kaynak: [Validation in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/validation?view=aspnetcore-10.0) (güncelleme 31 Ekim 2026). Kaynak üretici yalnız `AddValidation` çağrılan derlemeyi kapsar; bu yüzden istek tipleri `Mutalaa.Api` içinde tanımlanır, `Mutalaa.Domain` pakete bağımlı olmaz. .NET 10'da null olabilen değer türü parametreler doğrulanmaz ([dotnet/aspnetcore #67033](https://github.com/dotnet/aspnetcore/issues/67033)); bilinmeyen JSON alanını reddetmek için `UnmappedMemberHandling = Disallow` gerekir. Kod sınaması: zorunlu alanı eksik istek 400 `HttpValidationProblemDetails` döner.
  - **Derlemede OpenAPI belgesi.** Kaynak: [Generate OpenAPI documents](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0) (güncelleme 29 Ekim 2026). `Microsoft.Extensions.ApiDescription.Server` belgeyi derlemede üretir; dizin `OpenApiDocumentsDirectory`, dosya adı ve sürüm `OpenApiGenerateDocumentsOptions` ile (`--file-name`, `--openapi-version`) verilir. Üretim giriş noktasını `GetDocument.Insider` adıyla çalıştırır; veritabanı kodu `Assembly.GetEntryAssembly()?.GetName().Name != "GetDocument.Insider"` denetimiyle atlanır. .NET 10 varsayılanı OpenAPI 3.1'dir (.NET 11'de 3.2): `OpenApiVersion` açıkça `OpenApi3_1` yazılır. Kod sınaması: `dotnet build -c Release` veritabanı olmadan `openapi/v1.json` üretir; `--openapi-version` seçeneği 10.0.14 ile çalışmazsa çalışma zamanı ayarı yeterlidir.
  - **Scalar uç adı.** Kaynak: Scalar belgesi (`documentation/integrations/aspnetcore/integration.md`, commit `66ba1d76`). `app.MapScalarApiReference()` varsayılan yolu `/scalar`, varsayılan belge adı `v1`'dir. Backend API §6'daki `/scalar/v1` yolu çalışan API ile doğrulanır; farklıysa Backend API düzeltilir.
  - **Çerezde 401 ve 403.** Kaynak: [Cookie login redirects are disabled for known API endpoints](https://learn.microsoft.com/en-us/aspnet/core/breaking-changes/10/cookie-authentication-api-endpoints?view=aspnetcore-10.0) (güncelleme 29 Ekim 2026; .NET 10 Preview 7'den beri). JSON okuyan ya da yazan Minimal API uçları ve `TypedResults` kullanan uçlar yönlendirme yerine 401/403 döner; yanıtta `Location` başlığı kalır, yalnız durum kodu değişir. JSON yazmayan uç (sayfa görseli) kendiliğinden tanınmaz: `DisableCookieRedirect()` eklenir. Kod sınaması: oturumsuz JSON ucu ve oturumsuz görsel ucu 401 döner.
  - **`kalite-kapisi` hata kodu.** Backend API §6 kalite kapısına takılan yayın için 422 `kalite-kapisi` kodunu yazar; kod ve durum, yayın uçlarıyla birlikte sınanır. Değişirse Backend API ile A15 aynı değişiklikte eşitlenir.
- Npgsql enum eşlemesi, `xmin` (`IsRowVersion()`) ve `EFCore.NamingConventions` desteği A07'de çözüldü (27 Ekim 2026; [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §12); burada yeniden doğrulanmaz.
- Kararlar `/karar` ile, çözülen maddeler `/belge-esitle` ile işlenir.
- **Bitti sayılır:** her madde kaynak bağlantısıyla raporlu.

### A14.2 · İskelet, kimlik ve tohumlama
- Paketler `server/Directory.Packages.props` içine A14.0 tablosundaki sürümlerle eklenir. `Mutalaa.Api`: `Microsoft.AspNetCore.OpenApi`, `Microsoft.Extensions.ApiDescription.Server`, `Scalar.AspNetCore`, `Serilog.AspNetCore`, `Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore`. `Mutalaa.Api.Tests`: `Microsoft.AspNetCore.Mvc.Testing`. `Mutalaa.Domain` pakete bağımlı olmaz.
- `server/Mutalaa.Api/Program.cs` §3 iskeletini izler: varsayılan kültür `InvariantCulture`, Serilog, `Mutalaa:Features:Editor`, ProblemDetails, `DomainExceptionHandler`, OpenAPI (`OpenApiVersion = OpenApi3_1`), `/health/live` ve `/health/ready`, `Editor` ve `Admin` politikaları; yalnız `Development`'ta `/openapi/v1.json` ve `/scalar/v1`.
- `/health/ready` PostgreSQL denetimi hazır `AddDbContextCheck<IcerikDbContext>` ile (`ready` etiketiyle) yapılır; §3 iskeletindeki `DatabaseHealthCheck` sınıfı yazılmaz ve iskelet `/belge-esitle` ile bu çağrıya çevrilir.
- İz ve ölçü (OpenTelemetry) Teknoloji yığını §2.2'de A14'e yazılıdır ve Backend API §8'de tanımlıdır; paketler A14.0 tablosundadır, dışa aktarım yalnız `OTEL_EXPORTER_OTLP_ENDPOINT` verilirse açılır. Planda kullanıcıya sunulur; istenmezse A14 dışında kalır.
- Identity (`EditorUser`, roller `editor` ve `admin`, `kimlik` şeması, `seed`) A07'de hazırdır; yeni Identity göçü gerekmez. Bir göç gerekirse `ef-goc` becerisiyle eklenir ve SQL `dotnet ef migrations script --idempotent` ile gözden geçirilir.
- Çerez `HttpOnly`, `SameSite=Strict`, canlıda `Secure`; 8 saat kayan oturum (öneri). Parola kuralı (yalnız uzunluk >= 12) ve kilit (5 hatalı deneme, 15 dakika) A07'de `AddEditorIdentity` ile ayarlıdır.
- Giriş ucu kilit için yanlış parolayı `CheckPasswordSignInAsync(..., lockoutOnFailure: true)` üzerinden denetler (ya da `AccessFailedAsync` çağırır); başka bir parola denetimi sayacı artırmaz. Uç testi bunu kilitler: beşinci hatalı denemeden sonra doğru parola da reddedilir.
- `seed` A07'de teslim edildi ve idempotenttir; e-posta ve parola `Mutalaa:Seed:*` kullanıcı sırlarından okunur. `Mutalaa:Auth:DevAutoLogin` yalnız `Development` ortamında ve geri döngü isteğinde çalışır; başka ortamda açık bulunursa açılış hata verir.
- API `127.0.0.1:5080` adresine bağlanır; CORS kapalıdır.
- Uçlar: `POST /api/v1/auth/login`, `/auth/logout`; `GET /auth/me`; `GET`, `POST /api/v1/users`; `PUT /users/{id}/roles` (admin; kendi kendine kayıt yok).
- **Bitti sayılır:** `seed` iki kez çalışınca aynı sonuç; oturum ve kullanıcı uçlarının testleri yeşil.

### A14.3 · Kaynak ve birim uçları
- `GET /api/v1/sources`, `/sources/{slug}`: kaynak kaydının alanları (`slug`, `tur`, `baslik`, `yazar`, `surum`, `provider`, `kaynak_url`, `alinma_tarihi`, `dosya_sha256`, `baski_bilgisi`, `atif_metni`, `atif_url`, `notice_text`, `notlar`, `created_at`, `updated_at`) ve birim sayısı. Uçlar salt okunurdur: kaynak kaydını yazan uç yoktur; kayıt `pipeline/sources/{slug}.toml` dosyasından içerik hattıyla gelir. JSON alanları sütun adlarıyla aynıdır (snake_case); enum değerleri veritabanı etiketleridir.
- `GET /api/v1/units?source=&prefix=&q=&cursor=&limit=`: `q` A05'in C# normalizasyonundan geçer ve arama sütunlarında aranır; `prefix` çapa önekidir; imleçli sayfalama, en çok 200, yanıt `{ "items": [...], "next_cursor": "..." }`.
- `GET /units/{anchor}`: çapa `AnchorRef` ile doğrulanır; geçersizse 400 `capa-gecersiz`.
- `POST /units/{anchor}/corrections`: yalnız kendi ürettiğimiz metinde; önerilen metin NFC'ye çevrilir ve `review` satırı olur. Hazır kaynak metninde (Tanzil) 422 `degistirilemez-metin`. Hazır kaynak metni kaynak türüyle tanınır: `source.tur = 'kuran_metni'` (öneri; başka bir türü eklemek `/karar` ister).
- Not (EF sınırı, [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §12): `prefix` ve çapa aralığı sorguları dönüştürülmüş çapa sütunlarında LINQ ile `LIKE` ya da aralık işlecine çevrilmez; ham SQL ya da `AsNoTracking()` ile projeksiyon kullanılır. `unit` okumaları `tsv_tr` ve `tsv_ar` gölge sütunlarını da seçeceği için projeksiyon yapılır.
- **Bitti sayılır:** uç testleri yeşil; kaynak uçlarında `GET` dışındaki yöntemler 405 dönüyor; Tanzil birimine düzeltme 422 dönüyor.

### A14.4 · İnceleme kuyrukları ve ikinci onay
- `GET /api/v1/reviews?hedef_tablo=&alan=&durum=acik&cursor=`, `GET /reviews/{id}` (`onceki`, `onerilen`, kanıt, `yz_modeli`, `guven`), `GET /reviews/stats` (kuyruk başına açık kayıt).
- `POST /reviews/{id}/decision` (`{karar: onaylandi|reddedildi, onerilen?, gerekce}`) ve `POST /reviews/decisions` (toplu, en çok 100). `If-Match` zorunludur; ETag `xmin`'dir; uyuşmazsa 412 `surum-uyusmazligi`.
- Onay `onerilen` değerini hedefe aynı işlemde uygular; ret hedefi değiştirmez. Kendi `status` alanı olan tablolarda onay `onayli`, ret `red` yazar. Birim metni onayında `metin_durumu = 'onayli'` olur.
- İkinci onay gereken alanlar: meal ve tefsir metni ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §8). İlk onay `inceleyen` alanını doldurur, kayıt `acik` kalır; farklı bir editörün onayı değeri uygular ve `ikinci_inceleyen` alanını doldurur. Aynı kişinin ikinci onayı reddedilir (hata kodu öneri: 409 `durum-gecisi-gecersiz`).
- `oneren` ve `inceleyen` alanlarına Identity kullanıcı adı yazılır. Kur'an metni için metin incelemesi açılmaz. `yz_modeli` dolu kayıt yanıtta "doğrulanmamış" olarak işaretlenir (K-25). `review` yanıtı `yz_kaydi` alanını da döndürür. `dogrulanmis` saklanmaz; hedefin onaylı durumundan türetilir ([Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §8 notu, K-37): `status` sütunu olan tabloda `status = 'onayli'`, `unit`'te `metin_durumu = 'onayli'`, durum sütunu olmayan hedefte `review.durum = 'onaylandi'`.
- OCR kuyruğu sayfa görseli ister. Backend API §4 bu ucu öneri olarak taşır: yalnız editör kipinde, yalnız `data/raw/{baskı}/` altından okuyan, salt okunur bir görsel ucu; yöntemi ve yolu henüz yoktur ve `/karar` ile belirlenir. Uç JSON yazmadığı için çerez yönlendirmesi kendiliğinden kapanmaz; `DisableCookieRedirect()` eklenir (A14.1). Karar verilmezse A15'in OCR ekranı görselsiz kalır ve konu A16'dan önce kapanır.
- **Bitti sayılır:** karar, toplu karar ve ikinci onay testleri yeşil.

### A14.5 · Yayın uçları
- `POST /api/v1/releases` (admin): `{derleme, paketler?, notlar}` → 202, `Location`, `durum: hazirlaniyor` (`not` PostgreSQL'de ayrılmış sözcük olduğu için alan `notlar`dır; [K-46](../../00-ozet/02-karar-defteri.md#k-46--yayın-kaydı-içerik-özetleri-ve-fikstürler) madde 2). Kayıt `talep = yayin`, `paketler` ve `notlar` ile açılır. Sürüm istekte yoktur: `ReleaseVersion.Next` (Domain, A13) atar. Aynı derleme türünde `hazirlaniyor` kayıt varken 409 `yayin-suruyor`.
- `GET /releases?derleme=`, `/releases/{id}`: durum, kapı raporu, manifest.
- `POST /releases/preview` (admin): paket üretmeden kapı raporu; A13'te yazılan kalite kapısını (`Mutalaa.Domain/Releases`; P-01, P-07…P-14) çağırır. Kapıya takılan derleme 422 `kalite-kapisi` ve kapı raporuyla döner. A13 bitmediyse bu uç A13'ten sonraya kalır ve ilerleme dosyasına yazılır.
- `POST /releases/{id}/promote`, `/rollback` (admin): işi Yayınlayıcı `watch` yapar; `public` terfisi yalnız kullanıcı kararıyla çalışır (Backend API §10.6). Talep `release` kaydında taşınır ([K-46](../../00-ozet/02-karar-defteri.md#k-46--yayın-kaydı-içerik-özetleri-ve-fikstürler) madde 2): yeni satır `talep = terfi` ya da `geri_alma` ve `kaynak_release_id` (terfide `yayinlandi` durumundaki `internal` yayın, geri almada hedef yayın) taşır; `watch` talebe göre `promote` ya da `rollback` yürütür. Alanlar A13'te eklenir (EF göçü); A14 yalnız satırı açar.
- **Bitti sayılır:** 202, 409 ve yetki testleri yeşil.

### A14.6 · Hata modeli, OpenAPI ve testler
- ProblemDetails: `type` = `urn:mutalaa:problem:<kod>`, gövde `traceId` taşır; [Backend API](../../02-mimari/05-backend-api.md) §6 tablosundaki kodlar ve HTTP durumları. Girdi doğrulaması 400 `HttpValidationProblemDetails` döner.
- OpenAPI belgesi derlemede `server/Mutalaa.Api/openapi/v1.json` dosyasına üretilir (OpenAPI 3.1) ve depoya girer. Belge üretimi uygulamayı başlattığı için açılış kodu veritabanına bağlanmaz.
- Testler (`WebApplicationFactory` ve Testcontainers `postgres:18`): her uçta anonim, `editor` ve `admin` için yetki matrisi; ikinci onay (aynı kişi ve farklı kişi); 412; toplu karar sınırı; 422 Tanzil; 409 yayın; kaynak uçlarında yazma yöntemi 405; oturumsuz JSON ucu ve oturumsuz görsel ucu 401; `DevAutoLogin` `Development` dışında açılışı durduruyor; JSON alanları snake_case. Domain testleri `tr-TR` kültüründe de koşar.
- Test verisi sentetiktir ("Deneme paragrafı 1 …" gibi); Kur'an, meal ya da hadis metni testte hafızadan yazılmaz. Tanzil davranışı `source.tur = 'kuran_metni'` olan sentetik kaynakla sınanır.
- **Bitti sayılır:** `dotnet test` yeşil; belge üretiminden sonra `git diff` boş.

## Kabul ölçütleri
- [ ] Tedarik tablosundaki her kitaplığın sürümü NuGet kaydında doğrulanmış ve `server/Directory.Packages.props` ile aynı (`dotnet list server/Mutalaa.slnx package`); açılmayan adres yerine yedek aday yazılmış.
- [ ] `dotnet build`, `dotnet test` ve `dotnet format --verify-no-changes` yeşil.
- [ ] Yetki matrisi testi §4 tablosundaki her uç için anonim, `editor` ve `admin` sonucunu doğruluyor.
- [ ] Kaynak uçları salt okunur: `GET` dışındaki yöntemler 405 dönüyor (test).
- [ ] İkinci onay: aynı editörün ikinci onayı reddediliyor; farklı editörün onayı değeri uyguluyor ve `ikinci_inceleyen` alanını dolduruyor (test).
- [ ] Eski ETag ile karar 412, Tanzil düzeltmesi 422, süren yayın 409 dönüyor (test).
- [ ] `server/Mutalaa.Api/openapi/v1.json` güncel; `git diff --exit-code server/Mutalaa.Api/openapi` 0.
- [ ] Yerelde `/health/ready` başarılı; oturumsuz `GET /api/v1/sources` ve oturumsuz görsel isteği 401 ProblemDetails dönüyor (yönlendirme değil).
- [ ] `seed` (A07'de teslim edildi) idempotent; `DevAutoLogin` yalnız `Development` ve geri döngüde çalışıyor.
- [ ] Giriş ucunda yanlış parola `CheckPasswordSignInAsync(..., lockoutOnFailure: true)` üzerinden gidiyor; beşinci hatalı denemeden sonra doğru parola da reddediliyor (uç testi).
- [ ] Görsel ucu kararı karar defterinde ya da açık soru olarak ilerleme notunda; terfi/geri alma talebi K-46'da karara bağlandı (uygulama A14'te).

## Doğrulama
```bash
dotnet build server/Mutalaa.slnx
dotnet list server/Mutalaa.slnx package
dotnet test --solution server/Mutalaa.slnx
dotnet format server/Mutalaa.slnx --verify-no-changes
docker compose up -d
dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
dotnet run --project server/Mutalaa.Api -- seed
git diff --exit-code server/Mutalaa.Api/openapi
curl -s http://localhost:5080/health/ready
curl -si http://localhost:5080/api/v1/sources
```
Son iki komut API ayrı bir terminalde `dotnet watch --project server/Mutalaa.Api` ile çalışırken koşar. `ASPNETCORE_ENVIRONMENT=Development` gerekir ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §6). `dotnet list … package` çıktısı Tedarik tablosundaki sürümleri göstermelidir; son komut ilk satırda `401` ve `application/problem+json` verir.

## Dikkat
- Çerez kimlik doğrulaması .NET 10'da JSON okuyan ya da yazan Minimal API uçlarında yönlendirme yerine 401 ve 403 döner; JSON yazmayan uçlar (sayfa görseli) için `DisableCookieRedirect()` gerekir. API'de 401 ve 403 ProblemDetails dönecek biçimde yapılandırılır ve testle kanıtlanır.
- Kültür: CA1304, CA1305, CA1307, CA1309, CA1310 ve CA1311 hata düzeyindedir; Türkçe küçük harf açık eşlemeyle yapılır ([Backend API](../../02-mimari/05-backend-api.md) §9).
- API açılışında otomatik göç yoktur. Her değişiklik en çok bir göç ekler; uygulanmış göç değiştirilmez (`ef-goc`).
- Hazır kaynak metni (Tanzil) hiçbir uçta değişmez; NFC yalnız kendi ürettiğimiz metne ilk kayıtta uygulanır.
- `review.hedef_tablo` denetim listesi Editoryal veritabanı §8'de zaten `quran_word_fix`, `tr_root_index`, `tr_form` ve `surah_alias` değerlerini taşır; Backend API §4.1'deki açık soru "Çözüldü (19 Ekim 2026)" olarak işaretlidir.
- Gizli değerler `dotnet user-secrets` ile verilir; `appsettings*.json` içine parola yazılmaz. Günlüğe parola, belirteç ve çerez yazılmaz.
- Editör paneli dışarı açılmaz; açılırsa HTTPS, antiforgery ve iki adımlı doğrulama gerekir (§6).
- A08'den devir (CI): OpenAPI belgesi (`server/Mutalaa.Api/openapi/v1.json`) `dotnet build -c Release` içinde üretilmelidir. `ci-dotnet.yml` derlemeyi Release ile yapar ve belge varsa `git diff --exit-code server/Mutalaa.Api/openapi` ile farkı arar; belge başka bir yapılandırmada ya da ayrı komutla üretilirse CI farkı göremez. Belge ilk eklendiği PR'da bu adımın çalıştığı Actions'ta görülür ([Proje yapısı §7](../../02-mimari/03-proje-yapisi.md#7-ci-iş-akışları-github-actions)).

## İnsan adımları
- Yok. İlk yönetici e-posta ve parolasını Claude Code `dotnet user-secrets` ile verir (CLAUDE.md kural 11: onay sorulmaz); değerler sohbete, rapora ve commit'e yazılmaz. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `server/Mutalaa.Api/Program.cs`, `Endpoints/*`, `Problems/*`, `openapi/v1.json`
- `server/Directory.Packages.props` içinde sabitlenmiş A14 paket sürümleri (Tedarik tablosuyla aynı)
- İnceleme ve ikinci onay kuralları (`Mutalaa.Domain/Reviews`); Identity (`server/Mutalaa.Infrastructure/Identity/*`) A07'den gelir
- Api test projesinde yetki matrisi ve akış testleri
- Karar defterinde doğrulama sonuçları ve görsel ucu kayıtları (terfi/geri alma talebi K-46'dadır)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A14-api-editor-uclari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A13](./A13-yayinlayici-ve-kalite-kapisi.md) · Sonraki: [A15](./A15-editor-paneli.md)
