# A26 · Mushaf A (Medine düzeni, QPC fontları, cüz paketleri)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** [İ-06](../06-insan-adimlari.md) (QF Developer Console; A26.4'ten önce)
> **Ajanlar:** `mobil-gelistirici` · `lisans-denetcisi` · `arastirmaci` · `hat-gelistirici` ve `sunucu-gelistirici` (yalnız A26.4) · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `lisans-kapisi` · `paket-yayini` · **Tahmini oturum:** 2 + bekleme sonrası 2
> **Başlat:** `/asama A26`

## Amaç
Mod A, basılı Medine mushafıyla satır satır aynı sayfayı QPC sayfa fontlarıyla çizer; kelime seçimi ve ekran okuyucu için paralel Unicode katmanı sunar. Fontların ve satır düzeni verisinin dağıtım hakkı henüz belirsiz olduğu için (Açık soru MM-1, MM-2) aşama iki parçadır. Lisanstan bağımsız kod ve testler bekleme noktasına kadar yapılır; gerçek cüz paketleri ve cihaz ölçümleri lisans koşulları sağlanınca yapılır. Mod A `mushafA` bayrağının arkasındadır; paket görünmüyorsa okuma Mod C ile sürer.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7 ortak sözleşme, §7.1, §7.4, §9, §10 (`mushafA`, `tecvidRenkleri`), §15 (MM-1–MM-4)
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.5, §7, §9
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §2 (`qpc-*-font`, `medine-604-duzen`), §3.1, §8 yazışma 3
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §7.1, §7.4
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 (Mod A kelime aralığı), §13
- [Backend API](../../02-mimari/05-backend-api.md): §10.3 (P-01, P-02, P-03)
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §9.1 (`page_map.glyphs`)

## Kapsam
**Yapılır**
- Lisanstan bağımsız: font önbelleği, satır düzeni, isabet testi, jestler, "Seç" yolu, paralel Unicode katmanı (`src/features/reader/mushaf-a/`); sayfa → cüz paketi çözümü; eksik paket şeridi; `mushafA` bayrağı ve mod listesi; lisans raporu ve bekleme noktası kaydı.
- Bekleme noktasından sonra: `mushaf-a-cuz-NN` paket şeması, hat ve Yayınlayıcı desteği, yalnız `dev` yayını; cihaz ölçümleri.

**Yapılmaz**
- Mod B ([A40](./A40-mushaf-b.md)); tecvid renkleri V4 (v1.x; `tecvidRenkleri` kapalı kalır).
- Depolama'daki 30 cüzlük ızgara ve indirme kuyruğu (A29); tanıtımdaki "Mod A'yı Wi-Fi ile indir" önerisi (tanıtım ekranının işi; A21'deki nota bakılır); Kurul başvurusu (A34).

## Adımlar
### A26.1 · Lisans durumu ve doğrulamalar
- `lisans-denetcisi` raporu (`lisans-kapisi` becerisiyle): `qpc-v2-font` ve `medine-604-duzen` durumu (`bekliyor`); QF şartlarının izin verdiği ve vermediği (gömme için aktif hesap ve atıf; bir haftadan uzun önbellek yasağı; hazır veritabanı dağıtımı yasağı); P-02 (`kisitlar.hazir_vt_yasak`); Kurul durumu (Yayın kapısı §7.1). Rapor özeti ilerleme kaydına yazılır.
- `arastirmaci` (seçilen SDK için): expo-font'un yerelde woff2 kabulü (MM-3); `loadAsync`'te `file://` kaynağı; boşaltma yöntemi ve `ERR_UNLOAD` (MM-4); Reanimated 4'te JS'e geri çağırma API'si; Android'de `accessibilityLanguage` karşılığı; SDK 58 seçildiyse expo-sqlite'ın `ArrayBuffer` değişikliğinin BLOB okumaya etkisi.
- **Bitti sayılır:** lisans raporu ve doğrulama sonuçları dokümanda.

### A26.2 · Mod A kodu ve birim testleri
- `fontCache.ts` Mobil mimari §7.1'deki gibidir: aile adı `QPC_P{sayfa:3 hane}_{sürüm}`; font BLOB'u ayrı salt okunur bağlantıdan (A23 `src/db/packs.ts`) okunup `Paths.cache/mutalaa/qpc/` altına yazılır; `Font.loadAsync`; etkin küme `MAX_ACTIVE = 12` (ölçümle ayarlanır); okuma yönünde iki ileri, bir geri ısıtma; sayfa sınırı 1–604.
- Sayfa → paket: sayfa, ilk âyetinin bulunduğu cüzün paketine girer (İçerik paketleri §3.5); cüz verisi `core`'dan (A11 tablosu).
- Satır düzeni: satır başına bir `View`, kelimeler mantıksal sırayla ayrı `Text`, `flexDirection: 'row-reverse'`; `I18nManager` çevrilmez; glif metni `allowFontScaling={false}`; büyütme sayfa yakınlaştırmasıyla.
- İsabet testi (`hitTest.ts`): isabet alanı satır yüksekliğine ve en az 44 pt genişliğe büyür. Kısa dokunuş kelime kartını (A25), 350 ms uzun basış ve sürükleme seçimi başlatır; jest gerektirmeyen "Seç" yolu A25'teki akışla aynıdır.
- Paralel Unicode katmanı: glif katmanı ekran okuyucudan gizlidir. Her âyet için görünmez bir erişilebilir öğe Türkçe adres etiketi ve `core`'daki Arapça Unicode metni taşır; iOS'ta `accessibilityLanguage="ar"`. Kopyalama seçilen çapaların Tanzil Unicode metnini kopyalar; glif kodu asla kopyalanmaz.
- Etkin âyet ve kelime glifler üzerinden vurgulanır; kullanıcı vurguları kelime çapasıyla glife eşlenir (veri A30'da gelir).
- **Bitti sayılır:** birim testleri yeşil: `familyName`, `hitTest` (dar kelimede 44 pt genişleme, en yakın merkez), sayfa → cüz eşlemesi, ısıtma sınırları, kopyalamanın Unicode metin döndürmesi.

### A26.3 · Bayrak, mod listesi ve eksik paket
- `mushafA` `'paket'` kuralıyla açılır: derleme türünde görünür bir `mushaf-a-cuz-*` paketi yoksa kapalıdır (`isPackVisible`, A23). Paketler `bekliyor` kaldıkça yalnız `dev`'de görünebilir; `internal` ve `public`'te Mod A seçeneği listelenmez (Mobil mimari §7.4; Yayın kapısı §7.4).
- Mod A seçiliyken cüz paketi kurulu değilse sayfa Mod C ile çizilir ve üstte `reader.cuzMissing` şeridi görünür: "Bu cüzün Medine düzeni indirilmedi · İndir". "İndir" A29'un kuyruğuna devreder; A29'a kadar Depolama rotasını açar. Okuma hiçbir zaman beklemez.
- **Bitti sayılır:** RNTL testleri yeşil: görünür paket yokken seçenek listede yok; paket görünür ama cüz kurulu değilken Mod C ve şerit; `internal` bayrağıyla `bekliyor` paket gizli.

### Bekleme noktası
Aşağıdakilerin hepsi sağlanmadan A26.4'e geçilmez. Biri eksikse aşama ilerleme dosyasında `engelli` olarak, eksik koşul notuyla kaydedilir ve burada durur; A26.1–A26.3 tamamlanmış sayılır. Koşullar sağlanınca `/asama A26.4` ile sürdürülür.
1. İ-06 tamam: QF Developer Console hesabı açık; şartlar okundu ve kabul edildi.
2. MM-1 (AS-02): fontların kendi depomuzdan cüz paketiyle indirilmesinin QF şartlarına uyduğu yazılı olarak teyit edildi (yazışma 3, `/yazisma`) ve `qpc-v2-font` kaydı `/karar` ile güncellendi.
3. MM-2 (ÇŞ-6): satır düzeni verisinin kaynağı ve lisansı seçildi; kaynak `kisitlar.hazir_vt_yasak` taşımıyor (P-02). QF API'den gelen düzen verisi bu koşulu sağlamaz (Mobil mimari §7.1).

Kurul'un Medine fontlarına bakışı (AS-03) bu noktayı durdurmaz; yalnız `public` derlemeyi etkiler.

### A26.4 · Cüz paketleri (bekleme noktasından sonra)
- Paket DDL'i `packages/content-schema/sql/` altına İçerik paketleri §3.5'e göre yazılır: `page_font`, `page_line`, `glyph_word`.
- `hat-gelistirici`: seçilen kaynaktan fontları ve düzeni alır, editoryal `page_map` satırlarına `line`, `line_type`, `centered` ve `glyphs` alanlarını yazar; tarihli lisans kopyası `pipeline/sources/licenses/` altında durur.
- `sunucu-gelistirici`: Yayınlayıcı `mushaf-a-cuz-{01..30}` paketlerini üretir; P-01, P-02 ve P-03 uygulanır; QF atfı `attribution` tablosuna yazılır.
- `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev` ile paketler yalnız `dev` manifestine girer.
- **Bitti sayılır:** `dev` manifestinde 30 `mushaf-a-cuz-*` girişi var; `internal` ve `public` manifestlerinde yok.

### A26.5 · Cihaz ölçümleri ve görsel denetim (bekleme noktasından sonra)
- Cüz paketleri geliştirici menüsündeki basit indirme düğmesiyle kurulur (öneri; asıl kuyruk A29'dadır).
- `mobil-gelistirici` ölçer ve dokümana işler: woff2 ya da TTF ile paket boyutu (MM-3); 604 sayfa baştan sona çevrilirken bellek (MM-4; bütçe ortalama < 200 MB, Mobil mimari §9); tam satırların iki yana yaslanması ve ortalanmış satırlar. Bütçe aşılırsa `@shopify/react-native-skia` değerlendirmesi Açık soru olarak `/karar`'a götürülür.
- Görsel denetim: 1. sayfa ve Bakara 255'in sayfası Mod A'da, üç temada; kelimeye dokununca kelime kartı; "Seç" yolu. `arayuz-denetcisi` TalkBack ile âyet öğesinin Türkçe etiket ve Arapça metinle okunduğunu denetler.
- **Bitti sayılır:** ölçümler dokümanda; görüntüler ve rapor `.tmp/a26/` altında.

## Kabul ölçütleri
- [ ] Lisans raporu ilerleme kaydında; A26.1 doğrulamaları dokümanda.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: `familyName`, `hitTest`, sayfa → cüz, ısıtma sınırları, Unicode kopyalama, mod listesi, eksik paket şeridi.
- [ ] `internal` ve `public` bayrağıyla Mod A seçeneği yok; `dev`'de görünür paket yoksa da yok (test).
- [ ] Bekleme noktası: koşullar sağlanmadıysa ilerleme dosyasında `engelli` durumu ve eksik koşul yazılı.
- [ ] (Bekleme sonrası) `dev` manifestinde 30 `mushaf-a-cuz-*` girişi; `internal` ve `public` manifestlerinde 0.
- [ ] (Bekleme sonrası) MM-3 ve MM-4 ölçümleri dokümanda; Mod A görüntüleri ve `arayuz-denetcisi` raporu temiz.

## Doğrulama
```bash
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile lint
# Bekleme noktasından sonra:
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -oE '"mushaf-a-cuz-[0-9]{2}"' | sort -u | wc -l
curl -s http://localhost:8333/mutalaa/internal/manifest.json | grep -c "mushaf-a-cuz" || true
curl -s http://localhost:8333/mutalaa/public/manifest.json | grep -c "mushaf-a-cuz" || true
mkdir -p .tmp/a26
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://oku/fihrist"
adb shell input text "1:1"
adb shell input keyevent 66
adb exec-out screencap -p > .tmp/a26/mod-a-sayfa-1-kagit.png
```
Yerel depoda `internal` ya da `public` manifesti yoksa son iki `curl` boş döner; bu da "girmedi" sayılır. Yayınlayıcının `--dry-run` kapı raporu ayrıca okunur. Görüntüden önce "Aa" › Çizim yolu'ndan Mod A seçilir; görüntü üç tema için tekrarlanır.

## Dikkat
- QPC fontları "All rights reserved" taşır; yalnız QF şartlarıyla ve atıfla kullanılır. GitHub aynalarından toplu kopya alınmaz (Kapsam ve fazlar §6.3).
- QF API içeriği bir haftadan uzun önbelleğe alınmaz ve hazır veritabanı olarak dağıtılmaz; gömmesi de yapılmaz (`embed_ok = false`). Bu yüzden düzen verisi QF API'den pakete konmaz.
- `bekliyor` paket yalnız `dev`'de görünür. `public` için ayrıca Kurul onayı gerekir; Kurul Medine fontlarını kabul etmezse Mod A `public`'e girmez ve Mod C kalır (Yayın kapısı §7.4).
- Glif kodu kelimeyle ilgisiz bir sunum kod noktasıdır; kopyalama, arama ve ekran okuyucu her zaman Tanzil Unicode metnini kullanır.
- Kur'an metni elle yazılmaz; paralel katmandaki metin `core`'dan okunur.
- Tecvid renkleri (COLRv1, V4) bu aşamada açılmaz; `tecvidRenkleri` bayrağı kapalı kalır.
- Commit kapsamları `mobile`, `content-schema`, `pipeline`, `publisher`.

## İnsan adımları
- İ-06 · Quran Foundation Developer Console hesabı ve şartların kabulü: A26.4'ten önce gerekir.
- QF'ye yazışma 3 (fontların cüz paketiyle dağıtımı, düzen verisi, atıf ifadesi): `/yazisma` ile taslak hazırlanır, kullanıcı gönderir; cevap bekleme noktasının 2. koşuludur. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/mobile/src/features/reader/mushaf-a/`: `fontCache.ts`, `hitTest.ts`, `useWordGestures.ts`, satır düzeni ve Unicode katmanı bileşenleri, testler
- Mod listesi ve `reader.cuzMissing` şeridi; geliştirici menüsünde indirme düğmesi (öneri)
- Bekleme sonrası: `packages/content-schema/sql/` Mod A DDL'i, hat ve Yayınlayıcı ekleri, `pipeline/sources/` kaydı ve lisans kopyası
- Lisans raporu özeti ve ölçüm sonuçları; `.tmp/a26/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A26-mushaf-a.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A25](./A25-secim-kelime-karti-baglantilar.md) · Sonraki: [A27](./A27-ses-sistemi.md)
