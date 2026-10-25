# A08 · CI iş akışları (GitHub Actions)

> **Sürüm:** 1.3 · **Tarih:** 25 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-33](../../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** [İ-16](../06-insan-adimlari.md) (GitHub özel deposu ve `EXPO_TOKEN`)
> **Ajanlar:** `inceleyici` · `arastirmaci` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 1–2
> **Başlat:** `/asama A08`

## Amaç
Her PR'da üç dilin lint, tip, birim ve vektör denetimleri GitHub Actions'ta koşar ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §7; [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §12 "Her PR"). Faz 0 çıkış ölçütü "Vektör testleri üç dilde CI'da yeşil" bu aşamada kanıtlanır. GitHub deposu (İ-16) hazır olana kadar iş akışları yerelde denetlenir ve aynı komutlar yerelde çalıştırılır.

## Okunacak belgeler
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §6 Git kuralları, §7 CI iş akışları (dört YAML), §8 madde 3
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §12 CI düzeni
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §3 bağımlılık lisans denetimi, §4.1 sabitleme, §4.2 Dependabot
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §10.1 (CI'daki yerel ayar matrisinin nedeni)

## Kapsam
**Yapılır**
- `.github/workflows/ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `eas-build.yml` (Proje yapısı §7).
- PR başlığı denetimi (§6: "CI PR başlığının biçimini denetler"); dosya `pr-title.yml` (öneri).
- Bağımlılık lisans listesi adımları (Teknoloji yığını §3) ve `.github/dependabot.yml` (§4.2; öneri).
- Yerel eşdeğer koşu; İ-16'dan sonra ilk GitHub koşusu.

**Yapılmaz**
- Gece ve sürüm işleri: içerik hattı tam koşusu, altın setler, değişmezlik testleri, `internal` paket üretimi, Maestro, public yapıt taraması (A10, A13, A18, A33, A34).
- EAS derlemesini gerçekten başlatmak (A21 sonrası; İ-15). `eas submit` hiç çalıştırılmaz.
- Dal koruma ayarı: GitHub'da kullanıcı yapar (İ-16 kapsamında).

## Adımlar
### A08.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar:
  - Eylemlerin güncel ana sürümleri: `actions/checkout`, `pnpm/action-setup`, `actions/setup-node`, `actions/setup-dotnet`, `astral-sh/setup-uv`, `expo/expo-github-action` (Proje yapısı §7: "@v4, @v6, @v8 yazım günündeki ana sürümler; güncel ana sürümler Doğrulanacak").
  - Lisans listesi araçları: .NET için lisans aracı, Python için `pip-licenses` (Teknoloji yığını §3: "araç seçimi Doğrulanacak"); `pnpm licenses list` çıktı biçimi.
  - Turborepo'nun ortam değişkeni süzmesi: `LANG` görevlere geçiyor mu ve önbellek anahtarına giriyor mu. Geçmiyorsa `turbo.json`'a `globalEnv: ["LANG"]` eklenir (öneri).
  - Dependabot'un uv desteği (§4.2).
  - EAS'in ücretsiz planındaki aylık derleme sınırı (Proje yapısı §8 madde 3); sonuç A21 ve A33'ün planına not edilir.
  - Kurulum gerektirmeden çalışan bir iş akışı denetleyicisi (ör. actionlint; `uvx` ya da `pnpm dlx` ile).
  - `dotnet test --solution server/Mutalaa.slnx -c Release --no-build` birleşimi MTP kipinde ([K-33](../../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)). [dotnet test belgesi](https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-with-dotnet-test) `-c` ve `--no-build` bayraklarını destekler diyor, ama A02'de yerelde yalnız `--no-build` denendi; `-c Release` ile birleşimi burada doğrulanır, sonuç Proje yapısı §7'ye işlenir. `global.json` içindeki `test.runner` ayarı CI'da `setup-dotnet` ile gelen SDK'da da geçerli olmalı.
- **A04'ten devreden (2026-10-25):**
  - `turbo run test` görevine `LANG` ve `LC_ALL` bildirilir (`"env": ["LANG","LC_ALL"]` ya da `passThroughEnv`). A04'te iki `LANG` değeri için aynı görev özeti çıktı; bildirilmezse yerel ayar karşıtı koşu önbellekten gelir. Yukarıdaki `globalEnv` önerisinin yerine geçebilir.
  - `LANG` karşıtlığı yalnız Linux CI'da görülür (Windows'ta Node iki koşuda da `tr-TR`).
  - NFC içeren vektörler (`content-hash`, `offsets`) Linux'ta yeniden koşar: .NET ICU/NLS ve Python Unicode sürümü Windows'tan farklı olabilir. Üç çalışma zamanının A04'teki sürümleri [A04 aşama kaydında](./A04-capa-ve-test-vektorleri.md#aşama-kaydı-kapanış-2026-10-25).
- **Bitti sayılır:** maddeler kaynaklı aşama kaydında; seçilen araçlar yazılı.

### A08.2 · Dört iş akışı
- Dosyalar Proje yapısı §7'deki YAML'larla yazılır; eylem sürümleri A08.1'e göre güncellenir.
- Henüz olmayan uygulamalara bağlı adımlar dosya varlığıyla korunur (Proje yapısı §7): `expo install --check` adımı `hashFiles('apps/mobile/package.json') != ''`, editör API istemcisi adımı `hashFiles('apps/editor/package.json') != ''`, OpenAPI farkı adımı `hashFiles('server/Mutalaa.Api/openapi/v1.json') != ''` koşuluyla çalışır.
- `ci-ts.yml` matrisinin her ayağında Node'un çözdüğü yerel ayar günlüğe yazılır (öneri); `tr_TR.UTF-8` ayağının gerçekten Türkçe koştuğu böyle görülür.
- İş akışlarında en az izin: `permissions: contents: read` (öneri). Tetikleyici `pull_request`'tir; `pull_request_target` kullanılmaz.
- `ci-dotnet.yml` iş akışında `TESTINGPLATFORM_TELEMETRY_OPTOUT: 1` ve `DOTNET_CLI_TELEMETRY_OPTOUT: 1` ortam değişkenleri tanımlanır; xunit.v3'ün test koşusu Microsoft'a kullanım telemetrisi göndermesin ([Yerel geliştirme §10.4](../../02-mimari/04-yerel-gelistirme.md)).
- `eas-build.yml` §7'deki gibidir; yalnız elle ve `mobile-v*` etiketiyle tetiklenir. `EXPO_TOKEN` yalnız `secrets` içinden okunur.
- **Bitti sayılır:** dört dosya var; yerel denetleyici hatasız.

### A08.3 · PR başlığı, lisans listesi, Dependabot
- `pr-title.yml` (öneri): başlık `<tür>(<kapsam>): <özet>` biçimine karşı bash düzenli ifadesiyle sınanır; türler ve kapsamlar §6'daki listeden. Başlık ortam değişkeni üzerinden okunur, komuta doğrudan gömülmez (betik enjeksiyonuna karşı).
- Lisans listesi: `ci-ts.yml` içinde `pnpm licenses list`, `ci-dotnet.yml` ve `ci-pipeline.yml` içinde A08.1'de seçilen araçlar; çıktı koşu günlüğüne yazılır. GPL, AGPL ya da ticari lisanslı yeni bağımlılıkta PR'ı durdurma kuralı öneridir (Teknoloji yığını §3); kullanıcı onaylarsa açılır. Hat bağımlılıkları dağıtılmaz (`psycopg` LGPL-3.0; Teknoloji yığını §2.4); kural yalnız dağıtılan koda uygulanır.
- `.github/dependabot.yml` (öneri): npm, NuGet, GitHub Actions ve Docker için haftalık gruplu güncelleme (§4.2). Expo'ya bağlı paketler yalnız SDK yükseltmesiyle güncellenir; bu dışlama mobil gelince A21'de eklenir.
- **Bitti sayılır:** dosyalar yerel denetleyiciden geçti; durdurma kuralının açık ya da kapalı olduğu aşama kaydında.

### A08.4 · Yerel eşdeğer koşu
- `ci-ts`: `pnpm install --frozen-lockfile`, ardından `pnpm turbo run lint typecheck test`; ikinci kez `LANG=tr_TR.UTF-8` ile. Türkçe Windows'ta Node zaten Türkçe yerel ayarla koşar; Linux karşılığı ilk GitHub koşusunda görülür.
- `ci-dotnet`: `dotnet tool restore`, `restore --locked-mode`, `format --verify-no-changes --no-restore`, `build -c Release --no-restore`, `test --solution server/Mutalaa.slnx -c Release --no-build` (MTP kipi, K-33; `-c Release --no-build` birleşimi burada doğrulanır). Testcontainers için Docker Desktop açık olmalı.
- `ci-pipeline`: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`. CI `PYTHONUTF8` vermez; Claude Code oturumunda değer `1` olduğu için `pytest` bir kez de `PYTHONUTF8=0` ile koşar.
- **Bitti sayılır:** üç komut grubu yerelde yeşil; çıktı özeti aşama kaydında.

### A08.5 · İlk GitHub koşusu (İ-16'dan sonra)
- Özel depo (`karasaid379-hue/mutalaa`) ve `origin` A00'da hazırlandı. Kullanıcı yalnız `EXPO_TOKEN` sırrını tanımlar (İ-16). `EXPO_TOKEN` Expo hesabı (İ-15) ister; hesap yoksa sır A21'e kalır, `eas-build.yml` zaten elle tetiklenir.
- `git push` yalnız kullanıcının açık onayıyla yapılır; `--force` yasaktır.
- Bir deneme dalı ve PR açılır (başlık örneği `ci(infra): add github actions workflows`). Üç iş akışı ve başlık denetimi koşar. Biçimsiz başlıklı ikinci bir deneme PR'ı başlık denetiminde kırmızı olmalıdır (öneri dosya açıldıysa).
- Sonuçlar GitHub CLI kuruluysa `gh run list` ile, değilse kullanıcının Actions sekmesinden bildirdiğiyle kaydedilir.
- Dal koruması (CI yeşil olmadan birleştirme yok; §6) kullanıcının GitHub planında varsa açılır (Doğrulanacak).
- **Bitti sayılır:** `ci-ts` (iki yerel ayar), `ci-dotnet` ve `ci-pipeline` (Ubuntu ve Windows) yeşil; koşu bağlantıları aşama kaydında.

## Kabul ölçütleri
- [ ] `.github/workflows/` altında dört dosya ve onaylandıysa `pr-title.yml` var; yerel denetleyici hatasız.
- [ ] Eylem ana sürümleri doğrulanmış; kaynak bağlantısı aşama kaydında.
- [ ] A08.4'teki yerel komutların hepsi yeşil (`PYTHONUTF8=0` koşusu dahil).
- [ ] İş akışlarında düz metin sır yok; `EXPO_TOKEN` yalnız `secrets.EXPO_TOKEN` olarak geçiyor (grep).
- [ ] İ-16'dan sonraki ilk PR'da üç iş akışının bütün matris ayakları yeşil; vektör testleri üç dilde CI'da koştu.
- [ ] Biçimsiz başlıklı deneme PR'ı kırmızı (başlık denetimi açıldıysa).

## Doğrulama
```bash
ls .github/workflows/
grep -rn "EXPO_TOKEN" .github/workflows/                      # yalnız secrets.EXPO_TOKEN
grep -rn "pull_request_target" .github/workflows/ || echo "yok"
pnpm install --frozen-lockfile && pnpm turbo run lint typecheck test
LANG=tr_TR.UTF-8 pnpm turbo run test
dotnet tool restore && dotnet restore server/Mutalaa.slnx --locked-mode
dotnet format server/Mutalaa.slnx --verify-no-changes --no-restore
dotnet build server/Mutalaa.slnx -c Release --no-restore && dotnet test --solution server/Mutalaa.slnx -c Release --no-build
(cd pipeline && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest && PYTHONUTF8=0 uv run pytest)
gh run list --limit 10                                        # İ-16'dan sonra; gh kuruluysa
```

## Dikkat
- Sırlar yalnız GitHub sırlarındadır; iş akışı günlüğüne yazdırılmaz. Fork'tan gelen PR'a sır açan tetikleyici kullanılmaz.
- Kilit dosyaları CI'da birebir kullanılır: `pnpm install --frozen-lockfile`, `dotnet restore --locked-mode`, `uv sync --locked`. Kilit dosyası güncel değilse CI kırmızıdır; çözüm kilit dosyasını yerelde güncellemektir.
- `PYTHONUTF8` CI'da bilerek verilmez; kodlama hataları Windows ayağında görünür (§7 yorum satırı).
- Turborepo önbelleği yerelde `LANG` farkını görmeyebilir; A08.1'deki `turbo.json` ayarı yapılmadıysa yerel `tr_TR` koşusu önbellekten gelebilir. Kuşkuda `--force` ile koşulur.
- EAS'in ücretsiz plan sınırı Doğrulanacak (§8 madde 3); `eas-build.yml` elle tetiklendiği için kotayı kendiliğinden harcamaz.
- `git push`, `git reset` ve `git clean` kullanıcı onayı ister (CLAUDE.md kural 11). Ayrıntı: `windows-sorun` (Git Bash ve yol sorunları).

## İnsan adımları
- İ-16 · GitHub özel deposu ve `EXPO_TOKEN` sırrı: A08.5'ten önce gerekir. `EXPO_TOKEN` için İ-15 (Expo hesabı) gerekir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `.github/workflows/ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `eas-build.yml`; onaylanırsa `pr-title.yml`
- `.github/dependabot.yml` (öneri)
- Gerekirse `turbo.json` ortam ayarı
- `/belge-esitle` ile Proje yapısı §7'ye işlenen sürüm farkları ve `LANG` sonucu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A08-ci-is-akislari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A07](./A07-editoryal-veritabani.md) · Sonraki: [A09](./A09-elmalili-ocr-pilotu.md)
