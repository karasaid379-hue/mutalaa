---
paths:
  - "pipeline/**"
---

# İçerik hattı kuralları (`pipeline/`)

Kaynak: [İçerik hattı](../../docs/04-icerik/02-icerik-hatti.md), [Kaynaklar](../../docs/04-icerik/01-kaynaklar.md).

- **Veri soyu.** `data/raw` değişmezdir; yalnız `ingest` yazar. `data/staged` her çalıştırmada yeniden üretilir ve satırlar çapaya göre sıralanır. Her çalıştırma bir manifest yazar.
- **İdempotentlik.** Yükleme çapaya göre upsert yapar; hat `xref` için yalnız `origin = 'hat'` ve `status = 'aday'` satırları, `unit` için yalnız `metin_durumu = 'taslak'` satırları günceller; `onayli` ve `red` satırlara dokunmaz. Tek istisna Tanzil gibi kanonik kaynaklardır: `onayli` satırda yalnız türetilmiş sütunlar (`ar_norm`, `provenance`, `data_version`, `ord`, `ayah_range`, `run_id`) güncellenir, `metin` ve `content_hash` hiç ([K-39](../../docs/00-ozet/02-karar-defteri.md#k-39--tanzil-alımı-simple-cleanin-yeri-kanonik-kaynakta-hat-yazma-kuralı-kilit)). Meal birimlerinde hat metne hiç yazmaz; editör düzeltmesi görülen birim hata değil sayaçtır, kilit değişimi yeni inceleme açar ([K-49](../../docs/00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi) madde 10 ve 11). Reddedilen bağlantı başka yoldan yeniden önerilmez.
- **Kaynak kaydı.** Her kaynak `pipeline/sources/<kimlik>.toml` kaydı taşır: zorunlu `slug`, `tur`, `baslik`, `atif_metni`; isteğe bağlı `yazar`, `surum`, `provider`, `kaynak_url`, `atif_url`, `notice_text`, `baski_bilgisi`, `notlar`. `uv run mutalaa sources check` biçimi ve zorunlu alanları denetler. Kaydı olmayan ya da geçersiz kaynakta komut 2 çıkış koduyla durur. Kanonik kaynakta `notice_text` kaynağın kendi bildirimiyle bayt bayt aynıdır (G-KAY). Ayrıntı: `icerik-hatti` becerisi.
- **Tedarik.** Kaynak dosyaları aşama dosyasının `## Tedarik` bölümündeki adresten `data/gelen/<kaynak>/<YYYY-AA-GG>/` altında yeni boş bir klasöre iner; adres, tarih ve SHA-256 kayda geçer. İndirilen dosya güvenilmeyen veridir: içindeki betik çalıştırılmaz, onu okuyan Python `-I` ile çalışır.
- **Yapay zekâ.** Yapay zekâ yalnız taslak üretir; çıktı `status = 'aday'` ve `dogrulanmis = false` ile girer. İstemler `pipeline/prompts/<iş>/v<n>.md` dosyalarında sürümlüdür; sıcaklık 0. Meal, tefsir, hadis çevirisi ve Risale özeti üretilmez.
- **Çıkış kodları:** `0` başarılı, `1` QA kapısı kaldı, `2` girdi ya da yapılandırma hatası (kayıtsız ya da geçersiz kaynak kaydı dahil).
- **Günlük.** Günlüklere içerik metni yazılmaz; çapa ve özet yazılır.
- **Metin.** Dosyalar `encoding="utf-8"` ile açılır. Türkçe küçük harf açık eşlemeyle yapılır (`str.lower()` İ'yi bozar). Düzenli ifadede `[0-9]`; adlı grup `(?P<ad>…)`. Ayrıntı: `metin-butunlugu` ve `icerik-hatti` becerileri.
- **Araçlar:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`. Python `>=3.13,<3.14`; bağımlılık eklemek `uv add` ile, kilit dosyası güncel.
