# A02 · Tek depo iskeleti (pnpm + Turborepo, .NET çözümü, uv)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-09](../../00-ozet/02-karar-defteri.md#k-09--mobil-teknoloji) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A00](./A00-ortam-ve-depo.md) · **İnsan adımı:** yok
> **Ajanlar:** `web-gelistirici` · `sunucu-gelistirici` · `hat-gelistirici` · `arastirmaci` · `inceleyici` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A02`

## Amaç
Üç dilin tek depoda kurulduğu, derlendiği ve test edildiği boş iskelet hazırlanır: pnpm + Turborepo çalışma alanı, `server/` altında .NET çözümü, `pipeline/` altında uv projesi. Sonraki aşamalar bu iskelete kod ekler. Bu aşama içerik ya da iş mantığı yazmaz; her parça yer tutucu testle yeşil olur.

## Okunacak belgeler
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): tamamı (§1 dizin ağacı, §2 bağımlılık kuralları, §4 araçlar, §5 lint ve biçim, §6 Git kuralları, §8 açık sorular)
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §4 sürüm sabitleme ve yükseltme; §2.2–§2.4 (paket adları)
- [Backend API](../../02-mimari/05-backend-api.md): §2 çözüm yapısı ve `Directory.Build.props`
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §2 paket yapısı, §3 kurulum ve yapılandırma
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §10.1, §10.2, §10.4 (Windows ve yerel ayar tuzakları)

## Kapsam
**Yapılır**
- Kök araç dosyaları: `package.json`, `pnpm-workspace.yaml`, `.npmrc`, `turbo.json`, `tsconfig.base.json`, `eslint.config.mjs`, `.prettierrc.json`, `.nvmrc`, `global.json`, `.config/dotnet-tools.json`.
- Altı boş TypeScript paketi (`packages/anchors`, `content-schema`, `search`, `reader-core`, `player`, `ui-tokens`) ve `shared/test-vectors` çalışma alanı paketi.
- `server/` çözümü: dört proje, üç test projesi, `Directory.Build.props`, `Directory.Packages.props`, kilit dosyaları.
- `pipeline/` uv projesi: `pyproject.toml`, `uv.lock`, `.python-version`, `mutalaa.toml`, `src/mutalaa_pipeline/`, `sources/licenses/`, `prompts/`, `tests/`.
- `.gitignore` dosyasına eksik derleme çıktısı satırları (yalnız ekleme).

**Yapılmaz**
- `apps/mobile` (A21), `apps/editor` (A15), `apps/web` (A38).
- `docker-compose.yml`, `.env.example`, `infra/`, `scripts/` (A03). `.github/workflows/` (A08).
- Çapa, normalizasyon, kaynak kayıtları ve enum'lar (A04, A05, A06); EF Core ve göçler (A07).
- `.gitattributes`, `.editorconfig` ve `.gitignore` dosyalarını baştan yazmak: A00'da açıldılar, burada yalnız eksik satır eklenir.

## Adımlar
### A02.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar:
  - pnpm izole kurulumu Expo SDK 57'de (kararlıysa 58'de) Metro ile sorunsuz mu, yoksa `node-linker=hoisted` mı gerekir (Proje yapısı §4.1 ve §8 madde 1; Yerel geliştirme §11 madde 2). Kesin destek kanıtı yoksa `hoisted` kalır; kesin cevap A21'de yeniden sınanır.
  - `Mutalaa.slnx` biçiminin `dotnet format`'ta ve kullanıcının IDE'sinde desteği; `dotnet new sln` ile `.slnx` üretme yolu (Proje yapısı §4.2 ve §8 madde 2).
  - `xunit.v3` test projesi şablonu ve paket adları (Teknoloji yığını §2.2).
- Kurulu araçlar okunur: `node --version` (24), `pnpm --version`, `dotnet --list-sdks` (10.0.1xx), `uv --version`. Eksik araç varsa İ-01'e dönülür ve kullanıcıya söylenir.
- **Bitti sayılır:** üç soru kaynaklı cevaplandı ve aşama kaydına yazıldı; araç sürümleri kayıtlı.

### A02.2 · pnpm çalışma alanı ve Turborepo (`web-gelistirici`)
- Kök `package.json` Proje yapısı §4.1'deki gibi (`name`, `private`, `scripts`); `packageManager` alanına kurulu pnpm sürümü yazılır.
- `pnpm-workspace.yaml` (`apps/*`, `packages/*`, `shared/test-vectors`), `.npmrc` (A02.1 sonucuna göre), `turbo.json` (§4.1'deki `build`, `typecheck`, `lint`, `test`, `dev` görevleri), `.nvmrc` (`24`).
- Kök geliştirme bağımlılıkları `pnpm add -Dw` ile: `turbo`, `typescript`, `eslint`, `typescript-eslint`, `eslint-config-prettier`, `prettier`, `vitest`. Sürümler kurulum günü kilit dosyasına yazılır; elle sürüm yazılmaz (Teknoloji yığını §4.1).
- `eslint.config.mjs` Proje yapısı §5'teki özetle (yerel ayar kuralları, paketlerde `react-native`, `expo-*`, `next` yasağı). Ek olarak `packages/anchors` ve `packages/search` dosyalarında `@mutalaa/*` içe aktarımı yasaklanır (§2 kural 3; öneri).
- `.prettierrc.json`: `{ "printWidth": 100, "singleQuote": true, "trailingComma": "all", "endOfLine": "lf" }` (§5). `tsconfig.base.json`: `strict` açık ortak ayarlar (içerik dokümanda yok; öneri).
- **Bitti sayılır:** `pnpm install` hatasız; `pnpm-lock.yaml` oluştu.

### A02.3 · Paylaşılan paketler ve test vektörü paketi (`web-gelistirici`)
- Her paket: ad `@mutalaa/<klasör>`, `src/index.ts`, taban ayarı genişleten `tsconfig.json`, `build`, `typecheck`, `lint`, `test` betikleri, `test/` altında bir yer tutucu Vitest testi.
- İç bağımlılıklar §2'deki çizgeyle `workspace:*`: `content-schema → anchors`; `reader-core → anchors, search, content-schema`; `player → anchors`. `anchors`, `search` ve `ui-tokens` iç pakete bağlanmaz. Döngü yok.
- `shared/test-vectors/package.json` (`@mutalaa/test-vectors`): `build` betiği bir JSONL biçim denetleyicisi çalıştırır (öneri: `scripts/check.mjs`, isteğe bağlı klasör argümanıyla). Denetim: UTF-8, BOM yok, yalnız LF, son satır sonu var, her satır bir JSON nesnesi, dosya içinde benzersiz `id`. Vektör yoksa başarıyla biter. Klasörleri A04 ve A05 doldurur: `anchors/`, `offsets/`, `normalize/`, `content-hash/`, `fts-query/`.
- `anchors` ve `search` paketleri `@mutalaa/test-vectors` paketine geliştirme bağımlılığıyla bağlanır; vektör değişince Turborepo test önbelleğini geçersiz sayar (§4.1).
- Bozuk deneme dosyası Write aracıyla yazılmaz (biçim hook'u reddeder); `printf` ile ya da denetleyicinin kendi testinde `.tmp/` altında üretilir.
- **Bitti sayılır:** `pnpm turbo run build lint typecheck test` yedi çalışma alanı paketinde yeşil; denetleyici `.tmp/` altındaki temiz deneme dosyasını geçiriyor, yalnız BOM'lu ve yalnız CRLF'li deneme dosyalarını ayrı ayrı reddediyor.

### A02.4 · .NET çözümü (`sunucu-gelistirici`)
- Kökte `global.json` (`10.0.100`, `rollForward: latestFeature`). `dotnet new tool-manifest` ve `dotnet tool install dotnet-ef` ile `.config/dotnet-tools.json` (Proje yapısı §4.2); araç sürümü bildirime yazılır.
- `server/Mutalaa.slnx` ve projeler: `Mutalaa.Domain` (sınıf kitaplığı), `Mutalaa.Infrastructure` (sınıf kitaplığı), `Mutalaa.Api` (boş ASP.NET Core), `Mutalaa.Publisher` (konsol). Test projeleri: `server/tests/Mutalaa.Domain.Tests`, `Mutalaa.Api.Tests`, `Mutalaa.Publisher.Tests` (adlar öneri; §1 "Domain, Api ve Publisher test projeleri").
- Başvurular §2'deki gibi: `Api → Infrastructure → Domain`, `Publisher → Infrastructure`. `Api` ile `Publisher` birbirine bağlanmaz; `Domain` hiçbir projeye ve altyapı paketine bağlanmaz.
- `server/Directory.Build.props`: `TargetFramework=net10.0`, `Nullable=enable`, `TreatWarningsAsErrors=true`, `RestorePackagesWithLockFile=true`; `InvariantGlobalization` açılmaz (Backend API §2). `server/Directory.Packages.props` merkezi sürüm yönetimi; paket sürümü yalnız burada.
- Yer tutucu test bir mimari testidir: `Mutalaa.Domain` derlemesinin başvuruları arasında EF Core, Npgsql, AWS ve `Mutalaa.*` yoktur (Proje yapısı §2 son paragraf).
- `packages.lock.json` dosyaları üretilir ve depoya girer. `dotnet format --verify-no-changes` `.slnx` ile denenir; çalışmazsa `Mutalaa.sln`'e geçiş `/karar` ile yazılır (§4.2).
- **Bitti sayılır:** `dotnet build` ve `dotnet test` yeşil; `dotnet restore --locked-mode` hatasız.

### A02.5 · Python içerik hattı (`hat-gelistirici`)
- `pipeline/pyproject.toml` İçerik hattı §3'teki gibi: ad, `requires-python = ">=3.13,<3.14"`, bağımlılıklar, `arapca`, `turkce`, `gomme` grupları, `mutalaa = "mutalaa_pipeline.cli:app"`, hatchling. Geliştirme araçları: `uv add --dev pytest ruff mypy`. Ruff ayarı Proje yapısı §5'teki gibi (`py313`, `line-length = 100`, kural seçimi, `line-ending = "lf"`).
- `uv python pin 3.13`, `uv lock`, `uv sync`. Python 3.13 yoksa `uv python install 3.13` çalışır (kullanıcı onayı ister).
- `pipeline/mutalaa.toml` İçerik hattı §3'teki gibi; `[llm] model` yer tutucu kalır (model kimliği Doğrulanacak; ilk yapay zekâ işinde doğrulanır).
- `src/mutalaa_pipeline/cli.py` (Typer uygulaması `app`) ve alt paketler `ingest`, `normalize`, `anchor`, `enrich`, `qa`, `export` (`__init__.py`). Yardımcı modüller (`config.py`, `runctx.py` …) onları kullanan aşamada eklenir. `sources/licenses/` ve `prompts/` klasörleri `.gitkeep` ile.
- Yer tutucu test: `pipeline/tests/test_cli.py`, `mutalaa --help` çıkış kodu 0.
- **Bitti sayılır:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` ve `uv run mypy src` yeşil; `uv run mutalaa --help` çalışıyor.

### A02.6 · Son denetim
- `.gitignore` dosyasına eksikse eklenir: `node_modules/`, `dist/`, `.turbo/`, `*.tsbuildinfo`, `bin/`, `obj/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `coverage/`. A00'ın satırlarına dokunulmaz; yalnız kökteki veri satırı eski `data/` biçimindeyse `/data/` yapılır (yoksa `shared/data/` yok sayılır).
- `inceleyici`: bağımlılık kuralları (§2), paket adları, kilit dosyaları, gizli değer yokluğu.
- **Bitti sayılır:** `git status --porcelain` derleme çıktısı göstermiyor; Doğrulama bloğu baştan sona yeşil.

## Kabul ölçütleri
- [ ] `pnpm install --frozen-lockfile` hatasız; `pnpm -r ls --depth -1` çıktısında kök dışında yedi `@mutalaa/*` paketi var.
- [ ] `pnpm lint`, `pnpm typecheck`, `pnpm test` ve `pnpm turbo run build` yeşil.
- [ ] `@mutalaa/test-vectors` denetleyicisi temiz dosyayı geçiriyor, BOM'lu ya da CRLF'li dosyada sıfırdan farklı kodla çıkıyor.
- [ ] `dotnet restore server/Mutalaa.slnx --locked-mode`, `dotnet build`, `dotnet test` yeşil; mimari testi geçiyor.
- [ ] `dotnet format server/Mutalaa.slnx --verify-no-changes` çalışıyor ya da `.sln` kararı karar defterinde.
- [ ] `cd pipeline && uv sync --locked` hatasız; `pytest`, `ruff check`, `ruff format --check`, `mypy src` yeşil; `uv run mutalaa --help` 0 ile çıkıyor.
- [ ] `.npmrc` ve `.slnx` sorularının cevabı kaynak bağlantısıyla aşama kaydında.
- [ ] `git status --porcelain` içinde `node_modules`, `bin`, `obj`, `.venv`, `dist` yok.

## Doğrulama
```bash
pnpm install --frozen-lockfile
pnpm -r ls --depth -1
pnpm lint && pnpm typecheck && pnpm test && pnpm turbo run build
pnpm --filter @mutalaa/test-vectors build
mkdir -p .tmp/vektor-deneme/temiz .tmp/vektor-deneme/bom .tmp/vektor-deneme/crlf
printf '{"id":"a","input":"x","expected":"x"}\n' > .tmp/vektor-deneme/temiz/v.jsonl
printf '\xef\xbb\xbf{"id":"a","input":"x","expected":"x"}\n' > .tmp/vektor-deneme/bom/v.jsonl
printf '{"id":"a","input":"x","expected":"x"}\r\n' > .tmp/vektor-deneme/crlf/v.jsonl
for d in temiz bom crlf; do node shared/test-vectors/scripts/check.mjs ".tmp/vektor-deneme/$d"; echo "$d çıkış: $?"; done   # temiz 0; bom ve crlf 0 dışı
dotnet tool restore
dotnet restore server/Mutalaa.slnx --locked-mode
dotnet format server/Mutalaa.slnx --verify-no-changes --no-restore
dotnet build server/Mutalaa.slnx --no-restore
dotnet test server/Mutalaa.slnx --no-build
(cd pipeline && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest && uv run mutalaa --help)
git status --porcelain
```

## Dikkat
- Sürüm uydurulmaz. Dokümanın verdiği sabitler (`10.0.100`, Node 24, Python 3.13) dışındaki sürümler kurulum günü kilit dosyasına yazılır.
- `.npmrc` Metro'yu etkiler. Mobil (A21) gelene kadar `hoisted` güvenli varsayımdır; değişiklik `/karar` ister.
- Paketlerde `react-native`, `expo-*`, `next` ve DOM API'si kullanılmaz; `anchors` ve `search` yapraktır (§2). Ayrıntı: `.claude/rules/` altındaki paylaşılan paket kuralı.
- `Mutalaa.Domain` EF Core, Npgsql ve AWS paketlerine bağlanmaz; NuGet sürümü yalnız `Directory.Packages.props`'tadır. CA1304…CA1311 `.editorconfig`'te hata düzeyindedir; kültüre duyarlı çağrı derlemeyi durdurur.
- Python: dosyalar `encoding="utf-8"` ile açılır. Claude Code oturumunda `PYTHONUTF8=1` ayarlıdır; CI'da bilerek verilmez (A08).
- Windows: proje yolu boşluk, Türkçe karakter ve OneDrive içerir. Komutlarda göreli yol kullanılır. `node_modules`, `bin/obj` ve `.venv` proje klasöründe oluşur; A00'daki OneDrive kararına uyulur. Ayrıntı: `windows-sorun`.
- Satır içi kod (`node -e`, `python -c`) ve tek başına `node <betik>` onay ister; denetim betikleri paket içinde dosya olarak yazılır ve proje dışı yol kullanmaz.
- Commit: Conventional Commits, İngilizce; ör. `build(infra): scaffold pnpm, dotnet and uv workspaces`.

## İnsan adımları
- Yok. Araçlardan biri eksikse İ-01'e dönülür ([İnsan adımları](../06-insan-adimlari.md)).

## Çıktılar
- Kök: `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `.npmrc`, `turbo.json`, `tsconfig.base.json`, `eslint.config.mjs`, `.prettierrc.json`, `.nvmrc`, `global.json`, `.config/dotnet-tools.json`, `.gitignore` eki
- `packages/{anchors,content-schema,search,reader-core,player,ui-tokens}/` ve `shared/test-vectors/` (`package.json`, biçim denetleyicisi)
- `server/Mutalaa.slnx`, `server/Directory.Build.props`, `server/Directory.Packages.props`, `server/Mutalaa.{Domain,Infrastructure,Api,Publisher}/`, `server/tests/Mutalaa.{Domain,Api,Publisher}.Tests/`, `packages.lock.json` dosyaları
- `pipeline/pyproject.toml`, `uv.lock`, `.python-version`, `mutalaa.toml`, `src/mutalaa_pipeline/`, `sources/licenses/`, `prompts/`, `tests/test_cli.py`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A02-tek-depo-iskeleti.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A01](./A01-yazisma-paketi.md) · Sonraki: [A03](./A03-yerel-altyapi.md)
