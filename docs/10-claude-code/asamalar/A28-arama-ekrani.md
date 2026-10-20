# A28 · Arama ekranı

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A12](./A12-arama-indeksi-ve-paket-semasi.md) · [A24](./A24-okuyucu-mushaf-c.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `test-yazari` · `hat-gelistirici` (ölçüm kümesi) · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `test-vektoru` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A28`

## Amaç
Ara sekmesini kurar. Arama cihazda, ATTACH edilmiş bütün metin paketlerinin FTS5 indekslerinde tek deyimle yapılır; sonuçlar esere göre gruplanır ve âyet sonuçlarında Arapça metinle meal birlikte görünür. Kapsam süzgeci, tırnaklı ifade, "Bakara 255" ve "2:255" ile adrese gitme ve son aramalar eklenir. Geliştirici menüsündeki "Arama ölçümü" ekranı ve sorgu kümesi K-17'deki 50 ms hedefini (p95) ölçmeye hazırlanır; referans cihazdaki resmî ölçüm A33'tedir.

## Okunacak belgeler
- [Arama (FTS5)](../../03-veri/05-arama-fts5.md): tamamı; özellikle §3 sorgu ayrıştırma, §4 sıralama ve sonuç parçası, §5 ATTACH, §6 ölçüm, §7 açık sorular
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §1 Ara sekmesi, §3.1 ortak durumlar, §3.2 Ara satırı, §6 Geliştirici, §7 `mutalaa://ara?q=…`, §8 kural 1 ve 11
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §6.3 ATTACH yöneticisi, §9 bütçeler, §10 bayraklar, §12 telemetri, §14 `trLower`
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §12 sure adları ve insan yazımları
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §4.7 arama özellikleri, §8 B-02
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 madde 5, §9 Arama akışı, §10 performans
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §2.1 son aramalar satırı, §2.7, §5 madde 8

## Kapsam
**Yapılır**
- `src/features/search`: sorgu yürütücü, esere göre gruplama, "Tümü" listesi (ağırlıklı RRF), "Daha fazla", sonuç satırı; `app/(tabs)/ara/index.tsx` (A21'in yer tutucusu) doldurulur.
- `ara` derin bağlantısının `q` ve `kapsam` parametreleri (A25 bu türü A28'e bırakır).
- Adla adres çözümü ("Bakara 255", "Âl-i İmrân 7") ve "2:255" için en üstte "Git: …" satırı.
- Kapsam süzgeci, tırnaklı ifade, "Tam yazımla ara" anahtarı, Arapça trigram yedeği, `kök:` süzgecinin arayüzü.
- Son aramalar: v1 özelliği, yalnız cihazda (01-urun/01 §4.7; KVKK §2.1); ayrıntıları A28.1'de karara bağlanır.
- "Arama ölçümü" ekranı ve ölçüm sorgu kümesi (A12 bunu A28'e bırakır); sonuç parçasının `packages/reader-core` içinde üretimi.

**Yapılmaz**
- Normalleştirme kuralları (A05), FTS tabloları ve MATCH sorgu kurucusu (A12). Bir vektör kırılırsa düzeltme oraya, `test-vektoru` kuralıyla gider.
- Fihrist'teki "2:255" girişi (A24); `q` derin bağlantısı ve geri dönüş yığını (A25); öz test ekranı (A32); Maestro akışları ve referans cihazda B-02 ölçümü (A33).
- Kök verisi (`kelime-kok`): A17. Tefsir kapsamının gerçek pakete bağlanması: A37. Web araması: A38. Anlamsal arama: faz atanmadı.

## Adımlar
### A28.1 · Önkoşul, doğrulamalar ve iki karar
- A12 çıktısını denetle: `packages/search` sorgu kurucusu ve `shared/test-vectors/fts-query/query.jsonl` yeşil; metin paketlerinin `unit_fts`, `unit_tri` ve `tr_stem_lex` taşıdığı Yayınlayıcı testlerinde görülüyor; `dev` manifesti `core` ve `test-kucuk` paketlerini listeliyor (A13).
- AR-6 ve MM-5 (expo-sqlite derlemesindeki `SQLITE_MAX_ATTACHED`, şema nitelemeli FTS5 `MATCH`) A23.1'de cihazda ölçüldüyse sonuç okunur; ölçülmediyse burada ölçülür ve `/belge-esitle` ile işlenir.
- Karar 1 · Son aramaların ayrıntısı. Tutulması v1 kapsamındadır ve yalnız cihazdadır (01-urun/01 §4.7; KVKK §5 madde 8, 19 Ekim 2026'da çözüldü). Kayıt sayısı, Ara ekranındaki silme düğmesi ve Gizli mod kuralı kullanıcıya sorulur, `/karar` ile yazılır. Öneri: MMKV, en çok 10 kayıt, "Temizle" düğmesi, Gizli mod açıkken kayıt yok. "Verilerimi sil" son aramaları da siler (KVKK §2.7).
- Karar 2 · Ölçüm derlemesi. Ölçüm yalnız sürüm (release) kipinde geçerlidir (06-mobil/01 §9). `eas.json` `dev` türünü sürüm kipinde üreten bir profil içermez; `internal` derleme Kurul onayı yokken `core`'u gizleyebilir (06-mobil/01 §10). Seçenekleri kullanıcıya sun (öneri: `APP_FLAVOR=dev` ile sürüm kipinde ek EAS profili), `/karar` ile yaz. A33 bu kararı kullanır.
- **Bitti sayılır:** AR-6 sonucu ve iki karar yazılı; A12 testleri yeşil.

### A28.2 · Sorgu yürütücü ve adla adres çözümü
- MATCH ifadesi A12'nin sorgu kurucusundan gelir (03-veri/05 §3 tablosu). Çok paketli `UNION ALL` deyimi, gruplama, RRF (`Σ w / (60 + sıra)`; Âyet 1,2 · Meal 1,0 · Tefsir 0,9 · Risale 0,9 · Hadis 0,8), ek puanlar (başlık ×1,5, tam ifade ×1,3, dar anahtar ×1,2) ve sonuç parçası `packages/reader-core` içinde parametreli SQL olarak yazılır; SQL yürütücüsü arayüzle verilir (02-mimari/03 §2 kural 2).
- Şema adları A23'ün `ContentDb.ensure` yöneticisinden gelir; ATTACH açılışta bir kez yapılır. Her dal `LIMIT 20`, "Daha fazla" `OFFSET n`; hazırlanmış deyimler yeniden kullanılır; `tr_stem_lex` sorguları toplu yapılır. 2 karakterlik önekte bm25 hesaplanmaz, sıra `ord`'dur.
- Türkçe terim `â`, `î` ya da `û` içeriyorsa dar süzgeç uygulanır; sonuç kalmazsa geniş sonuçlar "Düzeltme işaretsiz yazımlar da gösteriliyor" notuyla döner. Arapça terim az sonuç verir ve en az 3 karakterse `unit_tri` sonuçları "otomatik eşleşme" çipiyle katlı gelir. `kök:` süzgeci yalnız `p_kelime_kok` bağlıyken çalışır; değilse "Kelime kökleri paketi gerekli" der.
- Adla adres: A12'nin kurucusu adres biçimini algılar ve sure adı çözücüsünü dışarıdan alır. Çözücü burada `core` `sure` tablosundan kurulur: girdi geniş anahtarla normalize edilir, `variants` ile eşlenir, sonuç `packages/anchors` ile çapaya çevrilip doğrulanır. Aralık dışı adres (`2:300`) "Git" satırı üretmez ve en yakın âyete yuvarlanmaz. Fihrist de adla girişe açılırsa aynı çözücüyü kullanır (öneri); ikinci kopya yazılmaz. `sure` tablosu boşsa (sure adları İ-23 onayını bekliyor; A13, A24) çözücü yalnız `2:255` biçimini tanır; ad tabanlı "Git" satırı A11.3'ten sonra açılır. Testlerin ad içeren girdileri belgedeki örneklerdir (Arama §3 madde 1), beklenen çapa `shared/data/sure-adlari.json` ile çözülür; dosya yoksa bu testler atlanır ve ilerleme notuna yazılır. Sure adı elle yazılmaz.
- **Bitti sayılır:** RRF, gruplama, sonuç parçası ve sure çözücüsü testleri Vitest'te yeşil; testler `LANG=tr_TR.UTF-8` altında da geçiyor.

### A28.3 · Ara ekranı
- Bileşenler: `SearchField`, `ScopeChips` (Tümü · Kur'an · Meal · Tefsir · Hadis · Risale; `kaynak:` süzgecinin arayüzü), `SearchResultRow`, son aramalar, `EmptyState`, `Skeleton` (150 ms kuralı). Rota dosyası yalnız özellik bileşenini çağırır.
- Ekran `q` ve `kapsam` parametrelerini okur (`mutalaa://ara?q=sabır&kapsam=kuran`; 01-urun/03 §7).
- Kapsam çipi yalnız derlemede görünen (`isPackVisible`) paketler için çıkar. Görünür ama kurulu olmayan kapsamda "Bu kapsamın paketi yok · İndir" (Depolama, A29).
- Âyet ve Meal satırları âyetin Arapçasını (kanonik Tanzil metni) ve `meal:elmalili:{sure}:{ayet}` mealini birlikte gösterir; 900 dp ve üstünde iki sütun (öneri). Meal `core`'da henüz yoksa yalnız Arapça görünür; yer tutucu meal yazılmaz.
- Sonuç parçası kanonik metinden ±12 sözcüktür; `search_text`, `snippet()` ve `highlight()` çıktısı ekrana girmez. Arapça sözcükler ayrı `Text` parçası olarak sağdan sola ve Arapça yazı tipiyle çizilir. Risale sonucunun kitabı kurulu değilse yalnız etiket ve indirme önerisi görünür.
- Okurken açılan aramada okunan eserin grubu önce gelir. Sonuca dokunuş hedefi 01-urun/03 §8 kural 1'e göre açar (Kur'an hedefi Oku'da, diğerleri Kütüphane'de); paketi olmayan hedefe atlanmaz, satırda "paket gerekli" yazar.
- Durumlar: boş sorgu → son aramalar; sonuç yok → "Tam ifade için tırnak kullan"; hata → satır içi kart ve "Yeniden dene".
- `testID` önerisi: `arama-alani`, `arama-sonuc-{çapa}`; A33 akışları bunları kullanır. Emülatördeki `isik` sınaması A13'ün "Işık" sözcüğünü taşıyan `test-kucuk` fikstürüyle yapılır.
- **Bitti sayılır:** RNTL testleri gruplama, kapsam, paket eksik ve sonuç yok durumlarını geçiyor; emülatör görüntüleri `arayuz-denetcisi` onayından geçti.

### A28.4 · Son aramalar
- A28.1 kararına göre yazılır. Kayıt yalnız `src/lib/kv.ts` (MMKV) üzerinden tutulur; `user.db`'ye, yedeğe ve Sentry'ye girmez (06-mobil/01 §12).
- **Bitti sayılır:** Birim testi kayıt sınırını, temizlemeyi ve kararın Gizli mod kuralını sınıyor.

### A28.5 · Arama ölçümü ekranı ve sorgu kümesi
- Rota (öneri ad) `app/(tabs)/ayarlar/gelistirici/arama-olcumu.tsx`; geliştirici menüsüne satır eklenir. `gelistiriciMenusu` bayrağıyla yalnız `dev` ve `internal` derlemede görünür; `public`'te Ayarlar'a yönlendirilir (03-veri/05 §6; 06-mobil/01 §10).
- Sorgu kümesi `shared/test-vectors/arama/olcum.jsonl` (03-veri/05 §6'daki konum, JSONL biçimi): yaklaşık 200 sorgu; sık ve seyrek sözcük, 2–4 karakterlik önek, ifade, düzeltme işaretli terim, ekli biçim, harekeli ve harekesiz Arapça, trigram, kök, adres ve birden çok paketi arayan sorgular. Satır alanları: `id`, `kategori`, `sorgu`, `beklenen` (ilk sonuç çapaları). Python ve C# vektör koşucuları bu klasörü de atlar (A12'deki `fts-query/` kuralı).
- Terimler ve beklenen sonuçlar hafızadan yazılmaz. `hat-gelistirici` terimleri paketteki normalize sözcüklerden sıklık bandına göre örnekleyen bir üreteci `uv run mutalaa export test-vectors` komutuna ekler; beklenen sonuçlar ilk koşudan alınır ve kullanıcı onayıyla dondurulur.
- Ekran kümeyi üç kez koşar, her sorguyu `performance.now()` ile ölçer, kategori başına p50, p95 ve en yüksek değeri gösterir; açılıştan sonraki ilk sorguyu ayrı yazar; beklenen ilk sonucu tutmayan sorguları listeler. Sonucu cihaz modeli ve paket sürümleriyle JSON olarak paylaşım menüsünden verir (paylaşım modülü Doğrulanacak; A30'daki yedekle aynı modül). `dev` derlemede aynı JSON uygulama belge klasörüne de yazılır (öneri).
- Emülatörde bir ön ölçüm yapılır ve `.tmp/a28/olcum.json` olarak saklanır. Geliştirme kipindeki değerler bütçeye tabi değildir.
- **Bitti sayılır:** Ekran kümenin tamamını koşuyor ve JSON üretiyor; dondurulmuş beklenen sonuçlarla uyuşmayan sorgu sayısı 0.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/search test`, `pnpm --filter @mutalaa/reader-core test` ve `pnpm --filter @mutalaa/mobile test` yeşil; yeni testler RRF, gruplama, sonuç parçası, sure çözücüsü ve ekran durumlarını kapsıyor.
- [ ] "2:255" en üstte "Git" satırı veriyor, "2:300" vermiyor (Vitest). "Bakara 255" ve "Âl-i İmrân 7" A11.3'ten sonra `shared/data/sure-adlari.json` ile sınanıyor; o zamana kadar bu testlerin atlandığı ilerleme notunda yazılı.
- [ ] Emülatörde `isik` araması "Işık" içeren sonucu ilk sırada gösteriyor ve dokunuş okuyucuyu açıyor (`.tmp/a28/`, `arayuz-denetcisi` raporu).
- [ ] Âyet sonucunda Arapça metin ve meal birlikte görünüyor; `search_text` hiçbir ekranda yok (`reader-core` testi, 07-yayin/03 §5 madde 5).
- [ ] `internal` bayrağıyla `bekliyor` durumundaki paketin kapsam çipi görünmüyor (RNTL).
- [ ] Arama sorgusu Sentry olayına ve kırıntısına girmiyor (telemetri birim testi).
- [ ] Arama ölçümü ekranı `public` bayrağında açılmıyor; `dev`'de kümeyi koşup JSON üretiyor; dondurulmuş beklenen sonuçlarla uyuşmazlık 0.
- [ ] `pnpm test` (JSONL biçim denetimi dahil), `dotnet test` ve `uv run pytest` yeşil; Python ve C# koşucuları `arama/` klasörünü atlıyor.
- [ ] AR-6 sonucu ve A28.1'deki iki karar karar defterinde ya da ilgili dokümanda yazılı.

## Doğrulama
```bash
pnpm --filter @mutalaa/search test
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test
pnpm test                                                    # Turborepo; shared/test-vectors JSONL denetimi dahil
pnpm lint && pnpm typecheck
dotnet test --solution server/Mutalaa.slnx && cd pipeline && uv run pytest && cd ..
curl -s http://localhost:8333/mutalaa/dev/manifest.json
mkdir -p .tmp/a28
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ara?q=isik'"
adb exec-out screencap -p > .tmp/a28/ara-isik.png            # mobil-ekran: PNG'yi Read ile oku
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ara?q=2:255'"
adb exec-out screencap -p > .tmp/a28/ara-adres.png
# Ölçüm JSON'u (yalnız dev derleme; dosya yolu A28.5'te belirlenir, Doğrulanacak):
# adb exec-out run-as app.mutalaa.dev cat files/<yol>/olcum.json > .tmp/a28/olcum.json
```

## Dikkat
- Kanonik metin değişmez; sonuç parçası ve işaretleme yalnız kanonik metinden üretilir (K-26; `metin-butunlugu`). Kur'an'da eşleşme Simple Clean normalize metniyle, gösterim Uthmani metinle yapılır; işaretlenemeyen eşleşmede satır yine gösterilir (AR-4).
- Türkçe küçük harf açık eşlemeyle yapılır (`packages/search`); `toLocaleLowerCase()` argümansız kullanılmaz. Hermes davranışı A32'deki öz testte ölçülür.
- Kullanıcı girdisindeki her sözcük FTS5 dizgisi olarak çift tırnağa alınır; SQL metnine yalnız ATTACH takma adı girer, değerler parametredir.
- Arama sorgusu telemetriye, günlüğe ve yedeğe girmez (06-mobil/01 §12; KVKK).
- Ölçüm kümesinde ve testlerde Kur'an metni hafızadan yazılmaz; Arapça terimler paketten örneklenir (CLAUDE.md kural 2).
- Arama ölçümü ekranı `dev` ve `internal` derlemededir; küme `shared/test-vectors/arama/olcum.jsonl`'dır (03-veri/05 §6, 01-urun/03 §6, 07-yayin/03 §10, 02-mimari/03 §1.2).
- URL'de `?` ya da `&` varsa `adb shell` komutu tek parça tırnaklanır; cihaz yolu içeren argümanlarda Git Bash yol dönüşümü için `windows-sorun`.
- Commit kapsamları: `mobile`, `reader-core`, `test-vectors`, `pipeline`.

## İnsan adımları
- Yok. A28.1'deki iki karar kullanıcı onayı ister.

## Çıktılar
- `apps/mobile/src/features/search/` (ekran, sorgu kancaları, son aramalar); `apps/mobile/app/(tabs)/ara/index.tsx`
- `apps/mobile/app/(tabs)/ayarlar/gelistirici/arama-olcumu.tsx` ve geliştirici menüsü satırı
- `packages/reader-core` içinde çok paketli sorgu, RRF, sonuç parçası ve sure çözücüsü; testleri
- `shared/test-vectors/arama/olcum.jsonl`, hattaki üreteci ve koşuculardaki atlama
- `apps/mobile/src/lib/i18n/tr.ts` anahtarları; `.tmp/a28/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A28-arama-ekrani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A27](./A27-ses-sistemi.md) · Sonraki: [A29](./A29-kutuphane-ve-depolama.md)
