# A27 · Ses sistemi (expo-audio + XState, `ses-test` fikstürü)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-18](../../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** [İ-07](../06-insan-adimlari.md) (yalnız gerçek hafız sesi için; aşamayı durdurmaz)
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `lisans-denetcisi` · `hat-gelistirici` ve `sunucu-gelistirici` (yalnız A27.3) · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `lisans-kapisi` · `paket-yayini` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A27`

## Amaç
Tilavet tek oynatıcılı bir ses motoru ve XState durum makinesiyle çalınır: âyet, aralık, sayfa, sure ve cüz; tekrar, âyet arası bekleme, hız, uyku zamanlayıcısı, arka plan ve kilit ekranı, âyet ve kelime vurgusu, takip modu. Önce karar işlevi ve makine motorsuz testlerle yazılır, sonra expo-audio motoru, mini oynatıcı ve Dinleme sayfası. Bütün denemeler sentetik `ses-test` fikstürüyle yapılır; gerçek hafız sesi yalnız yazılı izinle (İ-07) girer.

## Okunacak belgeler
- [Ses sistemi](../../06-mobil/02-ses-sistemi.md): tamamı
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (mini oynatıcı, `ChipSlot`), §5 (oynatıcı aktörü, `usePlayback`), §8 (`USER_SCROLLED`), §10 (`mealSesi`)
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §9 kural 9, §10 Sesli takip
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §6 (`MiniPlayer`, `PlayerSheet`, `ReciterRow`, `ChipSlot`, `FollowChip`)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.5 `ses-{hafiz}` · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §9.1 `audio_timing`
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §3, §8, §9 (Ses çal akışı)
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.7 · [Riskler](../../08-yol-haritasi/03-riskler.md): R-20

## Kapsam
**Yapılır**
- `packages/player`: motor arayüzü, `decideAfterItem`, `activeWordAt`, XState makinesi ve geçiş testleri.
- `ses-test` fikstürü (A13 bu aşamaya bıraktı).
- `SteppedEngine` (expo-audio), ses oturumu, kuyruk çözücü, uyku zamanlayıcısı.
- `MiniPlayer`, `PlayerSheet` (Dinleme), âyet ve kelime vurgusu, takip modu ve "Okunan âyete dön" çipi; eylem çubuğuna "Dinle".

**Yapılmaz**
- Sure ve cüz ses indirme, hafız başına silme ve indirme kuyruğu: [A29](./A29-kutuphane-ve-depolama.md).
- Kur'an + meal dönüşümü (v1.x; `mealSesi` kapalı); kesintisiz liste motoru `PlaylistEngine` (SDK 58 sonrası, Sonra); kelime telaffuz sesi (Açık soru); QF ses akışı (Açık soru, açılmaz).
- Maestro "Ses çal" akışı (A33); Kaynaklar ve lisanslar ekranındaki hafız ve quran-align atfı (A32); gerçek hafız paketleri (İ-07 ve Kurul onayı).

## Adımlar
### A27.1 · Doğrulamalar ve seçenek kararı
- `arastirmaci`, seçilen SDK'da expo-audio: `createAudioPlayer` imzası ve `updateInterval`, `replace()`, `setPlaybackRate` ve `shouldCorrectPitch`, `setActiveForLockScreen`, `updateLockScreenMetadata`, `clearLockScreenControls`, `playbackStatusUpdate` alanları (SS-1); `setAudioModeAsync` seçenekleri ve `doNotMix` ile `doNotMixPersistent` farkı (SS-4); eklentinin `enableBackgroundPlayback` seçeneği.
- XState v5: `createActor`, `fromCallback`, `fromPromise`, adlı gecikmeyle `after`; `@xstate/react` `useSelector`. Sürüm kilit dosyasına yazılır.
- Belgede yazmayan ve cihazda ölçülecek olanlar A27.6'ya not edilir: `replace()` sonrasında kilit ekranı bağı ve "sonraki/önceki" olaylarının JS'e ulaşması (SS-2), âyetler arası boşluk (SS-3), kesinti sonrası devam sinyali (SS-4), arka planda JS zamanlayıcıları.
- Uyku ve bekleme seçenekleri belgelerde eşitlendi (19 Ekim 2026): uyku zamanlayıcısı 15, 30, 60 dk ve "aralık bitince" (`aralik_sonu`; Okuma deneyimi §10, Ses sistemi §9); bekleme çarpanı 0 (kapalı), 0,5, 1, 1,5, 2 (Ses sistemi §5.1, Okuma deneyimi §10).
- **Bitti sayılır:** sonuçlar dokümanda; imza farkı varsa motor taslağı ona göre düzeltilmiş; seçenek kararı yazılı.

### A27.2 · `packages/player`: önce testler
- Paket `packages/player`; dış bağımlılık yalnız `xstate` (Teknoloji yığını §2.6). `react-native` ve `expo-*` içe aktarılmaz.
- Dosyalar: `engine.ts` (`EngineItem`, `EngineEvent`, `AudioEngine`; Ses sistemi §4), `decide.ts` (`decideAfterItem`, §5.4), `timing.ts` (`activeWordAt(segments, tMs)`, ikili arama), `machine.ts` (`createPlayerMachine(engine, resolveQueue, saved)`, §5.3 ve §5.5).
- Testler koddan önce yazılır (Vitest, sahte motor, Vitest sahte zamanlayıcıları):
  - Karar: belgedeki örnek (`repeatEach: 2`, `delayMultiplier: 1`, `rate: 1`, 10 saniyelik âyet → ilk karar `{ type: 'gap', ms: 10000, then: { type: 'replay' } }`, ikincisi sonraki âyete ilerleyen bekleme); meal öğesinden sonra bekleme yok; `repeatRange: 0` sınırsız; uyku `aralik_sonu` (aralık yeniden başlayacakken durur).
  - Geçişler: `idle → resolving → active`; `boot` autoplay'e göre; `PAUSE`, `PLAY`, `TOGGLE`; `ENGINE.BUFFERING` → `buffering` → `ENGINE.READY`; tamponda 20 saniye → `error`; `ENGINE.ITEM_END` → `routing` → tekrar, ilerleme, `gap`, `paused`, `ended`; `gap` içinde `PAUSE` ve `PLAY`; `ENGINE.INTERRUPTED` → `interrupted` → `shouldResume`'a göre; `ENGINE.EXTERNAL_PAUSE` → `paused` (kendiliğinden devam yok); `ENGINE.ERROR` → `error` → `RETRY`, `SKIP`, `STOP`; `SET_RECITER` aynı âyetten yeniden çözer; `PACK_REMOVED` → `idle`; `NEXT_AYAH`, `SEEK_AYAH`; `ended` + `PLAY` aralığı baştan başlatır; `USER_SCROLLED` takibi kapatır, `RETURN_TO_CURRENT` açar.
  - `activeWordAt`: bölüt sınırları; hız değişse de aynı sonuç (ortam zamanı).
- Test stratejisi §3'teki örnek test Ses sistemi §5'teki adları kullanır (`LOAD`, `ENGINE.ITEM_END`, `repeatEach`, `createPlayerMachine`).
- **Bitti sayılır:** `pnpm --filter @mutalaa/player test` yeşil; her durum ve olay en az bir testte geçer.

### A27.3 · `ses-test` fikstürü
- A13 `ses-*` paketlerini ve `ses-test` fikstürünü bu aşamaya bıraktı. Yerel `dev` manifestinde `ses-test` zaten varsa adım atlanır; yoksa üretilir:
  - Kaynak kaydı (`hat-gelistirici`): A13'teki fikstürler gibi `pipeline/sources/` altında; slug `test-ses` (paket kimliği `ses-test` kalır; Test stratejisi §9), `license_status = serbest`, açıklaması "Sentetik ton; Kur'an tilaveti değildir". P-12 gereği `public`'e hiç girmez; `dev` ve `internal`'a girer (Test stratejisi §9).
  - Ses: Fâtiha'nın âyetleri için (âyet listesi `core`'dan) kısa sentetik ton dosyaları betikle üretilir; süreler birkaç saniyedir. Ses biçimi, `audio_timing.file` değeri ve indirme birimi `/karar` ile yazılır: Ses sistemi §3 cihazda `audio/{hafiz}/{sss}{aaa}.mp3` der, Editoryal veritabanı §9.1 `002/255.mp3` örneği verir, İçerik paketleri §3.5 sure başına tek adresli `audio_part` tanımlar, Depolama yöneticisi §4 ses işlerini dosya düzeyinde sürdürür. MP3 kodlayıcı yoksa WAV denenir; expo-audio'nun WAV desteği `arastirmaci` ile doğrulanır.
  - Zamanlama: her dosya için sentetik `audio_timing` satırı ve kelime bölütleri; değerler betikten gelir.
  - Paket (`sunucu-gelistirici`): Yayınlayıcı `ses-test` dizin paketini (`audio_timing`, `audio_part`) ve ses dosyalarını yerel depoya yükler; ses paketi desteği yoksa İçerik paketleri §3.5'e göre eklenir. `publish --flavor dev`.
- **Bitti sayılır:** `dev` manifestinde `ses-test` var; ses dosyaları yerel depodan HTTP ile alınabiliyor; `test-ses` kaynağı `public` kapı raporunda "girmedi".

### A27.4 · Motor, oturum ve kuyruk çözücü
- `src/features/audio/session.ts`: `setAudioModeAsync` (`playsInSilentMode`, `shouldPlayInBackground`, `interruptionMode: 'doNotMixPersistent'`; A27.1 sonucuna göre).
- `src/features/audio/engine/stepped.ts` Ses sistemi §4'teki gibidir: tek `AudioPlayer`, her öğede `replace()`, her âyette kilit ekranı üst verisi (âyet adresi, hafız adı, "Mütâlaa"), sonraki ve önceki açık, ileri ve geri sarma kapalı. İlerleme makineye girmez; 100 ms'de bir `usePlayback` deposuna yazılır.
- Oynatıcı aktörü uygulama kökünde bir kez oluşur ve gezinmeden etkilenmez. Uygulama açılışta kendiliğinden çalmaz.
- Kuyruk çözücü: hafızın `ses-{hafiz}` paketi derleme türünde görünür mü (`isPackVisible`); âyet listesi `core`'dan (kapsam: âyet, aralık, sure, sayfa, cüz); kaynak önce `device.db` `audio_file`'daki yerel dosya, yoksa izin varsa akış adresi; ikisi de yoksa `not_downloaded` ile `error` ve "Bu sure indirilmedi · İndir" (indirme A29'da). Akış izninin yeri Açık sorudur (SS-10); `ses-test` için akış açık sayılır (öneri). Akışta sonraki iki âyet `Paths.cache` altına ön yüklenir.
- Uyku zamanlayıcısının dakika seçeneği makinenin dışındadır: süre dolunca ses 5 saniyede kısılır, `PAUSE` gönderilir, ses düzeyi geri gelir. "Aralık bitince" `decideAfterItem` içinde çözülür.
- **Bitti sayılır:** kuyruk çözücü testleri yeşil (görünmeyen hafız, yerel dosya, akış, `not_downloaded`); uyku zamanlayıcısı testi yeşil.

### A27.5 · Mini oynatıcı, Dinleme sayfası, vurgu ve takip
- `MiniPlayer` A21'in `MiniPlayerSlot`'unda: Oynat/Duraklat düğmesi, "Bakara · 255" biçiminde adres (sure adı yoksa "2:255"; `mobil-ekran`, sure adı kuralı), hafız adı, aralık ilerleme halkası (ilerleme yazıyla da okunur). Çalma yoksa gizlidir.
- `PlayerSheet` (Dinleme) tek `SheetHost` içinde %90'da açılır: hafız listesi ve 5 saniyelik ön dinleme (ayrı oynatıcı, kilit ekranını almaz), kapsam, her âyeti ×1, 2, 3, 5, 10, aralığı ×1, 2, 3, 5, 10, âyet arası bekleme, hız 0,75–1,5, uyku zamanlayıcısı, "Okunan âyete git". Seçenek listeleri A27.1'dekidir (Okuma deneyimi §10). Kur'an + meal satırı gizlidir (`mealSesi`, v1.x). İzinli hafız yoksa "Bu sürümde izinli hafız sesi yok" yazar ve mini oynatıcı görünmez.
- Vurgu: âyette zemin tonu, kelimede zemin ve alt çizgi; kelime vurgusu yalnız `hasWordTiming` hafızlarda. Dar abonelikle yalnız durumu değişen kelime yeniden çizilir. `testID`: `etkin-ayet-q:1:2` biçimi.
- Takip: `useFollowPlayback` (Ses sistemi §7); A24'teki sürükleme bağlantı noktası `USER_SCROLLED` gönderir. Zincir yokken ve takip kapalıyken `ChipSlot`'ta `FollowChip` ("Okunan âyete dön" ve âyet adresi) çıkar. Atlama zinciri önceliklidir; iki çip birlikte görünmez.
- A25'in eylem çubuğuna "Dinle" eklenir. Tekrar, bekleme, hız ve takip tercihleri MMKV'de durur. `MiniPlayer` ve `PlayerSheet` Tasarım vitrinine eklenir.
- **Bitti sayılır:** RNTL testleri yeşil: mini oynatıcı görünürlüğü, izinli hafız yokken metin, çip önceliği, etkin âyet `testID`'si.

### A27.6 · Cihaz denetimi
- Android geliştirme derlemesinde `ses-test` ile Fâtiha'dan çalınır: etkin âyet işareti `etkin-ayet-q:1:2` 20 saniye içinde görünür (görüntü).
- Ekran kapalıyken çalma 4 dakika sürer; kilit ekranında âyet ve hafız adı görünür, sonraki ve önceki çalışır (R-20; SS-2). Âyetler arası boşluk (SS-3), kesinti sonrası davranış (SS-4) ve arka planda uyku zamanlayıcısı ölçülür ve dokümana işlenir.
- iOS denemesi Apple Developer hesabı (İ-15) varsa EAS iOS geliştirme derlemesiyle yapılır; yoksa A33'e kalır. Her EAS derlemesi kullanıcı onayı ister.
- `lisans-denetcisi`: `internal` bayrağıyla `bekliyor` hafız listede yok; `ses-test` paketi (kaynağı `test-ses`) `public` manifestinde yok.
- **Bitti sayılır:** görüntüler `.tmp/a27/` altında; ölçümler dokümanda; raporlar temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/player test` yeşil; Ses sistemi §5.3'teki her durum ve §5.2'deki her olay en az bir testte geçer; belgedeki `decideAfterItem` örneği birebir sağlanır.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: kuyruk çözücü, uyku zamanlayıcısı, mini oynatıcı ve Dinleme sayfası, çip önceliği.
- [ ] `packages/player` içinde `react-native` ya da `expo` içe aktarımı yok.
- [ ] Yerel `dev` manifestinde `ses-test` var; `public` kapı raporunda `test-ses` kaynağı "girmedi".
- [ ] Cihazda `etkin-ayet-q:1:2` 20 saniye içinde görünür; ekran kapalıyken 4 dakika çalma sürer (görüntü ve not).
- [ ] Uyku ve bekleme seçenekleri A27.1'deki listeyle uygulandı (test); SS-2, SS-3, SS-4 ölçümleri dokümanda.
- [ ] Gerçek hafız sesi depoya ya da pakete girmedi; `arayuz-denetcisi` ve `lisans-denetcisi` raporlarında engelleyici bulgu yok.

## Doğrulama
```bash
pnpm --filter @mutalaa/player test
pnpm --filter @mutalaa/player typecheck
grep -rnE "from ['\"](react-native|expo)" packages/player/src || echo "player platformdan bağımsız"
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -o '"ses-test"'
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
mkdir -p .tmp/a27
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/1/1"
adb exec-out screencap -p > .tmp/a27/calma-q-1-1.png
```
`publish --dry-run` yalnız kapı raporu üretir; Kurul onayı olmayan paketler yüzünden `2` (kapı reddi) koduyla çıkabilir. Raporda `test-` önekli kaynağın P-12 ile girmediği okunur. Çalmayı başlatmak için mini oynatıcıdaki "Oynat"a `mobil-ekran` becerisindeki dokunma yöntemiyle basılır.

## Dikkat
- Gerçek hafız kaydı yazılı izin olmadan indirilmez, işlenmez, depoya ya da pakete konmaz (İ-07; lisans defteri §1 iç kullanım kuralı). Sesli Kur'an Kurul onayına tabidir.
- `ses-test` sentetik tondur; Kur'an tilavetine benzetilmez ve öyle adlandırılmaz. Fâtiha'nın âyet sayısı gibi üst veri elle yazılmaz, `core`'dan okunur.
- react-native-track-player ve expo-av kullanılmaz (K-28, K-30).
- Android'de kilit ekranı kontrolü yoksa ses yaklaşık 3 dakikada kesilir; v1 tek oynatıcılı `SteppedEngine` ile çıkar (R-20).
- Ses kendiliğinden başlamaz; her çalmanın görünür bir durdurma düğmesi vardır. Hareketi Azalt açıkken takip yumuşak kaydırma yerine doğrudan atlar.
- Mikrofon izni ve kayıt kapalıdır (`expo-audio` eklentisi).
- Telemetriye okunan âyet ve hafız seçimi gitmez; hata kodu gider (Mobil mimari §12).
- Commit kapsamları `player`, `mobile`, gerekirse `pipeline` ve `publisher`.

## İnsan adımları
- İ-07 · Hafız görüşmeleri ve yazılı izin: bu aşamayı durdurmaz; gerçek hafız paketi ancak izin ve Kurul onayıyla, ayrı bir işte eklenir.
- İ-15 · Apple Developer hesabı: yalnız iOS cihaz denemesi için (A27.6). Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/player/`: `engine.ts`, `decide.ts`, `timing.ts`, `machine.ts`, testler
- `apps/mobile/src/features/audio/`: `session.ts`, `engine/stepped.ts`, kuyruk çözücü, uyku zamanlayıcısı, `MiniPlayer`, `PlayerSheet`, `ReciterRow`, `usePlayback`
- `apps/mobile/src/features/reader/hooks/useFollowPlayback.ts`, `FollowChip`; eylem çubuğunda "Dinle"; Tasarım vitrini ekleri
- `ses-test` fikstürü: kaynak kaydı, ton üreteci, `audio_timing` satırları, Yayınlayıcı ses paketi desteği
- Karar defterinde ses yol düzeni, uyku ve bekleme seçenekleri; `.tmp/a27/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A27-ses-sistemi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A26](./A26-mushaf-a.md) · Sonraki: [A28](./A28-arama-ekrani.md)
