# Ses kaynağı araştırması (A27.1)

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak (araştırma tamam; cihaz ölçümleri kullanıcıya bırakıldı)
> **Bağlı kararlar:** [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-40](../00-ozet/02-karar-defteri.md#k-40--ses-kaynağı-hazır-dijital-tilavet-kaynakları) · [K-28](../00-ozet/02-karar-defteri.md#k-28--ses) · [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)

Bu dosya A27 ses sisteminin teknik dayanağıdır: hangi kaynaklar incelendi, okuyucular nasıl seçildi, hangi mimari neden seçildi ve kodlama hangi sırayla yapılacak. Ses sisteminin işleyişi [Ses sistemi](./02-ses-sistemi.md), aşama adımları [A27](../10-claude-code/asamalar/A27-ses-sistemi.md) dosyasındadır.

**Yöntem.** Sekiz ayrı araştırma yapıldı (okuma tarihi 30 Ekim 2026): QUD, MP3Quran, Maqra ve EveryAyah, Quran Foundation, okuyucu popülerliği, Expo ses ve dosya sistemi, başka sağlayıcılar ve zamanlama kümeleri, açık kaynak Kur'an uygulamalarının ses mimarisi. Herkese açık JSON uçları ve belgeler okundu. Ses dosyası indirilmedi, cihazda deneme yapılmadı. Sayılar araçların okuduğu sayfalardan gelir; A27.2'de yeniden okunur. Kimlik bilgisi kullanılmadı.

## 1. Gereksinimler (proje sahibi, 30 Ekim 2026)

| No | Gereksinim | Karşılayan bölüm |
|---|---|---|
| 1–3 | Yeni kayıt yok; hazır dijital sesler | §3, [K-40](../00-ozet/02-karar-defteri.md#k-40--ses-kaynağı-hazır-dijital-tilavet-kaynakları) |
| 4–7 | Az ama gerçekten çok dinlenen okuyucular; popülerlik araştırılarak seçilir | §4 |
| 8 | İlk kullanımda indirmeden çevrimiçi dinleme | §5.3, §5.5 |
| 9–10 | Sure ya da okuyucunun bütün Kur'an'ı isteğe bağlı indirilir, kalıcıdır, çevrimdışı çalar | §5.6 |
| 11–13 | Âyet âyet ve kesintisiz sure; sonraki âyet ve sure; âyet tekrarı; Nâs'ın sonunda tam tekrar açık değilse durur | §5.4, §5.8 |
| 14 | Çalan âyet vurgulanır | §5.7 |
| 15 | Kelime takibi zamanlama verisi varsa sonra eklenir | §5.7 |
| 16 | Yerel ya da çevrimiçi kaynağı uygulama kendisi seçer | §5.5 |

## 2. Projenin bugünkü durumu

- **Mobil uygulama yok.** `apps/mobile` A21'de kurulur. `packages/player` yalnız iskelettir (`packageName` dışa aktarımı). Planlanan yığın: Expo SDK 58 (kararlı 15 Ekim 2026; React Native 0.88), `expo-audio` ~58.0.10, `expo-file-system` ~58.0.13, `expo-sqlite` + Drizzle, XState v5 ([Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md); [bundledNativeModules sdk-58](https://github.com/expo/expo/blob/sdk-58/packages/expo/bundledNativeModules.json)).
- **Sunucuda ses kodu yok.** Editoryal veritabanında `icerik.audio_timing` tablosu (A07) duruyor.
- **Tasarımın dayanağı.** Âyet başına dosya sunan kaynaklardan EveryAyah'ın sure dosyası yok, QuranicAudio çalışma anında bağlanmaya uygun değil. Proje sahibi önce çevrimiçi dinleme ve kayıt başına tam indirme istiyor. Tasarım §5'te; karar [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme).

## 3. Kaynakların karşılaştırılması

Kaynaklar kapsam (114 sure, tam âyet zamanlaması), biçim (sure dosyası ya da âyet dosyası), erişilebilirlik (anahtarsız uç, GitHub ya da herkese açık CDN) ve sabitlenebilirlik (sürüm, adres, özet) ölçütleriyle karşılaştırılır ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 1 ve 2).

### 3.1 Özet

| Kaynak | Tür | Ses biçimi | Zamanlama | Mütâlaa'daki rolü |
|---|---|---|---|---|
| **MP3Quran** | Anahtarsız katalog API'si + CDN | Sure başına MP3 | Âyet düzeyi (`/api/v3/ayat_timing`), kelime yok | **Ses kaynağı** (ayna için tek seferlik alım) ve **yedek âyet zamanlaması** |
| **QUD v4.0.0** | GitHub release: katalog + zamanlama arşivleri | Ses barındırmaz; sure dosyası URL'leri | Âyet ve kelime (ms, sure dosyasına göre) | **Birincil zamanlama ve katalog kaynağı** |
| **Tarteel CDN** (QUD ve QUL kayıtlarının bir kısmı) | CDN | Sure başına MP3 | QUD ile | **Ses kaynağı** (ayna için tek seferlik alım; uygulama çalışma anında bağlanmaz) |
| Quran Foundation Content API | OAuth2 API (arka uç) + belirteçsiz ses URL'leri | Sure ve âyet | Âyet ve kelime (`segments`) | Kullanılmaz: anahtar ister, prelive yalnız iki sure taşır |
| EveryAyah | Dizin | Yalnız âyet başına MP3 | quran-align (12 klasör) | Kullanılmaz: sure dosyası yok |
| Maqra | EveryAyah'ın bayt bayt kopyası + manifest | Âyet başına | Âyet (tam sure kaydına göre) | Kullanılmaz; manifest yalnız âyet dosyalı kayıt eklenirse |
| Mushaf-Learning/quran-audio | EveryAyah adres listesi | — | Yok (klasör boş) | Kullanılmaz |
| QDC (`api.qurancdn.com`) | Belgesiz iç uç | Sure (`download.quranicaudio.com`) | Âyet ve kelime | Kullanılmaz: belgesiz, QF'nin OAuth'lu API'sine geçiş var |
| QuranicAudio | Katalog API'si + CDN | Sure | Yok | Kullanılmaz (QDC/QF ile aynı dosyalar) |
| AlQuran Cloud / Islamic Network | API + CDN | Âyet ve sure | Yok | Kullanılmaz: EveryAyah ve Quran Central kopyası, zamanlama yok |
| quranlab (Hugging Face) | Zamanlama kümesi | EveryAyah adresleri | Kelime | Kullanılmaz: âyet dosyalarına bağlı |
| quran-align | Zamanlama kümesi, 2016 | EveryAyah klasörleri | Kelime (0 tabanlı, bitiş hariç) | Kullanılmaz: âyet dosyalarına bağlı |
| archive.org, islamic.app, öteki HF kümeleri | Yükleme ve aynalar | Karışık | Karışık | Kullanılmaz: köken ve bayt kararlılığı yok |

### 3.2 MP3Quran

- **Uçlar** ([API](https://www.mp3quran.net/eng/api)): `https://mp3quran.net/api/v3/reciters?language=eng[&reciter=&rewaya=&sura=]`, `/riwayat`, `/moshaf`, `/suwar`. Yanıt: `reciters[].moshaf[]{id, name, rewaya_id, server, surah_total, moshaf_type, surah_list}`. Ses adresi `server` + `%03d.mp3` (ör. `https://cdn.mp3quran.net/audio/mishary-alafasy/r1/001.mp3`; indirme sayfasındaki biçim `/download/audio/...`). İki biçimin de çalıştığı A27.2'de denenir.
- **Zamanlama:** `/ayat_timing/reads` (115 kayıt; `id` = moshaf kimliği), `/ayat_timing/soar?read=`, `/ayat_timing?surah=&read=` → `[{ayah, start_time, end_time, polygon, x, y, page}]`. Birim belgede yok; değerler ms ile uyumlu (Bakara'nın son âyeti 7.539.060). Âyet 0 yok; 1. âyetten önceki birkaç saniye etiketsiz (istiâze ya da besmele). Kelime alanı yok.
- **Kapsam:** 13 adayın hepsinde 114 surelik Hafs murattal kaydı var. Maher Al-Muaiqly'nin murattal kaydında (102) zamanlama yok; mücevved kaydında (133) var.
- **Sınırlar:** boyut, süre ve özet alanı yok. Bilinmeyen kimlik hata vermiyor, tam liste dönüyor. Mücevved kayıtlarının rivayeti iki uçta farklı geliyor. Adresler geçmişte taşınmış (`server6.mp3quran.net` → `cdn.mp3quran.net`; QUD #312).

### 3.3 QUD (Quranic Universal Audio)

- **Sürüm:** v4.0.0, 24 Ekim 2026; 102 hizalı kayıt, 4 rivayet ([release](https://github.com/QUD-Technologies/quranic-universal-audio/releases/tag/v4.0.0)). Varlıklar: `manifest.json` (53.696 bayt), `catalog.json` (856.815 bayt), `surah_info.json`, `specials.json` (istiâze ve besmele), kayıt başına `<slug>.zip` (çoğu yaklaşık 0,6 MB); sha256 değerleri GitHub API `digest` alanında.
- **Katalog:** `recitations[]{slug, reciter_id, name_en, name_ar, riwayah, style, channel, audio_category, audio{chapter_urls, chapter_offsets_ms?, bitrate_mode, bitrate_kbps_nominal}, coverage{ayahs, surahs, missing_surahs?, missing_verses?}}`. Görülen bütün kayıtlar `by_surah`.
- **Zamanlama:** âyet satırı `[ref, start_ms, end_ms, canonical, silence_after_ms]`; kelime satırı `[word_idx (âyet içinde 1 tabanlı), start_ms, end_ms]`; `_meta{units, script, script_sha256, …}`. Harf katmanı v4.0.0'da askıda.
- **Ses–zamanlama bağı:** yalnız URL ile. QUD yayından önce her sureyi kaynaktan denetler (boyut değişirse ya da süre 2 sn'den fazla farklıysa sure çıkarılır); kaynak sesin sha256'sını yayımlamaz.
- **Sürümleme:** `content_hash`, `ts_version`, `check_updates.py`. GitHub Releases sürüm sabitli, Hugging Face kayan sürüm; Mütâlaa v4.0.0'a ve zip sha256'larına sabitlenir. Kaynağın kendi bildirimi ([NOTICE](https://raw.githubusercontent.com/QUD-Technologies/quranic-universal-audio/main/NOTICE.md)) kaynak kaydına bayt bayt yazılır ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 4).

### 3.4 Tarteel CDN ve QUL

- QUD'daki Maher, Sudais, Ghamdi ve Abdul Basit kayıtları `audio-cdn.tarteel.ai` adresli sure dosyalarına hizalı ([QUL kayıt belgesi](https://qul.tarteel.ai/resources/recitation/118/docs)). Bu dosyalar içerik hattıyla bir kez alınır ve aynadan sunulur (§5.2).
- QUL'un ses verisi indirme için giriş istiyor ve API'si yok; ses için QUL doğrudan kullanılmaz, kayıt listesi ve zamanlama QUD'dan gelir.

### 3.5 Quran Foundation Content API

- OAuth2 `client_credentials` (`scope=content`) ister; prelive `https://prelive-oauth2.quran.foundation/oauth2/token`, `https://apis-prelive.quran.foundation/content/api/v4`; production `https://oauth2.quran.foundation`, `https://apis.quran.foundation/content/api/v4` ([quickstart](https://api-docs.quran.foundation/docs/quickstart/), [OpenAPI](https://api-docs.quran.foundation/openAPI/content/v4.json)). Belirteç 3600 sn.
- **Prelive yalnız Fâtiha ve Bakara'yı taşır.** Tam veri production erişimiyle gelir.
- Uçlar: `/resources/chapter_reciters`, `/chapter_recitations/{id}/{sure}?segments=true` (`timestamps[]{verse_key, timestamp_from, timestamp_to, segments[[word_index, start_ms, end_ms]]}`), `/recitations/{id}/by_chapter/{n}` vb. Ses URL'leri belirteçsiz açılıyor (`download.quranicaudio.com/qdc/...`, `verses.quran.foundation/...`).
- **Değerlendirme:** Katalog ve zamanlama uçları belirteç, tam veri production erişimi ister. Anahtar isteyen içerik kaynağı seçilmediği için ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 2) v1 kataloğu QF'ye bağlı değildir; sure dosyaları MP3Quran ve Tarteel CDN'inden, zamanlama QUD'dan gelir.

### 3.6 EveryAyah, Maqra ve kopyaları

- EveryAyah yalnız âyet başına dosya sunar (`/data/{klasör}/{sss}{aaa}.mp3`); tam sure dosyası yok. Idriss Abkar ve Khalid Al-Jalil yok. Kök dizinde `bismillah.mp3` ve `audhubillah.mp3`; `{sss}000.mp3` besmele dosyaları sete göre değişiyor.
- Maqra EveryAyah'ın 2026-08-25 tarihli bayt bayt kopyasıdır; dosya başına `bytes`, `md5`, `sha256` manifesti verir. Islamic Network, Tarteel QUL (âyet kayıtları), quranlab ve tarteel-ai/everyayah da aynı dosyalara çıkar. Bunlar bağımsız arşiv sayılmaz.
- Âyet dosyalarını arka arkaya çalmak kesintisiz dinlemede boşluk ve sure geçişlerinde ek iş getirir; sure dosyası modeli bu yüzden seçildi (§5.1).

## 4. Okuyucuların seçimi

### 4.1 Ölçütler

1. Birbirinden bağımsız en az üç platformda üst sıralarda görünmek. Platform sayıları birbiriyle karşılaştırılmaz; evrensel sıra kurulmaz.
2. Türkiye pazarındaki uygulamalarda sunulmak (arz göstergesi).
3. Hafs an Âsım murattal kaydının 114 sure tam olması.
4. Aynı dosyaya bağlı tam âyet zamanlaması (tercihen kelime zamanlaması) bulunması.

### 4.2 Popülerlik kanıtı (okuma 30 Ekim 2026)

| Kaynak | Ölçtüğü | Bulgu |
|---|---|---|
| [Assabile best voices](https://www.assabile.com/quran/best-voices) | Site içi toplam dinlenme (günlük yeniden hesap) | 1 Sudais 81M · 2 Ghamdi 79M · 3 Maher 49M · 4 Alafasy 48M · 5 Abdul Basit 33M · 6 Shuraim 27M · 7 Ajmi 24M · 8 Husary 17M · 9 Fares Abbad 17M · 10 Minshawi 17M · 11 Yasser Al-Dosari 11M · 20 Idris Abkar 4,6M |
| [Assabile murattal koleksiyonları](https://www.assabile.com/quran/collections/quran-murattal/sort:stats_downloaded/direction:desc) | Site içi sıra | Sudais, Ghamdi, Alafasy, Maher, Abdul Basit, Ajmi, Shuraim, Fares, Husary, Minshawi (ilk 10) |
| [tvQuran](https://www.tvquran.com/) | Tek klip dinlenmesi (rastgele seçim) | Khalid Al-Jalil, Maher, Ajmi, Islam Sobhi, Juhany öne çıkıyor |
| [Way2Quran](https://way2quran.com/reciters) | Site içi dinlenme | Minshawi, Islam Sobhi, Yasser, Husary, Abdul Basit, Maher, Ghamdi ilk 20'de |
| Sharjah Quran Radio anketi ([Sharjah24](https://sharjah24.ae/en/Articles/2026/09/10/Ma16)) | Kullanıcı tercihi (örneklem verilmemiş) | Sudais, Bukhatir, Abdul Basit, Maher, Husary, Al-Balushi, Qatami, Alafasy |
| Spotify sanatçı sayfaları | 28 günlük dinleyici (arama özetinden, tarihsiz) | Alafasy, Ghamdi, Islam Sobhi, Maher, Sudais 300 binin üstünde |
| YouTube ([vidIQ](https://vidiq.com/youtube-stats/channel/UCmMcOjsVehVlEOteyrhjI2Q)) | Kanal abonesi | Alafasy 12,2M, Islam Sobhi 8,19M |
| Türk App Store uygulamaları (Vakit, İslami Yardımcı, Sesli Kuran) | Arz | Alafasy, Sudais, Abdul Basit, Maher, Minşavi, Husary ortak; ayrıca Ghamdi, Şüreym, Acemi |
| Quran.com kaynak kodu | Editoryal varsayılan | `DEFAULT_RECITER` Alafasy |

Çapraz özet: Maher ve Alafasy 5–6, Sudais, Abdul Basit, Ghamdi ve Husary 4, Minshawi ve Ajmi 3 platformda üst sinyal veriyor. Islam Sobhi YouTube ve Spotify'da çok güçlü ama klasik listelerde ve Türk uygulamalarında yok. Google Trends ve Google Play okunamadı; Türkiye'ye özgü dinlenme verisi bulunamadı.

### 4.3 v1 kayıtları (7 okuyucu, 9 kayıt)

| Kayıt kimliği | Okuyucu (Arapça) | Tarz | Dosya kaynağı (ayna için) | Zamanlama | Popülerlik |
|---|---|---|---|---|---|
| `alafasy-murattal` | Mishary Rashid Alafasy (مشاري بن راشد العفاسي) | Murattal | MP3Quran 123, `mishary-alafasy/r1` | QUD `mishary_rashid_al_afasy_mp3quran` (âyet, kelime); yedek MP3Quran 123 (âyet) | 5–6 platform; Quran.com varsayılanı |
| `maher-murattal` | Maher Al-Muaiqly (ماهر المعيقلي) | Murattal | Tarteel CDN (QUD `maher_al_muaiqly_tarteel` adresleri) | QUD (âyet, kelime) | 5–6 platform |
| `sudais-murattal` | Abdul Rahman Al-Sudais (عبد الرحمن السديس) | Murattal | Tarteel CDN (QUD `abdulrahman_al_sudais_tarteel`) | QUD (âyet, kelime); yedek: MP3Quran 54 dosyası ve âyet zamanı | Assabile 1. |
| `ghamdi-murattal` | Saad Al-Ghamdi (سعد الغامدي) | Murattal | Tarteel CDN (QUD `saad_al_ghamdi_tarteel`) | QUD (âyet, kelime); yedek: MP3Quran 30 | Assabile 2. |
| `abdulbasit-murattal` | Abdul Basit Abdul Samad (عبد الباسط عبد الصمد) | Murattal | Tarteel CDN (QUD `abdulbasit_abdulsamad_tarteel`) | QUD (âyet, kelime); yedek: MP3Quran 53 | 4 platform |
| `abdulbasit-mucevved` | Abdul Basit Abdul Samad | Mücevved | Tarteel CDN (QUD `abdulbasit_abdulsamad_mujawwad_tarteel`) | QUD (âyet, kelime); yedek: MP3Quran 51 | Quran.com ve Türk uygulamaları ayrı sunuyor |
| `husary-murattal` | Mahmoud Khalil Al-Husary (محمود خليل الحصري) | Murattal | MP3Quran 118, `mahmoud-husary/r1` | QUD `mahmoud_khalil_al_husary_mp3quran`; yedek MP3Quran 118 | 4 platform |
| `minshawi-murattal` | Mohamed Siddiq El-Minshawi (محمد صديق المنشاوي) | Murattal | MP3Quran 112, `muhammad-minshawi/r1` | QUD `mohammed_siddiq_al_minshawi_mp3quran`; yedek MP3Quran 112 | 3 platform |
| `minshawi-mucevved` | Mohamed Siddiq El-Minshawi | Mücevved | MP3Quran 113, `muhammad-minshawi/r2` | QUD `mohammed_siddiq_al_minshawi_mujawwad_mp3quran` (karışık bit hızı); MP3Quran'da zamanlama yok | Ayrı sunuluyor |

Hepsinde 114 sure var. QUD kapsamı bu kayıtlarda 6.236 âyet; A27.2 kesimden önce `coverage` alanından yeniden doğrular. MP3Quran mücevved kayıtlarının rivayet alanı tutarsız; kayıt adı ve QUD `riwayah` alanıyla teyit edilir.

**Sonraki adaylar (v1.1, katalog sürümüyle eklenir):** Yasser Al-Dosari (Tarteel + QUD ya da MP3Quran 92 + âyet zamanı), Saud Al-Shuraim (MP3Quran 31 + QUD), Ahmed Al-Ajmi (MP3Quran 5 + MP3Quran âyet zamanı), Fares Abbad (MP3Quran 81 + âyet zamanı), Husary muallim (öğrenme kullanımı), Islam Sobhi (QUD kapsamı 5.333 âyet; tamamlanınca), Idriss Abkar ve Khalid Al-Jalil (MP3Quran 12, 20 + âyet zamanı; QUD'da yok).

### 4.4 Boyut

Kaynak API'leri boyut vermez. Kesin boyut A27.2'de, dosyalar aynaya alınırken ölçülür ve katalogda saklanır (`kayit_sure.bayt`, kaydın toplamı). Kaba tahmin: bayt ≈ süre × bit hızı ÷ 8; bütün Kur'an bir murattal kayıtta 128 kbps'de yaklaşık 1–1,7 GB tutar (aynı okuyucuların EveryAyah 128 kbps setleri Maqra manifestlerinde 1,05–1,72 GB; mücevved kayıtlar daha uzundur, Abdul Basit mücevved 3,39 GB). Arayüz "yaklaşık" sözcüğü olmadan yalnız katalogdaki ölçülmüş değeri gösterir.

## 5. Mimari karar

Karar kaydı: [K-41](../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme). Ayrıntılı işleyiş: [Ses sistemi](./02-ses-sistemi.md).

### 5.1 Kayıt modeli

- **Okuyucu** birden çok **kayıt** taşır (murattal, mücevved, muallim). Kayıt kimliği `{okuyucu}-{tarz}` biçimindedir (ör. `alafasy-murattal`); ASCII, küçük harf.
- Her kayıt **114 sure dosyasından** oluşur. Âyetler dosya içinde **karedir**: `[başlangıç_ms, bitiş_ms)`. Besmele ve istiâze bölütleri (QUD `specials.json`, 1. âyetten önceki kısım) ayrı kare türüdür.
- Model quran_android ve quran-ios'taki "dosya × kare" desenidir: âyet başına dosyalı kayıt da aynı modele girer (her dosya tek kare), ama v1 kataloğunda bulunmaz ([quran-ios AudioRequest](https://github.com/quran/quran-ios)).

### 5.2 Ayna: dosyalar kendi içerik depomuzdan

Claude Code her kaydın sure dosyalarını kaynaktan (MP3Quran CDN, Tarteel CDN) **bir kez** `data/gelen/<kaynak>/<YYYY-AA-GG>/` altına indirir; toplu indirmede istek hızı sınırlanır ([K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 2). İçerik hattı dosyaları buradan alır, `data/raw/ses/{kayit}/{tarih}/{sss}.mp3` altına yazar ve şunları ölçer: bayt, sha256, süre, bit hızı türü (CBR ya da VBR). Yayınlayıcı dosyaları içerik deposuna (yerelde SeaweedFS, canlıda R2; [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı)) **değişmez ve sürümlü** adrese koyar: `audio/{kayit}/{dosya_surumu}/{sss}.mp3`. Uygulama üçüncü taraf ses sunucusuna bağlanmaz.

Gerekçe:
1. Android'de `createDownloadTask` sürdürmede `If-Range` ya da ETag göndermiyor; değişen bir dosyaya sürdürme bozuk dosya üretir. Değişmez adres bu riski kaldırır.
2. Kaynaklar boyut ve sha256 vermiyor; ayna her dosyanın boyutunu ve özetini bilir. İndirme doğrulaması ve boyut gösterimi buna dayanır.
3. Zamanlama sese yalnız URL ile bağlı; kaynakta dosya değişir ya da adres taşınırsa (MP3Quran #312) zamanlama kayar. Ayna dosyayı sabitler; kaynakta değişiklik içerik hattının denetiminde görülür, yeni `dosya_surumu` olarak gelir.
4. Kullanıcının IP adresi birden çok üçüncü taraf ses sunucusuna gitmez; yalnız zaten kullanılan içerik deposu ve CDN'e gider ([Gizlilik](../07-yayin/02-gizlilik.md) §2.4).
5. ASP.NET arka ucu ses baytlarını iletmez; depo nesne deposudur.

Bedel: dokuz kayıt için yaklaşık 12–16 GB depolama (kaba tahmin, §4.4). R2 fiyatı ve çıkış ücreti İ-18 ile hesap açılırken doğrulanır; ücretli işlem kural 11 gereği onay ister.

### 5.3 Paketler

| Paket | İçerik | İnişi |
|---|---|---|
| `ses-katalog` | `okuyucu`, `kayit`, `kayit_sure` (adres, bayt, sha256, süre_ms, dosya_surumu) | Manifestle kendiliğinden; küçük |
| `ses-zaman-{kayit}` | `ayet_zaman(anchor, start_ms, end_ms)`, `kelime_zaman(anchor, kelime_no, start_ms, end_ms)`, `ozel_bolut(sure, tur, start_ms, end_ms)` | Kayıt ilk seçildiğinde kendiliğinden (yaklaşık 1 MB); sonra çevrimdışı |

Kullanıcı hiçbir şey indirmeden çevrimiçi dinler: katalog ve zamanlama küçük üst veridir, ses akışla gelir. Paket şeması A12'nin paket şeması kurallarına göre yazılır; içerik hattı zamanlamayı `icerik.audio_timing` tablosu üzerinden geçirir.

### 5.4 Oynatma motoru

- **Tek motor arayüzü** (`packages/player`, platformdan bağımsız) ve iki gerçekleme (`apps/mobile/src/features/audio/engine/`):
  - `PlaylistEngine` (varsayılan): expo-audio SDK 58 `AudioPlaylist`; her sure dosyası bir parçadır. Kesintisiz sure geçişi ve kilit ekranında sonraki/önceki **sure** düğmeleri bu yolla gelir ("Support lockscreen controls with playlists", expo-audio 58.0.0).
  - `SingleEngine` (yedek): tek `AudioPlayer`; `replace()` ve `preload()` ile sure geçişi. Kilit ekranında sonraki/önceki yoktur (expo-audio'da tek oynatıcı için desteklenmiyor, [#43538](https://github.com/expo/expo/issues/43538)); kilit ekranı yine açılır, böylece Android ses ~3 dakikada kesilmez.
- **Âyet sınırı:** sabit sorgu yerine "sınıra kalan süre ÷ hız" kadar zamanlayıcı kurulur; tetiklenince konum yeniden okunur, 150 ms tolerans uygulanır (quran_android ve quran-ios deseni). Âyet tekrarı `seekTo(başlangıç)` ile; bekleme gerekirse duraklatma ve zamanlayıcı.
- **Oynatıcı modül düzeyindedir**, React bileşen ömrüne bağlanmaz ([#49906](https://github.com/expo/expo/issues/49906)).
- **Liste kilit ekranı açılmadan önce tam kurulur** (Android'de sonradan `add()` çöküyor, [#52192](https://github.com/expo/expo/issues/52192)).

### 5.5 Kaynak seçimi

Her sure için sırayla: (1) `device.db` `audio_file` içinde doğrulanmış yerel dosya → (2) bağlantı varsa aynadaki akış adresi → (3) bağlantı yoksa "Bu sure indirilmedi" durumu ve "İndir" düğmesi. Kullanıcı seçim yapmaz. İndirilmemiş sure çevrimdışıyken listede çalınabilir gösterilmez.

### 5.6 İndirme ve çevrimdışı

- Birimler: tek sure ve kaydın tamamı (114 sure). İşler A29'un kuyruğunda (`download_job`) çalışır; ses için ikinci kuyruk yazılmaz ([Depolama yöneticisi](./03-depolama-yoneticisi.md) §4).
- `File.createDownloadTask` (ilerleme, duraklatma, sürdürme, iptal, `savable()`); `.part` dosyası; bitince boyut ve `file.digest('SHA-256')` denetimi; `Paths.document/mutalaa/audio/{kayit}/{dosya_surumu}/{sss}.mp3` altına taşıma; `audio_file` satırı.
- Yalnız Wi-Fi ayarı, yer denetimi ve silme Depolama yöneticisindeki kurallarla.
- Kayıt değiştirilince başka kaydın dosyası kullanılmaz: anahtar `(kayit, sure, dosya_surumu)`.

### 5.7 Vurgu ve kelime takibi

- **Âyet vurgusu** v1'de bütün kayıtlarda: `ses-zaman-{kayit}` `ayet_zaman` satırlarında ikili arama.
- **Kelime takibi** `kelimeTakibi` bayrağıyla sonra açılır. Koşul: QUD kelime numaralarının (QPC/DigitalKhatt bölünmesi, 1 tabanlı) Tanzil kelime çapalarıyla (A11, A17) eşlemesinin içerik hattında doğrulanması. Eşleşmeyen âyette kelime vurgusu yapılmaz.

### 5.8 Sure sonu, tekrar, Nâs

- Sure bitince "Sonraki sureye geç" açıksa (varsayılan açık) aynı kayıtla sonraki sure çalar. Nâs (114) bitince "Bütün Kur'an'ı tekrarla" açık değilse çalma durur; açıksa Fâtiha'dan başlar.
- Âyet tekrarı (×1, 2, 3, 5, 10, sınırsız), aralık tekrarı ve âyet arası bekleme ([Ses sistemi](./02-ses-sistemi.md) §5) sure dosyasında kare olarak çalışır.

### 5.9 Arka planda çalma

`expo-audio` eklentisi `enableBackgroundPlayback: true` (Android `mediaPlayback` ön plan hizmeti, iOS `UIBackgroundModes: audio`); `setAudioModeAsync({ shouldPlayInBackground: true, interruptionMode: 'doNotMixPersistent', playsInSilentMode: true })`; kilit ekranı etkin. Android'de arka planda indirme mekanizması yok; indirme uygulama öndeyken ya da ses hizmeti çalışırken sürer (cihazda ölçülür).

### 5.10 Arka ucun rolü

Ses için arka uç bir rol üstlenmez: katalog ve zamanlama içerik hattında üretilir, Yayınlayıcı paket ve ayna dosyalarını içerik deposuna koyar, uygulama depodan okur. ASP.NET arka ucu ses baytlarını iletmez.

## 6. Değerlendirilen alternatifler

| Seçenek | Neden seçilmedi |
|---|---|
| Kaynak CDN'lerinden doğrudan çalma (ayna yok) | Boyut ve sha256 yok; adres taşınması ve dosya değişikliği zamanlamayı bozar; Android sürdürmesinde bozuk dosya riski; IP birden çok üçüncü tarafa gider |
| Âyet başına dosya (EveryAyah) + quran-align | Sure dosyası yok; kesintisiz dinlemede boşluk; quran-align 2016'dan beri güncellenmiyor ve 12 klasörle sınırlı; Maher, Ghamdi, Yasser için kelime zamanlaması yok |
| QDC (`api.qurancdn.com`) | Belgesiz iç uç; QF OAuth'lu API'ye geçiyor; veride negatif süreler |
| v1'i QF'ye dayandırmak | Anahtar ister; prelive yalnız iki sure taşır; tam veri production erişimi ister |
| `react-native-track-player` v5 | Ticari kullanımda ücretli (K-28) |
| `react-native-audio-api` | 0.x API, PCM bellek yükü, akış katmanı bize kalır; expo-audio yetmezse ikinci seçenek |
| Kendi Media3/AVPlayer Expo modülümüz | En güçlü yedek yol; expo-audio cihaz ölçümünde yetersiz kalırsa (A27.9) değerlendirilir |

## 7. Riskler ve doğrulanacaklar

| No | Konu | Ne zaman |
|---|---|---|
| SK-1 | VBR MP3'te `seekTo` doğruluğu Android'de güvenilmez (Media3 belgesi); kaynak bit hızı türü katalogda tutulur, VBR kayıtta âyet atlaması ölçülür. Gerekirse ayna CBR'ye yeniden kodlanır ve zamanlama kayması ölçülür | A27.2, cihaz (kullanıcı) |
| SK-2 | `AudioPlaylist`'te perde düzeltmeli hız ayarı yok; 0,75–1,5 hız perdeyi bozarsa hız değiştiğinde `SingleEngine`'e geçilir | Cihaz (kullanıcı) |
| SK-3 | Listede gerçek boşluk süresi ve iOS'ta çok parçalı kuyruk maliyeti | Cihaz (kullanıcı) |
| SK-4 | QUD kayıtlarının kaynağında değişiklik (#297); ayna sabitler, içerik hattı denetimi farkı gösterir | A27.2 |
| SK-5 | QUD kelime numarası ↔ Tanzil kelime çapası eşlemesi | A27.2 (kelime takibi bayrağı) |
| SK-6 | Besmele ve istiâze bölütü: QUD `specials.json` ile MP3Quran'daki etiketsiz ön kısım | A27.2 |
| SK-7 | iOS'ta indirilen seslerin iCloud yedeğinden dışlanması için Expo API'si yok | A27.6 (karar: küçük yerel modül ya da yedeğe girmeyi kabul) |
| SK-8 | MP3Quran adreslerinin `/download/` önekli ve öneksiz biçimleri | A27.2 |
| SK-9 | R2 depolama ve trafik bedeli | İ-18 |

## 8. Uygulama planı (özet)

Ayrıntılı adımlar ve kabul ölçütleri [A27](../10-claude-code/asamalar/A27-ses-sistemi.md) dosyasındadır. Sıra teknik bağımlılığa göredir:

1. **Tedarik (A27.0), katalog ve ayna (içerik hattı + Yayınlayıcı):** kaynak adreslerinin doğrulanması ve indirme (`data/gelen/`; [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) madde 2), `pipeline/src/mutalaa_pipeline/ses/` (QUD ve MP3Quran okuyucuları, ayna alımı, ölçüm), kaynak kayıtları, editoryal veritabanı ses tabloları (EF göçü), `ses-katalog` ve `ses-zaman-*` paketleri, ayna dosyalarının yüklenmesi.
2. **`packages/player`:** motor arayüzü (dosya × kare), kare zamanlayıcısı kararı, `decideAfterItem`, zamanlama araması, XState makinesi; önce testler.
3. **Çevrimiçi oynatma:** `PlaylistEngine`, `SingleEngine`, ses oturumu, kaynak çözücü (akış), okuyucu seçici, mini oynatıcı, Dinleme sayfası.
4. **Geçiş ve senkron:** âyet tekrarı, aralık, sonraki sure, Nâs kuralı, âyet vurgusu, takip modu.
5. **İndirme:** A29 kuyruğunda ses işleri (sure, kaydın tamamı), boyut ve özet doğrulaması.
6. **Çevrimdışı:** yerel öncelikli çözücü, çevrimdışı görünürlük.
7. **Sağlamlaştırma:** hata kodları, yeniden deneme, katalog güncellemesi, eski dosya sürümünün temizliği.
8. **Testler ve cihaz:** birim ve bileşen testleri; cihaz ölçümleri kullanıcıya bırakılır.

## 9. Kaynaklar

Okuma tarihi hepsi için 30 Ekim 2026.

- MP3Quran: [API](https://www.mp3quran.net/eng/api) · [reciters](https://mp3quran.net/api/v3/reciters?language=eng) · [ayat_timing/reads](https://mp3quran.net/api/v3/ayat_timing/reads)
- QUD: [depo](https://github.com/QUD-Technologies/quranic-universal-audio) · [v4.0.0](https://github.com/QUD-Technologies/quranic-universal-audio/releases/tag/v4.0.0) · [katalog belgesi](https://raw.githubusercontent.com/QUD-Technologies/quranic-universal-audio/main/docs/reference/catalog.md) · [NOTICE](https://raw.githubusercontent.com/QUD-Technologies/quranic-universal-audio/main/NOTICE.md)
- Tarteel QUL: [kayıtlar](https://qul.tarteel.ai/resources/recitation) · [kayıt belgesi](https://qul.tarteel.ai/resources/recitation/118/docs)
- Quran Foundation: [quickstart](https://api-docs.quran.foundation/docs/quickstart/) · [OpenAPI](https://api-docs.quran.foundation/openAPI/content/v4.json) · [ses SDK](https://api-docs.quran.foundation/docs/sdk/javascript/audio/)
- EveryAyah ve kopyaları: [everyayah.com](https://everyayah.com/) · [Maqra](https://github.com/Abdalla-Eldoumani/maqra) · [Mushaf-Learning/quran-audio](https://github.com/Mushaf-Learning/quran-audio) · [quran-align](https://github.com/cpfair/quran-align) · [quranlab](https://huggingface.co/datasets/quranlab/quran-audio) · [AlQuran Cloud CDN](https://alquran.cloud/cdn) · [QuranicAudio API](https://quranicaudio.com/api/qaris)
- Popülerlik: §4.2 tablosundaki bağlantılar.
- Expo: [expo-audio v58](https://docs.expo.dev/versions/v58.0.0/sdk/audio/) · [expo-audio CHANGELOG](https://github.com/expo/expo/blob/sdk-58/packages/expo-audio/CHANGELOG.md) · [expo-file-system v58](https://docs.expo.dev/versions/v58.0.0/sdk/filesystem/) · [expo-network v58](https://docs.expo.dev/versions/v58.0.0/sdk/network/) · [SDK 58](https://expo.dev/changelog/sdk-58)
- Açık kaynak uygulamalar: [quran_android](https://github.com/quran/quran_android) · [quran-ios](https://github.com/quran/quran-ios) · [quran.com-frontend-next](https://github.com/quran/quran.com-frontend-next) · [Media3 sorun giderme](https://developer.android.com/media/media3/exoplayer/troubleshooting)

## İlgili dosyalar

- [Ses sistemi](./02-ses-sistemi.md) · [Mobil mimari](./01-mobil-mimari.md) · [Depolama yöneticisi](./03-depolama-yoneticisi.md)
- [A27 aşaması](../10-claude-code/asamalar/A27-ses-sistemi.md) · [Karar defteri](../00-ozet/02-karar-defteri.md) · [Kaynaklar](../04-icerik/01-kaynaklar.md)
- [İçerik paketleri](../03-veri/03-icerik-paketleri.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [Gizlilik](../07-yayin/02-gizlilik.md)
