---
name: capa-gramer
description: >-
  Mütâlaa çapa (kalıcı adres) grameri ve kuralları; q:2:255, q:2:255:3-7, q:2:255-257, meal:, tf:,
  rn:, h:, ht:, k:, konu: biçimleri, @başlangıç-bitiş aralıkları, hata kodları, kanonik biçim,
  ofsetler, sıralama, rotalar ve depolama biçimi. Çapa üreten, ayrıştıran, karşılaştıran, saklayan ya
  da derin bağlantıya çeviren kod yazarken kullan.
---

# Çapa grameri (K-26)

Tam şartname: [Çapa şeması](../../../docs/03-veri/01-capa-semasi.md). Bu özet ondan türetilmiştir; çelişkide belge geçerlidir.

## Biçimler

| Birim | Biçim | Örnek |
|---|---|---|
| Âyet | `q:{sure}:{ayet}` | `q:2:255` |
| Kelime | `q:{sure}:{ayet}:{kelime}` | `q:2:255:3` |
| Kelime aralığı | `q:{sure}:{ayet}:{ilk}-{son}` | `q:2:255:3-7` |
| Âyet aralığı | `q:{sure}:{ilk}-{son}` | `q:2:255-257` (kendi metni yok) |
| Meal | `meal:{meal}:{sure}:{ayet}` | `meal:elmalili:2:255` |
| Tefsir paragrafı | `tf:{eser}:{sure}-{ilk}-{son}:p{n}` | `tf:elmalili:2-255-257:p3` |
| Âyetsiz tefsir bölümü | `tf:{eser}:{bolum}:p{n}` | `tf:elmalili:mukaddime:p4` |
| Risale paragrafı | `rn:{kitap}(:{bolum})*:p{n}` | `rn:sozler:soz-10:hakikat-3:p4` |
| Risale cümlesi | `rn:…:p{n}:s{cumle}` | `rn:sozler:soz-10:hakikat-3:p4:s2` |
| Hadis | `h:{koleksiyon}:{no}` | `h:buhari:52`, `h:tecrid:15` |
| Hadis çevirisi | `ht:{ceviri}:{koleksiyon}:{no}` | `ht:naim:tecrid:15` |
| Kitap (sonra) | `k:{kitap}(:{bolum})*:p{n}` | `k:kisas-i-enbiya:hz-ibrahim:p2` |
| Konu (v1.x) | `konu:{slug}` | `konu:tevhid` (metin taşımaz) |
| Kesin aralık | `{çapa}@{başlangıç}-{bitiş}` | `meal:elmalili:2:255@10-48` |

## Anlam kuralları

1. Sure 1–114; âyet o surenin âyet sayısını aşmaz (toplam 6.236). Âyet sayısı dizisi kaynak üst veriden üretilir, hafızadan yazılmaz.
2. Kelime numarası âyetin kelime sayısını aşmaz; bunu ayrıştırıcı değil içerik verisi (`quran_word`) denetler. Kelime numaraları QAC konumuna sabitlenir.
3. Aralıkta `ilk < son`. Tek kelime `q:2:255:3`, tek âyet `q:2:255` yazılır; `q:2:255:3-3` ve `q:2:255-255` kanonik değildir. Âyet aralığı tek sure içindedir.
4. Tefsir aralığında `ilk ≤ son` ve iki uç her zaman yazılır (`2-255-255`); sure sınırını geçmez.
5. `@` aralığı yarı açıktır `[başlangıç, bitiş)`, kod noktasıyla ölçülür; `başlangıç < bitiş ≤ metin uzunluğu` birim metniyle denetlenir.
6. `@` Kur'an, konu ve cümle çapasına eklenmez. Kur'an'da kesin aralık kelime aralığıyla yazılır.
7. `p4`, `s12` gibi adlar bölüm adı olamaz. Slug en çok 64 karakter, bölüm derinliği en çok 8, çapa en çok 256 karakter.
8. Çapa yalnız küçük harf ASCII'dir; baştaki sıfır ve büyük harf geçersizdir. "Bakara 255" gibi insan yazımı ayrı ayrıştırıcıyla çevrilir (`shared/data/sure-adlari.json`).

## Hata kodları

`BICIM` · `SURE_ARALIGI` · `AYET_ARALIGI` · `TERS_ARALIK` · `KANONIK_DEGIL` · `UZUNLUK`. Örnekler: `q:115:1` → `SURE_ARALIGI`; `q:2:287` → `AYET_ARALIGI`; `q:2:255:7-3` → `TERS_ARALIK`; `q:2:255-255` → `KANONIK_DEGIL`; `q:2:255@0-10`, `rn:sözler:p1`, `Q:2:255` → `BICIM`.

Öncelik (K-35 madde 1–2): `[a-z0-9:@-]` dışı karakter → `BICIM`; toplam > 256 → `UZUNLUK`; §3 deseni → `BICIM` (sure/âyet/kelime en çok üç hane, aralık bitişi ≥ 1: `q:1000:1`, `…@0-0` → `BICIM`); slug > 64, derinlik > 8 (yol uzunluğu, kitap dahil), sayı > 2.147.483.647 → `UZUNLUK`; sonra `SURE_ARALIGI` → `AYET_ARALIGI` → `TERS_ARALIK` → `KANONIK_DEGIL`.

## Sıralama, kapsama, birim (K-35 madde 3–5)

- `compare`: Kur'an'da okuma sırası: (sure, başlangıç âyeti) → âyet → kelimeler ve kelime aralıkları başlangıç kelimesine göre (tek kelime önce, sonra bitiş) → âyet aralığı. `q:2:255 < q:2:255:2 < q:2:255:2-3 < q:2:255:9 < q:2:255-257 < q:2:256`. Sonra `meal < tf < tfb < rn < h < ht < k < konu`; aynı türde alanlar kanonik dizgideki sırayla, olmayan isteğe bağlı alan önce (`p4 < p4@0-5 < p4:s1`).
- `contains`: kelime aralığı alt aralıklarını, âyet aralığı içindeki kelime aralıklarını kapsar; aralıklı paragraf cümleyi kapsamaz.
- `unitOf`: kelime(ler) → âyet, `@` atılır, cümle → paragraf. `toUnitSpan`: `qa` ve cümlede hata. `coveredAyahs`: `q`, `qa`, `tf`, `meal`; diğerleri boş. Üç işlev üç dilde vardır.

## Düzenli ifadeler

`[0-9]` kullanılır, `\d` kullanılmaz (.NET ve Python başka yazı sistemlerinin rakamlarını da eşler). Python'da adlı grup `(?P<ad>…)`; .NET'te `RegexOptions.CultureInvariant`, `IgnoreCase` yok. Desenler belgenin §3 bölümündedir.

## Kararlılık

- Çapa bir kez verilir, yeniden numaralanmaz, silinmez; kullanım dışı kalır (`status = 'kullanim_disi'`) ve `successors` yönlendirmesi taşır.
- Metin düzeltmesinde çapa aynı kalır, `content_hash` değişir; kullanıcı kayıtları yeniden çapalanır (belge §9).
- Her yayında önceki yayının bütün çapaları etkin ya da yönlendirmeli olmalıdır (yayın kapısı adımı).

## Uygulamalar (aynı vektörlerle kilitli)

| İşlev | TypeScript (`packages/anchors`) | Python (`pipeline/src/mutalaa_pipeline/anchor/capa.py`) | C# (`Mutalaa.Domain/Anchors`) |
|---|---|---|---|
| Ayrıştırma | `parse`, `tryParse` | `parse`, `try_parse` | `AnchorRef.Parse`, `TryParse` |
| Biçimleme | `format` (`parse(format(r)) == r`) | `format`, `str(r)` | `ToString()` |
| Sıralama | `compare` | `sort_key` | `IComparable<AnchorRef>` |
| Kapsama | `contains` | `contains` | `Contains` |
| Rota | `toRoute`, `fromRoute` | `to_route(r, hedef, sema?)` | `ToRoute(hedef, sema?)` |
| Birim | `unitOf`, `toUnitSpan`, `coveredAyahs` | `unit_of`, `to_unit_span`, `covered_ayahs` | `UnitOf`, `ToUnitSpan`, `CoveredAyahs` |
| Ofset | `cpToUtf16`, `utf16ToCp`, `snapSpan` | dilim zaten kod noktası; `snap_span` | `Rune` ile |

Kendi ayrıştırıcını yazma; bu uygulamaları kullan. Vektörler: `shared/test-vectors/anchors/{valid,invalid,compare,contains,route}.jsonl` ve `offsets/offsets.jsonl` (`test-vektoru` becerisi).

## Rota ve depolama

- Yerel rota: `{şema}://` + çapanın `:` işaretleri `/` olur; aralık `?aralik=` sorgusuna gider. Şema derleme türüne göre `mutalaa`, `mutalaa-internal`, `mutalaa-dev`. Örnek: `q:2:255:3-7` → `mutalaa://q/2/255/3-7`. Expo Router'da tek yakalayıcı rota (`[...capa].tsx`).
- Web rotası (Faz 5'te kesinleşir): `q:2:255` → `/kuran/2/255`. Yalnız §11 tablosundaki biçimler üretilir, diğerleri hata verir (K-35 madde 6). `fromRoute` yalnız üç yerel şemayı çözer.
- Depolamada (`xref`, `xref_idx`) uç birim düzeyindedir: `q:2:255:3-7` → birim `q:2:255` + kelime konumu aralığı `[3,8)`; metin birimlerinde aralık kod noktasıdır. Dönüşüm `toUnitSpan` ile.
- Notlarda bağlantı `[[q:2:255]]` biçimindedir.
- Test kimlikleri çapayı kullanır: `ayet-q:2:255`, `kelime-q:2:255:3`.
