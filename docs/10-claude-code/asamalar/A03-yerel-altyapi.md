# A03 · Yerel altyapı: Docker Compose, PostgreSQL 18, SeaweedFS

> **Sürüm:** 1.1 · **Tarih:** 21 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-11](../../00-ozet/02-karar-defteri.md#k-11--veritabanı-postgresql-18) · [K-20](../../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · **İnsan adımı:** [İ-01](../06-insan-adimlari.md) (Docker Desktop ve WSL2)
> **Ajanlar:** `sunucu-gelistirici` · `arastirmaci` · `inceleyici` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 1–2
> **Başlat:** `/asama A03`

## Amaç
Yerel altyapı tek komutla kalkar: `postgres:18` ve SeaweedFS'in S3 arayüzü (K-21). SeaweedFS'in imajı, bayrakları ve kimlik dosyası doğrulanır; anonim okuma ve HTTP Range istekleri ilk kurulumda sınanır. Yedekleme ve geri yükleme betikleri yazılır ve bir gidiş-dönüş denemesiyle kanıtlanır. Faz 0 çıkış ölçütü "Yerel ortam tek komutla kalkıyor" bu aşamada sağlanır.

## Okunacak belgeler
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §2 Windows hazırlığı (A00 kapsamında), §4 `docker-compose.yml` ve notlar, §5 ortam dosyaları, §6 adım 1 ve 9, §7 günlük akış, §9 yedekleme, §10.3 port ve ağ, §11 açık sorular
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §4.1 (Docker imajlarının sabitlenmesi)
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`infra/local`, `scripts/`, `.dockerignore`), §1.1 (`data/backups`)
- [Genel mimari](../../02-mimari/01-genel-mimari.md): yarım indirmenin Range ile sürdürülmesi (hata tablosu)

## Kapsam
**Yapılır**
- `docker-compose.yml` (§4), kök `.env.example` ve `pipeline/.env.example` (§5), `.dockerignore` (§4 notları).
- SeaweedFS kimlik dosyası şablonu `infra/local/s3.example.json` (gerekçe A03.2).
- `scripts/backup-db.ps1`, `scripts/restore-db.ps1`, `scripts/lan-ip.ps1`.
- PostgreSQL ve SeaweedFS doğrulamaları; yedek gidiş-dönüş denemesi.

**Yapılmaz**
- API, Yayınlayıcı ve editör Dockerfile'ları (A14, A13, A15). `app` profili bu dosyalar gelene kadar başlatılmaz; yalnız yapılandırması denetlenir.
- Göçler ve `seed` (A07). `apps/mobile/.env.example` (A21). Paket yayını ve manifest (A13).
- Günlük yedek görevinin Windows Görev Zamanlayıcı'ya kaydı: sistem ayarıdır, kullanıcı yapar (§9); aşama yalnız betiği hazırlar.

## Adımlar
### A03.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar (Yerel geliştirme §4 yorum satırı ve §11):
  - SeaweedFS imaj adı (`chrislusf/seaweedfs`), güncel kararlı etiket, `server -dir=/data -s3 -s3.port=8333 -s3.config=…` bayrakları ve `s3.json` biçimi (`identities`, `credentials`, `actions`, anonim `Read`).
  - `amazon/aws-cli` imajında `s3api head-bucket` ve `create-bucket` kullanımı.
  - Uykudan sonra görülen `RequestTimeTooSkewed` belirtisi (§10.3, Doğrulanacak); bilgi notu olarak kalır.
  - AWS CLI v2'nin yeni sürümlerinde varsayılan açık olan istek bütünlük sağlamalarının SeaweedFS ile çalışıp çalışmadığı. Çalışmıyorsa `s3-init` servisine `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` ve `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required` ortam değişkenleri eklenir (A13.1 aynı denetimi .NET SDK için yapar).
- Etiket `.env.example` içindeki `SEAWEEDFS_TAG` değerine sabitlenir (`latest` yerine; Teknoloji yığını §4.1, öneri).
- İmaj, bayrak ya da dosya biçimi dokümandan farklı çıkarsa fark `/belge-esitle` ile Yerel geliştirme §4'e işlenir.
- **Bitti sayılır:** maddeler kaynak bağlantısı ve okuma tarihiyle aşama kaydında.

### A03.2 · Compose ve ortam dosyaları
- `docker-compose.yml` Yerel geliştirme §4'teki metinle yazılır; yalnız A03.1'in değiştirdiği değerler farklıdır.
- `.env.example` ve `pipeline/.env.example` §5'teki içerikle; yalnız yer tutucu değer taşır.
- `infra/local/s3.json` gizli anahtar taşır ve depoya girmez: şablon `infra/local/s3.example.json` (§4'teki içerik, yer tutucu anahtarlar `.env.example` ile aynı), `infra/local/s3.json` satırı `.gitignore`'a eklenir (Yerel geliştirme §4, §5). Compose dosyası §4'teki gibi `./infra/local/s3.json` bağlar.
- `.dockerignore`: `**/node_modules`, `**/bin`, `**/obj`, `data/`, `.git` (§4 notları).
- `infra/local/s3.json` yoksa şablondan kopyalanır: `cp -n infra/local/s3.example.json infra/local/s3.json`. `.env` ve `pipeline/.env` dosyalarını kullanıcı oluşturur (`cp -n .env.example .env` ve `cp -n pipeline/.env.example pipeline/.env`; PowerShell'de `Copy-Item`): Claude Code `.env` dosyalarını okuyamaz, oluşturamaz ve düzenleyemez (izin kuralı). Kullanıcı parolayı değiştirirse `s3.json`'daki anahtarı ve `pipeline/.env` içindeki `MUTALAA_DB_URL` parolasını da aynı yapar; hat bu dosyayı A10'da kullanır.
- **Bitti sayılır:** `docker compose config --quiet` ve `docker compose --profile app config --quiet` 0 ile çıkıyor.
- **Uygulamada bilinçli sapmalar (21 Ekim 2026; Yerel geliştirme §4 ve §5 koda göre eşitlendi):**
  - `amazon/aws-cli` etiketi `latest` değil, `AWSCLI_TAG` değişkeniyle sabittir (`amazon/aws-cli:${AWSCLI_TAG:-2.38.3}`); `SEAWEEDFS_TAG` 4.48'dir. İkisi de `.env.example` içindedir.
  - `postgres` sağlık denetimi `pg_isready -h 127.0.0.1` ile TCP'yi dener; imajın ilk kurulumdaki geçici sunucusu yalnız unix soketini dinler.
  - `.dockerignore` beş kalıba ek olarak `.tmp/`, `**/.env`, `**/.env.*` (`!**/.env.example` hariç) ve `infra/local/s3.json` içerir; gizli değerler derleme bağlamına girmesin diye.

### A03.3 · Altyapıyı kaldırma ve PostgreSQL denetimi
- İ-01: Docker Desktop çalışıyor (`docker info`). Çalışmıyorsa kullanıcıdan başlatması istenir.
- `docker compose up -d`, ardından `docker compose ps -a`: `postgres` "healthy", `s3` çalışıyor, `s3-init` "exited (0)" (§6 adım 1). Durmuş konteynerler `-a` olmadan listelenmez.
- Denetim sorguları `.tmp/a03-kontrol.sql` dosyasına yazılır ve konteynerdeki ortam değişkenleriyle çalıştırılır (`.env` okunmaz):
  - `SHOW server_version;` (18)
  - `SELECT datcollate FROM pg_database WHERE datname = current_database();` (`C.UTF-8`)
  - `SELECT cfgname FROM pg_ts_config WHERE cfgname IN ('turkish','arabic') ORDER BY 1;` (iki satır; A07'deki `tsv_tr` ve `tsv_ar` için)
  - `SELECT count(*) FROM pg_collation WHERE collname = 'tr-x-icu';` (imajdaki ICU desteği; §4 notu, Doğrulanacak)
  - `SELECT count(*) FROM pg_available_extensions WHERE name = 'vector';` (yalnız bilgi; `embedding` tablosu v1.x)
- **Bitti sayılır:** beş sorgunun çıktısı aşama kaydında; `tr-x-icu` yoksa Türkçe sıralama notu düşülür.

### A03.4 · SeaweedFS S3 doğrulaması (Yerel geliştirme §11 madde 3)
- 1 MiB'lık deneme dosyası `.tmp/aralik.bin` olarak üretilir (`openssl rand -out .tmp/aralik.bin 1048576`; Git for Windows `openssl` taşır, `/dev/urandom` yolu klasör bekçisine takılır) ve kimlikli olarak yüklenir:
  `docker compose run --rm -T --entrypoint aws s3-init --endpoint-url http://s3:8333 s3 cp - s3://mutalaa/dev/deneme/aralik.bin < .tmp/aralik.bin`
  (kova adı `.env.example` varsayılanıdır; değiştirildiyse komutta da değişir.)
- Anonim okuma: `curl -I http://localhost:8333/mutalaa/dev/deneme/aralik.bin` → `200`; `Accept-Ranges` ve `ETag` başlıkları kaydedilir.
- Range: `curl -s http://localhost:8333/mutalaa/dev/deneme/aralik.bin -r 0-1023 -o /dev/null -w '%{http_code} %{size_download}\n'` → `206 1024`.
- Sürdürme benzetimi: dosya iki parçada indirilir (`-r 0-524287` ve `-r 524288-`), birleştirilir; `sha256sum` özgün dosyanınkiyle aynıdır (mobil indirme kuyruğunun `.part` sürdürmesi).
- Anonim yazma reddedilir: `curl -s http://localhost:8333/mutalaa/dev/deneme/yetkisiz.txt -X PUT --data x -o /dev/null -w '%{http_code}\n'` → `403` (beklenen; öneri).
- LAN tarafı: `lan-ip.ps1` çıktısındaki IP ile `curl -I http://<LAN-IP>:8333/mutalaa/dev/deneme/aralik.bin` (güvenlik duvarı kuralı Yerel geliştirme §2).
- Deneme nesneleri silinir: `docker compose run --rm -T --entrypoint aws s3-init --endpoint-url http://s3:8333 s3 rm --recursive s3://mutalaa/dev/deneme/`.
- **Bitti sayılır:** `200`, `206 1024`, `403` ve özet eşitliği aşama kaydında. Biri tutmazsa durulur; yedek aday Garage için `/karar` önerilir (§4 notu).

### A03.5 · Betikler ve yedek gidiş-dönüşü
- `scripts/backup-db.ps1` ve `scripts/restore-db.ps1` Yerel geliştirme §9'daki metinle. `scripts/lan-ip.ps1` §6 adım 9'daki `Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi"` komutuyla; bağdaştırıcı adı parametredir, varsayılanı `"Wi-Fi"` (öneri).
- Çağrı biçimi: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/<betik>.ps1`. Geri yükleme dosya yolunu konumsal argüman olarak alır.
- Gidiş-dönüş: `public.yedek_deneme` tablosu ve bir satır oluşturulur → yedek alınır → tablo silinir → en son yedek geri yüklenir → satır okunur → tablo silinir. Komutlar Doğrulama bloğundadır; geri yükleme (`pg_restore --clean --if-exists`) yalnız az önce alınan yedekle yapılır.
- **Bitti sayılır:** `data/backups/mutalaa-*.dump` oluştu; geri yüklemeden sonra deneme satırı okundu; `lan-ip.ps1` bir IPv4 adresi yazdı.
- **Uygulamada bilinçli sapmalar (21 Ekim 2026; Yerel geliştirme §6 adım 9 ve §9 koda göre eşitlendi):**
  - Yedek atomiktir: döküm konteynerde alınır, `pg_restore --list` ile doğrulanır, `.partial` adıyla kopyalanır ve başarıdan sonra yeniden adlandırılır. Altın arşivi de geçici adla yazılıp yeniden adlandırılır. Zaman damgası saniyelidir (`yyyyMMdd-HHmmss`).
  - Geri yükleme `--single-transaction` kullanır; yarıda kalan geri yükleme veritabanını yarım bırakmaz ve ilk hatada durur (`--exit-on-error` gerekmez).
  - Betikler `$ErrorActionPreference = "Stop"` ile çalışır, konteynerdeki geçici döküm başarıda da hatada da silinir ve hata kodu aktarılır. `Write-Error` çıkış kodunu 1'e düşürdüğü için hata iletisi `[Console]::Error.WriteLine` ile yazılır. Özel kodlar: `restore-db.ps1` dosya yoksa 2, `lan-ip.ps1` adres bulamazsa 1.
  - `restore-db.ps1` yolu bağıl yola çevirir, çünkü `docker compose cp` Windows `C:\` yolunu servis adı sanabilir. `lan-ip.ps1` `169.254.*` adreslerini atlar.
  - Betikler ASCII ve CRLF'tir (Windows PowerShell 5.1, BOM'suz UTF-8 dosyayı ANSI okur).

## Kabul ölçütleri
- [ ] `docker compose config --quiet` ve `docker compose --profile app config --quiet` 0 ile çıkıyor.
- [ ] `docker compose up -d` sonrası `docker compose ps -a`: `postgres` healthy, `s3` çalışıyor, `s3-init` exited (0).
- [ ] PostgreSQL sürümü 18; veritabanı harmanlaması `C.UTF-8`; `turkish` ve `arabic` yapılandırmaları var.
- [ ] Anonim GET `200`, Range GET `206` ve 1024 bayt, anonim PUT `403`; iki parçalı indirmenin SHA-256'sı özgün dosyayla aynı.
- [ ] Yedek → silme → geri yükleme deneme satırını geri getiriyor.
- [ ] `.env`, `pipeline/.env` ve `infra/local/s3.json` git dışı (`git check-ignore` üçünü de gösteriyor); `.env.example`, `pipeline/.env.example` ve `infra/local/s3.example.json` git dışı değil; kullanıcı iki `.env` dosyasını oluşturdu (`test -f`).
- [ ] A03.1 maddeleri kaynaklı; dokümandan sapma varsa `/belge-esitle` ile işlendi.

## Doğrulama
```bash
docker compose config --quiet && docker compose --profile app config --quiet
docker compose up -d && docker compose ps -a
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' < .tmp/a03-kontrol.sql
mkdir -p .tmp && openssl rand -out .tmp/aralik.bin 1048576
docker compose run --rm -T --entrypoint aws s3-init --endpoint-url http://s3:8333 s3 cp - s3://mutalaa/dev/deneme/aralik.bin < .tmp/aralik.bin
curl -I http://localhost:8333/mutalaa/dev/deneme/aralik.bin                                         # 200
curl -s http://localhost:8333/mutalaa/dev/deneme/aralik.bin -r 0-1023 -o /dev/null -w '%{http_code} %{size_download}\n'   # 206 1024
curl -s http://localhost:8333/mutalaa/dev/deneme/aralik.bin -r 0-524287 -o .tmp/parca1
curl -s http://localhost:8333/mutalaa/dev/deneme/aralik.bin -r 524288- -o .tmp/parca2
cat .tmp/parca1 .tmp/parca2 | sha256sum && sha256sum .tmp/aralik.bin                               # iki özet aynı
curl -s http://localhost:8333/mutalaa/dev/deneme/yetkisiz.txt -X PUT --data x -o /dev/null -w '%{http_code}\n'            # 403
docker compose run --rm -T --entrypoint aws s3-init --endpoint-url http://s3:8333 s3 rm --recursive s3://mutalaa/dev/deneme/
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE IF EXISTS public.yedek_deneme; CREATE TABLE public.yedek_deneme (x int); INSERT INTO public.yedek_deneme VALUES (1);"'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1 && ls data/backups/
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE public.yedek_deneme;"'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/restore-db.ps1 "$(ls -t data/backups/mutalaa-*.dump | head -n 1)"
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "SELECT x FROM public.yedek_deneme;"'   # 1
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE public.yedek_deneme;"'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lan-ip.ps1
test -f .env && test -f pipeline/.env && echo "iki .env dosyası var"
git check-ignore -v .env pipeline/.env infra/local/s3.json                                           # üç satır
git check-ignore .env.example pipeline/.env.example infra/local/s3.example.json || echo "örnekler izleniyor"
```
PowerShell'de elle çalıştırılacaksa `curl` yerine `curl.exe` yazılır (Yerel geliştirme §10.3).

## Dikkat
- PostgreSQL 18 imajında birim `/var/lib/postgresql` noktasına bağlanır; eski örneklerdeki `/var/lib/postgresql/data` kullanılmaz (§4 notu).
- `docker compose down -v` veritabanını siler: önce `backup-db.ps1`, sonra kullanıcı onayı (kural).
- 5432 doluysa ya da Hyper-V ayrılmış port aralığına düşüyorsa `.env` içinde port değiştirilir (§10.3); bunu kullanıcı yapar.
- S3 portu `0.0.0.0:8333`'e açıktır; yalnız "Özel" ağda ve güvenlik duvarı kuralıyla kullanılır (§2).
- Git Bash `/` ile başlayan argümanları Windows yoluna çevirebilir; konteyner içi yollar bu bloktaki gibi `sh -c '…'` içinde tırnaklı verilir. Ayrıntı: `windows-sorun`.
- `.ps1` dosyaları CRLF'tir (`.gitattributes`). İkili çıktı `>` ile yönlendirilmez; döküm konteynerde yazılıp `docker compose cp` ile alınır (§9).
- `infra/local/s3.json` OneDrive'da "yalnız çevrimiçi" kalmamalıdır; bağlama yerel dosya ister (öneri).
- MinIO kullanılmaz (K-21).

## İnsan adımları
- İ-01 · Docker Desktop ve WSL2 kurulu ve çalışıyor: A03.3'ten önce gerekir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- `.env` ve `pipeline/.env` dosyalarının örneklerinden kopyalanması ve gerekiyorsa parolanın iki dosyada da aynı biçimde değiştirilmesi kullanıcı işidir (Claude Code `.env` okuyamaz ve yazamaz); A03.3'ten önce.

## Çıktılar
- `docker-compose.yml`, `.env.example`, `pipeline/.env.example`, `.dockerignore`
- `infra/local/s3.example.json`; `.gitignore` eki (`infra/local/s3.json`)
- `scripts/backup-db.ps1`, `scripts/restore-db.ps1`, `scripts/lan-ip.ps1`
- Git dışı: `.env`, `pipeline/.env`, `infra/local/s3.json`, `data/backups/`; Docker birimleri `pgdata`, `s3data`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A03-yerel-altyapi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## A03.1 kaynak kaydı (okuma 2026-10-21)

| Konu | Bulgu | Kaynak |
|---|---|---|
| SeaweedFS imajı ve etiketi | İmaj `chrislusf/seaweedfs`; kararlı etiket 4.48 (GitHub sürümü 2026-09-28) | [Sürüm 4.48](https://github.com/seaweedfs/seaweedfs/releases/tag/4.48) · [Docker Hub](https://hub.docker.com/r/chrislusf/seaweedfs) |
| `server` bayrakları | `-dir`, `-s3`, `-s3.port`, `-s3.config` | [weed/command/server.go](https://github.com/seaweedfs/seaweedfs/blob/master/weed/command/server.go) |
| `s3.json` biçimi ve anonim kimlik | `identities`, `credentials`, `actions`; anonim kimlik adı `anonymous` | [docker/compose/s3.json](https://github.com/seaweedfs/seaweedfs/blob/master/docker/compose/s3.json) · [S3 Credentials](https://github.com/seaweedfs/seaweedfs/wiki/S3-Credentials) |
| `head-bucket` | Kova yokken 404 `NoSuchBucket` döner | weed/s3api/s3api_bucket_handlers.go ([depo](https://github.com/seaweedfs/seaweedfs/blob/master/weed/s3api/s3api_bucket_handlers.go)) |
| `amazon/aws-cli` etiketi | 2.38.3 (Docker Hub güncellemesi 2026-10-20); `ENTRYPOINT` `aws` | [Docker Hub](https://hub.docker.com/r/amazon/aws-cli) · [Dockerfile](https://github.com/aws/aws-cli/blob/v2/docker/Dockerfile) |
| `create-bucket` | `us-east-1` bölgesinde `LocationConstraint` gerekmez | [create-bucket](https://docs.aws.amazon.com/cli/latest/reference/s3api/create-bucket.html) |
| Checksum davranışı | AWS CLI varsayılanı değişti; `AWS_REQUEST_CHECKSUM_CALCULATION` ve `AWS_RESPONSE_CHECKSUM_VALIDATION` ortam değişkenleri `when_required` değerini alabilir | [ortam değişkenleri](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) · [aws-cli#9214](https://github.com/aws/aws-cli/issues/9214) |
| `RequestTimeTooSkewed` | Uyku sonrası WSL2 saat kayması bilinen sorun; Docker Desktop'a özgü resmî çözüm bulunamadı (bilgi notu) | [microsoft/WSL#10006](https://github.com/microsoft/WSL/issues/10006) |

Canlı sınamayla doğrulananlar:
- Anonim `PUT` için 403 ve açık uçlu `Range` (`bytes=524288-`) kaynak kodundan çıkarımdı; A03.4'te canlı doğrulandı (anonim `PUT` 403, açık uçlu Range 206).
- AWS CLI 2.38.3'ün varsayılan checksum davranışı SeaweedFS 4.48 ile canlı sınandı ve sorun çıkarmadı; `when_required` ortam değişkenleri eklenmedi.
- Anonim `Read` eyleminin bütün kovalara uygulanması ve kova kısıtının sürüme bağlı davranışı için [SeaweedFS #7134](https://github.com/seaweedfs/seaweedfs/issues/7134) okundu; canlı sınanmadı (bugün tek kova var).

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A02](./A02-tek-depo-iskeleti.md) · Sonraki: [A04](./A04-capa-ve-test-vektorleri.md)
