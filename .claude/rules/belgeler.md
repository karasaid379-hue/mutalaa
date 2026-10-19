---
paths:
  - "docs/**"
---

# Belge kuralları (`docs/`)

Kaynak: [docs/README.md](../../docs/README.md) "Çalışma kuralları".

- **Karar defteri tek doğruluk kaynağıdır.** Bir karar değişecekse önce [karar defteri](../../docs/00-ozet/02-karar-defteri.md) güncellenir, sonra ilgili dosyalar. Eski karar silinmez; "Geçersiz" diye işaretlenir ve yeni karara bağlanır. Bunun için `/karar` becerisi kullanılır.
- **Dosya düzeni.** Her dosya sürüm, tarih, durum ve bağlı karar numaralarıyla açılır, "İlgili dosyalar" bölümüyle biter. Bilinmeyen "Açık soru", doğrulanacak nokta "Doğrulanacak" diye yazılır; çözülünce üstü çizilir ya da "Çözüldü" diye işaretlenir ve kaynak eklenir.
- **Bağlantılar** görelidir. Başlık çapaları GitHub kuralıyla türetilir (ör. `#k-25--i̇lkeler`). Değişiklikten sonra `belge-esitle` becerisindeki bağlantı denetimi çalıştırılır.
- **Hukuki konular.** Lisans ve mevzuat notları kaynak bağlantısı taşır ve "hukuki görüş değildir" uyarısıyla yazılır.
- **Dil.** Türkçe, sade, kısa cümle. Emoji kullanılmaz. Dosya adları ASCII'dir.
- **İlerleme dosyası** (`docs/10-claude-code/05-ilerleme.md`) `/asama` ve `/durum` becerilerinin biçimine göre güncellenir; durum bloğunun işaretleri (`<!-- durum:baslangic -->`, `<!-- durum:bitis -->`) korunur.
- Yazışma taslakları `docs/yazismalar/` altındadır ve gönderilmeden önce kullanıcı onaylar.
