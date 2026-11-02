---
paths:
  - "server/**"
---

# .NET çözümü kuralları (`server/`)

Kaynak: [Backend API](../../docs/02-mimari/05-backend-api.md), [Editoryal veritabanı](../../docs/03-veri/02-editoryal-veritabani.md), [Yayın süreci](../../docs/07-yayin/01-yayin-sureci.md).

- **Bağımlılık.** `Mutalaa.Domain` başka projeye ve altyapı paketine (EF Core, Npgsql, AWS) bağlanmaz. `Mutalaa.Api` ile `Mutalaa.Publisher` birbirine bağlanmaz. NuGet sürümleri yalnız `Directory.Packages.props` içindedir.
- **Kültür.** Uygulama açılışta varsayılan kültürü `InvariantCulture` yapar. CA1304, CA1305, CA1307, CA1309, CA1310 ve CA1311 hata düzeyindedir. Karşılaştırmada `StringComparison.Ordinal`, sayı ve tarihte `CultureInfo.InvariantCulture`, düzenli ifadede `RegexOptions.CultureInvariant`. Domain testleri `tr-TR` kültüründe de geçer.
- **EF Core.** snake_case adlar, tekil tablo adları, `timestamptz` ve UTC, eşzamanlılık belirteci `xmin`. Her değişiklik en çok bir göç ekler; uygulanmış göç değiştirilmez (tek istisna: ilk göç K-42 kararıyla bir kez yeniden üretildi); SQL `dotnet ef migrations script --idempotent` ile gözden geçirilir. API açılışında otomatik göç yoktur. Ayrıntı: `ef-goc` becerisi.
- **Metin.** Âyet birimlerinin metni (`unit.kind = 'ayet'`, `q:` birimleri; Tanzil) değiştirilemez; düzeltme ucu 422 `degistirilemez-metin` döner. NFC yalnız kendi ürettiğimiz metne ilk kayıtta uygulanır.
- **API.** Editör uçları yalnız `127.0.0.1` adresine bağlanır. Hatalar RFC 9457 ProblemDetails ve dokümandaki kodlarla döner. JSON alan adları veritabanı sütunlarıyla aynıdır (snake_case). OpenAPI belgesi `server/Mutalaa.Api/openapi/v1.json` dosyasına üretilir ve güncel tutulur.
- **Yayınlayıcı.** Kapı kuralları P-01 ve P-07…P-14'tür; P-02…P-06 yoktur, numaralar yeniden verilmez. Her kuralın testi vardır. Kapı kaynak kaydına ve editoryal kaliteye bakar: kaynak kaydı olmayan içerik pakete girmez (P-01); insan onayı isteyen türün aday bağlantısı yalnız `dev` ve `internal`'a girer, otomatik türler güven eşiğiyle girer, `red` hiç girmez (P-07); onaysız birim ve onaysız yapay zekâ taslağı `public`'e girmez (P-08, P-10); `test-` önekli kaynak `public`'e girmez, `internal`'a yalnız uçtan uca fikstürler (`test-kucuk`, `test-ses`) girer (P-12). Derleme türü (`BuildFlavor`) `Mutalaa.Domain/Releases` altındadır. Manifest her derleme türünde imzalıdır. Ayrıntı: `paket-yayini` becerisi.
- **Gizli değerler** `dotnet user-secrets` ile verilir; `appsettings*.json` dosyalarına parola ya da anahtar yazılmaz.
- **Testler:** xUnit, `WebApplicationFactory`, Testcontainers ile `postgres:18`.
