---
name: karar
description: >-
  Mütâlaa karar defterine (docs/00-ozet/02-karar-defteri.md) yeni karar ekler ya da var olan kararı
  günceller; eski kararı silmez, "Geçersiz" diye işaretler, özet tabloyu ve etkilenen belgeleri
  günceller. Kullanıcının verdiği bir kararı kaydetmek gerektiğinde ya da kullanıcı /karar <konu>
  yazdığında kullan; kararı kullanıcı verir, bu beceri kaydı hazırlar ve onay alır.
argument-hint: "[konu ya da K-numarası]"
---

# Karar kaydı

Konu: `$ARGUMENTS`

Karar defteri projenin tek doğruluk kaynağıdır. Kararı kullanıcı verir; sen kaydı hazırlar ve onayını alırsın.

## 1. Durumu anla

- Karar defterini baştan sona oku. Konu var olan bir kararı değiştiriyor mu, yoksa yeni mi?
- Konuyla ilgili belge bölümlerini bul (`Grep` ile karar numarası ve anahtar kelimeler).
- Kararın dayanağını topla: kullanıcının sözü, araştırma sonucu (`arastirmaci`), ölçüm ya da test çıktısı. Kaynağı olmayan iddiayı karar metnine yazma.

## 2. Taslağı hazırla

Yeni kararın numarası, defterdeki en büyük numaranın bir fazlasıdır. Biçim:

```markdown
### K-32 · Kısa başlık
- **Karar:** Tek cümleyle ne kararlaştırıldı.
- **Gerekçe:** Neden; ölçüm ya da kaynak bağlantısıyla.
- **Değerlendirilen alternatifler:** (varsa) seçilmeyenler ve nedeni.
- **Kaynak:** Proje sahibinin kararı (YYYY-AA-GG) ya da belge/bağlantı.
```

Var olan bir karar değişiyorsa:
- Eski karar silinmez. Eski bölüme bir satır eklenir: `- **Güncelleme (YYYY-AA-GG):** … [K-32](#k-32--kısa-başlık) ile değişti.` Karar tamamen geçersizse başlığın altına `- **Durum:** Geçersiz (YYYY-AA-GG); yerini [K-32](#…) aldı.` yazılır.
- Özet tablodaki satır yeni kararı gösterecek biçimde güncellenir; yeni karar için tabloya satır eklenir.

Başlık çapası GitHub kuralıyla türetilir: küçük harf, harf-rakam-tire-boşluk dışındaki işaretler silinir, boşluk tireye döner. Örnek: `### K-31 · Geliştirme aracı: Claude Code` → `#k-31--geliştirme-aracı-claude-code`.

## 3. Onay

- Taslağı ve etkilenecek belgelerin listesini kullanıcıya göster. Kullanıcı onaylamadan karar defterine yazma. (Hook artık bu dosyada ayrıca onay istemez; kural yordamdır.)

## 4. Yaz ve yay

- Karar defterini güncelle.
- Etkilenen belgeleri `belge-bekcisi` ajanıyla güncelle; her belgenin başlığındaki "Bağlı kararlar" satırına yeni karar bağlantısını ekle.
- Bağlantı denetimini çalıştır: `node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs`.
- Commit: `docs(docs): record K-32 <kısa İngilizce özet>` (`/commit` kurallarıyla).

## Kurallar

- Hukuki konularda karar metni hukuki görüş gibi yazılmaz; "hukuki görüş değildir" uyarısı ve kaynak eklenir.
- Kod ve belge çelişiyorsa önce karar netleşir, sonra kod ya da belge değişir.
