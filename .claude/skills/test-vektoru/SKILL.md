---
name: test-vektoru
description: >-
  Mütâlaa ortak test vektörleri (shared/test-vectors) ile çalışma; çapa, ofset, Türkçe ve Arapça
  normalizasyon, content_hash ve FTS sorgu vektörlerinin biçimi, yeni kural için önce vektör ekleme ve
  TypeScript, C#, Python uygulamalarının aynı değişiklikte geçmesi. Normalizasyon, çapa ya da ofset
  kuralı değişirken veya yeni vektör eklerken kullan.
---

# Ortak test vektörleri

Kaynaklar: [Proje yapısı](../../../docs/02-mimari/03-proje-yapisi.md) §1.2, [Test stratejisi](../../../docs/07-yayin/03-test-stratejisi.md) §2, [Arama](../../../docs/03-veri/05-arama-fts5.md) §1.5, [Çapa şeması](../../../docs/03-veri/01-capa-semasi.md) §11.

## Düzen

```
shared/test-vectors/
  package.json                 JSONL biçim denetimi (Turborepo önbelleği için)
  anchors/valid.jsonl          çapa dizgisi → ref, canonical, unit, unit_span, ayahs
  anchors/invalid.jsonl        dizgi → hata kodu (BICIM, SURE_ARALIGI, AYET_ARALIGI, TERS_ARALIK, KANONIK_DEGIL, UZUNLUK)
  anchors/compare.jsonl        [a, b] → -1, 0, 1
  anchors/contains.jsonl       [dış, iç] → true, false
  anchors/route.jsonl          çapa (+ şema) → native, web
  offsets/offsets.jsonl        metin → codepoints, utf16, cp_to_utf16, snap; en az bir BMP dışı karakter
  normalize/tr.jsonl           Türkçe geniş ve dar anahtar
  normalize/ar.jsonl           Arapça hareke ve harf birleştirme
  content-hash/hash.jsonl      kanonik metin → SHA-256; en az bir NFC olmayan Arapça dizi
  fts-query/query.jsonl        arama sorguları (doğruluk)
  arama/olcum.jsonl            arama ölçüm kümesi (id, kategori, sorgu, beklenen); A28, A33; koşucular atlar
```

## Biçim

JSONL, UTF-8, BOM yok, LF, satır başına bir JSON nesnesi. Alanlar: `id` (dosyada benzersiz), `input`, `expected` (dize, sayı ya da nesne), isteğe bağlı `note` ([Proje yapısı](../../../docs/02-mimari/03-proje-yapisi.md) §1.2). Dosya başına `input` ve `expected` içeriği [A04](../../../docs/10-claude-code/asamalar/A04-capa-ve-test-vektorleri.md) ve [A05](../../../docs/10-claude-code/asamalar/A05-arama-normalizasyonu.md) tablolarındadır. Örnek satırlar:

```json
{"id":"tr-0001","input":"Işık","expected":{"dar":"ışık","genis":"isik"},"note":"I → ı"}
{"id":"an-0002","input":"q:2:255:7-3","expected":"TERS_ARALIK"}
{"id":"of-0001","input":"âlem 𝐀","expected":{"codepoints":6,"utf16":7},"note":"BMP dışı karakter"}
```

Arama ölçüm kümesi (`arama/olcum.jsonl`) bu kuralın istisnasıdır: alanları `id`, `kategori`, `sorgu`, `beklenen`; doğruluk vektörü değildir (A28).

Beklenen değerler [Arama](../../../docs/03-veri/05-arama-fts5.md) ve [Çapa şeması](../../../docs/03-veri/01-capa-semasi.md) kurallarından gelir. Metinler sentetiktir (Latin harf, `\u` kaçışlı birleşen işaretler, en az bir BMP dışı karakter). Kur'an, meal, hadis ya da Risale metni hafızadan ya da belgeden vektöre konmaz; Arapça normalizasyon vektörleri `\u` kaçışıyla kurulan sentetik harf ve işaret dizileridir. Tek istisna, A10'dan sonra Tanzil kaynak dosyasından betikle alınan girdilerdir: girdi Tanzil'in baytlarıdır, beklenen değer Arama §1.5 Arapça tablosunun `ar` sütunundan betikle alınır, `note` kaynak ve çapayı taşır ([A10](../../../docs/10-claude-code/asamalar/A10-tanzil-alimi.md) A10.7). Arama sorgusu örnekleri (Arama §3 tablosu, `fts-query/`) sorgu dizgisidir ve belgeden programla, bayt bayt alınır. Hiçbir Arapça dizgi hafızadan yazılmaz.

## İş akışı

1. Kuralı belgede bul; belge yoksa önce `/karar` ya da belge güncellemesi.
2. Önce vektörü ekle (kuralı gösteren en küçük örnek, tuzak durumları dahil: `İ`, `I`, `ı`, `i`, BMP dışı karakter, NFC olmayan dizi).
3. Üç koşucuyu çalıştır; yeni vektörün başarısız olduğunu gör.
4. Üç uygulamayı düzelt (paralel: `web-gelistirici` TypeScript, `sunucu-gelistirici` C#, `hat-gelistirici` Python).
5. Hepsi aynı değişiklikte yeşil olmadan bitti sayılmaz.

Vektörler hattın `uv run mutalaa export test-vectors` komutuyla üretilebilir; üretilen dosya elle gözden geçirilir.

## Koşucular

| Dil | Komut |
|---|---|
| TypeScript | `pnpm --filter @mutalaa/anchors test` · `pnpm --filter @mutalaa/search test` |
| C# | `dotnet test --solution server/Mutalaa.slnx` (Domain test projesi vektörleri okur) |
| Python | `cd pipeline && uv run pytest` |
| Biçim | `pnpm --filter ./shared/test-vectors build` |

TypeScript testleri `LANG=tr_TR.UTF-8` altında da, C# testleri `tr-TR` kültüründe de geçmelidir. Windows'ta `LANG` Node'un yerel ayarını değiştirmez; Türkçe Windows'ta iki koşu da `tr-TR`'dir ve karşıtlık Linux CI'da görülür (`windows-sorun`). Jest Hermes'i sınamaz; mobil `dev` derlemesindeki Öz test ekranı aynı vektörleri cihazda koşturur.

## Tuzaklar

| Tuzak | Not |
|---|---|
| Python `"İ".lower()` | `i` + U+0307 verir; açık eşleme gerekir |
| .NET `ToLower()` | geçerli kültüre bağlı |
| JavaScript `toLowerCase()` | Türkçe kurala uymaz; `toLocaleLowerCase('tr')` Hermes'te Doğrulanacak |
| Ofset | Python kod noktası, JS ve C# UTF-16 birimi sayar |
| FTS5 unicode61 | normalize edilmemiş metinde Türkçe ve harekeli Arapça aramayı kaçırır; indeks `search_text` üzerinde |
