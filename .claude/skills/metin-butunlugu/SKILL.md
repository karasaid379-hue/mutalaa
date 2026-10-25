---
name: metin-butunlugu
description: >-
  Mütâlaa metin bütünlüğü kuralları; Tanzil metninin bayt bayt korunması (NFC yok), kendi metnimizde
  ilk kayıt adımları, content_hash, kod noktası ofsetleri, arama metninin ayrı tutulması, Türkçe İ/ı
  ve yerel ayar tuzakları, UTF-8 ve satır sonu. Kur'an metni, meal, Unicode, normalizasyon,
  büyük-küçük harf ya da dosya kodlamasıyla ilgili kod yazarken kullan.
---

# Metin bütünlüğü (K-26)

Kaynaklar: [Çapa şeması](../../../docs/03-veri/01-capa-semasi.md) §7–§8, [Arama](../../../docs/03-veri/05-arama-fts5.md) §1, [Yerel geliştirme](../../../docs/02-mimari/04-yerel-gelistirme.md) §10.

## Kanonik metin

| Metin | Kural |
|---|---|
| Kaynaktan alınan (Tanzil Uthmani ve Simple Clean, hazır Arapça hadis metinleri) | Kaynağın dağıttığı hâliyle, bayt bayt saklanır. NFC dahil hiçbir dönüşüm yok. Birim metni kaynak dosyanın aynen bir parçasıdır: `kaynak[başlangıç:bitiş] == unit.text`. |
| Kendi ürettiğimiz (Elmalılı ve Risale transkripsiyonu, Naim aktarımı, kelime anlamları) | İlk kayıtta bir kez kanonikleştirilir, sonra değişmez. |

Neden: Tanzil şartları metni değiştirmeyi yasaklar ve NFC şedde ile harekenin sırasını değiştirir (U+0651 U+064E → U+064E U+0651).

**Kendi metnimizde ilk kayıt adımları (bu sırayla; K-35 madde 7):**
1. Silinir: U+FEFF, U+00AD, U+200E, U+200F, U+202A–U+202E, U+2066–U+2069, U+061C. Korunur: U+200C, U+200D.
2. Unicode NFC.
3. Satır sonu yalnız U+000A (CRLF ve tek CR → LF); U+0020 ve U+0009 dizileri tek U+0020 olur; metnin başı ve sonu yalnız U+0020, U+0009, U+000A'dan kırpılır. U+00A0 kenarda da korunur; U+2028, U+2029, U+0085'e dokunulmaz. Dilin varsayılan `trim`/`strip`/`Trim` işlevi kullanılmaz (U+00A0'ı da keser).
4. Kesme işareti, hareke ve düzeltme işaretleri basılı kaynaktaki gibi yazılır.

## content_hash

`sha256(kanonik_metin.encode("utf-8")).hexdigest()` (64 küçük harf onaltılık). Yalnız içerik hattında hesaplanır; cihaz yeniden hesaplamaz, paketteki değeri kopyalar. Normalize metinden hesaplanmaz. Kur'an biriminde özet farkı bir hat hatasıdır.

## Ofsetler

- Kanonik metindeki Unicode kod noktası sırası; 0'dan başlar; aralık `[başlangıç, bitiş)`.
- Python `str` kod noktasıyla indeksler. JavaScript ve C# UTF-16 birimiyle indeksler: dönüşüm yalnız `packages/anchors` (`cpToUtf16`, `utf16ToCp`) ve C#'ta `Rune` ile.
- `snapSpan`: başlangıç birleşen işaretin (Mn) üstüne düşerse geriye, bitiş Mn öncesine düşerse ileriye kayar; harf harekesinden ayrılmaz. Mn sınaması kod noktası üzerinde yapılır (JS `for…of` + `/\p{Mn}/u`, C# `Rune.GetUnicodeCategory`, Python `unicodedata.category`). Geçersiz aralık ya da konumda `snapSpan`, `cpToUtf16`, `utf16ToCp` hata verir (K-35 madde 8).
- Test: `offsets/offsets.jsonl` en az bir BMP dışı karakter içerir (`"âlem 𝐀"`: 6 kod noktası, 7 UTF-16 birimi).

## Arama metni

Normalize metin ayrı sütundadır (`search_text` ve anahtarlar) ve hiçbir ekranda gösterilmez; kanonik metnin yerine geçmez. Normalizasyon kuralı değişirse `normalizer_version` artar ve bütün metin paketleri yeniden üretilir.

## Türkçe yerel ayar tuzakları

| Ortam | Yanlış | Sonuç | Doğru |
|---|---|---|---|
| .NET | `"id".ToUpper()` (tr-TR) | `"İD"` | `ToUpperInvariant()`; karşılaştırmada `StringComparison.Ordinal` |
| .NET | `s.StartsWith("x")`, `IndexOf("x")` | kültüre duyarlı | `StringComparison.Ordinal` |
| .NET | `double.Parse("1.5")` | tr-TR'de virgül | `CultureInfo.InvariantCulture` |
| JavaScript | `'İ'.toLowerCase()` | `'i̇'` (iki kod noktası) | önce `İ→i`, `I→ı` açık eşleme |
| JavaScript | `toLocaleUpperCase()`, `a.localeCompare(b)` | cihaza bağlı | yerel ayarı açık ver ya da sıralı karşılaştır |
| Python | `'İ'.lower()` | `'i̇'` | açık eşleme (`mutalaa_pipeline.normalize`) |
| Python | `open(yol)` | Türkçe Windows'ta cp1254 | `encoding="utf-8"`; `PYTHONUTF8=1` |
| PostgreSQL | `lower()`, `ILIKE` | `C.UTF-8`'de Türkçe kurala uymaz | `search_text`; Türkçe sıralamada `COLLATE "tr-x-icu"` |

## Dosyalar

- UTF-8, BOM yok; LF (yalnız `.ps1`, `.cmd` CRLF); ASCII dosya adı.
- Kaynak dosyayı editörde açıp kaydetme; sessizce normalize olabilir. Tanzil dosyaları yalnız hat üzerinden okunur. `data/raw/` değişmez.

## Yasaklar

- Kur'an, meal, tefsir, hadis ya da Risale metnini hafızadan yazmak, tamamlamak, "düzeltmek".
- Kanonik metne normalizasyon, kırpma ya da biçim dönüşümü uygulamak.
- Ofseti UTF-16 birimiyle saklamak.
