---
paths:
  - "docker-compose.yml"
  - "infra/**"
  - "scripts/**"
  - ".github/**"
  - ".env.example"
  - "**/.env.example"
---

# Altyapı, betik ve CI kuralları

Kaynak: [Yerel geliştirme](../../docs/02-mimari/04-yerel-gelistirme.md), [Proje yapısı](../../docs/02-mimari/03-proje-yapisi.md) §7.

- **Docker Compose.** Varsayılan servisler `postgres`, `s3`, `s3-init`; `api`, `editor`, `publisher` `app` profilindedir. PostgreSQL portu yalnız `127.0.0.1` adresine açılır; S3 deposu telefonun erişmesi için `0.0.0.0:8333` üzerindedir. PostgreSQL 18 birimi `/var/lib/postgresql` noktasına bağlanır. Veriler adlı birimlerdedir.
- **Gizli değerler.** Compose dosyası ve `.env.example` yalnız yer tutucu değer taşır (`yerel-sifre-degistir` gibi). Gerçek değerler git dışı `.env` dosyasındadır.
- **Yıkıcı komutlar.** `docker compose down -v` veritabanını siler; önce `scripts/backup-db.ps1` ile yedek alınır ve kullanıcı onaylar.
- **PowerShell betikleri** CRLF satır sonuyla kaydedilir ve `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/<betik>.ps1` ile çalıştırılır. İkili çıktı `>` ile yönlendirilmez; dosya konteynerde yazılıp `docker compose cp` ile alınır.
- **CI.** İş akışları `.github/workflows/` altında `ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `ci-workflows.yml`, `pr-title.yml`, `eas-build.yml` dosyalarıdır; `.github/dependabot.yml` ve `scripts/ci/` (başlık ve lisans betikleri) yanındadır. Eylem sürümleri yazım günü `arastirmaci` ile doğrulanır.
  - Eylemler tam commit SHA'sıyla ve `# vX.Y.Z` yorumuyla sabitlenir; runner'lar `ubuntu-24.04` ve `windows-2025` (`-latest` değil); `uv` ve `eas-cli` sürümleri sabittir.
  - `permissions` en dar tutulur (`contents: read`, `pr-title` için iş düzeyinde). `pull_request_target` ve `workflow_run` kullanılmaz. `actions/checkout` `persist-credentials: false` ile çalışır.
  - `${{ github.event.* }}` ve `${{ inputs.* }}` değerleri `run:` içine gömülmez, `env:` ile okunur.
  - Sırlar (`EXPO_TOKEN`) yalnız GitHub sırlarında durur ve yalnız `eas-build.yml` içinde `secrets.EXPO_TOKEN` olarak geçer. Bu iş akışı ücretlidir: `mobile-v*` etiketi itmek üretim derlemesi başlatır (kural 11); `eas submit` hiçbir iş akışında yoktur.
  - Kilit dosyaları birebir kullanılır (`pnpm install --frozen-lockfile`, `dotnet restore --locked-mode`, `uv sync --locked`).
  - Değişiklikten sonra: `MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/repo" -w /repo rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 -color` (Git Bash) ve `uvx check-jsonschema@0.39.0 --builtin-schema vendor.github-workflows .github/workflows/*.yml`.
  - Lisans kapısı yalnız dağıtılan ve sunulan kodu denetler (`scripts/ci/check-licenses.mjs`); istisnalar `scripts/ci/license-exceptions.json` içinde kaynakla yazılır.
