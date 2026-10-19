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
- **CI.** İş akışları `ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `eas-build.yml` dosyalarıdır. Eylem ana sürümleri yazım günü `arastirmaci` ile doğrulanır. Sırlar (`EXPO_TOKEN`) yalnız GitHub sırlarında durur.
