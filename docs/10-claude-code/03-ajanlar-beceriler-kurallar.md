# Ajanlar, beceriler, kurallar ve hook'lar

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)

Bu dosya kitin her parçasını listeler. Dosyalar `.claude/` altındadır; değişiklikleri Claude Code onaysız yapar (K-31, 27 Ekim 2026 güncellemesi). `.claude/` Claude Code'un yerleşik korumalı yoludur: oradaki yazma, hook'tan bağımsız olarak Claude Code'un kendi onayını isteyebilir ve yalnız `bypassPermissions` kipinde kalkar.

## 1. Alt ajanlar (`.claude/agents/`)

Ajanlar Claude Code'un iş devrettiği uzmanlardır. Ana oturum açıklamalarına bakarak kendiliğinden seçer; adıyla da çağırabilirsiniz ("hat-gelistirici ajanıyla …"). Hepsi ana oturumun modelini kullanır (`model: inherit`).

| Ajan | Rol | Araçlar | Önceden yüklenen beceriler | Ne zaman |
|---|---|---|---|---|
| `mobil-gelistirici` | Expo, React Native, TypeScript | Hepsi (başka ajan başlatamaz) | `mobil-ekran`, `capa-gramer` | Mobil ekran, bileşen, veri katmanı, ses |
| `web-gelistirici` | Editör paneli, Next.js, TypeScript paketleri | Hepsi (başka ajan başlatamaz) | `capa-gramer` | `apps/editor`, `apps/web`, `packages/anchors`, `packages/search` |
| `sunucu-gelistirici` | ASP.NET Core 10, EF Core 10, PostgreSQL 18, Yayınlayıcı | Hepsi (başka ajan başlatamaz) | `ef-goc`, `lisans-kapisi`, `capa-gramer` | `server/` |
| `hat-gelistirici` | Python 3.13, uv, içerik hattı | Hepsi (başka ajan başlatamaz) | `icerik-hatti`, `metin-butunlugu`, `capa-gramer` | `pipeline/`, kaynak alımı, OCR, QA |
| `test-yazari` | Test yazımı ve çalıştırma | Hepsi (başka ajan başlatamaz) | `test-vektoru` | Kabul ölçütünü teste çevirme, vektörler, göç ve kapı testleri, Maestro |
| `inceleyici` | Kod incelemesi | Read, Grep, Glob, Bash (yazma aracı yok; Bash yalnız okuma ve test için) | `metin-butunlugu`, `lisans-kapisi`, `capa-gramer` | Her adım ve aşama sonunda, commit öncesi |
| `metin-denetcisi` | Metin bütünlüğü denetimi | Read, Grep, Glob, Bash | `metin-butunlugu`, `capa-gramer` | Kur'an metni, meal, normalizasyon, çapa, arama değişince |
| `lisans-denetcisi` | Lisans ve yayın kapısı denetimi | Read, Grep, Glob, Bash | `lisans-kapisi`, `paket-yayini` | Kaynak, paket, manifest, görünürlük, bağımlılık değişince ve yayın öncesi |
| `arayuz-denetcisi` | Tasarım sistemi ve erişilebilirlik denetimi | Read, Grep, Glob, Bash | `mobil-ekran` | Ekran ve bileşen değişince; ekran görüntüsü incelemesi |
| `belge-bekcisi` | Belgeleri kodla ve kararlarla eşitler | Read, Grep, Glob, Edit, Write, Bash (yalnız `docs/`) | — | Aşama sonunda, `/belge-esitle` |
| `arastirmaci` | Güncel sürüm, API ve "Doğrulanacak" maddelerini doğrular | Read, Grep, Glob, WebSearch, WebFetch | — | Emin olunamayan her teknik bilgi |

## 2. Beceriler (`.claude/skills/<ad>/SKILL.md`)

**İş akışı becerileri.** `/asama` yalnız siz yazınca çalışır (`disable-model-invocation: true`). Diğerlerini siz yazabilirsiniz; Claude Code da `/asama` adımlarında ya da gerektiğinde kendisi çağırır (ör. aşama sonunda `/inceleme` ve `/commit`):

| Komut | İş |
|---|---|
| `/asama A07` · `/asama A07.2` · `/asama sonraki` | Aşamayı baştan sona yürütür: önkoşul, plan ve onay, uygulama, doğrulama, inceleme, belge ve ilerleme, commit |
| `/durum` | İlerleme özeti, başlanabilir aşamalar, bekleyen insan adımları, önerilen adım (dosya değiştirmez) |
| `/karar <konu>` | Karar defterine yeni karar ya da güncelleme; eski karar silinmez |
| `/inceleme [kapsam]` | Hızlı denetimler ve denetçi ajanlarla commit öncesi inceleme |
| `/commit [ipucu]` | Conventional Commits; gizli ve git dışı dosyaları dışarıda bırakır; push yok |
| `/belge-esitle [kapsam]` | Belgeleri koda göre eşitler; bağlantı ve çapa denetimi (`baglanti-denetimi.mjs`) |
| `/yazisma <muhatap>` | Kurul, avukat, QAC, KFGQPC, QF, hafız, Tanzil, Sunnah.com, fawazahmed0 ve Tarteel (QUL) için yazışma taslağı (`docs/yazismalar/`); göndermez |

**Bilgi becerileri** Claude Code ilgili işe girince kendiliğinden yüklenir; isterseniz `/ad` ile de çağrılır:

| Beceri | İçerik |
|---|---|
| `capa-gramer` | Çapa biçimleri, anlam kuralları, hata kodları, üç dildeki API, rota ve depolama biçimi |
| `metin-butunlugu` | Kanonik metin, NFC kuralı, `content_hash`, ofsetler, Türkçe yerel ayar tuzakları, kodlama |
| `lisans-kapisi` | Lisans durumları, derleme türü matrisi, başlangıç durumları, P-01…P-14, manifest, yeni kaynak |
| `paket-yayini` | Yayınlayıcı komutları, depo düzeni, yerel `dev` döngüsü, `fetch-core`, sık hatalar |
| `ef-goc` | EF Core göç iş akışı ve kuralları |
| `mobil-ekran` | Ekran ve bileşen kontrol listesi; emülatörden ekran görüntüsüyle görsel doğrulama |
| `test-vektoru` | Ortak test vektörlerinin düzeni, biçimi, üç dilde geçirme |
| `icerik-hatti` | Hat modülleri, komutlar, çıkış kodları, veri soyu, QA kapıları, yapay zekâ politikası |
| `windows-sorun` | Windows'a özgü sorunların teşhis ve çözüm tablosu |

## 3. Kurallar (`.claude/rules/`)

Kurallar ilgili klasördeki bir dosya okunduğunda ya da düzenlendiğinde yüklenir (`paths` ön bilgisi).

| Dosya | Kapsam | Özet |
|---|---|---|
| `mobil.md` | `apps/mobile/**` | Katmanlar, kitaplıklar, veri, derleme türleri, jetonlar, erişilebilirlik, test kimlikleri |
| `paylasilan-paketler.md` | `packages/**`, `shared/**` | Platformdan bağımsızlık, yaprak paketler, vektörler şartnamedir, yerel ayar |
| `sunucu.md` | `server/**` | Bağımlılık, kültür, EF Core, metin, API, Yayınlayıcı, gizli değerler |
| `icerik-hatti.md` | `pipeline/**` | Veri soyu, idempotentlik, lisans, yapay zekâ, çıkış kodları |
| `editor-ve-web.md` | `apps/editor/**`, `apps/web/**` | Üretilen API istemcisi, inceleme akışı, web rotaları |
| `belgeler.md` | `docs/**` | Karar defteri önceliği, dosya düzeni, bağlantılar, hukuki uyarı |
| `altyapi.md` | `docker-compose.yml`, `infra/**`, `scripts/**`, `.github/**`, `.env.example` | Compose, gizli değerler, yıkıcı komutlar, PowerShell betikleri, CI |

## 4. Hook'lar (`.claude/hooks/`)

Hook'lar `.claude/settings.json` içinde tanımlıdır ve kabuk kullanmadan `node` ile çalışır (yoldaki boşluk ve Türkçe karakter sorun çıkarmaz).

| Betik | Olay | Davranış |
|---|---|---|
| `oturum-baslangici.mjs` | `SessionStart` (açılış, devam, `/clear`, `/compact`, çatallama) | `05-ilerleme.md` içindeki durum bloğunu ve kısa hatırlatmaları bağlama ekler |
| `klasor-bekcisi.mjs` | `PreToolUse` (Write, Edit, MultiEdit, NotebookEdit, Bash, PowerShell, Monitor); `onFailure: block` | Dosya araçlarında proje dışına ve `data/raw`, `.git` içine yazmayı reddeder; kit dosyaları, `CLAUDE.md` ve karar defteri onaysızdır. Kabuk komutlarında proje dışı yol, ev ya da geçici klasör başvurusu ile nadir git işleri (`filter-branch`, `filter-repo`, `update-ref`, `gc`, `reflog expire`, `commit --no-verify`) için onay ister; yönlendirme, `cp`, `mv`, `rm`, `tee`, `sed -i`, `touch`, `mkdir` hedeflerini aynı kurallardan geçirir. Kesin yasakları reddeder: zorla push, `git clean -x`, `data/raw`, `data/gold`, `data/backups` silme, gizli değer dosyalarına kabuktan erişim, `eas submit`, yayımlama, yedeksiz veri silme ve denetçi ajanların `.tmp/` dışına yazması ya da git'i değiştirmesi (`agent_type` alanı); tam liste [Çalışma düzeni §2](./02-calisma-duzeni.md). `mobile-v*` etiketi itmek ücretli derleme başlattığı için sorulur. Çalışamazsa işlem durur. Çalıştırılan programların içini göremez ([Kurulum §7](./01-kurulum.md#7-klasör-sınırı-neyi-engeller-neyi-engellemez)) |
| `metin-kurali.mjs` | `PostToolUse` (Write, Edit, MultiEdit, NotebookEdit) | BOM, CRLF, ASCII dışı dosya adı, bozuk JSON ve JSONL, kit ön bilgisi hatalarını Claude Code'a geri bildirir |

Testler: `node --test ".claude/hooks/test/*.test.mjs"` (Windows yolları, kabuk komutları, ilerleme dosyası ve kitin kendi tutarlılığı dahil 73 test).

## 5. Kit nasıl değiştirilir

- Kit dosyası değişikliği bir karar sayılır: önce gerekçe, sonra değişiklik, sonra test. Ajan ya da beceri eklemek için dosyayı `.claude/agents/<ad>.md` ya da `.claude/skills/<ad>/SKILL.md` olarak yazdırın; ad küçük harf ASCII ve tire.
- Değişiklikten sonra: hook testleri, ayar doğrulaması (oturumda `/doctor` ya da ayrı terminalde `claude doctor`), bağlantı denetimi ve yeni oturumda `/agents`, `/skills`, `/hooks` ile yüklendiğini görmek.
- Commit kapsamı `kit`: `chore(kit): …`.

## İlgili dosyalar

- [Claude Code rehberi](./README.md) · [Kurulum](./01-kurulum.md) · [Çalışma düzeni](./02-calisma-duzeni.md) · [Aşama haritası](./04-asama-haritasi.md)
