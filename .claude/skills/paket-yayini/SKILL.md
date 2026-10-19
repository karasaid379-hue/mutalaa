---
name: paket-yayini
description: >-
  Mütâlaa içerik paketlerini üretme, imzalama, yerel S3 deposuna (SeaweedFS) yayımlama, doğrulama ve
  mobil uygulamaya gömülü core paketini alma adımları; Yayınlayıcı komutları, çıkış kodları, depo
  düzeni ve sık hatalar. Paket ya da manifest üretmek, yenilemek veya doğrulamak gerektiğinde kullan.
---

# Paket yayını

Kaynaklar: [Backend API](../../../docs/02-mimari/05-backend-api.md) §10, [İçerik paketleri](../../../docs/03-veri/03-icerik-paketleri.md), [Yerel geliştirme](../../../docs/02-mimari/04-yerel-gelistirme.md) §6–§7. Kapı kuralları: `lisans-kapisi` becerisi.

## Akış

Hat → PostgreSQL (`aday`) → editör onayı (`onayli`) → Yayınlayıcı: kilit → anlık görüntü → lisans kapısı → paket başına `content_digest` → SQLite + FTS5 → sha256 → imzalı manifest → depoya yükleme (paketler, sonra manifest geçmişi, en son `manifest.json`).

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
| `promote --surum <s> --to public` | İç kanalda test edilen yayını `public` için üretir (Kurul onayı şart) |
| `rollback --flavor <f> --to <surum>` | Manifesti önceki yayına çevirir |
| `watch` | API'nin `hazirlaniyor` bıraktığı talepleri işler |

Çıkış kodları: `0` başarı, `2` kapı reddi, `3` doğrulama hatası, `4` depo hatası, `1` diğer.

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

- `public` yayını ve `promote` yalnız Kurul onayı ve kullanıcı kararıyla; `verify --flavor public --embedded-core …` her public sürümde zorunlu.
- Gömülü `core` EAS Update ile değişmez; yeni içerik yeni ikiliyle ya da manifestle gelir.
- İmza anahtarlarını dosyaya, koda ya da belgeye yazma.
