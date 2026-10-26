# Mütâlaa · Claude Code proje kılavuzu

Bu dosyayı Claude Code her oturumda okur. Burada her işte geçerli kurallar ve harita durur; ayrıntı `docs/` altındadır. Belgeler: [docs/README.md](docs/README.md) · Claude Code rehberi: [docs/10-claude-code/README.md](docs/10-claude-code/README.md).

## Proje

- **Mütâlaa:** Kur'an-ı Kerîm, Elmalılı meali, hadis ve Risale-i Nur için çevrimdışı okuma ve öğrenme uygulaması. Önce mobil (Expo), arka uç ASP.NET Core 10 + PostgreSQL 18, içerik hattı Python 3.13 (uv), editör paneli React + Vite, web sonra (Next.js).
- **Tek doğruluk kaynağı:** [docs/00-ozet/02-karar-defteri.md](docs/00-ozet/02-karar-defteri.md). Dokümanla çelişen kod yazılmaz. Çelişki görürsen dur, kullanıcıya göster ve `/karar` öner. Bilinen ve karar bekleyen çelişkiler [belge çelişkileri](docs/10-claude-code/07-belge-celiskileri.md) dosyasında, çözülecekleri aşamayla birlikte durur.
- **Çalışma birimi aşamadır:** [aşama haritası](docs/10-claude-code/04-asama-haritasi.md), [ilerleme](docs/10-claude-code/05-ilerleme.md). Bir isteğin hangi aşamaya ait olduğunu söyle; başka aşamanın işini sessizce yapma.

## İletişim

- Kullanıcıyla Türkçe konuş. Kod tanımlayıcıları, dosya adları ve commit mesajları İngilizce (Conventional Commits; [Proje yapısı §6](docs/02-mimari/03-proje-yapisi.md)). Arayüz metinleri Türkçe ve i18n dosyalarındadır.
- Rapor kısa ve kanıtlı olur: ne yapıldı, hangi komut ne sonuç verdi, ne kaldı.
- Emin olmadığın sürüm, komut, bayrak ya da API'yi uydurma. `arastirmaci` ajanıyla resmî kaynaktan doğrula.

## Kesin kurallar

1. **Klasör sınırı.** Proje klasörünün dışına dosya yazılmaz, oradan dosya okunmaz, oraya dosya taşınmaz. Geçici dosyalar proje içindeki `.tmp/` klasörüne yazılır. Yazdığın komut ve betiklerde proje dışı yol kullanma: mutlak yol, `..` ile kökten çıkış, `~`, `$HOME`, `$USERPROFILE`, `$TEMP`, `/tmp` yok. Ev klasörü, OneDrive'ın üst klasörleri ve başka projeler (ör. `quran-app-docs`) kapsam dışıdır. Araçların kendi önbellekleri ve geçici dosyaları (pnpm deposu, NuGet, uv, Gradle, Docker birimleri, test çerçevelerinin sistem geçici klasörü) bu kuralın dışındadır. Dosya araçlarını izin ayarı ve hook kesin olarak sınırlar; kabuk komutlarında hook görünen yolları denetler; çalıştırılan programları hiçbir şey sınırlamaz, bu yüzden kural senin için bağlayıcıdır. Engelleri aşmaya çalışma; engel çıkarsa dur ve kullanıcıya söyle.
2. **İçerik etiği.** Kur'an metni, meal, tefsir, hadis ya da Risale metni hafızadan yazılmaz, tamamlanmaz, "düzeltilmez" ve örnek diye uydurulmaz. Bu metinler yalnız kaynak dosyalardan, içerik hattı ile gelir. Testte açıkça sentetik metin ("Deneme paragrafı 1 …") ya da lisansı izin veren kaynak dosyasından alınmış parça kullanılır. Yapay zekâ ile meal, tefsir ya da hadis çevirisi üretilmez; Risale için yapay zekâ özeti yazılmaz (K-25, K-30).
3. **Kanonik metin (K-26).** Tanzil metni bayt bayt saklanır; NFC bile uygulanmaz. NFC yalnız kendi ürettiğimiz metne, ilk kayıtta uygulanır. Ofsetler Unicode kod noktasıdır; aralık yarı açıktır `[başlangıç, bitiş)`. Arama için normalize metin ayrı sütundadır. `data/raw/` değişmez. Ayrıntı: `metin-butunlugu` becerisi.
4. **Çapalar (K-26).** Tek gramer: `q:2:255`, `q:2:255:3-7`, `meal:elmalili:2:255`, `tf:elmalili:2-255-257:p3`, `rn:…`, `h:…`, `ht:…`, `konu:…`, `…@120-184`. Çapa yeniden numaralanmaz ve silinmez. Ayrıştırma ve biçimleme yalnız ortak uygulamalarla yapılır (`packages/anchors`, `Mutalaa.Domain/Anchors`, `mutalaa_pipeline.anchor`). Ayrıntı: `capa-gramer`.
5. **Lisans kapısı (K-06).** Durumlar `serbest`, `bekliyor`, `ic_kullanim`, `kapali`. `public` ve `internal` derleme yalnız `serbest` içerik görür; `dev` derleme `kapali` dışındakileri görür. `kapali` içerik işlenmez: Risale metni avukat görüşüne kadar `kapali`dır. QAC verisi ayrı `kelime-kok` paketindedir ve `bekliyor` durumundadır. `test-` önekli kaynak `public`'e girmez. Ayrıntı: `lisans-kapisi`.
6. **Kültürden bağımsızlık.** Türkçe İ/ı için açık eşleme kullanılır; büyük-küçük harf dönüşümü cihazın ya da işletim sisteminin yerel ayarına bırakılmaz. .NET'te `StringComparison.Ordinal` ve `CultureInfo.InvariantCulture`, Python'da `encoding="utf-8"`, düzenli ifadede `[0-9]` (`\d` değil).
7. **Dosya biçimi.** UTF-8 (BOM'suz), LF satır sonu (yalnız `.ps1` ve `.cmd` CRLF), ASCII dosya adı. `metin-kurali` hook'u her yazmadan sonra denetler.
8. **Gizli değerler.** `.env` dosyaları okunmaz (izin kuralı engeller). Parola, anahtar ve belirteç koda, dokümana ya da commit'e girmez. .NET'te `dotnet user-secrets`, diğerlerinde git dışı `.env` kullanılır; örnek değerler `.env.example` dosyasındadır.
9. **İlkeler (K-25).** Reklam yok, liderlik tablosu yok, fetva yok. Yapay zekâ ürünü her metin insan onayına kadar "doğrulanmamış" rozeti taşır.
10. **Gizlilik.** v1 kişisel veri toplamaz, analitik yoktur, hata raporu kullanıcı tanımlayıcısı taşımaz ([KVKK ve gizlilik](docs/07-yayin/02-kvkk-ve-gizlilik.md)).
11. **Yetki devri (27 Ekim 2026).** Kullanıcı terminal komutlarının ve geri dönüşü zor işlemlerin icrasını Claude Code'a devretti: `git push`, `git reset`, `git clean`, `git restore`, `rm -r`, `docker compose down -v`, `dotnet user-secrets` için onay sorulmaz. Kullanıcıya yalnız plan, karar, hata, proje durumu ya da kapsam değişikliği (ekleme, çıkarma, güncelleme) sorulur. Eklemeler (27 Ekim 2026): **veri silen işlerden önce yedek alınır** (`docker compose down -v`, `DROP SCHEMA`/`DROP DATABASE`, veritabanı birimi silmek: önce `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1`, yedek alınamazsa silinmez); **ücretli işlerde (`eas build`, `eas update`, ücretli bulut ya da API çağrısı) onay sorulur** (tahmini maliyeti söyle). Değişmeyenler: zorla push yok; mağazaya gönderim (`eas submit`) ve yayımlama (`npm publish`, `pnpm publish`) hiç çalıştırılmaz, kullanıcı elle yapar; `.env` dosyaları okunmaz; gizli değerler sohbete, rapora ve commit'e yazılmaz.

## Depo haritası

```
CLAUDE.md               bu dosya
.claude/                ajanlar, beceriler, kurallar, hook'lar, settings.json (kit)
docs/                   proje belgeleri (00-ozet … 09-kaynakca) ve 10-claude-code (rehber, aşamalar)
apps/mobile             Expo uygulaması            (A21'den sonra)
apps/editor             editör paneli              (A15'ten sonra)
apps/web                Next.js                    (A38'den sonra)
packages/*              anchors, search, content-schema, reader-core, player, ui-tokens
server/                 .NET çözümü: Domain, Infrastructure, Api, Publisher, tests
pipeline/               Python içerik hattı (uv)
shared/test-vectors/    üç dilin ortak test vektörleri (şartname)
infra/, scripts/        yerel altyapı, PowerShell betikleri
data/                   git dışı: gelen, raw, staged, ocr, gold (insan emeği, yedeklenir), packs, reports, backups …
.tmp/                   git dışı geçici dosyalar
```

Bağımlılık kuralları ve klasörlerin tamamı: [Proje yapısı](docs/02-mimari/03-proje-yapisi.md).

## Komutlar

İlgili aşama bitmeden bu komutların bir kısmı çalışmaz.

| İş | Komut |
|---|---|
| Altyapı | `docker compose up -d` · `docker compose ps` · `docker compose down` |
| TypeScript | `pnpm install` · `pnpm lint` · `pnpm typecheck` · `pnpm test` |
| .NET | `dotnet build server/Mutalaa.slnx` · `dotnet test --solution server/Mutalaa.slnx` · `dotnet format server/Mutalaa.slnx --verify-no-changes` |
| Göç | `dotnet ef database update --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api` |
| İçerik hattı | `cd pipeline && uv run pytest` · `uv run ruff check .` · `uv run mutalaa sources check` |
| Paket yayını | `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev` |
| Mobil | `pnpm dev:mobile` · `pnpm --filter @mutalaa/mobile test` |
| Kit testleri | `node --test ".claude/hooks/test/*.test.mjs"` |

## Çalışma düzeni

1. Oturum başında ilerleme özeti bağlama otomatik eklenir. İş başlatmak için `/asama <no>` (ör. `/asama A04`), durum için `/durum`.
2. Önce önkoşulları ve planı göster, kullanıcının onayını al, sonra kod yaz. Büyük işte plan modunu kullan. Aşamaya atanmış `açık` belge çelişkisi varsa planın ilk maddesi onun kararıdır.
3. Küçük adımlarla ilerle; her adımdan sonra ilgili testi ya da denetimi çalıştır. Test yazılmadan özellik bitmiş sayılmaz.
   - **Emülatör ve uygulama içi testleri kullanıcı yapar.** Uygulama emülatörde ya da cihazda çalıştırılıp denenmez, Maestro akışı çalıştırılmaz (yazılabilir), ekran görüntüsü alınmaz ve incelenmez. Birim testi, tip denetimi, lint ve kod incelemesi sürer. Aşama dosyası, beceri ya da ajan tanımı böyle bir doğrulama istese de adım atlanır ve aşamayı bekletmez; ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" diye yazılır.
4. "Bitti" demeden önce: kabul ölçütlerini komut çıktısıyla kanıtla, `/inceleme` çalıştır, [ilerleme](docs/10-claude-code/05-ilerleme.md) dosyasını güncelle, `/commit` ile commit at. A08'e kadar aşama sonunda `git push origin main` (onay sorulmaz, kural 11); A08'den sonra aşama dalı, PR ve squash ([Proje yapısı §6](docs/02-mimari/03-proje-yapisi.md)). Zorla push yok.
5. Kod dokümandan saparsa ya da bir "Doğrulanacak" çözülürse `/belge-esitle`; yeni karar gerekirse uygulamadan önce `/karar`.
6. Bir aşama bitince kullanıcıya `/clear` ile yeni oturum açmasını öner.
7. Claude Code'un yapamadığı işler (Kurul, avukat, hesaplar, izinler, insan düzeltmeleri) [insan adımları](docs/10-claude-code/06-insan-adimlari.md) listesindedir. Bekleyen insan adımına bağlı işi başlatma; kullanıcıya hangi adımın beklendiğini söyle.

## Ajanlar ve beceriler

- **Geliştiriciler:** `mobil-gelistirici`, `web-gelistirici`, `sunucu-gelistirici`, `hat-gelistirici`, `test-yazari`.
- **Denetçiler (dosya yazma araçları yok; Bash'i yalnız okuma ve test için kullanırlar):** `inceleyici`, `metin-denetcisi`, `lisans-denetcisi`, `arayuz-denetcisi`, `arastirmaci`. **Belgeler:** `belge-bekcisi`.
- **İş akışı becerileri:** `/asama` (yalnız kullanıcı başlatır), `/durum`, `/karar`, `/inceleme`, `/commit`, `/belge-esitle`, `/yazisma` (kullanıcı ya da sen çağırırsın; `/asama` adımları bunları kullanır).
- **Bilgi becerileri (kendiliğinden yüklenir):** `capa-gramer`, `metin-butunlugu`, `lisans-kapisi`, `paket-yayini`, `ef-goc`, `mobil-ekran`, `test-vektoru`, `icerik-hatti`, `windows-sorun`.
- Katalog: [Ajanlar, beceriler ve kurallar](docs/10-claude-code/03-ajanlar-beceriler-kurallar.md). Klasöre özgü kurallar `.claude/rules/` altındadır ve ilgili dosyalara dokunulunca yüklenir.

## Windows notları

- Proje yolu boşluk, Türkçe karakter ve OneDrive içerir. Komutlarda göreli yol kullan; mutlak yolu tırnakla.
- Oturum proje kökünde açılmış olmalı: çalışma dizini bu dosyanın klasörü değilse (alt klasörde açıldıysa) projenin ayarları ve hook'ları yüklenmemiştir; dur ve kullanıcıdan Claude Code'u proje kökünde yeniden başlatmasını iste.
- Komutlar Git Bash'te çalışır (bash sözdizimi); PowerShell aracı kapalıdır (`CLAUDE_CODE_USE_POWERSHELL_TOOL=0`). PowerShell betikleri `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/<betik>.ps1` ile çağrılır.
- Satır içi kod (`node -e`, `python -c`) ve tek başına `node <betik>` onay ister; bu beklenen davranıştır. Tekrar kullanılacak denetimleri ilgili paketin ya da `scripts/` klasörünün içinde, proje dışı yol kullanmayan betik olarak yaz; kullanıcı komutu görüp onaylar.
- Android geliştirme derlemesi varsayılan olarak EAS bulutunda yapılır; yerel derleme A00'daki yol kararına bağlıdır.
- Bilinen sorunlar ve çözümleri: `windows-sorun` becerisi.
