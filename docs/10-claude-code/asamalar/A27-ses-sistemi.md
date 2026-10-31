# A27 · Ses sistemi (hazır kayıtlar, ayna, çevrimiçi öncelikli dinleme, isteğe bağlı indirme)

> **Sürüm:** 2.0 · **Tarih:** 30 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-40](../../00-ozet/02-karar-defteri.md#k-40--ses-kaynağı-hazır-dijital-tilavet-kaynakları) · [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses) · [K-18](../../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A13](./A13-yayinlayici-ve-kalite-kapisi.md) · [A29](./A29-kutuphane-ve-depolama.md) (A29.4 yeterli; yalnız A27.5 ve sonrası için) · **İnsan adımı:** [İ-07](../06-insan-adimlari.md) (gerekmiyor, K-40) · İ-18 (yalnız `internal` ve `public` ayna için) · İ-15 (yalnız iOS cihaz denemesi)
> **Ajanlar:** `hat-gelistirici` · `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `icerik-hatti` · `ef-goc` · `paket-yayini` · `mobil-ekran` · **Tahmini oturum:** 5–7
> **Başlat:** `/asama A27`

## Amaç
Mütâlaa'da en çok dinlenen okuyucuların hazır kayıtları indirmeden çevrimiçi dinlenir; istenen sure ya da kaydın bütün Kur'an'ı cihaza kalıcı olarak indirilir ve çevrimdışı çalar. Ses sure başına tek dosyadır; âyetler dosya içinde karedir ve kayda bağlı zamanlamayla bulunur. Âyet âyet ve kesintisiz sure dinleme, âyet tekrarı, sonraki sureye geçiş ve Nâs kuralı tek motorla çalışır; çalan âyet okuyucuda vurgulanır. Dosyalar içerik hattıyla bir kez alınır ve kendi depomuzdan değişmez adreslerle sunulur. Dayanak: [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md), karar: [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme).

## Okunacak belgeler
- [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md): tamamı · [Ses sistemi](../../06-mobil/02-ses-sistemi.md): tamamı
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §2 `device.db`, §3 dosya düzeni, §4 kuyruk, §5 bütünlük
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (mini oynatıcı, `ChipSlot`), §5 (oynatıcı aktörü, `usePlayback`), §8 (`USER_SCROLLED`), §10 (bayraklar)
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §9 kural 9, §10 Sesli takip · [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §6 (`MiniPlayer`, `PlayerSheet`, `ReciterRow`, `ChipSlot`, `FollowChip`)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.5 · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §9.1 `audio_timing` · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4–§8
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §3, §8, §9 · [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar.md): §3.7

## Kapsam
**Yapılır**
- İçerik hattında ses kataloğu ve ayna: QUD v4.0.0 ve MP3Quran okuyucuları, kaynak dosyaların bir kez alınması ve ölçülmesi, `ses-katalog` ve `ses-zaman-{kayit}` paketleri, ayna dosyalarının içerik deposuna yüklenmesi.
- `packages/player`: dosya × kare motor arayüzü, `decideAfterFrame`, zamanlama araması, XState makinesi ve testleri.
- Mobil: `PlaylistEngine`, `SingleEngine`, ses oturumu, otomatik kaynak çözücü, okuyucu seçici, mini oynatıcı, Dinleme sayfası, âyet vurgusu ve takip modu, eylem çubuğunda "Dinle".
- Ses indirme işleri A29'un kuyruğunda (tek sure ve kaydın tamamı); çevrimdışı çalma.
- v1 kayıtları: `alafasy-murattal`, `maher-murattal`, `sudais-murattal`, `ghamdi-murattal`, `abdulbasit-murattal`, `abdulbasit-mucevved`, `husary-murattal`, `minshawi-murattal`, `minshawi-mucevved`.

**Yapılmaz**
- Kelime takibinin açılması (`kelimeTakibi` bayrağı kapalı kalır; eşleme doğrulanınca ayrı iş), Kur'an + meal dönüşümü (v1.x, `mealSesi` kapalı), kelime telaffuz sesi.
- Quran Foundation bağdaştırıcısı (v1.x; A14 API'sine ek uç, production erişimiyle).
- Genel paket indirme kuyruğunun kendisi ve Depolama ekranı ([A29](./A29-kutuphane-ve-depolama.md)); bu aşama kuyruğa ses işi ekler.
- Kaynaklar ve lisanslar ekranının son metni (A32), Maestro "Ses çal" akışı (A33), Kurul başvurusu (A34).

## Adımlar

### A27.1 · Kaynak ve teknoloji araştırması
- Araştırma 30 Ekim 2026'da yapıldı: [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md).
- Aşama başında `arastirmaci` yalnız üç noktayı yeniden doğrular: MP3Quran ses adresinin iki biçimi (`/audio/` ve `/download/audio/`; SK-8), QUD `catalog.json` alanları ve v4.0.0'dan sonra yeni sürüm olup olmadığı, Tarteel CDN adres kalıbı (QUD `chapter_urls`). Sonuçlar rapora işlenir.
- **Bitti sayılır:** rapordaki SK-8 kapandı; QUD sürüm kararı (v4.0.0 ya da daha yenisi) `/karar` gerekmeden rapora yazıldı.

### A27.2 · Okuyucu kataloğu ve ayna (içerik hattı, Yayınlayıcı)
- Kaynak kayıtları (`hat-gelistirici`): `pipeline/sources/ses-mp3quran.toml`, `ses-tarteel-cdn.toml`, `zamanlama-qud.toml` (CC BY 4.0, v4.0.0 ve zip sha256'ları), `zamanlama-mp3quran.toml`; `license_status = "serbest"`, `notlar` "proje sahibi kararı (K-41); yazılı izin dosyada yok". `test_sources.py` sayıları güncellenir. `ses-test` sentetik fikstürü `test-ses` kaynağıyla (sentetik ton, P-12 gereği `public`'e girmez).
- İçerik hattı: `pipeline/src/mutalaa_pipeline/ses/` — `uv run mutalaa ses katalog` (QUD `manifest.json` ve `catalog.json`, MP3Quran `reciters` ve `ayat_timing`; v1 kayıt listesi `pipeline/mutalaa.toml` içinde), `uv run mutalaa ses ayna --kayit <id>` (kaynaktan bir kez alım, `data/raw/ses/{kayit}/{tarih}/{sss}.mp3`, `fetch.json`; bayt, sha256, süre, bit hızı türü; zamanlama son âyetinin süreyi aşmaması ve QUD ölçümünden en çok 2 sn fark), `uv run mutalaa ses zaman --kayit <id>` (QUD zip'inden âyet, kelime ve özel bölüt satırları; çapa `q:{s}:{a}`).
- Editoryal veritabanı (`sunucu-gelistirici`, `ef-goc`): ses kayıtları ve sure dosyaları için tablolar (adlar ve sütunlar bu adımda `/karar` gerekmeden Editoryal veritabanı §9.1'e yazılır) ve `audio_timing`'in kayda bağlanması; EF göçü, göç testleri.
- Yayınlayıcı: `ses-katalog` ve `ses-zaman-{kayit}` paketleri; ayna dosyalarının `audio/{kayit}/{dosya_surumu}/{sss}.mp3` adresine yüklenmesi (yerelde SeaweedFS; canlı depo İ-18). Paket şeması [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §3.5.
- **Bitti sayılır:** 9 kaydın 114'er dosyası yerel depoda ve HTTP ile alınabiliyor; `dev` manifestinde `ses-katalog` ve 9 `ses-zaman-*` paketi var; katalogdaki her dosyanın bayt ve sha256 değeri depodaki dosyayla aynı; kayıt başına âyet zamanlaması 6.236 satır (eksik varsa raporda ve katalogda işaretli); `uv run pytest` ve `dotnet test` yeşil.

### A27.3 · Ortak ses motoru (`packages/player`, önce testler)
- Paket `packages/player`; dış bağımlılık yalnız `xstate`. `react-native` ve `expo-*` içe aktarılmaz.
- Dosyalar: `engine.ts` (`EngineTrack`, `EngineFrame`, `EngineEvent`, `AudioEngine`; Ses sistemi §4.1), `decide.ts` (`decideAfterFrame`, §5.4), `timing.ts` (`activeFrameAt`, `activeWordAt`), `frameTimer.ts` (kalan süre ÷ hız, 150 ms tolerans; §4.3), `machine.ts` (`createPlayerMachine(engine, resolveTracks, saved)`, §5.3 ve §5.5).
- Testler koddan önce (Vitest, sahte motor, sahte zamanlayıcılar): belgedeki karar örneği; `continue` ile `jump` ayrımı; özel bölütten sonra bekleme ve tekrar yok; `repeatRange: 0` sınırsız; uyku `aralik_sonu`; `autoNextSurah` açık ve kapalı; Nâs'ın sonunda `repeatQuran` kapalıyken `end`, açıkken Fâtiha; `ENGINE.TRACK_START` `remote: true` ile sayaçların sıfırlanması; Ses sistemi §5.3'teki her durum ve §5.2'deki her olay; zamanlaması olmayan kayıtta âyet işlevlerinin kapalı olması.
- **Bitti sayılır:** `pnpm --filter @mutalaa/player test` yeşil; her durum ve olay en az bir testte geçer.

### A27.4 · Çevrimiçi oynatma
- `apps/mobile/src/features/audio/`: `session.ts` (`setAudioModeAsync`), `engine/playlist.ts` (`PlaylistEngine`), `engine/single.ts` (`SingleEngine`), `engine/index.ts` (seçim kuralı), `resolveTracks.ts` (katalog, `core` âyet listesi, `ses-zaman-{kayit}`, kaynak: akış), `usePlayback.ts`; oynatıcı ve aktör modül düzeyinde.
- `ses-katalog` manifestle kendiliğinden iner; `ses-zaman-{kayit}` kayıt ilk seçildiğinde kendiliğinden iner.
- Arayüz: okuyucu seçici (`ReciterRow`, 5 saniyelik ön dinleme ayrı oynatıcıda), `MiniPlayer` (`MiniPlayerSlot`), `PlayerSheet` (kapsam, tekrar, bekleme, hız, sonraki sure, bütün Kur'an'ı tekrarla, uyku, "Okunan âyete git"), eylem çubuğunda "Dinle". Seçenek listeleri Okuma deneyimi §10'dan.
- **Bitti sayılır:** RNTL testleri yeşil: parça çözücü (akış adresi, eksik zamanlama), okuyucu seçici, mini oynatıcı görünürlüğü, Dinleme sayfası seçenekleri.

### A27.5 · İndirme (A29.4 kuyruğunda)
- Ses işleri: `scope` `{ "kayit": "alafasy-murattal", "sure": 2 }` ya da `{ "kayit": "alafasy-murattal", "tum": true }`; kaydın tamamı 114 dosyalık tek iştir, dosyalar üçerli paralel iner ve biten her dosya hemen `audio_file`'a yazılır.
- `File.createDownloadTask` → `tmp/<iş>.part`; bitince bayt `kayit_sure.bayt` ve `file.digest('SHA-256')` `kayit_sure.sha256` ile; tutarsa `Paths.document/mutalaa/audio/{kayit}/{dosya_surumu}/{sss}.mp3`.
- Dinleme sayfasında ve sure listesinde "İndir" (sure) ve "Bütün Kur'an'ı indir" (kayıt; boyut ve boş alan gösterilir); ilerleme, duraklatma, sürdürme, iptal ve yeniden deneme kuyruğun durumlarından.
- **Bitti sayılır:** kuyruk ve doğrulama testleri yeşil (sahte dosya sistemi ve sahte indirme): tek sure, kaydın tamamı, yarıda kesilip sürdürme, özet uyuşmazlığında yeniden indirme, Yalnız Wi-Fi'da bekleme.

### A27.6 · Çevrimdışı oynatma
- Kaynak çözücü yerel öncelikli: doğrulanmış `audio_file` → akış → `not_downloaded`. Kayıt değişince başka kaydın dosyası kullanılmaz (`kayit`, `sure`, `dosya_surumu`).
- Çevrimdışıyken yalnız indirilmiş sureler çalınabilir görünür; "Cihazda" rozeti; "Bu sure indirilmedi · İndir".
- iOS'ta indirilen seslerin yedekten dışlanması (SK-7): küçük yerel modül ya da yedeğe girmeyi kabul; seçim bu adımda yazılır.
- **Bitti sayılır:** çözücü testleri yeşil (yerel, akış, çevrimdışı eksik, kayıt değişimi, eski `dosya_surumu`).

### A27.7 · Âyet ve sure geçişleri, senkronizasyon
- Kare zamanlayıcısının motorlara bağlanması; âyet tekrarı ve aralık `seekFrame` ile; sonraki sure (`autoNextSurah`), Nâs kuralı (`repeatQuran`); kilit ekranından sonraki/önceki sure (`PlaylistEngine`).
- Âyet vurgusu (`usePlayback` konumu → `activeFrameAt`), takip modu (`useFollowPlayback`), `FollowChip`; `testID` `etkin-ayet-q:1:2` biçimi.
- **Bitti sayılır:** RNTL testleri yeşil: çip önceliği, etkin âyet `testID`'si, takip kapanıp açılması; motor bağlantısı sahte oynatıcıyla test edildi.

### A27.8 · Hata yönetimi ve sağlamlaştırma
- Hata kodları: `network`, `not_downloaded`, `buffering_timeout`, `source_404`, `integrity`, `recording_removed`; her birinin kullanıcı metni `i18n` dosyasında, yeniden dene ve atla düğmeleriyle.
- Katalog güncellemesi: yeni `dosya_surumu` gelince eski dosyalar çalmaya devam eder; Depolama "Güncelleme var" gösterir; eski sürüm dosyaları güncelleme inince temizlenir.
- Telemetriye okunan âyet ve okuyucu seçimi gitmez; yalnız hata kodu gider.
- **Bitti sayılır:** hata yolları testlerde; uygulama hiçbir ses hatasında çökmez (test).

### A27.9 · Otomatik testler ve cihaz testleri
- `pnpm --filter @mutalaa/player test`, `pnpm --filter @mutalaa/mobile test`, `typecheck`, `lint`; içerik hattı ve Yayınlayıcı testleri.
- Cihaz testleri kullanıcıya bırakılır (CLAUDE.md, çalışma düzeni 3): ekran kapalıyken 10 dakika çalma ve kilit ekranında sure adı ile sonraki/önceki; liste boşluğu (SK-3); 0,75 ve 1,5 hızda perde (SK-2); VBR kayıtta âyet atlaması (SK-1); kesinti ve kulaklık (SS-4); çevrimdışı çalma; kaydın tamamını indirme. Sonuçlar kullanıcı bildirince dokümana işlenir; ölçüm yetersiz çıkarsa `SingleEngine` ya da kendi yerel modülümüz değerlendirilir (araştırma §6).
- **Bitti sayılır:** otomatik testler yeşil; cihaz testleri ilerleme notunda "kullanıcıya bırakıldı".

### A27.10 · Belgelendirme ve kabul
- Araştırma raporu, Ses sistemi, Depolama yöneticisi ve İçerik paketleri koda göre eşitlenir (`/belge-esitle`); karar gereken sapma `/karar` ile.
- `inceleyici`, `arayuz-denetcisi` çalışır; engelleyici bulgu kalmaz.
- **Bitti sayılır:** kabul ölçütleri kanıtlı; ilerleme dosyası güncel.

## Kabul ölçütleri
- [ ] Yerel depoda 9 kaydın 114'er dosyası var; katalogdaki bayt ve sha256 değerleri dosyalarla aynı; `dev` manifestinde `ses-katalog` ve 9 `ses-zaman-*` paketi var.
- [ ] Her kayıtta âyet zamanlaması 6.236 satır ya da eksikler katalogda işaretli; son âyet bitişi dosya süresini aşmıyor (içerik hattı raporu).
- [ ] `pnpm --filter @mutalaa/player test` yeşil; Ses sistemi §5.3'teki her durum ve §5.2'deki her olay en az bir testte geçer; `decideAfterFrame` örneği birebir sağlanır.
- [ ] `packages/player` içinde `react-native` ya da `expo` içe aktarımı yok.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: parça çözücü (yerel, akış, çevrimdışı), indirme işleri ve doğrulama, mini oynatıcı ve Dinleme sayfası, çip önceliği, hata yolları.
- [ ] Uygulama koduna gömülü ses dosyası yok; üçüncü taraf ses sunucusu adresi uygulama kodunda ve paketlerde yok (`grep`).
- [ ] `uv run pytest`, `dotnet test --solution server/Mutalaa.slnx` yeşil; EF göçü testleri yeşil.
- [ ] Cihaz testleri ilerleme notunda "kullanıcıya bırakıldı" ya da kullanıcının sonuçlarıyla.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa ses katalog && uv run mutalaa ses ayna --kayit alafasy-murattal && uv run mutalaa ses zaman --kayit alafasy-murattal)
(cd pipeline && uv run pytest && uv run ruff check . && uv run mypy)
dotnet test --solution server/Mutalaa.slnx
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -o '"ses-[a-z-]*"' | sort -u
curl -sI http://localhost:8333/mutalaa/audio/alafasy-murattal/ | head -1
pnpm --filter @mutalaa/player test && pnpm --filter @mutalaa/player typecheck
grep -rnE "from ['\"](react-native|expo)" packages/player/src || echo "player platformdan bağımsız"
pnpm --filter @mutalaa/mobile test && pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
grep -rnE "mp3quran\.net|tarteel\.ai|everyayah\.com|quranicaudio\.com" apps/mobile/src || echo "uygulamada üçüncü taraf ses adresi yok"
```
Depo yolları ve paket adları A27.2'de kesinleşir; komutlar o zaman düzeltilir.

## Dikkat
- Ses kaynağı izinleri bu yapıyı kısıtlamaz (K-41 madde 10, proje sahibinin kararı); kaynak kayıtlarının `notlar` alanı bunu yazar. Hukuki görüş değildir.
- Ayna dosyaları değişmezdir: yayımlanmış bir `audio/{kayit}/{dosya_surumu}/` klasörü yerinde değiştirilmez, yeni sürüm açılır.
- `data/raw/ses/` büyüktür (9 kayıt için yaklaşık 12–16 GB, kaba tahmin); OneDrive eşitlemesi alım sırasında duraklatılır. `data/` git dışıdır.
- Kur'an metni ve üst verisi elle yazılmaz; âyet listesi `core`'dan okunur. `ses-test` sentetik tondur, Kur'an tilavetine benzetilmez.
- react-native-track-player ve expo-av kullanılmaz (K-28, K-30). Ses kendiliğinden başlamaz; her çalmanın görünür bir durdurma düğmesi vardır. Mikrofon izni kapalıdır.
- Commit kapsamları `pipeline`, `server`, `publisher`, `player`, `mobile`.

## İnsan adımları
- İ-07 · gerekmiyor (K-40, K-41): hafız sesi alınmayacak.
- İ-18 · Canlı içerik deposu: ayna dosyaları `internal` ve `public` derlemelerde canlı depodan sunulur; yerel geliştirme SeaweedFS ile beklemeden yürür. Depo ücretliyse tahmini maliyet kullanıcıya gösterilir (kural 11).
- İ-15 · Apple Developer hesabı: yalnız iOS cihaz denemesi için.
- Cihaz testleri kullanıcıya bırakılır (A27.9).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ses/`, kaynak kayıtları, `ses-test` fikstürü
- Editoryal veritabanı ses tabloları ve EF göçü; Yayınlayıcı `ses-katalog`, `ses-zaman-{kayit}` paketleri ve ayna yüklemesi
- `packages/player/`: `engine.ts`, `decide.ts`, `timing.ts`, `frameTimer.ts`, `machine.ts`, testler
- `apps/mobile/src/features/audio/`: `session.ts`, `engine/playlist.ts`, `engine/single.ts`, `engine/index.ts`, `resolveTracks.ts`, `usePlayback.ts`, ses indirme işleri, `MiniPlayer`, `PlayerSheet`, `ReciterRow`
- `apps/mobile/src/features/reader/hooks/useFollowPlayback.ts`, `FollowChip`; eylem çubuğunda "Dinle"

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A27-ses-sistemi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md) · Önceki: [A26](./A26-mushaf-a.md) · Sonraki: [A28](./A28-arama-ekrani.md)
