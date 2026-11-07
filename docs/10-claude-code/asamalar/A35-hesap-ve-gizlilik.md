# A35 · Hesap ve gizlilik

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-20](../../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 4 · **Önkoşul:** [A34](./A34-magaza-yayini.md) · **İnsan adımı:** İ-20
> **Ajanlar:** `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` (A35.0 tedarik) · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `ef-goc` · `mobil-ekran` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A35`

## Amaç
Okur için isteğe bağlı hesap kurulur: ASP.NET Core Identity ile e-posta ve parola, Google ile giriş ve onunla birlikte Apple ile Giriş, uygulama içinden hesap silme ve veri dökümü. Gizlilik tasarımının kod tarafı (en az veri, gizlilik metni, günlük kuralları, silme akışı) ve belge tarafı (veri işleyenler, saklama süreleri, mağaza beyanları) hazırlanır; uygulama hesapsız tam çalışmayı sürdürür. Aşama yerelde ve `dev` derlemesinde biter. Canlıya açılış barındırma seçimine (İ-20) bağlıdır; yalnız bu alt adım onu bekler ve senkronla birlikte A36'nın son adımında, bu aşamanın hazırladığı listeyle yapılır.

## Okunacak belgeler
- [Backend API](../../02-mimari/05-backend-api.md): §1 çalışma kipleri, §3 `Program.cs`, §5 v1.x uçları, §6 kimlik doğrulama ve hata modeli, §7 EF Core, §8 günlük, §9 kültür
- [Gizlilik](../../07-yayin/02-gizlilik.md): §3 tamamı, §4 "Faz 4 öncesi" listesi, §5 açık sorular · [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §7.2 mağaza formları ve gizlilik sayfası
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §2 ortak sütunlar ve `device_id`, §6 yedek biçimi, §8 "Gizlilik" maddesi
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §6.3, §7 ortamlar, §10, §11 soru 3 · [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): kimlik satırı ve NuGet sürüm tablosu
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10 bayraklar, §12 Sentry · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 rota ağacı, §6 ayarlar
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §7 `xref_vote`

## Kapsam
**Yapılır**
- Genel kipte (`Mutalaa:Features:Public=true`) Backend API §5'teki hesap uçları: kayıt, giriş, yenileme, çıkış, e-posta onayı, parola sıfırlama, Google ve Apple ile giriş, hesap silme, veri dökümü.
- Okur kimlik verisinin editoryal veritabanından ayrı tutulması kararı ve şeması.
- Mobilde Hesabım ekranı, giriş akışları, gizlilik metni, "Hesabımı sil"; `hesapVeSenkron` bayrağı yalnız `dev`.
- Gizlilik metni (v1.x), veri işleyenler listesi, mağaza beyanları ve canlıya açılış listesi.

**Yapılmaz**
- Senkron uçları, `kullanici` şemasındaki senkron tabloları ve istemci senkronu (A36). Canlıya açılış (A36 son adımı).
- Bağlantı oyu (`PUT`, `DELETE /api/v1/xrefs/{id}/vote`): [A36](./A36-senkron.md) A36.6. Silme akışı oy tablosu varsa oyları da kapsar.
- Web'de hesap (A38'in dışında; Faz 5'te istenirse ayrı plan). Uçtan uca şifreli notlar (ertelenmiş seçenek, Gizlilik §3.5).

## Tedarik
Araştırma tarihi 2 Kasım 2026; A35.0'da yenilenir. Bu aşama içerik dosyası almaz: hazır kitaplıkları, çatının yerleşik uçlarını ve mağaza kuralı sayfalarını kullanır. Hesaplar (e-posta sağlayıcısı, Apple Developer, Google Cloud) altyapıdır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Okur kimliği çekirdeği: kayıt, giriş, yenileme, e-posta onayı, parola sıfırlama | `Microsoft.AspNetCore.Identity.EntityFrameworkCore` 10.0.14 (NuGet, 25 Ekim 2026; `dotnet/dotnet` @0427b9ab; net10.0; A07'de eklenmiş) ve çatıdaki `MapIdentityApi<TUser>` | Yeni paket yok; `AddIdentityApiEndpoints<ReaderUser>()` ve `MapGroup("/api/v1/account").MapIdentityApi<ReaderUser>()` | `IdentityApiEndpointRouteBuilderExtensions.cs` (`dotnet/aspnetcore` @v10.0.14): `/register`, `/login`, `/refresh`, `/confirmEmail`, `/resendConfirmationEmail`, `/forgotPassword`, `/resetPassword`, `/manage/2fa`, `/manage/info` (dokuz yol); `logout` yok; yenileme ucu `ValidateSecurityStampAsync` çağırır; `IEmailSender<TUser>` DI'dan istenir. Learn "How to use Identity to secure a Web API backend for SPAs" (güncelleme 26 Ekim 2026): taşıyıcı ve yenileme belirteci | `UserManager` ve `SignInManager` ile kendi uçlarımız |
| Hız sınırı | .NET 10 çatısında yerleşik hız sınırı ara katmanı: `AddRateLimiter`, `UseRateLimiter`, `RateLimitPartition.GetFixedWindowLimiter` (bölüm anahtarı IP ya da hesap) | Yeni paket yok | Learn "Rate limiting middleware in ASP.NET Core" (güncelleme 27 Ekim 2026): IP ve kullanıcı bölümlü örnekler, `OnRejected` ile 429 ve `Retry-After`. NuGet'teki `Microsoft.AspNetCore.RateLimiting` paketinin kararlı sürümü yok (yalnız 7.0.0-rc.2); gerekmez | Yok (yerleşik) |
| Google ve Apple `id_token` doğrulaması | `Microsoft.IdentityModel.Protocols.OpenIdConnect` 8.23.0 ve `Microsoft.IdentityModel.JsonWebTokens` 8.23.0 (NuGet, 18 Eylül 2026; `AzureAD/azure-activedirectory-identitymodel-extensions-for-dotnet` @8b16f418; net10.0 dahil): `ConfigurationManager<OpenIdConnectConfiguration>` ile anahtar keşfi, `JsonWebTokenHandler.ValidateTokenAsync` ile imza, `iss`, `aud`, `exp` denetimi; tek doğrulayıcı iki sağlayıcıya yeter | `dotnet add package` (sürüm `server/Directory.Packages.props` içinde) | Adresler 2 Kasım 2026'da 200 döndü: Apple `https://appleid.apple.com/auth/keys` (3 RS256 anahtar) ve `https://appleid.apple.com/.well-known/openid-configuration`; Google `https://accounts.google.com/.well-known/openid-configuration` ve `https://www.googleapis.com/oauth2/v3/certs`. Google kuralı (güncelleme 22 Aralık 2025): `aud` istemci kimliklerinden biri, `iss` `accounts.google.com` ya da `https://accounts.google.com`, `exp` geçmemiş. Apple adımları A35.0'da Apple belgesinden okunur | Google için `Google.Apis.Auth` 1.78.0 (NuGet, 30 Ekim 2026; `googleapis/google-api-dotnet-client` v1.78.0 @e14fc8a0; `GoogleJsonWebSignature.ValidateAsync`; kaynakta `nonce` alanı geçmez, ayrıca okunur). Apple için `AspNet.Security.OAuth.Apple` 10.0.0 (NuGet, 11 Kasım 2025; web akışı) |
| E-posta gönderimi: parola sıfırlama, e-posta onayı, silme onayı | `MailKit` 4.18.2 ve `MimeKit` 4.18.2 (NuGet, 23 ve 21 Ekim 2026; `jstedfast/MailKit`; net10.0 hedefli) ile `IEmailSender<ReaderUser>`. Gönderim sağlayıcısı Resend SMTP: ana makine `smtp.resend.com`, bağlantı noktaları 465 ve 587, kullanıcı adı `resend`, parola API anahtarı (hesap: altyapı) | `dotnet add package MailKit`; Resend hesabını ve gönderen alanı kaydını hesap sahibi açar (İ-15, İ-18); anahtar `dotnet user-secrets` içinde | Resend fiyat ve SMTP sayfaları (2 Kasım 2026): ücretsiz plan 0 USD, ayda 3.000 ve günde 100 e-posta, 3 alan adı; Pro 20 USD/ay, 50.000 e-posta. Tahmini maliyet: parola sıfırlama, e-posta onayı ve silme onayı iletileri ücretsiz sınırın içinde kalır; aşılırsa Pro 20 USD/ay | Brevo ücretsiz plan (günde 300 e-posta; fiyat sayfası 2 Kasım 2026; SMTP ana makinesi A35.0'da ölçülür). Resend .NET SDK `Resend` 0.24.0 (NuGet, 16 Ekim 2026; `resend/resend-dotnet` v0.24.0 @5d237b56) |
| Yerel e-posta denemesi (SMTP sınama sunucusu) | Mailpit v1.33.0: Docker Hub `axllent/mailpit:v1.33.0` (31 Ekim 2026; amd64, arm64, 386); GitHub `axllent/mailpit` etiketi v1.33.0 (HEAD 984165e8) | `infra/` altındaki Docker Compose dosyasına isteğe bağlı hizmet ya da testte Testcontainers genel kapsayıcısı | Docker Hub etiket kaydı; SMTP ve arayüz bağlantı noktaları A35.0'da ölçülür | Yok (birim testlerinde sahte `IEmailSender` yeter) |
| Mobil: Apple ile Giriş | `expo-apple-authentication` ~58.0.2 (npm 58.0.2, 29 Eylül 2026; Expo SDK 58 `bundledNativeModules.json`; SDK 57 hattı için 57.0.2). Uygulama ayarı `ios.usesAppleSignIn: true` | `npx expo install expo-apple-authentication` (geliştirme derlemesi gerekir) | Expo belgesi `apple-authentication.mdx` (`usesAppleSignIn` ayarı); `AppleAuthentication.types.ts` içinde `nonce?: string` seçeneği | Android'de Apple ile Giriş gerekirse (A35.1 kararı) web akışı: `expo-auth-session` ~58.0.16 ve `expo-web-browser` ~58.0.7 ile `AspNet.Security.OAuth.Apple` 10.0.0 |
| Mobil: Google ile giriş | `react-native-nitro-google-signin` 2.3.1 (npm, 31 Ekim 2026; GitHub `react-native-nitro-google-sign-in/google-signin` etiket v2.3.1, HEAD 892f6532): Android Credential Manager, iOS Google Sign-In SDK, Expo yapılandırma eklentisi (`app.plugin.js`). Eşler: `expo` >=49, `react-native` >=0.76, `react-native-nitro-modules` >=0.36.0 (npm 0.37.1, 27 Ağustos 2026) | `npx expo install react-native-nitro-google-signin react-native-nitro-modules`; geliştirme derlemesi gerekir (Expo Go'da çalışmaz) | Expo rehberi (`guides/google-authentication.mdx`) iki kitaplığı sayar ve Credential Manager'ın nitro'da bulunduğunu yazar; npm paketi (190 dosya) `nonce?: string \| null` seçeneğini taşır (SHA-256 hex; boşsa kendisi üretir); haftalık indirme 145.108 | `@react-native-google-signin/google-signin` 17.0.0 (npm, 29 Ekim 2026; haftalık 1.613.041): ücretsiz sürüm Android'de Google'ın kullanımdan kaldırılmış eski Google Sign-In SDK'sını kullanır; Credential Manager yalnız ücretli teklifinde olduğundan seçilmez |
| Mobil: güvenli belirteç deposu, nonce üretimi | `expo-secure-store` ~58.0.2 (npm 58.0.2, 1 Ekim 2026; SDK 57 hattı için 57.0.4) ve `expo-crypto` ~58.0.7 (npm 58.0.7, 16 Ekim 2026; SDK 57 hattı için 57.0.4) | `npx expo install expo-secure-store expo-crypto` | `expo/expo` `sdk-58` dalındaki `bundledNativeModules.json` iki paketi de ~58.x verir | Yok (belirteç MMKV'ye yazılmaz) |
| Apple belirteç iptali (hesap silme) | Sign in with Apple REST API (`POST https://appleid.apple.com/auth/token` ve `https://appleid.apple.com/auth/revoke`); istemci sırrı ES256 imzalı JWT, `Microsoft.IdentityModel.JsonWebTokens` 8.23.0 ile üretilir | Yeni paket yok; `HttpClient`. `.p8` anahtarını hesap sahibi üretir (İ-15) | Apple haberi `https://developer.apple.com/news/?id=12m75xbj` (24 Mayıs 2022): Apple ile Giriş sunan uygulama hesabı silerken kullanıcı belirteçlerini REST API ile iptal eder. Uç adresleri ve JWT alanları A35.0'da Apple belgesinden okunur | `Golap.AppleAuth` 2.1.0 (NuGet; eski bağımlılıklar: `System.IdentityModel.Tokens.Jwt` 6.7.1; seçilmedi) |
| Mağaza kuralları: Apple ile Giriş ve uygulama içi hesap silme | Apple App Store Review Guidelines, `https://developer.apple.com/app-store/review/guidelines/` ("Last Updated: October 16, 2026"): 4.8 Login Services, 5.1.1(v). Google Play "Understanding Google Play's app account deletion requirements", `https://support.google.com/googleplay/android-developer/answer/13327111` | Sayfalar `arastirmaci` ile okunur (indirme yok) | 2 Kasım 2026'da okundu. 4.8: üçüncü taraf girişi sunan uygulama, veri toplamayı ad ve e-postayla sınırlayan, e-postayı gizli tutmaya izin veren ve reklam için etkileşim toplamayan eşdeğer bir giriş hizmetini de sunar (yalnız kendi hesap sistemini kullanan uygulama hariç). 5.1.1(v): hesap açılıyorsa uygulama içinden silme. Google Play: uygulama içi silme yolu ve silme isteği için web bağlantısı | Yok |
| Test altyapısı | `Microsoft.AspNetCore.Mvc.Testing`, `Testcontainers.PostgreSql`, `xunit.v3` (A07 ve A14'te kayıtlı sürümler); Maestro (A33) | `server/Directory.Packages.props` (eklenmiş) | [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) sürüm tablosu | Yok |

Kendimiz yapacağımız işler: okur kullanıcı tipi (`ReaderUser`), ayrı `DbContext`, şema ve göçler; `logout`, `external/google`, `external/apple`, `DELETE /account` ve `GET /account/export` uçları; OpenID doğrulayıcısını saran sınıf (sağlayıcı yapılandırması, `nonce` karşılaştırması, `user_logins` eşlemesi); `IEmailSender<ReaderUser>` uygulaması (MailKit); kalıcı silme işi (yerleşik `BackgroundService` ve `PeriodicTimer`) ve Apple belirteç iptali çağrısı; silme testi (`information_schema`); Hesabım ekranı, giriş akışları ve bayrak; gizlilik metni (v1.x), veri işleyenler listesi ve canlıya açılış listesi.

## Adımlar
### A35.0 · Tedarik doğrulaması ve indirme
- `arastirmaci`, `## Tedarik` tablosundaki her adresin açıldığını ve sürümlerin güncel olduğunu doğrular: NuGet kaydı (`https://api.nuget.org/v3-flatcontainer/<paket>/index.json`), npm kaydı (`https://registry.npmjs.org/<paket>/latest`) ve projenin SDK dalındaki `bundledNativeModules.json`, GitHub için `git ls-remote` (etiket ve commit), Apple ve Google anahtar uçları (`curl -sIL`), Resend fiyat ve SMTP sayfaları, Apple ve Google Play kural sayfaları (sayfa tarihleriyle). Açılmayan ya da sürümü değişen adresin yerine yedek aday kullanılır; değişiklik tabloya yazılır. Apple'ın kimlik belirteci doğrulama adımları (imza, `iss`, `aud`, `exp`, `nonce`) ve belirteç iptali Apple belgesinden okunup kayda geçer.
- Bu aşama içerik dosyası almaz: `data/gelen/` altına indirme ve `pipeline/sources/` kaydı gerekmez. Kitaplık sürümleri paket kaydından doğrulanır ve `server/Directory.Packages.props` ile `pnpm-lock.yaml` içinde sabitlenir; Expo'ya bağlı paketler `npx expo install` ile eklenir (sürüm uyumu SDK'dan gelir).
- Hesaplar altyapıdır ve hesap sahibi tarafından açılır: e-posta sağlayıcısı, Apple Developer (Sign in with Apple yeteneği ve `.p8` anahtarı) ve Google Cloud (OAuth istemcileri) (İ-15). Anahtarlar `dotnet user-secrets` ve EAS ortamında durur; depoya, sohbete ve rapora yazılmaz.
- **Bitti sayılır:** tablodaki her adres açıldı ve sürümler tabloyla uyumlu (fark varsa tablo güncel); paketler kilit dosyalarında sabit; Apple ve Google Play kuralları tarih ve bağlantıyla aşama notunda.

### A35.1 · Platform kuralları ve kararlar
- `arastirmaci` resmî kaynaktan, tarihli ve bağlantılı rapor yazar (A35.0 tablosundaki sayfalarla):
  - App Store yönergesi 4.8: Google ile giriş sunulursa Apple ile Giriş de sunulur (Backend API §5 "Doğrulanacak" maddesi bu rapordan kapanır) ve Android'de Apple ile Giriş'in gerekip gerekmediği.
  - Hesap silme: App Store 5.1.1(v), Google Play kuralı ve Google Play'deki silme bağlantısı sayfası (Gizlilik §3.6 "Doğrulanacak"); Apple ile giriş yapılmış hesapta belirteç iptali.
  - Google ve Apple `id_token` doğrulamasının resmî yolu (imza anahtarları, `iss`, `aud`, `exp`, `nonce`) ve her sağlayıcıda `nonce` değerinin istemciden belirtece nasıl aktığı (Expo `signInAsync` ve nitro `nonce` seçeneği).
  - Seçilen Expo modüllerinin SDK uyumu; sürümler kilit dosyasına yazılır.
- `/karar` ile (proje sahibi karar verir): okur kimliği ve kullanıcı verisi için ayrı veritabanı (öneri; Genel mimari §11 soru 3) ve Identity tablolarının `kimlik` şemasında durması (öneri; Backend API §7); erişim ve yenileme belirteci süreleri (öneri); silme bekleme süresi ve güvenlik günlüğü saklama süresi (Gizlilik §5 soru 2); e-posta gönderim sağlayıcısı (Tedarik önerisi Resend); `MapIdentityApi` uçlarından açık kalacaklar (öneri: `/manage/2fa` kapalı).
- **Bitti sayılır:** rapor ve kararlar kayıtlı; açık kalan soru yalnız barındırmaya bağlıysa İ-20'ye bağlanmış.

### A35.2 · Sunucu: Identity ve hesap uçları
- `sunucu-gelistirici` + `ef-goc`: okur kullanıcı tipi (öneri ad `ReaderUser`; editörün `EditorUser` tipiyle karışmaz), A35.1 kararındaki `DbContext` ve göçleri; her değişiklik en çok bir göç.
- Uçlar hazır `MapIdentityApi<ReaderUser>()` ile `/api/v1/account` grubunda açılır (Backend API §5): kayıt, giriş, yenileme, e-posta onayı, parola sıfırlama; taşıyıcı ve yenileme belirteci Identity'nin kendi belirteçleridir. `IEmailSender<ReaderUser>` MailKit ile yazılır. Eklenenler: `POST /logout` (güvenlik damgasını yeniler; yenileme ucu bu damgayı doğruladığı için bütün oturumlar düşer), `POST /external/google` ve `POST /external/apple` (gövde `{id_token, nonce}`; sunucu imzayı, `iss`, `aud`, `exp` ve `nonce` değerini Tedarik'teki OpenID doğrulayıcısıyla denetler; kullanıcı `user_logins` tablosunda sağlayıcı ve `sub` ile eşlenir), `DELETE` ve `GET /export` (A35.3). Hatalar RFC 9457 ProblemDetails ve §6 kodlarıyla (`dogrulama`, `oturum-acilamadi`, `yetki-yok`).
- Genel kipte editör uçları hiç eşlenmez; yerleşik `AddRateLimiter` hesap ve IP başına çalışır (kayıt, giriş, parola sıfırlama ve dış giriş uçlarında sıkı; `OnRejected` 429 ve `Retry-After` döner; proxy arkasında istemci IP'si için `UseForwardedHeaders` barındırmaya göre ayarlanır); günlüğe parola, belirteç, çerez, not içeriği ve e-posta yazılmaz (Backend API §8).
- Toplanan veri yalnız Gizlilik §3.2 tablosundaki kadardır: e-posta ya da Apple/Google giriş kimliği, Identity parola özeti, güvenlik günlüğü (IP, zaman, olay). Ad, telefon, doğum tarihi istenmez.
- Testler (`WebApplicationFactory`, Testcontainers `postgres:18`): kayıt, giriş, yenileme, çıkış; yanlış imza, yanlış `aud`, yanlış `nonce` için 401; hız sınırında 429; genel kipte editör uçları 404; giriş sırasında yakalanan günlükte e-posta ve parola geçmiyor. Dış sağlayıcı testleri test anahtarıyla, ağsız çalışır (test RSA anahtarı ve sahte yapılandırma yöneticisi). E-posta gönderimi birim testinde sahte `IEmailSender` ile, MailKit yolu Mailpit kapsayıcısıyla (Testcontainers) denenir.
- OpenAPI belgesi yeniden üretilir.
- **Bitti sayılır:** `dotnet test` yeşil, yukarıdaki testler raporda adıyla; `git diff --exit-code server/Mutalaa.Api/openapi` temiz.

### A35.3 · Hesap silme ve veri dökümü
- `DELETE /api/v1/account` kimliğin yeniden doğrulanmasını ister, hesabı silme işaretiyle kapatır, oturumları ve yenileme belirteçlerini düşürür; bekleme süresi yapılandırmadan okunur (A35.1). Süre dolunca kalıcı silme işi (yerleşik `BackgroundService` ve `PeriodicTimer`) kullanıcının bütün satırlarını, yumuşak silinmiş satırları, değişiklik akışı kayıtlarını, oturumları ve varsa `xref_vote` oylarını (`account_hash` ile) siler; kullanıcıya onay e-postası gider ([Gizlilik](../../07-yayin/02-gizlilik.md) §3.6).
- Apple ile giriş yapılmış hesapta silme sırasında istemci Apple ile yeniden doğrulanır; sunucu gelen `authorizationCode` değerini belirtece çevirip Apple REST API ile iptal eder (istemci sırrı ES256 imzalı JWT; `.p8` anahtarı kullanıcı sırlarında). Apple belirteci sunucuda saklanmaz (öneri; A35.1 raporuyla doğrulanır). Çağrı testte sahte HTTP işleyicisiyle sınanır.
- Silme testi şemadaki tabloları `information_schema.tables` ile listeler ve her tabloda kullanıcı satırı kalmadığını doğrular; A36'nın ekleyeceği tablolar böylece kendiliğinden kapsanır.
- `GET /api/v1/account/export` v1 yedek biçimini (`"format": "mutalaa-yedek"`, [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md) §6) sunucudaki hesap kayıtlarıyla döndürür; A36 senkron tablolarını aynı döküme ekler.
- **Bitti sayılır:** silme ve döküm testleri yeşil; döküm dosyası v1 içe aktarma koduyla açılıyor.

### A35.4 · Mobil: Hesabım, giriş, gizlilik metni, silme
- `mobil-gelistirici` + `mobil-ekran`: `app/(tabs)/ayarlar/hesap.tsx` (öneri; Mobil ekranlar §2 ve §6'ya `/belge-esitle` ile eklenir): durum, giriş yöntemleri, "Verilerimi dışa aktar", "Hesabımı sil".
- Hesap açma akışı gizlilik metnini (Gizlilik §3.8) hesap oluşmadan önce gösterir; Google ile giriş varsa Apple ile Giriş de vardır (A35.1 platform kuralıyla). Apple ile Giriş `expo-apple-authentication`, Google ile giriş `react-native-nitro-google-signin` ile yapılır; `nonce` değerini `expo-crypto` rastgele üretir, sağlayıcıya verilen biçim A35.1 raporunda yazılıdır ve sunucuya `{id_token, nonce}` gider. Hesap hiçbir akışta zorunlu değildir; tanıtımdaki "Hesap gerekmez" sözü geçerli kalır.
- Belirteçler `expo-secure-store` içinde durur; MMKV'ye, günlüğe ve Sentry olaylarına girmez.
- `src/lib/flags.ts`: `hesapVeSenkron` yalnız `dev` için açılır; `internal` ve `public` canlıya açılışa kadar kapalı.
- Maestro akışı `apps/mobile/e2e/hesap.yaml` yazılır: yerel API'ye karşı e-posta ve parolayla hesap aç, dışa aktar, hesabı sil.
- Geliştirme derlemesi, görsel denetim, Maestro koşusu ve Google ile Apple ile girişin gerçek test hesaplarıyla denenmesi kullanıcıya bırakılır ve aşamayı bekletmez (CLAUDE.md, çalışma düzeni 3). Geliştirme derlemesi (`eas build --profile development --platform android`) ücretlidir; kullanıcı onayı ve tahmini maliyet gerekir. Bakılacaklar (`mobil-ekran` listesi): Kâğıt, Âhar, Gece temaları ve %200 yazı boyutunda Hesabım ekranı, giriş akışları, silme onayı.
- **Bitti sayılır:** mobil birim testleri, tip denetimi ve lint yeşil; bayrak testi geçiyor; `arayuz-denetcisi` kod incelemesi temiz; Maestro akışı yazıldı; derleme, görsel denetim ve gerçek hesap denemeleri "kullanıcıya bırakıldı" diye ilerleme notunda yazılı.

### A35.5 · Gizlilik metni, mağaza beyanları ve canlıya açılış listesi
- Gizlilik metni (v1.x) Gizlilik §3.8'in altı başlığıyla `docs/07-yayin/gizlilik-metni-v1x.md` (öneri) dosyasına yazılır; uygulama içi metin i18n anahtarlarına, yayın sayfası alan adına (İ-18) bu dosyadan aktarılır.
- Veri işleyenler listesi (Gizlilik §3.4 tablosu) seçilen sağlayıcılarla güncellenir (e-posta: Resend; barındırma: İ-20 sonrası): her işleyenin adı, işlediği veri ve ülkesi tabloya ve gizlilik metnine yazılır. Saklama süreleri (güvenlik günlükleri, silme bekleme süresi, yedekler) A35.1 kararlarına göre Gizlilik §3.2, §3.6 ve §5'e işlenir (`/belge-esitle`).
- Mağaza beyanlarının (Gizlilik §2.6 tablosu) hesap verisiyle güncel hâli kayda yazılır: App Privacy ve Veri güvenliği formları, Veri güvenliği formundaki veri silme soruları ve Google Play'deki hesap silme bağlantısı sayfası dahil; formları hesap sahibi mağaza konsolunda doldurur (İ-15).
- Canlıya açılış listesi (A36.7'de kullanılır): barındırma kararı (İ-20), yalnız HTTPS, göç paketi (`dotnet ef migrations bundle`), canlıda `Mutalaa:Features:Public=true` ve `Editor=false`, sırların barındırma sırlarında olması, Data Protection anahtar halkasının kalıcı depoda tutulması (Identity belirteçleri bu anahtarlarla korunur), `/health/ready`, bayrakların açılma sırası (`internal`, sonra yeni uygulama sürümüyle `public`; A34 yordamı).
- Gizlilik §4 "Faz 4 öncesi" listesi ve canlıya açılış listesi `docs/07-yayin/surum-kayitlari/v1x-hesap.md` (öneri) dosyasında, her madde için kanıt alanıyla tutulur.
- **Bitti sayılır:** listedeki her madde kanıt ya da İ numarası taşıyor.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki her adres açıldı, sürümler paket kaydıyla doğrulandı ve kitaplıklar kilit dosyalarında sabit (A35.0).
- [ ] `dotnet test --solution server/Mutalaa.slnx` yeşil; hesap testleri (giriş, yenileme, çıkış, dış sağlayıcı ret durumları, 429, genel kipte editör uçları 404, günlükte e-posta ve parola yok) raporda adıyla.
- [ ] Silme testi `information_schema` ile listelenen her tabloda kullanıcı satırının 0 olduğunu doğruluyor.
- [ ] `git diff --exit-code server/Mutalaa.Api/openapi` temiz.
- [ ] Döküm dosyası `"format": "mutalaa-yedek"` taşıyor ve v1 içe aktarma testinde açılıyor.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; bayrak testi `hesapVeSenkron` değerini `internal` ve `public` için `false` buluyor.
- [ ] Maestro hesap akışı yazıldı; koşusu, ekran görüntüleri ve gerçek hesap denemeleri "kullanıcıya bırakıldı" diye ilerleme notunda yazılı; `arayuz-denetcisi` kod incelemesinde engelleyici bulgu yok.
- [ ] Gizlilik metni (v1.x) Gizlilik §3.8'in altı başlığını aynı sırayla taşıyor (`grep -n "^## "` çıktısıyla gözle).
- [ ] `arastirmaci` raporu Apple ile Giriş, hesap silme ve Apple belirteç iptali kurallarını tarih ve bağlantıyla veriyor.
- [ ] Gizlilik §4 "Faz 4 öncesi" listesinde kanıtsız madde yalnız İ numaralı.

## Doğrulama
```bash
dotnet test --solution server/Mutalaa.slnx
dotnet list server/Mutalaa.slnx package                        # yeni paket sürümleri Tedarik tablosuyla aynı
dotnet ef migrations script --idempotent --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api > .tmp/goc.sql
git diff --exit-code server/Mutalaa.Api/openapi
pnpm turbo run lint typecheck && pnpm --filter @mutalaa/mobile test
grep -n "^## " docs/07-yayin/gizlilik-metni-v1x.md
grep -n -- "- \[ \]" docs/07-yayin/surum-kayitlari/v1x-hesap.md | grep -v "İ-"   # boş
```
Cihaz komutları ve görüntüler kullanıcıya bırakılır (aşamayı bekletmez; kapanış raporunda "kullanıcıya bırakıldı" yazılır):
```bash
adb exec-out screencap -p > .tmp/hesap.png
maestro test apps/mobile/e2e/hesap.yaml          # akış klasörü A33'teki konumdur
```
Çözümde birden çok `DbContext` varsa göç komutlarında bağlam seçimi `ef-goc` becerisindeki biçimle yapılır. `eas build` ücretlidir; kullanıcı onayı ve tahmini maliyet ister.

## Dikkat
- Hesap isteğe bağlıdır (K-15); hesapsız okuma hiçbir ekranda engellenmez.
- Editör kimliği (çerez, yalnız `127.0.0.1`) ile okur kimliği (taşıyıcı belirteç, canlı sunucu) karışmaz; genel kipte editör uçları eşlenmez.
- `device_id` rastgele üretilir, donanım kimliği kullanılmaz (Gizlilik §3.2, öneri). Reklam kimliği, konum, kişiler toplanmaz.
- Kültürden bağımsızlık: e-posta ve kimlik karşılaştırmaları ordinal; testler `tr-TR` kültüründe de koşar (Backend API §9).
- Gizli değerler (bağlantı dizesi, istemci gizlileri, imza anahtarları, e-posta API anahtarı, Apple `.p8` anahtarı) yalnız kullanıcı sırlarında; Claude Code `.env` okumaz.
- Apple ve Google ile giriş kitaplıkları yerel kod ister: Expo Go'da çalışmaz, geliştirme derlemesi gerekir. Testcontainers Docker Desktop ister (İ-01).

## İnsan adımları
- İ-20 · Barındırma seçimi: Gizlilik §3.7 ölçütleriyle; canlıya açılıştan (A36.7) önce.
- İ-15 · Apple Developer (Sign in with Apple yeteneği, `.p8` anahtarı) ve Google (OAuth istemcileri) hesaplarında giriş istemcilerinin oluşturulması, e-posta sağlayıcısı hesabının açılması ve mağaza beyanlarının güncellenmesi: A35.0, A35.4 ve A35.5.
- İ-18 · Alan adı (gizlilik sayfası ve e-posta gönderen alanının DNS kaydı): A35.5.
- Google ve Apple ile girişin gerçek test hesaplarıyla elle denenmesi: A35.4.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `server/Mutalaa.Infrastructure/Identity/` (okur kimliği), yeni `DbContext` ve göçleri; `server/Mutalaa.Api/Endpoints/` hesap uçları; `openapi/v1.json`; `server/tests/` hesap testleri; `server/Directory.Packages.props` (yeni paket sürümleri)
- `apps/mobile/app/(tabs)/ayarlar/hesap.tsx`, `apps/mobile/src/features/settings/` hesap bileşenleri, `src/lib/flags.ts`, Maestro akışı; `pnpm-lock.yaml`
- `docs/07-yayin/gizlilik-metni-v1x.md` ve `docs/07-yayin/surum-kayitlari/v1x-hesap.md` (öneri), karar defteri girdileri
- `docs/07-yayin/02-gizlilik.md` ve `docs/01-urun/03-mobil-ekranlar.md` güncellemeleri (`/belge-esitle`)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A35-hesap-ve-gizlilik.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A34](./A34-magaza-yayini.md) · Sonraki: [A36](./A36-senkron.md)
