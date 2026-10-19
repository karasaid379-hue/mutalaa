# Kurulum (Windows)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-20](../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)

Bu dosya Claude Code'u ve projenin araçlarını Windows'a kurmayı, Claude Code'u proje klasöründe ilk kez açmayı ve kitin çalıştığını doğrulamayı anlatır. Buradaki kurulumlar sistem genelini değiştirdiği için Claude Code değil, siz yaparsınız (insan adımı İ-01). Kurulumdan sonra Claude Code, A00 aşamasında sürümleri denetler.

## 1. Gereksinimler

- Windows 10 1809 ya da üstü, ya da Windows 11. Docker Desktop için BIOS'ta sanallaştırma açık olmalı ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §1).
- Claude Code için Pro, Max, Team, Enterprise ya da Console hesabı. Ücretsiz claude.ai planı Claude Code içermez ([Claude Code kurulumu](https://code.claude.com/docs/en/setup)).
- İnternet bağlantısı.

## 2. Araçlar (İ-01)

Aşağıdaki komutlar PowerShell içindir. `winget` paket kimlikleri yazım günü bilinen kimliklerdir; bir kimlik bulunamazsa aracın resmî sayfasından yükleyici indirilir.

| Araç | Gereken sürüm | Kurulum | Doğrulama |
|---|---|---|---|
| Claude Code | 2.1.295 ya da üstü (kitin klasör bekçisi `onFailure` alanını kullanır) | `irm https://claude.ai/install.ps1 \| iex` (yerel kurulum, kendiliğinden güncellenir) ya da `winget install Anthropic.ClaudeCode` | `claude --version` |
| Git for Windows | güncel | `winget install --id Git.Git -e` | `git --version` |
| Node.js | 24 LTS | `winget install --id OpenJS.NodeJS.LTS -e` ya da nodejs.org'dan 24 LTS yükleyicisi | `node --version` (v24 beklenir; başka ana sürüm gelirse A00'da karar verilir) |
| pnpm | kuruluma göre belirlenir; `packageManager` sabitlemesi A02'dedir ([BÇ-28](./07-belge-celiskileri.md)) | `npm install -g pnpm` (pnpm'in güncel kurulum belgesi Windows için npm yolunu önerir: [pnpm kurulumu](https://pnpm.io/installation)). Node 24'te Corepack ile de olur: `corepack enable` (Corepack Node 25.0.0'dan itibaren dağıtılmaz; Program Files altındaki MSI kurulumunda yönetici terminali ya da `--install-directory` gerekebilir, açık "yönetici gerekir" cümlesi Doğrulanamadı) | `pnpm --version` |
| .NET SDK | 10.0 | `winget install --id Microsoft.DotNet.SDK.10 -e` | `dotnet --list-sdks` |
| uv | güncel | `winget install --id astral-sh.uv -e` | `uv --version` |
| WSL2 | güncel | Yönetici terminalde `wsl --install`, sonra `wsl --update` | `wsl --status` |
| Docker Desktop | güncel, Compose v2 | `winget install --id Docker.DockerDesktop -e` | `docker version` · `docker compose version` |
| EAS CLI | güncel | `npm install -g eas-cli` | `eas --version` |
| Android Studio (isteğe bağlı) | güncel | `winget install --id Google.AndroidStudio -e` | emülatör ve `adb --version` |
| PowerShell 7 ve Windows Terminal (önerilir) | güncel | `winget install --id Microsoft.PowerShell -e` · `winget install --id Microsoft.WindowsTerminal -e` | `pwsh --version` |

Notlar:
- **Git for Windows önemlidir.** Claude Code komutları Git Bash ile çalıştırır; aşama dosyalarındaki komutlar bash sözdizimindedir. Git kurulu değilse Claude Code PowerShell'e düşer.
- **Python'u ayrıca kurmayın.** uv, Python 3.13'ü proje için kendisi kurar (A02'de `uv python install 3.13`, onayınızla).
- **Hesaplar** (Expo, Apple Developer, Google Play, GitHub, Sentry) ilgili aşamada gerekir: [İnsan adımları](./06-insan-adimlari.md).
- **Maestro CLI** şimdi kurulmaz; uçtan uca testlerde (A33) gerekir. Windows'ta kurulum yolu o aşamada resmî kaynaktan doğrulanır ve size sorulur.

## 3. Windows hazırlığı (bir kez, yönetici PowerShell)

Kaynak: [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §2.

```powershell
# Uzun yol desteği
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
git config --global core.longpaths true
git config --global core.autocrlf false        # satır sonlarını .gitattributes yönetir

# Telefonun bağlanacağı Wi-Fi ağı "Özel" olmalı
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private

# Metro ve S3 deposu yalnız özel ağda açılır
New-NetFirewallRule -DisplayName "Mutalaa Metro 8081" -Direction Inbound -Protocol TCP -LocalPort 8081 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Mutalaa S3 8333" -Direction Inbound -Protocol TCP -LocalPort 8333 -Action Allow -Profile Private

# Python dosyaları UTF-8 açılsın (Türkçe Windows'ta varsayılan cp1254)
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

Kit, Claude Code'un kendi komutları için `PYTHONUTF8=1` değerini zaten verir (`.claude/settings.json` › `env`). Yukarıdaki satır sizin elle açtığınız terminaller içindir.

## 4. Proje klasörü ve OneDrive

Proje klasörü `C:\Users\MEHMET SAİD\OneDrive\Masaüstü\mutalaa-kit` yolundadır. Bu yolun üç özelliği sorun çıkarabilir:

| Özellik | Etkisi | Kitteki önlem |
|---|---|---|
| Boşluk ve Türkçe karakter (`MEHMET SAİD`, `Masaüstü`) | Android Gradle'ın yerel derlemesi bu yollarda kırılabilir | Geliştirme derlemesi varsayılan olarak EAS bulutunda yapılır; hook'lar kabuk kullanmadan, doğrudan `node` ile çalışır |
| OneDrive eşitlemesi | `node_modules`, derleme çıktıları ve `data/` binlerce dosya ve gigabaytlarca veri demektir; eşitleme dosyaları kilitleyebilir (EPERM) ve kotayı doldurabilir | A00'da yol kararı verilir |
| Uzun yol | Derin `node_modules` yolları sınırı aşabilir | `LongPathsEnabled` ve `core.longpaths` (bölüm 3) |

A00 aşamasında Claude Code yolu ölçer ve size üç seçenek sunar: (1) klasör yerinde kalır, OneDrive eşitlemesi yoğun işlerde duraklatılır ve klasör "Her zaman bu cihazda tut" yapılır; (2) klasörün tamamını OneDrive dışında kısa bir yola (ör. `C:\dev\mutalaa`) taşırsınız, kit taşınabilir olduğu için hiçbir şey bozulmaz; (3) yerel Android derlemesi gerekirse kısa bir sürücü harfi tanımlanır (`subst`, Doğrulanacak). Karar sizindir; taşımayı Claude Code değil siz yaparsınız.

## 5. İlk açılış

1. Proje klasöründe terminal açın: Dosya Gezgini'nde klasöre sağ tıklayıp "Terminalde aç", ya da:
   ```powershell
   cd "C:\Users\MEHMET SAİD\OneDrive\Masaüstü\mutalaa-kit"
   claude
   ```
   **Claude Code'u her zaman proje kökünde başlatın.** Alt klasörde (ör. `docs`, `apps\mobile`) başlatılırsa projenin `.claude/settings.json` dosyası, izin kuralları ve hook'ları yüklenmez; yalnız `CLAUDE.md` okunur ve klasör korumaları çalışmaz.
2. İlk kez açıyorsanız tarayıcıda Claude hesabınızla giriş yapın.
3. **Klasöre güven sorusunu onaylayın.** Projenin onaysız çalışacak komut listesi (`permissions.allow`) ancak güvenden sonra etkinleşir.
4. Kitin yüklendiğini denetleyin:

| Komut | Beklenen |
|---|---|
| `/hooks` | `SessionStart`, `PreToolUse`, `PostToolUse` altında üç kayıt (`oturum-baslangici`, `klasor-bekcisi`, `metin-kurali`) |
| `/agents` | 11 proje ajanı (`mobil-gelistirici` … `arastirmaci`) |
| `/skills` | 16 proje becerisi (`asama`, `durum` … `windows-sorun`) |
| `/permissions` | Projenin izin, sorma ve engelleme kuralları |
| `/status` | "Setting sources" satırında proje ayarları (`Project settings`) görünür |
| `/memory` | `CLAUDE.md`. Klasöre özgü `.claude/rules/` kuralları ilgili dosyaya dokunulunca yüklenir; o an yüklü olanlar `/context` ile görülür |

Oturumun ilk mesajında Claude Code'a ilerleme özeti eklenir ("Mütâlaa · oturum başlangıcı"). Sonra `/asama A00` yazın.

## 6. Ayarların anlamı

| Ayar (`.claude/settings.json`) | Değer | Neden |
|---|---|---|
| `language` | `turkish` | Claude Code yanıtları Türkçe |
| `permissions.defaultMode` | `acceptEdits` | Proje içindeki dosya düzenlemeleri sorulmadan uygulanır; komutlar kurallara göre sorulur. `Shift+Tab` ile kip değiştirilir |
| `permissions.blockReadsOutsideWorkingDirectories` | `true` | Dosya araçları proje dışını okuyamaz; çözümlenemeyen komutlar (ör. `node -e`) onay ister |
| `permissions.allow` | git'in okuma ve commit komutları, `pnpm`, `npx expo`, `dotnet`, `uv`, `docker compose`, `adb`, `maestro`, `eas`'ın okuma komutları, `node --test` ve bağlantı denetimi; belgeler için web alan adları | Günlük geliştirme sorulmadan yürür. Tek başına `node <betik>` ve `curl` sorulur |
| `permissions.deny` | `.env` ve `.env.*` okuma (`.env.example` hariç), `.env` ve `.env.local` yazma, anahtar dosyaları; `data/raw` içine yazma; zorla push; `eas submit`; paket yayımlama | Gizli değer, ham kaynak ve geri dönüşsüz işlem koruması |
| `permissions.ask` | push, `git reset`, `clean`, `restore`, `rebase`, `commit --amend`, `stash drop`, `branch -D`; `eas build` ve `update`; `docker compose down -v`; `dotnet user-secrets`; `rm -rf` ve benzerleri | Onayınız olmadan yapılmaz |
| `autoMemoryEnabled` | `false` | Proje bilgisi yalnız depodaki dosyalarda tutulur; klasör dışına hafıza yazılmaz |
| `enableArtifact` | `false` | Claude Code'un proje dışındaki oturum karalama klasörü (scratchpad) ve Artifact aracı kapalı; geçici dosyalar `.tmp/` altında |
| `plansDirectory` | `.tmp/planlar` | Plan dosyaları proje içinde ve git dışında |
| `env` | `CLAUDE_CODE_USE_POWERSHELL_TOOL=0`, `PYTHONUTF8=1`, `ASPNETCORE_ENVIRONMENT` ve `DOTNET_ENVIRONMENT` `Development`, .NET, Turborepo ve Next.js telemetrisi kapalı | Komutlar yalnız Git Bash'te çalışır (aşama komutları bash sözdizimindedir); Türkçe Windows kodlama tuzağı; `dotnet ef` ve Yayınlayıcı kullanıcı sırlarını yalnız `Development`'ta okur ve `export` komutlar arasında kalmaz; gizlilik |
| `hooks` | Oturum başı durum özeti; klasör bekçisi (`onFailure: block`); biçim denetimi | Bekçi çalışamazsa yazma ve komutlar durur (güvenli taraf) |

Kendi bilgisayarınıza özgü bir ayar gerekirse (ör. Git Bash yolu) `.claude/settings.local.json` dosyasına yazılır; bu dosya git dışındadır.

## 7. Klasör sınırı: neyi engeller, neyi engellemez

| Katman | Ne yapar | Sınırı |
|---|---|---|
| Dosya araçları (Read, Write, Edit) | Proje dışını okuyamaz (`blockReadsOutsideWorkingDirectories`) ve yazamaz (klasör bekçisi) | Kesin engel |
| Kabuk komutları (Git Bash, Monitor) | Komutta görünen proje dışı yol, ev ya da geçici klasör başvurusu (`~`, `$HOME`, `$USERPROFILE`, `$TEMP`, `/tmp` …) onay ister. `data/raw` ve `.git` içine yazma reddedilir; `CLAUDE.md`, kit dosyaları ve karar defterine yazma, özyinelemeli silme ve geri dönüşü zor git işlemleri onay ister | Komut metnine bakar; betiğin içinde kurulan yolu göremez |
| Çalıştırılan programlar (`uv run`, `dotnet run`, `pnpm` betikleri, testler, `node <betik>`) | Claude Code bunların açtığı dosyaları sınırlamaz | Windows'ta işletim sistemi düzeyinde kum havuzu (sandbox) yoktur |
| Claude Code'un ve araçların kendi dosyaları | Oturum kayıtları ve kullanıcı ayarları `%USERPROFILE%\.claude` altındadır; araç önbellekleri (pnpm, NuGet, uv, Docker) ve test çerçevelerinin geçici dosyaları kendi yerlerindedir | Kuralın dışındadır |

Bu yüzden kural 1 (CLAUDE.md) Claude için bağlayıcıdır: yazdığı betik ve komutlar proje dışı yol kullanmaz; `inceleyici` bunu denetler. Satır içi kod (`node -e`, `python -c`) ve tek başına `node <betik>` onay ister: komutu okuyup onaylayın ya da reddedin. İşletim sistemi düzeyinde kesin sınır isterseniz Claude Code'u yalnız bu klasöre erişimi olan ayrı bir Windows kullanıcısıyla ya da WSL2 içinde kum havuzu açıkken çalıştırmanız gerekir; bu kurulum kitin dışındadır (Doğrulanacak).

## 8. Güncelleme ve sorun giderme

- Yerel kurulum kendiliğinden güncellenir. WinGet kurulumunda `winget upgrade Anthropic.ClaudeCode`.
- `claude doctor` kurulumu ve ayar dosyalarını denetler; hatalı bir anahtar varsa anahtarın yolunu gösterir.
- Claude Code Git Bash'i bulamıyorsa `.claude/settings.local.json` içine yazın: `{"env": {"CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"}}`.
- Hook hatası ("node bulunamadı"): Node kurulu ve PATH'te olmalı; terminali yeniden açın. Klasör bekçisi çalışamazsa Claude Code güvenlik için dosya yazmayı ve komutları durdurur. Hook ayrıntısı için `claude --debug hooks`.
- Kit bozulursa geçici olarak `claude --safe-mode` ile özelleştirmeler kapalı açılır; sonra `node --test ".claude/hooks/test/*.test.mjs"` ile hook'ları sınayın.
- Diğer sorunlar: `windows-sorun` becerisi ve [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §10.

## İlgili dosyalar

- [Claude Code rehberi](./README.md) · [Çalışma düzeni](./02-calisma-duzeni.md) · [A00 · Ortam ve depo](./asamalar/A00-ortam-ve-depo.md) · [İnsan adımları](./06-insan-adimlari.md)
- [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) · [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md)
