---
name: paket-yayini
description: >-
  Mütâlaa içerik paketlerini üretme, imzalama, yerel S3 deposuna (SeaweedFS) yayımlama, doğrulama ve
  mobil uygulamaya gömülü core paketini alma adımları; derleme görünürlüğü (dev, internal, public),
  Yayınlayıcı kalite kapısı kuralları (P-01, P-07…P-14), manifest ve imzası, Yayınlayıcı komutları,
  çıkış kodları, depo düzeni ve sık hatalar. Paket, manifest ya da görünürlük kodu yazmak, üretmek,
  yenilemek veya doğrulamak gerektiğinde kullan.
---

# Paket yayını

Kaynaklar: [Backend API](../../../docs/02-mimari/05-backend-api.md) §10, [İçerik paketleri](../../../docs/03-veri/03-icerik-paketleri.md) §5–§7, [Yayın süreci](../../../docs/07-yayin/01-yayin-sureci.md), [Yerel geliştirme](../../../docs/02-mimari/04-yerel-gelistirme.md) §6–§7, [K-42](../../../docs/00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 5.

## Akış

Hat → PostgreSQL (`aday`) → editör onayı (`onayli`) → Yayınlayıcı: kilit → anlık görüntü → kalite kapısı → paket başına `content_digest` → SQLite + FTS5 → sha256 → imzalı manifest → depoya yükleme (paketler, sonra manifest geçmişi, en son `manifest.json`).

## Derleme görünürlüğü

Görünürlük editoryal kaliteye bağlıdır. Süzme kaynak ve birim düzeyinde yapılır; aynı paket kimliği derleme türüne göre farklı içerik taşıyabilir. Derleme türü (`BuildFlavor`) `Mutalaa.Domain/Releases` altındadır.

| İçerik | `dev` (ekip) | `internal` (davetli test) | `public` (mağaza) |
|---|---|---|---|
| Onaylı birim, onaylı bağlantı | var | var | var |
| Onaysız birim, onaysız yapay zekâ taslağı | "doğrulanmamış" rozetiyle | "doğrulanmamış" rozetiyle | yok |
| Aday bağlantı | var | var | yok |
| `red` bağlantı | yok | yok | yok |
| `test-` önekli kaynak | var | yalnız uçtan uca fikstürler (`test-kucuk`, `test-ses`) | yok |

Manifest her derleme türünde imzalıdır (Manifest bölümü).

## Kalite kapısı kuralları

| Kod | Kural | Derleme |
|---|---|---|
| P-01 | Kaynak kaydı olmayan içerik hiçbir pakete girmez | Hepsi |
| P-07 | Bağlantı: kaynak eser görünür; hedef eser görünür ya da ayrı kayıtlı bir dizine ait; `red` hiç girmez; `aday` yalnız `dev` ve `internal`'a girer | Hepsi |
| P-08 | Onaysız yapay zekâ taslağı `public`'e girmez; iç derlemelere "doğrulanmamış" işaretiyle girer | public |
| P-09 | `quran_word_fix`, `tr_root_index` ve `tr_form` satırlarından yalnız onaylılar uygulanır | Hepsi |
| P-10 | Yalnız `metin_durumu = onayli` birimler `public`'e girer | public |
| P-11 | Tanzil birimlerinin `content_hash` değeri ham dosyadan yeniden hesaplananla aynı; her kaynağın `atif_metni` ve `atif_url` değeri pakete aynen yazılır | Hepsi |
| P-12 | Slug'ı `test-` ile başlayan kaynak `public`'e girmez; `internal`'a yalnız uçtan uca fikstürler (`test-kucuk`, `test-ses`) girer | public, internal |
| P-13 | `depends_on` döngüsüz; her bağımlılık aynı manifestte | Hepsi |
| P-14 | Terfide içerik özetleri iç kanalda test edilen yayınla aynı | public |

P-02…P-06 yoktur; numaralar yeniden verilmez. Kapı raporu her paket ve kaynak için "girdi" ya da "girmedi" kararını kural koduyla yazar. `public` kuru çalıştırması (`publish --flavor public --dry-run`) 0 ile biter.

## Yayınlayıcı komutları

```bash
dotnet run --project server/Mutalaa.Publisher -- <komut>
```

| Komut | İş |
|---|---|
| `keys generate --flavor <dev\|internal\|public>` | Ed25519 anahtar çifti; özel anahtar kullanıcı sırlarına, açık anahtar ekrana (kullanıcı onayı gerekir) |
| `publish --flavor <f> [--pack <id>]… [--dry-run]` | Derleme, imza ve yükleme; `--dry-run` yalnız kapı raporu |
| `build --flavor <f> [--out <klasör>]` | Kapı, paket, sha256, imzalı manifest; varsayılan çıktı `data/packs/{flavor}/{surum}/` |
| `upload --flavor <f> --surum <s>` | Üretilmiş yayını yükler |
| `verify --flavor <f> [--manifest <yol>] [--embedded-core <yol>]` | İmza, şema, adres, boyut, sha256 ve kapı kurallarını yeniden denetler |
| `promote --surum <s> --to public` | İç kanalda test edilen yayını `public` için üretir (yalnız kullanıcı kararıyla) |
| `rollback --flavor <f> --to <surum>` | Manifesti önceki yayına çevirir |
| `watch` | API'nin `hazirlaniyor` bıraktığı talepleri işler |

Çıkış kodları: `0` başarı, `2` kapı reddi, `3` doğrulama hatası, `4` depo hatası, `1` diğer.

## Manifest

Her paket satırı: `pack_id, version, sha256, size_bytes, min_app_version, depends_on, url` (+ `schema_version`, `title`, `bundled`). Manifest her derleme türünde `signature: {alg, kid, value}` taşır; imzasız ya da imzası tutmayan manifesti `verify` reddeder, uygulama yok sayar.

## Depo düzeni

| Nesne | Anahtar |
|---|---|
| Paket | `packs/{flavor}/{pack_id}/{version}/{pack_id}-{version}.db` |
| Manifest | `{flavor}/manifest.json` |
| Manifest geçmişi | `{flavor}/manifests/{surum}.json` |

Sürüm CalVer `YYYY.M.N`. İçeriği değişmeyen paket önceki sürümünü korur. Var olan anahtara farklı sha256 ile yazılmaz.

## Yerel `dev` döngüsü

```bash
docker compose up -d
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json
MANIFEST_URL=http://localhost:8333/mutalaa/dev/manifest.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs
```

PowerShell'de elle: `$env:MANIFEST_URL = "http://localhost:8333/mutalaa/dev/manifest.json"`. `fetch-core.mjs` manifest imzasını ve paketin sha256 değerini doğrular, paketi `apps/mobile/assets/db/` klasörüne yazar.

## Sık hatalar

| Belirti | Neden | Çözüm |
|---|---|---|
| Telefon manifesti indiremiyor | `MANIFEST_URL` ya da `Storage:PublicBaseUrl` içinde `localhost`; LAN IP değişti | LAN IP kullan; değiştiyse `PublicBaseUrl` güncellenir ve `publish` yeniden çalışır |
| Uygulama manifesti reddediyor | İmza tutmuyor; uygulamadaki açık anahtar eski | `apps/mobile/src/packs/keys.ts` ile `keys generate` çıktısını karşılaştır |
| `RequestTimeTooSkewed` | Uykudan sonra WSL2 saati kaymış olabilir | `wsl --shutdown`, Docker Desktop'ı yeniden başlat |
| Yayınlayıcı açılışta duruyor | SQLite'ta FTS5 yok | `PRAGMA compile_options` çıktısında `ENABLE_FTS5` ara |
| Paket taşınamıyor | Windows açık dosyayı taşıtmaz | Bağlantı `Pooling=False` ile kapatılır |

## Kurallar

- `public` yayını ve `promote` yalnız kullanıcı kararıyla; `verify --flavor public --embedded-core …` her public sürümde zorunlu.
- Gömülü `core` EAS Update ile değişmez; yeni içerik yeni ikiliyle ya da manifestle gelir.
- İmza anahtarlarını dosyaya, koda ya da belgeye yazma.
