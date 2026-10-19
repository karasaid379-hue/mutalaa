---
name: durum
description: >-
  Mütâlaa projesinin durumunu özetler; aktif ve tamamlanan aşamalar, başlanabilecek aşamalar, bekleyen
  insan adımları, commit edilmemiş değişiklikler ve önerilen sonraki adım. Aşama seçerken, oturum
  başında ya da kullanıcı /durum yazdığında kullan. Dosya değiştirmez.
---

# Proje durumu

Dosya değiştirme; yalnız oku ve raporla.

## Oku

1. `docs/10-claude-code/05-ilerleme.md`: durum bloğu, aşama tablosu, oturum günlüğünün son beş satırı.
2. `docs/10-claude-code/06-insan-adimlari.md`: durumu `tamam` olmayan adımlar.
3. `docs/10-claude-code/04-asama-haritasi.md`: önkoşul ilişkileri.
4. `docs/10-claude-code/07-belge-celiskileri.md` §1: durumu `açık` olan maddeler ve aşamaları.
5. `git status --short` ve `git log --oneline -5` (depo henüz yoksa bunu söyle).

## Hesapla

- **Başlanabilecek aşamalar:** durumu `bekliyor`, önkoşulları `tamam`, insan adımı engeli olmayanlar. Önkoşulda parantez içinde adım yazılıysa (ör. "A11 (A11.2)") o önkoşul aşamasının yalnız bu adımlarının ilerleme notunda tamam görünmesi yeter.
- **İnsan adımı bekleyenler:** önkoşulları tamam ama bir insan adımı bekleyen aşamalar; hangi adım.
- **Yarım kalan:** durumu `sürüyor` olan aşama ve nerede kalındığı.

## Rapor (Türkçe, kısa)

```
Aktif: …
Son tamamlanan: …
Başlanabilir: A08 · …, A09 · …
İnsan adımı bekliyor: A16 (İ-11 düzeltme turu) …
Karar bekleyen çelişki: önerilen aşamada BÇ-07, BÇ-12 (toplam açık: …)
Commit edilmemiş değişiklik: var/yok (dosya sayısı)
Öneri: /asama A08
```

İlerleme dosyasıyla git geçmişi çelişiyorsa (ör. tabloda `tamam` ama commit yok) bunu ayrıca belirt; düzeltmeyi kullanıcıya öner.
