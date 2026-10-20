# A14 · API editör uçları

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** yok
> **Ajanlar:** `sunucu-gelistirici` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `ef-goc` · `lisans-kapisi` · `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A14`

## Amaç
Editör kipindeki ASP.NET Core 10 Minimal API kurulur: ASP.NET Core Identity ile oturum ve roller, kaynak ve birim uçları, tek `review` tablosu üzerinden inceleme kuyrukları ve ikinci onay, yayın talebi uçları, RFC 9457 hata modeli ve depoya giren OpenAPI belgesi. Editör paneli (A15) bu belgeden üretilen istemciyle çalışır; içerik hattının adayları bu uçlarla onaylanır.

## Okunacak belgeler
- [Backend API](../../02-mimari/05-backend-api.md): §1–§9 (tamamı)
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source`, §8 `review` ve inceleme akışı, §10 `release`, §12 EF Core notları
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §3 kullanıcı sırları, §6 adım 2–3 ve 5, §10.1 Türkçe yerel ayar
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §6.1 kaynaktan yayına akış
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 göç ve enum testleri

## Kapsam
**Yapılır**
- `Program.cs` iskeleti, Identity (`EditorUser`, `editor` ve `admin` rolleri), `seed` komutu, `DevAutoLogin`.
- [Backend API](../../02-mimari/05-backend-api.md) §4 tablosundaki bütün v1 uçları, §4.1 kuyrukları ve ikinci onay, §4.2 uç kuralları, §6 hata kodları.
- Derlemede üretilip depoya giren `server/Mutalaa.Api/openapi/v1.json`; sağlık uçları; Serilog.
- Uç başına yetki matrisi testleri.

**Yapılmaz**
- v1.x genel kip uçları: hesap, senkron, bağlantı oyu (A35, A36).
- Paket üretimi ve yükleme (A13); API yalnız `release` kaydı açar.
- Editör arayüzü (A15). Kuyruklara aday yazan hat işleri (A11, A16–A19).

## Adımlar
### A14.1 · Doğrulamalar
- `arastirmaci` resmî kaynaktan doğrular: .NET 10 Minimal API doğrulaması (`AddValidation()`); Npgsql EF Core 10 enum eşleme API'si; `xmin` eşzamanlılık belirteci yapılandırması (`IsRowVersion()`); derlemede OpenAPI belgesi üretimi (`Microsoft.Extensions.ApiDescription.Server`); `Scalar.AspNetCore` uç adı; `EFCore.NamingConventions` EF Core 10 desteği; çerez kimlik doğrulamasında API isteklerine yönlendirme yerine 401 ve 403 döndürmenin yolu. Bunlar Backend API §2, §3, §6, §7 ve Editoryal veritabanı §12'de "Doğrulanacak" diye işaretlidir.
- Kararlar `/karar` ile, çözülen maddeler `/belge-esitle` ile işlenir.
- **Bitti sayılır:** her madde kaynak bağlantısıyla raporlu.

### A14.2 · İskelet, kimlik ve tohumlama
- `server/Mutalaa.Api/Program.cs` §3 iskeletini izler: varsayılan kültür `InvariantCulture`, Serilog, `Mutalaa:Features:Editor`, ProblemDetails, `DomainExceptionHandler`, OpenAPI, `/health/live` ve `/health/ready`, `Editor` ve `Admin` politikaları; yalnız `Development`'ta `/openapi/v1.json` ve `/scalar/v1`.
- Identity: `EditorUser`, roller `editor` ve `admin`; tablolar `kimlik` şemasında (öneri). Göç `ef-goc` becerisiyle eklenir; SQL `dotnet ef migrations script --idempotent` ile gözden geçirilir.
- Çerez `HttpOnly`, `SameSite=Strict`, canlıda `Secure`. Parola en az 12 karakter, 5 hatalı denemede 15 dakika kilit, 8 saat kayan oturum (öneri).
- `seed` idempotenttir; e-posta ve parola `Mutalaa:Seed:*` kullanıcı sırlarından okunur. `Mutalaa:Auth:DevAutoLogin` yalnız `Development` ortamında ve geri döngü isteğinde çalışır; başka ortamda açık bulunursa açılış hata verir.
- API `127.0.0.1:5080` adresine bağlanır; CORS kapalıdır.
- Uçlar: `POST /api/v1/auth/login`, `/auth/logout`; `GET /auth/me`; `GET`, `POST /api/v1/users`; `PUT /users/{id}/roles` (admin; kendi kendine kayıt yok).
- **Bitti sayılır:** `seed` iki kez çalışınca aynı sonuç; oturum ve kullanıcı uçlarının testleri yeşil.

### A14.3 · Kaynak ve birim uçları
- `GET /api/v1/sources`, `/sources/{slug}`: lisans, Kurul alanları, `embed_ok`, `kisitlar`, birim sayısı. JSON alanları sütun adlarıyla aynıdır (snake_case); enum değerleri veritabanı etiketleridir.
- `PUT /sources/{slug}/license-status`, `/kurul-onay`, `/embed-ok` (admin): değeri doğrudan yazmaz, `review` satırı açar; farklı bir editörün ikinci onayıyla uygulanır.
- `GET /api/v1/units?source=&prefix=&q=&cursor=&limit=`: `q` A05'in C# normalizasyonundan geçer ve arama sütunlarında aranır; `prefix` çapa önekidir; imleçli sayfalama, en çok 200, yanıt `{ "items": [...], "next_cursor": "..." }`.
- `GET /units/{anchor}`: çapa `AnchorRef` ile doğrulanır; geçersizse 400 `capa-gecersiz`.
- `POST /units/{anchor}/corrections`: yalnız kendi ürettiğimiz metinde; önerilen metin NFC'ye çevrilir ve `review` satırı olur. Hazır kaynak metninde (Tanzil) 422 `degistirilemez-metin`. Hazır kaynak, `source.kisitlar.degistirme_yasak` alanıyla tanınır (öneri).
- **Bitti sayılır:** uç testleri yeşil; Tanzil birimine düzeltme 422 dönüyor.

### A14.4 · İnceleme kuyrukları ve ikinci onay
- `GET /api/v1/reviews?hedef_tablo=&alan=&durum=acik&cursor=`, `GET /reviews/{id}` (`onceki`, `onerilen`, kanıt, `yz_modeli`, `guven`), `GET /reviews/stats` (kuyruk başına açık kayıt).
- `POST /reviews/{id}/decision` (`{karar: onaylandi|reddedildi, onerilen?, gerekce}`) ve `POST /reviews/decisions` (toplu, en çok 100). `If-Match` zorunludur; ETag `xmin`'dir; uyuşmazsa 412 `surum-uyusmazligi`.
- Onay `onerilen` değerini hedefe aynı işlemde uygular; ret hedefi değiştirmez. Kendi `status` alanı olan tablolarda onay `onayli`, ret `red` yazar. Birim metni onayında `metin_durumu = 'onayli'` olur.
- İkinci onay gereken alanlar: meal ve tefsir metni, `license_status`, `kurul_onay`, `embed_ok`. İlk onay `inceleyen` alanını doldurur, kayıt `acik` kalır; farklı bir editörün onayı değeri uygular ve `ikinci_inceleyen` alanını doldurur. Aynı kişinin ikinci onayı reddedilir (hata kodu öneri: 409 `durum-gecisi-gecersiz`).
- `oneren` ve `inceleyen` alanlarına Identity kullanıcı adı yazılır. Kur'an metni için metin incelemesi açılmaz. `yz_modeli` dolu kayıt yanıtta "doğrulanmamış" olarak işaretlenir (K-25).
- OCR kuyruğu sayfa görseli ister. Backend API §4 bu ucu öneri olarak taşır: yalnız editör kipinde, yalnız `data/raw/{baskı}/` altından okuyan, salt okunur bir görsel ucu; yöntemi ve yolu henüz yoktur ve `/karar` ile belirlenir. Karar verilmezse A15'in OCR ekranı görselsiz kalır ve konu A16'dan önce kapanır.
- **Bitti sayılır:** karar, toplu karar ve ikinci onay testleri yeşil.

### A14.5 · Yayın uçları
- `POST /api/v1/releases` (admin): `{derleme, paketler?, not}` → 202, `Location`, `durum: hazirlaniyor`. Aynı derleme türünde `hazirlaniyor` kayıt varken 409 `yayin-suruyor`.
- `GET /releases?derleme=`, `/releases/{id}`: durum, kapı raporu, manifest.
- `POST /releases/preview` (admin): paket üretmeden kapı raporu; A13'teki `Mutalaa.Domain/Licensing` kapısını çağırır. A13 bitmediyse bu uç A13'ten sonraya kalır ve ilerleme dosyasına yazılır.
- `POST /releases/{id}/promote`, `/rollback` (admin): işi Yayınlayıcı `watch` yapar. Talebin `release` kaydında nasıl taşınacağı dokümanda yoktur; öneri planda sunulur ve `/karar` ile yazılır.
- **Bitti sayılır:** 202, 409 ve yetki testleri yeşil.

### A14.6 · Hata modeli, OpenAPI ve testler
- ProblemDetails: `type` = `urn:mutalaa:problem:<kod>`, gövde `traceId` taşır; [Backend API](../../02-mimari/05-backend-api.md) §6 tablosundaki kodlar ve HTTP durumları. Girdi doğrulaması 400 `HttpValidationProblemDetails` döner.
- OpenAPI belgesi derlemede `server/Mutalaa.Api/openapi/v1.json` dosyasına üretilir ve depoya girer. Belge üretimi uygulamayı başlattığı için açılış kodu veritabanına bağlanmaz.
- Testler (`WebApplicationFactory` ve Testcontainers `postgres:18`): her uçta anonim, `editor` ve `admin` için yetki matrisi; ikinci onay (aynı kişi ve farklı kişi); 412; toplu karar sınırı; 422 Tanzil; 409 yayın; `DevAutoLogin` `Development` dışında açılışı durduruyor; JSON alanları snake_case. Domain testleri `tr-TR` kültüründe de koşar.
- **Bitti sayılır:** `dotnet test` yeşil; belge üretiminden sonra `git diff` boş.

## Kabul ölçütleri
- [ ] `dotnet build`, `dotnet test` ve `dotnet format --verify-no-changes` yeşil.
- [ ] Yetki matrisi testi §4 tablosundaki her uç için anonim, `editor` ve `admin` sonucunu doğruluyor.
- [ ] İkinci onay: aynı editörün ikinci onayı reddediliyor; farklı editörün onayı değeri uyguluyor ve `ikinci_inceleyen` alanını dolduruyor (test).
- [ ] Eski ETag ile karar 412, Tanzil düzeltmesi 422, süren yayın 409 dönüyor (test).
- [ ] `server/Mutalaa.Api/openapi/v1.json` güncel; `git diff --exit-code server/Mutalaa.Api/openapi` 0.
- [ ] Yerelde `/health/ready` başarılı; oturumsuz `GET /api/v1/sources` 401 ProblemDetails dönüyor (yönlendirme değil).
- [ ] `seed` idempotent; `DevAutoLogin` yalnız `Development` ve geri döngüde çalışıyor.
- [ ] Görsel ucu ve terfi/geri alma talebi kararları karar defterinde ya da açık soru olarak ilerleme notunda.

## Doğrulama
```bash
dotnet build server/Mutalaa.slnx
dotnet test --solution server/Mutalaa.slnx
dotnet format server/Mutalaa.slnx --verify-no-changes
docker compose up -d
dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
dotnet run --project server/Mutalaa.Api -- seed
git diff --exit-code server/Mutalaa.Api/openapi
curl -s http://localhost:5080/health/ready
curl -s http://localhost:5080/api/v1/sources
```
Son iki komut API ayrı bir terminalde `dotnet watch --project server/Mutalaa.Api` ile çalışırken koşar. `ASPNETCORE_ENVIRONMENT=Development` gerekir ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §6).

## Dikkat
- Çerez kimlik doğrulaması varsayılan olarak giriş sayfasına yönlendirir; API'de 401 ve 403 ProblemDetails dönecek biçimde yapılandırılır.
- Kültür: CA1304, CA1305, CA1307, CA1309, CA1310 ve CA1311 hata düzeyindedir; Türkçe küçük harf açık eşlemeyle yapılır ([Backend API](../../02-mimari/05-backend-api.md) §9).
- API açılışında otomatik göç yoktur. Her değişiklik en çok bir göç ekler; uygulanmış göç değiştirilmez (`ef-goc`).
- Hazır kaynak metni (Tanzil) hiçbir uçta değişmez; NFC yalnız kendi ürettiğimiz metne ilk kayıtta uygulanır.
- `review.hedef_tablo` denetim listesi Editoryal veritabanı §8'de zaten `quran_word_fix`, `tr_root_index`, `tr_form` ve `surah_alias` değerlerini taşır; Backend API §4.1'deki açık soru "Çözüldü (19 Ekim 2026)" olarak işaretlidir.
- Gizli değerler `dotnet user-secrets` ile verilir; `appsettings*.json` içine parola yazılmaz. Günlüğe parola, belirteç ve çerez yazılmaz.
- Editör paneli dışarı açılmaz; açılırsa HTTPS, antiforgery ve iki adımlı doğrulama gerekir (§6).

## İnsan adımları
- Yok. İlk yönetici e-posta ve parolasını kullanıcı `dotnet user-secrets` ile verir (komut onay ister). Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `server/Mutalaa.Api/Program.cs`, `Endpoints/*`, `Problems/*`, `openapi/v1.json`
- `server/Mutalaa.Infrastructure/Identity/*` ve Identity göçü; inceleme ve ikinci onay kuralları (`Mutalaa.Domain/Review`)
- Api test projesinde yetki matrisi ve akış testleri
- Karar defterinde doğrulama sonuçları, görsel ucu ve terfi/geri alma talebi kayıtları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A14-api-editor-uclari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A13](./A13-yayinlayici-ve-yayin-kapisi.md) · Sonraki: [A15](./A15-editor-paneli.md)
