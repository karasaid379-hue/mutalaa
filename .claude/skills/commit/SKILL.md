---
name: commit
description: >-
  Mütâlaa değişikliklerini Conventional Commits biçiminde (İngilizce, proje kapsam listesiyle) anlamlı
  birimlere bölerek commit eder; gizli ve git dışı dosyaları dışarıda bırakır; push yapmaz. Bir aşamanın
  ya da işin sonunda, inceleme yapıldıktan sonra veya kullanıcı /commit yazdığında kullan.
argument-hint: "[isteğe bağlı: kısa açıklama ya da kapsam]"
---

# Commit

İpucu: `$ARGUMENTS`

## 1. Hazırlık

- `git status --short` ve `git diff --stat`. Depo yoksa dur ve A00 aşamasını öner.
- Değişiklikleri anlamlı birimlere ayır (ör. üretim kodu ve testi birlikte; belge düzeltmesi ayrı). Bir commit tek bir amaca hizmet eder.
- Dışarıda bırak: `.env`, `**/.env.local`, kökteki `data/` (`shared/data/` izlenir), `.tmp/`, `CLAUDE.local.md`, `.claude/settings.local.json`, derleme çıktıları. Bu dosyalardan biri izleniyorsa dur ve kullanıcıya söyle.
- Gizli değer taraması: eklenen satırlarda parola, anahtar, belirteç, bağlantı dizesi aranır (`git diff --staged` üzerinde). Şüpheli satır varsa commit atma, kullanıcıya göster.

## 2. Denetim

- Değişen alanın hızlı denetimini çalıştır (bkz. `/inceleme` tablosu) ya da `/inceleme` bu oturumda yeni yapıldıysa sonucunu kullan. Kırmızı denetimle commit atma; kullanıcı açıkça isterse mesajın gövdesine nedenini yaz.

## 3. Mesaj

Biçim ([Proje yapısı](../../../docs/02-mimari/03-proje-yapisi.md) §6):

```
<tür>(<kapsam>): <özet>

<isteğe bağlı gövde: neden; ilgili aşama, ör. "Stage: A07">
```

- **Türler:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `data`.
- **Kapsamlar:** `mobile`, `editor`, `web`, `api`, `server` (`Mutalaa.Domain`, `Mutalaa.Infrastructure` ve çözüm geneli), `publisher`, `pipeline`, `anchors`, `content-schema`, `search`, `reader-core`, `player`, `ui-tokens`, `test-vectors`, `infra`, `docs`, `kit` (CLAUDE.md ve `.claude/`).
- Özet İngilizce, emir kipinde, küçük harfle başlar, sonda nokta yok, en çok 72 karakter. Örnek: `feat(anchors): parse word-range anchors`.

## 4. Commit

- Dosyaları adıyla ekle (`git add <yol>`); `git add -A` kullanma.
- `git commit -m "<özet>" -m "<gövde>"`. Kanca ya da denetim atlama bayrağı (`--no-verify`) kullanma; yayımlanmış commit'i değiştirme (`--amend` yalnız henüz push edilmemiş kendi commit'inde ve kullanıcı isterse).
- **Push yapma.** Kullanıcı isterse bile önce dalı ve hedefi göster; `git push` her zaman onay ister, zorla gönderme yasaktır.

## 5. Rapor

Atılan commit'lerin kısa özeti (`git log --oneline -n <sayı>`) ve dışarıda bırakılan dosyalar.
