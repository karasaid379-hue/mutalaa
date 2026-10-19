# A00 · Ortam, klasör ve depo hazırlığı

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-20](../../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-31](../../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)
> **Faz:** 0 · Hazırlık · **Önkoşul:** yok · **İnsan adımı:** İ-01
> **Ajanlar:** `arastirmaci` · `belge-bekcisi` · `inceleyici` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 1
> **Başlat:** `/asama A00`

## Amaç

Claude Code ile geliştirmeye başlamadan önce bilgisayarın, proje klasörünün ve kitin hazır olduğunu kanıtlamak. Bu aşama sonunda araçların sürümleri bilinir, proje yolu için karar verilmiştir, git deposu açılmıştır ve kitin hook'ları, ayarları ve bağlantıları doğrulanmıştır.

## Okunacak belgeler

- [Kurulum](../01-kurulum.md): tamamı
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §1 Ön koşullar, §2 Windows hazırlığı, §10 Sık karşılaşılan sorunlar
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 Dizin ağacı, §5 Lint ve biçim (`.editorconfig`, `.gitattributes`)

## Kapsam

**Yapılır**
- Araç sürümlerinin denetimi ve eksiklerin listesi.
- Proje yolunun ölçümü ve yol kararı.
- Git deposu, kök `.gitignore`, `.gitattributes`, `.editorconfig`; ilk commit.
- Kitin doğrulanması: hook testleri, ayar doğrulaması, bağlantı denetimi.

**Yapılmaz**
- Tek depo iskeleti, paket yöneticisi ayarları, `.nvmrc`, `global.json`: [A02](./A02-tek-depo-iskeleti.md).
- Docker Compose ve `.env.example`: [A03](./A03-yerel-altyapi.md).
- Sistem genelindeki kurulumlar ve ayarlar (kayıt defteri, güvenlik duvarı, küresel git ayarı): kullanıcı yapar (İ-01).

## Adımlar

### A00.1 · Araç sürümleri

- Şu komutları çalıştır ve sonuçları tabloya dök (komut yoksa "yok" yaz):
  `git --version` · `node --version` · `pnpm --version` · `dotnet --list-sdks` · `uv --version` · `docker version --format '{{.Server.Version}}'` · `docker compose version` · `eas --version` · `adb --version`. Claude Code sürümünü kullanıcı `/status` çıktısından okur ve söyler (2.1.295 ya da üstü gerekir; Claude Code oturumunun içinden `claude` komutu çalıştırılmaz). Docker sunucu sürümü dönüyorsa Docker Desktop ve WSL2 arka ucu çalışıyordur; WSL durumunu kullanıcı PowerShell'de `wsl --status` ile görür.
- Gereken sürümlerle karşılaştır ([Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) §1): Node 24 LTS, .NET SDK 10.0, Docker Compose v2. Expo SDK sürümünün gerektirdiği Node aralığını `arastirmaci` ile doğrula; Node'un kurulu ana sürümü 24 değilse kullanıcıya iki seçenek sun (24 kurmak ya da belgeleri yeni LTS'ye göre güncellemek için `/karar`).
- Eksik araç için kullanıcıya [Kurulum](../01-kurulum.md) §2'deki komutu ver; kurulumu kendin yapma.
- **Bitti sayılır:** sürüm tablosu rapordadır ve zorunlu araçların (Git, Node, pnpm, .NET, uv) hepsi kuruludur. Docker, EAS CLI ve Android araçları eksikse not düşülür; bunlar A03 ve A21'de gerekir.

### A00.2 · Kitin doğrulanması

```bash
pwd -W                                   # proje kökü olmalı (CLAUDE.md'nin klasörü)
echo "PowerShell aracı: ${CLAUDE_CODE_USE_POWERSHELL_TOOL:-ayarlanmamış}"   # 0 beklenir
node --test ".claude/hooks/test/*.test.mjs"
node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs CLAUDE.md .claude
```

- Ayar doğrulamasını kullanıcı yapar: oturumda `/doctor` ya da ayrı bir terminalde `claude doctor` çalıştırır ve "Invalid settings" bölümü olup olmadığını söyler. Claude Code oturumunun içinden `claude doctor` çalıştırılmaz (iç içe oturum, terminal yok).
- Çalışma dizini proje kökü değilse dur: kullanıcı Claude Code'u kökte yeniden başlatır ([Kurulum](../01-kurulum.md) §5). Proje ayarları yüklendiyse `PowerShell aracı: 0` yazar.
- Hook testlerinin hepsi geçmeli. Kullanıcının `/doctor` sonucunda "Invalid settings" bölümü olmamalı.
- Kullanıcıdan `/hooks`, `/agents`, `/skills` ve `/status` komutlarını çalıştırmasını ve sonuçları doğrulamasını iste: 3 hook kaydı, 11 ajan, 16 beceri, "Setting sources" içinde proje ayarları ([Kurulum](../01-kurulum.md) §5).
- Klasör bekçisini canlı dene; deneme hedefi bilgisayarda olmayan bir sürücüdür, böylece onay verilse bile hiçbir yere yazılamaz. Kullanıcıya bilgisayarda `Z:` sürücüsü olup olmadığını sor; varsa kullanılmayan başka bir harf seç. (1) `Write` ile `Z:/mutalaa-bekci.txt` reddedilmeli; (2) `echo deneme > /z/mutalaa-bekci.txt` komutu onay sormalı ve kullanıcı reddetmeli. Retleri rapora koy. Ayrıntı ve sınırlar: [Kurulum](../01-kurulum.md) §7.
- **Bitti sayılır:** oturum proje kökünde; komutlar başarılı; kullanıcı sayıları ve ayar kaynağını doğruladı; iki dışarı yazma denemesi de engellendi.

### A00.3 · Proje yolu ve OneDrive kararı

- Yolu ölç ve raporla (`pwd -W` ve `df -h .`, Git Bash): tam yol, karakter sayısı, boşluk var mı, ASCII dışı karakter var mı, OneDrive altında mı (yolda `OneDrive` parçası), sürücüdeki boş alan.
- Kullanıcıya seçenekleri sun ([Kurulum](../01-kurulum.md) §4):
  1. **Yerinde kal.** Android geliştirme derlemesi EAS bulutunda; OneDrive yoğun işlerde (`pnpm install`, derleme, OCR) duraklatılır; klasör "Her zaman bu cihazda tut". `data/` büyüdükçe kota izlenir.
  2. **Klasörü taşı.** Kullanıcı klasörün tamamını OneDrive dışına kısa bir yola (ör. `C:\dev\mutalaa`) taşır ve Claude Code'u orada yeniden açar. Kit göreli yollarla çalıştığı için bozulmaz; Claude Code'un oturum geçmişi eski yolda kalır.
  3. **Kısa sürücü harfi.** Yerel Android derlemesi gerekirse `subst M: "<proje klasörü>"` ile `M:\` üzerinden açmak. Gradle'ın gerçek yolu çözüp çözmediği Doğrulanacak (`arastirmaci`); denenmeden varsayılan yapılmaz.
- Kararı ilerleme dosyasının not sütununa "Yol kararı: …" diye yaz. Seçenek 2 seçilirse aşamayı burada durdur; taşımadan sonra yeni oturumda `/asama A00` ile A00.4'ten devam edilir.
- **Bitti sayılır:** karar ilerleme dosyasında yazılıdır.

### A00.4 · Git deposu ve kök dosyalar

- `git rev-parse --is-inside-work-tree` ile depo var mı bak. Yoksa `git init -b main`.
- Yerel depo ayarı: `git config core.autocrlf false` (yalnız bu depo; küresel ayar kullanıcının işidir).
- `.gitattributes` ve `.editorconfig` dosyalarını [Proje yapısı](../../02-mimari/03-proje-yapisi.md) §5'teki içerikle yaz.
- `.gitignore` en az şunları içerir (A02 ve sonraki aşamalar ekleme yapar):
  ```gitignore
  # Kit ve Claude Code
  .claude/settings.local.json
  CLAUDE.local.md
  .tmp/
  # Gizli değerler
  .env
  .env.*
  !.env.example
  **/.env.local
  # Veri (git dışı; docs/02-mimari/03 §1.1). Kökte bağlanır: shared/data/ izlenir.
  /data/
  # Bağımlılıklar ve çıktılar
  node_modules/
  dist/
  bin/
  obj/
  .expo/
  .turbo/
  .venv/
  __pycache__/
  ```
- `git status` ile girecek dosyaları göster; `docs/`, `CLAUDE.md`, `.claude/` (yerel ayar dosyası hariç), `.gitattributes`, `.editorconfig`, `.gitignore`.
- İlk commit: `chore(kit): add Claude Code kit and project docs`. Push yok; uzak depo İ-16 ile gelir.
- **Bitti sayılır:** `git log --oneline` ilk commit'i gösterir; `git status --short` temizdir; `git check-ignore .claude/settings.local.json .tmp/x data/x .env` dört yolu da yok sayıldı olarak gösterir; `shared/data/x` yok sayılmaz.

### A00.5 · Kullanıcı ortamı denetim listesi

- Kullanıcının bir kez yapacağı Windows hazırlığını ([Kurulum](../01-kurulum.md) §3) listele ve hangilerinin yapıldığını sor. Claude Code bunları çalıştırmaz (sistem geneli değişiklik).
- Git Bash'ten denetlenebilenleri denetle: `git config --get core.longpaths` ve `git config --get core.autocrlf` (geçerli değerler; küresel ayarı kullanıcı değiştirir); kullanıcı ortamında `PYTHONUTF8` (`echo "$PYTHONUTF8"`; kitin `env` ayarı Claude Code için zaten 1 verir).
- **Bitti sayılır:** liste rapordadır; eksikler İ-01 notuna yazılmıştır.

## Kabul ölçütleri

- [ ] Araç sürüm tablosu raporda; Git, Node, pnpm, .NET 10 SDK ve uv kurulu.
- [ ] `node --test ".claude/hooks/test/*.test.mjs"` bütün testleri geçiyor.
- [ ] Bağlantı denetimi "kırık bağlantı yok" diyor.
- [ ] Kullanıcının `/doctor` (ya da ayrı terminalde `claude doctor`) çıktısında geçersiz ayar yok.
- [ ] Proje dışına yazma denemesi `klasor-bekcisi` tarafından reddedildi.
- [ ] Yol kararı ilerleme dosyasında yazılı.
- [ ] Git deposu açık; ilk commit var; `.gitignore` kit, gizli değer ve veri yollarını yok sayıyor.
- [ ] İlerleme dosyasında A00 `tamam`, sıradaki aşama A01.

## Doğrulama

```bash
node --test ".claude/hooks/test/*.test.mjs"
node .claude/skills/belge-esitle/baglanti-denetimi.mjs docs CLAUDE.md .claude
git log --oneline -1
git status --short
git check-ignore -v .claude/settings.local.json .tmp/x data/x .env
git check-ignore -q shared/data/x && echo "HATA: shared/data yok sayılıyor" || echo "shared/data izleniyor"
```

## Dikkat

- Sistem geneli değişiklikleri (winget kurulumları, kayıt defteri, güvenlik duvarı, `git config --global`) kullanıcı yapar; Claude Code komutu verir ve sonucu denetler.
- `.env` dosyalarını okumaya çalışma; izin kuralı engeller ve bu doğru davranıştır.
- `/doctor` çıktısındaki kurulum uyarıları (ör. otomatik güncelleme) aşamanın konusu değildir; rapora not düşülür.
- Bu aşamada hiçbir içerik (Kur'an metni, meal) indirilmez.

## İnsan adımları

- İ-01 · Araç kurulumu ve Windows hazırlığı: A00.1 ve A00.5'te eksikler listelenir; kurulum sizdedir.
- Yol kararı (A00.3) sizin kararınızdır; taşıma seçilirse taşımayı siz yaparsınız.

## Çıktılar

- `.gitignore`, `.gitattributes`, `.editorconfig`
- Git deposu ve ilk commit
- `docs/10-claude-code/05-ilerleme.md` (A00 satırı, yol kararı, durum bloğu)
- `docs/10-claude-code/06-insan-adimlari.md` (İ-01 durumu)

## Elle başlatma istemi

```text
docs/10-claude-code/asamalar/A00-ortam-ve-depo.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar

- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [Kurulum](../01-kurulum.md) · Sonraki: [A01](./A01-yazisma-paketi.md)
