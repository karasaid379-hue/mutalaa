---
name: belge-esitle
description: >-
  Kod değişikliklerinden sonra Mütâlaa belgelerini eşitler; koddan sapmaları ve çözülen "Doğrulanacak"
  maddelerini belgelere işler, bağlantı ve başlık çapalarını denetler. Bir aşamanın belge adımında,
  kod belgeden saptığında ya da kullanıcı /belge-esitle yazdığında kullan.
argument-hint: "[kapsam: boş = son değişiklikler | <belge yolu> | tum]"
---

# Belge eşitleme

Kapsam: `$ARGUMENTS`

## 1. Farkları bul

- Kapsam boşsa: `git diff --stat HEAD` ve son commit'ler; aktif aşamanın dosyası.
- Değişen kodun hangi belgelere dokunduğunu bul: klasör ve dosya adları ([Proje yapısı](../../../docs/02-mimari/03-proje-yapisi.md)), komutlar, tablo ve alan adları, uç yolları, paket adları, sürümler, ayar anahtarları.
- `Grep` ile belgelerde "Doğrulanacak" ve "Açık soru" maddelerinden bu aşamada çözülenleri bul.

## 2. Güncelle

- Belge işini `belge-bekcisi` ajanına ver: farkların listesi, çözülen maddeler ve kaynakları.
- Bir karar değişiyorsa belgeyi değil önce karar defterini güncelle (`/karar`).
- Kod belgeye aykırıysa ve belge doğruysa düzeltmeyi kodda öner; belgeyi koda uydurma.

## 3. Bağlantıları denetle

```bash
node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs CLAUDE.md .claude
```

Betik göreli bağlantıların hedef dosyasını ve `#başlık` çapalarını GitHub kuralıyla denetler; kırık bağlantıları `dosya:satır` ile listeler ve varsa 1 ile çıkar. Kırık bağlantıları düzelt ve betiği yeniden çalıştır.

## 4. Rapor

Değişen belgeler ve nedeni, çözülen "Doğrulanacak" maddeleri, koda yansıması gereken farklar, bağlantı denetimi sonucu.
