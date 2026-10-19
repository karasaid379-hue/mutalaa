---
paths:
  - "pipeline/**"
---

# İçerik hattı kuralları (`pipeline/`)

Kaynak: [İçerik hattı](../../docs/04-icerik/02-icerik-hatti.md), [Kaynaklar ve lisans defteri](../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md).

- **Veri soyu.** `data/raw` değişmezdir; yalnız `ingest` yazar. `data/staged` her çalıştırmada yeniden üretilir ve satırlar çapaya göre sıralanır. Her çalıştırma bir manifest yazar.
- **İdempotentlik.** Yükleme çapaya göre upsert yapar; hat yalnız `origin = 'hat'` ve `status = 'aday'` satırları günceller, `onayli` ve `red` satırlara dokunmaz. Reddedilen bağlantı başka yoldan yeniden önerilmez.
- **Lisans.** Her kaynak `pipeline/sources/<kimlik>.toml` kaydı ve tarihli lisans kopyası taşır. `kapali` kaynakta komut 3 çıkış koduyla durur. Ayrıntı: `lisans-kapisi` becerisi.
- **Yapay zekâ.** Yapay zekâ yalnız taslak üretir; çıktı `status = 'aday'` ve `dogrulanmis = false` ile girer. `embed_ok = false` kaynağın metni harici API'ye gönderilmez. İstemler `pipeline/prompts/<iş>/v<n>.md` dosyalarında sürümlüdür; sıcaklık 0. Meal, tefsir, hadis çevirisi ve Risale özeti üretilmez.
- **Çıkış kodları:** `0` başarılı, `1` QA kapısı kaldı, `2` girdi ya da yapılandırma hatası, `3` lisans kapısı.
- **Günlük.** Günlüklere içerik metni yazılmaz; çapa ve özet yazılır.
- **Metin.** Dosyalar `encoding="utf-8"` ile açılır. Türkçe küçük harf açık eşlemeyle yapılır (`str.lower()` İ'yi bozar). Düzenli ifadede `[0-9]`; adlı grup `(?P<ad>…)`. Ayrıntı: `metin-butunlugu` ve `icerik-hatti` becerileri.
- **Araçlar:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`. Python `>=3.13,<3.14`; bağımlılık eklemek `uv add` ile, kilit dosyası güncel.
