---
name: ef-goc
description: >-
  Mütâlaa editoryal veritabanında (PostgreSQL 18, EF Core 10 + Npgsql) şema değişikliği ve göç iş
  akışı; göç ekleme, idempotent SQL betiğini gözden geçirme, uygulama, Testcontainers göç testleri,
  yıkıcı değişikliklerde genişlet-taşı-daralt ve adlandırma kuralları. server/ altında varlık, tablo,
  sütun, indeks ya da enum değiştiğinde kullan.
---

# EF Core göç iş akışı

Kaynaklar: [Editoryal veritabanı](../../../docs/03-veri/02-editoryal-veritabani.md) §12, [Backend API](../../../docs/02-mimari/05-backend-api.md) §7, [Test stratejisi](../../../docs/07-yayin/03-test-stratejisi.md) §6.

## Kurallar

- Şemanın tek sahibi `server/Mutalaa.Infrastructure/Migrations` altındaki EF Core göçleridir. Ayrı SQL göç aracı yok; ham SQL gerekiyorsa `migrationBuilder.Sql` içinde.
- Her değişiklik en çok bir göç ekler. Uygulanmış göç değiştirilmez; düzeltme yeni göçle yapılır.
- Adlar snake_case (`EFCore.NamingConventions`), tablo adları tekil ve `ToTable("source")` gibi açık. Identity tabloları `kimlik` şemasında.
- PostgreSQL enum'ları (`license_status`, `xref_status` …) C# enum'larına Npgsql eşlemesiyle bağlanır; değerler `packages/content-schema` içindeki ortak enum JSON'uyla aynıdır ve testle denetlenir.
- Zaman `timestamptz` ve UTC (`DateTimeKind.Utc`); eşzamanlılık belirteci `xmin`.
- Yıkıcı değişiklik üç adımda: genişlet (yeni sütun/tablo) → taşı (veri) → daralt (eskiyi kaldır), ayrı göçlerle.
- API açılışında otomatik göç yoktur. CI ve canlıda göç paketi (`migrations bundle`) kullanılır.
- Göç adı İngilizce PascalCase ve ne yaptığını söyler: `AddXrefVote`, `CreateReviewQueue`.

## Adımlar

```bash
dotnet tool restore
# 1. Modeli değiştir (Domain varlığı, Infrastructure yapılandırması).
# 2. Göç ekle
dotnet ef migrations add <GocAdi> --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
# 3. Üretilen kodu oku; beklenmeyen tablo, sütun ya da veri kaybı var mı?
# 4. SQL'i gözden geçir
dotnet ef migrations script --idempotent --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api --output .tmp/goc.sql
# 5. Yerel veritabanına uygula (yıkıcıysa önce yedek: scripts/backup-db.ps1)
ASPNETCORE_ENVIRONMENT=Development dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api
# 6. Testler (Testcontainers postgres:18)
dotnet test --solution server/Mutalaa.slnx
```

Kit ayarları Claude Code'un her komutuna `ASPNETCORE_ENVIRONMENT=Development` ve `DOTNET_ENVIRONMENT=Development` verir (`.claude/settings.json` › `env`); bağlantı dizesi kullanıcı sırlarından yalnız bu ortamda okunur. `export` komutlar arasında kalmaz. Elle açılan terminalde: Git Bash'te değeri komutun başına yazın (5. adımdaki gibi), PowerShell'de `$env:ASPNETCORE_ENVIRONMENT = "Development"` sonra aynı komut.

## Bitti sayılmadan önce

- [ ] `MigrationTests`: boş `postgres:18` kabına bütün göçler uygulanır, bekleyen göç kalmaz.
- [ ] Şema dökümü (`pg_dump --schema-only`) depodaki anlık görüntüyle karşılaştırıldı; anlık görüntü bilerek güncellendiyse farkı rapora yaz.
- [ ] Enum tutarlılık testi geçti (PostgreSQL, C#, Python, TypeScript).
- [ ] İçerik hattının bütünleşik testleri yeni şemaya karşı geçti (`cd pipeline && uv run pytest`).
- [ ] Geri alma yolu yazıldı (önceki göçe `dotnet ef database update <OncekiGoc>` ya da yedekten dönüş).
