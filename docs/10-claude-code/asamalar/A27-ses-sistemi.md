# A27 · Ses sistemi: hazır kayıtlar, ayna, çevrimiçi öncelikli dinleme, isteğe bağlı indirme

> **Sürüm:** 2.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-40](../../00-ozet/02-karar-defteri.md#k-40--ses-kaynağı-hazır-dijital-tilavet-kaynakları) · [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses) · [K-18](../../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · [A13](./A13-yayinlayici-ve-kalite-kapisi.md) · [A29](./A29-kutuphane-ve-depolama.md) (A29.4; yalnız ses indirmesi için) · **İnsan adımı:** İ-18 (canlı ayna) · İ-15 (iOS denemesi)
> **Ajanlar:** `hat-gelistirici` · `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `icerik-hatti` · `ef-goc` · `paket-yayini` · `mobil-ekran` · **Tahmini oturum:** 5–7
> **Başlat:** `/asama A27`

## Amaç
Mütâlaa'da en çok dinlenen okuyucuların hazır kayıtları indirmeden çevrimiçi dinlenir; istenen sure ya da kaydın bütün Kur'an'ı cihaza kalıcı olarak indirilir ve çevrimdışı çalar. Ses sure başına tek dosyadır; âyetler dosya içinde karedir ve kayda bağlı zamanlamayla bulunur. Âyet âyet ve kesintisiz sure dinleme, âyet tekrarı, sonraki sureye geçiş ve Nâs kuralı tek motorla çalışır; çalan âyet okuyucuda vurgulanır. Dosyaları Claude Code kaynaktan bir kez indirir (A27.0), içerik hattı alır ve ölçer, Yayınlayıcı kendi depomuzdan değişmez adreslerle sunar. Dayanak: [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md), karar: [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme).

## Okunacak belgeler
- [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md): tamamı · [Ses sistemi](../../06-mobil/02-ses-sistemi.md): tamamı
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §2 `device.db`, §3 dosya düzeni, §4 kuyruk, §5 bütünlük
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §4 (mini oynatıcı, `ChipSlot`), §5 (oynatıcı aktörü, `usePlayback`), §8 (`USER_SCROLLED`), §10 (bayraklar)
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §9 kural 9, §10 Sesli takip · [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §6 (`MiniPlayer`, `PlayerSheet`, `ReciterRow`, `ChipSlot`, `FollowChip`)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.5 · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §9.1 `audio_timing` · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4–§8
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §3, §8, §9 · [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.7 (ses ve zamanlama), §5 (yeni kaynak ekleme)

## Kapsam
**Yapılır**
- Tedarik (A27.0): kaynak adreslerinin doğrulanması; 9 kaydın 1.026 sure dosyasının ve QUD v4.0.0 katalog ve zamanlama arşivlerinin `data/gelen/` altına indirilmesi; dört kaynak kaydının açılması.
- İçerik hattında ses kataloğu ve ayna: QUD v4.0.0 ve MP3Quran okuyucuları, indirilen dosyaların alınması ve ölçülmesi, `ses-katalog` ve `ses-zaman-{kayit}` paketleri, ayna dosyalarının içerik deposuna yüklenmesi.
- `packages/player`: dosya × kare motor arayüzü, `decideAfterFrame`, zamanlama araması, XState makinesi ve testleri.
- Mobil: `PlaylistEngine`, `SingleEngine`, ses oturumu, otomatik kaynak çözücü, okuyucu seçici, mini oynatıcı, Dinleme sayfası, âyet vurgusu ve takip modu, eylem çubuğunda "Dinle".
- Ses indirme işleri A29'un kuyruğunda (tek sure ve kaydın tamamı); çevrimdışı çalma.
- v1 kayıtları: `alafasy-murattal`, `maher-murattal`, `sudais-murattal`, `ghamdi-murattal`, `abdulbasit-murattal`, `abdulbasit-mucevved`, `husary-murattal`, `minshawi-murattal`, `minshawi-mucevved`.

**Yapılmaz**
- Kelime takibinin açılması (`kelimeTakibi` bayrağı kapalı kalır; eşleme doğrulanınca ayrı iş), Kur'an + meal dönüşümü (v1.x, `mealSesi` kapalı), kelime telaffuz sesi.
- Genel paket indirme kuyruğunun kendisi ve Depolama ekranı ([A29](./A29-kutuphane-ve-depolama.md)); bu aşama kuyruğa ses işi ekler.
- Ayarlar › Kaynaklar ekranının son metni (A32), Maestro "Ses çal" akışı (A33).

## Tedarik
Adresler 3 Kasım 2026'da yeniden açıldı (HTTP 200) ve 1.026 sure dosyasının tamamı yeniden ölçüldü; bayt, ETag ve son değişiklik tarihi 2 Kasım 2026 ölçümüyle aynı çıktı (fark 0). Seçim ölçütü eksiksizlik (9 kayıt × 114 sure dosyası, kayıt başına 6.236 âyet zamanlaması), biçim, sürümün sabitlenebilmesi ve doğrudan alınabilirliktir ([K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1 ve 2). Kaynakların hiçbiri başvuru, giriş ya da anahtar istemez. Karşılaştırma ve elenen adaylar: [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md) §3.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Sure ses dosyaları, MP3Quran CDN'indeki 4 kayıt: `alafasy-murattal`, `husary-murattal`, `minshawi-murattal`, `minshawi-mucevved` | MP3Quran, `https://cdn.mp3quran.net/audio/<okuyucu>/r<N>/<sss>.mp3`: `mishary-alafasy/r1` (moshaf 123), `mahmoud-husary/r1` (118), `muhammad-minshawi/r1` (112), `muhammad-minshawi/r2` (113). MP3, sure başına tek dosya, 128 kbps (QUD kataloğu: üçü `cbr`, Minshawi mücevved `mixed`). Tanıtım sayfası `https://www.mp3quran.net/eng/api`; adres listesi QUD `catalog.json` `chapter_urls` alanındadır | `curl -sL` ile doğrudan GET (anahtar, giriş ya da özel başlık yok; `Accept-Ranges: bytes`, kesilen indirme `curl -C -` ile sürer); en çok 2 eşzamanlı istek; `data/gelen/ses-mp3quran/<YYYY-AA-GG>/<kayit>/<sss>.mp3` | 456 adres HTTP 200 (3 Kasım 2026), hepsi `audio/mpeg`; toplam 10.664.402.058 bayt; en büyük dosya 293.492.927 bayt (Minshawi mücevved, Bakara). 2 Kasım 2026 ölçümüyle bayt, ETag ve son değişiklik tarihi aynı | `/download/audio/` önekli biçim (aynı dosya, aynı ETag; 3 Kasım 2026'da Fâtiha için yeniden denendi: iki biçim de HTTP 200 ve 837.734 bayt) |
| Sure ses dosyaları, Tarteel CDN'indeki 5 kayıt: `maher-murattal`, `sudais-murattal`, `ghamdi-murattal`, `abdulbasit-murattal`, `abdulbasit-mucevved` | Tarteel CDN, `https://audio-cdn.tarteel.ai/quran/surah/<okuyucu>/<tarz>/mp3/<sss>.mp3`: `maherAlMuaiqly/murattal`, `abdulrahmanAlSudais/murattal`, `ghamadi/murattal`, `abdulBasit/murattal`, `abdulBasit/mujawwad`. MP3, sure başına tek dosya, 128 kbps `cbr` (QUD kataloğu). Adresler QUD `catalog.json` `chapter_urls` alanındadır; kayıt sayfası `https://qul.tarteel.ai/resources/recitation` (HTTP 200) | `curl -sL` ile doğrudan GET (`Accept-Ranges: bytes`); en çok 2 eşzamanlı istek; `data/gelen/ses-tarteel-cdn/<YYYY-AA-GG>/<kayit>/<sss>.mp3`; uygulama bu adrese hiçbir zaman bağlanmaz | 570 adres HTTP 200 (3 Kasım 2026), hepsi `audio/mpeg`; toplam 9.074.309.134 bayt. 2 Kasım 2026 ölçümüyle bayt, ETag ve son değişiklik tarihi aynı | Aynı okuyucunun MP3Quran kaydı, dosya ve zamanlama birlikte MP3Quran'dan: Sudais (moshaf 54), Ghamdi (30), Abdul Basit murattal (53) ve mücevved (51). Maher murattal (102) için MP3Quran'da zamanlama yok, yedek yok |
| Katalog ve zamanlama: âyet, kelime ve özel bölüt (istiâze, besmele) zamanlaması, 9 kayıt | Quranic Universal Audio (QUD) v4.0.0, 24 Ekim 2026; `https://github.com/QUD-Technologies/quranic-universal-audio/releases/tag/v4.0.0`; etiket commit'i `ffdff3e3a4568275022a98d1716905fd6cc22672`. Varlıklar: `manifest.json` (53.696 bayt), `catalog.json` (856.815), `surah_info.json` (399.552) ve kayıt başına `<slug>.zip` (v1: 9 zip, 616.784–702.282 bayt; her biri `catalog.json`, `specials.json`, `verse_timestamps.json.gz`, `word_timestamps.json.gz` içerir) | `https://github.com/QUD-Technologies/quranic-universal-audio/releases/download/v4.0.0/<varlık>` doğrudan GET (GitHub API kullanılmaz); `data/gelen/zamanlama-qud/<YYYY-AA-GG>/`. Kaynağın kendi bildirimi `NOTICE.md` (2.268 bayt) etiket commit'inden alınır ve `zamanlama-qud` kaydına bayt bayt yazılır | Dokuz zip'in her birinde 6.236 benzersiz âyet satırı (`canonical`), 78.928–88.419 kelime satırı, kelimesiz satır 0; `catalog.json` `coverage`: 6.236 âyet, 114 sure, eksik sure yok. Zip sha256 değerleri sürümün `digest` alanlarından alınan listeyle (A27.0) ve 3 Kasım 2026'da yeniden indirilen kopyalarla aynı; varlık boyutları aynı. `git ls-remote --tags` (3 Kasım 2026): en yeni etiket `v4.0.0` | MP3Quran `ayat_timing` (yalnız âyet düzeyi) |
| Yedek âyet zamanlaması (QUD zip'i eksik çıkarsa) | MP3Quran `https://www.mp3quran.net/api/v3/ayat_timing/reads` (115 okuma), `soar?read=<moshaf>` ve `?surah=<n>&read=<moshaf>`; alanlar `ayah`, `start_time`, `end_time`; kelime alanı yok. `https://mp3quran.net/...` adresi 301 ile `www.mp3quran.net`'e yönlenir | `curl -sL` ile anahtarsız GET, JSON; `data/gelen/zamanlama-mp3quran/<YYYY-AA-GG>/` (`reads.json` ve 9 `soar-<id>.json`; sure başına yanıtlar yalnız yedek gerekince) | 3 Kasım 2026: `soar` listesi 114 sure olan okumalar 123, 118, 112, 54, 30, 53 ve 51; 102 (Maher murattal) ve 113 (Minshawi mücevved) için liste boş, zamanlama yok | QUD zip'leri (birincil) |
| Okuyucu ve kayıt üst verisi (ad, Arapça ad, rivayet, tarz, kanal) | QUD `catalog.json` (`name_en`, `name_ar`, `riwayah`, `style`, `channel`; 9 kayıt `hafs_an_asim`) ve MP3Quran `https://www.mp3quran.net/api/v3/reciters?language=eng` (244 okuyucu, 299 moshaf; `server` alanı dosya klasörüdür) | `curl -sL` ile anahtarsız GET, JSON; `data/gelen/ses-mp3quran/<YYYY-AA-GG>/reciters.json` | 9 kayıtta alanlar dolu; MP3Quran `server` klasörleri (9 moshaf, 3 Kasım 2026) yukarıdaki adreslerle aynı. Mücevved kayıtlarında MP3Quran `rewaya_id` iki uçta tutarsız: rivayet QUD `riwayah` alanından alınır | QUD `catalog.json` tek başına |
| MP3 süre, bit hızı ve bit hızı türü ölçümü | Python `mutagen` 1.48.1 (PyPI, 25 Haziran 2026; `py3-none-any` tekerleği, Python `>=3.10,<4`): `MP3(yol).info.bitrate`, `.bitrate_mode`, `.sample_rate`, `.length`. Xing/Info başlığı olmayan dosyada `bitrate_mode` `UNKNOWN` döner; tür kayıt düzeyinde QUD `audio.bitrate_mode` ile (8 kayıt `cbr`, Minshawi mücevved `mixed`) karşılaştırılır. `mixed` kayıtta süre bayt ÷ bit hızı ile kestirilemez (kanıt sütunu): süre, MP3 çerçeve başlıklarını tarayan kendi bağımsız betiğimizle (yaklaşık 40 satır) ölçülür | `uv add mutagen` (`pipeline/pyproject.toml` bağımlılıkları); çerçeve taraması `pipeline/src/mutalaa_pipeline/ses/` içinde | 3 Kasım 2026'da üç örnek dosyada (Fâtiha sure dosyaları) süre ve bit hızı okundu: 51,931 sn, 32,418 sn ve 177,432 sn; üçü de 128 kbps, 44,1 kHz, stereo; mod yalnız Maher dosyasında `CBR`, ötekilerde `UNKNOWN`; üç dosyanın MD5 değeri HEAD yanıtındaki ETag ile aynı. QUD son âyet bitişi ile bayt × 8 ÷ 128.000 kestirimi sure sure karşılaştırıldı: sekiz `cbr` kayıtta bitiş hiçbir surede kestirimi aşmıyor (fark −210 ile −0,06 sn; ortalama bit hızı medyanı 128,0–129,0 kbps); Minshawi mücevved'de ortalama bit hızı medyanı 192,1 kbps (en düşük 64,2, en yüksek 614,2) ve bitişin kestirimi aştığı en büyük fark 1.525 sn | `ffprobe` (makinede kurulu değil) çerçeve taramasının çapraz denetimi olarak |
| Mobil ses ve indirme kitaplıkları | `expo-audio` ~58.0.11 (`AudioPlaylist`, `useAudioPlaylist`; kilit ekranı denetimi oynatma listesiyle, değişiklik günlüğü 58.0.0, 10 Eylül 2026), `expo-file-system` ~58.0.13 (`File.createDownloadTask(url, hedef, seçenekler)`; `DownloadTask` `pause()`, `savable()` ve `DownloadTask.fromSavable()` ile duraklatma ve sürdürme; `file.digest('SHA-256')` küçük harfli onaltılık özet verir), `xstate` 5.33.3. Ağ durumu A23'ün `src/lib/network.ts` modülünden okunur | `npx expo install expo-audio expo-file-system` (A21 iskeleti; SDK 58 uyumlu sürümü seçer); `pnpm add xstate@5` (`packages/player`) | npm `latest`: `expo-audio` 58.0.11, `expo-file-system` 58.0.13, `xstate` 5.33.3; `expo` 58.0.22 paketinin `bundledNativeModules.json` dosyası `~58.0.11` ve `~58.0.13` verir (3 Kasım 2026); API adları paketlerin `build/*.d.ts` dosyalarında doğrulandı | `react-native-audio-api` (0.x); kendi Media3/AVPlayer modülümüz (expo-audio cihaz ölçümünde yetersiz kalırsa, A27.9) |
| iOS'ta indirilen seslerin iCloud yedeğinden dışlanması (SK-7) | Hazır yapı bulunamadı: `expo-file-system` 58.0.13 paketinde (242 dosya; TypeScript, Swift ve Kotlin kaynakları dahil) yedek dışlama geçmiyor, `expo-modules-core` 58.0.29 içinde `NSURLIsExcludedFromBackupKey` yok, npm aramaları (3 sorgu, 3 Kasım 2026) ilgili paket vermedi (`react-native-fs` son sürümü Mayıs 2022). Seçenek: `expo-modules-core` 58.0.29 ile küçük yerel modül (`NSURLIsExcludedFromBackupKey`) | Karar ve gerekirse modül A27.6'da | iOS cihazda yedek boyutu ölçümü kullanıcıya bırakılır (A27.9) | Yedeğe girmeyi kabul |
| Test sesi `test-ses` (sentetik ton; Kur'an tilavetine benzetilmez) | Kendimiz üretiriz: `lameenc` 1.9.0 (PyPI, 15 Ekim 2026; LAME MP3 kodlayıcısı; Python 3.13 için `win_amd64` ve `manylinux2014_x86_64` tekerlekleri var); `ffmpeg` ve `lame` makinede kurulu değil | `uv add --dev lameenc` (`pipeline` dev grubu); belirlenimci betik `data/` altında üretir | 3 kısa sure dosyası; kare sınırları betikte bilinen değerlerde, `ses ayna` ölçümüyle tutuyor (A27.2) | Python `wave` ile WAV (MP3 ölçümü yapılmaz) |

**Kendimiz yapacağımız işler:** QUD ve MP3Quran okuyucuları, ayna alımı ve ölçüm komutları (`mutalaa ses katalog`, `ses ayna`, `ses zaman`), MP3 çerçeve başlığı taraması (süre ölçümü), editoryal veritabanı ses tabloları, `ses-katalog` ve `ses-zaman-{kayit}` paketleri, `packages/player` (kare motoru, `decideAfterFrame`, XState makinesi), `PlaylistEngine` ve `SingleEngine` sargıları, ses indirme işleri (A29 kuyruğunda), Dinleme sayfası ve âyet vurgusu. Âyet düzeyinde tekrar, aralık ve Nâs kuralı için expo-audio üstüne hazır kitaplık bulunmadı (araştırma §6).

## Adımlar

### A27.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` Tedarik tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular ve sonuçları rapora yazar:
  - MP3Quran: API adresi `https://www.mp3quran.net/api/v3/...` (`mp3quran.net` adresi 301 ile oraya yönlenir, `curl -L` gerekir); CDN'de `/audio/` ve `/download/audio/` önekli iki biçim aynı dosyayı verir (SK-8).
  - Tarteel CDN: adresler QUD `catalog.json` `chapter_urls` alanından gelir; kalıp `https://audio-cdn.tarteel.ai/quran/surah/<okuyucu>/<tarz>/mp3/<sss>.mp3`.
  - QUD: `git ls-remote --tags https://github.com/QUD-Technologies/quranic-universal-audio.git`. `v4.0.0`'dan yeni etiket varsa katalog ve zip özetleri yeniden ölçülür; kullanılacak sürüm rapora yazılır ve K-41'deki sürüm ifadesi `/karar` ile güncellenir.
  - Kitaplıklar: `expo-audio` ve `expo-file-system` için npm `dist-tags` ve Expo SDK 58 `bundledNativeModules.json`; `xstate` için npm; `mutagen` ve `lameenc` için PyPI (Windows ve CI Linux tekerlekleri dahil).
  - Açılmayan adresin yerine Tedarik tablosundaki yedek aday kullanılır; yedekten gelen dosya kayda "yedek" diye yazılır.
- Claude Code dosyaları yeni boş klasörlere indirir; kaynakların hiçbiri form, giriş ya da anahtar istemez. Alt klasör adı kayıt kimliğidir (`alafasy-murattal` …); QUD slug eşlemesi [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md) §4.3'tedir. Toplu indirmede en çok 2 eşzamanlı istek, istekler arasında en az 1 saniye bekleme ve `--retry 3` kullanılır; kesilen indirme `curl -C -` ile sürer. Önce küçük dosyalar:
  ```bash
  G=$(date +%F)
  Q=data/gelen/zamanlama-qud/$G; mkdir -p data/gelen/zamanlama-qud && mkdir "$Q"
  V=https://github.com/QUD-Technologies/quranic-universal-audio/releases/download/v4.0.0
  for f in manifest.json catalog.json surah_info.json; do curl -sSL --retry 3 --max-time 120 -o "$Q/$f" "$V/$f"; sleep 1; done
  for s in mishary_rashid_al_afasy_mp3quran maher_al_muaiqly_tarteel abdulrahman_al_sudais_tarteel saad_al_ghamdi_tarteel abdulbasit_abdulsamad_tarteel abdulbasit_abdulsamad_mujawwad_tarteel mahmoud_khalil_al_husary_mp3quran mohammed_siddiq_al_minshawi_mp3quran mohammed_siddiq_al_minshawi_mujawwad_mp3quran; do curl -sSL --retry 3 --max-time 120 -o "$Q/$s.zip" "$V/$s.zip"; sleep 1; done
  curl -sSL --max-time 60 -o "$Q/NOTICE.md" https://raw.githubusercontent.com/QUD-Technologies/quranic-universal-audio/ffdff3e3a4568275022a98d1716905fd6cc22672/NOTICE.md
  sha256sum -b "$Q"/*.json "$Q"/*.zip "$Q"/NOTICE.md | sed "s#$Q/##" > "$Q/SHA256SUMS"
  M=data/gelen/ses-mp3quran/$G; mkdir -p data/gelen/ses-mp3quran && mkdir "$M"
  curl -sSL --max-time 60 -o "$M/reciters.json" 'https://www.mp3quran.net/api/v3/reciters?language=eng'
  T=data/gelen/zamanlama-mp3quran/$G; mkdir -p data/gelen/zamanlama-mp3quran && mkdir "$T"
  curl -sSL --max-time 60 -o "$T/reads.json" https://www.mp3quran.net/api/v3/ayat_timing/reads
  for r in 123 118 112 113 102 54 30 53 51; do curl -sSL --max-time 60 -o "$T/soar-$r.json" "https://www.mp3quran.net/api/v3/ayat_timing/soar?read=$r"; sleep 1; done
  sha256sum -b "$T"/*.json | sed "s#$T/##" > "$T/SHA256SUMS"
  ```
- Sure dosyaları: adres listesi (kayıt, sure, adres; 1.026 satır) QUD `catalog.json` `chapter_urls` alanından `.tmp/` altındaki geçici betikle çıkarılır. Her dosya `curl -sSL --retry 3 --max-time 900 -o data/gelen/<kaynak>/<G>/<kayit>/<sss>.mp3 <adres>` ile iner (`sss` üç haneli; `ses-mp3quran` için 4 kayıt, 456 dosya; `ses-tarteel-cdn` için 5 kayıt, 570 dosya). İndirmeden önce 1.026 adres için HEAD taraması (`curl -sIL`; `Content-Length` ve `ETag`) yeniden çalıştırılır; Git Bash'te `-w` biçim dizisine adres katılırsa `\t` ve `\n` bozulur, adres ayrıca yazdırılır. Bitince `sha256sum -b "$M"/*/*.mp3 "$M"/reciters.json | sed "s#$M/##" > "$M/SHA256SUMS"`; `ses-tarteel-cdn` için aynı kalıp (`reciters.json` olmadan).
- Bütünlük: indirilen her dosyanın bayt sayısı HEAD taramasındaki `Content-Length` ile aynı olmalıdır. ETag tek parçalı yüklemelerde dosyanın MD5'idir (1.026 dosyanın 764'ünde; üç örnekte MD5 ile doğrulandı): bu dosyalarda `md5sum` ETag ile eşleşir. Çok parçalı yüklenen 262 dosyada ETag `-` içerir ve yalnız bayt sayısı karşılaştırılır. Uyuşmayan dosya silinip yeniden indirilir (en çok 3 deneme), sonra rapora yazılır.
- QUD zip özetleri (sürümün `digest` alanları; `SHA256SUMS` ile birebir aynı olmalı):
  ```text
  118fac516a7afd12bfbbed143d00eb2606fd2147cc12f7d76c2458e2771287c9  mishary_rashid_al_afasy_mp3quran.zip
  9ce96b3d9be9eb497face3f1e76b14bc0395486175de1fa6e57634d2cbf60815  maher_al_muaiqly_tarteel.zip
  0b4e7ec053f94508d5cab490e48fd63f4dd7c3f066c8b35d707b8e4c34bed5ce  abdulrahman_al_sudais_tarteel.zip
  17a0230828fd14b63b52ffc9191cdd43b110eeb73121fe8f7c288a9917cf528e  saad_al_ghamdi_tarteel.zip
  10ae962c93d9c4388172020f6e231e1b4bc21e1af2c739f26d692f80345b145d  abdulbasit_abdulsamad_tarteel.zip
  f463212e3cdd0bc61d43220906b0b8a8addb844149f3f07b87a8909e58a757e2  abdulbasit_abdulsamad_mujawwad_tarteel.zip
  8ad2dfa18fc8656565c1bc02c3d219c72347934b5221e0ed567d1d8254c5c615  mahmoud_khalil_al_husary_mp3quran.zip
  5ee099e93b10bd3292d8d0544579519d7f35d4c3a249deb50803da934d1b38a3  mohammed_siddiq_al_minshawi_mp3quran.zip
  8cd239c3b8ad699168a97b64cd1f37739c1cd7855dfce23cd3d9ae4f970abb99  mohammed_siddiq_al_minshawi_mujawwad_mp3quran.zip
  ```
  Üç JSON varlığının örnek kopya özetleri (1 ve 3 Kasım 2026'da indirilen kopyalarda aynı çıktı; `SHA256SUMS` ile birebir aynı olmalı):
  ```text
  eaff17be92891be9b1025fde355aec65a9594a11ed808a83919bc5bfdd9bd8d6  manifest.json
  9a946f91bc4af5c4a1fe5279cd142c945ff4f050a1ef4fc98e63477fe1e1a038  catalog.json
  e8e1f39b9fe73a121b61f9b4ec8eee4880e0f4333acf9f34671ac15ff581e77b  surah_info.json
  ```
- **Ön ölçüm (3 Kasım 2026; HEAD taraması 4 eşzamanlı istekle 1 dakika 54 saniye sürdü, 1.026 adresin tamamı HTTP 200 ve `audio/mpeg`; 2 Kasım 2026 taramasıyla bayt, ETag ve son değişiklik tarihi aynı):**

  | Kayıt | Dosya kaynağı | MP3 toplam bayt (114 dosya) | QUD zip (bayt) | Kelime satırı | `specials` sure sayısı |
  |---|---|---|---|---|---|
  | `alafasy-murattal` | MP3Quran | 1.718.021.595 | 662.881 | 80.201 | 113 |
  | `maher-murattal` | Tarteel | 1.284.353.500 | 647.228 | 84.117 | 1 |
  | `sudais-murattal` | Tarteel | 1.215.702.083 | 616.784 | 79.590 | 1 |
  | `ghamdi-murattal` | Tarteel | 1.414.625.818 | 625.698 | 80.246 | 1 |
  | `abdulbasit-murattal` | Tarteel | 1.785.958.087 | 640.586 | 79.572 | 1 |
  | `abdulbasit-mucevved` | Tarteel | 3.373.669.646 | 665.797 | 80.989 | 1 |
  | `husary-murattal` | MP3Quran | 2.470.339.875 | 653.449 | 78.928 | 113 |
  | `minshawi-murattal` | MP3Quran | 1.670.332.001 | 643.926 | 79.571 | 112 |
  | `minshawi-mucevved` | MP3Quran | 4.805.708.587 | 702.282 | 88.419 | 112 |

  Toplam 19.738.711.192 bayt (19,74 GB; 18,38 GiB). Dokuz zip'in hepsinde `verse_count` 6.236, benzersiz âyet 6.236, `canonical` satır 6.236, kelimesiz satır 0. Sonuç aynıysa devam edilir; farklıysa fark kaynakta değişiklik mi, ölçüm hatası mı olduğu belirlenir ve yeni değerler rapora yazılır.

  Zamanlama ve boyut karşılaştırması (3 Kasım 2026): QUD satırlarında dosya süresi yoktur (`rows=[[ref,start,end,canonical,silence_after],...]`; son satırların `silence_after` değeri sonucu değiştirmiyor), bu yüzden son âyet bitişi bayt × 8 ÷ 128.000 kestirimiyle karşılaştırıldı. Sekiz `cbr` kayıtta bitiş hiçbir surede kestirimi aşmıyor (fark −210 ile −0,06 sn; kayıt başına medyan −4,91 ile −0,08 sn). Minshawi mücevved'de (`mixed`) kestirim geçersizdir: ortalama bit hızı medyanı 192,1 kbps, en düşük 64,2, en yüksek 614,2; bitişin kestirimi aştığı en büyük fark 1.525 sn. Bu kayıtta süre çerçeve başlıkları taranarak ölçülür (A27.2).
- Kaynak kayıtları (`hat-gelistirici`; `pipeline/sources/`): `ses-mp3quran.toml` ve `ses-tarteel-cdn.toml` (`tur = "ses"`), `zamanlama-qud.toml` ve `zamanlama-mp3quran.toml` (`tur = "zamanlama"`). Zorunlu alanlar `slug`, `tur`, `baslik`, `atif_metni`; ayrıca `provider`, `kaynak_url` (MP3Quran: `https://www.mp3quran.net/eng/api`; Tarteel: `https://qul.tarteel.ai/resources/recitation`; QUD: `https://github.com/QUD-Technologies/quranic-universal-audio/releases/tag/v4.0.0`), `surum` (yalnız QUD: `v4.0.0`; MP3Quran ve Tarteel sürüm vermez, alım tarihi klasör adındadır) ve `notlar` (adres kalıbı, kayıt listesi, indirme tarihi). Atıf satırı taslakları [Kaynaklar](../../04-icerik/01-kaynaklar.md) §3.7'dedir: "Ses kaydı: MP3Quran.", "Ses kaydı: Tarteel.", "Zamanlama: Quranic Universal Audio (QUD).", "Zamanlama: MP3Quran." (kesin metin A32'de). `zamanlama-qud` kaydının `notice_text` alanı indirilen `NOTICE.md` baytlarının betikle kopyasıdır, elle yazılmaz. `test_sources.py` kayıt sayısı dört artar.
- Kitaplık sürümleri `package.json` ve `pipeline/uv.lock` kayıtlarında sabitlenir; `mutagen` A27.2'de, `lameenc` `ses-test` fikstürü yazılırken eklenir.
- **Bitti sayılır:** `data/gelen/` altında `ses-mp3quran`, `ses-tarteel-cdn`, `zamanlama-qud` ve `zamanlama-mp3quran` için tarihli klasörler ve `SHA256SUMS` dosyaları var (satır sayıları 457, 570, 13 ve 10); 1.026 MP3'ün bayt sayıları HEAD taramasıyla aynı (kaynak değişmediyse toplam 19.738.711.192 bayt) ve tek parçalı dosyalarda MD5 ETag ile tuttu; dokuz zip'in özetleri yukarıdaki listeyle aynı; dört kaynak kaydı eklendi ve `uv --directory pipeline run mutalaa sources check` 0 hata, 0 uyarıyla bitiyor; tarih, adresler ve ölçümler ilerleme notunda.

### A27.1 · Kaynak ve teknoloji araştırması
- Araştırma 30 Ekim 2026'da yapıldı: [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md). A27.0'da `arastirmaci` üç noktayı yeniden doğrular ve sonuçlar rapora işlenir: MP3Quran ses adresinin iki biçimi (`/audio/` ve `/download/audio/`; SK-8), QUD `catalog.json` alanları ile v4.0.0'dan sonra yeni sürüm olup olmadığı, Tarteel CDN adres kalıbı (QUD `chapter_urls`). Ön sonuç (3 Kasım 2026): iki MP3Quran biçimi aynı dosyayı verir; v4.0.0 en yeni etikettir (`git ls-remote --tags`: v1.0.0 … v4.0.0); `specials.json` ayrı bir sürüm varlığı değil, her zip'in içindedir.
- Ölçülen boyutlar rapordaki kaba tahminin yerine yazılır (§4.4, §5.2: 9 kayıt için 19,74 GB).
- **Bitti sayılır:** rapordaki SK-8 kapandı; QUD sürümü (v4.0.0 ya da daha yenisi) rapora yazıldı, yeni sürüm seçildiyse K-41 `/karar` ile güncellendi.

### A27.2 · Okuyucu kataloğu ve ayna (içerik hattı, Yayınlayıcı)
- Kaynak kayıtları A27.0'da açıldı. `ses-test` sentetik fikstürü A13'te açılan `test-ses` kaynak kaydıyla gelir (sentetik ton; `internal`'a girer, `public`'e girmez); üretim aracı `lameenc` (Tedarik).
- İçerik hattı: `pipeline/src/mutalaa_pipeline/ses/` — `uv run mutalaa ses katalog` (QUD `manifest.json` ve `catalog.json`, MP3Quran `reciters` ve `ayat_timing`; v1 kayıt listesi `pipeline/mutalaa.toml` içinde), `uv run mutalaa ses ayna --kayit <id>` (A27.0'da `data/gelen/<kaynak>/<tarih>/<kayit>/` altına inen dosyaları `data/raw/ses/{kayit}/{tarih}/{sss}.mp3` altına alır, `fetch.json`; bayt, sha256, süre, bit hızı türü; zamanlama son âyetinin ölçülen süreyi aşmaması), `uv run mutalaa ses zaman --kayit <id>` (QUD zip'inden âyet, kelime ve özel bölüt satırları; çapa `q:{s}:{a}`). Süre, MP3 çerçeve başlıkları taranarak ölçülür; bit hızı, örnekleme ve Xing/Info başlığı `mutagen` ile okunur, `cbr` kayıtlarda iki süre arasındaki fark en çok 2 sn olmalıdır; bit hızı türü QUD `audio.bitrate_mode` ile karşılaştırılır (`cbr`, `mixed`).
- Editoryal veritabanı (`sunucu-gelistirici`, `ef-goc`): ses kayıtları ve sure dosyaları için tablolar (adlar ve sütunlar bu adımda `/karar` gerekmeden Editoryal veritabanı §9.1'e yazılır) ve `audio_timing`'in kayda bağlanması; EF göçü, göç testleri.
- Yayınlayıcı: `ses-katalog` ve `ses-zaman-{kayit}` paketleri (kaynak kaydı olan içerik olarak P-01'den geçer); ayna dosyalarının `audio/{kayit}/{dosya_surumu}/{sss}.mp3` adresine yüklenmesi (yerelde SeaweedFS; canlı depo İ-18). Paket şeması [İçerik paketleri](../../03-veri/03-icerik-paketleri.md) §3.5.
- **Bitti sayılır:** 9 kaydın 114'er dosyası yerel depoda ve HTTP ile alınabiliyor; `dev` manifestinde `ses-katalog` ve 9 `ses-zaman-*` paketi var; katalogdaki her dosyanın bayt ve sha256 değeri depodaki dosyayla aynı; kayıt başına âyet zamanlaması 6.236 satır (eksik varsa raporda ve katalogda işaretli); son âyet bitişi ölçülen dosya süresini aşmıyor; `uv run pytest` ve `dotnet test` yeşil.

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
- iOS'ta indirilen seslerin yedekten dışlanması (SK-7): hazır paket yok (Tedarik); küçük yerel modül ya da yedeğe girmeyi kabul; seçim bu adımda yazılır.
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
- Araştırma raporu, Ses sistemi, Depolama yöneticisi ve İçerik paketleri koda göre eşitlenir (`/belge-esitle`); [Kaynaklar](../../04-icerik/01-kaynaklar.md) §3.7 kartları A27.0'da açılan kayıtlarla eşitlenir; karar gereken sapma `/karar` ile.
- `inceleyici`, `arayuz-denetcisi` çalışır; engelleyici bulgu kalmaz.
- **Bitti sayılır:** kabul ölçütleri kanıtlı; ilerleme dosyası güncel.

## Kabul ölçütleri
- [ ] Tedarik: `data/gelen/ses-mp3quran/`, `ses-tarteel-cdn/`, `zamanlama-qud/` ve `zamanlama-mp3quran/` altında tarihli klasörler ve `SHA256SUMS` var; 1.026 MP3'ün (9 × 114) bayt sayıları HEAD taramasıyla aynı; dokuz QUD zip'inin özetleri sürümün `digest` değerleriyle aynı; dört kaynak kaydı geçerli (`mutalaa sources check` 0 hata, 0 uyarı).
- [ ] Yerel depoda 9 kaydın 114'er dosyası var; katalogdaki bayt ve sha256 değerleri dosyalarla aynı; `dev` manifestinde `ses-katalog` ve 9 `ses-zaman-*` paketi var.
- [ ] Her kayıtta âyet zamanlaması 6.236 satır ya da eksikler katalogda işaretli; son âyet bitişi dosya süresini aşmıyor (süre çerçeve taramasından; içerik hattı raporu).
- [ ] `pnpm --filter @mutalaa/player test` yeşil; Ses sistemi §5.3'teki her durum ve §5.2'deki her olay en az bir testte geçer; `decideAfterFrame` örneği birebir sağlanır.
- [ ] `packages/player` içinde `react-native` ya da `expo` içe aktarımı yok.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: parça çözücü (yerel, akış, çevrimdışı), indirme işleri ve doğrulama, mini oynatıcı ve Dinleme sayfası, çip önceliği, hata yolları.
- [ ] Uygulama koduna gömülü ses dosyası yok; üçüncü taraf ses sunucusu adresi uygulama kodunda ve paketlerde yok (`grep`).
- [ ] `uv run pytest`, `dotnet test --solution server/Mutalaa.slnx` yeşil; EF göçü testleri yeşil.
- [ ] Cihaz testleri ilerleme notunda "kullanıcıya bırakıldı" ya da kullanıcının sonuçlarıyla.

## Doğrulama
```bash
git ls-remote --tags https://github.com/QUD-Technologies/quranic-universal-audio.git
wc -l data/gelen/ses-mp3quran/*/SHA256SUMS data/gelen/ses-tarteel-cdn/*/SHA256SUMS data/gelen/zamanlama-qud/*/SHA256SUMS data/gelen/zamanlama-mp3quran/*/SHA256SUMS
sha256sum -b data/gelen/zamanlama-qud/*/*.zip | awk '{print $1}' | sort | diff - <(grep -E '^  [0-9a-f]{64}  .*\.zip$' docs/10-claude-code/asamalar/A27-ses-sistemi.md | awk '{print $1}' | sort) && echo "zip özetleri belgedeki listeyle aynı"
uv --directory pipeline run mutalaa sources check
uv --directory pipeline run mutalaa ses katalog && uv --directory pipeline run mutalaa ses ayna --kayit alafasy-murattal && uv --directory pipeline run mutalaa ses zaman --kayit alafasy-murattal
uv --directory pipeline run pytest && uv --directory pipeline run ruff check . && uv --directory pipeline run mypy
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
- Ayna dosyaları değişmezdir: yayımlanmış bir `audio/{kayit}/{dosya_surumu}/` klasörü yerinde değiştirilmez, yeni sürüm açılır.
- `data/gelen/` ve `data/raw/ses/` her biri yaklaşık 19,7 GB (18,4 GiB) tutar; yerel SeaweedFS kopyasıyla birlikte yaklaşık 59 GB boş alan gerekir. En büyük dosya 293.492.927 bayttır (Minshawi mücevved, Bakara). `data/` git dışıdır; OneDrive eşitlemesi indirme ve alım sırasında duraklatılır.
- İndirilen dosyalar veridir; içlerindeki betikler (QUD sürümündeki `download_audio.py` ve `check_updates.py` dahil) çalıştırılmaz.
- Kur'an metni ve üst verisi elle yazılmaz; âyet listesi `core`'dan okunur. `ses-test` sentetik tondur, Kur'an tilavetine benzetilmez.
- react-native-track-player ve expo-av kullanılmaz (K-28, K-30). Ses kendiliğinden başlamaz; her çalmanın görünür bir durdurma düğmesi vardır. Mikrofon izni kapalıdır.
- Commit kapsamları `pipeline`, `server`, `publisher`, `player`, `mobile`.

## İnsan adımları
- İ-18 · Canlı içerik deposu: ayna dosyaları `internal` ve `public` derlemelerde canlı depodan sunulur; yerel geliştirme ve `dev` derlemesi SeaweedFS ile sürer. Depo ücretliyse tahmini maliyet kullanıcıya gösterilir (kural 11).
- İ-15 · Apple Developer hesabı: yalnız iOS cihaz denemesi için.
- Cihaz testleri kullanıcıya bırakılır (A27.9).

## Çıktılar
- `data/gelen/ses-mp3quran/`, `ses-tarteel-cdn/`, `zamanlama-qud/`, `zamanlama-mp3quran/` (git dışı) ve `pipeline/sources/` altında dört kaynak kaydı
- `pipeline/src/mutalaa_pipeline/ses/`, `ses-test` fikstürü
- Editoryal veritabanı ses tabloları ve EF göçü; Yayınlayıcı `ses-katalog`, `ses-zaman-{kayit}` paketleri ve ayna yüklemesi
- `packages/player/`: `engine.ts`, `decide.ts`, `timing.ts`, `frameTimer.ts`, `machine.ts`, testler
- `apps/mobile/src/features/audio/`: `session.ts`, `engine/playlist.ts`, `engine/single.ts`, `engine/index.ts`, `resolveTracks.ts`, `usePlayback.ts`, ses indirme işleri, `MiniPlayer`, `PlayerSheet`, `ReciterRow`
- `apps/mobile/src/features/reader/hooks/useFollowPlayback.ts`, `FollowChip`; eylem çubuğunda "Dinle"

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A27-ses-sistemi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [Ses kaynağı araştırması](../../06-mobil/04-ses-kaynak-arastirmasi.md) · [Kaynaklar](../../04-icerik/01-kaynaklar.md) · Önceki: [A26](./A26-mushaf-a.md) · Sonraki: [A28](./A28-arama-ekrani.md)
