# A31 · Hadis ve Risale okuyucuları

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-04](../../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A25](./A25-secim-kelime-karti-baglantilar.md) · [A19](./A19-hadis-hatlari.md) · [A20](./A20-risale-altyapisi.md) · **İnsan adımı:** yok
> **Ajanlar:** `mobil-gelistirici` · `lisans-denetcisi` · `metin-denetcisi` · `hat-gelistirici` (fikstür gerekirse) · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `lisans-kapisi` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A31`

## Amaç
Tecrîd-i Sarîh ve Kütüb-i Sitte için Arapça ile Ahmed Naim Türkçesini yan yana gösteren hadis okuyucusunu ve Risale-i Nur okuyucusunun kodunu yazar. Risale metni hukukçu görüşüne kadar `kapali`dır; görüş olumluysa `ic_kullanim` olur ve yalnız ekip içi `dev` derlemede görünür (K-05, K-06). Görüş yoksa okuyucu yalnız A20'nin `test-` önekli sentetik fikstürüyle sınanır. Dizin-önce görünüm ve lügat yoğunluğu da aynı lisans kapısına bağlıdır.

## Okunacak belgeler
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §3 seçim, §11 hadis okuyucu, §12 Risale-i Nur okuyucu, §13 erişilebilirlik
- [Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md): tamamı; özellikle §1–§3 Naim ve Miras sınırı, §5 numaralandırma, §6 Tecrîd ↔ Buhârî, §8 derece
- [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md): tamamı; özellikle §1 iç kullanım uyarısı, §3.1–§3.6, §4
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 `kutuphane/hadis/*`, `kutuphane/risale/*`, `h/`, `ht/`, `rn/`; §3 hadis ve Risale satırları; §6 Okuma › Risale ayarları; §7 derin bağlantılar
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.4 bölüm vurgusu, §3.1–§3.3 yazı tipleri ve karışık yön, §6 `HadithPair`, `LugatGloss`, `LugatCard`, `IbareCard`, `CitationLink`, `FootnoteMarker`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §2 ATTACH bütçesi, §3.4 `risale-dizin`, §7 süzme
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §9 seçim çözümleme (Arapça ibare satırı), §10 okunur adres
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7.3 yerel seçim kuralı, §8 sayfa çevirme yönü, §13 sağdan sola parçalar

## Kapsam
**Yapılır**
- A21'in yer tutucu rotaları doldurulur: `kutuphane/hadis/[koleksiyon]/index.tsx` (kitap ve bâb listesi), `kutuphane/hadis/[koleksiyon]/[no].tsx` (hadis okuyucu), `kutuphane/risale/[kitap]/index.tsx` (bölüm ağacı, kitap ilerlemesi), `kutuphane/risale/[kitap]/[...bolum].tsx` (Risale okuyucu ya da dizin görünümü).
- `h`, `ht` ve `rn` derin bağlantıları: A25'in tek yakalayıcı rotası `app/[...capa].tsx` bu türleri de çözecek biçimde genişler (A25 bu türleri A31'e bırakır).
- Lügat katmanı ve kartı, ibare (iktibas) kartı, haşiye alt sayfası, açık atıf bağlantıları, baskı sayfa işaretleri.
- Bu okuyucularda seçim, vurgu ve not (A30 kayıtları) ve `reading_position` bağlamları (`hadis:tecrid`, `risale:{kitap}`).

**Yapılmaz**
- Hadis ve Risale hatları, paketleri ve gerçek veri: A19, A20. Kütüphane giriş listeleri (`hadis/index`, `risale/index`): A29.
- Risale metnini indirmek, almak ya da işlemek: İ-03 sonucuna ve A39 olayına bağlıdır; bu aşama hiçbir Risale metnine dokunmaz.
- Hadis numaralandırma kararı (04-icerik/04 §5; proje sahibi), derece etiketi (sonra), konkordans (v1.x), sesli Risale (takvime bağlı).
- Yapay zekâ ile özet ya da çeviri: bilerek yok (K-25, K-30).

## Adımlar
### A31.1 · Önkoşul ve lisans kapısı
- `dev` manifestini oku: `hadis-tecrid`, `hadis-kutub-i-sitte`, `risale-dizin`, `risale-*` ve `test-` önekli fikstür paketlerinin varlığı ve `license_status` değerleri.
- Risale metninin durumu: `pipeline/sources/risale-1956-1960.toml` içindeki `license_status` ve [insan adımları](../06-insan-adimlari.md) listesindeki İ-03 satırı. `kapali` ise okuyucu yalnız A20'nin sentetik fikstürüyle geliştirilir: kaynak `test-risale-ornek` (`ic_kullanim`, yalnız `dev`; 02-mimari/04 §8), kitap slug'ı `test-ornek`, paketler `risale-dizin` ve `risale-test-ornek`. Fikstürdeki iki sentetik `xref` satırı ibare kartını ve dizin görünümünü sınamaya yeter. Adlar 04-icerik/05 §3.6 ile aynıdır.
- Gerçek hadis paketi yoksa (İ-14 bekliyorsa) okuyucu aynı kuralla sentetik hadis fikstürüyle geliştirilir. Fikstür yoksa `hat-gelistirici` A13'teki `test-tefsir-ornek` kalıbıyla ekler (öneri: kaynak `test-hadis-ornek`, `ic_kullanim`; Türkçe "Deneme hadis metni 1 …", Arapça yerine açıkça sentetik harf dizisi).
- Derin bağlantı biçimi MM-14 ve ME-1'e bağlıdır (öneri 03-veri/01 §11 `toRoute`; 01-urun/03 §7 ona uyar: `mutalaa://h/tecrid/15`, `mutalaa://ht/naim/tecrid/15`, `mutalaa://rn/sozler/soz-10/hakikat-3/p4?aralik=120-184`). Kapanmadıysa öneri kullanıcıya sunulur ve `/karar` ile yazılır.
- `arastirmaci` doğrular: OD-5 (lügat kısa anlamının kelime üstünde, ruby biçiminde gösterimi), Android'de `accessibilityLanguage` karşılığı (A26'da doğrulandıysa sonuç okunur).
- `lisans-denetcisi` planı okur: hiçbir adım Risale metnine ya da `tecrid-miras`'a dokunmuyor.
- **Bitti sayılır:** Paket ve lisans durumu tablosu planda; fikstür adları ve bağlantı biçimi belli; doğrulama sonuçları yazılı.

### A31.2 · Hadis okuyucu
- Kitap › bâb › hadis gezinmesi paketteki `unit.parent_path` ve `label` alanlarından kurulur. `hadis_konum`'un pakette ayrı tablosu yoktur; konum `unit.parent_path`, `label`, `ord` ve `attrs` ile taşınır (04-icerik/04 §5, 03-veri/03 §3.2); A19 çıktısı esas alınır. Liste üstündeki arama alanı A28'in yürütücüsünü `kaynak:hadis` kapsamıyla kullanır (öneri).
- `HadithPair`: telefonda dikeyde Arapça üstte (sağdan sola, Amiri ya da Noto Naskh Arabic), Türkçe altta (Literata); üst çubukta "Arapça | Türkçe | İkisi". Yatay ve tablette iki sütun: Arapça sağda, Türkçe solda, satırlar hadis başında hizalı.
- Başlık: "Tecrîd-i Sarîh · 15", "Buhârî · 52" çipi, "Tercüme: Babanzâde Ahmed Naim"; değerler paketten gelir.
- Kâmil Miras kısmı: Türkçe sütunda "Bu hadisin Türkçesi 1 Ocak 2028'de serbest kalıyor". `tecrid-miras` `kapali` olduğu için hiçbir Miras metni okunmaz ve gösterilmez. Miras ciltlerinin Arapçası da 2028'e kadar alınmaz (04-icerik/04 §2; 01-urun/02 §11 buna uyduruldu, 19 Ekim 2026). Okuyucu Arapça birim varsa onu, yoksa yalnız notu gösterir.
- Kütüb-i Sitte yalnız Arapçadır; Tecrîd karşılığı olan hadiste "Tecrîd'deki tercümesine git" (A19'un `atif` bağlantısı, `xref_idx`).
- Arapça metindeki âyet iktibasları çini mavisi alt çizgiyle işaretlenir ve ibare kartını açar. Derece etiketi gösterilmez; yapay zekâ çevirisi yoktur.
- Seçim çapaları `h:tecrid:15@30-58` ve `ht:naim:tecrid:15@…` biçimindedir; kısa dokunuş, uzun basış ve "Seç" yolu 06-mobil/01 §7.3 kuralıdır.
- **Bitti sayılır:** RNTL testleri üç görünümü, Miras notunu ve "Tecrîd'deki tercümesine git" bağlantısını sınıyor; dikey ve yatay görüntüler onaylı.

### A31.3 · Risale okuyucu
- Paragraflar soldan sağa akar (Literata). Her Arapça dizi ayrı `Text` parçasıdır: `writingDirection: 'rtl'`, Amiri ya da Noto Naskh Arabic, Türkçe boyutun 1,15 katı (`okuma-ar-metin-ici`). Sayfa çevirme yönü soldan sağadır (06-mobil/01 §8).
- Metin kelimesi kelimesine gösterilir; kısaltma, sadeleştirme ve yapay zekâ özeti yoktur; kanonik metne hiçbir şey eklenmez.
- Haşiye işaretleri lâl renktedir ve kısa bir alt sayfa açar (`FootnoteMarker`). "(Bakara Sûresi, 255)" gibi açık atıflar `CitationLink` (noktalı alt çizgi) olur ve A25'in atlama yoluyla açılır.
- Ayarlar › Okuma'da baskı seçilmişse kenarda "s. 61" işaretleri görünür (`page_map`); "Sayfaya git" o baskının sayfa numarasını kabul eder.
- Lügat yoğunluğu Kapalı · Az* · Orta · Çok: kısa anlam kelimeden hemen sonra küçük punto ve ikincil renkle yazılır; metne eklenmez, kopyalanmaz, ofseti değiştirmez. Kelimeye dokunuş `LugatCard` açar (baş kelime, anlam, köken, varsa kök ve "Kur'an'da bu kök", Külliyat'tan örnek).
- İbare kartı (Arapça diziye dokunuş): `xref_idx`'te seçimle örtüşen `iktibas` ya da `atif` varsa âyet adresi, `core`'dan Unicode metin, Elmalılı meali, "Âyete git" ve "Karşılaştır". Yoksa cihazdaki Kur'an trigram tablosu ("otomatik eşleşme" çipi), sonra yüklü hadis paketleri, sonra "Kaynak bulunamadı" ve Bağlantılar paneline geçiş (01-urun/02 §12; zincir 05-capraz-referans/01 §9, metinleri 19 Ekim 2026'da 01-urun/02'ye uyduruldu).
- Bölüm ağacı, kitap başına yüzde ve kaldığın yer (`reading_position`, `risale:{kitap}`). Kitap paketleri istek anında bağlanır, en çok 3 (LRU); `risale-dizin` bir Risale kitabı kuruluyken bağlıdır (03-veri/03 §2).
- **Bitti sayılır:** Sentetik fikstürle bütün katmanlar emülatörde çalışıyor; görüntüler üç temada onaylı.

### A31.4 · Dizin-önce görünüm, lisans durumları ve derin bağlantılar
- Okuyucu üç durumu ayırır: metin görünür → okuyucu; metin görünmez, dizin görünür → dizin görünümü; ikisi de görünmez → `LicenseGate` paneli (neden, varsa serbest kalma tarihi, "Kaynaklar ve lisanslar" bağlantısı) ve içeriğin hiçbir parçası.
- Dizin görünümü: kitap ve bölüm yalnız yapısal adlarla ("10. Söz", "3. Hakikat"; bölüm başlıklarının metin sayılıp sayılmadığı OD-6, İ-03'e bağlı); "Bu bölümde geçen âyetler" listesi (âyet adresi, Unicode metin, Elmalılı meali, ¶ ve seçili baskının sayfası; dokunuş Kur'an okuyucusunu açar); bilgi şeridi "Risale-i Nur metni telif nedeniyle bu sürümde yok. Dizin âyet atıflarını ve baskı sayfalarını gösterir." ve "Neden?" → Kaynaklar ve lisanslar.
- Dizinin kendisi de avukat görüşüne bağlıdır (AS-04, IP-5); görünürlüğü yalnız `isPackVisible` belirler. Lügat yoğunluğu ve baskı sayfa ayarları yalnız Risale metni görünürken etkilidir (01-urun/01 §4.4).
- Derin bağlantılar 01-urun/03 §7 kurallarını izler: yol `packages/anchors` (`fromRoute`) ile çapaya çevrilip doğrulanır; geçerli hedef A25'in atlama kuralıyla açılır; geçersiz adres yuvarlanmaz ve "Bağlantı geçersiz" uyarısı görünür; paket cihazda yoksa indirme önerisi, derlemede yoksa lisans paneli açılır.
- `dev` derlemede fikstür hep görünür; dizin-önce ve kapı durumları RNTL'de sahte görünürlük değerleriyle sınanır. `internal` derlemede Risale bölümünün hiç görünmediği A33'te denetlenir.
- **Bitti sayılır:** Üç durumun ve derin bağlantıların testleri yeşil; `lisans-denetcisi` raporu temiz.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; hadis üç görünümü, Miras notu, Risale üç lisans durumu, ibare kartının dört sonucu ve `h`, `ht`, `rn` bağlantılarının geçerli ve geçersiz örnekleri test ediliyor.
- [ ] Lügat açıkken kopyalanan seçim ve kaydedilen vurgu aralığı lügat kapalıyken alınanla aynı (birim testi).
- [ ] Türkçe paragraftaki her Arapça dizi ayrı `Text`, sağdan sola ve Arapça yazı tipiyle çiziliyor (bileşen testi ve görüntü).
- [ ] Hadis ve Risale ekranlarında dokunma hedefleri en az 44×44 pt; "Arapça | Türkçe | İkisi" erişilebilirlik etiketli (`arayuz-denetcisi` raporu).
- [ ] Depoda Risale metni ya da `tecrid-miras` metni yok; fikstürler `test-` önekli ve açıkça sentetik (`lisans-denetcisi` ve `metin-denetcisi` raporu, `git grep` denetimi).
- [ ] `internal` ve `public` bayrağında `ic_kullanim` fikstür ve Risale bölümleri listelenmiyor (RNTL).
- [ ] Emülatörde hadis okuyucusu ve fikstürle Risale okuyucusu görüntüleri (`.tmp/a31/`) üç temada onaylı.

## Doğrulama
```bash
curl -s http://localhost:8333/mutalaa/dev/manifest.json | grep -o '"risale-[a-z0-9-]*"' | sort -u   # İ-03 olumlu değilse yalnız risale-dizin ve risale-test-ornek
pnpm --filter @mutalaa/mobile test
pnpm lint && pnpm typecheck
git grep -n -i "risaleinur\|Risale-i-Nur-Diyanet" -- apps packages   # beklenen: sonuç yok (hattaki ret listesi A20'nindir)
mkdir -p .tmp/a31
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://h/tecrid/15"   # pakette ya da fikstürde var olan bir numara
adb exec-out screencap -p > .tmp/a31/hadis.png
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://kutuphane/risale/test-ornek"   # A20 fikstür kitabı
adb exec-out screencap -p > .tmp/a31/risale-fikstur.png
```

## Dikkat
- Risale metni hafızadan yazılmaz ve hiçbir depodan indirilmez (alitekdemir/Risale-i-Nur-Diyanet dahil); eRisale ve yayınevi lügatleri ile Kelime-Frekans deposunun anlam sütunu kullanılmaz (04-icerik/05 §1, §3.5).
- Geliştirmede kullanılan sentetik `rn:` çapaları kalıcı bir dosyaya ya da kullanıcı verisine yazılmaz (04-icerik/05 §3.2); cihaz denemesinden sonra uygulama verisi temizlenir.
- Hadis Arapçası dağıtıldığı hâliyle gösterilir; okuyucu metni normalize etmez (K-26; `metin-butunlugu`).
- Görünürlük kararı yalnız `isPackVisible`'dadır; ekran derleme türüne bakarak kendi kuralını yazmaz (`lisans-kapisi`).
- Tarafsızlık: yayınevi markası öne çıkarılmaz; baskılar eşit listelenir, okur seçer (K-25).
- ATTACH sınırı 8 şemadır; Risale kitapları için aynı anda en çok 3 bağ (03-veri/03 §2). Derin bağlantı şeması `src/lib/env.ts`'den okunur, elle yazılmaz (A25).
- Commit kapsamları: `mobile`, `anchors` (yalnız rota yardımcısı değişirse), `pipeline` (fikstür).

## İnsan adımları
- Yok. İ-03 (avukat görüşü) gelirse Risale okuyucusu gerçek `ic_kullanim` metinle yalnız `dev`'de yeniden denenir; İ-14 (hadis kaynağı ve Naim taraması) gelirse hadis okuyucusu gerçek paketle yeniden denenir. İkisi de bu aşamayı engellemez.

## Çıktılar
- `apps/mobile/app/(tabs)/kutuphane/hadis/[koleksiyon]/index.tsx`, `[koleksiyon]/[no].tsx`; `apps/mobile/app/(tabs)/kutuphane/risale/[kitap]/index.tsx`, `[kitap]/[...bolum].tsx`
- `apps/mobile/app/[...capa].tsx` içinde `h`, `ht`, `rn` çözümü
- `apps/mobile/src/features/library/` altında hadis ve Risale modülleri (okuyucu, lügat, ibare kartı, dizin görünümü)
- Gerekirse `test-` önekli sentetik hadis fikstürü (hat tarafı), i18n anahtarları, testler; `.tmp/a31/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A31-hadis-ve-risale-okuyuculari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A30](./A30-defterim-ve-ilerleme.md) · Sonraki: [A32](./A32-ayarlar-erisilebilirlik-oz-test.md)
