---
name: karar
description: >-
  Mütâlaa karar defterine (docs/00-ozet/02-karar-defteri.md) yeni karar ekler ya da var olan kararın
  metnini yerinde günceller; özet tabloyu ve bağlı dosyaları aynı değişiklikte eşitler, kaldırılan
  kararın numarasını yeniden kullanmaz. Kullanıcının verdiği bir kararı kaydetmek gerektiğinde ya da
  kullanıcı /karar <konu> yazdığında kullan; kararı kullanıcı verir, bu beceri kaydı hazırlar ve
  onay alır.
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

Yeni kararın numarası, defterdeki en büyük numaranın bir fazlasıdır; kaldırılan kararın numarası yeniden kullanılmaz. Biçim:

```markdown
### K-32 · Kısa başlık
- **Karar:** Tek cümleyle ne kararlaştırıldı.
- **Gerekçe:** Neden; ölçüm ya da kaynak bağlantısıyla.
- **Değerlendirilen alternatifler:** (varsa) seçilmeyenler ve nedeni.
- **Kaynak:** Proje sahibinin kararı (YYYY-AA-GG) ya da belge/bağlantı.
```

Var olan bir karar değişiyorsa:
- Karar metni bugünkü kuralı anlatır. Metin yerinde güncellenir; artık geçerli olmayan cümle metinde kalmaz (eski metin git geçmişindedir).
- Özet tablodaki satır ve bağlı dosyalar (belgeler, CLAUDE.md, kurallar, beceriler, ajanlar) aynı değişiklikte eşitlenir; yeni karar için tabloya satır eklenir.
- Karar bütünüyle kalkıyorsa bölümü ve özet satırı silinir; ona giden bağlantılar aynı değişiklikte bugünkü kurala yönlendirilir.

Başlık çapası GitHub kuralıyla türetilir: küçük harf, harf-rakam-tire-boşluk dışındaki işaretler silinir, boşluk tireye döner. Örnek: `### K-31 · Geliştirme aracı: Claude Code` → `#k-31--geliştirme-aracı-claude-code`.

## 3. Onay

- Taslağı ve etkilenecek belgelerin listesini kullanıcıya göster. Kullanıcı onaylamadan karar defterine yazma. (Hook bu dosyada ayrıca onay ister.)

## 4. Yaz ve yay

- Karar defterini güncelle.
- Etkilenen belgeleri `belge-bekcisi` ajanıyla güncelle; her belgenin başlığındaki "Bağlı kararlar" satırına yeni karar bağlantısını ekle. Karara bağlı kit dosyalarını (CLAUDE.md, kurallar, beceriler, ajanlar) aynı değişiklikte eşitle.
- Bağlantı denetimini çalıştır: `node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs CLAUDE.md .claude`.
- Commit: `docs(docs): record K-32 <kısa İngilizce özet>` (`/commit` kurallarıyla).

## Kurallar

- Kaynak, tedarik ve derleme görünürlüğüyle ilgili kararlar [K-42](../../../docs/00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) kaynak ilkesine uyar.
- Kod ve belge çelişiyorsa önce karar netleşir, sonra kod ya da belge değişir.
