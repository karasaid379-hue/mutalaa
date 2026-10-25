# Teknoloji yığını

> **Sürüm:** 1.5 · **Tarih:** 25 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-09](../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-11](../00-ozet/02-karar-defteri.md#k-11--veritabanı-postgresql-18) · [K-12](../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-13](../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-14](../00-ozet/02-karar-defteri.md#k-14--web) · [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses) · [K-29](../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-30](../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-32](../00-ozet/02-karar-defteri.md#k-32--pnpm-kurulumu-sürüm-sabitleme-ve-düzen) · [K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform) · [K-34](../00-ozet/02-karar-defteri.md#k-34--typescript-tek-sürüm-60x) · [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları)

Bu dosya her katmanın teknolojisini, sürümünü, seçilme nedenini ve reddedilen seçenekleri listeler. Sürüm ve fiyatlar 16 Ekim 2026 araştırmasından gelir ([araştırma raporu](../09-kaynakca.md), araştırma notu 05). Kaynağı olmayan sürüm numaraları "Doğrulanacak" diye işaretlidir ve kurulum günü kilit dosyasına yazılır.

---

## 1. Katman tablosu

| Katman | Seçim ve sürüm (Ekim 2026) | Amaç | Neden | Reddedilen seçenek ve nedeni |
|---|---|---|---|---|
| Mobil çatı | Expo SDK 57 (30 Haziran 2026; React Native 0.86, React 19.2), kararlı çıkınca SDK 58 (beta 15 Eylül 2026; RN 0.88 RC) ([SDK 57](https://expo.dev/changelog/sdk-57), [SDK 58 beta](https://expo.dev/changelog/sdk-58-beta)) | Tek kodla iOS ve Android | K-09; React Native 0.82'den beri yalnız Yeni Mimari ([RN 0.82](https://reactnative.dev/blog/2025/10/08/react-native-0.82)) | Eski plandaki SDK 51: altı sürüm geride ve Yeni Mimari sınırından önce. Expo Go: yerel modül eklenemez |
| Yönlendirme | Expo Router (sürümü SDK'ya bağlı) | Sekmeler, derin bağlantı | SDK 56'dan beri react-navigation bağımlılığı yok ([SDK 56](https://expo.dev/changelog/sdk-56)) | — |
| Cihazda veri | expo-sqlite + Drizzle ORM | İçerik paketleri; `user.db`, `device.db` | Canlı sorgu ve göç desteği ([React Native Relay](https://reactnativerelay.com/article/building-offline-first-react-native-apps-2026-expo-sqlite-drizzle-orm-sync-strategies)) | WatermelonDB (K-30). op-sqlite: yalnız gerçek veriyle ölçüm sorun gösterirse |
| Cihazda arama | SQLite FTS5; expo-sqlite `enableFTS` Android ve iOS'ta açık ([expo-sqlite](https://docs.expo.dev/versions/v58.0.0/sdk/sqlite.md)) | Çevrimdışı arama | [K-17](../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) | Azure AI Search: Basic katmanı ayda 73,73 $ ([Turbo360](https://azure-cost-management-playbook.turbo360.com/docs/ai-search)) ve çevrimdışı çalışmaz |
| Ses | expo-audio + XState | Arka planda çalma, kilit ekranı, kesintisiz liste; tekrar ve aralık XState'te | K-28; expo-audio'da aralık döngüsü yok ([expo-audio](https://docs.expo.dev/versions/latest/sdk/audio/)) | react-native-track-player v5 ticari lisanslı, v4 donduruldu ([RNTP](https://github.com/doublesymmetry/react-native-track-player)); expo-av (K-30) |
| Mobil arayüz | NativeWind v4, React Native Reusables, @gorhom/bottom-sheet 5.2.x, Reanimated 4, Gesture Handler | Bileşenler, alt sayfa, jestler | K-29 | NativeWind v5: ön sürüm, "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)). Unistyles 3 yedek seçenek ([karşılaştırma](https://reactnativerelay.com/article/react-native-styling-2026-nativewind-unistyles-tamagui-compared)). Tamagui (eski plan) |
| Mobil durum | Zustand, TanStack Query, react-native-mmkv | Arayüz durumu, sorgu önbelleği, hızlı anahtar-değer | K-29 | — |
| Hata izleme | Sentry (`@sentry/react-native`) | Çökme ve hata kaydı; `dev` derlemede kapalı | Expo eklentisi var ([Mobil mimari](../06-mobil/01-mobil-mimari.md)) | Application Insights (K-30) |
| Derleme ve dağıtım | EAS Build, EAS Update | Bulutta iOS derlemesi, iç dağıtım, yalnız JavaScript güncellemesi | Geliştirme bilgisayarı Windows; iOS yerelde derlenemez | Yerel Xcode: Mac gerekir |
| Uçtan uca test | Maestro CLI; sürüm kurulum günü yazılır, Windows kurulumu Doğrulanacak | Mobil akışlar (`apps/mobile/e2e/*.yaml`) | Test stratejisinin aracı ([Test stratejisi](../07-yayin/03-test-stratejisi.md) §9); iOS koşusunun yeri Açık soru (aynı dosya §14 madde 7) | — |
| Arka uç | ASP.NET Core 10 LTS Minimal API; son yama 10.0.13 (13 Ekim 2026); destek 14 Kasım 2028 ([.NET destek politikası](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)) | Editör uçları, yayın; v1.x'te hesap ve senkron | K-10; .NET 8 ve 9'un desteği 10 Kasım 2026'da biter | Supabase, Cloudflare Workers + D1, güncellenmiş Azure (K-10). .NET 11: kısa süreli destek (STS) |
| ORM | EF Core 10 + Npgsql (sağlayıcı sürümü Doğrulanacak) | Editoryal veritabanı erişimi, göçler | K-10 | DbUp ile karma göç (eski plan): iki göç yolu bakım yükü getirir |
| Veritabanı | PostgreSQL 18 (Docker `postgres:18`) | Editoryal veri; v1.x'te kullanıcı verisi | K-11; hazır `turkish` ve `arabic` Snowball yapılandırmaları ([PostgreSQL 18](https://docs.w3cub.com/postgresql~18/textsearch-psql)) | MSSQL (K-11). PostgreSQL 19: RC1 15 Ekim 2026'da çıktı ([PG 19](https://www.postgresql.org/docs/19/release-19.html)); kararlı sürüm ve eklenti desteğinden sonra |
| Kimlik | ASP.NET Core Identity | v1'de editör rolleri, v1.x'te okur hesabı | Ek servis gerektirmez | Azure AD B2C: 1 Mayıs 2025'ten beri yeni müşteriye satılmıyor ([Microsoft Learn](https://learn.microsoft.com/en-my/azUre/active-directory-b2c/faq)) |
| İçerik hattı | Python 3.13 + uv | OCR ve düzeltme, Arapça NLP, gömme, toplu etiketleme | K-12 | .NET 10 + ZemberekDotNet; TypeScript (K-12) |
| Editör paneli | React, TypeScript, Vite, shadcn/ui, Tailwind CSS v4 (v4.3.3, [Tailwind](https://github.com/tailwindlabs/tailwindcss/releases)) | İç araç | K-13 | Next.js: iç araçta arama motoru görünürlüğü gerekmez (K-14) |
| Web (Faz 5) | Next.js 16.4 (6 Ekim 2026; React 19.3; `ensureStatic`) ([Next.js 16.4](https://nextjs.org/blog/next-16-4)) | Her âyete ayrı adresli statik sayfa | K-14 | Expo Router web: SSR SDK 58'de kararlı oluyor, 20 bin sayfalık kanıt yok ([araştırma raporu](../09-kaynakca.md)) |
| Nesne deposu | Yerelde S3 uyumlu konteyner (örnek SeaweedFS, Doğrulanacak); canlıda S3 uyumlu depo, öneri Cloudflare R2: depolama 0,015 $/GB-ay, veri çıkışı ücretsiz ([R2](https://developers.cloudflare.com/r2/pricing)) | Paket, manifest, ses | K-21 | MinIO topluluk sürümü: Ekim 2025'ten beri imaj yayımlanmıyor, Aralık 2025'ten beri bakım kipinde ([linuxiac](https://linuxiac.com/minio-ends-active-development/)). Supabase Storage: veri çıkışı GB başına 0,09 $ ([Toolradar](https://toolradar.com/blog/supabase-pricing-2026)) |
| Depo araçları | pnpm workspaces + Turborepo; .NET çözümü; uv | Üç dilin tek depoda derlenmesi | Brifteki proje yapısı | npm ve yarn çalışma alanları; Nx (değerlendirilmedi) |
| CI | GitHub Actions | Denetim ve EAS tetikleme | Eski planda da vardı | Azure DevOps (Azure yığını çıktı) |
| Konteyner | Docker Desktop (WSL2) + Docker Compose | Yerel yığın | K-20 | Azure Container Apps (K-30) |
| Yapay zekâ (sonra) | Claude Haiku 5.5: 100 bin token altı istemde milyon girdi tokenı 0,10 $, çıktı 0,50 $ ([Claude fiyatlandırma](https://platform.claude.com/docs/en/about-claude/pricing)) | Kelime anlamı ve bağlantı taslağı; sonra kaynaklı soru-cevap. Yalnız `source.embed_ok` açık kaynaklar dış API'ye gider | Düşük maliyet | Azure OpenAI GPT-4o (eski plan) |
| Vektör (sonra) | pgvector 0.8.7 (1 Ekim 2026; PostgreSQL License) ([PGXN](https://pgxn.org/dist/vector)) | Anlamsal katman | PostgreSQL içinde çalışır | Azure AI Search |

## 2. Uygulama başına kitaplıklar

Lisans sütunu: bağlantılı değerler araştırmadan gelir. "beyan" yazan değerler paket kayıtlarındaki beyandır; CI lisans denetimiyle doğrulanır (Doğrulanacak).

### 2.1 Mobil (`apps/mobile`)

| Kitaplık | Görev | Lisans | Not |
|---|---|---|---|
| `expo`, `expo-router`, `expo-dev-client`, `expo-updates` | Çatı, rotalar, geliştirme derlemesi, OTA | MIT (beyan) | Sürümler `npx expo install` ile SDK'ya göre seçilir |
| `expo-sqlite`, `drizzle-orm` (+ `drizzle-kit`) | Paketler, kullanıcı ve cihaz veritabanı | MIT, Apache-2.0 (beyan) | Drizzle yalnız `user.db` ve `device.db` için ([Mobil mimari](../06-mobil/01-mobil-mimari.md)) |
| `expo-audio`, `xstate` | Ses motoru ve oynatıcı makinesi | MIT (beyan) | [Ses sistemi](../06-mobil/02-ses-sistemi.md) |
| `expo-file-system`, `expo-font`, `expo-image` | İndirme, Mushaf A fontları, Mushaf B görselleri | MIT (beyan) | |
| `nativewind` v4 | Tailwind sözlüğüyle stil | MIT (beyan) | v5 RC kullanılmaz |
| React Native Reusables | Arayüz bileşenleri | MIT ([RN Reusables](https://github.com/founded-labs/react-native-reusables)) | Alt sayfa bileşeni yok |
| `@gorhom/bottom-sheet` 5.2.x | Kelime kartı, Bağlantılar paneli | MIT (beyan) | Reanimated 4 ve Gesture Handler ≥ 2.16.1 ister ([package.json](https://github.com/gorhom/react-native-bottom-sheet/blob/master/package.json)) |
| `react-native-reanimated` 4, `react-native-gesture-handler` | Sayfalayıcı, seçim | MIT (beyan) | |
| `zustand`, `@tanstack/react-query`, `react-native-mmkv` | Durum | MIT (beyan) | |
| `@sentry/react-native` | Hata izleme | MIT (beyan) | |
| `zod` | Manifest şema doğrulaması (öneri) | MIT (beyan) | Şema `packages/content-schema` içinde |
| `@noble/ed25519` | Manifest imzasını doğrulama (öneri) | MIT (beyan) | İmzasız manifest reddedilir; kitaplık seçimi Doğrulanacak ([İçerik paketleri](../03-veri/03-icerik-paketleri.md) IP-7) |
| `jest-expo`, `@testing-library/react-native` | Test | MIT (beyan) | |

### 2.2 API (`server/Mutalaa.Api`)

| Paket | Görev | Lisans |
|---|---|---|
| `Microsoft.AspNetCore.OpenApi` | Yerleşik OpenAPI belgesi | MIT (beyan) |
| `Scalar.AspNetCore` | OpenAPI arayüzü (yalnız geliştirme) | MIT (beyan) |
| `Microsoft.AspNetCore.Identity.EntityFrameworkCore` | Editör ve (v1.x) okur kimliği | MIT (beyan) |
| `Npgsql.EntityFrameworkCore.PostgreSQL` | EF Core sağlayıcısı | PostgreSQL License (beyan) |
| `EFCore.NamingConventions` | snake_case tablo ve sütun adları | Apache-2.0 (beyan) |
| `Serilog.AspNetCore` | Yapılandırılmış günlük | Apache-2.0 (beyan) |
| `OpenTelemetry.Extensions.Hosting`, `OpenTelemetry.Instrumentation.AspNetCore`, `OpenTelemetry.Exporter.OpenTelemetryProtocol`, `Npgsql.OpenTelemetry` | İz ve ölçü | Apache-2.0, PostgreSQL License (beyan) |
| `xunit.v3`, `Microsoft.AspNetCore.Mvc.Testing`, `Testcontainers.PostgreSql` | Birim ve tümleşik test | Apache-2.0, MIT (beyan) |

Test çalıştırıcısı ([K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)): `xunit.v3` 4.x, Microsoft.Testing.Platform (MTP v2) üzerinde koşar. `Microsoft.NET.Test.Sdk` ve `xunit.runner.visualstudio` eklenmez. MTP kipi kökteki `global.json` içindeki `test.runner` ile açılır; komut `dotnet test --solution server/Mutalaa.slnx`. Paket sürümü yalnız `server/Directory.Packages.props` içinde yazılır (A02.4'te `xunit.v3` 4.0.2). Neden: `xunit.v3` 4.0, VSTest hedefini .NET 10 SDK'da desteklemiyor ([xunit.v3 4.0.0](https://xunit.net/releases/v3/4.0.0), [dotnet test belgesi](https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-with-dotnet-test), okuma 21 Ekim 2026).

### 2.3 Yayınlayıcı (`server/Mutalaa.Publisher`)

| Paket | Görev | Lisans | Not |
|---|---|---|---|
| `Microsoft.Data.Sqlite` (SQLitePCLRaw e_sqlite3 ile) | Paket yazımı | MIT, Apache-2.0 (beyan) | FTS5 derleme seçeneği açılışta `PRAGMA compile_options` ile denetlenir |
| `AWSSDK.S3` | S3 uyumlu depoya yükleme | Apache-2.0 (beyan) | S3 uyumlu depolarda bütünlük sağlaması ayarı Doğrulanacak |
| `System.CommandLine` | Komut satırı | MIT (beyan) | Kararlı sürüm durumu Doğrulanacak |
| `NSec.Cryptography` ya da BouncyCastle | Manifest imzası (Ed25519) | MIT (beyan) | Algoritma ve kitaplık Doğrulanacak |
| `JsonSchema.Net` | Testte manifest şema doğrulaması | MIT (beyan) | Doğrulanacak |

### 2.4 İçerik hattı (`pipeline/`)

| Paket | Görev | Lisans ve durum |
|---|---|---|
| `psycopg` (3) | PostgreSQL bağlantısı | LGPL-3.0 (beyan); yalnız geliştirme bilgisayarında çalışır, dağıtılmaz |
| `regex`, `rapidfuzz` | Unicode düzenli ifade, bulanık eşleştirme (iktibas) | Apache-2.0, MIT (beyan) |
| CAMeL Tools | Tefsir ve Risale'deki Kur'an dışı Arapça | Kod MIT; 1.6.0 (8 Haziran 2026); Python 3.11–3.14 ([PyPI](https://pypi.org/project/camel-tools/)). Veri paketleri ayrı lisanslıdır, aşağıdaki nota bakın (Doğrulanacak) |
| `snowballstemmer` 3.1.1 | Türkçe gövde (`tr_stem`): `snowballstemmer.turkish_stemmer.TurkishStemmer`, `â î û` ön katlamasıyla ([Arama](../03-veri/05-arama-fts5.md) §1.2 madde 7, [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 6) | BSD-3-Clause (beyan), saf Python; tam sürümle sabitlenir (`==3.1.1`); yalnız geliştirme bilgisayarında çalışır, dağıtılmaz. Kaynak: [PyPI](https://pypi.org/pypi/snowballstemmer/json), okuma 25 Ekim 2026. Hukuki görüş değildir |
| zeyrek | Türkçe morfoloji (Zemberek'in kısmi Python uyarlaması) | Kod MIT; 0.1.3 (Aralık 2022), alfa ([PyPI](https://pypi.org/project/zeyrek)). Sözlük verisi Zemberek'ten uyarlanmıştır, aşağıdaki nota bakın (Doğrulanacak) |
| `sentence-transformers` + Qwen3-Embedding ya da BGE-M3 | Anlamsal katman (sonra) | Kitaplık Apache-2.0 (beyan); Qwen3-Embedding Apache-2.0, BGE-M3 MIT ([wz-it](https://wz-it.com/en/blog/best-embedding-models-german/)) |
| Kraken, Tesseract ya da görsel yapay zekâ modeli | Elmalılı OCR | Seçim [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) dosyasında |
| `anthropic` | Toplu etiketleme taslağı | MIT (beyan); `source.embed_ok` kapalı kaynağın metni gönderilmez ([Anlamsal katman](../05-capraz-referans/04-anlamsal-katman.md)) |
| `typer`, `pytest`, `ruff`, `mypy` | Komut satırı, test, biçim, tip denetimi | MIT (beyan) |

**Lisans bulguları, A02 lisans denetimi (21 Ekim 2026). Hukuki görüş değildir.** Aşağıdakiler kaynak dosyalarından okundu; çıktının paketlenen içeriğe etkisi ve veri haklarının kapsamı doğrulanmadı.

- **CAMeL Tools (Doğrulanacak).** Kod MIT'tir (camel-tools 1.6.0; [LICENSE](https://github.com/CAMeL-Lab/camel_tools/blob/master/LICENSE)). Ama veri paketleri kodla aynı lisansta değildir ([camel-tools-data kataloğu 1.6](https://raw.githubusercontent.com/CAMeL-Lab/camel-tools-data/main/catalogue-1.6.json)): varsayılan Modern Standart Arapça paketleri `morphology-db-msa-r13` ve `disambig-mle-calima-msa-r13` GPL v2; `morphology-db-msa-s31` LDC lisanslı; Mısır paketleri GPL v2; Körfez ve Şam paketleri CC BY 4.0; BERT modelleri MIT. `camel-kenlm` (camel-tools'un Windows dışındaki geçişli bağımlılığı) LGPL, 2.1 ya da sonrası ([LICENSE](https://raw.githubusercontent.com/CAMeL-Lab/camel-kenlm/master/LICENSE)). Kök ve lemma çıktısını hangi veri paketinin ürettiği ve bu çıktının paketlenen içeriğe (örneğin `kelime-kok`, Risale ve tefsir dizinleri) etkisi doğrulanmadı. Avukata sorulacak bir konudur ([BÇ-35](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)); soru taslağı henüz yazılmadı ve gönderilmeden önce kullanıcı onaylar.
- **zeyrek (Doğrulanacak).** Kod MIT'tir (0.1.3), ama Zemberek'ten uyarlanmış sözlük verisi taşır. Zemberek-NLP Apache-2.0'dır ([LICENSE](https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/LICENSE)); zeyrek tekerleğinde Apache bildirimi görünmüyor. Sözlük verisinin (TDK türevi dosyalar dahil) kaynağı ve hakkı doğrulanamadı. Hat içi morfolojide kullanılıp çıktı insan onayından geçen eşleme tablosuna dönüşüyorsa risk düşük görünüyor; bu hukuki sonuç değildir.
- **psycopg 3.3.6** LGPL-3.0-only'dir. Yukarıdaki satırdaki "yalnız geliştirme bilgisayarında çalışır, dağıtılmaz" beyanıyla tutarlıdır; ek işlem gerekmiyor.
- **`snowballstemmer` (A05, 25 Ekim 2026).** Lisans BSD-3-Clause olarak okundu ([PyPI](https://pypi.org/pypi/snowballstemmer/json)); paket yalnız hatta çalışır ve çıktısı (`tr_stem` sütunu) pakete girer, paketin kendisi dağıtılmaz. Hukuki görüş değildir. Öneri: `lisans-denetcisi` kilit dosyasındaki sürümün lisansını `pip-licenses` ile bir kez doğrular ve BSD bildirimi `THIRD_PARTY_NOTICES` taslağına eklenir (A34). C uzantılı `PyStemmer` bilerek kullanılmaz: aynı ortamda kuruluysa `snowballstemmer` sessizce ona geçerdi.
- **`THIRD_PARTY_NOTICES`.** `camel-kenlm` ile zeyrek/Zemberek için bildirimler mağaza sürümünden önce taslağa eklenir (bkz. bölüm 3, lisans denetimi maddesi).

### 2.5 Editör paneli (`apps/editor`)

| Paket | Görev | Lisans |
|---|---|---|
| `react`, `vite`, `@vitejs/plugin-react` | Çatı ve derleme | MIT (beyan) |
| `tailwindcss` v4.3, shadcn/ui (bileşenler depoya kopyalanır) | Arayüz | MIT (beyan) |
| `react-router` | Rotalar | MIT (beyan); sürüm Doğrulanacak |
| `@tanstack/react-query` | Sunucu durumu | MIT (beyan) |
| `openapi-typescript`, `openapi-fetch` | OpenAPI belgesinden tip ve istemci | MIT (beyan) |
| `vitest`, `@testing-library/react` | Test | MIT (beyan) |

### 2.6 Web (Faz 5) ve paylaşılan paketler

- Web: `next` 16.4, `react` 19.3, Tailwind CSS v4, shadcn/ui. Çevrimdışı web araması gerekirse Türkçe ve Arapça gövdeleyicisi olan Orama değerlendirilir ([Orama](https://docs.orama.com/open-source/supported-languages)); expo-sqlite'ın web derlemesinde FTS yok.
- Paylaşılan paketler (`packages/*`): yalnız `xstate` (oynatıcı) ve `drizzle-orm` (şema tipleri) dış bağımlılık taşır. Diğerleri bağımlılıksız TypeScript'tir.

## 3. Lisans notları

- **react-native-track-player:** v5'ten itibaren ticari lisanslı; kişisel ve eğitim amaçlı kullanım ücretsiz, v4 Apache-2.0 dalında donduruldu ([RNTP](https://github.com/doublesymmetry/react-native-track-player)). "Ticari" ifadesinin ücretsiz bir uygulama için anlamı yazılı netleşmeden kullanılmaz (K-28).
- **NativeWind v5:** `nativewind@5.0.0-rc.0`, `tailwindcss@4.1.12` sürümüne sabit ve "üretim için değil" ([NativeWind v5](https://www.nativewind.dev/v5/getting-started/installation)). v4 kullanılır (K-29).
- **Ticari lisansa geçen .NET kitaplıkları:** Eski plan MediatR'ın yeni sürümlerinin ticari olduğunu not eder (`quran-app-docs/02-mimari/03-mimari-karar-loglari.md`, ADR-003). Yeni yapıda MediatR yoktur; işleyiciler Minimal API uçlarındadır. AutoMapper ve FluentAssertions'ın yeni sürümleri için de lisans değişikliği bilinir (Doğrulanacak). Üçü de kullanılmaz.
- **İçerik lisansları** (Tanzil, QPC fontları, KFGQPC Hafs, QAC) kod lisanslarından ayrıdır ve [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) dosyasında izlenir.
- **Lisans denetimi:** CI her ekosistem için bağımlılık lisans listesi çıkarır (`pnpm licenses list`, `dotnet list package --include-transitive` ile bir lisans aracı, `pip-licenses`; araç seçimi Doğrulanacak). GPL, AGPL ya da ticari lisanslı yeni bir bağımlılık PR'ı durdurur (öneri). Mağaza sürümünden önce `THIRD_PARTY_NOTICES` dosyası bu listeden üretilir. Taslağa `camel-kenlm` (LGPL) ile zeyrek/Zemberek (Apache-2.0) bildirimleri mağaza sürümünden önce eklenir ([bölüm 2.4](#24-i̇çerik-hattı-pipeline) lisans bulguları; hukuki görüş değildir).
- **Uygulamanın kendi kaynak kodu lisansı** Açık soru. Eski plandaki AGPL-3.0 kararı yeni karar defterinde ele alınmadı.

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
| Python | `pipeline/.python-version` (3.13) ve `uv.lock`; CI `uv sync --locked` |
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
| Bağımlılık güncellemesi | Dependabot: npm, NuGet, GitHub Actions ve Docker için haftalık gruplu PR; uv desteği Doğrulanacak. Expo'ya bağlı paketler yalnız SDK yükseltmesiyle güncellenir. Güvenlik güncellemeleri beklemeden alınır |

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
2. Uygulamanın kendi kaynak kodu lisansı.
3. Kaynağı olmayan sürüm numaraları (Turborepo, pnpm, Vite, Npgsql sağlayıcısı, Sentry, Scalar) kurulum günü kilit dosyalarına yazılır ve bu tabloya işlenir.
4. CAMeL veri paketlerinin (GPL v2, LDC) ve zeyrek/Zemberek sözlük verisinin lisansı ile çıktının paketlenen içeriğe etkisi (Doğrulanacak; bölüm 2.4, [BÇ-35](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)). Avukata sorulacak konudur; hukuki görüş değildir.

## İlgili dosyalar

- [Genel mimari](./01-genel-mimari.md) · [Proje yapısı](./03-proje-yapisi.md) · [Yerel geliştirme](./04-yerel-gelistirme.md) · [Backend API](./05-backend-api.md)
- [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Ses sistemi](../06-mobil/02-ses-sistemi.md)
- [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) · [İçerik hattı](../04-icerik/02-icerik-hatti.md)
- [Karar defteri](../00-ozet/02-karar-defteri.md) · [Kaynakça](../09-kaynakca.md)
