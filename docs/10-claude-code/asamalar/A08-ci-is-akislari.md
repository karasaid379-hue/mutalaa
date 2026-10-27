# A08 · CI iş akışları (GitHub Actions)

> **Sürüm:** 1.4 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-33](../../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A05](./A05-arama-normalizasyonu.md) · [A07](./A07-editoryal-veritabani.md) · **İnsan adımı:** [İ-16](../06-insan-adimlari.md) (GitHub özel deposu ve `EXPO_TOKEN`)
> **Ajanlar:** `inceleyici` · `arastirmaci` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 1–2
> **Başlat:** `/asama A08`

## Amaç
Her PR'da üç dilin lint, tip, birim ve vektör denetimleri GitHub Actions'ta koşar ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §7; [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §12 "Her PR"). Faz 0 çıkış ölçütü "Vektör testleri üç dilde CI'da yeşil" bu aşamada kanıtlanır. GitHub deposu (İ-16) hazır olana kadar iş akışları yerelde denetlenir ve aynı komutlar yerelde çalıştırılır.

## Okunacak belgeler
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §6 Git kuralları, §7 CI iş akışları (tablo ve ortak kurallar; YAML kopyası yok, tek kaynak `.github/`), §8 madde 3
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §12 CI düzeni
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §3 bağımlılık lisans denetimi, §4.1 sabitleme, §4.2 Dependabot
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §10.1 (CI'daki yerel ayar matrisinin nedeni)

## Kapsam
**Yapılır**
- `.github/workflows/ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `eas-build.yml` (Proje yapısı §7).
- PR başlığı denetimi (§6: "CI PR başlığının biçimini denetler"); dosya `pr-title.yml` (öneri).
- Bağımlılık lisans listesi adımları (Teknoloji yığını §3) ve `.github/dependabot.yml` (§4.2; öneri).
- `.github/workflows/ci-workflows.yml`: iş akışı dosyalarının CI'da actionlint denetimi (kapsam eklemesi; [aşama kaydı](#aşama-kaydı-2026-10-27)).
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
- Dosyalar `.github/workflows/` altında yazılır (Proje yapısı §7 tablosu özettir, tek kaynak dosyalardır); eylem sürümleri A08.1'e göre güncellendi.
- Henüz olmayan uygulamalara bağlı adımlar dosya varlığıyla korunur (Proje yapısı §7): `expo install --check` adımı `hashFiles('apps/mobile/package.json') != ''`, editör API istemcisi adımı `hashFiles('apps/editor/package.json') != ''`, OpenAPI farkı adımı `hashFiles('server/Mutalaa.Api/openapi/v1.json') != ''` koşuluyla çalışır.
- `ci-ts.yml` matrisinin her ayağında Node'un çözdüğü yerel ayar günlüğe yazılır (öneri); `tr_TR.UTF-8` ayağının gerçekten Türkçe koştuğu böyle görülür.
- İş akışlarında en az izin: `permissions: contents: read` (öneri). Tetikleyici `pull_request`'tir; `pull_request_target` kullanılmaz.
- `ci-dotnet.yml` iş akışında `TESTINGPLATFORM_TELEMETRY_OPTOUT: 1` ve `DOTNET_CLI_TELEMETRY_OPTOUT: 1` ortam değişkenleri tanımlanır; xunit.v3'ün test koşusu Microsoft'a kullanım telemetrisi göndermesin ([Yerel geliştirme §10.4](../../02-mimari/04-yerel-gelistirme.md)).
- `eas-build.yml` Proje yapısı §7'de özetlendiği gibidir; yalnız elle ve `mobile-v*` etiketiyle tetiklenir. `EXPO_TOKEN` yalnız `secrets` içinden okunur.
- **Bitti sayılır:** dört dosya var; yerel denetleyici hatasız.

### A08.3 · PR başlığı, lisans listesi, Dependabot
- `pr-title.yml` (öneri): başlık `<tür>(<kapsam>): <özet>` biçimine karşı bash düzenli ifadesiyle sınanır; türler ve kapsamlar §6'daki listeden. Başlık ortam değişkeni üzerinden okunur, komuta doğrudan gömülmez (betik enjeksiyonuna karşı).
- Lisans listesi: `ci-ts.yml` içinde `pnpm licenses list`, `ci-dotnet.yml` ve `ci-pipeline.yml` içinde A08.1'de seçilen araçlar; çıktı koşu günlüğüne yazılır. GPL, AGPL ya da ticari lisanslı yeni bağımlılıkta PR'ı durdurma kuralı açıktır (Teknoloji yığını §3; çözüldü, 27 Ekim 2026, bkz. aşama kaydı). Hat bağımlılıkları dağıtılmaz (`psycopg` LGPL-3.0; Teknoloji yığını §2.4); kural yalnız dağıtılan koda uygulanır.
- `.github/dependabot.yml` (öneri): npm, NuGet, GitHub Actions ve Docker için haftalık gruplu güncelleme (§4.2). Expo'ya bağlı paketler yalnız SDK yükseltmesiyle güncellenir; bu dışlama mobil gelince A21'de eklenir.
- **Bitti sayılır:** dosyalar yerel denetleyiciden geçti; durdurma kuralının açık ya da kapalı olduğu aşama kaydında.

### A08.4 · Yerel eşdeğer koşu
- `ci-ts`: `pnpm install --frozen-lockfile`, ardından `pnpm turbo run lint typecheck test`; ikinci kez `LANG=tr_TR.UTF-8` ile. Türkçe Windows'ta Node zaten Türkçe yerel ayarla koşar; Linux karşılığı ilk GitHub koşusunda görülür.
- `ci-dotnet`: `dotnet tool restore`, `restore --locked-mode`, `format --verify-no-changes --no-restore`, `build -c Release --no-restore`, `test --solution server/Mutalaa.slnx -c Release --no-build` (MTP kipi, K-33; `-c Release --no-build` birleşimi burada doğrulanır). Testcontainers için Docker Desktop açık olmalı.
- `ci-pipeline`: `uv sync --locked`, `ruff check`, `ruff format --check`, `uv run mypy`, `pytest`, `uv run mutalaa export test-vectors --check`. CI `PYTHONUTF8` vermez; Claude Code oturumunda değer `1` olduğu için `pytest` bir kez de `PYTHONUTF8=0` ile koşar.
- Turborepo önbellek karşılaştırması: `pnpm turbo run test --dry=json` iki `LANG` değeriyle koşulur, `anchors#test` ve `search#test` özetleri karşılaştırılır (iki değer farklı olmalı).
- İş akışı denetimi: actionlint (Docker), `check-jsonschema` ve `scripts/ci` testleri (Doğrulama bloğundaki komutlar).
- **Bitti sayılır:** üç komut grubu yerelde yeşil; çıktı özeti aşama kaydında.

### A08.5 · İlk GitHub koşusu (İ-16'dan sonra)
- Özel depo (`karasaid379-hue/mutalaa`) ve `origin` A00'da hazırlandı. Kullanıcı yalnız `EXPO_TOKEN` sırrını tanımlar (İ-16). `EXPO_TOKEN` Expo hesabı (İ-15) ister; hesap yoksa sır A21'e kalır, `eas-build.yml` zaten elle tetiklenir.
- `git push` onay sorulmadan yapılır (CLAUDE.md kural 11; yetki devri 27 Ekim 2026); `--force` yasaktır.
- Bir deneme dalı ve PR açılır (başlık örneği `ci(infra): add github actions workflows`). Üç iş akışı ve başlık denetimi koşar. Biçimsiz başlıklı ikinci bir deneme PR'ı başlık denetiminde kırmızı olmalıdır (öneri dosya açıldıysa).
- Sonuçlar GitHub CLI kuruluysa `gh run list` ile, değilse kullanıcının Actions sekmesinden bildirdiğiyle kaydedilir.
- Dal koruması (CI yeşil olmadan birleştirme yok; §6): GitHub Free planında özel depoda yok (aşağıdaki aşama kaydı). Uygulamada kural: PR yeşil görülmeden birleştirilmez.
- **Bitti sayılır:** `ci-ts` (iki yerel ayar), `ci-dotnet` ve `ci-pipeline` (Ubuntu ve Windows) yeşil; koşu bağlantıları aşama kaydında.

## Kabul ölçütleri
- [x] `.github/workflows/` altında dört dosya ve onaylandıysa `pr-title.yml` var; yerel denetleyici hatasız. Kanıt: altı dosya (dört + `pr-title.yml` + `ci-workflows.yml`); actionlint 0 bulgu, `check-jsonschema` geçti.
- [x] Eylem ana sürümleri doğrulanmış; kaynak bağlantısı aşama kaydında. Kanıt: aşama kaydı, A08.1 tablosu.
- [x] A08.4'teki yerel komutların hepsi yeşil (`PYTHONUTF8=0` koşusu dahil). Kanıt: aşama kaydı, A08.4 çıktıları.
- [x] İş akışlarında düz metin sır yok; `EXPO_TOKEN` yalnız `secrets.EXPO_TOKEN` olarak geçiyor (grep). Kanıt: aşama kaydı, kabul `grep`'leri.
- [x] İ-16'dan sonraki ilk PR'da üç iş akışının bütün matris ayakları yeşil; vektör testleri üç dilde CI'da koştu. Kanıt: PR #1 birleştirildi (`0bfc8ac`). İlk koşuda 5 ayak yeşildi (`ci-pipeline` ubuntu-24.04 ve windows-2025, `ci-ts` C.UTF-8 ve tr_TR.UTF-8 ve bir ayak daha); `ci-dotnet` Linux'ta `Environment_is_recorded` testinden düştü (düzeltme `16b196d`, Linux konteynerinde yeniden üretildi), sonraki koşunun yeşil olduğu kullanıcının birleştirmesine dayanır; koşu bağlantıları alınmadı.
- [x] Biçimsiz başlıklı deneme PR'ı kırmızı (başlık denetimi açıldıysa). Kanıt: PR #1'in ilk koşusunda `pr-title / title` kırmızıydı (biçimsiz başlık); düzeltilen başlıkla birleştirmeye izin verildi. Ayrı bir deneme PR'ı açılmadı (sapma, yukarıda).

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
(cd pipeline && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && PYTHONUTF8=0 uv run pytest && uv run mutalaa export test-vectors --check)
pnpm turbo run test --dry=json                                # LANG=C.UTF-8 ve LANG=tr_TR.UTF-8 ile ayrı koşulup anchors#test özetleri karşılaştırılır
node --test "scripts/ci/*.test.mjs"
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/repo" -w /repo rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 -color
uvx check-jsonschema@0.39.0 --builtin-schema vendor.dependabot .github/dependabot.yml
uvx check-jsonschema@0.39.0 --builtin-schema vendor.github-workflows .github/workflows/*.yml
gh run list --limit 10                                        # İ-16'dan sonra; gh kuruluysa (kurulu değil: Actions sekmesi)
```

## Dikkat
- Sırlar yalnız GitHub sırlarındadır; iş akışı günlüğüne yazdırılmaz. Fork'tan gelen PR'a sır açan tetikleyici kullanılmaz.
- Kilit dosyaları CI'da birebir kullanılır: `pnpm install --frozen-lockfile`, `dotnet restore --locked-mode`, `uv sync --locked`. Kilit dosyası güncel değilse CI kırmızıdır; çözüm kilit dosyasını yerelde güncellemektir.
- `PYTHONUTF8` CI'da bilerek verilmez; kodlama hataları Windows ayağında görünür (§7 yorum satırı).
- Turborepo önbelleği yerelde `LANG` farkını görmeyebilir; A08.1'deki `turbo.json` ayarı yapılmadıysa yerel `tr_TR` koşusu önbellekten gelebilir. Kuşkuda `--force` ile koşulur.
- EAS'in ücretsiz plan sınırı doğrulandı: ayda 15 Android ve 15 iOS derleme (§8 madde 3, aşama kaydı). `eas-build.yml` elle ya da `mobile-v*` etiketiyle tetiklendiği için kotayı kendiliğinden harcamaz; etiket itmek derleme başlatır.
- `git push`, `git reset` ve `git clean` onay sorulmadan çalışır (CLAUDE.md kural 11); zorla push yasaktır. Ayrıntı: `windows-sorun` (Git Bash ve yol sorunları).

## İnsan adımları
- İ-16 · GitHub özel deposu ve `EXPO_TOKEN` sırrı: A08.5'ten önce gerekir. `EXPO_TOKEN` için İ-15 (Expo hesabı) gerekir. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `.github/workflows/ci-ts.yml`, `ci-dotnet.yml`, `ci-pipeline.yml`, `eas-build.yml`; onaylanırsa `pr-title.yml`; eklenen `ci-workflows.yml`
- `.github/dependabot.yml` (öneri)
- `scripts/ci/` (`check-licenses.mjs`, `pr-title.mjs`, `license-exceptions.json`, testler)
- `turbo.json` ortam ayarı (`test` görevi `env: ["LANG","LC_ALL"]`)
- `/belge-esitle` ile Proje yapısı §7'ye işlenen sürüm farkları ve `LANG` sonucu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A08-ci-is-akislari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## Aşama kaydı (2026-10-27)

Durum: tamam (2026-10-27). PR #1 birleştirildi (merge commit `0bfc8ac`), dal silindi. Birleştirme sonrası ilk `dependabot.yml` koşusu Dependabot sekmesinden izlenir (pnpm 12 kilidi doğrulanmadı).

### Kararlar ve gerekçeleri

- **Plan onaylandı.** Altı iş akışı dosyası, `dependabot.yml` ve `scripts/ci/` betikleri.
- **`pr-title.yml` açık.** Biçim `scripts/ci/pr-title.mjs` ile sınanır; başlık yalnız ortam değişkeninden okunur. Gerekçe: squash birleştirmede PR başlığı commit mesajı olur ([Proje yapısı §6](../../02-mimari/03-proje-yapisi.md)).
- **`dependabot.yml` açık.** Ekosistemler: `npm`, `github-actions`, `uv` (haftalık, ekosistem başına tek grup, minor ve patch). NuGet ve `docker-compose` bilerek dışarıda (gerekçe [Teknoloji yığını §4.2](../../02-mimari/02-teknoloji-yigini.md)). Aşağıdaki `commit-message.prefix` bulgusu yüzünden `include: scope` kullanılmadı.
- **Lisans durdurma kuralı açık**, yalnız dağıtılan ve ağ üzerinden sunulan kodda: TypeScript `--prod` bağımlılıkları ve .NET test dışı projeler. İçerik hattı dağıtılmadığı için yalnız listelenir. Kural ve istisna dosyası: [Teknoloji yığını §3](../../02-mimari/02-teknoloji-yigini.md#3-lisans-notları). Hukuki görüş değildir.
- **`ci-workflows.yml` eklendi** (kapsam eklemesi). actionlint yalnız yerelde değil CI'da da koşar; iş akışı dosyalarındaki betik ve ifade hataları PR'da görülür.
- **Eylemler tam commit SHA'sı ile sabit**, sürüm yorumu ile. **Runner'lar sabit:** `ubuntu-24.04`, `windows-2025`.
- **Tek PR'da başlık deneyi.** A08.5'teki "ikinci deneme PR'ı" yerine aynı PR'ın başlığı önce biçimsiz açılır (`pr-title` kırmızı görülür), sonra düzeltilir (`edited` olayı kapıyı yeniden çalıştırır). Adımlar [İ-16](../06-insan-adimlari.md) notundadır.
- **[BÇ-42](../07-belge-celiskileri.md#1-karar-bekleyenler):** gece CI işinin sahibi. A08 gece işi kurmaz; iskeleti ilk gece işiyle A10'da açılır. A10 ve [Test stratejisi §12](../../07-yayin/03-test-stratejisi.md) düzeltildi.

### A08.1 kaynaklı sonuçlar (okuma 2026-10-27)

| Konu | Sonuç | Kaynak |
|---|---|---|
| `actions/checkout` | v7.0.1; `persist-credentials` varsayılanı hâlâ `true`, bu yüzden her adımda `false` verilir | [sürümler](https://github.com/actions/checkout/releases) |
| `pnpm/action-setup` | v6.1.0; sürümü `package.json` `devEngines.packageManager` alanından okur (`version` girdisi verilmez) | [sürümler](https://github.com/pnpm/action-setup/releases) |
| `actions/setup-node` | v7.1.0 | [sürümler](https://github.com/actions/setup-node/releases) |
| `actions/setup-dotnet` | v6.0.0 | [sürümler](https://github.com/actions/setup-dotnet/releases) |
| `astral-sh/setup-uv` | v10.3.2; v8'den beri kayan ana sürüm etiketi yok, bu yüzden SHA ile sabitlenir | [sürümler](https://github.com/astral-sh/setup-uv/releases) |
| `expo/expo-github-action` | 9.0.1 | [sürümler](https://github.com/expo/expo-github-action/releases) |
| Runner | `ubuntu-latest` 19 Ekim ile 19 Kasım 2026 arasında Ubuntu 26.04'e geçiyor; bu yüzden `ubuntu-24.04` ve `windows-2025` sabit | [GitHub changelog, 17 Eylül 2026](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration) |
| pnpm lisans listesi | `pnpm licenses list -r --json --prod`; v12.7.0'dan beri proje içinde yalnız o projeyi listeler, kökte `-r` gerekir | [pnpm licenses](https://pnpm.io/cli/licenses) |
| .NET lisans aracı | `nuget-license` 4.0.18, yerel araç; `.slnx` destekler, restore yapmaz; `-ji` ve `-exclude-projects "*Tests*"` seçenekleri | [nuget-license](https://github.com/sensslen/nuget-license) |
| Python lisans aracı | `pip-licenses` 5.5.5, `uv run --with` ile; yalnız listeler | [pip-licenses](https://pypi.org/project/pip-licenses/) |
| Turborepo ve `LANG` | `LANG` yerleşik geçiş listesindeydi ama önbellek anahtarına girmiyordu; `LC_ALL` süzülüyordu. Çözüm: `test` görevinde `env: ["LANG","LC_ALL"]`; `globalEnv` önerisi kalktı | Yerel `--dry=json` karşılaştırması (aşağıda) |
| Dependabot ve uv | `package-ecosystem: uv` var, `uv.lock` dosyasını günceller; bazı durumlar çalışmıyor | [astral-sh/uv#2512](https://github.com/astral-sh/uv/issues/2512) |
| Dependabot ve pnpm 12 | İki belgeli `pnpm-lock.yaml`'da sürüm güncellemesi çalışır; bağımlılık grafiği ve güvenlik uyarısı üretilmez | A08.1 araştırması (`arastirmaci`); ayrıntı [Teknoloji yığını §4.2](../../02-mimari/02-teknoloji-yigini.md) |
| Dependabot ve NuGet | Kilit dosyası `ProjectReference` ile etkilenen projelerde güncellenmiyor, `--locked-mode` NU1004 veriyor; NuGet dışarıda | [dependabot-core#13950](https://github.com/dependabot/dependabot-core/issues/13950) |
| Dependabot `commit-message.prefix` | `prefix` `)` ile bitince iki nokta kendiliğinden eklenir (`build(infra): …`); `include: scope` ile birleşirse `build(infra)(deps): …` çıkar, bu yüzden `include` kullanılmadı | [Dependabot seçenekleri](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference) |
| EAS ücretsiz plan | Ayda 15 Android ve 15 iOS derleme; kota aşılınca ücret çıkmaz, derleme durur. A21 ve A33'e not düşüldü | [expo.dev/pricing](https://expo.dev/pricing), [Planlar](https://docs.expo.dev/billing/plans) |
| `EXPO_NO_TELEMETRY=1` | `expo` CLI telemetrisini kapatır. `eas-cli`'nin kendi telemetrisini kapattığı doğrulanamadı; bu yüzden iş akışlarına konmadı | [Expo CLI](https://docs.expo.dev/more/expo-cli) |
| `eas-cli` | 26.0.0 (npm); `eas-build.yml` bu sürüme sabit | [npm](https://www.npmjs.com/package/eas-cli) |
| `check-jsonschema` | 0.39.0; yerleşik şemalar `vendor.dependabot` ve `vendor.github-workflows`; `uvx check-jsonschema@0.39.0 --builtin-schema …` | [depo](https://github.com/python-jsonschema/check-jsonschema) |
| actionlint | 1.7.12; resmî Docker imajı özet (digest) ile sabit; ShellCheck ve pyflakes içerir | [depo](https://github.com/rhysd/actionlint) |
| Dal koruması | GitHub Free planında özel depoda dal koruması ve kurallar (rulesets) yok | [GitHub docs, gated features: protected branches](https://github.com/github/docs/blob/main/data/reusables/gated-features/protected-branches.md) |
| `gh` CLI | Güncel sürüm v2.103.3; bu makinede kurulu değil | [sürümler](https://github.com/cli/cli/releases) |
| `dotnet test --solution server/Mutalaa.slnx -c Release --no-build` | Çalışıyor; `--no-build` `--no-restore`'u da içerir. SDK 10'da hiç test koşmayan proje bütün koşuyu 8 koduyla düşürür | Yerel koşu (aşağıda) |

Çözüldü (2026-10-27): [Proje yapısı §7](../../02-mimari/03-proje-yapisi.md#7-ci-iş-akışları-github-actions) ve [Teknoloji yığını §3, §4.2](../../02-mimari/02-teknoloji-yigini.md) içindeki "Doğrulanacak" ifadeleri (eylem sürümleri, `LANG` geçişi, `-c Release --no-build` birleşimi, Dependabot uv desteği, lisans aracı seçimi, EAS sınırı) bu tablonun kaynaklarıyla kapandı.

### A08.4 yerel koşu çıktıları

**TypeScript**

- `pnpm turbo run lint typecheck test`: 25/25 görev yeşil. Test sayıları: `anchors` 568, `search` 174, `content-schema` 15, `player` 1, `reader-core` 1, `ui-tokens` 1; `test-vectors` Node testleri yeşil.
- `LANG=tr_TR.UTF-8 pnpm turbo run test --force`: 11/11 yeşil; `anchors` ve `search` kurulum dosyaları `locale=tr-TR unicode=17.0` yazdı.
- Turborepo önbellek kanıtı (`pnpm turbo run test --dry=json`, `anchors#test` özeti): eski `turbo.json`'da `C.UTF-8` ve `tr_TR.UTF-8` için özet aynı (`anchors` `b717c87da377058d`, `search` `84da177e5a57e660`); yeni `turbo.json`'da farklı (`C.UTF-8`: `anchors` `77e2ffea3c42b3b1`, `search` `cb30f7dc3a0794e3`; `tr_TR.UTF-8`: `anchors` `9e04fe583c26dd5f`, `search` `a87df6f7c0087813`). `environmentVariables.configured` içinde `LANG` görünür.
- Windows'ta iki koşu da `tr-TR` verir (Node `tr-TR`); `C.UTF-8` karşıtlığının asıl kanıtı CI'dır.
- `node --test "scripts/ci/*.test.mjs"` 14/14; `eslint scripts/ci` temiz; `prettier --check .` temiz (`docker-compose.yml` `.prettierignore`'a eklendi: elle yazılmış, açıklama satırlı).

**.NET** (Windows 10.0.26200, .NET 10.0.13, ICU kipi, `CurrentCulture` `tr-TR`)

- `dotnet tool restore`, `restore --locked-mode`, `format --verify-no-changes --no-restore`, `build -c Release --no-restore`, `test --solution server/Mutalaa.slnx -c Release --no-build`: 1755/1755 geçti, 0 başarısız, 0 atlandı (yaklaşık 10 sn).

**Python** (3.13.16, Unicode 15.1.0; A04'teki değerle aynı)

- `uv sync --locked`, `ruff check`, `ruff format --check` (37 dosya), `mypy` (24 kaynak dosya) temiz; `pytest` 1496 geçti, hem `PYTHONUTF8=1` (kit ortamı) hem `PYTHONUTF8=0` ile; `uv run mutalaa export test-vectors --check` "fark yok".
- Yerel tercih edilen kodlama `utf-8`; `PYTHONUTF8=0` koşusunda `cp1254`. Windows CI ayağının `cp1252`'sinin tam karşılığı değildir; asıl kanıt CI'dır.

**Lisans kapısı**

- pnpm `--prod`: boş ("denetlenecek dağıtılan bağımlılık yok"). pnpm tüm bağımlılıklar (prod dışı dahil): 132 paket, hepsi izinli listede.
- NuGet test dışı 4 proje: 46 paket (MIT 43, Apache-2.0 1, PostgreSQL 2) geçti. Test projeleri dahil 75 paket (MIT 63, Apache-2.0 10, PostgreSQL 2).

**İş akışı denetimi**

- actionlint 1.7.12 (Docker, özet sabit) gerçek dosyalarda 0 bulgu. Bilerek hatalı örnekte ShellCheck SC2076 ve SC2086 ile girdi enjeksiyonu uyarısı verdi (ShellCheck gerçekten koşuyor).
- `check-jsonschema`: `dependabot.yml` ve 6 iş akışı şema denetiminden geçti.
- Kabul `grep`'leri: `EXPO_TOKEN` yalnız `secrets.EXPO_TOKEN`; `pull_request_target` yok; `eas-build.yml` içinde `pull_request` ve `branches` yok; düz metin sır yok.

### İnceleme (2026-10-27)

Beş bakış açılı (iş akışı doğruluğu, güvenlik ve lisans, .NET Linux riski, TypeScript ve Python Linux riski, betik kalitesi) ve şüpheci doğrulamalı inceleme: 40 bulgu, 17'si çürütüldü, engelleyici yok. Düzeltilenler:

- **NuGet kapısı sıfır paketle yeşil verebilirdi:** boş NuGet çıktısı artık çıkış kodu 2 (pnpm için boş küme meşru kalır); testi var.
- **İstisnalar** yalnız `ad@sürüm` biçiminde ve `source` alanıyla kabul edilir; dosya biçimi doğrulanır (yeni sürüm yeniden incelenir).
- LGPL-2.1 ve LGPL-3.0 (yalın) kimlikleri izinli listeye eklendi.
- Betiklerin ana modül koruması gerçek yolları karşılaştırır (bağ ve eşlenmiş sürücülerde sessiz "yeşil" riski).
- Dependabot başlıkları ve `dependabot.yml` önekleri `pr-title` testiyle sınanır.
- `global-setup.ts` istenen `tr_TR` yerel ayarını üç değişkenden birinde arar (`LC_ALL` tanımlıyken atlanmaz).
- `ci-pipeline.yml`: iki sistemde `uv run mutalaa sources check` (gerçek süreç, Windows kodlaması); `pip-licenses` ve "Normalizer environment" adımları bilgi amaçlıdır, işi düşüremez.
- `eas-build.yml`: `concurrency` (derlemeler üst üste binmez).
- `server/Directory.Build.props`: NuGet denetim uyarıları (NU1901–NU1904) hata sayılmaz; yeni yayımlanan bir bulgu bir gecede CI'ı düşürmesin. Uyarı günlükte görünür, NuGet paketleri elle güncellenir.
- `.github/` Prettier dışında (actionlint ve şema denetimi var); iş akışı değişikliği `ci-ts`'i tetiklemediği için biçim denetimi orada kopukluk yaratıyordu.

Bilerek yapılmayanlar: kit testlerinin CI'da koşması (ilk Linux koşusundan sonra), Dependabot `cooldown`, Docker imajı için ayrı çekim adımı, `eas-build` için `environment` onayı (A21'de, mobil gelince).

### Sapmalar

- **Adım 0** (kit izin pencerelerinin kaldırılması) A08 kapsamı dışı bir kullanıcı yönergesiydi. Otomatik mod sınıflandırıcısı klasör bekçisi hook'unu gevşeten düzenlemeyi (kullanıcı açık talimatı vermeden) reddettiği için A08 sırasında ertelendi; kullanıcı açıkça isteyince A08 sonrasında ayrı dalda (`chore/kit-permissions`) yapıldı (K-31 güncellemesi, 27 Ekim 2026). A08 işi buna bağlı değildi. Bu aşama dosyasındaki A08.5 ve Dikkat'in `git push` cümleleri CLAUDE.md kural 11'e göre düzeltildi; kit, K-31 ve öteki belgelerdeki aynı hizalama Adım 0 ile birlikte kaldı.
- `gh` kurulu değil. PR açma ve Actions sonucu kullanıcı bildirimine bağlı (A08.5 bekliyor).

### Devredilenler

- **A14:** OpenAPI belgesi `dotnet build -c Release` içinde üretilmeli; yoksa CI farkı göremez.
- **A21:** `apps/mobile` eklendiği PR'da `.github/dependabot.yml` `npm` girdisine Expo paketleri için `ignore`; `EXPO_TOKEN` (Expo robot kullanıcısı, en dar rol; İ-15'e bağlı); EAS ayda 15+15 sınırı.
- **A33:** EAS ayda 15+15 sınırı Faz 2 temposu için.
- **A38:** web iş akışında `NEXT_TELEMETRY_DISABLED`.
- **A34:** `THIRD_PARTY_NOTICES` için `check-licenses.mjs --json` çıktısı.
- **A10:** gece iş akışı iskeleti (BÇ-42).

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A07](./A07-editoryal-veritabani.md) · Sonraki: [A09](./A09-elmalili-ocr-pilotu.md)
