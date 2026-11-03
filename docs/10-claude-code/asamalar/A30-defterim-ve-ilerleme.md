# A30 · Defterim, hatim ve yedekleme

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · [A25](./A25-secim-kelime-karti-baglantilar.md) · **İnsan adımı:** —
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `metin-denetcisi` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A30`

## Amaç
"Okuma simetrisi" çekirdeğini (K-30) cihazda kurar: isimli yer imleri, beş renkli vurgu, `[[q:2:255]]` bağlantılı Markdown notlar, karışık kaynaklı koleksiyonlar; hatim (30 cüz ızgarası, 604 sayfa çubuğu, aynı anda birden çok hatim), okuma geçmişi, varsayılan kapalı yumuşak seri ve Gizli mod. Kayıtlar senkrona hazır şemaya yazılır (K-15), dosyayla yedeklenip geri yüklenir ve içerik güncellemesinden sonra yeniden çapalanır; hiçbir kayıt sessizce kaybolmaz (B-08).

## Okunacak belgeler
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §2 şema, §3 HLC, §4 birleştirme, §5 not çakışması arayüzü, §6 yedek, §7 ayarların kapsamı
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 ofsetler, §9 yeniden çapalama, §12 sure adları ve insan yazımları
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 eylem çubuğu, §14 riyâsız ilerleme
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 (`defterim/*`, `not/[id]`, `hatim/yeni`, `ayarlar/ilerleme`), §3 Defterim satırları, §6 İlerleme ve gizlilik
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.3 vurgu renkleri, §6 `HighlightSwatch`, `HatimGrid`, `HatimBar`, `NoteLinkChip`, §7 tezhip kuralı
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §8 çapa denetimi, §9 paketi silinmiş kayıt
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.8, §4.9, §8 B-08
- [Gizlilik](../../07-yayin/02-gizlilik.md): §2.1 veri envanteri, §2.7 dışa aktarma
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): Expo'ya bağlı paketlerin kurulumu ve sürüm denetimi

## Kapsam
**Yapılır**
- Kitaplık tedariki ve doğrulaması (A30.0): fark, yaklaşık eşleşme, Markdown ve dosya paylaşımı kitaplıkları.
- Yer imi, vurgu, not ve koleksiyon kayıtları; okuyuculardaki işaretleri (A24 bunları A30'a bırakır) ve A25'in eylem çubuğuna Vurgula ve Not eylemleri.
- A21'in yer tutucu rotaları doldurulur: Defterim sekmesi, koleksiyon ve hatim ayrıntısı, not düzenleyici, hatim oluşturma, `ayarlar/ilerleme`.
- Hatim ilerlemesi, okuma geçmişi, seri ve Gizli mod.
- Yedek dışa ve içe aktarma (JSON dosyası) ve içe aktarmadaki not çakışmasının gösterimi.
- Yeniden çapalama ve `device.db` içinde `anchor_resolution` önbelleği (KV-5 önerisi).

**Yapılmaz**
- Hesap, senkron, giden kutusu ve sunucu: A35, A36 (v1.x). v1'de `outbox` yazılmaz.
- Seçim ve eylem çubuğunun kendisi: A25. Paket güncellemesi tetiği: A29. "Hata raporları" anahtarı ve "Verilerimi sil": A32.
- Kelime defteri (`vocab`), okuma planları, hatırlatıcılar, görsel içerik kartı: v1.x. PDF dışa aktarma: faz atanmadı.

## Tedarik

Araştırma tarihi: 2 Kasım 2026 (ön ölçümler yapıldı; kalanlar A30.0'da tamamlanır). Sürümler npm kaydından (`dist-tags.latest`), Expo'ya bağlı modüllerin sabitleri `bundledNativeModules.json` dosyasından (`expo@58.0.22`, A21 ile aynı), etiketler ve commit'ler `git ls-remote` ile okundu. Aşama yalnız kitaplık alır; içerik metni, veri dosyası, yazı tipi, ses, görsel, hesap ya da anahtar gerekmez. Kur'an metni, sure adları ve sayfa eşlemesi `core` paketinden (A13, A11) gelir.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Not sürümlerini kelime düzeyinde karşılaştırma (KV-6; içe aktarmadaki not çakışması, 03-veri/04 §5) | `diff` (jsdiff) 9.0.0 (13 Nisan 2026; [npm kaydı](https://registry.npmjs.org/diff/9.0.0), [GitHub](https://github.com/kpdecker/jsdiff), etiket `v9.0.0`); tipleri pakette, ESM | `pnpm --filter @mutalaa/mobile add diff` (A15 editör paneli aynı kitaplığı kendi paketinde kullanır) | Ölçüldü (2 Kasım 2026): arşiv SHA-1 `297c31cd7c280f13dfe335791ec2063bd4a73a6f` kayıttaki `dist.shasum` ile aynı; 136 dosya, 615.597 bayt, bağımlılık yok. Node 24.21.0'da Türkçe İ/i ve açıkça sentetik Arapça harf dizisiyle: `diffWordsWithSpace` Arapça sözcüğü harf harf böler, boşluk belirteçli `diffArrays` sözcük düzeyinde fark verir (seçilen yol). `intlSegmenter` yalnız `diffWords` içindir ve Hermes `Intl` belgesinde `Intl.Segmenter` geçmez | `fast-diff` 1.3.0 (npm; karakter düzeyi); `@sanity/diff-match-patch` 3.2.1 (npm) |
| Cihazda yaklaşık eşleşme (ÇŞ-5; yeniden çapalama, A30.6) | `approx-string-match` 2.0.1 (9 Ekim 2026; [npm kaydı](https://registry.npmjs.org/approx-string-match/2.0.1), [GitHub](https://github.com/robertknight/approx-string-match-js), etiket `v2.0.1` = commit `0473f1b722089e1c4cfcd11ce5c079618f360d6e`); tipleri pakette, ESM | `pnpm --filter @mutalaa/reader-core add approx-string-match` | Ölçüldü (2 Kasım 2026, Node 24.21.0): arşiv SHA-1 `bd5fef0a952e8d078f95f7e02b748095985a7401` kayıtla aynı; 5 dosya, 18.461 bayt, bağımlılık yok. `search(text, pattern, maxErrors)` `{ start, end, errors }` dizisi döner (Myers bit-paralel; UTF-16 kod birimi üzerinde). Sentetik rastgele metinde (2.000–50.000 karakter), 1.000 karakterlik alıntı ve `maxErrors` 150 ile: %0, %5, %10, %15 değişimde bulundu (benzerlik 1,00; 0,95; 0,90; 0,86), %20 değişimde ve alakasız alıntıda eşleşme yok; en çok 1,4 ms. Cihazda (Hermes) süre ölçümü kullanıcıya bırakılır | `fastest-levenshtein` 1.0.16 (npm; yalnız uzaklık, konum vermez); kendi Levenshtein'imiz |
| Not gövdesinin Markdown gösterimi (A30.3) | `react-native-marked` 8.3.3 (27 Ekim 2026; [npm kaydı](https://registry.npmjs.org/react-native-marked/8.3.3), [GitHub](https://github.com/gmsgowtham/react-native-marked), etiket `v8.3.3`); `marked` 18.1.2 ile gelir, tipleri pakette | `pnpm --filter @mutalaa/mobile add react-native-marked` (eş bağımlılık `react-native-svg` A22'de kurulur) | Kayıt (2 Kasım 2026): eş bağımlılıklar `react-native >=0.76.0` ve `react-native-svg >=12.3.0` (SDK 58 sabiti 15.16.0); README'de özel çizici (`renderer`), özel belirteçleyici (`tokenizer`) ve JSX biçimli bileşen gömme var. `[[…]]` bağlantısının `NoteLinkChip` olması ve sağdan sola metin A30.0'da jest-expo ile ölçülür | `@ronradtke/react-native-markdown-display` 9.0.3 (29 Haziran 2026; npm; `markdown-it` 14); küçük kendi dönüştürücümüz |
| Yedek dosyasını paylaşma ve içe aktarırken seçme (A30.5) | `expo-sharing` ~58.0.21 (28 Ekim 2026), `expo-document-picker` ~58.0.4 (npm `latest`, 1 Ekim 2026) ve `expo-file-system` ~58.0.13 (A23'te kurulu; JSON yazma ve okuma); belgeler: [Sharing](https://docs.expo.dev/versions/v58.0.0/sdk/sharing/), [DocumentPicker](https://docs.expo.dev/versions/v58.0.0/sdk/document-picker/), [FileSystem](https://docs.expo.dev/versions/v58.0.0/sdk/filesystem/) | `pnpm --filter @mutalaa/mobile exec expo install expo-sharing expo-document-picker` (sürümü `expo` belirler) | Ölçüldü (2 Kasım 2026): `bundledNativeModules.json` @ `expo@58.0.22` değerleri `~58.0.21`, `~58.0.4`, `~58.0.13` ve npm `latest` ile aynı; belge sayfaları SDK 58 için açılıyor (HTTP 200): `Sharing.shareAsync(url, options)` (`mimeType`, `UTI`, `dialogTitle`), `Sharing.isAvailableAsync()`, `getDocumentAsync` (`copyToCacheDirectory`). Çağrı imzaları A30.0'da jest-expo altında sınanır | `expo-file-system` `File.pickFileAsync` (seçici için ek paket gerekmez); paylaşım için React Native `Share` (çekirdek; yalnız metin, dosya taşımaz) |
| Satır kimliği (UUIDv7), HLC ve tek işlemde yazma yardımcısı | A23 çıktısı (`uuid` 14.0.3, `expo-crypto` 58.0.7, `packages/reader-core/src/sync/hlc.ts`) | A23'te kurulu; bu aşama yeni kitaplık eklemez | A23 Tedarik tablosu | — |
| `HatimGrid`, `HatimBar` çizimi ve hatim tamamlama ekranının tezhip çerçevesi | `react-native-svg` 15.16.0 (SDK 58 sabiti; npm 15 Ekim 2026) ve A22'nin `TezhipFrame` bileşeni (tek renkli SVG, `currentColor`) | A22'de kurulur; bu aşama yeni kitaplık eklemez | npm `latest` 15.16.0 = `bundledNativeModules.json` değeri; `react-native-marked` aynı eş bağımlılığı kullanır | 30 hücrelik ızgara için `View` ile çizim |
| Birim ve bileşen testleri | `jest-expo` ~58.0.13, `jest` 30.5.2, `@testing-library/react-native` 14.1.0 (A21 seçimi) | A21'de kurulu | A21 Tedarik tablosu | — |

Kendimiz yapacağımız işler: yeniden çapalama akışı (03-veri/01 §9: `successors`, özet, alıntı, bağlam ve ofset yakınlığı, komşu birim; `approx-string-match` üstünde ince sarmalayıcı), yedek biçimi ve birleştirmesi (03-veri/04 §6), not bağlantısı ayrıştırıcısı ve kanonikleştirme (`packages/anchors` ile), not karşılaştırması için boşluk belirteçleyici, hatim küme birleşimi ve otomatik işaret, okuma geçmişi, seri ve Gizli mod, kayıt yardımcıları ve Defterim ekranları. Hazır karşılıkları yoktur; hepsi uygulamaya özgüdür.

## Adımlar
### A30.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını (`curl -sIL --max-time 30 <adres>`; GitHub depoları için `git ls-remote`; npm için `https://registry.npmjs.org/<paket>/<sürüm>`) ve sürümlerin güncel olduğunu (`dist-tags.latest`; Expo'ya bağlı modüller için `bundledNativeModules.json` @ güncel `expo` sürümü) doğrula. Açılmayan adresin ya da güncelliğini yitiren sürümün yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Bu aşama içerik dosyası almaz: `data/gelen/` altına indirme ve `pipeline/sources/` kaydı yoktur. Kitaplıkları tablodaki alma yollarıyla kur; sürümler `pnpm-lock.yaml` içinde sabitlenir ve paket kaydıyla (`npm view <paket>@<sürüm> dist.shasum`) karşılaştırılır.
- Dört deneme (jest; yalnız sentetik metin; Hermes üzerinde süre ölçümü kullanıcıya bırakılır): (1) `diff` ile Türkçe İ/i ve açıkça sentetik Arapça harf dizisinde boşluk belirteçli `diffArrays`; (2) `approx-string-match` ile 0,85 eşiği ve 1.000 karakterlik alıntıda süre; (3) `react-native-marked` özel belirteçleyici ve çizicisiyle `[[q:2:255]]` bağlantısının `NoteLinkChip` olması, sağdan sola metin (RNTL); (4) `expo-sharing` ve `expo-document-picker` modüllerinin jest-expo altında içe aktarılması ve çağrı imzaları.
- Sonuçlar `## Tedarik` tablosundaki ilgili hücrelere yazılır; ön ölçümler yeniden çalıştırılıp fikstür testine çevrilir.
- **Bitti sayılır:** Tablodaki her adres açılıyor, sürümler `pnpm-lock.yaml` içinde sabit ve paket kaydıyla aynı, dört deneme yeşil ve ölçümler tabloya yazıldı.

### A30.1 · Önkoşul, doğrulamalar ve kararlar
- A23 çıktısını denetle: `packages/content-schema/src/user/` (her tabloda `id`, `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id`), `packages/reader-core/src/sync/hlc.ts`, tek işlemde UUIDv7 `id`, yeni `hlc` ve `device_id` yazan yardımcı (KV-4 A23.1'de doğrulandı).
- A30.0 sonuçları kullanılır, araştırma yinelenmez: ÇŞ-5 → `approx-string-match`; 03-veri/04 §6'daki paylaşım ve belge seçici modülleri → `expo-sharing` ve `expo-document-picker`; KV-6 → `diff` (`diffArrays` ve boşluk belirteçleyici); Markdown gösterimi → `react-native-marked`. ÇŞ-5 ve KV-6 "Doğrulanacak" maddeleri `/belge-esitle` ile çözüldü olarak işlenir.
- Kullanıcıya sorulur ve `/karar` ile yazılır:
  1. Okuma geçmişi ve seri için şemada tablo yok (03-veri/04 §2). Öneri: `user.db` içinde ortak sütunlu `reading_day(day, context, first_anchor, last_anchor)`; senkron kapsamı 03-veri/04 §7'ye eklenir.
  2. Gizli modun kapsamı belgelerde artık aynıdır, karar gerekmez (01-urun/02 §14, 03-veri/04 §7): okuma geçmişi, otomatik hatim işaretlemesi ve seri kaydı tutulmaz; okuma konumu ve elle hatim işareti sürer.
  3. Birden çok hatim açıkken otomatik işaretin hangi hatime yazılacağı tanımsız. Öneri: Defterim'de "etkin" seçilen hatim.
  4. Yer imi ekleme yeri eylem çubuğu listesinde yok (01-urun/02 §3). Öneri: eylem çubuğunda "Yer imi" ve okuyucu üst çubuğu menüsünde "Bu sayfaya yer imi".
- **Bitti sayılır:** A30.0 sonuçları işlendi ve 1., 3., 4. kararlar yazılı; şema eklentileri drizzle-kit göçü olarak planlandı.

### A30.2 · Yer imi, vurgu ve koleksiyon
- Her değişiklik A23'ün yazma yardımcısıyla tek işlemdir. Silme yumuşaktır (`deleted_at`) ve "Geri al" sunar.
- Kayıt oluşurken paketten `label`, `excerpt` (ilk 160 kod noktası) ve `content_hash` kopyalanır; âyet aralığında (`q:2:255-257`) `content_hash` NULL'dur. Cihaz özeti yeniden hesaplamaz.
- Vurgu: renk yuvası 1–5; varsayılan adlar Önemli, Ezber, Ders, Soru, Tefekkür; hazır takım Akide, İbadet, Ahlak, Tarih, Dil; adlar `setting` tablosunda. Kur'an aralığı kelime konumu, metin aralığı kod noktasıdır (`toUnitSpan`). `quote` en çok 1.000 kod noktası (uzunsa ilk ve son 500), `prefix` ve `suffix` 32'şer kod noktası. Paragraf sınırını aşan seçim birim başına satıra bölünür ve `group_id` ile bağlanır.
- Gösterim: okuyucu görünür birimlerin kayıtlarını `WHERE anchor IN (…)` ile tek sorguda alır (`useLiveQuery`) ve `HighlightInput.user` olarak çizicilere verir. Vurgu zemin tonu, 1,5 pt alt çizgi ve kenar simgesiyle çizilir; renk tek başına anlam taşımaz; Mod B'de âyet kutusunun kenarında işaret.
- Koleksiyon: ad, renk, `sort_key`; silinince bağlı yer imlerinin `collection_id` değeri NULL olur.
- **Bitti sayılır:** Oluşturma, renk, bölünmüş seçim ve "Geri al" testleri yeşil; Mod C ve meal görüntüleri üç temada `arayuz-denetcisi` onaylı.

### A30.3 · Notlar
- `app/not/[id].tsx` kök düzeyinde tam ekran modaldır (`id` = `yeni` ya da UUIDv7); okuyucudan açılınca sekme değişmez; kapatırken taslak kendiliğinden kaydedilir.
- Gövde Markdown'dır ve `react-native-marked` ile çizilir (A30.0). `[[q:2:255]]` ve `[[konu:sabir]]` bağlantıları özel belirteçleyici ve çizici ile `NoteLinkChip` olarak çözülür (çözüldü · çözülmedi); dokunuş hedefe A25'in atlama yoluyla gider. `[[Bakara 255]]` gibi insan yazımı kayıtta kanonik çapaya çevrilir (03-veri/01 §12); A28'in sure çözücüsü kullanılır, A28 henüz yoksa çözücü `packages/reader-core` içine burada yazılır ve A28 onu kullanır. `sure` tablosu boşsa (A11.3 tamamlanmadıysa) yalnız `[[2:255]]` biçimi çevrilir; ad içeren test A11.3'ten sonra açılır (`mobil-ekran`, sure adı kuralı).
- Not kelime aralığına, âyete, paragrafa ya da hadise bağlı olabilir ya da bağımsızdır (`anchor` NULL); `tags` JSON dizisi; isteğe bağlı `highlight_id` ve koleksiyon.
- **Bitti sayılır:** Bağlantı ayrıştırma ve kanonikleştirme testleri yeşil; düzenleyici görüntüsü onaylı.

### A30.4 · Defterim, hatim ve ilerleme
- `defterim/index.tsx`: `SegmentedControl` ile yer imi, vurgu, not, koleksiyon, hatim ve ilerleme bölümleri; boşken "Bir âyete dokun, Vurgula'yı seç". Paketi silinmiş kayıt adresi ve alıntısıyla görünür, içerik yerine "Bu içerik cihazda yok · İndir".
- `defterim/koleksiyon/[id].tsx`; `defterim/hatim/[id].tsx` (`HatimGrid` 30 cüz, `HatimBar` 604 sayfa, değerler yazıyla da); `hatim/yeni.tsx` (ad, isteğe bağlı bitiş tarihi; aynı adda hatim varsa uyarı). Silinmiş kayıtta "Bu kayıt silindi · Geri al".
- Hatim `(layout = 'medine-604', page)` ile tutulur; cüz ve sayfa sınırları `core`'dan okunur. `page_map` yoksa hatim ekranı bunu açıkça yazar (03-veri/03 §3.2; AS-10).
- Otomatik işaret: sayfa ekranda 20 saniye kalıp çevrilince okunmuş sayılır (öneri, OD-9); ayar "Hatim sayfalarını otomatik işaretle: Açık"; elle işaret her zaman vardır. Tamamlama ekranında ince tezhip çerçevesi (`TezhipFrame`) bulunur; ekran sayı paylaşmayı önermez.
- Okuma geçmişi (varsayılan açık) ve seri (varsayılan kapalı) A30.1 kararıyla yazılır. Seri yalnız "Bu hafta 4 gün okudun." gibi yumuşak dille görünür; kırılan seri uyarısı, kayıp korkusu ve karşılaştırma yoktur (K-25).
- Gizli mod açıkken okuma geçmişi, otomatik hatim işaretlemesi ve seri kaydı tutulmaz; okuma konumu ve elle hatim işareti sürer; mevcut kayıtlar gizlenir, silinmez (01-urun/02 §14). Gizli mod `setting` tablosundadır.
- `ayarlar/ilerleme.tsx`: bu satırlar ve yedek satırları. "Hata raporları" ve "Verilerimi sil" satırları A32'de eklenir.
- **Bitti sayılır:** Hatim küme birleşimi, otomatik işaret ve Gizli mod testleri yeşil; hatim ve Defterim görüntüleri onaylı.

### A30.5 · Yedek: dışa ve içe aktarma
- Biçim 03-veri/04 §6: `format: "mutalaa-yedek"`, `format_version: 1`, `user_schema_version`, `app_version`, `created_at`, `device_id`, `tables` (`bookmark`, `highlight`, `note`, `reading_position`, `hatim`, `hatim_page`, `collection`, `setting` ve A30.1'de eklenen tablo). Silinmiş satırlar girer; `outbox`, `sync_state` ve `device.db` girmez. Dosya adı `mutalaa-yedek-YYYY-MM-DD.json`; `expo-file-system` ile önbelleğe yazılır ve `expo-sharing` `shareAsync` ile (`mimeType: 'application/json'`, `UTI: 'public.json'`) paylaşım menüsünden kaydedilir.
- İçe aktarma `expo-document-picker` belge seçicisiyle açılır (`copyToCacheDirectory`, dosya `expo-file-system` ile okunur); önce önizleme ("142 vurgu, 37 not, 12 yer imi"). Varsayılan birleştirmedir ve §4 kurallarını kullanır; aynı dosyayı iki kez yüklemek bir şey değiştirmez. Aynı `id` ile farklı not gövdesinde cihazdaki asıl kalır, yedekteki `conflict_of` ile çakışma kopyası olur ve §5'teki şerit ve karşılaştırma (`diff`) görünür. "Tümünü değiştir" onay ister. Dosyanın `user_schema_version` değeri uygulamanınkinden büyükse işlem reddedilir ve güncelleme istenir; küçükse bellekte göç uygulanır.
- Dosya kişisel veridir; hiçbir sunucuya gitmez ve ekran bunu kullanıcıya söyler.
- **Bitti sayılır:** Gidiş-dönüş, idempotentlik, sürüm reddi ve çakışma kopyası testleri yeşil.

### A30.6 · Yeniden çapalama (B-08)
- Algoritma 03-veri/01 §9 akışıdır (öneri yer: `packages/reader-core`): kullanım dışı çapa → `successors` ile yeni çapa ve aralık; özet eşit → `tam`; alıntı yeni metinde bir kez geçiyor → `tasindi`; birden çok → bağlamı en benzer, eşitlikte uzunluk oranıyla ölçeklenmiş eski ofsete en yakın; hiç → yaklaşık eşleşme (`approx-string-match`: `search(metin, alıntı, ceil(0,15 × alıntı uzunluğu))`) ve kod noktası üzerinde `1 − düzenleme_uzaklığı / max(uzunluk)` ≥ 0,85 → `tasindi`; değilse komşu birimler (`ord` ±2); değilse `bulunamadi`.
- A29'un paket güncelleme olayıyla çalışır. Sonuç yalnız `anchor_resolution` tablosuna yazılır; senkronlanan kayıt yalnız kullanıcı eylemiyle değişir.
- Defterim'de değişen kayıt "Metin güncellendi, vurgunun yerini kontrol et" etiketini, bulunamayan kayıt rozeti alır; eylemler "Yeniden seç", "Birime bağla", "Sil". Kur'an biriminde özet farkı hat hatasıdır (03-veri/01 §9): kayıt `tam` sayılmaz ve paket kimliği ile sürümünü taşıyan, kişisel veri içermeyen bir hata kaydı gönderilir (öneri).
- Test fikstürü yalnız sentetik metindir ("Deneme paragrafı 1 …"): değişmeyen, yazımı düzeltilen, bölünen, birleşen, silinen, komşuya taşınan ve bulunamayan paragraflar.
- **Bitti sayılır:** B-08 testi: fikstürdeki her kayıt `tam`, `tasindi` ya da `bulunamadi` oluyor; hiçbir kayıt kaybolmuyor; `user.db` satırları değişmiyor.

## Kabul ölçütleri
- [ ] A30.0 tamam: `## Tedarik` tablosundaki sürümler `pnpm-lock.yaml` içinde sabit, ölçüm hücreleri dolu; Expo'ya bağlı modüller `expo install --check` ile SDK 58 tablosuna uyuyor.
- [ ] `pnpm --filter @mutalaa/content-schema test`, `pnpm --filter @mutalaa/reader-core test` ve `pnpm --filter @mutalaa/mobile test` yeşil; yeni testler A30.2–A30.6'nın "Bitti sayılır" maddelerini kapsıyor.
- [ ] Yeni ya da değişen her `user.db` tablosunda altı ortak sütun var; A23'ün göç fikstürü testleri yeni göçlerle de geçiyor (07-yayin/03 §6).
- [ ] Vurgu beş renkte, adıyla ve simgesiyle çiziliyor; Mod C, Âyet âyet ve meal görüntüleri üç temada onaylı (`.tmp/a30/`).
- [ ] Not içindeki `[[q:2:255]]` dokunuşla hedefi açıyor; `[[2:255]]` kayıtta `[[q:2:255]]` oluyor; `[[Bakara 255]]` dönüşümü A11.3'ten sonra sınanıyor, o zamana kadar atlandığı ilerleme notunda (test ve görüntü).
- [ ] Hatim ayrıntısı 30 cüzü ve 604 sayfayı yazıyla da veriyor; iki hatim aynı anda tutulabiliyor.
- [ ] Seri varsayılan kapalı; Gizli mod açıkken okuma geçmişi, otomatik hatim işareti ve seri kaydı yazılmıyor, okuma konumu yazılıyor (birim testi).
- [ ] Yedek gidiş-dönüşünde kayıp yok; aynı dosya ikinci kez yüklenince satır sayıları ve `hlc` değerleri değişmiyor.
- [ ] B-08 yeniden çapalama testi yeşil; `anchor_resolution` dışındaki tablolar değişmiyor.
- [ ] ÇŞ-5 ve KV-6 çözüldü; 03-veri/01 §13, 03-veri/04 §5, §6 ve §9 `/belge-esitle` ile eşitlendi.
- [ ] Testlerde ve fikstürlerde hafızadan yazılmış Kur'an, meal, hadis ya da Risale metni yok (`metin-denetcisi` raporu).

## Doğrulama
```bash
pnpm --filter @mutalaa/content-schema test
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm --filter @mutalaa/mobile exec expo install --check   # Expo'ya bağlı modüller SDK 58 tablosuna uyuyor mu
pnpm lint && pnpm typecheck
mkdir -p .tmp/a30
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"
adb exec-out screencap -p > .tmp/a30/vurgu.png           # vurgu, not ve yer imi işaretleri
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://defterim"
adb exec-out screencap -p > .tmp/a30/defterim.png
```

## Dikkat
- Çapalar yalnız `packages/anchors` ile ayrıştırılır ve biçimlenir (`capa-gramer`). Ofset kod noktasıdır; UTF-16 dönüşümü yalnız `cpToUtf16` ve `utf16ToCp` ile yapılır. `approx-string-match` UTF-16 kod birimi üzerinde çalışır: sonuç ofsetleri `utf16ToCp` ile kod noktasına çevrilir.
- `quote`, `prefix`, `suffix` ve `excerpt` paketten olduğu gibi kopyalanır; NFC ya da başka dönüşüm uygulanmaz (`metin-butunlugu`).
- Testlerde Kur'an, meal, hadis ya da Risale metni yazılmaz. Arapça örnek gerekiyorsa çalışma anında paketten okunur ya da açıkça sentetik harf dizisi kullanılır (CLAUDE.md kural 2).
- Not karşılaştırmasında `diffWords` yerine boşluk belirteçli `diffArrays` kullanılır; böylece Arapça sözcükler harf harf bölünmez (Hermes'te `Intl.Segmenter` yoktur).
- İlerleme gizlidir ve paylaşılmaz; liderlik tablosu, kırılan seri uyarısı ve sayı paylaşımı yoktur (K-25).
- Yedek dosyası ve not metni kişisel veridir; günlüğe ve Sentry'ye girmez.
- Atlama zinciri açıkken `reading_position` yazılmaz (A24, A25); hatim işareti bu kuralı bozmaz. Uygulanmış göç değiştirilmez; yeni göç eklenir (A23).
- Commit kapsamları: `mobile`, `content-schema`, `reader-core`.

## İnsan adımları
- Yok. A30.1'deki üç karar (1, 3, 4) plan onayıyla birlikte kullanıcıya sorulur.

## Çıktılar
- `apps/mobile/app/(tabs)/defterim/` (`_layout.tsx`, `index.tsx`, `koleksiyon/[id].tsx`, `hatim/[id].tsx`), `apps/mobile/app/not/[id].tsx`, `apps/mobile/app/hatim/yeni.tsx`, `apps/mobile/app/(tabs)/ayarlar/ilerleme.tsx`
- `apps/mobile/src/features/notebook/` (kayıtlar, Defterim, hatim, ilerleme, yedek)
- Şema eklentileri: `packages/content-schema/src/user/`, `apps/mobile/src/db/device/schema.ts` (`anchor_resolution`); göçler `apps/mobile/src/db/migrations/user/` ve `.../device/`
- `packages/reader-core` içinde yeniden çapalama ve not bağlantısı modülleri, sentetik fikstürler, testler; `.tmp/a30/` (git dışı)
- `apps/mobile/package.json`, `packages/reader-core/package.json` ve `pnpm-lock.yaml` (Tedarik kitaplıkları: `diff`, `react-native-marked`, `expo-sharing`, `expo-document-picker`, `approx-string-match`)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A30-defterim-ve-ilerleme.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A29](./A29-kutuphane-ve-depolama.md) · Sonraki: [A31](./A31-hadis-ve-risale-okuyuculari.md)
