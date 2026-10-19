---
name: lisans-kapisi
description: >-
  Mütâlaa lisans ve yayın kapısı kuralları (K-06); serbest, bekliyor, ic_kullanim, kapali durumları,
  dev/internal/public derleme görünürlüğü, Kurul onay alanları, manifest imzası, Yayınlayıcı kapı
  kuralları P-01…P-14, embed_ok ve yeni kaynak ekleme. Kaynak, paket, manifest, görünürlük, Kurul ya
  da yapay zekâ çıktısıyla ilgili kod veya veri işinde kullan.
---

# Lisans ve yayın kapısı (K-06)

Kaynaklar: [Yayın kapısı ve Kurul](../../../docs/07-yayin/01-yayin-kapisi-ve-kurul.md), [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md), [İçerik paketleri](../../../docs/03-veri/03-icerik-paketleri.md) §5–§7, [Backend API](../../../docs/02-mimari/05-backend-api.md) §10.3. Hukuki görüş değildir.

## Durumlar

| Durum | Anlamı |
|---|---|
| `serbest` | Kamu malı, açık lisanslı ya da yazılı izni olan içerik |
| `bekliyor` | İzin ya da açıklama istendi, cevap bekleniyor (ör. QAC verisi) |
| `ic_kullanim` | Hukukçu görüşüyle yalnız ekip içinde işlenebilir |
| `kapali` | Hiçbir derlemede kullanılmaz ve işlenmez |

Sıra (en kısıtlayıcı sağda): `serbest < bekliyor < ic_kullanim < kapali`. Paketin durumu kaynaklarının en kısıtlayıcısıdır.

## Derleme türüne göre görünürlük

| `license_status` | `dev` (ekip) | `internal` (davetli test) | `public` (mağaza) |
|---|---|---|---|
| `serbest` | var | var | var; `kurul_gerekli` ise `kurul_onay` dolu ve içerik özeti onaylı özete eşit |
| `bekliyor` | var | yok | yok |
| `ic_kullanim` | var | yok | yok |
| `kapali` | yok | yok | yok |

Kurul'un kapalı test cevabı gelene kadar `internal` derleme Kurul kuralını `public` gibi uygular ve dış test kullanıcısı alınmaz.

```ts
// apps/mobile/src/packs/visibility.ts ile aynı mantık
if (p.license_status === 'kapali') return false;
if (flavor === 'dev') return true;
if (p.license_status !== 'serbest') return false;
return !p.kurul_gerekli || Boolean(p.kurul_onay);
```

## Bugünkü başlangıç durumları (değişiklik yalnız lisans defteri ve inceleme akışıyla)

- Tanzil Kur'an metni: `serbest`, metin değiştirilemez, atıf ve tanzil.net bağlantısı zorunlu; Kurul gerekli.
- Elmalılı meali ve tefsiri (özgün baskı, baskı kimliği `elmalili-1935`): `serbest`; meal Kurul gerekli (mealli mushaf); tefsirin Kurul durumu Açık soru (IP-1).
- QAC kök ve lemma verisi: `bekliyor`; yalnız `kelime-kok` paketinde, `core` içinde değil.
- Risale-i Nur metni: avukat görüşüne kadar `kapali`; görüş olumluysa `ic_kullanim` (yalnız `dev`); 1 Ocak 2031'de ya da izinle `serbest`.
- Tecrîd-i Sarîh: Arapça ve Ahmed Naim kısmı `serbest`; Kâmil Miras ciltleri 1 Ocak 2028'e kadar `kapali`.
- `bekliyor`: Kütüb-i Sitte Arapça veri setleri (`hadis-fawaz-ar`, `hadis-sunnah-api`), KFGQPC Hafs yazı tipi, QPC sayfa yazı tipleri, Medine düzen verisi, QF ses API'si, QUL veri setleri.
- `kapali`: âyet ses dosyaları (`ses-everyayah`, `ses-quranicaudio`) ve Türk hafız sesleri hafız başına yazılı izne kadar; Risale atıf dizini (`risale-atif-dizini`) metinle birlikte hukukçu görüşüne kadar; Mushaf B (`mushaf-b-*`) lisans gelene kadar.
- `test-` önekli kaynaklar ve fikstürler: hiçbir koşulda `public`'e girmez (P-12).

Kesin ve güncel değerler lisans defterindedir; bu liste özetidir.

## Yayınlayıcı kapı kuralları

| Kod | Kural | Derleme |
|---|---|---|
| P-01 | Kaynak kaydı olmayan ya da `kapali` içerik hiçbir pakete girmez | Hepsi |
| P-02 | `kisitlar.hazir_vt_yasak` taşıyan kaynak hiçbir pakete girmez (QF şartları) | Hepsi |
| P-03 | Paketin durumu kaynaklarının en kısıtlayıcısıdır; `public` ve `internal` yalnız `serbest` | Hepsi |
| P-04 | `kurul_gerekli` kaynakta `kurul_onay` dolu ve içerik özeti onaylı özetle aynı; değilse paket kapı raporunda "girmedi" olur ve `public` derleme durur (çıkış `2`) | public |
| P-05 | QAC kaynaklı kök ve lemma `core`'a yazılmaz; ayrı pakette, `bekliyor` kaldıkça `public`'e girmez | Hepsi |
| P-06 | `embed_ok = false` kaynaktan türeyen gömme ve `anlamsal` bağlantı pakete girmez | Hepsi |
| P-07 | Bağlantı: kaynak ve hedef görünür ya da hedef ayrı kayıtlı dizinde; `xref.license` izin verir; `red` hiç, `aday` yalnız `dev`/`internal` | Hepsi |
| P-08 | Onaysız yapay zekâ taslağı `public`'e girmez; iç derlemelerde "doğrulanmamış" işaretli | public |
| P-09 | `quran_word_fix`, `tr_root_index`, `tr_form` satırlarından yalnız onaylılar uygulanır | Hepsi |
| P-10 | Yalnız `metin_durumu = onayli` birimler `public`'e girer | public |
| P-11 | Tanzil birimlerinin `content_hash` değeri ham dosyadan yeniden hesaplananla aynı; atıf metni pakete aynen yazılır | Hepsi |
| P-12 | Slug'ı `test-` ile başlayan kaynak `public`'e girmez | public |
| P-13 | `depends_on` döngüsüz; her bağımlılık aynı manifestte | Hepsi |
| P-14 | Terfide içerik özetleri iç kanalda test edilen yayınla aynı | public |

## Manifest

Her paket satırı: `pack_id, version, sha256, size_bytes, license_status, kurul_gerekli, kurul_onay, min_app_version, depends_on, url` (+ `schema_version`, `title`, `bundled`). `kurul_onay` = `{onay_no, onay_tarihi, onayli_surum, icerik_ozeti}` ya da `null`. Manifest her derleme türünde `signature: {alg, kid, value}` taşır; imzasız ya da imzası tutmayan manifest reddedilir.

## Yapay zekâ ve embed_ok

`source.embed_ok = false` kaynağın metni harici API'ye gönderilmez ve gömülmez (komut 3 ile durur). Yapay zekâ çıktısı insan onayına kadar `dogrulanmis = false` ve "doğrulanmamış" rozetiyle görünür (K-25).

## Yeni kaynak eklerken

1. [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) kontrol listesi; `pipeline/sources/<kimlik>.toml`, tarihli lisans kopyası ve SHA-256, atıf metni, `license_status`, `kurul_gerekli`, `embed_ok`, `kisitlar`.
2. Durum değişikliği editörde ikinci onayla uygulanır (`license_status`, `kurul_onay`, `embed_ok`).
3. Lisans belirsizse `bekliyor` yaz ve insan adımı aç; hukuki sonuç çıkarma.
4. `lisans-denetcisi` ajanıyla denetle; `uv run mutalaa sources check` ve `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev --dry-run` kapı raporunu incele.
