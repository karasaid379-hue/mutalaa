---
paths:
  - "server/**"
---

# .NET çözümü kuralları (`server/`)

Kaynak: [Backend API](../../docs/02-mimari/05-backend-api.md), [Editoryal veritabanı](../../docs/03-veri/02-editoryal-veritabani.md), [Yayın kapısı ve Kurul](../../docs/07-yayin/01-yayin-kapisi-ve-kurul.md).

- **Bağımlılık.** `Mutalaa.Domain` başka projeye ve altyapı paketine (EF Core, Npgsql, AWS) bağlanmaz. `Mutalaa.Api` ile `Mutalaa.Publisher` birbirine bağlanmaz. NuGet sürümleri yalnız `Directory.Packages.props` içindedir.
- **Kültür.** Uygulama açılışta varsayılan kültürü `InvariantCulture` yapar. CA1304, CA1305, CA1307, CA1309, CA1310 ve CA1311 hata düzeyindedir. Karşılaştırmada `StringComparison.Ordinal`, sayı ve tarihte `CultureInfo.InvariantCulture`, düzenli ifadede `RegexOptions.CultureInvariant`. Domain testleri `tr-TR` kültüründe de geçer.
- **EF Core.** snake_case adlar, tekil tablo adları, `timestamptz` ve UTC, eşzamanlılık belirteci `xmin`. Her değişiklik en çok bir göç ekler; uygulanmış göç değiştirilmez; SQL `dotnet ef migrations script --idempotent` ile gözden geçirilir. API açılışında otomatik göç yoktur. Ayrıntı: `ef-goc` becerisi.
- **Metin.** Hazır kaynak metni (Tanzil) değiştirilemez; düzeltme ucu 422 `degistirilemez-metin` döner. NFC yalnız kendi ürettiğimiz metne ilk kayıtta uygulanır.
- **API.** Editör uçları yalnız `127.0.0.1` adresine bağlanır. Hatalar RFC 9457 ProblemDetails ve dokümandaki kodlarla döner. JSON alan adları veritabanı sütunlarıyla aynıdır (snake_case). OpenAPI belgesi `server/Mutalaa.Api/openapi/v1.json` dosyasına üretilir ve güncel tutulur.
- **Yayınlayıcı.** Kapı kuralları P-01…P-14'tür; her kuralın testi vardır. Manifest her derleme türünde imzalıdır. Ayrıntı: `lisans-kapisi` ve `paket-yayini` becerileri.
- **Gizli değerler** `dotnet user-secrets` ile verilir; `appsettings*.json` dosyalarına parola ya da anahtar yazılmaz.
- **Testler:** xUnit, `WebApplicationFactory`, Testcontainers ile `postgres:18`.
