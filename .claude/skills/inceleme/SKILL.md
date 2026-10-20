---
name: inceleme
description: >-
  Commit öncesi inceleme yapar; değişen alanlara göre hızlı denetimleri çalıştırır, inceleyici ve
  gereken denetçi ajanları (metin, lisans, arayüz) devreye alır, bulguları önem sırasıyla raporlar ve
  onayla düzeltir. Commit öncesinde, bir aşamanın inceleme adımında ya da kullanıcı /inceleme
  yazdığında kullan.
argument-hint: "[kapsam: boş = çalışma ağacı | staged | <dosya/klasör>]"
---

# Commit öncesi inceleme

Kapsam: `$ARGUMENTS` (boşsa çalışma ağacındaki bütün değişiklikler)

## 1. Kapsamı çıkar

- `git status --short`, `git diff --stat`, `git diff --staged --stat`.
- Değişen dosyaları alanlara ayır: `apps/mobile`, `apps/editor`, `apps/web`, `packages/*`, `shared/test-vectors`, `server/`, `pipeline/`, `docs/`, `.claude/`, altyapı.

## 2. Hızlı denetimler (yalnız değişen alanlar)

| Alan | Komut |
|---|---|
| TypeScript | `pnpm lint` · `pnpm typecheck` · `pnpm test` (Turborepo önbelleği değişmeyen paketleri atlar) |
| .NET | `dotnet build server/Mutalaa.slnx` · `dotnet test --solution server/Mutalaa.slnx` · `dotnet format server/Mutalaa.slnx --verify-no-changes` |
| Python | `cd pipeline && uv run ruff check . && uv run ruff format --check . && uv run pytest` |
| Test vektörleri | üç dilin vektör testleri (bkz. `test-vektoru` becerisi) |
| Belgeler | `node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs` |
| Kit | `node --test ".claude/hooks/test/*.test.mjs"` |

Henüz kurulmamış bir alanın komutu çalışmazsa bunu not et; hata sayma.

## 3. Ajanlar

- Her durumda `inceleyici`.
- Metin, çapa, normalizasyon, arama ya da Kur'an verisi değiştiyse `metin-denetcisi`.
- Kaynak kaydı, paket, manifest, görünürlük kodu ya da bağımlılık değiştiyse `lisans-denetcisi`.
- Ekran ya da bileşen değiştiyse `arayuz-denetcisi`.
- Bağımsız denetçileri paralel çalıştır.

## 4. Rapor ve düzeltme

- Bulguları birleştir, tekrarları ayıkla, önem sırasıyla listele: **Engelleyici**, **Önemli**, **Öneri**. Her bulgu `dosya:satır`, sorun, kural ve öneri taşır.
- Engelleyici ve önemli bulgular için düzeltme planını göster; kullanıcı onaylarsa düzelt ve ilgili denetimi yeniden çalıştır.
- Sonuç satırı: "Commit'e hazır" ya da "Hazır değil: … engelleyici bulgu kaldı".
