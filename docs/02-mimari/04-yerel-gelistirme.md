# Yerel geliştirme

> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-09](../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-11](../00-ozet/02-karar-defteri.md#k-11--veritabanı-postgresql-18) · [K-12](../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-20](../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı)

Geliştirme ekibin kendi Windows bilgisayarında yapılır ([K-20](../00-ozet/02-karar-defteri.md#k-20--barındırma)). PostgreSQL ve S3 deposu Docker'da çalışır. API, editör ve Yayınlayıcı isteğe bağlı olarak Docker'da ya da doğrudan ana makinede çalışır. Node, .NET ve Python araçları ana makinededir. Uygulama telefonda ya da Android emülatöründe geliştirme derlemesiyle açılır.

```mermaid
flowchart LR
  subgraph PC["Windows bilgisayar"]
    subgraph DK["Docker Desktop · WSL2"]
      PG[("postgres:18<br/>127.0.0.1:5432")]
      S3[("S3 deposu<br/>0.0.0.0:8333")]
      API["api · profil app<br/>127.0.0.1:5080"]
      EDC["editor · profil app<br/>127.0.0.1:5174"]
      PUBC["publisher · profil app"]
    end
    HOST["Ana makine<br/>pnpm, dotnet, uv"]
    METRO["Metro<br/>0.0.0.0:8081"]
  end
  TEL["Telefon · dev derleme"]
  EMU["Android emülatörü"]
  HOST --> PG
  HOST --> S3
  TEL -->|"LAN IP:8081"| METRO
  TEL -->|"LAN IP:8333"| S3
  EMU -->|"10.0.2.2:8081"| METRO
  EMU -->|"10.0.2.2:8333"| S3
```

---

## 1. Ön koşullar

| Araç | Sürüm | Neden |
|---|---|---|
| Windows 11 (ya da WSL2 destekli Windows 10), BIOS'ta sanallaştırma açık | — | Docker Desktop WSL2 arka ucu |
| WSL2 | Güncel (`wsl --install`, `wsl --update`) | Docker Desktop |
| Docker Desktop | Güncel; Compose v2 | PostgreSQL ve S3 deposu |
| Git | Güncel | — |
| Node.js | 24 LTS (24.3 ya da üstü) | Expo SDK 58 araçları Node 22.13+, 24.3+ ya da 26+ ister; tek sayılı 23 ve 25 desteklenmez ([SDK 58](https://expo.dev/changelog/sdk-58)). Çözüldü (19 Ekim 2026): SDK 58 kararlı sürümü 15 Ekim 2026'da çıktı ve aralık beta notuyla aynıdır (`expo@58` `engines`: `^22.13.0 \|\| ^24.3.0 \|\| ^26.0.0 \|\| >=27.0.0`) |
| pnpm | Kuruluma göre belirlenir; kök `package.json` içindeki `packageManager` sabitlemesi A02'dedir ([BÇ-28](../10-claude-code/07-belge-celiskileri.md)) | Yol 1: `npm install -g pnpm`; pnpm'in güncel kurulum belgesi Corepack'i anmaz ve Windows için npm yolunu önerir ([pnpm kurulumu](https://pnpm.io/installation), `npx get-pnpm`). Yol 2: Node 24.x Corepack içerir (deneysel), `corepack enable`. Çözüldü (19 Ekim 2026): Corepack Node 25.0.0'dan itibaren dağıtılmıyor ([TSC oylaması](https://github.com/nodejs/TSC/pull/1697), [Node 25.0.0 sürüm notu](https://nodejs.org/en/blog/release/v25.0.0)). Program Files altındaki MSI kurulumunda `corepack enable` yönetici terminali ya da `--install-directory` gerektirebilir ([Corepack](https://github.com/nodejs/corepack) README); açık bir "yönetici gerekir" cümlesi yok (Doğrulanamadı). Corepack ile pnpm 12 uyumu da doğrulanamadı |
| .NET SDK | 10.0 (`global.json`) | API ve Yayınlayıcı |
| uv | Güncel | Python 3.13'ü de kurar: `uv python install 3.13` |
| Android Studio | Güncel | Emülatör, Android SDK ve yerel Android derlemesi için JDK |
| EAS CLI | Güncel (`npm install -g eas-cli`) | Bulutta derleme |
| Claude Code | Güncel ([Kurulum](../10-claude-code/01-kurulum.md)) | Geliştirme aracı ([K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)) |
| Hesaplar | Expo hesabı (EAS). iOS cihaz derlemesi için Apple Developer Program (yıllık 99 $). Mağaza için Google Play geliştirici hesabı (tek sefer 25 $) | Ücretler araştırma notu 05'ten ([Kaynakça](../09-kaynakca.md)) |

Kurulum `winget` ile yapılabilir (paket adları Doğrulanacak).

**iOS.** Windows'ta iOS derlemesi yapılmaz. Geliştirme derlemesi EAS Build ile bulutta üretilir; cihaz önce `eas device:create` ile kaydedilir. iOS simülatörü için Mac gerekir.

## 2. Windows hazırlığı (bir kez)

Yönetici PowerShell'de:

```powershell
# Uzun yol desteği (node_modules ve Gradle için)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
git config --global core.longpaths true
git config --global core.autocrlf false        # satır sonlarını .gitattributes yönetir

# Telefonun bağlanacağı Wi-Fi ağı "Özel" olmalı
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private

# Metro ve S3 deposu yalnız özel ağda açılır
New-NetFirewallRule -DisplayName "Mutalaa Metro 8081" -Direction Inbound -Protocol TCP -LocalPort 8081 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Mutalaa S3 8333" -Direction Inbound -Protocol TCP -LocalPort 8333 -Action Allow -Profile Private

# Python dosyalarını UTF-8 açsın (Türkçe Windows'ta varsayılan cp1254)
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

- **Proje konumu (K-31).** Proje kökü masaüstündeki `mutalaa-kit` klasörüdür (`C:\Users\…\OneDrive\Masaüstü\mutalaa-kit`). Yol boşluk, Türkçe karakter ve OneDrive içerir. React Native'in Android derlemesi uzun ve ASCII dışı yollarda kırılabilir ve `LongPathsEnabled` her aracı kurtarmaz; bu yüzden Android geliştirme derlemesi varsayılan olarak EAS bulutunda üretilir. OneDrive eşitlemesi `node_modules`, derleme çıktıları ve `data/` yüzünden dosya kilitleyebilir ve kotayı doldurabilir. Yol kararı A00 aşamasında verildi (19 Ekim 2026): klasör yerinde kalır. Seçenekler şunlardı: klasör yerinde kalır (eşitleme yoğun işlerde duraklatılır), klasörün tamamı OneDrive dışında kısa bir yola (ör. `C:\dev\mutalaa`) taşınır ya da yerel derleme için `subst` ile kısa sürücü harfi tanımlanır (Doğrulanacak). Ayrıntı: [Kurulum](../10-claude-code/01-kurulum.md) §4.
- PowerShell 7 ve Windows Terminal kullanın. Arapça ve Türkçe karakterler bozuk görünürse `[Console]::OutputEncoding = [Text.Encoding]::UTF8` çalıştırın. WSL2 belleği `%UserProfile%\.wslconfig` içinde `[wsl2]` altına `memory=6GB` yazılarak sınırlanır.

## 3. Depoyu alma ve kurulum

Ana geliştirme bilgisayarında proje klasörü zaten yerindedir ve git deposu A00'dan önce açılmıştır (uzak depo özel `karasaid379-hue/mutalaa`). Aşağıdaki adımlar depoyu başka bir bilgisayara klonlarken geçerlidir; o bilgisayarda kısa, ASCII ve OneDrive dışı bir yol seçilir. Bağımlılık kurulumu ilgili aşamalarda (A02, A03, A21) Claude Code tarafından yapılır.

```powershell
cd C:\dev
git clone <depo-adresi> mutalaa
cd mutalaa
Copy-Item .env.example .env
Copy-Item apps\mobile\.env.example apps\mobile\.env.local
Copy-Item pipeline\.env.example pipeline\.env
Copy-Item infra\local\s3.example.json infra\local\s3.json
corepack enable
pnpm install
dotnet tool restore
dotnet restore server\Mutalaa.slnx
cd pipeline; uv sync --frozen --extra arapca; cd ..
```

API ve Yayınlayıcı ana makinede çalışacaksa bağlantı dizesi .NET kullanıcı sırlarına yazılır; parola depoya girmez:

```powershell
dotnet user-secrets --project server/Mutalaa.Api set "ConnectionStrings:Editorial" "Host=localhost;Port=5432;Database=mutalaa;Username=mutalaa;Password=yerel-sifre-degistir"
dotnet user-secrets --project server/Mutalaa.Publisher set "ConnectionStrings:Editorial" "Host=localhost;Port=5432;Database=mutalaa;Username=mutalaa;Password=yerel-sifre-degistir"
dotnet user-secrets --project server/Mutalaa.Publisher set "Storage:SecretKey" "yerel-gizli-degistir"
dotnet user-secrets --project server/Mutalaa.Publisher set "Storage:PublicBaseUrl" "http://192.168.1.50:8333/mutalaa"
```

`Storage:PublicBaseUrl` manifestteki mutlak paket adreslerinin tabanıdır ([Backend API](./05-backend-api.md) §10.5). Bilgisayarın LAN IP adresi değişirse bu değer güncellenir ve `publish` yeniden çalıştırılır.

## 4. `docker-compose.yml`

Varsayılan komut (`docker compose up -d`) yalnız `postgres`, `s3` ve `s3-init` servislerini başlatır. API, editör ve Yayınlayıcı `app` profilindedir: `docker compose --profile app up -d --build`. Günlük geliştirmede bu üçü genellikle ana makinede çalışır (bölüm 7).

```yaml
# docker-compose.yml
name: mutalaa

services:
  postgres:
    image: postgres:${POSTGRES_TAG:-18}
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C.UTF-8"
      TZ: UTC
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql          # PostgreSQL 18 imajında birim burada
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20

  s3:
    # K-21: yerel S3 deposu SeaweedFS (Doğrulanacak: imaj, etiket, bayraklar, s3.json biçimi)
    image: chrislusf/seaweedfs:${SEAWEEDFS_TAG:-latest}
    restart: unless-stopped
    command: "server -dir=/data -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json"
    ports:
      - "0.0.0.0:${S3_PORT:-8333}:8333"     # telefon paketleri LAN üzerinden okur
    volumes:
      - s3data:/data
      - ./infra/local/s3.json:/etc/seaweedfs/s3.json:ro

  s3-init:
    image: amazon/aws-cli:latest
    depends_on: [s3]
    restart: "no"
    environment:
      AWS_ACCESS_KEY_ID: ${S3_ACCESS_KEY}
      AWS_SECRET_ACCESS_KEY: ${S3_SECRET_KEY}
      AWS_DEFAULT_REGION: us-east-1
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        for i in $$(seq 1 30); do
          aws --endpoint-url http://s3:8333 s3api head-bucket --bucket ${S3_BUCKET} && exit 0
          aws --endpoint-url http://s3:8333 s3api create-bucket --bucket ${S3_BUCKET} && exit 0
          echo "S3 deposu bekleniyor ($$i)"; sleep 2
        done
        exit 1

  api:
    profiles: ["app"]
    build: { context: ., dockerfile: server/Mutalaa.Api/Dockerfile }
    environment:
      ASPNETCORE_ENVIRONMENT: Development
      ASPNETCORE_HTTP_PORTS: "8080"
      ConnectionStrings__Editorial: "Host=postgres;Port=5432;Database=${POSTGRES_DB};Username=${POSTGRES_USER};Password=${POSTGRES_PASSWORD}"
      Mutalaa__Features__Editor: "true"
      Mutalaa__Features__Public: "false"
      Mutalaa__Seed__AdminEmail: ${MUTALAA_ADMIN_EMAIL}
      Mutalaa__Seed__AdminPassword: ${MUTALAA_ADMIN_PASSWORD}
    ports:
      - "127.0.0.1:${API_PORT:-5080}:8080"
    depends_on:
      postgres: { condition: service_healthy }

  editor:
    profiles: ["app"]
    build: { context: ., dockerfile: apps/editor/Dockerfile }
    ports:
      - "127.0.0.1:${EDITOR_PORT:-5174}:80"
    depends_on: [api]

  publisher:
    profiles: ["app"]
    build: { context: ., dockerfile: server/Mutalaa.Publisher/Dockerfile }
    command: ["watch"]
    environment:
      ConnectionStrings__Editorial: "Host=postgres;Port=5432;Database=${POSTGRES_DB};Username=${POSTGRES_USER};Password=${POSTGRES_PASSWORD}"
      Storage__ServiceUrl: http://s3:8333
      Storage__AccessKey: ${S3_ACCESS_KEY}
      Storage__SecretKey: ${S3_SECRET_KEY}
      Storage__Bucket: ${S3_BUCKET}
      Storage__PublicBaseUrl: http://${DEV_LAN_IP}:${S3_PORT:-8333}/${S3_BUCKET}
      Signing__dev__PrivateKey: ${PUBLISHER_DEV_SIGNING_KEY}
    volumes:
      - ./data/packs:/work
    depends_on:
      postgres: { condition: service_healthy }
      s3-init: { condition: service_completed_successfully }

volumes:
  pgdata:
  s3data:
```

`infra/local/s3.json` yerel kimlik bilgisini ve anonim okumayı tanımlar. Gizli anahtar taşıdığı için depoya girmez: depoda şablonu `infra/local/s3.example.json` durur (yer tutucu anahtarlar `.env.example` ile aynı), `infra/local/s3.json` `.gitignore` içindedir ve şablondan kopyalanır (bölüm 3). Anahtarlar `.env` içindeki `S3_ACCESS_KEY` ve `S3_SECRET_KEY` ile aynı olmalıdır. Şablonun içeriği:

```json
{
  "identities": [
    {
      "name": "mutalaa-yerel",
      "credentials": [{ "accessKey": "mutalaa", "secretKey": "yerel-gizli-degistir" }],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    },
    { "name": "anonymous", "actions": ["Read"] }
  ]
}
```

Notlar:
- **PostgreSQL 18 birimi.** Resmî imajda `PGDATA` 18'den itibaren sürüme bağlıdır (`/var/lib/postgresql/18/docker`) ve birim `/var/lib/postgresql` noktasına bağlanır ([Docker Hub postgres](https://hub.docker.com/_/postgres); araştırma raporu dışında, 18 Ekim 2026'da kontrol edildi). Eski örneklerdeki `/var/lib/postgresql/data` bağlaması kullanılmaz.
- **`C.UTF-8` yerel ayarı.** Sıralama kod noktasına göredir ve glibc güncellemesiyle değişmez. Türkçe sıralama gereken sorgu `COLLATE "tr-x-icu"` ile açıkça yazılır (imajdaki ICU desteği Doğrulanacak).
- **S3 deposu.** MinIO topluluk sürümü Ekim 2025'ten beri Docker imajı yayımlamıyor ve Aralık 2025'ten beri bakım kipinde ([linuxiac](https://linuxiac.com/minio-ends-active-development/), [ayedo](https://ayedo.de/en/posts/minio-im-maintenance-mode/)). Örnek bu yüzden SeaweedFS kullanır; diğer aday Garage'dır. Depo değişimi yalnız `.env` ve `Storage:ServiceUrl` değişikliğidir ([Genel mimari](./01-genel-mimari.md)).
- **Dockerfile'lar.** API ve Yayınlayıcı `mcr.microsoft.com/dotnet/sdk:10.0` ile derlenir (`global.json`, `.editorconfig` ve `server/` kopyalanır, `dotnet publish`); API `aspnet:10.0`, Yayınlayıcı `runtime:10.0` imajında çalışır ve `packages/content-schema/sql/` klasörünü de taşır. Editör `node:24-alpine` ile derlenir, `nginx:stable-alpine` ile sunulur; nginx `/api/` isteklerini `http://api:8080` adresine aktarır. `.dockerignore` `**/node_modules`, `**/bin`, `**/obj`, `data/` ve `.git` klasörlerini dışarıda bırakır.

## 5. Ortam dosyaları

```dotenv
# .env.example (kök; docker compose okur)
POSTGRES_TAG=18
POSTGRES_USER=mutalaa
POSTGRES_PASSWORD=yerel-sifre-degistir
POSTGRES_DB=mutalaa
POSTGRES_PORT=5432

SEAWEEDFS_TAG=latest
S3_PORT=8333
S3_ACCESS_KEY=mutalaa
S3_SECRET_KEY=yerel-gizli-degistir
S3_BUCKET=mutalaa

API_PORT=5080
EDITOR_PORT=5174
MUTALAA_ADMIN_EMAIL=admin@mutalaa.local
MUTALAA_ADMIN_PASSWORD=yerel-yonetici-sifresi-degistir

# Telefonun ulaşacağı bilgisayar adresi
DEV_LAN_IP=192.168.1.50
# Konteynerdeki Yayınlayıcı için dev imza anahtarı (keys generate çıktısı; depoya girmez)
PUBLISHER_DEV_SIGNING_KEY=
```

```dotenv
# apps/mobile/.env.example → .env.local (app.config.ts okur; Mobil mimari bölüm 10)
APP_FLAVOR=dev
# Telefon ve emülatör: bilgisayarın LAN IP adresi (manifestteki paket adresleri de bu IP'yi taşır)
MANIFEST_URL=http://192.168.1.50:8333/mutalaa/dev/manifest.json
SENTRY_DSN=
```

```dotenv
# pipeline/.env.example (değişken adları: İçerik hattı §3)
MUTALAA_DB_URL=postgresql://mutalaa:yerel-sifre-degistir@localhost:5432/mutalaa
ANTHROPIC_API_KEY=          # yalnız yapay zekâ taslakları; embed_ok kapalı kaynak gönderilmez
PYTHONUTF8=1
```

`.env`, `.env.local`, `pipeline/.env` ve `infra/local/s3.json` dosyaları `.gitignore` içindedir. `MANIFEST_URL` ve `SENTRY_DSN` uygulama paketine girer; bu dosyaya gizli değer yazılmaz.

## 6. İlk çalıştırma

1. **Altyapıyı başlatın.**
   ```powershell
   docker compose up -d
   docker compose ps -a       # postgres "healthy", s3-init "exited (0)" olmalı; -a çıkmış konteyneri de listeler
   ```
2. **Göçleri uygulayın.**
   ```powershell
   $env:ASPNETCORE_ENVIRONMENT = "Development"
   dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
   ```
3. **Rolleri ve ilk yöneticiyi oluşturun.** `seed` komutu idempotenttir; e-posta ve parola `Mutalaa:Seed:*` ayarlarından okunur.
   ```powershell
   dotnet user-secrets --project server/Mutalaa.Api set "Mutalaa:Seed:AdminEmail" "admin@mutalaa.local"
   dotnet user-secrets --project server/Mutalaa.Api set "Mutalaa:Seed:AdminPassword" "yerel-yonetici-sifresi-degistir"
   dotnet run --project server/Mutalaa.Api -- seed
   ```
4. **Kur'an metnini yükleyin.** Komutlar [İçerik hattı](../04-icerik/02-icerik-hatti.md) §4'tedir.
   ```powershell
   cd pipeline
   uv run mutalaa sources check
   uv run mutalaa ingest tanzil --variant uthmani
   uv run mutalaa normalize --source tanzil-uthmani
   uv run mutalaa anchor --source tanzil-uthmani
   uv run mutalaa qa run --source tanzil-uthmani
   uv run mutalaa export pg --source tanzil-uthmani
   cd ..
   ```
5. **API'yi ve editörü açın.**
   ```powershell
   dotnet watch --project server/Mutalaa.Api        # http://localhost:5080/scalar/v1
   pnpm --filter @mutalaa/editor dev                 # http://localhost:5173 (ayrı terminal)
   ```
6. **İmza anahtarı üretip paketleri yayımlayın.** Anahtar bir kez üretilir; özel anahtar kullanıcı sırlarına yazılır, açık anahtar `apps/mobile/src/packs/keys.ts` içindeki `dev` listesine eklenir (öneri; anahtar yönetimi Doğrulanacak).
   ```powershell
   dotnet run --project server/Mutalaa.Publisher -- keys generate --flavor dev
   dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
   curl.exe http://localhost:8333/mutalaa/dev/manifest.json
   ```
7. **Gömülü `core` paketini alın.** Betik manifest imzasını ve paketin sha256 değerini doğrular, paketi `apps/mobile/assets/db/` klasörüne yazar.
   ```powershell
   $env:MANIFEST_URL = "http://localhost:8333/mutalaa/dev/manifest.json"
   pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs
   ```
8. **Geliştirme derlemesini kurun.**
   - Android, bulutta: `cd apps/mobile; eas build --profile development --platform android`; çıkan APK telefona kurulur.
   - Android, yerelde (isteğe bağlı): `pnpm --filter @mutalaa/mobile exec expo run:android`.
   - iOS: `eas device:create`, ardından `eas build --profile development --platform ios`.
9. **Metro'yu başlatın ve bağlanın.**
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi" | Select-Object IPAddress
   $env:REACT_NATIVE_PACKAGER_HOSTNAME = "192.168.1.50"   # birden çok ağ bağdaştırıcısı varsa
   pnpm --filter @mutalaa/mobile start
   ```
   Telefondaki geliştirme derlemesi QR kodla Metro'ya bağlanır. Emülatör bilgisayarın LAN IP adresine de ulaşır; manifestteki paket adresleri bu IP'yi taşıdığı için emülatörde de LAN IP kullanılır. Metro'ya emülatörden `10.0.2.2:8081`, USB ile bağlı Android cihazdan `adb reverse tcp:8081 tcp:8081` sonrası `localhost:8081` ile de bağlanılır.
10. **Doğrulayın.** Ayarlar › Depolama ekranı `dev` manifestindeki paketleri listeler. Derin bağlantı Oku sekmesinde 2:255'i açar:
    ```powershell
    adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"
    ```

`dev` geliştirme derlemesi yerel ağdaki düz HTTP adresine bağlanır. `internal` ve `public` derlemeler yalnız HTTPS kullanır.

## 7. Günlük akış

| İş | Komut |
|---|---|
| Altyapı | `docker compose up -d` |
| API | `dotnet watch --project server/Mutalaa.Api` |
| Editör | `pnpm dev:editor` |
| Mobil | `pnpm dev:mobile` |
| Paketleri yenile | `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev` ya da editörde "Yayınla" + `docker compose --profile app up -d publisher` |
| Tüm denetimler | `pnpm lint; pnpm typecheck; pnpm test; dotnet test server/Mutalaa.slnx; cd pipeline; uv run pytest` |
| Durdur | `docker compose down` (birimler kalır). `docker compose down -v` birimleri ve veritabanını siler; önce yedek alın |

## 8. Örnek veri

| Ne | Nasıl | Kural |
|---|---|---|
| `editor` ve `admin` rolleri, ilk yönetici | `Mutalaa.Api -- seed` | İdempotent; parola yalnız kullanıcı sırlarında ya da `.env`'de |
| `source` satırları ve lisans durumları | Hattın `ingest` adımı | Değerler [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) ile aynı |
| Tanzil metni | `ingest tanzil --variant uthmani` | Metin dağıtıldığı gibi saklanır, NFC bile uygulanmaz; atıf ve tanzil.net bağlantısı korunur ([Tanzil şartları](https://raw.githubusercontent.com/OpenITI/0025AH/master/data/0001Quran/0001Quran.Mushaf/0001Quran.Mushaf.Tanzil001-ara1.mARkdown)) |
| Elmalılı meali | OCR çıktısı hazır olunca | Uydurma ya da yer tutucu meal metni yazılmaz |
| Uçtan uca test fikstürleri: metin paketi `test-kucuk`, ses paketi `ses-test` (kaynağı `test-ses`) | Slug `test-` ile başlar, durum `serbest`; içerik kendi ürettiğimiz sentetik metin ve tondur | `dev` ve `internal` derlemeye girer; Yayınlayıcı `test-` kaynaklarını `public` derlemeye hiçbir durumda almaz ([Backend API](./05-backend-api.md) P-12; [Test stratejisi](../07-yayin/03-test-stratejisi.md) §9) |
| Arayüz geliştirmek için sentetik eser kaynakları (ör. `test-tefsir-ornek`, `test-risale-ornek`) | Slug `test-` ile başlar, durum `ic_kullanim` | Yalnız `dev` derlemesinde görünür; `public`'e P-12 ile hiç girmez |

Tohumlama birim ve kaynaklarda çapa ya da slug üzerinden "varsa güncelle, yoksa ekle" mantığıyla çalışır; iki kez çalıştırmak aynı sonucu verir.

## 9. Yedekleme ve geri yükleme

Editoryal veritabanı yedeklenir, çünkü editör kararları yeniden üretilemez. Altın metinler ve altın setler (`data/gold/`) de insan emeğidir; betik onları da arşivler. `data/raw/` ve `data/llm-cache/` de yedeklenir; `data/` altında neyin yedeklendiği [Proje yapısı](./03-proje-yapisi.md) §1.1'dedir. S3 deposu yedeklenmez; Yayınlayıcı paketleri yeniden üretir.

```powershell
# scripts/backup-db.ps1
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
New-Item -ItemType Directory -Force data/backups | Out-Null
docker compose exec -T postgres sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /tmp/mutalaa.dump'
docker compose cp postgres:/tmp/mutalaa.dump "data/backups/mutalaa-$stamp.dump"
docker compose exec -T postgres rm /tmp/mutalaa.dump
if (Test-Path data/gold) { Compress-Archive -Path data/gold -DestinationPath "data/backups/gold-$stamp.zip" }
```

```powershell
# scripts/restore-db.ps1 (dosya adı parametreyle verilir)
param([string]$File)
docker compose cp $File postgres:/tmp/restore.dump
docker compose exec -T postgres sh -c 'pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists /tmp/restore.dump'
```

- Kullanıcı ve veritabanı adı konteynerin kendi ortam değişkenlerinden (`POSTGRES_USER`, `POSTGRES_DB`) okunur; `.env` değişince betik değişmez. Komut tek tırnak içindedir, bu yüzden değişkenleri PowerShell değil konteynerdeki `sh` açar. İç çift tırnak kullanılmaz, çünkü Windows PowerShell 5.1 yerel komuta geçen bağımsız değişkendeki çift tırnağı kaçışsız aktarır; bu iki değer `.env`'de boşluksuz yazılır.
- Elle çalıştırılan örnekler (bölüm 3'teki bağlantı dizeleri, aşama dosyalarındaki `psql -U mutalaa -d mutalaa` komutları) `.env.example` varsayılanlarını kullanır; `.env`'de bu adlar değiştiyse komutta da değiştirilir.
- Döküm konteyner içinde dosyaya yazılıp `docker compose cp` ile alınır; Windows PowerShell 5.1'de ikili çıktı yönlendirmesi (`>`) dosyayı bozabilir.
- Görev Zamanlayıcı her gün yedek alır; 7 günlük ve 4 haftalık yedek saklanır; haftada bir kopya bilgisayar dışına çıkarılır. Ayda bir yedek boş bir veritabanına geri yüklenip denenir. Büyük göçten ve `docker compose down -v` komutundan önce elle yedek alınır.

## 10. Sık karşılaşılan sorunlar

### 10.1 Türkçe yerel ayar (İ/ı)

Türkçe Windows'ta .NET'in `CurrentCulture` değeri `tr-TR`, Node'un varsayılan yerel ayarı Türkçe, Python'un dosya kodlaması cp1254'tür. Docker içindeki Linux ve CI yerel ayarsız çalışır. Aynı kod iki ortamda farklı sonuç verebilir.

| Ortam | Hatalı kullanım | Sonuç | Doğru kullanım |
|---|---|---|---|
| .NET | `"id".ToUpper()` (tr-TR) | `"İD"` | `ToUpperInvariant()`; karşılaştırmada `StringComparison.Ordinal` ya da `OrdinalIgnoreCase` |
| .NET | `s.IndexOf("x")`, `s.StartsWith("x")` | Kültüre duyarlı karşılaştırma | `StringComparison.Ordinal` verin |
| .NET | `double.Parse("1.5")`, `x.ToString()` | tr-TR'de ondalık ayırıcı virgüldür | `CultureInfo.InvariantCulture` |
| .NET | `new Regex(p, RegexOptions.IgnoreCase)` | tr-TR'de `i` ve `I` eşleşmesi değişir | `RegexOptions.CultureInvariant` ekleyin |
| JavaScript | `'İ'.toLowerCase()` | `'i̇'` (i + U+0307, iki kod noktası) | Önce `İ→i`, `I→ı` açık eşlemesi, sonra `toLowerCase()` (`packages/search`) |
| JavaScript | `s.toLocaleUpperCase()`, `a.localeCompare(b)` | Sonuç cihazın diline bağlıdır | Yerel ayarı açıkça verin ya da sıralı karşılaştırın; ESLint kuralı engeller ([Proje yapısı](./03-proje-yapisi.md)) |
| Python | `'İ'.lower()` | `'i̇'` (iki kod noktası) | Açık eşleme (`mutalaa_pipeline.normalize`) |
| Python | `open(yol)` | Türkçe Windows'ta cp1254 ile okur | `encoding="utf-8"`; `PYTHONUTF8=1` |
| PostgreSQL | `lower()` ve `ILIKE` ile Türkçe arama | `C.UTF-8` yerel ayarında Türkçe kurala uymaz | Hattın ürettiği `search_text` ve C# normalizasyonu; Türkçe sıralamada `COLLATE "tr-x-icu"` |
| Markdown | `### K-25 · İlkeler` başlığı | Bağlantı `#k-25--i̇lkeler` olur | Bu dokümanlardaki karar bağlantıları bu biçimi izler |

Kurallar:
- Kültürden bağımsızlık varsayılandır. Türkçe kural yalnız amaçlanan yerde ve açıkça (`tr`, `tr-TR`) verilir.
- Normalizasyon üç dilde açık eşleme tablosuyla yazılır ve çalışma zamanının yerel ayar verisine bırakılmaz. Hermes'te `toLocaleLowerCase('tr')` ve `String.prototype.normalize` davranışı cihazda Doğrulanacak. Öneri: `dev` derlemesinin geliştirici menüsü test vektörlerini cihazda da koşturur.
- .NET uygulamaları açılışta varsayılan kültürü `InvariantCulture` yapar. CA1304, CA1305, CA1307, CA1309, CA1310 ve CA1311 hata düzeyindedir. Domain testleri `tr-TR` kültüründe de koşar ([Backend API](./05-backend-api.md)).
- CI TypeScript testlerini `LANG=tr_TR.UTF-8` ile, Python testlerini Windows'ta da koşturur ([Proje yapısı](./03-proje-yapisi.md)).

### 10.2 Unicode, satır sonu, dosya adı

- `.gitattributes` metin dosyalarında LF, `*.ps1` ve `*.cmd` dosyalarında CRLF kullanır. CRLF'li kabuk betiği konteynerde `/bin/sh^M` hatası verir.
- Dosyalar BOM'suz UTF-8 kaydedilir. BOM'lu JSONL test vektörü Python'da ilk satırı bozar.
- Hazır kaynak metni dağıtıldığı gibi saklanır. Tanzil'e NFC bile uygulanmaz, çünkü NFC şedde ile harekenin sırasını değiştirir. NFC yalnız kendi ürettiğimiz metinlere (transkripsiyon, kelime anlamı) ilk kayıtta uygulanır ([K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)). Editörde ya da betikte kaynak metni açıp kaydetmek onu sessizce normalize edebilir; Tanzil dosyaları yalnız hat üzerinden okunur.
- Çapa ofsetleri kanonik metnin kod noktalarıdır. JavaScript ve C# dizeleri UTF-16 olduğu için ofset `Array.from` ya da `Rune` ile hesaplanır. Arama için normalize metin ayrı `search_text` sütunundadır.
- Depodaki dosya adları ASCII'dir. Windows büyük ve küçük harfi ayırmaz; yalnız harf büyüklüğünü değiştiren yeniden adlandırma `git mv` ile yapılır.

### 10.3 Port, ağ ve güvenlik duvarı

| Belirti | Neden | Çözüm |
|---|---|---|
| `bind: An attempt was made to access a socket in a way forbidden…` | Hyper-V ya da WSL ayrılmış port aralığı | `netsh interface ipv4 show excludedportrange protocol=tcp` ile bakın; `.env` içinde portu değiştirin |
| 5432 kullanımda | Bilgisayarda kurulu PostgreSQL servisi | Servisi durdurun ya da `POSTGRES_PORT=5433` |
| Telefon Metro'ya bağlanamıyor | Ağ "Ortak", güvenlik duvarı, yanlış bağdaştırıcı IP'si, VPN, misafir ağında istemci yalıtımı | Ağı Özel yapın; kuralları ekleyin; `REACT_NATIVE_PACKAGER_HOSTNAME` verin; VPN'i kapatın; USB'de `adb reverse` |
| Uygulama manifesti ya da paketi indiremiyor | `MANIFEST_URL` içinde `localhost`; LAN IP değişti | LAN IP kullanın; IP değiştiyse `Storage:PublicBaseUrl` güncellenir ve `publish` yeniden çalıştırılır |
| Uygulama manifesti reddediyor | İmza tutmuyor; uygulamadaki `dev` açık anahtarı eski | `keys.ts` içindeki açık anahtarı `keys generate` çıktısıyla karşılaştırın |
| S3 isteği `RequestTimeTooSkewed` ile reddediliyor | Uykudan sonra WSL2 saati kaymış olabilir (Doğrulanacak) | `wsl --shutdown`, ardından Docker Desktop'ı yeniden başlatın |
| PowerShell'de `curl` farklı davranıyor | Windows PowerShell'de `curl` başka bir komutun takma adıdır | `curl.exe` yazın |
| Konteynerden ana makineye erişilemiyor | `localhost` konteynerin kendisidir | `host.docker.internal`; konteynerler arasında servis adı (`postgres`, `s3`) |

### 10.4 Araçlar

- **Android derlemesinde yol hatası:** depoyu kısa bir yola taşıyın. **pnpm ve Metro:** sembolik bağ sorununda `.npmrc` içindeki `node-linker=hoisted` satırına bakın.
- **`expo prebuild`** SDK 57'den beri yerel klasörleri varsayılan olarak temizler ([Expo SDK 57](https://expo.dev/changelog/sdk-57)); `android/` ve `ios/` depoya girmez.
- **EF Core ve saat:** `timestamptz` sütununa `DateTimeKind.Utc` değer yazılır; yerel saat (UTC+3) kullanılmaz.
- **SQLite dosya kilidi:** Yayınlayıcı paketi taşımadan önce bağlantıyı kapatır (`Pooling=False`); Windows açık dosyayı taşıtmaz.
- **CAMeL Tools verisi** ayrıca indirilir: `camel_data -i light` ([PyPI camel-tools](https://pypi.org/project/camel-tools/)).

## 11. Açık sorular

1. ~~K-21 yerelde MinIO der.~~ Çözüldü: K-21 güncellendi, yerel depo SeaweedFS. Garage yedek seçenek olarak kalır.
2. pnpm `node-linker=hoisted` yerine izole kurulum Expo SDK 57'de çalışıyor mu?
3. SeaweedFS `server -s3` kipinin anonim okuma ve Range isteklerini mobil indirme kuyruğuyla sorunsuz karşıladığı ilk kurulumda doğrulanmalı.

## İlgili dosyalar

- [Genel mimari](./01-genel-mimari.md) · [Teknoloji yığını](./02-teknoloji-yigini.md) · [Proje yapısı](./03-proje-yapisi.md) · [Backend API](./05-backend-api.md)
- [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Depolama yöneticisi](../06-mobil/03-depolama-yoneticisi.md)
- [İçerik hattı](../04-icerik/02-icerik-hatti.md) · [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md)
- [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [Arama](../03-veri/05-arama-fts5.md) · [Çapa şeması](../03-veri/01-capa-semasi.md)
