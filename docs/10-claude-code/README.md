# Claude Code ile geliştirme

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)

Mütâlaa yalnız Claude Code ile ve yalnız bu proje klasörünün içinde geliştirilir ([K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)). Bu bölüm o işin rehberidir. Kit üç parçadır: kökteki `CLAUDE.md`, `.claude/` klasörü ve bu `docs/10-claude-code/` bölümü.

## On dakikada başlangıç

1. [Kurulum](./01-kurulum.md) dosyasındaki araçları kurun (İ-01) ve Claude Code'a giriş yapın.
2. Proje klasörünün kökünde bir terminal açın (ör. Windows Terminal'de) ve `claude` yazın. Alt klasörde başlatmayın: projenin ayarları ve hook'ları yalnız kökte yüklenir. İlk açılışta klasöre güven sorusunu onaylayın.
3. İlk oturumda yazın: `/asama A00`. Claude Code ortamı denetler, yol kararını size sorar, git deposunu açar ve kiti doğrular.
4. Sonra `/asama sonraki` yazın. Her aşama tedarikle başlar: Claude Code gereken yapıları internette ve GitHub'da araştırır, aşama dosyasının `## Tedarik` bölümüne yazar, dosyaları kendisi indirir ve işler.
5. Her aşamadan sonra `/clear` ile yeni oturum açın ve `/durum` ya da `/asama sonraki` yazın.

## Kitte neler var

| Parça | Yer | Görev |
|---|---|---|
| Proje kılavuzu | `CLAUDE.md` | Her oturumda okunan kesin kurallar, depo haritası, komutlar, çalışma düzeni |
| Ayarlar | `.claude/settings.json` | Türkçe yanıt, izin kuralları, klasör dışı okuma engeli, otomatik hafıza ve karalama klasörü kapalı, yalnız Git Bash, hook'lar |
| Hook'lar | `.claude/hooks/` | Klasör bekçisi (dışarı yazmayı engeller; kabuk komutlarında dış yolu, korunan yerlere yazmayı, özyinelemeli silmeyi ve riskli git işlemlerini denetler), biçim denetimi (BOM, CRLF, JSON, kit ön bilgisi), oturum başı durum özeti |
| Kurallar | `.claude/rules/` | Klasöre özgü kurallar; ilgili dosyaya dokunulunca yüklenir |
| Ajanlar | `.claude/agents/` | 10 alt ajan: geliştiriciler, test yazarı, denetçiler, belge bekçisi, araştırmacı |
| Beceriler | `.claude/skills/` | 6 iş akışı becerisi (`/asama` yalnız sizin başlattığınız; `/durum`, `/karar`, `/inceleme`, `/commit`, `/belge-esitle` hem sizin hem Claude'un çağırdığı) ve 8 bilgi becerisi |
| Aşamalar | `docs/10-claude-code/asamalar/` | A00–A40: her biri amaç, okunacak belgeler, tedarik, adımlar, kabul ölçütleri, doğrulama komutları |

Ayrıntılı katalog: [Ajanlar, beceriler ve kurallar](./03-ajanlar-beceriler-kurallar.md).

## Bu bölümün dosyaları

| Dosya | İçerik |
|---|---|
| [01-kurulum.md](./01-kurulum.md) | Windows'ta Claude Code ve proje araçlarının kurulumu, ilk açılış, kitin doğrulanması |
| [02-calisma-duzeni.md](./02-calisma-duzeni.md) | Oturum düzeni, aşama dosyası ve tedarik, izin kipleri, plan, onay, inceleme, commit, bağlam yönetimi |
| [03-ajanlar-beceriler-kurallar.md](./03-ajanlar-beceriler-kurallar.md) | Kitteki her ajan, beceri, kural ve hook'un ne yaptığı ve ne zaman kullanıldığı |
| [04-asama-haritasi.md](./04-asama-haritasi.md) | A00–A40 listesi, bağımlılıklar, kritik yol, fazlarla eşleşme |
| [05-ilerleme.md](./05-ilerleme.md) | Aşamaların durumu ve oturum günlüğü; oturum başında otomatik okunur |
| [06-insan-adimlari.md](./06-insan-adimlari.md) | Claude Code'un yapamadığı işler (hesaplar, altyapı, editör emeği) |
| [07-belge-celiskileri.md](./07-belge-celiskileri.md) | Belgelerde bulunan çelişkiler: karar bekleyenler (çözülecekleri aşamayla) ve düzeltilenler |
| [asamalar/](./asamalar/) | Aşama dosyaları |

## Temel ilkeler

- **Klasör sınırı.** Claude Code'un dosya araçları bu klasörün dışını okuyamaz ve yazamaz; kabuk komutlarında görünen dış yollar onay ister. Claude'un çalıştırdığı programlar işletim sistemi düzeyinde sınırlanmaz; ayrıntı ve sınırlar: [Kurulum §7](./01-kurulum.md#7-klasör-sınırı-neyi-engeller-neyi-engellemez). Geçici dosyalar `.tmp/` altındadır. Araçların kendi önbellekleri ve Claude Code'un kendi oturum kayıtları bu kuralın dışındadır.
- **İçerik etiği.** Kur'an, meal, tefsir, hadis ve Risale metni hiçbir zaman yapay zekâ hafızasından yazılmaz; yalnız kaynak dosyalardan, içerik hattıyla gelir.
- **Kaynak ilkesi.** Her aşama tedarikle başlar: araştır, belirle, işle. Hazır yapı önce gelir. Kaynaklar internetten ve GitHub'dan izin istenmeden alınır; hiçbir aşama dış bir onay ya da cevap beklemez. Bekleyen bir insan adımı yalnız kendisine bağlı alt adımı bekletir ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)).
- **Kanıtla bitir.** Bir aşama, kabul ölçütleri komut çıktısıyla kanıtlanmadan ve inceleme yapılmadan bitmiş sayılmaz.
- **Kararlar defterde.** Yeni karar `/karar` ile [karar defterine](../00-ozet/02-karar-defteri.md) yazılır; kod ve belge sonra uyar.

## İlgili dosyalar

- [Belgeler ana sayfası](../README.md) · [Karar defteri](../00-ozet/02-karar-defteri.md) · [Fazlar](../08-yol-haritasi/01-fazlar.md)
- [Proje yapısı](../02-mimari/03-proje-yapisi.md) · [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) · [Test stratejisi](../07-yayin/03-test-stratejisi.md)
