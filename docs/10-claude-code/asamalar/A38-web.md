# A38 · Web (Next.js 16; âyet ve sayfa adresleri)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-14](../../00-ozet/02-karar-defteri.md#k-14--web) · [K-08](../../00-ozet/02-karar-defteri.md#k-08--platform-sırası) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5)
> **Faz:** 5 · Web · **Önkoşul:** [A34](./A34-magaza-yayini.md) · **İnsan adımı:** Kurul'un web görüşü (İ-02 kanalı, gerekirse İ-19) · İ-18 (alan adı) · web barındırma kararı
> **Ajanlar:** `web-gelistirici` · `arayuz-denetcisi` · `arastirmaci` · `test-yazari` · `lisans-denetcisi` · `inceleyici` · **Beceriler:** `capa-gramer` · `test-vektoru` · `lisans-kapisi` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A38`

## Amaç
Next.js 16 ile her âyete (`/kuran/[sure]/[ayet]`, 6.236 sayfa) ve her mushaf sayfasına (`/mushaf/[sayfa]`, 604 sayfa) kalıcı adresli, statik üretilen ve arama motorunda görünen bir site kurulur. Site içeriği yalnız `public` kapısından geçmiş, imzalı public manifestteki paketlerden okur; paylaşılan paketleri (`anchors`, `search`, `reader-core`, `ui-tokens`) kullanır; `mutalaa://q/2/255` ile `/kuran/2/255` aynı çapaya gider. Web elektronik ortamda Kur'an yayınıdır; Kurul'un web görüşü gelmeden site canlıya açılmaz.

## Okunacak belgeler
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 5, §6 soru 3
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §11 `toRoute` ve web rotaları tablosu, §12 sure adları, §13 ÇŞ-7
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §1 Web satırı, §2.6, §4.2 Next.js
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §3, §8, §10, §11 soru 3 · [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1, §2, §3
- [Arama](../../03-veri/05-arama-fts5.md): §1 normalleştirme, §4 sonuç parçası, §5 web araması
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest ve imza, §7 süzme ve `page_map` notu
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §3, §6 atıf ve Kurul bilgisi, §7.5 soru 3
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.5, §9, §10 `packages/ui-tokens` · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §7 kural 5

## Kapsam
**Yapılır**
- Web rotalarının kesinleşmesi (ÇŞ-7), `apps/web` iskeleti, public paketlerden içerik okuma betiği.
- `/kuran/[sure]/[ayet]`, `/mushaf/[sayfa]` ve karara göre meal ve tefsir rotalarının statik üretimi; atıf ve Kurul bilgisi.
- Web araması, ortak vektörlerin web test koşusu, `mutalaa://` ↔ `https://` eşlik testi, evrensel bağlantı dosyaları.
- Canlıya açılış kapısı.

**Yapılmaz**
- Web'de hesap ve senkron: Fazlar Faz 5'e göre "hesap web'de istenirse" Faz 4'e bağlı; istenirse ayrı plan (`/karar`).
- Risale rotaları (Risale metni `public` olunca, A39). Mushaf A (QPC fontları) web'de: QF şartları web için incelenmedi; kapsam dışı (öneri).
- Mobil uygulamada evrensel bağlantının yayımlanması: yeni uygulama sürümüyle (A34 yordamı).

## Adımlar
### A38.1 · Doğrulamalar ve kararlar
- `arastirmaci` resmî kaynaktan doğrular: Faz 5 başındaki güncel kararlı Next.js sürümü, `ensureStatic` ve statik rota parametresi API'sinin davranışı (belge 16.4 diyor; yükseltme yolu `next upgrade --agent`); 6.840 statik sayfanın derleme süresi ve bellek etkisi; Orama'nın Türkçe ve Arapça gövdeleyicileri; Node'da paket SQLite dosyalarını salt okunur açacak kitaplık; Apple evrensel bağlantı ve Android uygulama bağlantısı dosyalarının biçimi. Sürümler kurulum günü kilit dosyasına yazılır.
- `/karar` (proje sahibi onaylar): web rotalarının kesin listesi, meal ve tefsir rotaları dahil (Çapa şeması §11 tablosu "Faz 5'te kesinleşir"); arama yolu; web barındırma.
- Arama kuralı: Arama §5 web aramasını editoryal veritabanındaki `tsvector` sütunlarına bağlıyor; oysa editoryal veritabanı lisansı bekleyen metinleri taşıdığı için dışarıya açılmaz (Genel mimari §10, §11 soru 3). Bu aşamada web araması editoryal veritabanını sorgulamaz. Seçenekler: (a) derlemede public paketlerden üretilen Orama dizini; (b) public paketlerden doldurulan ayrı bir arama veritabanı ve genel kipte bir uç. İki yolda da sorgu `packages/search` ile normalleşir; seçim `/karar` ile yapılır, Arama §5 `/belge-esitle` ile güncellenir.
- Kurul'a web sorusu `/yazisma kurul` ile taslaklanır (Yayın kapısı §7.5 soru 3).
- **Bitti sayılır:** rapor ve kararlar defterde; `shared/test-vectors/anchors/route.jsonl` kesinleşen web rotalarını taşıyor ve üç dilde yeşil.

### A38.2 · `apps/web` iskeleti ve içerik kaynağı
- `web-gelistirici`: `apps/web` (`@mutalaa/web`); Tailwind v4 ile `packages/ui-tokens` teması ve tema değişken blokları; shadcn/ui; ESLint ve Turborepo görevleri. `packages/*` içine `next` girmez (Proje yapısı §2 kural 2).
- İçerik betiği (öneri `apps/web/scripts/fetch-packs.mjs`): `MANIFEST_URL` ile public manifesti indirir, imzayı `public` açık anahtarıyla doğrular, her paketin sha256'sını denetler, her `pack_source` satırının `serbest` olduğunu ve `test-` kaynak bulunmadığını kontrol eder; aksi hâlde sıfırdan farklı kodla durur. Paketler `apps/web/.content/` (git dışı, öneri) altına iner. `dev` ve `internal` manifestleri hiçbir yapılandırmada okunmaz.
- **Bitti sayılır:** bozuk imzalı, `serbest` dışı ve `test-` kaynaklı üç fikstür manifestiyle betik sıfırdan farklı kodla çıkıyor (test).

### A38.3 · Rotalar ve statik üretim
- `/kuran/[sure]/[ayet]`: âyet metni kanonik Tanzil metniyle, hiçbir dönüşüm uygulanmadan (NFC yok), `lang="ar"` ve `dir="rtl"` ile; Elmalılı meali; sure adı `shared/data/sure-adlari.json`'dan; atıflar paketin `attribution` tablosundan (Tanzil bildiriminin tam metni ve tanzil.net bağlantısı, Elmalılı künyesi); Kurul onay bilgisi (numara, tarih, özetin ilk 12 karakteri).
- `/mushaf/[sayfa]`: Mod C mantığıyla Medine sayfa sınırları; sınırlar public `core` paketindeki `page_map`'ten gelir. `page_map` yoksa bu rotalar üretilmez ve kayda yazılır (İçerik paketleri §7).
- Meal ve tefsir rotaları A38.1 kararıyla; tefsir yalnız `tefsir-elmalili` public manifestte ise.
- `generateStaticParams` ve `ensureStatic` ile statik üretim; geçersiz adres (`/kuran/2/300`) en yakın âyete yuvarlanmaz, 404 döner.
- Erişilebilirlik [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md) §2.5 ve §9'a göre: metin kontrastı en az 4,5:1, dokunma hedefi, Arapça ve Türkçe ayrı boyut, %200 büyütme; `arayuz-denetcisi` ekran görüntüleriyle denetler.
- **Bitti sayılır:** statik parametre testleri 6.236 ve 604 değerini veriyor; 404 ve metin bütünlüğü testleri yeşil.

### A38.4 · Arama
- A38.1'deki yol uygulanır. Sorgu normalleştiricisinin sürümü paketlerin `normalizer_version` değeriyle aynıdır; sonuç parçası kanonik metinden `reader-core` ile üretilir, arama sütunu sayfada görünmez.
- `normalize/tr.jsonl`, `normalize/ar.jsonl` ve uygulanabilen `fts-query/query.jsonl` vektörleri web test koşusunda geçer (Faz 5 çıkış ölçütü).
- **Bitti sayılır:** arama testinde `Işık`, `ışık`, `IŞIK` ve `isik` sorguları aynı ilk sonucu getiriyor.

### A38.5 · Eşlik ve derin bağlantı
- `anchors/route.jsonl` her satırda yerel ve web rotasını taşır; `q:2:255` ↔ `mutalaa://q/2/255` ↔ `/kuran/2/255` satırı zorunludur. `toRoute` ve `fromRoute` gidiş-dönüş testi web test koşusunda da çalışır.
- Evrensel bağlantı ve uygulama bağlantısı dosyaları alan adında (İ-18) yayımlanmak üzere üretilir; uygulama tarafı yeni sürümle gelir. `https://<alan-adı>/kuran/2/255` uygulamada aynı çözücüye bağlanır (Mobil ekranlar §7 kural 5).
- **Bitti sayılır:** gidiş-dönüş testi yeşil; dosyalar üretildi ve sürüm kaydında.

### A38.6 · Canlıya açılış kapısı
- Önkoşullar: Kurul'un web görüşü karar defterinde, gerekiyorsa web için onay; barındırma kararı; alan adı. Eksikse aşama bu adımda `sürüyor` kalır ve beklenen insan adımı ilerleme dosyasına yazılır.
- Canlıda yalnız public paketler kullanılır; CI'daki web derlemesi aynı içerik betiğiyle doğrulanır.
- **Bitti sayılır:** canlı adreste `/kuran/2/255` 200 ve `/kuran/2/300` 404 dönüyor.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/web build` başarılı.
- [ ] Statik parametre testleri `/kuran` için 6.236, `/mushaf` için 604 değerini veriyor (ya da `page_map` yoksa `/mushaf` 0 ve gerekçe kayıtta).
- [ ] `anchors/route.jsonl` TypeScript, C#, Python ve web test koşusunda yeşil; `q:2:255` satırı iki rotayı taşıyor.
- [ ] Metin bütünlüğü testi: örnek âyetlerde sayfadaki Arapça metin `unit.text` ile bayt bayt aynı; `content-hash` vektöründeki NFC olmayan dizi bozulmuyor.
- [ ] İçerik betiğinin üç negatif testi sıfırdan farklı kodla duruyor.
- [ ] `/kuran/2/300` 404 testi ve arama testi yeşil.
- [ ] `apps/web` içinde PostgreSQL ya da editoryal veritabanı istemcisi yok (`grep` boş).
- [ ] Kontrast testi yeşil; `arayuz-denetcisi` bulguları kapalı.
- [ ] Canlıya açılış yapıldıysa karar defterinde Kurul'un web görüşü kayıtlı ve canlı adres testleri geçti.

## Doğrulama
```bash
pnpm --filter @mutalaa/anchors test && pnpm --filter @mutalaa/search test && pnpm --filter @mutalaa/ui-tokens test
pnpm --filter @mutalaa/web test
dotnet test server/Mutalaa.slnx && (cd pipeline && uv run pytest)
grep -n '"q:2:255"' shared/test-vectors/anchors/route.jsonl
grep -rniE "npgsql|postgres|ConnectionStrings" apps/web --include="*.ts" --include="*.tsx" --include="*.mjs"   # boş
MANIFEST_URL="https://<içerik-alanı>/public/manifest.json" pnpm --filter @mutalaa/web exec node scripts/fetch-packs.mjs
pnpm --filter @mutalaa/web build
# Canlıya açılıştan sonra (A38.6)
curl -s -o /dev/null -w "%{http_code}\n" "https://<alan-adı>/kuran/2/255"   # 200
curl -s -o /dev/null -w "%{http_code}\n" "https://<alan-adı>/kuran/2/300"   # 404
```
PowerShell'de: `$env:MANIFEST_URL = "https://<içerik-alanı>/public/manifest.json"` ve `curl.exe`.

## Dikkat
- Kanonik metin hiçbir katmanda dönüştürülmez: âyet metni React'e `normalize()` görmeden verilir; HTML kaçışı dışında değişiklik yoktur. Ayrıntı: `metin-butunlugu`.
- Web'e yalnız `public` içerik girer; `test-` kaynak hiçbir durumda girmez; editoryal veritabanı web'den sorgulanmaz.
- Kurul açısından web ayrı yayın olabilir (Açık soru); onaysız canlıya çıkış yoktur. Hukuki görüş değildir.
- Türkçe büyük-küçük harf `packages/search` açık eşlemesiyle; argümansız `toLocaleLowerCase` ve `localeCompare` ESLint'te yasak.
- Rotalar `packages/anchors` ile üretilir ve çözülür; elle dizgi birleştirilmez. Ayrıntı: `capa-gramer`.
- Windows: `.next/` ve `.content/` çok sayıda dosya üretir; OneDrive eşitlemesi ve uzun yol sorunları için `windows-sorun`.

## İnsan adımları
- Kurul'un web görüşü (Yayın kapısı §7.5 soru 3; İ-02 kanalıyla sorulur, gerekirse İ-19 ile başvuru): A38.6'dan önce.
- İ-18 · Alan adı (site, evrensel bağlantı dosyaları): A38.5 ve A38.6.
- Web barındırma kararı (numarasız; proje sahibi, `/karar`): A38.6'dan önce.
- Apple ekip kimliği ve Android imza parmak izi (İ-15 hesaplarından): A38.5.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/web/` (Next.js uygulaması, rotalar, `scripts/fetch-packs.mjs` öneri, testler)
- `shared/test-vectors/anchors/route.jsonl` (kesin web rotaları); `packages/anchors` web rota tablosu
- Evrensel bağlantı ve uygulama bağlantısı dosyaları (alan adında yayımlanmak üzere)
- Karar defteri: web rotaları, arama yolu, barındırma, Kurul web görüşü; Çapa şeması §11 ve Arama §5 güncellemeleri (`/belge-esitle`)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A38-web.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A37](./A37-elmalili-tefsir-paketi.md) · Sonraki: [A39](./A39-takvim-ve-lisans-olaylari.md)
