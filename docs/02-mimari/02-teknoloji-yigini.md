# Teknoloji yığını

> **Sürüm:** 1.11 · **Tarih:** 9 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json) · [K-46](../00-ozet/02-karar-defteri.md#k-46--yayın-kaydı-içerik-özetleri-ve-fikstürler) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-09](../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-11](../00-ozet/02-karar-defteri.md#k-11--veritabanı-postgresql-18) · [K-12](../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-13](../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-14](../00-ozet/02-karar-defteri.md#k-14--web) · [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses) · [K-29](../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-32](../00-ozet/02-karar-defteri.md#k-32--pnpm-kurulumu-sürüm-sabitleme-ve-düzen) · [K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform) · [K-34](../00-ozet/02-karar-defteri.md#k-34--typescript-tek-sürüm-60x) · [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) · [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme)

Bu dosya her katmanın teknolojisini, sürümünü, seçilme nedenini ve reddedilen seçenekleri listeler. Sürüm ve fiyatlar 16 Ekim 2026 araştırmasından gelir ([araştırma raporu](../09-kaynakca.md), araştırma notu 05). Kaynağı olmayan sürüm numaraları "Doğrulanacak" diye işaretlidir ve kurulum günü kilit dosyasına yazılır.

---

## 1. Katman tablosu

| Katman | Seçim ve sürüm (Ekim 2026) | Amaç | Neden | Reddedilen seçenek ve nedeni |
|---|---|---|---|---|
| Mobil çatı | Expo SDK 57 (30 Haziran 2026; React Native 0.86, React 19.2), kararlı çıkınca SDK 58 (beta 15 Eylül 2026; RN 0.88 RC) ([SDK 57](https://expo.dev/changelog/sdk-57), [SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)) | Tek kodla iOS ve Android | K-09; React Native 0.82'den beri yalnız Yeni Mimari ([RN 0.82](https://reactnative.dev/blog/2025/10/08/react-native-0.82)) | Eski plandaki SDK 51: altı sürüm geride ve Yeni Mimari sınırından önce. Expo Go: yerel modül eklenemez |
| Yönlendirme | Expo Router (sürümü SDK'ya bağlı) | Sekmeler, derin bağlantı | SDK 56'dan beri react-navigation bağımlılığı yok ([SDK 56](https://expo.dev/changelog/sdk-56)) | — |
| Cihazda veri | expo-sqlite + Drizzle ORM | İçerik paketleri; `user.db`, `device.db` | Canlı sorgu ve göç desteği ([React Native Relay](https://reactnativerelay.com/article/building-offline-first-react-native-apps-2026-expo-sqlite-drizzle-orm-sync-strategies)) | WatermelonDB (K-30). op-sqlite: yalnız gerçek veriyle ölçüm sorun gösterirse |
| Cihazda arama | SQLite FTS5; expo-sqlite `enableFTS` Android ve iOS'ta açık ([expo-sqlite](https://docs.expo.dev/versions/v58.0.0/sdk/sqlite.md)) | Çevrimdışı arama | [K-17](../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) | Azure AI Search: Basic katmanı ayda 73,73 $ ([Turbo360](https://azure-cost-management-playbook.turbo360.com/docs/ai-search)) ve çevrimdışı çalışmaz |
| Ses | expo-audio ~58.0.10 + XState; `expo-file-system` ~58.0.13 (indirme, `file.digest`) | Arka planda çalma; kilit ekranında sonraki/önceki sure (`AudioPlaylist`, SDK 58.0.0); sure dosyası + âyet kareleri; tekrar ve aralık XState'te | K-28, [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme); expo-audio'da aralık döngüsü yok ([expo-audio v58](https://docs.expo.dev/versions/v58.0.0/sdk/audio/); [Ses kaynağı araştırması](../06-mobil/04-ses-kaynak-arastirmasi.md)) | react-native-track-player v5 ticari kullanımda ücretli, v4 donduruldu ([RNTP](https://github.com/doublesymmetry/react-native-track-player)); expo-av (K-30) |
| Mobil arayüz | NativeWind v4, React Native Reusables, @gorhom/bottom-sheet 5.2.x, Reanimated 4, Gesture Handler | Bileşenler, alt sayfa, jestler | K-29 | NativeWind v5: ön sürüm, "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)). Unistyles 3 yedek seçenek ([karşılaştırma](https://reactnativerelay.com/article/react-native-styling-2026-nativewind-unistyles-tamagui-compared)). Tamagui (eski plan) |
| Mobil durum | Zustand, TanStack Query, react-native-mmkv | Arayüz durumu, sorgu önbelleği, hızlı anahtar-değer | K-29 | — |
| Hata izleme | Sentry (`@sentry/react-native`) | Çökme ve hata kaydı; `dev` derlemede kapalı | Expo eklentisi var ([Mobil mimari](../06-mobil/01-mobil-mimari.md)) | Application Insights (K-30) |
| Derleme ve dağıtım | EAS Build, EAS Update | Bulutta iOS derlemesi, iç dağıtım, yalnız JavaScript güncellemesi | Geliştirme bilgisayarı Windows; iOS yerelde derlenemez | Yerel Xcode: Mac gerekir |
| Uçtan uca test | Maestro CLI; sürüm kurulum günü yazılır, Windows kurulumu Doğrulanacak | Mobil akışlar (`apps/mobile/e2e/*.yaml`) | Test stratejisinin aracı ([Test stratejisi](../07-yayin/03-test-stratejisi.md) §9); iOS koşusunun yeri Açık soru (aynı dosya §14 madde 7) | — |
| Arka uç | ASP.NET Core 10 LTS Minimal API; son yama 10.0.14 (25 Ekim 2026, plan dışı güvenlik sürümü; kilit dosyasında EF Core paketleri ve `dotnet-ef` aynı sürümdedir); destek 14 Kasım 2028 ([.NET destek politikası](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)) | Editör uçları, yayın; v1.x'te hesap ve senkron | K-10; .NET 8 ve 9'un desteği 10 Kasım 2026'da biter | Supabase, Cloudflare Workers + D1, güncellenmiş Azure (K-10). .NET 11: kısa süreli destek (STS) |
| ORM | EF Core 10.0.14 + Npgsql EF Core 10.0.3 (A07, 27 Ekim 2026) | Editoryal veritabanı erişimi, göçler | K-10 | DbUp ile karma göç (eski plan): iki göç yolu bakım yükü getirir |
| Veritabanı | PostgreSQL 18 (Docker `postgres:18`) | Editoryal veri; v1.x'te kullanıcı verisi | K-11; hazır `turkish` ve `arabic` Snowball yapılandırmaları ([PostgreSQL 18](https://docs.w3cub.com/postgresql~18/textsearch-psql)) | MSSQL (K-11). PostgreSQL 19: RC1 15 Ekim 2026'da çıktı ([PG 19](https://www.postgresql.org/docs/19/release-19.html)); kararlı sürüm ve eklenti desteğinden sonra |
| Kimlik | ASP.NET Core Identity | v1'de editör rolleri, v1.x'te okur hesabı | Ek servis gerektirmez | Azure AD B2C: 1 Mayıs 2025'ten beri yeni müşteriye satılmıyor ([Microsoft Learn](https://learn.microsoft.com/en-my/azUre/active-directory-b2c/faq)) |
| İçerik hattı | Python 3.13 + uv | OCR ve düzeltme, Arapça NLP, gömme, toplu etiketleme | K-12 | .NET 10 + ZemberekDotNet; TypeScript (K-12) |
| Editör paneli | React, TypeScript, Vite, shadcn/ui, Tailwind CSS v4 (v4.3.3, [Tailwind](https://github.com/tailwindlabs/tailwindcss/releases)) | İç araç | K-13 | Next.js: iç araçta arama motoru görünürlüğü gerekmez (K-14) |
| Web (Faz 5) | Next.js 16.4 (6 Ekim 2026; React 19.3; `ensureStatic`) ([Next.js 16.4](https://nextjs.org/blog/next-16-4)) | Her âyete ayrı adresli statik sayfa | K-14 | Expo Router web: SSR SDK 58'de kararlı oluyor, 20 bin sayfalık kanıt yok ([araştırma raporu](../09-kaynakca.md)) |
| Nesne deposu | Yerelde S3 uyumlu konteyner (örnek SeaweedFS, Doğrulanacak); canlıda S3 uyumlu depo, öneri Cloudflare R2: depolama 0,015 $/GB-ay, veri çıkışı ücretsiz ([R2](https://developers.cloudflare.com/r2/pricing)) | Paket, manifest, ses | K-21 | MinIO topluluk sürümü: Ekim 2025'ten beri imaj yayımlanmıyor, Aralık 2025'ten beri bakım kipinde ([linuxiac](https://linuxiac.com/minio-ends-active-development/)). Supabase Storage: veri çıkışı GB başına 0,09 $ ([Toolradar](https://toolradar.com/blog/supabase-pricing-2026)) |
| Depo araçları | pnpm workspaces + Turborepo; .NET çözümü; uv | Üç dilin tek depoda derlenmesi | Brifteki proje yapısı | npm ve yarn çalışma alanları; Nx (değerlendirilmedi) |
| CI | GitHub Actions | Denetim ve EAS tetikleme | Eski planda da vardı | Azure DevOps (Azure yığını çıktı) |
| Konteyner | Docker Desktop (WSL2) + Docker Compose | Yerel yığın | K-20 | Azure Container Apps (K-30) |
| Yapay zekâ (sonra) | Claude Haiku 5.5: 100 bin token altı istemde milyon girdi tokenı 0,10 $, çıktı 0,50 $ ([Claude fiyatlandırma](https://platform.claude.com/docs/en/about-claude/pricing)) | Kelime anlamı ve bağlantı taslağı; sonra kaynaklı soru-cevap | Düşük maliyet | Azure OpenAI GPT-4o (eski plan) |
| Vektör (sonra) | pgvector 0.8.7 (1 Ekim 2026) ([PGXN](https://pgxn.org/dist/vector)) | Anlamsal katman | PostgreSQL içinde çalışır | Azure AI Search |

## 2. Uygulama başına kitaplıklar

Bu bölüm her uygulamanın dış bağımlılıklarını listeler. Kesin sürümler kilit dosyalarındadır (bölüm 4.1); bağımlılıklar CI'da yalnız listelenir (bölüm 3).

### 2.1 Mobil (`apps/mobile`)

| Kitaplık | Görev | Not |
|---|---|---|
| `expo`, `expo-router`, `expo-dev-client`, `expo-updates` | Çatı, rotalar, geliştirme derlemesi, OTA | Sürümler `npx expo install` ile SDK'ya göre seçilir |
| `expo-sqlite`, `drizzle-orm` (+ `drizzle-kit`) | Paketler, kullanıcı ve cihaz veritabanı | Drizzle yalnız `user.db` ve `device.db` için ([Mobil mimari](../06-mobil/01-mobil-mimari.md)) |
| `expo-audio`, `xstate` | Ses motoru ve oynatıcı makinesi | [Ses sistemi](../06-mobil/02-ses-sistemi.md) |
| `expo-file-system`, `expo-font`, `expo-image` | İndirme, Mushaf A fontları, Mushaf B görselleri | — |
| `nativewind` v4 | Tailwind sözlüğüyle stil | v5 RC kullanılmaz |
| [React Native Reusables](https://github.com/founded-labs/react-native-reusables) | Arayüz bileşenleri | Alt sayfa bileşeni yok |
| `@gorhom/bottom-sheet` 5.2.x | Kelime kartı, Bağlantılar paneli | Reanimated 4 ve Gesture Handler ≥ 2.16.1 ister ([package.json](https://github.com/gorhom/react-native-bottom-sheet/blob/master/package.json)) |
| `react-native-reanimated` 4, `react-native-gesture-handler` | Sayfalayıcı, seçim | — |
| `zustand`, `@tanstack/react-query`, `react-native-mmkv` | Durum | — |
| `@sentry/react-native` | Hata izleme | — |
| `zod` | Manifest şema doğrulaması (öneri) | Şema `packages/content-schema` içinde |
| `@noble/ed25519` | Manifest imzasını doğrulama (A23) | 3.2.0. İmzasız manifest reddedilir; Ed25519 ve RFC 8785 kararı [K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json) (IP-7 çözüldü) |
| `canonicalize` | Manifestin RFC 8785 (JCS) baytları (A23) | 5.1.0; .NET tarafıyla aynı baytları üretir ([K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json)) |
| `jest-expo`, `@testing-library/react-native` | Test | — |

### 2.2 API ve altyapı (`server/Mutalaa.Api`, `server/Mutalaa.Infrastructure`)

Veri erişimi paketleri `Mutalaa.Infrastructure` projesindedir (`Microsoft.EntityFrameworkCore.Design` yalnız `Mutalaa.Api` projesindedir, `PrivateAssets=all`). Sürümler `server/Directory.Packages.props` içinde sabittir.

| Paket | Görev | Sürüm |
|---|---|---|
| `Microsoft.EntityFrameworkCore`, `Microsoft.EntityFrameworkCore.Relational` (Infrastructure) | EF Core çekirdeği | 10.0.14 |
| `Microsoft.EntityFrameworkCore.Design` (Api) | `dotnet ef` tasarım zamanı | 10.0.14 (`dotnet-ef` aracı da 10.0.14) |
| `Microsoft.AspNetCore.Identity.EntityFrameworkCore` (Infrastructure) | Editör ve (v1.x) okur kimliği | 10.0.14 |
| `Npgsql.EntityFrameworkCore.PostgreSQL` (Infrastructure) | EF Core sağlayıcısı | 10.0.3 |
| `EFCore.NamingConventions` (Infrastructure) | snake_case tablo ve sütun adları | 10.0.1 |
| `Microsoft.AspNetCore.OpenApi` | Yerleşik OpenAPI belgesi (A14) | |
| `Scalar.AspNetCore` | OpenAPI arayüzü (yalnız geliştirme; A14) | |
| `Serilog.AspNetCore` | Yapılandırılmış günlük (A14) | |
| `OpenTelemetry.Extensions.Hosting`, `OpenTelemetry.Instrumentation.AspNetCore`, `OpenTelemetry.Exporter.OpenTelemetryProtocol`, `Npgsql.OpenTelemetry` | İz ve ölçü (A14) | |
| `xunit.v3` | Birim ve tümleşik test | 4.0.2 |
| `Testcontainers.PostgreSql` | Test kabı (`postgres:18.6-trixie`; yalnız test) | 4.16.0 |
| `Microsoft.AspNetCore.Mvc.Testing` | Uç testleri (A14) | |

`Testcontainers.PostgreSql` geçişli bağımlılıkları (`Docker.DotNet.Enhanced`, `SSH.NET`, `BouncyCastle`, `SharpZipLib`) yalnız test projesine girer, dağıtılan ürüne girmez.

Test çalıştırıcısı ([K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)): `xunit.v3` 4.x, Microsoft.Testing.Platform (MTP v2) üzerinde koşar. `Microsoft.NET.Test.Sdk` ve `xunit.runner.visualstudio` eklenmez. MTP kipi kökteki `global.json` içindeki `test.runner` ile açılır; komut `dotnet test --solution server/Mutalaa.slnx`. Paket sürümü yalnız `server/Directory.Packages.props` içinde yazılır (A02.4'te `xunit.v3` 4.0.2). Neden: `xunit.v3` 4.0, VSTest hedefini .NET 10 SDK'da desteklemiyor ([xunit.v3 4.0.0](https://xunit.net/releases/v3/4.0.0), [dotnet test belgesi](https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-with-dotnet-test), okuma 21 Ekim 2026).

### 2.3 Yayınlayıcı (`server/Mutalaa.Publisher`)

Sürümler `server/Directory.Packages.props` içinde sabittir. Sürümler NuGet kayıtlarından okundu (9 Kasım 2026); JCS, NSec ve SQLite ölçümleri A13.0'da yapıldı (.NET 10.0, Windows).

| Paket | Görev | Sürüm ve durum |
|---|---|---|
| `Microsoft.Data.Sqlite` (SQLitePCLRaw e_sqlite3 ile) | Paket yazımı | 10.0.14. `ENABLE_FTS5` derleme seçeneği ölçüldü ve var; yine de açılışta `PRAGMA compile_options` ile denetlenir |
| `AWSSDK.S3` | S3 uyumlu depoya yükleme | 4.0.104.11 (`AWSSDK.Core` [4.0.102.19, 5.0.0) ile gelir). Çözüldü (9 Kasım 2026): SeaweedFS 4.48 ile varsayılan (`WHEN_SUPPORTED`) ve `WHEN_REQUIRED` bütünlük sağlaması ikisi de HTTP'de çalıştı; ürün `WHEN_REQUIRED` kullanır (https, gerçek S3 ve büyük gövde sınanmadı). Ayrıntı: [A13](../10-claude-code/asamalar/A13-yayinlayici-ve-kalite-kapisi.md) Tedarik › SeaweedFS ölçüm sonuçları |
| `System.CommandLine` | Komut satırı | 2.0.14 (kararlı hat; [K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json) madde 6) |
| `Microsoft.Extensions.Hosting` | .NET genel ana bilgisayarı (`Host.CreateApplicationBuilder`; yapılandırma, kullanıcı sırları, günlük) | 10.0.14 |
| `NSec.Cryptography` | Manifest imzası (Ed25519) | 26.4.0. Ölçüm: RFC 8032 §7.1 TEST 1 açık anahtarını ve imzasını bayt bayt üretti; BouncyCastle ile aynı imzayı verdi. Yedek: `BouncyCastle.Cryptography` 2.7.0 ([K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json)) |
| `MackySoft.Json.Canonicalization` | Manifestin RFC 8785 (JCS) baytları | 0.1.0. Ölçüm: `cyberphone/json-canonicalization` @32a4819 altı girdi/çıktı çifti bayt bayt aynı. Yedek: `Jcs.Net` 0.1.1, aynı altı çiftte aynı çıktı ([K-45](../00-ozet/02-karar-defteri.md#k-45--manifest-imzası-ve-kanonik-json)) |
| `JsonSchema.Net` | Manifest şema doğrulaması (`verify` komutu ve testler) | 9.6.0 |

NSec yerel `libsodium` kitaplığını yükler; Linux CI'da yüklenmesi ilk koşuda görülür, yüklenmezse yedek BouncyCastle'dır.

### 2.4 İçerik hattı (`pipeline/`)

| Paket | Görev | Sürüm ve durum |
|---|---|---|
| `psycopg` (3) | PostgreSQL bağlantısı | 3.3.6; yalnız geliştirme bilgisayarında çalışır, dağıtılmaz |
| `regex`, `rapidfuzz` | Unicode düzenli ifade, bulanık eşleştirme (iktibas) | — |
| CAMeL Tools | Tefsir ve Risale'deki Kur'an dışı Arapça | 1.6.0 (8 Haziran 2026); Python 3.11–3.14 ([PyPI](https://pypi.org/project/camel-tools/)). Veri paketleri `camel_data` ile ayrıca indirilir ([Yerel geliştirme](./04-yerel-gelistirme.md) §10.4) |
| `snowballstemmer` 3.1.1 | Türkçe gövde (`tr_stem`): `snowballstemmer.turkish_stemmer.TurkishStemmer`, `â î û` ön katlamasıyla ([Arama](../03-veri/05-arama-fts5.md) §1.2 madde 7, [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 6) | Saf Python; tam sürümle sabitlenir (`==3.1.1`); yalnız geliştirme bilgisayarında çalışır, dağıtılmaz, çıktısı (`tr_stem` sütunu) pakete girer. C uzantılı `PyStemmer` bilerek kullanılmaz: aynı ortamda kuruluysa `snowballstemmer` sessizce ona geçerdi. Kaynak: [PyPI](https://pypi.org/pypi/snowballstemmer/json), okuma 25 Ekim 2026 |
| zeyrek | Türkçe morfoloji (Zemberek'in kısmi Python uyarlaması) | 0.1.3 (Aralık 2022), alfa ([PyPI](https://pypi.org/project/zeyrek)) |
| `sentence-transformers` + Qwen3-Embedding ya da BGE-M3 | Anlamsal katman (sonra) | — |
| Kraken, Tesseract ya da görsel yapay zekâ modeli | Elmalılı OCR | Seçim [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) dosyasında |
| `anthropic` | Toplu etiketleme taslağı | — |
| `typer`, `pytest`, `ruff`, `mypy` | Komut satırı, test, biçim, tip denetimi | — |

### 2.5 Editör paneli (`apps/editor`)

| Paket | Görev |
|---|---|
| `react`, `vite`, `@vitejs/plugin-react` | Çatı ve derleme |
| `tailwindcss` v4.3, shadcn/ui (bileşenler depoya kopyalanır) | Arayüz |
| `react-router` | Rotalar; sürüm Doğrulanacak |
| `@tanstack/react-query` | Sunucu durumu |
| `openapi-typescript`, `openapi-fetch` | OpenAPI belgesinden tip ve istemci |
| `vitest`, `@testing-library/react` | Test |

### 2.6 Web (Faz 5) ve paylaşılan paketler

- Web: `next` 16.4, `react` 19.3, Tailwind CSS v4, shadcn/ui. Çevrimdışı web araması gerekirse Türkçe ve Arapça gövdeleyicisi olan Orama değerlendirilir ([Orama](https://docs.orama.com/open-source/supported-languages)); expo-sqlite'ın web derlemesinde FTS yok.
- Paylaşılan paketler (`packages/*`): yalnız `xstate` (oynatıcı) ve `drizzle-orm` (şema tipleri) dış bağımlılık taşır. Diğerleri bağımlılıksız TypeScript'tir.

## 3. Kitaplık notları ve bağımlılık listesi

- **react-native-track-player:** v5 ticari kullanımda ücretlidir; v4 donduruldu ([RNTP](https://github.com/doublesymmetry/react-native-track-player)). Ücretli kitaplıkta tahmini maliyet kullanıcıya gösterilir (kural 11); ses motoru expo-audio + XState'tir (K-28).
- **NativeWind v5:** `nativewind@5.0.0-rc.0`, `tailwindcss@4.1.12` sürümüne sabit ve "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)). v4 kullanılır (K-29).
- **Ücretli .NET kitaplıkları:** MediatR'ın yeni sürümleri ücretlidir; eski plan bunu not eder (`quran-app-docs/02-mimari/03-mimari-karar-loglari.md`, ADR-003). Yeni yapıda MediatR yoktur; işleyiciler Minimal API uçlarındadır. AutoMapper ve FluentAssertions'ın yeni sürümleri de ücretlidir (Doğrulanacak). Üçü de kullanılmaz; kullanılacak olursa tahmini maliyet kullanıcıya gösterilir (kural 11).
- **İçerik kaynakları** kod bağımlılığı değildir; kaynak kaydı ve atıf [Kaynaklar](../04-icerik/01-kaynaklar.md) dosyasında ve `pipeline/sources/` altında izlenir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 4).
- **Bağımlılık listesi (A08; [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 6).** CI her ekosistemde bağımlılıkları lisanslarıyla yalnız listeler; hiçbir lisans derlemeyi ya da PR'ı durdurmaz. Araçlar:
  - TypeScript: `pnpm licenses list -r --json --prod`. pnpm v12.7.0'dan beri proje içinde yalnız o projeyi listeler; çalışma alanının tamamı için kökte `-r` gerekir ([pnpm licenses](https://pnpm.io/cli/licenses)).
  - .NET: `nuget-license` 4.0.18, yerel araç (`.config/dotnet-tools.json`). `.slnx` destekler, restore yapmaz (önce `dotnet restore` gerekir), `-exclude-projects "*Tests*"` ile test projelerini dışlar ([nuget-license](https://github.com/sensslen/nuget-license)).
  - Python: `pip-licenses` 5.5.5, `uv run --with "pip-licenses==5.5.5"` ile (projeye bağımlılık eklenmez) ([pip-licenses](https://pypi.org/project/pip-licenses/)).
  - Betik: [scripts/ci/list-licenses.mjs](../../scripts/ci/list-licenses.mjs). pnpm ve `nuget-license` çıktısını okur; paket başına bir satır ve lisans başına sayım yazar. Okuma, ayrıştırma ve alan hatasında (eksik ya da yeniden adlandırılmış paket alanı), `--json` dosyası yazılamadığında ve boş NuGet listesinde 2 ile çıkar, öteki her durumda 0.
  - İlk sonuçlar (27 Ekim 2026): pnpm `--prod` kümesi boş (uygulama paketleri henüz yok); .NET test dışı 4 proje, 46 paket (MIT 43, Apache-2.0 1, PostgreSQL 2).

  Liste Ayarlar › Kaynaklar ekranının açık kaynak bölümünü besler; `list-licenses.mjs --json` çıktısı girdi olur (A32).

## 4. Sürüm sabitleme ve yükseltme

### 4.1 Sabitleme

| Ne | Nerede |
|---|---|
| JavaScript bağımlılıkları | `pnpm-lock.yaml`; CI `pnpm install --frozen-lockfile` |
| pnpm sürümü | Kök `package.json` `devEngines.packageManager` alanı, tam sürüm; `packageManager` alanı ve Corepack kullanılmaz ([K-32](../00-ozet/02-karar-defteri.md#k-32--pnpm-kurulumu-sürüm-sabitleme-ve-düzen)) |
| Node.js | `.nvmrc` (24) |
| TypeScript | Tek sürüm, 6.0.x ([K-34](../00-ozet/02-karar-defteri.md#k-34--typescript-tek-sürüm-60x)). Kök `package.json` `devDependencies` içinde `typescript` gerçek paket olarak `~6.0` aralığıyla durur. TS 7 (native) kullanılmaz: `typescript-eslint` 8.72.0 eş bağımlılık aralığı `<6.1`'dir ve A02'de TS 7.0.2 ile "typescript-eslint does not support TS 7.0" hatası alındı (21 Ekim 2026). TS 7'ye geçiş `typescript-eslint`, Expo ve Next desteği belgelenince tek satırlık yükseltmedir; o zaman `/karar` ile karar defterine yazılır ([TS 7 duyurusu](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)) |
| .NET SDK ve test çalıştırıcısı | `global.json` (`10.0.100`, `rollForward: latestFeature`; `test.runner` = `Microsoft.Testing.Platform`, [K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)) |
| NuGet paketleri | `Directory.Packages.props` (merkezi sürüm) ve `packages.lock.json` (`RestorePackagesWithLockFile`) |
| Python | `pipeline/.python-version` (3.13) ve `uv.lock`; CI `uv sync --locked`. CI'da `uv` sürümü `0.13.1` olarak sabittir (`astral-sh/setup-uv` `version` girdisi; yerel kurulumla aynı, İ-01) |
| CI eylemleri ve runner'lar | Eylemler tam commit SHA'sı ve sürüm yorumuyla sabittir; runner'lar `ubuntu-24.04` ve `windows-2025` (`-latest` kullanılmaz). Sürümler ve gerekçe: [Proje yapısı §7](./03-proje-yapisi.md#7-ci-iş-akışları-github-actions) |
| pnpm sürümü (CI) | CI'da `pnpm/action-setup` sürümü `devEngines.packageManager` alanından okur; iş akışında `version` girdisi yoktur |
| Expo'ya bağlı paketler | `npx expo install` ile kurulur; CI `npx expo install --check` ile uyumu denetler |
| Docker imajları | En az ana sürümle (`postgres:18`); canlıya yakın ara sürüm ve özetle (digest). Yerel imajlar sabit etiketlidir: `postgres:18`, `chrislusf/seaweedfs:4.48`, `amazon/aws-cli:2.38.3`; `latest` kullanılmaz. Etiketler kök `.env.example` içindeki `POSTGRES_TAG`, `SEAWEEDFS_TAG` ve `AWSCLI_TAG` değişkenleriyle verilir ([Yerel geliştirme](./04-yerel-gelistirme.md) §5) |

### 4.2 Yükseltme politikası

| Bileşen | Kural |
|---|---|
| Expo SDK | 2026'da sürümler sık çıktı: SDK 56 21 Mayıs, SDK 57 30 Haziran, SDK 58 betası 15 Eylül ([SDK 56](https://expo.dev/changelog/sdk-56), [SDK 57](https://expo.dev/changelog/sdk-57), [SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)). Uygulama en güncel kararlı SDK'da kalır. Yeni SDK kararlı çıkınca Reanimated, NativeWind, bottom-sheet, Sentry ve Drizzle uyumlu olduğunda ayrı dalda geçilir. Cihaz kontrol listesi (FTS5, arka planda ses, kilit ekranı, paket indirme, Mushaf A fontları) geçmeden birleştirilmez. Mağaza yayınından önceki iki haftada SDK değişmez (öneri). SDK 57'de yama alt sınırı `expo@57.0.17` ([Mobil mimari](../06-mobil/01-mobil-mimari.md)) |
| Yerel React Native kitaplıkları | Yeni Mimari desteği şarttır |
| .NET | Yalnız LTS sürüm. .NET 10'da kalınır (destek 14 Kasım 2028). .NET 11 kısa süreli destekli olduğu için atlanır ([.NET destek politikası](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)). Aylık yamalar (SDK ve imaj) iki hafta içinde uygulanır. Sonraki LTS'ye geçiş 2028'de planlanır; LTS takvimi Doğrulanacak |
| PostgreSQL | 18'de kalınır; ara sürümler uygulanır. 19'a kararlı sürüm ve pgvector desteğinden sonra döküm ve geri yükleme ile geçilir |
| Node.js | Expo araçları 22.13+, 24.3+ ya da 26+ ister; tek sayılı 23 ve 25 desteklenmez ([SDK 58 kararlı sürüm notu](https://expo.dev/changelog/sdk-58), 15 Ekim 2026; aralık beta notuyla aynı). Seçim Node.js 24 LTS |
| Python | 3.13. CAMeL Tools 3.14'ü destekliyor; OCR araçları da hazır olunca 3.14'e geçilir |
| Next.js | Faz 5 başında güncel kararlı sürüm; yükseltmede `next upgrade --agent` ([Next.js 16.4](https://nextjs.org/blog/next-16-4)) |
| Bağımlılık güncellemesi | [Dependabot](../../.github/dependabot.yml): `npm`, `github-actions` ve `uv` (`/pipeline`) için haftalık PR; ekosistem başına tek grup (minor ve patch birlikte, major ayrı). Başlık önekleri `build(infra)`, `ci(infra)`, `build(pipeline)` (Proje yapısı §6 kapsamları). `uv` desteği doğrulandı (27 Ekim 2026, A08.1): `package-ecosystem: uv` vardır ve `uv.lock` dosyasını günceller; bazı durumlar çalışmıyor ([astral-sh/uv#2512](https://github.com/astral-sh/uv/issues/2512)). Expo'ya bağlı paketler yalnız SDK yükseltmesiyle güncellenir; Expo paketleri için `ignore` kuralı `apps/mobile` eklenirken A21'de yazılır. Güvenlik güncellemeleri beklemeden alınır. **Dependabot'un kapsamadıkları:** (1) pnpm 12'nin yazdığı iki belgeli `pnpm-lock.yaml`'da sürüm güncellemesi çalışır, ama bağımlılık grafiği ve güvenlik uyarısı üretilmez. (2) NuGet dışarıdadır: `ProjectReference` ile etkilenen projelerde kilit dosyası güncellenmiyor ve `dotnet restore --locked-mode` NU1004 veriyor ([dependabot-core#13950](https://github.com/dependabot/dependabot-core/issues/13950)). (3) `docker-compose.yml` dışarıdadır: imaj etiketleri `.env` değişkeninden geliyor ve Dependabot atlıyor. Bu yüzden `dotnet-ef`, .NET SDK, NuGet paketleri, Testcontainers imajı ve compose etiketleri elle güncellenir; compose etiketi ile `PostgresFixture` imajı birlikte değişir |

## 5. Eski plandan çıkarılan teknolojiler (K-30)

Eski plan: `quran-app-docs/02-mimari/01-genel-mimari.md` ve `quran-app-docs/00-baslangic/03-hizli-karar-cetveli.md`.

| Eski plan | Yerine | Neden |
|---|---|---|
| ASP.NET Core 9 modüler monolit (12 modül), MediatR ve Outbox | ASP.NET Core 10 ince API; işleyiciler uçlarda | .NET 9 desteği 10 Kasım 2026'da biter ([.NET](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)); tek geliştirici için fazla parça |
| Azure Container Apps, Container Registry, Functions, Key Vault, API Management | Docker Compose (yerel); canlı yöntem sonra (K-20) | v1'de okur trafiği sunucuya gelmez |
| Azure Database for PostgreSQL Flexible 16 | PostgreSQL 18 (Docker) | K-11 |
| Azure Cache for Redis | Yok | İçerik statik paketlerde |
| Azure AI Search S1 | Cihazda FTS5 | Basic katmanı bile ayda 73,73 $ ([Turbo360](https://azure-cost-management-playbook.turbo360.com/docs/ai-search)); çevrimdışı çalışmaz |
| Azure AD B2C | ASP.NET Core Identity (v1.x) | 1 Mayıs 2025'ten beri yeni müşteriye satılmıyor ([Microsoft Learn](https://learn.microsoft.com/en-my/azUre/active-directory-b2c/faq)) |
| Azure Blob Storage ve Front Door | S3 uyumlu depo (öneri R2) | Ses trafiğinde veri çıkış ücreti belirleyici ([R2](https://developers.cloudflare.com/r2/pricing)) |
| Azure SignalR, LiveKit, Notification Hubs | Yok | Mukabele ve ortak hatim kapsam dışı (K-30) |
| Application Insights, Log Analytics | Serilog ve OpenTelemetry (API), Sentry (mobil) | — |
| Bicep | Yok | Canlı barındırma seçilmedi |
| Azure OpenAI GPT-4o, Cohere Rerank, BGE-M3 GPU servisi, Python morfoloji servisi | Hat içinde çevrimdışı işler; sonra Claude Haiku 5.5 | Çalışma zamanında model yok |
| Expo SDK 51, expo-av, WatermelonDB, react-native-track-player | SDK 57/58, expo-audio, expo-sqlite + Drizzle, expo-audio + XState | K-09, K-28 |
| Next.js 15 | Next.js 16.4 | K-14 |
| Tamagui seçeneği | NativeWind v4 | K-29 |
| Web çevrimdışı katmanı (Dexie, Workbox) | Faz 5'te yeniden ele alınır | Web sonra |
| Poetry, Black | uv, ruff | K-12; tek araç |
| EF Core + DbUp karma göç | Yalnız EF Core göçleri (`migrationBuilder.Sql` ile) | Tek göç yolu |
| Swashbuckle | Yerleşik `Microsoft.AspNetCore.OpenApi` + Scalar | Ek paket gerekmez |
| SonarCloud, Snyk, Codecov, Trivy | v1'de yok | Maliyet ve bakım; gerekirse sonra |
| Kapsam dışı modüller | — | Zekât hesaplayıcı, çocuk modu, aile hesabı, LMS, mukabele, ortak hatim, kıraat-i seb'a, hac ve umre rehberi, AR, akıllı saat, botlar, açık API (K-30) |

## 6. Açık sorular

1. ~~Yerel S3 deposu: K-21 MinIO der.~~ Çözüldü: K-21 güncellendi, yerel depo SeaweedFS ([Genel mimari](./01-genel-mimari.md)).
2. Kaynağı olmayan sürüm numaraları (Turborepo, pnpm, Vite, Npgsql sağlayıcısı, Sentry, Scalar) kurulum günü kilit dosyalarına yazılır ve bu tabloya işlenir.

## İlgili dosyalar

- [Genel mimari](./01-genel-mimari.md) · [Proje yapısı](./03-proje-yapisi.md) · [Yerel geliştirme](./04-yerel-gelistirme.md) · [Backend API](./05-backend-api.md)
- [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Ses sistemi](../06-mobil/02-ses-sistemi.md)
- [Kaynaklar](../04-icerik/01-kaynaklar.md) · [İçerik hattı](../04-icerik/02-icerik-hatti.md)
- [Karar defteri](../00-ozet/02-karar-defteri.md) · [Kaynakça](../09-kaynakca.md)
