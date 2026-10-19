# A30 · Defterim, hatim ve yedekleme

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-30](../../00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A23](./A23-cihaz-veri-katmani.md) · [A25](./A25-secim-kelime-karti-baglantilar.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `metin-denetcisi` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A30`

## Amaç
Eski planın korunan "okuma simetrisi" çekirdeğini (K-30) cihazda kurar: isimli yer imleri, beş renkli vurgu, `[[q:2:255]]` bağlantılı Markdown notlar, karışık kaynaklı koleksiyonlar; hatim (30 cüz ızgarası, 604 sayfa çubuğu, aynı anda birden çok hatim), okuma geçmişi, varsayılan kapalı yumuşak seri ve Gizli mod. Kayıtlar senkrona hazır şemaya yazılır (K-15), dosyayla yedeklenip geri yüklenir ve içerik güncellemesinden sonra yeniden çapalanır; hiçbir kayıt sessizce kaybolmaz (B-08).

## Okunacak belgeler
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §2 şema, §3 HLC, §4 birleştirme, §5 not çakışması arayüzü, §6 yedek, §7 ayarların kapsamı
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 ofsetler, §9 yeniden çapalama, §12 not bağlantıları
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 eylem çubuğu, §14 riyâsız ilerleme
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 (`defterim/*`, `not/[id]`, `hatim/yeni`, `ayarlar/ilerleme`), §3 Defterim satırları, §6 İlerleme ve gizlilik
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.3 vurgu renkleri, §6 `HighlightSwatch`, `HatimGrid`, `HatimBar`, `NoteLinkChip`, §7 tezhip kuralı
- [Depolama yöneticisi](../../06-mobil/03-depolama-yoneticisi.md): §8 çapa denetimi, §9 paketi silinmiş kayıt
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.8, §4.9, §8 B-08
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §2.1 veri envanteri, §2.7 dışa aktarma

## Kapsam
**Yapılır**
- Yer imi, vurgu, not ve koleksiyon kayıtları; okuyuculardaki işaretleri (A24 bunları A30'a bırakır) ve A25'in eylem çubuğuna Vurgula ve Not eylemleri.
- A21'in yer tutucu rotaları doldurulur: Defterim sekmesi, koleksiyon ve hatim ayrıntısı, not düzenleyici, hatim oluşturma, `ayarlar/ilerleme`.
- Hatim ilerlemesi, okuma geçmişi, seri ve Gizli mod.
- Yedek dışa ve içe aktarma (JSON dosyası) ve içe aktarmadaki not çakışmasının gösterimi.
- Yeniden çapalama ve `device.db` içinde `anchor_resolution` önbelleği (KV-5 önerisi).

**Yapılmaz**
- Hesap, senkron, giden kutusu ve sunucu: A35, A36 (v1.x). v1'de `outbox` yazılmaz.
- Seçim ve eylem çubuğunun kendisi: A25. Paket güncellemesi tetiği: A29. "Hata raporları" anahtarı ve "Verilerimi sil": A32.
- Kelime defteri (`vocab`), okuma planları, hatırlatıcılar, görsel içerik kartı: v1.x. PDF dışa aktarma: faz atanmadı.

## Adımlar
### A30.1 · Önkoşul, doğrulamalar ve kararlar
- A23 çıktısını denetle: `packages/content-schema/src/user/` (her tabloda `id`, `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id`), `packages/reader-core/src/sync/hlc.ts`, tek işlemde UUIDv7 `id`, yeni `hlc` ve `device_id` yazan yardımcı (KV-4 A23.1'de doğrulandı).
- `arastirmaci` doğrular: ÇŞ-5 (cihazda yaklaşık eşleşme; kitaplık ya da kendi düzenleme uzaklığı), 03-veri/04 §6'daki paylaşım ve belge seçici modülleri, KV-6 (not karşılaştırması için fark kitaplığı), Markdown gösterimi (belgelerde kitaplık yok; öneri: yalnız gereken alt kümeyi çizen küçük bir dönüştürücü).
- Kullanıcıya sorulur ve `/karar` ile yazılır:
  1. Okuma geçmişi ve seri için şemada tablo yok (03-veri/04 §2). Öneri: `user.db` içinde ortak sütunlu `reading_day(day, context, first_anchor, last_anchor)`; senkron kapsamı 03-veri/04 §7'ye eklenir.
  2. Gizli modun kapsamı belgelerde artık aynıdır, karar gerekmez (01-urun/02 §14, 03-veri/04 §7): okuma geçmişi, otomatik hatim işaretlemesi ve seri kaydı tutulmaz; okuma konumu ve elle hatim işareti sürer.
  3. Birden çok hatim açıkken otomatik işaretin hangi hatime yazılacağı tanımsız. Öneri: Defterim'de "etkin" seçilen hatim.
  4. Yer imi ekleme yeri eylem çubuğu listesinde yok (01-urun/02 §3). Öneri: eylem çubuğunda "Yer imi" ve okuyucu üst çubuğu menüsünde "Bu sayfaya yer imi".
- **Bitti sayılır:** Doğrulama sonuçları ve 1., 3., 4. kararlar yazılı; şema eklentileri drizzle-kit göçü olarak planlandı.

### A30.2 · Yer imi, vurgu ve koleksiyon
- Her değişiklik A23'ün yazma yardımcısıyla tek işlemdir. Silme yumuşaktır (`deleted_at`) ve "Geri al" sunar.
- Kayıt oluşurken paketten `label`, `excerpt` (ilk 160 kod noktası) ve `content_hash` kopyalanır; âyet aralığında (`q:2:255-257`) `content_hash` NULL'dur. Cihaz özeti yeniden hesaplamaz.
- Vurgu: renk yuvası 1–5; varsayılan adlar Önemli, Ezber, Ders, Soru, Tefekkür; hazır takım Akide, İbadet, Ahlak, Tarih, Dil; adlar `setting` tablosunda. Kur'an aralığı kelime konumu, metin aralığı kod noktasıdır (`toUnitSpan`). `quote` en çok 1.000 kod noktası (uzunsa ilk ve son 500), `prefix` ve `suffix` 32'şer kod noktası. Paragraf sınırını aşan seçim birim başına satıra bölünür ve `group_id` ile bağlanır.
- Gösterim: okuyucu görünür birimlerin kayıtlarını `WHERE anchor IN (…)` ile tek sorguda alır (`useLiveQuery`) ve `HighlightInput.user` olarak çizicilere verir. Vurgu zemin tonu, 1,5 pt alt çizgi ve kenar simgesiyle çizilir; renk tek başına anlam taşımaz; Mod B'de âyet kutusunun kenarında işaret.
- Koleksiyon: ad, renk, `sort_key`; silinince bağlı yer imlerinin `collection_id` değeri NULL olur.
- **Bitti sayılır:** Oluşturma, renk, bölünmüş seçim ve "Geri al" testleri yeşil; Mod C ve meal görüntüleri üç temada `arayuz-denetcisi` onaylı.

### A30.3 · Notlar
- `app/not/[id].tsx` kök düzeyinde tam ekran modaldır (`id` = `yeni` ya da UUIDv7); okuyucudan açılınca sekme değişmez; kapatırken taslak kendiliğinden kaydedilir.
- Gövde Markdown'dır. `[[q:2:255]]` ve `[[konu:sabir]]` bağlantıları `NoteLinkChip` olarak çözülür (çözüldü · çözülmedi); dokunuş hedefe A25'in atlama yoluyla gider. `[[Bakara 255]]` gibi insan yazımı kayıtta kanonik çapaya çevrilir (03-veri/01 §12); A28'in sure çözücüsü kullanılır, A28 henüz yoksa çözücü `packages/reader-core` içine burada yazılır ve A28 onu kullanır. `sure` tablosu boşsa (İ-23) yalnız `[[2:255]]` biçimi çevrilir; ad içeren test A11.3'ten sonra açılır (`mobil-ekran`, sure adı kuralı).
- Not kelime aralığına, âyete, paragrafa ya da hadise bağlı olabilir ya da bağımsızdır (`anchor` NULL); `tags` JSON dizisi; isteğe bağlı `highlight_id` ve koleksiyon.
- **Bitti sayılır:** Bağlantı ayrıştırma ve kanonikleştirme testleri yeşil; düzenleyici görüntüsü onaylı.

### A30.4 · Defterim, hatim ve ilerleme
- `defterim/index.tsx`: `SegmentedControl` ile yer imi, vurgu, not, koleksiyon, hatim ve ilerleme bölümleri; boşken "Bir âyete dokun, Vurgula'yı seç". Paketi silinmiş kayıt adresi ve alıntısıyla görünür, içerik yerine "Bu içerik cihazda yok · İndir".
- `defterim/koleksiyon/[id].tsx`; `defterim/hatim/[id].tsx` (`HatimGrid` 30 cüz, `HatimBar` 604 sayfa, değerler yazıyla da); `hatim/yeni.tsx` (ad, isteğe bağlı bitiş tarihi; aynı adda hatim varsa uyarı). Silinmiş kayıtta "Bu kayıt silindi · Geri al".
- Hatim `(layout = 'medine-604', page)` ile tutulur; cüz ve sayfa sınırları `core`'dan okunur. `page_map` yoksa hatim ekranı bunu açıkça yazar (03-veri/03 §7; AS-10).
- Otomatik işaret: sayfa ekranda 20 saniye kalıp çevrilince okunmuş sayılır (öneri, OD-9); ayar "Hatim sayfalarını otomatik işaretle: Açık"; elle işaret her zaman vardır. Tamamlama ekranında ince tezhip çerçevesi bulunur; ekran sayı paylaşmayı önermez.
- Okuma geçmişi (varsayılan açık) ve seri (varsayılan kapalı) A30.1 kararıyla yazılır. Seri yalnız "Bu hafta 4 gün okudun." gibi yumuşak dille görünür; kırılan seri uyarısı, kayıp korkusu ve karşılaştırma yoktur (K-25).
- Gizli mod açıkken okuma geçmişi, otomatik hatim işaretlemesi ve seri kaydı tutulmaz; okuma konumu ve elle hatim işareti sürer; mevcut kayıtlar gizlenir, silinmez (01-urun/02 §14). Gizli mod `setting` tablosundadır.
- `ayarlar/ilerleme.tsx`: bu satırlar ve yedek satırları. "Hata raporları" ve "Verilerimi sil" satırları A32'de eklenir.
- **Bitti sayılır:** Hatim küme birleşimi, otomatik işaret ve Gizli mod testleri yeşil; hatim ve Defterim görüntüleri onaylı.

### A30.5 · Yedek: dışa ve içe aktarma
- Biçim 03-veri/04 §6: `format: "mutalaa-yedek"`, `format_version: 1`, `user_schema_version`, `app_version`, `created_at`, `device_id`, `tables` (`bookmark`, `highlight`, `note`, `reading_position`, `hatim`, `hatim_page`, `collection`, `setting` ve A30.1'de eklenen tablo). Silinmiş satırlar girer; `outbox`, `sync_state` ve `device.db` girmez. Dosya adı `mutalaa-yedek-YYYY-MM-DD.json`; paylaşım menüsüyle kaydedilir.
- İçe aktarma belge seçiciyle açılır; önce önizleme ("142 vurgu, 37 not, 12 yer imi"). Varsayılan birleştirmedir ve §4 kurallarını kullanır; aynı dosyayı iki kez yüklemek bir şey değiştirmez. Aynı `id` ile farklı not gövdesinde cihazdaki asıl kalır, yedekteki `conflict_of` ile çakışma kopyası olur ve §5'teki şerit ve karşılaştırma görünür. "Tümünü değiştir" onay ister. Dosyanın `user_schema_version` değeri uygulamanınkinden büyükse işlem reddedilir ve güncelleme istenir; küçükse bellekte göç uygulanır.
- Dosya kişisel veridir; hiçbir sunucuya gitmez ve ekran bunu kullanıcıya söyler.
- **Bitti sayılır:** Gidiş-dönüş, idempotentlik, sürüm reddi ve çakışma kopyası testleri yeşil.

### A30.6 · Yeniden çapalama (B-08)
- Algoritma 03-veri/01 §9 akışıdır (öneri yer: `packages/reader-core`): kullanım dışı çapa → `successors` ile yeni çapa ve aralık; özet eşit → `tam`; alıntı yeni metinde bir kez geçiyor → `tasindi`; birden çok → bağlamı en benzer, eşitlikte uzunluk oranıyla ölçeklenmiş eski ofsete en yakın; hiç → kod noktası üzerinde `1 − düzenleme_uzaklığı / max(uzunluk)` ≥ 0,85 → `tasindi`; değilse komşu birimler (`ord` ±2); değilse `bulunamadi`.
- A29'un paket güncelleme olayıyla çalışır. Sonuç yalnız `anchor_resolution` tablosuna yazılır; senkronlanan kayıt yalnız kullanıcı eylemiyle değişir.
- Defterim'de değişen kayıt "Metin güncellendi, vurgunun yerini kontrol et" etiketini, bulunamayan kayıt rozeti alır; eylemler "Yeniden seç", "Birime bağla", "Sil". Kur'an biriminde özet farkı hat hatasıdır (03-veri/01 §9): kayıt `tam` sayılmaz ve paket kimliği ile sürümünü taşıyan, kişisel veri içermeyen bir hata kaydı gönderilir (öneri).
- Test fikstürü yalnız sentetik metindir ("Deneme paragrafı 1 …"): değişmeyen, yazımı düzeltilen, bölünen, birleşen, silinen, komşuya taşınan ve bulunamayan paragraflar.
- **Bitti sayılır:** B-08 testi: fikstürdeki her kayıt `tam`, `tasindi` ya da `bulunamadi` oluyor; hiçbir kayıt kaybolmuyor; `user.db` satırları değişmiyor.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/content-schema test`, `pnpm --filter @mutalaa/reader-core test` ve `pnpm --filter @mutalaa/mobile test` yeşil; yeni testler A30.2–A30.6'nın "Bitti sayılır" maddelerini kapsıyor.
- [ ] Yeni ya da değişen her `user.db` tablosunda altı ortak sütun var; A23'ün göç fikstürü testleri yeni göçlerle de geçiyor (07-yayin/03 §6).
- [ ] Vurgu beş renkte, adıyla ve simgesiyle çiziliyor; Mod C, Âyet âyet ve meal görüntüleri üç temada onaylı (`.tmp/a30/`).
- [ ] Not içindeki `[[q:2:255]]` dokunuşla hedefi açıyor; `[[2:255]]` kayıtta `[[q:2:255]]` oluyor; `[[Bakara 255]]` dönüşümü A11.3'ten sonra sınanıyor, o zamana kadar atlandığı ilerleme notunda (test ve görüntü).
- [ ] Hatim ayrıntısı 30 cüzü ve 604 sayfayı yazıyla da veriyor; iki hatim aynı anda tutulabiliyor.
- [ ] Seri varsayılan kapalı; Gizli mod açıkken okuma geçmişi, otomatik hatim işareti ve seri kaydı yazılmıyor, okuma konumu yazılıyor (birim testi).
- [ ] Yedek gidiş-dönüşünde kayıp yok; aynı dosya ikinci kez yüklenince satır sayıları ve `hlc` değerleri değişmiyor.
- [ ] B-08 yeniden çapalama testi yeşil; `anchor_resolution` dışındaki tablolar değişmiyor.
- [ ] Testlerde ve fikstürlerde hafızadan yazılmış Kur'an, meal, hadis ya da Risale metni yok (`metin-denetcisi` raporu).

## Doğrulama
```bash
pnpm --filter @mutalaa/content-schema test
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm lint && pnpm typecheck
mkdir -p .tmp/a30
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"
adb exec-out screencap -p > .tmp/a30/vurgu.png           # vurgu, not ve yer imi işaretleri
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://defterim"
adb exec-out screencap -p > .tmp/a30/defterim.png
```

## Dikkat
- Çapalar yalnız `packages/anchors` ile ayrıştırılır ve biçimlenir (`capa-gramer`). Ofset kod noktasıdır; UTF-16 dönüşümü yalnız `cpToUtf16` ve `utf16ToCp` ile yapılır.
- `quote`, `prefix`, `suffix` ve `excerpt` paketten olduğu gibi kopyalanır; NFC ya da başka dönüşüm uygulanmaz (`metin-butunlugu`).
- Testlerde Kur'an, meal, hadis ya da Risale metni yazılmaz. Arapça örnek gerekiyorsa çalışma anında paketten okunur ya da açıkça sentetik harf dizisi kullanılır (CLAUDE.md kural 2).
- İlerleme gizlidir ve paylaşılmaz; liderlik tablosu, kırılan seri uyarısı ve sayı paylaşımı yoktur (K-25).
- Yedek dosyası ve not metni kişisel veridir; günlüğe ve Sentry'ye girmez.
- Atlama zinciri açıkken `reading_position` yazılmaz (A24, A25); hatim işareti bu kuralı bozmaz. Uygulanmış göç değiştirilmez; yeni göç eklenir (A23).
- Commit kapsamları: `mobile`, `content-schema`, `reader-core`.

## İnsan adımları
- Yok. A30.1'deki dört karar kullanıcı onayı ister.

## Çıktılar
- `apps/mobile/app/(tabs)/defterim/` (`_layout.tsx`, `index.tsx`, `koleksiyon/[id].tsx`, `hatim/[id].tsx`), `apps/mobile/app/not/[id].tsx`, `apps/mobile/app/hatim/yeni.tsx`, `apps/mobile/app/(tabs)/ayarlar/ilerleme.tsx`
- `apps/mobile/src/features/notebook/` (kayıtlar, Defterim, hatim, ilerleme, yedek)
- Şema eklentileri: `packages/content-schema/src/user/`, `apps/mobile/src/db/device/schema.ts` (`anchor_resolution`); göçler `apps/mobile/src/db/migrations/user/` ve `.../device/`
- `packages/reader-core` içinde yeniden çapalama ve not bağlantısı modülleri, sentetik fikstürler, testler; `.tmp/a30/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A30-defterim-ve-ilerleme.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A29](./A29-kutuphane-ve-depolama.md) · Sonraki: [A31](./A31-hadis-ve-risale-okuyuculari.md)
